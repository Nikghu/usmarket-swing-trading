# Design Document — MCP Server Module (MCP)

**Document ID:** DD-MCP
**Version:** 1.0.0
**Traces To:** SRD-MCP v1.0.0
**Status:** Draft
**Last Updated:** 2026-03-06
**Project:** US Swing Trading System

---

## DD-MCP-001.001.D01 — MCPServer Core Design

**Parent SRD:** SRD-MCP-001.001 — SRD-MCP-001.004

### Public Interface

```python
class MCPServer:
    def __init__(
        host: str,
        port: int,
        data_engine: DataEngine,
        universe_manager: UniverseManager,
        screener_engine: ScreenerEngine,
        strategy_engine: StrategyEngine,
        execution_router: ExecutionRouter,
        position_tracker: PositionTracker,
        daily_pnl_tracker: DailyPnLTracker,
        user_manager: UserManager,
        health_monitor: HealthMonitor,
    ) -> None

    async def start(self) -> None
    async def stop(self) -> None
```

### Tool Registration

```python
from fastmcp import FastMCP

mcp = FastMCP("us_swing")

@mcp.tool()
async def fetch_ohlcv(symbols: list[str], start_date: str | None = None, end_date: str | None = None) -> dict:
    ...

@mcp.tool()
async def get_universe() -> dict:
    ...

# ... (all 9 tools registered)
```

### Request Validation Flow

```
MCP Request received
    │
    ├─ 1. Load JSON schema from mcp/schemas/{tool_name}.json
    ├─ 2. jsonschema.validate(params, schema)
    │       └► ValidationError → return {"error": "validation_error", "details": [...]}
    ├─ 3. If tool requires user_id: validate user_id exists via UserManager
    │       └► Unknown user_id → return {"error": "unknown_user", "user_id": ...}
    ├─ 4. Delegate to service layer
    │       └► Exception → log ERROR, return {"error": "internal_error", "message": str(e)}
    └─ 5. Return tool result
```

### Error Response Contract

```python
# All error responses follow this structure:
{
    "error": str,      # error type: "validation_error" | "unknown_user" | "rejected" | "internal_error"
    "message": str,    # human-readable message (no stack traces or internal paths)
    "details": list,   # optional: validation details
}
```

---

## DD-MCP-005.001.D01 — submit_order Tool Design

**Parent SRD:** SRD-MCP-005.002

### Order Submission Flow

```
submit_order(user_id, symbol, side, quantity, order_type)
    │
    ├─ 1. Validate user_id via UserManager
    ├─ 2. Build TradeSignal from params
    ├─ 3. Determine quantity:
    │       if quantity provided → use as quantity_override
    │       else → let RiskManager.calculate_position_size()
    ├─ 4. Call ExecutionRouter.route_signal(user_id, signal, quantity_override=quantity)
    │       └► Rejection → return {"error": "rejected", "reason": validation_result.reason}
    └─ 5. Return {"order_id": result}
```

### Security Considerations

- `user_id` is validated against DB, not trusted from client.
- No execution without passing `RiskManager.validate_signal()` and `can_enter_new()`.
- `submit_order` uses the same `ExecutionRouter` as GUI — no separate code path.
