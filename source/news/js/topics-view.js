import { escapeHtml } from "./reports.js";

const hasOverride = (tracked, id) => Object.prototype.hasOwnProperty.call(tracked, id);
const isPinned = (event, tracked) => hasOverride(tracked, event.event_id) ? tracked[event.event_id] === true : Boolean(event.pinned);
const dayCount = (event) => new Set((event.history || []).map((row) => row.date)).size;
const validDate = (value) => /^\d{4}-\d{2}-\d{2}$/.test(String(value || ""));
const latestDate = (event) => [event.last_seen, ...(event.history || []).map((row) => row.date)]
  .filter(validDate)
  .sort()
  .at(-1) || "";

function eventCard(event, tracked, index, personal) {
  const pinned = isPinned(event, tracked); return `<article class="trk"><div class="trk-top"><h3>${escapeHtml(event.title)}</h3><button type="button" class="act" data-action="toggle-topic" aria-expanded="false" aria-controls="topic-${index}">展开进展</button>${personal ? `<button type="button" class="act ${pinned ? "done" : ""}" data-action="track-topic" data-event="${escapeHtml(event.event_id)}" data-date="${escapeHtml(latestDate(event))}" data-next="${!pinned}">${pinned ? "取消追踪" : "📌 追踪"}</button>` : ""}</div><div id="topic-${index}" class="trk-hist" hidden>${(event.history || []).slice().reverse().map((row) => `<p><a href="?view=reports&amp;period=day&amp;date=${escapeHtml(row.date)}" data-route>${escapeHtml(row.date)}</a> ${escapeHtml(row.summary)}</p>`).join("") || "暂无进展"}</div></article>`;
}

export async function renderTopics({ dataApi, personal, tracked = {} }) {
  const [registry, index] = await Promise.all([dataApi.events(), dataApi.index()]); const events = registry?.events || [];
  if (!events.length) return '<div class="empty" role="status">暂无主题数据</div>';
  const pinned = events.filter((event) => isPinned(event, tracked)); const running = events.filter((event) => !isPinned(event, tracked) && event.status === "active" && dayCount(event) >= 2); const archived = events.filter((event) => !isPinned(event, tracked) && event.status === "archived" && dayCount(event) >= 2);
  const counts = {}; for (const row of index) { if (row[2] !== "pick") continue; const tags = Array.isArray(row[5]) ? row[5] : String(row[5] || "").split(/[|,，]/); for (const tag of tags.map((value) => value.trim()).filter(Boolean)) counts[tag] = (counts[tag] || 0) + 1; }
  let sequence = 0; const group = (title, rows) => rows.length ? `<section class="topic-event-group"><h2 class="sec-title">${title} (${rows.length})</h2>${rows.map((event) => eventCard(event, tracked, sequence++, personal)).join("")}</section>` : "";
  return `<section><h1>主题</h1>${group("📌 追踪中", pinned)}${group("🔥 进行中", running)}${group("🗄 已归档", archived)}<section><h2 class="sec-title">题材地图</h2><div class="topic-grid">${Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([tag, count]) => `<a class="topic-card" href="?view=timeline&amp;tag=${encodeURIComponent(tag)}" data-route><b>${escapeHtml(tag)}</b><span>${count} 条精选</span></a>`).join("") || '<p class="section-empty">暂无标签</p>'}</div></section></section>`;
}

export function installTopicInteractions(root, { onTrack }) {
  root.addEventListener("click", (event) => { const button = event.target.closest("button[data-action]"); if (!button) return; if (button.dataset.action === "toggle-topic") { const panel = root.ownerDocument.getElementById(button.getAttribute("aria-controls")); const open = button.getAttribute("aria-expanded") === "true"; button.setAttribute("aria-expanded", String(!open)); button.textContent = open ? "展开进展" : "收起进展"; panel.hidden = open; } if (button.dataset.action === "track-topic") onTrack(button.dataset.event, button.dataset.next === "true", button.dataset.date); });
}
