import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import daily_news as dn


def _item(title, desc=None, *, source_id="current"):
    return {
        "title": title,
        "desc": desc or title,
        "url": f"https://example.test/{source_id}",
        "source": source_id,
        "source_id": source_id,
        "source_type": "fact",
        "tier": "T1",
        "credibility": 9,
        "time": "2026-08-02T10:00:00+00:00",
    }


def _event(title="DeepSeek V4 Flash released", *, category="ai"):
    return {
        "ids": [0],
        "title": title,
        "summary": title,
        "category": category,
        "dims": {dimension: 8.0 for dimension in dn.DIMS},
    }


def _line(*, item_ref="2026-08-01:pick-46", last_seen="2026-08-01",
          category="ai", status="archived"):
    return {
        "event_id": "evt-20260801-f55954",
        "title": "DeepSeek V4 Flash released",
        "category": category,
        "status": status,
        "first_seen": "2026-08-01",
        "last_seen": last_seen,
        "history": [{
            "date": "2026-08-01",
            "title": "DeepSeek V4 Flash released",
            "summary": "DeepSeek released V4 Flash after post-training.",
            "news_status": "confirmed",
            "item_ref": item_ref,
        }],
    }


class VerdictLLM:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def json_call(self, _system, user):
        self.calls.append(json.loads(user))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class SequenceLLM:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def json_call(self, _system, user):
        self.calls.append(json.loads(user))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class EchoDifferentLLM:
    def __init__(self):
        self.users = []

    def json_call(self, _system, user):
        self.users.append(user)
        payload = json.loads(user)
        return {"items": [{
            "idx": row["idx"],
            "decision": "different_event",
            "registry_index": None,
            "reason": "Distinct event.",
        } for row in payload["items"]]}


def _gate(llm, registry, tmp_path, stats=None, **guard):
    cfg = {
        "cost_guard": {
            "cross_source_novelty_batch_size": guard.get("batch_size", 20),
            "cross_source_novelty_max_calls": guard.get("max_calls", 8),
        }
    }
    return dn.CrossSourceNoveltyGate(
        llm, registry, tmp_path, "2026-08-03", cfg,
        stats if stats is not None else dn.new_cross_source_novelty_stats())


def test_new_url_restatement_is_suppressed_and_material_addition_is_kept(tmp_path):
    registry = {"version": 2, "events": [_line()]}
    restatement_llm = VerdictLLM({"items": [{
        "idx": 0,
        "decision": "restatement",
        "registry_index": 0,
        "reason": "The current core fact is already covered.",
    }]})
    event = _event()
    gate = _gate(restatement_llm, registry, tmp_path)

    result = gate.review([event], [_item(event["title"])])

    assert result["restatements"] == [event]
    assert result["material_hints"] == {}
    assert gate.stats["cross_source_restatements"] == 1

    material_llm = VerdictLLM({"items": [{
        "idx": 0,
        "decision": "material_addition",
        "registry_index": 0,
        "reason": "The official correction changes the known result.",
    }]})
    gate = _gate(material_llm, registry, tmp_path)
    result = gate.review([event], [_item(event["title"])])

    assert result["restatements"] == []
    assert result["material_hints"] == {
        dn.cross_source_event_key(event): "evt-20260801-f55954"
    }
    assert gate.stats["cross_source_material_additions"] == 1


def test_only_prior_picks_within_retention_and_same_category_can_block(tmp_path):
    event = _event()
    item = _item(event["title"])
    expired = _line(last_seen="2026-05-01")
    expired["history"][0].update({
        "date": "2026-05-01", "item_ref": "2026-05-01:pick-46"})
    for line in (
        _line(item_ref="2026-08-01:more-46"),
        expired,
        _line(category="tech"),
    ):
        llm = VerdictLLM({"items": []})
        gate = _gate(llm, {"version": 2, "events": [line]}, tmp_path)

        assert gate.review([event], [item])["restatements"] == []
        assert llm.calls == []

    boundary = _line(last_seen="2026-06-04")
    boundary["history"][0].update({
        "date": "2026-06-04", "item_ref": "2026-06-04:pick-46"})
    llm = VerdictLLM({"items": [{
        "idx": 0,
        "decision": "restatement",
        "registry_index": 0,
        "reason": "The prior pick explicitly covers the same release.",
    }]})
    gate = _gate(llm, {"version": 2, "events": [boundary]}, tmp_path)
    assert gate.review([event], [item])["restatements"] == [event]


def test_same_day_registry_rows_never_block_an_idempotent_rerun(tmp_path):
    today = _line(
        item_ref="2026-08-03:pick-46", last_seen="2026-08-03", status="active")
    today["history"][0]["date"] = "2026-08-03"
    llm = VerdictLLM({"items": []})
    gate = _gate(llm, {"version": 2, "events": [today]}, tmp_path)

    result = gate.review([_event()], [_item("DeepSeek V4 Flash released")])

    assert result["restatements"] == []
    assert llm.calls == []


def test_rerun_uses_only_registry_evidence_before_the_output_date(tmp_path):
    line = _line(last_seen="2026-08-03", status="active")
    line["history"].append({
        **line["history"][0],
        "date": "2026-08-03",
        "item_ref": "2026-08-03:pick-193",
        "summary": "The current run must not become its own history.",
    })
    llm = VerdictLLM({"items": [{
        "idx": 0,
        "decision": "different_event",
        "registry_index": None,
        "reason": "Evidence projection test.",
    }]})
    gate = _gate(llm, {"version": 2, "events": [line]}, tmp_path)

    gate.review([_event()], [_item("DeepSeek V4 Flash released")])

    history = llm.calls[0]["items"][0]["registry"][0]["history"]
    assert {row["date"] for row in history} == {"2026-08-01"}


def test_prior_item_ref_enriches_registry_evidence_without_network(tmp_path):
    daily = tmp_path / "daily"
    daily.mkdir()
    payload = {
        "items": [{
            "id": "pick-46",
            "title": "DeepSeek V4 Flash released",
            "summary": "The release was already selected.",
            "detail": "Architecture, parameters and benchmark results were published.",
            "status": "confirmed",
        }]
    }
    (daily / "2026-08-01.js").write_text(
        'window.NEWS_DATA["2026-08-01"] = '
        + json.dumps(payload) + ";\n", encoding="utf-8")
    llm = VerdictLLM({"items": [{
        "idx": 0,
        "decision": "different_event",
        "registry_index": None,
        "reason": "Kept for this evidence projection test.",
    }]})
    gate = _gate(llm, {"version": 2, "events": [_line()]}, tmp_path)

    gate.review([_event()], [_item("DeepSeek V4 Flash released")])

    history = llm.calls[0]["items"][0]["registry"][0]["history"][0]
    assert history["detail"] == payload["items"][0]["detail"]


def test_invalid_or_uncertain_model_output_fails_open_and_records_degradation(tmp_path):
    registry = {"version": 2, "events": [_line()]}
    event = _event()
    stats = dn.new_cross_source_novelty_stats()
    llm = VerdictLLM({"items": [{
        "idx": 0,
        "decision": "uncertain",
        "registry_index": 0,
        "reason": "Historical evidence is incomplete.",
    }]})
    gate = _gate(llm, registry, tmp_path, stats=stats)

    result = gate.review([event], [_item(event["title"])])

    assert result["restatements"] == []
    assert stats["cross_source_novelty_failures"] == 1
    assert stats["degraded"] is True


def test_malformed_batch_retries_once_then_fails_open(tmp_path):
    registry = {"version": 2, "events": [_line()]}
    stats = dn.new_cross_source_novelty_stats()
    llm = VerdictLLM({"items": [{
        "idx": 0,
        "decision": True,
        "registry_index": 0,
        "reason": "invalid enum",
    }]})
    gate = _gate(llm, registry, tmp_path, stats=stats, max_calls=8)

    result = gate.review([_event()], [_item("DeepSeek V4 Flash released")])

    assert result["restatements"] == []
    assert len(llm.calls) == 2
    assert stats["cross_source_novelty_calls"] == 2
    assert stats["cross_source_novelty_failures"] == 1


def test_call_exception_fails_open_without_structural_retry(tmp_path):
    registry = {"version": 2, "events": [_line()]}
    stats = dn.new_cross_source_novelty_stats()
    llm = SequenceLLM([
        RuntimeError("provider unavailable"),
        {"items": [{
            "idx": 0,
            "decision": "restatement",
            "registry_index": 0,
            "reason": "must not be consumed",
        }]},
    ])
    gate = _gate(llm, registry, tmp_path, stats=stats)

    result = gate.review([_event()], [_item("DeepSeek V4 Flash released")])

    assert result["restatements"] == []
    assert len(llm.calls) == 1
    assert stats["cross_source_novelty_failures"] == 1


def test_missing_duplicate_and_out_of_range_rows_retry_then_fail_open(tmp_path):
    malformed_results = [
        {"items": []},
        {"items": [
            {"idx": 0, "decision": "different_event",
             "registry_index": None, "reason": "first"},
            {"idx": 0, "decision": "different_event",
             "registry_index": None, "reason": "duplicate"},
        ]},
        {"items": [{
            "idx": 1, "decision": "different_event",
            "registry_index": None, "reason": "out of range",
        }]},
    ]
    for malformed in malformed_results:
        stats = dn.new_cross_source_novelty_stats()
        llm = VerdictLLM(malformed)
        gate = _gate(
            llm, {"version": 2, "events": [_line()]}, tmp_path, stats=stats)

        result = gate.review([_event()], [_item("DeepSeek V4 Flash released")])

        assert result["restatements"] == []
        assert len(llm.calls) == 2
        assert stats["cross_source_novelty_failures"] == 1


def test_same_url_invalid_structure_keeps_every_candidate():
    items = [
        _item("First changed story", source_id="one"),
        _item("Second changed story", source_id="two"),
    ]
    seen = {
        dn.canonical_news_url(item["url"]): {
            "last_seen": "2026-08-01",
            "first_seen": "2026-08-01",
            "title": "Prior title",
            "desc": "Prior summary",
            "fingerprint": "different",
        }
        for item in items
    }
    malformed = {"updates": [
        {"index": 0, "material": False},
        {"index": 0, "material": False},
    ]}
    quality = dn.new_quality_stats()

    kept = dn.filter_cross_day_news(
        VerdictLLM(malformed), items, seen, "2026-08-03", quality)

    assert kept == items
    assert quality["cross_day_duplicates"] == 0
    assert quality["update_judge_failures"] == 2
    assert quality["degraded"] is True


def test_budget_exhaustion_keeps_unreviewed_candidates(tmp_path):
    registry = {"version": 2, "events": [_line()]}
    stats = dn.new_cross_source_novelty_stats()
    llm = VerdictLLM({"items": []})
    gate = _gate(llm, registry, tmp_path, stats=stats, max_calls=0)

    result = gate.review([_event()], [_item("DeepSeek V4 Flash released")])

    assert result["restatements"] == []
    assert llm.calls == []
    assert stats["cross_source_novelty_deferred"] == 1
    assert stats["cross_source_novelty_budget_exhausted"] is True
    assert stats["degraded"] is True


def test_budget_exhaustion_during_structural_retry_is_recorded(tmp_path):
    stats = dn.new_cross_source_novelty_stats()
    llm = VerdictLLM({"items": []})
    gate = _gate(
        llm, {"version": 2, "events": [_line()]}, tmp_path,
        stats=stats, max_calls=1)

    result = gate.review([_event()], [_item("DeepSeek V4 Flash released")])

    assert result["restatements"] == []
    assert len(llm.calls) == 1
    assert stats["cross_source_novelty_failures"] == 1
    assert stats["cross_source_novelty_budget_exhausted"] is True


def test_large_evidence_is_split_by_prompt_budget(tmp_path, monkeypatch):
    llm = EchoDifferentLLM()
    gate = _gate(llm, {"version": 2, "events": []}, tmp_path, batch_size=20)
    large_registry = [{
        "event_id": f"evt-{line_index}",
        "title": "Historical event",
        "category": "ai",
        "history": [{
            "date": "2026-08-01",
            "title": "Historical title",
            "summary": "s" * 320,
            "detail": "d" * 600,
            "status": "confirmed",
            "item_ref": "2026-08-01:pick-1",
        } for _ in range(7)],
    } for line_index in range(6)]
    monkeypatch.setattr(
        gate, "_shortlist", lambda event, items: (
            dn._cross_source_current_projection(event, items), large_registry))
    events = [{**_event(f"Event {index}"), "ids": [index]}
              for index in range(3)]
    items = [_item(f"Event {index}", source_id=str(index)) for index in range(3)]

    gate.review(events, items)

    assert len(llm.users) > 1
    assert all(len(user) <= dn.CROSS_SOURCE_NOVELTY_MAX_PROMPT_CHARS
               for user in llm.users)


def test_novelty_metrics_are_health_only_and_do_not_enter_daily_quality(tmp_path):
    quality = dn.new_quality_stats()
    stats = dn.new_cross_source_novelty_stats()
    stats["cross_source_restatements"] = 2

    health = dn.update_quality_health(
        tmp_path, "2026-08-03", quality, novelty_stats=stats)
    public_quality = dn._quality_for_output(quality, include_rollout=True)

    assert health["records"][0]["cross_source_restatements"] == 2
    assert "cross_source_restatements" not in public_quality


def test_selection_replaces_restatement_but_keeps_full_scored_snapshot(tmp_path):
    items = [
        _item("DeepSeek V4 Flash released", source_id="cls-depth"),
        _item("Independent product launch", source_id="other"),
    ]
    events = [
        _event("DeepSeek V4 Flash released"),
        {**_event("Independent product launch"), "ids": [1]},
    ]
    events[0]["dims"] = {dimension: 9.0 for dimension in dn.DIMS}
    events[1]["dims"] = {dimension: 8.0 for dimension in dn.DIMS}
    cfg = {
        "interest_weights": {"ai": 1.0},
        "scoring": {
            "dim_weights": {dimension: 0.2 for dimension in dn.DIMS},
            "tier_multipliers": {"T1": 1.0},
        },
        "pick_threshold": 60,
        "pick_min": 1,
        "pick_max": 1,
        "min_per_category": 0,
        "max_per_category": {},
        "secondary_count": 0,
        "pick_dynamic": {"enabled": False, "backfill_offset": 8},
        "cost_guard": {
            "cross_source_novelty_batch_size": 20,
            "cross_source_novelty_max_calls": 8,
        },
    }
    llm = VerdictLLM({"items": [{
        "idx": 0,
        "decision": "restatement",
        "registry_index": 0,
        "reason": "Already covered by the August 1 pick.",
    }]})
    stats = dn.new_cross_source_novelty_stats()

    all_scored, picked, secondary, *_ = dn.select_review_and_record(
        None, None, events, items, cfg, tmp_path, "2026-08-03",
        dn.new_quality_stats(), novelty_llm=llm,
        registry={"version": 2, "events": [_line()]},
        novelty_stats=stats)

    ledger = json.loads((tmp_path / "score_history.json").read_text("utf-8"))
    assert len(all_scored) == 2
    assert all("score" in event for event in all_scored)
    assert [event["title"] for event in picked] == ["Independent product launch"]
    assert secondary == []
    assert len(ledger["days"]["2026-08-03"]["eligible_scores"]) == 1


def test_material_hint_only_proposes_pair_and_continuity_gate_still_decides(monkeypatch):
    registry = {"version": 2, "events": [{**_line(status="active")}]}
    picked = [_event()]
    items = [_item("DeepSeek V4 Flash released")]
    captured = {}

    monkeypatch.setattr(dn, "match_events_llm", lambda *_args, **_kwargs: [])

    def reject(_llm, pairs, _active, _picked, _date, health=None):
        captured["pairs"] = list(pairs)
        return [], {}

    monkeypatch.setattr(dn, "validate_continuity_llm", reject)
    cfg = {
        "events": {"match_window_days": 14, "archive_days": 7,
                   "prune_archived_days": 60},
        "trajectory": {"enabled": False},
    }

    updated = dn.prepare_registry_transaction(
        None, registry, picked, "2026-08-03", cfg, items=items,
        preferred_event_ids={
            dn.cross_source_event_key(picked[0]): "evt-20260801-f55954"
        })

    assert captured["pairs"] == [(0, 0)]
    assert picked[0]["event_id"] != "evt-20260801-f55954"
    assert len(updated["events"]) == 2


def test_material_hint_can_recall_archived_line_but_still_requires_continuity(monkeypatch):
    archived = _line(last_seen="2026-07-01", status="archived")
    archived["history"][0].update({
        "date": "2026-07-01",
        "item_ref": "2026-07-01:pick-46",
    })
    registry = {"version": 2, "events": [archived]}
    picked = [_event()]
    items = [_item("DeepSeek V4 Flash released")]
    captured = {}

    monkeypatch.setattr(dn, "match_events_llm", lambda *_args, **_kwargs: [])

    def accept(_llm, pairs, active, _picked, _date, health=None):
        captured["pairs"] = list(pairs)
        captured["event_ids"] = [event["event_id"] for event in active]
        return list(pairs), {0: [active[pairs[0][1]]["history"][0]]}

    monkeypatch.setattr(dn, "validate_continuity_llm", accept)
    cfg = {
        "events": {"match_window_days": 14, "archive_days": 7,
                   "prune_archived_days": 60},
        "trajectory": {"enabled": False},
    }

    updated = dn.prepare_registry_transaction(
        None, registry, picked, "2026-08-03", cfg, items=items,
        preferred_event_ids={
            dn.cross_source_event_key(picked[0]): "evt-20260801-f55954"
        })

    assert captured["pairs"] == [(0, 0)]
    assert captured["event_ids"] == ["evt-20260801-f55954"]
    assert picked[0]["event_id"] == "evt-20260801-f55954"
    line = next(event for event in updated["events"]
                if event["event_id"] == "evt-20260801-f55954")
    assert line["status"] == "active"
    assert line["last_seen"] == "2026-08-03"
