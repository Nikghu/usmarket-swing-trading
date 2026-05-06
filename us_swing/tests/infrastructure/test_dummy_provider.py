"""Unit tests — MD-INF-007.001.M02 DummyProvider.

Refs: UT-INF-007.001.M02.T01 – T04
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from us_swing.data.models import OHLCVBar, RealtimeBar
from us_swing.data.providers.dummy_provider import DummyProvider


async def test_T01_req_historical_data_returns_valid_bars() -> None:
    """UT-INF-007.001.M02.T01 — req_historical_data() returns non-empty list of OHLCVBar."""
    provider = DummyProvider(seed=42)
    end = datetime.now(tz=timezone.utc)
    bars = await provider.req_historical_data("AAPL", end, "1 Y", "1 day")
    assert len(bars) > 0
    assert all(isinstance(b, OHLCVBar) for b in bars)
    assert all(b.symbol == "AAPL" for b in bars)
    assert all(isinstance(b.datetime, datetime) for b in bars)


async def test_T02_all_bars_satisfy_ohlcv_constraints() -> None:
    """UT-INF-007.001.M02.T02 — every bar satisfies low <= open, close and high >= open, close."""
    provider = DummyProvider(seed=99)
    end = datetime.now(tz=timezone.utc)
    bars = await provider.req_historical_data("MSFT", end, "1 Y", "1 day")
    for b in bars:
        assert b.low  <= b.open,  f"low > open for {b}"
        assert b.low  <= b.close, f"low > close for {b}"
        assert b.high >= b.open,  f"high < open for {b}"
        assert b.high >= b.close, f"high < close for {b}"
        assert b.volume >= 0,     f"negative volume for {b}"


async def test_T03_same_seed_produces_identical_bars() -> None:
    """UT-INF-007.001.M02.T03 — two providers with same seed return equal bar sequences."""
    end = datetime.now(tz=timezone.utc)
    bars_a = await DummyProvider(seed=42).req_historical_data("AAPL", end, "1 Y", "1 day")
    bars_b = await DummyProvider(seed=42).req_historical_data("AAPL", end, "1 Y", "1 day")
    assert len(bars_a) == len(bars_b)
    for a, b in zip(bars_a, bars_b):
        assert a.open   == b.open
        assert a.high   == b.high
        assert a.low    == b.low
        assert a.close  == b.close
        assert a.volume == b.volume


async def test_T04_subscribe_realtime_bars_emits_via_callback() -> None:
    """UT-INF-007.001.M02.T04 — subscribe_realtime_bars() delivers ≥1 RealtimeBar via callback."""
    provider = DummyProvider(seed=7, realtime_interval_s=0.05)
    received: list[RealtimeBar] = []
    provider.on_realtime_bar(received.append)
    provider.subscribe_realtime_bars("AAPL")
    await asyncio.sleep(0.3)   # allow ~6 emissions at 0.05s interval
    provider.unsubscribe_realtime_bars("AAPL")
    assert len(received) >= 1
    assert all(isinstance(b, RealtimeBar) for b in received)
