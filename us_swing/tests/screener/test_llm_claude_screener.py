"""Unit tests: MD-SCR-002.003.M06 — screeners/llm_claude.py
Refs: UT-SCR-002.003.M06.T01 – UT-SCR-002.003.M06.T15
"""
from __future__ import annotations

import json
import logging
from datetime import timedelta
from unittest.mock import MagicMock, patch

from us_swing.screener.screeners.llm_claude import LLMClaudeScreener

from .conftest import make_bars

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

SYMBOLS = ["AAPL", "MSFT", "GOOGL"]
BARS = {s: make_bars(s, n=50, seed=i) for i, s in enumerate(SYMBOLS)}
BASE_CONFIG = {"api_key": "sk-test", "top_n": 3}

REQUIRED_FEATURE_KEYS = {"price", "trend", "RSI", "ATR", "support", "resistance", "volume"}


def _mock_response(scores: dict[str, float]) -> MagicMock:
    """Build a mock anthropic response with the given per-symbol scores."""
    resp = MagicMock()
    resp.content = [MagicMock(text=json.dumps(scores))]
    resp.usage = MagicMock(input_tokens=100, output_tokens=50)
    return resp


def _mock_client(response: MagicMock) -> MagicMock:
    client = MagicMock()
    client.messages.create.return_value = response
    return client


# ---------------------------------------------------------------------------
# T01 — batch_features() extracts features without making an API call
# ---------------------------------------------------------------------------

def test_t01_batch_features_no_api_call():
    """UT-SCR-002.003.M06.T01"""
    screener = LLMClaudeScreener()
    with patch("us_swing.screener.screeners.llm_claude.anthropic") as mock_anthro:
        result = screener.batch_features(SYMBOLS, BARS)
        mock_anthro.Anthropic.assert_not_called()
    assert isinstance(result, dict)
    assert set(result.keys()) == set(SYMBOLS)


# ---------------------------------------------------------------------------
# T02 — features include all required fields with correct types
# ---------------------------------------------------------------------------

def test_t02_features_include_required_fields():
    """UT-SCR-002.003.M06.T02"""
    screener = LLMClaudeScreener()
    result = screener.batch_features(SYMBOLS, BARS)
    for sym in SYMBOLS:
        features = result[sym]
        missing = REQUIRED_FEATURE_KEYS - set(features.keys())
        assert not missing, f"{sym}: missing feature keys {missing}"
        assert isinstance(features["price"], (int, float))
        assert isinstance(features["RSI"], (int, float))
        assert isinstance(features["ATR"], (int, float))
        assert isinstance(features["trend"], str)


# ---------------------------------------------------------------------------
# T03 — apply() calls Claude API; prompt contains symbol names
# ---------------------------------------------------------------------------

def test_t03_apply_calls_claude_api():
    """UT-SCR-002.003.M06.T03"""
    screener = LLMClaudeScreener()
    scores = {s: 0.7 for s in SYMBOLS}
    response = _mock_response(scores)

    with patch("us_swing.screener.screeners.llm_claude.anthropic") as mock_anthro:
        mock_anthro.Anthropic.return_value = _mock_client(response)
        screener.apply(SYMBOLS, BARS, BASE_CONFIG)
        # API must have been called exactly once
        client = mock_anthro.Anthropic.return_value
        client.messages.create.assert_called_once()
        # The prompt must contain at least one symbol name
        call_kwargs = client.messages.create.call_args[1]
        prompt_text = call_kwargs["messages"][0]["content"]
        assert any(sym in prompt_text for sym in SYMBOLS)


# ---------------------------------------------------------------------------
# T04 — apply() parses Claude JSON response into (bool, float) tuples
# ---------------------------------------------------------------------------

def test_t04_parses_claude_json_response():
    """UT-SCR-002.003.M06.T04"""
    screener = LLMClaudeScreener()
    scores = {"AAPL": 0.9, "MSFT": 0.7, "GOOGL": 0.5}
    response = _mock_response(scores)

    with patch("us_swing.screener.screeners.llm_claude.anthropic") as mock_anthro:
        mock_anthro.Anthropic.return_value = _mock_client(response)
        result = screener.apply(SYMBOLS, BARS, BASE_CONFIG)

    for sym, (passed, score) in result.items():
        assert isinstance(passed, bool)
        assert isinstance(score, float)


# ---------------------------------------------------------------------------
# T05 — all returned scores in [0, 1]
# ---------------------------------------------------------------------------

def test_t05_scores_in_unit_interval():
    """UT-SCR-002.003.M06.T05"""
    screener = LLMClaudeScreener()
    # Claude returns scores that might be outside [0,1]; screener should clamp
    scores = {"AAPL": 1.5, "MSFT": -0.2, "GOOGL": 0.6}
    response = _mock_response(scores)

    with patch("us_swing.screener.screeners.llm_claude.anthropic") as mock_anthro:
        mock_anthro.Anthropic.return_value = _mock_client(response)
        result = screener.apply(SYMBOLS, BARS, BASE_CONFIG)

    for sym, (_, score) in result.items():
        assert 0.0 <= score <= 1.0, f"{sym}: score {score} out of [0, 1]"


# ---------------------------------------------------------------------------
# T06 — API timeout → fallback (all pass, score=0), WARNING logged
# ---------------------------------------------------------------------------

def test_t06_api_timeout_triggers_fallback(caplog):
    """UT-SCR-002.003.M06.T06"""
    screener = LLMClaudeScreener()

    with patch("us_swing.screener.screeners.llm_claude.anthropic") as mock_anthro:
        mock_client = MagicMock()
        mock_anthro.Anthropic.return_value = mock_client
        mock_anthro.APITimeoutError = TimeoutError  # map to generic timeout
        mock_client.messages.create.side_effect = TimeoutError("timeout")

        with caplog.at_level(logging.WARNING):
            result = screener.apply(SYMBOLS, BARS, BASE_CONFIG)

    # Fallback: all symbols pass with score=0
    assert set(result.keys()) == set(SYMBOLS)
    for sym, (passed, score) in result.items():
        assert passed is True
        assert score == 0.0
    assert any("warning" in r.levelname.lower() or "fallback" in r.message.lower()
               for r in caplog.records)


# ---------------------------------------------------------------------------
# T07 — auth error → fallback, ERROR logged
# ---------------------------------------------------------------------------

def test_t07_auth_error_triggers_fallback(caplog):
    """UT-SCR-002.003.M06.T07"""
    screener = LLMClaudeScreener()

    with patch("us_swing.screener.screeners.llm_claude.anthropic") as mock_anthro:
        mock_client = MagicMock()
        mock_anthro.Anthropic.return_value = mock_client
        mock_anthro.AuthenticationError = PermissionError
        mock_client.messages.create.side_effect = PermissionError("auth")

        with caplog.at_level(logging.WARNING):
            result = screener.apply(SYMBOLS, BARS, BASE_CONFIG)

    assert set(result.keys()) == set(SYMBOLS)
    for _, (passed, _) in result.items():
        assert passed is True


# ---------------------------------------------------------------------------
# T08 — rate limit (429) → fallback, WARNING logged
# ---------------------------------------------------------------------------

def test_t08_rate_limit_triggers_fallback(caplog):
    """UT-SCR-002.003.M06.T08"""
    screener = LLMClaudeScreener()

    with patch("us_swing.screener.screeners.llm_claude.anthropic") as mock_anthro:
        mock_client = MagicMock()
        mock_anthro.Anthropic.return_value = mock_client
        mock_anthro.RateLimitError = RuntimeError
        mock_client.messages.create.side_effect = RuntimeError("429 rate limit")

        with caplog.at_level(logging.WARNING):
            result = screener.apply(SYMBOLS, BARS, BASE_CONFIG)

    assert set(result.keys()) == set(SYMBOLS)


# ---------------------------------------------------------------------------
# T09 — apply() calls usage_tracker.log_usage() after successful API call
# ---------------------------------------------------------------------------

def test_t09_logs_api_usage():
    """UT-SCR-002.003.M06.T09"""
    mock_tracker = MagicMock()
    screener = LLMClaudeScreener(usage_tracker=mock_tracker)

    scores = {s: 0.5 for s in SYMBOLS}
    response = _mock_response(scores)

    with patch("us_swing.screener.screeners.llm_claude.anthropic") as mock_anthro:
        mock_anthro.Anthropic.return_value = _mock_client(response)
        screener.apply(SYMBOLS, BARS, BASE_CONFIG)

    mock_tracker.log_usage.assert_called_once()
    call_kwargs = mock_tracker.log_usage.call_args[1]
    assert "tokens_in" in call_kwargs or len(mock_tracker.log_usage.call_args[0]) >= 2


# ---------------------------------------------------------------------------
# T10 — monthly cost > $50 triggers WARNING log
# ---------------------------------------------------------------------------

def test_t10_cost_threshold_warning(caplog):
    """UT-SCR-002.003.M06.T10"""
    mock_tracker = MagicMock()
    mock_tracker.get_monthly_cost.return_value = 55.0  # exceeds $50

    screener = LLMClaudeScreener(usage_tracker=mock_tracker)
    scores = {s: 0.5 for s in SYMBOLS}
    response = _mock_response(scores)

    with patch("us_swing.screener.screeners.llm_claude.anthropic") as mock_anthro:
        mock_anthro.Anthropic.return_value = _mock_client(response)
        with caplog.at_level(logging.WARNING):
            screener.apply(SYMBOLS, BARS, BASE_CONFIG)

    assert any("50" in r.message or "cost" in r.message.lower() for r in caplog.records)


# ===========================================================================
# Tool-augmented path tests (SRD-SCR-013.005)
# ===========================================================================

def _text_block(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _tool_use_block(tool_id: str, name: str, input_dict: dict) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_id
    block.name = name
    block.input = input_dict
    return block


def _agentic_response(content_blocks: list, stop_reason: str) -> MagicMock:
    resp = MagicMock()
    resp.content = content_blocks
    resp.stop_reason = stop_reason
    resp.usage = MagicMock(input_tokens=100, output_tokens=50)
    return resp


class _FakeDB:
    def fetch_bars(self, symbol, timeframe, start, end):
        from us_swing.data.models import OHLCVBar
        return [
            OHLCVBar(symbol=symbol, datetime=end - timedelta(days=i),
                     open=100.0, high=101.0, low=99.0, close=100.5,
                     volume=1_000_000, timeframe=timeframe)
            for i in range(5)
        ]


# ---------------------------------------------------------------------------
# T11 — non-empty ai_query routes to tool-augmented path; tools are sent
# ---------------------------------------------------------------------------

def test_t11_ai_query_uses_tools():
    """UT-SCR-002.003.M06.T11"""
    screener = LLMClaudeScreener()
    final = _agentic_response(
        [_text_block(json.dumps([
            {"symbol": s, "score": 0.8, "reasoning": f"{s} looks good"} for s in SYMBOLS
        ]))],
        stop_reason="end_turn",
    )
    config = {**BASE_CONFIG, "ai_query": "find bullish breakouts",
              "db": _FakeDB(), "passing_symbols": set(SYMBOLS)}

    with patch("us_swing.screener.screeners.llm_claude.anthropic") as mock_anthro:
        mock_anthro.Anthropic.return_value = _mock_client(final)
        result = screener.apply(SYMBOLS, BARS, config)

        client = mock_anthro.Anthropic.return_value
        kwargs = client.messages.create.call_args[1]
        # Tools must be present in the API call
        assert "tools" in kwargs
        assert kwargs["tools"][0]["name"] == "get_candle_data"
        # System prompt must include the user query
        assert "find bullish breakouts" in kwargs["system"]

    for sym, (passed, score) in result.items():
        assert passed is True
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# T12 — multi-turn loop: tool_use → tool_result → end_turn
# ---------------------------------------------------------------------------

def test_t12_multi_turn_tool_loop_routes_to_executor():
    """UT-SCR-002.003.M06.T12"""
    screener = LLMClaudeScreener()
    tool_use = _tool_use_block(
        "tu_1", "get_candle_data",
        {"symbol": "AAPL", "timeframe": "1d", "lookback_bars": 30},
    )
    turn1 = _agentic_response([tool_use], stop_reason="tool_use")
    turn2 = _agentic_response(
        [_text_block(json.dumps([
            {"symbol": s, "score": 0.6, "reasoning": "ok"} for s in SYMBOLS
        ]))],
        stop_reason="end_turn",
    )
    config = {**BASE_CONFIG, "ai_query": "rank these",
              "db": _FakeDB(), "passing_symbols": set(SYMBOLS)}

    with patch("us_swing.screener.screeners.llm_claude.anthropic") as mock_anthro:
        client = MagicMock()
        client.messages.create.side_effect = [turn1, turn2]
        mock_anthro.Anthropic.return_value = client

        result = screener.apply(SYMBOLS, BARS, config)

        assert client.messages.create.call_count == 2
        # 2nd call must include the tool_result message back to Claude
        second_call_kwargs = client.messages.create.call_args_list[1][1]
        msgs = second_call_kwargs["messages"]
        assert any(
            isinstance(m["content"], list)
            and any(c.get("type") == "tool_result" for c in m["content"])
            for m in msgs if isinstance(m["content"], list)
        )

    assert set(result.keys()) == set(SYMBOLS)


# ---------------------------------------------------------------------------
# T13 — reasoning is captured in screener.last_reasoning
# ---------------------------------------------------------------------------

def test_t13_reasoning_captured():
    """UT-SCR-002.003.M06.T13"""
    screener = LLMClaudeScreener()
    final = _agentic_response(
        [_text_block(json.dumps([
            {"symbol": "AAPL", "score": 0.9, "reasoning": "Strong breakout"},
            {"symbol": "MSFT", "score": 0.6, "reasoning": "Range-bound"},
            {"symbol": "GOOGL", "score": 0.3, "reasoning": "Weak momentum"},
        ]))],
        stop_reason="end_turn",
    )
    config = {**BASE_CONFIG, "ai_query": "rank by momentum",
              "db": _FakeDB(), "passing_symbols": set(SYMBOLS)}

    with patch("us_swing.screener.screeners.llm_claude.anthropic") as mock_anthro:
        mock_anthro.Anthropic.return_value = _mock_client(final)
        screener.apply(SYMBOLS, BARS, config)

    assert screener.last_reasoning["AAPL"] == "Strong breakout"
    assert screener.last_reasoning["MSFT"] == "Range-bound"


# ---------------------------------------------------------------------------
# T14 — reasoning truncated to ≤ 50 words
# ---------------------------------------------------------------------------

def test_t14_reasoning_truncated_to_50_words():
    """UT-SCR-002.003.M06.T14"""
    long_text = " ".join([f"word{i}" for i in range(80)])
    screener = LLMClaudeScreener()
    final = _agentic_response(
        [_text_block(json.dumps([{"symbol": "AAPL", "score": 0.5, "reasoning": long_text}]))],
        stop_reason="end_turn",
    )
    config = {**BASE_CONFIG, "ai_query": "rank",
              "db": _FakeDB(), "passing_symbols": {"AAPL"}}

    with patch("us_swing.screener.screeners.llm_claude.anthropic") as mock_anthro:
        mock_anthro.Anthropic.return_value = _mock_client(final)
        screener.apply(["AAPL"], BARS, config)

    assert len(screener.last_reasoning["AAPL"].split()) == 50


# ---------------------------------------------------------------------------
# T15 — empty ai_query falls back to legacy single-shot path (no tools)
# ---------------------------------------------------------------------------

def test_t15_empty_ai_query_uses_legacy_path():
    """UT-SCR-002.003.M06.T15"""
    screener = LLMClaudeScreener()
    response = _mock_response({s: 0.5 for s in SYMBOLS})
    config = {**BASE_CONFIG, "ai_query": ""}

    with patch("us_swing.screener.screeners.llm_claude.anthropic") as mock_anthro:
        mock_anthro.Anthropic.return_value = _mock_client(response)
        screener.apply(SYMBOLS, BARS, config)
        kwargs = mock_anthro.Anthropic.return_value.messages.create.call_args[1]
        # Legacy path uses no tools and no system prompt
        assert "tools" not in kwargs
        assert "system" not in kwargs

    assert screener.last_reasoning == {}
