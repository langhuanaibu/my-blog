import { CATEGORY_LABELS, dailyCard, escapeHtml } from "./reports.js";

export const createTimelineState = () => ({ days: 5, cat: "all", tag: null, query: "" });

function beijingTime(value) {
  if (!value) return "时间待确认";
  const time = new Date(value);
  if (Number.isNaN(time.getTime())) return "时间待确认";
  return new Intl.DateTimeFormat("zh-CN", { timeZone: "Asia/Shanghai", hour: "2-digit", minute: "2-digit", hour12: false }).format(time);
}

const DATE_PARTS = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit",
});
const WEEKDAY = new Intl.DateTimeFormat("zh-CN", { timeZone: "Asia/Shanghai", weekday: "short" });

function beijingDateKey(value) {
  const parts = Object.fromEntries(DATE_PARTS.formatToParts(new Date(value)).filter((part) => part.type !== "literal").map((part) => [part.type, part.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}

export function formatTimelineDate(date, now = Date.now()) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date || "");
  if (!match) return String(date || "");
  const [, year, month, day] = match;
  const today = beijingDateKey(now);
  const dayNumber = (value) => {
    const [y, m, d] = value.split("-").map(Number);
    return Date.UTC(y, m - 1, d) / 86400000;
  };
  const delta = dayNumber(date) - dayNumber(today);
  const prefix = delta === 0 ? "今天 · " : delta === -1 ? "昨天 · " : "";
  const weekday = WEEKDAY.format(new Date(`${year}-${month}-${day}T12:00:00+08:00`));
  return `${prefix}${Number(month)}月${Number(day)}日 ${weekday}`;
}

export async function renderTimeline({ dates, dataApi, hidden, personal, state, onData, timelineApi, now = Date.now(), ...options }) {
  if (!dates.length) return '<div class="empty" role="status">还没有任何日报数据。</div>';
  let selectedDates = dates.slice(0, state.days);
  if (state.query) {
    const query = state.query.toLowerCase(); const rows = await dataApi.index();
    selectedDates = [...new Set(rows.filter((row) => row[2] === "pick" && `${row[4] || ""} ${row[5] || ""}`.toLowerCase().includes(query)).map((row) => row[0]))].slice(0, 30);
  }
  const days = await Promise.all(selectedDates.map(async (date) => { const data = await dataApi.daily(date); onData?.(data, date); return [date, data]; }));
  const raw = days.flatMap(([date, data]) => (data?.items || []).filter((item) => item.tier === "pick" && !hidden[`${date}:${item.id}`]).map((item) => ({ reportDate: date, item: { ...item, _reportDate: date } })));
  const timeline = timelineApi?.timelineRows ? timelineApi.timelineRows(raw) : raw.map((row) => ({ ...row, publishedDate: row.reportDate }));
  const categoryRows = timeline.filter((row) => state.cat === "all" || row.item.category === state.cat);
  const tagCounts = {}; for (const row of categoryRows) for (const tag of row.item.tags || []) tagCounts[tag] = (tagCounts[tag] || 0) + 1;
  const filtered = categoryRows.filter((row) => !state.tag || (row.item.tags || []).includes(state.tag)).filter((row) => !state.query || `${row.item.title} ${(row.item.tags || []).join(" ")}`.toLowerCase().includes(state.query.toLowerCase()));
  const byDate = {}; for (const row of filtered) (byDate[row.publishedDate || row.reportDate] ||= []).push(row);
  for (const rows of Object.values(byDate)) rows.sort((a, b) => new Date(b.item.time || 0) - new Date(a.item.time || 0));
  const displayDates = Object.keys(byDate).sort().reverse();
  const recentRaw = raw.filter((row) => dates.indexOf(row.reportDate) < 3);
  const hot = (timelineApi?.groupHotEvents ? timelineApi.groupHotEvents(recentRaw) : recentRaw.map((row) => ({ latest: row, sourceCount: new Set((row.item.sources || []).map((source) => { try { return new URL(source.url).hostname; } catch { return source.name; } })).size }))).filter((group) => group.latest.reportDate === dates[0]).map((group) => {
    const item = group.latest.item; const age = Math.max(0, (now - new Date(item.time || 0).getTime()) / 36e5); return { ...group, rank: (item.score || 0) * .55 + Math.min(group.sourceCount, 3) * 12 + Math.max(0, 36 - age) * .5 };
  }).filter((group) => group.sourceCount >= 2 || (group.latest.item.score || 0) >= 78).sort((a, b) => b.rank - a.rank).slice(0, 3);
  const cats = ["all", ...Object.keys(CATEGORY_LABELS)];
  return `<section class="timeline-view"><h1>时间线</h1><div class="feed-bar"><label class="sr-only" for="timelineSearch">检索精选历史</label><input id="timelineSearch" type="search" value="${escapeHtml(state.query)}" placeholder="检索精选历史（标题/标签）" data-timeline-action="search"></div><div class="tabs">${cats.map((cat) => `<button type="button" class="tab ${state.cat === cat ? "on" : ""}" data-timeline-action="set-cat" data-value="${cat}">${cat === "all" ? "全部" : CATEGORY_LABELS[cat]}</button>`).join("")}</div>${Object.keys(tagCounts).length ? `<div class="tabs sub">${Object.entries(tagCounts).sort((a, b) => b[1] - a[1]).map(([tag, count]) => `<button type="button" class="tab sub ${state.tag === tag ? "on" : ""}" data-timeline-action="set-tag" data-value="${escapeHtml(tag)}">${escapeHtml(tag)} ${count}</button>`).join("")}</div>` : ""}${!state.query && hot.length ? `<aside class="timeline-mainline"><h2>今日主线</h2>${hot.map((group) => { const row = group.latest; return `<a href="?date=${row.reportDate}&amp;type=news&amp;item=${row.item.id}" data-route><span>${escapeHtml(row.item.title)}</span><small>${group.sourceCount} 个独立信源</small></a>`; }).join("")}</aside>` : ""}<div class="timeline-stream">${displayDates.map((date) => `<section class="timeline-day"><h2 class="feed-day"><time datetime="${escapeHtml(date)}">${escapeHtml(formatTimelineDate(date, now))}</time> <span class="n">${byDate[date].length} 条精选</span></h2><div class="timeline-list">${byDate[date].map((row) => dailyCard(row.item, row.reportDate, { personal, ...options, timeline: { time: beijingTime(row.item.time), continuation: Boolean(row.isContinuation) } })).join("")}</div></section>`).join("")}</div>${!state.query && state.days < dates.length ? '<button type="button" class="toggle-more" data-timeline-action="more">加载更早 5 天 ▼</button>' : ""}</section>`;
}
