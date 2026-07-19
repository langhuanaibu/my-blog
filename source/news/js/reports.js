import { routeUrl } from "./router.js";

export const CATEGORY_LABELS = { ai: "AI", tech: "互联网/科技", finance: "财经", society: "社会", world: "国际" };
const CATEGORY_KEYS = Object.keys(CATEGORY_LABELS);
const STATUS_CLASSES = new Set(["已确认", "发展中", "有争议", "仅传言"]);
export const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
export const safeUrl = (value) => /^https?:\/\//i.test(value || "") ? escapeHtml(value) : "#";

function annualIssue(date) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date || "");
  if (!match) return "";
  const [, yearText, monthText, dayText] = match;
  const year = Number(yearText); const month = Number(monthText); const day = Number(dayText);
  const stamp = Date.UTC(year, month - 1, day);
  const parsed = new Date(stamp);
  if (parsed.getUTCFullYear() !== year || parsed.getUTCMonth() !== month - 1 || parsed.getUTCDate() !== day) return "";
  const issue = Math.floor((stamp - Date.UTC(year, 0, 1)) / 86400000) + 1;
  return `${year} · 第${issue}期`;
}

function displayDate(date) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date || "");
  return match ? `${Number(match[2])}月${Number(match[3])}日` : "今日日报";
}

export function sourceLinks(item) {
  const sources = item.sources?.length ? item.sources : (item.url ? [{ name: item.source || "原文", url: item.url }] : []);
  return sources.map((source) => `<a href="${safeUrl(source.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(source.name || "原文")}</a>`).join("");
}

export function actionButtons(item, options = {}) {
  const { personal = false, date = "", type = "news" } = options;
  if (!personal) return "";
  const ref = escapeHtml(item.id); const event = item.event_id;
  const key = `${date}:${item.id}`; const state = options;
  const readLater = Boolean(state.readLater?.[key]); const favorite = Boolean(state.favorites?.[key]); const liked = Boolean(state.liked?.[key]); const tracked = Boolean(event && state.tracked?.[event]);
  const readLaterButton = `<button type="button" class="act ${readLater ? "done" : ""}" data-action="read-later" data-ref="${ref}" data-date="${date}" data-type="${type}">${readLater ? "✓ 已收" : "⏳ 稍后读"}</button>`;
  const favoriteButton = `<button type="button" class="act ${favorite ? "done" : ""}" data-action="favorite" data-ref="${ref}" data-date="${date}" data-type="${type}">${favorite ? "★ 已藏" : "⭐ 收藏"}</button>`;
  const newsMenu = type === "news" ? `<button type="button" class="act ${liked ? "done" : ""}" data-action="like" data-ref="${ref}" data-date="${date}">${liked ? "👍 已记录" : "👍 更多类似"}</button>${event ? `<button type="button" class="act ${tracked ? "done" : ""}" data-action="track" data-ref="${ref}" data-event="${escapeHtml(event)}" data-date="${date}">${tracked ? "📌 追踪中" : "📌 追踪"}</button>` : ""}<button type="button" class="act" data-action="source" data-ref="${ref}" data-date="${date}">🚫 来源</button>` : "";
  return `<div class="acts" aria-label="个人操作">
    ${type === "news" ? `<button type="button" class="act" data-action="not-interested" data-ref="${ref}" data-date="${date}">✕ 不感兴趣</button>` : ""}
    ${favoriteButton}
    <details class="action-overflow"><summary class="act" aria-label="更多操作">⋯</summary><div class="action-menu">${readLaterButton}${newsMenu}</div></details>
  </div><div class="fb-panel" aria-live="polite"></div>`;
}

export function dailyCard(item, date, options = {}) {
  const timeline = options.timeline || null;
  return `<article class="card report-card${timeline ? ` timeline-entry${timeline.continuation ? " is-continuation" : ""}` : ""}" data-item-id="${escapeHtml(item.id)}">
    <div class="card-top">${timeline?.time ? `<time class="timeline-time" datetime="${escapeHtml(item.time || "")}">${escapeHtml(timeline.time)}</time>` : ""}<span class="tag cat-${escapeHtml(item.category)}">${escapeHtml(CATEGORY_LABELS[item.category] || item.category)}</span>${item.is_update ? '<span class="tag update-mark">重大更新</span>' : ""}${timeline?.continuation ? '<span class="continuation-mark">延续</span>' : ""}${item.status ? `<span class="tag${STATUS_CLASSES.has(item.status) ? ` st-${item.status}` : ""}">${escapeHtml(item.status)}</span>` : ""}${Number.isFinite(item.score) ? `<span class="score-num">${item.score}</span>` : ""}</div>
    <h3><a href="${routeUrl({ view: "detail", date, type: "news", item: item.id })}" data-route>${escapeHtml(item.title)}</a></h3>
    ${item.summary ? `<p class="sum">${escapeHtml(item.summary)}</p>` : ""}
    ${item.why ? `<div class="kv why"><b>为什么重要：</b>${escapeHtml(item.why)}</div>` : ""}
    <div class="srcs">${sourceLinks(item)}</div>${actionButtons(item, { ...options, date, type: "news" })}
  </article>`;
}

function readMinutes(data) {
  if (Number.isFinite(data?.read_minutes)) return data.read_minutes;
  const text = [data?.lead, data?.brief, ...(data?.items || []).flatMap((item) => [item.summary, item.why])].filter(Boolean).join("");
  return Math.max(1, Math.ceil(text.length / 500));
}

function contentCard(item, type, date, options) {
  const title = item.title_zh || item.title || item.summary || "未命名";
  const detail = type === "opinion" ? "" : routeUrl({ view: "detail", date, type, item: item.id });
  return `<article class="deep ${type === "paper" ? "paper" : type === "opinion" ? "pulse" : ""}" data-item-id="${escapeHtml(item.id)}">
    <h3>${detail ? `<a href="${detail}" data-route>${escapeHtml(title)}</a>` : escapeHtml(title)}</h3>
    ${item.summary || item.brief || item.why_hot ? `<p>${escapeHtml(item.summary || item.brief || item.why_hot)}</p>` : ""}${item.why || item.takeaway || (type === "opinion" && item.mechanism) ? `<div class="kv why"><b>${type === "opinion" ? "传播机制" : "值得读"}：</b>${escapeHtml(item.why || item.takeaway || item.mechanism)}</div>` : ""}
    <div class="srcs">${sourceLinks(item)}</div>${type !== "opinion" ? actionButtons(item, { ...options, date, type }) : ""}
  </article>`;
}

export function collectionCard(item, type, date, options = {}) {
  return type === "news" ? dailyCard(item, date, options) : contentCard(item, type, date, options);
}

function trackingCard(item, date, options) {
  return `<article class="trk"><div class="trk-top"><h3>${escapeHtml(item.title)}</h3>${options.personal ? `<button type="button" class="act" data-action="untrack" data-event="${escapeHtml(item.event_id)}" data-date="${date}">取消追踪</button>` : ""}</div><div class="trk-hist">${(item.history || []).map((row) => `<p><a href="${routeUrl({ view: "reports", period: "day", date: row.date })}" data-route>${escapeHtml(row.date)}</a> ${escapeHtml(row.summary)}</p>`).join("") || "暂无进展"}</div></article>`;
}

function moreCard(item, date) {
  const url = item.url || item.sources?.[0]?.url;
  return `<article class="row"><strong>${escapeHtml(item.title)}</strong>${item.summary ? `<span>${escapeHtml(item.summary)}</span>` : ""}${url ? `<a href="${safeUrl(url)}" target="_blank" rel="noopener noreferrer">原文</a>` : ""}<a href="${routeUrl({ view: "detail", date, type: "news", item: item.id })}" data-route>详情</a></article>`;
}

export function renderDailyReport(data, options = {}) {
  if (!data) return '<div class="empty" role="status">暂无日报数据</div>';
  const hidden = options.hidden || {};
  const picks = (data.items || []).filter((item) => item.tier === "pick" && !hidden[`${data.date}:${item.id}`]);
  const hiddenCount = (data.items || []).filter((item) => item.tier === "pick" && hidden[`${data.date}:${item.id}`]).length;
  const continued = picks.filter((item) => Number(item.day_count || 0) >= 2).length;
  const sections = CATEGORY_KEYS.map((category) => {
    const rows = picks.filter((item) => item.category === category);
    return `<section class="report-section" data-category="${category}" aria-labelledby="cat-${category}"><h2 id="cat-${category}" class="sec-title">${CATEGORY_LABELS[category]} <span class="n">${rows.length} 篇</span></h2><div class="report-list">${rows.length ? rows.map((item) => dailyCard(item, data.date, options)).join("") : '<p class="section-empty">今日暂无精选</p>'}</div></section>`;
  }).join("");
  const themes = (data.themes || []).slice(0, 3);
  const supplementary = [
    ["追踪中", "tracking", (data.tracking || []).map((item) => trackingCard(item, data.date, options))],
    ["深度阅读", "deep", (data.deep || []).map((item) => contentCard(item, "deep", data.date, options))],
    ["今日论文", "papers", (data.papers || []).map((item) => contentCard(item, "paper", data.date, options))],
    ["舆论观察", "opinion", (data.opinion || []).map((item) => contentCard(item, "opinion", data.date, options))],
    ["更多资讯", "more", (data.items || []).filter((item) => item.tier === "more").map((item) => moreCard(item, data.date))],
  ].filter(([, , rows]) => rows.length).map(([title, kind, rows]) => `<section class="supplemental" data-kind="${kind}"><h2 class="sec-title">${title}</h2><div class="more-list">${rows.join("")}</div></section>`).join("");
  const dateLabel = displayDate(data.date); const issue = annualIssue(data.date);
  return `<article class="daily-report"><header class="masthead"><div class="mast-plate"><span class="date-seal" aria-hidden="true"><b>${dateLabel.replace("月", "月<br>")}</b></span><span class="mast-name">每日驾驶舱</span>${issue ? `<span class="mast-issue">${issue}</span>` : ""}</div><div class="mast-meta"><time datetime="${escapeHtml(data.date || "")}">${escapeHtml(dateLabel)}</time><span>约 ${readMinutes(data)} 分钟</span><span>今日新事件 <b>${picks.length - continued}</b></span><span>延续事件 <b>${continued}</b></span></div><h1 class="mast-lead">${escapeHtml(data.lead || data.brief || "今日日报")}</h1></header>${themes.length ? `<section class="mainlines"><h2 class="ml-h">今日主线</h2>${themes.map((theme) => `<article class="ml-item"><h3 class="ml-t">${escapeHtml(theme.title)}</h3><p class="ml-o">${escapeHtml(theme.overview || theme.one_liner || "")}</p></article>`).join("")}</section>` : ""}${hiddenCount ? `<div class="hidden-bar">已隐藏 ${hiddenCount} 条 <button type="button" class="act" data-action="restore-hidden" data-date="${data.date}">全部恢复</button></div>` : ""}${sections}${supplementary}</article>`;
}

function claimsHtml(item) {
  const claims = (item.claims || []).filter((claim) => claim?.text);
  const kindLabels = { fact: "事实", analysis: "分析", uncertain: "待核实" };
  return claims.length ? `<section><h2 class="detail-sec-t">事实与判断</h2><ul class="detail-claims">${claims.map((claim) => {
    const kind = Object.hasOwn(kindLabels, claim.kind) ? claim.kind : "uncertain";
    const sources = Array.isArray(claim.sources) ? claim.sources.filter((source) => typeof source === "string" && source.trim()) : [];
    return `<li class="detail-claim kind-${kind}"><span class="claim-kind">${kindLabels[kind]}</span>${escapeHtml(claim.text)}${sources.length ? `<div class="claim-sources">来源：${sources.map(escapeHtml).join("、")}</div>` : ""}</li>`;
  }).join("")}</ul></section>` : "";
}

function evidenceHtml(item) {
  const evidence = item.evidence;
  const basisLabels = { fulltext: "全文证据", mixed: "混合证据", snippet: "摘要证据" };
  const sources = item.sources;
  if (!evidence || typeof evidence !== "object" || Array.isArray(evidence)
    || !Object.hasOwn(basisLabels, evidence.basis)
    || typeof evidence.degraded !== "boolean"
    || !Number.isInteger(evidence.publisher_count) || evidence.publisher_count < 1
    || !Number.isInteger(evidence.independent_chain_count) || evidence.independent_chain_count < 0
    || evidence.independent_chain_count > evidence.publisher_count
    || !Array.isArray(sources) || sources.length === 0) return "";
  const mappingValid = sources.every((source) => source && typeof source === "object" && !Array.isArray(source)
    && typeof source.name === "string" && source.name.trim()
    && typeof source.url === "string" && source.url.trim()
    && (source.evidence_basis === "fulltext" || source.evidence_basis === "snippet")
    && (!Object.hasOwn(source, "evidence_chain")
      || (typeof source.evidence_chain === "string" && source.evidence_chain.trim())));
  if (!mappingValid) return "";
  const publisherKeys = sources.map((source) => source.name.trim().toLocaleLowerCase());
  const sourceUrls = sources.map((source) => source.url.trim());
  if (new Set(publisherKeys).size !== sources.length || new Set(sourceUrls).size !== sources.length) return "";
  const chainKeys = new Set(sources
    .filter((source) => Object.hasOwn(source, "evidence_chain"))
    .map((source) => source.evidence_chain.trim().toLocaleLowerCase()));
  const sourceBases = sources.map((source) => source.evidence_basis);
  const derivedBasis = sourceBases.every((basis) => basis === "fulltext")
    ? "fulltext" : sourceBases.some((basis) => basis === "fulltext") ? "mixed" : "snippet";
  if (evidence.publisher_count !== publisherKeys.length
    || evidence.independent_chain_count !== chainKeys.size
    || evidence.basis !== derivedBasis) return "";
  const publishers = evidence.publisher_count === 1 ? "单一发布源" : `${evidence.publisher_count} 个发布源`;
  return `<section class="detail-evidence" aria-label="证据概览"><h2 class="detail-sec-t">证据概览</h2><div class="evidence-meta"><span>${publishers}</span><span>独立证据链 ${evidence.independent_chain_count} 条</span><span>${basisLabels[evidence.basis]}</span>${evidence.degraded === true ? '<span class="evidence-degraded">证据降级</span>' : ""}</div></section>`;
}

export function renderDetail(item, type = "news", date = "", options = {}) {
  if (!item) return '<div class="empty">找不到这条内容（可能数据未加载）</div>';
  const title = item.title_zh || item.title;
  const common = item.summary || item.brief ? `<p class="detail-lede">${escapeHtml(item.summary || item.brief)}</p>` : "";
  const update = type === "news" && item.is_update ? `<div class="detail-update"><b>重大更新</b>${item.first_seen ? ` · 首次收录：${escapeHtml(item.first_seen)}` : ""}</div>` : "";
  let body = "";
  if (type === "news") body = `${item.detail ? `<div class="detail-body"><p>${escapeHtml(item.detail)}</p></div>` : ""}<div class="detail-kv">${[["为什么重要", item.why], ["背景机制", item.context], ["对我的意义", item.significance], ["后续关注", item.watch]].filter(([, value]) => value).map(([label, value]) => `<div class="kv"><b>${label}：</b>${escapeHtml(value)}</div>`).join("")}</div>${evidenceHtml(item)}${claimsHtml(item)}`;
  if (type === "deep") body = `${item.why ? `<div class="kv why"><b>为什么值得读：</b>${escapeHtml(item.why)}</div>` : ""}${item.takeaway ? `<div class="detail-takeaway"><b>核心观点：</b>${escapeHtml(item.takeaway)}</div>` : ""}${(item.key_points || []).length ? `<section><h2 class="detail-sec-t">关键点</h2><ul>${item.key_points.map((point) => `<li>${escapeHtml(point)}</li>`).join("")}</ul></section>` : ""}${item.audience ? `<div class="kv"><b>适合读者：</b>${escapeHtml(item.audience)}</div>` : ""}`;
  if (type === "paper") body = `${item.why ? `<div class="kv why"><b>为什么值得读：</b>${escapeHtml(item.why)}</div>` : ""}${item.takeaway ? `<div class="detail-takeaway"><b>研究结论：</b>${escapeHtml(item.takeaway)}</div>` : ""}${[["贡献", item.contribution], ["证据", item.evidence], ["局限", item.limitations]].filter(([, value]) => value).map(([label, value]) => `<div class="kv"><b>${label}：</b>${escapeHtml(value)}</div>`).join("")}`;
  return `<article class="detail-wrap reading-view"><a class="dback" href="${routeUrl({ view: "reports", period: "day", date })}" data-route>← 返回 ${escapeHtml(date)} 当日</a><h1 class="detail-title">${escapeHtml(title)}</h1>${common}${update}${body}<div class="srcs">${sourceLinks(item)}</div>${actionButtons(item, { ...options, date, type })}</article>`;
}

function refLink(ref, title) { const [date, ...rest] = String(ref || "").split(":"); const item = rest.join(":"); if (!date || !item) return ""; const type = item.startsWith("deep-") ? "deep" : item.startsWith("paper-") ? "paper" : "news"; return `<a data-ref="${escapeHtml(ref)}" href="${routeUrl({ view: "detail", date, type, item })}" data-route>${escapeHtml(title || ref)}</a>`; }

export function renderWeeklyReport(data) {
  if (!data) return '<div class="empty" role="status">暂无周报数据</div>';
  const coverage = data.coverage || {}; const lead = typeof data.lead === "string" ? { title: data.lead } : (data.lead || {}); const stats = data.stats || {}; const missing = coverage.missing_dates || [];
  const reading = Array.isArray(data.reading) ? data.reading : [
    ...(data.reading?.deep || []), ...(data.reading?.papers || []),
    ...(data.reading?.deep_refs || []).map((ref) => ({ ref, title: "深度阅读" })),
    ...(data.reading?.paper_refs || []).map((ref) => ({ ref, title: "研究论文" })),
  ];
  return `<article class="weekly-report weekly-reading"><header class="brief"><div class="bt">${escapeHtml(data.week || "周报")}</div><h1>${escapeHtml(lead.title || "本周综述")}</h1>${lead.summary ? `<p>${escapeHtml(lead.summary)}</p>` : ""}${coverage.daily_count != null ? `<p class="coverage">覆盖 ${coverage.daily_count}/${coverage.expected_days || 7} 期${missing.length ? ` · 缺失：${missing.map(escapeHtml).join("、")}` : ""}</p>` : ""}</header>${Object.keys(stats).length ? `<dl class="weekly-stats"><div><dt>精选</dt><dd>${escapeHtml(stats.pick_count ?? 0)}</dd></div><div><dt>独立事件</dt><dd>${escapeHtml(stats.event_count ?? stats.unique_event_count ?? 0)}</dd></div><div><dt>信源</dt><dd>${escapeHtml(stats.source_count ?? 0)}</dd></div><div><dt>阅读</dt><dd>${escapeHtml(stats.read_minutes ?? 0)} 分钟</dd></div></dl>` : ""}<section class="weekly-section weekly-threads"><h2 class="sec-title">动态主题</h2>${(data.threads || []).map((thread) => `<article class="wk-thread"><h3>${escapeHtml(thread.title)} ${thread.direction ? `<span class="tag dir-${escapeHtml(thread.direction)}">${escapeHtml(thread.direction)}</span>` : ""}</h3><p>${escapeHtml(thread.summary || thread.one_liner || thread.detail || "")}</p><div class="representatives">${(thread.representative_refs || []).map((ref) => refLink(ref, "代表报道")).join("")}</div></article>`).join("") || '<p class="section-empty">暂无主题</p>'}</section>${(data.watch_recap || []).length ? `<section class="weekly-section"><h2 class="sec-title">上周判断回收</h2>${data.watch_recap.map((row) => `<article class="wk-recap"><strong>${escapeHtml(row.title || row.watch)}</strong><span>${escapeHtml(row.note || row.result || "")}</span>${(row.evidence_refs || []).map((ref) => refLink(ref, "支撑报道")).join("")}</article>`).join("")}</section>` : ""}${reading.length ? `<section class="weekly-section"><h2 class="sec-title">本周值得读</h2><div class="reading-list">${reading.map((row) => refLink(row.ref || row.item_ref, row.title || row.ref)).join("")}</div></section>` : ""}${(data.outlook || []).length ? `<section class="weekly-section"><h2 class="sec-title">下周信号</h2><ul>${data.outlook.map((row) => `<li>${escapeHtml(typeof row === "string" ? row : row.text || row.title)}</li>`).join("")}</ul></section>` : ""}</article>`;
}
