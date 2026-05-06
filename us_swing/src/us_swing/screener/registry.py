"""Module: MD-SCR-001.003.M03 — registry.py
Parent SRD: SRD-SCR-002.001–002

ScreenerRegistry — class-level singleton for registering, discovering,
and instantiating screener plugins on demand.
"""
from __future__ import annotations

import logging
from typing import Any

from us_swing.screener.base import Screener, ScreenerNotFoundError

_log = logging.getLogger(__name__)


class ScreenerRegistry:
    """Class-level registry mapping screener_id -> screener class.

    All state is stored at the class level (singleton via class variables).
    Screener classes are instantiated on demand by get().
    """

    _registry: dict[str, type[Any]] = {}

    @classmethod
    def register(cls, screener_id: str, screener_class: type[Any]) -> None:
        """Register a screener class under screener_id.

        Overwrites any prior registration for the same ID without error.

        Args:
            screener_id: Unique identifier for this screener plugin.
            screener_class: Class implementing the Screener protocol.
        """
        cls._registry[screener_id] = screener_class
        _log.debug("registered screener %r -> %s", screener_id, screener_class.__name__)

    @classmethod
    def get(cls, screener_id: str) -> Screener:
        """Instantiate and return a registered screener by ID.

        Args:
            screener_id: ID of the previously registered screener.

        Returns:
            A new instance of the screener class.

        Raises:
            ScreenerNotFoundError: if screener_id is not registered.
        """
        _log.debug("instantiating screener %r", screener_id)
        if screener_id not in cls._registry:
            raise ScreenerNotFoundError(
                f"Screener '{screener_id}' is not registered. "
                f"Available: {list(cls._registry.keys())}"
            )
        return cls._registry[screener_id]()  # type: ignore[return-value]

    @classmethod
    def list_available(cls) -> dict[str, str]:
        """Return all registered screeners as {screener_id: class_name}.

        Returns:
            Mapping of screener_id -> display name (screener_class.__name__).
        """
        return {sid: klass.__name__ for sid, klass in cls._registry.items()}

    @classmethod
    def _clear(cls) -> None:
        """Clear all registrations.  Intended for test isolation only."""
        cls._registry.clear()
