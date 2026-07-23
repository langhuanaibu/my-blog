import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import daily_news as dn


def _item():
    return {
        "title": "Model launch",
        "desc": "The company launched a model.",
        "url": "https://example.test/model",
        "source": "Example",
        "source_id": "example",
        "source_type": "fact",
        "tier": "T1",
        "credibility": 9,
        "time": "2026-07-23T00:00:00Z",
    }


def _event():
    return {
        "ids": [0],
        "category": "ai",
        "title": "Model launch",
        "summary": "The company launched a model.",
        "status": "已确认",
        "score": 90,
        "tier": "T1",
        "tags": [],
    }


def test_publication_transaction_restores_daily_manifest_and_registry(
        tmp_path, monkeypatch):
    daily_dir = tmp_path / "daily"
    daily_dir.mkdir()
    daily_path = daily_dir / "2026-07-23.js"
    manifest_path = tmp_path / "manifest.js"
    registry_path = tmp_path / "events.json"
    prior = {
        daily_path: "prior daily\n",
        manifest_path: "prior manifest\n",
        registry_path: "prior registry\n",
    }
    for path, content in prior.items():
        path.write_text(content, encoding="utf-8")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    real_replace = dn.os.replace
    calls = 0

    def fail_second_replace(source, target):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated transaction failure")
        return real_replace(source, target)

    monkeypatch.setattr(dn.os, "replace", fail_second_replace)

    with pytest.raises(OSError, match="simulated transaction failure"):
        dn.write_output_and_commit_registry(
            "2026-07-23", "brief", [_event()], [], [_item()],
            {"events": {}}, {"version": 2, "events": []},
            quality=dn.new_quality_stats())

    assert {
        path: path.read_text(encoding="utf-8") for path in prior
    } == prior
    assert not list(tmp_path.rglob("*.tmp"))


def test_empty_selection_does_not_touch_publication_files(tmp_path, monkeypatch):
    daily_dir = tmp_path / "daily"
    daily_dir.mkdir()
    daily_path = daily_dir / "2026-07-23.js"
    manifest_path = tmp_path / "manifest.js"
    registry_path = tmp_path / "events.json"
    for path in (daily_path, manifest_path, registry_path):
        path.write_text("prior\n", encoding="utf-8")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    payload, errors = dn.write_output_and_commit_registry(
        "2026-07-23", "brief", [], [], [_item()],
        {"events": {}}, {"version": 2, "events": []},
        quality=dn.new_quality_stats())

    assert payload is None
    assert errors == ["picked items empty"]
    assert all(
        path.read_text(encoding="utf-8") == "prior\n"
        for path in (daily_path, manifest_path, registry_path)
    )
