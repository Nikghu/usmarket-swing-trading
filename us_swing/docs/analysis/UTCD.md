# Unit Test Case Document — Analysis / Live Signal Engine (ANA)

**Document ID:** UTCD-ANA
**Version:** 1.1.0
**Traces To:** MD-ANA v1.1.0
**Status:** Draft
**Last Updated:** 2026-03-06
**Project:** US Swing Trading System

> Tests written BEFORE implementation per process.md §7.

---

## Module: `analysis/indicators.py` — Shared Indicators

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-ANA-001.001.M04.T01 | MD-ANA-001.001.M04 | Unit | `ema(bars, 3)` — correct value for simple sequence | Closes: [10,11,12,13] | EMA3 ≈ 12.375 (multip=0.5) | Draft |
| UT-ANA-001.001.M04.T02 | MD-ANA-001.001.M04 | Unit | `atr(bars, 14)` returns positive value | 30 bars with varying Hi/Lo | ATR > 0 | Draft |
| UT-ANA-001.001.M04.T03 | MD-ANA-001.001.M04 | Edge | `rsi(bars, 14)` with 14 bars returns value in [0, 100] | Exactly 14 bars | float value in [0, 100] | Draft |
| UT-ANA-001.001.M04.T04 | MD-ANA-001.001.M04 | Edge | `rsi()` with fewer than 14+1 bars raises or returns NaN | 10 bars | `ValueError` or `float('nan')` depending on contract | Draft |

---

## Module: `analysis/candle_builder.py` — CandleBuilder

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-ANA-001.001.M01.T01 | MD-ANA-001.001.M01 | Unit | 12 consecutive 5s bars produce exactly one 1m candle | 12 `RealtimeBar` for AAPL spanning 60 s | Callback fires once with correct OHLCV aggregation | Draft |
| UT-ANA-001.001.M01.T02 | MD-ANA-001.001.M01 | Unit | 1m candle open = first-bar open | Bars: open=[10,11,12] | `candle.open == 10` | Draft |
| UT-ANA-001.001.M01.T03 | MD-ANA-001.001.M01 | Unit | 1m candle high = max of all bars | Bars with highs [12,15,11] | `candle.high == 15` | Draft |
| UT-ANA-001.001.M01.T04 | MD-ANA-001.001.M01 | Unit | 1m candle close = last-bar close | Bars: close=[10,11,13] | `candle.close == 13` | Draft |
| UT-ANA-001.001.M01.T05 | MD-ANA-001.001.M01 | Unit | 1m candle volume = sum of all bars | Bars: volume=[100,200,300] | `candle.volume == 600` | Draft |
| UT-ANA-001.001.M01.T06 | MD-ANA-001.001.M01 | Unit | 3m candle fires after 36 bars (3 × 12 × 5s) | 36 consecutive 5s bars | 3m callback fires exactly once | Draft |
| UT-ANA-001.001.M01.T07 | MD-ANA-001.001.M01 | Edge | Gap in 5s delivery: missing bar filled with carry-forward | Bar at T; next bar at T+10 (two 5s windows) | Synthetic bar inserted with volume=0; no exception | Draft |
| UT-ANA-001.001.M01.T08 | MD-ANA-001.001.M01 | Unit | Two symbols in parallel do not cross-contaminate buffers | Interleaved bars for AAPL and MSFT | Each symbol's candle uses only its own bars | Draft |
| UT-ANA-001.001.M01.T09 | MD-ANA-001.001.M01 | Unit | Live 1m candle equals historical aggregation of same 12 bars | Same 12 bars processed by both `CandleBuilder` and `aggregate_timeframe()` | Both produce identical `OHLCVBar` | Draft |

---

## Module: `analysis/strategy_engine.py` + `strategies/`

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-ANA-002.001.M01.T01 | MD-ANA-002.001.M01 | Unit | No signal when trend filter fails | 1h close < EMA50; 15m breakout triggered | No signal returned | Draft |
| UT-ANA-002.001.M01.T02 | MD-ANA-002.001.M01 | Unit | No signal when existing position open for active user | Valid breakout signal; `PositionTracker.has_open(user_id, "AAPL")=True` | Signal suppressed; DEBUG logged | Draft |
| UT-ANA-002.001.M02.T01 | MD-ANA-002.001.M02 | Unit | `BreakoutStrategy` emits BUY when 1h trend + 15m breakout | Cache with 1h close > EMA50; 15m close > 20-bar high | `TradeSignal(direction='BUY')` returned | Draft |
| UT-ANA-002.001.M02.T02 | MD-ANA-002.001.M02 | Edge | `BreakoutStrategy` returns None with < 21 bars in cache | Only 15 bars in 1h cache | `None` | Draft |
| UT-ANA-002.001.M03.T01 | MD-ANA-002.001.M03 | Unit | `PullbackStrategy` emits BUY on EMA21 cross-above | Prev 5m close < EMA21 AND current 5m close > EMA21; 1h uptrend | `TradeSignal(direction='BUY')` | Draft |
| UT-ANA-002.001.M03.T02 | MD-ANA-002.001.M03 | Unit | `PullbackStrategy` returns None when 1h trend fails | 1h close < EMA21; valid 5m cross | `None` | Draft |
| UT-ANA-002.001.M04.T01 | MD-ANA-002.001.M04 | Unit | Stop-loss exit when price ≤ stop_loss | Current bar `close=49.5`; `position.stop_loss=50.0` | `TradeSignal(direction='SELL', strategy_id='stop_loss')` | Draft |
| UT-ANA-002.001.M04.T02 | MD-ANA-002.001.M04 | Unit | Target exit when price ≥ target_price | Current bar `close=104.0`; `position.target_price=103.0` | `TradeSignal(direction='SELL', strategy_id='target')` | Draft |
| UT-ANA-002.001.M04.T03 | MD-ANA-002.001.M04 | Unit | Trailing stop updates upward only | Price moves from 100→110 then drops to 108; trail_offset=2 | Trail moves to 108 (max-seen-close minus offset); never below previous level | Draft |
| UT-ANA-002.001.M04.T04 | MD-ANA-002.001.M04 | Unit | `TradeSignal` prices are valid: target > entry > stop for BUY | Produce any BUY signal | `signal.target_price > signal.entry_price > signal.stop_loss` | Draft |

---

## Module: `analysis/db_persister.py` — DatabasePersister

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-ANA-001.001.M03.T01 | MD-ANA-001.001.M03 | Unit | `persist_candle()` enqueues bar without blocking | Call from main thread | Returns immediately (< 1 ms) | Draft |
| UT-ANA-001.001.M03.T02 | MD-ANA-001.001.M03 | Integration | Writer thread drains queue and inserts to DB | Enqueue 5 candles; wait 6 s | All 5 bars appear in `price_1m` table | Draft |
| UT-ANA-001.001.M03.T03 | MD-ANA-001.001.M03 | Edge | DB write failure does not crash persister | Mock DB insert raising `Exception` | ERROR logged; writer thread continues processing next items | Draft |

---

## Module: `analysis/strategy_engine.py` — Per-User Strategy Config

| ID | Module | Type | Objective | Input | Expected Output | Status |
|---|---|---|---|---|---|---|
| UT-ANA-003.001.M01.T01 | MD-ANA-002.001.M01 | Unit | `StrategyConfig.from_user_settings()` loads config from valid dict | `{"breakout_enabled": false, "r_multiple": 3.0}` | `config.breakout_enabled == False`, `config.r_multiple == 3.0`, others = defaults | Draft |
| UT-ANA-003.001.M01.T02 | MD-ANA-002.001.M01 | Edge | `StrategyConfig.from_user_settings()` with empty dict returns defaults | `{}` | All fields = defaults | Draft |
| UT-ANA-003.001.M01.T03 | MD-ANA-002.001.M01 | Unit | Disabled strategy is not evaluated | `breakout_enabled=False`; bar data triggers breakout | No BUY signal emitted; PullbackStrategy still evaluated | Draft |
| UT-ANA-003.001.M01.T04 | MD-ANA-002.001.M01 | Unit | Different users with different configs produce different signals | User A: breakout enabled; User B: breakout disabled; same bars | User A gets signal; User B does not | Draft |
