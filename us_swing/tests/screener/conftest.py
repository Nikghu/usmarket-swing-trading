"""Shared fixtures for screener unit tests.

Refs: UTCD-SCR v2.0.0 — Test Fixtures & Mocks section.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

import pytest

from us_swing.data.models import OHLCVBar
from us_swing.screener.preset import GroupLogic, Preset, PresetType, ScreenerGroup, ScreenerRef
from us_swing.screener.registry import ScreenerRegistry


# ---------------------------------------------------------------------------
# Bar generation helpers
# ---------------------------------------------------------------------------

def make_bars(
    symbol: str,
    n: int = 50,
    base_price: float = 100.0,
    seed: int = 42,
    volume: int = 2_000_000,
    trend: float = 0.0,
) -> list[OHLCVBar]:
    """Generate synthetic deterministic OHLCV bars for testing.

    Args:
        symbol: Ticker symbol.
        n: Number of bars.
        base_price: Starting close price.
        seed: RNG seed for reproducibility.
        volume: Base daily volume.
        trend: Daily drift fraction (e.g. 0.002 = slight uptrend).
    """
    rng = random.Random(seed)
    bars = []
    price = base_price
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for i in range(n):
        change = rng.gauss(trend, 0.02)  # 2% daily vol
        price = max(price * (1 + change), 1.0)
        spread = price * 0.01
        vol = max(1, int(rng.uniform(volume * 0.7, volume * 1.3)))
        bars.append(OHLCVBar(
            symbol=symbol,
            datetime=start + timedelta(days=i),
            open=price - spread / 2,
            high=price + spread,
            low=price - spread,
            close=price,
            volume=vol,
            timeframe="1d",
        ))
    return bars


def make_indicator_config(
    volatility: bool = True,
    rsi: bool = True,
    range_: bool = True,
    breakout: bool = True,
    volume: bool = True,
) -> dict:
    """Return a lenient IndicatorScreener config with each filter toggleable."""
    return {
        "filters": {
            "volatility": {"enabled": volatility, "min_atr_pct": 0.005},
            "rsi": {"enabled": rsi, "min": 20, "max": 90, "period": 14},
            "range": {"enabled": range_, "min_price": 5.0, "max_price": 5000.0},
            "breakout": {"enabled": breakout, "lookback": 5},
            "volume": {"enabled": volume, "min_volume_ratio": 0.5, "ma_period": 10},
        }
    }


# ---------------------------------------------------------------------------
# Registry isolation — reset class-level state between every test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_registry():
    """Wipe ScreenerRegistry before and after each test."""
    ScreenerRegistry._clear()
    yield
    ScreenerRegistry._clear()


# ---------------------------------------------------------------------------
# Mock screener classes (module-level so test files can use them as fixtures)
# ---------------------------------------------------------------------------

class MockScreener:
    """Generic mock that satisfies the Screener protocol."""

    def apply(self, symbols, bars, config):
        return {s: (True, 0.8) for s in symbols}

    def batch_features(self, symbols, bars):
        return {}


class MockIndicatorScreener(MockScreener):
    """Mock representing an indicator-based screener."""


class MockMLScreener(MockScreener):
    """Mock representing an ML-based screener."""


class MockLLMScreener(MockScreener):
    """Mock representing an LLM-based screener."""


# ---------------------------------------------------------------------------
# Fixtures exposing mock classes (for tests that need the class, not an instance)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_screener_class():
    return MockScreener


@pytest.fixture
def mock_indicator_class():
    return MockIndicatorScreener


@pytest.fixture
def mock_ml_class():
    return MockMLScreener


@pytest.fixture
def mock_llm_class():
    return MockLLMScreener


# ---------------------------------------------------------------------------
# Preset factory helpers (module-level; usable both as direct calls and fixtures)
# ---------------------------------------------------------------------------

def make_composite_preset(preset_id: str = "p1") -> Preset:
    ref1 = ScreenerRef(screener_id="indicator_composite", enabled=True)
    ref2 = ScreenerRef(screener_id="indicator_volume", enabled=True)
    group1 = ScreenerGroup(group_id="g1", logic=GroupLogic.AND, screeners=[ref1])
    group2 = ScreenerGroup(group_id="g2", logic=GroupLogic.OR, screeners=[ref2])
    return Preset(
        id=preset_id,
        name="Test Composite",
        preset_type=PresetType.COMPOSITE,
        description="A test composite preset",
        groups=[group1, group2],
        created_at=datetime(2026, 4, 16, 10, 30, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 16, 10, 30, 0, tzinfo=timezone.utc),
    )


def make_weighted_preset(preset_id: str = "p2") -> Preset:
    refs = [
        ScreenerRef(screener_id="indicator_composite", enabled=True, weight=0.4),
        ScreenerRef(screener_id="ml_ensemble", enabled=True, weight=0.3),
        ScreenerRef(screener_id="llm_claude_ranking", enabled=True, weight=0.3),
    ]
    return Preset(
        id=preset_id,
        name="Test Weighted",
        preset_type=PresetType.WEIGHTED,
        description="A test weighted preset",
        screeners=refs,
        threshold=0.6,
        created_at=datetime(2026, 4, 16, 10, 30, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 16, 10, 30, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def composite_preset() -> Preset:
    return make_composite_preset()


@pytest.fixture
def weighted_preset() -> Preset:
    return make_weighted_preset()
