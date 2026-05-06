"""Unit tests: MD-SCR-001.003.M03 — registry.py
Refs: UT-SCR-001.003.M03.T01 – UT-SCR-001.003.M03.T06
"""
from __future__ import annotations

import pytest

from us_swing.screener.base import ScreenerNotFoundError
from us_swing.screener.registry import ScreenerRegistry


# ---------------------------------------------------------------------------
# Shared minimal mock screeners (defined locally; simple enough for Phase 1)
# ---------------------------------------------------------------------------

class _IndicatorMock:
    def apply(self, symbols, bars, config): return {}
    def batch_features(self, symbols, bars): return {}


class _MLMock:
    def apply(self, symbols, bars, config): return {}
    def batch_features(self, symbols, bars): return {}


class _LLMMock:
    def apply(self, symbols, bars, config): return {}
    def batch_features(self, symbols, bars): return {}


# ---------------------------------------------------------------------------
# T01 — register() adds screener to registry
# ---------------------------------------------------------------------------

def test_t01_register_adds_screener():
    """UT-SCR-001.003.M03.T01"""
    ScreenerRegistry.register("test_screener", _IndicatorMock)
    assert "test_screener" in ScreenerRegistry.list_available()


# ---------------------------------------------------------------------------
# T02 — get() instantiates and returns a Screener instance
# ---------------------------------------------------------------------------

def test_t02_get_instantiates_screener():
    """UT-SCR-001.003.M03.T02"""
    ScreenerRegistry.register("indicator_composite", _IndicatorMock)
    result = ScreenerRegistry.get("indicator_composite")
    assert isinstance(result, _IndicatorMock)


# ---------------------------------------------------------------------------
# T03 — get() raises ScreenerNotFoundError for unregistered ID
# ---------------------------------------------------------------------------

def test_t03_get_unknown_raises():
    """UT-SCR-001.003.M03.T03"""
    with pytest.raises(ScreenerNotFoundError):
        ScreenerRegistry.get("nonexistent")


# ---------------------------------------------------------------------------
# T04 — list_available() returns ≥4 entries (after registering 4)
# ---------------------------------------------------------------------------

def test_t04_list_available_returns_all():
    """UT-SCR-001.003.M03.T04"""
    ScreenerRegistry.register("s1", _IndicatorMock)
    ScreenerRegistry.register("s2", _MLMock)
    ScreenerRegistry.register("s3", _LLMMock)
    ScreenerRegistry.register("s4", _IndicatorMock)
    available = ScreenerRegistry.list_available()
    assert len(available) >= 4
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in available.items())


# ---------------------------------------------------------------------------
# T05 — double-register with same ID overwrites (no error raised)
# ---------------------------------------------------------------------------

def test_t05_double_register_overwrites():
    """UT-SCR-001.003.M03.T05"""

    class _OldScreener:
        def apply(self, s, b, c): return {}
        def batch_features(self, s, b): return {}

    class _NewScreener:
        def apply(self, s, b, c): return {}
        def batch_features(self, s, b): return {}

    ScreenerRegistry.register("dup", _OldScreener)
    ScreenerRegistry.register("dup", _NewScreener)  # overwrite
    result = ScreenerRegistry.get("dup")
    assert isinstance(result, _NewScreener)
    assert not isinstance(result, _OldScreener)


# ---------------------------------------------------------------------------
# T06 — indicator, ML, and LLM types coexist in registry
# ---------------------------------------------------------------------------

def test_t06_multiple_types_coexist():
    """UT-SCR-001.003.M03.T06"""
    ScreenerRegistry.register("indicator", _IndicatorMock)
    ScreenerRegistry.register("ml", _MLMock)
    ScreenerRegistry.register("llm", _LLMMock)
    available = ScreenerRegistry.list_available()
    assert "indicator" in available
    assert "ml" in available
    assert "llm" in available
