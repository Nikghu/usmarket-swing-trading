# ISS-SCR-0001 — Edit Preset: Assigned Users Not Persisted on Save

**Date:** 2026-05-05
**Reported by:** User
**Severity:** Medium
**Status:** Resolved

## Summary

After adding a user in the "Assign Users" section of the Edit Preset dialog and clicking Save, the assigned user disappears when the dialog is reopened.

## Reproduction Steps

1. Right-click an existing (non-admin) preset → Edit Preset
2. In the Assign Users section, click "+ Add User"
3. Select a user in the picker and confirm
4. Click Save
5. Reopen Edit Preset → assigned user is gone

## Root Cause

`_PresetBuilderDialog._on_save` builds an update dict via `_build_preset_from_ui()`, which constructs a fresh `Preset(...)` without `assigned_to` — the dataclass default is `[]`. This empty list is then passed to `PresetManager.update_preset()`, which calls `setattr(preset, "assigned_to", [])` and persists the preset, overwriting any assignments that `_AssignUsersWidget` had already written via `grant_access()` when the user confirmed the picker.

**SRD root cause:** code diverged from SRD-SCR-005.005 / SRD-SCR-007.012 — SRD status unchanged (stays Approved).

## Fix

In `_PresetBuilderDialog._on_save`, pop `"assigned_to"` from the updates dict before calling `update_preset` when `_assign_widget is not None`. The widget manages access writes directly and immediately (on picker-accept); the update dict must not override them.

**File:** `us_swing/src/us_swing/gui/screener_panel.py` (lines ~2341–2344)

## Related

- SRD-SCR-005.007 (`grant_access`)
- SRD-SCR-005.008 (`revoke_access`)
- SRD-SCR-007.012 (`_AssignUsersWidget`)
- RN-SCR-1.0.1-20260505
