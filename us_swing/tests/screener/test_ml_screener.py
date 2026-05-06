"""Unit tests: MD-SCR-002.002.M05 — screeners/ml.py
Refs: UT-SCR-002.002.M05.T01 – UT-SCR-002.002.M05.T05
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from us_swing.screener.base import ScreenerError
from us_swing.screener.screeners.ml import MLScreener

from .conftest import make_bars


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_model(score: float = 0.75) -> MagicMock:
    """Return a mock sklearn-style model that returns a fixed probability."""
    model = MagicMock()
    model.predict_proba.return_value = [[1 - score, score]]
    return model


# ---------------------------------------------------------------------------
# T01 — MLScreener loads model from config["model_path"] (valid file)
# ---------------------------------------------------------------------------

def test_t01_loads_model_from_config(tmp_path):
    """UT-SCR-002.002.M05.T01"""
    model_file = tmp_path / "model.pkl"
    model_file.write_bytes(b"placeholder")

    mock_model = _make_mock_model(0.7)
    with patch("us_swing.screener.screeners.ml.joblib") as mock_joblib:
        mock_joblib.load.return_value = mock_model
        screener = MLScreener()
        bars = {"AAPL": make_bars("AAPL", n=50, seed=1)}
        config = {"model_path": str(model_file), "threshold": 0.5}
        result = screener.apply(["AAPL"], bars, config)

    mock_joblib.load.assert_called_once_with(str(model_file))
    assert "AAPL" in result


# ---------------------------------------------------------------------------
# T02 — apply() returns (bool, float) per symbol
# ---------------------------------------------------------------------------

def test_t02_apply_returns_bool_float(tmp_path):
    """UT-SCR-002.002.M05.T02"""
    model_file = tmp_path / "model.pkl"
    model_file.write_bytes(b"x")

    mock_model = _make_mock_model(0.6)
    symbols = ["AAPL", "MSFT", "GOOGL"]
    bars = {s: make_bars(s, n=50, seed=i) for i, s in enumerate(symbols)}

    with patch("us_swing.screener.screeners.ml.joblib") as mock_joblib:
        mock_joblib.load.return_value = mock_model
        screener = MLScreener()
        config = {"model_path": str(model_file), "threshold": 0.5}
        result = screener.apply(symbols, bars, config)

    assert set(result.keys()) == set(symbols)
    for sym, (passed, score) in result.items():
        assert isinstance(passed, bool)
        assert isinstance(score, float)


# ---------------------------------------------------------------------------
# T03 — raises ScreenerError when model file is missing
# ---------------------------------------------------------------------------

def test_t03_missing_model_raises():
    """UT-SCR-002.002.M05.T03"""
    screener = MLScreener()
    bars = {"AAPL": make_bars("AAPL", n=50)}
    config = {"model_path": "/nonexistent/path/model.pkl"}
    with pytest.raises(ScreenerError):
        screener.apply(["AAPL"], bars, config)


# ---------------------------------------------------------------------------
# T04 — batch_features() extracts and returns features dict
# ---------------------------------------------------------------------------

def test_t04_batch_features_returns_features():
    """UT-SCR-002.002.M05.T04"""
    screener = MLScreener()
    symbols = ["AAPL", "MSFT"]
    bars = {s: make_bars(s, n=50, seed=i) for i, s in enumerate(symbols)}
    result = screener.batch_features(symbols, bars)
    assert isinstance(result, dict)
    assert set(result.keys()) == set(symbols)
    for sym, features in result.items():
        assert isinstance(features, dict)
        assert len(features) > 0, f"{sym}: features must not be empty"


# ---------------------------------------------------------------------------
# T05 — threshold is configurable; symbols pass/fail accordingly
# ---------------------------------------------------------------------------

def test_t05_threshold_configurable(tmp_path):
    """UT-SCR-002.002.M05.T05 — score >= threshold → True; else → False."""
    model_file = tmp_path / "model.pkl"
    model_file.write_bytes(b"x")

    # Model returns score=0.65 for every symbol
    mock_model = _make_mock_model(0.65)
    bars = {"AAPL": make_bars("AAPL", n=50, seed=1)}

    with patch("us_swing.screener.screeners.ml.joblib") as mock_joblib:
        mock_joblib.load.return_value = mock_model

        screener_low = MLScreener()
        result_low = screener_low.apply(
            ["AAPL"], bars, {"model_path": str(model_file), "threshold": 0.5}
        )
        assert result_low["AAPL"][0] is True  # 0.65 >= 0.5

        screener_high = MLScreener()
        result_high = screener_high.apply(
            ["AAPL"], bars, {"model_path": str(model_file), "threshold": 0.8}
        )
        assert result_high["AAPL"][0] is False  # 0.65 < 0.8
