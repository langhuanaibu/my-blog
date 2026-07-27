import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import daily_news as dn


# 真实的碎片线共享大量词汇（实测 28-46 个低频键），候选门正是靠这一点把它们
# 与"同类目 + 区间重叠"的噪声区分开。夹具必须同样有实质文本，否则测的是一份
# 生产中不存在的稀薄数据。
IRAN_PROGRESS = (
    "美军战机空袭伊朗霍尔木兹海峡沿岸港口设施，德黑兰宣布关闭海峡并誓言报复，"
    "国际油价大幅上涨，多家航运公司暂停通行。")


def _line(event_id, title, dates, *, category="world", status="active",
          pinned=False, summary=None):
    """A registry event line: identity, category, status and its day-by-day history."""
    return {
        "event_id": event_id,
        "title": title,
        "category": category,
        "status": status,
        "pinned": pinned,
        "first_seen": dates[0],
        "last_seen": dates[-1],
        "history": [{
            "date": date,
            "title": f"{title} · {date}",
            "summary": summary or f"{title} 在 {date} 的进展。",
            "news_status": "已确认",
        } for date in dates],
    }


def _iran_line(event_id, title, dates, *, summary=None, **kwargs):
    """A fragment of the same continuing US-Iran story, with realistic overlap."""
    return _line(event_id, title, dates,
                 summary=summary or IRAN_PROGRESS, **kwargs)


class GroupingLLM:
    """Partitions each batch by a marker word, mirroring the same-day fake."""

    def __init__(self, marker="伊朗"):
        self.marker = marker
        self.calls = []

    def json_call(self, _system, user):
        payload = json.loads(user)
        self.calls.append(payload)
        marked = [index for index, row in enumerate(payload)
                  if self.marker in json.dumps(row, ensure_ascii=False)]
        marked_set = set(marked)
        groups = [[index] for index in range(len(payload))
                  if index not in marked_set]
        if marked:
            groups.append(marked)
        groups.sort(key=lambda group: group[0])
        return {"groups": groups}


def test_overlapping_lines_about_one_event_merge_under_the_earliest_name():
    events = [
        _iran_line("evt-a", "美国对伊朗发动新一轮空袭", ["2026-07-10", "2026-07-16"]),
        _iran_line("evt-b", "美国扩大对伊朗空袭", ["2026-07-12", "2026-07-25"]),
    ]

    merged = dn.reconcile_registry_events(
        GroupingLLM(), events, dn.new_quality_stats())

    assert len(merged) == 1
    assert merged[0]["title"] == "美国对伊朗发动新一轮空袭"
    assert merged[0]["event_id"] == "evt-a"
    assert [row["date"] for row in merged[0]["history"]] == [
        "2026-07-10", "2026-07-12", "2026-07-16", "2026-07-25"]
    assert merged[0]["first_seen"] == "2026-07-10"
    assert merged[0]["last_seen"] == "2026-07-25"


def test_lines_in_different_categories_never_reach_the_auditor():
    """同一批词也可能出现在别的类目，类目不同就不是同一件事。"""
    llm = GroupingLLM()
    events = [
        _iran_line("evt-a", "美国对伊朗发动空袭", ["2026-07-10", "2026-07-16"]),
        _line("evt-b", "伊朗芯片出口管制新规", ["2026-07-12", "2026-07-18"],
              category="tech"),
    ]

    merged = dn.reconcile_registry_events(llm, events, dn.new_quality_stats())

    assert len(merged) == 2
    assert llm.calls == []


def test_lines_whose_spans_do_not_overlap_never_reach_the_auditor():
    """区间不相交说明是先后两件事，不是同一条线的两截。"""
    llm = GroupingLLM()
    events = [
        _iran_line("evt-a", "美国对伊朗发动空袭", ["2026-07-01", "2026-07-05"]),
        _iran_line("evt-b", "美国扩大对伊朗空袭", ["2026-07-20", "2026-07-25"]),
    ]

    merged = dn.reconcile_registry_events(llm, events, dn.new_quality_stats())

    assert len(merged) == 2
    assert llm.calls == []


def test_auditor_failure_leaves_every_line_intact_and_marks_degraded():
    """审计失败即不合并：漏并留下两条线，误并毁掉事件身份。"""
    class BrokenLLM:
        def json_call(self, _system, _user):
            raise RuntimeError("audit unavailable")

    quality = dn.new_quality_stats()
    events = [
        _iran_line("evt-a", "美国对伊朗发动新一轮空袭", ["2026-07-10", "2026-07-16"]),
        _iran_line("evt-b", "美国扩大对伊朗空袭", ["2026-07-12", "2026-07-25"]),
    ]

    merged = dn.reconcile_registry_events(BrokenLLM(), events, quality)

    assert [event["event_id"] for event in merged] == ["evt-a", "evt-b"]
    assert quality["event_line_audit_failures"] == 1
    assert quality["degraded"] is True
    assert quality["event_lines_merged"] == 0


def test_one_row_per_date_survives_and_it_is_the_identity_line_s_row():
    """碎片化的症状就是同一天两条线各记一行；归并后每天只留一行。"""
    events = [
        _iran_line("evt-a", "美国对伊朗发动新一轮空袭",
                   ["2026-07-10", "2026-07-16"],
                   summary=f"身份线记的进展。{IRAN_PROGRESS}"),
        _iran_line("evt-b", "美国扩大对伊朗空袭",
                   ["2026-07-16", "2026-07-25"],
                   summary=f"碎片线记的进展。{IRAN_PROGRESS}"),
    ]

    merged = dn.reconcile_registry_events(
        GroupingLLM(), events, dn.new_quality_stats())

    history = merged[0]["history"]
    assert [row["date"] for row in history] == [
        "2026-07-10", "2026-07-16", "2026-07-25"]
    assert history[1]["summary"].startswith("身份线记的进展。")


def test_pin_and_active_status_survive_the_merge():
    """追踪标记是用户主动标的，归并不得把它吃掉。"""
    events = [
        _iran_line("evt-a", "美国对伊朗发动新一轮空袭", ["2026-07-10", "2026-07-16"],
              status="archived"),
        _iran_line("evt-b", "美国扩大对伊朗空袭", ["2026-07-12", "2026-07-25"],
              pinned=True),
    ]

    merged = dn.reconcile_registry_events(
        GroupingLLM(), events, dn.new_quality_stats())

    assert len(merged) == 1
    assert merged[0]["pinned"] is True
    assert merged[0]["status"] == "active"


def test_merge_count_is_recorded_for_the_quality_record():
    quality = dn.new_quality_stats()
    events = [
        _iran_line("evt-a", "美国对伊朗发动新一轮空袭", ["2026-07-10", "2026-07-16"]),
        _iran_line("evt-b", "美国扩大对伊朗空袭", ["2026-07-12", "2026-07-25"]),
        _iran_line("evt-c", "伊朗宣布关闭霍尔木兹海峡", ["2026-07-14", "2026-07-20"]),
    ]

    merged = dn.reconcile_registry_events(GroupingLLM(), events, quality)

    assert len(merged) == 1
    assert quality["event_lines_merged"] == 2
    assert quality["event_lines_audited"] == 3
    assert quality["degraded"] is False


def test_unrelated_lines_sharing_only_category_and_dates_never_reach_the_auditor():
    """同类目 + 区间重叠不构成候选，否则整张登记表每天都会被全量重审。"""
    llm = GroupingLLM()
    events = [
        _iran_line("evt-a", "美国对伊朗发动新一轮空袭", ["2026-07-10", "2026-07-16"],
              summary="美军战机再次打击伊朗港口设施，德黑兰誓言报复。"),
        _line("evt-b", "巴西亚马孙雨林砍伐率创新低", ["2026-07-11", "2026-07-17"],
              summary="卫星监测显示，雨林砍伐面积同比下降四成。"),
        _line("evt-c", "日本首相改组内阁", ["2026-07-12", "2026-07-18"],
              summary="首相更换六名阁僚，财务大臣留任。"),
    ]

    merged = dn.reconcile_registry_events(llm, events, dn.new_quality_stats())

    assert len(merged) == 3
    assert llm.calls == []


def test_candidate_batches_stay_a_small_fraction_of_a_realistic_registry():
    """批次规模必须随真正的重复数增长，而不是随登记表规模增长。"""
    events = []
    for index in range(120):
        day = 10 + index % 15
        events.append(_line(
            f"evt-{index}", f"第{index}号无关事件在某地发生",
            [f"2026-07-{day:02d}", f"2026-07-{day + 1:02d}"]))
    events.append(_iran_line("dup-a", "美国对伊朗发动新一轮空袭",
                        ["2026-07-12", "2026-07-16"]))
    events.append(_iran_line("dup-b", "美国扩大对伊朗空袭",
                        ["2026-07-14", "2026-07-20"]))

    batches = dn._cross_day_line_batches(events)
    audited = sum(len(batch) for batch in batches)

    assert audited <= 12, f"送审 {audited} 条，候选门没有收敛"
    assert any({"dup-a", "dup-b"} <= {events[i]["event_id"] for i in batch}
               for batch in batches), "真正的重复必须仍被送审"


class RegistryStageLLM:
    """Answers the match, continuity and line-reconcile stages of one transaction."""

    def __init__(self, matches):
        self.matches = matches
        self.reconcile_payloads = []

    def json_call(self, system, user):
        if "跨天事件线归并" in system:
            payload = json.loads(user)
            self.reconcile_payloads.append(payload)
            return {"groups": [list(range(len(payload)))]}
        if "连续性门" in system:
            return {"validations": [{
                "candidate": 0,
                "matches_mainline": True,
                "matches_latest": True,
                "history": [{"row": 0, "relevant": True}],
            }]}
        return {"matches": self.matches}


def test_transaction_merges_stale_fragments_but_never_today_s_own_line():
    """归并是对历史登记表的整理，不重新裁决今天的延续判断（ADR 0002）。"""
    registry = {"version": 2, "events": [
        _iran_line("evt-frag-a", "美国对伊朗发动空袭", ["2026-07-10", "2026-07-16"]),
        _iran_line("evt-frag-b", "美国扩大对伊朗空袭", ["2026-07-12", "2026-07-18"]),
        _line("evt-live", "Model launch", ["2026-07-20"], category="ai"),
    ]}
    today = {
        "ids": [0], "category": "ai", "title": "Model launch follow-up",
        "summary": "Adoption figures are now available.", "status": "confirmed",
        "score": 90, "tier": "T1", "tags": [],
    }
    items = [{
        "title": "Model launch follow-up", "desc": "Adoption figures published.",
        "url": "https://example.test/model", "source": "Example News",
        "source_id": "example-news", "source_type": "fact", "tier": "T1",
        "credibility": 9, "time": "2026-07-21T01:00:00+00:00",
    }]
    # 匹配用的是 eligible 顺序：两条历史碎片在前，今天要续接的线在索引 2。
    llm = RegistryStageLLM([{"today": 0, "registry": 2}])

    prepared = dn.prepare_registry_transaction(
        llm, registry, [today], "2026-07-21", {"events": {}}, items=items)

    names = [event["title"] for event in prepared["events"]]
    assert names == ["美国对伊朗发动空袭", "Model launch"]
    assert today["event_id"] == "evt-live"
    live = [event for event in prepared["events"]
            if event["event_id"] == "evt-live"][0]
    assert [row["date"] for row in live["history"]] == [
        "2026-07-20", "2026-07-21"]
    # 今天写入的那条线不得出现在归并批次里
    assert all("Model launch" not in json.dumps(payload, ensure_ascii=False)
               for payload in llm.reconcile_payloads)


def test_malformed_auditor_partition_is_rejected_without_merging():
    """不是完整划分的回复一律丢弃，绝不据此合并。"""
    class PartialLLM:
        def json_call(self, _system, _user):
            return {"groups": [[0]]}

    quality = dn.new_quality_stats()
    events = [
        _iran_line("evt-a", "美国对伊朗发动新一轮空袭", ["2026-07-10", "2026-07-16"]),
        _iran_line("evt-b", "美国扩大对伊朗空袭", ["2026-07-12", "2026-07-25"]),
    ]

    merged = dn.reconcile_registry_events(PartialLLM(), events, quality)

    assert len(merged) == 2
    assert quality["event_line_audit_failures"] == 1
    assert quality["degraded"] is True
