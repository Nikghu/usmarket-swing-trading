"""
Module: MD-EXE-009.001.M01 — core/monitoring_session/_enums.py
Parent SRD: SRD-EXE-009.012
"""
from __future__ import annotations

from enum import Enum


class LifecycleState(str, Enum):
    MONITORING = "MONITORING"
    ENTERED    = "ENTERED"
    SKIPPED    = "SKIPPED"
    EVICTED    = "EVICTED"
    EXITED     = "EXITED"


class TradeOrigin(str, Enum):
    SYSTEM = "system"
    MANUAL = "manual"


class Side(str, Enum):
    BUY  = "BUY"
    SELL = "SELL"
