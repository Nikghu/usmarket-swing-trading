"""Shared fixtures for INF unit tests."""
from __future__ import annotations

import pytest

# Import data.models first — this triggers the data→db→data.models loading chain
# via data/__init__.py (Scenario 1), which avoids the circular import that occurs
# when db/__init__.py is loaded first and db/manager.py re-enters partially.
from us_swing.data.models import OHLCVBar  # noqa: F401
from us_swing.config.settings import AppConfig
from us_swing.db.manager import DatabaseManager


@pytest.fixture
def in_memory_db() -> DatabaseManager:
    db = DatabaseManager("sqlite:///:memory:")
    db.create_schema()
    return db


@pytest.fixture
def app_config() -> AppConfig:
    return AppConfig()


@pytest.fixture
def live_config() -> AppConfig:
    cfg = AppConfig()
    cfg.live_mode_enabled = True
    return cfg
