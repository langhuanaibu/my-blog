import { escapeHtml } from "./reports.js";
import { STORAGE_KEYS } from "./storage.js";

const NI_REASONS = ["不关心这个领域", "这个事看腻了", "太水没实质", "只是今天不想看"];

export function installPersonalActions(root, context) {
  const { storage, api, resolveItem, rerender, trackPromise, toast = () => {} } = context;
  const base = (item, date) => ({ date, item_id: item.id, title: item.title_zh || item.title || "", category: item.category || "" });
  const run = (promise) => trackPromise(Promise.resolve(promise).catch((error) => toast(`同步失败：${error.message}`, true)));

  root.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-action]"); if (!button) return;
    const action = button.dataset.action; const date = button.dataset.date; const item = resolveItem(date, button.dataset.ref) || {};
    const key = storage.itemKey(date, item.id || button.dataset.ref);
    const overflow = button.closest("details.action-overflow"); if (overflow) overflow.open = false;

    if (action === "restore-hidden") { const hidden = storage.get(STORAGE_KEYS.hidden); for (const ref of Object.keys(hidden)) if (ref.startsWith(`${date}:`)) delete hidden[ref]; storage.set(STORAGE_KEYS.hidden, hidden); rerender(); return; }
    if (action === "retry-misses") { rerender(); return; }

    if (action === "submit-miss") {
      const tool = button.closest(".misses-tool");
      const title = tool?.querySelector('[data-miss-field="title"]')?.value.trim() || "";
      const url = tool?.querySelector('[data-miss-field="url"]')?.value.trim() || "";
      const reason = tool?.querySelector('[data-miss-field="reason"]')?.value || "";
      if (!title && !url) { toast("标题或链接至少填写一项", true); return; }
      if (url && !/^https?:\/\//i.test(url)) { toast("链接必须以 http:// 或 https:// 开头", true); return; }
      run(api.postMiss({ date, ...(title ? { title } : {}), ...(url ? { url } : {}), reason }).then(() => rerender()));
      return;
    }
    if (action === "remove-miss") {
      run(api.postMiss({ op: "remove", id: button.dataset.id }).then(() => rerender()));
      return;
    }

    if (action === "not-interested") {
      const panel = button.closest("article")?.querySelector(".fb-panel");
      if (panel) panel.innerHTML = `<p class="fb-tip">为什么不感兴趣？</p><div class="chips">${NI_REASONS.map((reason) => `<button type="button" class="chip" data-action="toggle-reason">${reason}</button>`).join("")}</div><label class="sr-only" for="ni-note-${escapeHtml(item.id)}">补充原因</label><textarea id="ni-note-${escapeHtml(item.id)}" class="fb-note" placeholder="补充原因（可选）"></textarea><div class="fb-btns"><button type="button" class="fb-go" data-action="submit-not-interested" data-ref="${escapeHtml(item.id)}" data-date="${date}">隐藏并提交</button><button type="button" class="fb-cancel" data-action="cancel-panel">取消</button></div>`;
      return;
    }
    if (action === "toggle-reason") { button.classList.toggle("on"); return; }
    if (action === "cancel-panel") { button.closest(".fb-panel").innerHTML = ""; return; }
    if (action === "submit-not-interested") {
      const panel = button.closest(".fb-panel"); const reasons = [...panel.querySelectorAll(".chip.on")].map((node) => node.textContent); const note = panel.querySelector("textarea")?.value || "";
      const hidden = storage.get(STORAGE_KEYS.hidden); hidden[key] = true; storage.set(STORAGE_KEYS.hidden, hidden);
      run(api.postFeedback({ ...base(item, date), action: "not_interested", reasons, note })); rerender(); return;
    }
    if (action === "source") {
      const panel = button.closest("article")?.querySelector(".fb-panel");
      if (panel) panel.innerHTML = `<p class="fb-tip">减少哪个来源？</p><div class="chips">${(item.sources || []).map((source, index) => `<button type="button" class="chip" data-action="down-source" data-index="${index}" data-ref="${escapeHtml(item.id)}" data-date="${date}">${escapeHtml(source.name)}</button>`).join("") || "暂无来源"}</div>`;
      return;
    }
    if (action === "down-source") { const source = (item.sources || [])[Number(button.dataset.index)]; if (source) run(api.postFeedback({ ...base(item, date), action: "low_quality_source", source: source.name })); button.classList.add("on"); return; }
    if (action === "like") { const next = storage.toggle(STORAGE_KEYS.liked, key); run(api.postFeedback({ ...base(item, date), action: "more_like_this", ...(next ? {} : { op: "remove" }) })); button.classList.toggle("done", next); return; }
    if (action === "track" || action === "untrack") { const eventId = button.dataset.event || item.event_id; const next = action === "track" ? storage.toggle(STORAGE_KEYS.tracked, eventId) : false; if (!next) storage.toggle(STORAGE_KEYS.tracked, eventId, false); run(api.postFeedback({ ...base(item, date), item_id: item.id || eventId, action: next ? "track" : "untrack", event_id: eventId })); rerender(); return; }
    if (action === "read-later") {
      const map = storage.get(STORAGE_KEYS.readLater); const exists = Boolean(map[key]); const url = item.url || item.sources?.[0]?.url || "";
      if (exists) delete map[key]; else map[key] = 1; storage.set(STORAGE_KEYS.readLater, map);
      run(api.postReadLater(exists ? { date, item_id: item.id, op: "remove" } : { ...base(item, date), category: item.category || button.dataset.type || "deep", url })); button.classList.toggle("done", !exists); return;
    }
    if (action === "favorite") {
      const map = storage.get(STORAGE_KEYS.favorites); const exists = Boolean(map[key]); const url = item.url || item.sources?.[0]?.url || "";
      if (exists) delete map[key]; else map[key] = 1; storage.set(STORAGE_KEYS.favorites, map);
      run(api.postFavorite(exists ? { date, item_id: item.id, op: "remove" } : { ...base(item, date), category: item.category || button.dataset.type || "deep", url }).then(() => context.onFavoriteChange?.({ removed: exists, button, key }))); button.classList.toggle("done", !exists);
    }
  });
}
