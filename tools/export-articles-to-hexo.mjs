import fs from 'node:fs/promises';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { pathToFileURL } from 'node:url';
import { pinyin } from 'pinyin-pro';

const API_BASE = 'https://aoiblog.top/api/getArticles';
const UNCATEGORIZED = '\u672a\u5206\u7c7b';
const COMMENTS_TITLE = '\u8bc4\u8bba\u533a';
const root = process.cwd();
const postsDir = path.join(root, 'source', '_posts');
const sourceDir = path.join(root, 'source');
const coverMapPath = path.join(sourceDir, '_data', 'category-covers.json');

function yamlString(value) {
  return JSON.stringify(String(value ?? ''));
}

function safeArticleId(value) {
  const id = String(value || '').trim();
  if (!/^[A-Za-z0-9_-]{1,100}$/.test(id)) {
    throw new Error(`Invalid legacy article id: ${id}`);
  }
  return id;
}

function safeInlineJson(value) {
  return JSON.stringify(value, null, 2)
    .replace(/</g, '\\u003c')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029');
}

function normalizeDate(value) {
  const text = String(value || '').trim();
  return /^\d{4}-\d{2}-\d{2}$/.test(text) ? text : new Date().toISOString().slice(0, 10);
}

function slugify(title, fallback) {
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

function normalizeContent(content) {
  return String(content || '')
    .replace(/src=(["'])\.?\/?images\//g, 'src=$1/images/')
    .replace(/src=(["'])images\//g, 'src=$1/images/')
    .replace(/\]\(\.\/images\//g, '](/images/')
    .replace(/\]\(images\//g, '](/images/');
}

async function readCoverMap() {
  try {
    return JSON.parse(await fs.readFile(coverMapPath, 'utf8'));
  } catch {
    return { default: '/images/covers/defaults/fallback.webp' };
  }
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed ${response.status}: ${url}`);
  }

  const data = await response.json();
  if (!data || data.success !== true) {
    throw new Error(`Invalid API response: ${url}`);
  }

  return data.data;
}

async function pathExists(target) {
  try {
    await fs.access(target);
    return true;
  } catch (error) {
    if (error.code === 'ENOENT') return false;
    throw error;
  }
}

async function replaceDirectoryAtomically(target, populate) {
  const parent = path.dirname(target);
  const name = path.basename(target);
  const nonce = randomUUID();
  const staging = path.join(parent, `.${name}.export-${nonce}`);
  const backup = path.join(parent, `.${name}.backup-${nonce}`);
  let currentMoved = false;
  let replacementMoved = false;

  await fs.mkdir(staging, { recursive: false });
  try {
    await populate(staging);
    if (await pathExists(target)) {
      await fs.rename(target, backup);
      currentMoved = true;
    }
    try {
      await fs.rename(staging, target);
      replacementMoved = true;
    } catch (error) {
      if (currentMoved) {
        await fs.rename(backup, target);
        currentMoved = false;
      }
      throw error;
    }
    if (currentMoved) {
      await fs.rm(backup, { recursive: true, force: true });
      currentMoved = false;
    }
  } finally {
    if (!replacementMoved) {
      await fs.rm(staging, { recursive: true, force: true });
    }
    if (currentMoved && !await pathExists(target) && await pathExists(backup)) {
      await fs.rename(backup, target);
    } else if (await pathExists(backup)) {
      await fs.rm(backup, { recursive: true, force: true });
    }
  }
}

async function writePost(article, usedSlugs, mapping, outputDir) {
  const articleId = safeArticleId(article.id);
  const date = normalizeDate(article.date);
  const [year, month, day] = date.split('-');
  const baseSlug = slugify(article.title, articleId);
  let slug = baseSlug;
  let index = 2;

  while (usedSlugs.has(`${date}-${slug}`)) {
    slug = `${baseSlug}-${index}`;
    index += 1;
  }
  usedSlugs.add(`${date}-${slug}`);

  const fileName = `${date}-${slug}.md`;
  const permalink = `/${year}/${month}/${day}/${slug}/`;
  const content = normalizeContent(article.content);
  const category = article.category || UNCATEGORIZED;
  const coverMap = await readCoverMap();
  const indexImg = coverMap[category] || coverMap.default;

  const frontMatter = [
    '---',
    `title: ${yamlString(article.title)}`,
    `date: ${yamlString(date)}`,
    `updated: ${yamlString(normalizeDate(article.modifyDate || date))}`,
    'categories:',
    `  - ${yamlString(category)}`,
    `index_img: ${yamlString(indexImg)}`,
    `old_id: ${yamlString(articleId)}`,
    `twikooPath: ${yamlString(articleId)}`,
    '---',
    ''
  ].join('\n');

  const twikooMount = [
    '',
    '<section class="legacy-comments">',
    `  <h2>${COMMENTS_TITLE}</h2>`,
    `  <div id="twikoo-${articleId}" data-twikoo-path="${articleId}"></div>`,
    '</section>',
    ''
  ].join('\n');

  await fs.writeFile(path.join(outputDir, fileName), `${frontMatter}${content}\n${twikooMount}`, 'utf8');
  mapping[articleId] = permalink;
}

async function writeCompatibilityPage(mapping) {
  const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>\u6587\u7ae0\u8df3\u8f6c - Aoitsuki</title>
  <meta name="robots" content="noindex">
  <script>
    const articleMap = ${safeInlineJson(mapping)};
    const id = decodeURIComponent((window.location.hash || '').replace(/^#/, ''));
    const target = articleMap[id];
    window.location.replace(target || '/archives/');
  </script>
</head>
<body>
  <p>\u6b63\u5728\u8df3\u8f6c\u5230\u65b0\u7684\u6587\u7ae0\u5730\u5740...</p>
</body>
</html>
`;
  await fs.writeFile(path.join(sourceDir, 'articles.html'), html, 'utf8');
}

async function writePages() {
  await fs.mkdir(path.join(sourceDir, 'about'), { recursive: true });
  await fs.mkdir(path.join(sourceDir, 'friends'), { recursive: true });
  await fs.mkdir(path.join(sourceDir, 'guestbook'), { recursive: true });

  await fs.writeFile(path.join(sourceDir, 'about', 'index.md'), `---
title: \u5173\u4e8e\u6211
layout: about
---

\u4e00\u540d\u5bcc\u6709\u4eba\u6587\u60c5\u6000\u7684\u5de5\u79d1\u751f\u3002

\u4e00\u540d\u52c7\u4e8e\u5b9e\u8df5\u7684\u7406\u60f3\u4e3b\u4e49\u8005\u3002

\u4e00\u540d\u6781\u5ea6\u4e50\u89c2\u7684\u60b2\u89c2\u4e3b\u4e49\u8005\u3002

## \u6280\u672f\u6808

- HTML5 & CSS3
- JavaScript
- C++ & C
- Python
- Git & GitHub
- \u6301\u7eed\u5b66\u4e60\u548c\u5b8c\u5584\u6280\u672f\u6808\u4e2d...
`, 'utf8');

  await fs.writeFile(path.join(sourceDir, 'friends', 'index.md'), `---
title: \u53cb\u60c5\u94fe\u63a5
---

## \u665a\u98ce\u62fe\u4e91\u7684\u535a\u5ba2

[https://www.cloudtide.xyz/](https://www.cloudtide.xyz/)

\u6f2b\u6f2b\u957f\u8def\uff0c\u539f\u4f5c\u6e05\u98ce\u4f34\u541b\u9014\u3002

## Aoitsuki's Blog

[https://langhuanaibu.github.io/my-blog/](https://langhuanaibu.github.io/my-blog/)

\u4e4c\u5e55\u5c7f\uff0c\u6d77\u76f8\u7eed...

## labuladong \u7684\u7b97\u6cd5\u7b14\u8bb0

[https://labuladong.online/zh/](https://labuladong.online/zh/)

\u6700\u9ad8\u6548\u7684\u7b97\u6cd5\u5237\u9898\u89e3\u51b3\u65b9\u6848\u3002
`, 'utf8');

  await fs.writeFile(path.join(sourceDir, 'guestbook', 'index.md'), `---
title: \u7559\u8a00\u677f
---

\u6b22\u8fce\u5728\u8fd9\u91cc\u7559\u4e0b\u4f60\u7684\u8db3\u8ff9\u3001\u5efa\u8bae\u6216\u4efb\u4f55\u60f3\u5bf9\u6211\u8bf4\u7684\u8bdd\u3002

\u90ae\u7bb1\uff1aantemeridiem@foxmail.com

GitHub\uff1a[github.com/langhuanaibu](https://github.com/langhuanaibu)

<section class="legacy-comments">
  <h2>${COMMENTS_TITLE}</h2>
  <div id="twikoo-guestbook" data-twikoo-path="/"></div>
</section>
`, 'utf8');
}

async function main() {
  const summaries = await fetchJson(`${API_BASE}?view=list`);
  if (!Array.isArray(summaries) || summaries.length === 0) {
    throw new Error('Article list is empty; existing posts were left untouched');
  }
  const articles = [];
  for (const summary of summaries) {
    const id = safeArticleId(summary?.id);
    const article = await fetchJson(`${API_BASE}?view=detail&id=${encodeURIComponent(id)}`);
    safeArticleId(article?.id);
    articles.push(article);
  }

  const usedSlugs = new Set();
  const mapping = {};
  await replaceDirectoryAtomically(postsDir, async (staging) => {
    for (const article of articles) {
      await writePost(article, usedSlugs, mapping, staging);
    }
  });

  await writeCompatibilityPage(mapping);
  await writePages();

  console.log(`Exported ${articles.length} posts.`);
}

export { replaceDirectoryAtomically, safeArticleId, safeInlineJson };

const invokedDirectly = process.argv[1]
  && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
if (invokedDirectly) {
  main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
