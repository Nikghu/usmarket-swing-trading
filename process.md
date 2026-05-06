# Development Process Document

**Project:** USMarket Swing Trading Toolkit
**Document ID:** PROC-001
**Process Version:** 0.5.0-draft
**Status:** Evolving — this process will be refined iteratively until declared stable.

> **Agent Directive:** Any agent (human or AI) executing work on this project **must** follow this process end-to-end. Deviation is not permitted unless a Process Change Request (PCR) is raised and approved. When given a task at the FO level, the agent must walk through every phase in order, producing all required artifacts before marking the task complete.

---

## ⚠️ Section 0 — Token Optimization Rules

> **AI agents: Do NOT read this entire document.** Read `AGENT_BOOT.md` instead — it contains everything you need to start working.

**Rules for AI agents:**

1. **Boot from `AGENT_BOOT.md` only.** Do not read idea.md, skill.md, or this full file at session start.
2. **Read sections on demand.** When starting a specific phase (e.g., writing SRD), read only the relevant section of this document (e.g., §4).
3. **Use compact table format** for SRD, MD, and UTCD artifacts where possible (see `AGENT_BOOT.md` for templates). Avoid verbose prose.
4. **Check before generating.** Read `docs/<tool>/TRACE.md` before creating artifacts — don't regenerate what already exists.
5. **Don't read skill.md** unless explicitly assessing competencies.
6. **Don't read idea.md** unless you need vision/roadmap context for a specific design decision.
7. **Keep process documents minimal.** Every edit must add specific value — no redundant prose, no repeated rules.
8. **Plan mode:** Use plan mode for tasks spanning multiple artifact types in a single session (e.g., writing FO + SRD together). Use direct execution for tasks with fully scoped, single-artifact objectives (e.g., "write the 38 INF tests"). When in doubt, plan first.

---

## Table of Contents

0. [Token Optimization Rules](#️-section-0--token-optimization-rules)
1. [Process Overview](#1-process-overview)
2. [Document Hierarchy & Traceability](#2-document-hierarchy--traceability)
3. [Phase 1 — Functional Objectives (FO)](#3-phase-1--functional-objectives-fo)
4. [Phase 2 — Software Requirement Document (SRD)](#4-phase-2--software-requirement-document-srd)
5. [Phase 3 — Design Document (DD)](#5-phase-3--design-document-dd)
6. [Phase 4 — Module Decomposition (MD)](#6-phase-4--module-decomposition-md)
7. [Phase 5 — Unit Test Case Document (UTCD)](#7-phase-5--unit-test-case-document-utcd)
8. [Phase 6 — Implementation](#8-phase-6--implementation)
9. [Phase 7 — Unit Testing & Verification](#9-phase-7--unit-testing--verification)
10. [Phase 8 — Integration Testing](#10-phase-8--integration-testing)
11. [Phase 9 — Review & Revision Notes](#11-phase-9--review--revision-notes)
12. [Issue Handling Process](#12-issue-handling-process)
13. [Traceability Matrix](#13-traceability-matrix)
14. [Numbering & Naming Conventions](#14-numbering--naming-conventions)
15. [Process Versioning & Change Control](#15-process-versioning--change-control)
16. [Definition of Done (DoD)](#16-definition-of-done-dod)
17. [Agent Workflow Summary](#17-agent-workflow-summary)
18. [Document Templates](#18-document-templates)

---

## 1. Process Overview

Every tool in the toolkit follows a **phased, traceable, document-driven** development lifecycle. The chain of artifacts is:

```
FO ──► SRD ──► DD ──► MD ──► UTCD ──► Code ──► Test Results ──► Revision Notes
```

Each artifact **links back** to its parent via section IDs so that:
- Every line of code traces to a module, which traces to a requirement, which traces to a functional objective.
- An agent given only an FO can deterministically produce all downstream artifacts.
- Any future audit or review can walk the chain in either direction.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FUNCTIONAL OBJECTIVE (FO)                │
│                  FO-<TOOL>-001, FO-<TOOL>-002 ...               │
└──────────────────────────┬──────────────────────────────────────┘
                           │ decomposes into
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              SOFTWARE REQUIREMENT DOCUMENT (SRD)                │
│         SRD-<TOOL>-001.001, SRD-<TOOL>-001.002 ...             │
└──────────────────────────┬──────────────────────────────────────┘
                           │ realized by
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DESIGN DOCUMENT (DD)                        │
│         DD-<TOOL>-001.001.D01, DD-<TOOL>-001.001.D02 ...       │
└──────────────────────────┬──────────────────────────────────────┘
                           │ decomposed into
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   MODULE DECOMPOSITION (MD)                     │
│       MD-<TOOL>-001.001.M01, MD-<TOOL>-001.001.M02 ...         │
└──────────────────────────┬──────────────────────────────────────┘
                           │ verified by
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                UNIT TEST CASE DOCUMENT (UTCD)                   │
│    UT-<TOOL>-001.001.M01.T01, UT-<TOOL>-001.001.M01.T02 ...    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ produces
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      REVISION NOTES (RN)                        │
│                RN-<TOOL>-<VERSION>-<DATE>                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Document Hierarchy & Traceability

| Level | Artifact | ID Pattern | Stored At | Links To |
|---|---|---|---|---|
| L0 | Functional Objective | `FO-<TOOL>-NNN` | `docs/<tool>/FO.md` | — (top level) |
| L1 | Software Requirement | `SRD-<TOOL>-NNN.NNN` | `docs/<tool>/SRD.md` | Parent FO |
| L2 | Design Document | `DD-<TOOL>-NNN.NNN.DNN` | `docs/<tool>/DD.md` | Parent SRD |
| L3 | Module Decomposition | `MD-<TOOL>-NNN.NNN.MNN` | `docs/<tool>/MD.md` | Parent SRD |
| L4 | Unit Test Case Doc | `UT-<TOOL>-NNN.NNN.MNN.TNN` | `docs/<tool>/UTCD.md` | Parent MD |
| L5 | Revision Notes | `RN-<TOOL>-VER-DATE` | `docs/<tool>/revisions/` | All impacted IDs |
| — | Traceability Matrix | — | `docs/<tool>/TRACE.md` | Cross-reference all |
| — | Issue Report | `ISS-<TOOL>-NNNN` | `docs/<tool>/issues/` | Impacted IDs |

---

## 3. Phase 1 — Functional Objectives (FO)

### 3.1 Purpose

Capture **what** the tool must accomplish from the user/business perspective in clear, testable bullet points. FOs are **not** technical — they describe outcomes.

### 3.2 Rules

1. Each tool gets its own FO document.
2. Every FO bullet is assigned a unique ID: `FO-<TOOL>-NNN` (three-digit, zero-padded).
3. FOs must be:
   - **Specific** — no ambiguity about the expected behavior.
   - **Testable** — an acceptance criterion can be written against it.
   - **Independent** — each FO can be delivered and verified on its own where possible.
4. FOs are approved before SRD work begins.

### 3.3 FO Document Structure

```markdown
# Functional Objectives — <Tool Name>
**Document ID:** FO-<TOOL>
**Version:** x.y.z
**Status:** Draft | Under Review | Approved
**Last Updated:** YYYY-MM-DD

## FO-<TOOL>-001: <Short Title>
- <Bullet describing the objective>
- <Bullet describing the objective>
- **Acceptance Criteria:** <How to verify this FO is met>

## FO-<TOOL>-002: <Short Title>
...
```

---

## 4. Phase 2 — Software Requirement Document (SRD)

### 4.1 Purpose

Decompose each FO into **detailed, implementable software requirements**. SRD is the contract between "what" (FO) and "how" (design/code).

### 4.2 Rules

1. Every SRD requirement **must** trace back to exactly one FO via its ID.
2. SRD numbering inherits from the parent FO:
   - FO `FO-SCR-001` → SRD items `SRD-SCR-001.001`, `SRD-SCR-001.002`, …
3. Requirements must specify:
   - **Inputs** — what data/parameters the requirement consumes.
   - **Processing** — the transformation or logic.
   - **Outputs** — the expected result or side-effect.
   - **Constraints** — performance, security, compatibility.
4. Each requirement has a **priority** (`Must` / `Should` / `Could`) and **status** (see §4.4).
5. Only `Approved` requirements may be implemented. After implementation, set status → `Implemented`.
6. `Verified` requirements are frozen. Only the user may set status to `Reopen`.
7. Agent may only edit requirement content when status is `Draft` or `Reopen`.

### 4.3 SRD Document Structure

```markdown
# Software Requirement Document — <Tool Name>
**Document ID:** SRD-<TOOL>
**Version:** x.y.z
**Traces To:** FO-<TOOL> vX.Y.Z
**Status:** Draft | Approved
**Last Updated:** YYYY-MM-DD

---

## Section 1: Requirements for FO-<TOOL>-001 — <FO Title>

### SRD-<TOOL>-001.001: <Requirement Title>
- **Parent FO:** FO-<TOOL>-001
- **Priority:** Must
- **Status:** Draft | Approved | Implemented | Verified | Reopen
- **Description:** <Detailed requirement>
- **Inputs:** <...>
- **Processing:** <...>
- **Outputs:** <...>
- **Constraints:** <...>
- **Notes:** <...>

### SRD-<TOOL>-001.002: <Requirement Title>
...

---

## Section 2: Requirements for FO-<TOOL>-002 — <FO Title>
...
```

### 4.4 Requirement Status Lifecycle

| Status | Set By | Agent May Edit Content? |
|---|---|---|
| `Draft` | LLM / Agent | **Yes** |
| `Approved` | User | No |
| `Implemented` | LLM / Agent | No |
| `Verified` | User | No (frozen) |
| `Reopen` | User | **Yes** |

```
Draft ──► Approved ──► Implemented ──► Verified
                                           │
                  ◄────── Reopen ◄─────────┘
```

---

## 5. Phase 3 — Design Document (DD)

### 5.1 Purpose

Bridge the gap between requirements (SRD) and implementation. Defines **architecture, data flow, class/function signatures, and interaction patterns** for each set of requirements.

### 5.2 Rules

1. One DD per tool (may have sub-sections per SRD section).
2. DD items trace back to SRD items: `DD-<TOOL>-001.001.D01`.
3. Must include:
   - **Component/class diagrams** (Mermaid preferred for agent-readability).
   - **Data flow** — how data moves through the module.
   - **Interface contracts** — function signatures, input/output types, error types.
   - **MCP tool descriptor draft** — JSON Schema for agent-facing interface.
   - **UI wireframe notes** (for GUI-bearing tools) — panel layout, widget list, signal/slot map.
4. DD is reviewed before module decomposition.

### 5.3 DD Document Structure

```markdown
# Design Document — <Tool Name>
**Document ID:** DD-<TOOL>
**Version:** x.y.z
**Traces To:** SRD-<TOOL> vX.Y.Z
**Last Updated:** YYYY-MM-DD

## DD-<TOOL>-001.001.D01: <Design Aspect Title>
- **Parent SRD:** SRD-<TOOL>-001.001
- **Component Diagram:** (mermaid block)
- **Data Flow:** ...
- **Interfaces:** ...
- **MCP Schema Draft:** (json block)
- **UI Notes:** ...
```

---

## 6. Phase 4 — Module Decomposition (MD)

### 6.1 Purpose

Break each SRD requirement into **concrete code modules** (files, classes, functions). This is the implementation blueprint.

### 6.2 Rules

1. Each module traces back to one or more SRD requirements.
2. Module ID inherits from SRD: `MD-<TOOL>-001.001.M01`.
3. Each module entry specifies:
   - **File path** — where the code will live.
   - **Responsibility** — single-responsibility description.
   - **Public API** — exported functions/classes with type signatures.
   - **Dependencies** — internal and external.
   - **MCP Exposure** — whether this module (or part of it) is exposed as an MCP tool.
4. Modules must be small enough that a single developer (or agent) can implement and test one in isolation.

### 6.3 MD Document Structure

```markdown
# Module Decomposition — <Tool Name>
**Document ID:** MD-<TOOL>
**Version:** x.y.z
**Traces To:** SRD-<TOOL> vX.Y.Z
**Last Updated:** YYYY-MM-DD

---

## MD-<TOOL>-001.001.M01: <Module Name>
- **Parent SRD:** SRD-<TOOL>-001.001
- **File:** `src/usswing/<tool>/<module>.py`
- **Responsibility:** <One sentence>
- **Public API:**
  - `function_name(param: Type) -> ReturnType` — <brief>
- **Dependencies:** <list>
- **MCP Exposed:** Yes / No
- **Notes:** <...>

## MD-<TOOL>-001.001.M02: <Module Name>
...
```

---

## 7. Phase 5 — Unit Test Case Document (UTCD)

### 7.1 Purpose

Define **every test case** for every module **before** writing code (test-first / TDD-aligned). The UTCD is the source of truth for what `pytest` must verify.

### 7.2 Rules

1. Each test case traces to a module: `UT-<TOOL>-001.001.M01.T01`.
2. Test cases must specify:
   - **Objective** — what is being verified.
   - **Preconditions** — setup/fixtures required.
   - **Input** — exact parameters or data.
   - **Expected Output** — exact return value, side-effect, or exception.
   - **Type** — `Positive` / `Negative` / `Edge` / `Performance`.
3. Every `Must`-priority SRD requirement must have **≥ 1 positive + ≥ 1 negative** test case.
4. UTCD is written **before** implementation code. Code is written to make tests pass.

### 7.3 UTCD Document Structure

```markdown
# Unit Test Case Document — <Tool Name>
**Document ID:** UTCD-<TOOL>
**Version:** x.y.z
**Traces To:** MD-<TOOL> vX.Y.Z
**Last Updated:** YYYY-MM-DD

---

## Tests for MD-<TOOL>-001.001.M01 — <Module Name>

### UT-<TOOL>-001.001.M01.T01: <Test Title>
- **Parent Module:** MD-<TOOL>-001.001.M01
- **Objective:** <What is verified>
- **Preconditions:** <Setup>
- **Input:** <Params/data>
- **Expected Output:** <Result>
- **Type:** Positive
- **Status:** Not Run | Pass | Fail

### UT-<TOOL>-001.001.M01.T02: <Test Title>
...
```

---

## 8. Phase 6 — Implementation

### 8.1 Rules

1. Code is written **module by module**, following the MD document.
2. Each module's code file must include a header comment referencing its MD ID:
   ```python
   """
   Module: MD-<TOOL>-001.001.M01 — <Module Name>
   Parent SRD: SRD-<TOOL>-001.001
   """
   ```
3. All public functions/classes must have Google-style docstrings with type annotations.
4. Code must pass `ruff`, `black`, and `mypy --strict` before being considered complete.
5. MCP-exposed modules must include their JSON Schema in a `schemas/` directory.
6. No module is "done" until its UTCD tests pass (see Phase 7).

### 8.2 Commit Convention

```
<type>(<tool>): <short summary>

Refs: MD-<TOOL>-NNN.NNN.MNN
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.

---

## 9. Phase 7 — Unit Testing & Verification

### 9.1 Rules

1. Implement tests defined in UTCD using `pytest`.
2. Test file naming: `tests/<tool>/test_<module>.py`.
3. Each test function's docstring references its UT ID:
   ```python
   def test_calculate_rsi_positive():
       """UT-SCR-001.001.M01.T01: RSI returns valid value for normal input."""
   ```
4. Run full test suite; update UTCD status column (`Pass` / `Fail`).
5. **Coverage gate:** ≥ 80 % line coverage per module; ≥ 90 % for `Must`-priority requirements.
6. All tests must pass before proceeding to integration testing.

---

## 10. Phase 8 — Integration Testing

### 10.1 Purpose

Verify that **modules work together** as described in the DD and that the tool meets its FOs end-to-end.

### 10.2 Rules

1. Integration tests live in `tests/<tool>/integration/`.
2. Each integration test references the FO(s) it validates.
3. MCP integration tests: invoke the tool via the MCP server (stdio transport) and verify structured output against the JSON Schema.
4. GUI integration tests (where applicable): use `pytest-qt` to simulate user interactions.
5. Results are logged and linked in the Traceability Matrix.

---

## 11. Phase 9 — Review & Revision Notes

### 11.1 Revision Notes (RN)

**At the end of every task** (whether new development, bug fix, or refactoring), the agent/developer **must** produce a Revision Note.

### 11.2 RN Document Structure

```markdown
# Revision Note
**Document ID:** RN-<TOOL>-<VERSION>-<YYYYMMDD>
**Date:** YYYY-MM-DD
**Author:** <Name or Agent ID>
**Task Type:** New Development | Bug Fix | Refactoring | Process Change

---

## Summary
<1–3 sentence summary of what was done>

## Artifacts Created / Modified

| Artifact ID | Action | Description |
|---|---|---|
| FO-<TOOL>-NNN | Created / Modified | <Brief> |
| SRD-<TOOL>-NNN.NNN | Created / Modified | <Brief> |
| MD-<TOOL>-NNN.NNN.MNN | Created | <Brief> |
| UT-<TOOL>-NNN.NNN.MNN.TNN | Created | <Brief> |

## Test Results Summary

| Total Tests | Passed | Failed | Skipped | Coverage |
|---|---|---|---|---|
| NN | NN | NN | NN | NN% |

## Impacted FOs
- FO-<TOOL>-NNN — <status after this revision>

## Open Items / Risks
- <Any deferred work, known issues, or risks>

## Linked Issues
- ISS-<TOOL>-NNNN (if applicable)

## Approvals
- [ ] Code Review
- [ ] Test Verification
- [ ] Documentation Updated
```

### 11.3 RN Rules

1. One RN per completed task — no batching across unrelated tasks.
2. RN is stored in `docs/<tool>/revisions/RN-<TOOL>-<VER>-<DATE>.md`.
3. RN must list **every** artifact ID that was created or modified.
4. RN must include test result summary.
5. RN is the **final gate** — a task is not "done" until its RN is written and checklist is complete.

---

## 12. Issue Handling Process

> **Note:** This section is a **placeholder**. The detailed issue handling workflow will be defined separately and integrated into this process document in a future revision. The structure below provides the skeleton that will be expanded.

### 12.1 Issue Lifecycle (Preliminary)

```
New ──► Triaged ──► Assigned ──► In Progress ──► Resolved ──► Verified ──► Closed
                                                    │
                                                    ▼
                                                 Reopened
```

### 12.2 Issue Report Structure (Preliminary)

```markdown
# Issue Report
**Issue ID:** ISS-<TOOL>-NNNN
**Date Raised:** YYYY-MM-DD
**Severity:** Critical | Major | Minor | Cosmetic
**Status:** New | Triaged | Assigned | In Progress | Resolved | Verified | Closed
**Raised By:** <Name or Agent ID>

## Description
<Clear description of the issue>

## Steps to Reproduce
1. ...

## Expected Behavior
<...>

## Actual Behavior
<...>

## Impacted Artifacts
- SRD-<TOOL>-NNN.NNN
- MD-<TOOL>-NNN.NNN.MNN

## Root Cause (filled during resolution)
<...>

## Fix Reference
- Commit: <hash>
- RN: RN-<TOOL>-<VER>-<DATE>

## Verification
- [ ] Fix verified by test: UT-<TOOL>-NNN.NNN.MNN.TNN
```

### 12.3 Issue → Process Integration

- Every resolved issue **must** produce a Revision Note.
- If the fix changes an SRD or FO, all downstream documents must be updated (cascade rule).
- Issue-specific process changes will be documented here in a future update.

---

## 13. Traceability Matrix

Each tool maintains a traceability matrix (`docs/<tool>/TRACE.md`) that maps every ID across all levels:

```markdown
# Traceability Matrix — <Tool Name>
**Last Updated:** YYYY-MM-DD

| FO ID | SRD ID | DD ID | MD ID | UT ID(s) | Status | RN |
|---|---|---|---|---|---|---|
| FO-SCR-001 | SRD-SCR-001.001 | DD-SCR-001.001.D01 | MD-SCR-001.001.M01 | UT-SCR-001.001.M01.T01, T02 | Verified | RN-SCR-1.0.0-20260301 |
| FO-SCR-001 | SRD-SCR-001.002 | DD-SCR-001.002.D01 | MD-SCR-001.002.M01 | UT-SCR-001.002.M01.T01 | In Progress | — |
```

**Rules:**
1. The matrix is updated at **every phase completion**.
2. No cell may be empty for a completed row — every code module must trace all the way up to an FO and down to a test.
3. An agent can read this matrix to determine what work remains.

---

## 14. Numbering & Naming Conventions

### 14.1 ID Format Summary

| Artifact | Format | Example |
|---|---|---|
| Tool Code | 3-letter uppercase | `SCR` (Screener), `ANA` (Analysis), `BKT` (Backtesting), `EXE` (Execution), `INF` (Infrastructure) |
| Functional Objective | `FO-<TOOL>-NNN` | `FO-SCR-001` |
| Software Requirement | `SRD-<TOOL>-NNN.NNN` | `SRD-SCR-001.003` |
| Design Document Item | `DD-<TOOL>-NNN.NNN.DNN` | `DD-SCR-001.003.D01` |
| Module | `MD-<TOOL>-NNN.NNN.MNN` | `MD-SCR-001.003.M02` |
| Unit Test Case | `UT-<TOOL>-NNN.NNN.MNN.TNN` | `UT-SCR-001.003.M02.T05` |
| Revision Note | `RN-<TOOL>-VER-YYYYMMDD` | `RN-SCR-1.0.0-20260301` |
| Issue | `ISS-<TOOL>-NNNN` | `ISS-SCR-0042` |
| Process Change Request | `PCR-NNNN` | `PCR-0001` |

### 14.2 Project Folder Structure — Complete Reference

All folders below are **relative to the project folder** (e.g., `pilot1/`, `us_swing/`), not the workspace root. The workspace root holds only workspace-level files (`process.md`, `skill.md`, `pyproject.toml`, `AGENT_BOOT.md`, etc.).

```
<project>/                                     # ── PROJECT FOLDER ──
│ ═══════════════════════════════════════════════════════════════════
│  A.  PROCESS & REQUIREMENTS DOCUMENTS          (docs/)
│ ═══════════════════════════════════════════════════════════════════
│
├── docs/
│   │
│   ├── templates/                             # Reusable document templates (Phase: Pilot+)
│   │   ├── FO_TEMPLATE.md
│   │   ├── SRD_TEMPLATE.md
│   │   ├── DD_TEMPLATE.md
│   │   ├── MD_TEMPLATE.md
│   │   ├── UTCD_TEMPLATE.md
│   │   ├── RN_TEMPLATE.md
│   │   ├── ISS_TEMPLATE.md
│   │   └── TRACE_TEMPLATE.md
│   │
│   ├── process/                               # Process-level artifacts (not tool-specific)
│   │   ├── pcr/                               #   Process Change Requests
│   │   │   └── PCR-0001.md
│   │   └── changelog.md                       #   Process change log (mirror of §15.3)
│   │
│   ├── screener/                              # ── Tool: Screener (SCR) ──
│   │   ├── FO.md                              #   Functional Objectives
│   │   ├── SRD.md                             #   Software Requirement Document
│   │   ├── DD.md                              #   Design Document
│   │   ├── MD.md                              #   Module Decomposition
│   │   ├── UTCD.md                            #   Unit Test Case Document
│   │   ├── TRACE.md                           #   Traceability Matrix
│   │   ├── revisions/                         #   Revision Notes
│   │   │   ├── RN-SCR-1.0.0-20260301.md
│   │   │   └── RN-SCR-1.1.0-20260315.md
│   │   └── issues/                            #   Issue Reports
│   │       ├── ISS-SCR-0001.md
│   │       └── ISS-SCR-0002.md
│   │
│   ├── analysis/                              # ── Tool: Analysis (ANA) ──
│   │   ├── FO.md
│   │   ├── SRD.md
│   │   ├── DD.md
│   │   ├── MD.md
│   │   ├── UTCD.md
│   │   ├── TRACE.md
│   │   ├── revisions/
│   │   └── issues/
│   │
│   ├── backtesting/                           # ── Tool: Backtesting (BKT) ──
│   │   ├── FO.md
│   │   ├── SRD.md
│   │   ├── DD.md
│   │   ├── MD.md
│   │   ├── UTCD.md
│   │   ├── TRACE.md
│   │   ├── revisions/
│   │   └── issues/
│   │
│   ├── execution/                             # ── Tool: Execution (EXE) ──
│   │   ├── FO.md
│   │   ├── SRD.md
│   │   ├── DD.md
│   │   ├── MD.md
│   │   ├── UTCD.md
│   │   ├── TRACE.md
│   │   ├── revisions/
│   │   └── issues/
│   │
│   └── infrastructure/                        # ── Tool: Infrastructure (INF) ──
│       ├── FO.md                              #   Shared data layer, config, MCP server
│       ├── SRD.md
│       ├── DD.md
│       ├── MD.md
│       ├── UTCD.md
│       ├── TRACE.md
│       ├── revisions/
│       └── issues/
│
│
│ ═══════════════════════════════════════════════════════════════════
│  B.  SOURCE CODE                                (src/)
│ ═══════════════════════════════════════════════════════════════════
│
├── src/
│   └── usswing/                               # Top-level namespace package
│       │
│       ├── __init__.py                        # Package root; version, public re-exports
│       ├── py.typed                           # PEP 561 marker for type-checker support
│       │
│       ├── core/                              # ── Shared Core (INF) ──
│       │   ├── __init__.py
│       │   ├── config.py                      #   YAML/TOML config loader, env overrides
│       │   ├── data_feed.py                   #   Abstract DataFeed interface
│       │   ├── db.py                          #   SQLAlchemy session factory, migrations
│       │   ├── logging.py                     #   Structured JSON logger (structlog)
│       │   ├── types.py                       #   Shared type aliases, enums, Pydantic models
│       │   ├── errors.py                      #   Base exception hierarchy, error codes
│       │   └── mcp/                           #   MCP server & tool registration
│       │       ├── __init__.py
│       │       ├── server.py                  #     MCP server entry point (stdio/SSE)
│       │       ├── registry.py                #     Tool registry — auto-discovers tools
│       │       └── schemas/                   #     Shared/global MCP JSON Schemas
│       │           └── common.json
│       │
│       ├── analysis/                          # ── Analysis Tool (ANA) ──
│       │   ├── __init__.py
│       │   ├── indicators/                    #   Technical indicator implementations
│       │   │   ├── __init__.py
│       │   │   ├── momentum.py                #     RSI, MACD, Stochastic, etc.
│       │   │   ├── trend.py                   #     SMA, EMA, ADX, Ichimoku, etc.
│       │   │   ├── volatility.py              #     Bollinger, ATR, Keltner, etc.
│       │   │   └── volume.py                  #     VWAP, OBV, MFI, etc.
│       │   ├── fundamental/                   #   Fundamental analysis modules
│       │   │   ├── __init__.py
│       │   │   ├── earnings.py
│       │   │   └── ratios.py
│       │   ├── sentiment/                     #   NLP / sentiment scoring
│       │   │   ├── __init__.py
│       │   │   └── finbert.py
│       │   ├── regime.py                      #   Market regime detection
│       │   ├── multi_timeframe.py             #   Multi-timeframe alignment
│       │   ├── schemas/                       #   MCP JSON Schemas for analysis tools
│       │   │   ├── indicators.json
│       │   │   └── sentiment.json
│       │   └── gui/                           #   PyQt GUI panels for analysis
│       │       ├── __init__.py
│       │       ├── chart_widget.py
│       │       ├── indicator_panel.py
│       │       └── resources/                 #     Icons, QSS themes, etc.
│       │
│       ├── screener/                          # ── Screener Tool (SCR) ──
│       │   ├── __init__.py
│       │   ├── rule_engine.py                 #   Rule-based filter engine
│       │   ├── pattern_detector.py            #   Chart pattern recognition
│       │   ├── fundamental_filter.py          #   Fundamental screening
│       │   ├── composite_scorer.py            #   Weighted composite scoring
│       │   ├── watchlist.py                   #   Watchlist CRUD
│       │   ├── alerting.py                    #   Real-time alert system
│       │   ├── schemas/                       #   MCP JSON Schemas for screener tools
│       │   │   ├── screen.json
│       │   │   └── watchlist.json
│       │   └── gui/
│       │       ├── __init__.py
│       │       ├── screener_panel.py
│       │       ├── watchlist_panel.py
│       │       └── resources/
│       │
│       ├── backtesting/                       # ── Backtesting Tool (BKT) ──
│       │   ├── __init__.py
│       │   ├── engine.py                      #   Event-driven backtesting engine
│       │   ├── strategy.py                    #   Strategy base class & DSL
│       │   ├── portfolio.py                   #   Portfolio-level simulation
│       │   ├── optimizer.py                   #   Parameter optimization (grid, Bayesian)
│       │   ├── metrics.py                     #   Performance & risk metrics
│       │   ├── walkforward.py                 #   Walk-forward / cross-validation
│       │   ├── schemas/
│       │   │   ├── backtest.json
│       │   │   └── strategy.json
│       │   └── gui/
│       │       ├── __init__.py
│       │       ├── backtest_panel.py
│       │       ├── equity_chart.py
│       │       └── resources/
│       │
│       ├── execution/                         # ── Execution Tool (EXE) ──
│       │   ├── __init__.py
│       │   ├── brokers/                       #   Broker adapter implementations
│       │   │   ├── __init__.py
│       │   │   ├── base.py                    #     Abstract broker interface
│       │   │   ├── alpaca_adapter.py
│       │   │   ├── ib_adapter.py
│       │   │   └── paper_simulator.py
│       │   ├── oms.py                         #   Order Management System
│       │   ├── risk_manager.py                #   Position sizing & risk enforcement
│       │   ├── signal_bridge.py               #   Signal → Order pipeline
│       │   ├── journal.py                     #   Trade journal auto-logger
│       │   ├── schemas/
│       │   │   ├── order.json
│       │   │   └── position.json
│       │   └── gui/
│       │       ├── __init__.py
│       │       ├── order_panel.py
│       │       ├── position_panel.py
│       │       ├── journal_panel.py
│       │       └── resources/
│       │
│       └── app/                               # ── Main Application Shell ──
│           ├── __init__.py
│           ├── main.py                        #   Application entry point
│           ├── main_window.py                 #   QMainWindow with dockable workspace
│           ├── command_palette.py             #   Ctrl+K command palette
│           ├── theme.py                       #   Dark/light theme management
│           └── resources/
│               ├── styles/
│               │   ├── dark.qss
│               │   └── light.qss
│               └── icons/
│
│
│ ═══════════════════════════════════════════════════════════════════
│  C.  TESTS                                      (tests/)
│ ═══════════════════════════════════════════════════════════════════
│
├── tests/
│   │
│   ├── conftest.py                            # Global pytest fixtures & configuration
│   ├── pytest.ini                             # (or section in pyproject.toml)
│   │
│   ├── core/                                  # ── Unit tests: Shared Core ──
│   │   ├── __init__.py
│   │   ├── test_config.py
│   │   ├── test_data_feed.py
│   │   ├── test_db.py
│   │   ├── test_errors.py
│   │   └── test_mcp_registry.py
│   │
│   ├── analysis/                              # ── Unit tests: Analysis ──
│   │   ├── __init__.py
│   │   ├── conftest.py                        #   Tool-specific fixtures (sample OHLCV data)
│   │   ├── test_momentum.py                   #   Maps to MD-ANA-*.M* modules
│   │   ├── test_trend.py
│   │   ├── test_volatility.py
│   │   ├── test_volume.py
│   │   ├── test_earnings.py
│   │   ├── test_regime.py
│   │   └── test_multi_timeframe.py
│   │
│   ├── screener/                              # ── Unit tests: Screener ──
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_rule_engine.py
│   │   ├── test_pattern_detector.py
│   │   ├── test_composite_scorer.py
│   │   └── test_watchlist.py
│   │
│   ├── backtesting/                           # ── Unit tests: Backtesting ──
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_engine.py
│   │   ├── test_strategy.py
│   │   ├── test_portfolio.py
│   │   ├── test_optimizer.py
│   │   └── test_metrics.py
│   │
│   ├── execution/                             # ── Unit tests: Execution ──
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_oms.py
│   │   ├── test_risk_manager.py
│   │   ├── test_signal_bridge.py
│   │   ├── test_alpaca_adapter.py
│   │   ├── test_ib_adapter.py
│   │   └── test_paper_simulator.py
│   │
│   ├── integration/                           # ── Integration tests (cross-module) ──
│   │   ├── __init__.py
│   │   ├── test_screen_to_backtest.py         #   Screener output → Backtesting input
│   │   ├── test_signal_to_order.py            #   Signal → OMS end-to-end
│   │   ├── test_mcp_server.py                 #   MCP tool invocation round-trip
│   │   └── test_gui_smoke.py                  #   pytest-qt basic GUI smoke tests
│   │
│   ├── regression/                            # ── Regression tests ──
│   │   ├── __init__.py
│   │   └── test_strategy_replay.py            #   Deterministic backtest result replay
│   │
│   └── fixtures/                              # ── Shared test data ──
│       ├── sample_ohlcv.parquet               #   Sample price data
│       ├── sample_fundamentals.json           #   Sample earnings/ratios
│       └── sample_mcp_request.json            #   Sample MCP tool call payloads
│
│
│ ═══════════════════════════════════════════════════════════════════
│  D.  CONFIGURATION & CI/CD                      (root-level)
│ ═══════════════════════════════════════════════════════════════════
│
├── .github/
│   └── workflows/
│       ├── ci.yml                             # Lint → Type-check → Test → Coverage
│       └── release.yml                        # Build & publish on tag
│
├── docker/
│   ├── Dockerfile                             # Reproducible build environment
│   └── docker-compose.yml                     # Local dev (DB + MCP server)
│
└── scripts/
    ├── seed_data.py                           # Download & cache initial market data
    └── run_mcp_server.py                      # Convenience launcher for MCP server
```

---

> **BKT scope note:** The Backtesting (BKT) tool folder structure is defined above, but no FO document has been drafted or approved yet. Do **not** begin BKT implementation until: (1) a BKT FO is written and approved following §3, and (2) EXE implementation is complete. BKT is explicitly deprioritized until after EXE.

### 14.3 Folder Structure Rules

These rules are **mandatory** for any agent or developer creating files:

#### 14.3.1 Process Documents (`docs/`)

| Rule | Detail |
|---|---|
| One folder per tool | `docs/screener/`, `docs/analysis/`, `docs/backtesting/`, `docs/execution/`, `docs/infrastructure/` |
| Fixed filenames | `FO.md`, `SRD.md`, `DD.md`, `MD.md`, `UTCD.md`, `TRACE.md` — no variations |
| Revisions subfolder | Every revision note goes in `docs/<tool>/revisions/` with naming `RN-<TOOL>-VER-DATE.md` |
| Issues subfolder | Every issue report goes in `docs/<tool>/issues/` with naming `ISS-<TOOL>-NNNN.md` |
| Process-level docs | Process Change Requests go in `docs/process/pcr/` |
| Templates | Stored in `docs/templates/` — never edited in place; copy to tool folder when starting a new tool |
| No nesting beyond two levels | `docs/<tool>/revisions/` is the deepest allowed path |

#### 14.3.2 Source Code (`src/`)

> `src/` lives inside the project folder, e.g. `pilot1/src/`.

| Rule | Detail |
|---|---|
| Namespace package | All code under `src/usswing/` — importable as `from usswing.<tool> import ...` |
| One folder per tool | `src/usswing/analysis/`, `src/usswing/screener/`, etc. |
| Shared code in `core/` | Cross-cutting concerns (config, DB, logging, types, errors, MCP server) live in `src/usswing/core/` |
| GUI code in `gui/` subfolder | Each tool's PyQt panels go in `src/usswing/<tool>/gui/` — keeps GUI cleanly separated from logic |
| MCP schemas in `schemas/` | Each tool's JSON Schemas go in `src/usswing/<tool>/schemas/` |
| Resources in `resources/` | Icons, QSS files, and static assets go in `gui/resources/` or `app/resources/` |
| `__init__.py` required | Every package directory must have an `__init__.py` (even if empty) |
| File header required | Every `.py` file must start with the module ID comment (see §8.1 Rule 2) |
| No business logic in `gui/` | GUI modules handle layout, signals/slots, and display only — all logic imports from the parent tool package |

#### 14.3.3 Tests (`tests/`)

> `tests/` lives inside the project folder, e.g. `pilot1/tests/`.

| Rule | Detail |
|---|---|
| Mirror source structure | Test folders mirror `src/usswing/` — `tests/analysis/` tests `src/usswing/analysis/` |
| Unit test naming | `test_<module>.py` — one test file per source module |
| Integration tests | Cross-module and end-to-end tests go in `tests/integration/` |
| Regression tests | Deterministic replay tests go in `tests/regression/` |
| Shared fixtures | Reusable test data (Parquet, JSON) goes in `tests/fixtures/` |
| Tool-level `conftest.py` | Each tool test folder may have its own `conftest.py` for tool-specific fixtures |
| Test function docstrings | Must reference UT ID (see §9.1 Rule 3) |
| No test logic in `src/` | Test code never lives alongside production code |

#### 14.3.4 Revision Notes (`docs/<tool>/revisions/`)

| Rule | Detail |
|---|---|
| One file per revision | Each completed task produces exactly one RN file |
| Strict naming | `RN-<TOOL>-<SEMVER>-<YYYYMMDD>.md` (e.g., `RN-SCR-1.2.0-20260315.md`) |
| Chronological | Files naturally sort by date due to the naming convention |
| No subdirectories | All RN files are flat inside `revisions/` — no year/month nesting |
| Immutable after approval | Once an RN is reviewed and approved, it is never modified — corrections go in a new RN |
| Links to all artifacts | Every RN must list the IDs of every artifact it created or modified (enforced by DoD) |

#### 14.3.5 When Adding a New Tool

When a new tool is added to the project, an agent or developer must create **both** the docs and source scaffolds:

```
1. Create docs/<newtool>/
   ├── FO.md          (copy from docs/templates/FO_TEMPLATE.md)
   ├── SRD.md         (copy from docs/templates/SRD_TEMPLATE.md)
   ├── DD.md          (copy from docs/templates/DD_TEMPLATE.md)
   ├── MD.md          (copy from docs/templates/MD_TEMPLATE.md)
   ├── UTCD.md        (copy from docs/templates/UTCD_TEMPLATE.md)
   ├── TRACE.md       (copy from docs/templates/TRACE_TEMPLATE.md)
   ├── revisions/     (empty)
   └── issues/        (empty)

2. Create src/<namespace>/<newtool>/
   ├── __init__.py
   ├── schemas/       (empty, ready for MCP JSON Schemas)
   └── gui/
       ├── __init__.py
       └── resources/

3. Create tests/<newtool>/
   ├── __init__.py
   └── conftest.py

4. Register the tool's 3-letter code in §14.1 ID Format Summary.
```

### 14.4 Document Versioning

- All documents use **Semantic Versioning**: `MAJOR.MINOR.PATCH`.
- `MAJOR` — breaking structural changes.
- `MINOR` — new sections/requirements added.
- `PATCH` — corrections, clarifications.
- The version is recorded in the document header and in the RN.

---

## 15. Process Versioning & Change Control

> This process itself is a living document. It will evolve until declared **Stable**.

### 15.1 Process Maturity Levels

| Level | Label | Meaning |
|---|---|---|
| 0 | **Draft** | Initial authoring; may have gaps. |
| 1 | **Pilot** | Being tested on 1–2 tools; feedback collected. |
| 2 | **Active** | Used across all tools; minor refinements expected. |
| 3 | **Stable** | Locked; changes only via formal PCR. |

**Current Level: 0 — Draft**

### 15.2 Process Change Requests (PCR)

When a change to this process is needed:

1. Raise a PCR with ID `PCR-NNNN`.
2. Describe the current process step, the proposed change, and the rationale.
3. **Tooling impact check:** If the change affects any document format (e.g. promotes a new ID layout, changes column order, or adds a new `_DOC_FILES` file type), the agent MUST verify that `alm/parser.py` can still parse the new format by running the ALM tool and confirming the audit banner is absent. If a parser update is needed, it must be part of the same PR as the PCR.
4. Review and approve.
5. Update `process.md`, increment its version, and log the change below.

### 15.3 Process Change Log

| PCR | Date | Version | Description | Author |
|---|---|---|---|---|
| — | 2026-02-28 | 0.1.0 | Initial process document created. | System |
| PCR-0001 | 2026-03-02 | 0.2.0 | Added mandatory CONTEXT.md & DEVLOG.md updates to DoD (§16) and Agent Workflow (§17 Step 13, Rule 6). Enables LLM context transfer between sessions. | Antigravity |
| PCR-0002 | 2026-03-02 | 0.3.0 | Added §0 Token Optimization Rules. Created AGENT_BOOT.md as single LLM boot file. Promotes compact table format for SRD/MD/UTCD. On-demand reading instead of upfront. | Antigravity |
| PCR-0003 | 2026-03-04 | 0.4.0 | Added SRD requirement status lifecycle (§4.4). Added `Reopen` status. Enforced agent editing and implementation guards in §4.2 and §17. | Antigravity |
| PCR-0004 | 2026-03-04 | 0.5.0 | Stripped noise from §4.2, §4.4, §17. Added §0 Rule 7: keep process documents minimal. | Antigravity |
| PCR-0005 | 2026-03-14 | 0.6.0 | Added tooling impact check to PCR procedure (§15.2 step 3). Added `audit_docs()` to `alm/parser.py` and amber warning banner to ALM UI — auto-detects parser/format mismatches on every load. | Antigravity |

---

## 16. Definition of Done (DoD)

A task (new feature, module, or fix) is **done** only when **all** of the following are true:

- [ ] FO exists and is approved (if new work).
- [ ] SRD requirements written, linked to FO, and approved.
- [ ] DD design items written, linked to SRD.
- [ ] MD modules defined, linked to SRD.
- [ ] UTCD test cases written for every module (before code).
- [ ] Code implemented, passes `ruff` + `black` + `mypy --strict`.
- [ ] All UTCD tests pass with ≥ 80 % coverage.
- [ ] Integration tests pass (if applicable).
- [ ] MCP schema validated (if module is MCP-exposed).
- [ ] Traceability matrix updated.
- [ ] Revision Note written with full artifact list and test summary.
- [ ] Commit pushed with proper convention.
- [ ] `CONTEXT.md` updated with current artifact status, open decisions, and known issues.
- [ ] `DEVLOG.md` updated with a new session entry (newest first) summarizing work done, decisions made, and next steps.

---

## 17. Agent Workflow Summary

When an AI agent receives a task at the **FO level**, it must execute the following steps **in order**, producing all artifacts. The agent must not skip steps.

```
┌──────────────────────────────────────────────────────────────────────┐
│  AGENT RECEIVES TASK (FO Level)                                      │
└──────────────┬───────────────────────────────────────────────────────┘
               │
               ▼
   ┌───────────────────────┐
   │ Step 1: Read Process  │  Read process.md, understand current rules
   │         Document      │
   └───────────┬───────────┘
               ▼
   ┌───────────────────────┐
   │ Step 2: Write/Update  │  Create or update FO.md with new FO entries
   │         FO Document   │  Assign FO-<TOOL>-NNN IDs
   └───────────┬───────────┘
               ▼
   ┌───────────────────────┐
   │ Step 3: Decompose     │  Write SRD entries for each FO
   │         into SRD      │  Assign SRD-<TOOL>-NNN.NNN IDs
   └───────────┬───────────┘
               ▼
   ┌───────────────────────┐
   │ Step 4: Create Design │  Write DD entries with diagrams, interfaces
   │         Document      │  Assign DD-<TOOL>-NNN.NNN.DNN IDs
   └───────────┬───────────┘
               ▼
   ┌───────────────────────┐
   │ Step 5: Decompose     │  Break SRDs into code modules
   │         into Modules  │  Assign MD-<TOOL>-NNN.NNN.MNN IDs
   └───────────┬───────────┘
               ▼
   ┌───────────────────────┐
   │ Step 6: Write UTCD    │  Define all test cases BEFORE coding
   │         (Test-First)  │  Assign UT-<TOOL>-NNN.NNN.MNN.TNN IDs
   └───────────┬───────────┘
               ▼
   ┌───────────────────────┐
   │ Step 7: Implement     │  Write code module by module
   │         Code          │  Include MD ID in file headers
   └───────────┬───────────┘
               ▼
   ┌───────────────────────┐
   │ Step 8: Run Tests     │  Execute pytest, verify all UTCD cases
   │                       │  Update UTCD status (Pass/Fail)
   └───────────┬───────────┘
               ▼
   ┌───────────────────────┐
   │ Step 9: Integration   │  Run integration tests if applicable
   │         Testing       │  Validate MCP schema if exposed
   └───────────┬───────────┘
               ▼
   ┌───────────────────────┐
   │ Step 10: Update       │  Fill in every row for this task
   │          Trace Matrix │
   └───────────┬───────────┘
               ▼
   ┌───────────────────────┐
   │ Step 11: Write        │  Mandatory final step
   │          Revision Note│  List all artifacts, test results, open items
   └───────────┬───────────┘
               ▼
    ┌───────────────────────┐
    │ Step 12: Verify DoD   │  Check every item in the DoD checklist
    │          Checklist    │  Task is COMPLETE only if all boxes checked
    └───────────┬───────────┘
               ▼
   ┌───────────────────────┐
   │ Step 13: Update       │  Update CONTEXT.md artifact status tables,
   │   CONTEXT.md &        │  open decisions, and known issues.
   │   DEVLOG.md           │  Add new session entry to DEVLOG.md (top).
   │                       │  This enables LLM context transfer.
   └───────────────────────┘
```

**Critical Agent Rules:**
1. **Never skip a phase.** Even if a phase seems trivial, produce the artifact.
2. **Always link IDs.** Every artifact must reference its parent.
3. **Test before declare done.** No task is complete without passing tests.
4. **Revision Note is mandatory.** This is the last step — no exceptions.
5. **If uncertain, re-read process.md.** This document is the single source of truth.
6. **Always update CONTEXT.md and DEVLOG.md.** This is the final action of every session — no exceptions. Even if a task is incomplete, update these files to record progress and enable the next agent to continue seamlessly.
7. **SRD status guard:** Only implement `Approved` requirements (→ set `Implemented` after). Only edit `Draft` or `Reopen` content.

---

## 18. Document Templates

All templates referenced in this process are defined inline within each phase section above. When the process reaches **Pilot** maturity (Level 1), standalone template files will be extracted to:

```
docs/templates/
  FO_TEMPLATE.md
  SRD_TEMPLATE.md
  DD_TEMPLATE.md
  MD_TEMPLATE.md
  UTCD_TEMPLATE.md
  RN_TEMPLATE.md
  ISS_TEMPLATE.md
  TRACE_TEMPLATE.md
```

---

*End of Process Document — PROC-001 v0.5.0*
