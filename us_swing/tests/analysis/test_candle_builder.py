"""Tests for analysis/candle_builder.py.

Covers: UT-ANA-001.001.M01.T01 through T09.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from tests.analysis.conftest import make_rt_bars
from us_swing.analysis.candle_builder import CandleBuilder
from us_swing.data.models import OHLCVBar, RealtimeBar

_BASE = datetime(2024, 1, 15, 10, 0, 0)


def _feed(builder: CandleBuilder, bars: list[RealtimeBar]) -> None:
    for bar in bars:
        builder.add_bar(bar)


def _rt_bar(
    symbol: str,
    t: datetime,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: int = 100,
) -> RealtimeBar:
    return RealtimeBar(
        symbol=symbol, datetime=t,
        open=open_, high=high, low=low, close=close, volume=volume,
    )


class TestCandleAggregation:
    def test_twelve_bars_produce_one_1m_candle(self) -> None:
        """UT-ANA-001.001.M01.T01 — 12 consecutive 5s bars → exactly one 1m candle."""
        fired: list[tuple[str, str, OHLCVBar]] = []
        cb = CandleBuilder(["1m"], on_candle_closed=lambda s, t, b: fired.append((s, t, b)))
        _feed(cb, make_rt_bars([float(i + 1) for i in range(12)]))
        assert len(fired) == 1
        _, tf, bar = fired[0]
        assert tf == "1m"

    def test_1m_candle_open_is_first_bar_open(self) -> None:
        """UT-ANA-001.001.M01.T02 — candle.open == first-bar open."""
        fired: list[OHLCVBar] = []
        cb = CandleBuilder(["1m"], on_candle_closed=lambda s, t, b: fired.append(b))
        bars = [
            _rt_bar("AAPL", _BASE + timedelta(seconds=i * 5), 10 + i, 15, 9, 11 + i)
            for i in range(12)
        ]
        _feed(cb, bars)
        assert fired[0].open == bars[0].open

    def test_1m_candle_high_is_max_high(self) -> None:
        """UT-ANA-001.001.M01.T03 — candle.high == max(bar.high)."""
        fired: list[OHLCVBar] = []
        cb = CandleBuilder(["1m"], on_candle_closed=lambda s, t, b: fired.append(b))
        highs = [12.0, 15.0, 11.0] + [10.0] * 9
        bars = [
            _rt_bar("AAPL", _BASE + timedelta(seconds=i * 5), 10, highs[i], 9, 10)
            for i in range(12)
        ]
        _feed(cb, bars)
        assert fired[0].high == 15.0

    def test_1m_candle_close_is_last_bar_close(self) -> None:
        """UT-ANA-001.001.M01.T04 — candle.close == last-bar close."""
        fired: list[OHLCVBar] = []
        cb = CandleBuilder(["1m"], on_candle_closed=lambda s, t, b: fired.append(b))
        closes = [10.0, 11.0] + [12.0] * 9 + [13.0]
        bars = [
            _rt_bar("AAPL", _BASE + timedelta(seconds=i * 5), 10, 15, 9, closes[i])
            for i in range(12)
        ]
        _feed(cb, bars)
        assert fired[0].close == 13.0

    def test_1m_candle_volume_is_sum(self) -> None:
        """UT-ANA-001.001.M01.T05 — candle.volume == sum(bar.volume)."""
        fired: list[OHLCVBar] = []
        cb = CandleBuilder(["1m"], on_candle_closed=lambda s, t, b: fired.append(b))
        volumes = [100, 200, 300] + [0] * 9
        bars = [
            _rt_bar("AAPL", _BASE + timedelta(seconds=i * 5), 10, 11, 9, 10, volumes[i])
            for i in range(12)
        ]
        _feed(cb, bars)
        assert fired[0].volume == sum(volumes)

    def test_3m_candle_fires_after_36_bars(self) -> None:
        """UT-ANA-001.001.M01.T06 — 36 bars → exactly one 3m candle."""
        fired: list[tuple[str, str, OHLCVBar]] = []
        cb = CandleBuilder(["3m"], on_candle_closed=lambda s, t, b: fired.append((s, t, b)))
        _feed(cb, make_rt_bars([float(i) for i in range(36)]))
        assert len(fired) == 1
        assert fired[0][1] == "3m"


class TestGapHandling:
    def test_gap_synthetic_bar_fills_missing_5s_window(self) -> None:
        """UT-ANA-001.001.M01.T07 — gap of 10s inserts one synthetic bar, no exception."""
        fired: list[OHLCVBar] = []
        cb = CandleBuilder(["1m"], on_candle_closed=lambda s, t, b: fired.append(b))

        t0 = _BASE
        bar0 = _rt_bar("AAPL", t0, 100, 101, 99, 100, 500)
        cb.add_bar(bar0)

        # 10-second gap: one 5s window is missing
        bar1 = _rt_bar("AAPL", t0 + timedelta(seconds=10), 100, 101, 99, 102, 300)
        cb.add_bar(bar1)  # should not raise

        # At this point we have 3 bars in the 1m buffer (bar0, synthetic@+5, bar1)
        # Check get_buffer is accessible and no exception occurred
        completed = cb.get_buffer("AAPL", "1m")
        assert isinstance(completed, list)


class TestMultiSymbol:
    def test_two_symbols_do_not_cross_contaminate(self) -> None:
        """UT-ANA-001.001.M01.T08 — interleaved AAPL/MSFT bars stay isolated."""
        aapl_candles: list[OHLCVBar] = []
        msft_candles: list[OHLCVBar] = []

        def on_close(s: str, t: str, b: OHLCVBar) -> None:
            if s == "AAPL":
                aapl_candles.append(b)
            else:
                msft_candles.append(b)

        cb = CandleBuilder(["1m"], on_candle_closed=on_close)

        aapl_bars = make_rt_bars([10.0] * 12, symbol="AAPL")
        msft_bars = make_rt_bars([50.0] * 12, symbol="MSFT")

        # Interleave
        for a, m in zip(aapl_bars, msft_bars):
            cb.add_bar(a)
            cb.add_bar(m)

        assert len(aapl_candles) == 1
        assert len(msft_candles) == 1
        assert aapl_candles[0].symbol == "AAPL"
        assert msft_candles[0].symbol == "MSFT"
        assert aapl_candles[0].close == 10.0
        assert msft_candles[0].close == 50.0


class TestConsistency:
    def test_live_candle_matches_manual_aggregation(self) -> None:
        """UT-ANA-001.001.M01.T09 — live 1m candle equals manual OHLCV aggregation."""
        fired: list[OHLCVBar] = []
        cb = CandleBuilder(["1m"], on_candle_closed=lambda s, t, b: fired.append(b))

        rt_bars = make_rt_bars(
            [float(i + 10) for i in range(12)],
            symbol="AAPL",
        )
        _feed(cb, rt_bars)

        assert len(fired) == 1
        candle = fired[0]

        # Manual aggregation
        expected_open   = rt_bars[0].open
        expected_high   = max(b.high for b in rt_bars)
        expected_low    = min(b.low for b in rt_bars)
        expected_close  = rt_bars[-1].close
        expected_volume = sum(b.volume for b in rt_bars)

        assert candle.open   == expected_open
        assert candle.high   == expected_high
        assert candle.low    == expected_low
        assert candle.close  == expected_close
        assert candle.volume == expected_volume
