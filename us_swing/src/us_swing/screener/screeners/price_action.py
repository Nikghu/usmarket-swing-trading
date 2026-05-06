"""Module: MD-SCR-002.005.M08 — screeners/price_action.py
Parent SRD: SRD-SCR-002.007

PriceActionScreener: detects 5 empirically-backed OHLCV patterns for swing trading.

Patterns (each independently toggleable via config):
  proximity_52w_high — George & Hwang (2004), Journal of Finance
  volume_breakout    — Bulkowski, Encyclopedia of Chart Patterns (3rd ed.)
  nr7_compression    — Crabel, Day Trading with Short-Term Price Patterns
  ema_pullback       — AQR momentum literature (Asness/Moskowitz/Pedersen 2012)
  engulfing          — Tharavanij et al. (2017), SAGE Open

Score = patterns_matched / patterns_enabled.
Symbol passes if score >= threshold (default 0.2 = at least 1 of 5).
"""
from __future__ import annotations

import logging
from typing import Any

from us_swing.analysis.indicators import ema
from us_swing.screener.base import ScreenerError

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default config
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG: dict[str, Any] = {
    "patterns": {
        "proximity_52w_high": {"enabled": True, "min_ratio": 0.90, "lookback": 252},
        "volume_breakout": {"enabled": True, "lookback": 20, "vol_multiplier": 1.5},
        "nr7_compression": {"enabled": False},
        "ema_pullback": {"enabled": False, "ema_period": 21},
        "engulfing": {"enabled": False},
    },
    "threshold": 0.2,
}

# ---------------------------------------------------------------------------
# Private pattern helpers
# ---------------------------------------------------------------------------


def _proximity_52w_high(bars: list[Any], cfg: dict[str, Any]) -> bool:
    """Close / max(closes[-lookback:]) >= min_ratio."""
    lookback: int = int(cfg.get("lookback", 252))
    min_ratio: float = float(cfg.get("min_ratio", 0.90))
    if len(bars) < lookback:
        window = bars
    else:
        window = bars[-lookback:]
    if not window:
        return False
    period_high = max(b.high for b in window)
    if period_high <= 0:
        return False
    return bool(bars[-1].close / period_high >= min_ratio)


def _volume_breakout(bars: list[Any], cfg: dict[str, Any]) -> bool:
    """close > max(highs of prior lookback bars) AND volume > vol_ma × multiplier."""
    lookback: int = int(cfg.get("lookback", 20))
    vol_multiplier: float = float(cfg.get("vol_multiplier", 1.5))
    # Need lookback prior bars + 1 current bar
    if len(bars) < lookback + 1:
        return False
    prior = bars[-(lookback + 1):-1]
    current = bars[-1]
    price_high = max(b.high for b in prior)
    vol_ma = sum(b.volume for b in prior) / len(prior)
    return bool(current.close > price_high and current.volume > vol_ma * vol_multiplier)


def _nr7_compression(bars: list[Any]) -> bool:
    """Current bar has the smallest high-low range of the last 7 bars."""
    if len(bars) < 7:
        return False
    window = bars[-7:]
    ranges = [b.high - b.low for b in window]
    # Last bar's range must be strictly the minimum
    return bool(ranges[-1] == min(ranges))


def _ema_pullback(bars: list[Any], cfg: dict[str, Any]) -> bool:
    """Close crossed above EMA(ema_period) on the last bar (was below prior bar)."""
    period: int = int(cfg.get("ema_period", 21))
    # Need at least period + 1 bars so both bars[-1] and bars[-2] have valid EMA
    if len(bars) < period + 1:
        return False
    ema_series = ema(bars, period)
    # bars[-1] crosses above: prev close was below EMA, current close is above
    prev_close = bars[-2].close
    prev_ema = ema_series[-2]
    curr_close = bars[-1].close
    curr_ema = ema_series[-1]
    return bool(prev_close < prev_ema and curr_close >= curr_ema)


def _bullish_engulfing(bars: list[Any]) -> bool:
    """Bearish candle followed by a larger bullish candle that fully engulfs it."""
    if len(bars) < 2:
        return False
    prev = bars[-2]
    curr = bars[-1]
    prev_is_bear = prev.close < prev.open
    curr_is_bull = curr.close > curr.open
    # Current body engulfs prior body
    engulfs = curr.open <= prev.close and curr.close >= prev.open
    return bool(prev_is_bear and curr_is_bull and engulfs)


# ---------------------------------------------------------------------------
# PriceActionScreener
# ---------------------------------------------------------------------------


class PriceActionScreener:
    """MD-SCR-002.005.M08 — price action pattern screener.

    Detects 5 empirically-backed patterns from OHLCV bars:
    proximity_52w_high, volume_breakout, nr7_compression, ema_pullback, engulfing.
    """

    screener_id: str = "price_action"
    screener_type: str = "price_action"
    name: str = "Price Action Screener"

    def apply(
        self,
        symbols: list[str],
        bars: dict[str, list[Any]],
        config: dict[str, Any],
    ) -> dict[str, tuple[bool, float]]:
        """Screen symbols for OHLCV price action patterns.

        Args:
            symbols: Symbols to screen.
            bars: Map of symbol → list[OHLCVBar] (oldest first).
            config: Pattern config (see SRD-SCR-002.007 for schema).

        Returns:
            dict mapping symbol → (passed, score). Symbols with <2 bars omitted.
        """
        patterns_cfg: dict[str, Any] = config.get("patterns", _DEFAULT_CONFIG["patterns"])
        threshold: float = float(config.get("threshold", 0.2))

        # Validate threshold range
        if not (0.0 <= threshold <= 1.0):
            raise ScreenerError(
                f"PriceActionScreener: threshold must be in [0, 1], got {threshold}"
            )

        results: dict[str, tuple[bool, float]] = {}

        for sym in symbols:
            sym_bars = bars.get(sym, [])
            if len(sym_bars) < 2:
                continue

            matched = 0
            enabled = 0

            # --- proximity_52w_high ---
            cfg_52w = patterns_cfg.get("proximity_52w_high", {})
            if cfg_52w.get("enabled", True):
                enabled += 1
                if len(sym_bars) >= 2 and _proximity_52w_high(sym_bars, cfg_52w):
                    matched += 1

            # --- volume_breakout ---
            cfg_vb = patterns_cfg.get("volume_breakout", {})
            if cfg_vb.get("enabled", True):
                enabled += 1
                lookback_vb = int(cfg_vb.get("lookback", 20))
                if len(sym_bars) >= lookback_vb + 1 and _volume_breakout(sym_bars, cfg_vb):
                    matched += 1

            # --- nr7_compression ---
            cfg_nr7 = patterns_cfg.get("nr7_compression", {})
            if cfg_nr7.get("enabled", False):
                enabled += 1
                if len(sym_bars) >= 7 and _nr7_compression(sym_bars):
                    matched += 1

            # --- ema_pullback ---
            cfg_ema = patterns_cfg.get("ema_pullback", {})
            if cfg_ema.get("enabled", False):
                enabled += 1
                period_ema = int(cfg_ema.get("ema_period", 21))
                if len(sym_bars) >= period_ema + 1 and _ema_pullback(sym_bars, cfg_ema):
                    matched += 1

            # --- engulfing ---
            cfg_eng = patterns_cfg.get("engulfing", {})
            if cfg_eng.get("enabled", False):
                enabled += 1
                if len(sym_bars) >= 2 and _bullish_engulfing(sym_bars):
                    matched += 1

            score = matched / enabled if enabled > 0 else 0.0
            results[sym] = (score >= threshold, round(score, 4))

        passed_count = sum(1 for p, _ in results.values() if p)
        _log.debug("price_action: screened %d symbols, %d passed", len(symbols), passed_count)
        return results

    def screen_detailed(
        self,
        symbols: list[str],
        bars: dict[str, list[Any]],
        config: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        """Return per-pattern match details for each symbol (used by executor for DETAILS column).

        Returns:
            dict mapping symbol → {pa_52w_high: bool, pa_vol_breakout: bool, ...}
        """
        patterns_cfg: dict[str, Any] = config.get("patterns", _DEFAULT_CONFIG["patterns"])
        details: dict[str, dict[str, Any]] = {}

        for sym in symbols:
            sym_bars = bars.get(sym, [])
            if len(sym_bars) < 2:
                continue

            row: dict[str, Any] = {}

            cfg_52w = patterns_cfg.get("proximity_52w_high", {})
            if cfg_52w.get("enabled", True):
                row["52wHigh"] = (
                    _proximity_52w_high(sym_bars, cfg_52w) if len(sym_bars) >= 2 else False
                )

            cfg_vb = patterns_cfg.get("volume_breakout", {})
            if cfg_vb.get("enabled", True):
                lookback_vb = int(cfg_vb.get("lookback", 20))
                row["volBreak"] = (
                    _volume_breakout(sym_bars, cfg_vb) if len(sym_bars) >= lookback_vb + 1 else False
                )

            cfg_nr7 = patterns_cfg.get("nr7_compression", {})
            if cfg_nr7.get("enabled", False):
                row["nr7"] = _nr7_compression(sym_bars) if len(sym_bars) >= 7 else False

            cfg_ema = patterns_cfg.get("ema_pullback", {})
            if cfg_ema.get("enabled", False):
                period_ema = int(cfg_ema.get("ema_period", 21))
                row["emaPB"] = (
                    _ema_pullback(sym_bars, cfg_ema) if len(sym_bars) >= period_ema + 1 else False
                )

            cfg_eng = patterns_cfg.get("engulfing", {})
            if cfg_eng.get("enabled", False):
                row["engulf"] = _bullish_engulfing(sym_bars) if len(sym_bars) >= 2 else False

            details[sym] = row

        return details

    def batch_features(
        self,
        symbols: list[str],
        bars: dict[str, list[Any]],
    ) -> dict[str, dict[str, Any]]:
        return {}
