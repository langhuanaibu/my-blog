import { collectionCard, escapeHtml, safeUrl } from "./reports.js";
import { STORAGE_KEYS } from "./storage.js";

const savedAt = (item) => item.ts || item.saved_at || item.favorited_at || item.created_at || "";
const savedAtValue = (item) => { const value = savedAt(item); const numeric = Number(value); return value && Number.isFinite(numeric) ? numeric : Date.parse(value) || 0; };

export async function renderFavorites({ storage, dataApi, api, personal, onData, isCurrent = () => true, state = { type: "all" }, ...options }) {
  const server = await api.get("favorites"); if (!isCurrent()) return ""; const favorites = server?.items || [];
  const local = {}; for (const item of favorites) local[`${item.date}:${item.item_id}`] = 1; storage.set(STORAGE_KEYS.favorites, local);
  if (!favorites.length) return '<section><h1>收藏</h1><div class="empty">还没有收藏内容</div></section>';
  const cache = new Map();
  for (const date of new Set(favorites.map((item) => item.date))) { const data = await dataApi.daily(date); if (!isCurrent()) return ""; cache.set(date, data); onData?.(data, date); }
  const resolved = favorites.map((favorite, index) => {
    const data = cache.get(favorite.date); let type = String(favorite.item_id).startsWith("deep-") ? "deep" : String(favorite.item_id).startsWith("paper-") ? "paper" : "news"; let item = null;
    for (const [candidate, rows] of [["news", data?.items], ["deep", data?.deep], ["paper", data?.papers]]) { item = (rows || []).find((row) => row.id === favorite.item_id); if (item) { type = candidate; break; } }
    return { favorite, item, type, index };
  }).sort((a, b) => {
    const explicit = savedAtValue(b.favorite) - savedAtValue(a.favorite); if (explicit) return explicit;
    const date = String(b.favorite.date || "").localeCompare(String(a.favorite.date || "")); return date || a.index - b.index;
  });
  const visible = resolved.filter((row) => state.type === "all" || row.type === state.type);
  const tabs = [["all", "全部"], ["news", "新闻"], ["deep", "深读"], ["paper", "论文"]];
  return `<section><h1>收藏</h1><div class="tabs favorite-filters">${tabs.map(([value, label]) => `<button type="button" class="tab ${state.type === value ? "on" : ""}" data-favorites-action="type" data-value="${value}">${label}</button>`).join("")}</div><div class="favorites-list">${visible.map(({ favorite, item, type }) => item ? collectionCard(item, type, favorite.date, { personal, ...options, favorites: local }) : `<article class="row"><h3><a href="${safeUrl(favorite.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(favorite.title || favorite.item_id)}</a></h3></article>`).join("") || '<div class="empty">该类型还没有收藏内容</div>'}</div></section>`;
}
