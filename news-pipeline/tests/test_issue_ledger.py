import importlib.util
from pathlib import Path
import json
import yaml


ROOT = Path(__file__).resolve().parents[2]


def ledger():
    path = ROOT / "news-pipeline" / "issue_ledger.py"
    spec = importlib.util.spec_from_file_location("issue_ledger_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def attempt(run_id, run_attempt, *, publication="success", selection="pass",
            trajectory="pass", runtime="a", trajectory_ui="b"):
    return {
        "run_id": str(run_id),
        "run_attempt": int(run_attempt),
        "sha": "0123456789abcdef0123456789abcdef01234567",
        "publication": publication,
        "selection": {"status": selection, "reasons": []},
        "trajectory": {"status": trajectory, "reasons": []},
        "judge": {"pass": 1, "fail": 0, "needs_review": 0, "watch_ratio": 1.0},
        "fingerprints": {
            "runtime": runtime * 64 if runtime else "",
            "trajectory_ui": trajectory_ui * 64 if trajectory_ui else "",
        },
    }


def state(date, attempts):
    return ledger().build_daily_state(date, attempts)


def test_publication_failure_is_permanent_across_same_day_reruns():
    il = ledger()
    failed = attempt(10, 1, publication="failure",
                     selection="needs_review", trajectory="needs_review")
    passed = attempt(10, 2)

    daily = il.build_daily_state("2026-07-22", [failed, passed])

    assert len(daily["attempts"]) == 2
    assert daily["aggregate"] == {
        "publication": "failure", "selection": "fail", "trajectory": "fail"
    }


def test_merging_same_run_attempt_is_idempotent_but_preserves_reruns():
    il = ledger()
    first = attempt(10, 1, selection="needs_review")
    replacement = attempt(10, 1, selection="pass")
    rerun = attempt(10, 2)

    merged = il.merge_attempts([first], replacement)
    merged = il.merge_attempts(merged, replacement)
    merged = il.merge_attempts(merged, rerun)

    assert [(row["run_id"], row["run_attempt"]) for row in merged] == [
        ("10", 1), ("10", 2)
    ]
    assert merged[0]["selection"]["status"] == "pass"


def test_distinct_workflow_run_ids_are_ordered_numerically():
    il = ledger()
    older = attempt(99, 1, selection="fail")
    newer = attempt(100, 1, selection="pass")

    daily = il.build_daily_state("2026-07-22", [newer, older])

    assert [row["run_id"] for row in daily["attempts"]] == ["99", "100"]
    assert daily["aggregate"]["selection"] == "pass"


def test_gate_streaks_follow_independent_fail_and_neutral_semantics():
    il = ledger()
    states = [
        state("2026-07-18", [attempt(1, 1)]),
        state("2026-07-19", [attempt(2, 1, selection="neutral", trajectory="pass")]),
        state("2026-07-20", [attempt(3, 1, selection="fail", trajectory="neutral")]),
        state("2026-07-21", [attempt(4, 1, selection="pass", trajectory="fail")]),
        state("2026-07-22", [attempt(5, 1, selection="needs_review",
                                      trajectory="needs_review")]),
    ]

    streaks = il.compute_streaks(states)

    assert streaks == {"selection": 1, "trajectory": 0}


def test_publication_failure_resets_both_streaks():
    il = ledger()
    states = [
        state("2026-07-20", [attempt(1, 1)]),
        state("2026-07-21", [attempt(2, 1)]),
        state("2026-07-22", [attempt(3, 1, publication="failure")]),
    ]

    assert il.compute_streaks(states) == {"selection": 0, "trajectory": 0}


def test_runtime_fingerprint_change_resets_both_before_current_evaluation():
    il = ledger()
    states = [
        state("2026-07-21", [attempt(1, 1, runtime="a", trajectory_ui="b")]),
        state("2026-07-22", [attempt(2, 1, runtime="c", trajectory_ui="b")]),
    ]

    assert il.compute_streaks(states) == {"selection": 1, "trajectory": 1}


def test_trajectory_ui_fingerprint_change_resets_only_trajectory():
    il = ledger()
    states = [
        state("2026-07-21", [attempt(1, 1, runtime="a", trajectory_ui="b")]),
        state("2026-07-22", [attempt(2, 1, runtime="a", trajectory_ui="c")]),
    ]

    assert il.compute_streaks(states) == {"selection": 2, "trajectory": 1}


def test_unrelated_fingerprint_fields_do_not_reset_streaks():
    il = ledger()
    prior = state("2026-07-21", [attempt(1, 1)])
    current = state("2026-07-22", [attempt(2, 1)])
    prior["fingerprints"]["articles"] = "x" * 64
    current["fingerprints"]["articles"] = "y" * 64

    assert il.compute_streaks([prior, current]) == {
        "selection": 2, "trajectory": 2
    }


def bot_comment(comment_id, daily_state, *, login="github-actions[bot]",
                user_type="Bot"):
    il = ledger()
    return {
        "id": comment_id,
        "user": {"login": login, "type": user_type},
        "body": il.render_comment(daily_state),
    }


def test_daily_comment_selection_ignores_untrusted_and_is_stable():
    il = ledger()
    daily = state("2026-07-22", [attempt(10, 1)])
    comments = [
        bot_comment(1, daily, login="attacker", user_type="User"),
        bot_comment(99, daily),
        bot_comment(42, daily),
        {"id": 2, "user": {"login": "github-actions[bot]", "type": "Bot"},
         "body": il.marker_for_date("2026-07-22") + "\n<!-- malformed -->"},
    ]

    selected = il.find_daily_comment(comments, "2026-07-22")

    assert selected["id"] == 2
    assert il.parse_machine_state(comments[0]) is None
    assert il.parse_machine_state(selected) is None
    assert il.parse_machine_state(comments[2])["date"] == "2026-07-22"


def test_rendered_comment_has_stable_marker_compact_state_and_human_summary():
    il = ledger()
    daily = state("2026-07-22", [attempt(10, 2)])
    daily["streaks"] = {"selection": 7, "trajectory": 5}

    body = il.render_comment(daily)

    assert body.count(il.marker_for_date("2026-07-22")) == 1
    assert "待人工最终确认" in body
    assert "2026-07-22" in body
    assert "10 / attempt 2" in body
    assert "0123456" in body
    assert "selection: 7" in body
    assert il.parse_machine_state({
        "user": {"login": "github-actions[bot]", "type": "Bot"}, "body": body,
    }) == daily


def test_attempt_projection_does_not_copy_evidence_or_credentials():
    il = ledger()
    report = {
        "date": "2026-07-22",
        "selection": {
            "status": "pass",
            "reasons": ["ok TOKEN=top-secret ghp_ABC123secret"],
        },
        "trajectory": {
            "status": "needs_review",
            "reasons": ["judge at https://user:top-secret@example.test/v1 failed"],
            "watch_ratio": 0.75,
            "verdicts": [
                {"decision": "pass", "reason": "source body must not be copied"},
                {"decision": "needs_review", "reason": "full article text"},
            ],
        },
        "fingerprints": {"runtime": "a" * 64, "trajectory_ui": "b" * 64},
        "review_cases": [{"article": "private source body"}],
        "token": "top-secret",
    }

    projected = il.build_attempt(
        report=report, publication="success", publication_reason="",
        run_id="10", run_attempt=2,
        sha="0123456789abcdef0123456789abcdef01234567")
    body = json.dumps(projected, ensure_ascii=False)

    assert projected["judge"] == {
        "pass": 1, "fail": 0, "needs_review": 1, "watch_ratio": 0.75
    }
    assert "top-secret" not in body
    assert "ghp_ABC123secret" not in body
    assert "private source body" not in body
    assert "full article text" not in body


class FakeClient:
    def __init__(self, *, issue_state="open", comments=None):
        self.issue_state = issue_state
        self.comments = list(comments or [])
        self.calls = []

    def get_issue(self, issue_number):
        self.calls.append(("get_issue", issue_number))
        return {"number": issue_number, "state": self.issue_state}

    def list_comments(self, issue_number):
        self.calls.append(("list_comments", issue_number))
        return list(self.comments)

    def create_comment(self, issue_number, body):
        self.calls.append(("create_comment", issue_number, body))
        return {"id": 500, "body": body}

    def update_comment(self, comment_id, body):
        self.calls.append(("update_comment", comment_id, body))
        return {"id": comment_id, "body": body}


def test_closed_issue_is_clean_no_op_before_comment_access():
    il = ledger()
    client = FakeClient(issue_state="closed")

    result = il.sync_issue(
        client, issue_number=15, date="2026-07-22", incoming=attempt(10, 1))

    assert result == {"status": "closed", "comment_id": None}
    assert client.calls == [("get_issue", 15)]


def test_sync_updates_same_daily_comment_idempotently():
    il = ledger()
    existing = state("2026-07-22", [attempt(10, 1, selection="needs_review")])
    client = FakeClient(comments=[bot_comment(88, existing)])

    result = il.sync_issue(
        client, issue_number=15, date="2026-07-22", incoming=attempt(10, 1))

    write_calls = [call for call in client.calls
                   if call[0] in {"create_comment", "update_comment"}]
    assert result == {"status": "updated", "comment_id": 88}
    assert len(write_calls) == 1
    assert write_calls[0][0:2] == ("update_comment", 88)
    parsed = il.parse_machine_state({
        "user": {"login": "github-actions[bot]", "type": "Bot"},
        "body": write_calls[0][2],
    })
    assert len(parsed["attempts"]) == 1
    assert parsed["attempts"][0]["selection"]["status"] == "pass"


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_rest_boundary_uses_bearer_token_and_expected_issue_endpoints():
    il = ledger()
    requests = []
    responses = iter([
        {"number": 15, "state": "open"},
        [],
        {"id": 12},
        {"id": 12},
    ])

    def opener(request, timeout):
        requests.append((request, timeout))
        return FakeResponse(next(responses))

    client = il.GitHubClient("owner/repo", "test-token", opener=opener)
    assert client.get_issue(15)["state"] == "open"
    assert client.list_comments(15) == []
    client.create_comment(15, "body")
    client.update_comment(12, "updated")

    assert [request.get_method() for request, _ in requests] == [
        "GET", "GET", "POST", "PATCH"
    ]
    assert [request.full_url for request, _ in requests] == [
        "https://api.github.com/repos/owner/repo/issues/15",
        "https://api.github.com/repos/owner/repo/issues/15/comments?per_page=100&page=1",
        "https://api.github.com/repos/owner/repo/issues/15/comments",
        "https://api.github.com/repos/owner/repo/issues/comments/12",
    ]
    assert all(request.get_header("Authorization") == "Bearer test-token"
               for request, _ in requests)


def test_check_open_cli_writes_closed_output_without_comment_calls(tmp_path):
    il = ledger()
    output = tmp_path / "github-output"
    client = FakeClient(issue_state="closed")

    result = il.main(
        ["check-open", "--issue", "15"],
        environ={
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_TOKEN": "test-token",
            "GITHUB_OUTPUT": str(output),
        },
        client_factory=lambda _repo, _token: client,
    )

    assert result == {"status": "closed", "open": False}
    assert output.read_text(encoding="utf-8") == "open=false\n"
    assert client.calls == [("get_issue", 15)]


def workflow():
    return yaml.safe_load(
        (ROOT / ".github" / "workflows" / "daily-news.yml").read_text(
            encoding="utf-8"))


def step_named(job, name):
    return next(step for step in job["steps"] if step.get("name") == name)


def test_workflow_permissions_are_minimal_and_publication_stage_is_unchanged():
    jobs = workflow()["jobs"]

    assert jobs["generate"]["permissions"] == {"contents": "write"}
    assert jobs["shadow"]["permissions"] == {"contents": "read"}
    assert jobs["rollout-review"]["permissions"] == {
        "contents": "read", "issues": "write"
    }
    commit = step_named(jobs["generate"], "Commit and push")["run"]
    assert "git add source/news/data" in commit
    assert "git add ." not in commit
    assert "git add -A" not in commit


def test_workflow_artifacts_are_temp_scoped_short_lived_and_sha_pinned():
    jobs = workflow()["jobs"]
    generate_step = step_named(jobs["generate"], "Generate daily briefing")
    assert generate_step["env"]["ROLLOUT_EVIDENCE_PATH"].startswith(
        "${{ runner.temp }}/")
    evidence_upload = step_named(jobs["generate"], "Upload rollout evidence")
    shadow_upload = step_named(jobs["shadow"], "Upload shadow status")
    expected_upload = (
        "actions/upload-artifact@"
        "ea165f8d65b6e75b540449e92b4886f43607fa02")
    assert evidence_upload["uses"] == expected_upload
    assert shadow_upload["uses"] == expected_upload
    assert 1 <= evidence_upload["with"]["retention-days"] <= 7
    assert 1 <= shadow_upload["with"]["retention-days"] <= 7
    assert "source/news/data" not in evidence_upload["with"]["path"]

    downloads = [step for step in jobs["rollout-review"]["steps"]
                 if str(step.get("uses", "")).startswith("actions/download-artifact@")]
    assert len(downloads) == 2
    assert all(step["uses"] == (
        "actions/download-artifact@"
        "d3f86a106a0bac45b974a628896c90dbdf5c8093") for step in downloads)


def test_shadow_failure_is_observed_without_failing_the_job():
    jobs = workflow()["jobs"]
    shadow = jobs["shadow"]
    run_step = step_named(shadow, "Run objectivity shadow")
    status_step = step_named(shadow, "Record shadow status")

    assert run_step["id"] == "shadow_run"
    assert run_step["continue-on-error"] is True
    assert status_step["if"] == "${{ always() }}"
    assert status_step["env"]["SHADOW_OUTCOME"] == (
        "${{ steps.shadow_run.outcome }}")
    assert shadow["env"]["SHADOW_STATUS_PATH"].startswith("/tmp/")
    assert "SHADOW_STATUS_PATH" not in jobs["generate"]["env"]


def test_review_checks_open_issue_before_dependencies_or_judge():
    review = workflow()["jobs"]["rollout-review"]
    names = [step.get("name") for step in review["steps"]]
    issue_index = names.index("Check rollout issue")
    install_index = names.index("Install review dependencies")
    judge_index = names.index("Evaluate rollout")

    assert review["needs"] == ["generate", "shadow"]
    assert review["if"] == "${{ always() }}"
    assert issue_index < install_index < judge_index
    assert step_named(review, "Check rollout issue")["id"] == "issue"
    assert "steps.issue.outputs.open == 'true'" in step_named(
        review, "Install review dependencies")["if"]
    judge_if = step_named(review, "Evaluate rollout")["if"]
    assert "steps.issue.outputs.open == 'true'" in judge_if
    assert "steps.prepare.outputs.judge_ready == 'true'" in judge_if


def test_generate_failure_or_missing_evidence_skips_judge_but_syncs_ledger():
    review = workflow()["jobs"]["rollout-review"]
    prepare = step_named(review, "Prepare rollout review")
    judge = step_named(review, "Evaluate rollout")
    sync = step_named(review, "Update rollout issue ledger")

    assert prepare["env"]["GENERATE_RESULT"] == "${{ needs.generate.result }}"
    assert "judge_ready" in prepare["run"]
    assert "steps.prepare.outputs.judge_ready == 'true'" in judge["if"]
    assert "steps.issue.outputs.open == 'true'" in sync["if"]
    assert "--publication" in sync["run"]
    assert "--report" in sync["run"]


def test_review_infrastructure_failures_warn_and_still_reach_ledger():
    review = workflow()["jobs"]["rollout-review"]
    issue = step_named(review, "Check rollout issue")
    setup = next(step for step in review["steps"]
                 if str(step.get("uses", "")).startswith("actions/setup-python@"))
    install = step_named(review, "Install review dependencies")
    sync = step_named(review, "Update rollout issue ledger")
    warning = step_named(review, "Warn on review failure")

    assert issue["continue-on-error"] is True
    assert setup["continue-on-error"] is True
    assert install["continue-on-error"] is True
    assert "always()" in sync["if"]
    assert "always()" in warning["if"]
    for step_id in ("issue", "setup", "install", "judge", "ledger"):
        assert f"steps.{step_id}.outcome == 'failure'" in warning["if"]


def test_needs_review_report_emits_a_workflow_warning():
    judge = step_named(
        workflow()["jobs"]["rollout-review"], "Evaluate rollout")

    assert "needs_review" in judge["run"]
    assert "::warning::" in judge["run"]
