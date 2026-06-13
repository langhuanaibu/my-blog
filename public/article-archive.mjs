function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

export function sortArticlesNewestFirst(articles) {
  return [...articles].sort((a, b) => new Date(b.date) - new Date(a.date));
}

export function filterArticles(articles, { category = 'all', keyword = '' } = {}) {
  const normalizedKeyword = String(keyword).toLowerCase().trim();

  return articles.filter((article) => {
    const matchesCategory = category === 'all' || article.category === category;
    const searchableText = `${article.title || ''} ${article.excerpt || ''}`.toLowerCase();
    return matchesCategory && (!normalizedKeyword || searchableText.includes(normalizedKeyword));
  });
}

export function renderArticleCardMarkup(article, isRead = false) {
  const category = article.category || '未分类';
  const excerpt = article.excerpt || '这篇文章暂时没有摘要。';
  const readTime = Number(article.readTime) || 1;
  const readBadge = isRead
    ? '<span class="article-summary-card__read">已读</span>'
    : '';

  return `
    <button class="article-summary-card" type="button" data-article-id="${escapeHtml(article.id)}">
      <span class="article-summary-card__topline">
        <span class="article-summary-card__category">${escapeHtml(category)}</span>
        ${readBadge}
      </span>
      <span class="article-summary-card__title">${escapeHtml(article.title)}</span>
      <span class="article-summary-card__excerpt">${escapeHtml(excerpt)}</span>
      <span class="article-summary-card__meta">
        <span>${escapeHtml(article.date)}</span>
        <span aria-hidden="true">·</span>
        <span>约 ${readTime} 分钟阅读</span>
      </span>
    </button>
  `;
}
