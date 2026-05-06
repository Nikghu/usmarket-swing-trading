# Functional Objectives — Analysis / Live Signal Engine (ANA)

**Document ID:** FO-ANA
**Version:** 1.1.0
**Status:** Draft
**Last Updated:** 2026-03-06
**Project:** US Swing Trading System

> Traces to: `us_swing/requirements.md` §9, §10, §11, §12, §22, §25

---

## FO-ANA-001: Real-Time Bar Ingestion & Multi-Timeframe Candle Construction
- **Status:** Approved

- The system shall subscribe to **5-second real-time bars** from IBKR for each stock in the active watchlist (maximum 20 symbols).
- Each 5-second bar shall be appended to an in-memory rolling buffer specific to its symbol.
- From the 5-second buffer the system shall construct completed candles for: **1m, 3m, 5m, 15m, and 1h** timeframes using the standard OHLCV aggregation rules (open = first-bar open, high = max, low = min, close = last-bar close, volume = sum).
- A candle is considered **complete** when its time boundary has elapsed and a new bar begins (e.g., a 1m candle closes at the 60-second mark).
- Completed candles shall be persisted to the database on a background thread without blocking signal evaluation.
- Live-constructed candles shall be byte-identical in OHLCV values to any historical bars stored for the same symbol and timestamp (consistency guarantee).
- The system shall handle gaps in 5-second bar delivery (e.g., no trades in a 5s window) by carrying forward OHLCV values with volume = 0.
- **Acceptance Criteria:**
  - Given 12 consecutive 5-second bars for symbol AAPL, the system produces exactly one complete 1m candle with correct OHLCV aggregation.
  - Given 3 complete 1m candles, the system produces exactly one complete 3m candle.
  - A completed 1m live candle that overlaps a historical 1m bar for the same symbol/timestamp is identical in all OHLCV fields.
  - 20 simultaneous live subscriptions process 5-second bars without throughput degradation or dropped events.
  - A gap (missing 5s bar) does not cause an error; the next received bar continues aggregation correctly.

---

## FO-ANA-002: Multi-Timeframe Entry & Exit Signal Generation
- **Status:** Draft

- The system shall evaluate entry and exit conditions **every time a new candle completes** on any tracked timeframe.
- Entry conditions shall operate on at least two timeframes in a top-down hierarchy (e.g., 1h trend confirmation → 15m setup → 5m entry trigger) to align swing intent with intraday timing.
- The following entry patterns shall be supported as configurable strategies (enable/disable per config):
  - **Breakout entry** — price closes above N-bar resistance level on the 15m or 5m timeframe.
  - **Pullback entry** — price retraces to a configurable EMA (e.g., EMA21) after a trend move and shows reversal confirmation.
- Exit conditions shall include:
  - **Stop loss** — fixed ATR-based stop below entry candle.
  - **Profit target** — fixed R-multiple target (e.g., 2R).
  - **Trailing stop** — ATR-based trail activated after price moves a configurable distance in profit.
- Each signal shall carry: symbol, direction (long/short), entry price, stop-loss price, target price, timeframe of trigger, strategy ID.
- The system shall never emit a signal for a symbol that already has an open position **for the same user** (no pyramiding by default; configurable per user).
- Strategy enable/disable and parameter configuration shall be per-user, loaded from the user's `settings_json` strategy config.
- **Acceptance Criteria:**
  - Given a configurable breakout strategy, a new 15m candle closing above the 20-bar high produces exactly one BUY signal for that symbol.
  - Given an open long position with a 2R target, the system emits a SELL signal when price reaches the target price.
  - Given an open long position with an ATR stop, the system emits a SELL signal when price closes below the stop level.
  - No entry signal is generated for a symbol that already has an open position for the active user (default config).
  - All signals are logged with full metadata (symbol, strategy, timeframe, prices) for audit.
