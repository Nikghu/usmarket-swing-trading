"""Module: data/providers/protocol.py — DataProvider protocol definition.
Parent SRD: SRD-INF-007.001

Defines the Protocol that all data provider implementations must satisfy.
Concrete providers (IBKRProvider, DummyProvider) are injected via this
interface, keeping HistoricalDataEngine decoupled from any specific source.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Protocol, runtime_checkable

from us_swing.data.models import OHLCVBar, RealtimeBar


@runtime_checkable
class DataProvider(Protocol):
    """Interface contract for all OHLCV data sources."""

    async def req_historical_data(
        self,
        symbol: str,
        end_datetime: datetime,
        duration: str,
        bar_size: str,
    ) -> list[OHLCVBar]:
        """Fetch historical bars for the given symbol and time range."""

    def subscribe_realtime_bars(self, symbol: str, bar_size: int = 5) -> None:
        """Begin streaming realtime 5-second bars for ``symbol``."""

    def unsubscribe_realtime_bars(self, symbol: str) -> None:
        """Stop streaming realtime bars for ``symbol``."""

    def on_realtime_bar(self, callback: Callable[[RealtimeBar], None]) -> None:
        """Register a callback invoked for each new realtime bar."""
