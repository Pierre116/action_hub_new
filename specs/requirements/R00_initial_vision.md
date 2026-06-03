# ActionHub — Vision & Foundation

> **Status**: Requirements-level specification  
> **Depends on**: None (root document)  
> **Decisions**: D1–D15 in `DECISIONS.md`  
> **Consumed by**: SpecForge for `00_initial_vision.md`, `02_functional_scope.md`

---

## §1 Project Overview

**ActionHub** is a centralized action log and follow-up platform designed to replace fragmented Excel-based action tracking across multiple teams. The system provides a single shared pool of action items, structured assignment workflows, automated follow-up notifications, and multi-level dashboards.

### Problem Statement

- Action items are scattered across 4+ Excel workbook formats with inconsistent schemas
- No automated follow-up — overdue items are discovered only in biweekly meetings
- No visibility — management lacks a cross-team overview
- No assignment accountability — no formal accept/decline mechanism
- Bilingual data (Chinese/English) with no standardized taxonomy


### Solution

A browser-based web application deployed on a local Windows server that:

1. Centralizes all action items in a shared SQLite database (zero-config, single-file)
2. Uses a single-owner action model with optional explicit assignees for visibility/workload while keeping one designated owner per action
3. Offers personal, team, and category dashboards with KPI cards
4. Supports bilingual UI (Chinese + English toggle)
5. Imports existing Excel logbook data (.xlsx only; no mandatory columns; interactive dept/category mapping)
6. Exports filtered action lists to Excel
7. Enables inline status updates for minimal friction; Admin can inline-edit all key fields (status, owner, deadline, priority, title, category) in a paginated action table (25 rows/page)
8. Delivers a "what do I do today?" personal dashboard as the landing page; completed/cancelled actions always shown but visually faded
9. Organizes actions by **global Categories** managed through the admin taxonomy configuration
10. Provides **structured comments** on actions: three types — *Comment*, *Achievement*, *Roadblock* — all rich-text, editable by Admin / TeamLead / author, and logged to action history
12. Exposes a **Category Dashboard** with KPIs (open / overdue / done / on-time / workload) and links actions to **meeting instances** (by date + type — not necessarily weekly); meeting memos (any file type) uploaded and stored as binary blob per meeting instance
19. Workflow instances are only started manually by the user from a dedicated workflow page or endpoint. Workflow instances do not carry their own Categories. Any category selection at workflow request time applies to the bound or created action. Team is not linkable at workflow creation. There is no auto-start or auto-binding logic for workflow instances.
13. Provides **View-by-Person**: every authenticated user can see all actions across all teams; team managers see per-employee workload cards (open + overdue per person)
14. Renders a **Gantt timeline** for a visual overview of actions/deadlines by team, category, or assignee
15. Shows an **in-app notification bell** with unread badge for assignment events and approaching deadlines
16. Employee list in Admin is editable with a team dropdown (employee always belongs to exactly one team)
17. **Personal Dashboard — enhanced**: tabbed view with four modes — *Overview* (KPI cards + overdue/due-soon), *By Deadline* (chronological flat list of all personal actions, faded when done/cancelled), *By Category* (actions grouped by category with per-category KPI row), and *Gantt* (personal timeline of actions by deadline); Admin and TeamLead can **switch employee** via a dropdown at the top of the Personal Dashboard to view any user's data (read-only)
18. Exposes a local **MCP (Model Context Protocol) server** (`mcp_actionhub/`) so AI agents (Claude Desktop, Copilot, etc.) can query ActionHub data in natural language; read-only tools: `get_actions`, `get_action_detail`, `get_my_actions`, `get_meetings`, `get_dashboard_summary`, `search_actions`; write tools (V1.1): `create_action`, `update_status`

### Execution Management Intent

ActionHub should remain focused on **execution management** for delivery-critical work. The platform is intended to make actions, owners, deadlines, meeting follow-up, and workflow steps visible across teams without adding parallel assessment layers.

This intent means ActionHub should progressively support:

1. clearer ownership and handoffs across EP&I, Supply Chain, and Manufacturing
2. meeting-driven follow-up with decisions linked to resulting actions
3. workflow stages that structure work and escalation without extra parallel status models
4. dashboards that summarize overdue work, capacity, and completion signals while keeping drill-down on the underlying actions

---

## §2 Strategic Goals

### Short-Term (V1 — 1.5-day MVP)

**Day 1 (Full Day) — Core Foundation + First Usable Product:**
- Project scaffold (Python web framework + SQLite + Jinja2 templates)
- SQLite database schema (core tables: Action, User, Team, Category, Assignment, ActionHistory)
- Simple auth (login page + bcrypt password in SQLite)
- Admin bootstrap: seed 12 teams + 8 categories + admin user account
- Action CRUD (create, read, update, delete) with status lifecycle (Open → In Progress → Under Review → Done)
- Action list page with filtering (team, status, priority, date range) + sorting
- Action detail page with activity stream
- New/edit action form with category selectors (primary required, secondary optional)
- Lead-based assignment model (creator is audit source; Lead is accountable role; immediate active assignment records when applicable)
- Seed data import from 4 Excel files (auto-detect format, preview, bulk create)
- Personal dashboard: "My Actions" + "Overdue" + "Recent Activity"
- User management page (Admin creates accounts)
- Quick-capture: "+" button always visible for fast action creation

**Day 2 AM (Half Day) — Dashboards + Export + Go-Live:**
- Team summary dashboard (KPI cards + status donut chart + overdue table)
- Bilingual UI toggle (English/Chinese — pre-built translation file)
- Excel export from any filtered action list
- Action list inline status update (click status badge → dropdown → update in-place)
- Final testing + bug fixes
- Deployment to Windows server + go-live

### V1.1 (Week 2 — Engagement & Hardening)

**Committed V1.1 scope:**

| Feature | Phase |
|---------|-------|
| Meeting memo upload (any file type, stored as DB blob, linked to meeting instance) | **MVP** |
| In-app notification bell with unread badge | **MVP** |
| Full RBAC enforcement (Admin / TeamLead / Member / ReadOnly) | V1.1 |
| Tags (free-form labels) | V1.1 |
| Team + Management dashboards | V1.1 |

Additional V1.1 work:
- Email notifications (SMTP: deadline reminders, assignment alerts)
- Notification preferences per user (which events trigger bell / email)
- Bulk operations (status change, reassign)
- Notification preferences per user
- Admin taxonomy configuration page (tree view)
- Windows AD/LDAP authentication

### V1.2 (Week 3–4 — Power Features)

- Scheduled report generation + auto-email delivery
- Report builder (custom columns, filters, grouping)
- Auto-escalation rules (overdue → escalated based on priority)
- Action dependencies (blocks / related_to)
- Trend charts (completion velocity, created vs completed)
- Management summary dashboard with drill-down
- Advanced search + saved filters

### Mid-Term (V2 — 2 months)

- Configurable workflow engine for multi-step processes
- Action dependencies and blocking relationships
- Trend charts and advanced analytics
- Advanced taxonomy with admin-configurable categories

### Long-Term (V3+ — 6 months)

- Agent framework for intelligent task routing and escalation
- Integration with external systems (SAP, email, WeChat) when needed
- Predictive analytics (risk of missing deadline, workload forecasting)

---

## §3 Key Stakeholders

| Stakeholder | Role | Interaction | MVP vs V1.1 |
|-------------|------|-------------|-------------|
| Team Heads | Review team dashboards, approve closures | Weekly | MVP: dept dashboard |
| Team Leads | Create/assign actions, validate completion | Daily | MVP: full CRUD + assign |
| Team Members | Execute actions, update status inline | Daily | MVP: dashboard + inline update |
| Plant Manager | View cross-team summary, escalation | Weekly | V1.1: mgmt dashboard |
| IT/Admin | User management, system configuration | As needed | MVP: user CRUD + import |
| Digitalization Team | System owner, seed data import | Ongoing | MVP: import + config |

---

## §4 Functional Scope — Core Domains

| Domain | Description | MVP (1.5d) | V1.1 | V1.2 |
|--------|-------------|:---:|:---:|:---:|
| **Action Management** | CRUD for actions, status lifecycle, priority levels | ✅ | — | Dependencies |
| **Assignment** | Lead-based model; optional explicit assignees | ✅ (simple) | Reassign, richer bulk ops | Bulk ops |
| **Taxonomy** | Teams, teams, global Categories (admin/TeamLead CRUD), categories | ✅ | Tags | — |
| **Comments** | Rich-text comments (Comment / Achievement / Roadblock) on actions; editable by Admin, TeamLead, author; audit-logged | ✅ | — | — |
| **Dashboards** | Personal + Team + Category views with KPI cards | ✅ (3 views) | Team + Management | Trend charts |
| **Gantt Timeline** | Visual Gantt chart of actions by deadline | ✅ | Filter by dept/category/person | — |
| **View by Person** | Scoped visibility: Created by/Lead/explicit assignment/meeting participant/team-lead policy | ✅ | — | — |
| **Reporting** | Excel export from filtered views | ✅ (ad-hoc) | Report builder | Scheduled |
| **Data Import** | Excel (.xlsx) only; no mandatory columns; interactive dept/category mapping | ✅ | Merge/dedup UI | — |
| **Meeting Instances** | Actions linkable to meeting instance; meeting memo upload (any file type, blob in DB) | ✅ | AI summarizer | — |
| **Security** | Simple auth + basic role check | ✅ | AD/LDAP, full RBAC | — |
| **Bilingual UI** | English/Chinese toggle | ✅ | Polish + date formats | — |
| **Notifications** | In-app status indicators on dashboard | ✅ (passive) | Email + bell + prefs | Digest |
| **Admin** | User creation, Category/Team CRUD, taxonomy seed | ✅ (full CRUD) | Full admin panel | — |

---

## §5 Scope Boundary

### V1 — In-Scope (to be spec'd)

- R01: Entity model (actions, users, teams, categories, assignments, global categories, meeting instances, comments)
- R02: Action lifecycle (statuses, priorities, escalation — no auto-escalation in MVP)
- R03: Action accountability model (Lead-based with explicit assignee compatibility)
- R04: Notifications (in-app dashboard indicators only — email in V1.1)
- R05: Dashboards (Personal + Team + **Category** + **Gantt** — Team + Management in V1.1)
- R06: Security (simple auth; view-by-person for all authenticated users; AD/full RBAC in V1.1)
- R07: Data import (Excel .xlsx only; no mandatory columns; interactive dept/category mapping)
- R08: Taxonomy (teams + teams + **global Categories** (admin/TeamLead CRUD) + categories seeded; full admin CRUD UI in MVP)
- R09: Bilingual UI (Chinese/English toggle)
- R12: Comments (rich-text, 3 types: Comment/Achievement/Roadblock, on actions, audit-logged)
- R13: Meeting Instances (date-based, category-linked, actions linkable to specific instance; meeting memo file upload as binary blob in SQLite)
- R15: Admin inline-editable actions table (Status, Owner, Deadline, Priority, Title, Category; 25 rows/page, prev/next pagination)
- R16: In-app notification bell (badge with unread count; events: assigned to action, deadline within 3 days, action overdue)
- R17: Employee list admin page with team dropdown (one dept per employee, required)

### V1.1 — Engagement (Week 2)

- Email notifications (SMTP)
- In-app notification bell
- Meeting minutes upload (.xlsx) linked to actions
- Tags (free-form labels)
- Team + Management dashboards
- Bulk operations
- Admin taxonomy configuration panel
- Windows AD/LDAP integration
- Full RBAC enforcement (Admin / TeamLead / Member / ReadOnly)

### V2+ — Out-of-Scope (acknowledged, not spec'd)

- R10: Workflow engine (configurable multi-step processes; workflow instances are only started manually, and do not carry their own categories or team link at creation. Any category selection applies to the bound or created action. No auto-start or auto-binding logic is permitted.)
- R11: Agent framework (automated routing, AI-driven escalation)
- Mobile-native app (V1 is responsive web only)
- External integrations (SAP, WeChat, Teams)
- Effort/time-tracking per action (V1 is count-based only)
- File versioning for meeting minutes
- Offline capability
- Action dependencies (V1.2)
- Trend charts (V1.2)
- Scheduled reports (V1.2)
- Report builder (V1.2)
- Auto-escalation (V1.2)

### §5.1 Launch Phasing (1.5-Day Sprint)

| Phase | Milestone | Duration | Risk Mitigation |
|-------|-----------|----------|------------------|
| **Day 1 AM** | Project scaffold, SQLite schema, auth, team seed, Action CRUD API | 4h | Use proven stack (Flask/Django); schema from R01 pre-validated |
| **Day 1 PM** | Action list + detail pages, new/edit form, simple assignment, seed import | 4h | Import v3+v4 first (largest datasets); v1+v2 are simpler to add |
| **Day 1 EVE** | Personal dashboard, user management, quick-capture, bug fixes | 2h | Dashboard = 3 queries + template; no charts yet, just KPI cards |
| **Day 2 AM** | Team dashboard, bilingual toggle, inline status update, Excel export | 3h | i18n = swap JSON file; export = openpyxl write from queryset |
| **Day 2 Noon** | Final testing, deployment to Windows server, go-live | 1h | SQLite = copy 1 file; no DB server to configure |

**Total: ~14 hours of focused development (1.5 working days)**

**Risk buffer**: If Day 1 EVE runs over, the personal dashboard can be simplified to a filtered action list ("My Actions" tab). The team dashboard from Day 2 AM can ship with KPI cards only (no chart), adding the donut chart in V1.1.

---

## §6 Core User Journeys

### Journey 1: Team Lead Creates Action from Meeting

```
Open app → Click "+" quick-capture button → Type title + set deadline + pick priority
→ Save (30 seconds) → Optionally open full form to add description, assign delegates
→ Action appears on personal dashboard immediately
```

### Journey 2: Team Member Checks Their Actions

```
Open app → Land on Personal Dashboard (“Today” view) → See overdue items in red
→ Click status badge on overdue action → Change to “In Progress” inline
→ Open action detail → Add comment “Waiting for supplier reply” → Close
```

### Journey 3: Manager Reviews Cross-Team Status

```
Open app → Navigate to Team dashboard → See KPI cards (open/overdue/done)
→ Filter by team → Click overdue count card → See filtered action list
→ Export to Excel → Share in Monday meeting
```

### Journey 4: Admin Imports Historical Data

```
Open app → Admin → Import → Upload action logbook-v3.xlsx → System auto-detects format
→ Preview: 89 rows mapped → Resolve 3 unknown owners → Confirm import
→ All actions appear in action list immediately → Personal dashboard populated
```

---

## §7 Non-Functional Requirements

| Category | MVP Launch (Day 2 noon) | V1.1 (Week 2) |
|----------|------------------------|----------------|
| **Response time** | < 3s page load | < 2s page load |
| **Concurrent users** | 5 | 10 |
| **Availability** | Business hours (8h × 5d) | Business hours |
| **Data retention** | 3 years | 5 years |
| **Browser support** | Chrome, Edge (latest) | Chrome, Edge, Firefox |
| **Language** | Chinese + English toggle | Chinese + English toggle |
| **Backup** | Manual SQLite file copy | Daily automated copy |
| **Deployment** | Single Windows server | Single Windows server |
| **Authentication** | Username/password | Windows AD/LDAP |
| **Database** | SQLite (WAL mode) | SQLite (WAL mode) |

---

## §7b UX & Engagement Strategy

### First-5-Minutes Experience

The MVP’s adoption depends on the first interaction. Within 5 minutes of seeing ActionHub, a user must:
1. **See their data** — imported Excel actions are already there
2. **Understand what’s overdue** — red highlights, overdue count prominent
3. **Update a status** — click status badge inline, pick new status, done
4. **Find anything** — filter by team/status/priority or text search

### Quick-Capture

A persistent "+" floating action button (bottom-right) opens a minimal form:
- Title (required)
- Deadline (required)
- Team (pre-filled from user profile)
- Priority (default: Medium)

The full form is accessible via "More details" link. Quick-capture removes the friction of "I’ll add it later" and captures actions during meetings in real-time.

### "Today" Focus View

The personal dashboard answers "What should I do today?" with 3 sections:
1. **🔴 Overdue** — red cards, sorted oldest-first, one-click status update
2. **⚠️ Due This Week** — amber cards, sorted by deadline
3. **✅ Recently Completed** — green cards (last 7 days) as positive reinforcement

### Inline Status Updates

From the action list page, users can change status without opening the detail page:
- Click the status badge → dropdown of valid next statuses → select → instant save
- Visual feedback: badge color animates to new status color
- Reduces a 3-click workflow to 2 clicks

### Progress Indicators

- Team dashboard shows a **completion progress bar** per team
- KPI cards use **green/amber/red** thresholds (>80% on-time = green, 60-80% = amber, <60% = red)
- Overdue count has a **pulse animation** when > 0 to draw attention

### Zero-Training Onboarding

- First login shows a 3-step tooltip tour: "Your actions" → "Filters" → "Quick capture"
- Empty states show contextual CTAs: "No overdue actions — great job! 🎉" rather than blank screens
- All buttons have bilingual tooltips on hover

---

## §8 Validation Gate Anchors

| Gate | Validates | Blocks |
|------|-----------|--------|
| G1 | Entity model covers all 4 Excel schemas | Data dictionary generation |
| G2 | All statuses and transitions defined | Lifecycle FSM |
| G3 | Lead-based assignment and visibility rules work end-to-end | Action lead workflow |
| G4 | Personal dashboard shows correct KPIs | UI spec generation |
| G5 | Simple auth works; import produces correct action records | Go-live |
