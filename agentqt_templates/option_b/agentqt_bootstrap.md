# AgentQt Bootstrap Prompt
# Agentic Waterfall Claude Code Framework for Python PyQt6 Projects
#
# HOW TO USE:
# 1. Create your project folder: mkdir <your_project_name>
# 2. Inside it, create idea.md and requirements.md (see format below)
# 3. Open the project root in Claude Code
# 4. Paste this entire file as your first message
# ─────────────────────────────────────────────────────────────────────────────

You are setting up the **AgentQt** framework — an Agentic Waterfall Claude Code
Framework for Python PyQt6 Projects.

Your job is to read the user's project definition files and generate a complete,
working AgentQt project scaffold. Follow every step below exactly.

---

## STEP 1 — Locate Project Definition Files

Ask the user for their project folder name, then read:
- `<project_name>/idea.md`
- `<project_name>/requirements.md`

If either file is missing, stop and instruct the user:

> Create `<project_name>/idea.md` with:
> - What is the project?
> - What problem does it solve?
> - Who uses it?
> - What are the main features at a high level?
>
> Create `<project_name>/requirements.md` with:
> - What are the main functional areas / tools? (e.g. Screener, Dashboard)
> - For each area: what should it do?
> - Any technical constraints?
> - Any non-functional requirements?

---

## STEP 2 — Extract Tool Codes

From `requirements.md`, identify all functional areas and assign each a
3-letter uppercase tool code. Rules:
- Must be unique
- Should be intuitive abbreviation of the area name
- Reserved codes (do not use): `BKT` (backtesting, always last)

Example extraction:
```
requirements.md mentions: Screener, Analysis, Execution, GUI, Infrastructure
→ SCR, ANA, EXE, GUI, INF
```

---

## STEP 3 — Generate CLAUDE.md

Write `CLAUDE.md` at the repo root using this template, substituting all
`{{placeholders}}`:

```markdown
# {{PROJECT_TITLE}} — Claude Instructions

**Active project:** `{{project_name}}`. Do NOT work on other folders unless
explicitly directed.

## Step 1 — Classify Every Prompt First

Silently classify before reading any file:

| Class | Trigger | Action |
|-------|---------|--------|
| **Q** | General question, no project work needed | Read nothing |
| **N** | Status check, "what's next?", navigation | Read `AGENT_BOOT.md` §2 only |
| **D** | Code, docs, tests, bug fix, any dev task | Read `AGENT_BOOT.md` §2–§4, then active tool docs only |
| **S** | First prompt of a new session | Read full `AGENT_BOOT.md` once |

Never read `requirements.md` or `idea.md` unless `AGENT_BOOT.md` §5 directs you to.

## Step 2 — Evaluate Before Acting (Class D and S)

Before executing any Class D or S prompt, delegate to the `prompt-evaluator` agent:
1. Pass the raw prompt to the agent
2. The agent classifies, identifies the active tool and artifact phase, checks
   clarity, and returns a reframed structured prompt
3. If the agent asks clarifying questions — stop and surface them to the user
4. Only act on the reframed prompt, not the original

## Session-End Rule

Update `{{project_name}}/CONTEXT.md` §0 and prepend to
`{{project_name}}/DEVLOG.md` before finishing every session.

## Always-On Rules

- `.claude/rules/code-style.md`
- `.claude/rules/testing.md`
- `.claude/rules/artifact-conventions.md`
- `.claude/rules/traceability.md`
```

---

## STEP 4 — Generate AGENT_BOOT.md

Write `AGENT_BOOT.md` at repo root. Substitute `{{tool_codes}}` with the list
extracted in Step 2, and `{{project_name}}` with the project folder name.

Use this exact content:

```markdown
# AGENT BOOT — {{PROJECT_TITLE}}

> **Active project:** `{{project_name}}`.

## §1 — Prompt Classification

| Class | Trigger | Agents | File reads |
|---|---|---|---|
| **Q** | General question | None | None |
| **N** | Status check | None | `CONTEXT.md §0` only |
| **D** | Any dev task | `prompt-evaluator` first | Per dev-context |
| **S** | First prompt of session | `prompt-evaluator` first | Full `AGENT_BOOT.md` |

## §2 — Agent Registry

**Gate agents (Haiku):**

| Agent | Purpose | Invoke |
|---|---|---|
| `prompt-evaluator` | Classify D/S prompts, reframe or clarify | Always first for D/S |
| `duplicate-detector` | Scan existing artifacts before writing new ones | Start of new-feature/auto-feature |
| `artifact-validator` | Check ID chains after each artifact phase | After every FO/SRD/DD/MD/UTCD write |
| `phase-gate` | Verify SRDs Approved + UTCD complete before code | Before Phase 6 in new-feature/auto-feature |
| `session-finalizer` | Sync TRACE.md, update CONTEXT.md, prepend DEVLOG | Final step of every command |

**Implementation agents (Sonnet):**

| Agent | Purpose | Invoke |
|---|---|---|
| `pyqt-architect` | GUI design: panels, signals, widget layout | Any GUI design question |
| `pyqt-code-writer` | Write new PyQt6 files from blueprint | After architect blueprint |
| `pyqt-code-reviewer` | Post-code gate for all PyQt6 files | After every PyQt6 write/edit |
| `pyqt-code-simplifier` | Complexity reduction | Only when reviewer flags MEDIUM+ |
| `test-writer` | Implement UTCD pytest test cases | When UTCD phase begins |
| `code-reviewer` | Post-code gate for non-GUI Python files | After every non-GUI write/edit |

## §3 — Active Tools

{{tool_codes}}

## §4 — When NOT to Invoke Agents

- Bug fix on single module → skip pyqt-architect
- Refactor within one file → skip pyqt-architect
- Comment/doc-only change → skip all agents
- Test-only change → skip code-reviewer; use test-writer directly
- Class Q/N prompts → skip prompt-evaluator
- pyqt-code-simplifier → never proactively; only on reviewer signal
- duplicate-detector → skip when FO anchor ID already known
- artifact-validator → skip for code-only or test-only changes
- phase-gate → skip for bug fixes and refactors on Implemented SRDs
- session-finalizer → skip for read-only tasks

## §5 — Full Project State

`{{project_name}}/CONTEXT.md §0`
```

---

## STEP 5 — Generate Project Files

Write the following inside `<project_name>/`:

**CONTEXT.md:**
```markdown
# {{PROJECT_TITLE}} — Current Context

**Last Updated:** {{today}}
**Session:** 1

## 0. Immediate Next Step

**Current:** Project initialized. Begin with first FO using /new-feature.

No features implemented yet.
```

**DEVLOG.md:**
```markdown
# Development Log — {{PROJECT_TITLE}}

---

## Session 1 — {{today}}

- Project initialized with AgentQt framework
- Tool codes assigned: {{tool_codes_inline}}
- CLAUDE.md, AGENT_BOOT.md, CONTEXT.md created
- Docs folder structure created for all tools
- Ready to begin feature development
```

---

## STEP 6 — Generate Docs Folder Structure

For each tool code, create:
```
<project_name>/docs/<tool_lowercase>/
    FO.md       ← blank with header only
    SRD.md      ← blank with header only
    DD.md       ← blank with header only
    MD.md       ← blank with header only
    UTCD.md     ← blank with header only
    TRACE.md    ← blank with header only
```

Each blank file header format:
```markdown
# <TOOL_NAME> — <Artifact Type>
**Tool:** <TOOL_CODE>
**Project:** {{project_name}}
**Version:** 0.0.1
**Last Updated:** {{today}}

---

_(No entries yet. Use /new-feature to begin.)_
```

---

## STEP 7 — Report to User

Print a summary:

```
AgentQt initialized for: {{PROJECT_TITLE}}

Tool codes assigned:
  {{tool_code_1}} — {{tool_area_1}}
  {{tool_code_2}} — {{tool_area_2}}
  ...

Files generated:
  CLAUDE.md
  AGENT_BOOT.md
  {{project_name}}/CONTEXT.md
  {{project_name}}/DEVLOG.md
  {{project_name}}/docs/<tool>/ × N tools

Next step: Run /new-feature to start your first feature.
```

---

## IMPORTANT RULES FOR SETUP

- Never skip a step
- Never create FO/SRD/DD content yet — only blank headers
- Never modify .claude/agents/ or .claude/rules/ — those are framework files
- If idea.md or requirements.md is unclear, ask before generating
- All file paths use the project folder name, not "project_name" literally
