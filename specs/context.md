# ActionHub — Project Context & Constraints

> **Status**: Living document  
> **Last updated**: 2026-03-23  
> **Consumed by**: All R-series and S-series specs, `CODE_GENERATION_PLAN.md`, `AGENTS.md`, `.github/copilot-instructions.md`

---

## 1. Organizational Context

**ActionHub** is a centralized action-tracking platform for a multinational industrial organization (~300 employees, 12 teams). It replaces fragmented Excel-based action logbooks with a unified web application providing action management, structured meetings, dashboards, and a configurable workflow engine.

### 1.1 Organization Profile

| Attribute | Value |
|-----------|-------|
| Headcount | ~300 employees |
| Teams | 12: Facility, IE, CI, Quality, HP, Warehouse, Logistic, Sourcing, Procurement, MM, ESL, Planning |
| Locations | Multi-site manufacturing (China + international) |
| Language | Bilingual — Chinese (primary) + English (management / cross-site) |
| Work culture | Weekly/biweekly review meetings per team; action follow-up driven by team leads |

### 1.2 Strategic Intent (from I00)

The organization's leadership identified three cross-functional priorities (see [I00_intent.md](requirements/I00_intent.md)):

1. **Specs, BOM & Engineering Definition** — early and stable technical definitions for reliable execution
2. **Material Management & Sourcing** — securing supply and anticipating constraints
3. **Manufacturing & Execution** — turning plans into on-time delivery through daily management

ActionHub is the **shared execution platform** across all three. Its scope centers on action management, structured meetings, dashboards, and workflow orchestration across teams.

---

## 2. Technical Constraints

### 2.1 Deployment

| Constraint | Detail |
|-----------|--------|
| Server | Single on-premise Windows server (LAN-accessible) |
| Network | Corporate intranet only — no public internet exposure |
| Concurrent users | <10 simultaneous (typically 5) |
| Availability | Business hours (8h × 5d); unattended restart via NSSM Windows service |
| Backup | Daily SQLite file copy (automated) |
| npm registry | China — use `registry.npmmirror.com` with `strict-ssl=false` if default fails |

### 2.2 Technology Stack (as-built, V3.5)

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend | Python 3.12 / Flask 3.x | App factory pattern |
| Database | SQLite (WAL mode, raw SQL, no ORM) | Single file at `action_hub/db/actionhub.db` |
| Frontend | React 18 + TypeScript + Vite 5 | SPA served from `action_hub/static/dist/` |
| Workflow engine runtime | In-house Python engine (`actionhub/workflow/engine.py`) | No external orchestration runtime (no Prefect/Camunda) |
| Workflow builder canvas | React Flow (`@xyflow/react`) | Visual authoring for `steps` / `transitions` graph |
| UI library | react-bootstrap (Bootstrap 5) | |
| Data fetching | TanStack Query v5 | Cache, refetch, optimistic updates |
| Tables | TanStack Table v8 | Headless sort/filter/pagination |
| Charts | react-chartjs-2 (Chart.js 4) | Dashboard KPIs |
| Forms | React Hook Form | Action create/edit |
| Routing | React Router v6 | Lazy-loaded page routes |
| Auth | JWT (PyJWT) — access + refresh tokens in sessionStorage | Replaced Flask sessions in SEP-1 |
| i18n | Custom `useTranslation()` hook — `en.json`/`zh.json` catalogs | Not `react-i18next` (lightweight inline solution) |
| WSGI server | Waitress | Windows-native, production-grade |
| Process manager | NSSM | Run as Windows service |
| Tests | pytest (~248 tests) | `action_hub/tests/` |

### 2.3 Retired Technologies

| Technology | Removed in | Replacement |
|-----------|-----------|-------------|
| Jinja2 templates | SEP-4 | React SPA |
| HTMX | SEP-4 | React Router + TanStack Query |
| Flask-Session (server-side sessions) | SEP-1 | JWT tokens |
| Inline `<script>` blocks | SEP-3 | `.tsx` components |
| Vendor-local Bootstrap/Chart.js JS | SEP-2 | npm packages |

---

## 3. Key Design Decisions

| Decision | Rationale |
|---------|-----------|
| SQLite (not MySQL/PostgreSQL) | Zero-config, single-file, sufficient for <10 users; WAL mode for concurrent reads |
| No ORM | Direct SQL control; fewer abstractions for a small team; parameterized queries for security |
| Raw SQL in `service.py` | Business logic and data access co-located per domain; thin `routes.py` for HTTP handling |
| React 18 (not Vue/Svelte) | Best ecosystem for 16 pages with complex UI (workflow canvas, dependent forms, CRUD tables); react-bootstrap reuses existing BS5 knowledge |
| Same-origin deployment | Flask serves SPA from `static/dist/` — simplest for intranet; split later if needed |
| JWT over sessions | Stateless API, enables future mobile/agent clients |
| Graph-as-JSON | Workflow template stored as single `wft_graph` JSON column — reduces 12 tables to 6 |

---

## 4. Conventions

### 4.1 Database

- Field codes: `XXX_FIELD_NAME` (3-letter entity prefix + UPPER_SNAKE_CASE)
- Audit fields: `*_CREATED_AT`, `*_UPDATED_AT`, `*_VERSION`, `*_DELETED_AT`
- Bilingual taxonomy: `_en` / `_cn` suffix (e.g. `top_name_en`, `top_name_cn`)
- Business status families used by the React UI and dashboard contracts: Not started, On-track, Late, Completed, Cancelled
- Soft-delete via `*_DELETED_AT` timestamp (not physical delete)

### 4.2 Code Organization

- Blueprints: one per domain (`actions/`, `admin/`, `auth/`, `dashboard/`, `meetings/`, `workflow/`, etc.)
- Each blueprint: `routes.py` (HTTP), `service.py` (business logic + SQL), optional `*_service.py` for sub-domains
- Frontend: `action_hub/frontend/src/` — pages, components, contexts, lib
- Build output: `action_hub/static/dist/` (Vite build)

### 4.3 Terminology

| Concept | DB table | DB prefix | UI label (EN) | UI label (ZH) |
|---------|----------|-----------|---------------|---------------|
| Category | `t_topic` | `TOP_*` | Category | 类别 |
| Action | `t_action` | `ACT_*` | Action | 行动项 |
| Meeting | `t_meeting_instance` | `MIN_*` | Meeting | 会议 |
| Workflow | `t_workflow_template` | `WFT_*` | Workflow | 工作流 |

> **Taxonomy note (2026-03-17)**: User-facing terminology is consolidated on **Category** for the strategic classification stored in `t_topic` / `TOP_*`. Actions support 1..2 categories; meetings and meeting decisions support 0..2 categories; workflow instances do not store categories.

---

## 5. Project History Timeline

| Version | Date | Milestone |
|---------|------|-----------|
| V1.0 | 2026-01 | MVP: Action CRUD, import, personal dashboard, Excel export |
| V1.1 | 2026-01 | Meetings, Gantt, notifications, comments |
| V2.0 | 2026-02 | Workflow engine V2 (pilot, SLA, approvals, in-app template editing, Drawflow canvas) |
| V3.0 | 2026-03 | Frontend/backend separation (SEP-0 → SEP-4), React SPA |
| V3.5 | 2026-03 | Workflow V3 (3-phase lifecycle, gateways, service steps, parallel branches, React Flow canvas) |

---

## 6. Product Trajectory

ActionHub's current trajectory focuses on strengthening execution discipline in three areas:

| Phase | Capability | Status |
|-------|-----------|--------|
| **Current** | Centralized action log, meeting follow-up, workflow engine | ✅ Deployed |
| **Near-term** | P11 category consolidation closeout, P12 meeting series workspace polish, broader validation | 🚧 In progress |
| **Long-term** | Better analytics, broader integrations, more automation | 🔮 Vision only |
