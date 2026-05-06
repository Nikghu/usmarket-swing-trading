"""Unit tests — MD-INF-003.001.M01 HistoricalDataEngine.

Refs: UT-INF-003.001.M01.T01 – T05
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from us_swing.config.settings import DataConfig
from us_swing.data.engine import HistoricalDataEngine
from us_swing.data.models import OHLCVBar
from us_swing.db.manager import DatabaseManager
from us_swing.exceptions import CandleConsistencyError


def _make_engine(
    db: DatabaseManager,
    provider: object | None = None,
) -> HistoricalDataEngine:
    cfg = DataConfig(provider="dummy", max_concurrent_bootstrap=1)
    if provider is None:
        provider = MagicMock()
    return HistoricalDataEngine(provider=provider, db=db, cfg=cfg)


def _bar(dt: datetime, o: float, h: float, lo: float, c: float, v: int = 1000, tf: str = "1m") -> OHLCVBar:
    return OHLCVBar(symbol="TEST", datetime=dt, open=o, high=h, low=lo, close=c, volume=v, timeframe=tf)


BASE_DT = datetime(2025, 1, 1, 9, 30, tzinfo=timezone.utc)


def test_T01_aggregate_3m_from_three_1m_bars(in_memory_db: DatabaseManager) -> None:
    """UT-INF-003.001.M01.T01 — aggregate_timeframe() builds correct 3m bar."""
    bars = [
        _bar(BASE_DT + timedelta(minutes=0), o=10, h=12, lo=9,  c=11, v=100),
        _bar(BASE_DT + timedelta(minutes=1), o=11, h=13, lo=10, c=12, v=200),
        _bar(BASE_DT + timedelta(minutes=2), o=12, h=14, lo=11, c=13, v=300),
    ]
    engine = _make_engine(in_memory_db)
    result = engine.aggregate_timeframe("TEST", "3m", bars)

    assert len(result) == 1
    bar = result[0]
    assert bar.open   == 10
    assert bar.high   == 14
    assert bar.low    == 9
    assert bar.close  == 13
    assert bar.volume == 600


def test_T02_aggregate_incomplete_group_excluded(in_memory_db: DatabaseManager) -> None:
    """UT-INF-003.001.M01.T02 — incomplete trailing group (1 bar, target 3m) → empty result."""
    bars = [_bar(BASE_DT, o=10, h=12, lo=9, c=11, v=100)]
    engine = _make_engine(in_memory_db)
    result = engine.aggregate_timeframe("TEST", "3m", bars)
    assert result == []


async def test_T03_update_missing_data_fetches_only_new_bars(
    in_memory_db: DatabaseManager,
) -> None:
    """UT-INF-003.001.M01.T03 — update_missing_data() inserts only bars after last stored ts."""
    last_stored = datetime(2025, 6, 1, tzinfo=timezone.utc)

    # Seed all 3 TFs so bootstrap is not triggered.
    for tf in ("1m", "1d", "1w"):
        seed_bar = OHLCVBar(
            symbol="AAPL", datetime=last_stored,
            open=100, high=105, low=99, close=103, volume=1000, timeframe=tf,
        )
        in_memory_db.insert_bars("AAPL", tf, [seed_bar])

    # Provider returns 2 old bars + 2 new bars for every request.
    old_bars = [
        OHLCVBar("AAPL", last_stored - timedelta(days=1), 99, 102, 98, 101, 1000, "1d"),
        OHLCVBar("AAPL", last_stored, 100, 105, 99, 103, 1000, "1d"),
    ]
    new_bars = [
        OHLCVBar("AAPL", last_stored + timedelta(days=1), 104, 108, 103, 107, 1000, "1d"),
        OHLCVBar("AAPL", last_stored + timedelta(days=2), 107, 110, 106, 109, 1000, "1d"),
    ]
    mock_provider = MagicMock()
    mock_provider.req_historical_data = AsyncMock(return_value=old_bars + new_bars)
    engine = _make_engine(in_memory_db, provider=mock_provider)

    results = await engine.update_missing_data("AAPL")

    # Each UpdateResult.inserted should reflect only new bars (2 per TF call).
    assert all(r.inserted == 2 for r in results)


async def test_T04_update_missing_data_falls_back_to_bootstrap(
    in_memory_db: DatabaseManager,
) -> None:
    """UT-INF-003.001.M01.T04 — update_missing_data() calls bootstrap when no data exists."""
    mock_provider = MagicMock()
    mock_provider.req_historical_data = AsyncMock(return_value=[])
    engine = _make_engine(in_memory_db, provider=mock_provider)

    with patch.object(engine, "bootstrap_symbol", new=AsyncMock()) as mock_bootstrap:
        await engine.update_missing_data("AAPL")
        mock_bootstrap.assert_called_once_with("AAPL")


def test_T05_candle_consistency_identical_bars_do_not_raise(
    in_memory_db: DatabaseManager,
) -> None:
    """UT-INF-003.001.M01.T05 — assert_candle_consistency passes for equal bars, raises for mismatch."""
    engine = _make_engine(in_memory_db)
    bar_a = _bar(BASE_DT, o=10, h=14, lo=9, c=13, v=600, tf="3m")
    bar_b = _bar(BASE_DT, o=10, h=14, lo=9, c=13, v=600, tf="3m")

    engine.assert_candle_consistency(bar_a, bar_b)  # must not raise

    bar_c = _bar(BASE_DT, o=10, h=15, lo=9, c=13, v=600, tf="3m")  # different high
    with pytest.raises(CandleConsistencyError):
        engine.assert_candle_consistency(bar_a, bar_c)
