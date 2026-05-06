"""Module: MD-SCR-002.004.M07 — screeners/llm_local.py
Parent SRD: SRD-SCR-002.006

Stub for v2.0 — local LLM via ollama (not yet implemented).
"""
from __future__ import annotations

import logging
from typing import Any

from us_swing.screener.base import ScreenerError

_log = logging.getLogger(__name__)


class LLMLocalScreener:
    """MD-SCR-002.004.M07 — local LLM screener stub."""

    def apply(
        self,
        symbols: list[str],
        bars: dict[str, list[Any]],
        config: dict[str, Any],
    ) -> dict[str, tuple[bool, float]]:
        raise ScreenerError("LLMLocalScreener is not implemented in v2.0.")

    def batch_features(
        self,
        symbols: list[str],
        bars: dict[str, list[Any]],
    ) -> dict[str, dict[str, Any]]:
        return {}
