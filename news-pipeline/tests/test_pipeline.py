# -*- coding: utf-8 -*-
"""管线纯逻辑回归测试（不调 LLM、不联网）
用法: python news-pipeline/tests/test_pipeline.py
覆盖: 舆论源封顶 / 同源封顶 / 跨批次合并 / 信源健康度 / 跨天事件登记表
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import daily_news as dn

failures = []


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


# ----------------------------------------------------------------
# 1. 舆论源硬约束（score_and_select）
# ----------------------------------------------------------------

def mk_item(sid, stype, tier="T2", cred=6):
    return {"source_id": sid, "source_type": stype, "tier": tier, "credibility": cred}


items = [
    mk_item("hn", "opinion"),             # 0
    mk_item("hn", "opinion"),             # 1
    mk_item("openai", "fact", "T1", 9),   # 2
    mk_item("verge", "fact", "T1.5", 7),  # 3
    mk_item("hn", "opinion"),             # 4
]
full_dims = {d: 10.0 for d in dn.DIMS}
events = [
    {"ids": [0, 1], "category": "tech", "dims": dict(full_dims), "title": "pure opinion"},
    {"ids": [2, 4], "category": "ai", "dims": dict(full_dims), "title": "mixed"},
    {"ids": [3], "category": "tech", "dims": dict(full_dims), "title": "pure fact"},
]
cfg = {
    "pick_threshold": 68, "pick_min": 1, "pick_max": 24,
    "secondary_count": 25, "min_per_category": 2,
    "interest_weights": {}, "scoring": {},
}
picked, secondary = dn.score_and_select(events, items, cfg)
ev_pure = next(e for e in events if e["title"] == "pure opinion")
ev_mixed = next(e for e in events if e["title"] == "mixed")
ev_fact = next(e for e in events if e["title"] == "pure fact")

check("纯opinion事件分数封顶在阈值下", ev_pure["score"] <= 67)
check("纯opinion事件带opinion_only标记", ev_pure["opinion_only"] is True)
check("有事实源交叉的事件不受限", ev_mixed["opinion_only"] is False and ev_mixed["score"] >= 68)
check("纯opinion不进精选(含类目保底)", ev_pure not in picked)
check("纯opinion落入secondary", ev_pure in secondary)
check("mixed与fact事件正常进精选", ev_mixed in picked and ev_fact in picked)

events_low = [
    {"ids": [0], "category": "tech", "dims": {d: 1.0 for d in dn.DIMS}, "title": "op low"},
    {"ids": [3], "category": "tech", "dims": {d: 1.0 for d in dn.DIMS}, "title": "fact low"},
]
picked_low, _ = dn.score_and_select(events_low, items,
                                    dict(cfg, pick_min=2, min_per_category=0))
check("pick_min补位跳过opinion_only", all(not e.get("opinion_only") for e in picked_low))

# 长尾软边角料过滤：整条事件来源都被预筛标 soft -> 不进更多资讯（精选不受影响）
soft_items = [
    {"source_id": "hn", "source_type": "fact", "tier": "T1.5", "credibility": 7, "soft": True},  # 0
    {"source_id": "verge", "source_type": "fact", "tier": "T1.5", "credibility": 7},              # 1
]
soft_events = [
    {"ids": [0], "category": "society", "dims": {d: 5.0 for d in dn.DIMS}, "title": "soft only"},
    {"ids": [1], "category": "society", "dims": {d: 5.0 for d in dn.DIMS}, "title": "normal"},
]
_, sec_s = dn.score_and_select(soft_events, soft_items,
                               dict(cfg, pick_threshold=99, pick_min=0, min_per_category=0))
soft_ev = next(e for e in soft_events if e["title"] == "soft only")
norm_ev = next(e for e in soft_events if e["title"] == "normal")
check("软边角料事件被标 soft", soft_ev["soft"] is True)
check("非软事件不标 soft", norm_ev["soft"] is False)
check("软边角料不进更多资讯", soft_ev not in sec_s)
check("非软事件进更多资讯", norm_ev in sec_s)

# ----------------------------------------------------------------
# 2. 同源封顶（cap_same_source）
# ----------------------------------------------------------------

src_items = [{"source_id": s} for s in
             ["36kr", "36kr", "36kr", "36kr", "36kr", "wscn", "atlantic", "wscn"]]
check("同源5条只留2条", dn.cap_same_source([0, 1, 2, 3, 4], src_items) == [0, 1])
check("混合来源各自封顶", dn.cap_same_source([0, 5, 1, 6, 2, 7, 3], src_items) == [0, 5, 1, 6, 7])
check("不超限时原样保留", dn.cap_same_source([0, 5, 6], src_items) == [0, 5, 6])

# ----------------------------------------------------------------
# 3. 跨批次合并（merge_events）：不抬分、同源封顶、保留主事件标题
# ----------------------------------------------------------------


class StubLLM:
    def json_call(self, system, user):
        return [[0, 1]]


merge_input = [
    {"ids": [6], "category": "society", "title": "主事件",
     "dims": {d: 3.0 for d in dn.DIMS}},
    {"ids": [5, 7, 0, 1, 2], "category": "ai", "title": "被合并事件",
     "dims": {d: 9.0 for d in dn.DIMS}},
]
merged = dn.merge_events(StubLLM(), merge_input, src_items)
check("合并后剩1个事件", len(merged) == 1)
check("维度分保留主事件(不取max)", all(merged[0]["dims"][d] == 3.0 for d in dn.DIMS))
check("合并后ids同源封顶", merged[0]["ids"] == [6, 5, 7, 0, 1])
check("标题保留主事件", merged[0]["title"] == "主事件")

# ----------------------------------------------------------------
# 4. 信源健康度（update_source_health）
# ----------------------------------------------------------------

tmp = Path(tempfile.mkdtemp(prefix="health_test_"))
old_data_dir = os.environ.get("DATA_DIR")
os.environ["DATA_DIR"] = str(tmp)
try:
    stats_ok = {"hn": {"name": "Hacker News", "count": 5, "error": False}}
    stats_err = {"hn": {"name": "Hacker News", "count": 0, "error": True}}

    dn.update_source_health(stats_ok, "2026-07-01")
    dn.update_source_health(stats_err, "2026-07-02")
    dn.update_source_health(stats_err, "2026-07-03")
    print("--- 连续第3天失败，下一行应出现 ::warning:: ↓")
    dn.update_source_health(stats_err, "2026-07-04")

    health = json.loads((tmp / "source_health.json").read_text(encoding="utf-8"))
    check("健康度文件含4天记录", len(health["days"]) == 4)
    check("记录结构正确", health["days"]["2026-07-04"]["hn"] == {"count": 0, "error": True})

    for i in range(5, 21):
        dn.update_source_health(stats_ok, f"2026-07-{i:02d}")
    health = json.loads((tmp / "source_health.json").read_text(encoding="utf-8"))
    check("滚动只保留14天", len(health["days"]) == dn.HEALTH_KEEP_DAYS)
    check("最老日期被清掉", "2026-07-01" not in health["days"])

    dn.update_source_health(stats_err, "2026-07-20")
    health = json.loads((tmp / "source_health.json").read_text(encoding="utf-8"))
    check("同日重跑覆盖", health["days"]["2026-07-20"]["hn"]["error"] is True)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
    if old_data_dir is None:
        os.environ.pop("DATA_DIR", None)
    else:
        os.environ["DATA_DIR"] = old_data_dir

# ----------------------------------------------------------------
# 5. 跨天事件登记表（load_registry / update_registry / match 校验）
# ----------------------------------------------------------------

EV_CFG = {"events": {"match_window_days": 14, "archive_days": 7,
                     "prune_archived_days": 60}}


def mk_pick(title, cat, summary="s", status="发展中"):
    return {"title": title, "category": cat, "summary": summary, "status": status}


def mk_reg_event(eid, title, cat, dates, status="active"):
    return {"event_id": eid, "title": title, "category": cat, "status": status,
            "pinned": False, "first_seen": dates[0], "last_seen": dates[-1],
            "history": [{"date": d, "title": title, "summary": f"{title}@{d}",
                         "news_status": "发展中"} for d in dates]}


tmp = Path(tempfile.mkdtemp(prefix="events_test_"))
try:
    # 冷启动：文件不存在 -> 空表；损坏 -> 重建
    reg = dn.load_registry(tmp)
    check("登记表冷启动为空表", reg == {"version": 1, "events": []})
    (tmp / "events.json").write_text("{broken", encoding="utf-8")
    check("登记表损坏时重建空表", dn.load_registry(tmp)["events"] == [])

    # 全新建：无匹配 -> 每条精选建一个事件，day_count=1
    reg = {"version": 1, "events": []}
    picks = [mk_pick("事件甲", "world"), mk_pick("事件乙", "ai")]
    dn.update_registry(reg, picks, [], [], "2026-07-04", EV_CFG)
    check("新事件全部登记", len(reg["events"]) == 2)
    check("新事件day_count=1", all(p["day_count"] == 1 for p in picks))
    check("新事件带event_id", all(p["event_id"].startswith("evt-20260704-") for p in picks))
    check("新事件不带history_prev", all(p["history_prev"] == [] for p in picks))

    # 同日同标题的两条精选 -> event_id 必须不同（哈希掺入首条原始条目索引）
    reg = {"version": 1, "events": []}
    dup_picks = [dict(mk_pick("同名事件", "world"), ids=[3]),
                 dict(mk_pick("同名事件", "world"), ids=[9])]
    dn.update_registry(reg, dup_picks, [], [], "2026-07-04", EV_CFG)
    check("同日同标题event_id不撞", dup_picks[0]["event_id"] != dup_picks[1]["event_id"])

    # 续接：昨日事件匹配上 -> day_count=2、last_seen 更新、history_prev 含昨日
    reg = {"version": 1, "events": [mk_reg_event("evt-x", "事件甲", "world", ["2026-07-03"])]}
    active = [e for e in reg["events"]]
    picks = [mk_pick("事件甲后续", "world")]
    dn.update_registry(reg, picks, [(0, 0)], active, "2026-07-04", EV_CFG)
    check("续接后day_count=2", picks[0]["day_count"] == 2)
    check("续接沿用event_id", picks[0]["event_id"] == "evt-x")
    check("last_seen更新", reg["events"][0]["last_seen"] == "2026-07-04")
    check("history_prev只含往日", [h["date"] for h in picks[0]["history_prev"]] == ["2026-07-03"])
    check("登记表不新增事件", len(reg["events"]) == 1)

    # 同日重跑幂等：再跑一次同日期，day_count 不涨、history 不重复
    picks2 = [mk_pick("事件甲后续v2", "world")]
    active2 = [e for e in reg["events"]
               if any(h["date"] != "2026-07-04" for h in e["history"])]
    dn.update_registry(reg, picks2, [(0, 0)], active2, "2026-07-04", EV_CFG)
    check("同日重跑day_count不变", picks2[0]["day_count"] == 2)
    check("同日重跑history不重复", len(reg["events"][0]["history"]) == 2)

    # 同日重跑清理孤儿：本日新建的事件在重跑时被移除重建
    reg = {"version": 1, "events": [mk_reg_event("evt-y", "事件丙", "tech", ["2026-07-04"])]}
    picks3 = [mk_pick("事件丙", "tech")]
    dn.update_registry(reg, picks3, [], [], "2026-07-04", EV_CFG)
    check("重跑后本日新建事件不留孤儿", len(reg["events"]) == 1)
    check("重跑重建day_count=1", picks3[0]["day_count"] == 1)

    # 归档：last_seen 超过 archive_days 的 active 事件被归档
    reg = {"version": 1, "events": [mk_reg_event("evt-old", "旧事件", "world", ["2026-06-25"])]}
    dn.update_registry(reg, [], None, [], "2026-07-04", EV_CFG)
    check("超期事件被归档", reg["events"][0]["status"] == "archived")

    # 剪枝：archived 超过 prune_archived_days 的事件被删除
    reg = {"version": 1, "events": [mk_reg_event("evt-ancient", "远古事件", "world",
                                                 ["2026-04-01"], status="archived")]}
    dn.update_registry(reg, [], None, [], "2026-07-04", EV_CFG)
    check("远古归档事件被剪枝", len(reg["events"]) == 0)

    # 降级：pairs=None（LLM 失败）-> 全部按新事件，不崩溃
    reg = {"version": 1, "events": [mk_reg_event("evt-x", "事件甲", "world", ["2026-07-03"])]}
    picks4 = [mk_pick("事件甲后续", "world")]
    dn.update_registry(reg, picks4, None, reg["events"][:], "2026-07-04", EV_CFG)
    check("LLM失败降级为新事件", picks4[0]["day_count"] == 1 and len(reg["events"]) == 2)

    # match 结果校验：跨类目/越界/重复对被丢弃（StubLLM 直接喂违规输出）
    class MatchStub:
        def __init__(self, matches):
            self._m = matches

        def json_call(self, system, user):
            return {"matches": self._m}

    active = [mk_reg_event("evt-a", "A事件", "world", ["2026-07-03"]),
              mk_reg_event("evt-b", "B事件", "ai", ["2026-07-03"])]
    picks5 = [mk_pick("A后续", "world"), mk_pick("B后续", "tech")]
    pairs = dn.match_events_llm(MatchStub([
        {"today": 0, "registry": 0},   # 合法
        {"today": 1, "registry": 1},   # 跨类目（tech vs ai）应丢弃
        {"today": 0, "registry": 1},   # today 重复应丢弃
        {"today": 9, "registry": 0},   # 越界应丢弃
    ]), active, picks5)
    check("匹配校验只留合法对", pairs == [(0, 0)])

    class BoomStub:
        def json_call(self, system, user):
            raise RuntimeError("boom")

    check("匹配调用异常返回None", dn.match_events_llm(BoomStub(), active, picks5) is None)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ----------------------------------------------------------------
# 6. 偏好学习（source_penalties / apply_pins / 画像 / 兴趣拟合 / 追踪区）
# ----------------------------------------------------------------

fb = [
    {"ts": "2026-07-01T08:00:00Z", "action": "low_quality_source", "source": "某源"},
    {"ts": "2026-07-01T09:00:00Z", "action": "low_quality_source", "source": "某源"},  # 同日只记一次
    {"ts": "2026-07-02T08:00:00Z", "action": "low_quality_source", "source": "某源"},
    {"ts": "2026-01-01T08:00:00Z", "action": "low_quality_source", "source": "旧源"},  # 超90天窗口
    {"ts": "2026-07-02T08:00:00Z", "action": "not_interested", "source": "别源"},      # 非该动作
]
pens = dn.source_penalties(fb, "2026-07-04")
check("来源降权按自然日计次", pens.get("某源") == 0.8)
check("超窗口反馈不计", "旧源" not in pens)
check("其他动作不计", "别源" not in pens)
many = [{"ts": f"2026-06-{d:02d}T08:00:00Z", "action": "low_quality_source", "source": "s"}
        for d in range(1, 20)]
check("降权下限0.7", dn.source_penalties(many, "2026-07-04")["s"] == 0.7)

reg = {"version": 1, "events": [
    {"event_id": "evt-1", "pinned": False},
    {"event_id": "evt-2", "pinned": True},
]}
pins = [
    {"ts": "2026-07-01T08:00:00Z", "action": "track", "event_id": "evt-1"},
    {"ts": "2026-07-02T08:00:00Z", "action": "untrack", "event_id": "evt-1"},
    {"ts": "2026-07-03T08:00:00Z", "action": "track", "event_id": "evt-1"},  # 最后一次为准
    {"ts": "2026-07-01T08:00:00Z", "action": "untrack", "event_id": "evt-2"},
    {"ts": "2026-07-01T08:00:00Z", "action": "track", "event_id": "evt-404"},  # 不存在的事件忽略
]
changed = dn.apply_pins(reg, pins)
check("track/untrack取最后一次", reg["events"][0]["pinned"] is True)
check("untrack解除钉选", reg["events"][1]["pinned"] is False)
check("变更计数", changed == 2)
check("空反馈不变更", dn.apply_pins(reg, []) == 0)

check("默认画像判空", dn.profile_has_content(dn.PROFILE_DEFAULT) is False)
check("有要点行判非空", dn.profile_has_content("## 更关注\n- AI 模型价格") is True)

tmp = Path(tempfile.mkdtemp(prefix="profile_test_"))
try:
    # 目录不存在时自动创建（本地 fresh clone 首跑不崩）
    missing = tmp / "not_yet" / "data"
    dn.update_profile(None, missing, [], [])
    check("画像落盘自动建目录", (missing / "interest_profile.md").exists())

    # 无新反馈：不调 LLM（llm=None 也不崩）、落盘默认画像
    text = dn.update_profile(None, tmp, [], [])
    check("无反馈时落盘默认画像", (tmp / "interest_profile.md").exists())
    check("无反馈时返回默认画像", "## 更关注" in text)

    # 反馈早于 marker：同样不调 LLM
    (tmp / "interest_profile.md").write_text(
        "# 兴趣画像\n<!-- last_feedback_ts: 2026-07-03T00:00:00Z -->\n\n## 更关注\n- 旧偏好\n\n## 不关注\n（暂无）\n",
        encoding="utf-8")
    old_fb = [{"ts": "2026-07-02T08:00:00Z", "action": "not_interested", "title": "t"}]
    text = dn.update_profile(None, tmp, old_fb, [])
    check("旧反馈不触发蒸馏", "- 旧偏好" in text)

    # 「只是今天不想看」且无备注：不入画像
    skip_fb = [{"ts": "2026-07-04T08:00:00Z", "action": "not_interested",
                "reasons": ["只是今天不想看"], "title": "t"}]
    text = dn.update_profile(None, tmp, skip_fb, [])
    check("今天不想看不入画像", "- 旧偏好" in text)

    # 蒸馏失败（llm=None 触发异常）：保留旧画像、marker 不推进
    new_fb = [{"ts": "2026-07-04T08:00:00Z", "action": "more_like_this",
               "title": "新话题", "category": "ai"}]
    text = dn.update_profile(None, tmp, new_fb, [])
    saved = (tmp / "interest_profile.md").read_text(encoding="utf-8")
    check("蒸馏失败保留旧画像", "- 旧偏好" in text and "2026-07-03T00:00:00Z" in saved)

    # 蒸馏成功：marker 推进到最新反馈 ts、内容更新
    class ProfileStub:
        model = "stub"

        class client:
            class chat:
                class completions:
                    @staticmethod
                    def create(**kw):
                        class R:
                            pass
                        r = R()
                        msg = type("M", (), {"content": "# 兴趣画像\n\n## 更关注\n- 旧偏好\n- AI新话题\n\n## 不关注\n（暂无）\n\n## 来源印象\n（暂无）"})
                        r.choices = [type("C", (), {"message": msg})]
                        return r

    text = dn.update_profile(ProfileStub(), tmp, new_fb, [])
    saved = (tmp / "interest_profile.md").read_text(encoding="utf-8")
    check("蒸馏成功更新画像", "- AI新话题" in saved)
    check("marker推进", "2026-07-04T08:00:00Z" in saved)
finally:
    shutil.rmtree(tmp, ignore_errors=True)


class FitStub:
    def json_call(self, system, user):
        return {"fits": [{"idx": 0, "fit": 10}, {"idx": 1, "fit": 0},
                         {"idx": 2, "fit": 5}, {"idx": 9, "fit": 10},  # 越界忽略
                         {"idx": "x", "fit": 3}]}                       # 脏数据忽略


fit_events = [{"title": "a", "category": "ai"}, {"title": "b", "category": "world"},
              {"title": "c", "category": "tech"}]
dn.interest_fit(FitStub(), "## 更关注\n- 某主题", fit_events)
check("拟合上限(默认span0.30)=1.30", fit_events[0]["interest_mult"] == 1.30)
check("拟合下限(默认span0.30)=0.70", fit_events[1]["interest_mult"] == 0.70)
check("中性5分=1.0", fit_events[2]["interest_mult"] == 1.0)

# span 可调：传 0.15 时回到旧的 ±0.15 幅度
fit_events_span = [{"title": "a", "category": "ai"}, {"title": "b", "category": "world"}]
dn.interest_fit(FitStub(), "## 更关注\n- 某主题", fit_events_span, span=0.15)
check("span=0.15上限1.15", fit_events_span[0]["interest_mult"] == 1.15)
check("span=0.15下限0.85", fit_events_span[1]["interest_mult"] == 0.85)


# ---- write_brief 结构化主线：成员 id 校验 / 跨 tier / 上限 3 / 失败降级 ----
class BriefStub:
    def json_call(self, system, user):
        return {"synthesis": "今日总纲", "themes": [
            {"title": "极端天气", "one_liner": "多地灾害",
             "member_ids": ["pick-10", "more-20", "bogus-x"]},   # bogus 过滤
            {"title": "空主线", "one_liner": "无成员", "member_ids": ["bogus-y"]},  # 无合法成员->丢
            {"title": "T2", "one_liner": "x", "member_ids": ["pick-11", "pick-10"]},
            {"title": "T3", "one_liner": "x", "member_ids": ["more-20", "pick-11"]},
            {"title": "T4超额", "one_liner": "x", "member_ids": ["pick-10"]},       # 超3条->截断
        ]}


brief_picked = [{"ids": [10], "category": "world", "title": "台风", "why": "w"},
                {"ids": [11], "category": "society", "title": "热浪", "why": "w"}]
brief_secondary = [{"ids": [20], "category": "world", "title": "野火"}]
synth, themes = dn.write_brief(BriefStub(), brief_picked, brief_secondary)
check("主线synthesis正常", synth == "今日总纲")
check("主线最多3条", len(themes) == 3)
check("非法id被过滤且跨tier", themes[0]["member_ids"] == ["pick-10", "more-20"])
check("无合法成员的主线被丢弃", all(t["title"] != "空主线" for t in themes))


class BriefBoom:
    def json_call(self, system, user):
        raise RuntimeError("boom")


check("主线生成失败降级为空", dn.write_brief(BriefBoom(), brief_picked, brief_secondary) == ("", []))

fit_events2 = [{"title": "a", "category": "ai"}]
dn.interest_fit(FitStub(), dn.PROFILE_DEFAULT, fit_events2)
check("空画像不打分", "interest_mult" not in fit_events2[0])


class FitBoom:
    def json_call(self, system, user):
        raise RuntimeError("boom")


fit_events3 = [{"title": "a", "category": "ai"}]
dn.interest_fit(FitBoom(), "## 更关注\n- 某主题", fit_events3)
check("拟合失败保持中性", "interest_mult" not in fit_events3[0])

reg = {"version": 1, "events": [
    mk_reg_event("evt-p1", "钉选未进精选", "world", ["2026-07-02", "2026-07-03"]),
    mk_reg_event("evt-p2", "钉选已进精选", "ai", ["2026-07-03", "2026-07-04"]),
    mk_reg_event("evt-p3", "未钉选", "tech", ["2026-07-03"]),
    mk_reg_event("evt-p4", "钉选但已归档", "world", ["2026-06-01"], status="archived"),
]}
reg["events"][0]["pinned"] = True
reg["events"][1]["pinned"] = True
reg["events"][3]["pinned"] = True
tracking = dn.build_tracking(reg, [{"event_id": "evt-p2"}], "2026-07-04")
check("追踪区只含钉选未进精选的活跃事件",
      [t["event_id"] for t in tracking] == ["evt-p1"])
check("追踪区day_count正确", tracking[0]["day_count"] == 2)
check("追踪区updated_today标记", tracking[0]["updated_today"] is False)
check("追踪区history倒序", [h["date"] for h in tracking[0]["history"]] ==
      ["2026-07-03", "2026-07-02"])

# ----------------------------------------------------------------
# 7. 三期：深读频道 / feed.xml / 搜索索引
# ----------------------------------------------------------------

check("阅读时长-中文", dn.estimate_read_minutes({"content_chars": 4000, "content_words": 0}, "zh") == 10)
check("阅读时长-英文", dn.estimate_read_minutes({"content_chars": 0, "content_words": 2200}, "en") == 10)
check("阅读时长下限3", dn.estimate_read_minutes({"content_chars": 100}, "zh") == 3)
check("阅读时长上限60", dn.estimate_read_minutes({"content_words": 999999}, "en") == 60)

tmp = Path(tempfile.mkdtemp(prefix="phase3_test_"))
old_data_dir = os.environ.get("DATA_DIR")
os.environ["DATA_DIR"] = str(tmp)
orig_fetch_rss = dn.fetch_rss
try:
    # --- deep_seen 冷启动与同日剔除 ---
    seen = dn.load_deep_seen(tmp, "2026-07-05")
    check("deep_seen冷启动", seen == {"version": 1, "urls": {}})
    (tmp / "deep_seen.json").write_text(json.dumps(
        {"version": 1, "urls": {"https://a.com/1": "2026-07-04",
                                "https://a.com/2": "2026-07-05"}}), encoding="utf-8")
    seen = dn.load_deep_seen(tmp, "2026-07-05")
    check("deep_seen剔除当日(重跑幂等)", list(seen["urls"]) == ["https://a.com/1"])

    # --- deep_channel：monkeypatch fetch_rss，离线跑选择逻辑 ---
    fake_articles = [
        {"title": "Deep A", "url": "https://a.com/1", "desc": "d", "time": "2026-07-05T00:00:00+00:00",
         "source": "SrcX", "source_id": "x", "source_type": "analysis", "tier": "T2",
         "credibility": 7, "content_chars": 0, "content_words": 2200},   # 已推荐过 -> 应被去重
        {"title": "Deep B & <best>", "url": "https://a.com/3", "desc": "d", "time": "2026-07-05T00:00:00+00:00",
         "source": "SrcX", "source_id": "x", "source_type": "analysis", "tier": "T2",
         "credibility": 7, "content_chars": 0, "content_words": 4400},
        {"title": "Deep C", "url": "https://a.com/4", "desc": "d", "time": "2026-07-05T00:00:00+00:00",
         "source": "SrcX", "source_id": "x", "source_type": "analysis", "tier": "T2",
         "credibility": 7, "content_chars": 0, "content_words": 440},
    ]
    dn.fetch_rss = lambda src, ws, mx: (list(fake_articles) if src["id"] == "simonwillison" else [], False)

    class DeepStub:
        def json_call(self, system, user):
            # 去重后候选只剩 B(0) C(1)：B 过线，C 不过线
            return [{"idx": 0, "score": 9, "title_zh": "深读B", "brief": "b", "why": "w"},
                    {"idx": 1, "score": 4, "title_zh": "深读C", "brief": "b", "why": "w"}]

    deep = dn.deep_channel(DeepStub(), {"deep": {"enabled": True, "pick_threshold": 7,
                                                 "pick_max": 3, "seen_keep_days": 60}},
                           "2026-07-05")
    check("deep已推荐URL被去重且阈值过滤", [d["url"] for d in deep] == ["https://a.com/3"])
    check("deep字段完整", deep[0]["title_zh"] == "深读B" and deep[0]["read_minutes"] == 20
          and deep[0]["id"].startswith("deep-"))
    seen = json.loads((tmp / "deep_seen.json").read_text(encoding="utf-8"))
    check("deep推荐写回seen", seen["urls"].get("https://a.com/3") == "2026-07-05")

    class DeepBoom:
        def json_call(self, system, user):
            raise RuntimeError("boom")

    check("deep LLM失败返回空", dn.deep_channel(DeepBoom(), {"deep": {"enabled": True}},
                                                "2026-07-05") == [])
    check("deep禁用返回空", dn.deep_channel(DeepStub(), {"deep": {"enabled": False}},
                                            "2026-07-05") == [])

    # --- papers_channel：monkeypatch fetch_hf_papers，离线跑选择逻辑 ---
    # 预置 papers_seen：.../1 记为往日(非当日) -> 应被去重；当日重跑幂等由 load 剔除同日
    (tmp / "papers_seen.json").write_text(json.dumps(
        {"version": 1, "urls": {"https://huggingface.co/papers/1": "2026-07-04"}}),
        encoding="utf-8")
    fake_papers = [
        {"title": "Paper Seen", "url": "https://huggingface.co/papers/1", "arxiv_id": "1",
         "summary": "s", "upvotes": 100, "comments": 2, "has_code": True},   # 已推荐 -> 去重
        {"title": "Paper B <best>", "url": "https://huggingface.co/papers/3", "arxiv_id": "3",
         "summary": "s", "upvotes": 80, "comments": 1, "has_code": True},
        {"title": "Paper C", "url": "https://huggingface.co/papers/4", "arxiv_id": "4",
         "summary": "s", "upvotes": 50, "comments": 0, "has_code": False},
    ]
    orig_fetch_papers = dn.fetch_hf_papers
    dn.fetch_hf_papers = lambda date_str, days=2: list(fake_papers)

    class PapersStub:
        def json_call(self, system, user):
            # 去重+点赞排序后候选：B(idx0,👍80) C(idx1,👍50)；B 过线、C 不过线
            return [{"idx": 0, "score": 9, "title_zh": "论文B", "brief": "b", "why": "w"},
                    {"idx": 1, "score": 4, "title_zh": "论文C", "brief": "b", "why": "w"}]

    try:
        pcfg = {"papers": {"enabled": True, "lookback_days": 2, "max_candidates": 30,
                           "pick_threshold": 7, "pick_max": 4, "seen_keep_days": 45}}
        papers = dn.papers_channel(PapersStub(), pcfg, "2026-07-05")
        check("papers已推荐URL被去重且阈值过滤",
              [p["url"] for p in papers] == ["https://huggingface.co/papers/3"])
        check("papers字段完整", papers[0]["title_zh"] == "论文B" and papers[0]["upvotes"] == 80
              and papers[0]["has_code"] is True and papers[0]["id"] == "paper-3")
        pseen = json.loads((tmp / "papers_seen.json").read_text(encoding="utf-8"))
        check("papers推荐写回seen", pseen["urls"].get("https://huggingface.co/papers/3") == "2026-07-05")

        class PapersBoom:
            def json_call(self, system, user):
                raise RuntimeError("boom")

        check("papers LLM失败返回空",
              dn.papers_channel(PapersBoom(), pcfg, "2026-07-05") == [])
        check("papers禁用返回空",
              dn.papers_channel(PapersStub(), {"papers": {"enabled": False}}, "2026-07-05") == [])
    finally:
        dn.fetch_hf_papers = orig_fetch_papers

    # --- write_feed ---
    daily = tmp / "daily"
    daily.mkdir(parents=True, exist_ok=True)

    def fake_daily(date, items, deep_items=None):
        payload = {"date": date, "generated_at": f"{date}T05:00:00+00:00",
                   "brief": "b", "stats": {}, "items": items}
        if deep_items:
            payload["deep"] = deep_items
        js = ("window.NEWS_DATA = window.NEWS_DATA || {};\n"
              f'window.NEWS_DATA["{date}"] = ' + json.dumps(payload, ensure_ascii=False) + ";\n")
        (daily / f"{date}.js").write_text(js, encoding="utf-8")

    pick = {"id": "pick-1", "tier": "pick", "category": "tech",
            "title": "A&B <公司> 收购", "summary": "s", "why": "w", "watch": "",
            "time": "2026-07-05T01:00:00+00:00",
            "sources": [{"name": "S&P", "url": "https://s.com/a?x=1&y=2"}]}
    more = {"id": "more-9", "tier": "more", "category": "tech", "title": "m",
            "summary": "", "time": "", "sources": []}
    fake_daily("2026-07-05", [pick, more],
               [{"id": "deep-abc", "title": "T", "title_zh": "深读题", "url": "https://d.com/1",
                 "source": "SrcX", "lang": "en", "brief": "b", "why": "w", "read_minutes": 12}])
    fake_daily("2026-06-01", [dict(pick, id="pick-old")])  # 超出 feed 窗口(7天)的旧文件

    dn.write_feed(tmp, "2026-07-05", {"feed_days": 7, "site_url": "https://aoiblog.top"})
    feed = (tmp / "feed.xml").read_text(encoding="utf-8")
    check("feed含精选item", "2026-07-05:pick-1" in feed)
    check("feed排除more", "more-9" not in feed)
    check("feed含深读item", "【深读】深读题" in feed and "2026-07-05:deep-abc" in feed)
    check("feed标题转义", "A&amp;B &lt;公司&gt; 收购" in feed)
    check("feed链接转义", "https://s.com/a?x=1&amp;y=2" in feed)
    check("feed窗口截断", "pick-old" in feed)  # 6-01 仍在最近7个文件内（只有2个文件）
    import xml.dom.minidom
    xml.dom.minidom.parseString(feed)
    check("feed是合法XML", True)

    # --- update_search_index ---
    cfg3 = {"search_index_days": 180}
    dn.update_search_index(tmp, "2026-07-05", cfg3)
    idx = json.loads((tmp / "search_index.js").read_text(encoding="utf-8")
                     .split(" = ", 1)[1].rstrip().rstrip(";"))
    n1 = len(idx)
    check("索引冷启动重建含双日", {r[0] for r in idx} == {"2026-07-05", "2026-06-01"})
    check("索引含deep行", any(r[2] == "deep" for r in idx))
    dn.update_search_index(tmp, "2026-07-05", cfg3)
    idx2 = json.loads((tmp / "search_index.js").read_text(encoding="utf-8")
                      .split(" = ", 1)[1].rstrip().rstrip(";"))
    check("索引同日重跑幂等", len(idx2) == n1)
    dn.update_search_index(tmp, "2026-07-05", {"search_index_days": 10})
    idx3 = json.loads((tmp / "search_index.js").read_text(encoding="utf-8")
                      .split(" = ", 1)[1].rstrip().rstrip(";"))
    check("索引按天数剪枝", {r[0] for r in idx3} == {"2026-07-05"})
finally:
    dn.fetch_rss = orig_fetch_rss
    shutil.rmtree(tmp, ignore_errors=True)
    if old_data_dir is None:
        os.environ.pop("DATA_DIR", None)
    else:
        os.environ["DATA_DIR"] = old_data_dir

# ----------------------------------------------------------------
# 7.5 逐源直连适配器 + 舆论观察（离线，monkeypatch 网络层）
# ----------------------------------------------------------------


class _FakeResp:
    def __init__(self, text="", data=None):
        self.text = text
        self._data = data

    def json(self):
        return self._data


# --- fetch_thepaper_list：__NEXT_DATA__ 解析 / 时间窗 / 脏数据 ---
_now = dn.datetime.now(dn.timezone.utc)
_fresh_ms = int((_now - dn.timedelta(hours=1)).timestamp() * 1000)
_old_ms = int((_now - dn.timedelta(hours=999)).timestamp() * 1000)
_fake_next = {"props": {"pageProps": {"data": {"list": [
    {"name": "新文章", "contId": "111", "pubTimeLong": _fresh_ms},
    {"name": "旧文章", "contId": "222", "pubTimeLong": _old_ms},   # 窗口外 -> 丢
    {"name": "", "contId": "333", "pubTimeLong": _fresh_ms},       # 空标题 -> 丢
    {"name": "无时间", "contId": "444"},                            # 无时间戳 -> 丢
]}}}}
_fake_html = ('<html><script id="__NEXT_DATA__" type="application/json">'
              + json.dumps(_fake_next, ensure_ascii=False) + '</script></html>')
_src_tp = {"id": "tp-edu", "name": "澎湃·教育家", "url": "https://x/list_25487",
           "source_type": "fact", "tier": "T1.5", "credibility": 7}
_ws = _now - dn.timedelta(hours=26)

orig_http_get = dn.http_get
dn.http_get = lambda url, **kw: _FakeResp(text=_fake_html)
try:
    got, err = dn.fetch_thepaper_list(_src_tp, _ws, 18)
    check("thepaper_list 只留窗口内且字段齐", not err and len(got) == 1
          and got[0]["title"] == "新文章"
          and got[0]["url"].endswith("newsDetail_forward_111")
          and got[0]["tier"] == "T1.5")
    dn.http_get = lambda url, **kw: (_ for _ in ()).throw(IOError("down"))
    got2, err2 = dn.fetch_thepaper_list(_src_tp, _ws, 18)
    check("thepaper_list 抓取失败返回 error", got2 == [] and err2 is True)
finally:
    dn.http_get = orig_http_get

# --- fetch_bilibili_hot（monkeypatch http_get）---
dn.http_get = lambda url, **kw: _FakeResp(data={"data": {"trending": {"list": [
    {"keyword": "话题A"}, {"show_name": "话题B"}, {}]}}})
try:
    bl = dn.fetch_bilibili_hot()
    check("B站热搜解析+过滤空词", [b["word"] for b in bl] == ["话题A", "话题B"]
          and bl[0]["platform"] == "B站")
finally:
    dn.http_get = orig_http_get


# --- fetch_weibo_hot（monkeypatch requests.Session：握手 + 过滤广告）---
class _FakeSession:
    def __init__(self):
        self.headers = {}

    def post(self, url, **kw):
        return _FakeResp(text='{"tid":"T123"}')

    def get(self, url, **kw):
        if "hotSearch" in url:
            return _FakeResp(data={"data": {"realtime": [
                {"word": "热词1", "num": "999"},
                {"word": "广告词", "is_ad": 1},
                {"word": "热词2"}]}})
        return _FakeResp(text="")


orig_session = dn.requests.Session
dn.requests.Session = _FakeSession
try:
    wb = dn.fetch_weibo_hot()
    check("微博热搜握手+过滤广告", [w["word"] for w in wb] == ["热词1", "热词2"]
          and wb[0]["hot"] == 999)
finally:
    dn.requests.Session = orig_session

# --- fetch_pulse_all 分发（开关 / 未知 type 跳过）---
orig_pf = dn.PULSE_FETCHERS
dn.PULSE_FETCHERS = {
    "weibo_hot": lambda: [{"platform": "微博", "word": "w", "hot": 1, "url": "u"}],
    "bilibili_hot": lambda: []}
try:
    pl = dn.fetch_pulse_all({"pulse_sources": [
        {"id": "a", "name": "微博热搜", "type": "weibo_hot", "enabled": True},
        {"id": "b", "name": "B站热搜", "type": "bilibili_hot", "enabled": True},
        {"id": "c", "name": "关掉的", "type": "weibo_hot", "enabled": False},
        {"id": "d", "name": "未知型", "type": "nope", "enabled": True}]})
    check("pulse_all 分发+开关+未知type跳过", len(pl) == 1 and pl[0]["word"] == "w")
    check("pulse_all 无配置返回空", dn.fetch_pulse_all({}) == [])
finally:
    dn.PULSE_FETCHERS = orig_pf

# --- apply_pulse_bonus：4字连片命中 / 不命中 / 关闭 ---
_pb_items = [{"title": "台风巴威登陆浙江沿海"}, {"title": "某公司发布新模型"}]
_pb_events = [{"ids": [0], "title": "台风巴威影响华东"},
              {"ids": [1], "title": "新模型发布"}]
_pb_pulse = [{"platform": "微博", "word": "台风巴威又改路线了", "hot": 1, "url": ""}]
hits = dn.apply_pulse_bonus(_pb_events, _pb_items, _pb_pulse,
                            {"opinion": {"cooccur_bonus": 1.08}})
check("co-occurrence 实体连片命中加乘数", hits == 1
      and _pb_events[0].get("pulse_mult") == 1.08
      and "pulse_mult" not in _pb_events[1])
check("co-occurrence bonus=1.0 关闭",
      dn.apply_pulse_bonus(_pb_events, _pb_items, _pb_pulse,
                           {"opinion": {"cooccur_bonus": 1.0}}) == 0)
check("co-occurrence 空热榜为0",
      dn.apply_pulse_bonus(_pb_events, _pb_items, [], {"opinion": {}}) == 0)


# --- opinion_pulse：挑选 / 重复与越界过滤 / 禁用 / LLM 失败 ---
class OpStub:
    def json_call(self, system, user):
        assert "今日热榜" in user
        return [{"idx": 0, "title": "话题一", "why_hot": "w", "emotion": "e", "mechanism": "m"},
                {"idx": 0, "title": "重复"},
                {"idx": 9, "title": "越界"},
                {"idx": 1, "title": "话题二", "why_hot": "w2"}]


_op_pulse = [{"platform": "微博", "word": "词A", "hot": 1, "url": "https://s"},
             {"platform": "B站", "word": "词B", "hot": 0, "url": ""}]
ops = dn.opinion_pulse(OpStub(), {"opinion": {"enabled": True, "pick_max": 3}}, _op_pulse)
check("舆论观察挑选+去重+越界过滤", len(ops) == 2 and ops[0]["title"] == "话题一"
      and ops[0]["platform"] == "微博" and ops[1]["word"] == "词B"
      and ops[0]["id"].startswith("op-"))
check("舆论观察禁用返回空",
      dn.opinion_pulse(OpStub(), {"opinion": {"enabled": False}}, _op_pulse) == [])
check("舆论观察空热榜返回空",
      dn.opinion_pulse(OpStub(), {"opinion": {"enabled": True}}, []) == [])


class OpBoom:
    def json_call(self, system, user):
        raise RuntimeError("boom")


check("舆论观察 LLM失败返回空",
      dn.opinion_pulse(OpBoom(), {"opinion": {"enabled": True}}, _op_pulse) == [])

# ----------------------------------------------------------------
# 8. 英语单词本（normalize / 去重 / 挑词 / 手动词补全）
# ----------------------------------------------------------------

check("词元归一去噪", dn.normalize_word("  Running! ") == "running")
check("词元归一空串", dn.normalize_word("2026") == "")

vocab_cfg = {"vocab": {"daily_min": 6, "daily_max": 10}}
v_items = [
    {"title": "Sanctions imposed on exports", "desc": "unprecedented scrutiny",
     "source_type": "fact", "credibility": 9},
    {"title": "Ceasefire talks resume", "desc": "resilience amid tension",
     "source_type": "fact", "credibility": 8},
]
v_picked = [{"ids": [0], "title": "中文A", "category": "world"},
            {"ids": [1], "title": "中文B", "category": "ai"}]


class VocabStub:
    def json_call(self, system, user):
        return [
            {"word": "Scrutiny", "phonetic": "/ˈskruːtɪni/", "pos": "n.",
             "sense_zh": "审查", "example_en": "E1", "item_id": 0},
            {"word": "scrutiny", "phonetic": "", "pos": "n.",           # 同词元重复 -> 丢
             "sense_zh": "审查", "example_en": "E1b", "item_id": 0},
            {"word": "resilience", "phonetic": "", "pos": "n.",         # 已收录 -> 丢
             "sense_zh": "韧性", "example_en": "E2", "item_id": 1},
            {"word": "ceasefire", "phonetic": "/ˈsiːsfaɪə/", "pos": "n.",
             "sense_zh": "停火", "example_en": "E3", "item_id": 1},
            {"word": "", "item_id": 0},                                 # 空词 -> 丢
        ]


cards = dn.extract_vocab(VocabStub(), v_picked, v_items, {"resilience"}, vocab_cfg)
lemmas = [c["lemma"] for c in cards]
check("挑词按词元去重+跳过已收录", lemmas == ["scrutiny", "ceasefire"])
check("挑词回链 item_id 对应精选", cards[0]["item_id"] == "pick-0" and cards[1]["item_id"] == "pick-1")
check("挑词保留原词面", cards[0]["word"] == "Scrutiny")
check("挑词带语境标题", cards[1]["item_title"] == "中文B")


class VocabEnrichStub:
    def json_call(self, system, user):
        return [
            {"word": "scrutiny", "phonetic": "/ˈskruːtɪni/", "pos": "n.",
             "sense_zh": "审查", "example_en": "E"},
            {"word": "run", "phonetic": "/rʌn/", "pos": "v.",
             "sense_zh": "运行", "example_en": "E"},
        ]


book_e = {"version": 1, "words": [{"word": "run", "lemma": "run"}],
          "pending": [{"word": "scrutiny", "date": "2026-07-06", "item_id": "pick-3"},
                      {"word": "run"}]}      # 与已有词重复 -> 补全时丢
n_enriched = dn.enrich_pending(VocabEnrichStub(), book_e)
check("手动词补全数量(去重后)", n_enriched == 1)
check("补全后 pending 清空", book_e["pending"] == [])
new_word = next((w for w in book_e["words"] if w["lemma"] == "scrutiny"), None)
check("补全词入册且标 manual", new_word is not None and new_word["source"] == "manual")
check("补全词保留来源回链", new_word["item_id"] == "pick-3")
check("补全空 pending 返回0", dn.enrich_pending(VocabEnrichStub(), {"words": [], "pending": []}) == 0)


class VocabBoom:
    def json_call(self, system, user):
        raise RuntimeError("boom")


book_boom = {"version": 1, "words": [], "pending": [{"word": "keep"}]}
check("补全 LLM 失败保留 pending", dn.enrich_pending(VocabBoom(), book_boom) == 0
      and book_boom["pending"] == [{"word": "keep"}])
check("挑词 LLM 失败返回空", dn.extract_vocab(VocabBoom(), v_picked, v_items, set(), vocab_cfg) == [])

tmp = Path(tempfile.mkdtemp(prefix="vocab_test_"))
try:
    check("单词本冷启动为空册",
          dn.load_vocab_book(tmp) == {"version": 1, "words": [], "pending": []})
    (tmp / dn.VOCAB_BOOK_FILE).write_text("{broken", encoding="utf-8")
    check("单词本损坏重建空册", dn.load_vocab_book(tmp)["words"] == [])

    # 全量去重集：历史 vocab/<date>.js ∪ 单词本 words+pending
    vdir = tmp / "vocab"
    vdir.mkdir(parents=True, exist_ok=True)
    dn.write_vocab("2026-07-05", [{"word": "Tariff", "lemma": "tariff"}], tmp)
    book_seen = {"words": [{"word": "scrutiny", "lemma": "scrutiny"}],
                 "pending": [{"word": "ceasefire"}]}
    seen = dn.collect_seen_lemmas(tmp, book_seen)
    check("去重集含历史挑词", "tariff" in seen)
    check("去重集含单词本词与pending", "scrutiny" in seen and "ceasefire" in seen)

    # write_vocab 落盘可被前端壳解析
    payload_src = (vdir / "2026-07-05.js").read_text(encoding="utf-8")
    import re as _re
    m = _re.search(r"window\.VOCAB_DATA\[[^\]]+\] = (\{.*\});", payload_src, _re.S)
    check("单词候选文件是可解析壳", m is not None
          and json.loads(m.group(1))["words"][0]["word"] == "Tariff")

    # ---- 周综述：write_weekly 落盘 + 剥壳 + 链式键 + 降级 ----
    class _FakeLLM:
        def json_call(self, system, user):
            self.last_user = user
            return {"threads": [{"title": "T", "one_liner": "o",
                                 "direction": "推进", "detail": "d"}],
                    "watch_recap": [{"prior": "p", "status": "未兑现", "note": "n"}],
                    "outlook": ["x"]}
    wtmp = tmp / "wk"
    (wtmp / "daily").mkdir(parents=True, exist_ok=True)
    for k in range(6, 13):
        ds = f"2026-07-{k:02d}"
        p = {"date": ds, "items": [{"id": "pick-0", "tier": "pick", "category": "ai",
                                    "title": "x", "summary": "s", "watch": "w"}]}
        (wtmp / "daily" / f"{ds}.js").write_text(
            f'window.NEWS_DATA["{ds}"] = {json.dumps(p, ensure_ascii=False)};\n',
            encoding="utf-8")
    wcfg = {"weekly": {"enabled": True, "lookback_days": 7, "keep_weeks": 26}}
    fake = _FakeLLM()
    dn.write_weekly(fake, "2026-07-13", wcfg, wtmp)   # 目标上周 = 含 7/06..7/12
    wkey = dn.iso_week_key(dn.datetime(2026, 7, 12))
    check("周综述键为 ISO 周", wkey == "2026-W28")
    check("周综述输入含精选与watch", "关注:w" in fake.last_user)
    wpl = dn.read_weekly_payload(wtmp / "weekly" / f"{wkey}.js")
    check("周综述落盘可剥壳", wpl is not None and wpl["week"] == wkey
          and len(wpl["threads"]) == 1 and len(wpl["watch_recap"]) == 1)
    check("周综述 manifest 含本周",
          (wtmp / "weekly" / "manifest.js").exists()
          and wkey in (wtmp / "weekly" / "manifest.js").read_text(encoding="utf-8"))
    dtmp = tmp / "wk_empty"
    (dtmp / "daily").mkdir(parents=True, exist_ok=True)
    dn.write_weekly(_FakeLLM(), "2026-07-13", wcfg, dtmp)
    check("周综述降级：无 daily 不产文件", not (dtmp / "weekly").exists())

    # ---- http_get 重试兜底（stub requests.get + time.sleep，不联网）----
    class _Resp:
        def raise_for_status(self):
            pass
    calls = {"n": 0}
    orig_get, orig_sleep = dn.requests.get, dn.time.sleep
    dn.time.sleep = lambda *a, **k: None
    try:
        def _flaky(url, **kw):
            calls["n"] += 1
            if calls["n"] < 3:
                raise IOError("reset")
            return _Resp()
        dn.requests.get = _flaky
        r = dn.http_get("http://x", retries=2)
        check("http_get 前两次失败后成功返回", isinstance(r, _Resp) and calls["n"] == 3)

        calls["n"] = 0
        def _down(url, **kw):
            calls["n"] += 1
            raise IOError("down")
        dn.requests.get = _down
        raised = False
        try:
            dn.http_get("http://x", retries=2)
        except IOError:
            raised = True
        check("http_get 始终失败则抛且共尝试 retries+1 次", raised and calls["n"] == 3)
    finally:
        dn.requests.get, dn.time.sleep = orig_get, orig_sleep

    # ---- 画像"学习参考系"段：切分 + 熬过蒸馏（stub LLM 返回丢掉参考系段的结果）----
    rest, blk = dn.split_section(
        "# t\n\n## 学习参考系\n- 补 TS 类型系统\n- 练数据结构\n\n## 更关注\n- a\n", "学习参考系")
    check("split_section 切出学习参考系段", "- 补 TS 类型系统" in blk and "- 练数据结构" in blk
          and "## 学习参考系" in blk and "学习参考系" not in rest and "## 更关注" in rest)

    class _Msg:
        def __init__(self, c):
            self.message = type("M", (), {"content": c})()
    class _Comp:
        def __init__(self, o):
            self._o = o
        def create(self, **kw):
            return type("R", (), {"choices": [_Msg(self._o)]})()
    class _ProfLLM:
        def __init__(self, o):
            self.model = "x"
            self.client = type("C", (), {
                "chat": type("H", (), {"completions": _Comp(o)})()})()

    ptmp = tmp / "prof"
    ptmp.mkdir(parents=True, exist_ok=True)
    (ptmp / "interest_profile.md").write_text(
        "# 兴趣画像\n<!-- last_feedback_ts: 2020-01-01T00:00:00Z -->\n\n导语\n\n"
        "## 学习参考系\n- 长期补系统设计\n- 优先补 TypeScript 类型系统\n\n"
        "## 更关注\n- 旧偏好\n\n## 不关注\n- 旧\n\n## 来源印象\n- 旧\n",
        encoding="utf-8")
    # LLM 蒸馏结果"丢掉了"参考系段（模拟全文重写会冲掉手写段）
    clobber = "# 兴趣画像\n\n## 更关注\n- 新AI\n\n## 不关注\n- 标题党\n\n## 来源印象\n- 官方\n"
    fb = [{"ts": "2026-07-01T00:00:00Z", "action": "more_like_this",
           "category": "ai", "title": "x"}]
    out_text = dn.update_profile(_ProfLLM(clobber), ptmp, fb, [])
    disk = (ptmp / "interest_profile.md").read_text(encoding="utf-8")
    check("学习参考系熬过蒸馏（落盘仍在且原样）",
          "## 学习参考系" in disk and "- 长期补系统设计" in disk
          and "- 优先补 TypeScript 类型系统" in disk and disk == out_text)
    check("蒸馏吸收了新兴趣且推进 marker",
          "- 新AI" in disk and "2026-07-01T00:00:00Z" in disk)
    check("学习参考系只出现一次（无重复）", disk.count("## 学习参考系") == 1)

    # 兼容旧画像：旧的"我的处境"不会被蒸馏冲掉，也不会重复插入。
    (ptmp / "interest_profile.md").write_text(
        "# 兴趣画像\n<!-- last_feedback_ts: 2020-01-01T00:00:00Z -->\n\n"
        "## 我的处境\n- 在学 TypeScript\n- 在做日报系统\n\n"
        "## 更关注\n- 旧\n\n## 不关注\n- 旧\n\n## 来源印象\n- 旧\n", encoding="utf-8")
    old_out = dn.update_profile(_ProfLLM(clobber), ptmp, fb, [])
    check("旧处境段兼容保留且不重复",
          "## 我的处境" in old_out and "- 在学 TypeScript" in old_out
          and old_out.count("## 我的处境") == 1 and old_out.count("## 学习参考系") == 0)

    # 无参考系/处境段时不报错、正常蒸馏
    (ptmp / "interest_profile.md").write_text(
        "# 兴趣画像\n<!-- last_feedback_ts: 2020-01-01T00:00:00Z -->\n\n"
        "## 更关注\n- 旧\n\n## 不关注\n- 旧\n\n## 来源印象\n- 旧\n", encoding="utf-8")
    out2 = dn.update_profile(_ProfLLM(clobber), ptmp, fb, [])
    check("无参考系/处境段蒸馏不报错",
          "## 更关注" in out2 and "学习参考系" not in out2 and "我的处境" not in out2)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ----------------------------------------------------------------
# 自建 RSSHub 占位符解析（resolve_rsshub_sources）
# ----------------------------------------------------------------

_rh_src = [
    {"id": "sciencenet", "name": "科学网", "url": "{rsshub}/sciencenet/blog"},
    {"id": "thepaper", "name": "澎湃", "url": "{rsshub}/thepaper/featured?limit=20"},
    {"id": "openai", "name": "OpenAI", "url": "https://openai.com/news/rss.xml"},
]
_rh_env = {"RSSHUB_BASE": os.environ.get("RSSHUB_BASE"), "RSSHUB_KEY": os.environ.get("RSSHUB_KEY")}
try:
    os.environ["RSSHUB_BASE"] = "https://ex.vercel.app/"   # 结尾斜杠应被去掉
    os.environ["RSSHUB_KEY"] = "SECRET"
    out = dn.resolve_rsshub_sources(_rh_src)
    by = {s["id"]: s["url"] for s in out}
    check("占位符替换并追加 key（? 分隔）",
          by.get("sciencenet") == "https://ex.vercel.app/sciencenet/blog?key=SECRET")
    check("已带 query 的路由用 & 追加 key",
          by.get("thepaper") == "https://ex.vercel.app/thepaper/featured?limit=20&key=SECRET")
    check("非 rsshub 源原样保留", by.get("openai") == "https://openai.com/news/rss.xml")

    os.environ.pop("RSSHUB_KEY")
    out_nokey = {s["id"]: s["url"] for s in dn.resolve_rsshub_sources(_rh_src)}
    check("无 key 时不追加 ?key",
          out_nokey.get("sciencenet") == "https://ex.vercel.app/sciencenet/blog")

    os.environ.pop("RSSHUB_BASE")
    out_nobase = {s["id"] for s in dn.resolve_rsshub_sources(_rh_src)}
    check("未配置 base 时占位符源被跳过、其余保留",
          out_nobase == {"openai"})
finally:
    for k, v in _rh_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

print()
print("全部通过" if not failures else f"{len(failures)} 项失败: {failures}")
sys.exit(1 if failures else 0)
