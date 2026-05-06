# Windows Installer Generator — Claude Instructions

Shared tool (workspace-level). Generates Inno Setup / NSIS installers from a YAML config,
signs the output, and bundles an auto-update stub. Runs standalone via PyQt6 GUI.
Not part of the `us_swing` package.

## Layout

```
installer/
├── __main__.py          ← entry point: python -m installer
├── config.py            ← BuildConfig dataclasses + YAML loader
├── builder.py           ← Jinja2 rendering + ISCC/makensis subprocess
├── signer.py            ← SHA-256 + RSA-PSS sign/verify
├── updater_stub.py      ← copy into target app for auto-update
├── main_window.py       ← PyQt6 main window
├── theme.py             ← UI theme/styling
├── config_example.yaml  ← reference config
└── templates/
    ├── setup.iss.j2     ← Inno Setup template
    └── setup.nsi.j2     ← NSIS template
```

## Run

```bash
python -m installer
```

## Rules

- No business logic in `main_window.py` — build logic lives in `builder.py`.
- No imports from `us_swing` or any project package.
- `signer.py` uses SHA-256 + RSA-PSS; do not change the signing algorithm without updating `updater_stub.py`.
- Must pass `ruff` + `mypy --strict` before any commit.
