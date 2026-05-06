"""Module: MD-ANA-002.001.M01 — analysis/strategy_engine.py
Parent SRD: SRD-ANA-002.001, SRD-ANA-002.007–008, SRD-ANA-003.001–002

StrategyEngine maintains a per-symbol bar cache, evaluates all enabled
strategies on each candle close, and suppresses duplicate entry signals
for users with existing open positions.

StrategyConfig is co-located here as it is the primary configuration
surface for the engine and its plugins.
"""
from __future__ import annotations

import dataclasses
import logging
from typing import Protocol, runtime_checkable

from us_swing.data.models import OHLCVBar, TradeSignal

log = logging.getLogger(__name__)


# ── Protocols ─────────────────────────────────────────────────────────────────

@runtime_checkable
class PositionTrackerProtocol(Protocol):
    """Minimal interface StrategyEngine needs from EXE's PositionTracker."""

    def has_open(self, user_id: int, symbol: str) -> bool:
        """Return True if *user_id* has an open position in *symbol*."""
        ...


@runtime_checkable
class StrategyProtocol(Protocol):
    """Interface all strategy plugins must satisfy."""

    def evaluate(
        self,
        symbol: str,
        bar_cache: dict[str, list[OHLCVBar]],
        config: "StrategyConfig",
    ) -> TradeSignal | None:
        """Evaluate signal for *symbol* from the given bar cache."""
        ...


# ── StrategyConfig ────────────────────────────────────────────────────────────

@dataclasses.dataclass
class StrategyConfig:
    """Per-user strategy parameters loaded from settings_json.

    All numeric fields must be > 0 (enforced by :meth:`validate`).
    """

    breakout_enabled:  bool  = True
    pullback_enabled:  bool  = True
    atr_multiplier:    float = 1.5
    r_multiple:        float = 2.0
    trail_multiplier:  float = 1.0
    activation_r:      float = 1.0
    breakout_tf:       str   = "15m"
    breakout_lookback: int   = 20
    cache_size:        int   = 50

    @classmethod
    def from_user_settings(cls, settings: dict) -> "StrategyConfig":
        """Build a StrategyConfig from a parsed settings dict.

        Unknown keys are ignored; missing keys fall back to defaults.

        Args:
            settings: Parsed dict from ``user.settings_json["strategy_config"]``.

        Returns:
            Populated :class:`StrategyConfig` instance.
        """
        cfg = cls()
        for f in dataclasses.fields(cfg):
            if f.name in settings:
                setattr(cfg, f.name, settings[f.name])
        return cfg

    def validate(self) -> None:
        """Raise ValueError for any out-of-range field."""
        if self.atr_multiplier <= 0:
            raise ValueError(f"atr_multiplier must be > 0, got {self.atr_multiplier}")
        if self.r_multiple <= 0:
            raise ValueError(f"r_multiple must be > 0, got {self.r_multiple}")
        if self.trail_multiplier <= 0:
            raise ValueError(f"trail_multiplier must be > 0, got {self.trail_multiplier}")
        if self.activation_r <= 0:
            raise ValueError(f"activation_r must be > 0, got {self.activation_r}")


# ── StrategyEngine ────────────────────────────────────────────────────────────

class StrategyEngine:
    """Evaluates all enabled strategies on each candle close.

    Args:
        user_id:          ID of the user this engine instance serves.
        config:           Per-user strategy configuration (defaults applied if None).
        position_tracker: Optional tracker; if provided, suppresses entry signals
                          when the user already has an open position in the symbol.
    """

    def __init__(
        self,
        user_id: int,
        config: StrategyConfig | None = None,
        position_tracker: PositionTrackerProtocol | None = None,
    ) -> None:
        self._user_id = user_id
        self._config = config or StrategyConfig()
        self._position_tracker = position_tracker

        # Lazy imports to avoid circular resolution at package load time
        from us_swing.analysis.strategies.breakout import BreakoutStrategy
        from us_swing.analysis.strategies.pullback import PullbackStrategy

        self._strategies: list[StrategyProtocol] = []
        if self._config.breakout_enabled:
            self._strategies.append(BreakoutStrategy())
        if self._config.pullback_enabled:
            self._strategies.append(PullbackStrategy())

        # bar_cache[symbol][tf] = list of last N OHLCVBars (newest at end)
        self._bar_cache: dict[str, dict[str, list[OHLCVBar]]] = {}

    def on_candle_closed(
        self, symbol: str, tf: str, bar: OHLCVBar
    ) -> TradeSignal | None:
        """Update bar cache and evaluate all enabled strategies.

        Evaluation must complete < 50 ms per symbol (SRD-ANA-002.001).

        Args:
            symbol: Ticker symbol.
            tf:     Timeframe string (e.g. ``"15m"``).
            bar:    The newly completed candle.

        Returns:
            First non-None :class:`TradeSignal`, or ``None`` if no signal fired.
        """
        # Update bar cache
        sym_cache = self._bar_cache.setdefault(symbol, {})
        tf_cache = sym_cache.setdefault(tf, [])
        tf_cache.append(bar)
        if len(tf_cache) > self._config.cache_size:
            tf_cache.pop(0)

        # Suppress entry for this user if an open position already exists
        if self._position_tracker and self._position_tracker.has_open(
            self._user_id, symbol
        ):
            log.debug(
                "Signal suppressed for %s (user=%d): existing position",
                symbol,
                self._user_id,
            )
            return None

        # Evaluate strategies in registration order; return first signal
        for strategy in self._strategies:
            signal = strategy.evaluate(symbol, sym_cache, self._config)
            if signal is not None:
                log.info(
                    "Signal: %s %s %s @ %.4f SL=%.4f TP=%.4f TF=%s",
                    signal.strategy_id,
                    signal.side,
                    symbol,
                    signal.entry_price,
                    signal.stop_loss,
                    signal.target_price,
                    tf,
                )
                return signal
        return None
