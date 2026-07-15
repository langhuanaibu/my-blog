export const STORAGE_KEYS = {
  hidden: "news_hidden", readLater: "news_rl", liked: "news_like", tracked: "news_tracked",
  favorites: "news_fav", seenDays: "news_seen_days",
};

export function createStorage(localStorage) {
  const get = (key) => { try { return JSON.parse(localStorage.getItem(key) || "{}"); } catch { return {}; } };
  const set = (key, value) => localStorage.setItem(key, JSON.stringify(value));
  const itemKey = (date, id) => /^\d{4}-\d{2}-\d{2}:/.test(id) ? id : `${date}:${id}`;
  const toggle = (key, id, value = undefined) => {
    const state = get(key); const next = value ?? !state[id];
    if (next) state[id] = true; else delete state[id];
    set(key, state); return next;
  };
  const markSeen = (date) => { const seen = get(STORAGE_KEYS.seenDays); seen[date] = 1; set(STORAGE_KEYS.seenDays, seen); };
  return { get, set, toggle, itemKey, markSeen };
}
