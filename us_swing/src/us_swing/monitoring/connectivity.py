"""
Module: connectivity.py — SRD-INF-008
Internet Connectivity Watcher.

Probes 8.8.8.8:53 (Google Public DNS) every PROBE_INTERVAL_MS milliseconds
inside a background QThread so the GUI stays responsive. Emits
``status_changed(bool)`` only when the reachability state flips, so consumers
receive at most two events per outage (down → up).

Usage::

    watcher = NetWatcher(parent=svc)
    watcher.status_changed.connect(handler)
    watcher.start()
"""
from __future__ import annotations

import logging
import socket

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

_log = logging.getLogger(__name__)


class _ProbeWorker(QThread):
    """One-shot thread: attempt TCP to 8.8.8.8:53, emit True/False result."""

    result = pyqtSignal(bool)

    _HOST    = "8.8.8.8"
    _PORT    = 53
    _TIMEOUT = 3.0

    def run(self) -> None:
        try:
            with socket.create_connection((self._HOST, self._PORT), timeout=self._TIMEOUT):
                pass
            self.result.emit(True)
        except OSError:
            self.result.emit(False)


class NetWatcher(QObject):
    """Periodically checks internet connectivity and emits ``status_changed``.

    Signals:
        status_changed(bool): emitted **only when state flips**.
                              ``True``  = internet is reachable.
                              ``False`` = internet is unreachable.

    The first probe fires immediately on ``start()``; subsequent probes fire
    every ``PROBE_INTERVAL_MS`` milliseconds.
    """

    status_changed = pyqtSignal(bool)   # True = online, False = offline

    PROBE_INTERVAL_MS: int = 15_000     # 15 s between probes

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._online: bool | None = None   # None until first probe completes
        self._worker: _ProbeWorker | None = None

        self._timer = QTimer(self)
        self._timer.setInterval(self.PROBE_INTERVAL_MS)
        self._timer.timeout.connect(self._probe)

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Begin monitoring.  First probe fires immediately."""
        self._probe()
        self._timer.start()

    def stop(self) -> None:
        """Stop monitoring and wait for any in-flight probe to finish."""
        self._timer.stop()
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(2_000)

    def is_online(self) -> bool:
        """Return current (last-known) connectivity state."""
        return self._online is True

    # ── Internal ──────────────────────────────────────────────────────────────

    def _probe(self) -> None:
        """Launch a background probe; skip if a previous one is still running."""
        if self._worker and self._worker.isRunning():
            return
        self._worker = _ProbeWorker()
        self._worker.result.connect(self._on_result)
        self._worker.start()

    def _on_result(self, online: bool) -> None:
        if self._online != online:
            self._online = online
            _log.info("connectivity: %s", "online" if online else "offline")
            self.status_changed.emit(online)
