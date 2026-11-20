import pytest
from token_engine.engine import TokenEngine

@pytest.fixture
def engine():
    return TokenEngine(threshold_percent=10.0, min_tokens=5)

def test_estimate_below_threshold(engine):
    prompt = "short"
    out = engine.process(prompt)
    assert out.startswith("MODEL_OUTPUT")

def test_throttle_trigger(engine, monkeypatch):
    # Very long prompt to exceed threshold
    prompt = "word " * 1000
    # Monkey‑patch input to auto‑accept confirmation (not used here because engine returns sentinel)
    monkeypatch.setattr("builtins.input", lambda _: "y")
    out = engine.process(prompt)
    assert out == "THROTTLE_REQUIRED"
