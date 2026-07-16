import assert from "node:assert/strict";
import test from "node:test";
import { JSDOM } from "jsdom";
import { readFile } from "node:fs/promises";

import { parseRoute, routeUrl } from "../../source/news/js/router.js";
import { daily as loadDaily, weekly as loadWeekly } from "../../source/news/js/data-loader.js";
import { dailyCard, renderDailyReport, renderDetail, renderWeeklyReport } from "../../source/news/js/reports.js";
import { updateNavigation } from "../../source/news/js/accessibility.js";

const daily = {
  date: "2026-07-15",
  lead: "今天最重要的一句话。",
  themes: [{ title: "主线一", overview: "主线说明" }],
  items: [
    { id: "pick-ai", tier: "pick", category: "ai", title: "AI 事件", summary: "摘要", why: "为什么重要", context: "背景机制", significance: "对我的意义", watch: "后续关注", detail: "长叙述", claims: [{ text: "事实", kind: "fact" }] },
    { id: "pick-world", tier: "pick", category: "world", title: "国际事件", summary: "国际摘要", why: "国际意义" },
  ],
  deep: [], papers: [], opinion: [], tracking: [],
};

test("新旧路由统一为 canonical reports/timeline routes", () => {
  assert.deepEqual(parseRoute("?view=picks"), { view: "timeline" });
  assert.deepEqual(parseRoute("?view=day&date=2026-07-15"), { view: "reports", period: "day", date: "2026-07-15" });
  assert.deepEqual(parseRoute("?view=week&week=2026-W28"), { view: "reports", period: "week", week: "2026-W28" });
  assert.deepEqual(parseRoute("?date=2026-07-15&type=news&item=pick-ai"), { view: "detail", date: "2026-07-15", type: "news", item: "pick-ai" });
  assert.equal(routeUrl({ view: "reports", period: "week", week: "2026-W28" }), "?view=reports&period=week&week=2026-W28");
});

test("新闻页共享外壳提供桌面侧栏和移动三层导航", async () => {
  const html = await readFile(new URL("../../source/news/index.html", import.meta.url), "utf8");
  const css = await readFile(new URL("../../source/news/news.css", import.meta.url), "utf8");
  const dom = new JSDOM(html);
  const doc = dom.window.document;
  const sidebar = doc.querySelector(".desktop-sidebar");
  assert.ok(sidebar?.querySelector(".logo"));
  assert.deepEqual([...sidebar.querySelectorAll("[data-view]")].map((node) => node.dataset.view), ["timeline", "all", "reports", "topics", "favs"]);
  assert.ok(doc.querySelector(".mobile-primary"));
  assert.ok(doc.querySelector(".mobile-nav"));
  assert.ok(doc.querySelector(".mobile-report-controls#reportControls"));
  assert.equal(doc.querySelector("#mobileSearchToggle").getAttribute("aria-controls"), "mobileSearchPanel");
  assert.equal(doc.querySelector("#mobileSearchPanel").getAttribute("role"), null);
  assert.equal(doc.querySelector("#mobileSearchPanel").getAttribute("aria-modal"), null);
  assert.ok(doc.querySelector("#mobileSearchPanel").getAttribute("aria-label"));
  assert.ok(doc.querySelector(".content-search #searchInput"));
  const readLater = doc.querySelector("#readLaterBtn");
  assert.ok(doc.querySelector(".content-toolbar")?.contains(readLater));
  assert.equal(doc.querySelector("#mobileSearchPanel").contains(readLater), false);
  assert.match(readLater.className, /shell-read-later/);
  assert.match(css, /@media\(max-width:899px\)[\s\S]*\.shell-read-later\{/);
  assert.match(css, /@media\(min-width:900px\)[\s\S]*\.reports-view \.report-controls\{[^}]*position:fixed;[^}]*left:240px;/);
  assert.match(css, /@media\(min-width:900px\)[\s\S]*\.reports-view \.site-header\{[^}]*position:static;[^}]*backdrop-filter:none;[^}]*-webkit-backdrop-filter:none;/);
  assert.match(css, /@media\(min-width:900px\)[\s\S]*\.reports-view \.content-column\{[^}]*margin-left:460px/);
  assert.match(css, /@media\(max-width:899px\)[\s\S]*\.reports-view \.content-column\{[^}]*margin-left:0/);
});

test("数据加载器拒绝把 URL 标识解释为任意脚本路径", async () => {
  await assert.rejects(() => loadDaily("../../js/app#"), /无效日报日期/);
  await assert.rejects(() => loadWeekly("..%2Fmanifest"), /无效周报编号/);
});

test("日报固定五类全部展开，精选卡只直出摘要和为什么重要", () => {
  const dom = new JSDOM(`<main id="app"></main>`);
  dom.window.document.querySelector("#app").innerHTML = renderDailyReport(daily);
  const sections = [...dom.window.document.querySelectorAll("[data-category]")];
  assert.deepEqual(sections.map((node) => node.dataset.category), ["ai", "tech", "finance", "society", "world"]);
  assert.ok(sections.every((node) => !node.hasAttribute("hidden")));
  assert.ok(sections.every((node) => node.querySelector(".report-list")));
  assert.equal(dom.window.document.querySelector(".report-section .grid"), null);
  const card = dom.window.document.querySelector('[data-item-id="pick-ai"]');
  assert.match(card.textContent, /摘要/);
  assert.match(card.textContent, /为什么重要/);
  assert.doesNotMatch(card.textContent, /背景机制|对我的意义|后续关注|长叙述|事实/);
});

test("时间线卡片保留事实状态徽标", () => {
  const html = dailyCard({ ...daily.items[0], status: "有争议" }, daily.date, { timeline: { time: "09:00" } });
  assert.match(html, /有争议/);
});

test("详情保留完整扩展字段", () => {
  const html = renderDetail({ ...daily.items[0], why: "单独的判断价值" }, "news", daily.date);
  assert.match(html, /detail-wrap reading-view/);
  assert.match(html, /为什么重要/);
  assert.match(html, /单独的判断价值/);
  for (const text of ["背景机制", "对我的意义", "后续关注", "长叙述", "事实"]) assert.match(html, new RegExp(text));
});

test("周报 v2 显示覆盖、缺失日期、代表报道回链和本周值得读", () => {
  const html = renderWeeklyReport({
    week: "2026-W28",
    coverage: { daily_count: 6, expected_days: 7, missing_dates: ["2026-07-09"] },
    lead: { title: "本周主线", summary: "总述" },
    stats: { pick_count: 30, unique_event_count: 22, source_count: 15, read_minutes: 12 },
    threads: [{ title: "动态主题", direction: "推进", summary: "进展", representative_refs: ["2026-07-10:pick-1"] }],
    reading: [{ ref: "2026-07-11:deep-1", title: "值得读" }],
  });
  const dom = new JSDOM(`<main>${html}</main>`);
  assert.ok(dom.window.document.querySelector(".weekly-report.weekly-reading"));
  assert.ok(dom.window.document.querySelector(".weekly-section.weekly-threads"));
  assert.match(dom.window.document.body.textContent, /6\/7|6 期/);
  assert.match(dom.window.document.body.textContent, /2026-07-09/);
  assert.equal(dom.window.document.querySelector('[data-ref="2026-07-10:pick-1"]').getAttribute("href"), "?date=2026-07-10&type=news&item=pick-1");
  assert.match(dom.window.document.body.textContent, /本周值得读/);
  assert.match(dom.window.document.body.textContent, /推进/);
  assert.match(renderWeeklyReport({ stats: { event_count: 9 }, threads: [] }), /9/);
});

test("深读与论文使用真实 brief/why 合同", () => {
  const deep = renderDetail({ id: "deep-1", title_zh: "深读", brief: "深读摘要", why: "推荐理由", key_points: ["关键点"], takeaway: "结论", audience: "产品经理" }, "deep", "2026-07-15");
  const paper = renderDetail({ id: "paper-1", title_zh: "论文", brief: "论文摘要", why: "论文理由" }, "paper", "2026-07-15");
  assert.match(deep, /深读摘要|推荐理由|关键点|结论|产品经理/);
  assert.match(paper, /论文摘要|论文理由/);
});

test("旧周报和空数据静默降级", () => {
  assert.doesNotThrow(() => renderWeeklyReport({ week: "2026-W27", threads: [], watch_recap: [], outlook: [] }));
  assert.match(renderDailyReport(null), /暂无日报数据/);
});

test("导航 aria-current 与原生键盘控件", () => {
  const dom = new JSDOM(`<nav><a href="?view=timeline" data-view="timeline"></a><a href="?view=reports" data-view="reports"></a></nav><button type="button">展开</button>`, { pretendToBeVisual: true });
  updateNavigation(dom.window.document, "reports");
  assert.equal(dom.window.document.querySelector('[data-view="reports"]').getAttribute("aria-current"), "page");
  assert.equal(dom.window.document.querySelector("button").tagName, "BUTTON");
  assert.equal(dom.window.document.querySelector('[role="button"]'), null);
});

test("生产 HTML 是语义骨架并通过 ES module 入口加载", async () => {
  const source = await readFile(new URL("../../source/news/index.html", import.meta.url), "utf8");
  const dom = new JSDOM(source);
  assert.ok(dom.window.document.querySelector("main#app"));
  assert.ok(dom.window.document.querySelector('a[href="#app"]'));
  assert.ok(dom.window.document.querySelector('script[type="module"][src="js/app.js"]'));
  assert.ok(dom.window.document.querySelector('link[rel="stylesheet"][href="news.css"]'));
  assert.equal(dom.window.document.querySelectorAll("[onclick]").length, 0);
  assert.equal(dom.window.document.querySelectorAll("style").length, 0);
  assert.equal(dom.window.document.querySelector('script[src*="legacy-app"]'), null);
  assert.equal(dom.window.document.querySelector('[data-view="reports"]').textContent.trim(), "报告");
});

test("hidden attribute wins over component display styles", async () => {
  const css = await readFile(new URL("../../source/news/news.css", import.meta.url), "utf8");
  assert.match(css, /(?:^|\})\s*\[hidden\]\s*\{\s*display\s*:\s*none\s*!important\s*\}/);
  const dom = new JSDOM(`<style>${css}</style><div class="archive-controls" hidden>周报归档</div>`, { pretendToBeVisual: true });
  assert.equal(dom.window.getComputedStyle(dom.window.document.querySelector(".archive-controls")).display, "none");
});
