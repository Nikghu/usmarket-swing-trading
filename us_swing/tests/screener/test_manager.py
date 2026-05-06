"""Tests for PresetManager — UTCD-SCR test_manager.py (20 tests, T01–T20)."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from us_swing.screener.base import PresetAccessDenied, PresetNotFoundError
from us_swing.screener.manager import PresetManager
from us_swing.screener.preset import Preset, PresetType

from tests.screener.conftest import make_composite_preset, make_weighted_preset


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mgr(tmp_path) -> PresetManager:
    return PresetManager(base_dir=tmp_path / "scr")


@pytest.fixture
def admin_preset() -> Preset:
    p = make_composite_preset("admin1")
    p.is_admin = True
    return p


@pytest.fixture
def user_preset() -> Preset:
    return make_composite_preset("user_p1")


# ---------------------------------------------------------------------------
# T01–T04  create_preset
# ---------------------------------------------------------------------------

def test_T01_create_admin_preset_goes_to_admin_path(mgr, admin_preset):
    path = mgr.create_preset(admin_preset, user_id="admin", is_admin_user=True)
    assert path == mgr._admin_path("admin1")
    assert path.exists()


def test_T02_create_user_preset_goes_to_user_path(mgr, user_preset):
    path = mgr.create_preset(user_preset, user_id="user1")
    assert path == mgr._user_path("user1", "user_p1")
    assert path.exists()


def test_T03_non_admin_cannot_create_admin_preset(mgr):
    p = make_composite_preset("forbidden")
    p.is_admin = True
    with pytest.raises(PresetAccessDenied):
        mgr.create_preset(p, user_id="user1", is_admin_user=False)


def test_T04_create_sets_created_at_and_created_by(mgr):
    p = make_composite_preset("meta_test")
    before = datetime.now(timezone.utc)
    mgr.create_preset(p, user_id="user1")
    assert p.created_by == "user1"
    assert p.created_at >= before


# ---------------------------------------------------------------------------
# T05–T06  load_preset
# ---------------------------------------------------------------------------

def test_T05_load_returns_preset_instance(mgr):
    p = make_composite_preset("loadme")
    mgr.create_preset(p, user_id="user1")
    loaded = mgr.load_preset("loadme", "user1")
    assert isinstance(loaded, Preset)
    assert loaded.id == "loadme"


def test_T06_load_raises_access_denied_for_unauthorized_user(mgr):
    p = make_composite_preset("private")
    mgr.create_preset(p, user_id="user1")
    with pytest.raises(PresetAccessDenied):
        mgr.load_preset("private", "user2")


# ---------------------------------------------------------------------------
# T07–T08  list_*_presets
# ---------------------------------------------------------------------------

def test_T07_list_admin_presets_returns_all_admin(mgr):
    for pid in ("a1", "a2"):
        p = make_composite_preset(pid)
        p.is_admin = True
        mgr.create_preset(p, user_id="admin", is_admin_user=True)
    results = mgr.list_admin_presets()
    assert len(results) == 2
    assert all(p.is_admin for p in results)


def test_T08_list_user_presets_returns_own_and_shared(mgr):
    own = make_composite_preset("own_u2")
    mgr.create_preset(own, user_id="user2")

    shared = make_composite_preset("shared_for_u2")
    shared.assigned_to = ["user2"]
    mgr.create_preset(shared, user_id="user1")

    not_shared = make_composite_preset("not_shared")
    mgr.create_preset(not_shared, user_id="user1")

    presets = mgr.list_user_presets("user2")
    ids = [p.id for p in presets]
    assert "own_u2" in ids
    assert "shared_for_u2" in ids
    assert "not_shared" not in ids


# ---------------------------------------------------------------------------
# T09–T10  update_preset
# ---------------------------------------------------------------------------

def test_T09_update_raises_access_denied_for_non_creator(mgr):
    p = make_composite_preset("upd1")
    mgr.create_preset(p, user_id="user1")
    with pytest.raises(PresetAccessDenied):
        mgr.update_preset("upd1", {"name": "hacked"}, "user2")


def test_T10_update_updates_updated_at(mgr):
    p = make_composite_preset("upd2")
    mgr.create_preset(p, user_id="user1")
    old_ts = p.updated_at
    time.sleep(0.05)
    updated = mgr.update_preset("upd2", {"name": "New Name"}, "user1")
    assert updated.updated_at > old_ts
    assert updated.name == "New Name"


# ---------------------------------------------------------------------------
# T11–T12  delete_preset
# ---------------------------------------------------------------------------

def test_T11_delete_removes_preset_file(mgr):
    p = make_composite_preset("del1")
    mgr.create_preset(p, user_id="user1")
    mgr.delete_preset("del1", "user1")
    with pytest.raises((PresetNotFoundError, FileNotFoundError)):
        mgr.load_preset("del1", "user1")


def test_T12_delete_removes_results_directory(mgr):
    p = make_composite_preset("del2")
    mgr.create_preset(p, user_id="user1")
    results_dir = mgr._results_dir("del2")
    results_dir.mkdir(parents=True)
    (results_dir / "2026-04-16.json").write_text("{}")
    mgr.delete_preset("del2", "user1")
    assert not results_dir.exists()


# ---------------------------------------------------------------------------
# T13–T14  grant/revoke access
# ---------------------------------------------------------------------------

def test_T13_grant_access_adds_users_to_assigned_to(mgr):
    p = make_composite_preset("acc1")
    mgr.create_preset(p, user_id="user1")
    updated = mgr.grant_access("acc1", ["user2", "user3"], "user1")
    assert "user2" in updated.assigned_to
    assert "user3" in updated.assigned_to


def test_T14_revoke_access_removes_user_from_assigned_to(mgr):
    p = make_composite_preset("acc2")
    p.assigned_to = ["user2", "user3"]
    mgr.create_preset(p, user_id="user1")
    updated = mgr.revoke_access("acc2", "user2", "user1")
    assert "user2" not in updated.assigned_to
    assert "user3" in updated.assigned_to


# ---------------------------------------------------------------------------
# T15  v1 migration
# ---------------------------------------------------------------------------

def test_T15_migrate_v1_creates_user_preset_with_indicator(mgr):
    v1_config = {
        "id": "legacy_screener",
        "name": "Old Screener",
        "filters": {"rsi": {"enabled": True, "min": 30, "max": 70}},
    }
    preset = mgr.migrate_v1_presets("user1", v1_config)
    assert preset.id == "legacy_screener"
    assert preset.preset_type == PresetType.WEIGHTED
    assert len(preset.screeners) == 1
    assert preset.screeners[0].screener_id == "indicator_composite"
    assert preset.screeners[0].config == v1_config
    assert mgr._user_path("user1", "legacy_screener").exists()


# ---------------------------------------------------------------------------
# T16–T20 — style_filter on list methods (SRD-SCR-005.004)
# ---------------------------------------------------------------------------

def _make_admin_preset(mgr: PresetManager, pid: str, styles: list[str]) -> None:
    p = make_composite_preset(pid)
    p.is_admin = True
    p.trading_styles = styles
    mgr.create_preset(p, user_id="admin", is_admin_user=True)


def test_t16_list_admin_style_filter_swing_includes_swing_and_untagged(mgr):
    """UT-SCR-005.001.M12.T16"""
    _make_admin_preset(mgr, "swing_only", ["swing"])
    _make_admin_preset(mgr, "day_only", ["day"])
    _make_admin_preset(mgr, "untagged", [])
    results = mgr.list_admin_presets(style_filter="swing")
    ids = {p.id for p in results}
    assert "swing_only" in ids
    assert "untagged" in ids
    assert "day_only" not in ids


def test_t17_list_user_style_filter_day(mgr):
    """UT-SCR-005.001.M12.T17"""
    p_day = make_composite_preset("p_day")
    p_day.trading_styles = ["day"]
    mgr.create_preset(p_day, user_id="alice")

    p_pos = make_composite_preset("p_pos")
    p_pos.trading_styles = ["position"]
    mgr.create_preset(p_pos, user_id="alice")

    p_untagged = make_composite_preset("p_untagged")
    mgr.create_preset(p_untagged, user_id="alice")

    results = mgr.list_user_presets("alice", style_filter="day")
    ids = {p.id for p in results}
    assert "p_day" in ids
    assert "p_untagged" in ids
    assert "p_pos" not in ids


def test_t18_list_style_filter_none_returns_all(mgr):
    """UT-SCR-005.001.M12.T18"""
    _make_admin_preset(mgr, "a1", ["swing"])
    _make_admin_preset(mgr, "a2", ["day"])
    _make_admin_preset(mgr, "a3", [])
    results = mgr.list_admin_presets(style_filter=None)
    assert len(results) == 3


def test_t19_invalid_style_filter_raises_value_error(mgr):
    """UT-SCR-005.001.M12.T19"""
    with pytest.raises(ValueError, match="scalp"):
        mgr.list_admin_presets(style_filter="scalp")
    with pytest.raises(ValueError, match="scalp"):
        mgr.list_user_presets("alice", style_filter="scalp")


def test_t20_untagged_preset_appears_in_every_style_filter(mgr):
    """UT-SCR-005.001.M12.T20"""
    _make_admin_preset(mgr, "untagged", [])
    for style in ("swing", "day", "position"):
        results = mgr.list_admin_presets(style_filter=style)
        assert any(p.id == "untagged" for p in results), f"untagged missing for filter={style!r}"
