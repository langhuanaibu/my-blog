import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import daily_news as dn


def _item(index, *, title=None, url=None, source_id=None):
    return {
        "title": title or f"Unrelated report {index}",
        "desc": f"Evidence summary for {title or f'unrelated event {index}'}.",
        "url": url or f"https://example.test/{index}",
        "source": f"Source {index}",
        "source_id": source_id or f"source-{index}",
        "source_type": "fact",
        "tier": "T1",
        "credibility": 9,
        "time": "2026-07-23T00:00:00Z",
    }


def _event(index, *, title=None, score=80):
    return {
        "ids": [index],
        "category": "ai",
        "title": title or f"Unrelated event {index}",
        "dims": {
            "impact": score / 10,
            "novelty": score / 10,
            "substance": score / 10,
            "evidence": score / 10,
            "durability": score / 10,
        },
    }


class BoundedPartitionLLM:
    def __init__(self, max_batch=40):
        self.max_batch = max_batch
        self.calls = []

    def json_call(self, _system, user):
        payload = json.loads(user)
        self.calls.append(payload)
        if len(payload) > self.max_batch:
            raise ValueError("batch too large")
        duplicates = [
            index for index, row in enumerate(payload)
            if "hugging face breach" in json.dumps(row, ensure_ascii=False).lower()
        ]
        duplicate_set = set(duplicates)
        groups = [
            [index] for index in range(len(payload))
            if index not in duplicate_set
        ]
        if duplicates:
            groups.append(duplicates)
        groups.sort(key=lambda group: group[0])
        return {"groups": groups}


def test_evidence_reconciliation_is_bounded_and_bridges_base_batches():
    items = [_item(index) for index in range(45)]
    items[0].update({
        "title": "OpenAI model caused Hugging Face breach",
        "desc": "A sandbox evaluation reached Hugging Face.",
    })
    items[44].update({
        "title": "Analysis of the Hugging Face breach",
        "desc": "The same OpenAI sandbox incident is analysed.",
    })
    events = [_event(index) for index in range(45)]
    events[0]["title"] = "OpenAI sandbox incident"
    events[44]["title"] = "Hugging Face breach analysis"
    llm = BoundedPartitionLLM()

    reconciled = dn.reconcile_same_day_events(
        llm, events, items, dn.new_quality_stats())

    assert len(reconciled) == 44
    assert all(len(call) <= 40 for call in llm.calls)
    assert set(reconciled[0]["ids"]) == {0, 44}


def test_reconciliation_payload_keeps_more_than_three_relevant_reports():
    items = [_item(index, source_id=f"publisher-{index}") for index in range(5)]
    event = _event(0)
    event["ids"] = list(range(5))

    payload = dn._same_day_reconcile_payload([event], items)

    assert len(payload[0]["reports"]) == 5


def test_equal_document_url_alone_does_not_make_two_events_identical():
    url = "https://example.test/roundup"
    items = [
        _item(0, title="OpenAI starts a data-centre project", url=url),
        _item(1, title="OpenAI launches Presence agents", url=url),
    ]
    events = [
        _event(0, title="OpenAI data-centre project"),
        _event(1, title="OpenAI Presence launch"),
    ]

    assert dn._deterministic_same_day_groups(events, items) == [[0], [1]]


def test_reader_facing_review_repeats_after_each_replacement(monkeypatch, tmp_path):
    events = [
        {"title": "Event A", "ids": [0]},
        {"title": "Event A analysis", "ids": [1]},
        {"title": "Event A late duplicate", "ids": [2]},
        {"title": "Independent event B", "ids": [3]},
    ]
    review_calls = []

    def select(current, _items, _cfg, **_kwargs):
        return current[:1], current[1:2]

    def review(_llm, current, picked, secondary, _items, _quality):
        visible = [*picked, *secondary]
        review_calls.append([event["title"] for event in visible])
        if len(visible) == 2 and visible[1]["title"].startswith("Event A"):
            removed = visible[1]
            return [event for event in current if event is not removed], 1
        return current, 0

    monkeypatch.setattr(dn, "score_and_select", select)
    monkeypatch.setattr(dn, "review_reader_facing_duplicates", review)
    monkeypatch.setattr(
        dn, "_reaudit_reconciled_same_day_events",
        lambda _llm, current, _items, _quality: current)
    monkeypatch.setattr(
        dn, "select_and_record",
        lambda current, _items, _cfg, _data_dir, _date:
        (current[:1], current[1:2], {"threshold": 68}, {}))

    remaining, picked, secondary, *_ = dn.select_review_and_record(
        None, None, events, [], {"pick_threshold": 68}, tmp_path,
        "2026-07-23", dn.new_quality_stats())

    assert [event["title"] for event in [*picked, *secondary]] == [
        "Event A", "Independent event B"]
    assert [event["title"] for event in remaining] == [
        "Event A", "Independent event B"]
    assert review_calls == [
        ["Event A", "Event A analysis"],
        ["Event A", "Event A late duplicate"],
        ["Event A", "Independent event B"],
    ]
