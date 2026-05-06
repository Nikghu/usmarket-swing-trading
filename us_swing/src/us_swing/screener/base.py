"""Module: MD-SCR-001.002.M02 — base.py
Parent SRD: SRD-SCR-002.001

Screener protocol (abstract interface) and error class hierarchy.
All screener plugins must implement the Screener protocol.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------

class ScreenerError(Exception):
    """Base class for all screener errors."""


class ScreenerNotFoundError(ScreenerError):
    """Raised when a screener_id is not registered in ScreenerRegistry."""


class ScreenerValidationError(ScreenerError):
    """Raised when a screener configuration fails validation."""


class PresetError(ScreenerError):
    """Base class for preset-related errors."""


class PresetValidationError(PresetError):
    """Raised when a Preset fails structural validation."""


class PresetAccessDenied(PresetError):
    """Raised when a user accesses a preset they do not own or share."""


class PresetNotFoundError(PresetError):
    """Raised when a preset cannot be found on disk."""


class ScreenerExecutionError(ScreenerError):
    """Raised when preset execution fails (non-validation error)."""


class PreFilterError(ScreenerExecutionError):
    """Raised when the pre-filter stage encounters an unrecoverable error."""


# ---------------------------------------------------------------------------
# Screener Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class Screener(Protocol):
    """Protocol that all screener plugins must satisfy.

    apply() screens symbols and returns per-symbol (passed, score) pairs.
    batch_features() extracts features for LLM ranking without API calls.
    """

    def apply(
        self,
        symbols: list[str],
        bars: dict[str, list[Any]],
        config: dict[str, Any],
    ) -> dict[str, tuple[bool, float]]:
        """Screen symbols.

        Args:
            symbols: Universe of symbol tickers to screen.
            bars: OHLCV bar data keyed by symbol.
            config: Screener-specific configuration dict.

        Returns:
            Mapping of symbol -> (passed, score) where score is in [0, 1].
        """
        ...

    def batch_features(
        self,
        symbols: list[str],
        bars: dict[str, list[Any]],
    ) -> dict[str, dict[str, Any]]:
        """Extract features for LLM ranking (no external API calls).

        Args:
            symbols: Symbols to extract features for.
            bars: OHLCV bar data keyed by symbol.

        Returns:
            Mapping of symbol -> {feature_name: value}.
        """
        ...
