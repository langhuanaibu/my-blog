import json
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import daily_news as dn


def test_default_watch_limit_is_90_characters():
    assert dn.OBJECTIVITY_FIELD_LIMITS["watch"] == 90
    assert dn.FULLTEXT_OBJECTIVITY_FIELD_LIMITS["watch"] == 90
    assert dn.FULLTEXT_OBJECTIVITY_FIELD_LIMITS["watch_detail"] == 260
    assert dn.FULLTEXT_OBJECTIVITY_FIELD_LIMITS["context"] == 240
    assert dn.FULLTEXT_OBJECTIVITY_FIELD_LIMITS["detail"] == 1200


class EnrichLLM:
    def __init__(self, response):
        self.response = response
        self.system = ""

    def json_call(self, system, _user):
        self.system = system
        return [dict(self.response)]


class RejectWatchAuditLLM:
    def __init__(self):
        self.system = ""

    def json_call(self, _system, _user):
        self.system = _system
        return {
            "fields": {
                "why": True,
                "context": True,
                "watch": False,
                "watch_detail": False,
            },
            "supported_claim_indexes": [],
        }


def _source_item():
    return {
        "title": "Factory begins pilot production",
        "desc": "The pilot starts this month and full production depends on yield tests.",
        "source": "Example Wire",
        "source_id": "example-wire",
        "source_type": "fact",
        "tier": "T1",
        "credibility": 9,
        "url": "https://example.test/factory",
        "time": "2026-07-21T01:00:00+00:00",
        "evidence_text": "The pilot starts this month and full production depends on yield tests.",
        "evidence_basis": "fulltext",
    }


def _event():
    return {
        "ids": [0],
        "category": "tech",
        "title": "Factory pilot",
        "score": 90,
        "tier": "T1",
    }


@pytest.mark.parametrize("mode", ["shadow", "active"])
def test_fulltext_enrich_uses_deep_reader_limits_without_significance(
        mode, monkeypatch):
    monkeypatch.setitem(dn.OBJECTIVITY_FIELD_LIMITS, "context", 11)
    monkeypatch.setitem(dn.OBJECTIVITY_FIELD_LIMITS, "watch", 17)
    monkeypatch.setitem(dn.FULLTEXT_OBJECTIVITY_FIELD_LIMITS, "context", 41)
    monkeypatch.setitem(dn.FULLTEXT_OBJECTIVITY_FIELD_LIMITS, "watch", 17)
    monkeypatch.setitem(dn.FULLTEXT_OBJECTIVITY_FIELD_LIMITS, "watch_detail", 61)
    response = {
        "idx": 0,
        "title": "Factory pilot expands",
        "summary": "Pilot production has begun.",
        "why": "The result affects the production timetable.",
        "context": "c" * 40,
        "context_evidence": [{
            "source_index": 0,
            "quote": "full production depends on yield tests",
        }],
        "watch": "w" * 120,
        "watch_detail": "d" * 60,
        "claims": [],
        "status": "发展中",
        "tags": [],
    }
    llm = EnrichLLM(response)
    event = _event()

    dn.enrich(llm, [event], [_source_item()], {
        "_objectivity_runtime_mode": mode,
        "topic_tags": [],
        "detail": {"enabled": False},
    })

    assert len(event["context"]) == 40
    assert "significance" not in event
    assert "significance" not in llm.system
    assert "读者兴趣画像" not in llm.system
    assert "watch" not in event
    assert "watch_detail" not in event
    assert "≤17字" in llm.system
    assert "watch_detail" in llm.system
    assert "普通条目约 250-600 字" not in llm.system  # detail disabled in this fixture


def test_interim_enrich_keeps_short_contract_and_omits_watch_detail():
    llm = EnrichLLM({
        "idx": 0,
        "title": "Factory pilot expands",
        "summary": "Pilot production has begun.",
        "why": "The result affects the production timetable.",
        "context": "",
        "context_evidence": [],
        "watch": "Watch the next yield report.",
        "watch_detail": "This field must be ignored in interim mode.",
        "claims": [],
        "status": "发展中",
        "tags": [],
    })
    event = _event()

    dn.enrich(llm, [event], [_source_item()], {
        "_objectivity_runtime_mode": "interim",
        "topic_tags": [],
        "detail": {"enabled": False},
    })

    assert event["watch"] == "Watch the next yield report."
    assert "watch_detail" not in event
    assert "watch_detail" not in llm.system


def test_interim_detail_prompt_does_not_use_fulltext_depth_contract():
    llm = EnrichLLM({
        "idx": 0,
        "title": "Factory pilot expands",
        "summary": "Pilot production has begun.",
        "why": "The result affects the production timetable.",
        "context": "",
        "context_evidence": [],
        "watch": "Watch the next yield report.",
        "detail": "The factory has started pilot production.",
        "claims": [],
        "status": "发展中",
        "tags": [],
    })

    dn.enrich(llm, [_event()], [_source_item()], {
        "_objectivity_runtime_mode": "interim",
        "topic_tags": [],
        "detail": {"enabled": True, "max_chars": 1000},
    })

    assert "现状短叙述" in llm.system
    assert "普通条目约 250-600 字" not in llm.system
    assert "利益相关方变化和未决事实" not in llm.system


def test_one_off_enrichment_outputs_an_evidence_constrained_trajectory():
    watch = "量产取决于良率测试；可观察下月披露的合格率与正式投产日期。"
    llm = EnrichLLM({
        "idx": 0,
        "title": "工厂启动试产",
        "summary": "工厂本月启动试产。",
        "why": "结果会影响后续产能安排。",
        "context": "",
        "watch": watch,
        "claims": [],
        "status": "发展中",
        "tags": [],
    })
    event = _event()

    dn.enrich(llm, [event], [_source_item()], {
        "_objectivity_runtime_mode": "interim",
        "topic_tags": [],
        "detail": {"enabled": False},
    })

    assert event["context"] == ""
    assert event["watch"] == watch
    assert "关键变量" in llm.system
    assert "可观察路标" in llm.system
    assert "具体概率" in llm.system
    assert "无条件断言" in llm.system
    assert "来源外类比" in llm.system


def test_support_audit_removed_watch_stays_absent_without_placeholder():
    event = {
        **_event(),
        "why": "重要性",
        "context": "",
        "watch": "没有来源支撑的走向",
        "watch_detail": "没有来源支撑的详情走向",
        "claims": [],
    }

    audit_llm = RejectWatchAuditLLM()
    dn.audit_enrichment_support_interim(audit_llm, [event], [_source_item()])

    assert "watch" not in event
    assert "watch_detail" not in event
    for rule in ("关键变量", "可观察路标", "具体概率", "无条件断言", "来源外类比"):
        assert rule in audit_llm.system


def test_full_objectivity_audit_enforces_the_same_watch_contract():
    for rule in ("关键变量", "可观察路标", "具体概率", "无条件断言", "来源外类比"):
        assert rule in dn.OBJECTIVITY_AUDIT_SYSTEM


def test_public_item_emits_watch_detail_but_never_significance():
    event = {
        **_event(),
        "watch": "Short watch.",
        "watch_detail": "Detailed watch.",
        "significance": "Legacy private advice.",
    }

    item = dn.event_to_item(event, [_source_item()], "pick")

    assert item["watch"] == "Short watch."
    assert item["watch_detail"] == "Detailed watch."
    assert "significance" not in item


def test_public_item_never_emits_watch_detail_without_short_watch():
    item = dn.event_to_item(
        {**_event(), "watch_detail": "Orphan detail watch."},
        [_source_item()],
        "pick",
    )

    assert "watch" not in item
    assert "watch_detail" not in item


def test_quality_stats_use_v2_extension_field_contract():
    quality = dn.new_quality_stats()

    assert quality["removed_field_counts_version"] == 2
    assert set(quality["removed_field_counts"]) == {
        "why", "context", "watch", "watch_detail", "detail", "claims",
    }
    assert "significance" not in quality["removed_field_counts"]


def test_unrepairable_overlong_objectivity_field_is_deleted_and_counted():
    event = {**_event(), "watch": "原走向。"}
    quality = dn.new_quality_stats()

    dn._apply_objectivity_repair(
        event,
        {"fields": {"watch": "x" * 200}, "claims": []},
        ["watch"],
        [],
        {"Example Wire"},
        quality=quality,
    )

    assert "watch" not in event
    assert quality["removed_field_counts"]["watch"] == 1
    assert quality["removed_field_reasons"]["generation_invalid"] == 1


def test_quality_validation_accepts_legacy_v1_and_current_v2_breakdowns():
    current = dn.new_quality_stats()
    assert dn.validate_daily_payload({"quality": current, "items": []}) == []

    legacy = dict(current)
    legacy.pop("removed_field_counts_version")
    legacy["removed_field_counts"] = {
        field: 0 for field in dn.QUALITY_EXTENSION_FIELDS_V1
    }
    legacy["removed_field_reasons"] = {
        reason: 0 for reason in dn.REMOVAL_REASONS_V1
    }
    assert dn.validate_daily_payload({"quality": legacy, "items": []}) == []

    invalid = dict(current)
    invalid["removed_field_counts_version"] = 2.0
    assert any(
        "removed_field_counts_version" in error
        for error in dn.validate_daily_payload({"quality": invalid, "items": []})
    )

    orphan_payload = {
        "quality": current,
        "items": [{
            "id": "pick-1",
            "title": "Factory pilot",
            "watch_detail": "Detail without its short contract.",
        }],
    }
    assert any(
        "requires a valid short watch" in error
        for error in dn.validate_daily_payload(orphan_payload)
    )


def test_fulltext_enrich_batches_at_three_events_while_interim_keeps_six():
    items = [_source_item()]
    picked = [{**_event(), "ids": [0]} for _ in range(7)]

    assert list(dn._enrich_batch_ranges(picked, items, False)) == [(0, 6), (6, 7)]
    assert list(dn._enrich_batch_ranges(picked, items, True)) == [
        (0, 3), (3, 6), (6, 7),
    ]


def test_fulltext_trajectory_generates_and_audits_short_and_detail_watch():
    short_watch = "量产取决于良率测试；观察下月合格率。"
    detail_watch = (
        "量产仍取决于良率测试，首个路标是下月披露的合格率。"
        "还需观察正式投产日期是否随测试结果确定。"
    )

    class TrajectoryLLM:
        def __init__(self):
            self.calls = []

        def json_call(self, system, user):
            self.calls.append((system, json.loads(user)))
            if system == dn.TRAJECTORY_GENERATION_SYSTEM:
                return {"trajectories": [{
                    "idx": 0,
                    "context": "工厂此前公布试产计划，今天已开始试产。",
                    "watch": short_watch,
                    "watch_detail": detail_watch,
                    "claims": [],
                }]}
            return {"audits": [{
                "idx": 0,
                "fields": {
                    "context": True,
                    "watch": True,
                    "watch_detail": True,
                },
                "claims": [],
            }]}

    llm = TrajectoryLLM()
    event = _event()
    succeeded = dn.run_trajectory_stage(
        llm,
        [event],
        [(0, 0)],
        {0: [{
            "date": "2026-07-20",
            "title": "工厂公布试产计划",
            "summary": "工厂计划本月试产。",
            "watch": "观察是否按期开始试产。",
        }]},
        [_source_item()],
        audit_llm=llm,
        include_watch_detail=True,
    )

    assert succeeded == {0}
    assert event["watch"] == short_watch
    assert event["watch_detail"] == detail_watch
    assert llm.calls[0][1]["items"][0]["include_watch_detail"] is True
    assert llm.calls[1][1]["items"][0]["trajectory"]["watch_detail"] == detail_watch


def test_fulltext_trajectory_missing_detail_watch_is_not_audited_as_success():
    class MissingDetailLLM:
        calls = 0

        def json_call(self, system, _user):
            self.calls += 1
            assert system == dn.TRAJECTORY_GENERATION_SYSTEM
            return {"trajectories": [{
                "idx": 0,
                "context": "工厂此前公布试产计划，今天已开始试产。",
                "watch": "量产取决于良率测试；观察下月合格率。",
                "claims": [],
            }]}

    llm = MissingDetailLLM()
    event = _event()
    succeeded = dn.run_trajectory_stage(
        llm,
        [event],
        [(0, 0)],
        {0: [{"date": "2026-07-20", "watch": "观察是否按期开始试产。"}]},
        [_source_item()],
        audit_llm=llm,
        include_watch_detail=True,
    )

    assert succeeded == set()
    assert llm.calls == 1


def test_fulltext_trajectory_restores_both_watches_if_either_fails_audit():
    class MixedAuditLLM:
        def json_call(self, system, _user):
            if system == dn.TRAJECTORY_GENERATION_SYSTEM:
                return {"trajectories": [{
                    "idx": 0,
                    "context": "工厂此前公布试产计划，今天已开始试产。",
                    "watch": "新短走向；观察新路标。",
                    "watch_detail": "新详情走向完整包含新短走向与新路标。",
                    "claims": [],
                }]}
            return {"audits": [{
                "idx": 0,
                "fields": {
                    "context": True,
                    "watch": True,
                    "watch_detail": False,
                },
                "claims": [],
            }]}

    event = {
        **_event(),
        "watch": "原短走向。",
        "watch_detail": "原详情走向。",
    }
    health = dn.new_trajectory_health()
    succeeded = dn.run_trajectory_stage(
        MixedAuditLLM(),
        [event],
        [(0, 0)],
        {0: [{"date": "2026-07-20", "watch": "观察是否按期开始试产。"}]},
        [_source_item()],
        include_watch_detail=True,
        health=health,
    )

    assert succeeded == {0}
    assert event["watch"] == "原短走向。"
    assert event["watch_detail"] == "原详情走向。"
    assert health["audit_fallbacks"] == 2


def test_feed_labels_existing_watch_field_as_trajectory(tmp_path):
    daily_dir = tmp_path / "daily"
    daily_dir.mkdir()
    payload = {
        "date": "2026-07-21",
        "generated_at": "2026-07-21T05:00:00+00:00",
        "items": [{
            "id": "pick-1",
            "tier": "pick",
            "category": "tech",
            "title": "工厂启动试产",
            "summary": "工厂本月启动试产。",
            "watch": "量产取决于良率测试。",
            "time": "2026-07-21T01:00:00+00:00",
            "sources": [{"name": "Example Wire", "url": "https://example.test/factory"}],
        }],
    }
    (daily_dir / "2026-07-21.js").write_text(
        'window.NEWS_DATA = window.NEWS_DATA || {};\n'
        f'window.NEWS_DATA["2026-07-21"] = {json.dumps(payload, ensure_ascii=False)};\n',
        encoding="utf-8",
    )

    dn.write_feed(tmp_path, "2026-07-21", {
        "feed_days": 7,
        "site_url": "https://example.test",
    })

    feed = (tmp_path / "feed.xml").read_text(encoding="utf-8")
    assert "<b>走向：</b>" in feed
    assert "后续关注" not in feed
