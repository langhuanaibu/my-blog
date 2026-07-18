import assert from "node:assert/strict";
import test from "node:test";
import { JSDOM } from "jsdom";
import { readFile, readdir, stat } from "node:fs/promises";

import { parseRoute, routeUrl } from "../../source/news/js/router.js";
import { daily as loadDaily, weekly as loadWeekly } from "../../source/news/js/data-loader.js";
import { dailyCard, renderDailyReport, renderDetail, renderWeeklyReport } from "../../source/news/js/reports.js";
import * as TimelineView from "../../source/news/js/timeline-view.js";
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
  const desktopBlogHome = sidebar.querySelector(".desktop-blog-home");
  assert.equal(desktopBlogHome?.getAttribute("href"), "/");
  assert.equal(desktopBlogHome?.hasAttribute("data-route"), false);
  assert.ok(doc.querySelector(".mobile-primary"));
  const mobileBlogHome = doc.querySelector(".mobile-blog-home");
  assert.equal(mobileBlogHome?.getAttribute("href"), "/");
  assert.equal(mobileBlogHome?.getAttribute("aria-label"), "返回博客");
  assert.equal(mobileBlogHome?.getAttribute("title"), "返回博客");
  assert.equal(mobileBlogHome?.hasAttribute("data-route"), false);
  assert.equal(mobileBlogHome?.getAttribute("target"), null);
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
  assert.match(css, /@media\(max-width:899\.98px\)[\s\S]*\.shell-read-later\{/);
  assert.match(css, /\.desktop-blog-home\{[^}]*margin-top:auto/);
  assert.match(css, /@media\(max-width:899\.98px\)[\s\S]*\.mobile-blog-home\{[^}]*display:inline-flex/);
  assert.match(css, /@media\(max-width:899\.98px\)[\s\S]*\.mobile-report-controls\{[^}]*scrollbar-width:none/);
  assert.match(css, /\.mobile-report-controls::-webkit-scrollbar\{display:none\}/);
  assert.match(css, /@media\(min-width:900px\)[\s\S]*\.reports-view \.report-controls\{[^}]*position:fixed;[^}]*left:240px;/);
  assert.match(css, /@media\(min-width:900px\)[\s\S]*\.reports-view \.site-header\{[^}]*position:static;[^}]*backdrop-filter:none;[^}]*-webkit-backdrop-filter:none;/);
  assert.match(css, /@media\(min-width:900px\)[\s\S]*\.reports-view \.content-column\{[^}]*margin-left:460px/);
  assert.match(css, /@media\(max-width:899\.98px\)[\s\S]*\.reports-view \.content-column\{[^}]*margin-left:0/);
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

test("日报卡片只显示有限数字分数", () => {
  const scored = new JSDOM(`<main>${dailyCard({ ...daily.items[0], score: 88 }, daily.date)}</main>`);
  assert.equal(scored.window.document.querySelector(".card-top .score-num")?.textContent, "88");
  const unscored = new JSDOM(`<main>${dailyCard({ ...daily.items[0], score: "88" }, daily.date)}</main>`);
  assert.equal(unscored.window.document.querySelector(".score-num"), null);
});

test("日报刊头使用稳定年度期号和单一主标题语义", () => {
  const dom = new JSDOM(`<main>${renderDailyReport(daily)}</main>`);
  const masthead = dom.window.document.querySelector(".masthead");
  assert.ok(masthead);
  assert.equal(dom.window.document.querySelectorAll("main h1").length, 1);
  assert.equal(dom.window.document.querySelector("main h1")?.textContent, daily.lead);
  assert.equal(masthead.querySelector("time")?.getAttribute("datetime"), daily.date);
  assert.equal(masthead.querySelector(".date-seal")?.getAttribute("aria-hidden"), "true");
  assert.match(masthead.querySelector(".mast-issue")?.textContent || "", /2026\s*·\s*第196期/);
});

test("日报 supplementary 暴露稳定的版式种类", () => {
  const html = renderDailyReport({
    ...daily,
    tracking: [{ title: "追踪", event_id: "event-1", history: [] }],
    deep: [{ id: "deep-1", title_zh: "深读" }],
    papers: [{ id: "paper-1", title_zh: "论文" }],
    opinion: [{ id: "opinion-1", title: "舆论" }],
    items: [...daily.items, { id: "more-1", tier: "more", category: "ai", title: "更多" }],
  });
  const dom = new JSDOM(`<main>${html}</main>`);
  assert.deepEqual(
    [...dom.window.document.querySelectorAll(".supplemental")].map((node) => node.dataset.kind),
    ["tracking", "deep", "papers", "opinion", "more"],
  );
});

test("时间线卡片保留事实状态徽标", () => {
  for (const status of ["已确认", "发展中", "有争议", "仅传言"]) {
    const dom = new JSDOM(`<main>${dailyCard({ ...daily.items[0], status }, daily.date, { timeline: { time: "09:00" } })}</main>`);
    const tag = [...dom.window.document.querySelectorAll(".card-top .tag")].find((node) => node.textContent === status);
    assert.ok(tag?.classList.contains(`st-${status}`), `${status} 应输出语义状态类`);
  }
});

test("时间线日期按北京时间统一格式并标记今天昨天", () => {
  const now = new Date("2026-07-16T16:30:00Z").getTime();
  assert.equal(TimelineView.formatTimelineDate("2026-07-17", now), "今天 · 7月17日 周五");
  assert.equal(TimelineView.formatTimelineDate("2026-07-16", now), "昨天 · 7月16日 周四");
  assert.equal(TimelineView.formatTimelineDate("2026-07-15", now), "7月15日 周三");
  const nextBeijingDay = new Date("2026-07-17T16:30:00Z").getTime();
  assert.equal(TimelineView.formatTimelineDate("2026-07-17", nextBeijingDay), "昨天 · 7月17日 周五");
});

test("重大更新在卡片和详情中明确标注首次收录日期", () => {
  const item = { ...daily.items[0], is_update: true, first_seen: "2026-07-14" };
  assert.match(dailyCard(item, daily.date), /重大更新/);
  const detail = renderDetail(item, "news", daily.date);
  assert.match(detail, /重大更新/);
  assert.match(detail, /首次收录：2026-07-14/);
});

test("详情保留完整扩展字段", () => {
  const html = renderDetail({ ...daily.items[0], why: "单独的判断价值" }, "news", daily.date);
  assert.match(html, /detail-wrap reading-view/);
  assert.match(html, /为什么重要/);
  assert.match(html, /单独的判断价值/);
  for (const text of ["背景机制", "对我的意义", "后续关注", "长叙述", "事实"]) assert.match(html, new RegExp(text));
});

test("新闻详情以可用证据概览区分发布源、独立链、证据基础与降级状态", () => {
  const cases = [
    [{ basis: "fulltext", publisher_count: 1, independent_chain_count: 1, degraded: false }, [{ name: "发布源 A", url: "https://a.example/1", evidence_basis: "fulltext", evidence_chain: "chain-a" }], "单一发布源", "独立证据链 1 条", "全文证据"],
    [{ basis: "mixed", publisher_count: 2, independent_chain_count: 1, degraded: true }, [{ name: "发布源 A", url: "https://a.example/1", evidence_basis: "fulltext", evidence_chain: "chain-a" }, { name: "发布源 B", url: "https://b.example/1", evidence_basis: "snippet" }], "2 个发布源", "独立证据链 1 条", "混合证据", "证据降级"],
    [{ basis: "snippet", publisher_count: 3, independent_chain_count: 2, degraded: true }, [{ name: "发布源 A", url: "https://a.example/1", evidence_basis: "snippet", evidence_chain: "chain-a" }, { name: "发布源 B", url: "https://b.example/1", evidence_basis: "snippet", evidence_chain: "chain-b" }, { name: "发布源 C", url: "https://c.example/1", evidence_basis: "snippet" }], "3 个发布源", "独立证据链 2 条", "摘要证据", "证据降级"],
  ];
  for (const [evidence, sources, ...labels] of cases) {
    const dom = new JSDOM(`<main>${renderDetail({ ...daily.items[0], evidence, sources }, "news", daily.date)}</main>`);
    const overview = dom.window.document.querySelector(".detail-evidence");
    assert.ok(overview);
    for (const label of labels) assert.match(overview.textContent, new RegExp(label));
    if (!evidence.degraded) assert.doesNotMatch(overview.textContent, /证据降级/);
  }
});

test("新闻详情拒绝缺失、畸形或重复且无法推导的来源映射", () => {
  const evidence = { basis: "snippet", publisher_count: 2, independent_chain_count: 1, degraded: true };
  const validSources = [
    { name: "发布源 A", url: "https://a.example/1", evidence_basis: "snippet", evidence_chain: "chain-a" },
    { name: "发布源 B", url: "https://b.example/1", evidence_basis: "snippet" },
  ];
  const malformedSources = [
    undefined,
    [],
    [{ name: "", url: "https://a.example/1", evidence_basis: "snippet", evidence_chain: "chain-a" }, validSources[1]],
    [{ ...validSources[0], evidence_basis: "unknown" }, validSources[1]],
    [{ ...validSources[0], evidence_chain: "" }, validSources[1]],
    [validSources[0], { ...validSources[1], name: "发布源 A" }],
    [validSources[0], { ...validSources[1], url: validSources[0].url }],
  ];
  for (const sources of malformedSources) {
    const dom = new JSDOM(`<main>${renderDetail({ ...daily.items[0], evidence, sources }, "news", daily.date)}</main>`);
    assert.equal(dom.window.document.querySelector(".detail-evidence"), null);
  }

  const mismatched = [
    { ...evidence, publisher_count: 1 },
    { ...evidence, independent_chain_count: 0 },
    { ...evidence, basis: "fulltext" },
  ];
  for (const row of mismatched) {
    const dom = new JSDOM(`<main>${renderDetail({ ...daily.items[0], evidence: row, sources: validSources }, "news", daily.date)}</main>`);
    assert.equal(dom.window.document.querySelector(".detail-evidence"), null);
  }
});

test("新闻详情不为不完整或自相矛盾的证据契约渲染概览", () => {
  const malformed = [
    { basis: "fulltext", publisher_count: 1, independent_chain_count: 1 },
    { basis: "fulltext", publisher_count: 1, independent_chain_count: 1, degraded: "false" },
    { basis: "fulltext", publisher_count: 0, independent_chain_count: 0, degraded: false },
    { basis: "fulltext", publisher_count: 1, independent_chain_count: 2, degraded: false },
    { basis: "unknown", publisher_count: 1, independent_chain_count: 1, degraded: false },
  ];
  for (const evidence of malformed) {
    const dom = new JSDOM(`<main>${renderDetail({ ...daily.items[0], evidence }, "news", daily.date)}</main>`);
    assert.equal(dom.window.document.querySelector(".detail-evidence"), null);
  }
});

test("新闻详情为声明显示种类与安全转义后的来源名", () => {
  const dom = new JSDOM(`<main>${renderDetail({
    ...daily.items[0],
    claims: [
      { text: "可验证声明", kind: "fact", sources: ["官方发布"] },
      { text: "解读声明", kind: "analysis", sources: ["分析机构"] },
      { text: "<script>alert(1)</script>未知声明", kind: "<script>alert(1)</script>", sources: ["<img src=x onerror=alert(1)>", 7, { name: "对象来源" }, ""] },
    ],
  }, "news", daily.date)}</main>`);
  const claims = [...dom.window.document.querySelectorAll(".detail-claim")];
  assert.deepEqual(claims.map((claim) => claim.querySelector(".claim-kind")?.textContent), ["事实", "分析", "待核实"]);
  assert.deepEqual(claims.map((claim) => claim.querySelector(".claim-sources")?.textContent), ["来源：官方发布", "来源：分析机构", "来源：<img src=x onerror=alert(1)>"]);
  assert.match(claims[2].textContent, /<script>alert\(1\)<\/script>未知声明/);
  assert.equal(dom.window.document.querySelector(".detail-claim img"), null);
  assert.equal(dom.window.document.querySelector(".detail-claim script"), null);
});

test("旧日报的缺失证据与旧形状声明保持静默兼容", () => {
  const dom = new JSDOM(`<main>${renderDetail({
    ...daily.items[0],
    claims: [{ text: "旧声明" }],
  }, "news", daily.date)}</main>`);
  assert.equal(dom.window.document.querySelector(".detail-evidence"), null);
  assert.equal(dom.window.document.querySelector(".claim-sources"), null);
  assert.equal(dom.window.document.querySelector(".claim-kind")?.textContent, "待核实");
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

test("日报视觉 token 区分阅读表面、浮层和触屏 hover", async () => {
  const css = await readFile(new URL("../../source/news/news.css", import.meta.url), "utf8");
  assert.match(css, /--reading-col\s*:\s*780px/);
  assert.match(css, /--card-border\s*:/);
  assert.match(css, /\.daily-report\s*,\s*\.weekly-report\s*\{[^}]*max-width\s*:\s*var\(--reading-col\)/s);
  assert.match(css, /#backTop\s*\{[^}]*box-shadow\s*:\s*var\(--shadow2\)/s);
  assert.match(css, /\.toast\s*\{[^}]*box-shadow\s*:\s*var\(--shadow2\)/s);
  assert.match(css, /@media\s*\(hover:hover\)\s*and\s*\(pointer:fine\)\s*\{[^}]*\.card:not\(\.timeline-entry\):hover/s);
  assert.match(css, /@media\s*\(max-width:899\.98px\)[\s\S]*min-height\s*:\s*44px/);
  assert.match(css, /\.vcard\s*\{[^}]*box-shadow\s*:\s*var\(--vocab-shadow\)/s);
  assert.match(css, /\.all-tools input\s*,\s*\.all-tools select\s*\{width\s*:\s*100%;min-height\s*:\s*44px\}/);
  assert.match(css, /\.datenav button\s*,\s*#dayCtrls button\s*\{[^}]*background\s*:\s*var\(--card-h\)[^}]*color\s*:\s*var\(--text\)/s);
  assert.match(css, /\.daily-report\s*\{[^}]*container-type\s*:\s*inline-size/s);
  assert.match(css, /@container\s*\(min-width\s*:\s*740px\)[\s\S]*\.supplemental:is\(\[data-kind="more"\],\[data-kind="papers"\],\[data-kind="tracking"\]\)\s+\.more-list/s);
});

test("日报自托管衬线字体包含样式入口与许可证", async () => {
  const html = await readFile(new URL("../../source/news/index.html", import.meta.url), "utf8");
  assert.match(html, /fonts\/noto-serif-sc-700\/result\.css/);
  const fontCss = await readFile(new URL("../../source/news/fonts/noto-serif-sc-700/result.css", import.meta.url), "utf8");
  const license = await readFile(new URL("../../source/news/fonts/noto-serif-sc-700/OFL.txt", import.meta.url), "utf8");
  assert.match(fontCss, /font-family:\s*["']Noto Serif SC["']/);
  assert.match(fontCss, /font-weight:\s*700/);
  assert.match(fontCss, /font-display:\s*swap/);
  assert.match(license, /SIL OPEN FONT LICENSE Version 1\.1/);
  const fontDir = new URL("../../source/news/fonts/noto-serif-sc-700/", import.meta.url);
  const files = (await readdir(fontDir)).filter((name) => name.endsWith(".woff2"));
  const transferBytes = (await Promise.all(files.map((name) => stat(new URL(name, fontDir))))).reduce((sum, item) => sum + item.size, 0);
  assert.ok(transferBytes <= 500_000, `cold font budget exceeded: ${transferBytes} bytes`);
});

test("报刊改版不保留已确认无引用的旧样式", async () => {
  const css = await readFile(new URL("../../source/news/news.css", import.meta.url), "utf8");
  for (const selector of [
    ".feed-clear", ".hotbox", ".hot-row", ".tl-item", ".tl-time", ".tl-badge",
    ".topic-group", ".grid", ".tag.topic", ".tag.day", ".ev-history", ".toc",
    ".readmore", ".card h3.clk", ".detail-fallback-note", ".detail-list",
    ".detail-link", ".detail-source-toggle", ".detail-actions-card", ".detail-kind",
    ".detail-topbar", ".detail-export", ".tag.mins", ".tag.code",
    ".wk-day", ".wk-date", ".wk-syn", ".wk-sub", ".wk-outlook",
  ]) assert.equal(css.includes(selector), false, `dead selector remains: ${selector}`);
});
