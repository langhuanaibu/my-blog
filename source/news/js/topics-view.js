import { escapeHtml } from "./reports.js";

const hasOverride = (tracked, id) => Object.prototype.hasOwnProperty.call(tracked, id);
const isPinned = (event, tracked) => hasOverride(tracked, event.event_id) ? tracked[event.event_id] === true : Boolean(event.pinned);
const dayCount = (event) => new Set((event.history || []).map((row) => row.date)).size;
const validDate = (value) => /^\d{4}-\d{2}-\d{2}$/.test(String(value || ""));
const eventDates = (event) => [event.first_seen, event.last_seen, ...(event.history || []).map((row) => row.date)]
  .filter(validDate)
  .sort();
const latestDate = (event) => eventDates(event).at(-1) || "";
const earliestDate = (event) => eventDates(event).at(0) || "";
const shortDate = (value) => validDate(value) ? value.slice(5) : "";
const latestProgress = (event) => (event.history || [])
  .filter((row) => validDate(row.date))
  .sort((left, right) => left.date.localeCompare(right.date))
  .at(-1) || null;

function spanLabel(event) {
  const from = earliestDate(event);
  const to = latestDate(event);
  if (!from || !to) return "";
  const days = dayCount(event);
  const range = from === to ? shortDate(from) : `${shortDate(from)} → ${shortDate(to)}`;
  return `${range} · 跨 ${days} 天`;
}

function eventCard(event, tracked, index, personal) {
  const pinned = isPinned(event, tracked);
  const progress = latestProgress(event);
  const archived = event.status === "archived";
  return `<article class="trk"><div class="trk-top"><h3>${escapeHtml(event.title)}</h3>${archived ? '<span class="trk-flag">已归档</span>' : ""}<span class="trk-span">${escapeHtml(spanLabel(event))}</span></div>${progress ? `<p class="trk-latest"><a href="?view=reports&amp;period=day&amp;date=${escapeHtml(progress.date)}" data-route>${escapeHtml(progress.date)}</a> ${escapeHtml(progress.summary || progress.title || "")}</p>` : ""}<div class="trk-acts"><button type="button" class="act" data-action="toggle-topic" aria-expanded="false" aria-controls="topic-${index}">展开进展</button>${personal ? `<button type="button" class="act ${pinned ? "done" : ""}" data-action="track-topic" data-event="${escapeHtml(event.event_id)}" data-date="${escapeHtml(latestDate(event))}" data-next="${!pinned}">${pinned ? "取消追踪" : "📌 追踪"}</button>` : ""}</div><div id="topic-${index}" class="trk-hist" hidden>${(event.history || []).slice().reverse().map((row) => `<p><a href="?view=reports&amp;period=day&amp;date=${escapeHtml(row.date)}" data-route>${escapeHtml(row.date)}</a> ${escapeHtml(row.summary)}</p>`).join("") || "暂无进展"}</div></article>`;
}

export async function renderTopics({ dataApi, personal, tracked = {} }) {
  const [registry, index] = await Promise.all([dataApi.events(), dataApi.index()]);
  const events = registry?.events || [];
  if (!events.length) return '<div class="empty" role="status">暂无档案数据</div>';

  // 题材地图：总量排序保持位置稳定（检索靠肌肉记忆），时间感由卡上的最新日期给。
  const counts = {};
  const freshest = {};
  for (const row of index) {
    if (row[2] !== "pick") continue;
    const date = validDate(row[0]) ? row[0] : "";
    const tags = Array.isArray(row[5]) ? row[5] : String(row[5] || "").split(/[|,，]/);
    for (const tag of tags.map((value) => value.trim()).filter(Boolean)) {
      counts[tag] = (counts[tag] || 0) + 1;
      if (date && date > (freshest[tag] || "")) freshest[tag] = date;
    }
  }
  const topicCards = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([tag, count]) => `<a class="topic-card" href="?view=timeline&amp;tag=${encodeURIComponent(tag)}" data-route><b>${escapeHtml(tag)}</b><span>${count} 条精选</span>${freshest[tag] ? `<span class="tc-fresh">最新 ${escapeHtml(shortDate(freshest[tag]))}</span>` : ""}</a>`)
    .join("");

  // 事件线：追踪中置顶，其余按最新日期倒序排一列，状态只作卡上标记。
  const lines = events.filter((event) => dayCount(event) >= 2);
  const pinned = lines.filter((event) => isPinned(event, tracked));
  const rest = lines
    .filter((event) => !isPinned(event, tracked))
    .sort((left, right) => latestDate(right).localeCompare(latestDate(left)));
  let sequence = 0;
  const group = (title, rows) => rows.length
    ? `<section class="topic-event-group"><h2 class="sec-title">${title} (${rows.length})</h2>${rows.map((event) => eventCard(event, tracked, sequence++, personal)).join("")}</section>`
    : "";

  return `<section><h1>档案</h1><section><h2 class="sec-title">题材地图</h2><div class="topic-grid">${topicCards || '<p class="section-empty">暂无标签</p>'}</div></section>${group("📌 追踪中", pinned)}${group("事件线", rest)}</section>`;
}

export function installTopicInteractions(root, { onTrack }) {
  root.addEventListener("click", (event) => { const button = event.target.closest("button[data-action]"); if (!button) return; if (button.dataset.action === "toggle-topic") { const panel = root.ownerDocument.getElementById(button.getAttribute("aria-controls")); const open = button.getAttribute("aria-expanded") === "true"; button.setAttribute("aria-expanded", String(!open)); button.textContent = open ? "展开进展" : "收起进展"; panel.hidden = open; } if (button.dataset.action === "track-topic") onTrack(button.dataset.event, button.dataset.next === "true", button.dataset.date); });
}
