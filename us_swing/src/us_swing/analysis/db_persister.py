"""Module: MD-ANA-001.001.M03 — analysis/db_persister.py
Parent SRD: SRD-ANA-001.006

Thread-safe async queue writer that persists completed candles to the
database without blocking LiveEngine. A dedicated daemon thread drains
the queue every _DRAIN_INTERVAL seconds and bulk-inserts via DatabaseManager.

Writer-thread errors are logged at ERROR level and do not crash the engine.
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from typing import TYPE_CHECKING

from us_swing.data.models import OHLCVBar

if TYPE_CHECKING:
    from us_swing.db.manager import DatabaseManager

log = logging.getLogger(__name__)

_DRAIN_INTERVAL = 5.0  # seconds between queue drains


class DatabasePersister:
    """Queues completed candles for async bulk insert.

    Args:
        db: DatabaseManager instance used for batch inserts.
    """

    def __init__(self, db: "DatabaseManager") -> None:
        self._db = db
        # Queue items: (symbol, timeframe, OHLCVBar) | None (sentinel)
        self._queue: queue.Queue[tuple[str, str, OHLCVBar] | None] = queue.Queue()
        self._thread = threading.Thread(
            target=self._writer_loop,
            daemon=True,
            name="candle-persister",
        )
        self._thread.start()

    # ── Public API ────────────────────────────────────────────────────────────

    def persist_candle(self, symbol: str, timeframe: str, bar: OHLCVBar) -> None:
        """Enqueue a completed candle for async write (non-blocking)."""
        self._queue.put_nowait((symbol, timeframe, bar))

    def stop(self) -> None:
        """Send sentinel to writer, flush remaining items, and join thread."""
        self._queue.put_nowait(None)
        self._thread.join(timeout=15.0)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _writer_loop(self) -> None:
        """Drain queue every _DRAIN_INTERVAL and bulk-insert to DB."""
        pending: list[tuple[str, str, OHLCVBar]] = []

        while True:
            deadline = time.monotonic() + _DRAIN_INTERVAL

            # Drain all available items until the drain-interval window expires
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                try:
                    item = self._queue.get(timeout=min(remaining, 0.5))
                except queue.Empty:
                    if time.monotonic() >= deadline:
                        break
                    continue

                if item is None:  # sentinel — flush and exit
                    self._flush(pending)
                    return

                pending.append(item)

            self._flush(pending)
            pending = []

    def _flush(self, items: list[tuple[str, str, OHLCVBar]]) -> None:
        """Group items by (symbol, timeframe) and bulk-insert."""
        if not items:
            return
        groups: dict[tuple[str, str], list[OHLCVBar]] = {}
        for symbol, tf, bar in items:
            groups.setdefault((symbol, tf), []).append(bar)

        for (symbol, tf), bars in groups.items():
            try:
                self._db.insert_bars(symbol, tf, bars)
            except Exception:
                log.error(
                    "Candle write failed for %s %s — %d bars dropped",
                    symbol, tf, len(bars),
                    exc_info=True,
                )
