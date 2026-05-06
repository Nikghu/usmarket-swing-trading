# Traceability Rules

Extracted from `process.md §13`.

## TRACE.md Structure

Each tool maintains `us_swing/docs/<tool>/TRACE.md`:

```markdown
# Traceability Matrix — <Tool Name>
**Last Updated:** YYYY-MM-DD

| FO ID | SRD ID | DD ID | MD ID | UT ID(s) | Status | RN |
|---|---|---|---|---|---|---|
| FO-SCR-001 | SRD-SCR-001.001 | DD-SCR-001.001.D01 | MD-SCR-001.001.M01 | UT-SCR-001.001.M01.T01, T02 | Verified | RN-SCR-1.0.0-20260301 |
```

## Rules

1. TRACE.md is updated at **every phase completion** — not just at the end
2. No cell may be empty for a completed row — every code module must trace all the way up to an FO and down to a test
3. An agent must read TRACE.md before creating artifacts to avoid regenerating what already exists
4. Every code file header references its MD ID: `Module: MD-<TOOL>-NNN.NNN.MNN`
5. Every test docstring references its UT ID: `UT-<TOOL>-NNN.NNN.MNN.TNN`

## Issue → Process Integration

- Every resolved issue must produce a Revision Note
- If a fix changes an SRD or FO, all downstream documents must be updated (cascade rule)
- Issue files: `docs/<tool>/issues/ISS-<TOOL>-NNNN.md`
