---
description: Write or extend ActionHub specifications by reading related roadmap, context, schema, and API docs, then updating spec index and planning references.
---

# Spec Writing Skill

Use this skill when asked to write a new specification, spec addendum, or document a backlog item before coding.

## Steps

1. Identify what to specify: check the user request, then read `BACKLOG.md` for scope if it's a B-* reference
2. Read `specs/README.md` — check existing specs to avoid duplication
3. Read `CODE_GENERATION_PLAN.md` — understand where the new spec fits in the roadmap
4. Read `specs/context.md` for project constraints and organization context
5. Read related existing specs (follow the "Depends On" column in `specs/README.md`)
6. Read `action_hub/db/schema.sql` for current table structures
7. Read `specs/specifications/S16_API_Contract.md` for endpoint patterns
8. Draft the specification using this structure:
   ```
   # SXX — Title
   **Date:** YYYY-MM-DD  |  **Version:** X.X  |  **Status:** 📋 Planned  |  **Depends On:** ...
   ## 1. Overview
   ## 2. Data Model (if new tables/columns)
   ## 3. Schema Changes (DDL)
   ## 4. API Endpoints
   ## 5. Backend Service Logic
   ## 6. Frontend Impact (if applicable)
   ## 7. Migration Plan
   ## 8. Test Plan
   ## 9. Glossary
   ```
9. Follow DB conventions: `XXX_FIELD_NAME` prefix, audit fields (`*_CREATED_AT`, etc.), bilingual `_en`/`_cn` suffix, 7 standard statuses
10. Follow API conventions: `/api/*` paths, `{ "data": ..., "meta": { "total": N } }` envelope, JWT auth
11. Cross-reference: verify no name conflicts with `S05_data_dictionary.md`, no endpoint conflicts with `S16_API_Contract.md`, no duplicate decisions in `specs/requirements/DECISIONS.md`
12. **Signal completion** by updating:
    - `specs/README.md` — add the new entry (status 📋 Planned)
    - `BACKLOG.md` — reference the new spec; mark backlog item as "spec ready"
    - `CODE_GENERATION_PLAN.md` — add the implementation phase for the new spec
    - `AGENT_STATUS.md` — log the spec writing activity
13. Do not write implementation code — only specifications
14. Do not modify existing specs without flagging the change to the user
15. Do not write execution results to the terminal; Bash-style terminal execution does not capture PI output correctly in this repo. When running PI spec checks or supporting scripts, capture stdout/stderr to log files and summarize the outcome separately
