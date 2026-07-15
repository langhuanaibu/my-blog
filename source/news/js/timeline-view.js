import { CATEGORY_LABELS, collectionCard, escapeHtml } from "./reports.js";

export const createTimelineState = () => ({ days: 5, cat: "all", tag: null, query: "", open: {} });

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
  const displayDates = Object.keys(byDate).sort().reverse();
  const recentRaw = raw.filter((row) => dates.indexOf(row.reportDate) < 3);
  const hot = (timelineApi?.groupHotEvents ? timelineApi.groupHotEvents(recentRaw) : recentRaw.map((row) => ({ latest: row, sourceCount: new Set((row.item.sources || []).map((source) => { try { return new URL(source.url).hostname; } catch { return source.name; } })).size }))).map((group) => {
    const item = group.latest.item; const age = Math.max(0, (now - new Date(item.time || 0).getTime()) / 36e5); const rank = (item.score || 0) * .55 + Math.min(group.sourceCount, 3) * 12 + Math.max(0, 36 - age) * .5; return { ...group, rank };
  }).filter((group) => group.sourceCount >= 2 || (group.latest.item.score || 0) >= 78).sort((a, b) => b.rank - a.rank).slice(0, 6);
  const cats = ["all", ...Object.keys(CATEGORY_LABELS)];
  return `<section class="timeline-view"><h1>时间线</h1><div class="feed-bar"><label class="sr-only" for="timelineSearch">检索精选历史</label><input id="timelineSearch" type="search" value="${escapeHtml(state.query)}" placeholder="检索精选历史（标题/标签）" data-timeline-action="search"></div><div class="tabs">${cats.map((cat) => `<button type="button" class="tab ${state.cat === cat ? "on" : ""}" data-timeline-action="set-cat" data-value="${cat}">${cat === "all" ? "全部" : CATEGORY_LABELS[cat]}</button>`).join("")}</div>${Object.keys(tagCounts).length ? `<div class="tabs sub">${Object.entries(tagCounts).sort((a, b) => b[1] - a[1]).map(([tag, count]) => `<button type="button" class="tab sub ${state.tag === tag ? "on" : ""}" data-timeline-action="set-tag" data-value="${escapeHtml(tag)}">${escapeHtml(tag)} ${count}</button>`).join("")}</div>` : ""}${!state.query && hot.length ? `<section class="hotbox"><h2 class="hot-h">当前热点</h2>${hot.map((group, index) => { const row = group.latest; return `<a class="hot-row" href="?date=${row.reportDate}&amp;type=news&amp;item=${row.item.id}" data-route><span class="hot-no n${index + 1}">${index + 1}</span><span class="hot-t">${escapeHtml(row.item.title)}</span><span class="hot-m">${group.sourceCount} 个独立信源</span></a>`; }).join("")}</section>` : ""}${displayDates.map((date, index) => { const rows = byDate[date] || []; const open = Boolean(state.query) || (state.open[date] ?? index === 0); return `<section class="timeline-day"><h2 class="feed-day"><button type="button" data-timeline-action="toggle-day" data-value="${date}" aria-expanded="${Boolean(open)}">${open ? "▾" : "▸"} ${escapeHtml(date)}</button> <span class="n">${rows.length} 条精选</span></h2>${open ? `<div class="grid">${rows.map((row) => collectionCard(row.item, "news", row.reportDate, { personal, ...options })).join("") || '<p class="section-empty">暂无精选</p>'}</div>` : ""}</section>`; }).join("")}${!state.query && state.days < dates.length ? '<button type="button" class="toggle-more" data-timeline-action="more">加载更早 5 天 ▼</button>' : ""}</section>`;
}
