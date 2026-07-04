# -*- coding: utf-8 -*-
"""管线纯逻辑回归测试（不调 LLM、不联网）
用法: python news-pipeline/tests/test_pipeline.py
覆盖: 舆论源封顶 / 同源封顶 / 跨批次合并 / 信源健康度
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

print()
print("全部通过" if not failures else f"{len(failures)} 项失败: {failures}")
sys.exit(1 if failures else 0)
