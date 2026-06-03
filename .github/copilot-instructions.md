# Copilot Instructions for ActionHub

## What ActionHub Is

A Flask + SQLite action-tracking platform for the organization (~300 employees, 12 teams). Replaces Excel logbooks with unified action management, meetings, dashboards, and a workflow engine.

## Repo Layout

```
actionhub/                        ← repo root
├── README.md                     ← START HERE — structure, stack, quick start
├── AGENTS.md                     ← agent instructions (static: rules, architecture, conventions)
├── specs/                        ← specifications & requirements
│   ├── context.md                    project context & constraints
│   ├── README.md                     navigation index (status, deps, reading order)
│   ├── CODE_UPDATE_PLAN.md           pending terminology rename plan
│   ├── archived/                     superseded specs (R10, R12, S40, S45)
│   ├── requirements/R*.md            domain requirements (R00–R18)
│   └── specifications/S*.md          technical specs (S05–S80)
├── action_hub/                   ← application code
│   ├── app.py                        Flask app factory
│   ├── config.py                     env-based configuration
│   ├── actionhub/                    Flask blueprints
│   │   ├── actions/                  Action CRUD, assignments, comments
│   │   ├── admin/                    User/team/business theme admin
│   │   ├── auth/                     Login/logout (JWT)
│   │   ├── dashboard/                Personal, team, business theme dashboards
│   │   ├── evolution/                Change requests / evolution tracking
│   │   ├── export/                   Excel/PDF export
│   │   ├── feedback/                 In-app feedback
│   │   ├── gantt/                    Gantt views
│   │   ├── i18n/                     en.json, zh.json
│   │   ├── meetings/                 Meeting CRUD, minutes
│   │   ├── middleware/               Auth middleware, request hooks
│   │   ├── notifications/            In-app alerts
│   │   ├── taxonomy/                 Teams, business themes, action types
│   │   ├── utils/                    Helpers (pagination, formatting, etc.)
│   │   └── workflow/                 Workflow engine V3, templates, instances
│   ├── db/                           SQLite DB + migration SQL
│   ├── frontend/                     React 18 + TypeScript + Vite SPA source
│   ├── static/                       Build output (dist/), CSS, vendor assets
│   └── tests/                        pytest suite (~254 tests)
└── CODE_GENERATION_PLAN.md       ← SINGLE SOURCE OF TRUTH: batch status, current batch (NEXT), roadmap
```

## Architecture

- **Backend:** Python 3.12 / Flask 3.x, raw SQL (no ORM), parameterized queries only
- **Database:** SQLite, WAL mode, single file at `action_hub/db/actionhub.db`
- **Frontend:** React 18 + TypeScript + Vite 5 SPA; react-bootstrap, TanStack Query v5/Table v8, React Hook Form, react-chartjs-2; served by Flask from `action_hub/static/dist/`
- **Auth:** JWT (PyJWT) — tokens in sessionStorage, Axios interceptors for automatic refresh
- **i18n:** Custom `useTranslation()` hook with inline catalogs (~340 lines per language); backend strings in `actionhub/i18n/en.json` / `zh.json`
- **Tests:** pytest, `action_hub/tests/`, 263 tests (2026-03-15)

## DB Conventions

- Field codes: `XXX_FIELD_NAME` (3-letter entity prefix + UPPER_SNAKE_CASE)
- Audit fields: `*_CREATED_AT`, `*_UPDATED_AT`, `*_VERSION`, `*_DELETED_AT`
- Bilingual taxonomy columns: `_en` / `_cn` suffix (e.g. `top_name_en`, `top_name_cn`)
- 7 statuses everywhere: Open, In Progress, Under Review, On Hold, Done, Cancelled, Postponed

## Terminology

| Concept | DB table | Prefix | UI label (EN) | UI label (ZH) |
|---------|----------|--------|---------------|---------------|
| Business Theme | `t_topic` | `TOP_*` | Business Theme | 业务主题 |
| Action Type | `t_category` | `CAT_*` | Action Type | 行动类型 |
| Action | `t_action` | `ACT_*` | Action | 行动项 |
| Meeting | `t_meeting_instance` | `MIN_*` | Meeting | 会议 |
| Workflow | `t_workflow_template` | `WFT_*` | Workflow | 工作流 |

## Key Files for Context

| Purpose | File |
|---------|------|
| Project context | `specs/context.md` |
| Spec navigation index | `specs/README.md` |
| All entities & fields | `specs/specifications/S05_data_dictionary.md` |
| DB schema | `action_hub/db/schema.sql` |
| API contract | `specs/specifications/S16_API_Contract.md` |
| Requirements overview | `specs/requirements/R00_initial_vision.md` |
| Workflow V3 engine | `specs/specifications/S70_workflow_engine_v3.md` |
| React frontend architecture | `specs/specifications/S80_react_frontend_architecture.md` |
| Readiness management | `specs/requirements/R18_readiness_management.md` |
| Meeting series workspace | `specs/requirements/R19_meeting_series_workspace.md` |
| Rename rollout plan | `specs/CODE_UPDATE_PLAN.md` |
| Unified implementation roadmap + batch status | `CODE_GENERATION_PLAN.md` |
| Frontend/backend separation | `specs/specifications/S60_frontend_backend_separation.md` |

## Dev Commands

```python
import subprocess, os
os.chdir(r"C:\Users\leung\Documents\Digitalization\actionhub\action_hub")
subprocess.run([r"..\.venv\Scripts\python.exe", "-m", "pip", "install", "-r", "requirements.txt"], check=True)
subprocess.run([r"..\.venv\Scripts\python.exe", "init_db.py"], check=True)
subprocess.run([r"..\.venv\Scripts\python.exe", "seed_data.py"], check=True)
subprocess.run([r"..\.venv\Scripts\python.exe", "app.py"])
```

Default login: `admin` / `Admin@2026`

## Testing

```python
import subprocess, os
os.chdir(r"C:\Users\leung\Documents\Digitalization\actionhub\action_hub")
subprocess.run([r"..\.venv\Scripts\python.exe", "-m", "pytest", "tests/", "-q"], check=True)
```

## Shell Restriction

- PI execution must use Python only.
- Do not use PowerShell, `cmd`, `cmd /c`, or `.bat` wrappers for PI tasks.
- If an external tool must be invoked, call it from Python `subprocess`.
- Do not print Python script results to the terminal for PI tasks; write results to log files and summarize them separately when needed.
- If the environment is Windows, do not use Linux shell commands such as `ls`, `grep`, `pwd`, `cat`, or similar Unix-only shortcuts. Use Python file operations and Windows-appropriate equivalents instead.

## Rules

- Always use `useTranslation()` hook in React components for display text — never hardcode UI strings
- Use parameterized SQL (`?` placeholders) — never interpolate user input into queries
- No ORM — all queries are raw SQL in service files
- Keep business logic in `service.py` files, HTTP handling in `routes.py`
- All new features must be API-first (JSON endpoints under `/api/*`)
- Keep `render_template()` routes minimal — Flask only serves the SPA shell
- React source lives in `action_hub/frontend/` (TypeScript + Vite) with build output in `action_hub/static/dist/`
- React components: use `.tsx` files, TanStack Query for data fetching, `react-bootstrap` for UI, `useTranslation()` for i18n — never raw `fetch()` or manual DOM manipulation in new frontend code
