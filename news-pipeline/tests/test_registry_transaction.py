import copy
import json
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import daily_news as dn


def _trusted_validation_response():
    return {"validations": [{
        "candidate": 0,
        "matches_mainline": True,
        "matches_latest": True,
        "history": [{"row": 0, "relevant": True}],
    }]}


class MatchLLM:
    def json_call(self, system, _user):
        if "连续性门" in system:
            return _trusted_validation_response()
        return {"matches": [{"today": 0, "registry": 0}]}


class NoMatchLLM:
    def json_call(self, system, _user):
        if "连续性门" in system:
            return _trusted_validation_response()
        return {"matches": []}


class TrustChainLLM:
    def __init__(self, validations, matches=None):
        self.validations = validations
        self.matches = matches or [{"today": 0, "registry": 0}]

    def json_call(self, system, _user):
        if "连续性门" in system:
            return {"validations": self.validations}
        return {"matches": self.matches}


def _legacy_registry():
    return {
        "version": 1,
        "events": [{
            "event_id": "evt-legacy",
            "title": "Model launch",
            "category": "ai",
            "status": "active",
            "pinned": False,
            "first_seen": "2026-07-20",
            "last_seen": "2026-07-20",
            "history": [{
                "date": "2026-07-20",
                "title": "Model launch",
                "summary": "The model launched.",
                "news_status": "confirmed",
            }],
        }],
    }


def _source_items():
    return [{
        "title": "Model launch follow-up",
        "desc": "The company published adoption figures.",
        "url": "https://example.test/model",
        "source": "Example News",
        "source_id": "example-news",
        "source_type": "fact",
        "tier": "T1",
        "credibility": 9,
        "time": "2026-07-21T01:00:00+00:00",
    }]


def _picked_event():
    return {
        "ids": [0],
        "category": "ai",
        "title": "Model launch follow-up",
        "summary": "Adoption figures are now available.",
        "status": "confirmed",
        "watch": "Watch whether enterprise adoption continues.",
        "score": 90,
        "tier": "T1",
        "tags": [],
    }


def test_legacy_registry_upgrades_with_final_metadata_without_public_projection_change(
        tmp_path, monkeypatch):
    legacy = _legacy_registry()
    (tmp_path / "events.json").write_text(
        json.dumps(legacy, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    picked = [_picked_event()]
    items = _source_items()

    registry = dn.track_events(
        MatchLLM(), picked, "2026-07-21", {"events": {}}, items=items)

    saved = json.loads((tmp_path / "events.json").read_text(encoding="utf-8"))
    assert registry == saved
    assert registry["version"] == 2
    assert registry["events"][0]["history"][-1] == {
        "date": "2026-07-21",
        "title": "Model launch follow-up",
        "summary": "Adoption figures are now available.",
        "news_status": "confirmed",
        "watch": "Watch whether enterprise adoption continues.",
        "sources": ["example-news"],
        "item_ref": "2026-07-21:pick-0",
    }

    public_item = dn.event_to_item(picked[0], items, "pick")
    assert public_item["day_count"] == 2
    assert public_item["history"] == [{
        "date": "2026-07-20",
        "summary": "The model launched.",
    }]
    assert "item_ref" not in public_item["history"][0]


def test_registry_transaction_is_prepared_in_memory_without_mutating_input(tmp_path):
    original = _legacy_registry()
    before = copy.deepcopy(original)
    picked = [_picked_event()]

    prepared = dn.prepare_registry_transaction(
        MatchLLM(), original, picked, "2026-07-21", {"events": {}},
        items=_source_items())

    assert original == before
    assert prepared["version"] == 2
    assert prepared["events"][0]["history"][-1]["date"] == "2026-07-21"
    assert not (tmp_path / "events.json").exists()


def test_atomic_persistence_failure_keeps_prior_registry_intact(tmp_path, monkeypatch):
    prior_text = json.dumps(_legacy_registry(), ensure_ascii=False, indent=2) + "\n"
    registry_path = tmp_path / "events.json"
    registry_path.write_text(prior_text, encoding="utf-8")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    def fail_replace(_source, _target):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(dn.os, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated replace failure"):
        dn.track_events(
            MatchLLM(), [_picked_event()], "2026-07-21", {"events": {}},
            items=_source_items())

    assert registry_path.read_text(encoding="utf-8") == prior_text
    assert list(tmp_path.glob(".events.json.*.tmp")) == []


def test_same_day_rerun_replaces_final_row_without_inflating_history(
        tmp_path, monkeypatch):
    (tmp_path / "events.json").write_text(
        json.dumps(_legacy_registry(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    first = _picked_event()
    first_registry = dn.track_events(
        MatchLLM(), [first], "2026-07-21", {"events": {}},
        items=_source_items())
    first_event_id = first_registry["events"][0]["event_id"]

    rerun = _picked_event()
    rerun["summary"] = "Corrected adoption figures are available."
    rerun["watch"] = "Watch the corrected enterprise adoption trend."
    registry = dn.track_events(
        NoMatchLLM(), [rerun], "2026-07-21", {"events": {}},
        items=_source_items())

    assert len(registry["events"]) == 1
    assert registry["events"][0]["event_id"] == first_event_id
    history = registry["events"][0]["history"]
    assert [row["date"] for row in history] == ["2026-07-20", "2026-07-21"]
    assert history[-1]["summary"] == "Corrected adoption figures are available."
    assert history[-1]["watch"] == "Watch the corrected enterprise adoption trend."
    assert rerun["day_count"] == 2


def test_pinned_secondary_history_uses_final_v2_metadata():
    registry = _legacy_registry()
    registry["events"][0]["pinned"] = True
    secondary = [_picked_event()]

    prepared = dn.prepare_registry_transaction(
        MatchLLM(), registry, [], "2026-07-21", {"events": {}},
        secondary=secondary, items=_source_items())

    assert prepared["events"][0]["history"][-1] == {
        "date": "2026-07-21",
        "title": "Model launch follow-up",
        "summary": "Adoption figures are now available.",
        "news_status": "confirmed",
        "watch": "Watch whether enterprise adoption continues.",
        "sources": ["example-news"],
        "item_ref": "2026-07-21:more-0",
    }


def test_pinned_secondary_same_day_rerun_replaces_row_without_llm_rematch():
    registry = _legacy_registry()
    registry["events"][0]["pinned"] = True
    first = _picked_event()
    prepared = dn.prepare_registry_transaction(
        MatchLLM(), registry, [], "2026-07-21", {"events": {}},
        secondary=[first], items=_source_items())

    rerun = _picked_event()
    rerun["summary"] = "Corrected secondary figures are available."
    rerun["watch"] = "Watch the corrected secondary trend."
    prepared = dn.prepare_registry_transaction(
        NoMatchLLM(), prepared, [], "2026-07-21", {"events": {}},
        secondary=[rerun], items=_source_items())

    history = prepared["events"][0]["history"]
    assert [row["date"] for row in history] == ["2026-07-20", "2026-07-21"]
    assert history[-1]["summary"] == "Corrected secondary figures are available."
    assert history[-1]["watch"] == "Watch the corrected secondary trend."
    assert history[-1]["item_ref"] == "2026-07-21:more-0"


def test_secondary_rerun_target_is_not_also_matched_to_a_picked_item():
    registry = _legacy_registry()
    registry["events"][0]["pinned"] = True
    prepared = dn.prepare_registry_transaction(
        MatchLLM(), registry, [], "2026-07-21", {"events": {}},
        secondary=[_picked_event()], items=_source_items())

    items = _source_items() + [{**_source_items()[0],
                                "url": "https://example.test/other",
                                "source_id": "other-news"}]
    picked = [{**_picked_event(), "ids": [1], "title": "Different picked item"}]
    prepared = dn.prepare_registry_transaction(
        MatchLLM(), prepared, picked, "2026-07-21", {"events": {}},
        secondary=[_picked_event()], items=items)

    legacy_event = next(event for event in prepared["events"]
                        if event["event_id"] == "evt-legacy")
    today_rows = [row for row in legacy_event["history"]
                  if row["date"] == "2026-07-21"]
    assert [row["item_ref"] for row in today_rows] == ["2026-07-21:pick-1"]
    assert picked[0]["event_id"] == "evt-legacy"
    assert picked[0]["day_count"] == 2


def test_untracked_secondary_rerun_does_not_restore_current_day_row():
    registry = _legacy_registry()
    registry["events"][0]["pinned"] = True
    prepared = dn.prepare_registry_transaction(
        MatchLLM(), registry, [], "2026-07-21", {"events": {}},
        secondary=[_picked_event()], items=_source_items())

    prepared = dn.prepare_registry_transaction(
        NoMatchLLM(), prepared, [], "2026-07-21", {"events": {}},
        secondary=[_picked_event()], items=_source_items(),
        feedback=[{"ts": "2026-07-21T12:00:00Z", "action": "untrack",
                   "event_id": "evt-legacy"}])

    event = prepared["events"][0]
    assert event["pinned"] is False
    assert [row["date"] for row in event["history"]] == ["2026-07-20"]


def test_trust_chain_filters_polluted_rows_and_projects_only_verified_history():
    registry = _legacy_registry()
    registry["events"][0]["history"] = [
        {
            "date": "2026-07-18",
            "title": "Model launch",
            "summary": "The model launched.",
            "news_status": "confirmed",
            "item_ref": "2026-07-18:pick-3",
        },
        {
            "date": "2026-07-19",
            "title": "Unrelated image launch",
            "summary": "A different image model launched.",
            "news_status": "confirmed",
        },
        {
            "date": "2026-07-20",
            "title": "Model launch adoption",
            "summary": "Initial adoption figures arrived.",
            "news_status": "confirmed",
        },
    ]
    registry["events"][0]["last_seen"] = "2026-07-20"
    picked = [_picked_event()]
    llm = TrustChainLLM([{
        "candidate": 0,
        "matches_mainline": True,
        "matches_latest": True,
        "history": [
            {"row": 0, "relevant": True},
            {"row": 1, "relevant": False},
            {"row": 2, "relevant": True},
        ],
    }])

    dn.prepare_registry_transaction(
        llm, registry, picked, "2026-07-21", {"events": {}},
        items=_source_items())

    assert picked[0]["trusted_continuation"] is True
    assert picked[0]["day_count"] == 3
    assert [row["date"] for row in picked[0]["history_prev"]] == [
        "2026-07-18", "2026-07-20"]
    public_item = dn.event_to_item(picked[0], _source_items(), "pick")
    assert public_item["trusted_continuation"] is True
    assert public_item["day_count"] == 3
    assert public_item["history"] == [
        {
            "date": "2026-07-20",
            "summary": "Initial adoption figures arrived.",
        },
        {
            "date": "2026-07-18",
            "summary": "The model launched.",
            "item_ref": "2026-07-18:pick-3",
        },
    ]


def test_same_category_false_join_fails_closed_as_one_off_without_context():
    picked = [{**_picked_event(), "context": "Untrusted inherited context",
               "watch_recap": {"status": "兑现"}}]
    llm = TrustChainLLM([{
        "candidate": 0,
        "matches_mainline": False,
        "matches_latest": False,
        "history": [{"row": 0, "relevant": False}],
    }])

    prepared = dn.prepare_registry_transaction(
        llm, _legacy_registry(), picked, "2026-07-21", {"events": {}},
        items=_source_items())

    assert picked[0]["event_id"] != "evt-legacy"
    assert picked[0]["day_count"] == 1
    assert picked[0]["history_prev"] == []
    assert "trusted_continuation" not in picked[0]
    assert "context" not in picked[0]
    assert "watch_recap" not in picked[0]
    assert len(prepared["events"]) == 2


def test_malformed_validation_fails_closed_only_for_affected_candidate():
    registry = _legacy_registry()
    second = copy.deepcopy(registry["events"][0])
    second.update({"event_id": "evt-second", "title": "Second launch"})
    registry["events"].append(second)
    picked = [_picked_event(), {**_picked_event(), "title": "Second follow-up"}]
    llm = TrustChainLLM(
        [{
            "candidate": 0,
            "matches_mainline": True,
            "matches_latest": True,
            "history": [{"row": 0, "relevant": True}],
        }, {
            "candidate": 99,
            "matches_mainline": True,
            "matches_latest": True,
            "history": [{"row": 0, "relevant": True}],
        }],
        matches=[{"today": 0, "registry": 0}, {"today": 1, "registry": 1}],
    )

    dn.prepare_registry_transaction(
        llm, registry, picked, "2026-07-21", {"events": {}},
        items=_source_items())

    assert picked[0]["event_id"] == "evt-legacy"
    assert picked[0]["trusted_continuation"] is True
    assert picked[1]["event_id"] not in {"evt-legacy", "evt-second"}
    assert picked[1]["day_count"] == 1
