"""Throwaway smoke test for FO-EXE-009 / FO-EXE-010 — run manually,
not pytest. Verifies the happy path end-to-end against an in-memory DB.
"""
from __future__ import annotations

import us_swing.data  # noqa: F401 — break circular-import in db package

from datetime import date

from sqlalchemy import create_engine, text

from us_swing.core.monitoring_session import (
    FillEvent,
    KeepSet,
    ReconcileCompleted,
    Side,
    SymbolEvicted,
    TradeOrigin,
    build_default_service,
)
from us_swing.db.schema import create_schema, monitoring_session


def _seed_user(engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (user_id, username, display_name, ibkr_client_id) "
                "VALUES (1, 'sys', 'System', 11)"
            )
        )


def _seed_price_rows(engine, symbol: str, n: int = 3) -> None:
    with engine.begin() as conn:
        for tf in ("price_1m", "price_3m", "price_15m"):
            for i in range(n):
                conn.execute(
                    text(
                        f"INSERT OR IGNORE INTO {tf} (symbol, datetime, open, high, low, close, volume) "
                        f"VALUES (:s, :dt, 1, 1, 1, 1, 1)"
                    ),
                    {"s": symbol, "dt": f"2026-05-14T09:3{i}:00"},
                )


class _FakeRun:
    def __init__(self, preset_id: str, ts: str, passed: list[str]) -> None:
        self.preset_id     = preset_id
        self.run_timestamp = ts
        self.results       = {s: {"passed": True} for s in passed}


def main() -> None:
    engine = create_engine("sqlite:///:memory:")
    create_schema(engine)
    _seed_user(engine)

    query, command, bus = build_default_service(
        engine,
        today_provider    = lambda: date(2026, 5, 14),
        filtered_provider = lambda d: frozenset({"A", "D"}) if d == date(2026, 5, 15) else frozenset({"A", "B", "C"}),
    )

    seen_events: list = []
    bus.subscribe(ReconcileCompleted, seen_events.append)
    bus.subscribe(SymbolEvicted,      seen_events.append)

    # --- Day T-1: screener emits A, B, C; system enters A ---
    keep_t1 = command.on_screener_results(_FakeRun("preset-x", "2026-05-14T13:30:00Z", ["A", "B", "C"]))
    print(f"Day T-1 keep_set: filtered={sorted(keep_t1.filtered)} carryover={sorted(keep_t1.carryover)}")
    assert keep_t1.filtered == frozenset({"A", "B", "C"})

    command.on_fill(FillEvent(
        symbol="A", trade_id="tr1", side=Side.BUY, qty=100, price=50.0,
        fill_time="2026-05-14T14:00:00", origin=TradeOrigin.SYSTEM, user_id=1,
    ))
    inv = query.check_invariant()
    print(f"After entry: invariant.ok={inv.ok} entered={sorted(query.open_system_positions())}")
    assert inv.ok and query.open_system_positions() == frozenset({"A"})

    # Seed candle rows for B and C so eviction has something to delete
    for s in ("A", "B", "C"):
        _seed_price_rows(engine, s)

    # --- Day T: reconcile.  filtered={A,D}, carryover={A} ---
    # Override today inside the service for this call by swapping providers
    query2, command2, bus2 = build_default_service(
        engine,
        today_provider    = lambda: date(2026, 5, 15),
        filtered_provider = lambda d: frozenset({"A", "D"}),
    )
    # Re-subscribe seen_events to the new bus (separate instance per build call)
    bus2.subscribe(ReconcileCompleted, seen_events.append)
    bus2.subscribe(SymbolEvicted,      seen_events.append)

    report = command2.reconcile_preopen(date(2026, 5, 15))
    print(
        f"Reconcile: filtered_n={report.filtered_n} carryover_n={report.carryover_n} "
        f"skipped_n={report.skipped_n} evicted_n={report.evicted_n} "
        f"evicted={report.evicted_symbols} errors={len(report.errors)}"
    )
    assert report.evicted_symbols == ("B", "C"), f"got {report.evicted_symbols}"

    # Check price rows for B/C are gone, A retained
    with engine.connect() as conn:
        for s, expected in (("A", 3), ("B", 0), ("C", 0)):
            for tf in ("price_1m", "price_3m", "price_15m"):
                n = conn.execute(
                    text(f"SELECT COUNT(*) FROM {tf} WHERE symbol = :s"),
                    {"s": s},
                ).scalar()
                assert n == expected, f"{s} {tf} expected {expected} got {n}"
    print("Price rows correctly retained/evicted")

    # Idempotency
    report2 = command2.reconcile_preopen(date(2026, 5, 15))
    print(f"Idempotent re-run: evicted_n={report2.evicted_n}")
    assert report2.evicted_n == 0

    # Closing exit fill
    command.on_fill(FillEvent(
        symbol="A", trade_id="tr2", side=Side.SELL, qty=100, price=55.0,
        fill_time="2026-05-15T14:00:00", origin=TradeOrigin.SYSTEM, user_id=1,
    ))
    inv = query.check_invariant()
    print(f"After exit: invariant.ok={inv.ok} entered={sorted(query.open_system_positions())}")
    assert inv.ok and query.open_system_positions() == frozenset()

    # History survives eviction
    hist_b = query.history("B", days=30)
    print(f"History for B: {len(hist_b)} row(s), state={hist_b[0].lifecycle_state.value if hist_b else 'NONE'}")
    assert len(hist_b) >= 1 and hist_b[0].lifecycle_state.value == "EVICTED"

    event_types = [type(e).__name__ for e in seen_events]
    print(f"Events received: {event_types}")
    print("ALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
