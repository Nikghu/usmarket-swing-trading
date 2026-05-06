"""Module: MD-SCR-002.006.M09 — screeners/mcp.py
Parent SRD: SRD-SCR-002.008

Stub for v2.0 — external MCP tool integration.
"""
from __future__ import annotations

import logging
from typing import Any

from us_swing.screener.base import ScreenerError

_log = logging.getLogger(__name__)


class MCPScreener:
    """MD-SCR-002.006.M09 — MCP external tool screener stub."""

    def apply(
        self,
        symbols: list[str],
        bars: dict[str, list[Any]],
        config: dict[str, Any],
    ) -> dict[str, tuple[bool, float]]:
        raise ScreenerError("MCPScreener is not implemented in v2.0.")

    def batch_features(
        self,
        symbols: list[str],
        bars: dict[str, list[Any]],
    ) -> dict[str, dict[str, Any]]:
        return {}
