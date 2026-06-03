# S60 — Frontend / Backend Separation Plan

**Status**: COMPLETED  
**Date**: 2026-03-13  
**Applies to**: ActionHub v3.0–v3.5

> **Updated**: 2026-03-14 — All SEP phases (SEP-0 through SEP-4) are DONE. The React SPA is the production frontend. §1 is retained as **historical context** describing the pre-separation Jinja2/HTMX architecture. See [S80_react_frontend_architecture.md](S80_react_frontend_architecture.md) for the as-built architecture. §2–§8 remain accurate as design rationale.

---

## 1. Current State (v3.4) — Historical Snapshot

| Aspect | Current Implementation |
|--------|----------------------|
| **Architecture** | Flask monolith — Jinja2 SSR + inline `<script>` blocks |
| **Templates** | ~37 Jinja2 `.html` files (including 8 workflow templates), most are thin shells that fetch data client-side via `fetch()` to `/api/*` endpoints |
| **Page routes** | 27 `render_template` calls, concentrated in `web_bp` (21), `feedback_bp` (3), `auth_bp` (2), `evolution_bp` (1) |
| **API routes** | ~100 JSON endpoints across 13 blueprints (`/api/auth/*`, `/api/actions/*`, `/api/admin/*`, `/api/meetings/*`, `/api/workflow/*`, etc.) |
| **JS files** | 9 files in `static/js/` (actions, dashboard, gantt, comments, import, quick-capture, app, workflow, drawflow_builder) |
| **Auth** | Server-side Flask session (`session["user"]`), file-backed (`flask_session/`), 3 decorators |
| **i18n** | Custom `t()` Jinja2 function, 2 JSON catalogs (`en.json`, `zh.json`), language in session |
| **HTMX** | `hx-boost="true"` on `<body>` — SPA-like navigation swapping `<main>` content |
| **Libraries** | Bootstrap 5, HTMX, Chart.js — all vendored locally |
| **Deployment** | Single Waitress process, NSSM Windows service, SQLite |

### Key Observation

The current codebase is **already 80% separated** in practice:
- Most templates are empty shells with `{% block content %}` containing markup + a `<script>` that calls `fetch('/api/...')` for all data.
- Business logic lives in `*_service.py` modules, not in template rendering.
- The main coupling points are: (a) session-based auth, (b) the `t()` translation function in templates, (c) `base.html` layout/navbar, and (d) a few routes that pass server-side data to templates via context variables.

---

## 2. Goals

| # | Goal | Rationale |
|---|------|-----------|
| G1 | **Separate deployable frontend** | Enable independent frontend updates without restarting the API server |
| G2 | **Pure JSON API backend** | Flask serves only `/api/*` + static assets; no `render_template` |
| G3 | **Token-based auth** | Replace server-side sessions with JWT for stateless API |
| G4 | **Client-side i18n** | Move translation to the frontend; API returns raw keys/data |
| G5 | **Structured frontend** | React 18 + TypeScript + Vite — justified by 16 pages with complex state (workflow canvas, dependent forms, chart dashboards, CRUD tables); `react-bootstrap` reuses existing BS5 knowledge; ~42 KB gzipped overhead negligible on intranet |
| G6 | **Zero downtime migration** | Both old and new frontends can work during transition |

---

## 3. Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  React 18 + TypeScript SPA (static/dist/)            │   │
│  │  • index.html + React Router v6                      │   │
│  │  • .tsx components per page (actions, dashboard…)    │   │
│  │  • react-i18next (loads en.json/zh.json)             │   │
│  │  • react-bootstrap + react-chartjs-2                 │   │
│  │  • TanStack Query/Table + React Hook Form            │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │ fetch('/api/...')                  │
│                         │ Authorization: Bearer <JWT>       │
└─────────────────────────┼───────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────┐
│  Flask API Server       │                                   │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │  /api/auth/*    – JWT login, refresh, change-pwd     │   │
│  │  /api/actions/* – CRUD, comments                     │   │
│  │  /api/admin/*   – users, teams, topics, feedback     │   │
│  │  /api/meetings/*– CRUD, memos                        │   │
│  │  /api/dashboard/*– personal, topic, team             │   │
│  │  /api/gantt/*   – gantt data                         │   │
│  │  /api/export/*  – Excel download                     │   │
│  │  /health        – health check                       │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  Middleware: JWT validation, CORS, rate-limiting      │   │
│  │  Services: *_service.py (unchanged)                  │   │
│  │  DB: SQLite (unchanged)                              │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Deployment Options

| Option | Description | Effort |
|--------|-------------|--------|
| **A. Same origin** | Flask serves SPA `index.html` as catch-all + `/api/*` routes *(simplest)* | Low |
| **B. Separate origins** | Frontend on Nginx/IIS static, API on Flask behind reverse proxy | Medium |
| **C. Hybrid transition** | Keep `web_bp` serving old pages during migration, new SPA pages coexist | Low → Medium |

**Recommendation**: Option **A** for pilot, evolve to **B** for production scale.

---

## 4. Migration Phases

### Phase 0 — API Hardening (pre-requisite, ~2 days)

| Task | Detail |
|------|--------|
| 0.1 Audit all `/api/*` responses | Ensure every endpoint returns consistent JSON (`{data}` or `{error}`) |
| 0.2 Add missing API endpoints | Some pages render server-side data (e.g., `gantt.html` receives `statuses`). Expose these as API calls |
| 0.3 API versioning prefix | Add `/api/v1/` prefix (optional, recommended) |
| 0.4 CORS headers | Add `flask-cors` for development (localhost cross-origin) |
| 0.5 Swagger / OpenAPI | Generate API contract documentation from existing routes |

### Phase 1 — Auth Migration (~2 days)

| Task | Detail |
|------|--------|
| 1.1 Add JWT support | Install `PyJWT`. Login returns `{access_token, refresh_token}`. Keep session auth as fallback |
| 1.2 Dual-mode middleware | `@login_required` checks JWT `Authorization: Bearer` header first, falls back to session |
| 1.3 Token refresh endpoint | `POST /api/auth/refresh` — issue new access token from refresh token |
| 1.4 Remove session dependency | After frontend migrated, remove `flask_session`, session files, cookie config |

### Phase 2 — Frontend Scaffold (~4 days)

| Task | Detail |
|------|--------|
| 2.1 Create `frontend/` directory | Under `action_hub/`, houses React SPA source |
| 2.2 Init React + Vite project | `npx create-vite frontend --template react-ts`; output → `static/dist/`; proxy `/api` → `:5000` |
| 2.3 Install core deps | `react-router-dom`, `react-bootstrap`, `@tanstack/react-query`, `@tanstack/react-table`, `react-i18next`, `react-hook-form`, `react-chartjs-2` |
| 2.4 SPA entry + router | `main.tsx` mounts `<App/>` with providers; React Router v6 lazy routes |
| 2.5 Layout component | `<AppLayout>` — navbar, footer, security banner in React; role-based nav via `useAuth()` |
| 2.6 Client-side i18n | `react-i18next` loading `en.json`/`zh.json` via `/api/i18n/:lang`; `useTranslation()` hook |
| 2.7 Auth context | `<AuthProvider>` stores JWT in memory; `useAuth()` hook; auto-refresh; 401 redirect |
| 2.8 Shared components | `<CrudTable>`, `<KpiCard>`, `<ChartPanel>`, `<ConfirmModal>`, `<StatusBadge>` |
| 2.9 Catch-all route | Flask serves `index.html` for all non-`/api/` and non-`/static/` paths |

### Phase 3 — Page-by-Page Migration (~5-8 days)

Migrate pages **one at a time**, ordered by complexity (simplest first):

| Priority | Page | Complexity | Notes |
|----------|------|------------|-------|
| 1 | Login / Change Password | Low | Already standalone. Replace Jinja2 with SPA login form |
| 2 | Help (Manual, Spec) | Low | Static content, just HTML/markdown rendering |
| 3 | Meetings list | Low | Already 100% client-rendered via fetch |
| 4 | Admin Teams | Low | Already 100% client-rendered via fetch |
| 5 | Admin Categories | Low | Already 100% client-rendered via fetch |
| 6 | Admin Users | Low | Already 100% client-rendered via fetch |
| 7 | Admin Categories | Low | Already 100% client-rendered via fetch |
| 8 | Feedback list/form | Low | Already mostly client-rendered |
| 8 | Feedback list/form | Low | Already mostly client-rendered |
| 9 | Personal Dashboard | Medium | Chart.js charts, KPI cards, action table — all via fetch |
| 10 | Category Dashboard | Medium | Similar to personal dashboard |
| 11 | Actions List | Medium | HTMX partial table swap → replace with JS table rendering |
| 12 | Action Form (create/edit) | Medium | Multiple dependent dropdowns, date logic |
| 13 | Action Detail | Medium | Tabs, comments, assignments |
| 14 | Meeting Detail | Medium | Memos, attached actions, notes editing |
| 14b | Decision Search (standalone) | Medium | FTS5 search, filters, paginated results — new page (V3.5) |
| 15 | Gantt Chart | High | Complex timeline rendering, custom Canvas/SVG |
| 16 | Admin Actions Table | Medium | Server-side rendered table → client-side |
| 17 | Team Dashboard | Medium | Cross-team aggregations |

### Phase 4 — Cleanup (~1-2 days)

| Task | Detail |
|------|--------|
| 4.1 Remove `templates/` | Delete all Jinja2 templates |
| 4.2 Remove `web_bp` | Delete `web/routes.py` — no more `render_template` |
| 4.3 Remove HTMX | No longer needed; remove vendor file and `hx-*` attributes |
| 4.4 Remove session config | Drop `flask_session/`, `SESSION_*` config, file-based session storage |
| 4.5 Remove `base.html` coupling | Navbar, footer, security banner all live in frontend JS |
| 4.6 Clean `__init__.py` | Remove `web_bp` registration, session init, Jinja context processors |
| 4.7 Update deployment scripts | `install_service.ps1`, `build.bat` — include frontend build step |

---

## 5. Files Affected

### Backend (modify)
| File | Change |
|------|--------|
| `actionhub/__init__.py` | Add CORS, JWT init, SPA catch-all route, remove session/web_bp |
| `actionhub/middleware/auth_middleware.py` | Dual-mode JWT + session → JWT-only |
| `actionhub/auth/routes.py` | Return JWT tokens on login, add `/api/auth/refresh` |
| `actionhub/i18n/__init__.py` | Expose `GET /api/i18n/:lang` to return catalog JSON, remove Jinja context processor |
| `config.py` | Add `JWT_SECRET_KEY`, `JWT_ACCESS_EXPIRY`, remove `SESSION_*` settings |
| `requirements.txt` | Add `PyJWT`, `flask-cors`; remove `flask-session` |

### Backend (delete)
| File/Dir | Reason |
|----------|--------|
| `actionhub/web/` | All page-serving routes — replaced by SPA |
| `templates/` (entire dir) | Jinja2 templates — replaced by SPA components |
| `flask_session/` | Server-side sessions — replaced by JWT |
| `static/vendor/htmx/` | HTMX no longer needed |

### Frontend (new — React 18 + TypeScript + Vite)
| File/Dir | Description |
|----------|-------------|
| `frontend/index.html` | SPA shell — `<div id="root">`, CSS links, `src/main.tsx` entry |
| `frontend/vite.config.ts` | Build config — output to `static/dist/`, proxy `/api` → `:5000` |
| `frontend/tsconfig.json` | TypeScript config with strict mode |
| `frontend/src/main.tsx` | React mount with providers: QueryClient, BrowserRouter, I18nextProvider, AuthProvider |
| `frontend/src/router.tsx` | React Router v6 lazy-loaded route definitions |
| `frontend/src/contexts/AuthContext.tsx` | JWT in-memory storage, login/logout, auto-refresh, 401 handling |
| `frontend/src/hooks/useAuth.ts` | Auth hook consumed by components |
| `frontend/src/lib/api.ts` | Fetch wrapper: Bearer injection, refresh on 401, error normalisation |
| `frontend/src/lib/i18n.ts` | `react-i18next` config loading catalogs from `/api/i18n/:lang` |
| `frontend/src/components/AppLayout.tsx` | Navbar, footer, security banner — role-based nav |
| `frontend/src/components/shared/` | `CrudTable`, `KpiCard`, `ChartPanel`, `ConfirmModal`, `StatusBadge`, `DateField` |
| `frontend/src/pages/*.tsx` | One React component per page (mirrors current template structure) |
| `frontend/.eslintrc.cjs` | ESLint config (react-app + TS rules) |
| `frontend/.prettierrc` | Prettier config |

---

## 6. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| JWT token in browser is vulnerable to XSS | High | Store access token in JS variable (not localStorage). Use short expiry (15 min) + HTTP-only refresh cookie |
| Breaking existing bookmarks / URLs | Medium | SPA router matches the same URL paths. Catch-all serves `index.html` |
| i18n regression | Medium | Reuse the same JSON catalogs. Automated comparison test |
| Dual-mode auth complexity during transition | Low | Clear timeline: Phase 1-3 = dual-mode, Phase 4 = JWT-only |
| Build tooling added complexity | Low | Vite is zero-config for React+TS. Single `npm run build` command. ESLint + Prettier enforce consistency |
| React learning curve | Low-Medium | Team writes vanilla JS; React adds component model and hooks. Mitigated by shared components (CrudTable, KpiCard) that encapsulate patterns — most pages become ~50 lines |
| Losing HTMX-style fast navigation | Low | React Router provides same SPA experience. TanStack Query prefetches on hover (optional) |

---

## 7. Effort Estimate

| Phase | Effort | Cumulative |
|-------|--------|------------|
| Phase 0 — API Hardening | 2 days | 2 days |
| Phase 1 — Auth Migration | 2 days | 4 days |
| Phase 2 — Frontend Scaffold | 4 days | 8 days |
| Phase 3 — Page Migration | 5-8 days | 13-16 days |
| Phase 4 — Cleanup | 1-2 days | 14-18 days |
| **Total** | **14-18 working days** | |

---

## 8. Decision Points

Before starting implementation, decide on:

| # | Question | Options |
|---|----------|---------|
| D1 | **Frontend framework?** | **(e) React 18 + TypeScript + Vite** *(decided)* — best ROI for 16 pages with complex UI; `react-bootstrap` reuses BS5; TanStack Query/Table for data grids; `react-i18next` for translations; ~42 KB gzipped |
| D2 | **Deployment model?** | **(a) Same-origin** *(decided)* — Flask serves SPA for pilot, evolve to (b) Split later |
| D3 | **Auth token storage?** | **(a) In-memory JS + HTTP-only refresh cookie** *(decided)* — most secure |
| D4 | **Migration strategy?** | **(b) Incremental** *(decided)* — page by page, dual-mode; zero downtime, lower risk |
| D5 | **Scope of v3.0?** | **(a) Full separation** *(decided)* — S60 targets 100% SPA |
