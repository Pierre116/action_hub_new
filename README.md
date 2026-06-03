# ActionHub

ActionHub is a Flask + React platform for operational work management across teams.
It replaces spreadsheet logbooks with one web application for actions, meetings, decisions, dashboards, taxonomy administration, and process workflows.


## Repo Structure

```
actionhub/                        ← repo root (YOU ARE HERE)
│
├── specs/                        ← 📐 SPECIFICATIONS & REQUIREMENTS
│   ├── context.md                    Project context & constraints
│   ├── README.md                     Navigation index (status, deps, reading order)
│   ├── CODE_UPDATE_PLAN.md           Pending terminology rename plan
│   ├── archived/                     Superseded specs (R10, R12, S40, S45)
│   ├── requirements/                 R-series requirement files (R00–R18)
│   │   ├── R00_initial_vision.md
│   │   ├── R01_entities.md
│   │   ├── ...
│   │   ├── R18_readiness_management.md
│   │   └── DECISIONS.md              Architectural decisions log (D1–D198)
│   └── specifications/               S-series technical specs (S05–S80)
│       ├── S05_data_dictionary.md
│       ├── S10_MCD.md
│       ├── S16_API_Contract.md
│       ├── S70_workflow_engine_v3.md
│       └── S80_react_frontend_architecture.md
│
├── action_hub/                   ← 🐍 APPLICATION CODE
│   ├── app.py                        Flask app factory
│   ├── config.py                     Configuration (env vars)
│   ├── wsgi.py                       WSGI entry point
│   ├── init_db.py                    Create DB schema
│   ├── seed_data.py                  Seed reference data + admin account
│   ├── requirements.txt              Python dependencies
│   ├── actionhub/                    Flask blueprints (the actual app)
│   │   ├── actions/                  Action CRUD, assignments, comments
│   │   ├── admin/                    User/team/business theme admin
│   │   ├── auth/                     Login/logout (JWT)
│   │   ├── dashboard/                Personal + team + business theme dashboards
│   │   ├── evolution/                Change requests / evolution tracking
│   │   ├── export/                   Excel/PDF export
│   │   ├── feedback/                 In-app feedback system
│   │   ├── gantt/                    Gantt chart views
│   │   ├── i18n/                     en.json / zh.json (bilingual labels)
│   │   ├── meetings/                 Meeting CRUD, minutes, action linking
│   │   ├── middleware/               Auth middleware, request hooks
│   │   ├── notifications/            In-app alerts
│   │   ├── taxonomy/                 Teams, business themes, action types
│   │   ├── utils/                    Helpers (pagination, formatting, etc.)
│   │   └── workflow/                 Workflow engine V3, templates, instances
│   ├── db/                           SQLite DB + migration SQL files
│   ├── frontend/                     React 18 + TypeScript + Vite SPA source
│   ├── static/                       Build output (dist/), CSS, vendor assets
│   └── tests/                        Pytest test suite (~248 tests)
│
├── .github/
│   └── copilot-instructions.md   ← LLM coding assistant reference
├── CODE_GENERATION_PLAN.md       ← Generation phases & status tracker
├── AGENTS.md                     ← Agent instructions & batch definitions
└── BACKLOG.md                    ← Unscheduled feature requests
```

## Tech Stack

| Layer | Choice |
|-------|--------|
| Backend | Python 3.12 / Flask 3.x |
| Database | SQLite (WAL mode, raw SQL, no ORM) |
| Frontend | React 18 + TypeScript + Vite 5 (SPA served by Flask from `static/dist/`) |
| UI Framework | react-bootstrap, TanStack Query v5, TanStack Table v8 |
| i18n | Custom `useTranslation()` hook + inline catalogs (en/zh) |
| Charts | react-chartjs-2 / Chart.js |
| Auth | JWT (PyJWT) — tokens in sessionStorage |
| WSGI | Waitress |
| Tests | pytest backend suite + Vite production build |

## Architecture

- **Backend:** Flask serves JSON APIs under `/api/*` and the SPA shell for authenticated navigation.
- **Frontend:** React 18 + TypeScript + Vite SPA built into `action_hub/static/dist/`.
- **Auth:** JWT Bearer access/refresh tokens, attached by Axios interceptors.
- **Workflow model:** process workflows are launched from the workflow area; they are not auto-started from action creation.
- **Workflow runtime note:** request-type workflows now instantiate directly as workflow runtime records without forcing a supporting `t_action` row. Older action-linked workflow records remain supported for compatibility.
- **Primary as-built references:** `specs/specifications/S16_API_Contract.md`, `specs/specifications/S80_react_frontend_architecture.md`, `CODE_GENERATION_PLAN.md`.

## Key Conventions

- **7 statuses everywhere:** Open / In Progress / Under Review / On Hold / Done / Cancelled / Postponed
- **Field codes:** `XXX_FIELD_NAME` (3-letter entity prefix + UPPER_SNAKE)
- **Bilingual taxonomy:** columns end in `_en` / `_cn` (e.g. `top_name_en`, `top_name_cn`)
- **Business Theme** (业务主题) = subject classification (`t_topic`, `TOP_*`, `act_topic_id`)
- **Action Type** (行动类型) = nature classification (`t_category`, `CAT_*`, `act_category_id`)
- All UI strings go through `i18n/en.json` and `i18n/zh.json` — never hardcode display text

## User Guidance

- End-user/admin operating guide: `HOW_TO.md`
- In-app instructions screen: `/instructions`
- Main user-flow SOP: `specs/specifications/S90_SOP_Main_User_Flows.md`
- Chinese SOP: `specs/specifications/S90_SOP_Main_User_Flows.zh.md`
- Workflow runtime entry: use the workflow dashboard and workflow workbench rather than action detail as the primary operating surface

## Quick Start

```python
import os
import subprocess

os.chdir(r"C:\Users\leung\Documents\Digitalization\actionhub\action_hub")
subprocess.run([r"..\.venv\Scripts\python.exe", "-m", "pip", "install", "-r", "requirements.txt"], check=True)
subprocess.run([r"..\.venv\Scripts\python.exe", "init_db.py"], check=True)
subprocess.run([r"..\.venv\Scripts\python.exe", "seed_data.py"], check=True)
subprocess.run([r"..\.venv\Scripts\python.exe", "app.py"], check=True)
```

## Where to Start Reading

| Goal | Start here |
|------|-----------|
| Understand the project | `specs/context.md` |
| Navigate all specs | `specs/README.md` |
| See all entities & fields | `specs/specifications/S05_data_dictionary.md` |
| See the DB schema | `action_hub/db/schema.sql` or `specs/specifications/S20_MLD.md` |
| See the API contract | `specs/specifications/S16_API_Contract.md` |
| Understand requirements | `specs/requirements/R00_initial_vision.md` → R01 → R02 … |
| React frontend architecture | `specs/specifications/S80_react_frontend_architecture.md` |
| Workflow V3 engine | `specs/specifications/S70_workflow_engine_v3.md` |
| Readiness management | `specs/requirements/R18_readiness_management.md` |
| See workflow + implementation roadmap | `CODE_GENERATION_PLAN.md` |
| Run tests | `action_hub/tests/` + `action_hub/frontend` build |
