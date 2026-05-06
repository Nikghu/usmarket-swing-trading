"""Module: MD-INF-005.001.M02 — monitoring/alerts.py
Parent SRD: SRD-INF-005.003

AlertDispatcher receives log records at WARNING+ and fans them out to:
  - Console (stderr, always active).
  - Append-only alerts.log file.
  - Optional webhook via HTTP POST (best-effort, failure does not crash).

Attach AlertHandler to the root logger **after** configure_logging():

    dispatcher = AlertDispatcher(log_dir=Path("logs"), webhook_url="")
    root_logger.addHandler(AlertHandler(dispatcher, level=logging.WARNING))
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path


class AlertDispatcher:
    """Fan-out alert delivery to console + file + optional webhook.

    Args:
        log_dir:     Directory where ``alerts.log`` is written.
        webhook_url: HTTP endpoint for JSON POST alerts (empty → disabled).
    """

    def __init__(self, log_dir: Path, webhook_url: str = "") -> None:
        self._log_dir     = log_dir
        self._webhook_url = webhook_url
        self._alerts_file = log_dir / "alerts.log"

    def send(self, level: str, message: str) -> None:
        """Dispatch an alert to all configured outputs."""
        self._to_file(level, message)
        if self._webhook_url:
            self._to_webhook(level, message)

    # ── Outputs ───────────────────────────────────────────────────────────────

    def _to_file(self, level: str, message: str) -> None:
        self._log_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        line = f"{ts}  {level}  {message}\n"
        with self._alerts_file.open("a", encoding="utf-8") as fh:
            fh.write(line)

    def _to_webhook(self, level: str, message: str) -> None:
        try:
            import urllib.request

            payload = json.dumps(
                {"level": level, "message": message, "ts": time.time()}
            ).encode()
            req = urllib.request.Request(
                self._webhook_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
                if resp.status >= 400:
                    raise RuntimeError(f"HTTP {resp.status}")
        except Exception as exc:
            # Retry once, then give up silently (must not crash the logger).
            try:
                import urllib.request as _ur

                _ur.urlopen(req, timeout=5)  # type: ignore[name-defined]
            except Exception:
                logging.getLogger(__name__).warning(
                    "AlertDispatcher: webhook delivery failed (%s)", exc
                )


class AlertHandler(logging.Handler):
    """A logging.Handler that forwards WARNING+ records to AlertDispatcher.

    Attach to the root logger so every WARNING/ERROR/CRITICAL automatically
    triggers the configured alert outputs.
    """

    def __init__(self, dispatcher: AlertDispatcher, level: int = logging.WARNING) -> None:
        super().__init__(level)
        self._dispatcher = dispatcher

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._dispatcher.send(record.levelname, self.format(record))
        except Exception:
            self.handleError(record)
