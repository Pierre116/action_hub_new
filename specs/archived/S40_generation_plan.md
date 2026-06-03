# ActionHub — Generation Plan

> **⚠️ ARCHIVED 2026-03-12** — Superseded by root `CODE_GENERATION_PLAN.md` which is the active, living implementation roadmap. Kept for historical reference only.

> **Level**: L5 — Planning  
> **Source**: S30_physical_specs.md (structure), S02_functional_scope.md (MoSCoW)  
> **Purpose**: Phased code generation roadmap — what to build, in what order, with validation gates

---

## 0. Phasing Summary

| Phase | Name | Timeline | Scope |
|-------|------|----------|-------|
| **Phase 1** | Foundation | Day 1 Morning (4h) | Project skeleton, DB, auth, seed data |
| **Phase 2** | Core Actions | Day 1 Afternoon (4h) | Action CRUD, status FSM, assignments, history |
| **Phase 2b** | SubActions & Comments | Day 1 Evening (2h) | t_subaction + t_comment CRUD, parent rollup, comment types |
| **Phase 3** | Views & Dashboards | Day 2 Morning (4h) | Dashboards, action list, detail, i18n, export |
| **Phase 3b** | Business Theme Dashboard & Gantt | Day 2 Afternoon (2h) | Business Theme KPI dashboard, Gantt timeline view |
| **Phase 4** | Admin & Import | Day 2 (remaining) | User management, import wizard, taxonomy admin, category + meeting admin |
| **Phase 5** | Hardening & Readiness | Week 2 | Automated tests, deployment scripts, config hardening, runbook |
| **Phase 5b** | V1.1 Committed Features | Week 3 | Accept/decline flow, meeting summary upload, full RBAC, tags |
| **Phase 6** | V1.2 Polish | Week 4 | Advanced charts, performance tuning, mobile fixes |

---

## 1. Phase 1 — Foundation (Day 1 AM)

### 1.1 Tasks

| # | Task | Output Files | Depends On |
|---|------|-------------|------------|
| 1.1 | Create project skeleton | All `__init__.py`, `app.py`, `config.py`, `wsgi.py` | — |
| 1.2 | Write `db/schema.sql` from S20_MLD.md | `db/schema.sql` | 1.1 |
| 1.3 | Write `init_db.py` | `init_db.py` | 1.2 |
| 1.4 | Write `db/seed.sql` (12 depts, 8 categories) | `db/seed.sql` | 1.2 |
| 1.5 | Write `seed_data.py` | `seed_data.py` | 1.3, 1.4 |
| 1.6 | Implement `middleware/db.py` (get_db, close_db) | `actionhub/middleware/db.py` | 1.1 |
| 1.7 | Implement auth service (bcrypt, sessions, lockout) | `actionhub/auth/service.py` | 1.6 |
| 1.8 | Implement auth routes (login, logout, me) | `actionhub/auth/routes.py` | 1.7 |
| 1.9 | Implement auth middleware (@login_required, @admin_required) | `actionhub/middleware/auth_middleware.py` | 1.7 |
| 1.10 | Create `templates/base.html` (nav, layout) | `templates/base.html` | 1.1 |
| 1.11 | Create `templates/login.html` | `templates/login.html` | 1.10 |
| 1.12 | Write `requirements.txt` | `requirements.txt` | — |
| 1.13 | Copy static vendor assets (Bootstrap, Chart.js) | `static/vendor/` | — |

### 1.2 Validation Gate (G1)

| Check | Pass Criteria |
|-------|--------------|
| DB initializes cleanly | `init_db.py` runs without errors, all tables created |
| Seed data loads | 12 teams + 8 categories in DB |
| Login works | Admin user can log in, session cookie set |
| Logout works | Session destroyed, redirect to login |
| Auth middleware blocks | Unauthenticated requests → 401 redirect |
| Login page renders | `/login` shows form in EN + CN |

---

## 2. Phase 2 — Core Actions (Day 1 PM)

### 2.1 Tasks

| # | Task | Output Files | Depends On |
|---|------|-------------|------------|
| 2.1 | Implement ref generator (`ACT-YYYY-NNNNN`) | `actionhub/utils/ref_generator.py` | Phase 1 |
| 2.2 | Implement action service (create, read, update) | `actionhub/actions/service.py` | 2.1 |
| 2.3 | Implement status FSM (VALID_TRANSITIONS, side effects) | Within `service.py` | 2.2 |
| 2.4 | Implement action history logging | Within `service.py` | 2.2 |
| 2.5 | Implement assignment service (Lead/Delegate/Participate) | Within `service.py` | 2.2 |
| 2.6 | Implement action queries (filter, sort, paginate) | `actionhub/actions/queries.py` | 2.2 |
| 2.7 | Implement action routes (REST API) | `actionhub/actions/routes.py` | 2.2, 2.6 |
| 2.8 | Implement input validators | `actionhub/utils/validators.py` | — |
| 2.9 | Implement error handlers | `actionhub/middleware/error_handlers.py` | Phase 1 |

### 2.2 Validation Gate (G2)

| Check | Pass Criteria |
|-------|--------------|
| Create action | POST returns 201 with ref |
| Read action | GET returns all fields |
| Update action | PATCH returns updated fields |
| Status transitions | All valid transitions work (5 statuses), invalid blocked |
| Side effects | Done → actual_date set; On Hold → reason required |
| History | Every field change logged |
| Assignment | Lead + Delegates + Participate roles created |
| Filters | Status, team, priority, search all filter correctly |
| Pagination | page/per_page work with correct totals |

---

## 2b. Phase 2b — SubActions & Comments (Day 1 Evening)

### 2b.1 Tasks

| # | Task | Output Files | Depends On |
|---|------|-------------|------------|
| 2b.1 | Extend `db/schema.sql` with t_subaction + t_comment DDL | `db/schema.sql` | 1.2 |
| 2b.2 | Implement subaction service (create, update, delete, rollup) | `actionhub/actions/subaction_service.py` | Phase 2 |
| 2b.3 | Implement subaction routes (REST API) | Extend `actionhub/actions/routes.py` | 2b.2 |
| 2b.4 | Implement comment service (create, edit, soft-delete, types) | `actionhub/actions/comment_service.py` | Phase 2 |
| 2b.5 | Implement comment routes (REST API) | Extend `actionhub/actions/routes.py` | 2b.4 |
| 2b.6 | Implement comment audit logging (ActionHistory) | Within `comment_service.py` | 2b.4 |

### 2b.2 Validation Gate (G2b)

| Check | Pass Criteria |
|-------|--------------|
| Create sub-action | POST returns 201; parent_act_id or parent_sac_id set correctly |
| Status rollup | All siblings Done → parent automatically set to Done |
| Unlimited depth | Sub-action of sub-action created successfully |
| Comment types | Comment/Achievement/Roadblock all accepted; invalid type rejected 400 |
| Comment edit | Only Admin/TeamLead/author can edit; CMT_EDITED_AT updated |
| Comment soft-delete | CMT_IS_DELETED = 1; record remains in DB |
| Comment history | CommentAdded/CommentEdited/CommentDeleted appear in ActionHistory |

---

## 3. Phase 3 — Views & Dashboards (Day 2 AM)

### 3.1 Tasks

| # | Task | Output Files | Depends On |
|---|------|-------------|------------|
| 3.1 | Implement dashboard service (KPI queries) | `actionhub/dashboard/service.py` | Phase 2 |
| 3.2 | Implement dashboard routes | `actionhub/dashboard/routes.py` | 3.1 |
| 3.3 | Create personal dashboard template | `templates/dashboard/personal.html` | 3.1 |
| 3.4 | Create team dashboard template | `templates/dashboard/team.html` | 3.1 |
| 3.5 | Create action list template (filters, table) | `templates/actions/list.html` | Phase 2 |
| 3.6 | Create action detail template (tabs, history, sub-actions, comments) | `templates/actions/detail.html` | Phase 2 |
| 3.7 | Create action form template (create/edit) | `templates/actions/form.html` | Phase 2 |
| 3.8 | Create quick-capture modal partial | `templates/actions/_quick_capture.html` | Phase 2 |
| 3.9 | Write i18n JSON files (en.json, zh.json) | `actionhub/i18n/` | — |
| 3.10 | Implement language toggle | `actionhub/i18n/__init__.py` + JS | 3.9 |
| 3.11 | Write custom CSS (actionhub.css) | `static/css/actionhub.css` | — |
| 3.12 | Write dashboard.js (KPI/status breakdown rendering) | `static/js/dashboard.js` | 3.3 |
| 3.13 | Write actions.js (filters, pagination, detail rendering, status transitions) | `static/js/actions.js` | 3.5 |
| 3.14 | Write quick-capture.js (FAB modal) | `static/js/quick-capture.js` | 3.8 |
| 3.15 | Implement export (openpyxl writer) | `actionhub/export/excel_writer.py` | Phase 2 |
| 3.16 | Implement export route | `actionhub/export/routes.py` | 3.15 |
| 3.17 | Implement taxonomy routes | `actionhub/taxonomy/routes.py` | Phase 1 |
| 3.18 | Create sub-action tree partial | `templates/actions/_subaction_tree.html` | Phase 2b |
| 3.19 | Create comment thread partial | `templates/actions/_comment_thread.html` | Phase 2b |
| 3.20 | Write comments.js (post/edit/delete interactions) | `static/js/comments.js` | 3.19 |

### 3.2 Validation Gate (G3)

| Check | Pass Criteria |
|-------|--------------|
| Personal dashboard | KPI cards show correct numbers |
| Team dashboard | Dept selector works, KPIs update |
| Action list | Filters, sort, pagination all work in UI |
| Action detail | Action, assignments, sub-action tree, comment thread, history all render |
| Status transitions | List/detail status controls call OP05 successfully with validation |
| Quick capture | Modal opens, creates action, redirects to detail page |
| Comment thread | Post/edit/delete comment visible without page reload |
| i18n | EN/CN toggle swaps all UI strings |
| Export | .xlsx downloads with filtered data |

---

## 3b. Phase 3b — Business Theme Dashboard & Gantt (Day 2 PM)

### 3b.1 Tasks

| # | Task | Output Files | Depends On |
|---|------|-------------|------------|
| 3b.1 | Implement Category KPI service (K50–K54) | `actionhub/dashboard/topic_service.py` | Phase 2 |
| 3b.2 | Implement Business Theme Dashboard route | `actionhub/dashboard/routes.py` (extend) | 3b.1 |
| 3b.3 | Create Business Theme Dashboard template | `templates/dashboard/topic.html` | 3b.1 |
| 3b.4 | Implement Gantt data route (GET /gantt) | `actionhub/gantt/routes.py` | Phase 2 |
| 3b.5 | Create Gantt page template | `templates/gantt/gantt.html` | 3b.4 |
| 3b.6 | Write gantt.js (Chart.js horizontal bar timeline) | `static/js/gantt.js` | 3b.5 |

### 3b.2 Validation Gate (G3b)

| Check | Pass Criteria |
|-------|--------------|
| Category KPI cards | K50–K54 all show correct values |
| Category action list | Filtered to selected category only |
| Gantt renders | Actions with deadlines shown as horizontal bars |
| Gantt filters | Filter by dept/category/person collapses chart |

---

## 4. Phase 4 — Admin & Import (Day 2 PM)

### 4.1 Tasks

| # | Task | Output Files | Depends On |
|---|------|-------------|------------|
| 4.1 | Implement user CRUD service | `actionhub/admin/user_service.py` | Phase 1 |
| 4.2 | Implement user management routes | `actionhub/admin/routes.py` | 4.1 |
| 4.3 | Create user management template | `templates/admin/users.html` | 4.2 |
| 4.4 | Implement import service (detect, preview, execute) | `actionhub/admin/import_service.py` | Phase 2 |
| 4.5 | Implement import routes | `actionhub/admin/routes.py` (extend) | 4.4 |
| 4.6 | Create import wizard template (3 steps) | `templates/admin/import.html` | 4.5 |
| 4.7 | Write import.js (wizard interactions) | `static/js/import.js` | 4.6 |
| 4.8 | Implement import rollback (OP13, D98) | Extend `import_service.py` + route | 4.4 |
| 4.9 | Create taxonomy admin template | `templates/admin/taxonomy.html` | 3.17 |
| 4.10 | Implement Category service (CRUD, archive) | `actionhub/admin/topic_service.py` | Phase 1 |
| 4.11 | Implement Category admin routes | `actionhub/admin/routes.py` (extend) | 4.10 |
| 4.12 | Create Category admin template | `templates/admin/topics.html` | 4.11 |
| 4.13 | Implement Meeting Instance service (create, link actions) | `actionhub/meetings/service.py` | Phase 2 |
| 4.14 | Implement Meeting Instance routes | `actionhub/meetings/routes.py` | 4.13 |
| 4.15 | Create Meeting Instance template | `templates/meetings/list.html` + `detail.html` | 4.14 |

### 4.2 Validation Gate (G4)

| Check | Pass Criteria |
|-------|--------------|
| Create user | New user can log in |
| Edit user | Changes persisted |
| Deactivate user | User cannot log in |
| Reset password | New password works |
| Import detect | v1/v2/v3/v4 formats detected correctly |
| Import preview | 20 rows shown, unresolved owners listed |
| Import execute | Actions created with source=Import |
| Import summary | Correct counts (imported/skipped/duplicates) |
| Import rollback | DELETE removes all actions from that import batch |
| Create category | New category appears in list; unique name enforced |
| Archive category | Existing actions retain category; new actions cannot use archived category |
| Create meeting instance | Instance linked to actions; type = free text accepted |

---

## 5. Phase 5 — Hardening & Deployment Readiness (Week 2)

### 5.1 Tasks

| # | Task | Output Files | Depends On |
|---|------|-------------|------------|
| 5.1 | Add test scaffolding | `tests/conftest.py` | Phase 4 |
| 5.2 | Add auth test coverage | `tests/test_auth.py` | 5.1 |
| 5.3 | Add actions test coverage | `tests/test_actions.py` | 5.1 |
| 5.4 | Add dashboard test coverage | `tests/test_dashboard.py` | 5.1 |
| 5.5 | Add import+rollback test coverage | `tests/test_import.py` | 5.1 |
| 5.6 | Add export test coverage | `tests/test_export.py` | 5.1 |
| 5.7 | Add backup automation script | `backup.bat` | Phase 1 |
| 5.8 | Add Windows service install script | `install_service.ps1` | Phase 1 |
| 5.9 | Add repo/runtime hygiene files | `.gitignore`, `.env.example` | — |
| 5.10 | Add operations runbook | `README.md` | Phase 4 |
| 5.11 | Harden session/config runtime | `config.py`, `actionhub/__init__.py`, `requirements.txt` | Phase 1 |

### 5.2 Validation Gate (G5)

| Check | Pass Criteria |
|-------|--------------|
| Automated tests | `python -m unittest discover -s tests -p "test_*.py"` passes |
| Auth regression | Login/auth middleware tests pass |
| Action regression | CRUD/FSM/assignment tests pass |
| Import rollback safety | Preview/execute/history/rollback tests pass |
| Export correctness | Excel export endpoint returns valid workbook |
| Production config safety | `ACTIONHUB_ENV=production` without `SECRET_KEY` is blocked |
| Deployment artifacts ready | `backup.bat` and `install_service.ps1` present and executable |

---

## 5b. Phase 5b — V1.1 Committed Features (Week 3)

| # | Task | Output Files | Notes |
|---|------|-------------|-------|
| 5b.1 | Accept/Decline assignment flow (OP: ASG_STATUS) | `actionhub/actions/assignment_service.py` | RBAC: TeamLead/Admin approve only |
| 5b.2 | Meeting summary file upload (t_meeting_summary) | `actionhub/meetings/summary_service.py` | .pdf/.docx/.xlsx |
| 5b.3 | Full RBAC enforcement (TeamLead role gates) | `actionhub/middleware/auth_middleware.py` | Separate from Admin |
| 5b.4 | Tag CRUD + tagging actions | `actionhub/admin/tag_service.py`, UI | Free-form labels |
| 5b.5 | Team Dashboard (KPIs by team within dept) | `actionhub/dashboard/team_service.py` | V1.1 committed |
| 5b.6 | Management Dashboard (cross-dept, top contributors) | `actionhub/dashboard/mgmt_service.py` | Admin/Management |

---

## 6. Phase 6 — V1.2 Polish (Week 4)

| # | Task | Notes |
|---|------|-------|
| 6.1 | Advanced filtering (date ranges, multi-status) | UI + query enhancement |
| 6.2 | Chart.js dashboards (trend lines, bar charts) | `dashboard.js` expansion |
| 6.3 | Tag management UI | Admin taxonomy tab |
| 6.4 | Bulk status update (select multiple → change) | Action list enhancement |
| 6.5 | Performance profiling + index tuning | SQLite EXPLAIN analysis |
| 6.6 | Error page templates (404, 500) | `templates/errors/` |
| 6.7 | Help / onboarding tooltips | First-5-minutes polish |
| 6.8 | Mobile responsive testing + fixes | CSS media queries |

---

## 7. File Generation Order

For AI-assisted code generation, files should be generated in this exact sequence to satisfy all dependencies:

```
1.  requirements.txt
2.  config.py
3.  db/schema.sql
4.  db/seed.sql
5.  init_db.py
6.  seed_data.py
7.  actionhub/__init__.py          (create_app factory)
8.  actionhub/middleware/db.py
9.  actionhub/middleware/error_handlers.py
10. actionhub/middleware/auth_middleware.py
11. actionhub/auth/service.py
12. actionhub/auth/routes.py
13. actionhub/utils/ref_generator.py
14. actionhub/utils/validators.py
15. actionhub/utils/date_utils.py
16. actionhub/actions/queries.py
17. actionhub/actions/service.py
18. actionhub/actions/routes.py
19. actionhub/taxonomy/routes.py
20. actionhub/dashboard/service.py
21. actionhub/dashboard/routes.py
22. actionhub/export/excel_writer.py
23. actionhub/export/routes.py
24. actionhub/admin/user_service.py
25. actionhub/admin/import_service.py
26. actionhub/admin/routes.py
27. actionhub/admin/topic_service.py
28. actionhub/actions/subaction_service.py
29. actionhub/actions/comment_service.py
30. actionhub/meetings/service.py
31. actionhub/meetings/routes.py
32. actionhub/dashboard/topic_service.py
33. actionhub/gantt/routes.py
34. actionhub/i18n/__init__.py
35. actionhub/i18n/en.json
36. actionhub/i18n/zh.json
37. static/css/actionhub.css
38. static/js/app.js
39. static/js/dashboard.js
40. static/js/actions.js
41. static/js/quick-capture.js
42. static/js/import.js
43. static/js/comments.js
44. static/js/gantt.js
45. templates/base.html
46. templates/login.html
47. templates/dashboard/personal.html
48. templates/dashboard/team.html
49. templates/dashboard/topic.html
50. templates/actions/list.html
51. templates/actions/detail.html
52. templates/actions/form.html
53. templates/actions/_quick_capture.html
54. templates/actions/_subaction_tree.html
55. templates/actions/_comment_thread.html
56. templates/admin/users.html
57. templates/admin/import.html
58. templates/admin/taxonomy.html
59. templates/admin/topics.html
60. templates/meetings/list.html
61. templates/meetings/detail.html
62. templates/gantt/gantt.html
63. wsgi.py
64. tests/conftest.py
65. tests/test_auth.py
66. tests/test_actions.py
67. tests/test_dashboard.py
68. tests/test_import.py
69. tests/test_export.py
70. backup.bat
71. install_service.ps1
72. README.md
```

---

## 8. Definition of Done (MVP)

| # | Criterion | Verified By |
|---|-----------|-------------|
| 1 | Admin can log in and create users | Manual test |
| 2 | Any user can create an action (<10s via quick-capture) | Manual test |
| 3 | Status transitions follow FSM with side effects | Automated test |
| 4 | Personal dashboard shows correct KPIs | Manual test |
| 5 | Team dashboard shows teamal data | Manual test |
| 6 | Action list filters and sorts work | Manual test |
| 7 | Excel import processes all 4 logbook versions | Manual test with sample files |
| 8 | Excel export downloads filtered actions | Manual test |
| 9 | EN/CN toggle works on all pages | Manual test |
| 10 | All pages render correctly in Chrome/Edge | Manual test |
| 11 | Application starts as Windows service | NSSM test |
| 12 | Database backup script runs successfully | Scheduled task test |
| 13 | Business Theme Dashboard shows K50–K54 KPI cards | Manual test |
| 14 | Users can post Comment/Achievement/Roadblock on actions | Manual test |
| 15 | Sub-actions created at 2+ levels of depth | Manual test |
| 16 | Sub-action status rollup updates parent | Automated test |
| 17 | Gantt view renders all actions with deadlines as bars | Manual test |
| 18 | Meeting instances created and linked to actions | Manual test |
