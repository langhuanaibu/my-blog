const {
  setCors,
  sendJson,
  createHttpError,
  requireAdminSession,
  readJsonBody,
  readTextFile,
  putTextFile
} = require('./_github');

// 新闻驾驶舱用户状态写回通道：反馈 / 稍后读 / 收藏，追加写入仓库数据文件。
// 仅本人（由 ADMIN_TOKEN 换取的签名会话）可用；管线在次日运行时读取 feedback/read_later。
const STATE_FILES = {
  feedback: 'source/news/data/feedback.json',
  read_later: 'source/news/data/read_later.json',
  favorites: 'source/news/data/favorites.json'
};

const FEEDBACK_ACTIONS = ['not_interested', 'more_like_this', 'low_quality_source', 'track', 'untrack'];
const READ_LATER_OPS = ['add', 'done', 'remove'];
const FAVORITES_OPS = ['add', 'remove'];
const MAX_ENTRIES = 1000;
const MAX_PAYLOAD_BYTES = 4096;

function emptyState(type) {
  return type === 'feedback'
    ? { version: 1, entries: [] }
    : { version: 1, items: [] };
}

function entriesKey(type) {
  return type === 'feedback' ? 'entries' : 'items';
}

function clip(value, max) {
  return String(value ?? '').slice(0, max);
}

function validateEntry(type, payload) {
  if (!STATE_FILES[type]) {
    throw createHttpError(400, `Invalid type: ${type}`);
  }
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw createHttpError(400, 'payload must be an object');
  }
  if (Buffer.byteLength(JSON.stringify(payload), 'utf8') > MAX_PAYLOAD_BYTES) {
    throw createHttpError(400, 'payload too large');
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(payload.date || ''))) {
    throw createHttpError(400, 'payload.date must be YYYY-MM-DD');
  }
  if (!String(payload.item_id || '').trim()) {
    throw createHttpError(400, 'payload.item_id is required');
  }

  const entry = {
    date: payload.date,
    item_id: clip(payload.item_id, 60),
    title: clip(payload.title, 200),
    category: clip(payload.category, 20)
  };

  if (type === 'feedback') {
    if (!FEEDBACK_ACTIONS.includes(payload.action)) {
      throw createHttpError(400, `payload.action must be one of: ${FEEDBACK_ACTIONS.join(', ')}`);
    }
    entry.action = payload.action;
    if (payload.op === 'remove') {
      // 撤销：删掉最后一条同 date+item_id+action 的反馈，当作没点过
      entry.op = 'remove';
      return entry;
    }
    entry.reasons = (Array.isArray(payload.reasons) ? payload.reasons : [])
      .slice(0, 5)
      .map((r) => clip(r, 50));
    entry.note = clip(payload.note, 500);
    if (payload.event_id) entry.event_id = clip(payload.event_id, 60);
    if (payload.source) entry.source = clip(payload.source, 100);
  } else if (type === 'read_later') {
    entry.op = READ_LATER_OPS.includes(payload.op) ? payload.op : 'add';
    if (entry.op === 'add') {
      const url = String(payload.url || '');
      if (!/^https?:\/\//i.test(url)) {
        throw createHttpError(400, 'payload.url must be an http(s) URL');
      }
      entry.url = clip(url, 500);
      entry.done = false;
    }
  } else {
    // favorites：永久收藏。核心是 date+item_id 引用（前端凭它从 daily/*.js
    // 重渲染完整卡片），url 仅作降级展示的兜底，允许缺省
    entry.op = FAVORITES_OPS.includes(payload.op) ? payload.op : 'add';
    if (entry.op === 'add') {
      const url = String(payload.url || '');
      if (/^https?:\/\//i.test(url)) entry.url = clip(url, 500);
    }
  }

  return entry;
}

function appendEntry(state, type, entry, now) {
  const key = entriesKey(type);
  const list = Array.isArray(state[key]) ? state[key] : [];

  if (type === 'read_later' || type === 'favorites') {
    const idx = list.findIndex((it) => it.item_id === entry.item_id && it.date === entry.date);
    if (entry.op === 'done') {
      if (idx === -1) return { state, deduped: true };
      const items = [...list];
      items[idx] = { ...items[idx], done: true, done_ts: now };
      return { state: { ...state, [key]: items }, deduped: false };
    }
    if (entry.op === 'remove') {
      if (idx === -1) return { state, deduped: true };
      return { state: { ...state, [key]: list.filter((_, i) => i !== idx) }, deduped: false };
    }
    if (idx !== -1) return { state, deduped: true };
    const { op, ...added } = entry;
    return { state: { ...state, [key]: [...list, { ts: now, ...added }].slice(-MAX_ENTRIES) }, deduped: false };
  }

  // 反馈撤销（feedback 专用；read_later/favorites 的 remove 在上面自己的分支里处理）：
  // 删掉最后一条同 (item_id, date, action) 的记录。匹配到 action 级，不看 reasons/source——
  // 目前只有 more_like_this 用它，每个 item+date 至多一条，精确无误。若将来给
  // low_quality_source / not_interested 也加撤销，需把匹配键细化到具体来源/理由。
  if (entry.op === 'remove') {
    let idx = -1;
    for (let i = list.length - 1; i >= 0; i--) {
      const it = list[i];
      if (it.item_id === entry.item_id && it.date === entry.date && it.action === entry.action) {
        idx = i;
        break;
      }
    }
    if (idx === -1) return { state, deduped: true };
    return { state: { ...state, [key]: list.filter((_, i) => i !== idx) }, deduped: false };
  }

  const next = { ...state, [key]: [...list, { ts: now, ...entry }].slice(-MAX_ENTRIES) };
  return { state: next, deduped: false };
}

async function readState(type) {
  try {
    const { content, sha } = await readTextFile(STATE_FILES[type]);
    const parsed = JSON.parse(content);
    if (parsed && typeof parsed === 'object') return { state: parsed, sha };
    return { state: emptyState(type), sha };
  } catch (error) {
    if (error.status === 404) {
      // 文件还不存在：冷启动，PUT 时不带 sha 即创建新文件
      return { state: emptyState(type), sha: undefined };
    }
    if (error instanceof SyntaxError) {
      throw createHttpError(500, `${STATE_FILES[type]} is corrupted`);
    }
    throw error;
  }
}

async function writeEntry(type, entry, now) {
  const attempt = async () => {
    const { state, sha } = await readState(type);
    const { state: next, deduped } = appendEntry(state, type, entry, now);
    if (!deduped) {
      await putTextFile(
        STATE_FILES[type],
        JSON.stringify(next, null, 1) + '\n',
        `news: ${entry.op === 'remove' ? 'remove' : 'append'} ${type} (${entry.date})`,
        sha
      );
    }
    return { deduped, count: next[entriesKey(type)].length };
  };

  try {
    return await attempt();
  } catch (error) {
    // sha 过期（与其他提交撞车）重读重试一次
    if (error.status === 409 || error.status === 422) {
      return attempt();
    }
    throw error;
  }
}

async function handler(req, res) {
  setCors(res);

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    requireAdminSession(req);

    if (req.method === 'GET') {
      const type = String(req.query?.type || '');
      if (!STATE_FILES[type]) {
        throw createHttpError(400, `Invalid type: ${type}`);
      }
      const { state } = await readState(type);
      return sendJson(res, 200, { success: true, data: state });
    }

    if (req.method === 'POST') {
      const body = await readJsonBody(req);
      const type = String(body.type || '');
      const entry = validateEntry(type, body.payload);
      const now = new Date().toISOString();
      const result = await writeEntry(type, entry, now);
      return sendJson(res, 200, {
        success: true,
        data: { type, count: result.count, deduped: result.deduped }
      });
    }

    return sendJson(res, 405, { success: false, error: 'Method not allowed' });
  } catch (error) {
    return sendJson(res, error.status || 500, {
      success: false,
      error: error.message || 'Request failed'
    });
  }
}

handler._test = {
  STATE_FILES,
  FEEDBACK_ACTIONS,
  validateEntry,
  appendEntry,
  emptyState
};

module.exports = handler;
