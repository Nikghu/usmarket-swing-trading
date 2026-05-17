"""
Module: MD-EXE-009.001.M02 — core/monitoring_session/_protocols.py
Parent SRD: SRD-EXE-009.010, SRD-EXE-009.011

Public Protocol surface.  Consumers MUST type-annotate dependencies against
these protocols, never against the concrete ``_service.MonitoringSessionService``.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Callable, Protocol, TypeVar, runtime_checkable

from us_swing.core.monitoring_session._dto import (
    FillEvent,
    InvariantReport,
    KeepSet,
    MonitoringSessionRow,
    ReconcileReport,
)


E_co = TypeVar("E_co", covariant=True)


@runtime_checkable
class Subscription(Protocol):
    """Handle returned by ``MonitoringEventBus.subscribe``."""

    def cancel(self) -> None: ...


@runtime_checkable
class MonitoringEventBus(Protocol):
    """Synchronous in-process publish/subscribe surface for lifecycle events."""

    def subscribe(
        self,
        event_type: type,
        handler: Callable[[Any], None],
    ) -> Subscription: ...

    def publish(self, event: Any) -> None: ...


@runtime_checkable
class MonitoringQuery(Protocol):
    """Read-only side of the service.  Cheap, side-effect-free, thread-safe."""

    def keep_set(self, today: date) -> KeepSet: ...

    def open_system_positions(self) -> frozenset[str]: ...

    def has_open_system_position(self, symbol: str) -> bool: ...

    def session_for(
        self,
        session_date: date,
        symbol: str,
    ) -> MonitoringSessionRow | None: ...

    def history(
        self,
        symbol: str,
        days: int = 30,
    ) -> tuple[MonitoringSessionRow, ...]: ...

    def check_invariant(self) -> InvariantReport: ...


@runtime_checkable
class MonitoringCommand(Protocol):
    """Mutating side of the service.  Called only by the order pipeline,
    screener handoff, and the reconciler."""

    def on_screener_results(self, result: Any) -> KeepSet: ...

    def on_fill(self, fill: FillEvent) -> None: ...

    def reconcile_preopen(self, today: date) -> ReconcileReport: ...
