# Functional Objectives — Execution & Risk Management (EXE)

**Document ID:** FO-EXE
**Version:** 1.5.0
**Status:** Draft
**Last Updated:** 2026-05-16
**Project:** US Swing Trading System

> Traces to: `us_swing/requirements.md` §10, §11, §12, §13, §21.4, §22, §23, §25

---

## FO-EXE-001: Risk-Controlled Order Submission

- The system shall receive trade signals from the Analysis Engine and validate each one against risk rules before submitting any order to IBKR.
- For each validated signal the system shall calculate position size using a configurable fixed-risk model: `position_size = (account_risk_per_trade × account_equity) / (entry_price − stop_loss_price)`.
- The system shall enforce the following pre-trade risk controls:
  - **Max position per symbol** — maximum dollar exposure per single position (configurable).
  - **Max capital allocation** — maximum percentage of total equity deployed across all open positions simultaneously (configurable default: 50%).
  - A signal that would breach either limit is **rejected** and logged; no order is submitted.
- Accepted orders shall be submitted to IBKR as **market orders** by default (configurable to limit orders at signal price ± configurable slippage buffer).
- The system shall persist every submitted order (order ID, symbol, side, quantity, order type, timestamp) to the `trades` table immediately upon submission.
- **Acceptance Criteria:**
  - Given a BUY signal, account equity = $100,000, risk-per-trade = 1%, entry = $50.00, stop = $48.00 → position size = 500 shares.
  - Given a BUY signal that would push total deployed capital above the max allocation limit, the signal is rejected with a logged reason and no order submitted.
  - A submitted market order appears in the `trades` table within 1 second of submission with a non-null IBKR order ID.
  - Given `order_type = limit`, the submitted order uses a limit price = entry_price (not a market order).

---

## FO-EXE-002: Position Tracking & Exit Execution

- The system shall maintain an in-memory and database-persisted snapshot of all open positions **per user** (symbol, user_id, quantity, average entry price, stop-loss level, target price, trailing-stop level, mode, state).
- Exit signals from the Analysis Engine (stop-loss, target reached, trailing-stop triggered) shall be executed immediately as market orders against the full open position size.
- On order fill confirmation from IBKR, the system shall:
  - Update the `positions` table (clear position if fully closed).
  - Update the `trades` table with exit time, exit price, and calculated PnL.
  - Emit a position-closed event to all subscribers (logging, monitoring, reporting).
- The system shall reconcile open positions against the IBKR account state on startup (in case of prior unclean shutdown) and re-adopt any unrecognised open positions.
- **Acceptance Criteria:**
  - An open long position of 500 AAPL shares receives a stop-loss exit signal → a SELL 500 AAPL market order is submitted within 1 second.
  - After fill confirmation, the `positions` table for AAPL shows quantity = 0.
  - PnL for the trade is calculated as `(exit_price − entry_price) × quantity` and stored in `trades`.
  - On startup with an existing IBKR open position not in the local database, the system re-adopts it and logs a reconciliation warning.

---

## FO-EXE-003: Daily Loss Circuit Breaker & Emergency Controls

- The system shall track total realised PnL for the current trading day.
- When the day's cumulative loss reaches or exceeds a configurable **max daily loss** threshold (default: 2% of start-of-day equity), the system shall:
  - Immediately cancel all pending open orders.
  - Close all open positions at market.
  - Suspend further signal processing for the remainder of the day.
  - Log a CRITICAL event and emit an alert notification.
- The system shall provide a manual emergency kill-switch (CLI command or keyboard shortcut in any GUI) that immediately triggers the same close-all-and-halt sequence.
- After a circuit-breaker trigger, the system shall require a manual restart to resume trading on the next trading day.
- **Acceptance Criteria:**
  - Given start-of-day equity = $100,000 and max-daily-loss = 2%, when cumulative realised loss reaches −$2,000, all positions are closed and no further orders are submitted for the rest of the day.
  - A CRITICAL log entry is produced, and the alert notification fires, within 5 seconds of the threshold breach.
  - After circuit-breaker activation, a new entry signal arriving for any symbol is silently discarded (not executed).
  - The manual kill-switch closes all positions within 10 seconds regardless of current system state.

---

## FO-EXE-004: Paper Trading Mode

> Traces to: `requirements.md` §23

- The system shall support **paper trading** (simulated execution) alongside live trading, togglable per user.
- Paper trading shall use identical strategy logic, risk rules, and position management as live trading — only order submission is simulated.
- Simulated order fills: market orders fill immediately at current price; limit orders fill when price crosses the limit level.
- Paper trades and positions shall be stored in the unified `trades` and `positions` tables with `mode = 'paper'` — no separate paper tables.
- Paper P&L shall be calculated identically to live P&L.
- No IBKR API order calls shall be made during paper execution; live market data is used for price reference.
- **Acceptance Criteria:**
  - Given a user in paper mode, a BUY signal generates a simulated fill (no IBKR `place_order()` call); the trade appears in the `trades` table with `mode = 'paper'`.
  - Paper and live trades for the same user are distinguishable by `mode` column.
  - Paper P&L matches what live P&L would have been for identical entry/exit prices.
  - Switching from paper to live mode requires confirmation and does not affect existing paper positions.

---

## FO-EXE-005: Position State Machine & Capital Availability Check

> Traces to: `requirements.md` §21.4, §21.5, §25

- Positions shall transition through states: **NEW → PARTIAL_ENTRY → OPEN → PARTIAL_EXIT → CLOSED**, persisted in the `positions` table `state` column.
- Position states shall be visible in the GUI Position Monitor Panel.
- Partial fills shall transition positions between states: a partial entry fill moves NEW → PARTIAL_ENTRY; full fill moves to OPEN.
- The system shall evaluate **capital availability** before allowing new entries:
  - `available_capital = total_equity - sum(open_position_values)`
  - `RiskManager.can_enter_new(signal, account_state)` returns True only if remaining capital covers the position.
- The GUI shall display: total equity, capital in use, capital available, max allocation limit, and "Can enter next stock? Yes/No" indicator.
- Users shall be able to **override the auto-calculated trade quantity** via the GUI Execution Panel before confirming a trade.
- **Acceptance Criteria:**
  - A new order submission sets position state to NEW; a partial fill changes state to PARTIAL_ENTRY; full fill changes to OPEN.
  - A partial exit fill changes state from OPEN to PARTIAL_EXIT; full exit changes to CLOSED.
  - `can_enter_new()` returns False when capital utilisation exceeds `max_allocation_pct`.
  - User quantity override is respected: if user enters 300 shares (vs auto-calc of 500), exactly 300 shares are submitted.
  - Position states persist across sessions and are correctly restored on startup.

---

## FO-EXE-006: Intraday Candle Readiness for Execution (Phase 1 — Download)

> Traces to: `requirements.md` §10, §21.4

- The system shall, upon receiving the latest screened stock list, download intraday OHLCV candles (1 m source bars, aggregated to 3 m and 15 m) for every symbol in the list and persist them in the database, ensuring a minimum of **390 candles per derived timeframe** are available before the next trading session begins.
- The download shall be **delta-aware**: if candle data already exists for a symbol, only candles for timestamps after the last stored bar shall be fetched; no re-downloading of existing bars.
- Candles for derived timeframes (3 m, 15 m) shall be **aggregated from 1 m source bars** using the `HistoricalDataEngine.aggregate_timeframe()` method defined in INF-003.003; IBKR API calls shall be made only for 1 m bars.
- **Acceptance Criteria:**
  - Given a stock list of N symbols and an empty database, after the download job completes, every symbol has ≥ 390 rows in the `price_1m`-derived 3 m and 15 m aggregated views.
  - Given a symbol with 350 existing 3 m bars, the system fetches only the missing bars and brings the count to ≥ 390 without duplicating existing rows.
  - Given a symbol that fails data fetch (IBKR error, rate-limit, etc.), that symbol is logged as failed and the download continues for remaining symbols.
  - The download job completes idempotently: running it twice on the same data produces no duplicate rows and no errors.

---

## FO-EXE-007: Live 3m Candle Formation During Trading Hours (Phase 2 — Live Feed)

> Traces to: `requirements.md` §10, §21.4
> Depends on: FO-EXE-006 (Phase 1 base candles must be present before live feed starts)

- During Regular Trading Hours (RTH: 09:30–16:00 ET, Monday–Friday), the system shall maintain a **live 3m candle** for every symbol in the active screened list by accumulating IBKR real-time 5-second bars (sourced via `IBKRClient.subscribe_realtime_bars()`) into per-symbol partial bars in memory.
- A **partial bar** tracks `open`, `high`, `low`, `close`, and `volume` for the current 3-minute window. On every incoming 5-second bar the partial bar is updated: `high = max(high, bar.high)`, `low = min(low, bar.low)`, `close = bar.close`, `volume += bar.volume`; `open` is set only on the first tick of a new window.
- On each **3-minute boundary** (wall-clock aligned to :00/:03/:06/…/:57 ET), the system shall:
  1. Finalise the completed partial bar as an `OHLCVBar` with `timeframe = '3m'`.
  2. Persist it to the database via `DatabaseManager.insert_bars()` (idempotent; duplicate timestamps are silently ignored).
  3. Emit a `candle_closed(symbol: str, bar: OHLCVBar)` PyQt signal to all downstream subscribers (Strategy Engine, GUI Chart Panel).
- After each 5-second tick update (before the bar closes), the system shall emit a `candle_updated(symbol: str, partial: PartialBar)` signal so the GUI can display a live in-progress candle without waiting for the 3-minute close.
- The live feed shall subscribe only to symbols in the **current active screened list**. Symbols added or removed from the list shall be subscribed/unsubscribed dynamically without restarting the aggregator.
- The system shall operate **only within RTH**. Outside RTH the aggregator discards incoming 5-second bars without updating any partial bar or emitting signals. If a partial bar is open at 16:00:00 ET it is discarded (not persisted).
- On **connection loss** mid-bar, the in-progress partial bar for each symbol is discarded. When the feed reconnects, a fresh partial bar starts on the next 3-minute boundary.
- The live 3m candles produced by this feature extend the Phase 1 historical base: after a `candle_closed` event, the symbol's 3m candle count increases by 1 and `get_readiness_report()` must reflect the updated count.
- **Acceptance Criteria:**
  - At 09:33:00 ET, given 6 received 5-second bars for AAPL since 09:30:00, a `candle_closed` signal fires with a completed `OHLCVBar(symbol='AAPL', timeframe='3m', open=…, high=…, low=…, close=…, volume=…)` and the bar is persisted to the database.
  - Immediately after a 5-second bar arrives mid-window, a `candle_updated` signal fires with a `PartialBar` reflecting the running OHLC + cumulative volume; no DB write occurs.
  - Given AAPL is removed from the active screened list at 10:05 ET, no further `candle_closed` or `candle_updated` signals are emitted for AAPL, and the IBKR real-time subscription for AAPL is cancelled.
  - At 16:00:00 ET an open partial bar is discarded; no `candle_closed` signal fires and no incomplete bar is written to the database.
  - After a simulated IBKR disconnect at 10:15:30 ET (mid-bar), the in-progress partial bar is cleared; on reconnect at 10:16:45 ET a fresh partial bar starts at the next 3-minute boundary (10:18:00 ET) with no gap row inserted.
  - Running `get_readiness_report(['AAPL'])` after the 09:33:00 `candle_closed` event returns `candles_3m` = (prior count + 1).

---

## FO-EXE-008: Live Market Data Tick Worker

**Status:** Approved
**Priority:** Must
**Depends on:** FO-EXE-007 (IBKR ib_insync connection pattern reused)
**Source:** GUI streaming price requirement — FO-GUI-012

The system shall provide a `LiveTickWorker` QThread module that maintains IBKR `reqMktData` streaming subscriptions for a caller-supplied set of tagged contracts and emits per-symbol last-price signals to the GUI. This worker owns its own `ib_insync.IB()` connection and dedicated IBKR client ID (`SystemConfig.ibkr_tick_client_id`, default 14), keeping it fully isolated from the candle bar worker (clientId 13) and historical loader (clientId 12).

### Requirements

1. `LiveTickWorker` accepts a tagged contract mapping `dict[str, Contract]` (tag → ib_insync Contract). Tags are the caller-visible identifiers (e.g., `"AAPL"`, `"^GSPC"`) used in emitted signals.
2. The worker emits `tick_price = pyqtSignal(str, float)` — `(tag, last_price)` — whenever `ib.pendingTickersEvent` fires and a non-NaN price is available. Price resolution priority: `ticker.last → ticker.close → skip`.
3. The worker emits `subscription_failed = pyqtSignal(str, int)` — `(tag, ibkr_error_code)` — on IBKR error codes 162, 354, or 420 for a specific contract, then removes that tag from active subscriptions. Other subscriptions are unaffected.
4. `set_contracts(contracts: dict[str, Contract])` dynamically reconciles the active subscription set: new tags are subscribed, removed tags have their `reqMktData` cancelled. Subscriptions are batched in groups of 10 with a 200 ms pause between batches to respect IBKR pacing limits.
5. `request_stop()` cancels all active `reqMktData` subscriptions, then disconnects and exits the event loop — following the same safe-stop pattern as `LiveBarWorker.request_stop()`.
6. The worker does **not** apply any RTH filter. `reqMktData` market-data streams whenever the exchange publishes quotes; the caller (AppService) decides whether to display or suppress values outside trading hours.
7. Reconnect on dropped connection is not in scope for this FO; the caller (AppService) tears down and restarts the worker on feed reconnect events.

### Acceptance Criteria

1. Within 500 ms of `set_contracts({"AAPL": stk_contract})` while the IBKR feed is live, at least one `tick_price("AAPL", price)` signal fires.
2. After `set_contracts({})` removes AAPL, no further `tick_price("AAPL", …)` signals fire.
3. IBKR error 354 ("No market data permission") for AAPL → `subscription_failed("AAPL", 354)` emitted within 2 s; `tick_price` for all other active symbols continues uninterrupted.
4. `request_stop()` completes within 3 s: all reqMktData subscriptions cancelled, IBKR connection closed, QThread exits cleanly.
5. Concurrent `set_contracts()` calls while the worker is running do not cause duplicate subscriptions or segfaults.
6. A `SystemConfig.ibkr_tick_client_id` collision (IBKR error 326) is logged at WARNING level and the worker retries with `ibkr_tick_client_id + 1` up to 3 times before emitting a connection-failed signal.

---

## FO-EXE-009: Intraday Monitoring Session Ledger & Lifecycle

**Status:** Approved
**Priority:** Must
**Depends on:** FO-EXE-006 (intraday candle download), FO-EXE-007 (live 3m formation), FO-SCR-008 (screener result persistence)
**Source:** User requirement — keep candle DB in sync with daily screener-filtered universe and open system positions; preserve lifecycle history (filtered → monitored → entered/skipped → exited/evicted) for audit; build a single cross-module integration seam that the upcoming Intraday Strategy Execution module will consume.

The system shall maintain a persistent **monitoring session ledger** — one row per `(session_date, symbol)` — that records every stock the screener emits intraday, its lifecycle outcome (monitored only, entered into a system position, skipped at end of day, evicted from the candle DB, or exited), and its linkage to the underlying trade fills. The ledger is the single source of truth for "what the system is currently watching" and "what the system is currently holding," and is exposed to other modules through a narrow Protocol-typed service surface with an event bus so future consumers (Intraday Strategy Execution, Backtesting, Risk Engine) can integrate without modifying core code.

### Requirements

1. **Ledger table.** The system shall provide a `monitoring_session` table keyed on `(session_date, symbol)` recording: `preset_id`, `run_timestamp`, `added_at`, `lifecycle_state` ∈ {`MONITORING`, `ENTERED`, `SKIPPED`, `EVICTED`, `EXITED`}, `entered_at`, `exited_at`, `evicted_at`, and `trade_id` (anchor system trade). Ledger rows are never deleted — they are the audit history even after candle rows for the symbol are evicted.

2. **Screener handoff.** When a new `ScreenerRunResult` lands for the current trading date, the system shall insert one `monitoring_session` row in state `MONITORING` for each newly-passed symbol. The insert shall be idempotent: re-running the same preset on the same date does not duplicate rows. Symbols that drop out of a later same-day re-run are NOT removed — the row remains as a historical record.

3. **System vs manual discrimination.** The `trades` table shall carry a new `trade_origin` column (`'system'` | `'manual'`) and a `monitoring_session_date` column linking each fill back to its anchor session. The `positions` table shall carry an `origin` column and `anchor_session_date` column. Only `trade_origin = 'system'` fills shall affect the monitoring ledger lifecycle; manual fills are recorded for PnL/audit but invisible to this feature.

4. **Lifecycle transitions on fills.** Fills are routed through a single entry point on the service. The state machine:
   - First system BUY fill against a `MONITORING` row → row flips to `ENTERED`; `positions.anchor_session_date` is set to that row's `session_date`; `entered_at` set to fill time; anchor `trade_id` recorded.
   - Subsequent system BUY fills on the same anchor (scale-in) → no state change; a new `trades` row is inserted tagged with the anchor `monitoring_session_date`.
   - Partial system SELL fills before full close → no state change; new `trades` row tagged to anchor.
   - The system SELL fill that drives `positions.state = CLOSED` (qty = 0) → flip the anchor `monitoring_session` row to `EXITED`; `exited_at` set to fill time.
   - Duplicate-filter case: if the screener re-emits a symbol already covered by an open anchor (e.g., next day), a new `MONITORING` row is inserted for the new `session_date`. That row shall NOT transition to `ENTERED` (the symbol is already held via the prior anchor) and shall be marked `SKIPPED` at end-of-day reconciliation — an accurate "filtered again, already held" record.

5. **Consistency invariant.** At all times: `{symbol : monitoring_session.lifecycle_state == ENTERED}` shall equal `{symbol : positions.state != 'CLOSED' AND positions.origin = 'system'}`. Every state transition must preserve this invariant; integration tests shall assert it.

6. **Cross-module service contract.** The system shall expose three Protocol-typed surfaces from `core/monitoring_session/__init__.py`:
   - `MonitoringQuery` — read-only methods (`keep_set`, `open_system_positions`, `has_open_system_position`, `session_for`, `history`). Cheap, side-effect-free, safe to call from any thread. Consumed by all downstream modules.
   - `MonitoringCommand` — state-mutating methods (`on_screener_results`, `on_fill`, `reconcile_preopen`). Consumed only by the order pipeline and the reconciler (FO-EXE-010).
   - `MonitoringEventBus` — publish/subscribe surface emitting a sealed `MonitoringEvent` union: `SymbolStartedMonitoring`, `SymbolEnteredPosition`, `SymbolPositionScaled`, `SymbolExitedPosition`, `SymbolSkipped`, `SymbolEvicted`, `ReconcileCompleted`.

7. **Versioned DTOs.** All cross-module payloads (`MonitoringSessionRow`, `KeepSet`, `ReconcileReport`, `FillEvent`, every `MonitoringEvent` subclass) shall be immutable frozen `@dataclass(slots=True)` containers with a `schema_version: int` field. Field additions are non-breaking; renames or removals bump the version.

8. **Core stays GUI-free.** No module under `src/us_swing/core/monitoring_session/` shall import from PyQt6. The GUI shall bridge events into Qt signals at its own boundary; headless tooling (Backtesting, MCP) shall consume the same events without requiring a Qt installation.

9. **Concrete-class isolation.** Consumers (EXE, GUI, future ISE, future BKT) shall type-annotate dependencies against the Protocols, never the concrete `_service.py` class, enabling in-memory test doubles and future replay implementations to be substituted without consumer code changes.

### Acceptance Criteria

1. After `service.on_screener_results(result)` with symbols `[A, B, C]` for `today`, the `monitoring_session` table contains exactly three rows with `lifecycle_state = 'MONITORING'`, `preset_id` and `run_timestamp` matching the input, and a `SymbolStartedMonitoring` event has been published for each symbol.
2. Calling `service.on_screener_results(same_result)` a second time produces no new rows and no duplicate events (idempotent).
3. A system BUY fill of 100 shares of A flips `monitoring_session(today, A).lifecycle_state` to `ENTERED`, sets `entered_at`, sets `positions(A).anchor_session_date = today` and `positions(A).origin = 'system'`, inserts a `trades` row with `trade_origin = 'system'` and `monitoring_session_date = today`, and publishes exactly one `SymbolEnteredPosition` event.
4. A second BUY fill of 50 shares of A (scale-in) does NOT change the lifecycle state, inserts a new `trades` row tagged to the same anchor, and publishes a `SymbolPositionScaled` event (not `SymbolEnteredPosition`).
5. A partial SELL of 80 shares of A (positions still open at qty = 70) does NOT change the lifecycle state and publishes `SymbolPositionScaled`. The final SELL closing the position flips `monitoring_session(today, A)` to `EXITED`, sets `exited_at`, and publishes exactly one `SymbolExitedPosition` event.
6. A manual-origin fill (`trade_origin = 'manual'`) for any symbol produces NO `monitoring_session` change and NO lifecycle event, but the trade is still recorded in `trades` for audit.
7. For every state transition, the invariant `{ENTERED symbols} == {open system position symbols}` holds (asserted in integration tests).
8. A new module placed under `src/us_swing/ise/` can implement its full integration by importing only from `us_swing.core.monitoring_session` (Protocols, DTOs, events, factory). No other `core/monitoring_session/*` module is imported and no concrete `_service.py` symbol is referenced.
9. Any `MonitoringEvent` payload exposes `schema_version: int`. A consumer compiled against `schema_version == 1` continues to receive valid events after a backwards-compatible field addition (version unchanged); a breaking change bumps `schema_version` and consumers are updated explicitly.

---

## FO-EXE-010: Pre-Open Candle DB Reconciliation

**Status:** Approved
**Priority:** Must
**Depends on:** FO-EXE-009 (ledger and service surface), FO-EXE-006 (intraday candle download), FO-EXE-007 (live 3m formation)
**Source:** User requirement — stocks monitored yesterday but never entered must not pollute today's candle DB ("failed entry" must not appear synced); stocks with open system positions must keep streaming candles until exit even if today's screener does not re-emit them.

Once per trading day, before the live feed subscribes for that day, the system shall reconcile the intraday candle database (`price_1m`, `price_3m`, `price_15m`) against the union of today's screener-filtered universe and the currently open system positions. Symbols outside that union and not currently held shall have their candle rows hard-deleted; their `monitoring_session` row is preserved and marked `EVICTED` so the history of the symbol's lifecycle remains queryable.

### Requirements

1. **Keep set.** The reconciler shall compute `keep_set(today) = filtered(today) ∪ open_system_positions()` where `filtered(today)` is the set of symbols passed by today's most recent screener run for the active preset (`MonitoringQuery.keep_set`) and `open_system_positions()` is `SELECT symbol FROM positions WHERE state != 'CLOSED' AND origin = 'system'`. The keep set is the authoritative answer to "which symbols should have candles in the database today."

2. **End-of-day finalization (run as the first step of pre-open).** All `monitoring_session` rows with `session_date < today` and `lifecycle_state = 'MONITORING'` (i.e., never anchored a system entry) shall be marked `SKIPPED` with `evicted_at = NULL`.

3. **Eviction.** For every `SKIPPED` symbol that is NOT in `keep_set(today)`, the reconciler shall, within a single database transaction:
   - `DELETE FROM price_1m WHERE symbol = X`
   - `DELETE FROM price_3m WHERE symbol = X`
   - `DELETE FROM price_15m WHERE symbol = X`
   - `UPDATE monitoring_session SET lifecycle_state = 'EVICTED', evicted_at = now WHERE session_date < today AND symbol = X AND lifecycle_state = 'SKIPPED'`
   - Publish `SymbolEvicted(symbol, evicted_session_dates)` after commit.
   - The full transaction is per-symbol: a failure on one symbol does not poison the others; failed symbols are retried once, logged, and reported in the `ReconcileReport`.

4. **Retention guarantees.** Symbols satisfying ANY of the following are retained (candles untouched, `monitoring_session` rows untouched):
   - Symbol is in `filtered(today)` (today's screener)
   - Symbol has an open system position (`positions.state != 'CLOSED' AND origin = 'system'`)
   - Symbol has any `monitoring_session` row in state `ENTERED` (consistency check)
   The duplicate-filter case (symbol in today's filtered set AND in an open anchor) keeps candles via both retention rules — no double-deletion risk.

5. **Idempotency.** `reconcile_preopen(today)` shall be safe to invoke multiple times on the same trading date: subsequent invocations produce zero deletions and zero state changes, and publish a `ReconcileCompleted` event with all eviction counts equal to zero.

6. **Trigger and scheduling.** The reconciler shall run automatically once per trading day before market open. Trigger sources:
   - Scheduled job at `09:15 ET` (configurable via the existing scheduler infrastructure used by `scheduler_dialog.py`).
   - On application startup, if no `ReconcileCompleted` event has fired for `today` and the local clock is between `09:15 ET` and `16:00 ET`, run immediately.
   Both paths invoke the same `MonitoringCommand.reconcile_preopen(today)` method. If the scheduled trigger fires while a prior invocation is still running, the second call is dropped (single-flight).

7. **Report.** Each invocation returns and publishes a `ReconcileReport(filtered_n, carryover_n, skipped_n, evicted_n, evicted_symbols: tuple[str, ...], duration_ms, errors: tuple[ReconcileError, ...])`. The report is logged at INFO level with topic prefix `[Lifecycle]` per `.claude/rules/logging.md`.

8. **History preservation.** After eviction, `MonitoringQuery.history(symbol, days=30)` for an evicted symbol shall return the full lifecycle row(s) — including `lifecycle_state = 'EVICTED'` and `evicted_at` — even though no candle rows remain. The user can inspect "why this stock used to be tracked" from the GUI.

9. **Live feed handoff.** The live bar worker (`LiveBarWorker.set_symbols`) and intraday historical loader (`IntradayCandleLoader`) shall pull their working symbol list from `MonitoringQuery.keep_set(today)` immediately after `reconcile_preopen` completes. They never receive evicted symbols.

### Acceptance Criteria

1. **Happy path eviction.** Given on day T-1 `monitoring_session` rows exist for symbols `[A, B, C]` all in state `MONITORING` and a system position is open on `A` only, when `reconcile_preopen(T)` runs with `filtered(T) = {A, D}`, then:
   - `B` and `C` lose all rows in `price_1m`, `price_3m`, `price_15m`.
   - `A` and `D` retain all candle rows.
   - `monitoring_session(T-1, B)` and `(T-1, C)` are marked `EVICTED` with `evicted_at` set.
   - `monitoring_session(T-1, A)` remains `ENTERED` (untouched).
   - One `SymbolEvicted` event fires for `B`, one for `C`; none for `A` or `D`.
   - A new `MONITORING` row is created by the upstream `on_screener_results` for `(T, D)`; the reconciler does not duplicate it.

2. **Carryover position retention.** Given `A` has been in state `ENTERED` since T-1 (open system position) and `filtered(T)` does not include `A`, after `reconcile_preopen(T)` runs, `A`'s candle rows in all three timeframes remain intact and `monitoring_session(T-1, A).lifecycle_state` is still `ENTERED`.

3. **Duplicate-filter retention.** Given `A` has been `ENTERED` since T-1 and `filtered(T)` ALSO includes `A` (so a new `(T, A)` `MONITORING` row exists), after `reconcile_preopen(T)` runs, `A`'s candles remain; the anchor row `(T-1, A)` remains `ENTERED`; the `(T, A)` row stays `MONITORING` (will be `SKIPPED` next day if never anchored). No deletion fires for `A`.

4. **Idempotency.** Calling `reconcile_preopen(T)` twice in succession produces, on the second call, `ReconcileReport.evicted_n == 0` and zero `SymbolEvicted` events.

5. **Per-symbol transaction atomicity.** If `DELETE FROM price_3m WHERE symbol = B` fails due to a transient lock, the same transaction's `price_1m` delete and the corresponding `monitoring_session` update are rolled back; `B` is reported in `ReconcileReport.errors`; `C`'s eviction proceeds unaffected.

6. **Startup catch-up.** If the application starts at `10:30 ET` on a trading day with no prior `ReconcileCompleted` event for that date, `reconcile_preopen(today)` is invoked exactly once during app initialization, before `LiveBarWorker.start()` is called.

7. **History after eviction.** After `B` is evicted in (1), `MonitoringQuery.history('B', days=7)` returns at least one row with `session_date = T-1` and `lifecycle_state = 'EVICTED'`. No `price_*` row for `B` exists.

8. **Logging.** Every reconcile invocation emits exactly one INFO log line with prefix `[Lifecycle]` summarising `filtered_n`, `carryover_n`, `skipped_n`, `evicted_n`, and `duration_ms`. Eviction errors emit one WARNING log line per failed symbol, also `[Lifecycle]`-prefixed.

9. **Live feed alignment.** Immediately after `reconcile_preopen(T)` completes, the symbol set passed to `LiveBarWorker.set_symbols(...)` equals `MonitoringQuery.keep_set(T).filtered ∪ MonitoringQuery.keep_set(T).carryover`; no evicted symbol appears in that set.
