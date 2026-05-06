# US Swing Trading System — Project Vision & Roadmap

**Document:** idea.md
**Version:** 2.0.0
**Created:** 2026-03-05
**Revised:** 2026-03-06

---

## 1. Vision

Build a **production-grade, modular, automated swing trading system** for the US equity market (S&P 500 universe) using Interactive Brokers as the execution venue, with a **dual interface**: a rich **PyQt6 GUI** for operator control and an **MCP server** for AI agent integration.

The system shall:
- Provide a **user-friendly PyQt6 GUI** with full manoeuvre access — every core operation (screener selection, quantity override, user management, position monitoring, paper/live toggle) controllable from the GUI.
- Expose an **MCP (Model Context Protocol) server** for each major task: data fetch, screening, analysis, execution command.
- Support **multiple users** with isolated settings, strategy configs, and IBKR client IDs.
- **Auto-launch** via Windows Task Scheduler before market open; perform data update, screening, and live monitoring autonomously.
- Identify swing trading set-ups overnight using a configurable, user-selected multi-factor screener.
- Execute trades intraday using multi-timeframe confirmation logic — supports both **paper trading** (simulated) and **live trading** (IBKR).
- Track positions across days: know if a position is new, partial entry, partial exit, or fully closed — visible in GUI.
- Evaluate available capital before entering additional stocks.
- Operate with strict risk controls (position sizing, daily loss limits, circuit breaker).
- Be extensible: new strategies, new screener filters, and new risk controls can be added without breaking existing code.

---

## 2. Core Design Principles

| Principle | Implementation |
|---|---|
| **Historical = Live consistency** | 5s bar → candle aggregation uses the same function as historical re-aggregation |
| **Separation of concerns** | INF / SCR / ANA / EXE are independent sub-packages; GUI is an interface layer over core |
| **Dual interface** | Every core function accessible via PyQt6 GUI **and** MCP server endpoint |
| **Config-driven** | Every threshold, filter, and risk parameter lives in `config/settings.py`; zero magic numbers in code |
| **Multi-user isolation** | Per-user config profiles, IBKR client IDs, position tracking, risk settings |
| **Fail-safe first** | Circuit breaker, auto-reconnect, emergency kill-switch built in from day 1 |
| **Testable by design** | All components accept dependency injection; no global state |
| **Paper/Live parity** | Paper trading mode simulates orders locally with identical logic; one toggle to switch |

---

## 3. Toolchain / Tech Stack

| Component | Choice | Rationale |
|---|---|---|
| Broker API | `ib_insync` (IBKR) | Mature async Python wrapper for TWS/Gateway |
| GUI Framework | PyQt6 | Rich desktop toolkit; used in pilot1; native Windows support |
| MCP Server | FastMCP / custom | AI agent protocol; one tool per major operation |
| Database (dev) | SQLite | Zero-config, file-based, same SQL as PostgreSQL |
| Database (prod) | PostgreSQL | Indexed time-series performance at 500-symbol scale |
| ORM | SQLAlchemy (Core, not ORM layer) | Backend-agnostic; performant bulk inserts |
| Concurrency | `asyncio` + `threading` for DB writes | IBKR event loop is asyncio; DB writes on thread |
| Scheduler | Windows Task Scheduler | Auto-launch system before market open |
| S&P 500 list | Wikipedia via `pandas.read_html` (configurable) | Free, reliable; replaceable with paid data source |
| S&P 500 OHLCV | IBKR Historical Data API | Primary source; dummy provider for dev/testing |
| Deployment | Windows VPS (initial); Linux VPS (future) | Matches IBKR Gateway OS compatibility |
| Language | Python 3.11+ | `tomllib`, `asyncio` improvements, `match` statements |

---

## 4. Tool Roadmap

| Phase | Tool | Scope | Priority |
|---|---|---|---|
| 1 | **INF** — Infrastructure | IBKR client, universe, historical data, DB, logging, multi-user config, scheduler | **Now** |
| 2 | **SCR** — Screener | 5-factor screener, watchlist generation, user-selectable filters | After INF |
| 3 | **ANA** — Analysis | Candle builder, live engine, strategy signals, user-pluggable strategies | After SCR |
| 4 | **EXE** — Execution | Risk manager, order engine, circuit breaker, paper/live toggle, position state tracking | After ANA |
| 5 | **GUI** — Graphical Interface | PyQt6 main window, dashboards for each tool, user management panel, trade quantity controls, position monitor | Parallel with INF–EXE |
| 6 | **MCP** — MCP Server | MCP endpoints for data fetch, screening, analysis commands, execution controls | Parallel with INF–EXE |
| 7 | **BKT** — Backtesting | Replay historical data through strategy + risk engine | Future |
| 8 | **RPT** — Reporting | Daily/weekly P&L reports, trade journal, performance analytics | Future |

---

## 5. Open Questions / Decisions

| # | Question | Decision | Date |
|---|---|---|---|
| 1 | SQLAlchemy ORM vs Core? | Use SQLAlchemy Core (raw SQL-like) for performance | 2026-03-05 |
| 2 | Async strategy evaluation or sync? | Sync (strategy evaluation < 50 ms; asyncio overhead not justified) | 2026-03-05 |
| 3 | Support short selling? | No — long-only for initial version | 2026-03-05 |
| 4 | Which broker pacing queue implementation? | asyncio token-bucket in `broker/pacing.py` | 2026-03-05 |
| 5 | GUI for monitoring? | **PyQt6 GUI is a core component** — full operator control, not just monitoring | 2026-03-06 |
| 6 | Multi-user support? | Yes — per-user profiles, settings, IBKR client IDs, isolated positions | 2026-03-06 |
| 7 | Paper trading mode? | Yes — simulated order execution with identical logic to live; toggle per user | 2026-03-06 |
| 8 | Auto-launch mechanism? | Windows Task Scheduler; system starts T-60 before market open | 2026-03-06 |
| 9 | MCP server? | Yes — one MCP tool per major operation (data fetch, screen, analyze, execute) | 2026-03-06 |
| 10 | S&P 500 data source for development? | Dummy provider (local CSV/mock) until real IBKR data available; configurable | 2026-03-06 |
| 11 | User-defined trade quantity? | Yes — users can override auto-calculated position size via GUI | 2026-03-06 |
| 12 | Position state tracking across days? | Track states: NEW, PARTIAL_ENTRY, OPEN, PARTIAL_EXIT, CLOSED — persist in DB, show in GUI | 2026-03-06 |

---

## 6. Future Enhancements (Backlog)

- Portfolio-level position sizing (Kelly criterion / Equal-weight)
- Pyramiding with configurable scale-in rules
- Machine learning screener layer (feature engineering from OHLCV)
- Multi-broker support (Alpaca, Tradier)
- Mobile push notifications (trade events, circuit breaker alerts)
- Market calendar awareness (US holidays, half-days, early closes)
- Data backup/export for external analysis
- User authentication (login/password or API key for multi-user security)
