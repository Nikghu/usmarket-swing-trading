# Screener Architecture Prompt v2 — Flexible, Composable, Multi-Type Preset Framework

**Version:** 2.0.0  
**Date:** 2026-04-16  
**Status:** Planning Input (for Agent)  
**Project:** US Swing Trading System (us_swing)

---

## Executive Summary

The current screener (v1) is a fixed indicator-based filter pipeline with per-user configuration. **v2 redesigns the screener as a flexible, composable preset framework** that:

- **Supports multiple screener types** (Indicator-based, ML-based, LLM-based, Price Action, Local LLM, MCP) as plugins
- **Introduces presets as composable units** (Composite or Weighted) that combine screener types
- **Enables user-created and admin-curated presets** with sharing/permission model
- **Implements hybrid execution** (daily cron + on-demand manual)
- **Optimizes performance** (pre-filter → parallel execution → optional ranking)
- **Stores results persistently** (file-based per preset per date)

This prompt describes the **complete architectural vision** for planning implementation.

---

## Section 1: Architecture Overview

### 1.1 Core Concepts (Locked via Q&A)

**Preset Type (Q1: Locked)**
```
Two preset types, user-selectable:
├─ Composite: Boolean logic (AND/OR) combining screeners
└─ Weighted: Ensemble voting with weights and threshold
```

**Preset Structure (Q2: Locked)**
```
COMPOSITE:
├─ Groups: [Group1 (AND), Group2 (OR), ...]
├─ Each Group: [Screener1, Screener2, ...]
└─ Final Logic: Group1 OR Group2 OR ... (all groups combined via OR)
└─ Result: {symbol, passed: bool, matching_groups: [G1, G2]}

WEIGHTED:
├─ Flat screener list (no groups)
├─ Each screener: {name, weight}
├─ Combined score = Σ(screener_score × weight) / Σ(weights)
└─ Result: {symbol, score: 0.0–1.0, passed: (score ≥ threshold)}
```

**Execution Modes (Q3: Locked)**
```
├─ Scheduled Daily Batch: Configurable cron (default 08:00 EST)
├─ On-Demand Manual: User clicks "Run Now" in GUI
└─ Screener runs only on historical/daily-weekly data (no real-time ticks)
```

**Result Storage (Q4: Locked)**
```
File-based: ~/.usswing/screener_results/
├─ preset_A/
│  ├─ 2026-04-16.json (run timestamp, passed symbols, details)
│  ├─ 2026-04-15.json
│  └─ ...
└─ preset_B/
   └─ ...
```

**User Permissions (Q5: Locked)**
```
ADMIN PRESETS: System-wide, curated, read-only
USER PRESETS: Private by default, can be shared with other users
```

**Performance Optimization (Q6: Locked)**
```
Stage 1 (Quick Pre-Filter, single-threaded):
├─ Price > $5, Volume > 1M, not halted
└─ Result: 500 → ~300 symbols

Stage 2 (Parallel Execution):
├─ CPU-bound screeners: multiprocessing pool
├─ I/O-bound screeners: asyncio (LLM APIs)
└─ Result: ~300 → ~20 symbols (example)

Stage 3 (Optional LLM Ranking):
├─ Only if preset includes LLM screener (optional)
├─ Feature extraction once (batch)
├─ LLM call: rank 20 symbols → return top-N (e.g., top 5)
└─ Result: ~20 → top-5 ranked
```

**LLM as Ranking Layer (Q7: Locked)**
```
├─ LLM screener is OPTIONAL, runs AFTER filtering
├─ Processes only final results (~20 symbols)
├─ Returns ranked list with scores + reasoning
├─ User-configurable: top-N selection (e.g., top 5)
└─ Batch feature extraction (reusable, cheap)
```

---

## Section 2: Data Model

### 2.1 Preset Data Structure

```python
# User/Admin-defined preset (serializable to JSON/YAML)
class Preset:
    id: str                          # e.g., "A", "custom_rsi_ml"
    name: str                        # e.g., "RSI Momentum + ML Ensemble"
    preset_type: Literal["Composite", "Weighted"]
    
    # For Composite presets
    if preset_type == "Composite":
        groups: list[ScreenerGroup]  # Groups combined via OR
        class ScreenerGroup:
            id: str                  # e.g., "group_1"
            logic: Literal["AND", "OR"]
            screeners: list[ScreenerRef]
    
    # For Weighted presets
    elif preset_type == "Weighted":
        screeners: list[ScreenerRef]  # Flat list
        weights: dict[str, float]     # {screener_id: 0.3, ...}
        threshold: float              # score ≥ threshold to pass
    
    # Common
    created_by: str                  # "admin" or user_id
    is_admin: bool                   # if True, system-curated
    is_shared: bool                  # if True, can be granted to other users
    assigned_to: list[str]           # user_ids who have permission
    created_at: datetime
    updated_at: datetime
    description: str                 # Optional notes

class ScreenerRef:
    screener_id: str                 # e.g., "indicator_rsi_14", "ml_ensemble_v3", "llm_claude"
    screener_type: Literal["indicator", "ml", "llm_claude", "llm_local", "price_action", "mcp"]
    enabled: bool
    config: dict                     # screener-specific params (e.g., {"period": 14, "threshold": 30})
    weight: float                    # For weighted presets only
```

### 2.2 Screener Run Result

```python
class ScreenerRunResult:
    preset_id: str
    preset_type: str                 # "Composite" or "Weighted"
    run_timestamp: datetime
    execution_mode: Literal["scheduled", "manual"]
    total_symbols_screened: int
    symbols_after_prefilter: int
    passed_count: int
    
    # Results per symbol
    results: list[SymbolResult]      # [{"symbol": "AAPL", "passed": true, ...}, ...]
    
    # For Composite presets
    if preset_type == "Composite":
        results[].matching_groups: list[str]
        results[].details: dict       # {screener_id: passed/score}
    
    # For Weighted presets
    elif preset_type == "Weighted":
        results[].score: float
        results[].details: dict       # {screener_id: score}
    
    # Optional ranking (if LLM screener included)
    llm_ranking: Optional[LLMRankingResult] = None
    class LLMRankingResult:
        enabled: bool
        top_n: int
        ranked_symbols: list[RankedSymbol]
        class RankedSymbol:
            rank: int
            symbol: str
            score: float
            reasoning: str
```

### 2.3 Storage

```
~/.usswing/screener_results/
├─ presets.json                              # Index of all presets (admin + user)
├─ presets_admin/                            # Admin preset definitions
│  ├─ preset_A.json
│  ├─ preset_B.json
│  └─ ...
├─ presets_user/                             # User-created presets
│  ├─ user1/
│  │  ├─ preset_custom_1.json
│  │  └─ ...
│  └─ user2/
│     └─ ...
├─ results/
│  ├─ preset_A/
│  │  ├─ 2026-04-16.json
│  │  ├─ 2026-04-15.json
│  │  └─ ...
│  └─ preset_B/
│     └─ ...
└─ screener_cache/                          # Optional: cached features, LLM calls
   └─ features_2026-04-16.json
```

---

## Section 3: Plugin Architecture — Screener Types

### 3.1 Screener Type Classification

```
SCREENER TYPES (Plugin-based):
├─ indicator: Technical indicators (RSI, ATR, MACD, Bollinger, etc.)
├─ price_action: Price patterns (support bounce, range breakout, etc.)
├─ ml: Machine learning models (trained offline, inference only)
├─ llm_claude: Claude API calls (feature extraction → ranking)
├─ llm_local: Local LLM via ollama or similar
├─ mcp: MCP server protocols (external tools)
└─ hybrid: Combinations (not a separate type, but can nest)
```

### 3.2 Screener Protocol (Interface)

```python
class Screener(Protocol):
    """Base protocol all screener types implement."""
    
    screener_id: str                 # e.g., "indicator_rsi_14"
    screener_type: str               # one of the types above
    name: str
    
    def apply(
        self,
        symbols: list[str],
        bars: dict[str, list[OHLCVBar]],  # {symbol: [bars], ...}
        config: dict
    ) -> dict[str, tuple[bool, float]]:
        """
        Filter symbols and return scores.
        
        Args:
            symbols: list of symbol codes to screen
            bars: historical bars per symbol (dict)
            config: screener-specific parameters
        
        Returns:
            {symbol: (passed: bool, score: 0–1), ...}
        
        Raises:
            ScreenerError if data insufficient or config invalid
        """
    
    def batch_features(
        self,
        symbols: list[str],
        bars: dict[str, list[OHLCVBar]],
        config: dict
    ) -> dict[str, dict]:
        """
        Extract features for all symbols (used by LLM ranking).
        Optional; default returns empty dict.
        """
```

### 3.3 Built-In Screener Examples

```python
# Indicator screener (v1 filters, refactored as plugin)
class IndicatorScreener(Screener):
    screener_id = "indicator_composite"
    screener_type = "indicator"
    
    # Composes 5 filters: RSI, ATR, Range, Breakout, Volume
    def apply(symbols, bars, config):
        # config = {rsi_min, rsi_max, atr_period, ...}
        # returns {AAPL: (True, 0.78), MSFT: (False, 0.45), ...}

# ML screener (loads model, infers)
class MLScreener(Screener):
    screener_id = "ml_ensemble_v3"
    screener_type = "ml"
    
    def apply(symbols, bars, config):
        # config = {model_path, threshold, feature_set}
        # Feature engineering from bars
        # Model inference
        # returns {AAPL: (True, 0.92), ...}
    
    def batch_features(symbols, bars, config):
        # Extract and cache features for LLM
        # returns {AAPL: {feature1: 0.5, feature2: ...}, ...}

# Claude LLM screener (ranking layer only)
class LLMClaudeScreener(Screener):
    screener_id = "llm_claude_ranking"
    screener_type = "llm_claude"
    
    def apply(symbols, bars, config):
        # NOT used for binary pass/fail; used only in ranking stage
        # Returns: {AAPL: (True, 0.95), ...} where all pass, score = confidence
    
    def batch_features(symbols, bars, config):
        # Extract features: price, trend, momentum, volatility, support, resistance
        # returns {AAPL: {price: 150.5, trend: "up", rsi: 45, ...}, ...}
```

### 3.4 Screener Registry

```python
class ScreenerRegistry:
    """Central registry of available screeners."""
    
    _screeners: dict[str, type[Screener]] = {
        "indicator_composite": IndicatorScreener,
        "ml_ensemble_v3": MLScreener,
        "llm_claude_ranking": LLMClaudeScreener,
        "llm_local_mistral": LLMLocalScreener,
        ...
    }
    
    @classmethod
    def get(cls, screener_id: str) -> Screener:
        """Instantiate and return screener by ID."""
    
    @classmethod
    def register(cls, screener_id: str, screener_class: type[Screener]):
        """Register a new screener type (extensible)."""
    
    @classmethod
    def list_available(cls) -> dict[str, str]:
        """Return all registered screeners with descriptions."""
```

---

## Section 4: Execution Pipeline

### 4.1 Three-Stage Flow

```
PRESET EXECUTION:
├─ STAGE 1: Pre-Filter (Quick, Single-threaded)
│  ├─ Load all 500 symbols + latest 1d candles
│  ├─ Quick checks: Price > $5, Volume > 1M, not halted
│  ├─ Output: ~300 symbols pass pre-filter
│  └─ Time: <1 sec
│
├─ STAGE 2: Parallel Screener Pipeline
│  ├─ Input: 300 symbols, screeners from preset config
│  ├─ CPU-bound (ML, indicators): multiprocessing pool
│  ├─ I/O-bound (LLM APIs): asyncio
│  ├─ Composite preset: apply groups, check AND/OR logic
│  ├─ Weighted preset: sum weighted scores, check threshold
│  ├─ Output: ~20 symbols pass screening
│  └─ Time: 5–30 sec (depends on screener complexity)
│
└─ STAGE 3: Optional LLM Ranking (if enabled in preset)
   ├─ Input: 20 symbols that passed Stage 2
   ├─ Feature extraction (batch, once)
   ├─ LLM call: "Rank these 20 stocks"
   ├─ Output: Ranked list, top-N (e.g., top 5)
   └─ Time: ~500ms–2s (1 LLM call)

TOTAL TIME: <2 min for S&P 500
```

### 4.2 Execution Modes (Q3: Locked)

```
MODE 1: Scheduled Daily Batch (Cron)
├─ Default: 08:00 EST every trading day
├─ User can customize: Settings → Screener → Cron Expression
├─ Automatic: runs if user hasn't triggered manually yet
├─ Persistent: results stored, accessible in GUI

MODE 2: On-Demand Manual Trigger
├─ User clicks "Run Screener Now" in GUI
├─ Runs immediately, same day (even if cron already ran)
├─ Useful: late start, test changes, after market move
├─ Results overwrite same-day results (by timestamp)

SCHEDULER:
├─ Cron daemon listens for scheduled times
├─ On trigger: call ScreenerExecutor.run_preset(preset_id, user_id)
├─ On completion: save results to file, emit event (GUI updates)
```

### 4.3 Data Flow: End-to-End

```
USER INITIATES:
├─ (A) Manual: GUI "Run Screener Now" button
├─ (B) Scheduled: Cron job fires at 08:00 EST
│
▼
SCREENER EXECUTOR:
├─ Load preset config (admin or user)
├─ Check user permissions (is user assigned to this preset?)
├─ Load universe (S&P 500 symbols)
├─ Fetch latest candles from candles.db
│
├─ STAGE 1: Pre-Filter
│  └─ 500 symbols → ~300 pass
│
├─ STAGE 2: Parallel Execution
│  ├─ Instantiate screeners from ScreenerRegistry
│  ├─ Run screeners in parallel (multiprocessing + asyncio)
│  ├─ Collect results per screener
│  ├─ Apply preset logic (Composite: groups AND/OR; Weighted: sum scores)
│  └─ ~300 → ~20 symbols pass
│
├─ STAGE 3: LLM Ranking (optional)
│  ├─ If preset.screeners includes llm_claude or llm_local:
│  ├─ Call batch_features() on LLM screener
│  ├─ Call LLM API (Claude or local)
│  ├─ Parse ranked output
│  └─ Top-N selection (~20 → ~5)
│
▼
RESULT PERSISTENCE:
├─ Serialize ScreenerRunResult to JSON
├─ Write to: ~/.usswing/screener_results/preset_{id}/{date}.json
├─ Emit event: screener_run_completed (for GUI refresh)
│
▼
GUI UPDATE:
├─ Screener panel shows results (symbol, score, details)
├─ User can export, filter, add to watchlist
```

---

## Section 5: Module Architecture (Proposed)

### 5.1 New Modules

```
src/us_swing/screener/
├─ __init__.py
├─ config.py                    [KEEP] ScreenerConfig (v1)
├─ filters.py                   [REFACTOR] Wrap in IndicatorScreener plugin
├─ engine.py                    [REFACTOR] ScreenerEngine → PresetExecutor
├─ watchlist.py                 [KEEP] WatchlistManager (v1)
├─ preset.py                    [NEW] Preset dataclass + PresetManager
├─ screeners/
│  ├─ __init__.py
│  ├─ base.py                   [NEW] Screener protocol
│  ├─ registry.py               [NEW] ScreenerRegistry
│  ├─ indicator.py              [NEW] IndicatorScreener (refactored v1)
│  ├─ ml.py                     [NEW] MLScreener
│  ├─ llm_claude.py             [NEW] LLMClaudeScreener
│  ├─ llm_local.py              [NEW] LLMLocalScreener
│  ├─ price_action.py           [NEW] PriceActionScreener
│  └─ mcp.py                    [NEW] MCPScreener (stub)
├─ executor.py                  [NEW] PresetExecutor (orchestrator)
├─ scheduler.py                 [NEW] ScreenerScheduler (cron)
├─ storage.py                   [NEW] ScreenerResultsStorage (file I/O)
└─ utils.py                     [NEW] Shared utilities (pre-filter, parallelization)
```

### 5.2 Key Class Interfaces (Pseudo-code)

```python
# Preset Management
class PresetManager:
    def create_preset(preset: Preset, user_id: str) -> str  # returns preset_id
    def load_preset(preset_id: str, user_id: str) -> Preset
    def list_user_presets(user_id: str) -> list[Preset]
    def list_admin_presets() -> list[Preset]
    def update_preset(preset_id: str, preset: Preset, user_id: str) -> None
    def delete_preset(preset_id: str, user_id: str) -> None
    def grant_access(preset_id: str, user_ids: list[str]) -> None

# Execution
class PresetExecutor:
    def run_preset(
        preset_id: str,
        user_id: str,
        manual: bool = False
    ) -> ScreenerRunResult:
        """Main entry point: load preset, run all stages, return results."""

# Storage
class ScreenerResultsStorage:
    def save_result(result: ScreenerRunResult) -> None
    def load_result(preset_id: str, date: date) -> ScreenerRunResult
    def load_latest(preset_id: str) -> ScreenerRunResult
    def list_results(preset_id: str, limit: int = 30) -> list[ScreenerRunResult]

# Scheduling
class ScreenerScheduler:
    def schedule_preset(preset_id: str, user_id: str, cron_expr: str) -> None
    def unschedule_preset(preset_id: str) -> None
    def get_schedule(preset_id: str) -> str  # returns cron expr
    def start() -> None  # start listening for triggers
```

### 5.3 Dependencies

```
screener/preset.py
├─ data/models.py (UniverseRecord, etc.)

screener/executor.py
├─ screener/preset.py
├─ screener/registry.py
├─ screener/utils.py (pre-filter, parallelization)
├─ db/manager.py (candle data)
├─ screener/storage.py

screener/screeners/*.py (all types)
├─ base.py
├─ analysis/indicators.py (shared utility)

screener/scheduler.py
├─ screener/executor.py
├─ apscheduler (external dependency for cron)

screener/storage.py
├─ os.path, json, pathlib
```

---

## Section 6: Backward Compatibility & Migration

### 6.1 v1 → v2 Migration Path

```
EXISTING (v1):
├─ ScreenerEngine.run_scan() → list[ScanResult]
├─ ScreenerConfig stored in users.settings_json
└─ Watchlist stored in DB

NEW (v2):
├─ PresetExecutor.run_preset(preset_id) → ScreenerRunResult
├─ Presets stored in ~/.usswing/screener_results/presets_*.json
└─ Results stored in ~/.usswing/screener_results/results/

MIGRATION STRATEGY:
├─ Create "Legacy v1" admin preset from v1 settings
├─ User's v1 config → automatically mapped to new PresetManager
├─ Old results: keep in DB (read-only), don't migrate
├─ GUI: support both v1 (deprecated) and v2 UI flows
├─ Deprecation timeline: Support v1 for 2 releases, then remove
```

### 6.2 API Changes (Breaking)

```
REMOVED:
├─ ScreenerEngine.run_scan(universe, config) 
   └─ Replaced by: PresetExecutor.run_preset(preset_id, user_id)

DEPRECATED (but kept for compatibility):
├─ ScreenerConfig in users.settings_json
   └─ Migrate to: Preset in ~/.usswing/screener_results/presets_*.json

ADDED:
├─ Preset, PresetManager, ScreenerRegistry
├─ Screener protocol (all types implement)
├─ PresetExecutor, ScreenerScheduler, ScreenerResultsStorage
```

---

## Section 7: Artifact Impact & Planning Sequence

### 7.1 Documentation Updates Required

| Artifact | Change | Scope | Priority |
|----------|--------|-------|----------|
| FO-SCR | Add new objectives for preset types, execution modes, LLM ranking | +3 new FOs | High |
| SRD-SCR | Complete rewrite: preset model, screener types, permissions, scheduler | ~40 requirements | High |
| DD-SCR | Redesign: preset logic, plugin architecture, execution pipeline, storage | Major | High |
| MD-SCR | New modules (preset, executor, screeners, scheduler, storage) | +6 modules | High |
| TRACE-SCR | Update all traceability mappings | Full refresh | High |
| UTCD-SCR | New unit tests for all new modules | ~60 new tests | High |

### 7.2 Implementation Sequence (Recommended)

```
PHASE 1: Foundations (Non-blocking)
├─ [ ] Update FO-SCR v2.0 (add new objectives)
├─ [ ] Update SRD-SCR v2.0 (preset model, registry, permissions)
├─ [ ] Write DD-SCR v2.0 (design new components)
└─ Blocks: All code phases

PHASE 2: Core Plugin System
├─ [ ] screener/base.py (Screener protocol)
├─ [ ] screener/registry.py (ScreenerRegistry)
├─ [ ] screener/preset.py (Preset dataclass + PresetManager)
├─ [ ] screener/storage.py (ScreenerResultsStorage)
└─ All tests: UTCD-SCR for these modules

PHASE 3: Refactor v1 as Plugin
├─ [ ] screener/screeners/indicator.py (IndicatorScreener, refactor filters)
├─ [ ] screener/executor.py (PresetExecutor, reuse Stage 2 logic)
└─ Tests: UTCD-SCR for executor

PHASE 4: New Screener Types (Optional MVP)
├─ [ ] screener/screeners/ml.py (MLScreener stub)
├─ [ ] screener/screeners/llm_claude.py (LLMClaudeScreener)
├─ [ ] screener/scheduler.py (ScreenerScheduler)
└─ Tests: UTCD-SCR

PHASE 5: GUI Integration
├─ [ ] GUI panel: preset selection, create preset
├─ [ ] GUI panel: run preset, view results
├─ [ ] GUI panel: settings (cron schedule)
└─ Tests: integration tests

PHASE 6: Backfill & Cleanup
├─ [ ] Migrate v1 configs to v2 presets
├─ [ ] Deprecate old ScreenerEngine APIs
├─ [ ] Archive old results (optional)
└─ Tests: migration validation
```

---

## Section 8: Key Architectural Decisions & Risks

### 8.1 Decision Rationale

| Decision | Rationale | Risk |
|----------|-----------|------|
| **File-based result storage** | Lightweight, easy archive, separate from market data | Slower query (JSON vs DB); need pagination for large result sets |
| **Plugin architecture (Screener protocol)** | Extensible, decoupled screener types, easy to add new types | More indirection, harder to debug; need clear interface |
| **Preset as serializable config** | Reproducible, versionable, shareable | Migration from v1 settings; need backward compat |
| **Optional LLM ranking (Stage 3)** | Cost-effective (1 LLM call, not 500), supports ranking use case | Users expect filtering, not ranking; need clear UI labels |
| **Pre-filter optimization** | Performance: 500→300 cuts expensive screeners by 40% | Might filter out edge cases; need configurable filters |
| **Async + multiprocessing** | Utilizes both CPU and I/O resources efficiently | Complex error handling, potential deadlocks if not careful |

### 8.2 Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **v1 preset config loss during migration** | Users lose custom configs | Auto-migrate v1 settings → v2 preset; keep v1 in DB read-only |
| **LLM API rate limits** | Screener hangs if Claude API overloaded | Implement retry logic, timeout, fallback to non-ranking |
| **Pre-filter too aggressive** | Filters out winners; user complaint | Configurable pre-filter params in PresetManager; log filtered symbols |
| **Preset sharing permission bugs** | Unauthorized access to presets | Unit tests for permission checks; audit logging |
| **File storage concurrency** | Race condition if two runs write same date | Atomic write (temp file + rename); lock per preset |
| **Performance regression** | Screener slower than v1 | Benchmark Stage 1–3 against v1; optimize hot paths |

---

## Section 9: Testing Strategy (UTCD Impact)

### 9.1 New Test Coverage

```
UNIT TESTS:
├─ screener/base.py
│  └─ Screener protocol validation (abstract methods)
├─ screener/registry.py
│  └─ Register/get screeners, error handling
├─ screener/preset.py
│  └─ Preset creation, validation, serialization/deserialization
├─ screener/screeners/indicator.py
│  └─ IndicatorScreener.apply(), batch_features()
│  └─ Integration with v1 filters (ATR, RSI, etc.)
├─ screener/screeners/ml.py
│  └─ MLScreener with mock model
├─ screener/screeners/llm_claude.py
│  └─ LLMClaudeScreener with mocked Claude API
├─ screener/executor.py
│  └─ PresetExecutor.run_preset() (3 stages, logic)
│  └─ Composite and Weighted preset logic
├─ screener/storage.py
│  └─ Save/load results, concurrent writes
├─ screener/scheduler.py
│  └─ Cron scheduling, trigger simulation
└─ ~80–100 new unit tests total

INTEGRATION TESTS:
├─ End-to-end: preset → execution → storage → retrieval
├─ v1→v2 migration (legacy preset loading)
├─ Multi-preset concurrent runs (no data corruption)
└─ ~20 integration tests

PERFORMANCE TESTS:
├─ Stage 1 pre-filter: <1 sec for 500 symbols
├─ Stage 2 parallel: <30 sec for 300 symbols
├─ Stage 3 LLM: <2 sec for 20 symbols
└─ Total: <2 min E2E
```

---

## Section 10: Questions for Agent (Planning Phase)

Before implementing, clarify:

1. **MVP Scope**: Is MVP v1 refactor + Composite presets only? (defer LLM, weighted, ML?)
2. **LLM Costs**: Should we add cost tracking/alerts for Claude API usage?
3. **Feature Extraction Caching**: Cache features per symbol per day? How long?
4. **Watchlist Integration**: Should top-N from LLM ranking automatically populate watchlist?
5. **Preset Versioning**: Do presets need version history (audit trail)?
6. **Configuration Language**: YAML, JSON, or Python DSL for preset definitions?
7. **GUI Complexity**: Bootstrap with simple preset selector, or full WYSIWYG builder?
8. **Backward Compatibility**: Kill v1 ScreenerEngine, or keep for 2 releases?

---

## Conclusion

This prompt defines **v2 screener architecture** that:
- ✅ Supports multiple screener types (plugin-based)
- ✅ Enables flexible, composable presets (Composite + Weighted)
- ✅ Implements hybrid execution (cron + manual)
- ✅ Optimizes performance (3-stage pipeline)
- ✅ Stores results persistently (file-based)
- ✅ Supports multi-tenant preset sharing (admin + user)
- ✅ Maintains backward compatibility (migration path)

**Next step:** Agent uses this prompt to generate FO/SRD/DD/MD/UTCD updates and implementation plan.

---

**Document prepared by:** Senior Architecture Review  
**Date:** 2026-04-16  
**Status:** Ready for Planning Phase
