import test from 'node:test';
import assert from 'node:assert/strict';

import {
  filterArticles,
  renderArticleCardMarkup,
  sortArticlesNewestFirst
} from '../public/article-archive.mjs';

const articles = [
  {
    id: 'older-post',
    title: 'C++ 速通笔记',
    excerpt: '整理基础语法和常见数据结构。',
    category: '数据结构与算法',
    date: '2026-04-12',
    readTime: 5
  },
  {
    id: 'newer-post',
    title: 'TypeScript 语法',
    excerpt: '记录 TypeScript 类型系统与实际使用方式。',
    category: '技术学习',
    date: '2026-05-07',
    readTime: 8
  }
];

test('sortArticlesNewestFirst returns a new list ordered by publish date', () => {
  const sorted = sortArticlesNewestFirst(articles);

  assert.deepEqual(sorted.map((article) => article.id), ['newer-post', 'older-post']);
  assert.deepEqual(articles.map((article) => article.id), ['older-post', 'newer-post']);
});

test('filterArticles applies category and keyword to title and excerpt', () => {
  assert.deepEqual(
    filterArticles(articles, { category: '技术学习', keyword: '类型' }).map((article) => article.id),
    ['newer-post']
  );
  assert.deepEqual(
    filterArticles(articles, { category: 'all', keyword: '数据结构' }).map((article) => article.id),
    ['older-post']
  );
});

test('renderArticleCardMarkup includes summary metadata and read state', () => {
  const markup = renderArticleCardMarkup(articles[1], true);

  assert.match(markup, /TypeScript 语法/);
  assert.match(markup, /记录 TypeScript 类型系统与实际使用方式。/);
  assert.match(markup, /技术学习/);
  assert.match(markup, /2026-05-07/);
  assert.match(markup, /约 8 分钟阅读/);
  assert.match(markup, /已读/);
  assert.match(markup, /data-article-id="newer-post"/);
});

test('renderArticleCardMarkup escapes article-provided HTML', () => {
  const markup = renderArticleCardMarkup({
    ...articles[1],
    title: '<img src=x onerror=alert(1)>',
    excerpt: '<script>alert(1)</script>'
  }, false);

  assert.doesNotMatch(markup, /<script>|<img/);
  assert.match(markup, /&lt;img/);
  assert.match(markup, /&lt;script&gt;/);
});
