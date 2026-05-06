"""Module: MD-SCR-002.001.M04 — screeners/indicator.py
Parent SRD: SRD-SCR-002.003
"""
from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions (SRD-SCR-012.004)
# ---------------------------------------------------------------------------

class BenchmarkDataUnavailableError(Exception):
    def __init__(self, symbol: str) -> None:
        super().__init__(
            f"Benchmark data for '{symbol}' is not available in price_1d."
            " Run bootstrap_benchmark() first."
        )
        self.symbol = symbol


class InsufficientUniverseDataError(Exception):
    pass


# ---------------------------------------------------------------------------
# Indicator helpers (inline — analysis/indicators.py not yet implemented)
# ---------------------------------------------------------------------------

def _atr_pct(bars: list[Any], period: int = 14) -> float:
    """ATR as a fraction of closing price."""
    if len(bars) < 2:
        return 0.0
    window = bars[max(0, len(bars) - period):]
    trs = [b.high - b.low for b in window]
    avg = sum(trs) / len(trs)
    close = bars[-1].close
    return avg / close if close > 0 else 0.0


def _rsi(bars: list[Any], period: int = 14) -> float:
    closes = [b.close for b in bars]
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(len(closes) - period, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    avg_g = sum(gains) / period
    avg_l = sum(losses) / period
    if avg_g == 0.0 and avg_l == 0.0:
        return 50.0
    if avg_l == 0.0:
        return 100.0
    return 100.0 - 100.0 / (1.0 + avg_g / avg_l)


def _volume_ratio(bars: list[Any], period: int = 10) -> float:
    if len(bars) < period + 1:
        return 1.0
    ma = sum(b.volume for b in bars[-(period + 1):-1]) / period
    return bars[-1].volume / ma if ma > 0 else 0.0


def _is_breakout(bars: list[Any], lookback: int = 5) -> bool:
    if len(bars) < lookback + 1:
        return False
    prior_high = max(b.close for b in bars[-(lookback + 1):-1])
    return bars[-1].close > prior_high


def _rs_slope(sym_bars: list[Any], bench_bars: list[Any], slope_days: int) -> bool:
    """Return True if the RS line (stock/benchmark) rose over the last slope_days bars."""
    n = min(len(sym_bars), len(bench_bars))
    if n < slope_days + 1:
        return True  # insufficient data — don't penalise
    b_now = bench_bars[-1].close
    b_prev = bench_bars[-slope_days - 1].close
    if b_now == 0 or b_prev == 0:
        return True
    rs_now = sym_bars[-1].close / b_now
    rs_prev = sym_bars[-slope_days - 1].close / b_prev
    return rs_now > rs_prev


def _compute_rs_ranks(
    symbols: list[str],
    bars: dict[str, list[Any]],
    lookback: int = 252,
) -> dict[str, float]:
    """Compute 252-day return percentile rank for each symbol (SRD-SCR-012.002/005).

    Uses pandas vectorised rank; symbols with insufficient data receive 50.0.
    """
    import pandas as pd  # lazy import — pandas is a project dependency

    returns: dict[str, float] = {}
    for sym in symbols:
        sym_bars = bars.get(sym, [])
        if len(sym_bars) >= lookback + 1:
            c_now = sym_bars[-1].close
            c_past = sym_bars[-lookback - 1].close
            if c_past > 0:
                returns[sym] = (c_now - c_past) / c_past

    if not returns:
        return {sym: 50.0 for sym in symbols}

    ranked = (pd.Series(returns).rank(pct=True) * 100.0).to_dict()
    return {sym: ranked.get(sym, 50.0) for sym in symbols}


# ---------------------------------------------------------------------------
# IndicatorScreener
# ---------------------------------------------------------------------------

class IndicatorScreener:
    """MD-SCR-002.001.M04 — indicator-based screener plugin.

    Applies up to five configurable filters (volatility, RSI, range,
    breakout, volume). Score = fraction of enabled filters that pass.
    """

    def apply(
        self,
        symbols: list[str],
        bars: dict[str, list[Any]],
        config: dict[str, Any],
    ) -> dict[str, tuple[bool, float]]:
        filters = config.get("filters", {})
        results: dict[str, tuple[bool, float]] = {}

        # Pre-compute RS ranks once for all symbols (SRD-SCR-012.005)
        ricfg = filters.get("rs_index", {})
        ri_enabled = ricfg.get("enabled", False)
        rs_ranks: dict[str, float] = {}
        bench_bars: list[Any] = []
        rs_min_pct: float = 0.0
        rs_slope_days: int = 0
        if ri_enabled:
            benchmark_sym: str = config.get("benchmark_symbol", "SPY")
            bench_bars = bars.get(benchmark_sym, [])
            if not bench_bars:
                raise BenchmarkDataUnavailableError(benchmark_sym)
            rs_min_pct = float(ricfg.get("rs_min_percentile", 0.0))
            rs_slope_days = int(ricfg.get("rs_slope_days", 0))
            rs_ranks = _compute_rs_ranks(symbols, bars)

        for sym in symbols:
            sym_bars = bars.get(sym, [])
            if not sym_bars:
                continue

            passed = 0
            total = 0

            vcfg = filters.get("volatility", {})
            if vcfg.get("enabled", True):
                total += 1
                if _atr_pct(sym_bars) >= vcfg.get("min_atr_pct", 0.01):
                    passed += 1

            rcfg = filters.get("rsi", {})
            if rcfg.get("enabled", True):
                total += 1
                rsi = _rsi(sym_bars, period=rcfg.get("period", 14))
                if rcfg.get("min", 30) <= rsi <= rcfg.get("max", 70):
                    passed += 1

            rngcfg = filters.get("range", {})
            if rngcfg.get("enabled", True):
                total += 1
                price = sym_bars[-1].close
                if rngcfg.get("min_price", 5.0) <= price <= rngcfg.get("max_price", 5000.0):
                    passed += 1

            bkcfg = filters.get("breakout", {})
            if bkcfg.get("enabled", True):
                total += 1
                if _is_breakout(sym_bars, lookback=bkcfg.get("lookback", 10)):
                    passed += 1

            volcfg = filters.get("volume", {})
            if volcfg.get("enabled", True):
                total += 1
                if _volume_ratio(sym_bars, period=volcfg.get("ma_period", 10)) >= volcfg.get("min_volume_ratio", 1.0):
                    passed += 1

            if ri_enabled:
                total += 1
                rank_ok = rs_ranks.get(sym, 50.0) >= rs_min_pct
                slope_ok = (
                    _rs_slope(sym_bars, bench_bars, rs_slope_days)
                    if rs_slope_days > 0
                    else True
                )
                if rank_ok and slope_ok:
                    passed += 1

            score = float(passed / total) if total > 0 else 0.0
            results[sym] = (passed == total, score)

        return results

    def screen_detailed(
        self,
        symbols: list[str],
        bars: dict[str, list[Any]],
        config: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        """Return per-symbol indicator values for the enabled filters.

        Keys match the enabled filters; values are the raw computed numbers
        or booleans so the GUI can display them in the Details column.
        """
        filters = config.get("filters", {})
        out: dict[str, dict[str, Any]] = {}

        # Pre-compute RS ranks if rs_index filter is enabled
        ricfg = filters.get("rs_index", {})
        ri_enabled = ricfg.get("enabled", False)
        rs_ranks: dict[str, float] = {}
        bench_bars: list[Any] = []
        rs_slope_days: int = 0
        if ri_enabled:
            benchmark_sym: str = config.get("benchmark_symbol", "SPY")
            bench_bars = bars.get(benchmark_sym, [])
            if bench_bars:
                rs_slope_days = int(ricfg.get("rs_slope_days", 0))
                rs_ranks = _compute_rs_ranks(symbols, bars)

        for sym in symbols:
            sym_bars = bars.get(sym, [])
            if not sym_bars:
                continue
            det: dict[str, Any] = {}

            vcfg = filters.get("volatility", {})
            if vcfg.get("enabled", True):
                det["atr"] = round(_atr_pct(sym_bars) * 100, 2)

            rcfg = filters.get("rsi", {})
            if rcfg.get("enabled", True):
                det["rsi"] = round(_rsi(sym_bars, period=rcfg.get("period", 14)), 1)

            rngcfg = filters.get("range", {})
            if rngcfg.get("enabled", True):
                det["price"] = round(sym_bars[-1].close, 2)

            bkcfg = filters.get("breakout", {})
            if bkcfg.get("enabled", True):
                det["breakout"] = _is_breakout(sym_bars, lookback=bkcfg.get("lookback", 10))

            volcfg = filters.get("volume", {})
            if volcfg.get("enabled", True):
                det["vol_ratio"] = round(
                    _volume_ratio(sym_bars, period=volcfg.get("ma_period", 10)), 2
                )

            if ri_enabled:
                det["rs_rank"] = round(rs_ranks.get(sym, 50.0), 1)
                if rs_slope_days > 0 and bench_bars:
                    det["rs_slope_up"] = _rs_slope(sym_bars, bench_bars, rs_slope_days)

            out[sym] = det
        return out

    def batch_features(
        self,
        symbols: list[str],
        bars: dict[str, list[Any]],
    ) -> dict[str, dict[str, Any]]:
        return {}
