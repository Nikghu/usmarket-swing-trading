"""
Module: MD-GUI-007.001.M02 — log_bridge.py
Parent SRD: SRD-GUI-007.001

QueueHandler → Qt signal bridge for thread-safe log streaming.
"""
from __future__ import annotations

import logging
import queue
from collections import deque
from logging.handlers import QueueHandler

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class LogBuffer:
    """Fixed-size FIFO buffer for log records (SRD-GUI-007.004)."""

    def __init__(self, max_entries: int = 10_000) -> None:
        self._buf: deque[logging.LogRecord] = deque(maxlen=max_entries)

    def append(self, record: logging.LogRecord) -> None:
        self._buf.append(record)

    def get_filtered(
        self,
        level: str,
        module_pat: str,
        symbol_pat: str,
    ) -> list[logging.LogRecord]:
        level_no = getattr(logging, level, 0) if level != "ALL" else 0
        out: list[logging.LogRecord] = []
        for r in self._buf:
            if r.levelno < level_no:
                continue
            if module_pat and module_pat.lower() not in r.name.lower():
                continue
            if symbol_pat and symbol_pat.lower() not in r.getMessage().lower():
                continue
            out.append(r)
        return out

    def __len__(self) -> int:
        return len(self._buf)


class LogSignalEmitter(QObject):
    """
    Polls a queue.Queue every 100ms and emits new_log_entry for each record.
    Parent SRD: SRD-GUI-007.001
    """

    new_log_entry = pyqtSignal(logging.LogRecord)  # type: ignore[type-arg]

    def __init__(
        self,
        log_queue: queue.Queue[logging.LogRecord],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._queue = log_queue
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._drain)
        self._timer.start(100)

    def _drain(self) -> None:
        while True:
            try:
                record = self._queue.get_nowait()
                self.new_log_entry.emit(record)
            except queue.Empty:
                break

    def stop(self) -> None:
        self._timer.stop()


def setup_queue_handler(max_entries: int = 10_000) -> tuple[LogSignalEmitter, LogBuffer, QueueHandler]:
    """
    Set up logging infrastructure.  Returns (emitter, buffer, handler).
    Caller should attach handler to the root logger.
    """
    log_queue: queue.Queue[logging.LogRecord] = queue.Queue()
    handler = QueueHandler(log_queue)
    handler.setLevel(logging.DEBUG)

    emitter = LogSignalEmitter(log_queue)
    buf = LogBuffer(max_entries)

    # Wire emitter → buffer
    emitter.new_log_entry.connect(buf.append)

    return emitter, buf, handler
