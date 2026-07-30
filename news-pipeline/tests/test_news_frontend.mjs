import assert from "node:assert/strict";
import test from "node:test";
import { JSDOM } from "jsdom";
import { readFile, readdir, stat } from "node:fs/promises";

import { parseRoute, routeUrl } from "../../source/news/js/router.js";
import { daily as loadDaily, weekly as loadWeekly } from "../../source/news/js/data-loader.js";
import { collectionCard, dailyCard, renderDailyReport, renderDetail, renderWeeklyReport } from "../../source/news/js/reports.js";
import * as TimelineView from "../../source/news/js/timeline-view.js";
import { updateNavigation } from "../../source/news/js/accessibility.js";

const daily = {
  date: "2026-07-15",
  lead: "今天最重要的一句话。",
  themes: [{ title: "主线一", overview: "主线说明" }],
  items: [
    { id: "pick-ai", tier: "pick", category: "ai", title: "AI 事件", summary: "摘要", why: "为什么重要", context: "背景机制", significance: "历史对我的意义", watch: "后续关注", watch_detail: "详细走向第一段。\n\n详细走向第二段。", detail: "现状第一段。\n\n现状第二段。", claims: [{ text: "事实", kind: "fact" }] },
    { id: "pick-world", tier: "pick", category: "world", title: "国际事件", summary: "国际摘要", why: "国际意义" },
  ],
  deep: [], papers: [], opinion: [], tracking: [],
};

test("漏读加载失败时明确提示并允许重试", () => {
  const html = renderDailyReport(daily, {
    personal: true,
    misses: [],
    missesError: "network <down>",
  });
  const document = new JSDOM(`<main>${html}</main>`).window.document;
  assert.match(document.querySelector(".misses-error").textContent, /加载失败.*network <down>.*重试/);
  assert.ok(document.querySelector('[data-action="retry-misses"]'));
  assert.doesNotMatch(html, /network <down>/);
});

test("渲染层没有裸插值：日期也走转义", () => {
  // date 目前由管线生成，但「上游可信所以这里可以不转义」是一条只要上游变一次
  // 就会破的规则。这条用例把不变式钉死：进入 HTML 的插值一律过 escapeHtml。
  const hostile = '2026-07-15" onclick="alert(1)';
  const state = { personal: true, favorites: {}, readLater: {}, liked: {}, tracked: {} };

  // 判据是解析后的 DOM，不是原始字符串：转义正确时 onclick= 仍以字面量留在
  // 属性值内部，它是否惰性只有解析器说了算。
  const cardDoc = new JSDOM(
    `<main>${dailyCard({ ...daily.items[0], event_id: "evt-1" }, hostile, state)}</main>`,
  ).window.document;
  const dated = [...cardDoc.querySelectorAll("button[data-date]")];
  assert.ok(dated.length >= 4, "个人操作按钮应当带 data-date");
  for (const node of dated) {
    assert.equal(node.dataset.date, hostile);
    assert.equal(node.getAttribute("onclick"), null);
  }

  const reportDoc = new JSDOM(`<main>${renderDailyReport(
    { ...daily, date: hostile },
    { ...state, hidden: { [`${hostile}:pick-ai`]: true } },
  )}</main>`).window.document;
  const restore = reportDoc.querySelector('[data-action="restore-hidden"]');
  assert.equal(restore.dataset.date, hostile);
  assert.equal(restore.getAttribute("onclick"), null);
});

test("新旧路由统一为 canonical reports/timeline routes", () => {
  assert.deepEqual(parseRoute(""), { view: "reports", period: "day" });
  assert.deepEqual(parseRoute("?view=unknown"), { view: "reports", period: "day" });
  assert.deepEqual(parseRoute("?view=picks"), { view: "timeline" });
  assert.deepEqual(parseRoute("?view=day&date=2026-07-15"), { view: "reports", period: "day", date: "2026-07-15" });
  assert.deepEqual(parseRoute("?view=week&week=2026-W28"), { view: "reports", period: "week", week: "2026-W28" });
  assert.deepEqual(parseRoute("?date=2026-07-15&type=news&item=pick-ai"), { view: "detail", date: "2026-07-15", type: "news", item: "pick-ai" });
  assert.equal(routeUrl({ view: "reports", period: "week", week: "2026-W28" }), "?view=reports&period=week&week=2026-W28");
});

test("个人操作按内容类型分为主操作和原生溢出菜单", () => {
  const state = { personal: true, favorites: {}, readLater: {}, liked: {}, tracked: {} };
  const news = new JSDOM(`<main>${dailyCard({ ...daily.items[0], event_id: "evt-1" }, daily.date, state)}</main>`).window.document;
  assert.deepEqual(
    [...news.querySelectorAll(".acts > button[data-action]")].map((node) => node.dataset.action),
    ["not-interested", "favorite"],
  );
  const newsMenu = news.querySelector(".acts details");
  assert.equal(newsMenu?.querySelector("summary")?.getAttribute("aria-label"), "更多操作");
  assert.deepEqual(
    [...newsMenu.querySelectorAll("button[data-action]")].map((node) => node.dataset.action),
    ["read-later", "like", "track", "source"],
  );

  const noEvent = new JSDOM(`<main>${dailyCard(daily.items[1], daily.date, state)}</main>`).window.document;
  assert.equal(noEvent.querySelector('[data-action="track"]'), null);

  for (const [type, item] of [["deep", { id: "deep-1", title: "深读" }], ["paper", { id: "paper-1", title: "论文" }]]) {
    const doc = new JSDOM(`<main>${collectionCard(item, type, daily.date, state)}</main>`).window.document;
    assert.deepEqual([...doc.querySelectorAll(".acts > button[data-action]")].map((node) => node.dataset.action), ["favorite"]);
    assert.deepEqual([...doc.querySelectorAll(".acts details button[data-action]")].map((node) => node.dataset.action), ["read-later"]);
  }

  const loggedOut = new JSDOM(`<main>${dailyCard(daily.items[0], daily.date)}</main>`).window.document;
  assert.equal(loggedOut.querySelector(".acts"), null);
});

test("个人操作溢出菜单向卡片内侧展开并允许窄屏换行", async () => {
  const css = await readFile(new URL("../../source/news/news.css", import.meta.url), "utf8");
  assert.match(css, /\.action-menu\{[^}]*right:0;[^}]*max-width:calc\(100vw - 28px\);[^}]*flex-wrap:wrap/);
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

test("日报固定五类全部展开，精选卡直出摘要、为什么重要和已有走向", () => {
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
  assert.match(card.textContent, /走向：后续关注/);
  assert.doesNotMatch(card.textContent, /背景机制|对我的意义|长叙述|事实/);
});

test("刊头按实际可见核心日报估时且忽略顶层 read_minutes", () => {
  const report = {
    date: "2026-07-15",
    read_minutes: 99,
    lead: "导".repeat(280),
    themes: [{ title: "主线标题", overview: "主线说明" }],
    items: [
      { id: "pick-ai", tier: "pick", category: "ai", title: "精选标题", summary: "精选摘要", why: "精选意义", watch: "精选走向" },
      { id: "pick-world", tier: "pick", category: "world", title: "藏".repeat(300), summary: "隐藏摘要" },
    ],
    deep: [], papers: [], opinion: [], tracking: [],
  };
  const doc = new JSDOM(`<main>${renderDailyReport(report, { hidden: { "2026-07-15:pick-world": true } })}</main>`).window.document;
  assert.match(doc.querySelector(".mast-meta")?.textContent || "", /核心日报约 2 分钟/);
  assert.doesNotMatch(doc.querySelector(".mast-meta")?.textContent || "", /99 分钟/);
});

test("关闭轨迹时核心估时不计入走向", () => {
  const report = {
    date: "2026-07-15",
    trajectory_enabled: false,
    lead: "导".repeat(290),
    items: [{ id: "pick-ai", tier: "pick", category: "ai", title: "标题", summary: "摘要", why: "意义", watch: "走".repeat(300) }],
    deep: [], papers: [], opinion: [], tracking: [],
  };
  const doc = new JSDOM(`<main>${renderDailyReport(report)}</main>`).window.document;
  assert.match(doc.querySelector(".mast-meta")?.textContent || "", /核心日报约 1 分钟/);
});

test("附栏导读估时覆盖舆论 why_hot 并与深读原文估时分开", () => {
  const report = {
    date: "2026-07-15",
    lead: "导语",
    items: [],
    deep: [{ id: "deep-1", title_zh: "深读", brief: "导读", read_minutes: 20 }],
    papers: [],
    opinion: [{ id: "opinion-1", title: "舆论", why_hot: "热".repeat(301), mechanism: "机制" }],
    tracking: [],
  };
  const doc = new JSDOM(`<main>${renderDailyReport(report)}</main>`).window.document;
  assert.match(doc.querySelector(".supplemental-load")?.textContent || "", /附栏导读约 2 分钟/);
  assert.match(doc.querySelector('[data-kind="deep"] .sec-title')?.textContent || "", /原文约 20 分钟/);
});

test("报告类目跳转只包含有可见精选的分类并指向现有标题", () => {
  const doc = new JSDOM(`<main>${renderDailyReport(daily, { hidden: { [`${daily.date}:pick-world`]: true } })}</main>`).window.document;
  const nav = doc.querySelector(".report-jump");
  assert.equal(nav?.getAttribute("aria-label"), "日报类目跳转");
  assert.deepEqual([...nav.querySelectorAll("a")].map((node) => [node.textContent, node.getAttribute("href")]), [["AI 1", "#cat-ai"]]);
  assert.equal(doc.querySelector("#cat-ai")?.tagName, "H2");
});

test("日报卡片只在 watch 存在时显示走向", () => {
  const withWatch = new JSDOM(`<main>${dailyCard(daily.items[0], daily.date)}</main>`).window.document;
  assert.equal(withWatch.querySelector(".kv.watch")?.textContent, "走向：后续关注");

  const withoutWatch = new JSDOM(`<main>${dailyCard({ ...daily.items[0], watch: "" }, daily.date)}</main>`).window.document;
  assert.equal(withoutWatch.querySelector(".kv.watch"), null);
  assert.doesNotMatch(withoutWatch.querySelector(".report-card").textContent, /走向/);
});

test("轨迹回滚标记关闭走向和可信延续展示", () => {
  const rolledBack = {
    ...daily,
    trajectory_enabled: false,
    items: [{
      ...daily.items[0],
      trusted_continuation: true,
      day_count: 3,
      history: [{ date: "2026-07-14", item_ref: "2026-07-14:pick-7" }],
    }],
  };
  const doc = new JSDOM(`<main>${renderDailyReport(rolledBack)}</main>`).window.document;
  assert.equal(doc.querySelector(".kv.watch"), null);
  assert.equal(doc.querySelector(".continuation-link"), null);
  assert.match(doc.querySelector(".mast-meta").textContent, /延续事件 0/);
});

test("可信延续徽标精确跳转上一条详情并为旧历史降级到日报", () => {
  const exact = new JSDOM(`<main>${dailyCard({
    ...daily.items[0],
    trusted_continuation: true,
    day_count: 3,
    history: [{ date: "2026-07-14", summary: "上一进展", item_ref: "2026-07-14:pick-7" }],
  }, daily.date)}</main>`).window.document;
  const exactLink = exact.querySelector(".continuation-link");
  assert.equal(exactLink?.textContent, "第 3 天·延续");
  assert.equal(exactLink?.getAttribute("href"), "?date=2026-07-14&type=news&item=pick-7");
  assert.equal(exactLink?.hasAttribute("data-route"), true);

  const legacy = new JSDOM(`<main>${dailyCard({
    ...daily.items[0],
    trusted_continuation: true,
    day_count: 2,
    history: [{ date: "2026-07-14", summary: "旧进展" }],
  }, daily.date)}</main>`).window.document;
  assert.equal(
    legacy.querySelector(".continuation-link")?.getAttribute("href"),
    "?view=reports&period=day&date=2026-07-14",
  );
});

test("一次性或验证失败条目不显示延续徽标", () => {
  const oneOff = new JSDOM(`<main>${dailyCard({
    ...daily.items[0],
    day_count: 8,
    history: [{ date: "2026-07-14", summary: "未经验证的旧历史" }],
  }, daily.date)}</main>`).window.document;
  assert.equal(oneOff.querySelector(".continuation-link"), null);

  const report = new JSDOM(`<main>${renderDailyReport({
    ...daily,
    items: [{ ...daily.items[0], day_count: 8, history: [{ date: "2026-07-14" }] }],
  })}</main>`).window.document;
  assert.match(report.querySelector(".mast-meta")?.textContent || "", /今日新事件 1/);
  assert.match(report.querySelector(".mast-meta")?.textContent || "", /延续事件 0/);
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

test("时间线最新一期榜单使用本期优先读名称", async () => {
  const date = "2026-07-15";
  const html = await TimelineView.renderTimeline({
    dates: [date],
    dataApi: { daily: async () => ({ date, items: [{ id: "pick-1", tier: "pick", category: "ai", title: "优先条目", score: 99, time: "2026-07-15T01:00:00Z", sources: [] }] }) },
    hidden: {},
    personal: false,
    state: TimelineView.createTimelineState(),
    now: new Date("2026-07-15T02:00:00Z").getTime(),
  });
  const doc = new JSDOM(`<main>${html}</main>`).window.document;
  assert.equal(doc.querySelector(".timeline-mainline h2")?.textContent, "本期优先读");
  assert.doesNotMatch(doc.querySelector(".timeline-mainline")?.textContent || "", /今日主线/);
});

test("重大更新在卡片和详情中明确标注首次收录日期", () => {
  const item = { ...daily.items[0], is_update: true, first_seen: "2026-07-14" };
  assert.match(dailyCard(item, daily.date), /重大更新/);
  const detail = renderDetail(item, "news", daily.date);
  assert.match(detail, /重大更新/);
  assert.match(detail, /首次收录：2026-07-14/);
});

test("详情保留完整扩展字段", () => {
  const html = renderDetail({ ...daily.items[0], trusted_continuation: true, why: "单独的判断价值" }, "news", daily.date);
  assert.match(html, /detail-wrap reading-view/);
  assert.match(html, /为什么重要/);
  assert.match(html, /单独的判断价值/);
  for (const text of ["背景机制", "详细走向第一段", "现状第一段", "事实"]) assert.match(html, new RegExp(text));
  assert.doesNotMatch(html, /历史对我的意义/);
  assert.doesNotMatch(html, /后续关注/);
});

test("新闻详情事实先行：来龙现状为什么重要和详情走向", () => {
  const doc = new JSDOM(`<main>${renderDetail({ ...daily.items[0], trusted_continuation: true }, "news", daily.date)}</main>`).window.document;
  const sections = [...doc.querySelectorAll(".detail-trajectory > section")];
  assert.deepEqual(sections.map((node) => node.dataset.trajectory), ["context", "body", "why", "watch"]);
  assert.deepEqual(sections.map((node) => node.querySelector("h2")?.textContent), ["来龙", "现状", "为什么重要", "走向"]);
  assert.match(sections[1].textContent, /现状第一段/);
  assert.match(sections[2].textContent, /为什么重要/);
});

test("详情把长字段按空行安全渲染为自然段", () => {
  const item = {
    ...daily.items[0],
    context: "起因一。\r\n\r\n起因二<script>alert(1)</script>。",
    detail: "现状一。\n\n\n现状二。",
    watch_detail: "走向一。\n \n走向二。",
  };
  const doc = new JSDOM(`<main>${renderDetail(item, "news", daily.date)}</main>`).window.document;
  assert.equal(doc.querySelectorAll('[data-trajectory="context"] p').length, 2);
  assert.equal(doc.querySelectorAll('[data-trajectory="body"] p').length, 2);
  assert.equal(doc.querySelectorAll('[data-trajectory="watch"] p').length, 2);
  assert.equal(doc.querySelector("script"), null);
  assert.match(doc.querySelector('[data-trajectory="context"]').textContent, /<script>alert\(1\)<\/script>/);
});

test("空白详情走向回退到短走向", () => {
  const doc = new JSDOM(`<main>${renderDetail({
    ...daily.items[0],
    watch: "短走向仍应显示。",
    watch_detail: " \n ",
  }, "news", daily.date)}</main>`).window.document;

  assert.match(doc.querySelector('[data-trajectory="watch"]')?.textContent || "", /短走向仍应显示/);
});

test("新闻详情把摘要放在标题下的无标题导语里而不是独立区块", () => {
  const doc = new JSDOM(`<main>${renderDetail(daily.items[0], "news", daily.date)}</main>`).window.document;
  const lede = doc.querySelector(".detail-lede");
  assert.match(lede?.textContent || "", new RegExp(daily.items[0].summary));
  // 摘要不再占章节标题，但必须仍然显示——搜索、周报引用和延续链接这三条入口
  // 进详情页时读者没见过卡片，删掉就是纯丢信息。
  assert.equal(doc.querySelector(".detail-trajectory > section")?.dataset.trajectory !== "current", true);
  assert.doesNotMatch(doc.body.textContent, /AI 摘要/);
});

test("只有摘要的次级条目详情页仍有正文可读", () => {
  const item = { id: "more-1", title: "次级条目", summary: "只有摘要的次级条目", sources: daily.items[0].sources };
  const doc = new JSDOM(`<main>${renderDetail(item, "news", daily.date)}</main>`).window.document;
  assert.match(doc.querySelector(".detail-lede")?.textContent || "", /只有摘要的次级条目/);
});

test("详情把末尾格式完整的四种走向回对独立显示", () => {
  for (const status of ["兑现", "部分兑现", "未兑现", "反转"]) {
    const item = {
      ...daily.items[0],
      trusted_continuation: true,
      context: `既有来龙。走向回对（${status}）：此前路标已有结论。`,
    };
    const doc = new JSDOM(`<main>${renderDetail(item, "news", daily.date)}</main>`).window.document;
    const recap = doc.querySelector(`.trajectory-recap.recap-${status}`);
    assert.match(recap?.textContent || "", new RegExp(`${status}.*此前路标已有结论`));
    assert.equal(doc.querySelector('[data-trajectory="context"]')?.textContent.includes("走向回对"), false);
    assert.ok(recap.compareDocumentPosition(doc.querySelector('[data-trajectory="watch"]')) & 4);
  }
});

test("详情不移动非末尾或格式不完整的走向回对", () => {
  for (const context of [
    "走向回对（兑现）：已有结论。后面还有普通来龙。",
    "既有来龙。走向回对（大致兑现）：证据不足。",
    "既有来龙，没有回对。",
  ]) {
    const doc = new JSDOM(`<main>${renderDetail({ ...daily.items[0], trusted_continuation: true, context }, "news", daily.date)}</main>`).window.document;
    assert.equal(doc.querySelector(".trajectory-recap"), null);
    assert.match(doc.querySelector('[data-trajectory="context"]')?.textContent || "", new RegExp(context.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
});

test("一次性条目的前情标为起因而不是来龙", () => {
  const doc = new JSDOM(`<main>${renderDetail(daily.items[0], "news", daily.date)}</main>`).window.document;
  const context = doc.querySelector('[data-trajectory="context"]');
  assert.equal(context?.querySelector("h2")?.textContent, "起因");
  assert.match(context?.textContent || "", /背景机制/);
  assert.doesNotMatch(doc.body.textContent, /来龙/);
});

test("起因占据来龙同一槽位并保持阅读顺序", () => {
  const doc = new JSDOM(`<main>${renderDetail(daily.items[0], "news", daily.date)}</main>`).window.document;
  const sections = [...doc.querySelectorAll(".detail-trajectory > section")];
  assert.deepEqual(sections.map((node) => node.dataset.trajectory), ["context", "body", "why", "watch"]);
  assert.equal(sections[0].querySelector("h2")?.textContent, "起因");
});

test("延续条目的走向回对不被起因标题吞掉", () => {
  const item = { ...daily.items[0], trusted_continuation: true, context: "既有来龙。走向回对（兑现）：此前路标已有结论。" };
  const doc = new JSDOM(`<main>${renderDetail(item, "news", daily.date)}</main>`).window.document;
  assert.equal(doc.querySelector('[data-trajectory="context"]')?.querySelector("h2")?.textContent, "来龙");
  assert.ok(doc.querySelector(".trajectory-recap.recap-兑现"));
});

test("新闻详情缺失轨迹字段时省略对应段落并保持其余顺序", () => {
  const item = { ...daily.items[0], context: "", watch: "", watch_detail: "", significance: "" };
  const doc = new JSDOM(`<main>${renderDetail(item, "news", daily.date)}</main>`).window.document;
  const sections = [...doc.querySelectorAll(".detail-trajectory > section")];
  assert.deepEqual(sections.map((node) => node.dataset.trajectory), ["body", "why"]);
  assert.deepEqual(sections.map((node) => node.querySelector("h2")?.textContent), ["现状", "为什么重要"]);
});

test("新闻详情把来源列成相关链接并把事实源排在判断源之前", () => {
  const item = {
    ...daily.items[0],
    sources: [
      { name: "评论员专栏", url: "https://opinion.example.com/a", type: "舆论源" },
      { name: "官方公告", url: "https://www.official.example.org/b", type: "事实源" },
      { name: "行业分析", url: "https://analysis.example.net/c", type: "分析源" },
    ],
  };
  const doc = new JSDOM(`<main>${renderDetail(item, "news", daily.date)}</main>`).window.document;
  const rows = [...doc.querySelectorAll(".detail-links .link-list li")];
  assert.deepEqual(rows.map((node) => node.querySelector(".src-type")?.textContent), ["事实源", "分析源", "舆论源"]);
  assert.deepEqual(rows.map((node) => node.querySelector(".link-host")?.textContent),
    ["official.example.org", "analysis.example.net", "opinion.example.com"]);
  assert.ok(rows[0].querySelector(".src-type")?.classList.contains("t-fact"));
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
