# Design Document — Analysis / Live Signal Engine (ANA)

**Document ID:** DD-ANA
**Version:** 1.1.0
**Traces To:** SRD-ANA v1.1.0
**Status:** Draft
**Last Updated:** 2026-03-06
**Project:** US Swing Trading System

---

## DD-ANA-001.001.D01 — CandleBuilder Design

**Parent SRD:** SRD-ANA-001.001 — SRD-ANA-001.006

### Public Interface

```python
@dataclass
class RealtimeBar:
    symbol:   str
    time:     datetime     # UTC, start of 5-second window
    open:     float
    high:     float
    low:      float
    close:    float
    volume:   int

CandleCallback = Callable[[str, str, OHLCVBar], None]  # (symbol, timeframe, bar)

class CandleBuilder:
    SUPPORTED_TF: ClassVar[list[str]] = ['1m', '3m', '5m', '15m', '1h']

    def __init__(
        on_candle_closed: CandleCallback,
        gap_fill: bool = True
    ) -> None

    def add_bar(bar: RealtimeBar) -> None
    def get_buffer(symbol: str, timeframe: str) -> list[OHLCVBar]  # last N completed
    def reset(symbol: str) -> None
```

### Internal Buffer Structure

```python
# per (symbol, timeframe)
_buffers: dict[tuple[str,str], list[RealtimeBar]]  # accumulating 5s bars
_completed: dict[tuple[str,str], deque[OHLCVBar]]  # rolling last-N completed candles (N=200)
_candle_start: dict[tuple[str,str], datetime]       # start time of current open candle
```

### Candle Boundary Calculation

For timeframe `T` (in seconds), candle start = `floor(bar.time / T) * T`.
When a new bar arrives with `floor(bar.time / T) > current_candle_start / T`:
1. Finalise current candle from buffer using aggregation rules.
2. Fire `on_candle_closed(symbol, timeframe, finalised_bar)`.
3. Clear buffer; initialise new candle.

### Gap Fill Logic

If `bar.time > prev_bar.time + 5s` (gap detected), insert synthetic bars:
```
synthetic = OHLCVBar(open=prev.close, high=prev.close, low=prev.close, close=prev.close, volume=0)
```
Fill all missing 5s slots before processing the real bar.

---

## DD-ANA-001.002.D01 — LiveEngine & Dispatcher Design

**Parent SRD:** SRD-ANA-001.001, SRD-ANA-001.004, SRD-ANA-001.006

### Public Interface

```python
class LiveEngine:
    def __init__(
        client: IBKRClient,
        candle_builder: CandleBuilder,
        strategy_engine: StrategyEngine,
        db_persister: DatabasePersister,
        config: LiveConfig,
    ) -> None

    async def start(symbols: list[str]) -> None
    async def stop() -> None
    def on_realtime_bar(bar: RealtimeBar) -> None          # IBKR callback entry point
```

### Event Dispatch on Candle Close

```
CandleBuilder fires on_candle_closed(symbol, tf, bar)
          │
          ├─► [sync]  StrategyEngine.on_candle_closed(symbol, tf, bar)
          │               │
          │               └─► returns TradeSignal | None
          │                         │
          │                         └─► [if signal] ExecutionEngine.submit_signal(signal)
          │
          └─► [async] DatabasePersister.persist_candle(symbol, tf, bar)
```

### DatabasePersister Design

```python
class DatabasePersister:
    def __init__(db: DatabaseManager) -> None

    def persist_candle(symbol: str, timeframe: str, bar: OHLCVBar) -> None  # enqueues

    # Internal:
    _queue: queue.Queue[tuple[str,str,OHLCVBar]]
    _writer_thread: threading.Thread  # drains queue every 5 s
```

---

## DD-ANA-002.001.D01 — StrategyEngine & Signal Design

**Parent SRD:** SRD-ANA-002.001 — SRD-ANA-002.008

### Public Interface

```python
@dataclass
class TradeSignal:
    symbol:      str
    direction:   Literal['BUY', 'SELL']
    entry_price: float
    stop_loss:   float
    target_price:float
    timeframe:   str
    strategy_id: str
    timestamp:   datetime

class StrategyEngine:
    def __init__(
        strategies: list[Strategy],
        exit_manager: ExitManager,
        position_tracker: PositionTracker,
        config: StrategyConfig,
        user_id: int,                    # active user for position checks
    ) -> None

    def on_candle_closed(symbol: str, timeframe: str, bar: OHLCVBar) -> TradeSignal | None

    # Internal bar cache
    _cache: dict[tuple[str,str], deque[OHLCVBar]]  # (symbol, tf) → last N bars
```

### Strategy Protocol

```python
class Strategy(Protocol):
    strategy_id: str
    trigger_timeframes: list[str]   # only called when these TFs close

    def evaluate(
        self,
        symbol: str,
        bar_cache: dict[str, deque[OHLCVBar]],  # keyed by timeframe
        config: StrategyConfig,
    ) -> TradeSignal | None
```

### BreakoutStrategy Logic

```
1. Check: cache['1h'] has ≥ 50 bars
2. Trend filter:  close_1h > EMA(cache['1h'], 50)
3. Entry trigger: close_15m > max(cache['15m'][-21:-1], key=lambda b: b.high)  [prior 20 bars]
4. If both True:
   atr = ATR(cache['15m'], 14)
   signal = TradeSignal(direction='BUY',
       entry_price = close_15m,
       stop_loss   = close_15m - atr * config.atr_multiplier,
       target_price= close_15m + (atr * config.atr_multiplier) * config.r_multiple,
       strategy_id = 'breakout_15m', timeframe='15m')
```

### PullbackStrategy Logic

```
1. Check: cache['1h'] has ≥ 21 bars, cache['5m'] has ≥ 21 bars
2. Trend:    close_1h > EMA(cache['1h'], 21)
3. Pullback: prev_5m.close < EMA(cache['5m'], 21)  AND  cur_5m.close > EMA(cache['5m'], 21)
4. If both True → BUY signal with same ATR-based SL/TP
```

### ExitManager Design

```python
class ExitManager:
    def evaluate(
        symbol: str,
        bar: OHLCVBar,
        position: OpenPosition,
        bar_cache: dict[str, deque[OHLCVBar]],
        config: StrategyConfig,
    ) -> TradeSignal | None
```

Exit triggers (evaluated in order, first match wins):
1. `bar.close ≤ position.stop_loss` → stop-loss exit
2. `bar.close ≥ position.target_price` → target exit
3. Trailing stop: update trail → if `bar.close ≤ position.trailing_stop` → trail exit
