"""Module: MD-ANA-001.001.M04 — analysis/indicators.py
Parent SRD: SRD-SCR-001.002–006 (shared)

Shared technical indicator library. All functions are pure (no side-effects)
and receive list[OHLCVBar] as input, returning float | list[float].

EMA is seeded from bars[0].close and uses multiplier k = 2 / (period + 1).
"""
from __future__ import annotations

import math

from us_swing.data.models import OHLCVBar


def ema(bars: list[OHLCVBar], period: int) -> list[float]:
    """Compute the full EMA series for bar closes.

    Seeded from bars[0].close, multiplier k = 2 / (period + 1).

    Args:
        bars:   OHLCV bar list (must be non-empty).
        period: EMA period (e.g. 21 for EMA21).

    Returns:
        List of floats of the same length as *bars*.
    """
    if not bars:
        return []
    k = 2.0 / (period + 1)
    values: list[float] = [bars[0].close]
    for bar in bars[1:]:
        values.append(bar.close * k + values[-1] * (1.0 - k))
    return values


def ema_value(bars: list[OHLCVBar], period: int) -> float:
    """Return the most recent EMA value.

    Args:
        bars:   OHLCV bar list.
        period: EMA period.

    Returns:
        Most recent EMA float, or NaN if bars is empty.
    """
    result = ema(bars, period)
    return result[-1] if result else float("nan")


def atr(bars: list[OHLCVBar], period: int) -> float:
    """Average True Range (Wilder's definition) over the last *period* bars.

    Args:
        bars:   OHLCV bar list (needs at least 2 bars).
        period: ATR period (e.g. 14).

    Returns:
        ATR float (0.0 if fewer than 2 bars).
    """
    if len(bars) < 2:
        return 0.0
    trs: list[float] = []
    for i in range(1, len(bars)):
        tr = max(
            bars[i].high - bars[i].low,
            abs(bars[i].high - bars[i - 1].close),
            abs(bars[i].low - bars[i - 1].close),
        )
        trs.append(tr)
    window = trs[-period:]
    return sum(window) / len(window)


def rsi(bars: list[OHLCVBar], period: int) -> float:
    """Relative Strength Index.

    Returns NaN when fewer than *period* bars are provided.

    Args:
        bars:   OHLCV bar list.
        period: RSI period (e.g. 14).

    Returns:
        RSI value in [0, 100], or float('nan') if insufficient data.
    """
    if len(bars) < period:
        return float("nan")
    closes = [b.close for b in bars]
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(0.0, c) for c in changes]
    losses = [max(0.0, -c) for c in changes]
    n = min(period, len(changes))
    avg_gain = sum(gains[-n:]) / n
    avg_loss = sum(losses[-n:]) / n
    if avg_loss == 0.0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)
