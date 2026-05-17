"""
Module: MD-EXE-010.001.M01 — core/monitoring_session/_scheduler.py
Parent SRD: SRD-EXE-010.004

Glue between the existing scheduler infrastructure and
``MonitoringCommand.reconcile_preopen``.  Provides a daily cron trigger and a
startup catch-up mechanism for app launches that miss the scheduled time.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time
from typing import Callable
from zoneinfo import ZoneInfo

from us_swing.core.monitoring_session._events import ReconcileCompleted
from us_swing.core.monitoring_session._protocols import (
    MonitoringCommand,
    MonitoringEventBus,
)
from us_swing.core.monitoring_session._dto import ReconcileReport

log = logging.getLogger(__name__)

_NY      = ZoneInfo("America/New_York")
_OPEN_ET = time(9, 15)
_CLOSE_ET = time(16, 0)
_CRON_EXPR = "15 9 * * MON-FRI"


def _today_et() -> date:
    return datetime.now(_NY).date()


class _ReconcileScheduler:
    """Registers the daily reconcile cron + provides startup catch-up.

    Single-flight protection lives in
    :meth:`MonitoringSessionService.reconcile_preopen` — manual, scheduled, and
    startup-catch-up invocations all funnel through the same lock.
    """

    def __init__(
        self,
        command: MonitoringCommand,
        bus: MonitoringEventBus,
        cron_register: Callable[[str, Callable[[], None]], None],
        *,
        clock: Callable[[], datetime] | None      = None,
        today_provider: Callable[[], date] | None = None,
    ) -> None:
        self._command       = command
        self._bus           = bus
        self._cron_register = cron_register
        self._clock         = clock or (lambda: datetime.now(_NY))
        self._today         = today_provider or _today_et
        self._seen_for:     date | None = None
        self._subscription  = bus.subscribe(ReconcileCompleted, self._mark_seen)

    def start(self) -> None:
        """Register the 09:15 ET weekday cron."""
        self._cron_register(_CRON_EXPR, self._fire)

    def maybe_run_on_startup(self) -> ReconcileReport | None:
        """Invoke ``reconcile_preopen`` once if the daily run was missed.

        Returns the report if reconcile fired, or ``None`` if conditions did
        not warrant a run (weekend, off-hours, or already-seen).
        """
        today = self._today()
        if today.weekday() >= 5:
            return None
        now_et = self._clock().astimezone(_NY).time()
        if not (_OPEN_ET <= now_et <= _CLOSE_ET):
            return None
        if self._seen_for == today:
            return None
        return self._command.reconcile_preopen(today)

    def _fire(self) -> None:
        self._command.reconcile_preopen(self._today())

    def _mark_seen(self, _event: ReconcileCompleted) -> None:
        self._seen_for = self._today()
