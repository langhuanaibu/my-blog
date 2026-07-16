const {
  POSTS_DIR,
  setCors,
  sendJson,
  createHttpError,
  requireAdmin,
  readJsonBody,
  listDirectory,
  readTextFile,
  putTextFile,
  deleteFile,
  validatePostPath,
  parsePost,
  composePost,
  readCoverMap,
  slugify,
  normalizeDate
} = require('./_github');

async function mapConcurrent(items, limit, fn) {
  const results = new Array(items.length);
  let next = 0;

  async function worker() {
    while (next < items.length) {
      const index = next++;
      results[index] = await fn(items[index]);
    }
  }

  await Promise.all(
    Array.from({ length: Math.min(limit, items.length) }, worker)
  );
  return results;
}

async function listPosts() {
  const files = (await listDirectory(POSTS_DIR)).filter(
    (item) => item.type === 'file' && item.name.endsWith('.md')
  );

  // 并发拉取文章内容，串行逐篇会随文章数增长撞上函数超时
  const posts = await mapConcurrent(files, 8, async (file) => {
    const { content, sha } = await readTextFile(file.path);
    return parsePost(file.path, content, sha);
  });

  posts.sort((a, b) => String(b.date).localeCompare(String(a.date)));
  return posts;
}

async function createPostPath(title, date) {
  const files = await listDirectory(POSTS_DIR);
  const used = new Set(files.map((file) => file.name));
  const base = `${normalizeDate(date).slice(0, 10)}-${slugify(title)}`;
  let name = `${base}.md`;
  let index = 2;

  while (used.has(name)) {
    name = `${base}-${index}.md`;
    index += 1;
  }

  return `${POSTS_DIR}/${name}`;
}

module.exports = async (req, res) => {
  setCors(res);

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    requireAdmin(req);

    if (req.method === 'GET') {
      const coverMap = await readCoverMap();

      if (req.query?.view === 'categories') {
        return sendJson(res, 200, {
          success: true,
          data: {
            categories: Object.keys(coverMap).filter((key) => key !== 'default'),
            coverMap
          }
        });
      }

      if (req.query?.filePath) {
        const filePath = validatePostPath(req.query.filePath);
        const { content, sha } = await readTextFile(filePath);
        return sendJson(res, 200, {
          success: true,
          data: parsePost(filePath, content, sha, true)
        });
      }

      return sendJson(res, 200, { success: true, data: await listPosts() });
    }

    if (req.method === 'POST') {
      const body = await readJsonBody(req);
      const article = body.article || {};
      const coverMap = await readCoverMap();
      let filePath = article.filePath ? validatePostPath(article.filePath) : '';
      let existing = null;
      let sha = '';

      if (filePath) {
        const current = await readTextFile(filePath);
        if (!article.sha || article.sha !== current.sha) {
          throw createHttpError(409, 'Article changed since it was opened; reload before saving');
        }
        sha = current.sha;
        existing = parsePost(filePath, current.content, sha, true);
      } else {
        filePath = await createPostPath(article.title, article.date);
      }

      const next = composePost(article, coverMap, existing);
      const result = await putTextFile(
        filePath,
        next.content,
        `${existing ? 'update' : 'publish'} post: ${next.title}`,
        sha || undefined
      );

      const saved = parsePost(filePath, next.content, result?.content?.sha, true);
      return sendJson(res, 200, { success: true, data: saved });
    }

    if (req.method === 'DELETE') {
      const body = await readJsonBody(req);
      const filePath = validatePostPath(body.filePath || req.query?.filePath);
      const { sha } = await readTextFile(filePath);
      if (!body.sha || body.sha !== sha) {
        throw createHttpError(409, 'Article changed since it was opened; reload before deleting');
      }
      await deleteFile(filePath, `delete post: ${filePath.split('/').pop()}`, sha);
      return sendJson(res, 200, { success: true });
    }

    return sendJson(res, 405, { success: false, error: 'Method not allowed' });
  } catch (error) {
    return sendJson(res, error.status || 500, {
      success: false,
      error: error.message || 'Request failed'
    });
  }
};
