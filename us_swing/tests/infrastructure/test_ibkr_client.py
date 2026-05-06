"""Unit tests — MD-INF-001.001.M01 IBKRClient.

Refs: UT-INF-001.001.M01.T01 – T05
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from us_swing.broker.client import IBKRClient, _backoff
from us_swing.data.models import ConnectionStatus
from us_swing.exceptions import BrokerConnectionError


def _make_mock_ib(*, connect_slow: bool = False) -> tuple[MagicMock, MagicMock]:
    """Return (mock_ib_module_IB_class, mock_ib_instance)."""
    mock_instance = MagicMock()
    mock_instance.isConnected = MagicMock(return_value=True)
    mock_instance.reqAccountSummaryAsync = AsyncMock(return_value=[])
    mock_instance.disconnectedEvent = MagicMock()
    mock_instance.client = MagicMock(host="127.0.0.1", port=7497, clientId=1)

    if connect_slow:
        async def _hang(*_args, **_kwargs) -> None:
            await asyncio.sleep(100)
        mock_instance.connectAsync = AsyncMock(side_effect=_hang)
    else:
        mock_instance.connectAsync = AsyncMock(return_value=None)

    mock_ib_class = MagicMock(return_value=mock_instance)
    return mock_ib_class, mock_instance


async def test_T01_connect_calls_connectAsync_with_correct_args() -> None:
    """UT-INF-001.001.M01.T01 — connect() calls IB.connectAsync with correct host/port/clientId."""
    mock_ib_class, mock_instance = _make_mock_ib()
    with patch("ib_insync.IB", mock_ib_class):
        client = IBKRClient()
        await client.connect("127.0.0.1", 7497, 1)
    mock_instance.connectAsync.assert_called_once_with("127.0.0.1", 7497, clientId=1)


def test_T02_is_connected_false_before_connect() -> None:
    """UT-INF-001.001.M01.T02 — is_connected() is False on a fresh IBKRClient."""
    client = IBKRClient()
    assert client.is_connected() is False


async def test_T03_connect_raises_on_timeout() -> None:
    """UT-INF-001.001.M01.T03 — connect() raises BrokerConnectionError when IB hangs."""
    mock_ib_class, _ = _make_mock_ib(connect_slow=True)
    with patch("ib_insync.IB", mock_ib_class):
        client = IBKRClient()
        with pytest.raises(BrokerConnectionError):
            await client.connect("127.0.0.1", 7497, 1, timeout=0.05)


async def test_T04_status_callback_fires_on_disconnect() -> None:
    """UT-INF-001.001.M01.T04 — on_status_change callback fires with DISCONNECTED."""
    client = IBKRClient()
    received: list[ConnectionStatus] = []
    client.on_status_change(received.append)
    client._connected = True
    client._ib = MagicMock()
    client._ib.client = MagicMock(host="127.0.0.1", port=7497, clientId=1)

    with patch("asyncio.ensure_future"):      # prevent reconnect loop from starting
        client._on_disconnect()

    assert ConnectionStatus.DISCONNECTED in received


def test_T05_reconnect_backoff_sequence() -> None:
    """UT-INF-001.001.M01.T05 — backoff delays ≈ [2, 4, 8] (within 10%)."""
    expected = [2.0, 4.0, 8.0]
    for attempt, exp in enumerate(expected, start=1):
        actual = _backoff(attempt)
        assert abs(actual - exp) / exp < 0.10, f"attempt={attempt}: {actual} not near {exp}"
