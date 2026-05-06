# ALM Traceability Viewer — Claude Instructions

Shared tool (workspace-level). Reads `us_swing/docs/<tool>/TRACE.md` files and renders a
traceability matrix in a PyQt6 GUI. Not part of the `us_swing` package — runs standalone.

## Layout

```
alm/
├── __main__.py        ← entry point: python -m alm
├── main_window.py     ← PyQt6 main window
└── parser.py          ← TRACE.md markdown parser → data model
```

## Run

```bash
python -m alm
```

## Rules

- No business logic in `main_window.py` — parsing lives in `parser.py`.
- No imports from `us_swing` or any project package.
- Must pass `ruff` + `mypy --strict` before any commit.
