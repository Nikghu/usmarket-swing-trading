"""Module: MD-SCR-002.002.M05 — screeners/ml.py
Parent SRD: SRD-SCR-002.004
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

try:
    import joblib
except ImportError:  # pragma: no cover
    joblib = None  # type: ignore[assignment]

from us_swing.screener.base import ScreenerError

_log = logging.getLogger(__name__)


def _extract_features(sym_bars: list[Any]) -> list[float]:
    """Extract a minimal feature vector from OHLCV bars."""
    closes = [b.close for b in sym_bars]
    volumes = [b.volume for b in sym_bars]
    n = len(closes)
    last_close = closes[-1]
    mean_close = sum(closes) / n
    mean_vol = sum(volumes) / n
    tr_list = [b.high - b.low for b in sym_bars]
    atr = sum(tr_list[-14:]) / min(14, n)
    return [last_close, mean_close, atr, mean_vol, volumes[-1]]


class MLScreener:
    """MD-SCR-002.002.M05 — ML model screener plugin.

    Loads a scikit-learn model via joblib, extracts numeric features from
    OHLCV bars, and scores each symbol using predict_proba.
    """

    def apply(
        self,
        symbols: list[str],
        bars: dict[str, list[Any]],
        config: dict[str, Any],
    ) -> dict[str, tuple[bool, float]]:
        model_path: str = config.get("model_path", "")
        threshold: float = float(config.get("threshold", 0.5))

        if not Path(model_path).exists():
            raise ScreenerError(f"Model file not found: {model_path}")

        model = joblib.load(model_path)

        results: dict[str, tuple[bool, float]] = {}
        for sym in symbols:
            sym_bars = bars.get(sym, [])
            if not sym_bars:
                continue
            features = _extract_features(sym_bars)
            proba = model.predict_proba([features])
            score = float(proba[0][1])
            results[sym] = (bool(score >= threshold), score)
        return results

    def batch_features(
        self,
        symbols: list[str],
        bars: dict[str, list[Any]],
    ) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for sym in symbols:
            sym_bars = bars.get(sym, [])
            if not sym_bars:
                continue
            feats = _extract_features(sym_bars)
            result[sym] = {
                "close": feats[0],
                "mean_close": feats[1],
                "atr": feats[2],
                "mean_volume": feats[3],
                "last_volume": feats[4],
            }
        return result
