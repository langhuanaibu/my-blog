"""Issue #15 rollout ledger with pure aggregation and a thin REST boundary."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import urllib.request
from pathlib import Path


GATE_STATUSES = {"pass", "fail", "neutral", "needs_review"}
TRUSTED_BOT = "github-actions[bot]"
MARKER_TEMPLATE = "<!-- daily-news-rollout:{date} -->"
STATE_PREFIX = "<!-- daily-news-rollout-state:"
STATE_SUFFIX = " -->"
_STATE_RE = re.compile(r"<!-- daily-news-rollout-state:(\{.*\}) -->")
_SECRET_RE = re.compile(
    r"(?i)\b(api[_-]?key|token|password|secret)\s*[=:]\s*[^\s,;]+")
_TOKEN_VALUE_RE = re.compile(
    r"(?i)\b(?:gh[pousr]_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]{8,}|bearer\s+\S+)")
_URL_RE = re.compile(r"https?://[^\s]+", re.I)
_SHA256_RE = re.compile(r"[0-9a-f]{64}")


def _attempt_key(attempt):
    run_id = str(attempt.get("run_id") or "")
    ordered_id = (0, int(run_id)) if run_id.isdigit() else (1, run_id)
    return ordered_id, int(attempt.get("run_attempt") or 0)


def merge_attempts(existing, incoming):
    """Upsert one workflow attempt without collapsing distinct reruns."""
    merged = [copy.deepcopy(row) for row in existing]
    key = _attempt_key(incoming)
    for index, row in enumerate(merged):
        if _attempt_key(row) == key:
            merged[index] = copy.deepcopy(incoming)
            break
    else:
        merged.append(copy.deepcopy(incoming))
    return sorted(merged, key=_attempt_key)


def _gate_status(attempt, gate):
    value = attempt.get(gate)
    status = value.get("status") if isinstance(value, dict) else None
    return status if status in GATE_STATUSES else "needs_review"


def _latest_fingerprints(attempts):
    result = {"runtime": "", "trajectory_ui": ""}
    for attempt in attempts:
        fingerprints = attempt.get("fingerprints")
        if not isinstance(fingerprints, dict):
            continue
        for name in result:
            value = fingerprints.get(name)
            if isinstance(value, str) and value:
                result[name] = value
    return result


def build_daily_state(date, attempts):
    """Aggregate all attempts for one Beijing date."""
    ordered = sorted((copy.deepcopy(row) for row in attempts), key=_attempt_key)
    latest = ordered[-1] if ordered else {}
    publication_failed = any(
        row.get("publication") == "failure" for row in ordered)
    aggregate = {
        "publication": "failure" if publication_failed else "success",
        "selection": "fail" if publication_failed else _gate_status(latest, "selection"),
        "trajectory": "fail" if publication_failed else _gate_status(latest, "trajectory"),
    }
    return {
        "version": "issue-ledger-v1",
        "date": str(date),
        "attempts": ordered,
        "aggregate": aggregate,
        "fingerprints": _latest_fingerprints(ordered),
        "streaks": {"selection": 0, "trajectory": 0},
    }


def _apply_gate(streak, status):
    if status == "pass":
        return streak + 1
    if status == "fail":
        return 0
    return streak


def compute_streaks(states):
    """Compute independent gate streaks over chronological daily states."""
    streaks = {"selection": 0, "trajectory": 0}
    previous = {"runtime": "", "trajectory_ui": ""}
    for state in sorted(states, key=lambda row: str(row.get("date") or "")):
        fingerprints = state.get("fingerprints")
        fingerprints = fingerprints if isinstance(fingerprints, dict) else {}
        runtime = fingerprints.get("runtime")
        trajectory_ui = fingerprints.get("trajectory_ui")
        if previous["runtime"] and runtime and runtime != previous["runtime"]:
            streaks = {"selection": 0, "trajectory": 0}
        elif (previous["trajectory_ui"] and trajectory_ui
              and trajectory_ui != previous["trajectory_ui"]):
            streaks["trajectory"] = 0

        aggregate = state.get("aggregate")
        aggregate = aggregate if isinstance(aggregate, dict) else {}
        if aggregate.get("publication") == "failure":
            streaks = {"selection": 0, "trajectory": 0}
        else:
            for gate in ("selection", "trajectory"):
                streaks[gate] = _apply_gate(streaks[gate], aggregate.get(gate))

        if runtime:
            previous["runtime"] = runtime
        if trajectory_ui:
            previous["trajectory_ui"] = trajectory_ui
    return streaks


def marker_for_date(date):
    return MARKER_TEMPLATE.format(date=str(date))


def _sanitize_text(value, limit=240):
    text = " ".join(str(value or "").split())
    text = _SECRET_RE.sub(lambda match: f"{match.group(1)}=[redacted]", text)
    text = _TOKEN_VALUE_RE.sub("[redacted]", text)
    text = _URL_RE.sub("[url]", text)
    text = text.replace("--", "—")
    return text[:limit]


def _project_reasons(value):
    if not isinstance(value, list):
        return []
    return [reason for reason in (_sanitize_text(row) for row in value[:5]) if reason]


def _project_gate(report, gate):
    source = report.get(gate) if isinstance(report, dict) else None
    source = source if isinstance(source, dict) else {}
    status = source.get("status")
    return {
        "status": status if status in GATE_STATUSES else "needs_review",
        "reasons": _project_reasons(source.get("reasons")),
    }


def _project_fingerprints(report):
    source = report.get("fingerprints") if isinstance(report, dict) else None
    source = source if isinstance(source, dict) else {}
    return {
        name: value if isinstance(value := source.get(name), str)
        and _SHA256_RE.fullmatch(value) else ""
        for name in ("runtime", "trajectory_ui")
    }


def _judge_summary(report):
    trajectory = report.get("trajectory") if isinstance(report, dict) else None
    trajectory = trajectory if isinstance(trajectory, dict) else {}
    counts = {"pass": 0, "fail": 0, "needs_review": 0}
    verdicts = trajectory.get("verdicts")
    if isinstance(verdicts, list):
        for verdict in verdicts:
            decision = verdict.get("decision") if isinstance(verdict, dict) else None
            if decision in counts:
                counts[decision] += 1
    ratio = trajectory.get("watch_ratio")
    counts["watch_ratio"] = (
        round(float(ratio), 4)
        if isinstance(ratio, (int, float)) and not isinstance(ratio, bool)
        and 0 <= float(ratio) <= 1 else None)
    return counts


def build_attempt(*, report, publication, publication_reason, run_id,
                  run_attempt, sha):
    """Project a report into the compact, non-sensitive ledger schema."""
    publication = "success" if publication == "success" else "failure"
    selection = _project_gate(report, "selection")
    trajectory = _project_gate(report, "trajectory")
    reason = _sanitize_text(publication_reason)
    if publication == "failure":
        selection = {"status": "fail", "reasons": [reason or "publication failed"]}
        trajectory = {"status": "fail", "reasons": [reason or "publication failed"]}
    elif not isinstance(report, dict):
        selection = trajectory = {
            "status": "needs_review", "reasons": ["rollout report unavailable"]}
    return {
        "run_id": str(run_id),
        "run_attempt": int(run_attempt),
        "sha": str(sha)[:40],
        "publication": publication,
        "selection": selection,
        "trajectory": trajectory,
        "judge": _judge_summary(report),
        "fingerprints": _project_fingerprints(report),
    }


def _trusted_bot_comment(comment):
    user = comment.get("user") if isinstance(comment, dict) else None
    return (isinstance(user, dict) and user.get("login") == TRUSTED_BOT
            and user.get("type") == "Bot")


def _valid_machine_state(state):
    return (isinstance(state, dict)
            and state.get("version") == "issue-ledger-v1"
            and isinstance(state.get("date"), str)
            and isinstance(state.get("attempts"), list)
            and isinstance(state.get("aggregate"), dict)
            and isinstance(state.get("fingerprints"), dict)
            and isinstance(state.get("streaks"), dict))


def parse_machine_state(comment):
    """Parse only comments authored by the workflow's trusted bot identity."""
    if not _trusted_bot_comment(comment):
        return None
    body = comment.get("body")
    if not isinstance(body, str):
        return None
    match = _STATE_RE.search(body)
    if not match:
        return None
    try:
        state = json.loads(match.group(1))
    except (TypeError, ValueError):
        return None
    if (not _valid_machine_state(state)
            or marker_for_date(state["date"]) not in body):
        return None
    return state


def find_daily_comment(comments, date):
    marker = marker_for_date(date)
    candidates = [
        comment for comment in comments
        if _trusted_bot_comment(comment)
        and marker in str(comment.get("body") or "")
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda row: int(row.get("id") or 0))


def _gate_reasons(state, gate):
    attempts = state.get("attempts") or []
    if (state.get("aggregate", {}).get("publication") == "failure"
            and any(row.get("publication") == "failure" for row in attempts)):
        return ["at least one publication attempt failed"]
    latest = attempts[-1] if attempts else {}
    projected = latest.get(gate) if isinstance(latest, dict) else None
    return projected.get("reasons") if isinstance(projected, dict) else []


def render_comment(state):
    """Render one readable daily comment plus compact hidden machine state."""
    machine = json.dumps(state, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"))
    attempts = state.get("attempts") or []
    latest = attempts[-1] if attempts else {}
    aggregate = state.get("aggregate") or {}
    streaks = state.get("streaks") or {}
    fingerprints = state.get("fingerprints") or {}
    judge = latest.get("judge") if isinstance(latest, dict) else {}
    judge = judge if isinstance(judge, dict) else {}

    def reasons_for(gate):
        reasons = _gate_reasons(state, gate)
        return "; ".join(reasons) if reasons else "none"

    lines = [
        marker_for_date(state.get("date", "")),
        f"{STATE_PREFIX}{machine}{STATE_SUFFIX}",
        f"## 日报验收 · {state.get('date', '')}",
        "",
        (f"- Run: {latest.get('run_id', '')} / attempt "
         f"{latest.get('run_attempt', '')} · `{str(latest.get('sha', ''))[:7]}`"),
        f"- Publication: **{aggregate.get('publication', 'needs_review')}**",
        (f"- Selection: **{aggregate.get('selection', 'needs_review')}** — "
         f"{reasons_for('selection')}"),
        (f"- Trajectory: **{aggregate.get('trajectory', 'needs_review')}** — "
         f"{reasons_for('trajectory')}"),
        (f"- Judge: pass={judge.get('pass', 0)}, fail={judge.get('fail', 0)}, "
         f"needs_review={judge.get('needs_review', 0)}, "
         f"watch_ratio={judge.get('watch_ratio') if judge.get('watch_ratio') is not None else 'n/a'}"),
        (f"- Fingerprints: runtime=`{str(fingerprints.get('runtime') or '')[:12]}`, "
         f"trajectory_ui=`{str(fingerprints.get('trajectory_ui') or '')[:12]}`"),
        (f"- Current streaks: selection: {int(streaks.get('selection') or 0)}, "
         f"trajectory: {int(streaks.get('trajectory') or 0)}"),
    ]
    if (int(streaks.get("selection") or 0) >= 7
            and int(streaks.get("trajectory") or 0) >= 5):
        lines.append("- 状态：待人工最终确认")
    return "\n".join(lines) + "\n"


def sync_issue(client, *, issue_number, date, incoming):
    """Idempotently create or update the trusted comment for one date."""
    issue = client.get_issue(issue_number)
    if str(issue.get("state") or "").lower() != "open":
        return {"status": "closed", "comment_id": None}

    comments = client.list_comments(issue_number)
    current_comment = find_daily_comment(comments, date)
    current_state = (parse_machine_state(current_comment)
                     if current_comment is not None else None)
    attempts = merge_attempts(
        current_state.get("attempts", []) if current_state else [], incoming)
    updated = build_daily_state(date, attempts)

    states_by_date = {}
    for comment in sorted(comments, key=lambda row: int(row.get("id") or 0)):
        parsed = parse_machine_state(comment)
        if parsed is not None and parsed["date"] not in states_by_date:
            states_by_date[parsed["date"]] = parsed
    states_by_date[str(date)] = updated
    updated["streaks"] = compute_streaks(states_by_date.values())
    body = render_comment(updated)

    if current_comment is None:
        response = client.create_comment(issue_number, body)
        return {"status": "created", "comment_id": response.get("id")}
    response = client.update_comment(current_comment["id"], body)
    return {"status": "updated", "comment_id": response.get("id")}


class GitHubClient:
    """Small GitHub Issues REST client; aggregation remains independently testable."""

    def __init__(self, repository, token, *, opener=None):
        if not re.fullmatch(r"[^/\s]+/[^/\s]+", str(repository or "")):
            raise ValueError("GITHUB_REPOSITORY must be owner/repo")
        if not str(token or "").strip():
            raise ValueError("GITHUB_TOKEN is required")
        self.base_url = f"https://api.github.com/repos/{repository}"
        self.token = str(token).strip()
        self.opener = opener or urllib.request.urlopen

    def _request(self, method, endpoint, payload=None):
        data = None
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/{endpoint}", data=data, method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "daily-news-rollout-ledger",
                "X-GitHub-Api-Version": "2022-11-28",
            })
        with self.opener(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_issue(self, issue_number):
        return self._request("GET", f"issues/{int(issue_number)}")

    def list_comments(self, issue_number):
        comments = []
        page = 1
        while True:
            rows = self._request(
                "GET", f"issues/{int(issue_number)}/comments?per_page=100&page={page}")
            if not isinstance(rows, list):
                raise ValueError("GitHub comments response must be a list")
            comments.extend(rows)
            if len(rows) < 100:
                return comments
            page += 1

    def create_comment(self, issue_number, body):
        return self._request(
            "POST", f"issues/{int(issue_number)}/comments", {"body": body})

    def update_comment(self, comment_id, body):
        return self._request(
            "PATCH", f"issues/comments/{int(comment_id)}", {"body": body})


def parse_cli_args(argv=None):
    parser = argparse.ArgumentParser(description="Update the rollout Issue ledger")
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check-open")
    check.add_argument("--issue", type=int, default=15)
    sync = subparsers.add_parser("sync")
    sync.add_argument("--issue", type=int, default=15)
    sync.add_argument("--date", required=True)
    sync.add_argument("--publication", required=True, choices=("success", "failure"))
    sync.add_argument("--publication-reason", default="")
    sync.add_argument("--report", default="")
    sync.add_argument("--run-id", required=True)
    sync.add_argument("--run-attempt", required=True, type=int)
    sync.add_argument("--sha", required=True)
    return parser.parse_args(argv)


def _write_output(environ, name, value):
    target = str(environ.get("GITHUB_OUTPUT") or "").strip()
    if target:
        with Path(target).open("a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


def _load_report(path):
    if not str(path or "").strip():
        return None
    target = Path(path)
    if not target.is_file():
        return None
    try:
        report = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return None
    return report if isinstance(report, dict) else None


def main(argv=None, *, environ=None, client_factory=GitHubClient):
    environ = os.environ if environ is None else environ
    args = parse_cli_args(argv)
    client = client_factory(
        environ.get("GITHUB_REPOSITORY", ""), environ.get("GITHUB_TOKEN", ""))
    if args.command == "check-open":
        issue = client.get_issue(args.issue)
        is_open = str(issue.get("state") or "").lower() == "open"
        _write_output(environ, "open", str(is_open).lower())
        result = {"status": "open" if is_open else "closed", "open": is_open}
    else:
        incoming = build_attempt(
            report=_load_report(args.report), publication=args.publication,
            publication_reason=args.publication_reason, run_id=args.run_id,
            run_attempt=args.run_attempt, sha=args.sha)
        result = sync_issue(
            client, issue_number=args.issue, date=args.date, incoming=incoming)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return result


if __name__ == "__main__":
    main()
