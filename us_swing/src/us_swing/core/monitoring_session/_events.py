"""
Module: MD-EXE-009.001.M03 — core/monitoring_session/_events.py
Parent SRD: SRD-EXE-009.011

Seven frozen event dataclasses forming the ``MonitoringEvent`` sealed union,
plus an in-process synchronous event bus.  Handler exceptions are caught,
logged with the ``[Lifecycle]`` topic, and never block sibling handlers.
"""
from __future__ import annotations

import logging
import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Union

from us_swing.core.monitoring_session._dto import ReconcileReport
from us_swing.core.monitoring_session._enums import Side
from us_swing.core.monitoring_session._protocols import (
    MonitoringEventBus,
    Subscription,
)

log = logging.getLogger(__name__)


# ── Event dataclasses ────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class SymbolStartedMonitoring:
    event_id:       str
    occurred_at:    str
    symbol:         str
    session_date:   str
    preset_id:      str
    run_timestamp:  str
    schema_version: int = 1


@dataclass(frozen=True, slots=True)
class SymbolEnteredPosition:
    event_id:            str
    occurred_at:         str
    symbol:              str
    anchor_session_date: str
    trade_id:            str
    fill_qty:            int
    fill_time:           str
    schema_version:      int = 1


@dataclass(frozen=True, slots=True)
class SymbolPositionScaled:
    event_id:            str
    occurred_at:         str
    symbol:              str
    anchor_session_date: str
    trade_id:            str
    side:                Side
    fill_qty:            int
    new_position_state:  str
    fill_time:           str
    schema_version:      int = 1


@dataclass(frozen=True, slots=True)
class SymbolExitedPosition:
    event_id:            str
    occurred_at:         str
    symbol:              str
    anchor_session_date: str
    exit_trade_id:       str
    exit_time:           str
    realised_pnl:        float
    schema_version:      int = 1


@dataclass(frozen=True, slots=True)
class SymbolSkipped:
    event_id:       str
    occurred_at:    str
    symbol:         str
    session_date:   str
    schema_version: int = 1


@dataclass(frozen=True, slots=True)
class SymbolEvicted:
    event_id:              str
    occurred_at:           str
    symbol:                str
    evicted_session_dates: tuple[str, ...]
    schema_version:        int = 1


@dataclass(frozen=True, slots=True)
class ReconcileCompleted:
    event_id:       str
    occurred_at:    str
    report:         ReconcileReport
    schema_version: int = 1


MonitoringEvent = Union[
    SymbolStartedMonitoring,
    SymbolEnteredPosition,
    SymbolPositionScaled,
    SymbolExitedPosition,
    SymbolSkipped,
    SymbolEvicted,
    ReconcileCompleted,
]


# ── Bus implementation ───────────────────────────────────────────────────────

@dataclass(slots=True)
class _SubscriptionHandle:
    """Concrete ``Subscription`` returned by :class:`_InProcessBus`."""

    _bus:        "_InProcessBus"
    _event_type: type
    _handler:    Callable[[Any], None]
    _alive:      bool = True

    def cancel(self) -> None:
        if not self._alive:
            return
        self._bus._unregister(self._event_type, self._handler)
        self._alive = False


class _InProcessBus(MonitoringEventBus):
    """Single-process synchronous event bus.

    ``publish`` invokes handlers on the calling thread in registration order.
    Handler exceptions are caught and logged at ERROR with the ``[Lifecycle]``
    topic; one bad handler does not block siblings.
    """

    def __init__(self) -> None:
        self._lock     = threading.RLock()
        self._handlers: dict[type, list[Callable[[Any], None]]] = defaultdict(list)

    def subscribe(
        self,
        event_type: type,
        handler: Callable[[Any], None],
    ) -> Subscription:
        with self._lock:
            self._handlers[event_type].append(handler)
        return _SubscriptionHandle(self, event_type, handler)

    def publish(self, event: Any) -> None:
        with self._lock:
            handlers = list(self._handlers.get(type(event), ()))
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                log.error(
                    "[Lifecycle] Handler %s raised on %s: %r",
                    getattr(handler, "__qualname__", repr(handler)),
                    type(event).__name__,
                    exc,
                )

    def _unregister(
        self,
        event_type: type,
        handler: Callable[[Any], None],
    ) -> None:
        with self._lock:
            try:
                self._handlers[event_type].remove(handler)
            except ValueError:
                pass
