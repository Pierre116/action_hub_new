---
description: Implement ActionHub code changes by reading the active batch, comparing specs to code, filling gaps, validating tests, and updating batch status files.
---

# Coding Skill

Use this skill when asked to implement a batch, write code, fix bugs, or fill spec-to-code gaps.

## Steps

1. Read `AGENTS.md` — find the **NEXT** batch under "Current Priorities"
2. Read `AGENT_STATUS.md` — confirm what was last completed
3. Read `CODE_GENERATION_PLAN.md` — locate the batch phase and its spec references
4. Read the **spec section(s)** referenced by the current batch (`specs/specifications/S*.md`)
5. Read the **existing code** in the target files listed in the batch
6. Read the **DB schema** (`action_hub/db/schema.sql`) for referenced tables/columns
7. Read the **API contract** (`specs/specifications/S16_API_Contract.md`) for referenced endpoints
8. Read the **test files** that cover the area being changed (`action_hub/tests/`)
9. **Compare**: List every requirement from the spec. For each, check if existing code implements it. Produce a **gap list**.
10. If no gaps exist, report "no changes needed" and skip to step 14.
11. **Implement**: Work through the gap list one item at a time, following these rules:
    - Parameterized SQL only (`?` placeholders) — never string interpolation
    - No ORM — raw SQL in `service.py` files
    - Business logic in services — `routes.py` handles HTTP only
    - API-first — all features must have JSON endpoints under `/api/*`
    - Security — no dynamic code execution; service handlers are whitelisted callables only
    - i18n — use `useTranslation()` hook in React; backend strings in `actionhub/i18n/*.json`
    - React conventions — `.tsx` files, TanStack Query for data fetching, `react-bootstrap` for UI
12. After implementing each gap, verify it passes tests
13. Run the full test suite: `cd action_hub && ../.venv/bin/python -m pytest tests/ -q --tb=short`
14. **Signal completion** by updating these files:
    - `AGENT_STATUS.md` — move the batch row to ✅ DONE, add notes and test counts
    - `CODE_GENERATION_PLAN.md` — mark the phase as DONE in the roadmap table
    - `AGENTS.md` — move the batch from NEXT to DONE, set the next batch as NEXT
15. Do not modify specs — only read them
16. Do not leave TODO/FIXME comments without implementing the code
17. Do not use `subprocess`, `eval`, `exec`, or `importlib` for dynamic handler loading
18. Do not write execution results to the terminal; Bash-style terminal execution does not capture PI output correctly in this repo. When running scripts, tests, or builds for PI tasks, capture stdout/stderr to log files and summarize the outcome separately
