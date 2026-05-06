"""Module: MD-ANA-001.001.M02 — analysis/live_engine.py
Parent SRD: SRD-ANA-001.001, SRD-ANA-001.004, SRD-ANA-001.006

LiveEngine subscribes to IBKR 5-second realtime bars for up to 20 symbols,
routes each bar to CandleBuilder, and fans out completed candles synchronously
to all registered StrategyEngines and asynchronously to DatabasePersister.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from us_swing.data.models import OHLCVBar, RealtimeBar

if TYPE_CHECKING:
    from us_swing.analysis.candle_builder import CandleBuilder
    from us_swing.analysis.db_persister import DatabasePersister
    from us_swing.analysis.strategy_engine import StrategyEngine
    from us_swing.broker.client import IBKRClient

log = logging.getLogger(__name__)

_MAX_SUBSCRIPTIONS = 20


class LiveEngine:
    """Orchestrates realtime bar ingestion, candle building, and signal dispatch.

    Wires itself into CandleBuilder as the on_candle_closed callback so that
    strategy evaluation and DB persistence are driven by candle completions.

    Args:
        ibkr_client:      Broker client for realtime bar subscriptions.
        candle_builder:   Aggregates 5s bars; LiveEngine registers its own
                          callback on this builder during construction.
        strategy_engines: One StrategyEngine per active user.
        db_persister:     Async candle writer.
    """

    def __init__(
        self,
        ibkr_client: "IBKRClient",
        candle_builder: "CandleBuilder",
        strategy_engines: list["StrategyEngine"],
        db_persister: "DatabasePersister",
    ) -> None:
        self._client = ibkr_client
        self._builder = candle_builder
        self._strategy_engines = strategy_engines
        self._persister = db_persister
        self._subscribed: set[str] = set()

        # Wire ourselves as the candle-closed callback
        candle_builder.register_callback(self._on_candle_closed)
        # Register bar callback with broker
        ibkr_client.on_realtime_bar(self.on_realtime_bar)

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self, symbols: list[str]) -> None:
        """Subscribe to realtime bars for the given symbol list.

        Caps at _MAX_SUBSCRIPTIONS; excess symbols are warned and dropped.
        Unsubscribes any symbol that was previously subscribed but is no
        longer in the new list.

        Args:
            symbols: Ticker symbols to subscribe.
        """
        if len(symbols) > _MAX_SUBSCRIPTIONS:
            log.warning(
                "Requested %d symbols but max is %d; truncating",
                len(symbols),
                _MAX_SUBSCRIPTIONS,
            )
            symbols = symbols[:_MAX_SUBSCRIPTIONS]

        new_set = set(symbols)

        # Unsubscribe removed symbols
        for sym in self._subscribed - new_set:
            try:
                self._client.unsubscribe_realtime_bars(sym)
                log.debug("Unsubscribed realtime bars: %s", sym)
            except Exception:
                log.warning("Failed to unsubscribe %s", sym, exc_info=True)

        # Subscribe new symbols
        for sym in new_set - self._subscribed:
            try:
                self._client.subscribe_realtime_bars(sym, bar_size=5)
                log.info("Subscribed realtime bars: %s", sym)
            except Exception:
                log.error("Failed to subscribe %s", sym, exc_info=True)
                new_set.discard(sym)

        self._subscribed = new_set

    def stop(self) -> None:
        """Unsubscribe all symbols and stop the DB persister."""
        for sym in list(self._subscribed):
            try:
                self._client.unsubscribe_realtime_bars(sym)
            except Exception:
                log.warning("Failed to unsubscribe %s on stop", sym, exc_info=True)
        self._subscribed.clear()
        self._persister.stop()
        log.info("LiveEngine stopped")

    def on_realtime_bar(self, bar: RealtimeBar) -> None:
        """Callback registered with IBKRClient — routes bar to CandleBuilder."""
        self._builder.add_bar(bar)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _on_candle_closed(self, symbol: str, tf: str, bar: OHLCVBar) -> None:
        """Registered as CandleBuilder callback.

        Dispatches to all StrategyEngines (synchronous) then DB (async).
        """
        # Synchronous strategy evaluation
        for engine in self._strategy_engines:
            try:
                engine.on_candle_closed(symbol, tf, bar)
            except Exception:
                log.error(
                    "StrategyEngine error for %s %s", symbol, tf, exc_info=True
                )

        # Async DB write
        self._persister.persist_candle(symbol, tf, bar)
