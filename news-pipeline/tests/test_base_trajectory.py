import json
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import daily_news as dn


def test_default_watch_limit_is_90_characters():
    assert dn.OBJECTIVITY_FIELD_LIMITS["watch"] == 90


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
                "significance": True,
                "watch": False,
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


@pytest.mark.parametrize("mode", ["interim", "shadow", "active"])
def test_enrich_uses_shared_reader_field_limits_in_every_objectivity_mode(
        mode, monkeypatch):
    monkeypatch.setitem(dn.OBJECTIVITY_FIELD_LIMITS, "context", 11)
    monkeypatch.setitem(dn.OBJECTIVITY_FIELD_LIMITS, "significance", 13)
    monkeypatch.setitem(dn.OBJECTIVITY_FIELD_LIMITS, "watch", 17)
    response = {
        "idx": 0,
        "title": "Factory pilot expands",
        "summary": "Pilot production has begun.",
        "why": "The result affects the production timetable.",
        "context": "c" * 40,
        "significance": "s" * 40,
        "watch": "w" * 120,
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

    assert len(event["context"]) == 11
    assert len(event["significance"]) == 13
    assert len(event["watch"]) == 17
    assert "≤17字" in llm.system


def test_one_off_enrichment_outputs_an_evidence_constrained_trajectory():
    watch = "量产取决于良率测试；可观察下月披露的合格率与正式投产日期。"
    llm = EnrichLLM({
        "idx": 0,
        "title": "工厂启动试产",
        "summary": "工厂本月启动试产。",
        "why": "结果会影响后续产能安排。",
        "context": "",
        "significance": "",
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
        "significance": "",
        "watch": "没有来源支撑的走向",
        "claims": [],
    }

    audit_llm = RejectWatchAuditLLM()
    dn.audit_enrichment_support_interim(audit_llm, [event], [_source_item()])

    assert "watch" not in event
    for rule in ("关键变量", "可观察路标", "具体概率", "无条件断言", "来源外类比"):
        assert rule in audit_llm.system


def test_full_objectivity_audit_enforces_the_same_watch_contract():
    for rule in ("关键变量", "可观察路标", "具体概率", "无条件断言", "来源外类比"):
        assert rule in dn.OBJECTIVITY_AUDIT_SYSTEM


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
