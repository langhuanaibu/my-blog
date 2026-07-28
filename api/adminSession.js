const {
  ADMIN_SESSION_COOKIE,
  createAdminSession,
  createHttpError,
  readJsonBody,
  requireAdminSession,
  sendJson,
  setCors
} = require('./_github');

const COOKIE_BASE = `${ADMIN_SESSION_COOKIE}=`;
const MAX_FAILED_ATTEMPTS = 5;
const LOGIN_WINDOW_MS = 15 * 60 * 1000;
const MAX_TRACKED_CLIENTS = 1000;
const loginAttempts = new Map();

function clientAddress(req) {
  const forwarded = req.headers?.['x-vercel-forwarded-for']
    || req.headers?.['x-forwarded-for'];
  const raw = Array.isArray(forwarded) ? forwarded[0] : forwarded;
  return String(raw || req.socket?.remoteAddress || 'unknown')
    .split(',')[0].trim().slice(0, 128) || 'unknown';
}

function pruneLoginAttempts(now) {
  for (const [key, row] of loginAttempts) {
    if (now - row.startedAt >= LOGIN_WINDOW_MS) loginAttempts.delete(key);
  }
  while (loginAttempts.size >= MAX_TRACKED_CLIENTS) {
    loginAttempts.delete(loginAttempts.keys().next().value);
  }
}

function retryAfterSeconds(req, now = Date.now()) {
  pruneLoginAttempts(now);
  const row = loginAttempts.get(clientAddress(req));
  if (!row || row.failures < MAX_FAILED_ATTEMPTS) return 0;
  return Math.max(1, Math.ceil((LOGIN_WINDOW_MS - (now - row.startedAt)) / 1000));
}

function recordFailedLogin(req, now = Date.now()) {
  pruneLoginAttempts(now);
  const key = clientAddress(req);
  const row = loginAttempts.get(key);
  if (row) {
    row.failures += 1;
  } else {
    loginAttempts.set(key, { failures: 1, startedAt: now });
  }
}

function clearLoginAttempts(req) {
  loginAttempts.delete(clientAddress(req));
}

async function handler(req, res) {
  setCors(res);
  res.setHeader('Cache-Control', 'no-store');

  if (req.method === 'OPTIONS') return res.status(200).end();

  try {
    if (req.method === 'POST') {
      const retryAfter = retryAfterSeconds(req);
      if (retryAfter) {
        res.setHeader('Retry-After', String(retryAfter));
        throw createHttpError(429, 'Too many login attempts');
      }
      const body = await readJsonBody(req);
      const expected = process.env.ADMIN_TOKEN;
      if (!expected) throw createHttpError(500, 'ADMIN_TOKEN is not configured');
      const supplied = String(body.token || '');
      const crypto = require('crypto');
      const a = Buffer.from(supplied);
      const b = Buffer.from(expected);
      if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) {
        recordFailedLogin(req);
        throw createHttpError(401, 'Unauthorized');
      }
      clearLoginAttempts(req);
      const session = createAdminSession(expected);
      res.setHeader('Set-Cookie', `${COOKIE_BASE}${session}; Path=/api; HttpOnly; Secure; SameSite=Strict; Max-Age=28800`);
      return sendJson(res, 200, { success: true, data: { authenticated: true } });
    }
    if (req.method === 'DELETE') {
      res.setHeader('Set-Cookie', `${COOKIE_BASE}; Path=/api; HttpOnly; Secure; SameSite=Strict; Max-Age=0`);
      return sendJson(res, 200, { success: true });
    }
    if (req.method === 'GET') {
      requireAdminSession(req);
      return sendJson(res, 200, { success: true, data: { authenticated: true } });
    }
    return sendJson(res, 405, { success: false, error: 'Method not allowed' });
  } catch (error) {
    return sendJson(res, error.status || 500, { success: false, error: error.message || 'Request failed' });
  }
}

handler._test = {
  MAX_FAILED_ATTEMPTS,
  resetLoginAttempts: () => loginAttempts.clear()
};

module.exports = handler;
