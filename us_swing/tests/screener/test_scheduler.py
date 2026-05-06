"""Tests for ScreenerScheduler — UTCD-SCR test_scheduler.py (6 tests, T01–T06)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from us_swing.screener.scheduler import CronError, ScreenerScheduler


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_apscheduler() -> MagicMock:
    sched = MagicMock()
    sched.add_job.return_value = MagicMock()
    return sched


@pytest.fixture
def schedules_file(tmp_path) -> Path:
    return tmp_path / "screener_schedules.json"


@pytest.fixture
def scheduler(mock_apscheduler, schedules_file) -> ScreenerScheduler:
    return ScreenerScheduler(
        executor=MagicMock(),
        schedules_file=schedules_file,
        scheduler=mock_apscheduler,
    )


# ---------------------------------------------------------------------------
# T01  valid cron registers a job
# ---------------------------------------------------------------------------

def test_T01_schedule_valid_cron_registers_job(scheduler, mock_apscheduler):
    scheduler.schedule("daily_rsi", "user1", "0 8 * * 1-5")
    mock_apscheduler.add_job.assert_called_once()
    _, kwargs = mock_apscheduler.add_job.call_args
    assert kwargs["id"] == "daily_rsi"


# ---------------------------------------------------------------------------
# T02  invalid cron raises CronError / ValueError
# ---------------------------------------------------------------------------

def test_T02_schedule_invalid_cron_raises(scheduler):
    with pytest.raises((CronError, ValueError)):
        scheduler.schedule("bad_preset", "user1", "99 99 99 99 99")


# ---------------------------------------------------------------------------
# T03  schedule persists to JSON file
# ---------------------------------------------------------------------------

def test_T03_schedule_persists_to_json_file(scheduler, schedules_file):
    scheduler.schedule("daily_rsi", "user1", "0 8 * * 1-5")
    assert schedules_file.exists()
    data = json.loads(schedules_file.read_text())
    assert "daily_rsi" in data
    assert data["daily_rsi"]["cron"] == "0 8 * * 1-5"


# ---------------------------------------------------------------------------
# T04  load persisted schedules on startup
# ---------------------------------------------------------------------------

def test_T04_load_persisted_schedules_on_startup(mock_apscheduler, schedules_file):
    schedules_file.write_text(
        json.dumps({"daily_rsi": {"cron": "0 8 * * 1-5", "user_id": "user1"}}),
        encoding="utf-8",
    )
    sched = ScreenerScheduler(
        executor=MagicMock(),
        schedules_file=schedules_file,
        scheduler=mock_apscheduler,
    )
    sched.start()
    mock_apscheduler.add_job.assert_called()
    _, kwargs = mock_apscheduler.add_job.call_args
    assert kwargs["id"] == "daily_rsi"


# ---------------------------------------------------------------------------
# T05  unschedule removes job and deletes file entry
# ---------------------------------------------------------------------------

def test_T05_unschedule_removes_job_and_file_entry(scheduler, mock_apscheduler, schedules_file):
    scheduler.schedule("daily_rsi", "user1", "0 8 * * 1-5")
    scheduler.unschedule("daily_rsi")
    mock_apscheduler.remove_job.assert_called_with("daily_rsi")
    data = json.loads(schedules_file.read_text()) if schedules_file.exists() else {}
    assert "daily_rsi" not in data


# ---------------------------------------------------------------------------
# T06  APScheduler fires → run_preset called with manual=False
# ---------------------------------------------------------------------------

def test_T06_apscheduler_fires_calls_run_preset_with_manual_false(schedules_file):
    mock_executor = MagicMock()
    mock_apscheduler = MagicMock()
    mock_apscheduler.add_job.return_value = MagicMock()
    sched = ScreenerScheduler(
        executor=mock_executor,
        schedules_file=schedules_file,
        scheduler=mock_apscheduler,
    )
    sched.schedule("daily_rsi", "user1", "0 8 * * 1-5")
    sched._run_preset("daily_rsi", "user1")
    mock_executor.run_preset.assert_called_once_with("daily_rsi", "user1", manual=False)
