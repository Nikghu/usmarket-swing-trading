"""Module: MD-ANA-002.001.M03 — analysis/strategies/pullback.py
Parent SRD: SRD-ANA-002.003

PullbackStrategy fires a BUY signal when:
  - Trend filter:  1h close > 1h EMA(21)
  - Entry filter:  5m close crosses back above 5m EMA(21) after being below it
                   (EMA must be computed from at least 21 bars)
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from us_swing.analysis.indicators import atr, ema, ema_value
from us_swing.data.models import OHLCVBar, TradeSignal

if TYPE_CHECKING:
    from us_swing.analysis.strategy_engine import StrategyConfig

_log = logging.getLogger(__name__)
_MIN_1H_BARS = 21   # need ≥ 21 bars for EMA21 trend filter
_MIN_5M_BARS = 22   # need ≥ 22 bars: 21 for EMA + 1 previous bar for cross detection


class PullbackStrategy:
    """EMA-21 pullback-recovery entry strategy."""

    strategy_id = "pullback"

    def evaluate(
        self,
        symbol: str,
        bar_cache: dict[str, list[OHLCVBar]],
        config: "StrategyConfig",
    ) -> TradeSignal | None:
        """Evaluate pullback entry for *symbol*.

        Args:
            symbol:    Ticker symbol.
            bar_cache: Dict of tf -> list[OHLCVBar] (newest at end).
            config:    Active strategy configuration.

        Returns:
            BUY :class:`TradeSignal` or ``None``.
        """
        h1_bars = bar_cache.get("1h", [])
        m5_bars = bar_cache.get("5m", [])

        if len(h1_bars) < _MIN_1H_BARS or len(m5_bars) < _MIN_5M_BARS:
            return None

        # Trend filter: 1h close > 1h EMA(21)
        if h1_bars[-1].close <= ema_value(h1_bars, 21):
            return None

        # Entry filter: 5m close crosses above 5m EMA(21)
        m5_ema = ema(m5_bars, 21)
        prev_close = m5_bars[-2].close
        curr_close = m5_bars[-1].close
        prev_ema = m5_ema[-2]
        curr_ema = m5_ema[-1]

        if not (prev_close < prev_ema and curr_close > curr_ema):
            return None

        # Build signal
        entry = curr_close
        atr_val = atr(m5_bars, 14)
        stop = entry - atr_val * config.atr_multiplier
        target = entry + (entry - stop) * config.r_multiple

        _log.info("pullback signal: %s entry=%.2f stop=%.2f target=%.2f", symbol, entry, stop, target)
        return TradeSignal(
            symbol=symbol,
            side="BUY",
            strategy_id=self.strategy_id,
            score=1.0,
            entry_price=entry,
            stop_loss=max(stop, 0.01),
            target_price=target,
        )
