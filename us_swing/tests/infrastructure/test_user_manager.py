"""Unit tests — MD-INF-006.001.M01 UserManager.

Refs: UT-INF-006.001.M01.T01 – T09
"""
from __future__ import annotations

import json

import pytest

from us_swing.config.settings import AppConfig
from us_swing.data.models import UserProfile, UserRecord
from us_swing.db.manager import DatabaseManager
from us_swing.exceptions import (
    ConfirmationRequiredError,
    DuplicateUserError,
    LiveModeDisabledError,
    UserNotFoundError,
)
from us_swing.user.manager import UserManager

_LIVE_TOKEN = "CONFIRM_LIVE_TRADING"


def _make_manager(db: DatabaseManager, cfg: AppConfig | None = None) -> UserManager:
    return UserManager(db=db, cfg=cfg or AppConfig())


def test_T01_create_user_returns_profile_with_paper_mode(in_memory_db: DatabaseManager) -> None:
    """UT-INF-006.001.M01.T01 — create_user() returns UserProfile with username and mode=paper."""
    mgr = _make_manager(in_memory_db)
    profile = mgr.create_user("trader1", "Trader One", ibkr_client_id=101)
    assert isinstance(profile, UserProfile)
    assert profile.username == "trader1"
    assert profile.mode == "paper"


def test_T02_create_user_duplicate_raises(in_memory_db: DatabaseManager) -> None:
    """UT-INF-006.001.M01.T02 — create_user() raises DuplicateUserError on duplicate username."""
    mgr = _make_manager(in_memory_db)
    mgr.create_user("trader1", "Trader One", ibkr_client_id=101)
    with pytest.raises(DuplicateUserError):
        mgr.create_user("trader1", "Trader One Again", ibkr_client_id=102)


def test_T03_get_user_parses_risk_config(in_memory_db: DatabaseManager) -> None:
    """UT-INF-006.001.M01.T03 — get_user() returns profile with parsed risk_config."""
    settings = {
        "risk_config": {"risk_per_trade_pct": 2.0},
        "strategy_config": {},
        "screener_config": {},
    }
    record = UserRecord(
        user_id=0, username="trader2", display_name="Trader Two",
        ibkr_client_id=102, settings_json=json.dumps(settings), mode="paper",
    )
    user_id = in_memory_db.insert_user(record)
    mgr = _make_manager(in_memory_db)
    profile = mgr.get_user(user_id)
    assert profile.risk_config.risk_per_trade_pct == 2.0


def test_T04_get_user_not_found_raises(in_memory_db: DatabaseManager) -> None:
    """UT-INF-006.001.M01.T04 — get_user() raises UserNotFoundError for unknown ID."""
    mgr = _make_manager(in_memory_db)
    with pytest.raises(UserNotFoundError):
        mgr.get_user(9999)


def test_T05_update_user_modifies_specified_field(in_memory_db: DatabaseManager) -> None:
    """UT-INF-006.001.M01.T05 — update_user() changes only the specified field."""
    mgr = _make_manager(in_memory_db)
    profile = mgr.create_user("trader3", "Old Name", ibkr_client_id=103)
    updated = mgr.update_user(profile.user_id, display_name="New Name")
    assert updated.display_name == "New Name"
    assert updated.username == "trader3"    # unchanged


def test_T06_delete_user_retains_orphan_trades(in_memory_db: DatabaseManager) -> None:
    """UT-INF-006.001.M01.T06 — delete_user() removes user but leaves trades intact."""
    from datetime import datetime, timezone
    from us_swing.data.models import TradeRecord

    mgr = _make_manager(in_memory_db)
    profile = mgr.create_user("trader4", "Trader Four", ibkr_client_id=104)
    trade = TradeRecord(
        trade_id="TRD001", user_id=profile.user_id, symbol="AAPL",
        side="BUY", quantity=10, entry_price=150.0, mode="paper",
        strategy_id="breakout", entry_time=datetime.now(timezone.utc),
    )
    in_memory_db.insert_trade(trade)

    mgr.delete_user(profile.user_id)

    with pytest.raises(UserNotFoundError):
        mgr.get_user(profile.user_id)

    # Trades are retained (orphan records).
    import sqlalchemy as sa
    from us_swing.db.schema import trades
    with in_memory_db._engine.connect() as conn:
        count = conn.execute(
            sa.select(sa.func.count()).select_from(trades)
            .where(trades.c.trade_id == "TRD001")
        ).scalar()
    assert count == 1


def test_T07_list_users_returns_all(in_memory_db: DatabaseManager) -> None:
    """UT-INF-006.001.M01.T07 — list_users() returns all created users."""
    mgr = _make_manager(in_memory_db)
    mgr.create_user("u1", "User One",   ibkr_client_id=201)
    mgr.create_user("u2", "User Two",   ibkr_client_id=202)
    mgr.create_user("u3", "User Three", ibkr_client_id=203)
    result = mgr.list_users()
    assert len(result) == 3


def test_T08_switch_mode_live_without_token_raises(in_memory_db: DatabaseManager) -> None:
    """UT-INF-006.001.M01.T08 — switch_mode('live') without token raises ConfirmationRequiredError."""
    live_cfg = AppConfig()
    live_cfg.live_mode_enabled = True
    mgr = _make_manager(in_memory_db, cfg=live_cfg)
    profile = mgr.create_user("trader5", "Trader Five", ibkr_client_id=105)
    with pytest.raises(ConfirmationRequiredError):
        mgr.switch_mode(profile.user_id, "live")  # no token


def test_T09_switch_mode_live_with_valid_token_succeeds(in_memory_db: DatabaseManager) -> None:
    """UT-INF-006.001.M01.T09 — switch_mode('live') with correct token updates mode to 'live'."""
    live_cfg = AppConfig()
    live_cfg.live_mode_enabled = True
    mgr = _make_manager(in_memory_db, cfg=live_cfg)
    profile = mgr.create_user("trader6", "Trader Six", ibkr_client_id=106)
    updated = mgr.switch_mode(profile.user_id, "live", confirm_token=_LIVE_TOKEN)
    assert updated.mode == "live"
