"""Module: MD-SCR-011.001.M18 — _tool_executor.py
Parent SRD: SRD-SCR-013.003, SRD-SCR-013.004

CandleToolExecutor — bridges AI-provider ``get_candle_data`` tool calls to
``DatabaseManager.fetch_bars()``.  Enforces a per-symbol call cap and a
Stage-2 symbol allowlist.  All error conditions are returned to the model
as JSON (never raised) so the agentic loop can continue with partial data.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Final

from us_swing.data.models import OHLCVBar
from us_swing.db.manager import DatabaseManager

logger = logging.getLogger(__name__)

TOOL_NAME: Final[str] = "get_candle_data"

_VALID_TIMEFRAMES: Final[frozenset[str]] = frozenset({"1d", "1w"})
_MAX_LOOKBACK_BARS: Final[int] = 300

# Calendar-day span needed to cover N bars of each timeframe, with a buffer
# for weekends and market holidays.  Fetch wide; slice to last N afterwards.
_CALENDAR_DAYS_PER_BAR: Final[dict[str, int]] = {"1d": 2, "1w": 8}
assert _VALID_TIMEFRAMES == _CALENDAR_DAYS_PER_BAR.keys(), (
    "_CALENDAR_DAYS_PER_BAR must cover every entry in _VALID_TIMEFRAMES"
)


class CandleToolExecutor:
    """Routes ``get_candle_data`` tool calls to the candle database.

    The executor is **single-use per provider run**: construct one, hand it
    to the AI provider, discard at run end.  Per-symbol counters reset
    naturally with each new instance.
    """

    __slots__ = ("_db", "_allowed", "_max_per_symbol", "_calls")

    def __init__(
        self,
        db: DatabaseManager,
        allowed_symbols: set[str],
        max_calls_per_symbol: int = 3,
    ) -> None:
        self._db = db
        self._allowed = set(allowed_symbols)
        self._max_per_symbol = max_calls_per_symbol
        self._calls: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        """Execute a tool call and return a string for the model.

        On success returns compact pipe-delimited plain text (header + one row
        per bar).  On error returns a JSON string
        ``{"error": "<code>", "message": "..."}`` — never raised, so the
        agentic loop can continue with partial data.
        """
        if tool_name != TOOL_NAME:
            return _err("unknown_tool", f"Unknown tool '{tool_name}'.")

        try:
            symbol = str(tool_input["symbol"]).upper()
            timeframe = str(tool_input["timeframe"])
            lookback = int(tool_input["lookback_bars"])
        except (KeyError, TypeError, ValueError) as exc:
            return _err("invalid_input", f"Bad tool input: {exc}.")

        if timeframe not in _VALID_TIMEFRAMES:
            return _err(
                "invalid_timeframe",
                f"timeframe must be one of {sorted(_VALID_TIMEFRAMES)}, got '{timeframe}'.",
            )
        if not (1 <= lookback <= _MAX_LOOKBACK_BARS):
            return _err(
                "invalid_lookback",
                f"lookback_bars must be in [1, {_MAX_LOOKBACK_BARS}], got {lookback}.",
            )
        if symbol not in self._allowed:
            return _err(
                "symbol_not_allowed",
                f"Symbol '{symbol}' did not pass Stage 2 and is not available for inspection.",
            )

        used = self._calls.get(symbol, 0)
        if used >= self._max_per_symbol:
            return _err(
                "tool_call_cap_exceeded",
                f"Tool-call cap of {self._max_per_symbol} per symbol reached for '{symbol}'.",
            )
        self._calls[symbol] = used + 1

        bars = self._fetch(symbol, timeframe, lookback)
        if not bars:
            return _err("no_data", f"No candle data found for '{symbol}' ({timeframe}).")
        return _bars_to_compact_text(symbol, timeframe, bars)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch(self, symbol: str, timeframe: str, lookback: int) -> list[OHLCVBar]:
        end = datetime.now(timezone.utc)
        span_days = lookback * _CALENDAR_DAYS_PER_BAR[timeframe]
        start = end - timedelta(days=span_days)
        bars = self._db.fetch_bars(symbol, timeframe, start, end)
        return bars[-lookback:] if len(bars) > lookback else bars


# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------

def _bars_to_compact_text(symbol: str, timeframe: str, bars: list[OHLCVBar]) -> str:
    """Return pipe-delimited candle data — one header row then one row per bar.

    Volume is floor-divided by 1000 (VOLK) to cut token count on large
    lookbacks.  Callers should treat VOLK as an approximation to the nearest
    1 000 shares.
    """
    lines = [
        f"{symbol} {timeframe} {len(bars)}bars",
        "DATE|O|H|L|C|VOLK",
    ]
    for b in bars:
        lines.append(
            f"{b.datetime.strftime('%Y%m%d')}|"
            f"{b.open:.2f}|{b.high:.2f}|{b.low:.2f}|{b.close:.2f}|"
            f"{int(b.volume // 1000)}"
        )
    return "\n".join(lines)


def _err(code: str, message: str) -> str:
    logger.warning("CandleToolExecutor error %s: %s", code, message)
    return json.dumps({"error": code, "message": message})
