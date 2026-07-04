const crypto = require('crypto');
const { pinyin } = require('pinyin-pro');

const POSTS_DIR = 'source/_posts';
const COVER_MAP_PATH = 'source/_data/category-covers.json';
const FALLBACK_COVER = '/images/covers/defaults/fallback.webp';

function setCors(res) {
  // 鉴权走 Bearer 头不依赖 Cookie，不设 Allow-Credentials（与 * 组合本身非法）
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,POST,DELETE');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
}

function sendJson(res, status, body) {
  return res.status(status).json(body);
}

function createHttpError(status, message) {
  const error = new Error(message);
  error.status = status;
  return error;
}

function timingSafeEqual(a, b) {
  const bufA = Buffer.from(String(a));
  const bufB = Buffer.from(String(b));
  return bufA.length === bufB.length && crypto.timingSafeEqual(bufA, bufB);
}

function requireAdmin(req) {
  const expected = process.env.ADMIN_TOKEN;
  if (!expected) {
    throw createHttpError(500, 'ADMIN_TOKEN is not configured');
  }

  if (!timingSafeEqual(req.headers.authorization || '', `Bearer ${expected}`)) {
    throw createHttpError(401, 'Unauthorized');
  }
}

function repoConfig() {
  const token = process.env.GITHUB_TOKEN;
  const owner = process.env.GITHUB_OWNER || process.env.GITHUB_REPOSITORY_OWNER;
  const repo =
    process.env.GITHUB_REPO ||
    (process.env.GITHUB_REPOSITORY || '').split('/')[1];
  const branch = process.env.GITHUB_BRANCH || 'main';

  if (!token || !owner || !repo) {
    throw createHttpError(500, 'GitHub repository environment is not configured');
  }

  return { token, owner, repo, branch };
}

function encodePath(filePath) {
  return filePath.split('/').map(encodeURIComponent).join('/');
}

async function githubRequest(filePath, options = {}) {
  const { token, owner, repo, branch } = repoConfig();
  const method = options.method || 'GET';
  const url = new URL(`https://api.github.com/repos/${owner}/${repo}/contents/${encodePath(filePath)}`);

  if (method === 'GET') {
    url.searchParams.set('ref', branch);
  }

  const response = await fetch(url, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'Content-Type': 'application/json',
      'User-Agent': 'aoiblog-admin'
    },
    body: options.body ? JSON.stringify({ ...options.body, branch }) : undefined
  });

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      // GitHub 偶发 502 返回 HTML，保留原状态码而不是抛裸 SyntaxError
      data = null;
    }
  }

  if (!response.ok) {
    const message = data?.message || `GitHub request failed: ${response.status}`;
    throw createHttpError(response.status, message);
  }

  if (text && data === null) {
    throw createHttpError(502, 'GitHub returned a non-JSON response');
  }

  return data;
}

async function readJsonBody(req) {
  if (req.body && typeof req.body === 'object') return req.body;
  if (typeof req.body === 'string') return JSON.parse(req.body || '{}');

  const chunks = [];
  for await (const chunk of req) {
    chunks.push(chunk);
  }

  const raw = Buffer.concat(chunks).toString('utf8');
  return raw ? JSON.parse(raw) : {};
}

async function listDirectory(dirPath) {
  const data = await githubRequest(dirPath);
  return Array.isArray(data) ? data : [];
}

async function readTextFile(filePath) {
  const data = await githubRequest(filePath);
  const content = Buffer.from(String(data.content || '').replace(/\n/g, ''), 'base64').toString('utf8');
  return { content, sha: data.sha };
}

async function putTextFile(filePath, content, message, sha) {
  return githubRequest(filePath, {
    method: 'PUT',
    body: {
      message,
      content: Buffer.from(content, 'utf8').toString('base64'),
      sha
    }
  });
}

async function putBase64File(filePath, contentBase64, message) {
  return githubRequest(filePath, {
    method: 'PUT',
    body: {
      message,
      content: contentBase64
    }
  });
}

async function deleteFile(filePath, message, sha) {
  return githubRequest(filePath, {
    method: 'DELETE',
    body: { message, sha }
  });
}

function validatePostPath(filePath) {
  const value = String(filePath || '');
  if (!value.startsWith(`${POSTS_DIR}/`) || !value.endsWith('.md') || value.includes('..')) {
    throw createHttpError(400, 'Invalid post path');
  }
  return value;
}

function yamlString(value) {
  return JSON.stringify(String(value ?? ''));
}

function unquote(value) {
  return String(value || '').trim().replace(/^['"]|['"]$/g, '');
}

function readScalar(frontMatter, key) {
  const match = frontMatter.match(new RegExp(`^${key}:\\s*(.+)$`, 'm'));
  return match ? unquote(match[1]) : '';
}

function readList(frontMatter, key) {
  const match = frontMatter.match(new RegExp(`^${key}:\\n((?:\\s+-\\s*.+\\n?)+)`, 'm'));
  if (!match) return [];
  return match[1]
    .split(/\r?\n/)
    .map((line) => line.replace(/^\s+-\s*/, '').trim())
    .filter(Boolean)
    .map(unquote);
}

function splitLegacyComments(content) {
  const match = content.match(/\n*<section class="legacy-comments">[\s\S]*?<\/section>\s*$/);
  return {
    editableContent: match ? content.slice(0, match.index).trimEnd() : content.trimEnd(),
    legacySuffix: match ? match[0].trim() : ''
  };
}

function parsePost(filePath, source, sha, includeContent = false) {
  const match = source.match(/^---\n([\s\S]*?)\n---\n?/);
  const frontMatter = match ? match[1] : '';
  const rawContent = match ? source.slice(match[0].length) : source;
  const { editableContent, legacySuffix } = splitLegacyComments(rawContent);
  const categories = readList(frontMatter, 'categories');

  const article = {
    filePath,
    sha,
    title: readScalar(frontMatter, 'title') || filePath.replace(/^.*\/|\.md$/g, ''),
    date: readScalar(frontMatter, 'date'),
    updated: readScalar(frontMatter, 'updated'),
    category: categories[0] || '未分类',
    categories,
    index_img: readScalar(frontMatter, 'index_img'),
    old_id: readScalar(frontMatter, 'old_id'),
    twikooPath: readScalar(frontMatter, 'twikooPath'),
    excerpt: editableContent.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim().slice(0, 160)
  };

  if (includeContent) {
    article.content = editableContent;
    article.legacySuffix = legacySuffix;
  }

  return article;
}

function normalizeDate(value) {
  const text = String(value || '').trim();
  if (!text) return today();
  // 接受纯日期或带时间的日期（原样保留，日期变了 permalink 就变了）
  if (/^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?$/.test(text)) return text;
  // 无法解析的日期直接报错，静默回退到今天会改文章 URL、断开评论关联
  throw createHttpError(400, `Invalid date: ${text}`);
}

function today() {
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  });
  return formatter.format(new Date());
}

function timestamp() {
  const formatter = new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });
  return formatter
    .formatToParts(new Date())
    .filter((part) => part.type !== 'literal')
    .map((part) => part.value)
    .join('');
}

function slugify(title, fallback = 'post') {
  const latin = pinyin(String(title || ''), {
    toneType: 'none',
    type: 'array',
    nonZh: 'consecutive'
  }).join(' ');

  const slug = latin
    .toLowerCase()
    .replace(/['"]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .replace(/-{2,}/g, '-');

  return slug || fallback;
}

function stripFrontMatter(content) {
  return String(content || '').replace(/^---\n[\s\S]*?\n---\n?/, '').trim();
}

function coverForCategory(coverMap, category, explicitCover) {
  return explicitCover || coverMap[category] || coverMap.default || FALLBACK_COVER;
}

function composePost(article, coverMap, existing) {
  const title = String(article.title || '').trim();
  if (!title) throw createHttpError(400, 'Title is required');

  const category = String(article.category || existing?.category || '未分类').trim() || '未分类';
  const date = normalizeDate(article.date || existing?.date);
  const updated = today();
  const indexImg = coverForCategory(coverMap, category, String(article.index_img || '').trim());
  const oldId = existing?.old_id || '';
  const twikooPath = existing?.twikooPath || '';
  let body = stripFrontMatter(article.content);

  if (existing?.legacySuffix && !body.includes('legacy-comments')) {
    body = `${body}\n\n${existing.legacySuffix}`;
  }

  const frontMatter = [
    '---',
    `title: ${yamlString(title)}`,
    `date: ${yamlString(date)}`,
    `updated: ${yamlString(updated)}`,
    'categories:',
    `  - ${yamlString(category)}`,
    `index_img: ${yamlString(indexImg)}`
  ];

  if (oldId) frontMatter.push(`old_id: ${yamlString(oldId)}`);
  if (twikooPath) frontMatter.push(`twikooPath: ${yamlString(twikooPath)}`);
  frontMatter.push('---', '');

  return {
    content: `${frontMatter.join('\n')}${body.trim()}\n`,
    date,
    category,
    indexImg,
    title
  };
}

async function readCoverMap() {
  try {
    const { content } = await readTextFile(COVER_MAP_PATH);
    return JSON.parse(content);
  } catch {
    return { default: FALLBACK_COVER };
  }
}

module.exports = {
  POSTS_DIR,
  setCors,
  sendJson,
  createHttpError,
  requireAdmin,
  readJsonBody,
  listDirectory,
  readTextFile,
  putTextFile,
  putBase64File,
  deleteFile,
  validatePostPath,
  parsePost,
  composePost,
  readCoverMap,
  slugify,
  timestamp,
  normalizeDate
};
