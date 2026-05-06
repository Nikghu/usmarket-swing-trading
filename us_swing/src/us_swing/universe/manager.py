"""Module: MD-INF-002.001.M01 — universe/manager.py
Parent SRD: SRD-INF-002.001 – SRD-INF-002.004

UniverseManager maintains the S&P 500 constituent list, loading it from
the database and refreshing it from the Wikipedia source on demand or on
a weekly asyncio schedule.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime

from us_swing.config.settings import UniverseConfig
from us_swing.data.models import UniverseRecord
from us_swing.db.manager import DatabaseManager

log = logging.getLogger(__name__)

_SYMBOL_PATTERN = re.compile(r"^[A-Z]{1,5}$")


@dataclass
class RefreshResult:
    """Summary of a universe refresh operation."""
    added:   int
    removed: int
    total:   int


class UniverseManager:
    """S&P 500 universe CRUD and scheduled refresh.

    Args:
        db:  :class:`DatabaseManager` with schema already created.
        cfg: :class:`UniverseConfig` (source URL, refresh interval).
    """

    def __init__(self, db: DatabaseManager, cfg: UniverseConfig) -> None:
        self._db  = db
        self._cfg = cfg
        self._task: asyncio.Task | None = None

    # ── Load ──────────────────────────────────────────────────────────────────

    def load_universe(self) -> list[UniverseRecord]:
        """Return all universe records from the database.

        Returns an empty list (not an error) if the table is empty.
        """
        return self._db.fetch_universe()

    # ── Refresh ───────────────────────────────────────────────────────────────

    async def refresh_universe(self) -> RefreshResult:
        """Download the S&P 500 list and upsert into the database.

        Returns:
            :class:`RefreshResult` with added/removed/total counts.
        """
        import pandas as pd  # deferred: not needed at import time

        log.info("UniverseManager: refresh started from %s", self._cfg.source_url)
        before = {r.symbol for r in self._db.fetch_universe()}

        try:
            tables = pd.read_html(self._cfg.source_url, attrs={"id": "constituents"})
            df = tables[0]
        except Exception as exc:
            log.error("UniverseManager: fetch failed — %s", exc)
            raise

        # Normalise column names (Wikipedia table headers vary slightly)
        col_map = {
            "Symbol": "symbol",
            "Security": "name",
            "GICS Sector": "sector",
        }
        df = df.rename(columns=col_map)[["symbol", "name", "sector"]]

        records: list[UniverseRecord] = []
        for _, row in df.iterrows():
            try:
                rec = self._validate_record(str(row["symbol"]), str(row["name"]), str(row["sector"]))
                records.append(rec)
            except ValueError as exc:
                log.warning("UniverseManager: skipping invalid record — %s", exc)

        self._db.upsert_universe(records)

        after = {r.symbol for r in records}
        result = RefreshResult(
            added   = len(after - before),
            removed = len(before - after),
            total   = len(after),
        )
        log.info(
            "UniverseManager: refresh done — total=%d added=%d removed=%d",
            result.total, result.added, result.removed,
        )
        return result

    # ── Scheduler ─────────────────────────────────────────────────────────────

    async def schedule_refresh(self) -> None:
        """Start a persistent asyncio task that refreshes every N days.

        If ``refresh_interval_days == 0`` the scheduler is disabled.
        """
        if self._cfg.refresh_interval_days <= 0:
            log.info("UniverseManager: periodic refresh disabled (interval=0)")
            return
        interval_s = self._cfg.refresh_interval_days * 86_400
        self._task = asyncio.create_task(self._refresh_loop(interval_s))
        log.info("UniverseManager: scheduled refresh every %d days", self._cfg.refresh_interval_days)

    # ── Internals ─────────────────────────────────────────────────────────────

    async def _refresh_loop(self, interval_s: float) -> None:
        while True:
            await asyncio.sleep(interval_s)
            try:
                await self.refresh_universe()
            except Exception:
                log.exception("UniverseManager: scheduled refresh failed")

    @staticmethod
    def _validate_record(symbol: str, name: str, sector: str) -> UniverseRecord:
        symbol = symbol.strip().upper()
        name   = name.strip()
        sector = sector.strip()
        if not symbol or not _SYMBOL_PATTERN.match(symbol):
            raise ValueError(f"Invalid symbol: '{symbol}'")
        if not name:
            raise ValueError(f"Empty name for symbol '{symbol}'")
        if not sector:
            raise ValueError(f"Empty sector for symbol '{symbol}'")
        return UniverseRecord(symbol=symbol, name=name, sector=sector)
