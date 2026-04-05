<template>
  <div class="page-shell">
    <header class="site-header">
      <div class="container header-inner">
        <a class="brand" href="#hero">Aoitsuki</a>
        <nav class="site-nav" aria-label="主导航">
          <a href="#latest">最新文章</a>
          <a href="#columns">专栏</a>
          <a href="#about">关于我</a>
          <a href="#contact">留言</a>
          <a href="/articles.html">文章归档</a>
          <button
            class="theme-toggle"
            type="button"
            :aria-label="isDark ? '切换到浅色主题' : '切换到深色主题'"
            @click="toggleTheme"
          >
            {{ isDark ? '浅色' : '深色' }}
          </button>
        </nav>
      </div>
    </header>

    <main>
      <section id="hero" class="hero-section">
        <div class="container hero-grid">
          <div class="hero-copy">
            <p class="eyebrow">Vue 驱动的轻量首页</p>
            <h1>用更少的首屏脚本，让博客更快抵达读者。</h1>
            <p class="hero-text">
              首页现在由 Vue 渲染，静态内容走组件化复用，文章摘要走按需请求，评论系统改成延后加载，
              保留内容表达，同时减少阻塞资源。
            </p>
            <div class="hero-actions">
              <a class="primary-link" href="/articles.html">阅读全部文章</a>
              <a class="secondary-link" href="#latest">查看最新更新</a>
            </div>
          </div>

          <aside class="hero-panel" aria-label="性能亮点">
            <div class="metric-card">
              <span>首页策略</span>
              <strong>Vue 组件化</strong>
              <p>减少零散 DOM 操作，后续扩展和维护更轻松。</p>
            </div>
            <div class="metric-card">
              <span>外部资源</span>
              <strong>按需加载</strong>
              <p>评论区脚本不再阻塞首屏，用户需要时再拉取。</p>
            </div>
            <div class="metric-card">
              <span>文章摘要</span>
              <strong>无 Markdown 运行时</strong>
              <p>首页不再为摘要渲染加载整套 Markdown 解析库。</p>
            </div>
          </aside>
        </div>
      </section>

      <section id="latest" class="content-section">
        <div class="container">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Latest Posts</p>
              <h2>最新文章</h2>
            </div>
            <a class="text-link" href="/articles.html">进入归档页</a>
          </div>

          <div v-if="loading" class="state-card">正在加载最新文章...</div>
          <div v-else-if="error" class="state-card state-error">{{ error }}</div>
          <div v-else class="article-grid">
            <article
              v-for="article in latestArticles"
              :key="article.id"
              class="article-card"
            >
              <div class="article-meta">
                <span>{{ formatDate(article.date) }}</span>
                <span>{{ readingTime(article.content) }}</span>
              </div>
              <h3>{{ article.title }}</h3>
              <p class="article-tag">{{ article.category || '未分类' }}</p>
              <p class="article-excerpt">{{ excerpt(article.content) }}</p>
              <a class="text-link" :href="`/articles.html#${article.id}`">继续阅读</a>
            </article>
          </div>
        </div>
      </section>

      <section id="columns" class="content-section alt-section">
        <div class="container">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Columns</p>
              <h2>知识专栏</h2>
            </div>
          </div>

          <div class="column-grid">
            <a
              v-for="column in columns"
              :key="column.name"
              class="column-card"
              :href="column.href"
            >
              <span class="column-icon">{{ column.icon }}</span>
              <h3>{{ column.name }}</h3>
              <p>{{ column.description }}</p>
            </a>
          </div>
        </div>
      </section>

      <section id="about" class="content-section">
        <div class="container about-grid">
          <div>
            <p class="eyebrow">About</p>
            <h2>关于我</h2>
            <p class="about-copy">
              我在这里记录技术学习、算法训练和日常思考。新的首页尽量把视觉表达留给 CSS，
              把交互交给 Vue，把首屏网络负担降下来。
            </p>
          </div>
          <div class="stack-card">
            <h3>当前技术栈</h3>
            <ul>
              <li>Vue 3 组件化首页</li>
              <li>文章归档页与后台继续沿用现有页面</li>
              <li>API 仍然复用你的文章接口</li>
              <li>评论区脚本改为点击后加载</li>
            </ul>
          </div>
        </div>
      </section>

      <section id="contact" class="content-section contact-section">
        <div class="container contact-grid">
          <div>
            <p class="eyebrow">Contact</p>
            <h2>留言板</h2>
            <p class="about-copy">
              评论系统仍然使用 Twikoo，但只有当你准备查看或留言时才加载，
              这样首页访问不会先为评论能力付出性能成本。
            </p>
            <div class="contact-links">
              <a class="text-link" href="mailto:antemeridiem@foxmail.com">antemeridiem@foxmail.com</a>
              <a class="text-link" href="https://github.com/langhuanaibu" target="_blank" rel="noreferrer">GitHub</a>
            </div>
          </div>

          <div class="comments-card">
            <button
              v-if="!commentsVisible"
              class="primary-link button-link"
              type="button"
              @click="loadComments"
            >
              加载评论区
            </button>
            <p v-if="commentsStatus" class="comments-status">{{ commentsStatus }}</p>
            <div id="twikoo-comments" class="comments-host" />
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';

const THEME_KEY = 'theme';
const API_URL = 'https://api.aoiblog.top/api/getArticles';
const COMMENTS_SRC = 'https://cdn.staticfile.net/twikoo/1.6.32/twikoo.all.min.js';

const articles = ref([]);
const loading = ref(true);
const error = ref('');
const theme = ref('light');
const commentsVisible = ref(false);
const commentsStatus = ref('');

const columns = [
  {
    name: '技术学习',
    icon: '01',
    description: '记录前端、后端与工程化实践。',
    href: '/articles.html?category=' + encodeURIComponent('技术学习'),
  },
  {
    name: '数据结构与算法',
    icon: '02',
    description: '整理刷题思路与算法理解。',
    href: '/articles.html?category=' + encodeURIComponent('数据结构与算法'),
  },
  {
    name: '生活随笔',
    icon: '03',
    description: '保留日常感受与阶段性的思考。',
    href: '/articles.html?category=' + encodeURIComponent('随笔'),
  },
];

const latestArticles = computed(() => articles.value.slice(0, 3));
const isDark = computed(() => theme.value === 'dark');

function applyTheme(value) {
  theme.value = value;
  if (value === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
  } else {
    document.documentElement.removeAttribute('data-theme');
  }
}

function toggleTheme() {
  const nextTheme = theme.value === 'dark' ? 'light' : 'dark';
  applyTheme(nextTheme);
  window.localStorage.setItem(THEME_KEY, nextTheme);
}

function normalizeMarkdown(text) {
  return (text || '')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/!\[[^\]]*\]\([^)]+\)/g, ' ')
    .replace(/\[[^\]]+\]\([^)]+\)/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/[*_~>-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function excerpt(text) {
  const plain = normalizeMarkdown(text);
  return plain.length > 88 ? `${plain.slice(0, 88)}...` : plain || '这篇文章还没有摘要。';
}

function readingTime(text) {
  const plain = normalizeMarkdown(text);
  const minutes = Math.max(1, Math.ceil(plain.length / 280));
  return `${minutes} 分钟阅读`;
}

function formatDate(value) {
  if (!value) return '最近更新';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(date);
}

async function fetchArticles() {
  loading.value = true;
  error.value = '';

  try {
    const response = await fetch(API_URL, {
      method: 'GET',
      cache: 'no-store',
    });

    if (!response.ok) {
      throw new Error(`请求失败：${response.status}`);
    }

    const payload = await response.json();
    const list = Array.isArray(payload?.data) ? payload.data : [];

    articles.value = list.sort((left, right) => {
      return new Date(right.date) - new Date(left.date);
    });
  } catch (err) {
    error.value = '最新文章暂时无法加载，请稍后再试。';
    console.error(err);
  } finally {
    loading.value = false;
  }
}

function ensureCommentScript() {
  return new Promise((resolve, reject) => {
    if (window.twikoo) {
      resolve(window.twikoo);
      return;
    }

    const existing = document.querySelector(`script[src="${COMMENTS_SRC}"]`);
    if (existing) {
      existing.addEventListener('load', () => resolve(window.twikoo), { once: true });
      existing.addEventListener('error', reject, { once: true });
      return;
    }

    const script = document.createElement('script');
    script.src = COMMENTS_SRC;
    script.async = true;
    script.onload = () => resolve(window.twikoo);
    script.onerror = reject;
    document.body.appendChild(script);
  });
}

async function loadComments() {
  if (commentsVisible.value) {
    return;
  }

  commentsStatus.value = '正在加载评论区...';

  try {
    const twikoo = await ensureCommentScript();
    await twikoo.init({
      envId: 'https://twikoo.aoiblog.top',
      el: '#twikoo-comments',
      path: '/',
      lang: 'zh-CN',
    });
    commentsVisible.value = true;
    commentsStatus.value = '';
  } catch (err) {
    commentsStatus.value = '评论区加载失败，请稍后重试。';
    console.error(err);
  }
}

onMounted(() => {
  const savedTheme = window.localStorage.getItem(THEME_KEY);
  const preferredDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  applyTheme(savedTheme || (preferredDark ? 'dark' : 'light'));
  fetchArticles();
});
</script>

<style>
:root {
  --bg: #f4efe7;
  --surface: rgba(255, 255, 255, 0.8);
  --surface-strong: rgba(255, 255, 255, 0.96);
  --surface-border: rgba(92, 63, 38, 0.14);
  --text: #271c15;
  --muted: #6f5a4d;
  --accent: #9f4d2c;
  --accent-strong: #7f371b;
  --shadow: 0 18px 50px rgba(62, 36, 22, 0.12);
}

:root[data-theme='dark'] {
  --bg: #17120f;
  --surface: rgba(31, 24, 21, 0.72);
  --surface-strong: rgba(39, 30, 26, 0.96);
  --surface-border: rgba(255, 220, 194, 0.08);
  --text: #f5eadf;
  --muted: #c8b39f;
  --accent: #ff9f6e;
  --accent-strong: #ffb58a;
  --shadow: 0 18px 50px rgba(0, 0, 0, 0.28);
}

* {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  background:
    radial-gradient(circle at top left, rgba(255, 177, 129, 0.28), transparent 28%),
    radial-gradient(circle at 85% 15%, rgba(238, 227, 181, 0.26), transparent 22%),
    linear-gradient(180deg, #f7f2ea 0%, var(--bg) 52%, #efe5d5 100%);
  color: var(--text);
  min-height: 100vh;
}

:root[data-theme='dark'] body {
  background:
    radial-gradient(circle at top left, rgba(255, 159, 110, 0.18), transparent 28%),
    radial-gradient(circle at 85% 15%, rgba(255, 212, 120, 0.08), transparent 20%),
    linear-gradient(180deg, #120e0c 0%, var(--bg) 52%, #120d0b 100%);
}

a {
  color: inherit;
  text-decoration: none;
}

.page-shell {
  position: relative;
}

.container {
  width: min(1120px, calc(100% - 40px));
  margin: 0 auto;
}

.site-header {
  position: sticky;
  top: 0;
  z-index: 10;
  backdrop-filter: blur(18px);
  background: rgba(244, 239, 231, 0.72);
  border-bottom: 1px solid var(--surface-border);
}

:root[data-theme='dark'] .site-header {
  background: rgba(23, 18, 15, 0.72);
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 18px 0;
}

.brand {
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.site-nav {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
}

.site-nav a,
.theme-toggle {
  font-size: 0.96rem;
  color: var(--muted);
  transition: color 0.2s ease, transform 0.2s ease;
}

.site-nav a:hover,
.theme-toggle:hover,
.text-link:hover {
  color: var(--accent);
  transform: translateY(-1px);
}

.theme-toggle {
  border: 0;
  background: transparent;
  cursor: pointer;
  padding: 0;
}

.hero-section {
  padding: 88px 0 48px;
}

.hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(300px, 0.9fr);
  gap: 28px;
  align-items: stretch;
}

.hero-copy,
.hero-panel,
.article-card,
.column-card,
.stack-card,
.comments-card,
.state-card {
  background: var(--surface);
  border: 1px solid var(--surface-border);
  border-radius: 28px;
  box-shadow: var(--shadow);
}

.hero-copy {
  padding: 44px;
}

.eyebrow {
  margin: 0 0 10px;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-size: 0.78rem;
  font-weight: 700;
}

.hero-copy h1,
.section-heading h2,
.about-grid h2,
.contact-grid h2 {
  margin: 0;
  font-size: clamp(2.4rem, 5vw, 4.5rem);
  line-height: 1.04;
}

.hero-text,
.about-copy,
.metric-card p,
.article-excerpt,
.column-card p,
.stack-card li,
.comments-status {
  color: var(--muted);
  line-height: 1.8;
}

.hero-text {
  margin: 20px 0 0;
  max-width: 42rem;
  font-size: 1.02rem;
}

.hero-actions,
.contact-links {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  margin-top: 28px;
}

.primary-link,
.secondary-link,
.button-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 46px;
  padding: 0 20px;
  border-radius: 999px;
  font-weight: 600;
}

.primary-link {
  background: var(--accent);
  color: #fff8f4;
}

.primary-link:hover {
  background: var(--accent-strong);
}

.secondary-link {
  border: 1px solid var(--surface-border);
}

.hero-panel {
  padding: 22px;
  display: grid;
  gap: 14px;
}

.metric-card {
  background: var(--surface-strong);
  border-radius: 22px;
  padding: 22px;
}

.metric-card span,
.article-meta,
.article-tag {
  color: var(--muted);
  font-size: 0.9rem;
}

.metric-card strong {
  display: block;
  margin-top: 8px;
  font-size: 1.3rem;
}

.content-section {
  padding: 32px 0 44px;
}

.alt-section {
  padding-top: 12px;
}

.section-heading,
.about-grid,
.contact-grid {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
}

.section-heading {
  margin-bottom: 22px;
}

.article-grid,
.column-grid {
  display: grid;
  gap: 20px;
}

.article-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.column-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.article-card,
.column-card,
.stack-card,
.comments-card,
.state-card {
  padding: 24px;
}

.article-card h3,
.column-card h3,
.stack-card h3 {
  margin: 14px 0 12px;
  font-size: 1.28rem;
}

.article-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.article-tag {
  display: inline-flex;
  margin: 0 0 10px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(159, 77, 44, 0.12);
  color: var(--accent);
}

.column-card {
  min-height: 220px;
}

.column-icon {
  display: inline-flex;
  width: 44px;
  height: 44px;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  background: rgba(159, 77, 44, 0.12);
  color: var(--accent);
  font-weight: 700;
}

.about-grid,
.contact-grid {
  align-items: stretch;
}

.about-grid > *,
.contact-grid > * {
  flex: 1;
}

.stack-card ul {
  margin: 18px 0 0;
  padding-left: 18px;
}

.stack-card li + li {
  margin-top: 10px;
}

.contact-section {
  padding-bottom: 90px;
}

.comments-card {
  min-height: 220px;
}

.comments-host {
  margin-top: 16px;
}

.state-card {
  text-align: center;
}

.state-error {
  color: #b34747;
}

.text-link {
  color: var(--accent);
  font-weight: 600;
}

@media (max-width: 980px) {
  .hero-grid,
  .article-grid,
  .column-grid,
  .about-grid,
  .contact-grid {
    grid-template-columns: 1fr;
    display: grid;
  }

  .hero-copy {
    padding: 32px 24px;
  }

  .section-heading {
    display: grid;
    align-items: start;
  }
}

@media (max-width: 720px) {
  .container {
    width: min(100% - 28px, 1120px);
  }

  .header-inner {
    align-items: flex-start;
  }

  .site-nav {
    justify-content: flex-start;
    gap: 12px;
  }

  .hero-section {
    padding-top: 58px;
  }

  .hero-copy h1,
  .section-heading h2,
  .about-grid h2,
  .contact-grid h2 {
    font-size: clamp(2rem, 10vw, 3rem);
  }

  .article-grid,
  .column-grid {
    grid-template-columns: 1fr;
  }
}
</style>
