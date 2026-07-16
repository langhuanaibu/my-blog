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

module.exports = async (req, res) => {
  setCors(res);
  res.setHeader('Cache-Control', 'no-store');

  if (req.method === 'OPTIONS') return res.status(200).end();

  try {
    if (req.method === 'POST') {
      const body = await readJsonBody(req);
      const expected = process.env.ADMIN_TOKEN;
      if (!expected) throw createHttpError(500, 'ADMIN_TOKEN is not configured');
      const supplied = String(body.token || '');
      const crypto = require('crypto');
      const a = Buffer.from(supplied);
      const b = Buffer.from(expected);
      if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) throw createHttpError(401, 'Unauthorized');
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
};
