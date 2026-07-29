const {
  ADMIN_SESSION_COOKIE,
  createAdminSession,
  createHttpError,
  readJsonBody,
  requireAdminSession,
  sendError,
  sendJson,
  setCors
} = require('./_github');
const {
  MAX_FAILED_ATTEMPTS,
  clearLoginAttempts,
  recordFailedLogin,
  resetLoginAttempts,
  retryAfterSeconds
} = require('./_loginGuard');

const COOKIE_BASE = `${ADMIN_SESSION_COOKIE}=`;

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
      // 验过明文主口令，签发的会话才配得上 admin scope（可发文章/改设置/传图）。
      const session = createAdminSession(expected, Date.now(), 'admin');
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
    return sendError(res, error);
  }
}

handler._test = {
  MAX_FAILED_ATTEMPTS,
  resetLoginAttempts
};

module.exports = handler;
