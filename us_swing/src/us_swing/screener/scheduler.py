"""Module: MD-SCR-004.001.M11 — screener/scheduler.py
Parent SRD: SRD-SCR-004.001–006

ScreenerScheduler — cron-based job scheduling for preset execution.
Uses APScheduler BackgroundScheduler; persists schedules to JSON.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

_SCHEDULES_DEFAULT = Path.home() / ".usswing" / "screener_schedules.json"


class CronError(ValueError):
    """Raised when an invalid cron expression is provided to the scheduler."""


class ScreenerScheduler:
    """Cron-based scheduler for preset execution.

    Schedules are persisted to ``~/.usswing/screener_schedules.json`` as a
    mapping of ``{preset_id: {"cron": "0 8 * * 1-5", "user_id": "user1"}}``.
    On ``start()``, persisted schedules are re-registered with APScheduler.

    All APScheduler dependencies are injectable to facilitate unit testing.
    """

    def __init__(
        self,
        executor: Any = None,
        schedules_file: Path | None = None,
        scheduler: Any = None,
    ) -> None:
        self._executor = executor
        self._file = schedules_file or _SCHEDULES_DEFAULT
        self._scheduler = scheduler
        self._jobs: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start APScheduler and re-register all persisted schedules."""
        if self._scheduler is None:
            from apscheduler.schedulers.background import BackgroundScheduler
            self._scheduler = BackgroundScheduler()
        self._scheduler.start()
        self._load_persisted_schedules()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def schedule(self, preset_id: str, user_id: str, cron: str) -> None:
        """Register a cron job for *preset_id* and persist to disk.

        Args:
            preset_id: Preset to execute when the job fires.
            user_id: User on whose behalf the job runs.
            cron: 5-field cron expression (e.g. ``"0 8 * * 1-5"``).

        Raises:
            CronError: if *cron* is not a valid cron expression.
        """
        trigger = self._make_trigger(cron)
        job = self._scheduler.add_job(
            self._run_preset,
            trigger=trigger,
            args=[preset_id, user_id],
            id=preset_id,
            replace_existing=True,
        )
        self._jobs[preset_id] = job
        self._persist_entry(preset_id, user_id, cron)

    def unschedule(self, preset_id: str) -> None:
        """Remove the scheduled job and delete its persisted entry."""
        if preset_id in self._jobs:
            try:
                self._scheduler.remove_job(preset_id)
            except Exception:
                pass
            del self._jobs[preset_id]
        self._delete_persisted_entry(preset_id)

    def get_schedule(self, preset_id: str) -> str | None:
        """Return the cron expression for *preset_id*, or None if unscheduled."""
        entry = self._load_file().get(preset_id)
        return entry.get("cron") if entry else None

    # ------------------------------------------------------------------
    # APScheduler callback
    # ------------------------------------------------------------------

    def _run_preset(self, preset_id: str, user_id: str) -> None:
        """Invoked by APScheduler on each cron tick."""
        if self._executor is not None:
            self._executor.run_preset(preset_id, user_id, manual=False)

    # ------------------------------------------------------------------
    # Trigger construction
    # ------------------------------------------------------------------

    def _make_trigger(self, cron: str) -> Any:
        """Parse *cron* into an APScheduler CronTrigger.

        Raises:
            CronError: if *cron* is syntactically invalid.
        """
        try:
            from apscheduler.triggers.cron import CronTrigger
            return CronTrigger.from_crontab(cron)
        except (ValueError, KeyError) as exc:
            raise CronError(f"Invalid cron expression '{cron}': {exc}") from exc

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load_file(self) -> dict[str, Any]:
        if not self._file.exists():
            return {}
        try:
            return json.loads(self._file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _persist_entry(self, preset_id: str, user_id: str, cron: str) -> None:
        schedules = self._load_file()
        schedules[preset_id] = {"cron": cron, "user_id": user_id}
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._file.write_text(json.dumps(schedules, indent=2), encoding="utf-8")

    def _delete_persisted_entry(self, preset_id: str) -> None:
        schedules = self._load_file()
        if preset_id in schedules:
            del schedules[preset_id]
            self._file.parent.mkdir(parents=True, exist_ok=True)
            self._file.write_text(json.dumps(schedules, indent=2), encoding="utf-8")

    def _load_persisted_schedules(self) -> None:
        """Re-register all persisted schedules with APScheduler on startup."""
        for preset_id, entry in self._load_file().items():
            cron = entry.get("cron", "")
            user_id = entry.get("user_id", "")
            try:
                trigger = self._make_trigger(cron)
                job = self._scheduler.add_job(
                    self._run_preset,
                    trigger=trigger,
                    args=[preset_id, user_id],
                    id=preset_id,
                    replace_existing=True,
                )
                self._jobs[preset_id] = job
            except CronError:
                _log.warning(
                    "Skipping invalid persisted cron for preset '%s': %s", preset_id, cron
                )
