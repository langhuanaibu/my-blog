"""Acceptance-only rollout evidence and Judge evaluation.

This module never participates in publication decisions.  It accepts only
allow-listed pipeline projections and emits temporary evidence/report JSON.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlsplit


EVIDENCE_VERSION = "rollout-evidence-v1"
REPORT_VERSION = "rollout-report-v1"

SELECTION_METRICS = {
    "threshold",
    "quality_floor",
    "picked_count",
    "category_counts",
    "qualified_supply",
    "reserved_count",
    "below_threshold_reserved",
    "over_threshold_secondary",
    "threshold_source",
    "history_days",
    "selected_below_quality_floor",
    "selected_opinion_only",
    "category_reservation_violations",
    "threshold_clamp",
    "threshold_clamp_valid",
    "threshold_in_clamp",
}

TRAJECTORY_METRICS = {
    "candidate_matches",
    "continuity_accepted",
    "continuity_rejected",
    "filtered_history_rows",
    "generation_fallbacks",
    "audit_fallbacks",
    "final_watch_count",
    "final_trusted_continuation_count",
    "selected_count",
    "final_watch_coverage",
}

JUDGE_ROW_FIELDS = {
    "idx",
    "continuity",
    "history_support",
    "watch_has_variable",
    "watch_has_landmark",
    "decision",
    "certainty",
    "reason_code",
    "reason",
}
JUDGE_CERTAINTIES = {"certain", "uncertain"}
JUDGE_REASON_CODES = {
    "supported", "unsupported", "insufficient_evidence", "ambiguous",
}

JUDGE_SYSTEM = """你是日报轨迹验收 Judge，与生成和发布审计相互独立。
一次性检查用户提供的全部 cases，逐项返回且不得遗漏、重复或改写 idx。
continuity/history_support 只能是 pass、fail、not_applicable；只有可信延续才适用。
watch_has_variable 与 watch_has_landmark 必须是布尔值，分别表示公开 watch 是否包含
关键变量和可观察路标。decision 只能是 pass、fail、needs_review；certainty 只能是
certain、uncertain；reason_code 只能是 supported、unsupported、insufficient_evidence、
ambiguous。pass 必须同时使用 certain + supported；任何不确定都必须用 uncertain，且
decision 必须是 needs_review，禁止猜测通过。reason 用一句简洁理由。
只输出 JSON：{"rows":[{"idx":0,"continuity":"pass",
"history_support":"pass","watch_has_variable":true,
"watch_has_landmark":true,"decision":"pass","certainty":"certain",
"reason_code":"supported","reason":"..."}]}。"""

_UNCERTAINTY_PATTERNS = (
    re.compile(
        r"\b(?:may|might|could|possibly|perhaps|maybe)\s+"
        r"(?:still\s+)?(?:be\s+)?"
        r"(?:supported|valid|correct|related|confirmed|verified)\b"
        r"|\b(?:may|might|could)\s+(?:still\s+)?not\s+(?:be\s+)?"
        r"(?:supported|valid|correct|related|confirmed|verified|"
        r"verify|confirm|determine|establish)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:it|this|that|evidence|evidence\s+verification|"
        r"relationship|support|continuation|"
        r"the\s+(?:evidence|relationship|support|continuation))\s+"
        r"(?:is|remains|seems|appears)\s+(?:still\s+)?"
        r"(?:uncertain|unclear|inconclusive|unverified|unconfirmed|ambiguous|doubtful)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:cannot|can't|unable\s+to)\s+"
        r"(?:(?:independently|conclusively|fully)\s+)?"
        r"(?:verify|confirm|determine|establish)\b"
        r"|\b(?:cannot|can't)\s+be\s+"
        r"(?:(?:independently|conclusively|fully)\s+)?"
        r"(?:verified|confirmed|determined|established)\b"
        r"|\bnot\s+(?:(?:independently|conclusively|fully)\s+)?"
        r"(?:verified|confirmed)\b"
        r"|\b(?:insufficient|inadequate)\s+evidence\s+"
        r"(?:to|for)\s+(?:verify|confirm|determine|establish)\b",
        re.I,
    ),
    re.compile(
        r"^\s*(?:uncertain|unclear|inconclusive|unverified|unconfirmed|ambiguous|doubtful|not\s+sure)"
        r"\s*[.!?]?\s*$",
        re.I,
    ),
    re.compile(
        r"不确定|证据不足|(?:可能|也许|或许)(?:仍然|仍|尚)?"
        r"(?:得到|获得)?(?:支持|通过|成立|有效|相关|属实|正确)"
        r"|(?:可能|也许|或许)(?:仍然|仍|尚)?(?:并不|并未|不|尚未|未)"
        r"(?:得到|获得)?(?:支持|通过|成立|有效|相关|属实|正确|确认|核实|验证)"
        r"|(?:目前)?(?:尚|仍|依然)?(?:不清楚|不明确)(?:是否)?"
        r"|(?:证据|核验结果|验证结果|关系|延续|结论)(?:仍|尚|依然)?"
        r"(?:无定论|未经核实|未获确认|未确认|不明确|不清楚)"
        r"|证据(?:仍|尚|依然)?(?:不足|不充分)(?:以|来)?"
        r"(?:确认|核实|验证|判断|支持)"
        r"|(?:尚待|有待)(?:确认|核实|验证)"
        r"|(?:无法|不能|尚不能)(?:独立|充分|最终)?(?:确认|核实|验证|判断)"
        r"|存疑|(?:存在|仍有|含有)?歧义"
    ),
)
_ADVERSATIVE_RE = re.compile(
    r"\b(?:but|however|nevertheless)\b|(?:但是|不过|然而|可是|但)", re.I)
_PRIOR_CONTEXT_RE = re.compile(
    r"\b(?:previously|earlier|initially|formerly)\b|(?:此前|先前|之前|早先|曾经|原先|原有)",
    re.I,
)
_CURRENT_CONTEXT_RE = re.compile(
    r"\b(?:now|currently|today)\b|\b(?:new|latest)\s+"
    r"(?:evidence|filing|report|document)\b"
    r"|(?:现在|目前|当前|如今|今天|现已|新文件|最新文件|新证据|最新证据)",
    re.I,
)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PUBLIC_ITEM_ID_RE = re.compile(r"^(?:pick|more)-\d+$")
_ITEM_REF_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}):((?:pick|more)-\d+)$")
_FORBIDDEN_EVIDENCE_KEYS = {
    "fulltext", "content", "article_body", "article_bodies", "body",
    "api_key", "password", "token", "cookie", "credentials",
    "environment", "environ", "environment_values", "env", "secret", "secrets",
    "article", "article_text", "raw_text", "evidence_text",
}


def _has_explicit_uncertainty(reason):
    normalized = " ".join(str(reason).split())
    adversatives = list(_ADVERSATIVE_RE.finditer(normalized))
    if adversatives:
        normalized = normalized[adversatives[-1].end():].strip()
    else:
        prior = _PRIOR_CONTEXT_RE.search(normalized)
        if prior:
            current = [match for match in _CURRENT_CONTEXT_RE.finditer(normalized)
                       if match.start() > prior.end()]
            if current:
                normalized = normalized[current[0].start():].strip()
    return any(pattern.search(normalized) for pattern in _UNCERTAINTY_PATTERNS)


def _fingerprint(paths, projection=None):
    digest = hashlib.sha256()
    for raw_path in paths:
        path = Path(raw_path)
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    if projection is not None:
        digest.update(b"config\0")
        digest.update(json.dumps(
            projection, ensure_ascii=False, sort_keys=True,
            separators=(",", ":")).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _endpoint_identity(value):
    try:
        parsed = urlsplit(str(value or "").strip())
        if not parsed.scheme or not parsed.hostname:
            return ""
        port = f":{parsed.port}" if parsed.port else ""
        path = re.sub(r"/+", "/", parsed.path or "/")
        if len(path) > 1:
            path = path.rstrip("/")
        route_hash = hashlib.sha256(path.encode("utf-8")).hexdigest()[:16]
        return (f"{parsed.scheme.lower()}://{parsed.hostname.lower()}{port}"
                f"|route:{route_hash}")
    except (TypeError, ValueError):
        return ""


def _model_projection(raw, *, enabled=False):
    raw = raw if isinstance(raw, dict) else {}
    projection = {}
    if enabled:
        projection["enabled"] = raw.get("enabled") is True
    for key in ("model", "temperature", "max_retries"):
        if key in raw:
            projection[key] = copy.deepcopy(raw[key])
    endpoint = _endpoint_identity(raw.get("base_url"))
    if endpoint:
        projection["endpoint"] = endpoint
    extra = raw.get("extra_body") if isinstance(raw.get("extra_body"), dict) else {}
    extra_projection = {}
    for section in ("thinking", "response_format"):
        value = extra.get(section)
        if isinstance(value, dict) and "type" in value:
            extra_projection[section] = {"type": copy.deepcopy(value["type"])}
    if extra_projection:
        projection["extra_body"] = extra_projection
    return projection


def _selected_mapping(raw, keys):
    raw = raw if isinstance(raw, dict) else {}
    return {key: copy.deepcopy(raw[key]) for key in keys if key in raw}


def _runtime_config_projection(config):
    config = config if isinstance(config, dict) else {}
    return {
        "llm": _model_projection(config.get("llm")),
        "audit_llm": _model_projection(config.get("audit_llm")),
        "prefilter": _model_projection(config.get("prefilter"), enabled=True),
        "objectivity": _selected_mapping(config.get("objectivity"), ("mode",)),
        "selection": {
            **_selected_mapping(config, (
                "pick_threshold", "pick_min", "pick_max",
                "min_per_category", "max_per_category", "interest_weights")),
            "pick_dynamic": _selected_mapping(config.get("pick_dynamic"), (
                "enabled", "window_days", "percentile", "clamp",
                "min_history_days", "backfill_offset")),
            "scoring": _selected_mapping(config.get("scoring"), (
                "dim_weights", "tier_multipliers", "fit_span")),
            "opinion": _selected_mapping(config.get("opinion"), ("cooccur_bonus",)),
        },
    }


def _trajectory_config_projection(config):
    config = config if isinstance(config, dict) else {}
    return {
        "trajectory": _selected_mapping(config.get("trajectory"), ("enabled",)),
        "events": _selected_mapping(config.get("events"), (
            "match_window_days", "archive_days", "prune_archived_days")),
    }


def build_stage_fingerprints(*, config, runtime_paths, trajectory_ui_paths):
    """Hash only allow-listed config and files that affect each rollout stage."""
    return {
        "runtime": _fingerprint(
            runtime_paths, _runtime_config_projection(config)),
        "trajectory_ui": _fingerprint(
            trajectory_ui_paths, _trajectory_config_projection(config)),
    }


def build_rollout_evidence(*, date_str, mode, runtime_seconds, selection,
                           trajectory, review_cases, runtime_paths,
                           trajectory_ui_paths, config):
    """Build a JSON-safe evidence envelope from already allow-listed inputs."""
    return {
        "version": EVIDENCE_VERSION,
        "date": str(date_str),
        "run": {
            "status": "success",
            "mode": str(mode),
            "runtime_seconds": round(float(runtime_seconds), 3),
        },
        "selection": copy.deepcopy(selection),
        "trajectory": copy.deepcopy(trajectory),
        "fingerprints": build_stage_fingerprints(
            config=config, runtime_paths=runtime_paths,
            trajectory_ui_paths=trajectory_ui_paths),
        "review_cases": copy.deepcopy(review_cases),
    }


def _reject_forbidden_keys(value, path="evidence"):
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            if normalized in _FORBIDDEN_EVIDENCE_KEYS:
                raise ValueError(f"forbidden evidence field at {path}.{key}")
            _reject_forbidden_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_keys(child, f"{path}[{index}]")


def _validate_evidence_allowlist(evidence):
    if set(evidence) != {
            "version", "date", "run", "selection", "trajectory",
            "fingerprints", "review_cases"}:
        raise ValueError("rollout evidence violates the allow-list")
    if (not isinstance(evidence.get("run"), dict)
            or set(evidence["run"]) != {"status", "mode", "runtime_seconds"}
            or not isinstance(evidence.get("selection"), dict)
            or set(evidence["selection"]) != SELECTION_METRICS
            or not isinstance(evidence.get("trajectory"), dict)
            or set(evidence["trajectory"]) != TRAJECTORY_METRICS
            or not isinstance(evidence.get("fingerprints"), dict)
            or set(evidence["fingerprints"]) != {"runtime", "trajectory_ui"}
            or not isinstance(evidence.get("review_cases"), list)):
        raise ValueError("rollout evidence violates the allow-list")
    public_fields = {
        "id", "title", "summary", "context", "watch", "claims",
        "trusted_continuation", "day_count", "history",
    }
    history_fields = {"date", "title", "summary", "watch", "item_ref"}

    def bounded_text(value, limit, *, empty=True):
        return (isinstance(value, str) and len(value) <= limit
                and (empty or bool(value.strip())))

    def valid_history_row(row, *, public_history=False):
        allowed = ({"date", "summary", "item_ref"}
                   if public_history else history_fields)
        if (not isinstance(row, dict) or not set(row).issubset(allowed)
                or not bounded_text(row.get("date"), 10, empty=False)
                or not _DATE_RE.fullmatch(row["date"])
                or not bounded_text(row.get("summary", ""), 160)):
            return False
        limits = {"title": 80, "watch": 160, "item_ref": 120}
        return all(bounded_text(row[field], limits[field])
                   for field in limits if field in row)

    for case in evidence["review_cases"]:
        if not isinstance(case, dict):
            raise ValueError("rollout evidence violates the allow-list")
        public = case.get("public")
        if (set(case) != {"idx", "picked_index", "public", "sources",
                          "verified_history"}
                or type(case.get("idx")) is not int or case["idx"] < 0
                or type(case.get("picked_index")) is not int
                or case["picked_index"] < 0
                or not isinstance(public, dict)
                or not set(public).issubset(public_fields)
                or not bounded_text(public.get("id"), 80, empty=False)
                or not _PUBLIC_ITEM_ID_RE.fullmatch(public["id"])
                or not bounded_text(public.get("title"), 80, empty=False)
                or not bounded_text(public.get("summary"), 160)
                or ("context" in public and not bounded_text(public["context"], 160))
                or ("watch" in public and not bounded_text(public["watch"], 160))
                or ("trusted_continuation" in public
                    and type(public["trusted_continuation"]) is not bool)
                or ("day_count" in public
                    and (type(public["day_count"]) is not int
                         or public["day_count"] < 1))
                or ("history" in public
                    and (not isinstance(public["history"], list)
                         or any(not valid_history_row(row, public_history=True)
                                for row in public["history"])))
                or ("claims" in public
                    and (not isinstance(public["claims"], list)
                         or len(public["claims"]) > 4
                         or any(not isinstance(claim, dict)
                                or set(claim) != {"text", "kind", "sources"}
                                or not bounded_text(claim.get("text"), 120, empty=False)
                                or claim.get("kind") not in {"fact", "analysis", "uncertain"}
                                or not isinstance(claim.get("sources"), list)
                                or any(not bounded_text(source, 200, empty=False)
                                       for source in claim["sources"])
                                for claim in public["claims"])))
                or not isinstance(case.get("sources"), list)
                or any(not isinstance(source, dict)
                       or set(source) != {"source", "title", "snippet"}
                       or not bounded_text(source.get("source"), 200, empty=False)
                       or not bounded_text(source.get("title"), 400)
                       or not bounded_text(source.get("snippet"), 400)
                       for source in case["sources"])
                or not isinstance(case.get("verified_history"), list)
                or any(not valid_history_row(row)
                       for row in case["verified_history"])):
            raise ValueError("rollout evidence violates the allow-list")


def write_rollout_evidence(evidence, *, data_dir, environ=None):
    """Atomically write evidence only when ROLLOUT_EVIDENCE_PATH is explicit."""
    environ = os.environ if environ is None else environ
    configured = str(environ.get("ROLLOUT_EVIDENCE_PATH") or "").strip()
    if not configured:
        return False
    target = Path(configured).resolve()
    public_data = Path(data_dir).resolve()
    if target == public_data or public_data in target.parents:
        raise ValueError("ROLLOUT_EVIDENCE_PATH must be outside DATA_DIR")
    repository_data = (Path(__file__).resolve().parent.parent
                       / "source" / "news" / "data").resolve()
    if target == repository_data or repository_data in target.parents:
        raise ValueError("ROLLOUT_EVIDENCE_PATH must be outside source/news/data")
    if not isinstance(evidence, dict) or evidence.get("version") != EVIDENCE_VERSION:
        raise ValueError("unsupported rollout evidence")
    _reject_forbidden_keys(evidence)
    _validate_evidence_allowlist(evidence)
    target.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=target.parent,
        prefix=f".{target.name}.", suffix=".tmp", delete=False)
    temp_path = Path(handle.name)
    try:
        with handle:
            json.dump(evidence, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temp_path, target)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    return True


def resolve_judge_llm_config(cfg):
    """Reuse audit LLM identity/settings while forcing deterministic sampling."""
    primary = dict(cfg.get("llm") or {})
    override = cfg.get("audit_llm") or {}
    merged = dict(primary)
    for key, value in override.items():
        if key in {"base_url", "api_key", "model"} and not str(value or "").strip():
            continue
        if value is not None:
            merged[key] = value
    merged["temperature"] = 0.0
    return merged


def _is_nonnegative_int(value):
    return type(value) is int and value >= 0


def _selection_result(evidence, shadow_success):
    selection = evidence.get("selection") if isinstance(evidence, dict) else None
    if not isinstance(shadow_success, bool):
        return "needs_review", ["shadow outcome is malformed"], selection or {}
    if not isinstance(selection, dict) or not SELECTION_METRICS.issubset(selection):
        return "needs_review", ["selection evidence metrics are incomplete"], selection or {}
    integer_fields = (
        "threshold", "quality_floor", "picked_count", "reserved_count",
        "below_threshold_reserved", "over_threshold_secondary", "history_days",
        "selected_below_quality_floor", "selected_opinion_only",
        "category_reservation_violations",
    )
    category_counts = selection.get("category_counts")
    qualified_supply = selection.get("qualified_supply")
    if (any(not _is_nonnegative_int(selection.get(field)) for field in integer_fields)
            or not isinstance(category_counts, dict) or not category_counts
            or not isinstance(qualified_supply, dict)
            or set(category_counts) != set(qualified_supply)
            or any(not _is_nonnegative_int(value) for value in category_counts.values())
            or any(not _is_nonnegative_int(value) for value in qualified_supply.values())
            or not isinstance(selection.get("threshold_source"), str)
            or not selection["threshold_source"].strip()
            or type(selection.get("threshold_clamp_valid")) is not bool
            or type(selection.get("threshold_in_clamp")) is not bool
            or not isinstance(selection.get("threshold_clamp"), list)
            or len(selection["threshold_clamp"]) != 2
            or any(not _is_nonnegative_int(value) for value in selection["threshold_clamp"])):
        return "needs_review", ["selection evidence metrics are malformed"], selection
    if (sum(category_counts.values()) != selection["picked_count"]
            or selection["quality_floor"] > selection["threshold"]
            or selection["reserved_count"] > selection["picked_count"]
            or selection["below_threshold_reserved"] > selection["reserved_count"]
            or selection["selected_below_quality_floor"] > selection["picked_count"]
            or selection["selected_opinion_only"] > selection["picked_count"]
            or selection["category_reservation_violations"] > len(category_counts)):
        return "needs_review", ["selection evidence metrics are inconsistent"], selection
    reasons = []
    if not shadow_success:
        reasons.append("shadow outcome was not successful")
    if selection["selected_below_quality_floor"]:
        reasons.append("selected items fell below the active quality floor")
    if selection["selected_opinion_only"]:
        reasons.append("selected opinion-only items were present")
    if selection["category_reservation_violations"]:
        reasons.append("category reservation violations were present")
    if selection["picked_count"] > 32:
        reasons.append("picked count exceeded 32")
    clamp = selection["threshold_clamp"]
    actual_in_clamp = clamp[0] <= selection["threshold"] <= clamp[1]
    if (not selection["threshold_clamp_valid"]
            or not selection["threshold_in_clamp"]
            or clamp[0] > clamp[1] or not actual_in_clamp):
        reasons.append("threshold was not inside a valid clamp")
    return ("fail" if reasons else "pass"), reasons, selection


def _continuation_link_valid(public):
    if public.get("trusted_continuation") is not True:
        return True
    day_count = public.get("day_count")
    history = public.get("history")
    if (type(day_count) is not int or day_count < 2
            or not isinstance(history, list) or not history
            or not isinstance(history[0], dict)):
        return False
    history_date = str(history[0].get("date") or "")
    if not _DATE_RE.fullmatch(history_date):
        return False
    item_ref = history[0].get("item_ref")
    if not item_ref:
        return True
    match = _ITEM_REF_RE.fullmatch(str(item_ref))
    return bool(match and match.group(1) == history_date)


def _valid_case_set(cases):
    if not isinstance(cases, list):
        return False
    expected = set(range(len(cases)))
    indexes = {case.get("idx") for case in cases if isinstance(case, dict)}
    if indexes != expected or len(indexes) != len(cases):
        return False
    picked_indexes = []
    item_ids = []
    for case in cases:
        if (not isinstance(case, dict)
                or type(case.get("picked_index")) is not int
                or case["picked_index"] < 0
                or not isinstance(case.get("public"), dict)
                or not isinstance(case.get("sources"), list)
                or not isinstance(case.get("verified_history"), list)):
            return False
        public = case["public"]
        if not isinstance(public.get("id"), str) or not public["id"]:
            return False
        picked_indexes.append(case["picked_index"])
        item_ids.append(public["id"])
        if public.get("trusted_continuation") is not True and not public.get("watch"):
            return False
    return (len(set(picked_indexes)) == len(picked_indexes)
            and len(set(item_ids)) == len(item_ids))


def _needs_review_verdict(case, reason):
    return {
        "idx": case["idx"],
        "item_id": str(case.get("public", {}).get("id") or ""),
        "continuity": "not_applicable",
        "history_support": "not_applicable",
        "watch_has_variable": False,
        "watch_has_landmark": False,
        "decision": "needs_review",
        "certainty": "uncertain",
        "reason_code": "ambiguous",
        "reason": reason,
    }


def _judge_verdicts(cases, judge_llm):
    try:
        raw = judge_llm.json_call(
            JUDGE_SYSTEM, json.dumps({"cases": cases}, ensure_ascii=False))
    except Exception as exc:
        reason = f"Judge infrastructure failure: {exc}"
        return [_needs_review_verdict(case, reason) for case in cases], reason
    rows = raw.get("rows") if isinstance(raw, dict) else None
    if not isinstance(rows, list):
        reason = "Judge schema failure: rows must be a list"
        return [_needs_review_verdict(case, reason) for case in cases], reason

    by_index = {}
    duplicates = set()
    global_malformed = False
    for row in rows:
        if not isinstance(row, dict):
            global_malformed = True
            continue
        index = row.get("idx")
        if type(index) is not int or not 0 <= index < len(cases):
            global_malformed = True
            continue
        if index in by_index:
            duplicates.add(index)
        else:
            by_index[index] = row

    verdicts = []
    for case in cases:
        index = case["idx"]
        row = by_index.get(index)
        reason = None
        if global_malformed:
            reason = "Judge returned an out-of-range or malformed row"
        elif index in duplicates:
            reason = "Judge returned a duplicate row"
        elif not isinstance(row, dict):
            reason = "Judge omitted the required row"
        elif set(row) != JUDGE_ROW_FIELDS:
            reason = "Judge row fields were malformed"
        elif (row.get("continuity") not in {"pass", "fail", "not_applicable"}
              or row.get("history_support") not in {"pass", "fail", "not_applicable"}
              or type(row.get("watch_has_variable")) is not bool
              or type(row.get("watch_has_landmark")) is not bool
              or row.get("decision") not in {"pass", "fail", "needs_review"}
              or row.get("certainty") not in JUDGE_CERTAINTIES
              or row.get("reason_code") not in JUDGE_REASON_CODES
              or not isinstance(row.get("reason"), str)
              or not row["reason"].strip() or len(row["reason"].strip()) > 240):
            reason = "Judge row values were malformed"
        elif (row["decision"] == "needs_review"
              or row["certainty"] == "uncertain"
              or row["reason_code"] in {"insufficient_evidence", "ambiguous"}
              or _has_explicit_uncertainty(row["reason"])):
            reason = row["reason"]
        elif ((row["decision"] == "pass"
               and (row["certainty"] != "certain"
                    or row["reason_code"] != "supported"))
              or (row["decision"] == "fail"
                  and (row["certainty"] != "certain"
                       or row["reason_code"] != "unsupported"))):
            reason = "Judge decision contradicted its structured reason"
        else:
            trusted = case["public"].get("trusted_continuation") is True
            expected = {"pass", "fail"} if trusted else {"not_applicable"}
            if (row["continuity"] not in expected
                    or row["history_support"] not in expected):
                reason = "Judge applicability did not match the review case"
        if reason is not None:
            verdicts.append(_needs_review_verdict(case, reason))
            continue
        verdict = copy.deepcopy(row)
        verdict["item_id"] = str(case["public"].get("id") or "")
        trusted = case["public"].get("trusted_continuation") is True
        if trusted and (verdict["continuity"] != "pass"
                        or verdict["history_support"] != "pass"):
            verdict["decision"] = "fail"
        verdicts.append(verdict)
    return verdicts, None


def _trajectory_result(evidence, judge_llm):
    health = evidence.get("trajectory") if isinstance(evidence, dict) else None
    cases = evidence.get("review_cases") if isinstance(evidence, dict) else None
    if (not isinstance(health, dict) or not TRAJECTORY_METRICS.issubset(health)
            or any(not _is_nonnegative_int(health.get(field))
                   for field in TRAJECTORY_METRICS - {"final_watch_coverage"})
            or isinstance(health.get("final_watch_coverage"), bool)
            or not isinstance(health.get("final_watch_coverage"), (int, float))):
        return "needs_review", ["trajectory evidence metrics are incomplete or malformed"], 0.0, [], health or {}
    expected_coverage = (health["final_watch_count"] / health["selected_count"]
                         if health["selected_count"] else 0.0)
    if (health["final_watch_count"] > health["selected_count"]
            or health["final_trusted_continuation_count"]
            > health["continuity_accepted"]
            or health["continuity_accepted"] + health["continuity_rejected"]
            > health["candidate_matches"]
            or not 0.0 <= float(health["final_watch_coverage"]) <= 1.0
            or abs(float(health["final_watch_coverage"]) - expected_coverage) > 1e-9):
        return "needs_review", ["trajectory evidence metrics are inconsistent"], 0.0, [], health
    if not _valid_case_set(cases):
        return "needs_review", ["trajectory review cases are incomplete or malformed"], 0.0, [], health

    public_watch_cases = [case for case in cases if case["public"].get("watch")]
    trusted_cases = [case for case in cases
                     if case["public"].get("trusted_continuation") is True]
    if (len(public_watch_cases) != health["final_watch_count"]
            or any(case["picked_index"] >= health["selected_count"] for case in cases)):
        return "needs_review", ["public watch review-case coverage is incomplete"], 0.0, [], health
    if len(trusted_cases) != health["final_trusted_continuation_count"]:
        return "needs_review", ["final trusted continuation review-case coverage is incomplete"], 0.0, [], health
    if health["candidate_matches"] < 1 or health["final_watch_count"] < 1:
        return "neutral", ["no candidate match or no public watch"], 0.0, [], health
    if judge_llm is None:
        verdicts = [_needs_review_verdict(case, "Judge is unavailable") for case in cases]
        return "needs_review", ["Judge infrastructure is unavailable"], 0.0, verdicts, health

    verdicts, judge_error = _judge_verdicts(cases, judge_llm)
    verdict_by_index = {row["idx"]: row for row in verdicts}
    watch_good = sum(
        1 for case in public_watch_cases
        if verdict_by_index[case["idx"]]["watch_has_variable"]
        and verdict_by_index[case["idx"]]["watch_has_landmark"])
    watch_ratio = round(watch_good / len(public_watch_cases), 4)
    reasons = []
    if judge_error:
        reasons.append(judge_error)
    if any(not _continuation_link_valid(case["public"]) for case in trusted_cases):
        reasons.append("deterministic continuation link validation failed")
    if any(verdict_by_index[case["idx"]]["continuity"] != "pass"
           or verdict_by_index[case["idx"]]["history_support"] != "pass"
           for case in trusted_cases):
        reasons.append("trusted continuation or history support failed")
    if watch_ratio < 0.8:
        reasons.append("fewer than 80% of public watches had a variable and landmark")
    decisions = {row["decision"] for row in verdicts}
    if "needs_review" in decisions:
        status = "needs_review"
        if not reasons:
            reasons.append("Judge returned needs_review")
    elif "fail" in decisions or reasons:
        status = "fail"
        if "fail" in decisions and not reasons:
            reasons.append("Judge failed one or more review cases")
    else:
        status = "pass"
    return status, reasons, watch_ratio, verdicts, health


def evaluate_rollout(evidence, *, shadow_success, judge_llm):
    """Evaluate selection and trajectory gates without changing pipeline state."""
    required_envelope = {
        "version", "date", "run", "selection", "trajectory",
        "fingerprints", "review_cases",
    }
    run = evidence.get("run") if isinstance(evidence, dict) else None
    fingerprints = evidence.get("fingerprints") if isinstance(evidence, dict) else None
    valid_envelope = (
        isinstance(evidence, dict) and set(evidence) == required_envelope
        and evidence.get("version") == EVIDENCE_VERSION
        and bool(_DATE_RE.fullmatch(str(evidence.get("date") or "")))
        and isinstance(run, dict)
        and set(run) == {"status", "mode", "runtime_seconds"}
        and run.get("status") == "success"
        and isinstance(run.get("mode"), str) and bool(run["mode"])
        and isinstance(run.get("runtime_seconds"), (int, float))
        and not isinstance(run.get("runtime_seconds"), bool)
        and run["runtime_seconds"] >= 0
        and isinstance(fingerprints, dict)
        and set(fingerprints) == {"runtime", "trajectory_ui"}
        and all(isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))
                for value in fingerprints.values()))
    if valid_envelope:
        try:
            _reject_forbidden_keys(evidence)
            _validate_evidence_allowlist(evidence)
        except (TypeError, ValueError):
            valid_envelope = False
    if valid_envelope:
        selection_status, selection_reasons, selection_metrics = _selection_result(
            evidence, shadow_success)
        trajectory_status, trajectory_reasons, watch_ratio, verdicts, trajectory_metrics = \
            _trajectory_result(evidence, judge_llm)
    else:
        selection_status = trajectory_status = "needs_review"
        selection_reasons = trajectory_reasons = ["rollout evidence envelope is invalid"]
        selection_metrics = {}
        trajectory_metrics = {}
        watch_ratio = 0.0
        verdicts = []
    return {
        "version": REPORT_VERSION,
        "date": evidence.get("date", "") if isinstance(evidence, dict) else "",
        "selection": {
            "status": selection_status,
            "reasons": selection_reasons,
            "metrics": copy.deepcopy(selection_metrics),
        },
        "trajectory": {
            "status": trajectory_status,
            "reasons": trajectory_reasons,
            "watch_ratio": watch_ratio,
            "metrics": copy.deepcopy(trajectory_metrics),
            "verdicts": verdicts,
        },
        "fingerprints": copy.deepcopy(evidence.get("fingerprints", {}))
        if isinstance(evidence, dict) else {},
    }


def parse_cli_args(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate rollout evidence")
    parser.add_argument("--evidence", required=True, help="rollout-evidence-v1 JSON")
    parser.add_argument("--shadow-outcome", required=True, choices=("success", "failure"))
    parser.add_argument("--config", default=str(Path(__file__).with_name("config.yaml")))
    parser.add_argument("--output", default="", help="optional rollout-report-v1 JSON path")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_cli_args(argv)
    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    shadow_success = args.shadow_outcome == "success"
    report = evaluate_rollout(
        evidence, shadow_success=shadow_success, judge_llm=None)
    if (report["trajectory"]["status"] == "needs_review"
            and report["trajectory"]["reasons"]
            == ["Judge infrastructure is unavailable"]):
        try:
            import yaml
            import daily_news

            cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
            if os.environ.get("LLM_API_KEY", "").strip():
                cfg.setdefault("llm", {})["api_key"] = os.environ["LLM_API_KEY"].strip()
            judge = daily_news.LLM(resolve_judge_llm_config(cfg))
        except Exception:
            judge = None
        if judge is not None:
            report = evaluate_rollout(
                evidence, shadow_success=shadow_success, judge_llm=judge)
    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return report


if __name__ == "__main__":
    main()
