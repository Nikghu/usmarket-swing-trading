# Revision Note — RN-GUI-1.1.0-20260515

**Version:** 1.1.0
**Date:** 2026-05-15
**Tool:** GUI
**Artifact:** FO-GUI-012 / SRD-GUI-012.001–007

---

## Summary

Wired `LiveTickWorker` (MD-EXE-008.001.M01) into `AppService` to replace yfinance polling for three GUI surfaces. Market Watch strip, Watchlist LTP column, and Position Monitor `current_price` now update within 1 s of an IBKR price change. The 15 s `_MarketWatchWorker` and its QTimer are removed entirely; the 30 s `_WatchlistQuoteWorker` is retained only for static metadata (day_open, year_high, volume, market_cap).

---

## Modified Files

| File | Change |
|---|---|
| `gui/app_service.py` | Start/stop `LiveTickWorker`; wire 3 tick handlers; remove `_MarketWatchWorker`; split watchlist into static-metadata (yfinance once) + live-price (tick); add S&P 500 gate and 95-symbol subscription cap |
| `gui/settings_panel.py` | Added "Tick Data Client ID" spinbox (range 1–999) in System tab, saved to `ibkr_tick_client_id` |
| `gui/system_store.py` | Added deserialization of `ibkr_tick_client_id` in `load_system_config()` (field already present in `SystemConfig` from Phase 1) |

---

## Architecture

```
AppService
├── LiveTickWorker  (clientId=14, QThread)
│   └── tick_price(tag, price)
│       ├── _on_mktwatch_tick   → market_watch_updated
│       ├── _on_watchlist_tick  → watchlist_updated
│       └── _on_position_tick   → positions_updated
├── _sync_tick_subscriptions()
│   ├── MW index contracts  (^GSPC → SPX/CBOE, etc.)
│   ├── S&P 500 gated watchlist symbols
│   └── S&P 500 gated position symbols (trimmed first if > 95)
└── _fetch_mw_prev_close_once()  — one-shot yfinance at connect time
```

---

## Behaviour on Disconnect

- Market Watch: `ltp` → `None`, `change_pct` → `None`; panel shows "–"
- Watchlist: retains last known LTP (no clearing)
- Positions: retain last known `current_price` (no clearing)

---

## Tests

19 unit tests — `tests/gui/test_app_service_tick.py` (T01–T19, all Pass).

---

## SRDs Satisfied

SRD-GUI-012.001–007 (all set to Implemented).
