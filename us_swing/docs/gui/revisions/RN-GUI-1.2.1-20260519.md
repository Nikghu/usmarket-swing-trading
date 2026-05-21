# RN-GUI-1.2.1-20260519 — GUI v1.2.1

**Date:** 2026-05-19
**Tool:** GUI (Graphical Interface)
**Version:** 1.2.1
**Type:** Bugfix

## Summary

The TWS login window is now pinned always-on-top (`HWND_TOPMOST` via `SetWindowPos`) for the entire duration of the credential fill so it cannot be obscured by other windows during the fill sequence. A `finally` block releases the pin (`HWND_NOTOPMOST`) after the fill completes, regardless of success or error, so TWS does not remain permanently on top.

## Changed Modules

| MD ID | File | Change Description |
|---|---|---|
| MD-GUI-000.004 | `gui/scheduler_dialog.py` | Wrapped `_FillWorker.run()` fill sequence in `try/finally`; pin TWS to `HWND_TOPMOST` before focus logic, unpin with `HWND_NOTOPMOST` in `finally` |

## Requirements Addressed

| SRD ID | Description | Status |
|---|---|---|
| SRD-GUI-006.005 | TWS credential fill operates without user intervention | Draft |

## Issues Resolved

None

## Test Coverage

Pending
