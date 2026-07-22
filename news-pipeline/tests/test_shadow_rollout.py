import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml


PIPELINE_DIR = Path(__file__).resolve().parents[1]
ROOT = PIPELINE_DIR.parent
spec = importlib.util.spec_from_file_location("daily_news_shadow_test", PIPELINE_DIR / "daily_news.py")
dn = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = dn
spec.loader.exec_module(dn)


def _load_eval_module():
    path = PIPELINE_DIR / "objectivity_eval.py"
    assert path.exists(), "objectivity evaluation harness is missing"
    module_spec = importlib.util.spec_from_file_location("objectivity_eval_test", path)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    return module


def test_objectivity_acceptance_workflow_is_manual_read_only_and_publishes_report():
    workflow_path = ROOT / ".github" / "workflows" / "objectivity-acceptance.yml"
    assert workflow_path.exists(), "manual objectivity acceptance workflow is missing"

    workflow_text = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.load(workflow_text, Loader=yaml.BaseLoader)

    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read"}
    assert set(workflow["jobs"]) == {"evaluate"}

    evaluate = workflow["jobs"]["evaluate"]
    assert evaluate["permissions"] == {"contents": "read"}
    assert evaluate["env"]["LLM_API_KEY"] == "${{ secrets.LLM_API_KEY }}"

    steps = evaluate["steps"]
    run_scripts = "\n".join(step.get("run", "") for step in steps)
    assert "python news-pipeline/objectivity_eval.py" in run_scripts
    assert "tee" in run_scripts
    assert "git commit" not in run_scripts
    assert "git push" not in run_scripts

    upload = next(
        step for step in steps
        if step.get("uses", "").startswith("actions/upload-artifact@")
    )
    assert upload["if"] == "${{ always() }}"
    assert upload["with"]["path"] == "${{ runner.temp }}/objectivity-acceptance.json"


def test_mode_defaults_to_interim_and_shadow_overrides_active():
    default_args = dn.parse_cli_args([])
    default = dn.resolve_run_policy({}, default_args)
    active = dn.resolve_run_policy(
        {"objectivity": {"mode": "active"}}, dn.parse_cli_args([]))
    shadow = dn.resolve_run_policy(
        {"objectivity": {"mode": "active"}},
        dn.parse_cli_args(["--objectivity-shadow"]),
    )

    assert default == {
        "mode": "interim",
        "full_objectivity": False,
        "writes_public_data": True,
    }
    assert active == {
        "mode": "active",
        "full_objectivity": True,
        "writes_public_data": True,
    }
    assert shadow == {
        "mode": "shadow",
        "full_objectivity": True,
        "writes_public_data": False,
    }


def test_invalid_configured_mode_is_rejected():
    with pytest.raises(ValueError, match="objectivity.mode"):
        dn.resolve_run_policy(
            {"objectivity": {"mode": "surprise"}}, dn.parse_cli_args([]))


def test_shadow_snapshots_existing_data_dir_while_public_uses_configured_path(tmp_path):
    public_dir = tmp_path / "public-data"
    (public_dir / "weekly").mkdir(parents=True)
    marker = public_dir / "daily.js"
    marker.write_text("public", encoding="utf-8")
    (public_dir / "feedback.json").write_text('{"keep":true}', encoding="utf-8")
    (public_dir / "profile.json").write_text('{"reader":"existing"}', encoding="utf-8")
    (public_dir / "events.json").write_text('{"events":[]}', encoding="utf-8")
    (public_dir / "weekly" / "2026-W28.js").write_text("weekly", encoding="utf-8")
    environ = {"DATA_DIR": str(public_dir)}

    shadow_dir, shadow_owner = dn.prepare_run_data_dir(
        {"writes_public_data": False}, environ)
    public_result, public_owner = dn.prepare_run_data_dir(
        {"writes_public_data": True}, environ)
    try:
        assert shadow_owner is not None
        assert shadow_dir != public_dir
        assert (shadow_dir / "daily.js").read_text(encoding="utf-8") == "public"
        assert (shadow_dir / "feedback.json").exists()
        assert (shadow_dir / "profile.json").exists()
        assert (shadow_dir / "events.json").exists()
        assert (shadow_dir / "weekly" / "2026-W28.js").exists()
        (shadow_dir / "daily.js").write_text("shadow", encoding="utf-8")
        assert public_result == public_dir
        assert public_owner is None
    finally:
        shadow_owner.cleanup()

    assert marker.read_text(encoding="utf-8") == "public"


@pytest.mark.parametrize("exit_kind", ["return", "exception", "validation_failure"])
def test_shadow_data_dir_lifecycle_never_mutates_source_on_any_exit(
        tmp_path, exit_kind):
    public_dir = tmp_path / "public-data"
    public_dir.mkdir()
    marker = public_dir / "marker.txt"
    marker.write_text("public", encoding="utf-8")
    environ = {"DATA_DIR": str(public_dir)}
    captured = []

    def run():
        with dn.managed_run_data_dir(
                {"writes_public_data": False}, environ) as shadow_dir:
            captured.append(shadow_dir)
            assert environ["DATA_DIR"] == str(shadow_dir)
            assert (shadow_dir / "marker.txt").read_text(encoding="utf-8") == "public"
            (shadow_dir / "marker.txt").write_text("shadow", encoding="utf-8")
            (shadow_dir / "generated.tmp").write_text("temporary", encoding="utf-8")
            if exit_kind == "return":
                return
            if exit_kind == "validation_failure":
                raise ValueError("daily payload validation failed")
            raise RuntimeError("pipeline failed")

    if exit_kind == "return":
        run()
    else:
        expected = ValueError if exit_kind == "validation_failure" else RuntimeError
        with pytest.raises(expected):
            run()

    assert environ["DATA_DIR"] == str(public_dir)
    assert marker.read_text(encoding="utf-8") == "public"
    assert captured and not captured[0].exists()


def test_shadow_data_dir_lifecycle_supports_empty_snapshot(tmp_path):
    public_dir = tmp_path / "empty-public-data"
    public_dir.mkdir()
    environ = {"DATA_DIR": str(public_dir)}

    with dn.managed_run_data_dir(
            {"writes_public_data": False}, environ) as shadow_dir:
        assert list(shadow_dir.iterdir()) == []
        (shadow_dir / "generated.js").write_text("shadow", encoding="utf-8")

    assert list(public_dir.iterdir()) == []


def test_objectivity_stage_dispatches_interim_support_only_and_full_audit():
    items = [
        {"title": "Source one", "desc": "Fact one", "source": "Wire A",
         "source_type": "fact", "credibility": 9, "url": "https://a.example"},
        {"title": "Source two", "desc": "Fact two", "source": "Wire B",
         "source_type": "fact", "credibility": 9, "url": "https://b.example"},
    ]

    class InterimStub:
        def __init__(self):
            self.systems = []

        def json_call(self, system, _user):
            self.systems.append(system)
            return {"fields": {"why": True}, "supported_claim_indexes": [0]}

    interim_event = {
        "ids": [0], "title": "Edited", "summary": "Summary", "why": "Why",
        "claims": [{"text": "Fact", "kind": "fact", "sources": ["Wire A"]}],
    }
    interim_secondary = {"ids": [1], "title": "Secondary", "summary": "Other"}
    interim_quality = dn.new_quality_stats()
    interim_stub = InterimStub()
    dn.run_objectivity_stage(
        {"full_objectivity": False}, interim_stub, [interim_event],
        [interim_secondary], items, interim_quality)

    assert interim_stub.systems == [dn.SUPPORT_AUDIT_SYSTEM]
    assert interim_quality["objectivity_audited"] == 0
    assert interim_secondary == {"ids": [1], "title": "Secondary", "summary": "Other"}

    class FullStub:
        def __init__(self):
            self.systems = []

        def json_call(self, system, _user):
            self.systems.append(system)
            return {"fields": {"title": True, "summary": True}, "claims": []}

    picked = [{"ids": [0], "title": "Edited", "summary": "Summary"}]
    secondary = [{"ids": [1], "title": "Secondary", "summary": "Other"}]
    full_quality = dn.new_quality_stats()
    full_stub = FullStub()
    dn.run_objectivity_stage(
        {"full_objectivity": True}, full_stub, picked, secondary, items, full_quality)

    assert full_stub.systems == [dn.OBJECTIVITY_AUDIT_SYSTEM, dn.OBJECTIVITY_AUDIT_SYSTEM]
    assert full_quality["objectivity_audited"] == 2


def test_public_serialization_strips_rollout_fields_in_interim_and_keeps_active(
        tmp_path, monkeypatch):
    item = {
        "title": "Source title", "desc": "Source description",
        "source": "Wire A", "source_id": "wire-a", "source_type": "fact",
        "tier": "T1", "credibility": 9, "url": "https://a.example/item",
        "time": "2026-07-18T00:00:00+00:00", "evidence_basis": "fulltext",
        "source_family": "wire-a", "provenance": "original",
    }
    event = {
        "ids": [0], "category": "ai", "title": "Edited", "summary": "Summary",
        "status": "已确认", "score": 90, "tier": "T1", "tags": [],
        "evidence": {
            "basis": "fulltext", "publisher_count": 1,
            "independent_chain_count": 1, "degraded": False,
        },
    }
    quality = dn.new_quality_stats()
    quality["objectivity_audited"] = 1
    quality["article_fetch_attempts"] = 1

    interim_dir = tmp_path / "interim"
    monkeypatch.setenv("DATA_DIR", str(interim_dir))
    interim = dn.write_output(
        "2026-07-18", "brief", [event], [], [item],
        {"objectivity": {"mode": "interim"}}, quality=quality)

    assert "evidence" not in interim["items"][0]
    assert "evidence_basis" not in interim["items"][0]["sources"][0]
    assert "objectivity_audited" not in interim["quality"]
    assert "article_fetch_attempts" not in interim["quality"]

    active_dir = tmp_path / "active"
    monkeypatch.setenv("DATA_DIR", str(active_dir))
    active = dn.write_output(
        "2026-07-18", "brief", [event], [], [item],
        {"objectivity": {"mode": "active"}}, quality=quality)

    assert active["items"][0]["evidence"]["basis"] == "fulltext"
    assert active["items"][0]["sources"][0]["evidence_basis"] == "fulltext"
    assert active["quality"]["objectivity_audited"] == 1
    assert active["quality"]["article_fetch_attempts"] == 1


def test_config_declares_interim_default():
    config = yaml.safe_load((PIPELINE_DIR / "config.yaml").read_text(encoding="utf-8"))
    assert config["objectivity"]["mode"] == "interim"


def test_shadow_summary_has_stable_shape_and_excludes_content_and_secrets():
    selected_before = [
        {
            "ids": [0],
            "risk_flags": {"allegation_legal": True},
            "evidence": {
                "basis": "fulltext",
                "publisher_count": 1,
                "independent_chain_count": 1,
                "degraded": False,
            },
            "detail": "ARTICLE_SENTINEL",
        },
        {
            "ids": [1, 2],
            "risk_flags": {},
            "evidence": {
                "basis": "mixed",
                "publisher_count": 2,
                "independent_chain_count": 0,
                "degraded": True,
            },
        },
    ]
    selected_after = [selected_before[1]]
    items = [
        {"source": "Wire A", "evidence_text": "ARTICLE_SENTINEL"},
        {"source": "Outlet B"},
        {"source": "Outlet C", "api_key": "SECRET_SENTINEL"},
    ]
    quality = {
        "article_fetch_attempts": 3,
        "article_fetch_successes": 2,
        "article_fetch_retries": 1,
        "objectivity_audited": 2,
        "objectivity_repaired": 1,
        "objectivity_degraded": 1,
        "high_risk_demoted": 1,
    }

    summary = dn.build_shadow_summary(
        selected_before, selected_after, items, quality, runtime_seconds=12.3456)

    assert set(summary) == {
        "mode", "runtime_seconds", "selected_before_audit",
        "selected_after_audit", "audited_candidate_count",
        "demoted_from_selected", "high_risk_selected_before_audit",
        "single_source_selected_before_audit", "high_risk_single_source_count",
        "high_risk_single_source_rate", "evidence_basis", "fetch",
        "objectivity", "independent_chain_distribution",
        "source_reference_concentration",
    }
    assert summary["runtime_seconds"] == 12.346
    assert summary["selected_before_audit"] == 2
    assert summary["selected_after_audit"] == 1
    assert summary["audited_candidate_count"] == 2
    assert summary["demoted_from_selected"] == 1
    assert summary["high_risk_single_source_count"] == 1
    assert summary["high_risk_single_source_rate"] == 1.0
    assert summary["evidence_basis"] == {"fulltext": 1, "mixed": 1, "snippet": 0}
    assert summary["fetch"] == {"attempts": 3, "successes": 2, "retries": 1}
    assert summary["objectivity"] == {
        "repaired": 1, "degraded": 1,
    }
    assert summary["independent_chain_distribution"] == {"0": 1, "1": 1}
    encoded = json.dumps(summary, ensure_ascii=False)
    assert "ARTICLE_SENTINEL" not in encoded
    assert "SECRET_SENTINEL" not in encoded


def test_github_summary_appends_compact_markdown(tmp_path):
    target = tmp_path / "step-summary.md"
    summary = {
        "mode": "shadow",
        "runtime_seconds": 2.5,
        "selected_before_audit": 5,
        "selected_after_audit": 4,
        "audited_candidate_count": 7,
        "demoted_from_selected": 1,
        "high_risk_selected_before_audit": 1,
        "single_source_selected_before_audit": 1,
        "high_risk_single_source_count": 1,
        "high_risk_single_source_rate": 1.0,
        "evidence_basis": {"fulltext": 2, "mixed": 1, "snippet": 1},
        "fetch": {"attempts": 5, "successes": 4, "retries": 1},
        "objectivity": {"repaired": 1, "degraded": 0},
        "independent_chain_distribution": {"0": 1, "1": 3},
        "source_reference_concentration": [
            {"source": "Wire A", "reference_count": 2, "reference_share": 0.5}
        ],
    }

    assert dn.append_github_shadow_summary(summary, {"GITHUB_STEP_SUMMARY": str(target)})
    text = target.read_text(encoding="utf-8")
    assert "Objectivity shadow" in text
    assert "2.500s" in text
    assert "selected before/after audit: 5/4" in text
    assert "audited candidates/demoted from selected: 7/1" in text
    assert "source reference concentration" in text
    assert "fulltext/mixed/snippet: 2/1/1" in text
    assert "high-risk single-source: 1 (100.0%)" in text
    assert "ARTICLE_SENTINEL" not in text


def test_selection_summary_appends_threshold_and_composition_without_content(tmp_path):
    target = tmp_path / "step-summary.md"
    summary = {
        "threshold": 74,
        "threshold_source": "dynamic_history",
        "history_days": 7,
        "quality_floor": 66,
        "picked_count": 24,
        "category_counts": {"ai": 8, "tech": 4, "finance": 4, "society": 4, "world": 4},
        "qualified_supply": {"ai": 20, "tech": 6, "finance": 5, "society": 4, "world": 7},
        "reserved_count": 15,
        "below_threshold_reserved": 3,
        "over_threshold_secondary": 2,
        "detail": "ARTICLE_SENTINEL",
    }

    assert dn.append_github_selection_summary(
        summary, {"GITHUB_STEP_SUMMARY": str(target)})
    text = target.read_text(encoding="utf-8")
    assert "News selection" in text
    assert "threshold: 74 (dynamic_history; 7 history days)" in text
    assert "quality floor: 66" in text
    assert "reserved/below-threshold reserved: 15/3" in text
    assert "over-threshold secondary: 2" in text
    assert "ARTICLE_SENTINEL" not in text


def test_article_fetch_reports_transient_retry_count():
    calls = []

    class Response:
        status_code = 200
        headers = {"Content-Type": "text/html"}

        def iter_content(self, chunk_size):
            yield b"<html>ok</html>"

        def close(self):
            return None

    def request_get(*_args, **_kwargs):
        calls.append(True)
        if len(calls) == 1:
            raise TimeoutError("transient")
        return Response()

    result = dn.fetch_article_evidence(
        {"url": "https://news.example/item", "title": "t", "desc": "d"},
        request_get=request_get,
        extractor=lambda _html: "safe evidence " * 30,
        resolver=lambda *_args, **_kwargs: [(None, None, None, None, ("93.184.216.34", 443))],
        sleep=lambda _seconds: None,
    )

    assert result["evidence_basis"] == "fulltext"
    assert result["attempts"] == 2
    assert result["retries"] == 1


def test_fixture_corpus_has_required_count_categories_and_schema():
    evaluator = _load_eval_module()
    fixtures = evaluator.load_checked_in_corpus()
    errors = evaluator.validate_fixture_schema(fixtures)

    assert errors == []
    assert len(fixtures) == 45
    assert {fixture["category"] for fixture in fixtures} == {
        "waic_framing",
        "legal_procedure",
        "armed_conflict",
        "company_claim",
        "magnitude_without_baseline",
        "motive_causal_inference",
        "sensitive_single_source",
        "shared_evidence",
        "forbidden_fabricated_balance",
    }
    assert {
        category: sum(fixture["category"] == category for fixture in fixtures)
        for category in evaluator.CATEGORIES
    } == {category: 5 for category in evaluator.CATEGORIES}


def test_fixture_schema_rejects_unknown_keys_and_long_excerpts():
    evaluator = _load_eval_module()
    fixture = {
        "id": "bad-01",
        "category": "company_claim",
        "source": "Synthetic Wire",
        "excerpt": "x" * 281,
        "expected": {
            "labels": ["company_claim"],
            "attribution_required": True,
            "redlines": [],
        },
        "unexpected": True,
    }

    errors = evaluator.validate_fixture_schema([fixture])

    assert any("unexpected" in error for error in errors)
    assert any("excerpt" in error for error in errors)


def test_fixture_schema_enforces_size_categories_vocab_and_consistency():
    evaluator = _load_eval_module()
    fixtures = evaluator.load_checked_in_corpus()

    undersized_errors = evaluator.validate_fixture_schema(fixtures[:8])
    assert any("exactly 45" in error for error in undersized_errors)
    assert any("all 9 categories" in error for error in undersized_errors)

    oversized_errors = evaluator.validate_fixture_schema(fixtures + [fixtures[0]])
    assert any("exactly 45" in error for error in oversized_errors)

    imbalanced = json.loads(json.dumps(fixtures))
    imbalanced[0]["category"] = "legal_procedure"
    imbalanced[0]["expected"]["labels"] = ["legal_procedure"]
    imbalanced_errors = evaluator.validate_fixture_schema(imbalanced)
    assert any("exactly 5 fixtures" in error for error in imbalanced_errors)

    bad = json.loads(json.dumps(fixtures))
    bad[0]["expected"]["labels"] = ["legal_procedure"]
    bad[1]["expected"]["redlines"] = ["not_in_the_allowed_vocabulary"]
    bad[2]["id"] = bad[3]["id"]
    errors = evaluator.validate_fixture_schema(bad)
    assert any("must exactly match category" in error for error in errors)
    assert any("redline" in error and "allowed" in error for error in errors)
    assert any("duplicated" in error for error in errors)


def test_fixture_corpus_is_fixed_to_checked_in_path_and_hash():
    evaluator = _load_eval_module()
    raw = evaluator.CORPUS_PATH.read_bytes()
    lf_raw = raw.replace(b"\r\n", b"\n")
    crlf_raw = lf_raw.replace(b"\n", b"\r\n")
    canonical_digest = "259a1f55824e38302bb8d84c1d9071062a2f92e03b6ac944adfe04d0a36cc2d4"

    assert evaluator.CORPUS_PATH == PIPELINE_DIR / "fixtures" / "objectivity_evidence.json"
    assert evaluator.CORPUS_SHA256 == canonical_digest
    assert evaluator.canonical_corpus_sha256(lf_raw) == canonical_digest
    assert evaluator.canonical_corpus_sha256(crlf_raw) == canonical_digest
    assert evaluator.load_checked_in_corpus() == json.loads(raw.decode("utf-8"))
    with pytest.raises(SystemExit):
        evaluator.main(["--fixtures", str(PIPELINE_DIR / "fixtures" / "tiny.json")])


def test_three_run_worst_case_aggregation_and_thresholds():
    evaluator = _load_eval_module()
    fixtures = evaluator.load_checked_in_corpus()
    required_indexes = [
        index for index, fixture in enumerate(fixtures)
        if fixture["expected"]["attribution_required"]
    ]
    wrong_index = required_indexes[0]
    calls = []

    def stub_runner(_fixtures, run_number):
        calls.append(run_number)
        wrong = {wrong_index} if run_number == 2 else set()
        return [
            {
                "id": fixture["id"],
                "labels": [fixture["category"]],
                "attribution_ok": index not in wrong,
                "redlines": [],
            }
            for index, fixture in enumerate(_fixtures)
        ]

    report = evaluator.evaluate_three_runs(fixtures, stub_runner)

    assert calls == [1, 2, 3]
    assert report["worst"] == {
        "redline_count": 0,
        "attribution_accuracy": round(
            (len(required_indexes) - 1) / len(required_indexes), 4),
        "structure_validity": 1.0,
    }
    assert report["accepted"] is True

    failed = evaluator.acceptance_result([
        {"redline_count": 1, "attribution_accuracy": 1.0, "structure_validity": 1.0},
        {"redline_count": 0, "attribution_accuracy": 0.949, "structure_validity": 1.0},
        {"redline_count": 0, "attribution_accuracy": 1.0, "structure_validity": 0.999},
    ])
    assert failed["accepted"] is False
    assert failed["worst"] == {
        "redline_count": 1,
        "attribution_accuracy": 0.949,
        "structure_validity": 0.999,
    }


def test_score_run_reports_aggregate_failure_breakdown():
    evaluator = _load_eval_module()
    fixtures = [
        {
            "id": "case-1",
            "category": "company_claim",
            "source": "Synthetic Wire",
            "excerpt": "A company reported a benchmark result.",
            "expected": {
                "labels": ["company_claim"],
                "attribution_required": True,
                "redlines": ["internal_benchmark_as_independent"],
            },
        },
        {
            "id": "case-2",
            "category": "legal_procedure",
            "source": "Synthetic Wire",
            "excerpt": "Prosecutors filed an allegation.",
            "expected": {
                "labels": ["legal_procedure"],
                "attribution_required": True,
                "redlines": ["allegation_as_conviction"],
            },
        },
        {
            "id": "case-3",
            "category": "waic_framing",
            "source": "Synthetic Wire",
            "excerpt": "An organizer described a product as leading.",
            "expected": {
                "labels": ["waic_framing"],
                "attribution_required": True,
                "redlines": ["marketing_as_fact"],
            },
        },
    ]
    rows = [
        {
            "id": "case-1",
            "labels": ["company_claim"],
            "attribution_ok": True,
            "redlines": [],
        },
        {
            "id": "case-2",
            "labels": ["company_claim"],
            "attribution_ok": False,
            "redlines": ["allegation_as_conviction"],
        },
        {"judge_batch_invalid": True},
    ]

    score = evaluator.score_run(fixtures, rows)

    assert score["diagnostics"] == {
        "invalid_case_count": 1,
        "label_mismatch_count": 1,
        "reported_redline_count": 1,
        "attribution_correct_count": 1,
        "attribution_required_count": 3,
    }


def test_structure_validity_rejects_extra_model_rows():
    evaluator = _load_eval_module()
    fixtures = [{
        "id": "case-1",
        "category": "company_claim",
        "source": "Synthetic Wire",
        "excerpt": "A company said a lab metric improved.",
        "expected": {
            "labels": ["company_claim"],
            "attribution_required": True,
            "redlines": [],
        },
    }]
    rows = [{
        "id": "case-1",
        "labels": ["company_claim"],
        "attribution_ok": True,
        "redlines": [],
    }, {
        "id": "invented-case",
        "labels": ["company_claim"],
        "attribution_ok": True,
        "redlines": [],
    }]

    assert evaluator.score_run(fixtures, rows)["structure_validity"] == 0.0


def test_production_harness_uses_real_pipeline_without_metadata_leaks_or_self_judging():
    evaluator = _load_eval_module()
    fixture = next(
        row for row in evaluator.load_checked_in_corpus()
        if row["category"] == "company_claim"
    )
    calls = {"candidate": [], "audit": [], "judge": []}

    class CandidateLLM:
        def json_call(self, system, user):
            calls["candidate"].append((system, user))
            return [{
                "idx": 0,
                "title": "The company described a prototype result",
                "summary": "The company said a prototype improved a lab metric.",
                "why": "The statement describes a test result.",
                "context": "The evidence is a company statement.",
                "significance": "The result has not been independently verified.",
                "watch": "Watch for independent verification.",
                "detail": "The company reported a result from a lab test.",
                "claims": [],
                "labels": [],
                "redlines": [],
            }]

    class AuditLLM:
        def json_call(self, system, user):
            calls["audit"].append((system, user))
            content = json.loads(user)["content"]
            return {
                "fields": {key: True for key in dn.OBJECTIVITY_FIELDS if key in content},
                "claims": [True for _ in content.get("claims", [])],
            }

    class JudgeLLM:
        def json_call(self, system, user):
            calls["judge"].append((system, user))
            return {"cases": [{
                "case_index": 0,
                "labels": ["company_claim"],
                "attribution_ok": True,
                "redlines": [fixture["expected"]["redlines"][0]],
            }]}

    runner = evaluator.ProductionHarnessRunner(
        dn, CandidateLLM(), AuditLLM(), JudgeLLM(),
        config={"topic_tags": [], "detail": {"enabled": True, "max_chars": 600}},
        batch_size=10,
    )
    rows = runner([fixture], run_number=1)

    assert len(calls["candidate"]) == 1
    assert len(calls["audit"]) == 1
    assert len(calls["judge"]) == 1
    assert calls["audit"][0][0] == dn.OBJECTIVITY_AUDIT_SYSTEM
    forbidden = (
        fixture["id"], fixture["category"], fixture["expected"]["redlines"][0],
        "expected", "threshold", "0.95", "95%", "100%",
    )
    for _system, user in (
            calls["candidate"] + calls["audit"] + calls["judge"]):
        assert all(value not in user for value in forbidden)

    judge_payload = json.loads(calls["judge"][0][1])
    assert set(judge_payload) == {"cases"}
    assert len(judge_payload["cases"]) == 1
    assert set(judge_payload["cases"][0]) == {"evidence", "candidate"}
    assert rows == [{
        "id": fixture["id"],
        "labels": ["company_claim"],
        "attribution_ok": True,
        "redlines": [fixture["expected"]["redlines"][0]],
    }]
    assert evaluator.score_run([fixture], rows)["redline_count"] == 1


def test_production_harness_keeps_fail_closed_fallback_candidate_for_judging():
    evaluator = _load_eval_module()
    fixture = evaluator.load_checked_in_corpus()[0]
    systems = []

    class CandidateLLM:
        def json_call(self, _system, _user):
            return [{
                "idx": 0, "title": "Unsafe candidate", "summary": "Unsafe summary",
                "why": "Unsafe why", "context": "Unsafe context",
                "significance": "Unsafe significance", "watch": "Unsafe watch",
                "detail": "Unsafe detail", "claims": [],
            }]

    class FailClosedAudit:
        def json_call(self, system, user):
            systems.append(system)
            if system == dn.OBJECTIVITY_REPAIR_SYSTEM:
                return {
                    "fields": {field: "Still unsafe" for field in dn.OBJECTIVITY_FIELDS},
                    "claims": [],
                }
            content = json.loads(user)["content"]
            return {
                "fields": {key: False for key in dn.OBJECTIVITY_FIELDS if key in content},
                "claims": [False for _ in content.get("claims", [])],
            }

    class JudgeLLM:
        def json_call(self, _system, user):
            candidate = json.loads(user)["cases"][0]["candidate"]
            assert candidate["title"].startswith(fixture["source"][:10])
            return {"cases": [{
                "case_index": 0, "labels": [fixture["category"]],
                "attribution_ok": True, "redlines": [],
            }]}

    runner = evaluator.ProductionHarnessRunner(
        dn, CandidateLLM(), FailClosedAudit(), JudgeLLM(),
        config={"topic_tags": [], "detail": {"enabled": True, "max_chars": 600}},
    )

    rows = runner([fixture], run_number=1)

    assert systems == [
        dn.OBJECTIVITY_AUDIT_SYSTEM,
        dn.OBJECTIVITY_REPAIR_SYSTEM,
        dn.OBJECTIVITY_AUDIT_SYSTEM,
    ]
    assert len(rows) == 1


@pytest.mark.parametrize("raw_judge", [
    {
        "cases": [{
            "case_index": 0, "labels": ["company_claim"],
            "attribution_ok": True, "redlines": [],
        }],
        "unexpected": True,
    },
    {"cases": [{
        "case_index": 0, "labels": ["company_claim"],
        "attribution_ok": True, "redlines": [], "unexpected": True,
    }]},
    {"cases": []},
    {"cases": [
        {
            "case_index": 0, "labels": ["company_claim"],
            "attribution_ok": True, "redlines": [],
        },
        {
            "case_index": 0, "labels": ["company_claim"],
            "attribution_ok": True, "redlines": [],
        },
    ]},
    {"cases": [{
        "case_index": 1, "labels": ["company_claim"],
        "attribution_ok": True, "redlines": [],
    }]},
    {"cases": [{
        "case_index": "0", "labels": ["company_claim"],
        "attribution_ok": True, "redlines": [],
    }]},
    {"cases": [{
        "case_index": 0, "labels": ["not_allowed"],
        "attribution_ok": True, "redlines": [],
    }]},
    {"cases": [{
        "case_index": 0, "labels": [{}],
        "attribution_ok": True, "redlines": [],
    }]},
    {"cases": [{
        "case_index": 0, "labels": [[]],
        "attribution_ok": True, "redlines": [],
    }]},
    {"cases": [{
        "case_index": 0, "labels": [7],
        "attribution_ok": True, "redlines": [],
    }]},
    {"cases": [{
        "case_index": 0, "labels": [None],
        "attribution_ok": True, "redlines": [],
    }]},
    {"cases": [{
        "case_index": 0, "labels": ["company_claim"],
        "attribution_ok": True, "redlines": [{}],
    }]},
    {"cases": [{
        "case_index": 0, "labels": ["company_claim"],
        "attribution_ok": True, "redlines": [[]],
    }]},
    {"cases": [{
        "case_index": 0, "labels": ["company_claim"],
        "attribution_ok": True, "redlines": [7],
    }]},
    {"cases": [{
        "case_index": 0, "labels": ["company_claim"],
        "attribution_ok": True, "redlines": [None],
    }]},
])
def test_production_harness_does_not_launder_invalid_raw_judge_batches(raw_judge):
    evaluator = _load_eval_module()
    fixture = next(
        row for row in evaluator.load_checked_in_corpus()
        if row["category"] == "company_claim"
    )

    class CandidateLLM:
        def json_call(self, _system, _user):
            return [{
                "idx": 0, "title": "Safe candidate", "summary": "Safe summary.",
                "why": "", "context": "", "significance": "", "watch": "",
                "detail": "", "claims": [],
            }]

    class AuditLLM:
        def json_call(self, _system, user):
            content = json.loads(user)["content"]
            return {
                "fields": {key: True for key in content if key != "claims"},
                "claims": [],
            }

    class JudgeLLM:
        def json_call(self, _system, _user):
            return raw_judge

    runner = evaluator.ProductionHarnessRunner(
        dn, CandidateLLM(), AuditLLM(), JudgeLLM(),
        config={"topic_tags": [], "detail": {"enabled": True, "max_chars": 600}},
    )

    rows = runner([fixture], run_number=1)
    score = evaluator.score_run([fixture], rows)

    assert score["structure_validity"] < 1.0


def test_production_harness_marks_validator_exceptions_as_invalid(monkeypatch):
    evaluator = _load_eval_module()
    fixture = next(
        row for row in evaluator.load_checked_in_corpus()
        if row["category"] == "company_claim"
    )

    class CandidateLLM:
        def json_call(self, _system, _user):
            return [{
                "idx": 0, "title": "Safe candidate", "summary": "Safe summary.",
                "why": "", "context": "", "significance": "", "watch": "",
                "detail": "", "claims": [],
            }]

    class AuditLLM:
        def json_call(self, _system, user):
            content = json.loads(user)["content"]
            return {
                "fields": {key: True for key in content if key != "claims"},
                "claims": [],
            }

    class JudgeLLM:
        def json_call(self, _system, _user):
            return {"cases": [{
                "case_index": 0, "labels": ["company_claim"],
                "attribution_ok": True, "redlines": [],
            }]}

    def raise_validator_error(_raw, _expected_count):
        raise RuntimeError("validator failed")

    monkeypatch.setattr(
        evaluator, "_validated_judge_batch", raise_validator_error)
    runner = evaluator.ProductionHarnessRunner(
        dn, CandidateLLM(), AuditLLM(), JudgeLLM(),
        config={"topic_tags": [], "detail": {"enabled": True, "max_chars": 600}},
    )

    rows = runner([fixture], run_number=1)

    assert evaluator.score_run([fixture], rows)["structure_validity"] < 1.0


def test_objectivity_field_caps_apply_to_enrichment_repair_and_serialization():
    limits = dn.OBJECTIVITY_FIELD_LIMITS
    oversized = "oversized text " * 200
    event = {"ids": [0], **{field: "safe" for field in dn.OBJECTIVITY_FIELDS}}

    dn._apply_objectivity_repair(
        event,
        {"fields": {field: oversized for field in dn.OBJECTIVITY_FIELDS}},
        list(dn.OBJECTIVITY_FIELDS),
        [],
        {"Synthetic Wire"},
    )

    assert all(len(event[field]) <= limits[field] for field in dn.OBJECTIVITY_FIELDS)

    evidence_text = "FULLTEXT_SENTINEL_DO_NOT_PERSIST_" + ("z" * 900)
    item = {
        "title": "Safe source title", "desc": "Safe public description",
        "source": "Synthetic Wire", "source_id": "synthetic-wire",
        "source_type": "fact", "tier": "T1", "credibility": 9,
        "url": "https://example.test/item",
        "time": "2026-07-18T00:00:00+00:00",
        "evidence_text": evidence_text, "evidence_basis": "fulltext",
        "source_family": "synthetic-wire", "provenance": "original",
    }
    leaky = {
        "ids": [0], "category": "ai", "score": 90, "tier": "T1",
        "status": "发展中", "tags": [],
        **{field: evidence_text for field in dn.OBJECTIVITY_FIELDS},
    }

    serialized = dn.event_to_item(
        leaky, [item], "pick", full_objectivity=True, source_limit=4)

    assert "FULLTEXT_SENTINEL_DO_NOT_PERSIST" not in json.dumps(
        serialized, ensure_ascii=False)
    assert all(
        len(serialized[field]) <= limits[field]
        for field in dn.OBJECTIVITY_FIELDS
        if field in serialized
    )


def test_conservative_fallback_never_uses_fulltext_when_public_desc_is_empty():
    sentinel = "FULLTEXT_SENTINEL_DO_NOT_PERSIST_" + ("e" * 400)
    item = {
        "title": "Safe source title", "desc": "", "source": "Synthetic Wire",
        "source_type": "fact", "evidence_text": sentinel,
    }
    event = {
        "ids": [0], "title": sentinel, "summary": sentinel,
        "why": sentinel, "evidence": {"degraded": False},
    }

    dn._conservative_event_fallback(event, [item], dn.new_quality_stats())

    assert "FULLTEXT_SENTINEL_DO_NOT_PERSIST" not in json.dumps(
        event, ensure_ascii=False)


def test_final_serialization_strips_substantial_fulltext_copy_with_attribution_prefix():
    copied = (
        "The filing says the laboratory result was measured under a private internal "
        "benchmark and has not been independently reproduced by another organization."
    )
    item = {
        "title": "Safe filing title", "desc": "A short public RSS description.",
        "source": "Synthetic Wire", "source_id": "synthetic-wire",
        "source_type": "fact", "tier": "T1", "credibility": 9,
        "url": "https://example.test/filing",
        "time": "2026-07-18T00:00:00+00:00",
        "evidence_text": copied, "evidence_basis": "fulltext",
    }
    event = {
        "ids": [0], "category": "finance", "score": 90, "tier": "T1",
        "title": "Safe edited title", "summary": "Safe edited summary.",
        "detail": f"According to Synthetic Wire: {copied}",
        "status": "发展中", "tags": [],
    }

    serialized = dn.event_to_item(
        event, [item], "pick", full_objectivity=True, source_limit=4)

    assert "detail" not in serialized


def test_missing_title_and_summary_defaults_never_persist_fulltext(
        tmp_path, monkeypatch):
    sentinel = "DEFAULT_PROJECTION_FULLTEXT_SENTINEL_" + ("q" * 180)
    item = {
        "title": sentinel, "desc": sentinel,
        "source": "Synthetic Wire", "source_id": "synthetic-wire",
        "source_type": "fact", "tier": "T1", "credibility": 9,
        "url": "https://example.test/default-projection",
        "time": "2026-07-18T00:00:00+00:00",
        "evidence_text": sentinel, "evidence_basis": "fulltext",
    }
    event = {
        "ids": [0], "category": "ai", "score": 90, "tier": "T1",
        "status": "developing", "tags": [],
    }

    serialized = dn.event_to_item(
        dict(event), [item], "pick", full_objectivity=True, source_limit=4)

    assert "DEFAULT_PROJECTION_FULLTEXT_SENTINEL" not in json.dumps(
        serialized, ensure_ascii=False)

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    payload = dn.write_output(
        "2026-07-18", "safe brief", [dict(event)], [], [item],
        {"objectivity": {"mode": "active"}}, quality=dn.new_quality_stats(),
    )

    assert "DEFAULT_PROJECTION_FULLTEXT_SENTINEL" not in json.dumps(
        payload, ensure_ascii=False)
    persisted = (tmp_path / "daily" / "2026-07-18.js").read_text(encoding="utf-8")
    assert "DEFAULT_PROJECTION_FULLTEXT_SENTINEL" not in persisted


@pytest.mark.parametrize("variant", ["suffix", "punctuation_whitespace"])
def test_persistence_strips_substantial_fulltext_copy_variants(
        tmp_path, monkeypatch, variant):
    evidence = (
        "The regulator recorded 128 transactions; the filing says they were reviewed "
        "under an internal process, but no independent audit was included."
    )
    if variant == "suffix":
        copied = evidence + " — according to Synthetic Wire."
    else:
        copied = (
            "The regulator recorded 128 transactions ... the filing says\n"
            "they were reviewed under an internal process — but no independent\t"
            "audit was included!"
        )
    item = {
        "title": "Safe filing title", "desc": "A short public RSS description.",
        "source": "Synthetic Wire", "source_id": "synthetic-wire",
        "source_type": "fact", "tier": "T1", "credibility": 9,
        "url": "https://example.test/filing",
        "time": "2026-07-18T00:00:00+00:00",
        "evidence_text": evidence, "evidence_basis": "fulltext",
    }
    event = {
        "ids": [0], "category": "finance", "score": 90, "tier": "T1",
        "title": "Safe edited title", "summary": "Safe edited summary.",
        "detail": copied, "status": "发展中", "tags": [],
    }
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    payload = dn.write_output(
        "2026-07-18", "safe brief", [event], [], [item],
        {"objectivity": {"mode": "active"}}, quality=dn.new_quality_stats(),
    )

    assert "detail" not in payload["items"][0]
    persisted = (tmp_path / "daily" / "2026-07-18.js").read_text(encoding="utf-8")
    assert copied not in persisted


def test_fulltext_overlap_guard_preserves_paraphrase_and_ordinary_short_fact():
    evidence = (
        "The company said its internal benchmark improved by twelve percent during a "
        "private laboratory run, and no outside organization reproduced the result."
    )
    item = {
        "title": "Safe company title", "desc": "A short public RSS description.",
        "source": "Synthetic Wire", "source_id": "synthetic-wire",
        "source_type": "fact", "tier": "T1", "credibility": 9,
        "url": "https://example.test/company",
        "time": "2026-07-18T00:00:00+00:00",
        "evidence_text": evidence, "evidence_basis": "fulltext",
    }
    paraphrase = (
        "The reported improvement came from the firm's own test and still lacks "
        "replication by an external organization."
    )
    short_fact = "The company reported a result."
    event = {
        "ids": [0], "category": "finance", "score": 90, "tier": "T1",
        "title": "Safe edited title", "summary": short_fact,
        "detail": paraphrase, "status": "发展中", "tags": [],
    }

    serialized = dn.event_to_item(
        event, [item], "pick", full_objectivity=True, source_limit=4)

    assert serialized["summary"] == short_fact
    assert serialized["detail"] == paraphrase


def test_repair_strips_attributed_fulltext_copy_before_reaudit():
    evidence = (
        "The filing describes an internal benchmark measured during a private test and "
        "states that no independent organization reproduced the reported result."
    )
    item = {
        "title": "Safe title", "desc": "Short RSS description.",
        "source": "Synthetic Wire", "source_type": "fact",
        "evidence_text": evidence, "evidence_basis": "fulltext",
    }
    event = {
        "ids": [0], "title": "Safe title", "summary": "Safe summary.",
        "detail": "Unsafe initial detail.", "category": "finance",
    }

    class RepairAudit:
        def __init__(self):
            self.audit_calls = 0

        def json_call(self, system, user):
            if system == dn.OBJECTIVITY_REPAIR_SYSTEM:
                return {
                    "fields": {"detail": f"Synthetic Wire reported: {evidence}"},
                    "claims": [],
                }
            content = json.loads(user)["content"]
            self.audit_calls += 1
            if self.audit_calls == 1:
                return {
                    "fields": {key: key != "detail" for key in content if key != "claims"},
                    "claims": [],
                }
            assert "detail" not in content
            return {
                "fields": {key: True for key in content if key != "claims"},
                "claims": [],
            }

    dn.audit_enrichment_support(
        RepairAudit(), [event], [item], dn.new_quality_stats(), secondary=[])

    assert "detail" not in event


def test_fail_closed_fallback_does_not_reintroduce_fulltext_via_desc_overlap():
    evidence = (
        "The filing describes an internal benchmark measured during a private test and "
        "states that no independent organization reproduced the reported result."
    )
    item = {
        "title": "Safe title", "desc": evidence,
        "source": "Synthetic Wire", "source_type": "fact",
        "evidence_text": evidence, "evidence_basis": "fulltext",
    }
    event = {
        "ids": [0], "title": "Unsafe title", "summary": "Unsafe summary.",
        "detail": "Unsafe detail.", "category": "finance",
    }

    class AlwaysFailAudit:
        def json_call(self, system, user):
            if system == dn.OBJECTIVITY_REPAIR_SYSTEM:
                return {"fields": {}, "claims": []}
            content = json.loads(user)["content"]
            return {
                "fields": {key: False for key in content if key != "claims"},
                "claims": [],
            }

    dn.audit_enrichment_support(
        AlwaysFailAudit(), [event], [item], dn.new_quality_stats(), secondary=[])

    assert evidence not in event["summary"]
    assert len(event["summary"]) < 80


def test_fulltext_sentinel_never_survives_repair_fallback_or_persistent_consumers(
        tmp_path, monkeypatch):
    sentinel = "FULLTEXT_SENTINEL_DO_NOT_PERSIST_" + ("q" * 900)
    item = {
        "title": "Safe source title", "desc": "Safe public description",
        "source": "Synthetic Wire", "source_id": "synthetic-wire",
        "source_type": "fact", "tier": "T1", "credibility": 9,
        "url": "https://example.test/item",
        "time": "2026-07-18T00:00:00+00:00",
        "evidence_text": sentinel, "evidence_basis": "fulltext",
        "source_family": "synthetic-wire", "provenance": "original",
    }
    event = {
        "ids": [0], "category": "ai", "title": "Initial safe title",
        "summary": "Initial safe summary", "why": "Initial safe why",
        "context": "Initial safe context", "significance": "Initial safe significance",
        "watch": "Initial safe watch", "detail": "Initial safe detail",
        "claims": [], "score": 90, "tier": "T1", "status": "发展中",
        "tags": [], "risk_flags": {"allegation_legal": True},
        "evidence": {
            "basis": "fulltext", "publisher_count": 1,
            "independent_chain_count": 1, "degraded": False,
        },
    }

    class FailClosedAudit:
        def json_call(self, system, user):
            if system == dn.OBJECTIVITY_REPAIR_SYSTEM:
                return {
                    "fields": {field: sentinel for field in dn.OBJECTIVITY_FIELDS},
                    "claims": [],
                }
            content = json.loads(user)["content"]
            return {
                "fields": {key: False for key in dn.OBJECTIVITY_FIELDS if key in content},
                "claims": [False for _ in content.get("claims", [])],
            }

    quality = dn.new_quality_stats()
    picked = [event]
    secondary = []
    dn.audit_enrichment_support(
        FailClosedAudit(), picked, [item], quality, secondary=secondary)

    assert picked == []
    assert secondary == [event]
    assert event["title"].startswith("Synthetic Wire")
    assert event["summary"].endswith("Safe public description")
    assert not any(field in event for field in dn.QUALITY_EXTENSION_FIELDS)
    assert "FULLTEXT_SENTINEL_DO_NOT_PERSIST" not in json.dumps(
        event, ensure_ascii=False)

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    registry = dn.track_events(
        None, [event], "2026-07-18", {"events": {}}, secondary=[])
    payload = dn.write_output(
        "2026-07-18", "safe brief", [event], [], [item],
        {"objectivity": {"mode": "active"}}, registry=registry, quality=quality,
    )
    dn.write_feed(
        tmp_path, "2026-07-18",
        {"feed_days": 7, "site_url": "https://example.test"},
    )
    weekly_material = dn.weekly_pick_material([payload])

    assert "FULLTEXT_SENTINEL_DO_NOT_PERSIST" not in json.dumps(
        registry, ensure_ascii=False)
    assert "FULLTEXT_SENTINEL_DO_NOT_PERSIST" not in json.dumps(
        payload, ensure_ascii=False)
    assert "FULLTEXT_SENTINEL_DO_NOT_PERSIST" not in "\n".join(weekly_material)
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert "FULLTEXT_SENTINEL_DO_NOT_PERSIST" not in path.read_text(
                encoding="utf-8")


def test_workflow_shadow_job_is_non_blocking_read_only_and_untracked():
    workflow = (ROOT / ".github" / "workflows" / "daily-news.yml").read_text(encoding="utf-8")
    assert "shadow:" in workflow
    generate = workflow.split("  generate:", 1)[1].split("  shadow:", 1)[0]
    assert "python news-pipeline/daily_news.py\n" in generate
    assert "git commit" in generate
    assert "git push" in generate
    assert "--objectivity-shadow" not in generate
    shadow = workflow.split("  shadow:", 1)[1]
    assert "continue-on-error: true" in shadow
    assert "timeout-minutes: 24" in shadow
    assert "needs: generate" in shadow
    assert "needs.generate.result == 'success'" in shadow
    assert "contents: read" in shadow
    assert "ref: main" in shadow
    assert "python news-pipeline/daily_news.py --objectivity-shadow" in shadow
    assert "${{ github.workspace }}/source/news/data" in shadow
    assert "${{ runner.temp }}" not in shadow
    assert "git commit" not in shadow
    assert "git push" not in shadow


def test_weekly_repair_prompt_names_actual_scoped_evidence_keys():
    assert "cited_items" not in dn.WEEKLY_REPAIR_SYSTEM
    for key in ("whole_week_evidence", "thread_evidence", "watch_recap_evidence"):
        assert key in dn.WEEKLY_REPAIR_SYSTEM


def test_rollout_docs_state_interim_and_unmet_acceptance_contract():
    objectivity = (ROOT / "docs" / "news_objectivity_plan.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs" / "news_source_roadmap.md").read_text(encoding="utf-8")
    readme = (ROOT / "readme.md").read_text(encoding="utf-8")
    combined = "\n".join((objectivity, roadmap, readme))

    for phrase in (
        "interim wording hotfix",
        "--objectivity-shadow",
        "7-day",
        "45-case",
        "three-run",
        "95%",
        "100%",
        "active mode is not enabled",
        "publisher_count",
        "independent_chain_count",
        "degraded",
        "paywall",
    ):
        assert phrase in combined

    for stale_count in ("40+", "至少 40", "at least 40"):
        assert stale_count not in combined
    assert "45 条" in combined
    assert "9 类各 5 条" in combined
    assert "14-day" in roadmap
    assert "before adding sources" in roadmap
    assert "full text is not persisted" in combined
    assert "live acceptance has not occurred" in combined
    for metric_name in (
        "selected_before_audit",
        "selected_after_audit",
        "audited_candidate_count",
        "demoted_from_selected",
        "source_reference_concentration",
    ):
        assert metric_name in combined
