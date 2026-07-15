import { collectionCard, escapeHtml, safeUrl } from "./reports.js";
import { STORAGE_KEYS } from "./storage.js";

export async function renderFavorites({ storage, dataApi, api, personal, onData, ...options }) {
  const server = await api.get("favorites"); const favorites = server?.items || [];
  const local = {}; for (const item of favorites) local[`${item.date}:${item.item_id}`] = 1; storage.set(STORAGE_KEYS.favorites, local);
  if (!favorites.length) return '<section><h1>收藏</h1><div class="empty">还没有收藏内容</div></section>';
  const dates = [...new Set(favorites.map((item) => item.date))].sort().reverse(); const groups = [];
  for (const date of dates) {
    const data = await dataApi.daily(date); onData?.(data, date); const wanted = favorites.filter((item) => item.date === date); const cards = [];
    for (const favorite of wanted) {
      let found = false; for (const [type, rows] of [["news", data?.items], ["deep", data?.deep], ["paper", data?.papers]]) { const item = (rows || []).find((row) => row.id === favorite.item_id); if (item) { cards.push(collectionCard(item, type, date, { personal, ...options, favorites: local })); found = true; break; } }
      if (!found) cards.push(`<article class="row"><a href="${safeUrl(favorite.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(favorite.title || favorite.item_id)}</a></article>`);
    }
    groups.push(`<section><h2 class="feed-day">${date} <span class="n">${wanted.length} 条</span></h2><div class="grid">${cards.join("")}</div></section>`);
  }
  return `<section><h1>收藏</h1>${groups.join("")}</section>`;
}
