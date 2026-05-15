# Revision Note — RN-EXE-1.2.0-20260515

**Version:** 1.2.0
**Date:** 2026-05-15
**Tool:** EXE — Execution & Risk Management
**Artifact:** FO-EXE-008 / MD-EXE-008.001.M01

---

## Summary

Implemented `LiveTickWorker` — a new `QThread` that streams live last-price ticks for a set of IBKR contracts via `reqMktData`. Replaces yfinance polling for the Market Watch strip, Watchlist price column, and Position Monitor current price. Uses a dedicated IBKR clientId (default 14, configurable via `SystemConfig.ibkr_tick_client_id`).

---

## New File

| File | Module ID | Description |
|---|---|---|
| `execution/live_tick_worker.py` | MD-EXE-008.001.M01 | IBKR reqMktData streaming tick worker |

---

## Key Design Decisions

- **`threading.RLock`** instead of `Lock` — `set_contracts` holds the lock and calls `_subscribe_batch` → `ib.reqMktData()`, which can dispatch `pendingTickersEvent` synchronously on the same thread. A plain Lock would deadlock; RLock allows re-entry.
- **`run_in_executor` for initial subscription** — `_async_run` dispatches the first `set_contracts` call via `loop.run_in_executor()` to avoid blocking the asyncio event loop during the 200 ms per-batch pacing sleep.
- **Dual tag lookup** (`reqId` primary, `conId` fallback) — at subscription time the conId may be 0 if IBKR hasn't resolved the contract yet; the reqId lookup handles the common case, the conId dict handles late-binding.
- **clientId collision retry** — `_connect_with_retry` attempts up to 4 connects with incrementing clientId to handle IBKR error 326 (clientId in use).

---

## Fatal Error Codes

| Code | Meaning | Action |
|---|---|---|
| 200 | No matching contract | Remove from active, emit `subscription_failed` |
| 354 | No market data permission | Remove from active, emit `subscription_failed` |
| 420 | Invalid tick type | Remove from active, emit `subscription_failed` |

---

## Tests

16 unit tests — `tests/execution/test_live_tick_worker.py` (T01–T16, all Pass).

---

## SRDs Satisfied

SRD-EXE-008.001–006 (all set to Implemented).
