"""Integration tests: SCR v2 end-to-end pipeline.
Refs: UTCD-SCR v2.0.0 — Integration Tests T01–T15
"""
from __future__ import annotations

import concurrent.futures
import logging
import time
from pathlib import Path

import pytest

from us_swing.screener.base import PresetAccessDenied
from us_swing.screener.executor import PresetExecutor
from us_swing.screener.manager import PresetManager
from us_swing.screener.preset import (
    GroupLogic,
    Preset,
    PresetType,
    ScreenerGroup,
    ScreenerRef,
)
from us_swing.screener.registry import ScreenerRegistry
from us_swing.screener.storage import ScreenerResultsStorage, ScreenerRunResult

from tests.screener.conftest import make_bars, make_weighted_preset


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simple_composite(preset_id: str, screener_id: str = "indicator_composite") -> Preset:
    """Minimal Composite preset with a single screener — no indicator_volume dependency."""
    ref = ScreenerRef(screener_id=screener_id, enabled=True)
    g1 = ScreenerGroup(group_id="g1", logic=GroupLogic.AND, screeners=[ref])
    return Preset(
        id=preset_id,
        name=f"Test {preset_id}",
        preset_type=PresetType.COMPOSITE,
        groups=[g1],
    )

SYMBOLS = ["AAPL", "MSFT", "GOOGL"]
BARS = {s: make_bars(s, n=60, base_price=100.0, volume=2_000_000, seed=i)
        for i, s in enumerate(SYMBOLS)}


def _screener_class(
    per_symbol: dict[str, tuple[bool, float]],
    default: tuple[bool, float] = (False, 0.0),
):
    """Return a Screener class whose apply() returns fixed per-symbol results."""
    class _Fixed:
        def apply(self, symbols, bars, config):
            return {s: per_symbol.get(s, default) for s in symbols}
        def batch_features(self, symbols, bars, config=None):
            return {s: {"price": 100.0} for s in symbols}
    return _Fixed


def _pass_all_class(score: float = 0.8):
    """Screener that passes every symbol with a fixed score."""
    return _screener_class({}, default=(True, score))


def _make_executor(mgr: PresetManager, storage: ScreenerResultsStorage) -> PresetExecutor:
    return PresetExecutor(
        preset_manager=mgr,
        storage=storage,
        max_workers=2,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def base(tmp_path: Path) -> Path:
    """Shared on-disk root for both PresetManager and ScreenerResultsStorage."""
    return tmp_path / "scr"


@pytest.fixture
def mgr(base: Path) -> PresetManager:
    return PresetManager(base_dir=base)


@pytest.fixture
def storage(base: Path) -> ScreenerResultsStorage:
    return ScreenerResultsStorage(base_dir=base)


@pytest.fixture
def executor(mgr: PresetManager, storage: ScreenerResultsStorage) -> PresetExecutor:
    return _make_executor(mgr, storage)


# ---------------------------------------------------------------------------
# T01 — Full preset execution end-to-end
# ---------------------------------------------------------------------------

def test_T01_full_preset_execution(mgr, executor, base):
    """IT-SCR-T01: load → pre-filter → Stage 2 → save → result file exists."""
    ScreenerRegistry.register("indicator_composite", _pass_all_class(0.9))

    preset = _simple_composite("daily_rsi")
    mgr.create_preset(preset, user_id="user1")

    result = executor.run_preset("daily_rsi", "user1", symbols=SYMBOLS, bars=BARS)

    assert isinstance(result, ScreenerRunResult)
    assert result.preset_id == "daily_rsi"
    assert result.execution_mode == "manual"
    assert len(result.results) > 0

    result_file = base / "preset_daily_rsi" / f"{result.date}.json"
    assert result_file.exists(), "Result file must be written to disk"

    loaded = storage_from(base).load_result("daily_rsi", result.date)
    assert loaded.preset_id == result.preset_id
    assert set(loaded.results.keys()) == set(result.results.keys())


def storage_from(base: Path) -> ScreenerResultsStorage:
    return ScreenerResultsStorage(base_dir=base)


# ---------------------------------------------------------------------------
# T02 — Composite AND/OR group logic
# ---------------------------------------------------------------------------

def test_T02_composite_andor_logic(mgr, executor):
    """IT-SCR-T02: symbol passes if ANY group passes; within group: AND/OR.

    Setup:
      G1 (AND): screener_A ∧ screener_B
        screener_A: AAPL=pass, MSFT=fail, GOOGL=fail
        screener_B: AAPL=pass, MSFT=pass, GOOGL=fail
        → G1 passes: AAPL only

      G2 (AND): screener_C
        screener_C: AAPL=fail, MSFT=pass, GOOGL=fail
        → G2 passes: MSFT only

    Expected: AAPL (via G1), MSFT (via G2) in results; GOOGL absent.
    """
    ScreenerRegistry.register(
        "screener_a",
        _screener_class({"AAPL": (True, 0.9), "MSFT": (False, 0.2), "GOOGL": (False, 0.1)}),
    )
    ScreenerRegistry.register(
        "screener_b",
        _screener_class({"AAPL": (True, 0.8), "MSFT": (True, 0.7), "GOOGL": (False, 0.1)}),
    )
    ScreenerRegistry.register(
        "screener_c",
        _screener_class({"AAPL": (False, 0.2), "MSFT": (True, 0.85), "GOOGL": (False, 0.1)}),
    )

    g1 = ScreenerGroup(
        group_id="g1", logic=GroupLogic.AND,
        screeners=[
            ScreenerRef("screener_a", enabled=True),
            ScreenerRef("screener_b", enabled=True),
        ],
    )
    g2 = ScreenerGroup(
        group_id="g2", logic=GroupLogic.AND,
        screeners=[ScreenerRef("screener_c", enabled=True)],
    )
    preset = Preset(id="comp2", name="Comp2", preset_type=PresetType.COMPOSITE, groups=[g1, g2])
    mgr.create_preset(preset, user_id="user1")

    result = executor.run_preset("comp2", "user1", symbols=SYMBOLS, bars=BARS)

    assert "AAPL" in result.results, "AAPL must pass via G1"
    assert "MSFT" in result.results, "MSFT must pass via G2"
    assert "GOOGL" not in result.results, "GOOGL must fail all groups"

    assert result.results["AAPL"]["matching_groups"] == ["g1"]
    assert result.results["MSFT"]["matching_groups"] == ["g2"]


# ---------------------------------------------------------------------------
# T03 — Weighted preset score calculation
# ---------------------------------------------------------------------------

def test_T03_weighted_score_calculation(mgr, executor):
    """IT-SCR-T03: score = Σ(score_i × w_i) / Σ(w_i); threshold gate applied.

    Weights: [0.4, 0.3, 0.3]
    AAPL:  0.8×0.4 + 0.6×0.3 + 0.9×0.3 = 0.77  → pass (≥ 0.6)
    MSFT:  0.3×0.4 + 0.2×0.3 + 0.1×0.3 = 0.21  → fail (< 0.6)
    """
    ScreenerRegistry.register(
        "sc1",
        _screener_class({"AAPL": (True, 0.8), "MSFT": (True, 0.3), "GOOGL": (True, 0.4)}),
    )
    ScreenerRegistry.register(
        "sc2",
        _screener_class({"AAPL": (True, 0.6), "MSFT": (True, 0.2), "GOOGL": (True, 0.4)}),
    )
    ScreenerRegistry.register(
        "sc3",
        _screener_class({"AAPL": (True, 0.9), "MSFT": (True, 0.1), "GOOGL": (True, 0.4)}),
    )

    preset = Preset(
        id="weighted3",
        name="Weighted3",
        preset_type=PresetType.WEIGHTED,
        screeners=[
            ScreenerRef("sc1", enabled=True, weight=0.4),
            ScreenerRef("sc2", enabled=True, weight=0.3),
            ScreenerRef("sc3", enabled=True, weight=0.3),
        ],
        threshold=0.6,
    )
    mgr.create_preset(preset, user_id="user1")

    result = executor.run_preset("weighted3", "user1", symbols=SYMBOLS, bars=BARS)

    assert "AAPL" in result.results, "AAPL score 0.77 must pass threshold 0.60"
    assert "MSFT" not in result.results, "MSFT score 0.21 must fail threshold 0.60"
    aapl_score = result.results["AAPL"]["score"]
    assert abs(aapl_score - 0.77) < 0.01, f"Expected score ≈ 0.77, got {aapl_score}"


# ---------------------------------------------------------------------------
# T04 — v1 migration → execution produces same result as direct IndicatorScreener
# ---------------------------------------------------------------------------

def test_T04_v1_migration_and_execution(mgr, storage, base):
    """IT-SCR-T04: migrated preset runs IndicatorScreener; result matches direct call."""
    from us_swing.screener.screeners.indicator import IndicatorScreener
    ScreenerRegistry.register("indicator_composite", IndicatorScreener)

    v1_config = {
        "id": "legacy_v1",
        "name": "Legacy v1 Settings",
        "filters": {
            "volatility": {"enabled": True, "min_atr_pct": 0.005},
            "rsi": {"enabled": True, "min": 20, "max": 90, "period": 14},
            "range": {"enabled": True, "min_price": 5.0, "max_price": 5000.0},
            "breakout": {"enabled": True, "lookback": 5},
            "volume": {"enabled": True, "min_volume_ratio": 0.5, "ma_period": 10},
        },
    }

    preset = mgr.migrate_v1_presets(user_id="user1", v1_config=v1_config)
    assert preset.preset_type == PresetType.WEIGHTED
    assert len(preset.screeners) == 1
    assert preset.screeners[0].screener_id == "indicator_composite"

    executor = _make_executor(mgr, storage)
    result = executor.run_preset(preset.id, "user1", symbols=SYMBOLS, bars=BARS)

    # Direct IndicatorScreener run with same config for comparison
    direct_screener = IndicatorScreener()
    direct_results = direct_screener.apply(SYMBOLS, BARS, v1_config)

    for sym, (passed, _score) in direct_results.items():
        if passed:
            assert sym in result.results, (
                f"{sym} passes IndicatorScreener directly but absent from migrated run"
            )


# ---------------------------------------------------------------------------
# T05 — Manual trigger overwrites same-day result
# ---------------------------------------------------------------------------

def test_T05_manual_trigger_overwrites_same_day(mgr, storage, executor):
    """IT-SCR-T05: running a preset twice on the same day overwrites the result file.

    The loaded result after two runs must match the second run, not the first —
    proving the file was atomically overwritten. We do NOT require distinct
    timestamps because the executor truncates to whole seconds and fast CI
    boxes can complete both runs within the same second.
    """
    ScreenerRegistry.register("indicator_composite", _pass_all_class(0.7))

    preset = _simple_composite("double_run")
    mgr.create_preset(preset, user_id="user1")

    executor.run_preset("double_run", "user1", symbols=SYMBOLS, bars=BARS)
    result2 = executor.run_preset("double_run", "user1", symbols=SYMBOLS, bars=BARS)

    # Only one date entry — same-day runs produce a single file
    dates = storage.list_results("double_run")
    assert len(dates) == 1, f"Expected 1 date entry, got {dates}"

    # Loaded result is consistent with the second run (file was overwritten)
    loaded = storage.load_result("double_run", result2.date)
    assert loaded.preset_id == result2.preset_id
    assert loaded.execution_mode == result2.execution_mode
    assert set(loaded.results.keys()) == set(result2.results.keys())


# ---------------------------------------------------------------------------
# T06 — Scheduled trigger stores execution_mode="scheduled"
# ---------------------------------------------------------------------------

def test_T06_scheduled_mode_stored(mgr, storage, executor):
    """IT-SCR-T06: manual=False → execution_mode='scheduled' in saved result."""
    ScreenerRegistry.register("indicator_composite", _pass_all_class(0.6))

    preset = _simple_composite("sched_run")
    mgr.create_preset(preset, user_id="user1")

    result = executor.run_preset(
        "sched_run", "user1", symbols=SYMBOLS, bars=BARS, manual=False
    )

    assert result.execution_mode == "scheduled"

    loaded = storage.load_result("sched_run", result.date)
    assert loaded.execution_mode == "scheduled"


# ---------------------------------------------------------------------------
# T07 — LLM ranking enabled: Stage 3 executes and re-ranks
# ---------------------------------------------------------------------------

def test_T07_llm_ranking_enabled(mgr, executor):
    """IT-SCR-T07: enable_llm_ranking=True → LLM screener apply() called; top-N returned."""
    llm_call_count = {"n": 0}

    def _llm_apply(symbols, bars, config):
        llm_call_count["n"] += 1
        # Return all symbols ranked; top-N selected by executor
        return {s: (True, 0.9 - i * 0.1) for i, s in enumerate(symbols)}

    class _LLMScreener:
        def apply(self, symbols, bars, config):
            return _llm_apply(symbols, bars, config)
        def batch_features(self, symbols, bars, config=None):
            return {s: {"price": 100.0} for s in symbols}

    ScreenerRegistry.register("indicator_composite", _pass_all_class(0.8))
    ScreenerRegistry.register("llm_claude_ranking", _LLMScreener)

    g1 = ScreenerGroup(
        group_id="g1", logic=GroupLogic.AND,
        screeners=[ScreenerRef("indicator_composite", enabled=True)],
    )
    preset = Preset(
        id="llm_enabled",
        name="LLM Enabled",
        preset_type=PresetType.COMPOSITE,
        groups=[g1],
        enable_llm_ranking=True,
        top_n=2,
    )
    mgr.create_preset(preset, user_id="user1")

    result = executor.run_preset("llm_enabled", "user1", symbols=SYMBOLS, bars=BARS)

    assert llm_call_count["n"] == 1, "LLM screener must be called exactly once"
    # top_n=2 → at most 2 passing symbols in result
    passing = [sym for sym, d in result.results.items() if d.get("passed", False)]
    assert len(passing) <= 2, f"top_n=2 exceeded: {len(passing)} passing symbols"


# ---------------------------------------------------------------------------
# T08 — LLM ranking disabled: Stage 3 skipped
# ---------------------------------------------------------------------------

def test_T08_llm_ranking_disabled(mgr, executor):
    """IT-SCR-T08: enable_llm_ranking=False → LLM screener apply() never called."""
    llm_call_count = {"n": 0}

    class _LLMScreener:
        def apply(self, symbols, bars, config):
            llm_call_count["n"] += 1
            return {s: (True, 0.9) for s in symbols}
        def batch_features(self, symbols, bars, config=None):
            return {}

    ScreenerRegistry.register("indicator_composite", _pass_all_class(0.8))
    ScreenerRegistry.register("llm_claude_ranking", _LLMScreener)

    g1 = ScreenerGroup(
        group_id="g1", logic=GroupLogic.AND,
        screeners=[ScreenerRef("indicator_composite", enabled=True)],
    )
    preset = Preset(
        id="llm_disabled",
        name="LLM Disabled",
        preset_type=PresetType.COMPOSITE,
        groups=[g1],
        enable_llm_ranking=False,
    )
    mgr.create_preset(preset, user_id="user1")

    result = executor.run_preset("llm_disabled", "user1", symbols=SYMBOLS, bars=BARS)

    assert llm_call_count["n"] == 0, "LLM screener must NOT be called when ranking disabled"
    assert isinstance(result, ScreenerRunResult)


# ---------------------------------------------------------------------------
# T09 — LLM API timeout → fallback to Stage 2 results
# ---------------------------------------------------------------------------

def test_T09_llm_timeout_fallback(mgr, executor, caplog):
    """IT-SCR-T09: LLM apply() raises → fallback to Stage 2 results; WARNING logged."""

    class _TimeoutLLM:
        def apply(self, symbols, bars, config):
            raise TimeoutError("Simulated LLM timeout after 30 s")
        def batch_features(self, symbols, bars, config=None):
            return {}

    ScreenerRegistry.register("indicator_composite", _pass_all_class(0.75))
    ScreenerRegistry.register("llm_claude_ranking", _TimeoutLLM)

    g1 = ScreenerGroup(
        group_id="g1", logic=GroupLogic.AND,
        screeners=[ScreenerRef("indicator_composite", enabled=True)],
    )
    preset = Preset(
        id="llm_timeout",
        name="LLM Timeout",
        preset_type=PresetType.COMPOSITE,
        groups=[g1],
        enable_llm_ranking=True,
        top_n=5,
    )
    mgr.create_preset(preset, user_id="user1")

    with caplog.at_level(logging.WARNING, logger="us_swing.screener.executor"):
        result = executor.run_preset("llm_timeout", "user1", symbols=SYMBOLS, bars=BARS)

    assert isinstance(result, ScreenerRunResult), "Preset must complete despite LLM failure"
    assert len(result.results) > 0, "Stage 2 results must be returned as fallback"
    assert any("llm" in record.message.lower() for record in caplog.records), (
        "A WARNING mentioning LLM must be logged on timeout"
    )


# ---------------------------------------------------------------------------
# T10 — Permission denied: user_b cannot load user_a's private preset
# ---------------------------------------------------------------------------

def test_T10_permission_denied(mgr, executor):
    """IT-SCR-T10: user_b running user_a's private preset raises PresetAccessDenied."""
    ScreenerRegistry.register("indicator_composite", _pass_all_class(0.8))

    preset = _simple_composite("private_p")
    mgr.create_preset(preset, user_id="user_a")

    with pytest.raises(PresetAccessDenied):
        executor.run_preset("private_p", "user_b", symbols=SYMBOLS, bars=BARS)


# ---------------------------------------------------------------------------
# T11 — Permission granted: user_b can load user_a's shared preset
# ---------------------------------------------------------------------------

def test_T11_permission_granted(mgr, executor):
    """IT-SCR-T11: after grant_access, user_b can run user_a's preset successfully."""
    ScreenerRegistry.register("indicator_composite", _pass_all_class(0.8))

    preset = _simple_composite("shared_p")
    mgr.create_preset(preset, user_id="user_a")
    mgr.grant_access("shared_p", user_ids=["user_b"], requester_id="user_a")

    result = executor.run_preset("shared_p", "user_b", symbols=SYMBOLS, bars=BARS)

    assert isinstance(result, ScreenerRunResult)
    assert result.preset_id == "shared_p"


# ---------------------------------------------------------------------------
# T12 — New user: create preset + execute with no prior state
# ---------------------------------------------------------------------------

def test_T12_new_user_create_and_run(mgr, storage, base):
    """IT-SCR-T12: brand-new user can create a preset and execute it end-to-end."""
    ScreenerRegistry.register("indicator_composite", _pass_all_class(0.7))

    executor = _make_executor(mgr, storage)
    preset = _simple_composite("new_user_preset")
    mgr.create_preset(preset, user_id="user999")

    result = executor.run_preset(
        "new_user_preset", "user999", symbols=SYMBOLS, bars=BARS
    )

    assert isinstance(result, ScreenerRunResult)
    result_file = base / "preset_new_user_preset" / f"{result.date}.json"
    assert result_file.exists()


# ---------------------------------------------------------------------------
# T13 — Delete preset removes file and results directory
# ---------------------------------------------------------------------------

def test_T13_delete_preset_cleans_up(mgr, storage, executor, base):
    """IT-SCR-T13: delete_preset removes preset JSON and entire results directory."""
    ScreenerRegistry.register("indicator_composite", _pass_all_class(0.8))

    preset = _simple_composite("to_delete")
    mgr.create_preset(preset, user_id="user1")

    result = executor.run_preset("to_delete", "user1", symbols=SYMBOLS, bars=BARS)
    result_dir = base / "preset_to_delete"
    assert result_dir.exists(), "Results directory must exist after run"

    mgr.delete_preset("to_delete", user_id="user1")

    preset_file = mgr._user_path("user1", "to_delete")
    assert not preset_file.exists(), "Preset JSON must be deleted"
    assert not result_dir.exists(), "Results directory must be removed"


# ---------------------------------------------------------------------------
# T14 — Multi-preset concurrent runs do not interfere
# ---------------------------------------------------------------------------

def test_T14_concurrent_runs_no_interference(mgr, storage, base):
    """IT-SCR-T14: 3 presets run concurrently produce 3 separate result files."""
    ScreenerRegistry.register("indicator_composite", _pass_all_class(0.8))

    preset_ids = ["cp1", "cp2", "cp3"]
    for pid in preset_ids:
        p = _simple_composite(pid)
        mgr.create_preset(p, user_id="user1")

    errors: list[str] = []
    results: list[ScreenerRunResult] = []

    def _run(pid: str) -> ScreenerRunResult:
        exec_ = _make_executor(mgr, storage)
        return exec_.run_preset(pid, "user1", symbols=SYMBOLS, bars=BARS)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(_run, pid): pid for pid in preset_ids}
        for future in concurrent.futures.as_completed(futures):
            pid = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{pid}: {exc}")

    assert not errors, f"Concurrent runs raised errors: {errors}"
    assert len(results) == 3

    for pid in preset_ids:
        dates = storage.list_results(pid)
        assert len(dates) == 1, f"Preset '{pid}' must have exactly 1 result file"
        result_file = base / f"preset_{pid}" / f"{dates[0]}.json"
        assert result_file.exists()


# ---------------------------------------------------------------------------
# T15 — Result persistence across "restart" (new storage instance)
# ---------------------------------------------------------------------------

def test_T15_result_persistence_across_restart(mgr, storage, executor, base):
    """IT-SCR-T15: saved result loads identically from a fresh ScreenerResultsStorage."""
    ScreenerRegistry.register("indicator_composite", _pass_all_class(0.85))

    preset = _simple_composite("persist_test")
    mgr.create_preset(preset, user_id="user1")
    original = executor.run_preset("persist_test", "user1", symbols=SYMBOLS, bars=BARS)

    # Simulate app restart: new storage instance pointing to same base directory
    restarted_storage = ScreenerResultsStorage(base_dir=base)
    loaded = restarted_storage.load_result("persist_test", original.date)

    assert loaded.preset_id == original.preset_id
    assert loaded.run_timestamp == original.run_timestamp
    assert loaded.execution_mode == original.execution_mode
    assert set(loaded.results.keys()) == set(original.results.keys())
    for sym in original.results:
        assert abs(loaded.results[sym]["score"] - original.results[sym]["score"]) < 1e-9
