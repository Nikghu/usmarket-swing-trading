# Traceability Matrix — Analysis / Live Signal Engine (ANA)

**Document ID:** TRACE-ANA
**Version:** 1.1.0
**Project:** US Swing Trading System
**Last Updated:** 2026-03-06

---

## Forward Traceability: FO → SRD → DD → MD → UTCD

| FO ID | SRD ID | DD ID | MD ID | UTCD IDs | Code File | Status |
|---|---|---|---|---|---|---|
| FO-ANA-001 | SRD-ANA-001.002–005 | DD-ANA-001.001.D01 | MD-ANA-001.001.M01 | T01–T09 | `analysis/candle_builder.py` | Draft |
| FO-ANA-001 | SRD-ANA-001.001, 004, 006 | DD-ANA-001.001.D02 | MD-ANA-001.001.M02 | — | `analysis/live_engine.py` | Draft |
| FO-ANA-001 | SRD-ANA-001.006 | DD-ANA-001.001.D02 | MD-ANA-001.001.M03 | T01–T03 | `analysis/db_persister.py` | Draft |
| FO-ANA-001/002 | SRD-SCR-001.002–006 (shared) | — | MD-ANA-001.001.M04 | T01–T04 | `analysis/indicators.py` | Draft |
| FO-ANA-002 | SRD-ANA-002.001, 007–008, 003.001–002 | DD-ANA-002.001.D01 | MD-ANA-002.001.M01 | T01–T02, 003.T01–T04 | `analysis/strategy_engine.py` | Draft |
| FO-ANA-002 | SRD-ANA-002.002 | DD-ANA-002.001.D01 | MD-ANA-002.001.M02 | T01–T02 | `analysis/strategies/breakout.py` | Draft |
| FO-ANA-002 | SRD-ANA-002.003 | DD-ANA-002.001.D01 | MD-ANA-002.001.M03 | T01–T02 | `analysis/strategies/pullback.py` | Draft |
| FO-ANA-002 | SRD-ANA-002.005–006 | DD-ANA-002.001.D01 | MD-ANA-002.001.M04 | T01–T04 | `analysis/exit_manager.py` | Draft |

---

## Reverse Traceability

| Module | MD ID | Parent SRD | Parent FO |
|---|---|---|---|
| `analysis/indicators.py` | MD-ANA-001.001.M04 | SRD-ANA (shared utility) | FO-ANA-001/002, FO-SCR-001 |
| `analysis/candle_builder.py` | MD-ANA-001.001.M01 | SRD-ANA-001.002–005 | FO-ANA-001 |
| `analysis/live_engine.py` | MD-ANA-001.001.M02 | SRD-ANA-001.001, 004, 006 | FO-ANA-001 |
| `analysis/db_persister.py` | MD-ANA-001.001.M03 | SRD-ANA-001.006 | FO-ANA-001 |
| `analysis/strategy_engine.py` | MD-ANA-002.001.M01 | SRD-ANA-002.001, 007–008, 003.001–002 | FO-ANA-002 |
| `analysis/strategies/breakout.py` | MD-ANA-002.001.M02 | SRD-ANA-002.002 | FO-ANA-002 |
| `analysis/strategies/pullback.py` | MD-ANA-002.001.M03 | SRD-ANA-002.003 | FO-ANA-002 |
| `analysis/exit_manager.py` | MD-ANA-002.001.M04 | SRD-ANA-002.005–006 | FO-ANA-002 |

---

## Status Summary

| Artifact | Total Items | Draft | Approved | Implemented | Verified |
|---|---|---|---|---|---|
| FO | 2 | 1 | 1 | 0 | 0 |
| SRD | 19 | 19 | 0 | 0 | 0 |
| DD | 3 | 3 | 0 | 0 | 0 |
| MD | 8 | 8 | 0 | 0 | 0 |
| UTCD | 28 | 28 | 0 | 0 | 0 |
| Code | 8 files | — | — | 0 | 0 |
