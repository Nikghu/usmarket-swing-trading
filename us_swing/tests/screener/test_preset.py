"""Unit tests: MD-SCR-001.001.M01 — preset.py
Refs: UT-SCR-001.001.M01.T01 – UT-SCR-001.001.M01.T20
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from us_swing.screener.base import PresetValidationError
from us_swing.screener.preset import GroupLogic, Preset, PresetType, ScreenerGroup, ScreenerRef


# ---------------------------------------------------------------------------
# T01 — to_dict() produces JSON-compatible types
# ---------------------------------------------------------------------------

def test_t01_to_dict_json_compatible(composite_preset):
    """UT-SCR-001.001.M01.T01"""
    d = composite_preset.to_dict()
    assert isinstance(d["created_at"], str), "created_at must be a string"
    assert "T" in d["created_at"], "created_at must contain ISO-8601 'T' separator"
    assert isinstance(d["preset_type"], str), "preset_type must be a plain string, not Enum"
    assert isinstance(d["groups"], list)


# ---------------------------------------------------------------------------
# T02 — round-trip: from_dict(to_dict()) ≡ original
# ---------------------------------------------------------------------------

def test_t02_round_trip(composite_preset):
    """UT-SCR-001.001.M01.T02"""
    restored = Preset.from_dict(composite_preset.to_dict())
    assert restored == composite_preset


# ---------------------------------------------------------------------------
# T03 — composite preset with 2 groups validates without error
# ---------------------------------------------------------------------------

def test_t03_composite_validates(composite_preset):
    """UT-SCR-001.001.M01.T03"""
    composite_preset.validate()  # must not raise


# ---------------------------------------------------------------------------
# T04 — weighted preset with valid weights and threshold validates
# ---------------------------------------------------------------------------

def test_t04_weighted_validates(weighted_preset):
    """UT-SCR-001.001.M01.T04"""
    weighted_preset.validate()  # must not raise


# ---------------------------------------------------------------------------
# T05 — validate() raises PresetValidationError for empty (invalid) screener_id
# ---------------------------------------------------------------------------

def test_t05_unknown_screener_id_raises():
    """UT-SCR-001.001.M01.T05"""
    ref = ScreenerRef(screener_id="")  # empty string = structurally invalid
    group = ScreenerGroup(group_id="g1", screeners=[ref])
    preset = Preset(
        id="p1",
        name="Bad",
        preset_type=PresetType.COMPOSITE,
        groups=[group],
    )
    with pytest.raises(PresetValidationError):
        preset.validate()


# ---------------------------------------------------------------------------
# T06 — validate() raises error when Weighted preset has no threshold
# ---------------------------------------------------------------------------

def test_t06_missing_threshold_raises(weighted_preset):
    """UT-SCR-001.001.M01.T06"""
    weighted_preset.threshold = None
    with pytest.raises(PresetValidationError):
        weighted_preset.validate()


# ---------------------------------------------------------------------------
# T07 — validate() raises error on non-unique group IDs
# ---------------------------------------------------------------------------

def test_t07_duplicate_group_ids_raises():
    """UT-SCR-001.001.M01.T07"""
    ref = ScreenerRef(screener_id="s1")
    group1 = ScreenerGroup(group_id="g1", screeners=[ref])
    group2 = ScreenerGroup(group_id="g1", screeners=[ref])  # duplicate id
    preset = Preset(
        id="p1",
        name="Bad",
        preset_type=PresetType.COMPOSITE,
        groups=[group1, group2],
    )
    with pytest.raises(PresetValidationError):
        preset.validate()


# ---------------------------------------------------------------------------
# T08 — ScreenerRef.enabled flag can be toggled independently
# ---------------------------------------------------------------------------

def test_t08_screener_ref_enabled_toggle():
    """UT-SCR-001.001.M01.T08"""
    ref = ScreenerRef(screener_id="s1", enabled=True)
    ref.enabled = False
    assert ref.enabled is False


# ---------------------------------------------------------------------------
# T09 — ScreenerGroup raises on invalid logic value
# ---------------------------------------------------------------------------

def test_t09_screener_group_invalid_logic_raises():
    """UT-SCR-001.001.M01.T09"""
    with pytest.raises((ValueError, KeyError)):
        ScreenerGroup(group_id="g1", logic="XOR")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# T10 — from_dict() applies defaults for missing optional fields
# ---------------------------------------------------------------------------

def test_t10_from_dict_missing_optional_uses_defaults():
    """UT-SCR-001.001.M01.T10"""
    d = {"id": "p1", "name": "Test", "preset_type": "composite"}
    preset = Preset.from_dict(d)
    assert preset.description == ""
    assert preset.groups == []
    assert preset.screeners == []
    assert preset.is_admin is False
    assert preset.enable_llm_ranking is False
    assert preset.top_n == 5


# ---------------------------------------------------------------------------
# T11 — from_dict() ignores unknown top-level keys silently
# ---------------------------------------------------------------------------

def test_t11_from_dict_unknown_keys_ignored():
    """UT-SCR-001.001.M01.T11"""
    d = {
        "id": "p1",
        "name": "Test",
        "preset_type": "composite",
        "extra_field": 123,
    }
    preset = Preset.from_dict(d)  # must not raise
    assert not hasattr(preset, "extra_field")


# ---------------------------------------------------------------------------
# T12 — to_dict() produces 'Z'-terminated ISO-8601 for UTC datetimes
# ---------------------------------------------------------------------------

def test_t12_iso8601_utc_format():
    """UT-SCR-001.001.M01.T12"""
    dt = datetime(2026, 4, 16, 10, 30, 0, tzinfo=timezone.utc)
    preset = Preset(
        id="p1",
        name="Test",
        preset_type=PresetType.COMPOSITE,
        created_at=dt,
        updated_at=dt,
    )
    d = preset.to_dict()
    assert d["created_at"] == "2026-04-16T10:30:00Z"
    assert d["updated_at"] == "2026-04-16T10:30:00Z"


# ---------------------------------------------------------------------------
# T13 — trading_styles serializes and round-trips correctly
# ---------------------------------------------------------------------------

def test_t13_trading_styles_roundtrip():
    """UT-SCR-001.001.M01.T13"""
    preset = Preset(
        id="p1",
        name="Swing + Day",
        preset_type=PresetType.COMPOSITE,
        trading_styles=["swing", "day"],
    )
    d = preset.to_dict()
    assert d["trading_styles"] == ["swing", "day"]
    restored = Preset.from_dict(d)
    assert restored.trading_styles == ["swing", "day"]


# ---------------------------------------------------------------------------
# T14 — empty trading_styles serializes to []
# ---------------------------------------------------------------------------

def test_t14_empty_trading_styles_serializes_to_empty_list():
    """UT-SCR-001.001.M01.T14"""
    preset = Preset(id="p2", name="Untagged", preset_type=PresetType.COMPOSITE)
    d = preset.to_dict()
    assert d["trading_styles"] == []


# ---------------------------------------------------------------------------
# T15 — validate() raises PresetValidationError on unknown style
# ---------------------------------------------------------------------------

def test_t15_validate_rejects_unknown_style():
    """UT-SCR-001.001.M01.T15"""
    preset = Preset(
        id="p3",
        name="Bad Style",
        preset_type=PresetType.COMPOSITE,
        trading_styles=["scalp"],
    )
    with pytest.raises(PresetValidationError, match="scalp"):
        preset.validate()


# ---------------------------------------------------------------------------
# T16 — from_dict() on JSON without trading_styles defaults to []
# ---------------------------------------------------------------------------

def test_t16_from_dict_missing_trading_styles_defaults_to_empty():
    """UT-SCR-001.001.M01.T16"""
    raw = {
        "id": "old_preset",
        "name": "Legacy",
        "preset_type": "composite",
    }
    preset = Preset.from_dict(raw)
    assert preset.trading_styles == []


# ---------------------------------------------------------------------------
# T17 — ai_query / ai_model defaults and round-trip (SRD-SCR-013.001)
# ---------------------------------------------------------------------------

def test_t17_ai_fields_defaults_and_roundtrip():
    """UT-SCR-001.001.M01.T17"""
    preset = Preset(id="p1", name="Default", preset_type=PresetType.COMPOSITE)
    assert preset.ai_query == ""
    assert preset.ai_model == "claude-haiku-4-5-20251001"

    preset.ai_query = "find bullish breakout candidates"
    preset.ai_model = "claude-sonnet-4-5-20250929"
    d = preset.to_dict()
    assert d["ai_query"] == "find bullish breakout candidates"
    assert d["ai_model"] == "claude-sonnet-4-5-20250929"

    restored = Preset.from_dict(d)
    assert restored.ai_query == preset.ai_query
    assert restored.ai_model == preset.ai_model


# ---------------------------------------------------------------------------
# T18 — legacy JSON without ai_query / ai_model loads with defaults
# ---------------------------------------------------------------------------

def test_t18_legacy_json_without_ai_fields():
    """UT-SCR-001.001.M01.T18"""
    raw = {"id": "legacy", "name": "Legacy", "preset_type": "composite"}
    preset = Preset.from_dict(raw)
    assert preset.ai_query == ""
    assert preset.ai_model == "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# T19 — validate() rejects ai_query longer than 500 chars
# ---------------------------------------------------------------------------

def test_t19_ai_query_max_length_enforced():
    """UT-SCR-001.001.M01.T19"""
    preset = Preset(
        id="p1",
        name="Long Query",
        preset_type=PresetType.COMPOSITE,
        enable_llm_ranking=True,
        ai_query="x" * 501,
    )
    with pytest.raises(PresetValidationError, match="ai_query"):
        preset.validate()


# ---------------------------------------------------------------------------
# T20 — empty ai_query is always valid (legacy fallback path)
# ---------------------------------------------------------------------------

def test_t20_empty_ai_query_is_valid():
    """UT-SCR-001.001.M01.T20"""
    preset = Preset(
        id="p1",
        name="Empty Query",
        preset_type=PresetType.COMPOSITE,
        enable_llm_ranking=True,
        ai_query="",
    )
    preset.validate()  # must not raise — legacy ranking path
