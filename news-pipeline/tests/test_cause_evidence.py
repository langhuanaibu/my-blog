# -*- coding: utf-8 -*-
"""起因原文核对闸：起因必须能逐字回溯到来源正文，否则整条丢弃。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import daily_news as dn


ARTICLE = (
    "最高法院于2月20日裁定，特朗普此前依据《国际紧急经济权力法》加征的全球关税违法。"
    "白宫随即改用第301条重新加征，并选在旧关税到期当天生效。"
)


def _items(evidence_text=ARTICLE):
    return [{
        "title": "新关税生效数小时后即遭起诉",
        "desc": "新关税遭到起诉。",
        "evidence_text": evidence_text,
        "source": "Synthetic Wire",
        "source_id": "synthetic-wire",
        "source_type": "fact",
        "tier": "T1",
        "credibility": 9,
        "url": "https://example.com/report",
        "time": "2026-07-26T00:00:00+00:00",
    }]


def _event(cause, span):
    return {
        "ids": [0], "category": "world", "title": "关税遭起诉",
        "context": cause, "context_evidence": span,
    }


def test_verbatim_span_keeps_the_cause():
    event = _event(
        "最高法院裁定旧关税违法，白宫改用第301条并在旧关税到期当天生效。",
        "白宫随即改用第301条重新加征，并选在旧关税到期当天生效。")
    quality = dn.new_quality_stats()

    assert dn.verify_cause_evidence(event, _items(), quality) is True
    assert event["context"].startswith("最高法院裁定")
    assert quality["cause_evidence_rejected"] == 0
    # 内部字段不得泄漏到后续阶段
    assert "context_evidence" not in event


def test_span_absent_from_sources_drops_the_cause():
    event = _event(
        "白宫意在向北京施压。",
        "白宫官员表示此举意在向北京施压。")
    quality = dn.new_quality_stats()

    assert dn.verify_cause_evidence(event, _items(), quality) is False
    assert "context" not in event
    assert "context_evidence" not in event
    assert quality["cause_evidence_rejected"] == 1


def test_paraphrased_span_is_rejected():
    """改写过的引文不算逐字回溯——这正是要拦住的推断路径。"""
    event = _event(
        "最高法院裁定关税违法后白宫换了法律依据。",
        "由于最高法院作出了不利裁决，白宫方面决定更换加征关税所依据的法律条文。")
    quality = dn.new_quality_stats()

    assert dn.verify_cause_evidence(event, _items(), quality) is False
    assert "context" not in event
    assert quality["cause_evidence_rejected"] == 1


def test_trivially_short_span_cannot_vouch_for_a_cause():
    event = _event("白宫改用第301条。", "白宫")
    quality = dn.new_quality_stats()

    assert dn.verify_cause_evidence(event, _items(), quality) is False
    assert quality["cause_evidence_rejected"] == 1


def test_empty_cause_needs_no_span_and_is_not_counted_as_rejected():
    event = _event("", "")
    quality = dn.new_quality_stats()

    assert dn.verify_cause_evidence(event, _items(), quality) is False
    # 空起因保持 enrich 的空串约定，不是被闸门拒绝
    assert event["context"] == ""
    assert "context_evidence" not in event
    assert quality["cause_evidence_rejected"] == 0


def test_punctuation_and_width_differences_still_match():
    event = _event(
        "白宫改用第301条并在旧关税到期当天生效。",
        "白宫随即改用第３０１条重新加征，并选在旧关税到期当天生效")
    quality = dn.new_quality_stats()

    assert dn.verify_cause_evidence(event, _items(), quality) is True
    assert quality["cause_evidence_rejected"] == 0


def test_span_matched_against_rss_summary_when_no_fulltext():
    """interim 模式只有 200 字摘要，闸门照样按同一份材料核对。"""
    items = _items(evidence_text="")
    items[0]["desc"] = "新关税遭到起诉，原因是旧关税已被最高法院裁定违法。"
    event = _event(
        "旧关税已被最高法院裁定违法。",
        "原因是旧关税已被最高法院裁定违法")
    quality = dn.new_quality_stats()

    assert dn.verify_cause_evidence(event, items, quality) is True


def test_enrich_drops_unbacked_cause_end_to_end():
    class InventedCauseLLM:
        def json_call(self, _system, _user):
            return [{
                "idx": 0, "title": "关税遭起诉", "summary": "新关税遭起诉。",
                "why": "影响进口商。",
                "context": "白宫意在向北京施压。",
                "context_evidence": "白宫官员表示此举意在向北京施压。",
                "significance": "", "watch": "", "claims": [],
                "status": "已确认", "tags": [],
            }]

    events = [{"ids": [0], "category": "world", "title": "关税遭起诉"}]
    quality = dn.new_quality_stats()

    dn.enrich(InventedCauseLLM(), events, _items(),
              {"topic_tags": [], "detail": {"enabled": False},
               "objectivity": {"mode": "interim"}}, quality=quality)

    assert "context" not in events[0]
    assert "context_evidence" not in events[0]
    assert quality["cause_evidence_rejected"] == 1


def test_enrich_keeps_backed_cause_end_to_end():
    class GroundedCauseLLM:
        def json_call(self, _system, _user):
            return [{
                "idx": 0, "title": "关税遭起诉", "summary": "新关税遭起诉。",
                "why": "影响进口商。",
                "context": "最高法院裁定旧关税违法，白宫改用第301条。",
                "context_evidence": "白宫随即改用第301条重新加征，并选在旧关税到期当天生效。",
                "significance": "", "watch": "", "claims": [],
                "status": "已确认", "tags": [],
            }]

    events = [{"ids": [0], "category": "world", "title": "关税遭起诉"}]
    quality = dn.new_quality_stats()

    dn.enrich(GroundedCauseLLM(), events, _items(),
              {"topic_tags": [], "detail": {"enabled": False},
               "objectivity": {"mode": "interim"}}, quality=quality)

    assert events[0]["context"].startswith("最高法院裁定")
    assert "context_evidence" not in events[0]
    assert quality["cause_evidence_rejected"] == 0


def test_prompt_requires_a_verbatim_span():
    class CapturingLLM:
        system = ""

        def json_call(self, system, _user):
            CapturingLLM.system = system
            return []

    dn.enrich(CapturingLLM(), [{"ids": [0], "category": "world", "title": "T"}],
              _items(), {"topic_tags": [], "detail": {"enabled": False},
                         "objectivity": {"mode": "interim"}})

    assert "context_evidence" in CapturingLLM.system
    assert "逐字复制" in CapturingLLM.system
