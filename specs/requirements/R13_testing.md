# ActionHub — Testing Strategy

> **Status**: Requirements-level specification  
> **Current state**: As-built testing baseline for the Flask API + React SPA runtime  
> **Depends on**: All active product requirements  
> **Consumed by**: backend pytest execution, frontend production build validation, roadmap closeout

---

## §1 Objectives

| # | Objective |
|---|-----------|
| T1 | Detect regressions across auth, actions, meetings, decisions, dashboards, workflow, and admin modules |
| T2 | Validate the published API contract against actual Flask responses and authorization behavior |
| T3 | Verify current product rules such as manual workflow start, meeting-linked constraints, and admin-only surfaces |
| T4 | Validate the React SPA through successful TypeScript/Vite production builds |
| T5 | Provide a repeatable local validation routine for documentation, code, and roadmap reconciliation |

---

## §2 Scope

### In Scope

| Layer | What is validated |
|-------|-------------------|
| Backend API | JSON endpoints, auth handling, validation, status codes, and error envelopes |
| Business rules | Action lifecycle, assignment restrictions, meeting visibility, workflow lifecycle, and attachments |
| Data integrity | Schema constraints, migrations, seed compatibility, graph validation |
| Frontend integration | Route compilation, shared components, workflow builder, and production bundle generation |
| Documentation-critical flows | Instructions route, workflow launch model, dashboard navigation, and meeting/action behavior |

### Out of Scope

| Layer | Reason |
|-------|--------|
| Browser E2E | No maintained Playwright/Cypress suite in the current baseline |
| Large-scale load testing | Current pass is correctness-focused |
| Visual regression | Not part of the current engineering workflow |

---

## §3 Primary Test Types

### §3.1 Backend Integration Tests

- Use pytest under `action_hub/tests/`
- Use Flask test client flows against isolated SQLite test databases
- Cover auth, actions, meetings, decisions, dashboards, workflow, admin, export, and related services

### §3.2 Focused Regression Tests

- Use targeted pytest runs when closing a known defect or behavior mismatch
- Follow them with the full suite before closeout

### §3.3 Frontend Validation

- Build the React SPA with Vite from `action_hub/frontend/`
- Treat route import errors, JSX/TypeScript errors, and bundle failures as release blockers for UI changes

---

## §4 Standard Validation Commands

### Backend

From `action_hub/`:

```python
import subprocess
subprocess.run([r"..\.venv\Scripts\python.exe", "-m", "pytest", "tests/", "-q", "--tb=short"], check=True)
```

### Frontend

From `action_hub/frontend/`:

```python
import subprocess
subprocess.run(["npm", "run", "build"], check=True)
```

---

## §5 Acceptance Bar

| Area | Requirement |
|------|-------------|
| Backend suite | Must pass without newly introduced failures |
| Frontend build | Must complete successfully |
| Changed files | Must be free of editor-reported syntax/type errors |
| Closeout notes | Must identify what was audited, changed, and validated |

---

## §6 Guidance

- Prefer the full backend suite over partial confidence claims.
- Pair frontend route/navigation changes with a production build.
- When workflow behavior changes, validate both process-first runtime paths and any compatibility paths that remain.
