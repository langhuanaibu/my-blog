import assert from "node:assert/strict";
import test from "node:test";
import { JSDOM } from "jsdom";
import { createRequire } from "node:module";

import { createNewsApp } from "../../source/news/js/app.js";
const TimelineCore = createRequire(import.meta.url)("../../source/news/news-timeline.js");
const NewsState = createRequire(import.meta.url)("../../api/newsState.js");

const day = {
  date: "2026-07-15", lead: "导语", themes: [], tracking: [{ event_id: "evt-1", title: "追踪事件", history: [] }],
  items: [
    { id: "pick-1", event_id: "evt-1", tier: "pick", category: "ai", title: "隐藏候选", summary: "摘要", why: "意义", sources: [{ name: "官方", url: "https://example.com/a" }] },
    { id: "pick-2", tier: "pick", category: "tech", title: "保留新闻", summary: "摘要二", why: "意义二", sources: [] },
    { id: "more-1", tier: "more", category: "world", title: "更多新闻", summary: "更多摘要", sources: [{ name: "原文", url: "https://example.com/m" }] },
  ],
  deep: [{ id: "deep-1", title: "Deep", title_zh: "深读", takeaway: "要点", key_points: ["关键点"], audience: "读者", url: "https://example.com/deep" }],
  papers: [{ id: "paper-1", title: "Paper", title_zh: "论文", takeaway: "结论", contribution: "贡献", evidence: "证据", limitations: "局限", url: "https://example.com/paper" }],
  opinion: [{ id: "op-1", title: "舆论", summary: "舆论说明", source: "X" }],
};

function shell(url = "https://example.test/news/?view=day&date=2026-07-15") {
  return new JSDOM(`<!doctype html><body><a data-view="timeline"></a><a data-view="all"></a><a data-view="reports"></a><a data-view="topics"></a><a id="favoritesNav" data-view="favs" hidden></a><div id="reportControls"><a data-period="day"></a><a data-period="week"></a><div id="dayArchive"><select id="dateSel"></select></div><div id="weekArchive"><select id="weekSel"></select></div></div><span id="dayCtrls"><button id="prevBtn"></button><button id="nextBtn"></button></span><input id="searchInput"><div id="searchRes"></div><main id="app"></main><div id="liveStatus"></div></body>`, { url, pretendToBeVisual: true });
}

function dataApi() {
  return {
    daily: async (date) => date === day.date ? structuredClone(day) : null,
    weeklyManifest: async () => ["2026-W28", "2026-W27"],
    weekly: async (week) => ({ week, coverage: { daily_count: 6, expected_days: 7, missing_dates: [] }, lead: { title: `周报 ${week}` }, threads: [] }),
    allManifest: async () => [day.date],
    allDay: async () => ({ date: day.date, min_score: 40, items: [{ id: "all-1", c: "ai", title: "全部动态一", score: 60, url: "https://example.com/all" }] }),
    index: async () => [[day.date, "pick-2", "pick", "tech", "保留新闻", "标签"]],
    events: async () => ({ events: [{ event_id: "evt-1", title: "主题事件", status: "active", pinned: false, history: [{ date: day.date, summary: "进展" }] }] }),
  };
}

test("app rewrites old route, marks seen and respects hidden state", async () => {
  const dom = shell();
  dom.window.localStorage.setItem("news_hidden", JSON.stringify({ "2026-07-15:pick-1": true }));
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: dataApi() });
  await app.start();
  assert.equal(dom.window.location.search, "?view=reports&period=day&date=2026-07-15");
  assert.equal(JSON.parse(dom.window.localStorage.getItem("news_seen_days"))[day.date], 1);
  assert.doesNotMatch(dom.window.document.querySelector("main").textContent, /隐藏候选/);
  assert.match(dom.window.document.querySelector("main").textContent, /深度阅读|今日论文|追踪中|舆论观察|更多资讯/);
  assert.ok(dom.window.document.querySelector("main h1"));
  assert.equal(dom.window.document.querySelector("#weekArchive").hidden, true);
  assert.equal(dom.window.document.querySelectorAll('div[role="button"],span[onclick],div[onclick]').length, 0);
});

test("weekly archive, browser Back and old week route are integrated", async () => {
  const dom = shell("https://example.test/news/?view=week&week=2026-W27");
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: dataApi() });
  await app.start();
  assert.equal(dom.window.location.search, "?view=reports&period=week&week=2026-W27");
  assert.match(dom.window.document.querySelector("main").textContent, /周报 2026-W27/);
  assert.equal(dom.window.document.querySelector("#dayArchive").hidden, true);
  dom.window.document.querySelector("#weekSel").value = "2026-W28";
  dom.window.document.querySelector("#weekSel").dispatchEvent(new dom.window.Event("change", { bubbles: true }));
  await app.idle();
  assert.equal(dom.window.location.search, "?view=reports&period=week&week=2026-W28");
  dom.window.history.back();
  await new Promise((resolve) => dom.window.setTimeout(resolve, 10));
  await app.idle();
  assert.match(dom.window.document.querySelector("main").textContent, /周报 2026-W27/);
});

test("personal not-interested stays in module layout and deep/paper details retain type fields", async () => {
  const dom = shell("https://example.test/news/?view=reports&period=day&date=2026-07-15");
  dom.window.localStorage.setItem("aoiblog_admin_token", "token");
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: dataApi(), fetch: async () => ({ ok: true, json: async () => ({ success: true, data: {} }) }) });
  await app.start();
  const hide = dom.window.document.querySelector('[data-action="not-interested"][data-ref="pick-1"]');
  hide.click();
  const submit = dom.window.document.querySelector('[data-action="submit-not-interested"]');
  submit.click();
  await app.idle();
  assert.doesNotMatch(dom.window.document.querySelector("main").textContent, /隐藏候选/);
  assert.match(dom.window.document.querySelector("main").textContent, /保留新闻/);
  await app.go({ view: "detail", date: day.date, type: "deep", item: "deep-1" });
  assert.match(dom.window.document.querySelector("main").textContent, /关键点|读者/);
  await app.go({ view: "detail", date: day.date, type: "paper", item: "paper-1" });
  assert.match(dom.window.document.querySelector("main").textContent, /贡献|证据|局限/);
});

test("empty manifest degrades and rendered interactions use native controls", async () => {
  const dom = shell("https://example.test/news/?view=timeline");
  const emptyApi = { ...dataApi(), daily: async () => null };
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: emptyApi, manifests: { daily: [] } });
  await app.start();
  assert.match(dom.window.document.querySelector("main").textContent, /还没有任何日报数据|暂无/);
  assert.equal(dom.window.document.querySelectorAll('div[role="button"],span[onclick],div[onclick]').length, 0);
});

test("personal actions preserve newsState storage and API contracts", async () => {
  const dom = shell("https://example.test/news/?view=reports&period=day&date=2026-07-15");
  dom.window.localStorage.setItem("aoiblog_admin_token", "token");
  const requests = [];
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: dataApi(), fetch: async (_url, init) => { requests.push(JSON.parse(init.body)); return { ok: true, json: async () => ({ success: true, data: {} }) }; } });
  await app.start();
  dom.window.document.querySelector('[data-action="like"][data-ref="pick-1"]').click();
  dom.window.document.querySelector('[data-action="favorite"][data-ref="pick-1"]').click();
  dom.window.document.querySelector('[data-action="read-later"][data-ref="pick-1"]').click();
  dom.window.document.querySelector('[data-action="source"][data-ref="pick-1"]').click();
  dom.window.document.querySelector('[data-action="down-source"]').click();
  await app.idle();
  assert.ok(requests.some((request) => request.type === "feedback" && request.payload.action === "more_like_this"));
  assert.ok(requests.some((request) => request.type === "feedback" && request.payload.action === "low_quality_source"));
  assert.ok(requests.some((request) => request.type === "favorites"));
  assert.ok(requests.some((request) => request.type === "read_later"));
  assert.equal(JSON.parse(dom.window.localStorage.getItem("news_like"))["2026-07-15:pick-1"], true);
});

test("timeline restores hot list, folding, filters, tags, search and older loading", async () => {
  const dates = Array.from({ length: 7 }, (_, index) => `2026-07-${String(15 - index).padStart(2, "0")}`);
  const api = dataApi(); api.daily = async (date) => ({ ...structuredClone(day), date, items: day.items.map((item) => ({ ...item, score: 82, time: `${date}T01:00:00Z`, tags: item.id === "pick-2" ? ["Agent"] : ["模型"] })) });
  const dom = shell("https://example.test/news/?view=timeline");
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api, manifests: { daily: dates } });
  await app.start();
  assert.ok(dom.window.document.querySelector(".hotbox"));
  assert.ok(dom.window.document.querySelector('[data-timeline-action="toggle-day"]'));
  assert.ok(dom.window.document.querySelector('[data-timeline-action="set-cat"]'));
  assert.ok(dom.window.document.querySelector('[data-timeline-action="set-tag"]'));
  const older = dom.window.document.querySelector('[data-timeline-action="more"]'); older.click(); await app.idle();
  assert.match(dom.window.document.querySelector("main").textContent, /2026-07-09/);
  const search = dom.window.document.querySelector("#timelineSearch"); search.value = "保留"; search.dispatchEvent(new dom.window.Event("input", { bubbles: true })); await app.idle();
  assert.match(dom.window.document.querySelector("main").textContent, /保留新闻/);
});

test("timeline uses production timeline helpers for publish-day grouping, continuation collapse and decayed event hotness", async () => {
  const dates = ["2026-07-15", "2026-07-14"];
  const api = dataApi(); api.daily = async (date) => ({ date, items: [{ id: `pick-${date}`, tier: "pick", category: "ai", event_id: "evt-same", title: "同一事件", summary: "相同进展", score: 82, time: date === dates[0] ? "2026-07-14T16:30:00Z" : "2026-07-14T10:00:00Z", sources: [{ name: date, url: `https://${date}.example.com/story` }] }] });
  const dom = shell("https://example.test/news/?view=timeline"); const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api, manifests: { daily: dates }, timelineApi: TimelineCore, now: new Date("2026-07-15T02:00:00Z").getTime() }); await app.start();
  assert.equal(dom.window.document.querySelectorAll(".timeline-day .report-card").length, 1);
  assert.match(dom.window.document.querySelector(".timeline-day").textContent, /2026-07-15/);
  assert.equal(dom.window.document.querySelectorAll(".hotbox .hot-row").length, 1);
  assert.match(dom.window.document.querySelector(".hotbox").textContent, /2 个独立信源/);
});

test("timeline renders actual published-date groups even when they differ from selected report dates", async () => {
  const api = dataApi(); api.daily = async () => ({ date: day.date, items: [{ id: "pick-old", tier: "pick", category: "ai", title: "前日发布", summary: "摘要", score: 80, time: "2026-07-13T16:30:00Z", sources: [] }] }); api.index = async () => [[day.date, "pick-old", "pick", "ai", "前日发布", "模型"]];
  const make = async (url) => { const dom = shell(url); const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api, manifests: { daily: [day.date] }, timelineApi: TimelineCore }); await app.start(); return { dom, app }; };
  const ordinary = await make("https://example.test/news/?view=timeline"); assert.match(ordinary.dom.window.document.querySelector(".timeline-day").textContent, /2026-07-14/); assert.match(ordinary.dom.window.document.querySelector(".timeline-day").textContent, /前日发布/);
  const searched = await make("https://example.test/news/?view=timeline"); const input = searched.dom.window.document.querySelector("#timelineSearch"); input.value = "前日"; input.dispatchEvent(new searched.dom.window.Event("input", { bubbles: true })); await new Promise((resolve) => setTimeout(resolve, 160)); await searched.app.idle(); assert.match(searched.dom.window.document.querySelector(".timeline-day").textContent, /2026-07-14/); assert.match(searched.dom.window.document.querySelector(".timeline-day").textContent, /前日发布/);
});

test("timeline search debounces typing, restores focus/caret and rejects stale async results", async () => {
  let calls = 0; const api = dataApi(); api.index = async () => { calls++; await new Promise((resolve) => setTimeout(resolve, calls === 1 ? 80 : 5)); return [[day.date, "pick-a", "pick", "tech", "保X", "Agent"], [day.date, "pick-2", "pick", "tech", "保留新闻", "Agent"]]; }; api.daily = async () => ({ ...structuredClone(day), items: [...day.items, { id: "pick-a", tier: "pick", category: "tech", title: "保X", summary: "A", tags: ["Agent"] }].map((item) => ({ ...item, tags: item.tags || ["Agent"] })) });
  const dom = shell("https://example.test/news/?view=timeline"); const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api, manifests: { daily: [day.date] } }); await app.start();
  let input = dom.window.document.querySelector("#timelineSearch"); input.focus(); input.value = "保"; input.setSelectionRange(1, 1); input.dispatchEvent(new dom.window.Event("input", { bubbles: true })); await new Promise((resolve) => setTimeout(resolve, 140));
  input = dom.window.document.querySelector("#timelineSearch"); input.value = "保留"; input.setSelectionRange(2, 2); input.dispatchEvent(new dom.window.Event("input", { bubbles: true })); await new Promise((resolve) => setTimeout(resolve, 220)); await app.idle();
  const cardText = [...dom.window.document.querySelectorAll(".timeline-day .report-card")].map((node) => node.textContent).join(" "); assert.match(cardText, /保留新闻/); assert.doesNotMatch(cardText, /保X/); assert.equal(dom.window.document.activeElement.id, "timelineSearch"); assert.equal(dom.window.document.activeElement.selectionStart, 2);
});

test("all dynamics restores score threshold, category, show-all and older loading", async () => {
  const api = dataApi(); api.allManifest = async () => Array.from({ length: 8 }, (_, index) => `2026-07-${String(15 - index).padStart(2, "0")}`); api.allDay = async (date) => ({ date, min_score: 40, items: [{ id: "high", c: "ai", t: "高分", score: 60 }, { id: "low", c: "world", t: "低分", score: 20 }] });
  const dom = shell("https://example.test/news/?view=all"); const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api }); await app.start();
  assert.match(dom.window.document.querySelector("main").textContent, /高分/); assert.doesNotMatch([...dom.window.document.querySelectorAll("main article strong")].map((node) => node.textContent).join(" "), /低分/);
  dom.window.document.querySelector('[data-all-action="show-all"]').click(); await app.idle(); assert.match([...dom.window.document.querySelectorAll("main article strong")].map((node) => node.textContent).join(" "), /低分/);
  assert.ok(dom.window.document.querySelector('[data-all-action="set-cat"]')); dom.window.document.querySelector('[data-all-action="more"]').click(); await app.idle(); assert.match(dom.window.document.querySelector("main").textContent, /2026-07-08/);
});

test("topics restores groups/map and local tracked override has stable direction", async () => {
  const api = dataApi(); api.events = async () => ({ events: [
    { event_id: "pin", title: "追踪主题", status: "active", pinned: true, history: [{ date: day.date, summary: "A" }, { date: "2026-07-14", summary: "B" }] },
    { event_id: "run", title: "进行主题", status: "active", pinned: false, history: [{ date: day.date, summary: "A" }, { date: "2026-07-14", summary: "B" }] },
    { event_id: "arc", title: "归档主题", status: "archived", history: [{ date: day.date, summary: "A" }, { date: "2026-07-14", summary: "B" }] },
  ] }); api.index = async () => [[day.date, "pick-1", "pick", "ai", "新闻", "Agent|模型"], [day.date, "deep-1", "deep", "ai", "深读", "不应统计"]]; api.daily = async () => ({ ...structuredClone(day), items: day.items.map((item) => ({ ...item, tags: ["Agent"] })) });
  const requests = []; const dom = shell("https://example.test/news/?view=topics"); dom.window.localStorage.setItem("aoiblog_admin_token", "token");
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api, manifests: { daily: [day.date] }, fetch: async (_url, init) => { requests.push(JSON.parse(init.body)); return { ok: true, json: async () => ({ success: true, data: {} }) }; } }); await app.start();
  assert.match(dom.window.document.querySelector("main").textContent, /追踪中|进行中|已归档|题材地图/);
  const untrack = dom.window.document.querySelector('[data-event="pin"]'); assert.match(untrack.textContent, /取消追踪/); untrack.click(); await app.idle();
  assert.equal(JSON.parse(dom.window.localStorage.getItem("news_tracked")).pin, false);
  const untrackRequest = requests.find((request) => request.payload.action === "untrack");
  assert.equal(untrackRequest.payload.date, day.date);
  assert.doesNotThrow(() => NewsState._test.validateEntry("feedback", untrackRequest.payload));
  assert.match(dom.window.document.querySelector('[data-event="pin"]').textContent, /追踪/);
  assert.doesNotMatch(dom.window.document.querySelector("main").textContent, /不应统计/); const agent = [...dom.window.document.querySelectorAll(".topic-card")].find((node) => node.textContent.includes("Agent")); agent.click(); await app.idle(); assert.match(dom.window.document.querySelector("main").textContent, /保留新闻/);
});

test("favorites uses server truth, backfills local/index, and read-later supports done/remove", async () => {
  const dom = shell("https://example.test/news/?view=favs"); dom.window.document.body.insertAdjacentHTML("beforeend", '<button id="readLaterBtn" hidden></button><aside id="rlDrawer" hidden inert></aside>'); dom.window.localStorage.setItem("aoiblog_admin_token", "token");
  const requests = [];
  const fetchStub = async (url, init = {}) => {
    if (!init.method && String(url).includes("type=favorites")) return { ok: true, json: async () => ({ success: true, data: { items: [{ date: day.date, item_id: "pick-2", title: "保留新闻", category: "tech" }] } }) };
    if (!init.method && String(url).includes("type=read_later")) return { ok: true, json: async () => ({ success: true, data: { items: [{ date: day.date, item_id: "deep-1", title: "深读", url: "https://example.com/deep", done: false }] } }) };
    requests.push(JSON.parse(init.body)); return { ok: true, json: async () => ({ success: true, data: {} }) };
  };
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: dataApi(), fetch: fetchStub }); await app.start();
  assert.match(dom.window.document.querySelector("main").textContent, /保留新闻/); assert.equal(JSON.parse(dom.window.localStorage.getItem("news_fav"))[`${day.date}:pick-2`], 1);
  dom.window.document.querySelector('[data-action="favorite"][data-ref="pick-2"]').click(); await app.idle(); assert.ok(requests.some((request) => request.type === "favorites" && request.payload.item_id === "pick-2")); assert.doesNotMatch(dom.window.document.querySelector("main").textContent, /保留新闻/);
  dom.window.document.querySelector("#readLaterBtn").click(); await app.idle(); assert.equal(dom.window.document.querySelector("#rlDrawer").hidden, false); assert.ok(dom.window.document.querySelector('[data-read-later-op="done"]')); dom.window.document.querySelector('[data-read-later-op="done"]').click(); await app.idle(); assert.ok(requests.some((request) => request.type === "read_later" && request.payload.op === "done")); dom.window.document.querySelector('[data-read-later-op="remove"]').click(); await app.idle(); assert.ok(requests.some((request) => request.type === "read_later" && request.payload.op === "remove")); dom.window.document.querySelector("[data-close-drawer]").click(); assert.equal(dom.window.document.querySelector("#rlDrawer").hidden, true); assert.equal(dom.window.document.activeElement.id, "readLaterBtn");
});

test("route load errors render malicious week values as text", async () => {
  const payload = '<img src=x onerror="globalThis.pwned=1"><script>globalThis.pwned=2</script>';
  const dom = shell(`https://example.test/news/?view=reports&period=week&week=${encodeURIComponent(payload)}`);
  const api = { ...dataApi(), weeklyManifest: async () => [payload], weekly: async () => { throw new Error(`坏周报 ${payload}`); } };
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api });
  await app.start();
  const main = dom.window.document.querySelector("main");
  assert.equal(main.querySelector("img,script"), null);
  assert.match(main.textContent, /坏周报 <img/);
  assert.equal(dom.window.pwned, undefined);
});

test("read-later rejects unsafe URLs and escapes quoted data attributes", async () => {
  const dom = shell("https://example.test/news/?view=reports&period=day&date=2026-07-15");
  dom.window.document.body.insertAdjacentHTML("beforeend", '<button id="readLaterBtn" hidden></button><aside id="rlDrawer" hidden inert></aside>');
  dom.window.localStorage.setItem("aoiblog_admin_token", "token");
  const malicious = { date: '2026-07-15" autofocus="', item_id: 'deep-1" data-evil="1', title: "<b>标题</b>", url: "javascript:alert(1)", done: false };
  const fetchStub = async (url) => String(url).includes("type=read_later")
    ? { ok: true, json: async () => ({ success: true, data: { items: [malicious] } }) }
    : { ok: true, json: async () => ({ success: true, data: {} }) };
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: dataApi(), fetch: fetchStub });
  await app.start();
  dom.window.document.querySelector("#readLaterBtn").click();
  await app.idle();
  const drawer = dom.window.document.querySelector("#rlDrawer");
  assert.equal(drawer.querySelector("a").getAttribute("href"), "#");
  assert.equal(drawer.querySelector("b"), null);
  assert.match(drawer.textContent, /<b>标题<\/b>/);
  assert.equal(drawer.querySelector("[autofocus], [data-evil]"), null);
  assert.equal(drawer.querySelector('[data-read-later-op="done"]').dataset.date, malicious.date);
  assert.equal(drawer.querySelector('[data-read-later-op="done"]').dataset.item, malicious.item_id);
});
