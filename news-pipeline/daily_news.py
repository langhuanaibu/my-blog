# -*- coding: utf-8 -*-
"""
每日新闻驾驶舱 - 聚合管线
用法:
    python daily_news.py              # 正常跑：抓取 -> LLM 处理 -> 生成当日数据
    python daily_news.py --dry-run    # 只抓取不调 LLM，检查各源是否正常
    python daily_news.py --date 2026-07-03   # 指定输出日期（默认今天）

流程:
    1. 抓取 sources.yaml 里所有启用的源（RSS + AI HOT API）
    2. 时间窗过滤、清洗、限量
    3. 预筛（便宜模型）：丢弃垃圾/无关条目，主模型只处理幸存者
    4. LLM 阶段A：去重聚类 + 分类 + 五维分项打分（影响面/新颖/实质/佐证/持续）
    5. 代码合成最终分：维度加权 + 来源可信度 + 信源层级乘数(T1/T1.5/T2) + 兴趣权重
       阈值制精选：过线才进精选（含上下限与五类保底），不硬凑固定条数
       硬约束：纯舆论源事件封顶在阈值之下，只能进"更多资讯"
    6. LLM 阶段B：对精选生成 一句话摘要 / 为什么重要 / 后续关注 / 状态标记
    7. 写入 data/daily/YYYY-MM-DD.js 和 data/manifest.js（前端直接读）
    8. 更新 data/source_health.json：滚动记录 14 天各源抓取状态，
       连续 3 天抓取失败的源发 GitHub Actions ::warning:: 注解
"""
import argparse
import concurrent.futures
import hashlib
import html
import json
from email.utils import format_datetime
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import feedparser
import requests
import yaml

# Windows 控制台中文输出
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

CATEGORIES = ["ai", "tech", "finance", "society", "world"]
CAT_NAMES = {"ai": "AI", "tech": "互联网/科技", "finance": "财经",
             "society": "社会", "world": "国际"}
TYPE_NAMES = {"fact": "事实源", "analysis": "分析源", "opinion": "舆论源"}
STATUS_SET = {"已确认", "发展中", "有争议", "仅传言"}
TIER_ORDER = {"T1": 0, "T1.5": 1, "T2": 2}
DIMS = ["impact", "novelty", "substance", "evidence", "durability"]


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ----------------------------------------------------------------
# 1. 抓取
# ----------------------------------------------------------------

def strip_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_time(entry):
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def http_get(url, timeout=20, retries=2, backoff=1.5):
    """带指数退避的 GET；全部尝试失败才抛。retries 指额外重试次数。
    治 AIHOT 连接重置这类偶发失败——单次 requests.get 一挂整源归零。"""
    last = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as e:
            last = e
            if attempt < retries:
                time.sleep(backoff * (attempt + 1))
    raise last


def fetch_rss(src, window_start, max_items):
    """返回 (items, fetch_error)。fetch_error=True 表示抓取本身失败，
    与"源正常但窗口内无新文章"（items 为空、error=False）区分开。"""
    try:
        resp = http_get(src["url"])
        feed = feedparser.parse(resp.content)
    except Exception as e:
        log(f"  ✗ {src['name']}: 抓取失败 ({e})")
        return [], True
    items = []
    for e in feed.entries:
        pub = parse_time(e)
        if pub is None or pub < window_start:
            continue
        title = strip_html(e.get("title", ""))
        link = e.get("link", "")
        if not title or not link:
            continue
        # 全文长度指标（仅深读频道估算阅读时长用，不存全文本身）
        content = ""
        if e.get("content"):
            try:
                content = strip_html(e["content"][0].get("value", ""))
            except Exception:
                content = ""
        if not content:
            content = strip_html(e.get("summary", e.get("description", "")))
        items.append({
            "title": title,
            "url": link,
            "desc": strip_html(e.get("summary", e.get("description", "")))[:400],
            "content_chars": len(re.sub(r"\s", "", content)),
            "content_words": len(content.split()),
            "time": pub.isoformat(),
            "source": src["name"],
            "source_id": src["id"],
            "source_type": src["source_type"],
            "tier": src.get("tier", "T2"),
            "credibility": src["credibility"],
        })
    items.sort(key=lambda x: x["time"], reverse=True)
    return items[:max_items], False


# AI HOT 分类 → 主题标签提示：enrich 阶段优先采纳，保证论文/技巧观点不被大类淹没。
# 值必须在 config.yaml 的 topic_tags 词表里，否则会被过滤掉。
AIHOT_TAG_HINT = {
    "ai-models": "模型发布",
    "ai-products": "产品发布",
    "paper": "研究论文",
    "tip": "技巧观点",
}


def fetch_aihot(src, window_start, max_items):
    """AI HOT 公开 API 适配器（精选池）。返回 (items, fetch_error)。
    AIHOT 是最对味的中文 AI 源、已精选噪音低，是 AI 深度的独木——放宽单源取量
    （不受全局 max_per_source 压制），让它多供给。"""
    cap = max(max_items, 40)
    since = window_start.strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f"{src['url']}?mode=selected&since={since}&take={min(cap * 2, 100)}"
    try:
        resp = http_get(url)
        data = resp.json()
    except Exception as e:
        log(f"  ✗ {src['name']}: 抓取失败 ({e})")
        return [], True
    items = []
    for it in data.get("items", []):
        inner = it.get("source", "")
        # 按 AI HOT 的内部来源粗分类型：X 推文算舆论，公众号算分析，其余算事实
        if inner.startswith("X："):
            stype, tier = "opinion", "T2"
        elif inner.startswith("公众号"):
            stype, tier = "analysis", "T2"
        else:
            stype, tier = src["source_type"], src.get("tier", "T1.5")
        # source_id 透传 AIHOT 内部真实来源：多源加分/同源封顶按真实出处计数，
        # 统一记成 "aihot" 会把独立信源信号压扁（多家报道被当成同一来源）
        sid = f"{src['id']}:{re.sub(r'\s+', '', inner)}" if inner else src["id"]
        items.append({
            "title": it.get("title") or it.get("title_en") or "",
            "url": it.get("url", ""),
            "desc": (it.get("summary") or "")[:400],
            "time": it.get("publishedAt") or datetime.now(timezone.utc).isoformat(),
            "source": f"AI HOT · {inner}" if inner else src["name"],
            "source_id": sid,
            "source_type": stype,
            "tier": tier,
            "credibility": src["credibility"],
            "tag_hint": AIHOT_TAG_HINT.get(it.get("category") or ""),
        })
    return [x for x in items if x["title"] and x["url"]][:cap], False


def fetch_thepaper_list(src, window_start, max_items):
    """澎湃频道页适配器（AIHOT 式"网页内嵌数据"直连，无 RSSHub 依赖）。
    澎湃各频道 list_* 页同构：__NEXT_DATA__ -> props.pageProps.data.list，
    每条带 name / contId / pubTimeLong（epoch 毫秒，绝对时间戳）。"""
    try:
        resp = http_get(src["url"])
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                      resp.text, re.S)
        rows = json.loads(m.group(1))["props"]["pageProps"]["data"]["list"] if m else []
    except Exception as e:
        log(f"  ✗ {src['name']}: 抓取失败 ({e})")
        return [], True
    items = []
    for it in rows:
        title = (it.get("name") or "").strip()
        cont_id = str(it.get("contId") or "")
        ts = it.get("pubTimeLong")
        if not title or not cont_id or not ts:
            continue
        try:
            pub = datetime.fromtimestamp(int(ts) / 1000, tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            continue
        if pub < window_start:
            continue
        items.append({
            "title": title,
            "url": f"https://www.thepaper.cn/newsDetail_forward_{cont_id}",
            "desc": "",
            "time": pub.isoformat(),
            "source": src["name"],
            "source_id": src["id"],
            "source_type": src["source_type"],
            "tier": src.get("tier", "T2"),
            "credibility": src["credibility"],
        })
    items.sort(key=lambda x: x["time"], reverse=True)
    return items[:max_items], False


# ----------------------------------------------------------------
# 1.1 舆论热榜适配器（直连公开接口，无 RSSHub / 无浏览器）
#   热榜词条只作两个用途，本身永不成为新闻条目：
#   ① opinion_pulse 舆论观察模块的 LLM 输入
#   ② co-occurrence 暗排序：与真新闻事件重合时加公众热度 bonus
# ----------------------------------------------------------------

def fetch_weibo_hot(limit=40):
    """微博热搜：genvisitor 两步握手拿访客 cookie（无需登录/浏览器），再取榜单。
    失败返回 []（独立故障域，只丢当天微博信号）。"""
    try:
        sess = requests.Session()
        sess.headers.update({"User-Agent": UA})
        r1 = sess.post("https://passport.weibo.com/visitor/genvisitor",
                       data={"cb": "gen_callback"}, timeout=15)
        m = re.search(r'"tid":"([^"]+)"', r1.text)
        if m:
            sess.get("https://passport.weibo.com/visitor/visitor",
                     params={"a": "incarnate", "t": m.group(1), "w": "2",
                             "c": "095", "cb": "cross_domain"}, timeout=15)
        r2 = sess.get("https://weibo.com/ajax/side/hotSearch",
                      headers={"Referer": "https://weibo.com/"}, timeout=15)
        rows = (r2.json().get("data") or {}).get("realtime") or []
        out = []
        for x in rows:
            w = (x.get("word") or "").strip()
            if not w or x.get("is_ad"):
                continue
            out.append({"platform": "微博", "word": w,
                        "hot": int(x.get("num") or 0),
                        "url": "https://s.weibo.com/weibo?q=" + quote(f"#{w}#")})
        return out[:limit]
    except Exception as e:
        log(f"  ✗ 微博热搜: {e}")
        return []


def fetch_bilibili_hot(limit=30):
    """B站热搜：公开 JSON 接口，无鉴权。失败返回 []（独立故障域）。"""
    try:
        resp = http_get("https://api.bilibili.com/x/web-interface/search/square?limit=30")
        rows = (((resp.json().get("data") or {}).get("trending") or {}).get("list")) or []
        out = []
        for x in rows:
            w = (x.get("keyword") or x.get("show_name") or "").strip()
            if not w:
                continue
            out.append({"platform": "B站", "word": w, "hot": 0,
                        "url": "https://search.bilibili.com/all?keyword=" + quote(w)})
        return out[:limit]
    except Exception as e:
        log(f"  ✗ B站热搜: {e}")
        return []


PULSE_FETCHERS = {"weibo_hot": fetch_weibo_hot, "bilibili_hot": fetch_bilibili_hot}


def fetch_pulse_all(src_cfg):
    """拉全部启用的舆论热榜源。单平台失败只丢该平台，永不抛异常。"""
    pulse = []
    for s in (src_cfg.get("pulse_sources") or []):
        if not s.get("enabled", True):
            continue
        fn = PULSE_FETCHERS.get(s.get("type"))
        if not fn:
            continue
        got = fn()
        if got:
            log(f"  ✓ {s.get('name', s['type'])}: {len(got)} 条热榜词")
        pulse += got
    return pulse


FETCHERS = {"aihot": fetch_aihot, "thepaper_list": fetch_thepaper_list}


def fetch_all(sources, cfg):
    """返回 (items, fetch_stats)。fetch_stats 按源记录条数与抓取是否失败，
    供健康度记录使用。"""
    window_start = datetime.now(timezone.utc) - timedelta(hours=cfg["window_hours"])
    max_items = cfg["max_per_source"]
    results = []
    fetch_stats = {}
    log(f"开始抓取 {len(sources)} 个源（窗口 {cfg['window_hours']} 小时）...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futs = {}
        for src in sources:
            fn = FETCHERS.get(src["type"], fetch_rss)
            futs[pool.submit(fn, src, window_start, max_items)] = src
        for fut in concurrent.futures.as_completed(futs):
            src = futs[fut]
            try:
                items, err = fut.result()
            except Exception as e:
                log(f"  ✗ {src['name']}: {e}")
                items, err = [], True
            fetch_stats[src["id"]] = {"name": src["name"],
                                      "count": len(items), "error": err}
            if items:
                log(f"  ✓ {src['name']}: {len(items)} 条")
            results.extend(items)
    # URL 级去重（同链接完全相同的）
    seen, deduped = set(), []
    for it in results:
        key = it["url"].split("?")[0]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(it)
    log(f"共抓取 {len(results)} 条，URL 去重后 {len(deduped)} 条")
    return deduped, fetch_stats


# ----------------------------------------------------------------
# 2. LLM 客户端
# ----------------------------------------------------------------

class LLM:
    def __init__(self, cfg):
        from openai import OpenAI
        self.client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])
        self.model = cfg["model"]
        self.temperature = cfg.get("temperature", 0.3)
        self.max_retries = cfg.get("max_retries", 3)
        # 供应商专有请求体字段（如 DeepSeek V4 的 thinking 开关），原样透传。
        # 不配置则完全不发，保持对任意 OpenAI 兼容接口的通用性。
        self.extra_body = cfg.get("extra_body") or None

    def json_call(self, system, user):
        """调用并解析 JSON，自动重试"""
        last_err = None
        for attempt in range(self.max_retries):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    messages=[{"role": "system", "content": system},
                              {"role": "user", "content": user}],
                    extra_body=self.extra_body,
                )
                text = resp.choices[0].message.content.strip()
                # 提取 JSON（容忍 ```json 包裹）
                m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
                if m:
                    text = m.group(1).strip()
                start = min([i for i in (text.find("["), text.find("{")) if i >= 0])
                text = text[start:]
                return json.loads(text)
            except Exception as e:
                last_err = e
                log(f"  LLM 调用失败（第{attempt + 1}次）: {e}")
                time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"LLM 调用重试均失败: {last_err}")


# ----------------------------------------------------------------
# 3. 预筛（便宜模型）：丢垃圾，主模型只处理幸存者
# ----------------------------------------------------------------

PREFILTER_SYSTEM = """你是新闻信息流的第一道过滤器。用户给你一批带编号的条目标题。
输出两类编号：
- drop（丢弃）：广告软文、纯营销、促销、招聘、菜谱/生活贴士、纯情绪帖、
  以及明显不属于（AI/互联网科技/财经/社会事件/国际时事）任何一类的内容。拿不准一律不丢。
- soft（软边角料）：本身是真实新闻、但对建立长期判断价值低的轻资讯——
  体育赛事结果/花絮、明星八卦与私生活、猎奇轶闻、纯日抛型热点。
  这类不丢弃（仍可留作长尾），只是打个标记。拿不准算不算边角料的，倾向不标。
只输出 JSON：{"drop": [编号...], "soft": [编号...]}，无对应项输出空数组。"""


def prefilter(llm, items):
    batch_size = 80
    drop, soft = set(), set()
    for bi in range(0, len(items), batch_size):
        batch = items[bi:bi + batch_size]
        lines = [f"[{bi + j}] ({it['source']}) {it['title']}"
                 for j, it in enumerate(batch)]
        try:
            result = llm.json_call(PREFILTER_SYSTEM, "\n".join(lines))
            for i in result.get("drop", []):
                if isinstance(i, int) and bi <= i < bi + len(batch):
                    drop.add(i)
            for i in result.get("soft", []):
                if isinstance(i, int) and bi <= i < bi + len(batch):
                    soft.add(i)
        except Exception as e:
            log(f"  预筛批次失败，该批全部保留: {e}")
    for i in soft:
        if i not in drop:
            items[i]["soft"] = True   # 标记随 item 传递到事件层，用于长尾过滤
    kept = [it for i, it in enumerate(items) if i not in drop]
    n_soft = sum(1 for it in kept if it.get("soft"))
    log(f"预筛：丢弃 {len(drop)} 条，保留 {len(kept)} 条（其中软边角料 {n_soft} 条）")
    return kept


# ----------------------------------------------------------------
# 4. 阶段A：去重聚类 + 分类 + 五维分项打分
# ----------------------------------------------------------------

TRIAGE_SYSTEM = """你是一个严格的新闻编辑，负责筛选每日高质量新闻。
用户会给你一批带编号的新闻条目（标题+简介+来源）。你的任务：
1. 把报道【同一事件】的条目合并成一个事件（去重）
   同一事件 = 同一主体 + 同一具体事实（同一次发布/同一起事故/同一项决定）。
   仅仅主题相同、领域相同、都和 AI 或同一家公司有关，【不算】同一事件，禁止合并。
   拿不准就不合并，宁可各自成事件也不要打包。
   事件标题必须只描述一件事，禁止"X与Y"式拼盘标题。
2. 给每个事件分类：ai(人工智能) / tech(互联网科技) / finance(财经) / society(社会事件) / world(国际政治与时事)
3. 给每个事件打 5 个维度的分项分（各 0-10，不要打总分）：
   - impact     影响面：波及多少人/多大市场/多少行业
   - novelty    新颖性：全新事件=高分；旧闻翻炒、周年回顾、老话题重提=低分
   - substance  实质性：有真实信息增量（数据/决策/事实）=高分；口水、软文、纯观点=低分
   - evidence   佐证强度：官方发布或多个独立来源交叉=高分；单一匿名爆料=低分
   - durability 持续重要性：一周后还重要=高分；日抛型花边=低分
   注意：大佬转发/名人鸡汤 substance 和 durability 必须低；论文没有实验验证时 impact 别打高。
4. 丢弃残余垃圾（广告、花边、无信息量的帖子）

只输出 JSON 数组，每个元素：
{"ids": [条目编号列表，同一事件的都放进来], "category": "ai|tech|finance|society|world",
 "dims": {"impact": 0-10, "novelty": 0-10, "substance": 0-10, "evidence": 0-10, "durability": 0-10},
 "title": "该事件的一句话中文标题"}
被丢弃的条目不要出现在任何事件里。不要输出任何其他文字。"""


def cap_same_source(ids, items, limit=2):
    """一个事件里同一来源最多保留 limit 条——同源 3 条以上几乎必然是
    "快讯打包"式错误聚类，代码层直接拦住。"""
    kept, per_src = [], {}
    for i in ids:
        sid = items[i]["source_id"]
        per_src[sid] = per_src.get(sid, 0) + 1
        if per_src[sid] <= limit:
            kept.append(i)
    return kept


def triage(llm, items):
    """分批聚类打分，返回事件列表"""
    batch_size = 50
    events = []
    for bi in range(0, len(items), batch_size):
        batch = items[bi:bi + batch_size]
        lines = []
        for j, it in enumerate(batch):
            idx = bi + j
            lines.append(f"[{idx}] ({it['source']}|{TYPE_NAMES[it['source_type']]}|{it['tier']}) "
                         f"{it['title']} —— {it['desc'][:120]}")
        log(f"  阶段A 批次 {bi // batch_size + 1}: {len(batch)} 条")
        result = llm.json_call(TRIAGE_SYSTEM, "\n".join(lines))
        for ev in result:
            # 编号必须落在本批次范围内——模型若返回批内相对编号，
            # 会静默指向其他批次的条目，造成标题与来源错配
            ids = [i for i in ev.get("ids", [])
                   if isinstance(i, int) and bi <= i < bi + len(batch)]
            ids = cap_same_source(ids, items)
            if not ids:
                continue
            raw_dims = ev.get("dims", {}) or {}
            dims = {d: max(0.0, min(10.0, float(raw_dims.get(d, 3)))) for d in DIMS}
            events.append({
                "ids": ids,
                "category": ev.get("category") if ev.get("category") in CATEGORIES else "world",
                "dims": dims,
                "title": ev.get("title", items[ids[0]]["title"]),
            })
    # 跨批次二次去重
    if len(items) > batch_size and len(events) > 1:
        events = merge_events(llm, events, items)
    return events


MERGE_SYSTEM = """下面是一批新闻事件标题（带编号）。有些编号可能描述的是同一事件（来自不同批次）。
只有当两个标题明显描述【同一具体事件】（同一主体+同一事实）时才算重复；
仅主题相近、领域相同不算，拿不准就不合并。
只输出 JSON 数组：需要合并的编号组，如 [[0,5],[2,9,11]]。没有可合并的就输出 []。不要输出其他文字。"""


def merge_events(llm, events, items):
    lines = [f"[{i}] {ev['title']}" for i, ev in enumerate(events)]
    try:
        groups = llm.json_call(MERGE_SYSTEM, "\n".join(lines))
    except Exception:
        return events
    merged_away = set()
    for group in groups:
        group = [g for g in group if isinstance(g, int) and 0 <= g < len(events)]
        if len(group) < 2:
            continue
        primary = group[0]
        for g in group[1:]:
            if g in merged_away or g == primary:
                continue
            # 只吸收来源，维度分保留主事件的——避免错误合并抬高分数
            events[primary]["ids"].extend(events[g]["ids"])
            events[primary]["ids"] = cap_same_source(events[primary]["ids"], items)
            merged_away.add(g)
    result = [ev for i, ev in enumerate(events) if i not in merged_away]
    if merged_away:
        log(f"  跨批次合并了 {len(merged_away)} 个重复事件")
    return result


# ----------------------------------------------------------------
# 5. 评分（代码合成最终分）+ 阈值制精选
# ----------------------------------------------------------------

def score_and_select(events, items, cfg):
    weights = cfg.get("interest_weights", {})
    scoring = cfg.get("scoring", {})
    dim_w = scoring.get("dim_weights", {})
    dim_w = {d: float(dim_w.get(d, 0.2)) for d in DIMS}
    tier_mult = scoring.get("tier_multipliers", {"T1": 1.0, "T1.5": 0.93, "T2": 0.83})
    threshold = int(cfg.get("pick_threshold", 68))

    for ev in events:
        # 事件层级 = 其所有来源中最高的层级（官方/一线优先）
        best_tier = min((items[i]["tier"] for i in ev["ids"]),
                        key=lambda t: TIER_ORDER.get(t, 2))
        ev["tier"] = best_tier
        # 五维加权 -> 重要性
        importance = sum(ev["dims"][d] * dim_w[d] for d in DIMS) / max(sum(dim_w.values()), 1e-6)
        ev["importance"] = importance
        cred = max(items[i]["credibility"] for i in ev["ids"])
        multi_bonus = min(len(set(items[i]["source_id"] for i in ev["ids"])) - 1, 2) * 0.4
        w = float(weights.get(ev["category"], 1.0))
        raw = (0.62 * importance + 0.30 * cred + multi_bonus) * 10 \
            * float(tier_mult.get(best_tier, 0.83)) * w \
            * float(ev.get("interest_mult", 1.0)) \
            * float(ev.get("pulse_mult", 1.0))
        ev["score"] = int(max(5, min(99, round(raw))))
        # 舆论源硬约束：事件的所有来源都是舆论源（无事实/分析源交叉）时，
        # 分数封顶在阈值之下——只能进"更多资讯"，不进精选、不参与保底补位
        ev["opinion_only"] = all(items[i]["source_type"] == "opinion"
                                 for i in ev["ids"])
        if ev["opinion_only"]:
            ev["score"] = min(ev["score"], threshold - 1)

    events.sort(key=lambda e: e["score"], reverse=True)
    pick_min = int(cfg.get("pick_min", 8))
    pick_max = int(cfg.get("pick_max", 24))
    min_per = cfg.get("min_per_category", 2)

    eligible = [e for e in events if e["score"] >= threshold]
    rest = [e for e in events if e["score"] < threshold]
    # 纯舆论源事件不参与任何补位，只能留在"更多资讯"
    backfill = [e for e in rest if not e.get("opinion_only")]

    picked = []
    # 五类保底：优先从过线的里拿，每类不足再从线下最高分补
    for cat in CATEGORIES:
        cat_pool = ([e for e in eligible if e["category"] == cat] +
                    [e for e in backfill if e["category"] == cat])
        for e in cat_pool[:min_per]:
            if e not in picked:
                picked.append(e)
    # 过线的按分补进来
    for e in eligible:
        if len(picked) >= pick_max:
            break
        if e not in picked:
            picked.append(e)
    # 不足保底条数时，从线下补齐
    if len(picked) < pick_min:
        for e in backfill:
            if len(picked) >= pick_min:
                break
            if e not in picked:
                picked.append(e)
    picked = sorted(picked, key=lambda e: e["score"], reverse=True)[:pick_max]

    # 单类精选上限（config max_per_category；2026-07-11 翻案仅对 ai 启用）：
    # 该类只留最高分 N 条，超限的高分事件降级——events 按分排序，它们会
    # 自然落到"更多资讯"头部，不丢失。腾出的位置从线下补齐到保底条数。
    max_per_cat = cfg.get("max_per_category") or {}
    if max_per_cat:
        kept, counts = [], {}
        for e in picked:
            cat = e["category"]
            counts[cat] = counts.get(cat, 0) + 1
            cap = max_per_cat.get(cat)
            if cap is not None and counts[cat] > int(cap):
                continue
            kept.append(e)
        if len(kept) < len(picked):
            log(f"  单类上限：{len(picked) - len(kept)} 条超限事件降级到更多资讯")
            picked = kept
            if len(picked) < pick_min:
                for e in backfill:
                    if len(picked) >= pick_min:
                        break
                    cap = max_per_cat.get(e["category"])
                    n_cat = sum(1 for p in picked if p["category"] == e["category"])
                    if e in picked or (cap is not None and n_cat >= int(cap)):
                        continue
                    picked.append(e)
                picked = sorted(picked, key=lambda e: e["score"], reverse=True)

    over = sum(1 for e in picked if e["score"] >= threshold)
    log(f"  阈值 {threshold} 分：过线 {len(eligible)} 个事件，精选 {len(picked)} 条（其中过线 {over}）")

    # 长尾过滤：整条事件的来源都被预筛标为软边角料时，不进"更多资讯"
    # （精选不受影响——上面已选完；软事件即便分高也只是被挡在长尾外）
    for ev in events:
        ev["soft"] = bool(ev["ids"]) and all(items[i].get("soft") for i in ev["ids"])
    remaining = [e for e in events if e not in picked and not e.get("soft")]
    n_soft = sum(1 for e in events if e.get("soft") and e not in picked)
    if n_soft:
        log(f"  长尾过滤：{n_soft} 个软边角料事件挡在更多资讯外")
    secondary = remaining[:cfg["secondary_count"]]
    return picked, secondary


# ----------------------------------------------------------------
# 5. 阶段B：精选深加工
# ----------------------------------------------------------------

ENRICH_SYSTEM = """你是资深新闻主编，为个人读者的"每日信息驾驶舱"加工精选新闻。
用户给你若干事件，每个事件附带一条或多条原始报道（标题+简介+来源）。
若给出了【读者兴趣画像】，请据此写 significance；没有画像则 significance 输出空字符串。
对每个事件输出：
- title: 精炼中文标题（≤30字，信息完整，不标题党）
- summary: 一句话事实摘要（≤70字，只说发生了什么，含关键数字）
- why: 为什么重要（≤80字，说清影响面和利害关系）
- context: 背景与机制（≤60字，交代来龙去脉或它反映的运行逻辑，帮读者理解为什么会这样，没有可写就留空）
- significance: 对我的意义（≤60字）。优先结合【读者兴趣画像】里的"学习参考系"段（兼容旧"我的处境"段），给一个学习路线导向的具体参考：该补什么概念、读什么文档/论文、试什么工具、或观察什么能力趋势。要具体到能立刻行动，禁止"值得关注""可以了解一下"这类空话；与读者学习参考系无可操作关联就留空（宁空毋凑）
- watch: 后续关注点（≤60字，接下来看什么信号/节点）
- claims: 2-4 条关键结论，每条包含 text、kind 和 source_indexes。kind 只能是 fact、analysis、uncertain；source_indexes 对应输入来源前的编号，无直接来源时留空数组
{detail_field}- status: 事件状态，只能是这四个之一：
    已确认（官方发布或多个独立可信来源证实）
    发展中（事件仍在进行，信息还在更新）
    有争议（各方说法明显冲突）
    仅传言（单一来源爆料，未获证实）
- tags: 从下面的词表里选 1-2 个最贴切的主题标签，只能用词表里的词，不得自创：
    {tag_list}

只输出 JSON 数组，每个元素：
{{"idx": 事件编号, "title": "...", "summary": "...", "why": "...", "context": "...", "significance": "...", "watch": "...", "claims": [{{"text":"...","kind":"fact","source_indexes":[0]}}]{detail_json}, "status": "...", "tags": ["..."]}}
不要输出任何其他文字。"""


def sanitize_claims(raw_claims, source_names):
    """规范关键结论，把 LLM 的 source_indexes 立即解析为来源名。
    输出 sources 存名字而非索引：build_item 会对来源重排去重，
    索引出了 enrich 这一层就没有稳定含义，存名字才不会张冠李戴。"""
    if not isinstance(raw_claims, list):
        return []
    claims = []
    for raw in raw_claims[:4]:
        if not isinstance(raw, dict):
            continue
        text = str(raw.get("text", "")).strip()[:120]
        if not text:
            continue
        kind = raw.get("kind")
        if kind not in {"fact", "analysis", "uncertain"}:
            kind = "uncertain"
        indexes = raw.get("source_indexes")
        if not isinstance(indexes, list):
            indexes = []
        names = list(dict.fromkeys(
            source_names[i] for i in indexes
            if isinstance(i, int) and 0 <= i < len(source_names)
        ))
        claims.append({"text": text, "kind": kind, "sources": names})
    return claims


def enrich(llm, picked, items, cfg, profile_text=""):
    tag_vocab = [str(t) for t in (cfg.get("topic_tags") or [])]
    tag_set = set(tag_vocab)
    dcfg = cfg.get("detail") or {}
    detail_on = dcfg.get("enabled", True)
    detail_chars = int(dcfg.get("max_chars", 600) or 600)
    detail_field = (
        f"- detail: 中文长叙述（约 {detail_chars} 字以内，2-4 段自然行文，段间空行，不用小标题；"
        "按\"背景→具体发生了什么→为什么重要→接下来看什么\"讲清整件事，让没读过原文的人也能看懂；"
        "严格基于所给原始报道，不得编造原文没有的事实/数字/引语；素材不足就写多少算多少，宁短毋凑）\n"
    ) if detail_on else ""
    detail_json = ', "detail": "..."' if detail_on else ""
    system = ENRICH_SYSTEM.format(
        tag_list="、".join(tag_vocab) if tag_vocab else "（词表为空，tags 输出空数组）",
        detail_field=detail_field, detail_json=detail_json)
    prof_block = ""
    if profile_has_content(profile_text):
        prof_block = "【读者兴趣画像】\n" + profile_text.strip() + "\n\n"
    batch_size = 6
    for bi in range(0, len(picked), batch_size):
        batch = picked[bi:bi + batch_size]
        blocks = []
        for j, ev in enumerate(batch):
            srcs = []
            for source_index, i in enumerate(ev["ids"][:4]):
                it = items[i]
                srcs.append(f"  - [{source_index}] [{it['source']}|{TYPE_NAMES[it['source_type']]}] "
                            f"{it['title']}：{it['desc'][:200]}")
            hints = list(dict.fromkeys(items[i].get("tag_hint") for i in ev["ids"]
                                       if items[i].get("tag_hint") in tag_set))
            hint_line = ("\n  （来源分类提示，若贴切请优先选为标签："
                         + "、".join(hints) + "）") if hints else ""
            blocks.append(f"事件[{bi + j}] {ev['title']}\n" + "\n".join(srcs) + hint_line)
        log(f"  阶段B 批次 {bi // batch_size + 1}: {len(batch)} 个事件")
        result = llm.json_call(system, prof_block + "【今日事件】\n" + "\n\n".join(blocks))
        for r in result:
            k = r.get("idx")
            if not isinstance(k, int) or not (0 <= k < len(picked)):
                continue
            ev = picked[k]
            ev["title"] = r.get("title", ev["title"])
            ev["summary"] = r.get("summary", "")
            ev["why"] = r.get("why", "")
            ev["context"] = str(r.get("context", ""))[:80]
            ev["significance"] = str(r.get("significance", ""))[:70]
            ev["watch"] = r.get("watch", "")
            ev["claims"] = sanitize_claims(
                r.get("claims"), [items[i]["source"] for i in ev["ids"][:4]])
            if detail_on:
                ev["detail"] = str(r.get("detail", "")).strip()[:detail_chars + 200]
            ev["status"] = r.get("status") if r.get("status") in STATUS_SET else "发展中"
            raw_tags = r.get("tags") or []
            if not isinstance(raw_tags, list):
                raw_tags = []
            tags = [t for t in raw_tags if t in tag_set]
            # 兜底：AI HOT 携带的分类提示（研究论文/技巧观点等）优先入选，防止被淹没
            for h in (items[i].get("tag_hint") for i in ev["ids"]):
                if h in tag_set and h not in tags:
                    tags.insert(0, h)
            ev["tags"] = tags[:2]
    return picked


BRIEF_SYSTEM = """你是新闻主编。用户给你今天的条目列表（每条带 id、类目、标题、可能有要点）。
你的任务是替读者"拼主线"：把相关的条目归拢成今天的 2-3 条主线，让读者一眼看懂今天的世界在发生什么。
输出 JSON：
{"synthesis": "一句话总纲，≤60字，概括今天整体格局",
 "themes": [{"title": "主线名，≤12字", "one_liner": "这条主线的一句综合，≤50字",
             "member_ids": ["属于这条主线的条目 id，2个及以上"]}]}
规则：
- themes 最多 3 条，宁缺毋滥；每条主线必须有 ≥2 个成员 id（单个孤立事件不算主线，除非是压倒性头条可破例给 1 个）。
- member_ids 只能从用户给出的 id 里选，禁止自造 id；一条可以跨类目（如极端天气可同时含国际和社会的条目）。
- 今天若确实没有能归拢的主线，themes 给空数组，synthesis 照常写。
只输出 JSON，不要其他文字。"""


def write_brief(llm, picked, secondary=None):
    """产出结构化今日主线：返回 (synthesis, themes)。
    themes 里的 member_ids 用最终输出 id（pick-N/more-N），与 event_to_item 保持一致。"""
    entries = ([("pick", e) for e in picked] +
               [("more", e) for e in (secondary or [])])
    id_of = {}
    lines = []
    for tier, e in entries:
        _id = f"{tier}-{e['ids'][0]}"
        id_of[_id] = e
        extra = f" — {e.get('why', '')}" if e.get("why") else ""
        lines.append(f"[{_id}] ({CAT_NAMES.get(e['category'], e['category'])}) {e['title']}{extra}")
    valid = set(id_of)
    try:
        result = llm.json_call(BRIEF_SYSTEM, "\n".join(lines))
        synthesis = str(result.get("synthesis", "")).strip()[:80] if isinstance(result, dict) else ""
        themes = []
        for t in (result.get("themes", []) if isinstance(result, dict) else []):
            if not isinstance(t, dict):
                continue
            members = [m for m in (t.get("member_ids") or []) if m in valid]
            members = list(dict.fromkeys(members))   # 去重保序
            if not members:
                continue
            themes.append({
                "title": str(t.get("title", "")).strip()[:14],
                "one_liner": str(t.get("one_liner", "")).strip()[:60],
                "member_ids": members[:8],
            })
            if len(themes) >= 3:
                break
        return synthesis, themes
    except Exception as e:
        log(f"  导语/主线生成失败: {e}")
        return "", []


# ----------------------------------------------------------------
# 5.5 跨天事件登记表：今日精选与历史活跃事件的延续性匹配
# ----------------------------------------------------------------

EVENT_MATCH_SYSTEM = """你负责维护跨天新闻事件登记表。输入两组条目：
【登记表】正在追踪的活跃事件（编号 R0、R1…，含最近一次进展摘要和日期）
【今日】今天的精选事件（编号 T0、T1…）
找出今日事件中哪些是登记表某事件的【后续进展】：
同一主体 + 同一条持续发展的具体事件线（同一场冲突的后续、同一起收购案的新进展、同一次发布的后续反应）。
仅主题相似、领域相同、或只是涉及同一家公司的不同事情，都【不算】。
类别(category)不同的禁止匹配。拿不准就不匹配。
只输出 JSON：{"matches":[{"today":数字,"registry":数字}]}；没有匹配输出 {"matches":[]}。
不要输出任何其他文字。"""


def load_registry(data_dir):
    """读 events.json；不存在或损坏时返回空登记表（冷启动）。"""
    f = data_dir / "events.json"
    if f.exists():
        try:
            reg = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(reg.get("events"), list):
                return reg
            log("  events.json 结构异常，重建")
        except Exception as e:
            log(f"  events.json 读取失败，重建: {e}")
    return {"version": 1, "events": []}


def match_events_llm(llm, active_events, picked):
    """LLM 匹配今日精选与活跃事件，返回 [(today_idx, registry_idx), ...]。
    任何异常返回 None，调用方视为"今日全部按新事件处理"。"""
    reg_lines = []
    for i, e in enumerate(active_events):
        last = e["history"][-1] if e.get("history") else {}
        reg_lines.append(f"[R{i}] ({e.get('category', '')}) {e.get('title', '')} ｜ "
                         f"最近进展 {e.get('last_seen', '')}: {str(last.get('summary', ''))[:100]}")
    today_lines = []
    for j, ev in enumerate(picked):
        today_lines.append(f"[T{j}] ({ev.get('category', '')}) {ev.get('title', '')} ｜ "
                           f"{str(ev.get('summary', ''))[:100]}")
    user = "【登记表】\n" + "\n".join(reg_lines) + "\n\n【今日】\n" + "\n".join(today_lines)
    try:
        result = llm.json_call(EVENT_MATCH_SYSTEM, user)
        matches = result.get("matches", []) if isinstance(result, dict) else []
        pairs, seen_today, seen_reg = [], set(), set()
        for m in matches:
            try:
                t, r = int(m["today"]), int(m["registry"])
            except Exception:
                continue
            if not (0 <= t < len(picked) and 0 <= r < len(active_events)):
                continue
            if t in seen_today or r in seen_reg:
                continue
            # 同类目硬校验：LLM 违规跨类匹配直接丢弃
            if picked[t].get("category") != active_events[r].get("category"):
                continue
            seen_today.add(t)
            seen_reg.add(r)
            pairs.append((t, r))
        return pairs
    except Exception as e:
        log(f"  事件匹配调用失败，今日全部按新事件处理: {e}")
        return None


def update_registry(registry, picked, pairs, active_events, date_str, cfg):
    """纯函数：把今日精选写入登记表（续接或新建），归档与剪枝，
    并回填 picked 的 event_id / day_count / history_prev。
    pairs 为 None（LLM 失败）时全部按新事件处理。"""
    evcfg = cfg.get("events") or {}
    archive_days = int(evcfg.get("archive_days", 7))
    prune_days = int(evcfg.get("prune_archived_days", 60))
    today = datetime.strptime(date_str, "%Y-%m-%d")
    events = registry.setdefault("events", [])

    # 同日重跑幂等：先清掉本日已写入的进展；本日早前一跑新建的事件随之整个移除
    for e in events:
        e["history"] = [h for h in e.get("history", []) if h.get("date") != date_str]
    events[:] = [e for e in events if e["history"]]
    for e in events:
        e["last_seen"] = e["history"][-1]["date"]

    matched = {}
    for t, r in (pairs or []):
        if 0 <= t < len(picked) and 0 <= r < len(active_events):
            tgt = active_events[r]
            if tgt.get("history"):  # 被幂等清理移除的目标不再续接
                matched[t] = tgt

    for idx, ev in enumerate(picked):
        entry = {"date": date_str, "title": ev.get("title", ""),
                 "summary": ev.get("summary", ""), "news_status": ev.get("status", "")}
        tgt = matched.get(idx)
        if tgt is None:
            # 哈希掺入首条原始条目索引（当天唯一），防同日同标题撞出重复 event_id
            seed = f"{ev.get('title', '')}|{(ev.get('ids') or [idx])[0]}"
            eid = "evt-{}-{}".format(
                date_str.replace("-", ""),
                hashlib.sha1(seed.encode("utf-8")).hexdigest()[:6])
            tgt = {"event_id": eid, "title": ev.get("title", ""),
                   "category": ev.get("category", ""), "status": "active",
                   "pinned": False, "first_seen": date_str, "last_seen": date_str,
                   "history": [entry]}
            events.append(tgt)
        else:
            tgt["history"].append(entry)
            tgt["last_seen"] = date_str
            tgt["title"] = ev.get("title", tgt.get("title", ""))
        ev["event_id"] = tgt["event_id"]
        ev["day_count"] = len({h["date"] for h in tgt["history"]})
        ev["history_prev"] = [h for h in tgt["history"] if h["date"] != date_str][-7:]

    def days_since(d):
        try:
            return (today - datetime.strptime(d, "%Y-%m-%d")).days
        except Exception:
            return 10 ** 6

    for e in events:
        if e.get("status") == "active" and days_since(e.get("last_seen", "")) > archive_days:
            e["status"] = "archived"
    events[:] = [e for e in events
                 if not (e.get("status") == "archived"
                         and days_since(e.get("last_seen", "")) > prune_days)]
    return registry


def track_events(llm, picked, date_str, cfg, secondary=None, feedback=None):
    """编排：读登记表 -> 应用钉选 -> 组活跃匹配池 -> LLM 匹配 -> 更新 ->
    钉选事件与"更多资讯"补匹配 -> 写回。返回登记表供输出使用。"""
    data_dir = Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    registry = load_registry(data_dir)
    pinned_changed = apply_pins(registry, feedback or [])
    if pinned_changed:
        log(f"  钉选状态更新：{pinned_changed} 个事件")
    evcfg = cfg.get("events") or {}
    window = int(evcfg.get("match_window_days", 14))
    today = datetime.strptime(date_str, "%Y-%m-%d")

    def days_since(d):
        try:
            return (today - datetime.strptime(d, "%Y-%m-%d")).days
        except Exception:
            return 10 ** 6

    # 活跃池：active 且 last_seen 在窗口内；只含"今天之前"就有历史的事件，
    # 排除本日早前一跑新建的条目（同日重跑时它们会被幂等清理重建）
    active = [e for e in registry["events"]
              if e.get("status") == "active"
              and 0 <= days_since(e.get("last_seen", "")) <= window
              and any(h.get("date") != date_str for h in e.get("history", []))]

    pairs = match_events_llm(llm, active, picked) if (active and picked) else []
    update_registry(registry, picked, pairs, active, date_str, cfg)

    # 钉选事件今天没进精选时，尝试与"更多资讯"补匹配续接进展，
    # 保证追踪中的事件不因分数不过线而断档
    if secondary:
        pinned_stale = [e for e in registry["events"]
                        if e.get("pinned") and e.get("status") == "active"
                        and e.get("last_seen") != date_str
                        and any(h.get("date") != date_str for h in e.get("history", []))]
        if pinned_stale:
            sec_pairs = match_events_llm(llm, pinned_stale, secondary) or []
            for t, r in sec_pairs:
                sev, tgt = secondary[t], pinned_stale[r]
                tgt["history"].append({"date": date_str, "title": sev.get("title", ""),
                                       "summary": sev.get("summary") or sev.get("title", ""),
                                       "news_status": sev.get("status", "")})
                tgt["last_seen"] = date_str
            if sec_pairs:
                log(f"  钉选补匹配：{len(sec_pairs)} 个钉选事件从'更多资讯'续上进展")

    (data_dir / "events.json").write_text(
        json.dumps(registry, ensure_ascii=False, indent=1), encoding="utf-8")
    n_cont = sum(1 for ev in picked if ev.get("day_count", 0) >= 2)
    log(f"  事件登记表：活跃 {len(active)}，续接 {n_cont}，登记总数 {len(registry['events'])}")
    return registry


# ----------------------------------------------------------------
# 5.6 偏好学习：消费 feedback.json / read_later.json
#   - track/untrack  -> events.json 钉选
#   - 来源质量低      -> 运行时降低该源条目可信度（不改 sources.yaml）
#   - 其余反馈+稍后读 -> LLM 蒸馏进 interest_profile.md（明文，可手改）
#   - 画像            -> 对当日事件打"兴趣契合分"，换算成分数乘数
# ----------------------------------------------------------------

PROFILE_MARKER_RE = re.compile(r"<!--\s*last_feedback_ts:\s*([^>]*?)\s*-->")
PROFILE_DEFAULT = """# 兴趣画像
<!-- last_feedback_ts: 1970-01-01T00:00:00Z -->

本文件由管线自动蒸馏页面反馈生成，也可以直接手改（增删行都会保留，
除非与后续反馈明确矛盾）。要点行以"- "开头，管线据此判断画像是否为空。

## 学习参考系
（暂无，可手写：长期学习方向 / 当前能力栈 / 希望积累的判断力 / 资讯转化偏好。此段蒸馏时受保护、不被自动改写）

## 更关注
（暂无）

## 不关注
（暂无）

## 来源印象
（暂无）
"""

PROFILE_SYSTEM = """你维护一份个人新闻"兴趣画像"文档（markdown）。
输入：当前画像全文 + 一批新的用户反馈（动作、条目标题、类目、理由、备注、来源）和新收藏的稍后读标题。
任务：把新反馈蒸馏进画像，输出更新后的画像全文。
规则：
- 保持三个小节：## 更关注 / ## 不关注 / ## 来源印象；每节内是要点行，每行以"- "开头（一行一个偏好，≤25字）
- 若输入含"## 学习参考系"段，原样保留、不要改写（那是用户手写的长期学习参考系）
- 若输入仍含旧"## 我的处境"段，也原样保留、不要改写
- 已有要点行是用户认可或手写的，除非与新反馈明确矛盾，否则原样保留
- 归纳到主题/领域层面（如"- 航天工程细节"），不要罗列具体新闻标题
- 同一偏好被反复印证时可在行尾标注 (xN) 表示强度
- 全文不超过 40 行；小节为空时写"（暂无）"
只输出画像 markdown 全文，不要解释，不要代码块包裹。"""

FIT_SYSTEM = """根据用户的兴趣画像，为每条新闻事件打"兴趣契合分"0-10：
10 = 画像明确表示高度关注的主题；5 = 画像未提及或中性；0 = 画像明确表示不关注。
画像没提到的一律给 5，不要引申猜测。
只输出 JSON：{"fits":[{"idx":编号,"fit":0-10}]}，不要其他文字。"""

FEEDBACK_ACT_NAMES = {"not_interested": "不感兴趣", "more_like_this": "更关注类似",
                      "low_quality_source": "来源质量低", "track": "继续追踪"}


def load_state_list(data_dir, filename, key):
    """读 feedback.json / read_later.json 里的列表；缺失或损坏一律返回 []。"""
    f = data_dir / filename
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        lst = data.get(key)
        return lst if isinstance(lst, list) else []
    except Exception as e:
        log(f"  {filename} 读取失败，忽略: {e}")
        return []


def source_penalties(feedback, date_str, window_days=90, step=0.1, floor=0.7):
    """"来源质量低"反馈 -> {来源名: 可信度乘数}。
    近 window_days 天内每个"有反馈的自然日"记一次，每次降 step，最低 floor。"""
    today = datetime.strptime(date_str, "%Y-%m-%d")
    strikes = {}
    for e in feedback:
        if e.get("action") != "low_quality_source" or not e.get("source"):
            continue
        day = str(e.get("ts", ""))[:10]
        try:
            if not (0 <= (today - datetime.strptime(day, "%Y-%m-%d")).days <= window_days):
                continue
        except ValueError:
            continue
        strikes.setdefault(str(e["source"]), set()).add(day)
    return {s: round(max(floor, 1 - step * len(days)), 2) for s, days in strikes.items()}


def apply_pins(registry, feedback):
    """track/untrack 反馈 -> 登记表事件 pinned 位（按时间取每个事件最后一次动作）。"""
    by_event = {}
    for e in feedback or []:
        if e.get("action") in ("track", "untrack") and e.get("event_id"):
            by_event.setdefault(e["event_id"], []).append((str(e.get("ts", "")), e["action"]))
    changed = 0
    for ev in registry.get("events", []):
        acts = by_event.get(ev.get("event_id"))
        if not acts:
            continue
        want = max(acts)[1] == "track"
        if bool(ev.get("pinned")) != want:
            ev["pinned"] = want
            changed += 1
    return changed


def profile_has_content(text):
    return any(line.strip().startswith("- ") for line in (text or "").splitlines())


def split_section(text, header):
    """按 '## <header>' 切出该段（含标题行，到下一个 '## ' 或 EOF）。
    返回 (去掉该段的文本, 该段块字符串或 '')。找不到则 (原文, '')。
    用于把用户手写的"学习参考系"等保护段摘出、绕过画像蒸馏 LLM，再原样贴回——
    否则 PROFILE_SYSTEM 全文重写会把它丢掉。"""
    lines = (text or "").splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.strip() == f"## {header}"), None)
    if start is None:
        return text, ""
    end = next((j for j in range(start + 1, len(lines)) if lines[j].startswith("## ")),
               len(lines))
    block = "\n".join(lines[start:end]).rstrip()
    rest = "\n".join(lines[:start] + lines[end:])
    return rest, block


def update_profile(llm, data_dir, feedback, read_later):
    """把 marker 之后的新反馈蒸馏进 interest_profile.md。
    无新反馈不调 LLM；蒸馏失败保留旧画像、不推进 marker。返回画像全文。"""
    data_dir.mkdir(parents=True, exist_ok=True)  # 本函数早于 main 里其他 mkdir 执行
    pf = data_dir / "interest_profile.md"
    try:
        text = pf.read_text(encoding="utf-8") if pf.exists() else PROFILE_DEFAULT
    except Exception:
        text = PROFILE_DEFAULT
    m = PROFILE_MARKER_RE.search(text)
    marker = m.group(1).strip() if m else "1970-01-01T00:00:00Z"

    def newer(ts):
        return isinstance(ts, str) and ts > marker

    fb_new = [e for e in feedback
              if newer(e.get("ts")) and e.get("action") in FEEDBACK_ACT_NAMES
              and not (e.get("action") == "not_interested"
                       and "只是今天不想看" in (e.get("reasons") or [])
                       and not e.get("note"))]
    rl_new = [it for it in read_later if newer(it.get("ts"))]
    if not fb_new and not rl_new:
        if not pf.exists():
            pf.write_text(text, encoding="utf-8")  # 首次落盘默认画像，方便手改
        return text

    fb_lines = []
    for e in fb_new[-80:]:
        parts = [FEEDBACK_ACT_NAMES[e["action"]], f"[{e.get('category', '')}]",
                 str(e.get("title", ""))[:60]]
        if e.get("reasons"):
            parts.append("理由:" + "/".join(str(r) for r in e["reasons"]))
        if e.get("note"):
            parts.append("备注:" + str(e["note"])[:80])
        if e.get("source"):
            parts.append("来源:" + str(e["source"]))
        fb_lines.append(" ｜ ".join(parts))
    rl_lines = [f"[{it.get('category', '')}] {str(it.get('title', ''))[:60]}"
                for it in rl_new[-40:]]
    # 手写参考系段摘出、不进 LLM（LLM 只蒸馏兴趣），蒸馏完再原样贴回。
    # 同时兼容旧的"我的处境"段，避免老画像在全文重写时被冲掉。
    text_for_llm = text
    protected_blocks = []
    for header in ("学习参考系", "我的处境"):
        text_for_llm, block = split_section(text_for_llm, header)
        if block:
            protected_blocks.append(block)
    body = PROFILE_MARKER_RE.sub("", text_for_llm).strip()
    user = ("【当前画像】\n" + body +
            "\n\n【新反馈】\n" + ("\n".join(fb_lines) or "（无）") +
            "\n\n【新收藏的稍后读】\n" + ("\n".join(rl_lines) or "（无）"))
    new_marker = max([str(e.get("ts", "")) for e in fb_new] +
                     [str(it.get("ts", "")) for it in rl_new])
    try:
        resp = llm.client.chat.completions.create(
            model=llm.model, temperature=0.2,
            messages=[{"role": "system", "content": PROFILE_SYSTEM},
                      {"role": "user", "content": user}])
        out = resp.choices[0].message.content.strip()
        out = re.sub(r"^```(?:markdown)?\s*|\s*```$", "", out).strip()
        if "## 更关注" not in out or "## 不关注" not in out:
            raise ValueError("画像输出缺少必需小节")
        out = PROFILE_MARKER_RE.sub("", out).strip()
        for header in ("学习参考系", "我的处境"):
            out, _ = split_section(out, header)  # 去掉 LLM 可能误带的保护段，防重复
        lines = out.splitlines()
        insert_at = 1 if lines and lines[0].startswith("#") else 0
        lines.insert(insert_at, f"<!-- last_feedback_ts: {new_marker} -->")
        if protected_blocks:  # 保护段原样贴回：放在第一个 "## " 小节前（导语之后）
            pos = next((k for k, ln in enumerate(lines) if ln.startswith("## ")), len(lines))
            lines.insert(pos, "\n\n".join(protected_blocks) + "\n")
        new_text = "\n".join(lines).rstrip() + "\n"
        pf.write_text(new_text, encoding="utf-8")
        log(f"  画像已更新：吸收 {len(fb_new)} 条反馈、{len(rl_new)} 条稍后读")
        return new_text
    except Exception as e:
        log(f"  画像蒸馏失败，保留旧画像: {e}")
        return text


def interest_fit(llm, profile_text, events, span=0.30):
    """按画像给事件打契合分，写入 ev['interest_mult'] ∈ [1-span, 1+span]。
    span 由 config 的 scoring.fit_span 控制（默认 0.30，即 ±30%）。
    画像为空或调用失败时不写（默认 1.0）。中性 5 分恰好等于 1.0。"""
    if not events or not profile_has_content(profile_text):
        return
    span = max(0.0, min(0.6, float(span)))
    lines = [f"[{i}] ({CAT_NAMES.get(e.get('category', ''), e.get('category', ''))}) "
             f"{e.get('title', '')}" for i, e in enumerate(events)]
    user = "【兴趣画像】\n" + profile_text + "\n\n【今日事件】\n" + "\n".join(lines)
    try:
        result = llm.json_call(FIT_SYSTEM, user)
        fits = result.get("fits", []) if isinstance(result, dict) else []
        for f_ in fits:
            try:
                i, fit = int(f_["idx"]), float(f_["fit"])
            except Exception:
                continue
            if 0 <= i < len(events):
                fit = max(0.0, min(10.0, fit))
                events[i]["interest_mult"] = round(1.0 + (fit - 5.0) / 5.0 * span, 3)
        n = sum(1 for e in events if e.get("interest_mult", 1.0) != 1.0)
        log(f"  兴趣拟合：{n}/{len(events)} 个事件获得非中性乘数")
    except Exception as e:
        log(f"  兴趣拟合失败，保持中性: {e}")


# ----------------------------------------------------------------
# 5.7 深度阅读频道：独立于新闻管线的长文推荐（阈值制 0-3 篇）
# ----------------------------------------------------------------

DEEP_SYSTEM = """你为个人读者筛选"今天值得花时间深读的长文"。
输入若干候选文章（标题+摘要+来源），可能附带读者的兴趣画像。
给每篇打"深读价值分"0-10，标准：
- 实质密度：有真实信息增量、数据、一手经验，而非口水/热点复读
- 独到洞察：提供新框架、方法论或反直觉结论
- 持久价值：一周后再读仍有价值
显著契合兴趣画像可 +1，明确落在画像"不关注"里的 -2。宁缺毋滥，平庸的给低分。
对每篇输出：
{"idx": 编号, "score": 0-10, "title_zh": "中文标题（中文原题则原样保留，≤30字）",
 "brief": "一句话讲这篇是什么（≤40字）", "why": "为什么值得花时间读（≤60字）",
 "key_points": ["核心观点，最多3条，每条≤60字"], "audience": "适合谁读（≤50字）",
 "takeaway": "读完最该带走的一句话（≤80字）"}
只输出 JSON 数组，不要其他文字。"""


def estimate_read_minutes(item, lang):
    """按 RSS 全文长度估算阅读分钟数（中文 400 字/分，英文 220 词/分），3-60 封顶。"""
    if lang == "zh":
        n = item.get("content_chars") or len(re.sub(r"\s", "", item.get("desc", "")))
        m = n / 400
    else:
        n = item.get("content_words") or len(item.get("desc", "").split())
        m = n / 220
    return max(3, min(60, int(m + 0.999)))


def load_deep_seen(data_dir, date_str, filename="deep_seen.json"):
    """已推荐 URL 滚动表；当日条目剔除（同日重跑幂等：重跑时重新评选）。
    filename 可切换到 papers_seen.json 等，供其他独立频道共用同一去重逻辑。"""
    f = data_dir / filename
    seen = {"version": 1, "urls": {}}
    if f.exists():
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data.get("urls"), dict):
                seen["urls"] = {u: d for u, d in data["urls"].items() if d != date_str}
        except Exception as e:
            log(f"  deep_seen.json 读取失败，重建: {e}")
    return seen


def deep_channel(llm, cfg, date_str, profile_text=""):
    """深读频道编排。独立故障域：任何异常只 log 并返回 []，绝不影响新闻主管线。"""
    try:
        dcfg = cfg.get("deep") or {}
        if not dcfg.get("enabled", False):
            return []
        src_cfg = yaml.safe_load((ROOT / "sources.yaml").read_text(encoding="utf-8"))
        deep_sources = [s for s in (src_cfg.get("deep_sources") or [])
                        if s.get("enabled", True)]
        # deep 源同样支持 {rsshub} 占位符（未配 RSSHUB_BASE 时自动跳过该源）
        deep_sources = resolve_rsshub_sources(deep_sources)
        if not deep_sources:
            return []
        window_start = datetime.now(timezone.utc) - timedelta(
            hours=int(dcfg.get("window_hours", 78)))
        max_per = int(dcfg.get("max_per_source", 5))
        candidates = []
        for s in deep_sources:
            src = dict(s, source_type="analysis", credibility=7)
            fetched, _err = fetch_rss(src, window_start, max_per)
            for it in fetched:
                it["lang"] = s.get("lang", "en")
            candidates += fetched

        data_dir = Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data"
        seen = load_deep_seen(data_dir, date_str)
        candidates = [c for c in candidates if c["url"] not in seen["urls"]]
        log(f"  深读候选：{len(candidates)} 篇（去重后）")
        if not candidates:
            return []

        lines = [f"[{i}] ({c['source']}/{c['lang']}) {c['title']}\n    {c['desc'][:200]}"
                 for i, c in enumerate(candidates)]
        user = ""
        if profile_has_content(profile_text):
            user = "【兴趣画像】\n" + profile_text + "\n\n"
        user += "【候选文章】\n" + "\n".join(lines)
        result = llm.json_call(DEEP_SYSTEM, user)

        scored = []
        for r in (result if isinstance(result, list) else []):
            try:
                i, score = int(r["idx"]), float(r["score"])
            except Exception:
                continue
            if 0 <= i < len(candidates):
                scored.append((max(0.0, min(10.0, score)), i, r))
        threshold = float(dcfg.get("pick_threshold", 7))
        pick_max = int(dcfg.get("pick_max", 3))
        scored = sorted([t for t in scored if t[0] >= threshold], key=lambda t: -t[0])

        deep, used = [], set()
        for score, i, r in scored:
            if len(deep) >= pick_max:
                break
            if i in used:
                continue
            used.add(i)
            c = candidates[i]
            deep.append({
                "id": "deep-" + hashlib.sha1(c["url"].encode("utf-8")).hexdigest()[:8],
                "title": c["title"],
                "title_zh": str(r.get("title_zh") or c["title"])[:40],
                "url": c["url"],
                "source": c["source"],
                "lang": c["lang"],
                "brief": str(r.get("brief", ""))[:60],
                "why": str(r.get("why", ""))[:90],
                "key_points": [str(x).strip()[:80] for x in (r.get("key_points") or [])
                               if str(x).strip()][:3],
                "audience": str(r.get("audience", "")).strip()[:70],
                "takeaway": str(r.get("takeaway", "")).strip()[:100],
                "score": int(score),
                "read_minutes": estimate_read_minutes(c, c["lang"]),
            })

        for d in deep:
            seen["urls"][d["url"]] = date_str
        prune = int(dcfg.get("seen_keep_days", 60))
        today = datetime.strptime(date_str, "%Y-%m-%d")

        def _keep(dt):
            try:
                return (today - datetime.strptime(dt, "%Y-%m-%d")).days <= prune
            except ValueError:
                return False

        seen["urls"] = {u: dt for u, dt in seen["urls"].items() if _keep(dt)}
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "deep_seen.json").write_text(
            json.dumps(seen, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"  深读推荐：{len(deep)} 篇（阈值 {threshold} 分）")
        return deep
    except Exception as e:
        log(f"  深读频道失败（不影响主管线）: {e}")
        return []


# ----------------------------------------------------------------
# 5.1 今日论文频道（Hugging Face Daily Papers）
#   独立于新闻管线：抓 HF 每日社区精选论文，LLM 按读者学习坐标挑 3-4 篇，
#   产出"该读什么/该补什么概念"。论文不是新闻——不进精选评分、自成一块。
#   与深读频道同为独立故障域：任何异常只 log 并返回 []。
# ----------------------------------------------------------------

HF_PAPERS_API = "https://huggingface.co/api/daily_papers"

PAPERS_SYSTEM = """你为一位**前端/全栈开发者**从每天的 arXiv 热门论文里挑"值得他花时间读的"。
读者不是研究员，学习坐标是：前端/全栈工程、AI 工具应用、数据与自动化管线、计算机基础。
他要的是：该补什么概念、能不能用得上、有没有可跑的代码/工具，而非纯理论推导。
输入若干候选论文（标题+摘要+点赞数+是否带开源代码），可能附带读者兴趣画像。
给每篇打"该读价值分"0-10，标准：
- 可落地：方法/工具能迁移到工程或学习实践，带开源代码/项目页的加分
- 认知增量：讲清一个值得掌握的概念、框架或反直觉结论，能转成学习路线
- 贴合坐标：越靠近读者学习方向越高；纯数学/理论且离工程很远的压低
社区点赞高只是线索、不是理由，平庸或过于窄众的仍给低分。宁缺毋滥。
对每篇输出：
{"idx": 编号, "score": 0-10, "title_zh": "中文标题（≤30字）",
 "brief": "一句话这篇做了什么（≤40字）",
 "why": "为什么值得读：该补什么概念/能不能用上（≤60字）",
 "contribution": "核心贡献（≤80字）", "evidence": "主要证据或实验（≤80字）",
 "limitations": "适用边界或局限（≤80字）", "takeaway": "对个人学习最有用的结论（≤80字）"}
只输出 JSON 数组，不要其他文字。"""


def fetch_hf_papers(date_str, days=2):
    """抓 HF Daily Papers（社区精选 + 点赞）。合并 date_str 及往前 days-1 天，
    按 arxiv id 去重，返回规范化候选 list。抓取失败该日跳过、不抛（独立故障域）。"""
    base = datetime.strptime(date_str, "%Y-%m-%d")
    merged = {}
    for d in range(max(1, days)):
        day = (base - timedelta(days=d)).strftime("%Y-%m-%d")
        try:
            resp = http_get(f"{HF_PAPERS_API}?date={day}", timeout=25)
            data = resp.json()
        except Exception as e:
            log(f"  HF Papers {day} 抓取失败: {e}")
            continue
        if not isinstance(data, list):
            continue
        for it in data:
            p = it.get("paper") or {}
            aid = p.get("id")
            if not aid or aid in merged:
                continue
            title = (it.get("title") or p.get("title") or "").strip()
            if not title:
                continue
            merged[aid] = {
                "title": title,
                "url": f"https://huggingface.co/papers/{aid}",
                "arxiv_id": aid,
                "summary": (p.get("ai_summary") or it.get("summary")
                            or p.get("summary") or "").strip(),
                "upvotes": int(p.get("upvotes") or 0),
                "comments": int(it.get("numComments") or 0),
                "has_code": bool(p.get("githubRepo")),
            }
    return list(merged.values())


def papers_channel(llm, cfg, date_str, profile_text=""):
    """今日论文频道编排。独立故障域：任何异常只 log 并返回 []，绝不影响主管线。"""
    try:
        pcfg = cfg.get("papers") or {}
        if not pcfg.get("enabled", False):
            return []
        candidates = fetch_hf_papers(date_str, days=int(pcfg.get("lookback_days", 2)))
        data_dir = Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data"
        seen = load_deep_seen(data_dir, date_str, "papers_seen.json")
        candidates = [c for c in candidates if c["url"] not in seen["urls"]]
        # 点赞预排序 + 截断，控 token（候选本就是社区精选，40+ 篇取头部足够）
        candidates.sort(key=lambda c: (-c["upvotes"], -c["comments"]))
        candidates = candidates[:int(pcfg.get("max_candidates", 30))]
        log(f"  论文候选：{len(candidates)} 篇（去重 + 预排序后）")
        if not candidates:
            return []

        lines = []
        for i, c in enumerate(candidates):
            code = "，带开源代码" if c["has_code"] else ""
            lines.append(f"[{i}] (👍{c['upvotes']}{code}) {c['title']}\n    {c['summary'][:220]}")
        user = ""
        if profile_has_content(profile_text):
            user = "【兴趣画像】\n" + profile_text + "\n\n"
        user += "【候选论文】\n" + "\n".join(lines)
        result = llm.json_call(PAPERS_SYSTEM, user)

        scored = []
        for r in (result if isinstance(result, list) else []):
            try:
                i, score = int(r["idx"]), float(r["score"])
            except Exception:
                continue
            if 0 <= i < len(candidates):
                scored.append((max(0.0, min(10.0, score)), i, r))
        threshold = float(pcfg.get("pick_threshold", 7))
        pick_max = int(pcfg.get("pick_max", 4))
        scored = sorted([t for t in scored if t[0] >= threshold], key=lambda t: -t[0])

        papers, used = [], set()
        for score, i, r in scored:
            if len(papers) >= pick_max:
                break
            if i in used:
                continue
            used.add(i)
            c = candidates[i]
            papers.append({
                "id": "paper-" + c["arxiv_id"],
                "title": c["title"],
                "title_zh": str(r.get("title_zh") or c["title"])[:40],
                "url": c["url"],
                "arxiv_id": c["arxiv_id"],
                "brief": str(r.get("brief", ""))[:60],
                "why": str(r.get("why", ""))[:90],
                "contribution": str(r.get("contribution", "")).strip()[:100],
                "evidence": str(r.get("evidence", "")).strip()[:100],
                "limitations": str(r.get("limitations", "")).strip()[:100],
                "takeaway": str(r.get("takeaway", "")).strip()[:100],
                "score": int(score),
                "upvotes": c["upvotes"],
                "has_code": c["has_code"],
            })

        for p in papers:
            seen["urls"][p["url"]] = date_str
        prune = int(pcfg.get("seen_keep_days", 45))
        today = datetime.strptime(date_str, "%Y-%m-%d")

        def _keep(dt):
            try:
                return (today - datetime.strptime(dt, "%Y-%m-%d")).days <= prune
            except ValueError:
                return False

        seen["urls"] = {u: dt for u, dt in seen["urls"].items() if _keep(dt)}
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "papers_seen.json").write_text(
            json.dumps(seen, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"  今日论文：{len(papers)} 篇（阈值 {threshold} 分）")
        return papers
    except Exception as e:
        log(f"  今日论文频道失败（不影响主管线）: {e}")
        return []


# ----------------------------------------------------------------
# 5.2 舆论观察（微博/B站热榜 → 传播机制解读）+ co-occurrence 暗排序
#   热榜词条永不成为新闻条目：只作 LLM 输入与排序信号。
# ----------------------------------------------------------------

OPINION_SYSTEM = """你为一位关注"舆论机制"的读者做每日舆论观察。输入是今天微博/B站的热榜词条。
读者不想看热榜本身，想理解传播现象：一件事为什么热、映射什么群体情绪、什么平台机制在起作用。
从候选里挑 2-3 个真正值得说的（有公共意义/群体情绪/平台机制可讲的）：
- 纯明星八卦、综艺、剧集、体育赛果本身一律跳过，除非其传播方式本身反映平台机制
- 优先：社会公共事件、青年/教育/就业议题、科技产品争议、梗与亚文化破圈现象
对每个输出：
{"idx": 编号, "title": "话题的中性转述（≤24字）",
 "why_hot": "为什么热：事件是什么+传播动力（≤60字）",
 "emotion": "映射的群体情绪（≤40字）",
 "mechanism": "平台机制的作用（算法推流/话题运营/社群结构等，≤40字）"}
拿不准的宁可少挑，一个都不值得说就输出 []。只输出 JSON 数组，不要其他文字。"""


def _cjk_norm(s):
    """匹配用归一化：只留中英数字，去掉标点/空白/emoji。"""
    return re.sub(r"[^0-9A-Za-z一-鿿]", "", s or "")


def _bigrams(s):
    return {s[i:i + 2] for i in range(len(s) - 1)}


def apply_pulse_bonus(events, items, pulse, cfg):
    """co-occurrence 暗排序：热榜词条与事件文本重合 -> 事件最终分乘公众热度 bonus。
    命中判据（宁松勿严，bonus 很温和）：热榜词的任意 4 字连片出现在事件文本里
    （实体名兜底，如"台风巴威"），或热榜词字符二元组被事件文本覆盖率 >= 0.5。
    每事件最多命中一次。返回命中数。"""
    bonus = float((cfg.get("opinion") or {}).get("cooccur_bonus", 1.08))
    if not pulse or bonus <= 1.0:
        return 0
    hits = 0
    for ev in events:
        text = _cjk_norm(ev.get("title", "") + " " + " ".join(
            items[i]["title"] for i in ev.get("ids", []) if 0 <= i < len(items)))
        tb = _bigrams(text)
        for p in pulse:
            wn = _cjk_norm(p["word"])
            if len(wn) < 2:
                continue
            wb = _bigrams(wn)
            if any(wn[i:i + 4] in text for i in range(max(len(wn) - 3, 0))) or \
               (wb and len(wb & tb) / len(wb) >= 0.5):
                ev["pulse_mult"] = bonus
                ev["pulse_word"] = p["word"]
                hits += 1
                break
    return hits


def opinion_pulse(llm, cfg, pulse, profile_text=""):
    """舆论观察编排。独立故障域：任何异常只 log 并返回 []，绝不影响主管线。"""
    try:
        ocfg = cfg.get("opinion") or {}
        if not ocfg.get("enabled", False) or not pulse:
            return []
        cand = pulse[:int(ocfg.get("max_candidates", 50))]
        lines = [f"[{i}] ({p['platform']}) {p['word']}" for i, p in enumerate(cand)]
        user = ""
        if profile_has_content(profile_text):
            user = "【读者兴趣画像】\n" + profile_text + "\n\n"
        user += "【今日热榜】\n" + "\n".join(lines)
        result = llm.json_call(OPINION_SYSTEM, user)

        out, used = [], set()
        pick_max = int(ocfg.get("pick_max", 3))
        for r in (result if isinstance(result, list) else []):
            try:
                i = int(r["idx"])
            except Exception:
                continue
            if not (0 <= i < len(cand)) or i in used or len(out) >= pick_max:
                continue
            used.add(i)
            p = cand[i]
            out.append({
                "id": "op-" + hashlib.sha1(
                    (p["platform"] + p["word"]).encode("utf-8")).hexdigest()[:8],
                "platform": p["platform"],
                "word": p["word"],
                "title": str(r.get("title") or p["word"])[:30],
                "why_hot": str(r.get("why_hot", ""))[:90],
                "emotion": str(r.get("emotion", ""))[:60],
                "mechanism": str(r.get("mechanism", ""))[:60],
                "url": p.get("url", ""),
            })
        log(f"  舆论观察：{len(out)} 条")
        return out
    except Exception as e:
        log(f"  舆论观察失败（不影响主管线）: {e}")
        return []


# ----------------------------------------------------------------
# 6. 输出
# ----------------------------------------------------------------

def event_to_item(ev, items, tier):
    ids = ev["ids"]
    # 主链接：可信度最高的事实源优先
    sorted_ids = sorted(ids, key=lambda i: (
        items[i]["source_type"] != "fact", -items[i]["credibility"]))
    sources = []
    seen_urls = set()
    for i in sorted_ids:
        it = items[i]
        if it["url"] in seen_urls:
            continue
        seen_urls.add(it["url"])
        sources.append({"name": it["source"], "url": it["url"],
                        "type": TYPE_NAMES[it["source_type"]]})
    primary = items[sorted_ids[0]]
    item = {
        "id": f"{tier}-{ids[0]}",
        "tier": tier,
        "category": ev["category"],
        "title": ev.get("title", primary["title"]),
        "summary": ev.get("summary", primary["desc"][:100]),
        "why": ev.get("why", ""),
        "watch": ev.get("watch", ""),
        "status": ev.get("status", ""),
        "tags": ev.get("tags", []),
        **({"context": ev["context"]} if ev.get("context") else {}),
        **({"significance": ev["significance"]} if ev.get("significance") else {}),
        **({"detail": ev["detail"]} if ev.get("detail") else {}),
        **({"claims": ev["claims"]} if ev.get("claims") else {}),
        "score": ev["score"],
        "src_tier": ev.get("tier", ""),
        "source_type": TYPE_NAMES[primary["source_type"]],
        "time": primary["time"],
        "sources": sources[:5],
    }
    # 精选恒带 event_id（前端"继续追踪"按钮需要）；
    # 跨天延续字段（第 2 天起）才带 day_count/history，文件保持干净
    if ev.get("event_id"):
        item["event_id"] = ev["event_id"]
    if ev.get("day_count", 0) >= 2:
        item["day_count"] = ev["day_count"]
        item["history"] = [{"date": h.get("date", ""), "summary": h.get("summary", "")}
                           for h in reversed(ev.get("history_prev", []))]
    return item


def build_tracking(registry, picked, date_str):
    """「追踪中」区数据：钉选且活跃、今天没进精选的事件。"""
    if not registry:
        return []
    picked_ids = {ev.get("event_id") for ev in picked if ev.get("event_id")}
    tracking = []
    for e in registry.get("events", []):
        if e.get("status") != "active" or not e.get("pinned"):
            continue
        if e.get("event_id") in picked_ids:
            continue
        hist = e.get("history", [])
        tracking.append({
            "event_id": e.get("event_id", ""),
            "title": e.get("title", ""),
            "category": e.get("category", ""),
            "day_count": len({h.get("date") for h in hist}),
            "last_seen": e.get("last_seen", ""),
            "updated_today": e.get("last_seen") == date_str,
            "history": [{"date": h.get("date", ""), "summary": h.get("summary", "")}
                        for h in reversed(hist[-7:])],
        })
    return tracking


# ----------------------------------------------------------------
# 6.1.5 英语单词本：从精选英文原文挑高价值词 + 补全手动加的裸词
#   数据流与 feedback/read_later 一致：用户在页面收藏/加词 -> api/vocab.js
#   写回 vocab-book.json；管线次日读它做全量去重、并把 pending 裸词补全成完整卡。
#   每日候选写 data/vocab/<date>.js（前端按日懒加载，无需 manifest）。
# ----------------------------------------------------------------

VOCAB_BOOK_FILE = "vocab-book.json"

VOCAB_SYSTEM = """你是英语词汇教练，为中文母语的英语学习者从今日英文新闻里挑"高价值单词"。
用户给你若干条今日精选新闻的英文标题与英文摘要（附中文事件标题和条目编号 [k]）。
请挑出 {n_min}-{n_max} 个最值得积累的高价值单词/短语，标准：
- 兼收两类：①通用进阶词汇（CEFR B2-C1，可迁移到写作/考试，如 scrutiny、resilience、unprecedented）
  ②时事高频术语（如 sanctions、tariff、ceasefire、inflation）
- 按"对中文母语学习者的学习价值"综合权衡，宁缺毋滥
排除：专有名词、地名、人名、机构名、太基础的词（四级以下）、以及只在该新闻里出现、迁移价值低的生僻词。
用户会给出【已收录、请跳过】的词元清单，清单里的词一律不要再挑。
对每个词输出一张精炼卡：
- word: 原词的词元 lemma（动词还原原形、名词还原单数、去掉时态/复数）
- phonetic: 音标（带斜杠，如 /ˈskruːtɪni/）
- pos: 词性缩写（n. / v. / adj. / adv. / phrase 等）
- sense_zh: 该新闻语境下的中文释义（≤20字，只给这个语境的义项）
- example_en: 一句包含该词的英文例句，优先直接取自给定的新闻标题/摘要原文
- item_id: 该词来自哪条新闻的编号（就是用户给的 [k] 里的 k，整数）
只输出 JSON 数组，每个元素：
{{"word":"...","phonetic":"...","pos":"...","sense_zh":"...","example_en":"...","item_id":k}}
不要输出任何其他文字。"""

VOCAB_ENRICH_SYSTEM = """你是英语词汇教练。用户给你若干英文单词/短语（可能带一句来源语境）。
为每个词生成精炼卡，供中文母语学习者积累：
- word: 词元原形
- phonetic: 音标（带斜杠）
- pos: 词性缩写（n. / v. / adj. / adv. / phrase 等）
- sense_zh: 最常用的中文释义（≤20字；若给了语境则取该语境义）
- example_en: 一句自然的英文例句（若给了来源语境句可直接采用）
按输入顺序输出 JSON 数组，每个元素：
{"word":"...","phonetic":"...","pos":"...","sense_zh":"...","example_en":"..."}
不要输出其他文字。"""


def normalize_word(w):
    """词元归一：小写、只留字母（run/Running/ran 各自的表面形按输入，去噪即可）。"""
    return re.sub(r"[^a-z]", "", str(w or "").strip().lower())


def load_vocab_book(data_dir):
    """读 vocab-book.json；缺失/损坏一律返回空册（结构补齐）。"""
    f = data_dir / VOCAB_BOOK_FILE
    if not f.exists():
        return {"version": 1, "words": [], "pending": []}
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("not a dict")
        data.setdefault("version", 1)
        if not isinstance(data.get("words"), list):
            data["words"] = []
        if not isinstance(data.get("pending"), list):
            data["pending"] = []
        return data
    except Exception as e:
        log(f"  {VOCAB_BOOK_FILE} 读取失败，重建空册: {e}")
        return {"version": 1, "words": [], "pending": []}


def collect_seen_lemmas(data_dir, book, skip_date=None):
    """已出现过的词元集合：单词本 words+pending ∪ 历史 vocab/<date>.js。
    skip_date 对应的当日文件不计入——同日重跑时才能重新生成、而非把自己去空。"""
    seen = set()
    for w in book.get("words", []):
        seen.add(w.get("lemma") or normalize_word(w.get("word")))
    for p in book.get("pending", []):
        seen.add(p.get("lemma") or normalize_word(p.get("word")))
    vdir = data_dir / "vocab"
    if vdir.exists():
        for p in sorted(vdir.glob("*.js")):
            if skip_date and p.stem == skip_date:
                continue
            try:
                src = p.read_text(encoding="utf-8")
                m = re.search(r"window\.VOCAB_DATA\[[^\]]+\] = (\{.*\});", src, re.S)
                if not m:
                    continue
                payload = json.loads(m.group(1))
                for w in payload.get("words", []):
                    seen.add(w.get("lemma") or normalize_word(w.get("word")))
            except Exception:
                continue
    seen.discard("")
    return seen


def extract_vocab(llm, picked, items, seen_lemmas, cfg):
    """从精选事件的英文标题+摘要挑高价值词，返回精炼卡列表（已按 seen_lemmas 去重）。"""
    vcfg = cfg.get("vocab") or {}
    n_min = int(vcfg.get("daily_min", 6))
    n_max = int(vcfg.get("daily_max", 10))
    if not picked:
        return []
    blocks = []
    idx_to_meta = {}
    for k, ev in enumerate(picked):
        ids = ev.get("ids") or []
        if not ids:
            continue
        # 主源排序与 event_to_item 一致：事实源优先、可信度高优先
        sorted_ids = sorted(ids, key=lambda i: (
            items[i]["source_type"] != "fact", -items[i]["credibility"]))
        en_parts = []
        for i in sorted_ids[:2]:
            it = items[i]
            en_parts.append(f"{it['title']}. {it.get('desc', '')[:300]}")
        en_text = " ".join(en_parts).strip()
        if not en_text:
            continue
        idx_to_meta[k] = {"item_id": f"pick-{ids[0]}", "item_title": ev.get("title", ""),
                          "category": ev.get("category", "")}
        blocks.append(f"[{k}]（{ev.get('title', '')}）\n{en_text}")
    if not blocks:
        return []
    skip_hint = ""
    if seen_lemmas:
        skip_hint = "\n\n【已收录、请跳过这些词元】\n" + ", ".join(sorted(seen_lemmas)[:200])
    system = VOCAB_SYSTEM.format(n_min=n_min, n_max=n_max)
    try:
        result = llm.json_call(system, "\n\n".join(blocks) + skip_hint)
    except Exception as e:
        log(f"  单词本挑词失败，今日跳过: {e}")
        return []
    cards = []
    used = set()
    for r in (result if isinstance(result, list) else []):
        word = str(r.get("word", "")).strip()
        lemma = normalize_word(word)
        if not lemma or lemma in seen_lemmas or lemma in used:
            continue
        k = r.get("item_id")
        meta = idx_to_meta.get(k) if isinstance(k, int) else None
        if meta is None:   # LLM 漏填或填错编号：退化到第一条精选，避免丢词
            meta = next(iter(idx_to_meta.values()),
                        {"item_id": "", "item_title": "", "category": ""})
        used.add(lemma)
        cards.append({
            "word": word,
            "lemma": lemma,
            "phonetic": str(r.get("phonetic", "")).strip(),
            "pos": str(r.get("pos", "")).strip(),
            "sense_zh": str(r.get("sense_zh", "")).strip()[:40],
            "example_en": str(r.get("example_en", "")).strip()[:400],
            "item_id": meta["item_id"],
            "item_title": meta["item_title"],
            "category": meta["category"],
        })
        if len(cards) >= n_max:
            break
    return cards


def enrich_pending(llm, book):
    """把 vocab-book.json 的 pending 裸词补全成完整卡并移入 words。返回补全条数；
    LLM 失败则原样保留 pending 下次再试。"""
    pending = book.get("pending") or []
    if not pending:
        return 0
    existing = {w.get("lemma") or normalize_word(w.get("word"))
                for w in book.get("words", [])}
    lines, valid = [], []
    for p in pending:
        word = str(p.get("word", "")).strip()
        if not word:
            continue
        ctx = str(p.get("context", "")).strip()
        lines.append(f"[{len(valid)}] {word}" + (f"  语境: {ctx}" if ctx else ""))
        valid.append(p)
    if not valid:
        book["pending"] = []
        return 0
    try:
        result = llm.json_call(VOCAB_ENRICH_SYSTEM, "\n".join(lines))
    except Exception as e:
        log(f"  手动词补全失败，保留 pending 下次再试: {e}")
        return 0
    result = result if isinstance(result, list) else []
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    for i, p in enumerate(valid):
        r = result[i] if i < len(result) else {}
        word = str(r.get("word") or p.get("word") or "").strip()
        lemma = normalize_word(word)
        if not lemma or lemma in existing:
            continue
        existing.add(lemma)
        book.setdefault("words", []).append({
            "word": word,
            "lemma": lemma,
            "phonetic": str(r.get("phonetic", "")).strip(),
            "pos": str(r.get("pos", "")).strip(),
            "sense_zh": str(r.get("sense_zh", "")).strip()[:40],
            "example_en": str(r.get("example_en", "")).strip()[:400],
            "item_id": p.get("item_id", ""),
            "item_title": p.get("item_title", ""),
            "date": p.get("date", ""),
            "source": "manual",
            "collected_ts": now,
            "mastered": False,
        })
        n += 1
    book["pending"] = []   # 处理过的都清空：成功的入册，无效/重复的丢弃
    return n


def write_vocab(date_str, cards, data_dir):
    vdir = data_dir / "vocab"
    vdir.mkdir(parents=True, exist_ok=True)
    payload = {"date": date_str,
               "generated_at": datetime.now(timezone.utc).isoformat(),
               "words": cards}
    js = ("window.VOCAB_DATA = window.VOCAB_DATA || {};\n"
          f"window.VOCAB_DATA[{json.dumps(date_str)}] = "
          f"{json.dumps(payload, ensure_ascii=False, indent=1)};\n")
    (vdir / f"{date_str}.js").write_text(js, encoding="utf-8")


def build_vocab(llm, picked, items, date_str, cfg):
    """单词本编排：补全手动裸词 -> 全量去重 -> 挑今日候选 -> 落盘。"""
    vcfg = cfg.get("vocab") or {}
    if not vcfg.get("enabled", True):
        return
    data_dir = Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    book = load_vocab_book(data_dir)
    had_pending = bool(book.get("pending"))
    n_enriched = enrich_pending(llm, book)          # 先补全，纳入去重集
    seen = collect_seen_lemmas(data_dir, book, skip_date=date_str)
    cards = extract_vocab(llm, picked, items, seen, cfg)
    if cards:                                        # 空结果不落盘，避免覆盖前次好数据 / 产出空文件
        write_vocab(date_str, cards, data_dir)
    if had_pending or not (data_dir / VOCAB_BOOK_FILE).exists():
        (data_dir / VOCAB_BOOK_FILE).write_text(
            json.dumps(book, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log(f"  英语单词本：新挑 {len(cards)} 词，补全手动词 {n_enriched} 个")


def write_all_archive(items, sources, date_str, keep_days=90, min_score=40):
    """全部动态轻档：窗口内全量抓取条目的轻字段落盘 data/all/<date>.js。
    不经 LLM、零 token；供前端「全部动态」板块按天懒加载，也是筛选器的
    可核查底账。滚动保留 keep_days 天防仓库膨胀（git 历史仍会增长，接受）。
    类别取来源配置的 category（条目级类别在此阶段尚不存在）；min_score 是
    前端默认展示阈值，评分由 backfill_all_scores 在评分阶段后回填。"""
    data_dir = Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data"
    adir = data_dir / "all"
    adir.mkdir(parents=True, exist_ok=True)
    cat_by_src = {s["id"]: s.get("category", "") for s in sources}
    rows = [{
        "t": it["title"],
        "u": it["url"],
        "s": it["source"],
        "c": cat_by_src.get(it["source_id"].split(":")[0], ""),
        "time": it["time"],
    } for it in items]
    rows.sort(key=lambda r: r["time"], reverse=True)
    payload = {"date": date_str, "min_score": min_score, "items": rows}
    js = ("window.NEWS_ALL = window.NEWS_ALL || {};\n"
          f"window.NEWS_ALL[{json.dumps(date_str)}] = "
          f"{json.dumps(payload, ensure_ascii=False, indent=1)};\n")
    (adir / f"{date_str}.js").write_text(js, encoding="utf-8")
    # 滚动剪枝（ISO 日期字符串可直接比大小）+ manifest 倒序
    cutoff = (datetime.strptime(date_str, "%Y-%m-%d")
              - timedelta(days=keep_days)).strftime("%Y-%m-%d")
    for p in adir.glob("*.js"):
        if p.stem != "manifest" and p.stem < cutoff:
            p.unlink()
    dates = sorted([p.stem for p in adir.glob("*.js") if p.stem != "manifest"],
                   reverse=True)
    (adir / "manifest.js").write_text(
        f"window.ALL_MANIFEST = {json.dumps(dates, ensure_ascii=False)};\n",
        encoding="utf-8")
    log(f"已写入 data/all/{date_str}.js（全量 {len(rows)} 条 · 保留 {keep_days} 天）")


def backfill_all_scores(events, items, date_str):
    """评分回填全量档：按 URL（去 query，与 fetch_all 去重同口径）把事件分
    写到当日 all 档匹配条目的 score 字段。被预筛砍掉的条目不参与评分、无分，
    前端默认隐藏、可切换显示。独立故障域，档缺失/格式异常只记日志。"""
    data_dir = Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data"
    f = data_dir / "all" / f"{date_str}.js"
    if not f.exists():
        return
    m = re.search(r"window\.NEWS_ALL\[[^\]]+\] = (\{.*\});",
                  f.read_text(encoding="utf-8"), re.S)
    if not m:
        log("  全量档格式异常，跳过评分回填")
        return
    payload = json.loads(m.group(1))
    url_score = {}
    for ev in events:
        sc = ev.get("score")
        if sc is None:
            continue
        for i in ev.get("ids", []):
            url_score[items[i]["url"].split("?")[0]] = round(sc)
    n = 0
    for r in payload.get("items", []):
        sc = url_score.get((r.get("u") or "").split("?")[0])
        if sc is not None:
            r["score"] = sc
            n += 1
    js = ("window.NEWS_ALL = window.NEWS_ALL || {};\n"
          f"window.NEWS_ALL[{json.dumps(date_str)}] = "
          f"{json.dumps(payload, ensure_ascii=False, indent=1)};\n")
    f.write_text(js, encoding="utf-8")
    log(f"  全量档评分回填：{n}/{len(payload.get('items') or [])} 条带分")


def write_output(date_str, brief, picked, secondary, items, cfg, registry=None, deep=None, themes=None, papers=None, opinion=None):
    # DATA_DIR 环境变量可重定向输出目录（云端 CI 直接写入博客仓库的
    # source/news/data/，checkout 自带历史文件，manifest 扫描结果完整）
    data_dir = Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data"
    daily_dir = data_dir / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)

    out_items = ([event_to_item(e, items, "pick") for e in picked] +
                 [event_to_item(e, items, "more") for e in secondary])
    payload = {
        "date": date_str,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "brief": brief,
        "stats": {
            "sources_count": len(set(i["source_id"] for i in items)),
            "raw_count": len(items),
            "pick_count": len(picked),
            "more_count": len(secondary),
        },
        "items": out_items,
    }
    if themes:
        payload["themes"] = themes
    tracking = build_tracking(registry, picked, date_str)
    if tracking:
        payload["tracking"] = tracking
    if deep:
        payload["deep"] = deep
    if papers:
        payload["papers"] = papers
    if opinion:
        payload["opinion"] = opinion
    js = ("window.NEWS_DATA = window.NEWS_DATA || {};\n"
          f"window.NEWS_DATA[{json.dumps(date_str)}] = "
          f"{json.dumps(payload, ensure_ascii=False, indent=1)};\n")
    (daily_dir / f"{date_str}.js").write_text(js, encoding="utf-8")

    # 更新 manifest（倒序）
    dates = sorted([p.stem for p in daily_dir.glob("*.js")], reverse=True)
    manifest = f"window.NEWS_MANIFEST = {json.dumps(dates, ensure_ascii=False)};\n"
    (data_dir / "manifest.js").write_text(manifest, encoding="utf-8")
    log(f"已写入 data/daily/{date_str}.js（精选 {len(picked)} + 更多 {len(secondary)}）")


# ----------------------------------------------------------------
# 6.1.8 每周综述：趋势连线 + 待验证回收（长期判断力沉淀）
#   每周一由主管线额外合成上周综述，链式读上周综述 + 本周 daily + events.json。
#   失败只记日志、不阻断每日产出（与深读频道同等地位）。
# ----------------------------------------------------------------

WEEKLY_DIRECTIONS = {"新增", "推进", "反转", "停滞"}
WEEKLY_STATUS = {"兑现", "部分兑现", "未兑现", "反转"}

WEEKLY_SYSTEM = """你是资深主编，为个人读者写"每周综述"，帮他把一周的信息流沉淀成判断。
用户会给你：可能有【上周综述】、本周的【精选与关注点】(每条带日期/类目/关注信号)、
本周【跨天事件线】(同一事件多天的进展)。若给了【读者兴趣画像】，综述要向读者关注的领域倾斜。
产出三部分：
- threads: 3-5 条本周演进主线，把相关事件连成线，说清"这周往哪走"。每条：
    title(≤12字主线名) / one_liner(≤50字这周整体走向) /
    direction(只能是 新增|推进|反转|停滞，相对上周或本周内的态势) / detail(≤80字关键进展与机制)
- watch_recap: 回收"待验证"。结合【上周综述】提出的主线/关注点，对照本周事实，逐条说它兑现没：
    prior(上周关注的点，≤40字) / status(只能是 兑现|部分兑现|未兑现|反转) / note(≤50字现在怎样了)
    没有【上周综述】就给空数组；不要编造上周没提过的点。
- outlook: 2-3 条下周值得盯的信号(每条≤40字)。
只输出 JSON：{"threads":[...],"watch_recap":[...],"outlook":[...]}。不要其他文字。"""


def iso_week_key(d):
    """datetime/date -> 'YYYY-Www'（ISO 周，与前端命名一致）。"""
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def read_daily_payload(path):
    """从本管线写出的 daily js 里剥壳取 JSON；失败返回 None。"""
    try:
        src = path.read_text(encoding="utf-8")
        m = re.search(r"window\.NEWS_DATA\[[^\]]+\] = (\{.*\});", src, re.S)
        return json.loads(m.group(1)) if m else None
    except Exception:
        return None


def read_weekly_payload(path):
    """从周综述 js 里剥壳取 JSON；失败返回 None。"""
    try:
        src = path.read_text(encoding="utf-8")
        m = re.search(r"window\.WEEKLY_DATA\[[^\]]+\] = (\{.*\});", src, re.S)
        return json.loads(m.group(1)) if m else None
    except Exception:
        return None


def write_weekly(llm, date_str, cfg, data_dir, profile_text=""):
    """合成上周综述，写 data/weekly/<YYYY-Www>.js + manifest.js。宁缺毋滥、失败不抛。"""
    wcfg = cfg.get("weekly") or {}
    lookback = int(wcfg.get("lookback_days", 7))
    keep = int(wcfg.get("keep_weeks", 26))
    today = datetime.strptime(date_str, "%Y-%m-%d")
    target_day = today - timedelta(days=1)          # 周一跑 -> 目标是上周
    week_key = iso_week_key(target_day)

    # 本周素材：回看窗口内的 daily 精选与其 watch
    daily_dir = data_dir / "daily"
    days = []
    for k in range(1, lookback + 1):
        p = daily_dir / f"{(today - timedelta(days=k)).strftime('%Y-%m-%d')}.js"
        payload = read_daily_payload(p)
        if payload:
            days.append(payload)
    if not days:
        log("  周综述：回看窗口无 daily 数据，跳过")
        return
    pick_lines = []
    for dp in days:
        for it in dp.get("items", []):
            if it.get("tier") != "pick":
                continue
            w = it.get("watch", "")
            pick_lines.append(
                f"[{dp.get('date', '')}|{CAT_NAMES.get(it.get('category', ''), it.get('category', ''))}] "
                f"{it.get('title', '')}：{it.get('summary', '')}"
                + (f" ｜关注:{w}" if w else ""))

    # 跨天事件线：events.json 里本周窗口内、≥2 天的活跃事件
    ev_lines = []
    win = {dp.get("date") for dp in days}
    try:
        reg = data_dir / "events.json"
        registry = json.loads(reg.read_text(encoding="utf-8")) if reg.exists() else {}
        for e in registry.get("events", []):
            hist = e.get("history", [])
            ds = {h.get("date") for h in hist}
            if len(ds) >= 2 and (ds & win):
                seq = " → ".join(f"{h.get('date', '')}:{h.get('summary', '')}"
                                 for h in hist[-4:])
                ev_lines.append(
                    f"[{CAT_NAMES.get(e.get('category', ''), e.get('category', ''))}] "
                    f"{e.get('title', '')}｜{seq}")
    except Exception:
        pass

    # 链式：读上周综述
    prev_key = iso_week_key(target_day - timedelta(days=7))
    prev = read_weekly_payload(data_dir / "weekly" / f"{prev_key}.js")
    prev_block = ""
    if prev:
        pt = "；".join((t.get("title", "") + ":" + t.get("one_liner", ""))
                      for t in prev.get("threads", []))
        pw = "；".join(o for o in prev.get("outlook", []))
        prev_block = f"【上周综述·主线】{pt}\n【上周综述·下周关注】{pw}\n\n"

    prof_block = ("【读者兴趣画像】\n" + profile_text.strip() + "\n\n"
                  if profile_has_content(profile_text) else "")
    user = (prof_block + prev_block
            + "【本周精选与关注点】\n" + "\n".join(pick_lines[:80])
            + "\n\n【本周跨天事件线】\n" + ("\n".join(ev_lines) or "（无）"))

    result = llm.json_call(WEEKLY_SYSTEM, user)
    if not isinstance(result, dict):
        log("  周综述：LLM 输出异常，跳过")
        return

    def _clip(s, n):
        return str(s or "")[:n]

    threads = []
    for t in (result.get("threads") or [])[:5]:
        if not isinstance(t, dict):
            continue
        threads.append({
            "title": _clip(t.get("title"), 12),
            "one_liner": _clip(t.get("one_liner"), 50),
            "direction": t.get("direction") if t.get("direction") in WEEKLY_DIRECTIONS else "推进",
            "detail": _clip(t.get("detail"), 80),
        })
    recap = []
    for r in (result.get("watch_recap") or [])[:6]:
        if not isinstance(r, dict):
            continue
        recap.append({
            "prior": _clip(r.get("prior"), 40),
            "status": r.get("status") if r.get("status") in WEEKLY_STATUS else "未兑现",
            "note": _clip(r.get("note"), 50),
        })
    outlook = [_clip(o, 40) for o in (result.get("outlook") or [])[:3] if str(o or "").strip()]
    if not threads and not recap:
        log("  周综述：无有效内容，跳过写文件")
        return

    payload = {
        "week": week_key,
        "range": {"start": days[-1].get("date", ""), "end": days[0].get("date", "")},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "threads": threads,
        "watch_recap": recap,
        "outlook": outlook,
    }
    wdir = data_dir / "weekly"
    wdir.mkdir(parents=True, exist_ok=True)
    js = ("window.WEEKLY_DATA = window.WEEKLY_DATA || {};\n"
          f"window.WEEKLY_DATA[{json.dumps(week_key)}] = "
          f"{json.dumps(payload, ensure_ascii=False, indent=1)};\n")
    (wdir / f"{week_key}.js").write_text(js, encoding="utf-8")

    weeks = sorted([p.stem for p in wdir.glob("*.js") if p.stem != "manifest"],
                   reverse=True)
    for old in weeks[keep:]:
        try:
            (wdir / f"{old}.js").unlink()
        except Exception:
            pass
    weeks = weeks[:keep]
    (wdir / "manifest.js").write_text(
        f"window.WEEKLY_MANIFEST = {json.dumps(weeks, ensure_ascii=False)};\n",
        encoding="utf-8")
    log(f"  周综述已写入 data/weekly/{week_key}.js（主线 {len(threads)} · 回收 {len(recap)}）")


# ----------------------------------------------------------------
# 6.2 RSS 输出：data/feed.xml（每条精选一个 item，含深读推荐）
#   注：daily/weekly 剥壳解析器 read_daily_payload/read_weekly_payload 见上方周综述节，
#   feed 生成复用 read_daily_payload。
# ----------------------------------------------------------------

def xml_esc(s):
    return html.escape(str(s or ""), quote=True)


def _cdata(s):
    # CDATA 内唯一的禁忌是 "]]>"
    return "<![CDATA[" + str(s or "").replace("]]>", "]]&gt;") + "]]>"


def _rfc822(iso, fallback):
    try:
        return format_datetime(datetime.fromisoformat(str(iso)))
    except Exception:
        return fallback


def write_feed(data_dir, date_str, cfg):
    """生成 feed.xml。失败只 log 不中止（新闻数据已落盘）。"""
    try:
        feed_days = int(cfg.get("feed_days", 7))
        site = str(cfg.get("site_url", "")).rstrip("/")
        daily_dir = data_dir / "daily"
        dates = sorted([p.stem for p in daily_dir.glob("*.js")], reverse=True)[:feed_days]
        now_rfc = format_datetime(datetime.now(timezone.utc))
        items_xml = []
        for d in dates:
            payload = read_daily_payload(daily_dir / f"{d}.js")
            if not payload:
                continue
            day_rfc = _rfc822(payload.get("generated_at"), now_rfc)
            for it in payload.get("items", []):
                if it.get("tier") != "pick":
                    continue
                srcs = it.get("sources") or []
                link = (srcs[0].get("url") if srcs else "") or f"{site}/news/"
                desc = f"<p>{html.escape(it.get('summary', ''))}</p>"
                if it.get("why"):
                    desc += f"<p><b>为什么重要：</b>{html.escape(it['why'])}</p>"
                if it.get("watch"):
                    desc += f"<p><b>后续关注：</b>{html.escape(it['watch'])}</p>"
                if srcs:
                    desc += "<p>来源：" + "、".join(
                        f'<a href="{html.escape(s.get("url", ""), quote=True)}">'
                        f'{html.escape(s.get("name", ""))}</a>' for s in srcs) + "</p>"
                cat = CAT_NAMES.get(it.get("category", ""), it.get("category", ""))
                items_xml.append(
                    "<item>"
                    f"<title>{xml_esc('[' + cat + '] ' + it.get('title', ''))}</title>"
                    f"<link>{xml_esc(link)}</link>"
                    f"<guid isPermaLink=\"false\">{xml_esc(d + ':' + it.get('id', ''))}</guid>"
                    f"<pubDate>{_rfc822(it.get('time'), day_rfc)}</pubDate>"
                    f"<description>{_cdata(desc)}</description>"
                    "</item>")
            for dp in payload.get("deep", []):
                desc = f"<p>{html.escape(dp.get('brief', ''))}</p>"
                if dp.get("why"):
                    desc += f"<p><b>为什么值得读：</b>{html.escape(dp['why'])}</p>"
                desc += (f"<p>{html.escape(dp.get('source', ''))} · "
                         f"约 {int(dp.get('read_minutes') or 0)} 分钟</p>")
                items_xml.append(
                    "<item>"
                    f"<title>{xml_esc('【深读】' + (dp.get('title_zh') or dp.get('title', '')))}</title>"
                    f"<link>{xml_esc(dp.get('url', ''))}</link>"
                    f"<guid isPermaLink=\"false\">{xml_esc(d + ':' + dp.get('id', ''))}</guid>"
                    f"<pubDate>{day_rfc}</pubDate>"
                    f"<description>{_cdata(desc)}</description>"
                    "</item>")
        feed = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<rss version="2.0"><channel>'
                "<title>每日驾驶舱 · Daily Briefing</title>"
                f"<link>{xml_esc(site + '/news/')}</link>"
                "<description>个人信息筛选驾驶舱：每日精选新闻与深读推荐</description>"
                "<language>zh-cn</language>"
                f"<lastBuildDate>{now_rfc}</lastBuildDate>"
                + "".join(items_xml) +
                "</channel></rss>\n")
        (data_dir / "feed.xml").write_text(feed, encoding="utf-8")
        log(f"  feed.xml：{len(items_xml)} 个 item（近 {len(dates)} 天）")
    except Exception as e:
        log(f"  feed.xml 生成失败（不影响主管线）: {e}")


# ----------------------------------------------------------------
# 6.3 搜索索引：data/search_index.js（紧凑数组，前端懒加载）
# ----------------------------------------------------------------

def index_rows(payload):
    rows = []
    d = payload.get("date", "")
    for it in payload.get("items", []):
        rows.append([d, it.get("id", ""), it.get("tier", ""), it.get("category", ""),
                     it.get("title", ""), "|".join(it.get("tags") or [])])
    for dp in payload.get("deep", []):
        rows.append([d, dp.get("id", ""), "deep", "deep",
                     dp.get("title_zh") or dp.get("title", ""), ""])
    return rows


def update_search_index(data_dir, date_str, cfg):
    """当日条目替换写入（幂等）；索引缺失/损坏时从现存 daily 文件全量重建。"""
    try:
        keep_days = int(cfg.get("search_index_days", 180))
        daily_dir = data_dir / "daily"
        idx_file = data_dir / "search_index.js"
        entries = []
        if idx_file.exists():
            try:
                m = re.search(r"window\.NEWS_INDEX = (\[.*\]);",
                              idx_file.read_text(encoding="utf-8"), re.S)
                entries = json.loads(m.group(1)) if m else []
            except Exception as e:
                log(f"  search_index.js 读取失败，重建: {e}")
                entries = []
        if entries:
            entries = [r for r in entries if r and r[0] != date_str]
        else:
            for d in sorted(p.stem for p in daily_dir.glob("*.js")):
                if d == date_str:
                    continue
                payload = read_daily_payload(daily_dir / f"{d}.js")
                if payload:
                    entries += index_rows(payload)
        payload = read_daily_payload(daily_dir / f"{date_str}.js")
        if payload:
            entries += index_rows(payload)
        today = datetime.strptime(date_str, "%Y-%m-%d")

        def _fresh(dt):
            try:
                return (today - datetime.strptime(dt, "%Y-%m-%d")).days <= keep_days
            except ValueError:
                return False

        entries = [r for r in entries if _fresh(r[0])]
        entries.sort(key=lambda r: r[0], reverse=True)
        idx_file.write_text("window.NEWS_INDEX = "
                            + json.dumps(entries, ensure_ascii=False) + ";\n",
                            encoding="utf-8")
        log(f"  搜索索引：{len(entries)} 条")
    except Exception as e:
        log(f"  搜索索引更新失败（不影响主管线）: {e}")


# ----------------------------------------------------------------
# 6.5 信源健康度：滚动记录抓取状态，连续失败报警
# ----------------------------------------------------------------

HEALTH_KEEP_DAYS = 14
HEALTH_ALERT_DAYS = 3


def update_source_health(fetch_stats, date_str):
    """把当日各源抓取状态写入 source_health.json（滚动保留最近 14 天），
    并对"最近 3 个记录日连续抓取失败"的源发 GitHub Actions ::warning:: 注解
    （本地运行时就是普通日志行）。"""
    data_dir = Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    health_file = data_dir / "source_health.json"
    health = {"days": {}}
    if health_file.exists():
        try:
            health = json.loads(health_file.read_text(encoding="utf-8"))
        except Exception as e:
            log(f"  source_health.json 读取失败，重建: {e}")
            health = {"days": {}}
    days = health.setdefault("days", {})
    days[date_str] = {sid: {"count": st["count"], "error": st["error"]}
                      for sid, st in fetch_stats.items()}
    for old in sorted(days)[:-HEALTH_KEEP_DAYS]:
        del days[old]
    health_file.write_text(json.dumps(health, ensure_ascii=False, indent=1),
                           encoding="utf-8")

    recent = sorted(days, reverse=True)[:HEALTH_ALERT_DAYS]
    if len(recent) < HEALTH_ALERT_DAYS:
        return
    for sid, st in fetch_stats.items():
        if all(days[d].get(sid, {}).get("error") for d in recent):
            print(f"::warning::信源 {st['name']} ({sid}) "
                  f"已连续 {HEALTH_ALERT_DAYS} 天抓取失败，请检查 RSS 地址是否失效", flush=True)


# ----------------------------------------------------------------
# 7. 同步发布到博客（可选，永不自动 push）
# ----------------------------------------------------------------

def publish_to_blog(cfg, date_str):
    import shutil
    import subprocess
    pub = cfg.get("publish") or {}
    blog_dir = (pub.get("blog_dir") or "").strip()
    if not blog_dir:
        return
    blog = Path(blog_dir)
    news_dir = blog / "source" / "news"
    if not blog.exists():
        log(f"发布跳过：博客目录不存在 {blog}")
        return
    dst_data = news_dir / "data"
    (dst_data / "daily").mkdir(parents=True, exist_ok=True)
    src_data = ROOT / "data"
    shutil.copy2(src_data / "manifest.js", dst_data / "manifest.js")
    n = 0
    for f in (src_data / "daily").glob("*.js"):
        shutil.copy2(f, dst_data / "daily" / f.name)
        n += 1
    log(f"已同步 {n} 个数据文件到博客 source/news/data/")

    if pub.get("git_commit"):
        try:
            subprocess.run(["git", "add", "source/news/data"],
                           cwd=blog, check=True, capture_output=True)
            diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=blog)
            if diff.returncode != 0:
                subprocess.run(
                    ["git", "commit", "-m", f"Update daily briefing data ({date_str})"],
                    cwd=blog, check=True, capture_output=True)
                log("博客已本地 commit（未 push，上线请手动 git push）")
            else:
                log("博客数据无变化，跳过 commit")
        except Exception as e:
            log(f"博客 git commit 失败（数据已同步，可手动提交）: {e}")


# ----------------------------------------------------------------
# 自建 RSSHub 占位符解析
# ----------------------------------------------------------------

def resolve_rsshub_sources(sources):
    """把 sources.yaml 里的 {rsshub} 占位符替换成自建实例地址并追加访问密钥。
    base/key 从环境变量 RSSHUB_BASE / RSSHUB_KEY 读取——公开仓库不落地址与密钥。
    未配置 RSSHUB_BASE 时，带占位符的源自动跳过，不影响其余源。"""
    base = os.environ.get("RSSHUB_BASE", "").strip().rstrip("/")
    key = os.environ.get("RSSHUB_KEY", "").strip()
    out = []
    for s in sources:
        url = s.get("url", "")
        if "{rsshub}" not in url:
            out.append(s)
            continue
        if not base:
            log(f"  ⚠ 跳过 {s['name']}：未配置 RSSHUB_BASE 环境变量（自建 RSSHub 源）")
            continue
        resolved = url.replace("{rsshub}", base)
        if key:
            sep = "&" if "?" in resolved else "?"
            resolved = f"{resolved}{sep}key={key}"
        out.append({**s, "url": resolved})
    return out


# ----------------------------------------------------------------
# main
# ----------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只抓取，不调 LLM")
    ap.add_argument("--date", default=None, help="输出日期 YYYY-MM-DD，默认今天")
    args = ap.parse_args()

    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))

    # ---- 环境变量覆盖（供云端 CI 使用，本地运行无感知） ----
    if os.environ.get("LLM_API_KEY", "").strip():
        cfg["llm"]["api_key"] = os.environ["LLM_API_KEY"].strip()
    if os.environ.get("PREFILTER_API_KEY", "").strip():
        cfg.setdefault("prefilter", {})["api_key"] = os.environ["PREFILTER_API_KEY"].strip()
    if os.environ.get("BLOG_DIR"):
        cfg.setdefault("publish", {})["blog_dir"] = os.environ["BLOG_DIR"]
    if os.environ.get("BLOG_GIT_COMMIT") == "0":
        cfg.setdefault("publish", {})["git_commit"] = False

    src_cfg = yaml.safe_load((ROOT / "sources.yaml").read_text(encoding="utf-8"))
    sources = [s for s in src_cfg["sources"] if s.get("enabled", True)]
    sources = resolve_rsshub_sources(sources)
    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    items, fetch_stats = fetch_all(sources, cfg)
    if not items:
        log("没有抓到任何内容，退出。")
        sys.exit(1)

    # 舆论热榜（独立信号层）：dry-run 也拉取——CI 手动 dry-run 即可验证
    # 热榜接口从 GitHub Actions 出口 IP 是否可达
    pulse = fetch_pulse_all(src_cfg)

    if args.dry_run:
        log("dry-run 完成，各源状态：")
        for sid, st in sorted(fetch_stats.items(), key=lambda x: -x[1]["count"]):
            flag = "✗ 抓取失败" if st["error"] else ("- 窗口内无新文章" if st["count"] == 0 else "✓")
            print(f"    {st['name']}: {st['count']} 条 {flag}")
        for s in (src_cfg.get("pulse_sources") or []):
            if s.get("enabled", True):
                n = sum(1 for p in pulse
                        if p["platform"] in s.get("name", s.get("type", "")))
                print(f"    [热榜] {s.get('name', s['type'])}: {n} 条词条")
        return

    # 全量轻档（不经 LLM，独立故障域）：写失败只记日志，不阻断主管线
    try:
        write_all_archive(items, sources, date_str,
                          min_score=int(cfg.get("all_view_min_score", 40)))
    except Exception as e:
        log(f"  全量轻档写入失败（不影响主管线）: {e}")

    if "在这里填" in cfg["llm"]["api_key"]:
        log("错误：请先在 config.yaml 里填写 llm.api_key")
        sys.exit(1)

    llm = LLM(cfg["llm"])

    # ---- 偏好学习输入：反馈与稍后读（缺失/损坏一律安全忽略） ----
    _data_dir = Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data"
    feedback = load_state_list(_data_dir, "feedback.json", "entries")
    read_later = load_state_list(_data_dir, "read_later.json", "items")
    pens = source_penalties(feedback, date_str)
    if pens:
        n_pen = 0
        for it in items:
            mult = pens.get(it["source"])
            if mult:
                it["credibility"] = it["credibility"] * mult
                n_pen += 1
        log(f"  来源降权：{pens}（影响 {n_pen} 条）")

    # 预筛：便宜模型先丢垃圾（未配置独立模型则复用主模型）
    pf_cfg = cfg.get("prefilter", {})
    if pf_cfg.get("enabled", False):
        merged = dict(cfg["llm"])
        for k in ("base_url", "api_key", "model"):
            if pf_cfg.get(k):
                merged[k] = pf_cfg[k]
        pf_model = merged["model"]
        log(f"预筛（{pf_model}）：过滤垃圾与无关条目 ...")
        items = prefilter(LLM(merged), items)

    log("阶段A：去重聚类 + 分类 + 五维打分 ...")
    events = triage(llm, items)
    log(f"  聚成 {len(events)} 个事件")

    log("偏好学习：画像蒸馏 + 兴趣拟合 ...")
    profile = update_profile(llm, _data_dir, feedback, read_later)
    interest_fit(llm, profile, events,
                 span=cfg.get("scoring", {}).get("fit_span", 0.30))

    # co-occurrence 暗排序：热榜与真新闻事件重合 -> 公众热度 bonus（热榜不进条目）
    n_pulse = apply_pulse_bonus(events, items, pulse, cfg)
    if n_pulse:
        log(f"  公众热度加权：{n_pulse} 个事件命中热榜")

    picked, secondary = score_and_select(events, items, cfg)

    # 评分回填全量档（独立故障域）：让「全部动态」能按分数过滤
    try:
        backfill_all_scores(events, items, date_str)
    except Exception as e:
        log(f"  全量档评分回填失败（不影响主管线）: {e}")

    log(f"阶段B：精加工 {len(picked)} 条精选 ...")
    enrich(llm, picked, items, cfg, profile)
    for ev in secondary:
        ev.setdefault("status", "")
    log("事件登记表：跨天延续性匹配 ...")
    registry = track_events(llm, picked, date_str, cfg,
                            secondary=secondary, feedback=feedback)
    brief, themes = write_brief(llm, picked, secondary)

    log("深读频道：长文筛选 ...")
    deep = deep_channel(llm, cfg, date_str, profile)

    log("今日论文：HF Daily Papers 筛选 ...")
    papers = papers_channel(llm, cfg, date_str, profile)

    log("舆论观察：热榜传播机制解读 ...")
    opinion = opinion_pulse(llm, cfg, pulse, profile)

    write_output(date_str, brief, picked, secondary, items, cfg,
                 registry=registry, deep=deep, themes=themes, papers=papers,
                 opinion=opinion)
    log("英语单词本：挑词 + 补全手动词 ...")
    build_vocab(llm, picked, items, date_str, cfg)

    # 每周综述：仅在配置的 weekday（默认周一）额外合成上周综述；失败不阻断每日产出
    wk = cfg.get("weekly") or {}
    if wk.get("enabled") and datetime.now().weekday() == wk.get("run_weekday", 0):
        log("周综述：趋势连线 + 待验证回收 ...")
        try:
            write_weekly(llm, date_str, cfg, _data_dir, profile)
        except Exception as e:
            log(f"  周综述失败（不影响每日产出）: {e}")

    update_source_health(fetch_stats, date_str)
    write_feed(_data_dir, date_str, cfg)
    update_search_index(_data_dir, date_str, cfg)

    # ---- 发布前校验：精选非空、输出文件存在且包含当日数据 ----
    _data_dir = Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data"
    out_file = _data_dir / "daily" / f"{date_str}.js"
    if (not picked or not out_file.exists()
            or f'window.NEWS_DATA["{date_str}"]' not in out_file.read_text(encoding="utf-8")):
        log("校验失败：精选为空或输出文件异常，中止发布。")
        sys.exit(2)

    publish_to_blog(cfg, date_str)
    log("完成 ✓  访问 /news/ 查看今日日报")


if __name__ == "__main__":
    main()
