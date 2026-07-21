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


class TrajectoryLLM:
    def __init__(self, trajectories, audits, validations=None, matches=None):
        self.trajectories = trajectories
        self.audits = audits
        self.validations = validations or _trusted_validation_response()["validations"]
        self.matches = matches or [{"today": 0, "registry": 0}]
        self.calls = []

    def json_call(self, system, user):
        if "连续性门" in system:
            stage = "continuity"
            response = {"validations": self.validations}
        elif "轨迹生成" in system:
            stage = "generation"
            response = self.trajectories
        elif "轨迹审计" in system:
            stage = "audit"
            response = self.audits
        else:
            stage = "match"
            response = {"matches": self.matches}
        self.calls.append((stage, user))
        if isinstance(response, Exception):
            raise response
        return response


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


def _trajectory_registry():
    registry = _legacy_registry()
    registry["events"][0]["history"][0].update({
        "watch": "Watch for the first enterprise adoption report.",
        "sources": ["example-news"],
        "item_ref": "2026-07-20:pick-4",
    })
    return registry


def _trajectory_result(context="走向回对（兑现）：首份企业采用报告已经发布。",
                       watch="若企业席位继续增长，可观察下一份采用报告。",
                       claims=None):
    return {"trajectories": [{
        "idx": 0,
        "context": context,
        "watch": watch,
        "claims": claims if claims is not None else [{
            "text": "采用数据仍只覆盖初期窗口。",
            "kind": "uncertain",
            "sources": ["Example News"],
        }],
    }]}


def _trajectory_audit(fields=None, claims=None):
    return {"audits": [{
        "idx": 0,
        "fields": fields or {"context": True, "watch": True},
        "claims": claims if claims is not None else [True],
    }]}


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
        "source_keys": dn._same_day_source_keys(picked[0], items),
        "event_identity": dn._same_day_event_identity(picked[0], items),
    }

    public_item = dn.event_to_item(picked[0], items, "pick")
    assert "trusted_continuation" not in public_item
    assert "day_count" not in public_item
    assert "history" not in public_item


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


def test_deferred_registry_transaction_survives_output_failure(tmp_path, monkeypatch):
    prior_text = json.dumps(_legacy_registry(), ensure_ascii=False, indent=2) + "\n"
    registry_path = tmp_path / "events.json"
    registry_path.write_text(prior_text, encoding="utf-8")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    prepared = dn.track_events(
        MatchLLM(), [_picked_event()], "2026-07-21", {"events": {}},
        items=_source_items(), persist=False)

    assert prepared["version"] == 2
    assert registry_path.read_text(encoding="utf-8") == prior_text
    persisted = []
    monkeypatch.setattr(dn, "persist_registry",
                        lambda registry, data_dir=None: persisted.append(registry))

    def fail_output(*_args, **_kwargs):
        raise RuntimeError("output failed")

    monkeypatch.setattr(dn, "write_output", fail_output)
    with pytest.raises(RuntimeError, match="output failed"):
        dn.write_output_and_commit_registry(
            "2026-07-21", "brief", [_picked_event()], [], _source_items(),
            {"events": {}}, prepared)
    assert persisted == []
    assert registry_path.read_text(encoding="utf-8") == prior_text

    monkeypatch.setattr(dn, "write_output", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(
        dn, "validate_daily_output_file", lambda *_args: ["invalid output"])
    _, errors = dn.write_output_and_commit_registry(
        "2026-07-21", "brief", [_picked_event()], [], _source_items(),
        {"events": {}}, prepared)
    assert errors == ["invalid output"]
    assert persisted == []

    monkeypatch.setattr(dn, "validate_daily_output_file", lambda *_args: [])
    _, errors = dn.write_output_and_commit_registry(
        "2026-07-21", "brief", [_picked_event()], [], _source_items(),
        {"events": {}}, prepared)
    assert errors == []
    assert persisted == [prepared]


def test_output_sanitization_precedes_registry_snapshot(monkeypatch):
    picked = [{**_picked_event(), "context": "Generated context.",
               "claims": [{"text": "Generated claim.", "kind": "analysis",
                           "sources": ["Example News"]}]}]

    def sanitize(event, _items):
        for field in ("context", "watch", "claims"):
            event.pop(field, None)

    monkeypatch.setattr(dn, "sanitize_objectivity_event", sanitize)
    cfg = {"events": {}, "_objectivity_runtime_mode": "active"}
    dn.prepare_events_for_output(picked, [], _source_items(), cfg)
    prepared = dn.prepare_registry_transaction(
        NoMatchLLM(), {"version": 1, "events": []}, picked, "2026-07-21",
        cfg, items=_source_items())

    assert not ({"context", "watch", "claims"} & set(picked[0]))
    assert "watch" not in prepared["events"][0]["history"][-1]


def test_post_trajectory_sanitization_matches_registry_and_public_watch(monkeypatch):
    picked = [_picked_event()]
    original_sanitize = dn.sanitize_objectivity_event

    def sanitize(event, items):
        original_sanitize(event, items)
        if str(event.get("watch", "")).startswith("若企业席位"):
            event.pop("watch", None)

    monkeypatch.setattr(dn, "sanitize_objectivity_event", sanitize)
    cfg = {"events": {}, "_objectivity_runtime_mode": "active"}
    prepared = dn.prepare_registry_transaction(
        TrajectoryLLM(_trajectory_result(), _trajectory_audit()),
        _trajectory_registry(), picked, "2026-07-21", cfg,
        items=_source_items())
    public = dn.event_to_item(
        picked[0], _source_items(), "pick", full_objectivity=True,
        source_limit=4)

    assert "watch" not in picked[0]
    assert "watch" not in prepared["events"][0]["history"][-1]
    assert "watch" not in public


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
    assert rerun["day_count"] == 1
    assert "trusted_continuation" not in rerun


def test_first_day_same_day_rerun_keeps_event_id_when_title_changes():
    first = _picked_event()
    prepared = dn.prepare_registry_transaction(
        NoMatchLLM(), {"version": 1, "events": []}, [first], "2026-07-21",
        {"events": {}}, items=_source_items())
    event_id = first["event_id"]

    rerun = {**_picked_event(), "title": "Corrected launch title",
             "summary": "Corrected first-day summary."}
    prepared = dn.prepare_registry_transaction(
        NoMatchLLM(), prepared, [rerun], "2026-07-21", {"events": {}},
        items=_source_items())

    assert len(prepared["events"]) == 1
    assert rerun["event_id"] == event_id
    assert rerun["day_count"] == 1
    assert "trusted_continuation" not in rerun
    assert prepared["events"][0]["history"][-1]["title"] == \
        "Corrected launch title"


def test_same_day_identity_survives_global_index_and_event_id_reordering():
    primary = _source_items()[0]
    corroborating = {
        **primary,
        "title": "Wire version of the same event",
        "url": "https://wire.example.test/model",
        "source": "Wire",
        "source_id": "wire",
        "credibility": 8,
    }
    unrelated = {
        **primary,
        "title": "Unrelated item",
        "url": "https://example.test/unrelated",
        "source": "Other",
        "source_id": "other",
    }
    first_items = [primary, corroborating, unrelated]
    first = {**_picked_event(), "ids": [0, 1]}
    prepared = dn.prepare_registry_transaction(
        NoMatchLLM(), {"version": 1, "events": []}, [first], "2026-07-21",
        {"events": {}}, items=first_items)
    event_id = first["event_id"]
    identity = prepared["events"][0]["history"][-1]["event_identity"]

    rerun_items = [unrelated, corroborating, primary]
    rerun = {**_picked_event(), "ids": [1, 2], "title": "Corrected title"}
    prepared = dn.prepare_registry_transaction(
        NoMatchLLM(), prepared, [rerun], "2026-07-21", {"events": {}},
        items=rerun_items)

    assert len(prepared["events"]) == 1
    assert rerun["event_id"] == event_id
    assert prepared["events"][0]["history"][-1]["event_identity"] == identity
    assert prepared["events"][0]["history"][-1]["item_ref"] == \
        "2026-07-21:pick-1"
    assert dn.event_to_item(rerun, rerun_items, "pick")["id"] == "pick-1"


def test_same_day_identity_survives_higher_priority_source_addition():
    original = _source_items()[0]
    first = _picked_event()
    prepared = dn.prepare_registry_transaction(
        NoMatchLLM(), {"version": 1, "events": []}, [first], "2026-07-21",
        {"events": {}}, items=[original])
    event_id = first["event_id"]
    event_identity = prepared["events"][0]["history"][-1]["event_identity"]
    first_public = dn.event_to_item(first, [original], "pick")

    higher_priority = {
        **original,
        "title": "Wire confirmation of the same launch",
        "url": "https://wire.example.test/model-confirmation?edition=late",
        "source": "Wire",
        "source_id": "wire",
        "credibility": 10,
    }
    rerun_items = [original, higher_priority]
    rerun = {**_picked_event(), "ids": [1, 0], "title": "Updated launch title"}
    prepared = dn.prepare_registry_transaction(
        NoMatchLLM(), prepared, [rerun], "2026-07-21", {"events": {}},
        items=rerun_items)
    rerun_public = dn.event_to_item(rerun, rerun_items, "pick")

    assert len(prepared["events"]) == 1
    assert rerun["event_id"] == event_id
    assert prepared["events"][0]["history"][-1]["event_identity"] == \
        event_identity
    assert first_public["event_id"] == rerun_public["event_id"]


def test_same_day_identity_survives_removing_one_of_the_prior_sources():
    original = _source_items()[0]
    corroborating = {
        **original,
        "title": "Independent confirmation of the same launch",
        "url": "https://wire.example.test/model-confirmation",
        "source": "Wire",
        "source_id": "wire",
        "credibility": 10,
    }
    first = _picked_event()
    prepared = dn.prepare_registry_transaction(
        NoMatchLLM(), {"version": 1, "events": []}, [first], "2026-07-21",
        {"events": {}}, items=[original])
    event_id = first["event_id"]
    event_identity = prepared["events"][0]["history"][-1]["event_identity"]

    expanded = {**_picked_event(), "ids": [1, 0]}
    prepared = dn.prepare_registry_transaction(
        NoMatchLLM(), prepared, [expanded], "2026-07-21", {"events": {}},
        items=[original, corroborating])
    retained_only = {**_picked_event(), "ids": [0], "title": "Final wire title"}
    prepared = dn.prepare_registry_transaction(
        NoMatchLLM(), prepared, [retained_only], "2026-07-21", {"events": {}},
        items=[corroborating])

    assert len(prepared["events"]) == 1
    assert retained_only["event_id"] == event_id
    assert prepared["events"][0]["history"][-1]["event_identity"] == \
        event_identity


def test_same_day_identity_does_not_merge_distinct_urls_from_one_aggregator():
    first_item = _source_items()[0]
    second_item = {
        **first_item,
        "title": "A different launch from the same aggregator",
        "desc": "A different company launched a different model.",
        "url": "https://example.test/other-model?ref=feed",
    }
    first_events = [
        _picked_event(),
        {**_picked_event(), "ids": [1], "title": "Other model launch"},
    ]
    prepared = dn.prepare_registry_transaction(
        NoMatchLLM(), {"version": 1, "events": []}, first_events,
        "2026-07-21", {"events": {}}, items=[first_item, second_item])
    event_ids = {event["title"]: event["event_id"] for event in first_events}

    rerun_items = [second_item, first_item]
    rerun_events = [
        {**_picked_event(), "ids": [0], "title": "Other model launch"},
        {**_picked_event(), "ids": [1]},
    ]
    prepared = dn.prepare_registry_transaction(
        NoMatchLLM(), prepared, rerun_events, "2026-07-21", {"events": {}},
        items=rerun_items)

    assert len(prepared["events"]) == 2
    assert rerun_events[0]["event_id"] == event_ids["Other model launch"]
    assert rerun_events[1]["event_id"] == event_ids["Model launch follow-up"]


def test_same_day_overlap_must_be_one_to_one_before_reusing_an_event():
    first_item = _source_items()[0]
    second_item = {
        **first_item,
        "title": "Corroborating report",
        "url": "https://wire.example.test/model",
        "source": "Wire",
        "source_id": "wire",
    }
    combined = {**_picked_event(), "ids": [0, 1]}
    prepared = dn.prepare_registry_transaction(
        NoMatchLLM(), {"version": 1, "events": []}, [combined],
        "2026-07-21", {"events": {}}, items=[first_item, second_item])
    combined_event_id = combined["event_id"]

    split_events = [
        {**_picked_event(), "ids": [0], "title": "Original report event"},
        {**_picked_event(), "ids": [1], "title": "Separate wire event"},
    ]
    prepared = dn.prepare_registry_transaction(
        NoMatchLLM(), prepared, split_events, "2026-07-21", {"events": {}},
        items=[first_item, second_item])

    assert len(prepared["events"]) == 2
    assert split_events[0]["event_id"] != split_events[1]["event_id"]
    assert all(event["event_id"] != combined_event_id for event in split_events)
    assert {event["event_id"] for event in prepared["events"]} == {
        event["event_id"] for event in split_events
    }


def test_same_day_mixed_overlap_graph_rejects_every_ambiguous_edge():
    source_x = _source_items()[0]
    source_y = {
        **source_x,
        "title": "Independent event Y",
        "url": "https://wire.example.test/event-y",
        "source": "Wire",
        "source_id": "wire",
    }
    prior_events = [
        {**_picked_event(), "ids": [0], "title": "Prior event A"},
        {**_picked_event(), "ids": [1], "title": "Prior event B"},
    ]
    prepared = dn.prepare_registry_transaction(
        NoMatchLLM(), {"version": 1, "events": []}, prior_events,
        "2026-07-21", {"events": {}}, items=[source_x, source_y])
    prior_ids = {event["event_id"] for event in prior_events}
    prior_registry = copy.deepcopy(prepared)

    current_events = [
        {**_picked_event(), "ids": [0], "title": "Prior event A"},
        {**_picked_event(), "ids": [0, 1], "title": "Current event C2"},
    ]
    prepared = dn.prepare_registry_transaction(
        NoMatchLLM(), prepared, current_events, "2026-07-21", {"events": {}},
        items=[source_x, source_y])
    current_ids = [event["event_id"] for event in current_events]

    assert len(prepared["events"]) == 2
    assert prior_ids.isdisjoint(current_ids)
    assert len(set(current_ids)) == 2
    assert {event["event_id"] for event in prepared["events"]} == set(current_ids)

    reordered_events = [
        {**_picked_event(), "ids": [0, 1], "title": "Current event C2"},
        {**_picked_event(), "ids": [1], "title": "Prior event A"},
    ]
    dn.prepare_registry_transaction(
        NoMatchLLM(), prior_registry, reordered_events, "2026-07-21",
        {"events": {}}, items=[source_y, source_x])
    assert {event["title"]: event["event_id"] for event in current_events} == {
        event["title"]: event["event_id"] for event in reordered_events
    }


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
        "source_keys": dn._same_day_source_keys(
            secondary[0], _source_items()),
        "event_identity": dn._same_day_event_identity(
            secondary[0], _source_items()),
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


def test_pinned_secondary_same_day_rerun_inherits_identity_after_source_addition():
    registry = _legacy_registry()
    registry["events"][0]["pinned"] = True
    original = _source_items()[0]
    first = _picked_event()
    prepared = dn.prepare_registry_transaction(
        MatchLLM(), registry, [], "2026-07-21", {"events": {}},
        secondary=[first], items=[original])
    event_identity = prepared["events"][0]["history"][-1]["event_identity"]

    higher_priority = {
        **original,
        "url": "https://wire.example.test/model-confirmation",
        "source": "Wire",
        "source_id": "wire",
        "credibility": 10,
    }
    rerun = {**_picked_event(), "ids": [1, 0]}
    prepared = dn.prepare_registry_transaction(
        NoMatchLLM(), prepared, [], "2026-07-21", {"events": {}},
        secondary=[rerun], items=[original, higher_priority])

    assert len(prepared["events"]) == 1
    assert prepared["events"][0]["event_id"] == "evt-legacy"
    assert prepared["events"][0]["history"][-1]["event_identity"] == \
        event_identity


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
    assert picked[0]["day_count"] == 1
    assert "trusted_continuation" not in picked[0]


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
    validations = [{
        "candidate": 0,
        "matches_mainline": True,
        "matches_latest": True,
        "history": [
            {"row": 0, "relevant": True},
            {"row": 1, "relevant": False},
            {"row": 2, "relevant": True},
        ],
    }]
    llm = TrajectoryLLM(
        _trajectory_result(context="Verified prior updates lead to today."),
        _trajectory_audit(), validations=validations)

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


def test_continuity_rejects_latest_row_marked_irrelevant_despite_latest_flag():
    registry = _legacy_registry()
    registry["events"][0]["history"].insert(0, {
        "date": "2026-07-19",
        "title": "Earlier related update",
        "summary": "An earlier update was related.",
        "news_status": "confirmed",
    })
    picked = [{**_picked_event(), "context": "Untrusted inherited context"}]
    llm = TrustChainLLM([{
        "candidate": 0,
        "matches_mainline": True,
        "matches_latest": True,
        "history": [
            {"row": 0, "relevant": True},
            {"row": 1, "relevant": False},
        ],
    }])

    dn.prepare_registry_transaction(
        llm, registry, picked, "2026-07-21", {"events": {}},
        items=_source_items())

    assert picked[0]["event_id"] != "evt-legacy"
    assert picked[0]["day_count"] == 1
    assert "trusted_continuation" not in picked[0]
    assert "context" not in picked[0]


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


def test_unmatched_one_off_does_not_publish_base_enrich_context():
    picked = [{**_picked_event(), "context": "Generic product background."}]

    dn.prepare_registry_transaction(
        NoMatchLLM(), {"version": 1, "events": []}, picked, "2026-07-21",
        {"events": {}, "trajectory": {"enabled": True}}, items=_source_items())
    public = dn.event_to_item(picked[0], _source_items(), "pick")

    assert "context" not in picked[0]
    assert "context" not in public


def test_malformed_validation_fails_closed_only_for_affected_candidate():
    registry = _legacy_registry()
    second = copy.deepcopy(registry["events"][0])
    second.update({"event_id": "evt-second", "title": "Second launch"})
    registry["events"].append(second)
    picked = [_picked_event(), {**_picked_event(), "title": "Second follow-up"}]
    validations = [{
                "candidate": 0,
            "matches_mainline": True,
            "matches_latest": True,
            "history": [{"row": 0, "relevant": True}],
        }, {
            "candidate": 99,
            "matches_mainline": True,
            "matches_latest": True,
            "history": [{"row": 0, "relevant": True}],
            }]
    llm = TrajectoryLLM(
        _trajectory_result(context="Verified prior updates lead to today."),
        _trajectory_audit(), validations=validations,
        matches=[{"today": 0, "registry": 0}, {"today": 1, "registry": 1}])

    dn.prepare_registry_transaction(
        llm, registry, picked, "2026-07-21", {"events": {}},
        items=_source_items())

    assert picked[0]["event_id"] == "evt-legacy"
    assert picked[0]["trusted_continuation"] is True
    assert picked[1]["event_id"] not in {"evt-legacy", "evt-second"}
    assert picked[1]["day_count"] == 1


def test_trusted_trajectory_uses_scoped_evidence_and_persists_final_watch():
    registry = _trajectory_registry()
    registry["events"][0]["history"].insert(0, {
        "date": "2026-07-19",
        "title": "Unrelated image launch",
        "summary": "A different image model launched.",
        "news_status": "confirmed",
        "watch": "Watch image subscriptions.",
        "sources": ["unrelated-news"],
    })
    picked = [{
        **_picked_event(),
        "context": "Base audited context.",
        "claims": [{"text": "Base claim.", "kind": "analysis",
                    "sources": ["Example News"]}],
    }]
    llm = TrajectoryLLM(
        _trajectory_result(),
        _trajectory_audit(),
        validations=[{
            "candidate": 0,
            "matches_mainline": True,
            "matches_latest": True,
            "history": [
                {"row": 0, "relevant": False},
                {"row": 1, "relevant": True},
            ],
        }],
    )

    prepared = dn.prepare_registry_transaction(
        llm, registry, picked, "2026-07-21", {"events": {}},
        items=_source_items())

    assert [stage for stage, _ in llm.calls] == [
        "match", "continuity", "generation", "audit"]
    generation_payload = json.loads(next(
        user for stage, user in llm.calls if stage == "generation"))
    audit_payload = json.loads(next(
        user for stage, user in llm.calls if stage == "audit"))
    assert [row["date"] for row in generation_payload["items"][0]["history"]] == [
        "2026-07-20"]
    assert "Unrelated image launch" not in json.dumps(
        generation_payload, ensure_ascii=False)
    assert audit_payload["items"][0]["history"] == \
        generation_payload["items"][0]["history"]
    assert audit_payload["items"][0]["reports"] == \
        generation_payload["items"][0]["reports"]
    assert picked[0]["context"] == "走向回对（兑现）：首份企业采用报告已经发布。"
    assert picked[0]["watch"] == "若企业席位继续增长，可观察下一份采用报告。"
    assert picked[0]["tier"] == "T1"
    assert prepared["events"][0]["history"][-1]["watch"] == picked[0]["watch"]
    assert prepared["events"][0]["history"][-1]["sources"] == ["example-news"]
    assert prepared["events"][0]["history"][-1]["item_ref"] == \
        "2026-07-21:pick-0"


def test_trajectory_audit_restores_fields_independently_and_drops_failed_claims():
    base_claim = {"text": "Base claim.", "kind": "analysis",
                  "sources": ["Example News"]}
    picked = [{
        **_picked_event(),
        "context": "Base audited context.",
        "watch": "Base audited watch.",
        "claims": [base_claim],
    }]
    generated_claims = [
        {"text": "Supported trajectory claim.", "kind": "analysis",
         "sources": ["Example News"]},
        {"text": "Unsupported trajectory claim.", "kind": "uncertain",
         "sources": ["Example News"]},
    ]
    llm = TrajectoryLLM(
        _trajectory_result(claims=generated_claims),
        _trajectory_audit(
            fields={"context": False, "watch": True},
            claims=[True, False]),
    )

    dn.prepare_registry_transaction(
        llm, _trajectory_registry(), picked, "2026-07-21", {"events": {}},
        items=_source_items())

    assert "context" not in picked[0]
    assert picked[0]["watch"] == "若企业席位继续增长，可观察下一份采用报告。"
    assert picked[0]["claims"] == [generated_claims[0]]
    assert picked[0]["tier"] == "T1"


def test_trajectory_claim_source_ids_cannot_escape_the_public_source_contract():
    base_claim = {"text": "Base claim.", "kind": "analysis",
                  "sources": ["Example News"]}
    picked = [{**_picked_event(), "claims": [base_claim]}]
    llm = TrajectoryLLM(
        _trajectory_result(claims=[{
            "text": "Historical source-id claim.",
            "kind": "analysis",
            "sources": ["example-news"],
        }]),
        _trajectory_audit(fields={"context": True, "watch": True}, claims=[]),
    )

    dn.prepare_registry_transaction(
        llm, _trajectory_registry(), picked, "2026-07-21", {"events": {}},
        items=_source_items())

    assert picked[0]["claims"] == [base_claim]
    assert "claims" not in json.loads(next(
        user for stage, user in llm.calls if stage == "audit"))["items"][0]["trajectory"]


def test_trajectory_claims_use_the_same_active_mode_source_limit_as_output():
    items = [{
        **_source_items()[0],
        "source": f"Source {index}",
        "source_id": f"source-{index}",
        "url": f"https://example.test/source-{index}",
    } for index in range(1, 6)]
    base_claim = {"text": "Base claim.", "kind": "analysis",
                  "sources": ["Source 1"]}
    picked = [{**_picked_event(), "ids": list(range(5)), "claims": [base_claim]}]
    llm = TrajectoryLLM(
        _trajectory_result(claims=[{
            "text": "Fifth-source claim.",
            "kind": "analysis",
            "sources": ["Source 5"],
        }]),
        _trajectory_audit(fields={"context": True, "watch": True}, claims=[]),
    )

    dn.prepare_registry_transaction(
        llm, _trajectory_registry(), picked, "2026-07-21",
        {"events": {}, "_objectivity_runtime_mode": "active"}, items=items)

    generation = json.loads(next(
        user for stage, user in llm.calls if stage == "generation"))
    assert [row["source"] for row in generation["items"][0]["reports"]] == [
        "Source 1", "Source 2", "Source 3", "Source 4"]
    assert picked[0]["claims"] == [base_claim]


def test_trajectory_audit_can_remove_generated_field_when_base_field_is_absent():
    picked = [_picked_event()]
    picked[0].pop("watch")
    llm = TrajectoryLLM(
        _trajectory_result(),
        _trajectory_audit(
            fields={"context": True, "watch": False}, claims=[True]),
    )

    dn.prepare_registry_transaction(
        llm, _trajectory_registry(), picked, "2026-07-21", {"events": {}},
        items=_source_items())

    assert "watch" not in picked[0]
    assert picked[0]["context"].startswith("走向回对（兑现）")


@pytest.mark.parametrize("status", ["待观察", "大致兑现", "基本反转"])
def test_invalid_recap_status_falls_back_before_trajectory_audit(status):
    picked = [{**_picked_event(), "context": "Base audited context."}]
    llm = TrajectoryLLM(
        _trajectory_result(context=f"走向回对（{status}）：出现了新数据。"),
        _trajectory_audit(fields={"watch": True}, claims=[True]),
    )

    dn.prepare_registry_transaction(
        llm, _trajectory_registry(), picked, "2026-07-21", {"events": {}},
        items=_source_items())

    assert "context" not in picked[0]
    audit_payload = json.loads(next(
        user for stage, user in llm.calls if stage == "audit"))
    assert "context" not in audit_payload["items"][0]["trajectory"]


def test_additional_invalid_recap_clause_falls_back_before_trajectory_audit():
    picked = [{**_picked_event(), "context": "Base audited context."}]
    llm = TrajectoryLLM(
        _trajectory_result(
            context="走向回对（兑现）：已有数据；走向回对（大致兑现）：仍待确认。"),
        _trajectory_audit(fields={"watch": True}, claims=[True]),
    )

    dn.prepare_registry_transaction(
        llm, _trajectory_registry(), picked, "2026-07-21", {"events": {}},
        items=_source_items())

    assert "context" not in picked[0]
    audit_payload = json.loads(next(
        user for stage, user in llm.calls if stage == "audit"))
    assert "context" not in audit_payload["items"][0]["trajectory"]


def test_recap_without_prior_final_watch_falls_back_to_base_context():
    picked = [{**_picked_event(), "context": "Base audited context."}]
    llm = TrajectoryLLM(
        _trajectory_result(),
        _trajectory_audit(fields={"watch": True}, claims=[True]),
    )

    dn.prepare_registry_transaction(
        llm, _legacy_registry(), picked, "2026-07-21", {"events": {}},
        items=_source_items())

    assert "context" not in picked[0]


def test_recap_requires_the_latest_verified_history_row_to_have_final_watch():
    registry = _trajectory_registry()
    registry["events"][0]["history"][0]["date"] = "2026-07-19"
    registry["events"][0]["history"].append({
        "date": "2026-07-20",
        "title": "Latest verified update",
        "summary": "A later update omitted its watch.",
        "news_status": "confirmed",
    })
    registry["events"][0]["last_seen"] = "2026-07-20"
    picked = [{**_picked_event(), "context": "Base audited context."}]
    llm = TrajectoryLLM(
        _trajectory_result(),
        _trajectory_audit(fields={"watch": True}, claims=[True]),
        validations=[{
            "candidate": 0,
            "matches_mainline": True,
            "matches_latest": True,
            "history": [
                {"row": 0, "relevant": True},
                {"row": 1, "relevant": True},
            ],
        }],
    )

    dn.prepare_registry_transaction(
        llm, registry, picked, "2026-07-21", {"events": {}},
        items=_source_items())

    assert "context" not in picked[0]
    audit_payload = json.loads(next(
        user for stage, user in llm.calls if stage == "audit"))
    assert "context" not in audit_payload["items"][0]["trajectory"]


def test_missing_generation_result_falls_back_only_for_affected_item():
    registry = _trajectory_registry()
    second = copy.deepcopy(registry["events"][0])
    second.update({"event_id": "evt-second", "title": "Second launch"})
    registry["events"].append(second)
    first = {**_picked_event(), "context": "First base context."}
    second_pick = {**_picked_event(), "ids": [1], "title": "Second follow-up",
                   "context": "Second base context.", "watch": "Second base watch."}
    items = _source_items() + [{**_source_items()[0],
                                "url": "https://example.test/second",
                                "source_id": "second-news"}]
    llm = TrajectoryLLM(
        _trajectory_result(),
        _trajectory_audit(),
        validations=[{
            "candidate": index,
            "matches_mainline": True,
            "matches_latest": True,
            "history": [{"row": 0, "relevant": True}],
        } for index in range(2)],
        matches=[{"today": 0, "registry": 0}, {"today": 1, "registry": 1}],
    )

    dn.prepare_registry_transaction(
        llm, registry, [first, second_pick], "2026-07-21", {"events": {}},
        items=items)

    assert first["watch"] == "若企业席位继续增长，可观察下一份采用报告。"
    assert "context" not in second_pick
    assert second_pick["watch"] == "Second base watch."
    assert "trusted_continuation" not in second_pick
    assert second_pick["day_count"] == 1


def test_whole_trajectory_audit_failure_restores_all_base_fields():
    base_claim = {"text": "Base claim.", "kind": "analysis",
                  "sources": ["Example News"]}
    picked = [{
        **_picked_event(),
        "context": "Base audited context.",
        "watch": "Base audited watch.",
        "claims": [base_claim],
    }]
    llm = TrajectoryLLM(
        _trajectory_result(), RuntimeError("trajectory audit unavailable"))

    prepared = dn.prepare_registry_transaction(
        llm, _trajectory_registry(), picked, "2026-07-21", {"events": {}},
        items=_source_items())

    assert "context" not in picked[0]
    assert picked[0]["watch"] == "Base audited watch."
    assert picked[0]["claims"] == [base_claim]
    assert "trusted_continuation" not in picked[0]
    assert picked[0]["day_count"] == 1
    assert prepared["events"][0]["history"][-1]["watch"] == "Base audited watch."


@pytest.mark.parametrize("audit", [
    {
        "idx": 0,
        "fields": {"context": True, "watch": True},
        "claims": [],
        "unexpected": True,
    },
    {
        "idx": 0,
        "fields": {"context": True, "watch": True},
        "claims": [True],
    },
])
def test_malformed_trajectory_audit_row_falls_back_without_partial_apply(audit):
    picked = [{
        **_picked_event(),
        "context": "Base audited context.",
        "watch": "Base audited watch.",
    }]
    trajectories = {"trajectories": [{
        "idx": 0,
        "context": "Verified history led to today's update.",
        "watch": "If adoption grows, observe the next company report.",
    }]}
    llm = TrajectoryLLM(trajectories, {"audits": [audit]})

    dn.prepare_registry_transaction(
        llm, _trajectory_registry(), picked, "2026-07-21", {"events": {}},
        items=_source_items())

    assert "context" not in picked[0]
    assert picked[0]["watch"] == "Base audited watch."
    assert "trusted_continuation" not in picked[0]
