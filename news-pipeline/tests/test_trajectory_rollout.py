import copy
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import daily_news as dn


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "trajectory_rollout.json"


class FixtureLLM:
    def __init__(self, responses, forbid=()):
        self.responses = responses
        self.forbid = set(forbid)
        self.calls = []

    def json_call(self, system, _user):
        if "连续性门" in system:
            stage = "continuity"
        elif "轨迹生成" in system:
            stage = "generation"
        elif "轨迹审计" in system:
            stage = "audit"
        else:
            stage = "matches"
        assert stage not in self.forbid
        self.calls.append(stage)
        return copy.deepcopy(self.responses[stage])


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_fixture_exposes_rollout_health_for_trusted_polluted_and_legacy_history():
    fixture = load_fixture()
    picked = copy.deepcopy(fixture["picked"])
    health = dn.new_trajectory_health()

    dn.prepare_registry_transaction(
        FixtureLLM(fixture["responses"]), fixture["registry"], picked,
        fixture["date"], {"events": {}, "trajectory": {"enabled": True}},
        items=fixture["items"], trajectory_health=health)

    assert health == {
        "candidate_matches": 1,
        "continuity_accepted": 1,
        "continuity_rejected": 0,
        "filtered_history_rows": 1,
        "generation_fallbacks": 0,
        "audit_fallbacks": 0,
        "final_watch_count": 1,
        "selected_count": 1,
        "final_watch_coverage": 1.0,
    }
    public = dn.event_to_item(picked[0], fixture["items"], "pick")
    assert public["day_count"] == 3
    assert [row["date"] for row in public["history"]] == [
        "2026-07-20", "2026-07-18"]
    assert "item_ref" not in public["history"][0]
    assert public["history"][1]["item_ref"] == "2026-07-18:pick-3"


def test_health_counts_generation_and_audit_fallbacks():
    fixture = load_fixture()
    responses = copy.deepcopy(fixture["responses"])
    responses["generation"] = {"trajectories": []}
    picked = copy.deepcopy(fixture["picked"])
    health = dn.new_trajectory_health()

    dn.prepare_registry_transaction(
        FixtureLLM(responses), fixture["registry"], picked, fixture["date"],
        {"events": {}, "trajectory": {"enabled": True}},
        items=fixture["items"], trajectory_health=health)

    assert health["generation_fallbacks"] == 1
    assert health["audit_fallbacks"] == 0
    assert picked[0]["watch"] == "Base audited watch."

    responses = copy.deepcopy(fixture["responses"])
    responses["audit"]["audits"][0]["fields"]["watch"] = False
    picked = copy.deepcopy(fixture["picked"])
    health = dn.new_trajectory_health()
    dn.prepare_registry_transaction(
        FixtureLLM(responses), fixture["registry"], picked, fixture["date"],
        {"events": {}, "trajectory": {"enabled": True}},
        items=fixture["items"], trajectory_health=health)

    assert health["generation_fallbacks"] == 0
    assert health["audit_fallbacks"] == 1
    assert picked[0]["watch"] == "Base audited watch."


def test_partial_generation_fallback_counts_the_affected_item_once():
    fixture = load_fixture()
    responses = copy.deepcopy(fixture["responses"])
    del responses["generation"]["trajectories"][0]["watch"]
    del responses["audit"]["audits"][0]["fields"]["watch"]
    picked = copy.deepcopy(fixture["picked"])
    health = dn.new_trajectory_health()

    dn.prepare_registry_transaction(
        FixtureLLM(responses), fixture["registry"], picked, fixture["date"],
        {"events": {}, "trajectory": {"enabled": True}},
        items=fixture["items"], trajectory_health=health)

    assert health["generation_fallbacks"] == 1
    assert picked[0]["context"] == "两轮企业采用数据把事件推进到今天。"
    assert picked[0]["watch"] == "Base audited watch."


def test_malformed_continuity_result_counts_rejection_and_all_filtered_rows():
    fixture = load_fixture()
    responses = copy.deepcopy(fixture["responses"])
    responses["continuity"] = {"validations": []}
    health = dn.new_trajectory_health()

    dn.prepare_registry_transaction(
        FixtureLLM(responses), fixture["registry"], copy.deepcopy(fixture["picked"]),
        fixture["date"], {"events": {}, "trajectory": {"enabled": True}},
        items=fixture["items"], trajectory_health=health)

    assert health["continuity_accepted"] == 0
    assert health["continuity_rejected"] == 1
    assert health["filtered_history_rows"] == 3


def test_rollback_switch_skips_generation_and_strips_trajectory_projection():
    fixture = load_fixture()
    picked = copy.deepcopy(fixture["picked"])
    llm = FixtureLLM(fixture["responses"], forbid={"generation", "audit"})
    health = dn.new_trajectory_health()

    dn.prepare_registry_transaction(
        llm, fixture["registry"], picked, fixture["date"],
        {"events": {}, "trajectory": {"enabled": False}},
        items=fixture["items"], trajectory_health=health)

    assert llm.calls == ["matches", "continuity"]
    public = dn.event_to_item(
        picked[0], fixture["items"], "pick", trajectory_enabled=False)
    assert not ({"context", "watch", "trusted_continuation", "day_count", "history"}
                & set(public))
    assert health["final_watch_count"] == 0
    assert health["final_watch_coverage"] == 0.0


def test_rollback_config_propagates_through_daily_output():
    fixture = load_fixture()
    picked = copy.deepcopy(fixture["picked"])
    dn.prepare_registry_transaction(
        FixtureLLM(fixture["responses"], forbid={"generation", "audit"}),
        fixture["registry"], picked, fixture["date"],
        {"events": {}, "trajectory": {"enabled": False}},
        items=fixture["items"])
    temp_dir = Path(tempfile.mkdtemp(prefix="trajectory-output-"))
    old_data_dir = os.environ.get("DATA_DIR")
    try:
        os.environ["DATA_DIR"] = str(temp_dir)
        payload = dn.write_output(
            fixture["date"], "fixture", picked, [], fixture["items"],
            {"events": {}, "trajectory": {"enabled": False}})
        assert payload["trajectory_enabled"] is False
        public = payload["items"][0]
        assert not ({"context", "watch", "trusted_continuation", "day_count", "history"}
                    & set(public))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        if old_data_dir is None:
            os.environ.pop("DATA_DIR", None)
        else:
            os.environ["DATA_DIR"] = old_data_dir


def test_health_log_has_all_rollout_signals():
    fixture = load_fixture()
    messages = []
    temp_dir = Path(tempfile.mkdtemp(prefix="trajectory-health-"))
    old_data_dir = os.environ.get("DATA_DIR")
    old_log = dn.log
    try:
        os.environ["DATA_DIR"] = str(temp_dir)
        dn.log = messages.append
        (temp_dir / "events.json").write_text(
            json.dumps(fixture["registry"], ensure_ascii=False), encoding="utf-8")
        dn.track_events(
            FixtureLLM(fixture["responses"]), copy.deepcopy(fixture["picked"]),
            fixture["date"], {"events": {}, "trajectory": {"enabled": True}},
            items=fixture["items"])
    finally:
        dn.log = old_log
        shutil.rmtree(temp_dir, ignore_errors=True)
        if old_data_dir is None:
            os.environ.pop("DATA_DIR", None)
        else:
            os.environ["DATA_DIR"] = old_data_dir

    line = next(message for message in messages if "轨迹健康" in message)
    for label in ("候选匹配 1", "连续性通过/拒绝 1/0", "过滤历史行 1",
                  "生成回退 0", "审计回退 0", "最终走向 1/1 (100.0%)"):
        assert label in line


TESTS = [
    test_fixture_exposes_rollout_health_for_trusted_polluted_and_legacy_history,
    test_health_counts_generation_and_audit_fallbacks,
    test_partial_generation_fallback_counts_the_affected_item_once,
    test_malformed_continuity_result_counts_rejection_and_all_filtered_rows,
    test_rollback_switch_skips_generation_and_strips_trajectory_projection,
    test_rollback_config_propagates_through_daily_output,
    test_health_log_has_all_rollout_signals,
]


def run_tests():
    results = []
    for test_fn in TESTS:
        try:
            test_fn()
            results.append((test_fn.__name__, True, ""))
        except Exception as exc:
            results.append((test_fn.__name__, False, repr(exc)))
    return results


if __name__ == "__main__":
    failures = []
    for name, passed, detail in run_tests():
        print(("PASS " if passed else "FAIL ") + name
              + (f": {detail}" if detail else ""))
        if not passed:
            failures.append(name)
    raise SystemExit(1 if failures else 0)
