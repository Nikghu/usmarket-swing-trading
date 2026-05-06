"""Tests for strategy_engine.py, BreakoutStrategy, PullbackStrategy, ExitManager.

Covers:
  UT-ANA-002.001.M01.T01–T02  (StrategyEngine + BreakoutStrategy)
  UT-ANA-002.001.M02.T01–T02  (BreakoutStrategy)
  UT-ANA-002.001.M03.T01–T02  (PullbackStrategy)
  UT-ANA-002.001.M04.T01–T04  (ExitManager)
  UT-ANA-003.001.M01.T01–T04  (StrategyConfig per-user)
"""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from tests.analysis.conftest import make_ohlcv_series, make_open_position
from us_swing.analysis.exit_manager import ExitManager
from us_swing.analysis.strategies.breakout import BreakoutStrategy
from us_swing.analysis.strategies.pullback import PullbackStrategy
from us_swing.analysis.strategy_engine import StrategyConfig, StrategyEngine
from us_swing.data.models import OHLCVBar

_BASE = datetime(2024, 1, 15, 10, 0, 0)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_bars(
    closes: list[float],
    tf: str = "15m",
    symbol: str = "AAPL",
    highs: list[float] | None = None,
    lows: list[float] | None = None,
) -> list[OHLCVBar]:
    return make_ohlcv_series(closes, symbol=symbol, tf=tf, highs=highs, lows=lows)


def _default_config(**overrides) -> StrategyConfig:
    cfg = StrategyConfig()
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


# ── BreakoutStrategy ──────────────────────────────────────────────────────────

class TestBreakoutStrategy:
    def _bar_cache_with_trend_and_breakout(self, config: StrategyConfig) -> dict:
        """Build a bar cache that satisfies the breakout conditions."""
        n = config.breakout_lookback + 2  # need lookback+1 bars minimum

        # 1h bars: increasing closes so last close > EMA50
        h1_bars = _make_bars([100.0 + i for i in range(n)], tf="1h")

        # breakout TF bars: prior lookback bars all have high=99, last bar close=101
        prior_closes = [98.0] * config.breakout_lookback
        last_close = [101.0]
        prior_highs = [99.0] * config.breakout_lookback
        last_high = [101.5]
        btf_bars = _make_bars(
            prior_closes + last_close,
            tf=config.breakout_tf,
            highs=prior_highs + last_high,
        )

        return {"1h": h1_bars, config.breakout_tf: btf_bars}

    def test_buy_signal_when_trend_and_breakout(self) -> None:
        """UT-ANA-002.001.M02.T01 — BUY when 1h trend + breakout TF breakout."""
        config = _default_config()
        cache = self._bar_cache_with_trend_and_breakout(config)
        strategy = BreakoutStrategy()
        signal = strategy.evaluate("AAPL", cache, config)
        assert signal is not None
        assert signal.side == "BUY"
        assert signal.strategy_id == "breakout"

    def test_no_signal_when_insufficient_bars(self) -> None:
        """UT-ANA-002.001.M02.T02 — None when only 15 bars in 1h cache (< 21)."""
        config = _default_config()
        h1_bars = _make_bars([100.0 + i for i in range(15)], tf="1h")
        btf_bars = _make_bars([100.0] * 21, tf=config.breakout_tf)
        cache = {"1h": h1_bars, config.breakout_tf: btf_bars}
        strategy = BreakoutStrategy()
        assert strategy.evaluate("AAPL", cache, config) is None

    def test_no_signal_when_trend_filter_fails(self) -> None:
        """UT-ANA-002.001.M01.T01 — None when 1h close < EMA50."""
        config = _default_config()
        n = config.breakout_lookback + 2
        # Declining 1h: last close is BELOW EMA (seeded high, falling fast)
        h1_closes = [200.0 - i * 5 for i in range(n)]  # e.g. 200,195,...
        h1_bars = _make_bars(h1_closes, tf="1h")
        btf_bars = _make_bars([98.0] * config.breakout_lookback + [101.0], tf=config.breakout_tf)
        cache = {"1h": h1_bars, config.breakout_tf: btf_bars}
        strategy = BreakoutStrategy()
        assert strategy.evaluate("AAPL", cache, config) is None

    def test_signal_prices_valid(self) -> None:
        """UT-ANA-002.001.M04.T04 — target > entry > stop for BUY."""
        config = _default_config()
        cache = self._bar_cache_with_trend_and_breakout(config)
        strategy = BreakoutStrategy()
        signal = strategy.evaluate("AAPL", cache, config)
        assert signal is not None
        assert signal.target_price > signal.entry_price > signal.stop_loss


# ── PullbackStrategy ──────────────────────────────────────────────────────────

class TestPullbackStrategy:
    def _bar_cache_with_cross(self) -> dict:
        """Build a cache with an uptrend and a 5m EMA21 cross-above."""
        # 1h uptrend: 21 increasing bars, so last close > EMA21
        h1_bars = _make_bars([100.0 + i for i in range(21)], tf="1h")

        # 5m bars: 20 flat at 100, then dip to 90 (prev below EMA), then 120 (curr above EMA)
        # EMA21 seeded at 100 and stays ~100 for flat bars; after dip EMA ≈ 99.something
        # We need: prev_close < prev_ema AND curr_close > curr_ema
        m5_flat = [100.0] * 20
        m5_bars = _make_bars(m5_flat + [90.0, 120.0], tf="5m")
        return {"1h": h1_bars, "5m": m5_bars}

    def test_buy_signal_on_ema21_cross_above(self) -> None:
        """UT-ANA-002.001.M03.T01 — BUY on EMA21 cross-above with uptrend."""
        cache = self._bar_cache_with_cross()
        strategy = PullbackStrategy()
        config = _default_config()
        signal = strategy.evaluate("AAPL", cache, config)
        assert signal is not None
        assert signal.side == "BUY"
        assert signal.strategy_id == "pullback"

    def test_no_signal_when_1h_trend_fails(self) -> None:
        """UT-ANA-002.001.M03.T02 — None when 1h close < EMA21."""
        # Declining 1h: last close < EMA (seeded high, falling)
        h1_bars = _make_bars([200.0 - i * 8 for i in range(21)], tf="1h")
        m5_bars = _make_bars([100.0] * 20 + [90.0, 120.0], tf="5m")
        cache = {"1h": h1_bars, "5m": m5_bars}
        strategy = PullbackStrategy()
        assert strategy.evaluate("AAPL", cache, _default_config()) is None

    def test_no_signal_insufficient_bars(self) -> None:
        h1_bars = _make_bars([100.0] * 10, tf="1h")  # < 21
        m5_bars = _make_bars([100.0] * 22, tf="5m")
        cache = {"1h": h1_bars, "5m": m5_bars}
        assert PullbackStrategy().evaluate("AAPL", cache, _default_config()) is None


# ── StrategyEngine (entry suppression) ───────────────────────────────────────

class TestStrategyEngine:
    def test_no_signal_when_existing_position(self) -> None:
        """UT-ANA-002.001.M01.T02 — signal suppressed when user has open position."""
        tracker = MagicMock()
        tracker.has_open.return_value = True

        engine = StrategyEngine(user_id=1, config=_default_config(), position_tracker=tracker)

        # Feed enough bars to potentially trigger breakout
        n = 22
        h1_bars = _make_bars([100.0 + i for i in range(n)], tf="1h")
        for bar in h1_bars:
            engine.on_candle_closed("AAPL", "1h", bar)

        btf_bars = _make_bars(
            [98.0] * 20 + [101.0],
            tf="15m",
            highs=[99.0] * 20 + [101.5],
        )
        signal = None
        for bar in btf_bars:
            signal = engine.on_candle_closed("AAPL", "15m", bar)

        assert signal is None
        tracker.has_open.assert_called()

    def test_disabled_breakout_not_evaluated(self) -> None:
        """UT-ANA-003.001.M01.T03 — breakout disabled → no BUY from breakout."""
        config = _default_config(breakout_enabled=False, pullback_enabled=False)
        engine = StrategyEngine(user_id=1, config=config)

        # Feed bars that would trigger breakout
        n = 22
        h1_bars = _make_bars([100.0 + i for i in range(n)], tf="1h")
        for bar in h1_bars:
            engine.on_candle_closed("AAPL", "1h", bar)

        btf_bars = _make_bars(
            [98.0] * 20 + [101.0], tf="15m", highs=[99.0] * 20 + [101.5]
        )
        signals = [engine.on_candle_closed("AAPL", "15m", b) for b in btf_bars]
        assert all(s is None for s in signals)


# ── StrategyConfig per-user ───────────────────────────────────────────────────

class TestStrategyConfig:
    def test_from_user_settings_loads_overrides(self) -> None:
        """UT-ANA-003.001.M01.T01 — partial dict overrides specific fields."""
        cfg = StrategyConfig.from_user_settings(
            {"breakout_enabled": False, "r_multiple": 3.0}
        )
        assert cfg.breakout_enabled is False
        assert cfg.r_multiple == 3.0
        # Others remain at defaults
        assert cfg.pullback_enabled is True
        assert cfg.atr_multiplier == 1.5

    def test_from_user_settings_empty_gives_defaults(self) -> None:
        """UT-ANA-003.001.M01.T02 — empty dict → all defaults."""
        cfg = StrategyConfig.from_user_settings({})
        default = StrategyConfig()
        assert cfg.breakout_enabled == default.breakout_enabled
        assert cfg.r_multiple       == default.r_multiple
        assert cfg.atr_multiplier   == default.atr_multiplier

    def test_different_users_different_signals(self) -> None:
        """UT-ANA-003.001.M01.T04 — user A (breakout on) gets signal; user B does not."""
        config_a = StrategyConfig.from_user_settings({"breakout_enabled": True, "pullback_enabled": False})
        config_b = StrategyConfig.from_user_settings({"breakout_enabled": False, "pullback_enabled": False})

        engine_a = StrategyEngine(user_id=1, config=config_a)
        engine_b = StrategyEngine(user_id=2, config=config_b)

        n = 22
        h1_bars = _make_bars([100.0 + i for i in range(n)], tf="1h")
        for bar in h1_bars:
            engine_a.on_candle_closed("AAPL", "1h", bar)
            engine_b.on_candle_closed("AAPL", "1h", bar)

        btf_bars = _make_bars(
            [98.0] * 20 + [101.0], tf="15m", highs=[99.0] * 20 + [101.5]
        )
        sig_a = sig_b = None
        for bar in btf_bars:
            sig_a = engine_a.on_candle_closed("AAPL", "15m", bar)
            sig_b = engine_b.on_candle_closed("AAPL", "15m", bar)

        assert sig_a is not None, "User A should get a breakout signal"
        assert sig_b is None,     "User B should get no signal (breakout disabled)"

    def test_validate_rejects_negative_atr_multiplier(self) -> None:
        cfg = StrategyConfig(atr_multiplier=-1.0)
        with pytest.raises(ValueError, match="atr_multiplier"):
            cfg.validate()


# ── ExitManager ───────────────────────────────────────────────────────────────

class TestExitManager:
    def _bar_cache(self, closes: list[float], tf: str = "15m") -> dict:
        return {tf: _make_bars(closes, tf=tf, highs=[c + 0.5 for c in closes],
                               lows=[c - 0.5 for c in closes])}

    def test_stop_loss_exit(self) -> None:
        """UT-ANA-002.001.M04.T01 — SELL(stop_loss) when close ≤ stop_loss."""
        from tests.analysis.conftest import make_ohlcv
        mgr = ExitManager()
        position = make_open_position(stop_loss=50.0, target_price=200.0)
        bar = make_ohlcv(close=49.5, tf="15m")
        signal = mgr.evaluate("AAPL", bar, position, {}, _default_config())
        assert signal is not None
        assert signal.side == "SELL"
        assert signal.strategy_id == "stop_loss"

    def test_target_exit(self) -> None:
        """UT-ANA-002.001.M04.T02 — SELL(target) when close ≥ target_price."""
        from tests.analysis.conftest import make_ohlcv
        mgr = ExitManager()
        position = make_open_position(stop_loss=50.0, target_price=103.0)
        bar = make_ohlcv(close=104.0, tf="15m")
        signal = mgr.evaluate("AAPL", bar, position, {}, _default_config())
        assert signal is not None
        assert signal.side == "SELL"
        assert signal.strategy_id == "target"

    def test_trailing_stop_only_advances(self) -> None:
        """UT-ANA-002.001.M04.T03 — trail moves to 108 (max−offset=2); never retreats."""
        from tests.analysis.conftest import make_ohlcv
        # Setup: entry=100, stop=90, R=10, activation_r=1.0 → activates at 110
        # ATR of flat bars (h=c+0.5, l=c-0.5) = 1.0; trail_multiplier=2 → trail_offset=2
        config = _default_config(activation_r=1.0, trail_multiplier=2.0)
        position = make_open_position(
            average_price=100.0, stop_loss=90.0, trailing_stop=0.0
        )
        flat_bars = _make_bars([100.0] * 20, tf="15m",
                               highs=[100.5] * 20, lows=[99.5] * 20)
        bar_cache = {"15m": flat_bars}

        mgr = ExitManager()

        # Bar at 110 — activates trail; trail = 110 - 1.0*2 = 108
        bar_110 = make_ohlcv(close=110.0, tf="15m", high=110.5, low=109.5)
        mgr.update_trailing_stop("AAPL", bar_110, position, bar_cache, config)
        assert abs(position.trailing_stop - 108.0) < 1e-9

        # Bar at 108 — price drops; trail stays at 108 (never retreats)
        bar_108 = make_ohlcv(close=108.0, tf="15m", high=108.5, low=107.5)
        mgr.update_trailing_stop("AAPL", bar_108, position, bar_cache, config)
        assert position.trailing_stop >= 108.0 - 1e-9  # did not decrease

    def test_signal_prices_valid_for_buy(self) -> None:
        """UT-ANA-002.001.M04.T04 — produced BUY signal has target > entry > stop."""
        config = _default_config()
        n = 22
        h1_bars = _make_bars([100.0 + i for i in range(n)], tf="1h")
        btf_bars = _make_bars(
            [98.0] * 20 + [101.0], tf="15m", highs=[99.0] * 20 + [101.5]
        )
        cache = {"1h": h1_bars, "15m": btf_bars}
        signal = BreakoutStrategy().evaluate("AAPL", cache, config)
        assert signal is not None
        assert signal.target_price > signal.entry_price > signal.stop_loss
