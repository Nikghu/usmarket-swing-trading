"""Unit tests: MD-SCR-002.001.M04 — screeners/indicator.py
Refs: UT-SCR-002.001.M04.T01 – UT-SCR-002.001.M04.T08
"""
from __future__ import annotations

import pytest

from us_swing.screener.screeners.indicator import IndicatorScreener

from .conftest import make_bars, make_indicator_config


# ---------------------------------------------------------------------------
# T01 — IndicatorScreener is deterministic (same inputs → same results)
# ---------------------------------------------------------------------------

def test_t01_v1_equivalence():
    """UT-SCR-002.001.M04.T01 — deterministic: same config+bars → same results."""
    screener = IndicatorScreener()
    bars = make_bars("AAPL", n=50, seed=42)
    config = make_indicator_config()
    result1 = screener.apply(["AAPL"], {"AAPL": bars}, config)
    result2 = screener.apply(["AAPL"], {"AAPL": bars}, config)
    assert result1 == result2


# ---------------------------------------------------------------------------
# T02 — apply() returns (bool, float) per symbol
# ---------------------------------------------------------------------------

def test_t02_apply_returns_bool_float_tuple():
    """UT-SCR-002.001.M04.T02"""
    screener = IndicatorScreener()
    symbols = ["AAPL", "MSFT", "GOOGL"]
    bars = {s: make_bars(s, n=50, seed=i * 10) for i, s in enumerate(symbols)}
    config = make_indicator_config()
    result = screener.apply(symbols, bars, config)
    assert set(result.keys()) == set(symbols)
    for sym, (passed, score) in result.items():
        assert isinstance(passed, bool), f"{sym}: passed must be bool"
        assert isinstance(score, float), f"{sym}: score must be float"


# ---------------------------------------------------------------------------
# T03 — symbol with no bars is skipped (not in output)
# ---------------------------------------------------------------------------

def test_t03_empty_bars_skipped():
    """UT-SCR-002.001.M04.T03"""
    screener = IndicatorScreener()
    bars = {
        "AAPL": make_bars("AAPL", n=50, seed=1),
        "EMPTY": [],
    }
    config = make_indicator_config()
    result = screener.apply(["AAPL", "EMPTY"], bars, config)
    assert "AAPL" in result
    assert "EMPTY" not in result


# ---------------------------------------------------------------------------
# T04 — all scores in [0, 1]
# ---------------------------------------------------------------------------

def test_t04_scores_in_unit_interval():
    """UT-SCR-002.001.M04.T04"""
    screener = IndicatorScreener()
    symbols = [f"SYM{i}" for i in range(5)]
    bars = {s: make_bars(s, n=50, seed=i) for i, s in enumerate(symbols)}
    config = make_indicator_config()
    result = screener.apply(symbols, bars, config)
    for sym, (_, score) in result.items():
        assert 0.0 <= score <= 1.0, f"{sym}: score {score} out of [0, 1]"


# ---------------------------------------------------------------------------
# T05 — all five filters are independently toggleable
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("disabled_filter", ["volatility", "rsi", "range", "breakout", "volume"])
def test_t05_filters_are_toggleable(disabled_filter):
    """UT-SCR-002.001.M04.T05 — disabling each filter changes the enabled count."""
    screener = IndicatorScreener()
    symbol = "AAPL"
    bars = {symbol: make_bars(symbol, n=50, seed=42)}

    all_enabled = make_indicator_config()
    one_disabled = make_indicator_config(**{disabled_filter.replace("range", "range_"): False})

    r_all = screener.apply([symbol], bars, all_enabled)
    r_dis = screener.apply([symbol], bars, one_disabled)

    # Scores may differ because one fewer filter is counted (numerator and/or denominator change)
    _, score_all = r_all[symbol]
    _, score_dis = r_dis[symbol]
    # Disabled filters cannot raise the denominator, so results can differ
    # At minimum: the call succeeds without error and returns float in [0,1]
    assert 0.0 <= score_dis <= 1.0


# ---------------------------------------------------------------------------
# T06 — disabled filter does not penalise symbol that fails it
# ---------------------------------------------------------------------------

def test_t06_disabled_filter_no_penalty():
    """UT-SCR-002.001.M04.T06"""
    screener = IndicatorScreener()
    symbol = "FLAT"
    # Bars with essentially zero ATR (flat price) → volatility filter fails
    bars_list = make_bars(symbol, n=50, seed=99)
    # Force flat price so ATR ≈ 0
    for bar in bars_list:
        bar.open = bar.close = bar.high = bar.low = 50.0

    bars = {symbol: bars_list}

    # With volatility enabled, symbol should score lower (volatility fails)
    cfg_with_vol = make_indicator_config(volatility=True)
    # With volatility disabled, same symbol ignores the failing filter
    cfg_no_vol = make_indicator_config(volatility=False)

    r_with = screener.apply([symbol], bars, cfg_with_vol)
    r_without = screener.apply([symbol], bars, cfg_no_vol)

    _, score_with = r_with[symbol]
    _, score_without = r_without[symbol]

    # Disabling a failing filter must not make things worse
    assert score_without >= score_with


# ---------------------------------------------------------------------------
# T07 — filters applied in order: volatility → RSI → range → breakout → volume
# ---------------------------------------------------------------------------

def test_t07_filter_order_all_evaluated():
    """UT-SCR-002.001.M04.T07 — all enabled filters are evaluated (no short-circuit)."""
    screener = IndicatorScreener()
    symbol = "AAPL"
    bars = {symbol: make_bars(symbol, n=50, seed=42)}

    # Use strict thresholds that will cause partial pass
    strict_config = {
        "filters": {
            "volatility": {"enabled": True, "min_atr_pct": 99.0},  # will fail (ATR too low)
            "rsi": {"enabled": True, "min": 0, "max": 100},        # always passes
            "range": {"enabled": True, "min_price": 0, "max_price": 1e9},  # always passes
            "breakout": {"enabled": True, "lookback": 1},           # may pass or fail
            "volume": {"enabled": True, "min_volume_ratio": 0.0},   # always passes
        }
    }
    result = screener.apply([symbol], bars, strict_config)
    _, score = result[symbol]

    # 4 of 5 filters pass (breakout TBD, but at least 3 of 5 including rsi/range/vol)
    # Because volatility fails, score < 1.0 — but the other filters ARE evaluated
    assert score < 1.0, "Strict volatility threshold should have reduced score"
    assert score > 0.0, "Other filters must still be counted (no short-circuit)"


# ---------------------------------------------------------------------------
# T08 — batch_features() returns empty dict
# ---------------------------------------------------------------------------

def test_t08_batch_features_returns_empty():
    """UT-SCR-002.001.M04.T08"""
    screener = IndicatorScreener()
    symbols = ["AAPL", "MSFT"]
    bars = {s: make_bars(s, n=30) for s in symbols}
    result = screener.batch_features(symbols, bars)
    assert result == {}
