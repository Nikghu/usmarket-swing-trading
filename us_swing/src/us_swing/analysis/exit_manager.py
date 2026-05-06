"""Module: MD-ANA-002.001.M04 — analysis/exit_manager.py
Parent SRD: SRD-ANA-002.005–006

ExitManager evaluates stop-loss, take-profit, and ATR trailing-stop exit
conditions for open positions. Only one SELL signal is emitted per evaluation
cycle. Trailing-stop activation and updates are logged at DEBUG level.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from us_swing.analysis.indicators import atr
from us_swing.data.models import OHLCVBar, OpenPosition, TradeSignal

if TYPE_CHECKING:
    from us_swing.analysis.strategy_engine import StrategyConfig

log = logging.getLogger(__name__)


class ExitManager:
    """Evaluates exit conditions for open positions.

    Maintains per-symbol highest-close state for trailing-stop tracking.
    """

    def __init__(self) -> None:
        # _trailing_highs[symbol] = highest close seen since trail activation
        self._trailing_highs: dict[str, float] = {}

    def evaluate(
        self,
        symbol: str,
        bar: OHLCVBar,
        position: OpenPosition,
        bar_cache: dict[str, list[OHLCVBar]],
        config: "StrategyConfig",
    ) -> TradeSignal | None:
        """Check stop-loss, target, and trailing-stop in priority order.

        Args:
            symbol:    Ticker symbol.
            bar:       Current completed candle.
            position:  Open position to evaluate.
            bar_cache: Dict of tf -> list[OHLCVBar] for ATR calculation.
            config:    Strategy configuration with exit parameters.

        Returns:
            SELL :class:`TradeSignal` or ``None``.
        """
        # 1. Hard stop-loss
        if bar.close <= position.stop_loss:
            return TradeSignal(
                symbol=symbol,
                side="SELL",
                strategy_id="stop_loss",
                score=1.0,
                entry_price=bar.close,
            )

        # 2. Take-profit target
        if position.target_price > 0 and bar.close >= position.target_price:
            return TradeSignal(
                symbol=symbol,
                side="SELL",
                strategy_id="target",
                score=1.0,
                entry_price=bar.close,
            )

        # 3. Trailing stop
        if position.trailing_stop > 0 and bar.close <= position.trailing_stop:
            return TradeSignal(
                symbol=symbol,
                side="SELL",
                strategy_id="trailing_stop",
                score=1.0,
                entry_price=bar.close,
            )

        return None

    def update_trailing_stop(
        self,
        symbol: str,
        bar: OHLCVBar,
        position: OpenPosition,
        bar_cache: dict[str, list[OHLCVBar]],
        config: "StrategyConfig",
    ) -> None:
        """Advance trailing stop upward if price moves above activation threshold.

        Trail = highest_close_seen − ATR(14) × trail_multiplier.
        Stop is never moved downward (SRD-ANA-002.006).

        Args:
            symbol:    Ticker symbol.
            bar:       Current completed candle.
            position:  Open position whose ``trailing_stop`` may be mutated.
            bar_cache: Dict of tf -> list[OHLCVBar] for ATR calculation.
            config:    Strategy configuration (activation_r, trail_multiplier).
        """
        r = position.average_price - position.stop_loss
        if r <= 0:
            return

        activation_price = position.average_price + config.activation_r * r
        if bar.close < activation_price:
            return  # trail not yet activated

        # Track highest close since activation
        prev_high = self._trailing_highs.get(symbol, bar.close)
        current_high = max(prev_high, bar.close)
        self._trailing_highs[symbol] = current_high

        # Compute new trail using ATR from current bar's timeframe cache
        tf_bars = bar_cache.get(bar.timeframe, [])
        atr_val = atr(tf_bars, 14) if len(tf_bars) >= 2 else 0.0
        new_trail = current_high - atr_val * config.trail_multiplier

        # Only advance — never retract
        if new_trail > position.trailing_stop:
            log.debug(
                "Trail updated for %s: %.4f → %.4f (highest=%.4f, ATR=%.4f)",
                symbol,
                position.trailing_stop,
                new_trail,
                current_high,
                atr_val,
            )
            position.trailing_stop = new_trail
