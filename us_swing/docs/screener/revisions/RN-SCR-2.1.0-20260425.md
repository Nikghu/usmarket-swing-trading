# Revision Note — Screener (SCR) v2.1.0

**Revision ID:** RN-SCR-2.1.0-20260425
**Revision Date:** 2026-04-25
**Revision Type:** Feature (Phase 1 of multi-phase rollout)
**Author:** Implementation Phase
**Status:** Draft

---

## 1. Summary

Adds **FO-SCR-011 — AI-Assisted Stock Ranking (Phase 1)**: extends the existing Stage-3 LLM ranking layer so that, after the technical filter passes ~20 symbols, an AI provider analyses them against a **user-authored natural-language query** and returns a ranked list with **per-stock reasoning (≤ 50 words)**. The AI may invoke a `get_candle_data` tool to fetch daily/weekly OHLCV on demand.

Phase 1 uses **Anthropic Claude Haiku 4.5** (`claude-haiku-4-5-20251001` snapshot, configurable via `Preset.ai_model`) and is provider-agnostic at the design level so Phase 2 (multi-provider single-choice) and Phase 3 (parallel orchestration with consensus) can extend it without rework.

---

## 2. Scope

### Functional Objective Added
- **FO-SCR-011** — AI-Assisted Stock Ranking with Tool-Augmented Reasoning (Phase 1)

### Software Requirements Added (8)
- **SRD-SCR-013.001 – 013.008** — `Preset.ai_query`/`ai_model` fields, `get_candle_data` tool, `CandleToolExecutor`, per-symbol call cap, multi-turn `tool_use` loop, executor wiring, `ai_reasoning` side-channel, GUI Query field + Reasoning column.

### Design Description Added
- **DD-SCR-011.001.D21** — AI Stock Ranking with Tool-Augmented Reasoning (Phase 1).

### Module Added
- **MD-SCR-011.001.M18** — `src/us_swing/screener/screeners/_tool_executor.py` (`CandleToolExecutor`).

### Modules Modified
| Module | File | Change |
|---|---|---|
| MD-SCR-001.001.M01 | `screener/preset.py` | Added `ai_query`, `ai_model` fields + `_validate_ai_query()` |
| MD-SCR-002.003.M06 | `screener/screeners/llm_claude.py` | Added tool-augmented multi-turn `apply()` path (legacy path preserved verbatim) |
| MD-SCR-003.001.M10 | `screener/executor.py` | Stage 3 now passes `db`, `passing_symbols`, `ai_query`, `ai_model`; merges `ai_reasoning` side-channel |
| MD-SCR-007.010.M16 | `gui/screener_panel.py` | AI Query `QLineEdit`; AI Reasoning column with truncated preview + tooltip; CSV export updated; `DatabaseManager` passed into `PresetExecutor` |

---

## 3. Files Touched

### New (3)
- `us_swing/src/us_swing/screener/screeners/_tool_executor.py` — `CandleToolExecutor` (~140 LOC)
- `us_swing/tests/screener/test_tool_executor.py` — 10 unit tests
- `us_swing/docs/screener/revisions/RN-SCR-2.1.0-20260425.md` (this file)

### Modified (8)
- `us_swing/docs/screener/FO.md` — added FO-SCR-011 (Draft)
- `us_swing/docs/screener/SRD.md` — added Section 13 with SRD-SCR-013.001–008 (Draft)
- `us_swing/docs/screener/DD.md` — added D21
- `us_swing/docs/screener/MD.md` — added M18, footer note for modified existing modules
- `us_swing/docs/screener/TRACE.md` — added FO-SCR-011 trace tree, coverage summary
- `us_swing/docs/screener/UTCD.md` — added 22 unit-test entries (T17–T20 preset, T01–T10 tool_executor, T11–T15 llm_claude, T21–T22 executor)
- `us_swing/src/us_swing/screener/preset.py` — fields + validation
- `us_swing/src/us_swing/screener/screeners/llm_claude.py` — tool-augmented path
- `us_swing/src/us_swing/screener/executor.py` — Stage 3 wiring + reasoning merge
- `us_swing/src/us_swing/gui/screener_panel.py` — AI Query field, AI Reasoning column, DB handle wiring
- `us_swing/tests/screener/test_preset.py` — T17–T20
- `us_swing/tests/screener/test_llm_claude_screener.py` — T11–T15
- `us_swing/tests/screener/test_executor.py` — T21–T22

---

## 4. Implementation Highlights

1. **Backward compatibility preserved.** Empty `ai_query` keeps the legacy single-shot ranking path verbatim — all 10 pre-existing `test_llm_claude_screener.py` tests still pass unchanged.
2. **Tool definition is provider-agnostic.** `get_candle_data` schema (`symbol`, `timeframe ∈ {1d, 1w}`, `lookback_bars ∈ [1, 300]`) maps directly to OpenAI function calling and Gemini tool use — Phase 2 will not need to redesign it.
3. **Per-symbol call cap (default 3).** Prevents runaway loops; excess returns a JSON error to the model rather than raising, so the agentic loop continues with partial data.
4. **Symbol allowlist.** Tool calls are restricted to Stage-2 passing symbols; out-of-scope calls return `symbol_not_allowed` JSON. Bounds API cost and prevents drift outside the screener's universe.
5. **Reasoning side-channel.** Public `Screener.apply()` return type unchanged (`dict[str, tuple[bool, float]]`). Reasoning is exposed via `screener.last_reasoning: dict[str, str]` and merged into `result.results[sym]["ai_reasoning"]` by `PresetExecutor`. ScreenerRunResult JSON round-trips automatically (no schema change).
6. **GUI integration.** Preset Builder gains an "AI Query" `QLineEdit` (height `C.INPUT_H`, max 500 chars, with placeholder + tooltip). Results table gains an "AI Reasoning" column with 60-char truncated preview and `Qt.ItemDataRole.ToolTipRole` tooltip showing full text. CSV export updated.
7. **DB handle wiring.** `_PresetRunWorker` instantiates `DatabaseManager(f"sqlite:///{candles.db}")` per run and threads it through `PresetExecutor(db=...)` → screener config → `CandleToolExecutor(db, allowed_symbols)`. No long-lived DB handle on the GUI thread.

---

## 5. Verification

### Unit Tests
```
$ python -m pytest us_swing/tests/screener/ -q
173 passed in 2.04 s
```

| File | Pre-Phase-1 | Post-Phase-1 | Δ |
|---|---:|---:|---:|
| test_preset.py | 16 | 20 | +4 |
| test_tool_executor.py | — | 13 (10 logical, 4 from parameterised T05) | +13 |
| test_llm_claude_screener.py | 10 | 15 | +5 |
| test_executor.py | 20 | 22 | +2 |
| **Other (unchanged)** | 103 | 103 | 0 |
| **Total** | 149 | **173** | **+24** |

### Lint / Type Checks
- `ruff check` — clean for all new code; pre-existing warnings in unrelated lines untouched.
- `mypy --strict` — clean for `preset.py`, `_tool_executor.py`, and the new sections of `executor.py`. Pre-existing strict-mode complaints (28 errors across 13 files) untouched.

### Manual Smoke Test
- **Status:** Pending. Requires a real `ANTHROPIC_API_KEY` and a populated `~/.usswing/candles.db`. Operator should:
  1. Open the Screener Panel, edit (or create) a preset.
  2. Set "AI Query" to e.g. `find bullish breakout candidates with strong momentum`.
  3. Save and click ▶ Run Now.
  4. Verify the results table populates the **AI Reasoning** column for ranked symbols.
  5. Hover over a cell to confirm the tooltip shows the full ≤50-word reasoning.

---

## 6. Definition of Done — Status

- [x] FO approved (Draft, awaiting Approved status from user)
- [x] SRD written (Draft, awaiting Approved status from user)
- [x] DD written
- [x] MD modules defined
- [x] UTCD test cases written
- [x] Code passes `ruff check` (no new warnings introduced)
- [x] All UTCD tests pass (173 / 173)
- [ ] Integration tests pass — n/a for Phase 1 (no new integration scenarios)
- [ ] MCP schema validated — n/a (FO-MCP not yet implemented)
- [x] TRACE.md updated
- [x] Revision Note written (this file)
- [ ] Commit with proper convention — pending
- [ ] `CONTEXT.md` updated — pending session-end
- [ ] `DEVLOG.md` updated — pending session-end

---

## 7. Phase 2 / 3 Forward Notes (informational)

- **Phase 2** — multi-provider single-choice (Claude / OpenAI / Gemini): refactor `_apply_with_tools()` into a provider-agnostic helper; introduce `screener/ai_ranking/` package with `AIProviderProtocol`, `AIProviderRegistry`, and provider modules. `CandleToolExecutor` is reused unchanged.
- **Phase 3** — parallel orchestration + consensus: introduce `AIRankingOrchestrator` that runs all enabled providers via `asyncio.gather()`, aggregates per-symbol scores by mean (or weighted mean), and stores per-provider reasoning in `result.results[sym]["ai_ranking"]["provider_reasoning"]`.

---

## 8. Risks & Open Questions

1. **API cost on real-world workloads.** A typical S&P 500 run with `ai_query` set will cost well under $0.01 per execution at Haiku 4.5 pricing, but operators should monitor `APIUsageTracker.get_monthly_cost()` (existing $50/month soft threshold).
2. **Model output drift.** The agentic loop trusts Claude to return a parseable JSON array. The implementation strips ``` code fences and falls back to `(passed=True, score=0.0)` for all symbols on parse failure, but malformed responses lead to ranking degradation. If observed in production, add a JSON-mode response or stricter prompt.
3. **DB schema mismatch.** `DatabaseManager` and the GUI's raw-sqlite3 candle code share the same `price_1d` / `price_1w` tables. If schemas diverge in the future, the AI tool path will fail silently (returning no bars). Add a startup sanity check in Phase 2.

---

**Approved by:** _(pending)_
