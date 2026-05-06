# Software Requirements Document — MCP Server Module (MCP)

**Document ID:** SRD-MCP
**Version:** 1.0.0
**Traces To:** FO-MCP v1.0.0
**Status:** Draft
**Last Updated:** 2026-03-06
**Project:** US Swing Trading System

---

## Section 1: Requirements for FO-MCP-001 — MCP Server Interface

| ID | Parent | P | Description | In | Out | Constraints | Status |
|---|---|---|---|---|---|---|---|
| SRD-MCP-001.001 | FO-MCP-001 | Must | `MCPServer` class wraps FastMCP, registers all tool handlers on init, and starts listening on a configurable `host:port`. Server lifecycle is tied to application lifecycle. | `AppConfig.mcp_host`, `AppConfig.mcp_port` | Running MCP server | Port must be configurable via Settings panel and config file | Draft |
| SRD-MCP-001.002 | FO-MCP-001 | Must | Each MCP tool handler validates its input against a JSON schema stored in `mcp/schemas/{tool_name}.json`. Invalid input returns `{"error": "validation_error", "details": [...]}`. | Raw MCP request | Validated params or error response | Uses `jsonschema` library for validation | Draft |
| SRD-MCP-001.003 | FO-MCP-001 | Must | All tool handlers that modify state (e.g., `submit_order`) require a `user_id` parameter. Read-only tools (`get_universe`, `system_health`) do not require `user_id`. | Request params | Scoped response | `user_id` validated against `users` table; unknown user_id → error | Draft |
| SRD-MCP-001.004 | FO-MCP-001 | Must | Unhandled exceptions in tool handlers are caught, logged as ERROR, and returned as `{"error": "internal_error", "message": str(e)}`. No stack traces exposed to client. | Exception in handler | Error response + log | Security: no internal paths or secrets in error messages | Draft |

---

## Section 2: Requirements for FO-MCP-002 — Data & Universe Tools

| ID | Parent | P | Description | In | Out | Constraints | Status |
|---|---|---|---|---|---|---|---|
| SRD-MCP-002.001 | FO-MCP-002 | Must | `fetch_ohlcv` tool: accepts `{"symbols": list[str], "start_date": str|null, "end_date": str|null}`. Delegates to `DataEngine.fetch()` for each symbol. Returns `{"fetched": {symbol: bar_count}}`. | JSON params | Fetch result dict | Respects broker pacing limits; may take seconds per symbol | Draft |
| SRD-MCP-002.002 | FO-MCP-002 | Must | `get_universe` tool: accepts `{}` (no params). Returns `{"symbols": [{"symbol": str, "name": str, "sector": str}]}` from `UniverseManager.get_all()`. | Empty params | Universe list | Read-only; no user_id required | Draft |

---

## Section 3: Requirements for FO-MCP-003 — Screener & Watchlist Tools

| ID | Parent | P | Description | In | Out | Constraints | Status |
|---|---|---|---|---|---|---|---|
| SRD-MCP-003.001 | FO-MCP-003 | Must | `run_screener` tool: accepts `{"user_id": int, "config_override": dict|null}`. If `config_override` is null, uses user's saved `ScreenerConfig`. Delegates to `ScreenerEngine.run(config)`. Returns `{"results": [{"symbol": str, "score": float, "filters": dict}]}`. | JSON params | Screener results | Max 500 results (full universe) | Draft |
| SRD-MCP-003.002 | FO-MCP-003 | Must | `get_watchlist` tool: accepts `{"user_id": int}`. Returns `{"watchlist": [str]}` — current day's watchlist symbols for the user (max 20). | JSON params | Watchlist symbols | Read-only | Draft |

---

## Section 4: Requirements for FO-MCP-004 — Analysis & Signal Tools

| ID | Parent | P | Description | In | Out | Constraints | Status |
|---|---|---|---|---|---|---|---|
| SRD-MCP-004.001 | FO-MCP-004 | Must | `get_signals` tool: accepts `{"user_id": int}`. Returns `{"signals": [{"symbol": str, "side": str, "strategy_id": str, "entry_price": float, "stop_loss": float, "target": float, "recommended_qty": int}]}`. Only returns unacted signals. | JSON params | Pending signals list | Scoped to user_id; signals expire at end of trading day | Draft |

---

## Section 5: Requirements for FO-MCP-005 — Execution & Position Tools

| ID | Parent | P | Description | In | Out | Constraints | Status |
|---|---|---|---|---|---|---|---|
| SRD-MCP-005.001 | FO-MCP-005 | Must | `get_positions` tool: accepts `{"user_id": int}`. Returns `{"positions": [{"symbol": str, "qty": int, "avg_entry": float, "state": str, "unrealised_pnl": float, "mode": str}]}`. | JSON params | Open positions | Only non-CLOSED positions returned | Draft |
| SRD-MCP-005.002 | FO-MCP-005 | Must | `submit_order` tool: accepts `{"user_id": int, "symbol": str, "side": str, "quantity": int|null, "order_type": str}`. Delegates to `ExecutionRouter.route_signal()`. Returns `{"order_id": int}` on success or `{"error": "rejected", "reason": str}`. | JSON params | Order result | `side` must be BUY or SELL; `order_type` must be MKT or LMT; validated by RiskManager before execution | Draft |
| SRD-MCP-005.003 | FO-MCP-005 | Must | `get_daily_pnl` tool: accepts `{"user_id": int}`. Returns `{"daily_pnl": float, "trade_count": int}`. | JSON params | P&L summary | Read-only; delegates to `DailyPnLTracker` | Draft |

---

## Section 6: Requirements for FO-MCP-006 — System Health Tool

| ID | Parent | P | Description | In | Out | Constraints | Status |
|---|---|---|---|---|---|---|---|
| SRD-MCP-006.001 | FO-MCP-006 | Should | `system_health` tool: accepts `{}`. Returns `{"broker_connected": bool, "active_subscriptions": int, "last_data_update": str, "error_count_today": int, "circuit_breaker_active": bool}`. | Empty params | Health status | Read-only; response time ≤ 500ms; no user_id required | Draft |
