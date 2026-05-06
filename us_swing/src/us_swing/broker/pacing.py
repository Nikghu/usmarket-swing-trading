"""Module: MD-INF-001.001.M02 — broker/pacing.py
Parent SRD: SRD-INF-001.005

Token-bucket implementation of the IBKR historical-data pacing limit:
≤ 50 requests per 600-second rolling window.

``PacingQueue.acquire()`` must be awaited before every
``req_historical_data()`` call.  Callers do not need to release tokens
manually; the internal cleanup task handles expiry automatically.
"""
from __future__ import annotations

import asyncio
import logging
from collections import deque
from time import monotonic

log = logging.getLogger(__name__)

_IBKR_LIMIT    = 50
_IBKR_WINDOW_S = 600


class PacingQueue:
    """Asyncio rolling-window token bucket for IBKR request pacing.

    Args:
        limit:    Maximum requests allowed per ``window_s`` seconds.
        window_s: Rolling window duration in seconds.
    """

    def __init__(self, limit: int = _IBKR_LIMIT, window_s: float = _IBKR_WINDOW_S) -> None:
        self._limit    = limit
        self._window_s = window_s
        self._slots: deque[float] = deque()   # monotonic timestamps of issued tokens
        self._lock  = asyncio.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def available(self) -> int:
        """Remaining slots in the current window (informational only)."""
        self._purge_expired()
        return max(0, self._limit - len(self._slots))

    async def acquire(self) -> None:
        """Wait until a pacing slot is available, then consume it."""
        while True:
            async with self._lock:
                self._purge_expired()
                if len(self._slots) < self._limit:
                    self._slots.append(monotonic())
                    return
            # No slot available — wait briefly and retry.
            wait_s = self._time_until_next_slot()
            log.debug("Pacing: %d/%d slots used; waiting %.1fs", len(self._slots), self._limit, wait_s)
            await asyncio.sleep(max(0.5, wait_s))

    def release_expired(self) -> None:
        """Manually purge expired slots (useful in tests)."""
        self._purge_expired()

    # ── Internals ─────────────────────────────────────────────────────────────

    def _purge_expired(self) -> None:
        cutoff = monotonic() - self._window_s
        while self._slots and self._slots[0] < cutoff:
            self._slots.popleft()

    def _time_until_next_slot(self) -> float:
        if not self._slots:
            return 0.0
        return self._slots[0] + self._window_s - monotonic()
