"""
Provider-agnostic LLM client.

Agents call `llm_client.complete(system, user)` and never know which
provider is behind it. Selection is config-driven via LLM_PROVIDER in .env:

    LLM_PROVIDER=anthropic   -> uses ANTHROPIC_API_KEY
    LLM_PROVIDER=openai      -> uses OPENAI_API_KEY
    LLM_PROVIDER=mock        -> deterministic canned responses, no key needed

The mock provider is what lets the whole agent/orchestrator layer be
developed and unit-tested before any real API key is wired in.
"""
from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.settings import settings


class LLMClient(ABC):
    @abstractmethod
    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        """Return the model's text response."""
        raise NotImplementedError


class AnthropicClient(LLMClient):
    def __init__(self):
        import anthropic
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set but LLM_PROVIDER=anthropic")
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in resp.content if block.type == "text")


class OpenAIClient(LLMClient):
    def __init__(self):
        import openai
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY not set but LLM_PROVIDER=openai")
        self._client = openai.OpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content


class MockClient(LLMClient):
    """
    Deterministic, key-free stand-in for a real LLM. Returns structured,
    plausible-looking text keyed off the content it's given, so tests and
    local dev produce stable, reproducible agent output.
    """

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        seed = hashlib.sha256((system + user).encode()).hexdigest()[:8]

        if "root cause" in system.lower():
            likely_cause, evidence = _infer_mock_cause(user)
            return json.dumps({
                "likely_cause": likely_cause,
                "supporting_evidence": evidence,
                "confidence": 0.8,
                "trace_id": seed,
            })
        if "risk" in system.lower():
            return json.dumps({
                "asset_criticality": "High",
                "operational_impact": "Medium",
                "attack_severity": "High",
                "business_risk_score": 0.78,
                "trace_id": seed,
            })
        if "response" in system.lower() or "remediat" in system.lower():
            return json.dumps({
                "recommended_actions": [
                    "Isolate affected asset from the control network segment",
                    "Enable enhanced monitoring on related IEDs",
                    "Notify on-call ICS security engineer",
                ],
                "trace_id": seed,
            })
        if "knowledge" in system.lower() or "retriev" in system.lower():
            return json.dumps({
                "references": [
                    "MITRE ATT&CK for ICS: relevant technique context",
                    "NIST SP 800-82: ICS security control guidance",
                ],
                "trace_id": seed,
            })
        # generic detection-agent style summary
        return json.dumps({
            "summary": "Traffic pattern flagged by the anomaly detector shows characteristics "
                       "consistent with a known ICS attack category.",
            "trace_id": seed,
        })


def _infer_mock_cause(user_prompt: str) -> tuple[str, list[str]]:
    """
    Very small heuristic used ONLY by the mock provider so agent-pipeline
    tests/demos produce a coherent, non-random incident report without any
    real LLM call. A real provider would reason over this from the prompt.
    """
    text = user_prompt.lower()

    def has(*keywords: str) -> bool:
        return any(k in text for k in keywords)

    if has("dos") or (_extract_number(text, "request_rate") or 0) > 30:
        return (
            "Traffic pattern consistent with a Denial of Service attempt against the target asset: "
            "elevated request rate with reduced packet size.",
            ["request_rate significantly above baseline", "packet_size below normal operating range"],
        )
    if has("mitm", "man-in-the-middle") or (_extract_number(text, "latency_ms") or 0) > 30:
        return (
            "Traffic pattern consistent with a Man-in-the-Middle interception: elevated latency and jitter.",
            ["latency_ms above baseline", "jitter_ms elevated", "unexpected src/dst asset pairing"],
        )
    if has("fdi", "false data injection") or abs(_extract_number(text, "value_deviation") or 0) > 2:
        return (
            "Reported value statistically inconsistent with historical baseline, consistent with False Data Injection.",
            ["value_deviation outside normal range", "Write/Report service call involved"],
        )
    if has("replay") or (_extract_number(text, "duplicate_ratio") or 0) > 0.5:
        return (
            "Near-duplicate payloads with unnaturally regular timing, consistent with a Replay attack.",
            ["duplicate_ratio elevated", "inter_arrival_ms unusually consistent"],
        )
    return (
        "Anomalous protocol pattern flagged, but evidence is insufficient to attribute a specific attack technique.",
        ["Deviation from baseline traffic profile", "No single feature dominates the anomaly score"],
    )


def _extract_number(text: str, key: str) -> float | None:
    import re
    match = re.search(rf'"{key}"\s*:\s*(-?\d+\.?\d*)', text)
    if match:
        return float(match.group(1))
    return None


_PROVIDERS = {
    "anthropic": AnthropicClient,
    "openai": OpenAIClient,
    "mock": MockClient,
}


def get_llm_client(provider: str | None = None) -> LLMClient:
    provider = (provider or settings.llm_provider).lower()
    if provider not in _PROVIDERS:
        raise ValueError(f"Unknown LLM_PROVIDER '{provider}'. Choose one of {list(_PROVIDERS)}")
    return _PROVIDERS[provider]()
