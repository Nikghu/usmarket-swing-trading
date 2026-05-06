"""Unit tests — MD-INF-001.001.M02 PacingQueue.

Refs: UT-INF-001.001.M02.T01 – T04
"""
from __future__ import annotations

import asyncio
from time import monotonic

import pytest

from us_swing.broker.pacing import PacingQueue


def test_T01_initial_available_equals_limit() -> None:
    """UT-INF-001.001.M02.T01 — 50 slots available on fresh queue."""
    q = PacingQueue(limit=50, window_s=600)
    assert q.available == 50


async def test_T02_acquire_decrements_available() -> None:
    """UT-INF-001.001.M02.T02 — acquire() once → available == 49."""
    q = PacingQueue(limit=50, window_s=600)
    await q.acquire()
    assert q.available == 49


async def test_T03_acquire_suspends_when_full() -> None:
    """UT-INF-001.001.M02.T03 — acquire() suspends when 0 slots remain."""
    q = PacingQueue(limit=5, window_s=600)
    for _ in range(5):
        await q.acquire()
    assert q.available == 0
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(q.acquire(), timeout=0.15)


def test_T04_release_expired_frees_old_slots() -> None:
    """UT-INF-001.001.M02.T04 — release_expired() purges slots older than window."""
    q = PacingQueue(limit=50, window_s=600)
    q._slots.append(monotonic() - 601)   # inject an expired slot
    assert q.available == 50             # purge happens inside .available property
    # Explicitly calling release_expired() also purges it:
    q2 = PacingQueue(limit=50, window_s=600)
    q2._slots.append(monotonic() - 601)
    q2.release_expired()
    assert q2.available == 50
