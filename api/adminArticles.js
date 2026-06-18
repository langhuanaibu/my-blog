const {
  POSTS_DIR,
  setCors,
  sendJson,
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

async function listPosts() {
  const files = await listDirectory(POSTS_DIR);
  const posts = [];

  for (const file of files.filter((item) => item.type === 'file' && item.name.endsWith('.md'))) {
    const { content, sha } = await readTextFile(file.path);
    posts.push(parsePost(file.path, content, sha));
  }

  posts.sort((a, b) => String(b.date).localeCompare(String(a.date)));
  return posts;
}

async function createPostPath(title, date) {
  const files = await listDirectory(POSTS_DIR);
  const used = new Set(files.map((file) => file.name));
  const base = `${normalizeDate(date)}-${slugify(title)}`;
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
        sha = current.sha;
        existing = parsePost(filePath, current.content, sha, true);
      } else {
        filePath = await createPostPath(article.title, article.date);
      }

      const next = composePost(article, coverMap, existing);
      await putTextFile(
        filePath,
        next.content,
        `${existing ? 'update' : 'publish'} post: ${next.title}`,
        sha || undefined
      );

      const saved = parsePost(filePath, next.content, undefined, true);
      return sendJson(res, 200, { success: true, data: saved });
    }

    if (req.method === 'DELETE') {
      const body = await readJsonBody(req);
      const filePath = validatePostPath(body.filePath || req.query?.filePath);
      const { sha } = await readTextFile(filePath);
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
