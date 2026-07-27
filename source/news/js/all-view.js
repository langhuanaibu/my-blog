import { CATEGORY_LABELS, escapeHtml, safeUrl } from "./reports.js";

export const createAllState = () => ({ days: 7, cat: "all", showAll: false, query: "", source: "all" });

const sourceName = (item) => item.source || item.s || item.sources?.[0]?.name || "未知来源";

// 精选标记是装饰，绝不能挡住整页渲染：全部动态页不依赖日报文件是否可用、是否够快。
// 只标最新一天——补漏网是当天的行为，旧日期的「已进精选」你已记不得读没读过。
export function decoratePickedEntries({ dataApi, root, date, stillCurrent = () => true }) {
  return (async () => {
    const daily = await dataApi.daily(date);
    if (!daily || !stillCurrent()) return;
    const urls = new Set();
    for (const item of daily.items || []) {
      for (const source of item.sources || []) {
        if (source?.url) urls.add(String(source.url));
      }
    }
    if (!urls.size) return;
    const day = root.querySelector(`.all-day[data-date="${CSS.escape(date)}"]`);
    for (const entry of day?.querySelectorAll(".all-entry[data-url]") || []) {
      if (!urls.has(entry.dataset.url)) continue;
      entry.classList.add("picked");
      entry.querySelector(".all-entry-meta")?.insertAdjacentHTML(
        "afterbegin", '<span class="picked-flag">✓ 已进精选</span>');
    }
  })().catch(() => {});
}

export async function renderAllDynamics({ dataApi, state }) {
  const dates = await dataApi.allManifest(); if (!dates.length) return '<div class="empty" role="status">暂无全部动态数据</div>';
  const shown = dates.slice(0, state.days); const days = await Promise.all(shown.map(async (date) => [date, await dataApi.allDay(date)])); const cats = ["all", ...Object.keys(CATEGORY_LABELS)];
  const sources = [...new Set(days.flatMap(([, data]) => (data?.items || []).map(sourceName)))].sort();
  const tools = `<div class="all-tools"><label><span class="sr-only">搜索动态</span><input type="search" data-all-action="search" value="${escapeHtml(state.query)}" placeholder="搜索动态"></label><label><span class="sr-only">筛选来源</span><select data-all-action="source"><option value="all">全部来源</option>${sources.map((source) => `<option value="${escapeHtml(source)}"${state.source === source ? " selected" : ""}>${escapeHtml(source)}</option>`).join("")}</select></label></div>`;
  return `<section><h1>全部动态</h1>${tools}<div class="tabs">${cats.map((cat) => `<button type="button" class="tab ${state.cat === cat ? "on" : ""}" data-all-action="set-cat" data-value="${cat}">${cat === "all" ? "全部" : CATEGORY_LABELS[cat]}</button>`).join("")}<button type="button" class="tab ${state.showAll ? "on" : ""}" data-all-action="show-all">${state.showAll ? "✓ 含低分/未评分" : "显示全部（含低分/未评分）"}</button></div><div class="all-timeline">${days.map(([date, data]) => { const min = Number(data?.min_score ?? 40); const query = state.query.toLowerCase(); const all = (data?.items || []).filter((item) => state.cat === "all" || item.c === state.cat).filter((item) => state.source === "all" || sourceName(item) === state.source).filter((item) => !query || `${item.title || item.t || ""} ${item.summary || item.sn || ""}`.toLowerCase().includes(query)); const rows = all.filter((item) => state.showAll || (Number.isFinite(item.score) && item.score >= min)); const hidden = all.length - rows.length; return `<section class="all-day" data-date="${escapeHtml(date)}"><h2 class="feed-day"><time datetime="${escapeHtml(date)}">${escapeHtml(date)}</time></h2>${hidden ? `<p class="hidden-bar">已隐藏 ${hidden} 条低分/未评分</p>` : ""}<div class="all-list">${rows.map((item) => { const url = item.url || item.u; return `<article class="all-entry"${url ? ` data-url="${escapeHtml(String(url))}"` : ""}><div class="all-entry-meta"><span class="tag">${escapeHtml(CATEGORY_LABELS[item.c] || item.c)}</span><span>${escapeHtml(sourceName(item))}</span>${Number.isFinite(item.score) ? `<span>${item.score} 分</span>` : ""}</div><strong>${escapeHtml(item.title || item.t)}</strong>${item.summary || item.sn ? `<p>${escapeHtml(item.summary || item.sn)}</p>` : ""}${url ? `<a href="${safeUrl(url)}" target="_blank" rel="noopener noreferrer">原文</a>` : ""}</article>`; }).join("") || '<p class="section-empty">暂无动态</p>'}</div></section>`; }).join("")}</div>${state.days < dates.length ? '<button type="button" class="toggle-more" data-all-action="more">加载更早 ▼</button>' : ""}</section>`;
}
