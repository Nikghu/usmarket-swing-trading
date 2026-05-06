# Module Decomposition — Analysis / Live Signal Engine (ANA)

**Document ID:** MD-ANA
**Version:** 1.1.0
**Traces To:** SRD-ANA v1.1.0 / DD-ANA v1.1.0
**Status:** Draft
**Last Updated:** 2026-03-06
**Project:** US Swing Trading System

---

## ANA Modules

| ID | Parent SRD | File | Responsibility | Public API | Deps | MCP | Status |
|---|---|---|---|---|---|---|---|
| MD-ANA-001.001.M01 | SRD-ANA-001.002–005 | `src/us_swing/analysis/candle_builder.py` | `CandleBuilder` — accepts 5s bars, builds multi-TF candles, fires `on_candle_closed` callback, handles gaps | `add_bar(bar: RealtimeBar)`, `get_buffer(symbol, tf) -> list[OHLCVBar]`, `reset(symbol)` | `data/models.py` | No | Draft |
| MD-ANA-001.001.M02 | SRD-ANA-001.001, SRD-ANA-001.004, SRD-ANA-001.006 | `src/us_swing/analysis/live_engine.py` | `LiveEngine` — subscribes to IBKR bars, routes to `CandleBuilder`, dispatches to strategy and DB persister | `start(symbols: list[str])`, `stop()`, `on_realtime_bar(bar: RealtimeBar)` | `broker/client.py`, `candle_builder.py`, `strategy_engine.py`, `db_persister.py`, `data/models.py` | No | Approved |
| MD-ANA-001.001.M03 | SRD-ANA-001.006 | `src/us_swing/analysis/db_persister.py` | `DatabasePersister` — thread-safe async queue writer for completed candles | `persist_candle(symbol, tf, bar)`, (internal) `_writer_loop()` | `db/manager.py`, `data/models.py`, `queue`, `threading` | No | Draft |
| MD-ANA-002.001.M01 | SRD-ANA-002.001, SRD-ANA-002.007–008, SRD-ANA-003.001–002 | `src/us_swing/analysis/strategy_engine.py` | `StrategyEngine` — maintains bar cache, calls strategies, guards against duplicate positions per user. Accepts `user_id` and per-user `StrategyConfig`. | `on_candle_closed(symbol, tf, bar) -> TradeSignal \| None` | `strategies/`, `exit_manager.py`, `execution/position_tracker.py`, `data/models.py` | No | Approved |
| MD-ANA-002.001.M02 | SRD-ANA-002.002 | `src/us_swing/analysis/strategies/breakout.py` | `BreakoutStrategy` — 1h trend + 15m/5m breakout above N-bar high | `evaluate(symbol, bar_cache, config) -> TradeSignal \| None` | `analysis/indicators.py`, `data/models.py` | No | Draft |
| MD-ANA-002.001.M03 | SRD-ANA-002.003 | `src/us_swing/analysis/strategies/pullback.py` | `PullbackStrategy` — 1h uptrend + 5m EMA21 pullback recovery | `evaluate(symbol, bar_cache, config) -> TradeSignal \| None` | `analysis/indicators.py`, `data/models.py` | No | Draft |
| MD-ANA-002.001.M04 | SRD-ANA-002.005–006 | `src/us_swing/analysis/exit_manager.py` | `ExitManager` — evaluates stop-loss, target, trailing-stop exit conditions | `evaluate(symbol, bar, position, bar_cache, config) -> TradeSignal \| None`, `update_trailing_stop(symbol, bar, position)` | `analysis/indicators.py`, `execution/position_tracker.py`, `data/models.py` | No | Draft |
| MD-ANA-001.001.M04 | SRD-SCR-001.002–006 (shared) | `src/us_swing/analysis/indicators.py` | Shared indicator library: `atr(bars, period)`, `rsi(bars, period)`, `ema(bars, period)`, `ema_value(bars, period)` | All functions are pure (no side effects), receive `list[OHLCVBar]`, return `float \| list[float]` | `data/models.py` | No | Approved |

---

## Module Dependency Graph

```
data/models.py
analysis/indicators.py          ← data/models.py

analysis/candle_builder.py      ← data/models.py
analysis/db_persister.py        ← db/manager.py, data/models.py

analysis/strategies/breakout.py ← indicators.py, data/models.py
analysis/strategies/pullback.py ← indicators.py, data/models.py
analysis/exit_manager.py        ← indicators.py, execution/position_tracker.py, data/models.py

analysis/strategy_engine.py     ← strategies/, exit_manager.py, execution/position_tracker.py
analysis/live_engine.py         ← broker/client.py, candle_builder.py, strategy_engine.py, db_persister.py
```
