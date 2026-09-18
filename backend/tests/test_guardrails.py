import pytest
from backend.app.guardrails.readability import ReadabilityGuardrail

def test_readability_guardrail_clean_text():
    guard = ReadabilityGuardrail()
    clean_sample = (
        "We have to ground this in concrete mechanical sympathy. "
        "The primary bottleneck in this distributed design isn't raw computation, "
        "but memory bandwidth and cross-node latency under heavy load."
    )
    res = guard.calculate_human_readability(clean_sample)
    assert res["passed"] is True
    assert res["score"] > 20.0
    assert res["metrics"]["words"] > 10

def test_readability_guardrail_rejects_degeneration():
    guard = ReadabilityGuardrail()
    repetitive_sample = "hello world test " * 20
    res = guard.calculate_human_readability(repetitive_sample)
    assert res["passed"] is False
    assert "repetition" in res["reason"].lower() or "trigram" in res["reason"].lower()

def test_readability_guardrail_rejects_too_short():
    guard = ReadabilityGuardrail()
    short_sample = "Too short."
    res = guard.calculate_human_readability(short_sample)
    assert res["passed"] is False
    assert "too short" in res["reason"].lower()
