import { escapeHtml, safeUrl } from "./reports.js";
import { STORAGE_KEYS } from "./storage.js";

export function installReadLater({ button, drawer, api, storage, trackPromise }) {
  if (!button || !drawer) return;
  const close = (restoreFocus = true) => { drawer.classList.remove("open"); drawer.hidden = true; drawer.inert = true; button.setAttribute("aria-expanded", "false"); if (restoreFocus) button.focus(); };
  const load = () => trackPromise(api.get("read_later").then((data) => {
    const items = (data?.items || []).slice().reverse(); const todo = items.filter((item) => !item.done); const done = items.filter((item) => item.done).slice(0, 20);
    const row = (item) => `<article class="rl-item ${item.done ? "done" : ""}"><a href="${safeUrl(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title || item.item_id)}</a><div class="rl-meta">${escapeHtml(item.date)}</div><div class="rl-ops">${item.done ? "" : `<button type="button" data-read-later-op="done" data-date="${escapeHtml(item.date)}" data-item="${escapeHtml(item.item_id)}">✓ 读完了</button>`}<button type="button" data-read-later-op="remove" data-date="${escapeHtml(item.date)}" data-item="${escapeHtml(item.item_id)}">✕ 移除</button></div></article>`;
    drawer.innerHTML = `<div class="rl-head"><h2>📥 稍后读</h2><button type="button" data-close-drawer aria-label="关闭稍后读">✕</button></div>${todo.map(row).join("") || '<p class="empty">队列是空的</p>'}${done.length ? `<h3>最近读完</h3>${done.map(row).join("")}` : ""}`;
    drawer.querySelector("[data-close-drawer]")?.focus();
  }).catch((error) => { drawer.innerHTML = `<p role="alert">加载失败：${escapeHtml(error.message)}</p>`; }));
  button.addEventListener("click", () => { if (!drawer.hidden) { close(); return; } drawer.hidden = false; drawer.inert = false; drawer.classList.add("open"); button.setAttribute("aria-expanded", "true"); load(); });
  drawer.addEventListener("click", (event) => {
    if (event.target.closest("[data-close-drawer]")) { close(); return; }
    const op = event.target.closest("button[data-read-later-op]"); if (!op) return;
    trackPromise(api.postReadLater({ date: op.dataset.date, item_id: op.dataset.item, op: op.dataset.readLaterOp }).then(() => { if (op.dataset.readLaterOp === "remove") { const local = storage.get(STORAGE_KEYS.readLater); delete local[`${op.dataset.date}:${op.dataset.item}`]; storage.set(STORAGE_KEYS.readLater, local); } return load(); }));
  });
  close(false);
}
