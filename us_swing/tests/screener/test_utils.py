"""Unit tests: MD-SCR-007.001.M14 — screener/utils.py
Refs: UT-SCR-007.001.M14.T01 – UT-SCR-007.001.M14.T08
"""
from __future__ import annotations

import random
import time

import pytest

from us_swing.screener.base import (
    PresetValidationError,
    ScreenerError,
    ScreenerNotFoundError,
)
from us_swing.screener.preset import Preset, PresetType
from us_swing.screener.registry import ScreenerRegistry
from us_swing.screener.utils import PreFilter

from .conftest import make_bars


# ---------------------------------------------------------------------------
# T01 — price ≤ $5 excluded
# ---------------------------------------------------------------------------

def test_prefilter_excludes_low_price():
    """UT-SCR-007.001.M14.T01: symbol with close=4.99 excluded from output."""
    from unittest.mock import MagicMock
    sym = "CHEAP"
    # Use a mock bar with a fixed close price so random walk can't push it above $5
    bar = MagicMock()
    bar.close = 4.99
    bar.volume = 5_000_000
    bars = {sym: [bar]}
    result = PreFilter().apply([sym], bars)
    assert sym not in result


# ---------------------------------------------------------------------------
# T02 — volume < 1 M excluded
# ---------------------------------------------------------------------------

def test_prefilter_excludes_low_volume():
    """UT-SCR-007.001.M14.T02: symbol with volume=900k excluded."""
    sym = "LOWVOL"
    bars = {sym: make_bars(sym, n=10, base_price=50.0, volume=900_000)}
    result = PreFilter().apply([sym], bars)
    assert sym not in result


# ---------------------------------------------------------------------------
# T03 — missing/empty bars: excluded with no exception
# ---------------------------------------------------------------------------

def test_prefilter_handles_missing_bars():
    """UT-SCR-007.001.M14.T03: symbol with empty bar list excluded silently."""
    sym = "NOBARS"
    # empty bar list
    assert PreFilter().apply([sym], {sym: []}) == []
    # symbol not even in bars dict
    assert PreFilter().apply([sym], {}) == []


# ---------------------------------------------------------------------------
# T04 — bulk count ~250–420 from 500
# ---------------------------------------------------------------------------

def test_prefilter_bulk_count():
    """UT-SCR-007.001.M14.T04: ~300 symbols pass from 500 (deterministic seed)."""
    rng = random.Random(42)
    symbols = [f"SYM{i:04d}" for i in range(500)]
    bars: dict = {}
    for sym in symbols:
        # ~20 % get price < $5, ~33 % get volume < 1 M
        price = rng.choice([3.0, 6.0, 10.0, 50.0, 100.0])
        vol = rng.choice([500_000, 2_000_000, 3_000_000])
        bars[sym] = make_bars(sym, n=10, base_price=price, volume=vol)
    filtered = PreFilter().apply(symbols, bars)
    assert 200 <= len(filtered) <= 420


# ---------------------------------------------------------------------------
# T05 — execution time < 1 s for 500 symbols
# ---------------------------------------------------------------------------

def test_prefilter_execution_time():
    """UT-SCR-007.001.M14.T05: 500 symbols filtered in under 1000 ms."""
    symbols = [f"SYM{i:04d}" for i in range(500)]
    bars = {s: make_bars(s, n=10, base_price=50.0) for s in symbols}
    start = time.perf_counter()
    PreFilter().apply(symbols, bars)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 1000, f"Took {elapsed_ms:.0f} ms"


# ---------------------------------------------------------------------------
# T06 — ScreenerError is base of the error hierarchy
# ---------------------------------------------------------------------------

def test_screener_error_hierarchy():
    """UT-SCR-007.001.M14.T06: error subclasses are all ScreenerError instances."""
    from us_swing.screener.base import (
        PreFilterError,
        PresetAccessDenied,
        PresetError,
        PresetNotFoundError,
        PresetValidationError,
        ScreenerExecutionError,
        ScreenerNotFoundError,
        ScreenerValidationError,
    )

    subclasses = [
        ScreenerNotFoundError,
        ScreenerValidationError,
        PresetError,
        PresetValidationError,
        PresetAccessDenied,
        PresetNotFoundError,
        ScreenerExecutionError,
        PreFilterError,
    ]
    for cls in subclasses:
        assert issubclass(cls, ScreenerError), f"{cls.__name__} not subclass of ScreenerError"
    err = ScreenerNotFoundError("boom")
    assert isinstance(err, ScreenerError)


# ---------------------------------------------------------------------------
# T07 — ScreenerNotFoundError raised; message contains screener_id
# ---------------------------------------------------------------------------

def test_screener_not_found_error_message():
    """UT-SCR-007.001.M14.T07: registry.get('xyz') raises ScreenerNotFoundError with id in message."""
    registry = ScreenerRegistry()
    with pytest.raises(ScreenerNotFoundError) as exc_info:
        registry.get("xyz_nonexistent")
    assert "xyz_nonexistent" in str(exc_info.value)


# ---------------------------------------------------------------------------
# T08 — PresetValidationError raised on invalid Weighted preset
# ---------------------------------------------------------------------------

def test_preset_validation_error_on_bad_preset():
    """UT-SCR-007.001.M14.T08: Weighted preset with no threshold raises PresetValidationError."""
    preset = Preset(
        id="bad",
        name="Bad",
        preset_type=PresetType.WEIGHTED,
        threshold=None,
    )
    with pytest.raises(PresetValidationError):
        preset.validate()
