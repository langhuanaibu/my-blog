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
    6. LLM 阶段B：对精选生成 一句话摘要 / 为什么重要 / 后续关注 / 状态标记
    7. 写入 data/daily/YYYY-MM-DD.js 和 data/manifest.js（前端直接读）
"""
import argparse
import concurrent.futures
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

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


def fetch_rss(src, window_start, max_items):
    try:
        resp = requests.get(src["url"], headers={"User-Agent": UA}, timeout=20)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except Exception as e:
        log(f"  ✗ {src['name']}: 抓取失败 ({e})")
        return []
    items = []
    for e in feed.entries:
        pub = parse_time(e)
        if pub is None or pub < window_start:
            continue
        title = strip_html(e.get("title", ""))
        link = e.get("link", "")
        if not title or not link:
            continue
        items.append({
            "title": title,
            "url": link,
            "desc": strip_html(e.get("summary", e.get("description", "")))[:400],
            "time": pub.isoformat(),
            "source": src["name"],
            "source_id": src["id"],
            "source_type": src["source_type"],
            "tier": src.get("tier", "T2"),
            "credibility": src["credibility"],
            "cat_hint": src.get("category", "mixed"),
        })
    items.sort(key=lambda x: x["time"], reverse=True)
    return items[:max_items]


def fetch_aihot(src, window_start, max_items):
    """AI HOT 公开 API 适配器（精选池）"""
    since = window_start.strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f"{src['url']}?mode=selected&since={since}&take={min(max_items * 2, 100)}"
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log(f"  ✗ {src['name']}: 抓取失败 ({e})")
        return []
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
        items.append({
            "title": it.get("title") or it.get("title_en") or "",
            "url": it.get("url", ""),
            "desc": (it.get("summary") or "")[:400],
            "time": it.get("publishedAt") or datetime.now(timezone.utc).isoformat(),
            "source": f"AI HOT · {inner}" if inner else src["name"],
            "source_id": src["id"],
            "source_type": stype,
            "tier": tier,
            "credibility": src["credibility"],
            "cat_hint": "ai",
        })
    return [x for x in items if x["title"] and x["url"]][:max_items]


def fetch_all(sources, cfg):
    window_start = datetime.now(timezone.utc) - timedelta(hours=cfg["window_hours"])
    max_items = cfg["max_per_source"]
    results = []
    log(f"开始抓取 {len(sources)} 个源（窗口 {cfg['window_hours']} 小时）...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futs = {}
        for src in sources:
            fn = fetch_aihot if src["type"] == "aihot" else fetch_rss
            futs[pool.submit(fn, src, window_start, max_items)] = src
        for fut in concurrent.futures.as_completed(futs):
            src = futs[fut]
            try:
                items = fut.result()
            except Exception as e:
                log(f"  ✗ {src['name']}: {e}")
                items = []
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
    return deduped


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
找出应该【丢弃】的编号：广告软文、纯营销、促销、招聘、体育赛果、娱乐八卦、
菜谱/生活贴士、纯情绪帖、以及明显不属于（AI/互联网科技/财经/社会事件/国际时事）任何一类的内容。
拿不准的一律保留。只输出 JSON：{"drop": [编号列表]}，没有可丢的输出 {"drop": []}。"""


def prefilter(llm, items):
    batch_size = 80
    drop = set()
    for bi in range(0, len(items), batch_size):
        batch = items[bi:bi + batch_size]
        lines = [f"[{bi + j}] ({it['source']}) {it['title']}"
                 for j, it in enumerate(batch)]
        try:
            result = llm.json_call(PREFILTER_SYSTEM, "\n".join(lines))
            for i in result.get("drop", []):
                if isinstance(i, int) and bi <= i < bi + len(batch):
                    drop.add(i)
        except Exception as e:
            log(f"  预筛批次失败，该批全部保留: {e}")
    kept = [it for i, it in enumerate(items) if i not in drop]
    log(f"预筛：丢弃 {len(drop)} 条，保留 {len(kept)} 条")
    return kept


# ----------------------------------------------------------------
# 4. 阶段A：去重聚类 + 分类 + 五维分项打分
# ----------------------------------------------------------------

TRIAGE_SYSTEM = """你是一个严格的新闻编辑，负责筛选每日高质量新闻。
用户会给你一批带编号的新闻条目（标题+简介+来源）。你的任务：
1. 把报道【同一事件】的条目合并成一个事件（去重）
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
            ids = [i for i in ev.get("ids", []) if isinstance(i, int) and 0 <= i < len(items)]
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
        events = merge_events(llm, events)
    return events


MERGE_SYSTEM = """下面是一批新闻事件标题（带编号）。有些编号可能描述的是同一事件（来自不同批次）。
只输出 JSON 数组：需要合并的编号组，如 [[0,5],[2,9,11]]。没有可合并的就输出 []。不要输出其他文字。"""


def merge_events(llm, events):
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
            events[primary]["ids"].extend(events[g]["ids"])
            for d in DIMS:
                events[primary]["dims"][d] = max(events[primary]["dims"][d],
                                                 events[g]["dims"][d])
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
            * float(tier_mult.get(best_tier, 0.83)) * w
        ev["score"] = int(max(5, min(99, round(raw))))

    events.sort(key=lambda e: e["score"], reverse=True)
    threshold = int(cfg.get("pick_threshold", 68))
    pick_min = int(cfg.get("pick_min", 8))
    pick_max = int(cfg.get("pick_max", 24))
    min_per = cfg.get("min_per_category", 2)

    eligible = [e for e in events if e["score"] >= threshold]
    rest = [e for e in events if e["score"] < threshold]

    picked = []
    # 五类保底：优先从过线的里拿，每类不足再从线下最高分补
    for cat in CATEGORIES:
        cat_pool = ([e for e in eligible if e["category"] == cat] +
                    [e for e in rest if e["category"] == cat])
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
        for e in rest:
            if len(picked) >= pick_min:
                break
            if e not in picked:
                picked.append(e)
    picked = sorted(picked, key=lambda e: e["score"], reverse=True)[:pick_max]
    over = sum(1 for e in picked if e["score"] >= threshold)
    log(f"  阈值 {threshold} 分：过线 {len(eligible)} 个事件，精选 {len(picked)} 条（其中过线 {over}）")

    remaining = [e for e in events if e not in picked]
    secondary = remaining[:cfg["secondary_count"]]
    return picked, secondary


# ----------------------------------------------------------------
# 5. 阶段B：精选深加工
# ----------------------------------------------------------------

ENRICH_SYSTEM = """你是资深新闻主编，为个人读者的"每日信息驾驶舱"加工精选新闻。
用户给你若干事件，每个事件附带一条或多条原始报道（标题+简介+来源）。
对每个事件输出：
- title: 精炼中文标题（≤30字，信息完整，不标题党）
- summary: 一句话事实摘要（≤70字，只说发生了什么，含关键数字）
- why: 为什么重要（≤80字，说清影响面和利害关系）
- watch: 后续关注点（≤60字，接下来看什么信号/节点）
- status: 事件状态，只能是这四个之一：
    已确认（官方发布或多个独立可信来源证实）
    发展中（事件仍在进行，信息还在更新）
    有争议（各方说法明显冲突）
    仅传言（单一来源爆料，未获证实）

只输出 JSON 数组，每个元素：
{"idx": 事件编号, "title": "...", "summary": "...", "why": "...", "watch": "...", "status": "..."}
不要输出任何其他文字。"""


def enrich(llm, picked, items):
    batch_size = 6
    for bi in range(0, len(picked), batch_size):
        batch = picked[bi:bi + batch_size]
        blocks = []
        for j, ev in enumerate(batch):
            srcs = []
            for i in ev["ids"][:4]:
                it = items[i]
                srcs.append(f"  - [{it['source']}|{TYPE_NAMES[it['source_type']]}] "
                            f"{it['title']}：{it['desc'][:200]}")
            blocks.append(f"事件[{bi + j}] {ev['title']}\n" + "\n".join(srcs))
        log(f"  阶段B 批次 {bi // batch_size + 1}: {len(batch)} 个事件")
        result = llm.json_call(ENRICH_SYSTEM, "\n\n".join(blocks))
        for r in result:
            k = r.get("idx")
            if not isinstance(k, int) or not (0 <= k < len(picked)):
                continue
            ev = picked[k]
            ev["title"] = r.get("title", ev["title"])
            ev["summary"] = r.get("summary", "")
            ev["why"] = r.get("why", "")
            ev["watch"] = r.get("watch", "")
            ev["status"] = r.get("status") if r.get("status") in STATUS_SET else "发展中"
    return picked


BRIEF_SYSTEM = """你是新闻主编。根据今天的精选新闻标题列表，写一段 2-3 句的中文"今日导语"，
点出今天最值得注意的 2-3 条主线。只输出导语文字本身，不要任何格式。"""


def write_brief(llm, picked):
    lines = [f"- [{CAT_NAMES[e['category']]}] {e['title']}" for e in picked]
    try:
        resp = llm.client.chat.completions.create(
            model=llm.model, temperature=0.4,
            messages=[{"role": "system", "content": BRIEF_SYSTEM},
                      {"role": "user", "content": "\n".join(lines)}])
        return resp.choices[0].message.content.strip()
    except Exception as e:
        log(f"  导语生成失败: {e}")
        return ""


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
    return {
        "id": f"{tier}-{ids[0]}",
        "tier": tier,
        "category": ev["category"],
        "title": ev.get("title", primary["title"]),
        "summary": ev.get("summary", primary["desc"][:100]),
        "why": ev.get("why", ""),
        "watch": ev.get("watch", ""),
        "status": ev.get("status", ""),
        "score": ev["score"],
        "src_tier": ev.get("tier", ""),
        "source_type": TYPE_NAMES[primary["source_type"]],
        "time": primary["time"],
        "sources": sources[:5],
    }


def write_output(date_str, brief, picked, secondary, items, cfg):
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
    if pub.get("sync_page"):
        shutil.copy2(ROOT / "index.html", news_dir / "index.html")
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
    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    items = fetch_all(sources, cfg)
    if not items:
        log("没有抓到任何内容，退出。")
        sys.exit(1)

    if args.dry_run:
        by_src = {}
        for it in items:
            by_src[it["source"]] = by_src.get(it["source"], 0) + 1
        log("dry-run 完成，各源条数：")
        for k, v in sorted(by_src.items(), key=lambda x: -x[1]):
            print(f"    {k}: {v}")
        return

    if "在这里填" in cfg["llm"]["api_key"]:
        log("错误：请先在 config.yaml 里填写 llm.api_key")
        sys.exit(1)

    llm = LLM(cfg["llm"])

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

    picked, secondary = score_and_select(events, items, cfg)
    log(f"阶段B：精加工 {len(picked)} 条精选 ...")
    enrich(llm, picked, items)
    for ev in secondary:
        ev.setdefault("status", "")
    brief = write_brief(llm, picked)

    write_output(date_str, brief, picked, secondary, items, cfg)

    # ---- 发布前校验：精选非空、输出文件存在且包含当日数据 ----
    _data_dir = Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data"
    out_file = _data_dir / "daily" / f"{date_str}.js"
    if (not picked or not out_file.exists()
            or f'window.NEWS_DATA["{date_str}"]' not in out_file.read_text(encoding="utf-8")):
        log("校验失败：精选为空或输出文件异常，中止发布。")
        sys.exit(2)

    publish_to_blog(cfg, date_str)
    log("完成 ✓  打开 index.html 查看今日日报")


if __name__ == "__main__":
    main()
