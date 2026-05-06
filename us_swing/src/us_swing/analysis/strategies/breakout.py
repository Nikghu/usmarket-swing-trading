"""Module: MD-ANA-002.001.M02 — analysis/strategies/breakout.py
Parent SRD: SRD-ANA-002.002

BreakoutStrategy fires a BUY signal when:
  - Trend filter:  1h close > 1h EMA(50)
  - Entry filter:  breakout_tf close > highest high of prior breakout_lookback bars
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from us_swing.analysis.indicators import atr, ema_value
from us_swing.data.models import OHLCVBar, TradeSignal

# Avoid import cycle: StrategyConfig imported at call time via TYPE_CHECKING

if TYPE_CHECKING:
    from us_swing.analysis.strategy_engine import StrategyConfig

_log = logging.getLogger(__name__)


class BreakoutStrategy:
    """Multi-timeframe breakout entry strategy."""

    strategy_id = "breakout"

    def evaluate(
        self,
        symbol: str,
        bar_cache: dict[str, list[OHLCVBar]],
        config: "StrategyConfig",
    ) -> TradeSignal | None:
        """Evaluate breakout entry for *symbol*.

        Args:
            symbol:    Ticker symbol.
            bar_cache: Dict of tf -> list[OHLCVBar] (newest at end).
            config:    Active strategy configuration.

        Returns:
            BUY :class:`TradeSignal` or ``None``.
        """
        breakout_bars = bar_cache.get(config.breakout_tf, [])
        h1_bars = bar_cache.get("1h", [])

        min_bars = config.breakout_lookback + 1
        if len(h1_bars) < min_bars or len(breakout_bars) < min_bars:
            return None

        # Trend filter: 1h close must be above 1h EMA(50)
        if h1_bars[-1].close <= ema_value(h1_bars, 50):
            return None

        # Entry filter: current close > highest high of prior lookback bars
        prior = breakout_bars[-(config.breakout_lookback + 1):-1]
        if len(prior) < config.breakout_lookback:
            return None
        highest_high = max(b.high for b in prior)
        current = breakout_bars[-1]
        if current.close <= highest_high:
            return None

        # Build signal
        entry = current.close
        atr_val = atr(breakout_bars, 14)
        stop = entry - atr_val * config.atr_multiplier
        target = entry + (entry - stop) * config.r_multiple

        _log.info("breakout signal: %s entry=%.2f stop=%.2f target=%.2f", symbol, entry, stop, target)
        return TradeSignal(
            symbol=symbol,
            side="BUY",
            strategy_id=self.strategy_id,
            score=1.0,
            entry_price=entry,
            stop_loss=max(stop, 0.01),
            target_price=target,
        )
