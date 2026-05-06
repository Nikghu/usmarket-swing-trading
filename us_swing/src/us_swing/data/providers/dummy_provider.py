"""Module: MD-INF-007.001.M02 — data/providers/dummy_provider.py
Parent SRD: SRD-INF-007.003, SRD-INF-007.005

DummyProvider generates synthetic OHLCV bars using a seeded random walk.
All bars satisfy the same structural constraints as real bars:
    ``low <= open, close, high``   and   ``volume >= 0``.

Realtime-bar simulation emits synthetic bars on a configurable timer
(default 5 s), allowing the live engine to be tested without IBKR.
"""
from __future__ import annotations

import asyncio
import logging
import math
import random
from collections.abc import Callable
from datetime import datetime, timedelta

from us_swing.data.models import OHLCVBar, RealtimeBar

log = logging.getLogger(__name__)

_MINUTES_PER_SESSION = 390   # 9:30–16:00 ET
_DEFAULT_REALTIME_INTERVAL_S = 5.0


class DummyProvider:
    """Synthetic data provider for development and testing.

    Args:
        seed:          Random seed for reproducible output.
        base_price:    Starting price for the random walk.
        volatility:    Daily-return standard deviation (e.g. ``0.02`` = 2%).
        realtime_interval_s: Seconds between synthetic realtime bars.
    """

    def __init__(
        self,
        seed: int = 42,
        base_price: float = 200.0,
        volatility: float = 0.02,
        realtime_interval_s: float = _DEFAULT_REALTIME_INTERVAL_S,
    ) -> None:
        self._seed       = seed
        self._base_price = base_price
        self._volatility = volatility
        self._rt_interval_s = realtime_interval_s
        self._rt_callbacks: list[Callable[[RealtimeBar], None]] = []
        self._rt_tasks: dict[str, asyncio.Task] = {}
        self._last_prices: dict[str, float] = {}

    # ── DataProvider interface ────────────────────────────────────────────────

    async def req_historical_data(
        self,
        symbol: str,
        end_datetime: datetime,
        duration: str,
        bar_size: str,
    ) -> list[OHLCVBar]:
        """Return a synthetic OHLCV bar series deterministic on (seed, symbol)."""
        rng = random.Random(self._seed + hash(symbol) % (2 ** 31))
        n_bars, delta = self._parse_request(duration, bar_size)
        tf  = self._bar_size_to_tf(bar_size)
        price = self._base_price
        bars: list[OHLCVBar] = []

        for i in range(n_bars):
            dt    = end_datetime - delta * (n_bars - i)
            price = self._next_price(rng, price, tf)
            bar   = self._make_bar(rng, symbol, dt, price, tf)
            bars.append(bar)
            self._last_prices[symbol] = bar.close

        return bars

    def subscribe_realtime_bars(self, symbol: str, bar_size: int = 5) -> None:
        if symbol in self._rt_tasks:
            return
        self._rt_tasks[symbol] = asyncio.ensure_future(
            self._emit_loop(symbol)
        )
        log.debug("DummyProvider: subscribed realtime bars for %s", symbol)

    def unsubscribe_realtime_bars(self, symbol: str) -> None:
        task = self._rt_tasks.pop(symbol, None)
        if task:
            task.cancel()
            log.debug("DummyProvider: unsubscribed realtime bars for %s", symbol)

    def on_realtime_bar(self, callback: Callable[[RealtimeBar], None]) -> None:
        self._rt_callbacks.append(callback)

    # ── Internals ─────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_request(duration: str, bar_size: str) -> tuple[int, timedelta]:
        """Convert IBKR-style duration/bar_size strings → (n_bars, timedelta)."""
        bar_deltas: dict[str, timedelta] = {
            "1 min":   timedelta(minutes=1),
            "1 day":   timedelta(days=1),
            "1 week":  timedelta(weeks=1),
            "3 mins":  timedelta(minutes=3),
            "5 mins":  timedelta(minutes=5),
            "15 mins": timedelta(minutes=15),
            "1 hour":  timedelta(hours=1),
            "4 hours": timedelta(hours=4),
        }
        delta = bar_deltas.get(bar_size, timedelta(days=1))

        parts = duration.split()
        qty   = int(parts[0]) if parts else 1
        unit  = parts[1].upper() if len(parts) > 1 else "D"

        if "Y" in unit:
            n_bars = int(qty * 252) if "day" in bar_size else int(qty * 252 * _MINUTES_PER_SESSION)
        elif "M" in unit and "min" not in bar_size:
            n_bars = int(qty * 21)
        elif "D" in unit and "day" not in bar_size:
            n_bars = int(qty * _MINUTES_PER_SESSION)
        else:
            n_bars = qty

        return max(1, n_bars), delta

    def _next_price(self, rng: random.Random, price: float, tf: str) -> float:
        """Geometric Brownian Motion step scaled to the timeframe."""
        scale = {"1m": 1 / 390, "1d": 1.0, "1w": 5.0}.get(tf, 1.0)
        daily_vol = self._volatility * math.sqrt(scale)
        return price * math.exp(rng.gauss(0, daily_vol))

    def _make_bar(
        self, rng: random.Random, symbol: str, dt: datetime, close: float, tf: str
    ) -> OHLCVBar:
        spread = close * self._volatility * 0.3
        open_  = close * math.exp(rng.gauss(0, self._volatility * 0.1))
        high   = max(open_, close) + abs(rng.gauss(0, spread))
        low    = min(open_, close) - abs(rng.gauss(0, spread))
        volume = max(0, int(rng.gauss(500_000, 150_000)))
        return OHLCVBar(
            symbol=symbol,
            datetime=dt,
            open=round(open_, 2),
            high=round(high, 2),
            low=round(low, 2),
            close=round(close, 2),
            volume=volume,
            timeframe=tf,
        )

    async def _emit_loop(self, symbol: str) -> None:
        rng = random.Random(self._seed + hash(symbol + "rt") % (2 ** 31))
        price = self._last_prices.get(symbol, self._base_price)
        while True:
            await asyncio.sleep(self._rt_interval_s)
            price = self._next_price(rng, price, "1m")
            bar = self._make_bar(rng, symbol, datetime.utcnow(), price, "1m")
            rtb = RealtimeBar(
                symbol=symbol,
                datetime=bar.datetime,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
            )
            for cb in self._rt_callbacks:
                try:
                    cb(rtb)
                except Exception:
                    log.exception("DummyProvider: realtime callback error")

    @staticmethod
    def _bar_size_to_tf(bar_size: str) -> str:
        mapping = {
            "1 min": "1m", "1 day": "1d", "1 week": "1w",
            "3 mins": "3m", "5 mins": "5m", "15 mins": "15m",
            "1 hour": "1h", "4 hours": "4h",
        }
        return mapping.get(bar_size, "1d")
