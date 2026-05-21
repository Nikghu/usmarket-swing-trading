# Revision Note — RN-GUI-1.2.2-20260521

**Version:** 1.2.2
**Date:** 2026-05-21
**Tool:** GUI
**Artifact:** Code refactor — Strategy Executor table columns added (prototype, no FO assigned)
**Type:** Refactor

---

## Summary

Added seven new data columns to the Strategy Executor table (StrategyTableModel): Trade Type, Start Date, End Date, Target, Target Type, Stop Loss, and Stop Loss Type. Conditional display ensures Target and Stop Loss values appear only when enabled, with their type selectors (Fixed/Trailing) visible only alongside enabled values. Also added 1-based row numbers to the vertical header by implementing `headerData()` with `Qt.Vertical` orientation support. Execution panel now exposes all column constants and configures widths for the new columns.

---

## Modified Files

| MD ID | File | Change |
|---|---|---|
| — | `src/us_swing/gui/strategy_table_model.py` | New file: StrategyTableModel with 7 new columns (Trade Type, Start Date, End Date, Target, Target Type, Stop Loss, Stop Loss Type); `headerData()` returns 1-based row numbers for vertical orientation |
| MD-GUI-004.001.M01 | `src/us_swing/gui/execution_panel.py` | Imported 7 new column constants; added column width configuration for each new column; enabled vertical header visibility (setVisible + setMinimumWidth) |

---

## Requirements Addressed

| SRD ID | Description | Status |
|---|---|---|
| — | Prototype refactor — no formal SRD assigned | Design Document |

---

## Design Decisions

- **Conditional Value Display:** Target and Stop Loss fields show numeric value (e.g., "2.0%") only when enabled in the UI; disabled state displays "—" (em dash) for clarity.
- **Type Selector Visibility:** Target Type and Stop Loss Type columns display "Fixed" or "Trailing" only when their parent (Target/Stop Loss) is enabled; disabled state shows "—".
- **Row Numbers:** Implemented via `headerData()` with `Qt.Vertical` orientation; returns 1-based index to match user expectations (row 1, row 2, etc.).
- **Column Constants:** All new columns exported from strategy_table_model as module-level constants (`COL_TRADE_TYPE`, `COL_START_DATE`, `COL_END_DATE`, `COL_TARGET`, `COL_TARGET_TYPE`, `COL_STOP_LOSS`, `COL_STOP_LOSS_TYPE`) for centralized width management in execution_panel.

---

## Issues Resolved

None — prototype refactor with no issues assigned.

---

## Test Coverage

Pending — UTCD test cases not yet specified. This refactor is prototype work awaiting FO-GUI-013 (Strategy Builder Dialog) approval before writing formal tests.

---

## Notes

This session documents **prototype work only**. No formal FO has been assigned; these changes prepare the UI layer for the upcoming Strategy Builder feature. Once FO-GUI-013 is approved and traced through SRD/DD/MD/UTCD, test coverage will be added. The row-number implementation is complete and ready for integration; column constants follow project conventions for centralized layout management.
