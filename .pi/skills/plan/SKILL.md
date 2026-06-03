---
description: Plan the next ActionHub implementation batch by reading the roadmap, specs, current code, and producing an actionable task list with validation steps.
---

# Planning Skill

Use this skill when asked to plan implementation work, produce a task list for a batch, or figure out what to work on next.

## Steps

1. Read `CODE_GENERATION_PLAN.md` — find the next non-DONE phase in the roadmap table
2. Read `AGENT_STATUS.md` — confirm the last completed batch and test baseline
3. Read `AGENTS.md` — check the current NEXT batch; plan the one after it, or refine the current one if no plan exists yet
4. Read the full spec section(s) for the target batch (specs are in `specs/specifications/S*.md`)
5. Read `specs/specifications/S16_API_Contract.md` for affected endpoints
6. Read `action_hub/db/schema.sql` for current schema state
7. Read existing source files in the target module to understand what already exists
8. For each task in the plan, output:
   - **Task ID** (e.g., `<batch>.1`, `<batch>.2`)
   - **What**: One-sentence description
   - **Spec ref**: Section and decision ID (e.g., S70 §4.5, D186)
   - **Files**: Which files to create or modify
   - **Depends on**: Which prior tasks must be done first
   - **Test**: How to verify it works
9. Keep task granularity at ~30 minutes of implementation work per task
10. Include migration tasks when schema changes are needed
11. End with a verification section (test commands + expected results)
12. **Signal completion**: Update `AGENTS.md` — replace or add the batch instructions section with the new plan
13. Do not plan backlog items (B-*) unless the user explicitly requests it
14. Do not write code — only produce plans
15. Do not write execution results to the terminal; Bash-style terminal execution does not capture PI output correctly in this repo. When validating PI planning work with scripts or checks, capture stdout/stderr to log files and summarize the outcome separately
