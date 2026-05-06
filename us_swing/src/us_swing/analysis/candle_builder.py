"""Module: MD-ANA-001.001.M01 — analysis/candle_builder.py
Parent SRD: SRD-ANA-001.002–005

CandleBuilder aggregates 5-second realtime bars into multi-timeframe OHLCV
candles. Fires an on_candle_closed callback on each completed candle window.
Handles gaps in 5s delivery by inserting carry-forward synthetic bars.

Supported timeframes: 1m, 3m, 5m, 15m, 1h.
Candle windows are count-based: TF_seconds / 5 bars close one candle.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import timedelta

from us_swing.data.models import OHLCVBar, RealtimeBar

log = logging.getLogger(__name__)

_BAR_SECONDS = 5
_TF_SECONDS: dict[str, int] = {
    "1m":  60,
    "3m":  180,
    "5m":  300,
    "15m": 900,
    "1h":  3600,
}


class CandleBuilder:
    """Aggregates 5-second bars into multi-timeframe OHLCV candles.

    Args:
        timeframes:       Timeframes to maintain (e.g. ["1m", "5m", "15m", "1h"]).
        on_candle_closed: Optional callback(symbol, tf, bar) invoked on each
                          completed candle. Can also be set later via
                          :meth:`register_callback`.
    """

    def __init__(
        self,
        timeframes: list[str],
        on_candle_closed: Callable[[str, str, OHLCVBar], None] | None = None,
    ) -> None:
        for tf in timeframes:
            if tf not in _TF_SECONDS:
                raise ValueError(f"Unsupported timeframe: {tf!r}")
        self._tfs = timeframes
        self._callback: Callable[[str, str, OHLCVBar], None] = (
            on_candle_closed if on_candle_closed is not None else self._noop
        )
        # _buffers[symbol][tf]   = in-progress 5s bars for the current candle
        self._buffers:   dict[str, dict[str, list[RealtimeBar]]] = {}
        # _completed[symbol][tf] = list of finished OHLCVBar candles
        self._completed: dict[str, dict[str, list[OHLCVBar]]] = {}
        # _last_bar[symbol]      = most recent real bar (for gap detection)
        self._last_bar:  dict[str, RealtimeBar] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def register_callback(
        self, on_candle_closed: Callable[[str, str, OHLCVBar], None]
    ) -> None:
        """Replace the candle-closed callback (e.g. wired in by LiveEngine)."""
        self._callback = on_candle_closed

    def add_bar(self, bar: RealtimeBar) -> None:
        """Process one 5-second bar, filling gaps and closing completed candles."""
        symbol = bar.symbol
        self._ensure_symbol(symbol)

        # Gap detection: if previous bar exists and gap > 5 s, insert synthetic bars
        if symbol in self._last_bar:
            prev = self._last_bar[symbol]
            delta = (bar.datetime - prev.datetime).total_seconds()
            if delta > _BAR_SECONDS:
                gaps = round(delta / _BAR_SECONDS) - 1
                for i in range(1, gaps + 1):
                    synthetic = RealtimeBar(
                        symbol=symbol,
                        datetime=prev.datetime + timedelta(seconds=i * _BAR_SECONDS),
                        open=prev.close,
                        high=prev.close,
                        low=prev.close,
                        close=prev.close,
                        volume=0,
                    )
                    log.debug("Gap fill %s @ %s (vol=0)", symbol, synthetic.datetime)
                    self._process_bar(synthetic)

        self._process_bar(bar)
        self._last_bar[symbol] = bar

    def get_buffer(self, symbol: str, tf: str) -> list[OHLCVBar]:
        """Return a copy of the completed candle list for (symbol, tf)."""
        return list(self._completed.get(symbol, {}).get(tf, []))

    def reset(self, symbol: str) -> None:
        """Clear all in-progress and completed buffers for *symbol*."""
        self._buffers.pop(symbol, None)
        self._completed.pop(symbol, None)
        self._last_bar.pop(symbol, None)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _ensure_symbol(self, symbol: str) -> None:
        if symbol not in self._buffers:
            self._buffers[symbol]   = {tf: [] for tf in self._tfs}
            self._completed[symbol] = {tf: [] for tf in self._tfs}

    def _process_bar(self, bar: RealtimeBar) -> None:
        """Append *bar* to all TF buffers; emit completed candles."""
        symbol = bar.symbol
        for tf in self._tfs:
            buf = self._buffers[symbol][tf]
            buf.append(bar)
            needed = _TF_SECONDS[tf] // _BAR_SECONDS
            if len(buf) >= needed:
                candle = self._aggregate(symbol, tf, buf)
                self._completed[symbol][tf].append(candle)
                log.debug("Candle closed: %s %s @ %s", symbol, tf, candle.datetime)
                self._callback(symbol, tf, candle)
                self._buffers[symbol][tf] = []

    @staticmethod
    def _aggregate(
        symbol: str, tf: str, bars: list[RealtimeBar]
    ) -> OHLCVBar:
        return OHLCVBar(
            symbol=symbol,
            datetime=bars[0].datetime,
            open=bars[0].open,
            high=max(b.high for b in bars),
            low=min(b.low for b in bars),
            close=bars[-1].close,
            volume=sum(b.volume for b in bars),
            timeframe=tf,
        )

    @staticmethod
    def _noop(symbol: str, tf: str, bar: OHLCVBar) -> None:
        pass
