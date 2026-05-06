# USMarket Swing Trading Toolkit

**An end-to-end, modular platform for US equity swing trading** — encompassing analysis, screening, backtesting, and execution.

Built with Python 3.11+, PyQt6, and MCP (Model Context Protocol) for dual human + AI-agent operation.

---

## 🤖 AI Agent — Start Here

> **Read [`AGENT_BOOT.md`](AGENT_BOOT.md) — that is the ONLY file you need to begin.**

---

## Project Structure

```
USMarket_Backtesting/           ← workspace root
├── AGENT_BOOT.md               # AI agent entry point
├── process.md                  # Generic dev process (all projects)
├── skill.md                    # Generic skills inventory
├── PROMPTS.md                  # Reusable prompt patterns
├── pyproject.toml              # Build config & dependencies
│
├── pilot1/                     # Pilot 1 project (active)
│   ├── idea.md                 #   Vision & roadmap
│   ├── ALM.md                  #   ALM tool spec
│   ├── CONTEXT.md              #   Current dev state
│   ├── DEVLOG.md               #   Session journal
│   ├── docs/infrastructure/    #   INF tool docs (FO→TRACE)
│   ├── tests/core/             #   Unit tests
│   └── data/cache/             #   Local data cache (Parquet)
│
├── us_swing/                   # US Swing project (requirements stage)
│   └── requirements.md
│
├── pilot1/src/usswing/pilot1/core/ # Pilot 1 source code
└── alm/                        # ALM viewer tool (PyQt6)
```

---

## Quick Start

```bash
cd USMarket_Backtesting
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"
pytest                           # Run tests
python -m alm                    # Launch ALM viewer
```
