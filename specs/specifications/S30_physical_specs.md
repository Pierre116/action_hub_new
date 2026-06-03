# ActionHub — Physical Specifications

> **Level**: L4 — Physical  
> **Merise Phase**: Modèle Physique des Données + Spécifications Techniques  
> **Source**: S20_MLD.md (DDL), S16_API_Contract.md (endpoints), R04_technical.md, R06_security.md  
> **Purpose**: Stack decisions, project structure, deployment, performance, security hardening

> **Updated**: 2026-03-14 — Fully rewritten post-SEP-4. §1 split into Backend/Frontend stacks. §2 project structure reflects React SPA layout. §5 auth updated for JWT. §9 deps split into backend/frontend. §11 as-built notes added.

---

## 1. Technology Stack

### 1.1 Backend

| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| **Language** | Python | 3.12 | Team familiarity, rapid prototyping |
| **Web Framework** | Flask | 3.x | Lightweight, fits MVP timeline |
| **Database** | SQLite | 3.35+ | Zero-config, WAL mode, <10 concurrent users |
| **ORM** | None (raw SQL) | — | Direct control, parameterized queries only |
| **Auth** | PyJWT | 2.x | JWT access/refresh tokens |
| **Password Hashing** | bcrypt | 4.x | Industry standard |
| **Excel** | openpyxl | 3.x | .xlsx import/export |
| **WSGI Server** | Waitress | 3.x | Production-grade, cross-platform |
| **Process Manager** | NSSM | 2.x | Windows service (prod only) |

### 1.2 Frontend

| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| **UI Library** | React | 18.x | Component model, ecosystem |
| **Language** | TypeScript | 5.x | Type safety, IDE support |
| **Bundler** | Vite | 5.x | Fast HMR, optimized builds |
| **CSS Framework** | react-bootstrap + Bootstrap | 2.x / 5.3 | Responsive grid, bilingual ready |
| **Data Fetching** | TanStack Query | 5.x | Cache, refetch, loading states |
| **Tables** | TanStack Table | 8.x | Sorting, filtering, pagination |
| **Forms** | React Hook Form | 7.x | Validation, performance |
| **Charts** | react-chartjs-2 + Chart.js | 5.x / 4.x | Donut/bar charts for dashboards |
| **Routing** | React Router | 6.x | SPA navigation, lazy loading |
| **HTTP Client** | Axios | 1.x | Bearer injection, 401 auto-refresh |
| **i18n** | Custom `useTranslation()` hook | — | Inline EN/ZH catalogs (~340 lines each) |
| **Icons** | Bootstrap Icons | 1.x | Consistent with Bootstrap theme |

---

## 2. Project Structure

```
action_hub/                     # Application root
├── app.py                      # Flask application factory
├── config.py                   # Configuration (dev/prod, JWT settings)
├── wsgi.py                     # Waitress entry point
├── requirements.txt            # Python dependencies
├── init_db.py                  # Database initialization script
├── seed_data.py                # Seed teams, categories, admin user
│
├── db/
│   ├── schema.sql              # Full DDL (from S20_MLD.md)
│   ├── seed.sql                # Seed data INSERT statements
│   └── migrate_v*.sql          # Incremental migration scripts
│
├── actionhub/                  # Application package (Flask blueprints)
│   ├── __init__.py             # create_app(), blueprint registration
│   │
│   ├── auth/                   # Authentication blueprint
│   │   ├── routes.py           # /api/auth/* (login, refresh, change-pwd)
│   │   └── service.py          # JWT token logic, bcrypt, lockout
│   │
│   ├── actions/                # Actions blueprint
│   │   ├── routes.py           # /api/actions/*
│   │   ├── service.py          # CRUD, status transitions, assignments
│   │   └── queries.py          # SQL query builders
│   │
│   ├── dashboard/              # Dashboard blueprint
│   │   ├── routes.py           # /api/dashboard/*
│   │   └── service.py          # KPI aggregation queries
│   │
│   ├── admin/                  # Admin blueprint
│   │   ├── routes.py           # /api/admin/*
│   │   ├── user_service.py     # User CRUD
│   │   └── import_service.py   # Excel import pipeline
│   │
│   ├── taxonomy/               # Reference data blueprint
│   │   └── routes.py           # /api/teams, /api/topics, etc.
│   │
│   ├── meetings/               # Meetings blueprint
│   │   ├── routes.py           # /api/meetings/*
│   │   └── service.py          # Meeting CRUD, minutes, participants
│   │
│   ├── workflow/               # Workflow engine V3
│   │   ├── engine.py           # Core engine (lifecycle, gateway, parallel)
│   │   ├── gateway.py          # Decision table evaluation
│   │   ├── routes.py           # /api/workflow/*
│   │   └── service.py          # Template/instance CRUD
│   │
│   ├── export/                 # Export blueprint
│   │   ├── routes.py           # /api/export/*
│   │   └── excel_writer.py     # openpyxl export logic
│   │
│   ├── i18n/                   # Backend i18n (API error/label strings)
│   │   ├── en.json             # English strings
│   │   └── zh.json             # Chinese strings
│   │
│   ├── middleware/             # Cross-cutting concerns
│   │   ├── auth_middleware.py  # @login_required (JWT), @admin_required
│   │   ├── error_handlers.py  # Global error handlers
│   │   └── db.py              # get_db(), close_db() per-request
│   │
│   └── utils/                 # Shared utilities
│       ├── ref_generator.py   # ACT-YYYY-NNNNN generation
│       ├── validators.py      # Input validation helpers
│       └── date_utils.py      # Date parsing, overdue checks
│
├── frontend/                  # React 18 SPA source (TypeScript + Vite)
│   ├── index.html             # SPA shell — <div id="root">
│   ├── vite.config.ts         # Build config — output → ../static/dist/
│   ├── tsconfig.json          # TypeScript strict mode
│   ├── package.json           # npm dependencies
│   └── src/
│       ├── main.tsx           # React mount with providers
│       ├── App.tsx            # Layout + router wrapper
│       ├── router.tsx         # React Router v6 lazy routes
│       ├── contexts/
│       │   └── AuthContext.tsx # JWT storage, login/logout, auto-refresh
│       ├── lib/
│       │   ├── api.ts         # Axios wrapper: Bearer injection, 401 refresh
│       │   └── i18n.ts        # useTranslation() hook + inline catalogs
│       ├── components/
│       │   ├── AppLayout.tsx   # Navbar, footer, role-based nav
│       │   └── shared/        # CrudTable, KpiCard, ChartPanel, StatusBadge, etc.
│       └── pages/             # One .tsx per route (actions/, admin/, dashboard/, etc.)
│
├── static/                    # Build output + legacy assets
│   ├── dist/                  # Vite build output (JS/CSS bundles)
│   ├── css/actionhub.css      # Brand theme CSS variables
│   ├── img/logo.svg           # Company logo
│   └── vendor/                # Bootstrap Icons (no longer Bootstrap/HTMX/Chart.js)
│
└── tests/                     # pytest suite (~248 tests)
    ├── conftest.py            # Fixtures (test DB, client, AppTestCase)
    ├── test_auth.py
    ├── test_actions.py
    ├── test_dashboard.py
    ├── test_workflow_engine.py
    └── ...                    # ~20 test files
```

---

## 3. Configuration

### 3.1 config.py

```python
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-prod')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dev-jwt-key-change-in-prod')
    JWT_ACCESS_EXPIRY = 900       # 15 minutes
    JWT_REFRESH_EXPIRY = 28800    # 8 hours
    DATABASE = os.environ.get('DATABASE', 'db/actionhub.db')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
    JSON_SORT_KEYS = False
    
class ProductionConfig(Config):
    SECRET_KEY = os.environ['SECRET_KEY']  # required in prod
    DATABASE = os.environ.get('DATABASE', 'C:/ActionHub/data/actionhub.db')

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    DATABASE = ':memory:'
```

### 3.2 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Prod only | `dev-key-change…` | Flask secret key |
| `JWT_SECRET_KEY` | Prod only | `dev-jwt-key…` | JWT signing key |
| `DATABASE` | No | `db/actionhub.db` | SQLite file path |
| `ACTIONHUB_ENV` | No | `development` | `development` / `production` |
| `PORT` | No | `5000` | Waitress listen port |
| `HOST` | No | `0.0.0.0` | Waitress bind address |

---

## 4. Database Physical Design

### 4.1 SQLite Configuration

```sql
PRAGMA journal_mode = WAL;        -- Write-Ahead Logging for concurrent reads
PRAGMA foreign_keys = ON;         -- Enforce referential integrity
PRAGMA busy_timeout = 5000;       -- Wait 5s on lock contention
PRAGMA cache_size = -8000;        -- 8MB page cache
PRAGMA synchronous = NORMAL;      -- Safe with WAL
PRAGMA temp_store = MEMORY;       -- Temp tables in RAM
```

### 4.2 Connection Management

```python
# Per-request connection (Flask g object)
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
        g.db.execute("PRAGMA busy_timeout=5000")
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()
```

### 4.3 Storage Estimates

| Table | Year 1 Rows | Avg Row Size | Total |
|-------|-------------|-------------|-------|
| t_action | ~2,000 | 500 B | 1 MB |
| t_action_history | ~10,000 | 200 B | 2 MB |
| t_assignment | ~5,000 | 100 B | 0.5 MB |
| t_user | ~50 | 300 B | 15 KB |
| t_import_log | ~20 | 500 B | 10 KB |
| **Total (Year 1)** | | | **~4 MB** |
| **Total (5 years)** | | | **~20 MB** |

SQLite handles databases up to 281 TB. A 20 MB database is trivially small.

### 4.4 Backup Strategy

| Aspect | Strategy |
|--------|----------|
| Method | File copy of `actionhub.db` (WAL checkpoint first) |
| Frequency | Daily at 02:00 via Windows Task Scheduler |
| Retention | 30 daily backups |
| Location | Network share `\\server\backups\actionhub\` |
| Script | `backup.bat` using SQLite `.backup` command |

```bat
@echo off
set DB=C:\ActionHub\data\actionhub.db
set BACKUP=\\server\backups\actionhub\actionhub_%date:~-4%%date:~3,2%%date:~0,2%.db
sqlite3 %DB% ".backup '%BACKUP%'"
```

---

## 5. Security Hardening

### 5.1 Authentication

| Aspect | Implementation |
|--------|---------------|
| Password storage | bcrypt with cost factor 12 |
| Auth mechanism | JWT (PyJWT) — `Authorization: Bearer <token>` header |
| Access token | Short-lived (configurable, default 15 min); stored in sessionStorage |
| Refresh token | Longer-lived; `POST /api/auth/refresh` issues new access token |
| Token storage | `sessionStorage` (cleared on tab close); Axios interceptors handle refresh |
| Lockout | 5 failed attempts in 15 min → 30 min lockout |
| Password policy | Min 8 chars; complexity rules per `config.py` |

### 5.2 RBAC Model

**Full model (4 roles):** Admin, TeamLead, Member, ReadOnly — defined in S05, S20 (`t_user.usr_role`).

**MVP simplification (D160):** Binary Admin/Member check only. All `@admin_required` middleware checks `usr_role == 'Admin'`. All other authenticated users are treated as Member. TeamLead and ReadOnly role-specific behavior is deferred to V1.1.

| Middleware | Logic |
|-----------|-------|
| `@login_required` | Valid JWT in `Authorization: Bearer` header; token not expired |
| `@admin_required` | `@login_required` + JWT claim `role == 'Admin'` |

### 5.3 SLA Thresholds (D30)

Used by overdue detection logic and dashboard color-coding:

| Priority | SLA (calendar days from creation) | Overdue Color |
|----------|----------------------------------|---------------|
| Critical | ≤3 days | Red (pulsing badge) |
| High | ≤7 days | Red |
| Medium | ≤14 days | Amber (>7d), Red (>14d) |
| Low | ≤30 days | Amber (>14d), Red (>30d) |

**Implementation:** `date_utils.py` → `is_overdue(deadline, priority)` and `sla_status(deadline, priority)` functions.

### 5.4 Input Validation

| Vector | Mitigation |
|--------|-----------|
| SQL Injection | Parameterized queries only (never string concatenation) |
| XSS | React auto-escapes JSX by default; no `dangerouslySetInnerHTML` in codebase |
| CSRF | JWT Bearer tokens (not cookies) — CSRF not applicable for token-based auth |
| Path Traversal | File upload validates .xlsx extension + MIME type |
| File Size | `MAX_CONTENT_LENGTH = 10 MB` |
| Mass Assignment | Explicit field whitelisting in request parsing |

### 5.5 Headers

```python
@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Cache-Control'] = 'no-store'
    return response
```

---

## 6. Deployment

### 6.1 Target Environment

| Aspect | Specification |
|--------|--------------|
| OS | Windows Server 2016+ or Windows 10/11 |
| Python | 3.10+ (embedded or system-installed) |
| Network | LAN only (no internet exposure) |
| Port | TCP 5000 (configurable) |
| Users | <10 concurrent |

### 6.2 Installation Steps

```powershell
# 1. Create directory
mkdir C:\ActionHub
cd C:\ActionHub

# 2. Extract application files
# (copy actionhub/ folder to C:\ActionHub\)

# 3. Create virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Initialize database
python init_db.py

# 6. Seed reference data
python seed_data.py

# 7. Create admin user
python -c "from actionhub.admin.user_service import create_user; create_user('admin', 'Admin@2026', 'Administrator', role='Admin', dept_id=1)"

# 8. Start server (test)
python wsgi.py

# 9. Install as Windows service (production)
nssm install ActionHub "C:\ActionHub\.venv\Scripts\python.exe" "C:\ActionHub\wsgi.py"
nssm set ActionHub AppDirectory "C:\ActionHub"
nssm set ActionHub Start SERVICE_AUTO_START
nssm start ActionHub
```

### 6.3 wsgi.py

```python
from waitress import serve
from actionhub import create_app
import os

app = create_app()

if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    print(f"ActionHub starting on http://{host}:{port}")
    serve(app, host=host, port=port, threads=4)
```

---

## 7. Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Login response | <500ms | Time from submit to dashboard render |
| Dashboard load | <1s | Full page load including KPI queries |
| Action list (filtered) | <500ms | API response time |
| Action create | <300ms | API response time |
| Status transition | <200ms | API response time |
| Import 200 rows | <10s | Total processing time |
| Export 500 rows | <5s | File generation time |
| Page weight | <500KB | Total transfer (HTML + CSS + JS + fonts) |

### 7.1 Query Optimization

| Query | Expected Perf | Optimization |
|-------|--------------|-------------|
| Overdue actions | <50ms | Partial index `idx_action_overdue` |
| Action list + filters | <100ms | Composite indexes on status, dept, deadline |
| Dashboard KPIs | <200ms | `v_user_workload` view, pre-aggregated |
| History for action | <20ms | Index on `ahi_action_id` |

---

## 8. Logging

### 8.1 Application Logging

```python
import logging

logging.basicConfig(
    filename='logs/actionhub.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
```

| Log Level | Usage |
|-----------|-------|
| ERROR | Unhandled exceptions, DB errors |
| WARNING | Failed login attempts, validation errors |
| INFO | Successful logins, imports, exports, user creation |
| DEBUG | SQL queries (dev only) |

### 8.2 Log Rotation

- Use `logging.handlers.RotatingFileHandler`
- Max file size: 10 MB
- Keep 5 backup files
- Location: `C:\ActionHub\logs\`

---

## 9. Dependencies

### 9.1 Backend (requirements.txt)

```
Flask==3.1.*
PyJWT==2.*
bcrypt==4.2.*
openpyxl==3.1.*
waitress==3.0.*
```

Total: 5 packages + their transitive deps. `Flask-Session` and `cachelib` were removed in SEP-1 (JWT migration).

### 9.2 Frontend (package.json)

Key production dependencies:

```
react, react-dom                    18.x
react-router-dom                    6.x
react-bootstrap, bootstrap          2.x / 5.3
@tanstack/react-query               5.x
@tanstack/react-table               8.x
react-hook-form                     7.x
react-chartjs-2, chart.js           5.x / 4.x
axios                               1.x
```

Build: Vite 5.x + TypeScript 5.x. Output → `action_hub/static/dist/`.

---

## 10. Phase Deployment Plan

| Phase | Deliverable | Status |
|-------|------------|--------|
| MVP (V1.0) | Auth, Actions CRUD, Status FSM, Dashboards, Import/rollback, Export, i18n | ✅ Delivered |
| V1.0 Hardening | Test suite, deployment scripts, production config hardening, backup flow | ✅ Delivered |
| V1.1–V2 | Meetings, Notifications, Workflow V1–V2, escalation engine | ✅ Delivered |
| V3.0–V3.5 | React 18 SPA (SEP-0–SEP-4), JWT auth, Workflow V3 engine (WF-10–WF-12.5) | ✅ Delivered |
| V3.6+ (planned) | WF-12 (service steps), WF-13 (notification steps), Meeting Decisions (P8) | 📋 Planned |

---

## 11. As-Built Baseline Notes (V3.5)

- **Auth**: JWT-based (PyJWT). Access tokens in `sessionStorage`; Axios interceptors auto-refresh on 401. Flask-Session removed in SEP-1.
- **Frontend**: React 18 + TypeScript SPA served from `static/dist/`. Jinja2 templates and HTMX removed in SEP-4.
- **Production mode**: enforces `SECRET_KEY` and `JWT_SECRET_KEY` at app startup (`ACTIONHUB_ENV=production`); startup fails if missing.
- **Migrations**: incremental `.py` scripts in `action_hub/migrations/`; base schema in `db/schema.sql`.
- **Test suite**: 248 tests passing, 6 pre-existing failures (post test-folder consolidation, 2026-03-14).
