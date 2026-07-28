import importlib.util
import sys
import types
from pathlib import Path

import pytest
import requests
import yaml


PIPELINE_DIR = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "daily_news_llm_protocol_test", PIPELINE_DIR / "daily_news.py")
dn = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = dn
spec.loader.exec_module(dn)


def test_repository_defaults_to_deepseek_and_keeps_stepfun_available():
    config = yaml.safe_load(
        (PIPELINE_DIR / "config.yaml").read_text(encoding="utf-8"))

    assert config["llm"]["active_provider"] == "deepseek"
    assert config["llm"]["providers"]["deepseek"]["protocol"] == "openai"
    assert config["llm"]["providers"]["deepseek"]["extra_body"] == {
        "thinking": {"type": "disabled"},
    }
    assert config["llm"]["providers"]["stepfun"]["protocol"] == "anthropic"


def provider_config(active="stepfun"):
    return {
        "llm": {
            "active_provider": active,
            "providers": {
                "stepfun": {
                    "protocol": "anthropic",
                    "base_url": "https://api.stepfun.com/v1/",
                    "api_key_env": "STEPFUN_API_KEY",
                    "model": "step-explore",
                    "max_tokens": 16384,
                    "max_retries": 3,
                    "request_timeout": [10, 180],
                    "price_usd_per_mtok": {
                        "input_miss": 0,
                        "input_hit": 0,
                        "output": 0,
                    },
                },
                "deepseek": {
                    "protocol": "openai",
                    "base_url": "https://api.deepseek.com/v1",
                    "api_key_env": "DEEPSEEK_API_KEY",
                    "model": "deepseek-v4-flash",
                    "temperature": 0.3,
                    "max_retries": 3,
                    "extra_body": {"thinking": {"type": "disabled"}},
                    "price_usd_per_mtok": {
                        "input_miss": 0.14,
                        "input_hit": 0.0028,
                        "output": 0.28,
                    },
                },
            },
        },
        "audit_llm": {"provider": "", "model": ""},
        "prefilter": {"enabled": True, "provider": "", "model": ""},
    }


def test_named_provider_resolves_its_secret_and_role_inheritance():
    cfg = provider_config()
    environ = {
        "STEPFUN_API_KEY": "step-secret",
        "DEEPSEEK_API_KEY": "deepseek-secret",
    }

    primary = dn.resolve_llm_config(cfg, "llm", environ=environ)
    audit = dn.resolve_llm_config(cfg, "audit_llm", environ=environ)
    prefilter = dn.resolve_llm_config(cfg, "prefilter", environ=environ)

    assert primary["provider"] == "stepfun"
    assert primary["api_key"] == "step-secret"
    assert audit["provider"] == "stepfun"
    assert audit["api_key"] == "step-secret"
    assert prefilter["provider"] == "stepfun"
    assert prefilter["api_key"] == "step-secret"
    assert "providers" not in primary

    cfg["llm"]["active_provider"] = "deepseek"
    fallback = dn.resolve_llm_config(cfg, "llm", environ=environ)
    assert fallback["provider"] == "deepseek"
    assert fallback["api_key"] == "deepseek-secret"


def test_named_provider_rejects_missing_or_unknown_active_provider():
    cfg = provider_config()
    cfg["llm"]["active_provider"] = ""
    with pytest.raises(ValueError, match="active_provider"):
        dn.resolve_llm_config(cfg, environ={})

    cfg["llm"]["active_provider"] = "missing"
    with pytest.raises(ValueError, match="missing"):
        dn.resolve_llm_config(cfg, environ={})


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._payload


def anthropic_payload(text='{"ok":true}', *, stop_reason="end_turn", usage=None):
    return {
        "content": [{"type": "text", "text": text}],
        "stop_reason": stop_reason,
        "usage": usage or {"input_tokens": 20, "output_tokens": 12},
    }


def test_anthropic_json_call_uses_stepfun_contract_and_normalizes_usage(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(payload=anthropic_payload(
            usage={
                "input_tokens": 20,
                "cache_read_input_tokens": 5,
                "cache_creation_input_tokens": 3,
                "output_tokens": 12,
            }))

    monkeypatch.setattr(dn.requests, "post", fake_post)
    cfg = dn.resolve_llm_config(
        provider_config(), environ={"STEPFUN_API_KEY": "secret"})
    llm = dn.LLM(cfg)

    assert llm.json_call("system prompt", "user prompt") == {"ok": True}
    assert len(calls) == 1
    url, kwargs = calls[0]
    assert url == "https://api.stepfun.com/v1/messages"
    assert kwargs["timeout"] == (10, 180)
    assert kwargs["headers"] == {
        "x-api-key": "secret",
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    assert kwargs["json"] == {
        "model": "step-explore",
        "max_tokens": 16384,
        "system": "system prompt",
        "messages": [{"role": "user", "content": "user prompt"}],
    }
    assert "temperature" not in kwargs["json"]
    assert "thinking" not in kwargs["json"]
    assert "extra_body" not in kwargs["json"]
    assert llm.stage_usage["OTHER"] == {
        "calls": 1,
        "input": 28,
        "input_cached": 5,
        "output": 12,
    }


def test_anthropic_retries_retryable_status_with_retry_after(monkeypatch):
    responses = [
        FakeResponse(429, text="rate limited", headers={"retry-after": "7"}),
        FakeResponse(payload=anthropic_payload()),
    ]
    sleeps = []
    monkeypatch.setattr(dn.requests, "post", lambda *a, **k: responses.pop(0))
    monkeypatch.setattr(dn.time, "sleep", sleeps.append)
    llm = dn.LLM(dn.resolve_llm_config(
        provider_config(), environ={"STEPFUN_API_KEY": "secret"}))

    assert llm.json_call("system", "user") == {"ok": True}
    assert sleeps == [7.0]


def test_json_parse_failure_is_metered_but_not_retried(monkeypatch):
    responses = [FakeResponse(payload=anthropic_payload("not json"))]
    sleeps = []
    monkeypatch.setattr(dn.requests, "post", lambda *a, **k: responses.pop(0))
    monkeypatch.setattr(dn.time, "sleep", sleeps.append)
    llm = dn.LLM(dn.resolve_llm_config(
        provider_config(), environ={"STEPFUN_API_KEY": "secret"}))

    with pytest.raises(RuntimeError, match="no JSON"):
        llm.json_call("system", "user")
    assert sleeps == []
    assert llm.stage_usage["OTHER"]["calls"] == 1


@pytest.mark.parametrize("status", [400, 401, 402, 404, 451])
def test_anthropic_does_not_retry_terminal_http_status(monkeypatch, status):
    calls = []
    sleeps = []

    def fake_post(*args, **kwargs):
        calls.append(1)
        return FakeResponse(status, text="terminal")

    monkeypatch.setattr(dn.requests, "post", fake_post)
    monkeypatch.setattr(dn.time, "sleep", sleeps.append)
    llm = dn.LLM(dn.resolve_llm_config(
        provider_config(), environ={"STEPFUN_API_KEY": "secret"}))

    with pytest.raises(RuntimeError, match=str(status)):
        llm.json_call("system", "user")
    assert len(calls) == 1
    assert sleeps == []


def test_anthropic_timeout_and_truncation_share_attempt_budget_and_record_usage(
        monkeypatch):
    responses = [
        requests.ReadTimeout("slow"),
        FakeResponse(payload=anthropic_payload(
            "incomplete", stop_reason="max_tokens",
            usage={"input_tokens": 11, "output_tokens": 16384})),
        FakeResponse(payload=anthropic_payload()),
    ]
    sleeps = []

    def fake_post(*args, **kwargs):
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(dn.requests, "post", fake_post)
    monkeypatch.setattr(dn.time, "sleep", sleeps.append)
    llm = dn.LLM(dn.resolve_llm_config(
        provider_config(), environ={"STEPFUN_API_KEY": "secret"}))

    assert llm.json_call("system", "user") == {"ok": True}
    assert sleeps == [1, 2]
    assert llm.stage_usage["OTHER"]["calls"] == 2
    assert llm.stage_usage["OTHER"]["output"] == 16396


@pytest.mark.parametrize("payload", [
    {"stop_reason": "end_turn", "usage": {"input_tokens": 2, "output_tokens": 1}},
    anthropic_payload(""),
])
def test_anthropic_does_not_retry_malformed_success_response(monkeypatch, payload):
    calls = []
    sleeps = []

    def fake_post(*args, **kwargs):
        calls.append(1)
        return FakeResponse(payload=payload)

    monkeypatch.setattr(dn.requests, "post", fake_post)
    monkeypatch.setattr(dn.time, "sleep", sleeps.append)
    llm = dn.LLM(dn.resolve_llm_config(
        provider_config(), environ={"STEPFUN_API_KEY": "secret"}))

    with pytest.raises(RuntimeError):
        llm.json_call("system", "user")
    assert len(calls) == 1
    assert sleeps == []


def test_unexpected_internal_error_is_not_retried(monkeypatch):
    calls = []
    sleeps = []
    llm = dn.LLM(dn.resolve_llm_config(
        provider_config(), environ={"STEPFUN_API_KEY": "secret"}))

    def fail(*args, **kwargs):
        calls.append(1)
        raise AttributeError("unexpected response shape")

    monkeypatch.setattr(llm, "_complete", fail)
    monkeypatch.setattr(dn.time, "sleep", sleeps.append)

    with pytest.raises(RuntimeError, match="unexpected response shape"):
        llm.text_call("system", "user")
    assert len(calls) == 1
    assert sleeps == []


def test_text_call_uses_shared_transport_and_openai_keeps_request_options(monkeypatch):
    seen = []

    class Completions:
        @staticmethod
        def create(**kwargs):
            seen.append(kwargs)
            message = types.SimpleNamespace(content="profile markdown")
            choice = types.SimpleNamespace(message=message, finish_reason="stop")
            usage = types.SimpleNamespace(
                prompt_tokens=9, prompt_cache_hit_tokens=4, completion_tokens=3)
            return types.SimpleNamespace(choices=[choice], usage=usage)

    class OpenAI:
        def __init__(self, **kwargs):
            self.chat = types.SimpleNamespace(completions=Completions())

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=OpenAI))
    cfg = dn.resolve_llm_config(
        provider_config("deepseek"),
        environ={"DEEPSEEK_API_KEY": "deep-secret"},
    )
    llm = dn.LLM(cfg)

    assert llm.text_call("profile system", "profile user", temperature=0.2) == (
        "profile markdown")
    assert seen == [{
        "model": "deepseek-v4-flash",
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": "profile system"},
            {"role": "user", "content": "profile user"},
        ],
        "extra_body": {"thinking": {"type": "disabled"}},
    }]
    assert llm.stage_usage["OTHER"] == {
        "calls": 1,
        "input": 9,
        "input_cached": 4,
        "output": 3,
    }


def test_usage_report_keeps_model_identity_and_marks_unknown_cost():
    known = types.SimpleNamespace(
        provider="stepfun",
        model="step-explore",
        price_usd_per_mtok={"input_miss": 0, "input_hit": 0, "output": 0},
        stage_usage={"TRIAGE_SYSTEM": {
            "calls": 1, "input": 100, "input_cached": 0, "output": 20}},
    )
    unknown = types.SimpleNamespace(
        provider="other",
        model="future-model",
        price_usd_per_mtok=None,
        stage_usage={"TRIAGE_SYSTEM": {
            "calls": 1, "input": 50, "input_cached": 0, "output": 10}},
    )

    merged = dn.merge_usage([known, unknown])
    assert set(merged) == {
        ("stepfun", "step-explore", "TRIAGE_SYSTEM"),
        ("other", "future-model", "TRIAGE_SYSTEM"),
    }
    totals = dn.usage_totals(merged)
    assert totals["llm_calls"] == 2
    assert totals["llm_cost_usd"] is None
    assert totals["llm_cost_known"] is False
