# Unit Test Case Document â€” GUI Module (GUI)

**Document ID:** UTCD-GUI
**Version:** 1.2.0
**Traces To:** MD-GUI v1.2.0
**Status:** Draft
**Last Updated:** 2026-05-16
**Project:** US Swing Trading System

> Tests written BEFORE implementation per process.md Â§7.
> GUI tests use `pytest-qt` (`qtbot` fixture) for widget testing.

---

## Module: `gui/main_window.py` â€” MainWindow

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-GUI-001.001.M01.T01 | MD-GUI-001.001.M01 | Unit | MainWindow creates exactly 4 nav tab buttons in `_TitleBar` | Construct `MainWindow(svc)` | `len(window._title_bar._tabs) == 4`; labels: Dashboard, Screener, Execution, Settings | Implemented |
| UT-GUI-001.001.M01.T02 | MD-GUI-001.001.M01 | Unit | Status bar has Internet pill, P&L, Positions (left) and NYSE, NASDAQ pills (right) | Construct `MainWindow(svc)` | `_sb_conn`, `_sb_pnl`, `_sb_pos`, `_sb_nyse`, `_sb_nasdaq` exist and are visible | Implemented |
| UT-GUI-001.001.M01.T03 | MD-GUI-001.001.M01 | Unit | Scope combo change updates `_AdminContextBar` scope icon | `svc.set_viewing_uid(user_id)` emits `viewing_changed` | `_admin_ctx_bar._scope_icon.text() == "ðŸ‘¤"` for single-user; `"ðŸŒ"` for all-users | Implemented |
| UT-GUI-001.001.M01.T04 | MD-GUI-001.001.M01 | Unit | `feed_status_changed("connected")` updates feed button text | Emit `svc.feed_status_changed("connected")` | `_title_bar._feed_btn.text() == "ðŸŸ¢  Connected"` | Implemented |
| UT-GUI-001.001.M01.T05 | MD-GUI-001.001.M01 | Unit | Window geometry saved on close | Close window | `QSettings("USSwing", "MainWindow")` contains `"geometry"` key | Implemented |
| UT-GUI-001.001.M01.T06 | MD-GUI-001.001.M01 | Unit | Window geometry restored on launch | Pre-set `QSettings` geometry | Window position matches saved values | Implemented |

---

## Module: `gui/position_table_model.py` â€” PositionTableModel

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-GUI-002.001.M02.T01 | MD-GUI-002.001.M02 | Unit | Empty model has 0 rows, 9 columns (base, no User col) | `PositionTableModel()` with no positions | `rowCount() == 0`; `columnCount() == 9` | Implemented |
| UT-GUI-002.001.M02.T02 | MD-GUI-002.001.M02 | Unit | User column prepended when `set_show_user(True)` | `set_show_user(True, {1: "alice"})` | `columnCount() == 10`; `headerData(0) == "User"` | Implemented |
| UT-GUI-002.001.M02.T03 | MD-GUI-002.001.M02 | Unit | Positive P&L cell has green-tinted background and green foreground | Position with `unrealised_pnl=500` | `BackgroundRole == QColor(C.PNL_POS_BG)`; `ForegroundRole == QColor(C.GREEN)` | Implemented |
| UT-GUI-002.001.M02.T04 | MD-GUI-002.001.M02 | Unit | Negative P&L cell has red-tinted background and red foreground | Position with `unrealised_pnl=-200` | `BackgroundRole == QColor(C.PNL_NEG_BG)`; `ForegroundRole == QColor(C.RED)` | Implemented |
| UT-GUI-002.001.M02.T05 | MD-GUI-002.001.M02 | Unit | `refresh()` resets model and reflects new positions | `refresh([pos1, pos2])` | `rowCount() == 2`; `modelReset` signal emitted via `beginResetModel/endResetModel` | Implemented |

---

## Module: `gui/screener_panel.py` â€” ScreenerPanel

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-GUI-003.001.M01.T01 | MD-GUI-003.001.M01 | Unit | Filter chips reflect enabled state from `AppService.get_screener_filters()` | Service returns 2 of 5 filters enabled | 2 `_FilterChip` checkboxes checked, 3 unchecked | Approved |
| UT-GUI-003.001.M01.T02 | MD-GUI-003.001.M01 | Unit | "Run Screener" button disabled during execution | Click run; check button state immediately | `_run_btn.isEnabled() == False`; re-enabled on `_ScreenerWorker.finished` | Approved |
| UT-GUI-003.001.M01.T03 | MD-GUI-003.001.M01 | Unit | Results table populated after screener run | Worker emits `finished` with 10 results | `_results_model.rowCount() == 10` | Approved |
| UT-GUI-003.001.M01.T04 | MD-GUI-003.001.M01 | Unit | Filter chip spinboxes disabled when chip unchecked | Uncheck a `_FilterChip` | All `_spins` in that chip have `isEnabled() == False` | Approved |

---

## Module: `gui/execution_panel.py` â€” ExecutionPanel

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-GUI-004.001.M01.T01 | MD-GUI-004.001.M01 | Unit | Signal rows created from `AppService.get_pending_signals()` at init | Service returns 2 signals | `len(panel._signal_rows) == 2`; each row has symbol label and Execute button | Implemented |
| UT-GUI-004.001.M01.T02 | MD-GUI-004.001.M01 | Unit | Override qty shows "(overridden)" when value differs from recommended | Set `_spin.value` != `signal.recommended_qty` | `_override_lbl.text() == "(overridden)"` | Implemented |
| UT-GUI-004.001.M01.T03 | MD-GUI-004.001.M01 | Unit | Override qty spinbox minimum is 1 | Attempt to set value to 0 | `_spin.value() == 1` (clamped by `setRange(1, 10_000)`) | Implemented |
| UT-GUI-004.001.M01.T04 | MD-GUI-004.001.M01 | Unit | Circuit breaker disables all execute buttons and shows banner | `panel.on_circuit_breaker(True)` | All `_SignalRow._exec_btn.isEnabled() == False`; `_cb_banner.isVisible() == True` | Implemented |
| UT-GUI-004.001.M01.T05 | MD-GUI-004.001.M01 | Unit | `viewing_changed` syncs Execute-for combo to current scope | `svc.set_viewing_uid(user_id)` | `_exec_user_combo` index matches `user_id` entry | Implemented |

---

## Module: `gui/position_monitor_panel.py` â€” PositionMonitorPanel

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-GUI-005.001.M01.T01 | MD-GUI-005.001.M01 | Unit | Positions from `AppService.get_positions()` shown on init | Service returns 2 OPEN positions | `_pos_model.rowCount() == 2` | Implemented |
| UT-GUI-005.001.M01.T02 | MD-GUI-005.001.M01 | Unit | Capital indicator shows correct available amount | `equity=100_000`, `open_position_value=30_000` | `_remaining_lbl.text() == "$70,000  of  $100,000"` | Implemented |
| UT-GUI-005.001.M01.T03 | MD-GUI-005.001.M01 | Unit | "CAN ENTER" badge when capital available | `available > 0` and `util_pct < max_allocation_pct` | `_can_enter.text() == "CAN ENTER"` | Implemented |
| UT-GUI-005.001.M01.T04 | MD-GUI-005.001.M01 | Unit | "CANNOT ENTER" badge when capital exhausted | `util_pct >= max_allocation_pct` | `_can_enter.text() == "CANNOT ENTER"` | Implemented |
| UT-GUI-005.001.M01.T05 | MD-GUI-005.001.M01 | Unit | Position state colour coding | OPEN and PARTIAL_EXIT positions | OPEN `BackgroundRole == QColor("#1a3326")`; PARTIAL_EXIT `QColor("#332500")` | Implemented |

---

## Module: `gui/settings_panel.py` â€” SettingsPanel

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-GUI-006.001.M01.T01 | MD-GUI-006.001.M01 | Unit | Settings panel has 5 sub-tabs in correct order | Construct `SettingsPanel(svc)` | `tabs.count() == 5`; tab texts: Users, Strategies, Screeners, System, Universe | Implemented |
| UT-GUI-006.001.M01.T02 | MD-GUI-006.001.M01 | Unit | New user dialog calls `AppService.add_user()` | Fill `_UserDialog` and click OK | `svc.add_user()` called once; `users_changed` triggers table refresh | Implemented |
| UT-GUI-006.001.M01.T03 | MD-GUI-006.001.M01 | Unit | Delete user blocked when `AppService.delete_user()` returns error | Select user; click Delete; confirm | Warning `QMessageBox` shown; user remains in table | Implemented |
| UT-GUI-006.001.M01.T04 | MD-GUI-006.001.M01 | Unit | Universe tab meta label shows constituent count | `svc.get_sp500_universe()` returns 503 records | `_meta_label.text()` contains `"503 constituents"` | Implemented |

---

## Module: `gui/log_viewer_panel.py` â€” Log Viewer

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-GUI-007.001.M01.T01 | MD-GUI-007.001.M01 | Unit | Log entries appear when `AppService.log_message` emitted | Emit `svc.log_message("INFO", "hello")` 3 times | `panel._line_count == 3`; `_log_view` is non-empty | Implemented |
| UT-GUI-007.001.M01.T02 | MD-GUI-007.001.M01 | Unit | ERROR entry emits `error_occurred` signal | Emit `svc.log_message("ERROR", "fail")` | `error_occurred` signal emitted once | Implemented |
| UT-GUI-007.001.M01.T03 | MD-GUI-007.001.M01 | Unit | Level filter hides lower-priority entries | Buffer: 2 INFO + 1 WARNING; set level combo to WARNING | `_reapply_filter()` renders 1 visible entry | Implemented |
| UT-GUI-007.001.M01.T04 | MD-GUI-007.001.M01 | Unit | Buffer evicts oldest entries when exceeding `MAX_LINES` | Push `MAX_LINES + 5` messages | `len(panel._buffer) == MAX_LINES` | Implemented |
| UT-GUI-007.001.M01.T05 | MD-GUI-007.001.M01 | Unit | Pause halts display; Resume flushes buffered entries | Pause; emit 3 messages; Resume | After Resume `_line_count` increases by 3 | Implemented |

---

## Module: `gui/app_service.py` â€” AppService (FO-GUI-012 tick integration)

### LiveTickWorker lifecycle (SRD-GUI-012.001)

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-GUI-012.001.M01.T01 | MD-GUI-004.001.M01 | Positive | `_on_connect_ok()` creates `LiveTickWorker` with host/port from `SystemConfig` and `ibkr_tick_client_id=14` | Mock `SystemConfig` with `ibkr_tick_client_id=14`; call `svc._on_connect_ok()` | `svc._tick_worker` is not None; `isinstance(svc._tick_worker, LiveTickWorker) is True`; constructed with clientId=14 | Pass |
| UT-GUI-012.001.M01.T02 | MD-GUI-004.001.M01 | Positive | `disconnect_feed()` calls `request_stop()` on the running worker and sets `_tick_worker = None` | Attach mock `LiveTickWorker` to `svc._tick_worker`; call `svc.disconnect_feed()` | `mock_worker.request_stop.called is True`; `svc._tick_worker is None` | Pass |
| UT-GUI-012.001.M01.T03 | MD-GUI-004.001.M01 | Negative | Second call to `_on_connect_ok()` while worker is running does not start a second worker | Call `_on_connect_ok()` twice; `_tick_worker.isRunning()` returns True | `LiveTickWorker` constructor called exactly once (not twice) | Pass |
| UT-GUI-012.001.M01.T19 | MD-GUI-004.001.M01 | Negative | `disconnect_feed()` when `_tick_worker is None` (never connected) does not raise | `svc._tick_worker = None`; call `svc.disconnect_feed()` | No exception raised; `market_watch_updated` still emitted (ltp cleared) | Pass |

### Market Watch â€” IBKR contract routing (SRD-GUI-012.002)

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-GUI-012.001.M01.T04 | MD-GUI-004.001.M01 | Positive | `_sync_tick_subscriptions()` maps `"^GSPC"` to `Contract(symbol="SPX", secType="IND", exchange="CBOE")` in the set passed to `LiveTickWorker.set_contracts()` | `svc._watch` contains item with `symbol="^GSPC"`; mock `_tick_worker` | `set_contracts` called with dict containing key `"^GSPC"` whose value has `symbol="SPX"`, `secType="IND"`, `exchange="CBOE"` | Pass |
| UT-GUI-012.001.M01.T05 | MD-GUI-004.001.M01 | Negative | Symbol absent from `_YAHOO_TO_IBKR` map is not included in `set_contracts()` call | `svc._watch` contains `symbol="^CUSTOM"` (not in map) | `set_contracts` called without `"^CUSTOM"` key | Pass |

### _on_mktwatch_tick (SRD-GUI-012.003)

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-GUI-012.001.M01.T06 | MD-GUI-004.001.M01 | Positive | `_on_mktwatch_tick` updates ltp, computes change_pct, emits `market_watch_updated` | `_watch` has item `symbol="^GSPC"`; `_watch_prev_close={"^GSPC": 5100.0}`; call `_on_mktwatch_tick("^GSPC", 5200.0)` | item.ltp=5200.0; item.change_pctâ‰ˆ1.96; `market_watch_updated` emitted once | Pass |
| UT-GUI-012.001.M01.T07 | MD-GUI-004.001.M01 | Positive | `change_pct` is None when no prev_close stored; signal still emitted | `_watch_prev_close={}` (empty); call `_on_mktwatch_tick("^GSPC", 5200.0)` | item.ltp=5200.0; item.change_pct is None; `market_watch_updated` emitted | Pass |
| UT-GUI-012.001.M01.T08 | MD-GUI-004.001.M01 | Negative | `_on_mktwatch_tick` with unknown tag â†’ no signal, no exception | Call `_on_mktwatch_tick("UNKNOWN", 100.0)` | `market_watch_updated` NOT emitted; no exception raised | Pass |

### _on_watchlist_tick (SRD-GUI-012.004)

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-GUI-012.001.M01.T09 | MD-GUI-004.001.M01 | Positive | `_on_watchlist_tick` updates ltp/change/change_pct and emits `watchlist_updated` | `_watchlist` has `{"symbol": "AAPL", "prev_close": 175.0, "ltp": 175.0, ...}`; call `_on_watchlist_tick("AAPL", 180.0)` | item["ltp"]=180.0; item["change"]=5.0; item["change_pct"]â‰ˆ2.857; `watchlist_updated` emitted | Pass |
| UT-GUI-012.001.M01.T10 | MD-GUI-004.001.M01 | Negative | Non-S&P 500 symbol is absent from the dict passed to `set_contracts()` | `_watchlist_symbols={"AAPL", "NOTSP"}` where "NOTSP" absent from `_sp500_cache`; call `_sync_tick_subscriptions()` | `set_contracts` called without `"NOTSP"` key | Pass |

### _on_position_tick (SRD-GUI-012.005)

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-GUI-012.001.M01.T11 | MD-GUI-004.001.M01 | Positive | `_on_position_tick` updates `current_price` on matching open position and emits `positions_updated` | `_positions` has `OpenPosition(symbol="AAPL", current_price=180.0, state="OPEN")`; call `_on_position_tick("AAPL", 185.0)` | `pos.current_price == 185.0`; `positions_updated` emitted once | Pass |
| UT-GUI-012.001.M01.T12 | MD-GUI-004.001.M01 | Negative | `_on_position_tick` with no matching position â†’ no signal, no exception | `_positions=[]`; call `_on_position_tick("AAPL", 185.0)` | `positions_updated` NOT emitted; no exception | Pass |

### _sync_tick_subscriptions() (SRD-GUI-012.006)

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-GUI-012.001.M01.T13 | MD-GUI-004.001.M01 | Positive | `_sync_tick_subscriptions()` merges Market Watch, watchlist S&P 500, and position S&P 500 into one `set_contracts()` call | `_watch=["^GSPC"]`; watchlist=`["AAPL"]` (S&P 500); positions=`[OpenPosition("MSFT")]` (S&P 500) | `set_contracts` called once with dict containing `"^GSPC"`, `"AAPL"`, `"MSFT"` | Pass |
| UT-GUI-012.001.M01.T14 | MD-GUI-004.001.M01 | Edge | > 95 total contracts â†’ WARNING logged; position contracts trimmed; Market Watch and watchlist contracts preserved | Build 100-contract scenario (3 market watch + 30 watchlist + 67 positions); call `_sync_tick_subscriptions()` | WARNING log contains "near IBKR limit"; `set_contracts` called with â‰¤ 95 keys; all 3 Market Watch and all 30 watchlist keys present | Pass |
| UT-GUI-012.001.M01.T18 | MD-GUI-004.001.M01 | Negative | `_sync_tick_subscriptions()` is a no-op when `_tick_worker is None` (called before connect) | `svc._tick_worker = None`; call `svc._sync_tick_subscriptions()` | `set_contracts` NOT called; no exception raised | Pass |

### Disconnect behaviour (SRD-GUI-012.007)

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-GUI-012.001.M01.T15 | MD-GUI-004.001.M01 | Positive | `disconnect_feed()` sets all `_watch` item `ltp=None` and emits `market_watch_updated` | `_watch` has 3 items with non-None ltp; call `svc.disconnect_feed()` | All items have `ltp is None`; `market_watch_updated` emitted | Pass |
| UT-GUI-012.001.M01.T16 | MD-GUI-004.001.M01 | Negative | Position `current_price` is NOT cleared on disconnect | `_positions` has `OpenPosition(current_price=185.0)`; call `svc.disconnect_feed()` | `pos.current_price == 185.0` (unchanged) | Pass |
| UT-GUI-012.001.M01.T17 | MD-GUI-004.001.M01 | Negative | Watchlist ltp is NOT cleared on disconnect | `_watchlist` has item with `ltp=180.0`; call `svc.disconnect_feed()` | `item["ltp"] == 180.0` (unchanged) | Pass |

