"""
Script: qualify_sp500_ibkr.py
══════════════════════════════════════════════════════════════════════════════
Scrapes the S&P 500 ticker list from Wikipedia, qualifies all contracts
against IBKR TWS / Gateway, and writes a CSV with conid + primary exchange.

Usage
─────
    python -m us_swing.scripts.qualify_sp500_ibkr [--host 127.0.0.1] [--port 7497] [--client-id 99]

Output
──────
    ~/.usswing/sp500_ibkr.csv   — Symbol, IbkrSymbol, conid, PrimaryExch

Requirements
────────────
    - IBKR TWS or Gateway must be running on the specified host:port.
    - Paper or live mode both work; no orders are placed.
    - ib_insync must be installed  (pip install ib_insync).

Notes
─────
    Dots in tickers are replaced with spaces before qualification
    (e.g. BRK.B → BRK B) as IBKR uses spaces as the separator for
    share-class suffixes.

    The script qualifies contracts in batches of 50 with a 1-second
    pause between batches to avoid TWS pacing violations.
"""
from __future__ import annotations

import argparse
import csv
import logging
import sys
import time
from pathlib import Path

log = logging.getLogger(__name__)

_APP_DIR  = Path.home() / ".usswing"
_OUT_CSV  = _APP_DIR / "sp500_ibkr.csv"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Qualify S&P 500 contracts against IBKR TWS")
    p.add_argument("--host",      default="127.0.0.1", help="TWS / Gateway host (default: 127.0.0.1)")
    p.add_argument("--port",      type=int, default=7497, help="TWS port: 7497=paper, 7496=live (default: 7497)")
    p.add_argument("--client-id", type=int, default=99,   help="IBKR client ID (default: 99)")
    p.add_argument("--force",     action="store_true",    help="Re-download Wikipedia ticker list even if cache is fresh")
    return p.parse_args()


def _load_tickers(force: bool) -> list[tuple[str, str]]:
    """Return list of (original_symbol, ibkr_symbol) tuples from universe.store."""
    # Import here to keep the script self-contained when run directly
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from us_swing.universe.store import load_sp500
    records = load_sp500(force_refresh=force)
    return [(r.symbol, r.ibkr_symbol) for r in records]


def _qualify_all(
    tickers: list[tuple[str, str]],
    host: str,
    port: int,
    client_id: int,
) -> list[dict]:
    """Connect to TWS, qualify all Stock contracts, return list of result dicts."""
    try:
        from ib_insync import IB, Stock
    except ImportError:
        log.error("ib_insync is not installed. Run: pip install ib_insync")
        sys.exit(1)

    ib = IB()
    log.info("Connecting to TWS at %s:%d (client_id=%d) …", host, port, client_id)
    ib.connect(host, port, clientId=client_id, timeout=10)
    log.info("Connected. Qualifying %d contracts …", len(tickers))

    results: list[dict] = []
    batch_size = 50

    for batch_start in range(0, len(tickers), batch_size):
        batch = tickers[batch_start: batch_start + batch_size]
        contracts = [Stock(ibkr_sym, "SMART", "USD") for _, ibkr_sym in batch]

        try:
            qualified = ib.qualifyContracts(*contracts)
        except Exception as exc:
            log.warning("Batch %d failed: %s — skipping", batch_start // batch_size, exc)
            qualified = []

        sym_map = {ibkr_sym: orig for orig, ibkr_sym in batch}
        for c in qualified:
            if c.conId:
                results.append({
                    "Symbol":      sym_map.get(c.symbol, c.symbol),
                    "IbkrSymbol":  c.symbol,
                    "conid":       str(c.conId),
                    "PrimaryExch": c.primaryExch or "",
                })

        done = min(batch_start + batch_size, len(tickers))
        log.info("  … %d / %d qualified so far", done, len(tickers))

        if batch_start + batch_size < len(tickers):
            time.sleep(1)   # pacing: avoid TWS rate limits

    ib.disconnect()
    log.info("Disconnected. Total qualified: %d / %d", len(results), len(tickers))
    return results


def _save_csv(rows: list[dict]) -> None:
    _APP_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _OUT_CSV.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Symbol", "IbkrSymbol", "conid", "PrimaryExch"])
        w.writeheader()
        w.writerows(rows)
    tmp.replace(_OUT_CSV)
    log.info("Saved %d rows → %s", len(rows), _OUT_CSV)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    args = _parse_args()

    tickers = _load_tickers(args.force)
    log.info("Loaded %d tickers from sp500_store (first: %s)", len(tickers), tickers[0] if tickers else "–")

    rows = _qualify_all(tickers, args.host, args.port, args.client_id)

    if not rows:
        log.error("No contracts were qualified. Check TWS connectivity and pacing settings.")
        sys.exit(1)

    _save_csv(rows)
    print(f"\n✔  Qualified {len(rows)} contracts → {_OUT_CSV}")


if __name__ == "__main__":
    main()
