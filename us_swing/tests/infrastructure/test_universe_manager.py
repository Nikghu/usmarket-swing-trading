"""Unit tests — MD-INF-002.001.M01 UniverseManager.

Refs: UT-INF-002.001.M01.T01 – T04
"""
from __future__ import annotations

import logging
from unittest.mock import patch

import pandas as pd
import pytest

from us_swing.config.settings import UniverseConfig
from us_swing.data.models import UniverseRecord
from us_swing.db.manager import DatabaseManager
from us_swing.universe.manager import UniverseManager


def _make_manager(db: DatabaseManager) -> UniverseManager:
    cfg = UniverseConfig(refresh_interval_days=0, source_url="http://fake.url")
    return UniverseManager(db, cfg)


def _make_wiki_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame({
        "Symbol":     [r["symbol"]  for r in rows],
        "Security":   [r["name"]    for r in rows],
        "GICS Sector":[r["sector"]  for r in rows],
    })


def test_T01_load_universe_returns_seeded_records(in_memory_db: DatabaseManager) -> None:
    """UT-INF-002.001.M01.T01 — load_universe() returns all records from DB."""
    records = [
        UniverseRecord("AAPL", "Apple", "IT"),
        UniverseRecord("MSFT", "Microsoft", "IT"),
        UniverseRecord("AMZN", "Amazon", "Consumer"),
    ]
    in_memory_db.upsert_universe(records)
    mgr = _make_manager(in_memory_db)
    result = mgr.load_universe()
    assert len(result) == 3
    symbols = {r.symbol for r in result}
    assert symbols == {"AAPL", "MSFT", "AMZN"}


def test_T02_load_universe_empty_table(in_memory_db: DatabaseManager) -> None:
    """UT-INF-002.001.M01.T02 — load_universe() returns [] if universe table is empty."""
    mgr = _make_manager(in_memory_db)
    assert mgr.load_universe() == []


async def test_T03_refresh_universe_upserts_correctly(in_memory_db: DatabaseManager) -> None:
    """UT-INF-002.001.M01.T03 — refresh_universe() upserts all valid records."""
    existing = [
        UniverseRecord("AAPL", "Apple Old", "IT"),
        UniverseRecord("MSFT", "Microsoft Old", "IT"),
    ]
    in_memory_db.upsert_universe(existing)

    wiki_rows = [
        {"symbol": "AAPL",  "name": "Apple",     "sector": "IT"},
        {"symbol": "MSFT",  "name": "Microsoft",  "sector": "IT"},
        {"symbol": "GOOGL", "name": "Alphabet",   "sector": "IT"},
        {"symbol": "AMZN",  "name": "Amazon",     "sector": "Consumer"},
        {"symbol": "TSLA",  "name": "Tesla",      "sector": "Automotive"},
    ]
    mock_df = _make_wiki_df(wiki_rows)
    mgr = _make_manager(in_memory_db)

    with patch("pandas.read_html", return_value=[mock_df]):
        result = await mgr.refresh_universe()

    assert result.total == 5
    loaded = in_memory_db.fetch_universe()
    assert len(loaded) == 5


async def test_T04_malformed_record_skipped_with_warning(
    in_memory_db: DatabaseManager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """UT-INF-002.001.M01.T04 — empty symbol is skipped; WARNING logged; others inserted."""
    wiki_rows = [
        {"symbol": "AAPL", "name": "Apple",     "sector": "IT"},
        {"symbol": "",     "name": "BadRecord",  "sector": "IT"},
        {"symbol": "MSFT", "name": "Microsoft",  "sector": "IT"},
    ]
    mock_df = _make_wiki_df(wiki_rows)
    mgr = _make_manager(in_memory_db)

    with caplog.at_level(logging.WARNING), patch("pandas.read_html", return_value=[mock_df]):
        await mgr.refresh_universe()

    loaded = in_memory_db.fetch_universe()
    symbols = {r.symbol for r in loaded}
    assert "" not in symbols
    assert {"AAPL", "MSFT"} <= symbols
    assert any("skipping" in r.message.lower() for r in caplog.records)
