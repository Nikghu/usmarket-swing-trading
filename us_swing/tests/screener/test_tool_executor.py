"""Unit tests: MD-SCR-011.001.M18 — _tool_executor.py
Refs: UT-SCR-011.001.M18.T01 – UT-SCR-011.001.M18.T11
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

import pytest

from us_swing.data.models import OHLCVBar
from us_swing.screener.screeners._tool_executor import (
    TOOL_NAME,
    CandleToolExecutor,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class _FakeDB:
    """Minimal DatabaseManager stub — records calls and returns synthetic bars."""

    def __init__(self, bars_per_call: int = 5) -> None:
        self._bars_per_call = bars_per_call
        self.calls: list[tuple[str, str, datetime, datetime]] = []

    def fetch_bars(
        self, symbol: str, timeframe: str, start: datetime, end: datetime,
    ) -> list[OHLCVBar]:
        self.calls.append((symbol, timeframe, start, end))
        return [
            OHLCVBar(
                symbol=symbol,
                datetime=end - timedelta(days=i),
                open=100.0 + i,
                high=101.0 + i,
                low=99.0 + i,
                close=100.5 + i,
                volume=1_000_000 + i,
                timeframe=timeframe,
            )
            for i in range(self._bars_per_call)
        ]


@pytest.fixture
def db() -> _FakeDB:
    return _FakeDB(bars_per_call=10)


@pytest.fixture
def executor(db: _FakeDB) -> CandleToolExecutor:
    return CandleToolExecutor(db, allowed_symbols={"AAPL", "MSFT"})


def _input(symbol: str = "AAPL", timeframe: str = "1d", lookback: int = 5) -> dict[str, Any]:
    return {"symbol": symbol, "timeframe": timeframe, "lookback_bars": lookback}


# ---------------------------------------------------------------------------
# T01 — happy path returns compact text with bars
# ---------------------------------------------------------------------------

def test_t01_happy_path_returns_bars(executor: CandleToolExecutor, db: _FakeDB) -> None:
    """UT-SCR-011.001.M18.T01: Happy path returns compact text with header and correct data rows."""
    out = executor.execute(TOOL_NAME, _input("AAPL", "1d", 5))
    lines = out.splitlines()
    assert lines[0] == "AAPL 1d 5bars"
    assert lines[1] == "DATE|O|H|L|C|VOLK"
    assert len(lines) == 7  # 2 header lines + 5 data rows
    assert len(lines[2].split("|")) == 6  # DATE|O|H|L|C|VOLK
    assert len(db.calls) == 1


# ---------------------------------------------------------------------------
# T02 — symbol allowlist rejects symbols that didn't pass Stage 2
# ---------------------------------------------------------------------------

def test_t02_disallowed_symbol_returns_error(executor: CandleToolExecutor, db: _FakeDB) -> None:
    """UT-SCR-011.001.M18.T02: Symbol not in Stage-2 allowlist returns symbol_not_allowed without querying DB."""
    out = json.loads(executor.execute(TOOL_NAME, _input("TSLA", "1d", 5)))
    assert out["error"] == "symbol_not_allowed"
    assert db.calls == []  # DB never queried


# ---------------------------------------------------------------------------
# T03 — call cap enforced per symbol; 4th call returns error
# ---------------------------------------------------------------------------

def test_t03_per_symbol_call_cap(executor: CandleToolExecutor) -> None:
    """UT-SCR-011.001.M18.T03: Fourth call on same symbol returns tool_call_cap_exceeded; other symbols unaffected."""
    for _ in range(3):
        out = executor.execute(TOOL_NAME, _input("AAPL", "1d", 5))
        assert out.splitlines()[0] == "AAPL 1d 5bars"
    out4 = json.loads(executor.execute(TOOL_NAME, _input("AAPL", "1d", 5)))
    assert out4["error"] == "tool_call_cap_exceeded"
    # Other symbols still have full quota
    out_msft = executor.execute(TOOL_NAME, _input("MSFT", "1d", 5))
    assert out_msft.splitlines()[0] == "MSFT 1d 5bars"


# ---------------------------------------------------------------------------
# T04 — invalid timeframe rejected
# ---------------------------------------------------------------------------

def test_t04_invalid_timeframe(executor: CandleToolExecutor) -> None:
    """UT-SCR-011.001.M18.T04: Unsupported timeframe string returns invalid_timeframe error."""
    out = json.loads(executor.execute(TOOL_NAME, _input("AAPL", "5m", 5)))
    assert out["error"] == "invalid_timeframe"


# ---------------------------------------------------------------------------
# T05 — lookback_bars out of range rejected
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lookback", [0, -5, 301, 1000])
def test_t05_invalid_lookback(executor: CandleToolExecutor, lookback: int) -> None:
    """UT-SCR-011.001.M18.T05: Out-of-range lookback_bars values return invalid_lookback error."""
    out = json.loads(executor.execute(TOOL_NAME, _input("AAPL", "1d", lookback)))
    assert out["error"] == "invalid_lookback"


# ---------------------------------------------------------------------------
# T06 — unknown tool name rejected
# ---------------------------------------------------------------------------

def test_t06_unknown_tool_name(executor: CandleToolExecutor) -> None:
    """UT-SCR-011.001.M18.T06: Tool name other than get_candle_data returns unknown_tool error."""
    out = json.loads(executor.execute("get_news_sentiment", _input()))
    assert out["error"] == "unknown_tool"


# ---------------------------------------------------------------------------
# T07 — malformed input (missing key) returns invalid_input error
# ---------------------------------------------------------------------------

def test_t07_malformed_input(executor: CandleToolExecutor) -> None:
    """UT-SCR-011.001.M18.T07: Missing required key in tool_input returns invalid_input error."""
    out = json.loads(executor.execute(TOOL_NAME, {"symbol": "AAPL", "timeframe": "1d"}))
    assert out["error"] == "invalid_input"


# ---------------------------------------------------------------------------
# T08 — fetch span widens for 1w timeframe (calendar-day buffer)
# ---------------------------------------------------------------------------

def test_t08_weekly_timeframe_uses_wider_span(db: _FakeDB) -> None:
    """UT-SCR-011.001.M18.T08: Weekly timeframe multiplies lookback by 8 calendar days to cover weekends."""
    ex = CandleToolExecutor(db, allowed_symbols={"AAPL"})
    ex.execute(TOOL_NAME, _input("AAPL", "1w", 10))
    sym, tf, start, end = db.calls[0]
    assert tf == "1w"
    span = (end - start).days
    # 10 weekly bars × 8 calendar days/bar = 80 days
    assert span == 10 * 8


# ---------------------------------------------------------------------------
# T09 — fetched bar list is sliced to last `lookback_bars`
# ---------------------------------------------------------------------------

def test_t09_slice_to_lookback() -> None:
    """UT-SCR-011.001.M18.T09: When DB returns more bars than requested, output is sliced to lookback_bars."""
    db = _FakeDB(bars_per_call=50)
    ex = CandleToolExecutor(db, allowed_symbols={"AAPL"})
    out = ex.execute(TOOL_NAME, _input("AAPL", "1d", 7))
    lines = out.splitlines()
    assert lines[0] == "AAPL 1d 7bars"
    assert len(lines) == 9  # 2 header lines + 7 data rows


# ---------------------------------------------------------------------------
# T10 — symbol comparison is case-insensitive (lowercase passes when uppercased)
# ---------------------------------------------------------------------------

def test_t10_symbol_uppercased(db: _FakeDB) -> None:
    """UT-SCR-011.001.M18.T10: Lowercase symbol input is uppercased in the compact text response."""
    ex = CandleToolExecutor(db, allowed_symbols={"AAPL"})
    out = ex.execute(TOOL_NAME, _input("aapl", "1d", 3))
    assert out.startswith("AAPL")  # symbol uppercased in compact header
    assert "bars" in out


# ---------------------------------------------------------------------------
# T11 — empty DB result returns no_data error, not a silent 0bars response
# ---------------------------------------------------------------------------

def test_t11_empty_db_result_returns_error() -> None:
    """UT-SCR-011.001.M18.T11: No candle data returns no_data error JSON."""
    empty_db = _FakeDB(bars_per_call=0)
    ex = CandleToolExecutor(empty_db, allowed_symbols={"AAPL"})
    out = json.loads(ex.execute(TOOL_NAME, _input("AAPL", "1d", 5)))
    assert out["error"] == "no_data"
