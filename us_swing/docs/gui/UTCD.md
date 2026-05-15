# Unit Test Case Document — GUI Module (GUI)

**Document ID:** UTCD-GUI
**Version:** 1.1.0
**Traces To:** MD-GUI v1.0.0
**Status:** Draft
**Last Updated:** 2026-03-16
**Project:** US Swing Trading System

> Tests written BEFORE implementation per process.md §7.
> GUI tests use `pytest-qt` (`qtbot` fixture) for widget testing.

---

## Module: `gui/main_window.py` — MainWindow

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-GUI-001.001.M01.T01 | MD-GUI-001.001.M01 | Unit | MainWindow creates exactly 4 nav tab buttons in `_TitleBar` | Construct `MainWindow(svc)` | `len(window._title_bar._tabs) == 4`; labels: Dashboard, Screener, Execution, Settings | Implemented |
| UT-GUI-001.001.M01.T02 | MD-GUI-001.001.M01 | Unit | Status bar has Internet pill, P&L, Positions (left) and NYSE, NASDAQ pills (right) | Construct `MainWindow(svc)` | `_sb_conn`, `_sb_pnl`, `_sb_pos`, `_sb_nyse`, `_sb_nasdaq` exist and are visible | Implemented |
| UT-GUI-001.001.M01.T03 | MD-GUI-001.001.M01 | Unit | Scope combo change updates `_AdminContextBar` scope icon | `svc.set_viewing_uid(user_id)` emits `viewing_changed` | `_admin_ctx_bar._scope_icon.text() == "👤"` for single-user; `"🌐"` for all-users | Implemented |
| UT-GUI-001.001.M01.T04 | MD-GUI-001.001.M01 | Unit | `feed_status_changed("connected")` updates feed button text | Emit `svc.feed_status_changed("connected")` | `_title_bar._feed_btn.text() == "🟢  Connected"` | Implemented |
| UT-GUI-001.001.M01.T05 | MD-GUI-001.001.M01 | Unit | Window geometry saved on close | Close window | `QSettings("USSwing", "MainWindow")` contains `"geometry"` key | Implemented |
| UT-GUI-001.001.M01.T06 | MD-GUI-001.001.M01 | Unit | Window geometry restored on launch | Pre-set `QSettings` geometry | Window position matches saved values | Implemented |

---

## Module: `gui/position_table_model.py` — PositionTableModel

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-GUI-002.001.M02.T01 | MD-GUI-002.001.M02 | Unit | Empty model has 0 rows, 9 columns (base, no User col) | `PositionTableModel()` with no positions | `rowCount() == 0`; `columnCount() == 9` | Implemented |
| UT-GUI-002.001.M02.T02 | MD-GUI-002.001.M02 | Unit | User column prepended when `set_show_user(True)` | `set_show_user(True, {1: "alice"})` | `columnCount() == 10`; `headerData(0) == "User"` | Implemented |
| UT-GUI-002.001.M02.T03 | MD-GUI-002.001.M02 | Unit | Positive P&L cell has green-tinted background and green foreground | Position with `unrealised_pnl=500` | `BackgroundRole == QColor(C.PNL_POS_BG)`; `ForegroundRole == QColor(C.GREEN)` | Implemented |
| UT-GUI-002.001.M02.T04 | MD-GUI-002.001.M02 | Unit | Negative P&L cell has red-tinted background and red foreground | Position with `unrealised_pnl=-200` | `BackgroundRole == QColor(C.PNL_NEG_BG)`; `ForegroundRole == QColor(C.RED)` | Implemented |
| UT-GUI-002.001.M02.T05 | MD-GUI-002.001.M02 | Unit | `refresh()` resets model and reflects new positions | `refresh([pos1, pos2])` | `rowCount() == 2`; `modelReset` signal emitted via `beginResetModel/endResetModel` | Implemented |

---

## Module: `gui/screener_panel.py` — ScreenerPanel

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-GUI-003.001.M01.T01 | MD-GUI-003.001.M01 | Unit | Filter chips reflect enabled state from `AppService.get_screener_filters()` | Service returns 2 of 5 filters enabled | 2 `_FilterChip` checkboxes checked, 3 unchecked | Approved |
| UT-GUI-003.001.M01.T02 | MD-GUI-003.001.M01 | Unit | "Run Screener" button disabled during execution | Click run; check button state immediately | `_run_btn.isEnabled() == False`; re-enabled on `_ScreenerWorker.finished` | Approved |
| UT-GUI-003.001.M01.T03 | MD-GUI-003.001.M01 | Unit | Results table populated after screener run | Worker emits `finished` with 10 results | `_results_model.rowCount() == 10` | Approved |
| UT-GUI-003.001.M01.T04 | MD-GUI-003.001.M01 | Unit | Filter chip spinboxes disabled when chip unchecked | Uncheck a `_FilterChip` | All `_spins` in that chip have `isEnabled() == False` | Approved |

---

## Module: `gui/execution_panel.py` — ExecutionPanel

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-GUI-004.001.M01.T01 | MD-GUI-004.001.M01 | Unit | Signal rows created from `AppService.get_pending_signals()` at init | Service returns 2 signals | `len(panel._signal_rows) == 2`; each row has symbol label and Execute button | Implemented |
| UT-GUI-004.001.M01.T02 | MD-GUI-004.001.M01 | Unit | Override qty shows "(overridden)" when value differs from recommended | Set `_spin.value` != `signal.recommended_qty` | `_override_lbl.text() == "(overridden)"` | Implemented |
| UT-GUI-004.001.M01.T03 | MD-GUI-004.001.M01 | Unit | Override qty spinbox minimum is 1 | Attempt to set value to 0 | `_spin.value() == 1` (clamped by `setRange(1, 10_000)`) | Implemented |
| UT-GUI-004.001.M01.T04 | MD-GUI-004.001.M01 | Unit | Circuit breaker disables all execute buttons and shows banner | `panel.on_circuit_breaker(True)` | All `_SignalRow._exec_btn.isEnabled() == False`; `_cb_banner.isVisible() == True` | Implemented |
| UT-GUI-004.001.M01.T05 | MD-GUI-004.001.M01 | Unit | `viewing_changed` syncs Execute-for combo to current scope | `svc.set_viewing_uid(user_id)` | `_exec_user_combo` index matches `user_id` entry | Implemented |

---

## Module: `gui/position_monitor_panel.py` — PositionMonitorPanel

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-GUI-005.001.M01.T01 | MD-GUI-005.001.M01 | Unit | Positions from `AppService.get_positions()` shown on init | Service returns 2 OPEN positions | `_pos_model.rowCount() == 2` | Implemented |
| UT-GUI-005.001.M01.T02 | MD-GUI-005.001.M01 | Unit | Capital indicator shows correct available amount | `equity=100_000`, `open_position_value=30_000` | `_remaining_lbl.text() == "$70,000  of  $100,000"` | Implemented |
| UT-GUI-005.001.M01.T03 | MD-GUI-005.001.M01 | Unit | "CAN ENTER" badge when capital available | `available > 0` and `util_pct < max_allocation_pct` | `_can_enter.text() == "CAN ENTER"` | Implemented |
| UT-GUI-005.001.M01.T04 | MD-GUI-005.001.M01 | Unit | "CANNOT ENTER" badge when capital exhausted | `util_pct >= max_allocation_pct` | `_can_enter.text() == "CANNOT ENTER"` | Implemented |
| UT-GUI-005.001.M01.T05 | MD-GUI-005.001.M01 | Unit | Position state colour coding | OPEN and PARTIAL_EXIT positions | OPEN `BackgroundRole == QColor("#1a3326")`; PARTIAL_EXIT `QColor("#332500")` | Implemented |

---

## Module: `gui/settings_panel.py` — SettingsPanel

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-GUI-006.001.M01.T01 | MD-GUI-006.001.M01 | Unit | Settings panel has 5 sub-tabs in correct order | Construct `SettingsPanel(svc)` | `tabs.count() == 5`; tab texts: Users, Strategies, Screeners, System, Universe | Implemented |
| UT-GUI-006.001.M01.T02 | MD-GUI-006.001.M01 | Unit | New user dialog calls `AppService.add_user()` | Fill `_UserDialog` and click OK | `svc.add_user()` called once; `users_changed` triggers table refresh | Implemented |
| UT-GUI-006.001.M01.T03 | MD-GUI-006.001.M01 | Unit | Delete user blocked when `AppService.delete_user()` returns error | Select user; click Delete; confirm | Warning `QMessageBox` shown; user remains in table | Implemented |
| UT-GUI-006.001.M01.T04 | MD-GUI-006.001.M01 | Unit | Universe tab meta label shows constituent count | `svc.get_sp500_universe()` returns 503 records | `_meta_label.text()` contains `"503 constituents"` | Implemented |

---

## Module: `gui/log_viewer_panel.py` — Log Viewer

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-GUI-007.001.M01.T01 | MD-GUI-007.001.M01 | Unit | Log entries appear when `AppService.log_message` emitted | Emit `svc.log_message("INFO", "hello")` 3 times | `panel._line_count == 3`; `_log_view` is non-empty | Implemented |
| UT-GUI-007.001.M01.T02 | MD-GUI-007.001.M01 | Unit | ERROR entry emits `error_occurred` signal | Emit `svc.log_message("ERROR", "fail")` | `error_occurred` signal emitted once | Implemented |
| UT-GUI-007.001.M01.T03 | MD-GUI-007.001.M01 | Unit | Level filter hides lower-priority entries | Buffer: 2 INFO + 1 WARNING; set level combo to WARNING | `_reapply_filter()` renders 1 visible entry | Implemented |
| UT-GUI-007.001.M01.T04 | MD-GUI-007.001.M01 | Unit | Buffer evicts oldest entries when exceeding `MAX_LINES` | Push `MAX_LINES + 5` messages | `len(panel._buffer) == MAX_LINES` | Implemented |
| UT-GUI-007.001.M01.T05 | MD-GUI-007.001.M01 | Unit | Pause halts display; Resume flushes buffered entries | Pause; emit 3 messages; Resume | After Resume `_line_count` increases by 3 | Implemented |
