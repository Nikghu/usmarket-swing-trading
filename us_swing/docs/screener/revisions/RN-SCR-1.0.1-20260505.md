# RN-SCR-1.0.1-20260505 — Fix Assigned Users Not Persisted on Preset Save

**Date:** 2026-05-05
**Type:** Bug Fix
**Issue:** ISS-SCR-0001
**Affected Module:** `screener_panel.py` → `_PresetBuilderDialog._on_save`

## Change Summary

Prevented `_build_preset_from_ui()` from clobbering `assigned_to` on save.

## Problem

`_PresetBuilderDialog._on_save` called `_build_preset_from_ui()` to produce an updates dict. That method constructs a fresh `Preset(...)` with no `assigned_to` field, so the dataclass default `[]` was included in the updates. `PresetManager.update_preset()` iterated the dict and set `assigned_to = []`, overwriting the assignments that `_AssignUsersWidget` had already persisted via `grant_access()`.

## Fix

Added three lines in `_on_save` (edit-mode branch):

```python
if self._assign_widget is not None:
    # Access writes happen immediately on picker-accept; don't
    # let the empty-list default from _build_preset_from_ui clobber them.
    updates.pop("assigned_to", None)
```

`_assign_widget` is only non-`None` for non-admin user-owned presets in edit mode — exactly the cases where `_AssignUsersWidget` may have called `grant_access`/`revoke_access`.

## Test Results

239 tests pass (2 pre-existing failures in `test_preset.py` related to AI-model migration — unrelated to this fix).

## SRD Impact

None. SRDs SRD-SCR-005.007 and SRD-SCR-007.012 correctly describe the intended behaviour. Code was diverged from spec; no SRD changes needed.
