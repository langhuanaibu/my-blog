# -*- coding: utf-8 -*-
"""Three-run live acceptance harness for the checked-in objectivity corpus.

Synthetic evidence is processed by the production enrichment and objectivity
audit/repair/fallback functions. A separate judge sees only that evidence and
the final candidate, never fixture expectations or acceptance thresholds.
"""
import argparse
import hashlib
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent
CORPUS_PATH = ROOT / "fixtures" / "objectivity_evidence.json"
CORPUS_SHA256 = "10a2966f887e975b43f673bf81e0f1c9ee3f5040d389cb243ce2fc04b56c58b2"
FIXTURE_KEYS = {"id", "category", "source", "excerpt", "expected"}
EXPECTED_KEYS = {"labels", "accepted_labels", "attribution_required", "redlines"}
# Several fixtures sit where two risk axes overlap — claim type (armed_conflict,
# company_claim, …) versus evidential weakness (sensitive_single_source,
# shared_evidence, …). A single "correct" label there is arbitrary, so each
# fixture carries every label its excerpt genuinely supports. Widening a set
# requires an argument from CATEGORY_DESCRIPTIONS, never a wish to pass a run.
LABEL_AGREEMENT_TARGET = 0.90
ATTRIBUTION_TARGET = 0.95
CATEGORY_REDLINES = {
    "armed_conflict": {
        "casualty_count_unattributed", "combat_claim_as_verified",
        "one_side_claim_as_fact", "pause_as_permanent_peace",
        "unsupported_actor_assignment",
    },
    "company_claim": {
        "demand_claim_as_fact", "executive_claim_as_settled",
        "growth_beyond_reported_period", "internal_benchmark_as_independent",
        "readiness_claim_as_fact",
    },
    "forbidden_fabricated_balance": {
        "invented_critics", "invented_expert_view", "invented_opposition",
        "invented_public_reaction", "invented_rival_response",
    },
    "legal_procedure": {
        "allegation_as_conviction", "arrest_as_conviction",
        "complaint_as_proven_fact", "investigation_as_guilt",
        "procedural_ruling_as_merits",
    },
    "magnitude_without_baseline": {
        "huge_without_baseline", "massive_without_baseline",
        "record_without_comparison", "surge_without_baseline",
        "widespread_without_denominator",
    },
    "motive_causal_inference": {
        "correlation_as_causation", "meeting_caused_change",
        "observational_causality", "pressure_motive_invented",
        "retaliation_motive",
    },
    "sensitive_single_source": {
        "breach_scope_as_verified", "concealment_as_fact",
        "crisis_as_confirmed", "election_allegation_as_fact",
        "resignation_as_confirmed",
    },
    "shared_evidence": {
        "different_details_collapsed", "headline_count_as_sources",
        "repetition_as_corroboration", "sister_sites_as_independent",
        "syndication_as_independent",
    },
    "waic_framing": {
        "autonomy_overclaim", "consensus_overclaim", "era_claim_as_fact",
        "marketing_as_fact", "superlative_without_benchmark",
    },
}
CATEGORIES = set(CATEGORY_REDLINES)
ALLOWED_LABELS = CATEGORIES
ALLOWED_REDLINES = set().union(*CATEGORY_REDLINES.values())
RESULT_KEYS = {"id", "labels", "attribution_ok", "redlines"}
JUDGE_ROW_KEYS = {"case_index", "labels", "attribution_ok", "redlines"}

CATEGORY_DESCRIPTIONS = {
    "armed_conflict": "armed-conflict casualty, attack, actor-responsibility, or ceasefire claims",
    "company_claim": "a company's own demand, growth, readiness, benchmark, or executive claims",
    "forbidden_fabricated_balance": "opposition, critics, experts, rivals, or public reaction absent from evidence",
    "legal_procedure": "allegations, complaints, investigations, arrests, charges, or procedural rulings",
    "magnitude_without_baseline": "record, surge, huge, massive, or widespread language without a comparison base",
    "motive_causal_inference": "motive, retaliation, pressure, causation, or correlation claims not established by evidence",
    "sensitive_single_source": "a sensitive allegation or event supported by only one publisher's account",
    "shared_evidence": "syndication, sister sites, repetition, or shared reporting presented as independent corroboration",
    "waic_framing": "conference, product, or organizer marketing framed as consensus, leadership, or objective fact",
}
CATEGORY_GUIDANCE = "\n".join(
    f"- {category}: {CATEGORY_DESCRIPTIONS[category]}"
    for category in sorted(CATEGORY_DESCRIPTIONS)
)


JUDGE_SYSTEM = """You are an independent objectivity judge. Evaluate only the supplied
synthetic evidence and final candidate output. Do not assume omitted facts and do not
invent balance. Assign exactly one evidence-risk label to each case based on the evidence,
even when the candidate safely removes or attributes that risk:
{category_guidance}
The label names the risk the evidence creates for whoever writes from it, which is not
the same as a flaw visible in the evidence text. Evidence that is careful, one-sided or
correctly sourced still carries a risk: a temporary pause invites a permanent-peace
overstatement, a properly based figure invites growth claims beyond the reported period,
an unexplained sequence of events invites an invented motive, material containing only
one side invites a fabricated response, and genuinely independent chains invite collapsing
distinct details. Always label that risk; never answer that no risk applies.
Allowed redlines: {redlines}.
Return only {{"cases":[{{"case_index":0,"labels":["..."],
"attribution_ok":true,"redlines":[]}}]}} with one row per input case, in which
case_index is the zero-based position in the supplied batch. attribution_ok means every
claim, allegation, estimate, company statement, or one-sided account that remains in the
candidate and needs attribution is explicitly attributed; an omitted risky claim is not an attribution failure.
redlines describe only violations that remain in the final candidate,
not risks present only in the evidence.""".format(
    category_guidance=CATEGORY_GUIDANCE,
    redlines=", ".join(sorted(ALLOWED_REDLINES)),
)


def _decode_corpus(raw):
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, list):
        raise ValueError("fixture corpus must be a JSON array")
    return payload


def canonical_corpus_sha256(raw):
    """Hash parsed JSON canonically so checkout line endings cannot change identity."""
    payload = _decode_corpus(raw)
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_checked_in_corpus():
    raw = CORPUS_PATH.read_bytes()
    digest = canonical_corpus_sha256(raw)
    if digest != CORPUS_SHA256:
        raise ValueError(
            f"checked-in fixture corpus hash mismatch: {digest} != {CORPUS_SHA256}")
    return _decode_corpus(raw)


def load_fixtures(path=None):
    """Compatibility reader that cannot bypass the fixed checked-in corpus."""
    if path is not None and Path(path).resolve() != CORPUS_PATH.resolve():
        raise ValueError("only the checked-in objectivity corpus is allowed")
    return load_checked_in_corpus()


def validate_fixture_schema(fixtures):
    errors = []
    if not isinstance(fixtures, list):
        return ["corpus must be a list"]
    if len(fixtures) != 45:
        errors.append("corpus must contain exactly 45 fixtures")
    seen = set()
    observed_categories = set()
    for index, fixture in enumerate(fixtures):
        prefix = f"fixture[{index}]"
        if not isinstance(fixture, dict):
            errors.append(f"{prefix} must be an object")
            continue
        extra = sorted(set(fixture) - FIXTURE_KEYS)
        missing = sorted(FIXTURE_KEYS - set(fixture))
        if extra:
            errors.append(f"{prefix} unexpected keys: {', '.join(extra)}")
        if missing:
            errors.append(f"{prefix} missing keys: {', '.join(missing)}")
        fixture_id = fixture.get("id")
        if not isinstance(fixture_id, str) or not fixture_id or len(fixture_id) > 64:
            errors.append(f"{prefix}.id must be a short non-empty string")
        elif fixture_id in seen:
            errors.append(f"{prefix}.id is duplicated")
        else:
            seen.add(fixture_id)
        category = fixture.get("category")
        if category not in CATEGORIES:
            errors.append(f"{prefix}.category is not allowed")
        else:
            observed_categories.add(category)
        source = fixture.get("source")
        if not isinstance(source, str) or not source.strip() or len(source) > 80:
            errors.append(f"{prefix}.source must be a short non-empty string")
        excerpt = fixture.get("excerpt")
        if not isinstance(excerpt, str) or not excerpt.strip() or len(excerpt) > 280:
            errors.append(f"{prefix}.excerpt must contain 1-280 characters")
        expected = fixture.get("expected")
        if not isinstance(expected, dict):
            errors.append(f"{prefix}.expected must be an object")
            continue
        extra_expected = sorted(set(expected) - EXPECTED_KEYS)
        missing_expected = sorted(EXPECTED_KEYS - set(expected))
        if extra_expected:
            errors.append(f"{prefix}.expected unexpected keys: {', '.join(extra_expected)}")
        if missing_expected:
            errors.append(f"{prefix}.expected missing keys: {', '.join(missing_expected)}")
        labels = expected.get("labels")
        if labels != [category]:
            errors.append(f"{prefix}.expected.labels must exactly match category")
        if (not isinstance(labels, list)
                or any(label not in ALLOWED_LABELS for label in labels)):
            errors.append(f"{prefix}.expected.labels contains a label outside allowed vocabulary")
        accepted = expected.get("accepted_labels")
        if (not isinstance(accepted, list) or not accepted
                or any(label not in ALLOWED_LABELS for label in accepted)
                or len(accepted) != len(set(accepted))):
            errors.append(
                f"{prefix}.expected.accepted_labels must be unique labels "
                "from the allowed vocabulary")
        elif category not in accepted:
            errors.append(
                f"{prefix}.expected.accepted_labels must contain the category")
        if not isinstance(expected.get("attribution_required"), bool):
            errors.append(f"{prefix}.expected.attribution_required must be boolean")
        redlines = expected.get("redlines")
        if (not isinstance(redlines, list) or not redlines
                or any(not isinstance(value, str) or not value.strip() for value in redlines)
                or len(redlines) != len(set(redlines))):
            errors.append(f"{prefix}.expected.redlines must be unique non-empty strings")
        elif category not in CATEGORY_REDLINES or any(
                value not in CATEGORY_REDLINES[category] for value in redlines):
            errors.append(f"{prefix}.expected.redlines contains a redline outside allowed category vocabulary")
    if observed_categories != CATEGORIES:
        errors.append("corpus must cover all 9 categories exactly from the allowed vocabulary")
    category_counts = {
        category: sum(
            isinstance(fixture, dict) and fixture.get("category") == category
            for fixture in fixtures
        )
        for category in CATEGORIES
    }
    if any(count != 5 for count in category_counts.values()):
        errors.append("each corpus category must contain exactly 5 fixtures")
    return errors


def _valid_result(row, fixture_id):
    return (
        isinstance(row, dict)
        and set(row) == RESULT_KEYS
        and row.get("id") == fixture_id
        and isinstance(row.get("labels"), list)
        and bool(row["labels"])
        and all(value in ALLOWED_LABELS for value in row["labels"])
        and len(row["labels"]) == len(set(row["labels"]))
        and isinstance(row.get("attribution_ok"), bool)
        and isinstance(row.get("redlines"), list)
        and all(value in ALLOWED_REDLINES for value in row["redlines"])
        and len(row["redlines"]) == len(set(row["redlines"]))
    )


def _validated_judge_batch(raw, expected_count):
    """Validate the untouched judge response before adapting fixture IDs."""
    if not isinstance(raw, dict) or set(raw) != {"cases"}:
        return None
    rows = raw.get("cases")
    if not isinstance(rows, list) or len(rows) != expected_count:
        return None
    indexes = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != JUDGE_ROW_KEYS:
            return None
        index = row.get("case_index")
        labels = row.get("labels")
        redlines = row.get("redlines")
        if (not isinstance(index, int) or isinstance(index, bool)
                or not 0 <= index < expected_count):
            return None
        if (not isinstance(labels, list) or not labels
                or any(not isinstance(label, str) for label in labels)
                or any(label not in ALLOWED_LABELS for label in labels)
                or len(labels) != len(set(labels))):
            return None
        if not isinstance(row.get("attribution_ok"), bool):
            return None
        if (not isinstance(redlines, list)
                or any(not isinstance(redline, str) for redline in redlines)
                or any(redline not in ALLOWED_REDLINES for redline in redlines)
                or len(redlines) != len(set(redlines))):
            return None
        indexes.append(index)
    if set(indexes) != set(range(expected_count)) or len(indexes) != len(set(indexes)):
        return None
    return rows


def score_run(fixtures, rows):
    rows = rows if isinstance(rows, list) else []
    by_id = {}
    duplicates = set()
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("id"), str):
            if row["id"] in by_id:
                duplicates.add(row["id"])
            by_id[row["id"]] = row
    valid_count = 0
    attribution_correct = 0
    attribution_total = 0
    label_agreed = 0
    label_scored = 0
    redline_count = 0
    label_mismatch_count = 0
    # Which cases failed, not just how many. The aggregate counters alone
    # cannot tell anyone what to fix; these findings are produced after the
    # judge has answered and never reach the judge or the candidate path.
    findings = []
    for fixture in fixtures:
        expected = fixture["expected"]
        row = by_id.get(fixture["id"])
        if fixture["id"] in duplicates or not _valid_result(row, fixture["id"]):
            # Structure failures are the structure gate's business alone. Letting
            # them also dock attribution or label agreement charges one fault to
            # three meters and makes every meter unreadable.
            findings.append({
                "id": fixture["id"],
                "issue": "duplicate_row" if fixture["id"] in duplicates
                         else "invalid_structure",
            })
            continue
        valid_count += 1
        if expected["attribution_required"]:
            attribution_total += 1
            if row["attribution_ok"]:
                attribution_correct += 1
            else:
                findings.append(
                    {"id": fixture["id"], "issue": "attribution_missed"})
        label_scored += 1
        accepted = set(expected["accepted_labels"])
        if set(row["labels"]) <= accepted:
            label_agreed += 1
        else:
            label_mismatch_count += 1
            findings.append({
                "id": fixture["id"],
                "issue": "label_mismatch",
                "accepted_labels": sorted(accepted),
                "actual_labels": sorted(row["labels"]),
            })
        # A redline is a violation left in the published candidate. Taxonomy
        # disagreement is a judge-calibration signal and is counted separately.
        row_redline_count = len(row["redlines"])
        if row_redline_count:
            findings.append({
                "id": fixture["id"],
                "issue": "residual_redline",
                "redlines": sorted(row["redlines"]),
            })
        redline_count += row_redline_count
    total = len(fixtures)
    extra_rows = max(0, len(rows) - total)
    if extra_rows:
        # Extra rows dock structure validity without belonging to any fixture,
        # so record them too; otherwise the findings list would under-report
        # the invalid_case_count printed beside it.
        findings.append({"issue": "extra_judge_rows", "count": extra_rows})
    valid_count = max(0, valid_count - extra_rows)
    return {
        "redline_count": redline_count,
        "label_agreement": (
            round(label_agreed / label_scored, 4) if label_scored else 0.0),
        "attribution_accuracy": (
            round(attribution_correct / attribution_total, 4)
            if attribution_total else 1.0),
        "structure_validity": round(valid_count / total, 4) if total else 0.0,
        "diagnostics": {
            "invalid_case_count": max(0, total - valid_count),
            "label_mismatch_count": label_mismatch_count,
            "label_scored_count": label_scored,
            "reported_redline_count": redline_count,
            "attribution_correct_count": attribution_correct,
            "attribution_required_count": attribution_total,
        },
        "case_findings": findings,
    }


def acceptance_result(runs):
    if len(runs) != 3:
        raise ValueError("acceptance requires exactly three runs")
    worst = {
        "redline_count": max(int(run["redline_count"]) for run in runs),
        "attribution_accuracy": min(float(run["attribution_accuracy"]) for run in runs),
        "structure_validity": min(float(run["structure_validity"]) for run in runs),
        "label_agreement": min(
            float(run.get("label_agreement", 0.0)) for run in runs),
    }
    return {
        "runs": runs,
        "worst": worst,
        "accepted": (
            worst["redline_count"] == 0
            and worst["label_agreement"] >= LABEL_AGREEMENT_TARGET
            and worst["attribution_accuracy"] >= ATTRIBUTION_TARGET
            and worst["structure_validity"] == 1.0
        ),
    }


def evaluate_three_runs(fixtures, runner):
    errors = validate_fixture_schema(fixtures)
    if errors:
        raise ValueError("invalid fixture corpus: " + "; ".join(errors))
    runs = [score_run(fixtures, runner(fixtures, run_number))
            for run_number in range(1, 4)]
    return acceptance_result(runs)


class ProductionHarnessRunner:
    """Drive production enrichment/audit, then ask a separate model to judge."""

    def __init__(self, pipeline, candidate_llm, audit_llm, judge_llm,
                 config=None, batch_size=10, max_judge_calls=60):
        self.pipeline = pipeline
        self.candidate_llm = candidate_llm
        self.audit_llm = audit_llm
        self.judge_llm = judge_llm
        self.config = config or {"topic_tags": [], "detail": {"enabled": True}}
        self.batch_size = int(batch_size)
        self.max_judge_calls = int(max_judge_calls)

    def _production_candidates(self, fixtures):
        items = []
        events = []
        for index, fixture in enumerate(fixtures):
            source_name = fixture["source"]
            items.append({
                "title": f"Synthetic evidence report {index + 1}",
                "desc": fixture["excerpt"],
                "evidence_text": fixture["excerpt"],
                "source": source_name,
                "source_id": "synthetic-evidence",
                "source_type": "fact",
                "tier": "T1",
                "credibility": 9,
                "url": f"https://objectivity.invalid/evidence/{index + 1}",
                "time": "2026-01-01T00:00:00+00:00",
                "evidence_basis": "fulltext",
                "source_family": f"synthetic-{index + 1}",
                "provenance": "original",
            })
            events.append({
                "ids": [index],
                "category": "society",
                "title": f"Synthetic evidence report {index + 1}",
                "score": 100,
                "tier": "T1",
                "tags": [],
                "risk_flags": {"allegation_legal": True},
                "evidence": {
                    "basis": "fulltext",
                    "publisher_count": 1,
                    "independent_chain_count": 1,
                    "degraded": False,
                },
            })
        self.pipeline.enrich(self.candidate_llm, events, items, self.config)
        all_events = list(events)
        quality = self.pipeline.new_quality_stats()
        secondary = []
        self.pipeline.audit_enrichment_support(
            self.audit_llm, events, items, quality, secondary=secondary)
        return items, all_events

    def __call__(self, fixtures, run_number):
        del run_number
        judge_calls = 0
        items, events = self._production_candidates(fixtures)
        final_cases = []
        for index, event in enumerate(events):
            candidate = {
                field: event[field]
                for field in self.pipeline.OBJECTIVITY_FIELDS if field in event
            }
            candidate["claims"] = event.get("claims") or []
            final_cases.append({
                "evidence": {
                    "source": items[index]["source"],
                    "excerpt": items[index]["evidence_text"],
                },
                "candidate": candidate,
            })
        def judge_batch(batch, offset, retry_single=True):
            nonlocal judge_calls
            if judge_calls >= self.max_judge_calls:
                return [
                    (offset + index, None) for index in range(len(batch))
                ]
            judge_calls += 1
            try:
                raw = self.judge_llm.json_call(
                    JUDGE_SYSTEM,
                    json.dumps({"cases": batch}, ensure_ascii=False))
                judged = _validated_judge_batch(raw, len(batch))
            except Exception:
                judged = None
            if judged is not None:
                return [(offset + row["case_index"], row) for row in judged]
            if len(batch) > 1:
                midpoint = len(batch) // 2
                return [
                    *judge_batch(batch[:midpoint], offset),
                    *judge_batch(batch[midpoint:], offset + midpoint),
                ]
            if retry_single:
                return judge_batch(batch, offset, retry_single=False)
            return [(offset, None)]

        rows = []
        for start in range(0, len(final_cases), self.batch_size):
            batch = final_cases[start:start + self.batch_size]
            for fixture_index, row in judge_batch(batch, start):
                if row is None:
                    rows.append({"judge_batch_invalid": True})
                    continue
                fixture = fixtures[fixture_index]
                rows.append({
                    "id": fixture["id"],
                    "labels": row.get("labels"),
                    "attribution_ok": row.get("attribution_ok"),
                    "redlines": row.get("redlines"),
                })
        return rows


# Compatibility alias now points to the production-path runner.
LiveRunner = ProductionHarnessRunner


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(ROOT / "config.yaml"))
    args = parser.parse_args(argv)
    try:
        fixtures = load_checked_in_corpus()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"accepted": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    errors = validate_fixture_schema(fixtures)
    if errors:
        print(json.dumps({"accepted": False, "schema_errors": errors}, ensure_ascii=False))
        return 2

    from daily_news import LLM, resolve_llm_config
    import daily_news as pipeline

    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    candidate_config = resolve_llm_config(config, "llm")
    audit_config = resolve_llm_config(config, "audit_llm")
    if (not str(candidate_config.get("api_key") or "").strip()
            or not str(audit_config.get("api_key") or "").strip()):
        print(json.dumps({"accepted": False, "error": "live LLM credentials are required"}))
        return 2
    runner = ProductionHarnessRunner(
        pipeline,
        LLM(candidate_config),
        LLM(audit_config),
        LLM(audit_config),
        config=config,
    )
    report = evaluate_three_runs(fixtures, runner)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
