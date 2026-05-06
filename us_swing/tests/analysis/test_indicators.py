"""Tests for analysis/indicators.py.

Covers: UT-ANA-001.001.M04.T01 through T04.
"""
from __future__ import annotations

import math

import pytest

from tests.analysis.conftest import make_ohlcv_series
from us_swing.analysis.indicators import atr, ema, ema_value, rsi


class TestEMA:
    def test_ema_value_matches_seed_recursive_formula(self) -> None:
        """UT-ANA-001.001.M04.T01 — ema(bars, 3) on [10,11,12,13] ≈ 12.375."""
        bars = make_ohlcv_series([10.0, 11.0, 12.0, 13.0])
        result = ema(bars, 3)
        # k = 2/(3+1) = 0.5; seed=10; 10→10, 11→10.5, 12→11.25, 13→12.125
        # Note: UTCD listed 12.375 (arithmetic error) — correct value is 12.125
        assert abs(result[-1] - 12.125) < 1e-9

    def test_ema_length_matches_bars(self) -> None:
        bars = make_ohlcv_series([1.0, 2.0, 3.0, 4.0, 5.0])
        assert len(ema(bars, 3)) == 5

    def test_ema_empty_returns_empty(self) -> None:
        assert ema([], 3) == []

    def test_ema_value_nan_on_empty(self) -> None:
        assert math.isnan(ema_value([], 3))


class TestATR:
    def test_atr_positive_for_varying_bars(self) -> None:
        """UT-ANA-001.001.M04.T02 — ATR(14) > 0 for 30 bars with varied Hi/Lo."""
        import random
        random.seed(42)
        closes = [100.0 + random.uniform(-2, 2) for _ in range(30)]
        bars = make_ohlcv_series(
            closes,
            highs=[c + random.uniform(0.5, 2.0) for c in closes],
            lows=[c - random.uniform(0.5, 2.0) for c in closes],
        )
        result = atr(bars, 14)
        assert result > 0

    def test_atr_zero_for_fewer_than_two_bars(self) -> None:
        bars = make_ohlcv_series([100.0])
        assert atr(bars, 14) == 0.0

    def test_atr_uses_true_range_formula(self) -> None:
        # Bars with h=c+0.5, l=c-0.5, constant close → TR = 1.0 → ATR = 1.0
        bars = make_ohlcv_series(
            [100.0] * 20,
            highs=[100.5] * 20,
            lows=[99.5] * 20,
        )
        assert abs(atr(bars, 14) - 1.0) < 1e-9


class TestRSI:
    def test_rsi_returns_value_in_range_with_exact_period_bars(self) -> None:
        """UT-ANA-001.001.M04.T03 — rsi(14 bars) returns value in [0, 100]."""
        closes = [100.0 + i for i in range(14)]
        bars = make_ohlcv_series(closes)
        result = rsi(bars, 14)
        assert not math.isnan(result)
        assert 0.0 <= result <= 100.0

    def test_rsi_nan_when_fewer_than_period_bars(self) -> None:
        """UT-ANA-001.001.M04.T04 — rsi() with 10 bars (< 14) → NaN."""
        bars = make_ohlcv_series([100.0 + i for i in range(10)])
        result = rsi(bars, 14)
        assert math.isnan(result)

    def test_rsi_100_when_all_gains(self) -> None:
        bars = make_ohlcv_series([float(i) for i in range(1, 20)])
        result = rsi(bars, 14)
        assert result == 100.0

    def test_rsi_0_when_all_losses(self) -> None:
        bars = make_ohlcv_series([float(20 - i) for i in range(20)])
        result = rsi(bars, 14)
        assert result == 0.0
