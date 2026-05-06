# US Swing Trading System Design Document

## Project Name
US_Swing_Requirement

---

# 1. Objective

Design and implement a scalable swing trading system that:

- Uses S&P 500 stock universe (approx. 500 stocks)
- Stores 1 year of historical multi-timeframe data
- Updates data daily before market open
- Runs a screener to filter maximum 20 stocks
- Trades selected stocks using intraday multi-timeframe logic
- Ensures historical and live candle consistency

---

# 2. System Requirements

## Functional Requirements

1. Start system 1 hour before market open (auto-launch via Windows Task Scheduler).
2. Load S&P 500 universe.
3. Download and store 1 year historical data:
   - 1m
   - 3m
   - 5m
   - 15m
   - 1h
   - 4h
   - 1d
   - 1w
4. Store data in database.
5. Daily incremental update of missing data.
6. Run user-selected screeners across 500 stocks.
7. Select maximum 20 stocks.
8. Subscribe to real-time bars for selected stocks.
9. Build intraday candles locally for entry/exit logic.
10. Execute trades and manage positions (paper or live mode per user).
11. Provide PyQt6 GUI with full operator control over all operations.
12. Support multiple users with isolated settings and positions.
13. Track position states across days (partial entry/exit awareness).
14. Allow user-defined trade quantity override via GUI.
15. Evaluate available capital before allowing new entries.
16. Expose MCP server endpoints for AI agent integration.

## Non-Functional Requirements

- Historical and live candles must match.
- Respect broker pacing limits.
- System must be modular and scalable.
- Fail-safe reconnection handling.
- Thread-safe event-driven architecture.

---

# 3. High-Level Architecture

Modules:

1. Universe Manager
2. Historical Data Engine
3. Database Layer
4. Screener Engine
5. Live Trading Engine
6. Execution & Risk Manager
7. Logging & Monitoring Module
8. GUI Module (PyQt6 — operator interface)
9. MCP Server Module (AI agent interface)
10. Multi-User Manager
11. Paper Trading Engine
12. Notification & Alert Service

---

# 4. System Startup Flow (T - 60 Minutes)

> **Auto-launch:** Windows Task Scheduler triggers this sequence T-60 before market open (see §24 for full scheduler spec).

1. GUI main window opens (auto via Task Scheduler or manual).
2. Active user profile loaded (user selection prompt if multiple users).
3. Start IBKR Gateway/API session for active user(s).
4. Validate connection; show status in GUI status bar.
5. Load S&P 500 universe from database.
6. Perform incremental data update (fetch missing bars since last session).
7. Run user-selected screener filters (GUI Screener Panel shows progress).
8. Select top 20 stocks, persist watchlist.
9. Subscribe to real-time bars for watchlist stocks.
10. Live engine starts; GUI Dashboard activates with position and signal monitoring.

---

# 5. Universe Manager

## Responsibilities

- Maintain S&P 500 stock list (scraped from Wikipedia: List of S&P 500 companies).
- Store universe as a flat CSV at `~/.usswing/sp500_universe.csv` (same directory as user data).
- Refresh automatically if the cache is older than **7 days** or missing; otherwise load from disk.
- Record `last_fetched` timestamp in `~/.usswing/sp500_meta.json` (ISO-8601 UTC) so staleness can be determined on next startup.
- Replace `.` with ` ` in ticker symbols for IBKR compatibility (e.g. `BRK.B` → `BRK B`).
- On startup (500 ms deferred), `AppService` checks the cache and logs the result to the Live Log panel.

## Output

- `~/.usswing/sp500_universe.csv` — columns: Symbol, IbkrSymbol, Name, Sector (≈500 rows).
- `~/.usswing/sp500_meta.json` — `{"last_fetched": "<ISO timestamp>", "source": "<URL>", "count": 503}`.

## IBKR Contract Qualification

**Script:** `python -m us_swing.scripts.qualify_sp500_ibkr [--host 127.0.0.1] [--port 7497] [--client-id 99]`

- Reads `sp500_universe.csv` (IbkrSymbol column).
- Connects to IBKR TWS / Gateway on port **7497** (paper) or 7496 (live).
- Qualifies all ~500 `Stock` contracts via `SMART` exchange in batches of 50 (1 s pacing between batches to respect TWS rate limits).
- Exports `~/.usswing/sp500_ibkr.csv` — columns: **Symbol, IbkrSymbol, conid, PrimaryExch**.
- If the IBKR CSV does not exist, `AppService` emits a WARNING in the Live Log on startup.

## Universe Tab — Candle Coverage Display

The Universe tab (Settings → Universe) shall show candle database coverage inline with the S&P 500 list.

Two additional columns are displayed for every symbol:

| Column | Description |
|---|---|
| **DB** | ✔ (green) = current data; ⚠ (amber) = stale data; ✘ (red) = no data in candles.db |
| **Last Updated** | Most recent `price_1d` date for that symbol, or `—` if absent |

**Discrepancy highlighting:** Rows whose last candle date is behind the last completed NYSE trading day are tinted amber; rows with no data at all are tinted red. Current rows use the standard alternating row background.

The coverage data is read with a single `SELECT symbol, MAX(datetime) FROM price_1d GROUP BY symbol` query on startup and refreshes automatically whenever the candle database status changes (`candle_db_status_changed` signal).

## Status

**Implemented** — `src/us_swing/gui/sp500_store.py` (flat-file store) and `src/us_swing/scripts/qualify_sp500_ibkr.py` (IBKR qualification script).  The older `src/us_swing/universe/manager.py` (database-backed) is retained for backward compatibility.

Universe tab candle coverage columns: **Implemented** — `AppService.get_candle_symbol_coverage()` + `get_last_trading_day()` feed the updated `_build_universe_html()` in `settings_panel.py`.

---

# 6. Historical Data Engine

## Initial Setup

For each stock:

- Download 1 year of 1m data.
- Download 1d and 1w data.
- Store in database.

Higher timeframes (3m, 5m, 15m, 1h, 4h) are aggregated locally from 1m data.

## Daily Incremental Update

1. Query last stored timestamp per symbol.
2. Request data from last timestamp to current.
3. Append only missing candles.

---

# 7. Database Design

## Tables

### universe
- symbol
- name
- sector

### price_1m
- symbol
- datetime
- open
- high
- low
- close
- volume

### price_1d
- symbol
- datetime
- open
- high
- low
- close
- volume

### price_1w
- symbol
- datetime
- open
- high
- low
- close
- volume

### watchlist
- symbol
- date_selected

### trades
- trade_id
- user_id
- symbol
- entry_time
- entry_price
- exit_time
- exit_price
- pnl
- mode (paper / live)

### positions
- symbol
- user_id
- quantity
- average_price
- mode (paper / live)
- state (NEW / PARTIAL_ENTRY / OPEN / PARTIAL_EXIT / CLOSED)

### users
- user_id
- username
- display_name
- ibkr_client_id
- settings_json
- mode (paper / live)

Indexes:
- (symbol, datetime) on all `price_*` tables
- (user_id, symbol) on `positions` and `trades`

> **Schema note:** `trades` covers both paper and live trades via the `mode` column (`'paper'` or `'live'`).
> `positions` similarly uses `mode` to distinguish paper vs live open positions.
> No separate `paper_trades` or `paper_positions` tables — the `mode` column is sufficient.

---

# 8. Screener Engine

## Input
- 500 stocks
- Historical data from DB

## Screening Timeframes
- 1d
- 1h
- 15m (optional)

## Example Filters
- Volatility expansion
- RSI threshold
- Range compression
- Breakout proximity
- Volume spike

## Output
Maximum 20 selected stocks.

---

# 9. Live Trading Engine

## Data Source
- Real-time 5-second bars

## Process

1. Subscribe to 5-second bars for selected stocks.
2. Maintain rolling buffer.
3. Build candles:
   - 1m
   - 3m
   - 5m
   - 15m
   - 1h
4. Persist completed candles to database.

## Decision Loop

Every 5 seconds:

- Update buffers
- Check if new 1m candle closed
- Update higher timeframe candles
- Evaluate entry/exit rules

---

# 10. Execution & Risk Management

## Entry
- Market or limit order

## Exit
- Stop loss
- Target
- Trailing stop

## Risk Controls
- Max position per stock
- Max capital allocation
- Max daily loss
- Circuit breaker on system error

---

# 11. Threading / Event Model

Main Thread:
- Broker event loop
- Order management

Worker Threads:
- Historical update
- Screener
- Database write operations

Async Callbacks:
- Market data events

---

# 12. Daily Operational Workflow

**T - 60 Minutes (auto via Task Scheduler):**
- GUI opens; active user profile loaded
- Broker connection established; status shown in GUI
- Incremental historical data update
- User-selected screeners run (visible in Screener Panel)
- Top 20 watchlist generated; user can review/modify in GUI

**Market Open:**
- Subscribe to 5s real-time bars for watchlist stocks
- GUI Dashboard activates; live price feed visible
- Carry-over positions from prior days loaded and reconciled with IBKR

**During Market:**
- Candles built from 5s bars (1m/3m/5m/15m/1h)
- Strategy engine evaluates signals
- GUI shows entry conditions live; user can override quantity or skip
- Trades executed (paper or live per user); position state updated in GUI
- Capital availability check before each new entry

**After Market:**
- Final candles and trades persisted to database
- Daily P&L summary shown in GUI Dashboard
- Performance report available (CSV export for offline analysis)
- Position states for open/partial positions persisted for next day

---

# 13. Error Handling

- Automatic reconnection on API disconnect.
- Retry logic on pacing errors.
- Log all exceptions.
- Alert system on critical failure.

---

# 14. Performance Considerations

- Batch historical requests.
- Limit concurrent subscriptions to 20 stocks.
- Use indexed database tables.
- Use in-memory caching for active symbols.

---

# 15. Future Enhancements

- Portfolio-level position sizing (Kelly criterion / Equal-weight).
- Pyramiding with configurable scale-in rules.
- Machine learning screener layer (feature engineering from OHLCV).
- Multi-broker support (Alpaca, Tradier).
- Mobile push notifications for trade events and alerts.
- Market calendar awareness (US holidays, half-days, early closes).
- User authentication (login/password for multi-user access control).
- Data backup/export for external analysis tools.

---

# 16. Conclusion

This architecture ensures:

- Historical and live candle consistency
- Scalable swing trading design
- Controlled API usage
- Modular and maintainable system structure

---

# 17. Sequence Diagram

## 17.1 System Startup Sequence (T - 60 Minutes)

Sequence Flow:

1. System Boot
2. Connect to IBKR Gateway
3. Validate API Connection
4. Load Universe from DB
5. Historical Data Engine checks last timestamps
6. Fetch Missing Historical Data
7. Update Database
8. Screener Engine runs filters
9. Select Top 20 Stocks
10. Initialize Live Trading Engine

Textual Sequence Representation:

System -> IBKR_API : connect()
IBKR_API -> System : connection_confirmed
System -> Database : load_universe()
System -> HistoricalEngine : update_missing_data()
HistoricalEngine -> IBKR_API : reqHistoricalData()
IBKR_API -> HistoricalEngine : historical_bars
HistoricalEngine -> Database : store_bars()
System -> ScreenerEngine : run_scan()
ScreenerEngine -> Database : read_price_data()
ScreenerEngine -> System : selected_symbols (max 20)
System -> LiveEngine : initialize(selected_symbols)

---

## 17.2 Live Trading Sequence

Every 5 seconds:

IBKR_API -> LiveEngine : 5s_bar_update
LiveEngine -> CandleBuilder : add_5s_bar()
CandleBuilder -> CandleBuilder : build_1m_if_complete()
CandleBuilder -> StrategyEngine : on_new_candle()
StrategyEngine -> RiskManager : validate_entry()
RiskManager -> ExecutionEngine : place_order()
ExecutionEngine -> IBKR_API : submit_order()
IBKR_API -> ExecutionEngine : order_status_update
ExecutionEngine -> Database : store_trade()

---

# 18. Class Diagram

## 18.1 Core Classes

### 1. IBKRClient
Responsibilities:
- Manage connection
- Handle historical requests
- Subscribe to real-time bars
- Submit orders
- Handle callbacks

Key Methods:
- connect()
- req_historical_data()
- subscribe_realtime_bars()
- place_order()
- handle_market_data()

---

### 2. UniverseManager
Responsibilities:
- Maintain S&P 500 list
- Update constituents

Methods:
- load_universe()
- refresh_universe()

---

### 3. HistoricalDataEngine
Responsibilities:
- Fetch initial 1 year data
- Incremental updates
- Aggregate higher timeframes

Methods:
- bootstrap_data(symbol)
- update_missing_data(symbol)
- aggregate_timeframes(symbol)

---

### 4. DatabaseManager
Responsibilities:
- CRUD operations
- Efficient indexed queries

Methods:
- insert_bars()
- fetch_bars()
- get_last_timestamp()
- store_trade()

---

### 5. ScreenerEngine
Responsibilities:
- Run screening logic
- Rank stocks

Methods:
- run_scan()
- apply_filters()
- select_top_n(n=20)

---

### 6. CandleBuilder
Responsibilities:
- Maintain rolling 5s buffer
- Build higher timeframe candles

Methods:
- add_5s_bar()
- build_1m()
- build_3m()
- build_15m()
- build_1h()

---

### 7. StrategyEngine
Responsibilities:
- Evaluate entry/exit conditions
- Multi-timeframe logic

Methods:
- evaluate_entry(symbol)
- evaluate_exit(symbol)

---

### 8. RiskManager
Responsibilities:
- Position sizing
- Capital allocation
- Daily loss control

Methods:
- validate_entry()
- calculate_position_size()
- check_daily_loss()

---

### 9. ExecutionEngine
Responsibilities:
- Order submission
- Order status tracking

Methods:
- place_order()
- handle_order_status()

---

# 19. Technical Architecture

## 19.1 Technology Stack

Language: Python 3.11+
Broker API: IBKR TWS / Gateway API
Database: PostgreSQL (Production) / SQLite (Development)
ORM (optional): SQLAlchemy
Concurrency: asyncio + event-driven callbacks
Deployment: Windows or Linux VPS
Scheduler: Windows Task Scheduler / cron

---

## 19.2 Folder Structure

us_swing_trading/
│
├── __main__.py           ← CLI entry point
├── config/
│   └── settings.py
├── broker/
│   ├── ibkr_client.py
│   └── pacing.py
├── data/
│   ├── historical_engine.py
│   ├── candle_builder.py
│   ├── database.py
│   └── providers/
│       ├── ibkr_provider.py
│       └── dummy_provider.py   ← dev/test stub
├── screener/
│   ├── config.py
│   ├── filters.py
│   ├── engine.py
│   └── watchlist.py
├── analysis/
│   ├── indicators.py
│   ├── strategy_engine.py
│   ├── live_engine.py
│   └── strategies/
│       ├── breakout.py
│       └── pullback.py
├── execution/
│   ├── risk_manager.py
│   ├── position_tracker.py
│   ├── execution_engine.py
│   ├── paper_engine.py        ← simulated fills
│   ├── circuit_breaker.py
│   └── emergency.py
├── user/
│   └── manager.py             ← multi-user CRUD
├── gui/
│   ├── main_window.py
│   ├── dashboard_panel.py
│   ├── screener_panel.py
│   ├── execution_panel.py
│   ├── position_panel.py
│   ├── settings_panel.py
│   ├── log_viewer.py
│   └── theme.py
├── mcp/
│   ├── server.py
│   └── tools/
│       ├── fetch_ohlcv.py
│       ├── run_screener.py
│       ├── get_positions.py
│       ├── submit_order.py
│       └── system_health.py
├── models/
│   └── data_models.py
├── logs/
└── tests/

---

## 19.3 Runtime Flow

__main__.py
    -> Load Config
    -> Load User Profile(s)
    -> Launch GUI (PyQt6 main window)
        GUI auto-triggers:
        -> Connect IBKRClient (per user, unique clientId)
        -> Run Historical Update (incremental)
        -> Run User-Selected Screeners
        -> Generate Watchlist
        -> Start Live Engine
        -> Enter Event Loop

Event Loop handles:
- Market Data (5s bars → candle builder)
- Order Updates (fill events → position state transitions)
- GUI signals (user qty override, manual close, screener run)
- Timers (daily P&L reset, universe refresh)

MCP Server (parallel, optional):
    -> Exposes same operations as GUI via MCP protocol
    -> Runs in background thread; shares core engine instances

---

## 19.4 Scalability Considerations

- Limit live subscriptions to 20 stocks
- Use connection heartbeat monitor
- Use retry with exponential backoff
- Maintain in-memory cache for active symbols
- Separate screening and live trading logic

---

# 20. Deployment Architecture

Single Machine Deployment:

Machine:
- IBKR Gateway
- Trading Application
- PostgreSQL

Future Upgrade Option:

Machine 1:
- Data + Screening

Machine 2:
- Live Trading + Execution

Communication via REST or message queue (Redis / RabbitMQ).

---

# 21. GUI Module

The system shall provide a **PyQt6 desktop GUI** as the primary operator interface. All core operations must be accessible through the GUI — no CLI-only workflows for daily operation.

## 21.1 Main Window & Layout

**Status: Implemented**

- Tabbed or panel-based main window with sections for: Dashboard, Screener, Positions, Trade Execution, Settings, Logs.
- System status bar showing: broker connection state, active user, paper/live mode, daily P&L, open position count.
- Auto-launch capability (see §24).
- **Feed status pill** in the Dashboard scope strip — dot + label (`Feed: Disconnected / Connecting… / Connected / Error`) updates in real time via `DemoService.feed_status_changed` signal.

## 21.2 Dashboard Panel

**Status: Implemented**

- Real-time overview: open positions, today's P&L, capital utilisation %, watchlist stocks, system health.
- Position table: symbol, qty, avg entry, current price, unrealised P&L, stop-loss, target, position state (NEW / PARTIAL_ENTRY / OPEN / PARTIAL_EXIT / CLOSED).
- Trade history log: today's executed trades with entry/exit prices, P&L, strategy ID.

## 21.3 Screener Panel

**Status: Implemented**

- List of available screener filters with enable/disable toggle per filter.
- Parameter controls: user can adjust thresholds (RSI range, ATR period, volume multiplier, etc.) from GUI.
- "Run Screener" button — triggers manual screen outside scheduled time.
- Results table: symbol, composite score, per-filter pass/fail, "Add to Watchlist" action.
- User selects which screeners to run (not all must run every day).

## 21.4 Trade Execution Panel

**Status: Implemented**

- For each watchlist stock: entry conditions status, recommended quantity (auto-calculated), user-override quantity input.
- User can manually adjust quantity before confirming trade.
- Paper/Live mode toggle — visible and switchable per user.
- Entry confirmation dialog before execution (optional, configurable).
- Exit controls: manual close button per position, modify stop-loss/target from GUI.

## 21.5 Position Monitor Panel

- Persistent across days: shows carry-over positions from prior sessions.
- Position states tracked: NEW, PARTIAL_ENTRY, OPEN, PARTIAL_EXIT, CLOSED.
- Capital available for new entries: show remaining capital vs. max allocation.
- Explicit indicator: "Can enter next stock? Yes/No" with remaining capital amount.

## 21.6 Settings Panel

**Status: Implemented**

- User management: create/edit/delete users (see §22). The Users table shows 11 columns: ID · Username · Display Name · IBKR ID · Mode · Risk % · Max Capital % · Max Position · Max Daily Loss · Default Order · Order Confirm. Each user dialog includes both profile fields and a **Risk Settings** section (risk %, max position, max allocation %, daily loss limit, default order type, order confirmation toggle) — risk is user-specific and edited inline.
- Strategy configuration: enable/disable strategies, adjust strategy parameters.
- Screener configuration: filter enable/disable, parameter tuning.
- System config: log level, IBKR connection params (host/port), scheduler settings.
- **4 sub-tabs:** Users · Strategies · Screeners · System. Risk settings are per-user and accessed via the Edit User dialog — no separate Risk tab.

### 21.6.1 Data Feed Connection UI

**Status: Implemented — moved to title bar**

The Connect / Disconnect feed toggle lives in the `_TitleBar` (not Settings). The title bar button cycles through three states: `Connect Feed` → `⟳ Connecting…` → `🟢 Connected`. Disconnecting via the connected button shows a confirmation dialog.

The Settings → System sub-tab provides only configuration fields (host, port, log level, scheduler) — no connect/disconnect controls.

## 21.7 Log Viewer Panel

**Status: Implemented (embedded in Dashboard)**

- Real-time streaming log viewer (INFO/WARNING/ERROR).
- Filterable by level, module, symbol.
- Error highlighting and alert indicators in system status bar.

---

# 22. Multi-User Support

## 22.1 User Profiles

- System supports multiple user profiles.
- Each user has: username, display name, IBKR client ID, risk settings, strategy preferences, screener config.
- User selection at startup or switchable from GUI.
- Active users for a trading session are selectable — system can run for selected users simultaneously.

## 22.2 User Isolation

- Each user's positions tracked independently (keyed by user ID + symbol in DB).
- Each user's capital, risk limits, and daily P&L tracked separately.
- Watchlists may be shared or per-user (configurable).
- Trade records tagged with user ID.

## 22.3 User Settings Storage

**Status: Implemented (development — JSON; production — DB)**

- **Development:** User profiles persisted to `~/.usswing/users.json` via atomic write (`write → .tmp → Path.replace()`). On first launch, seed demo users are written to file.
- **Production (planned):** Migrate to `users` table in PostgreSQL/SQLite: `user_id`, `username`, `display_name`, `ibkr_client_id`, `settings_json`.
- Settings JSON contains: `risk_per_trade_pct`, `max_position_value`, `max_allocation_pct`, `max_daily_loss_pct`, `default_order_type`, `strategy_config`, `screener_config`.
- Security: API keys and broker credentials must use OS keychain (`keyring`) — never stored in JSON files.

## 22.4 System Config Storage

**Status: Implemented**

- System configuration (IBKR host, port, log level, scheduler times) persisted to `~/.usswing/system.json` via atomic write.
- `SystemConfig` dataclass serialised via `dataclasses.asdict()` to JSON.
- Loaded at `DemoService.__init__`; reloaded on every Save in Settings → System tab.

---

# 23. Paper Trading Mode

## 23.1 Overview

- System supports **paper trading** (simulated execution) alongside live trading.
- Toggle per user: each user can be in paper mode or live mode independently.
- Paper trading uses identical logic to live (same strategy, same risk rules) — only order submission is simulated.

## 23.2 Paper Trading Engine

- Simulated order fill: market orders fill at current price; limit orders fill when price crosses limit level.
- Simulated positions and trades stored in the unified `positions` and `trades` tables with `mode = 'paper'` — no separate paper tables needed.
- P&L calculated identically to live trades.
- No IBKR API calls during paper execution; uses live market data for price reference.

## 23.3 Paper/Live Switch

**Status: Partially Implemented — Paper only during development**

- Switchable from GUI Settings panel per user.
- Requires confirmation dialog: "Switch to LIVE mode? This will submit real orders."
- Visual indicator in GUI: prominent banner/badge showing PAPER or LIVE mode.
- **Development constraint:** Live mode is disabled in the GUI (`_UserDialog` mode dropdown shows Paper only). Live mode will be re-enabled once development and paper-mode testing are complete.

---

# 24. Windows Task Scheduler Integration

## 24.1 Auto-Launch

- System shall be launchable via Windows Task Scheduler.
- Default schedule: T-60 minutes before US market open (8:30 AM ET → launch at 7:30 AM ET; adjusted for DST).
- Task starts the application which auto-opens the GUI.

## 24.2 Auto-Workflow on Launch

On scheduled launch, system performs automatically:
1. Open GUI main window.
2. Connect to IBKR Gateway.
3. Load universe.
4. Perform incremental data update (download missing bars since last session).
5. Run user-selected screeners.
6. Generate watchlist.
7. Subscribe to real-time data for watchlist stocks.
8. Begin monitoring for entry/exit signals.

User can observe and intervene at any step via GUI.

## 24.3 Scheduler Configuration

- Install/update Windows Task Scheduler entry from GUI Settings panel.
- Configurable launch time (default: 60 min before market open).
- Enable/disable scheduled launch from GUI.

---

# 25. Position State Tracking Across Days

## 25.1 Position States

Positions transition through states, persisted in DB and visible in GUI:

```
NEW → PARTIAL_ENTRY → OPEN → PARTIAL_EXIT → CLOSED
```

| State | Meaning |
|---|---|
| NEW | Signal generated, order submitted, not yet filled |
| PARTIAL_ENTRY | Order partially filled (some shares acquired) |
| OPEN | Entry fully filled, position active |
| PARTIAL_EXIT | Exit order partially filled (some shares sold) |
| CLOSED | Position fully exited; final P&L recorded |

## 25.2 Overnight Carry-Over

- Positions persist in DB across sessions (days).
- On next-day startup, `PositionTracker.reconcile()` re-loads positions from DB and reconciles with IBKR account.
- GUI shows carry-over positions with their current state.
- Strategy engine knows about existing positions: no duplicate entry, handles partial states.

## 25.3 Capital Availability Check

- Before entering a new stock, system evaluates: `available_capital = total_equity - sum(open_position_values)`.
- `RiskManager.can_enter_new(signal, account_state)` returns True only if remaining capital covers the position.
- GUI shows: total equity, capital in use, capital available, max allocation limit.

---

# 26. S&P 500 Data Source

## 26.1 Universe List Source

- **Production:** Wikipedia S&P 500 page via `pandas.read_html()` (configurable URL).
- **Development/Testing:** Local CSV file or hardcoded dummy list.
- Source is configurable in settings; system does not hard-depend on any single source.

## 26.2 OHLCV Data Source

- **Production:** IBKR Historical Data API via `ib_insync`.
- **Development/Testing:** Dummy data provider returning synthetic/cached OHLCV bars (same interface as IBKR provider).
- Provider selection via config: `DATA_PROVIDER = "ibkr"` or `DATA_PROVIDER = "dummy"`.
- Note: Real S&P 500 OHLCV data source for non-IBKR environments (e.g., free API) is TBD. Coding proceeds with dummy provider until a specific source is chosen.

---

# 27. MCP Server Interface

## 27.1 Overview

- Each major tool exposes MCP (Model Context Protocol) endpoints for AI agent integration.
- MCP server runs alongside GUI; both can operate simultaneously.
- MCP tools mirror core functionality — no separate business logic.

## 27.2 MCP Tools (Planned)

| Tool Name | Module | Action |
|---|---|---|
| `fetch_ohlcv` | INF | Fetch / update historical data for symbol(s) |
| `get_universe` | INF | Return current S&P 500 universe list |
| `run_screener` | SCR | Run screening with specified config, return results |
| `get_watchlist` | SCR | Return current day's watchlist |
| `get_signals` | ANA | Return pending entry/exit signals |
| `get_positions` | EXE | Return open positions with state |
| `submit_order` | EXE | Submit entry/exit order for symbol |
| `get_daily_pnl` | EXE | Return today's realised P&L |
| `system_health` | INF | Return system health status |

---

# 28. Notifications & Alerts

## 28.1 Alert Channels

- **GUI:** Toast notifications and status bar alerts for trade events, errors, circuit breaker.
- **Log file:** All events logged per existing logging spec.
- **Webhook (optional):** POST to configured URL on WARNING+ events.

## 28.2 Alert Events

- Trade executed (entry/exit with details).
- Position state change.
- Screener completed (with result count).
- Circuit breaker triggered.
- Broker disconnection / reconnection.
- Data update failed for symbol(s).

---

# 29. Performance Reporting

## 29.1 Scope

- Daily P&L summary available in GUI Dashboard.
- Trade history with full details (entry/exit prices, P&L, duration, strategy).
- Per-user reporting — each user sees their own trades and P&L.

## 29.2 Reports (Future)

- Weekly/monthly P&L aggregation.
- Win rate, average win/loss, R-multiple distribution.
- Export to CSV for external analysis.

---

# 30. Final Notes

This architecture ensures:

- Clean separation of concerns
- Historical/live consistency
- Controlled API usage
- Scalable swing trading system
- Production-ready modular design

End of Document.

---

# 31. Implementation Status

Last updated: 2026-03-15

## GUI Module (§21)

| Section | Feature | Status |
|---|---|---|
| §21.1 | Main window — 5-tab horizontal nav (Dashboard · Screener · Execution · Chart · Settings) | ✅ Implemented |
| §21.1 | Feed status pill in Dashboard scope strip | ✅ Implemented |
| §21.2 | Dashboard — KPI cards, positions table, trade history, live log | ✅ Implemented |
| §21.3 | Screener Panel — filters, run button, results table | ✅ Implemented |
| §21.4 | Execution Panel — signals, quantity override, entry confirmation | ✅ Implemented |
| §21.5 | Position Monitor Panel | ⬜ Planned (merged into Dashboard) |
| §21.6 | Settings Panel — 5 sub-tabs (Users · Risk · Strategies · Screeners · System) | ✅ Implemented |
| §21.6.1 | Settings → System — Connect/Disconnect feed button + status pill | ✅ Implemented |
| §21.6.1 | Settings → System — config persistence to `~/.usswing/system.json` | ✅ Implemented |
| §21.7 | Log Viewer — embedded in Dashboard (level filter, search, pause, clear) | ✅ Implemented |
| §32 | Chart Viewer Panel — TradingView Lightweight Charts (1D/1W, symbol select) | ✅ Implemented |

## Multi-User Support (§22)

| Section | Feature | Status |
|---|---|---|
| §22.1 | User profiles — create/edit/delete from GUI | ✅ Implemented |
| §22.2 | Per-user position isolation (keyed by user_id) | ✅ Implemented |
| §22.3 | User persistence — JSON file (`~/.usswing/users.json`), atomic write | ✅ Implemented |
| §22.4 | System config persistence — JSON file (`~/.usswing/system.json`) | ✅ Implemented |

## Paper Trading (§23)

| Section | Feature | Status |
|---|---|---|
| §23.1 | Paper trading mode toggle per user | ✅ Implemented |
| §23.2 | Simulated fills, P&L calculation | ✅ Implemented (demo) |
| §23.3 | Live mode disabled during development (paper only) | ✅ Implemented |

## Backend / Infrastructure (§5–§14)

| Section | Feature | Status |
|---|---|---|
| §5 | Universe Manager | ⬜ Planned |
| §6 | Historical Data Engine | ⬜ Planned |
| §7 | Database Layer (PostgreSQL/SQLite) | ⬜ Planned |
| §8 | Screener Engine (real filters) | ⬜ Planned |
| §9 | Live Trading Engine | ⬜ Planned |
| §10 | Execution & Risk Management | ⬜ Planned |
| §27 | MCP Server Interface | 🔄 Partial (pilot1 MCP tools) |

---

# 32. Chart Viewer Panel

## 32.1 Overview

The system shall provide a **Candle Chart Viewer** panel as the 4th tab in the main navigation ("📈 Chart"), positioned between Execution and Settings.

Purpose: allow the operator to visually inspect any stock's OHLCV candle data stored in `~/.usswing/candles.db` to verify data completeness and quality after a download.

## 32.2 Chart Engine

- **Library:** TradingView Lightweight Charts v5 (open source, Apache 2.0)
- **Rendering:** `QWebEngineView` (already in deps: `PyQt6-WebEngine>=6.5`)
- **JS bundle:** Downloaded once to `src/us_swing/gui/resources/lightweight-charts.standalone.production.js` — used offline. Falls back to CDN URL if bundle is missing.
- **Chart types:** Candlestick (main pane) + Histogram volume (sub-pane, 80 px height)
- **Theme:** Dark theme matching the app's terminal aesthetic (BASE/SURFACE/OVERLAY colours from `theme.C`)

## 32.3 Toolbar Controls

| Control | Description |
|---|---|
| **Symbol** combo (editable) | Populated from `SELECT DISTINCT symbol FROM price_1d ORDER BY symbol` |
| **Timeframe** combo | "1d" or "1w" (maps to `price_1d` / `price_1w` tables) |
| **Bars** spinbox | Number of most-recent bars to display (range 20–2000, default 500) |
| **Load Chart** button | Fetches data and renders chart |
| **↺ Refresh List** button | Re-queries DB for latest symbol list |

## 32.4 Crosshair Tooltip

A header strip below the toolbar shows OHLCV + volume values for the bar under the crosshair (live update via `subscribeCrosshairMove`).

## 32.5 Time Scale Sync

Both the candlestick pane and the volume histogram pane scroll and zoom in sync via `subscribeVisibleLogicalRangeChange`.

## 32.6 Watermark

Bottom-left watermark: `"US Swing | <SYMBOL> — <TIMEFRAME>"`.

## 32.7 AppService Methods Added

| Method | Signature | Description |
|---|---|---|
| `get_candle_symbols` | `() -> list[str]` | All symbols with data in `price_1d` |
| `get_candles_for_symbol` | `(symbol, timeframe, limit) -> list[dict]` | OHLCV rows as dicts with Unix `time` timestamps |

## 32.8 Status

**Implemented** — `src/us_swing/gui/chart_panel.py`, `AppService.get_candles_for_symbol()`, bundled JS at `src/us_swing/gui/resources/lightweight-charts.standalone.production.js`.
