import copy
import json
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import daily_news as dn


class MatchLLM:
    def json_call(self, _system, _user):
        return {"matches": [{"today": 0, "registry": 0}]}


class NoMatchLLM:
    def json_call(self, _system, _user):
        return {"matches": []}


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
