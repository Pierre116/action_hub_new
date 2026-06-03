# ActionHub — Agent Instructions

## What This Project Is

ActionHub is a Flask + SQLite action-tracking platform for the organization (~300 employees, 12 teams).
It replaces Excel logbooks with unified action management, meetings, dashboards, and a workflow engine.

**Current branch**: `actionhub_workload_management`
**Current version**: V3.6
**Dev OS**: Windows or Linux (instructions below cover both)
**Python venv**: `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (Linux) — relative to repo root

---

## Agent Tooling

### GitHub Copilot Chat Agents

Three custom agents in `.github/agents/` for use with GitHub Copilot Chat:

| Agent | Invoke with | Purpose |
|-------|-------------|---------|
| `@planning_agent` | `@planning_agent plan the next batch` | Reads roadmap + specs, produces step-by-step implementation plan |
| `@agent_code` | `@agent_code implement the current batch` | 4-phase protocol: Read spec → Compare with code → Implement gaps → Run tests |
| `@spec_writer` | `@spec_writer write spec for B-2` | Writes new spec sections following Merise conventions |

### Pi Coding Agent

Pi picks up this `AGENTS.md` automatically. Additional pi-specific files in `.pi/`:

| Type | Path | Usage |
|------|------|-------|
| Skill | `.pi/skills/plan/` | `/skill:plan` — planning workflow |
| Skill | `.pi/skills/code/` | `/skill:code` — implementation workflow |
| Skill | `.pi/skills/spec/` | `/skill:spec` — spec writing workflow |
| Prompt | `.pi/prompts/status.md` | `/status` — project status check |
| Prompt | `.pi/prompts/test.md` | `/test` — run tests + report |
| Prompt | `.pi/prompts/gaps.md` | `/gaps` — spec-vs-code gap analysis |
| Prompt | `.pi/prompts/build.md` | `/build` — frontend build |

### Recommended Workflow (any agent)

1. **Plan** → produces a numbered task list in `CODE_GENERATION_PLAN.md`
2. **Code** → implements each task, comparing code against spec at every step
3. **Spec** → used when a backlog item needs a spec before coding
4. **All agents signal completion** by updating `CODE_GENERATION_PLAN.md` only

---

## Repo Layout

```
actionhub/                        ← repo root (you are here)
├── AGENTS.md                         ← this file
├── CODE_GENERATION_PLAN.md           ← MASTER ROADMAP — read this first
├── BACKLOG.md                        ← future feature requests
├── specs/                            ← all specifications
│   ├── context.md                        project context & constraints
│   ├── CODE_UPDATE_PLAN.md               pending terminology rename plan
│   ├── requirements/R*.md                domain requirements (R00–R16)
│   └── specifications/S*.md             technical specs (S05–S70)
└── action_hub/                       ← application code
    ├── app.py                            Flask app factory
    ├── config.py                         env-based configuration
    ├── actionhub/                        Flask blueprints
    │   ├── actions/                      Action CRUD, assignments, comments
    │   ├── admin/                        User/team/business theme admin
    │   ├── auth/                         Login/logout
    │   ├── dashboard/                    Personal, team, business theme dashboards
    │   ├── evolution/                    Change requests / evolution tracking
    │   ├── export/                       Excel/PDF export
    │   ├── feedback/                     In-app feedback
    │   ├── gantt/                        Gantt views
    │   ├── i18n/                         en.json, zh.json (bilingual UI strings)
    │   ├── meetings/                     Meeting CRUD, minutes
    │   ├── middleware/                   Auth middleware, request hooks
    │   ├── migrations/                   DB migration helpers
    │   ├── notifications/                In-app alerts
    │   ├── taxonomy/                     Teams, business themes, action types
    │   ├── utils/                        Helpers (pagination, formatting, misc.)
    │   └── workflow/                     Workflow engine, YAML builder, canvas
    ├── db/                               SQLite DB + migration SQL
    ├── static/                           CSS, JS, vendor assets
    └── tests/                            pytest suite (~254 tests)
```

---

## Architecture

- **Backend**: Python 3.12 / Flask, raw SQL (no ORM), parameterized queries only (`?` placeholders)
- **Database**: SQLite, WAL mode, single file at `action_hub/db/actionhub.db`
- **Frontend (current runtime)**: React 18 SPA served by Flask from `action_hub/static/dist/`
- **Legacy frontend**: Jinja2 + HTMX runtime removed during SEP-4 cleanup
- **Frontend (target)**: React 18 + TypeScript + Vite 5; react-bootstrap, TanStack Query v5, TanStack Table v8, React Router v6, react-i18next, React Hook Form, react-chartjs-2; build output in `action_hub/static/dist/`
- **i18n**: Display strings in `actionhub/i18n/en.json` / `zh.json` — never hardcode UI text
- **Tests**: pytest, `action_hub/tests/`, ~81% coverage, 254 passed / 5 pre-existing failures

### Architecture Notes (V3.6 updates)

- **Decisions list**: `team_projects_only` filter removed from frontend and backend. All decisions are shown to authenticated users by default.
- **Actions list**: `lead_only=true` is now the default filter — shows only actions where the current user is Lead (`act_owner_id`). Users can toggle "My Lead" switch to see all.
- **Team Dashboard**: GET `/api/dashboard/team-lead` now returns `by_lead` and `by_category` grouped arrays. The frontend uses an outer `<Tabs>` (Overview / By Lead / By Category) mirroring the Personal Dashboard.

### Agent Troubleshooting Note (Linux venv path)

If you see an error like `No such file or directory: '../.venv/bin/python'` when running tests or scripts, check your working directory:

- If you are in the project root (`/home/pierre/Github/actionhub`), use `.venv/bin/python` (no leading `../`).
- If you are in a subdirectory, adjust the path accordingly.

The virtual environment should be referenced relative to your current directory. Using `../.venv/bin/python` from the project root will fail because it looks for the venv in the parent directory.

### DB Conventions

- Field codes: `XXX_FIELD_NAME` (3-letter prefix + UPPER_SNAKE_CASE)
- Audit fields: `*_CREATED_AT`, `*_UPDATED_AT`, `*_VERSION`, `*_DELETED_AT`
- Bilingual taxonomy: `_en` / `_cn` suffix (e.g. `top_name_en`, `top_name_cn`)
- 7 statuses everywhere: Open, In Progress, Under Review, On Hold, Done, Cancelled, Postponed

### Terminology (DB internal → UI display)

| DB table | DB prefix | UI label (EN) | UI label (ZH) |
|----------|-----------|---------------|---------------|
| `t_topic` | `TOP_*` | Business Theme | 业务主题 |
| `t_category` | `CAT_*` | Action Type | 行动类型 |
| `t_action` | `ACT_*` | Action | 行动项 |
| `t_meeting_instance` | `MIN_*` | Meeting | 会议 |
| `t_workflow_template` | `WFT_*` | Workflow | 工作流 |

### Backend Setup / Run

**Windows:**
```python
import subprocess, os
os.chdir(r"C:\Users\leung\Documents\Digitalization\actionhub\action_hub")
subprocess.run([r"..\.\.venv\Scripts\python.exe", "-m", "AGENTp", "install", "-r", "requirements.txt"], check=True)
subprocess.run([r"..\.\.venv\Scripts\python.exe", "init_db.py"], check=True)
subprocess.run([r"..\.\.venv\Scripts\python.exe", "seed_data.py"], check=True)
subprocess.run([r"..\.\.venv\Scripts\python.exe", "app.py"])  # dev server → http://localhost:5000
```

**Linux:**
```bash
cd action_hub
../.venv/bin/python -m AGENTp install -r requirements.txt
../.venv/bin/python init_db.py
../.venv/bin/python seed_data.py
../.venv/bin/python app.py  # dev server → http://localhost:5000
```

- `migrations/migrate_v5_0.py` is reserved for workflow V3 alpha schema changes.

Default login: `admin` / `Admin@2026`

### Running Tests

**Windows:**
```python
import subprocess, os
os.chdir(r"C:\Users\leung\Documents\Digitalization\actionhub\action_hub")
os.makedirs(r"C:\Users\leung\Documents\Digitalization\actionhub\logs", exist_ok=True)
with open(r"C:\Users\leung\Documents\Digitalization\actionhub\logs\AGENT_pytest.log", "w", encoding="utf-8") as log_file:
    subprocess.run([r"..\.\.venv\Scripts\python.exe", "-m", "pytest", "tests/", "-q", "--tb=short"], check=True, stdout=log_file, stderr=subprocess.STDOUT)
```

**Linux:**
```bash
cd action_hub
../.venv/bin/python -m pytest tests/ -q --tb=short
```

Do not use `.bat`, `cmd`, or PowerShell wrappers for AGENT execution on Windows. Use Python directly.

### Frontend Dev / Build

**Windows:**
```python
import subprocess, os
os.chdir(r"C:\Users\leung\Documents\Digitalization\actionhub\action_hub\frontend")
subprocess.run(["npm", "config", "set", "registry", "https://registry.npmmirror.com"], check=True)
subprocess.run(["npm", "config", "set", "strict-ssl", "false"], check=True)
os.makedirs(r"C:\Users\leung\Documents\Digitalization\actionhub\logs", exist_ok=True)
with open(r"C:\Users\leung\Documents\Digitalization\actionhub\logs\AGENT_npm_install.log", "w", encoding="utf-8") as log_file:
    subprocess.run(["npm", "install", "--loglevel", "verbose"], check=True, stdout=log_file, stderr=subprocess.STDOUT)
with open(r"C:\Users\leung\Documents\Digitalization\actionhub\logs\AGENT_npm_build.log", "w", encoding="utf-8") as log_file:
    subprocess.run(["npm", "run", "build"], check=True, stdout=log_file, stderr=subprocess.STDOUT)
subprocess.run(["npm", "run", "dev"])
```

**Linux:**
```bash
cd action_hub/frontend
npm install
npm run build
npm run dev
```

Do not use `.bat`, `cmd`, or PowerShell wrappers for AGENT frontend work on Windows. Use Python directly.

---

## Current Priorities — Where to Start

> **Single source of truth for batch status and current tasks:** `CODE_GENERATION_PLAN.md`
>
> Read `CODE_GENERATION_PLAN.md` to find out:
> - What has been completed (DONE batches)
> - What the current batch is (NEXT)
> - The detailed task list for the current batch
> - What comes after (roadmap)

---

## Coding Rules

### General
1. **Parameterized SQL only** — never interpolate user input: `db.execute("SELECT ... WHERE id = ?", (id,))`
2. **No ORM** — all queries are raw SQL in `service.py` files
3. **Business logic in services** — `routes.py` handles HTTP; `service.py` handles logic and SQL
4. **Thin routes** — `render_template()` pages should be shells; data via JSON endpoints
5. **i18n always** — use `useTranslation()` hook in React; never hardcode display text
6. **API-first** — every UI feature needs a JSON endpoint independent of template rendering
7. **React conventions** (when writing frontend): `.tsx` files, TanStack Query for data fetching, `react-bootstrap` for UI, and the currently active i18n approach
8. **Security**: OWASP Top 10 compliance — no SQL injection, no XSS, validate at boundaries

### Testing Rules
1. **Test file organization**: All test files go in `action_hub/tests/` directory
2. **Test package**: Create `tests/__init__.py` to make it a proper Python package (required for imports)
3. **Test class pattern**: Always extend `AppTestCase` from `tests.conftest`:
   ```python
   from tests.conftest import AppTestCase
   
   class MyTests(AppTestCase):
       def test_something(self):
           self.login_admin()
           # use self.client for requests
   ```
4. **Use self.client**: All HTTP requests in tests must use `self.client`, not creating a new test client
5. **Test signatures**: Always include `self` as the first parameter for test methods
6. **Always return responses**: AAGENT endpoints must always return a response (never `return None`)
7. **Run tests with**: `../.venv/bin/python -m pytest tests/ -q --tb=short` (Linux) or `..\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short` (Windows) from the `action_hub` directory
8. **Shell commands**: On Windows, use Python only for execution orchestration via `subprocess` — do not use PowerShell, `cmd`, `cmd /c`, or `.bat` batch files. On Linux, standard shell commands (`bash`, `grep`, `cat`, etc.) are fine.
9. **Search commands**: On Windows, do not use `findstr`; use a Python recursive search (e.g. `pathlib.Path.rglob()` with text scanning). On Linux, standard tools like `grep -r` or `find` are acceptable.
10. **Terminal output**: Do not depend on terminal output for verification or reporting. Redirect stdout/stderr to log files under `logs/` and reference those logs in status updates.
11. **OS awareness**: Detect the current OS and use appropriate paths and commands. Use `/` path separators on Linux and `\` on Windows. Do not assume a single OS — both Windows and Linux are supported dev environments.

---

## Key Spec Files

| Purpose | File |
|---------|------|
| Full implementation roadmap | `CODE_GENERATION_PLAN.md` |
| Project context | `specs/context.md` |
| Spec navigation index | `specs/README.md` |
| Workflow V3 engine spec | `specs/specifications/S70_workflow_engine_v3.md` |
| React SPA architecture | `specs/specifications/S80_react_frontend_architecture.md` |
| Readiness management reqs | `specs/requirements/R18_readiness_management.md` |
| Meeting series workspace | `specs/requirements/R19_meeting_series_workspace.md` |
| Frontend/backend separation | `specs/specifications/S60_frontend_backend_separation.md` |
| API contract | `specs/specifications/S16_API_Contract.md` |
| DB schema | `action_hub/db/schema.sql` |
| Data dictionary | `specs/specifications/S05_data_dictionary.md` |
| Terminology rename plan | `specs/CODE_UPDATE_PLAN.md` |

---

