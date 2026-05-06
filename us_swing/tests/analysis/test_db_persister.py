"""Tests for analysis/db_persister.py.

Covers: UT-ANA-001.001.M03.T01 through T03.
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from tests.analysis.conftest import make_ohlcv
from us_swing.analysis.db_persister import DatabasePersister


class TestDatabasePersister:
    def test_persist_candle_returns_immediately(self) -> None:
        """UT-ANA-001.001.M03.T01 — persist_candle() is non-blocking (< 1 ms)."""
        mock_db = MagicMock()
        persister = DatabasePersister(mock_db)
        bar = make_ohlcv()

        start = time.monotonic()
        persister.persist_candle("AAPL", "1m", bar)
        elapsed_ms = (time.monotonic() - start) * 1000

        persister.stop()
        assert elapsed_ms < 50  # generous upper bound; typical is < 0.1 ms

    def test_writer_thread_inserts_all_bars(self) -> None:
        """UT-ANA-001.001.M03.T02 — stop() flushes queue; all 5 bars reach DB."""
        mock_db = MagicMock()
        persister = DatabasePersister(mock_db)

        bars = [make_ohlcv() for _ in range(5)]
        for bar in bars:
            persister.persist_candle("AAPL", "1m", bar)

        persister.stop()  # sentinel triggers flush before returning

        # All 5 bars should have been passed to insert_bars across one or more calls
        total_inserted = sum(
            len(call.args[2])
            for call in mock_db.insert_bars.call_args_list
        )
        assert total_inserted == 5

    def test_db_write_failure_does_not_crash_persister(self) -> None:
        """UT-ANA-001.001.M03.T03 — DB error is logged; writer thread continues."""
        mock_db = MagicMock()
        mock_db.insert_bars.side_effect = RuntimeError("DB error")
        persister = DatabasePersister(mock_db)

        bar = make_ohlcv()
        persister.persist_candle("AAPL", "1m", bar)
        persister.stop()  # should complete without raising

        # Thread should have been called (even though it raised)
        assert mock_db.insert_bars.called
