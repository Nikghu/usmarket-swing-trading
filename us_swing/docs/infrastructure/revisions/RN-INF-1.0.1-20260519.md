# RN-INF-1.0.1-20260519 — Infrastructure v1.0.1

**Date:** 2026-05-19
**Tool:** INF (Infrastructure)
**Version:** 1.0.1
**Type:** Bugfix

## Summary

Suppressed verbose INFO-level log output from the `ib_insync` library. After root logger configuration, the `ib_insync` logger is pinned to `WARNING` so only actionable messages (warnings and errors) appear in the log file and GUI log panel. A pre-existing unused-variable lint error (`midnight` in `_compute_next_rollover`) was also removed.

## Changed Modules

| MD ID | File | Change Description |
|---|---|---|
| MD-INF-005.001.M01 | `monitoring/logging_setup.py` | Added `logging.getLogger("ib_insync").setLevel(logging.WARNING)` after root logger setup; removed unused `midnight` variable |

## Requirements Addressed

| SRD ID | Description | Status |
|---|---|---|
| SRD-INF-005.001 | Root logger configured with daily file handler and stream handler | Draft |
| SRD-INF-005.002 | Log verbosity is configurable and third-party noise is suppressed | Draft |

## Issues Resolved

None

## Test Coverage

Pending
