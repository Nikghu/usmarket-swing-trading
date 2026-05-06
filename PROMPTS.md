# Prompt Patterns — Quick Reference

How to give tasks to any LLM on this project. Copy, adapt, and paste.

---

## Session Resume

```
Resume: Read AGENT_BOOT.md. Active project: us_swing.
Next task from last session: <paste §0 from us_swing/CONTEXT.md>
Confirm you have read CONTEXT.md §0 and §2 (Artifact Status) before proceeding.
```

**Example:**
```
Resume: Read AGENT_BOOT.md. Active project: us_swing.
Next task: Write 38 INF unit tests in us_swing/tests/infrastructure/ per UTCD.md.
Confirm context loaded.
```

---

## Test Writing (UTCD → pytest)

```
Write tests: Implement all UTCD tests for <TOOL> module <module_name>.
Source: us_swing/docs/<tool>/UTCD.md — section "Module: <module_file>"
Target file: us_swing/tests/<tool>/test_<module>.py
Rules:
- Each test function docstring must reference its UT ID (e.g., "UT-INF-001.001.M01.T01: ...")
- Follow pytest conventions; use fixtures for shared setup
- After writing, note UTCD Status: Draft → Not Run in CONTEXT.md
```

**Example:**
```
Write tests: Implement all UTCD tests for INF module broker/client.py.
Source: us_swing/docs/infrastructure/UTCD.md — section "Module: broker/client.py — IBKRClient"
Target file: us_swing/tests/infrastructure/test_client.py
```

---

## New Feature (FO)

```
FO: The system shall <action> given <input>, returning <output>.
Constraints: <any limits>.
```

**Examples:**

```
FO: The system shall filter stocks where RSI(14) < 30 AND daily volume > 2× 20-day 
average, returning a DataFrame with columns [symbol, rsi, volume_ratio, close].
```

```
FO: The system shall compute Bollinger Bands (20-period SMA, 2 std dev) for a given 
ticker and date range, returning DataFrame [date, upper, middle, lower, close].
Constraints: Must use the existing DataFeed interface.
```

```
FO: The system shall display a candlestick chart with volume bars for a given ticker 
using PyQt6. The chart shall support zoom, pan, and crosshair overlay.
```

---

## Bug / Issue

```
ISS: <module or function>. Expected: <what should happen>. Actual: <what happens instead>.
```

**Examples:**

```
ISS: cache.get() returns stale data when requested end_date > cached end_date.
Expected: fetch missing days and merge with cache. Actual: returns cached subset silently.
```

```
ISS: validators.validate_ticker() accepts lowercase tickers like "aapl" but Yahoo 
provider fails on them. Expected: auto-uppercase or reject with clear error.
```

```
ISS: OHLCV table model shows dates as datetime objects instead of formatted strings.
Expected: "2025-06-15" format. Actual: "2025-06-15 00:00:00".
```

---

## Refactor

```
Refactor: <what to change> → <desired outcome>.
```

**Examples:**

```
Refactor: Move pilot1/ code to final src/usswing/core/ layout per process.md §14.2.
Update all imports and test paths.
```

```
Refactor: Extract common validation logic from validators.py into a reusable 
decorator that can be applied to any DataFeed method.
```

---

## Enhancement to Existing Module

```
Enhance <module>: Add <capability>. Input: <X>. Output: <Y>.
```

**Examples:**

```
Enhance data_feed: Add support for Polygon.io as a second data provider.
Input: same as Yahoo (symbol, start, end). Output: same DataFrame schema.
```

```
Enhance cache: Add cache expiry — data older than 24 hours should be re-fetched.
```

---

## Document Status Update (session-end)

```
Update docs: Session <N> complete.
- Completed: <brief description>
- Artifact changes: <list — e.g., "UTCD-INF: 38 tests written → Not Run status">
- Next step: <single sentence>
Update us_swing/CONTEXT.md §0 (Immediate Next Step) and §2 (changed Artifact Status rows).
Prepend new entry to us_swing/DEVLOG.md: date, session number, agent, completed work, decisions, next steps.
```

---

## Architecture Review (before starting a new tool)

```
Review: Before implementing <TOOL>, read:
1. us_swing/docs/<tool>/FO.md — understand objectives
2. us_swing/docs/<tool>/SRD.md — scan Approved requirements only
3. us_swing/docs/<tool>/MD.md — list all modules and their file paths
4. us_swing/docs/<tool>/UTCD.md — count tests and confirm scope
Then summarize: first module to implement, INF dependencies, test count.
```

**Example:**
```
Review: Before implementing SCR, read SCR FO/SRD/MD/UTCD.
Summarize: first module to implement, INF dependencies, test count.
```

---

## Tips

1. **Be specific about input/output** — the LLM can derive everything else from these
2. **Name the module** if you know it — saves the LLM from searching
3. **One FO per prompt** — complex features should be split into separate FOs
4. **For bugs, always give Expected vs Actual** — eliminates ambiguity
5. **Start every session with:** "Read AGENT_BOOT.md"
