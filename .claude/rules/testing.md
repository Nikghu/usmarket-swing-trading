# Testing Rules

Extracted from `process.md §7 (Phase 5 UTCD)`, `§9 (Phase 7)`, and `§10 (Phase 8)`.

## Framework

- `pytest` + `pytest-asyncio` (asyncio_mode = "auto") + `pytest-qt` for GUI tests
- Test paths: `us_swing/tests/`
- Run: `python -m pytest us_swing/tests/ -q`

## File Naming

- Unit tests: `tests/<tool>/test_<module>.py` — one file per source module
- Integration tests: `tests/integration/test_<scenario>.py`
- Regression tests: `tests/regression/`
- Tool-specific fixtures: `tests/<tool>/conftest.py`
- Global fixtures: `tests/conftest.py`

## Test ID Convention

Every test function docstring **must** reference its UTCD ID (format: `UT-<TOOL>-NNN.NNN.MNN.TNN`):

```python
def test_calculate_rsi_positive():
    """UT-SCR-001.001.M01.T01: RSI returns valid value for normal input."""
```

## Coverage Gate

- ≥ 80% line coverage per module
- ≥ 90% for `Must`-priority SRD requirements
- No task is "done" until all UTCD tests pass

## UTCD-First Rule

- Test cases are written **before** implementation code (TDD-aligned)
- Every `Must`-priority SRD requirement needs ≥ 1 positive + ≥ 1 negative test case
- Test types: `Positive` / `Negative` / `Edge` / `Performance`

## No Mocking the Database

- Integration tests must use real SQLAlchemy sessions (in-memory SQLite is fine)
- Do not mock DB calls — this has caused prod divergence before
- Use fixture factories for test data; never hardcode raw SQL in tests

## UTCD Status Tracking

After running tests, update the `Status` column in `docs/<tool>/UTCD.md`:
- `Not Run` → `Pass` or `Fail`

## Integration Tests

- Live in `tests/integration/`; each references the FO(s) it validates
- MCP integration tests: invoke via MCP server stdio transport, verify against JSON Schema
- GUI integration tests: use `pytest-qt` to simulate user interactions
