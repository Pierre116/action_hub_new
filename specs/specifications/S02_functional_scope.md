# ActionHub — Functional Scope & MoSCoW Priorities

> **Level**: L0 — Foundation  
> **Merise Phase**: Schéma Directeur  
> **Source**: R00–R11 requirement files  
> **Decisions**: D1–D165

---

## 1. Functional Domain Decomposition

| Domain ID | Domain | Description | Primary R-File |
|-----------|--------|-------------|----------------|
| DOM-ACT | Action Management | CRUD, lifecycle, priority, escalation | R02 |
| DOM-ASG | Assignment | Lead-based model with explicit assignee compatibility | R03 |
| DOM-TAX | Taxonomy | Teams, teams, global Categories (admin/TeamLead managed), categories, tags | R08 |
| DOM-DSH | Dashboards | Personal, Team, Category, Gantt; Team, Management views | R05 |
| DOM-RPT | Reporting | Excel export, report builder, scheduled delivery | R05 |
| DOM-IMP | Data Import | Excel .xlsx import; no mandatory columns; interactive dept/category mapping | R07 |
| DOM-SEC | Security | Authentication, authorization, view-by-person, audit | R06 |
| DOM-I18 | Internationalization | Bilingual UI (EN/CN), date/number formats | R09 |
| DOM-NTF | Notifications | Dashboard indicators, email, in-app bell | R04 |
| DOM-CMT | Comments | Rich-text comments (Comment/Achievement/Roadblock) on actions | R12 |
| DOM-MTG | Meetings | Meeting instance tracking + action linking; minutes upload (.xlsx) in V1.1 | R13 |
| DOM-MDC | Meeting Decisions | Centralized decision log per meeting; lifecycle, search, dashboard integration | R17 |
| DOM-WFE | Workflow Engine | Configurable multi-step processes | R10 |
| DOM-AGT | Agent Framework | Automated routing and escalation | R11 |

---

## 2. MoSCoW Prioritization

### Must Have (MVP — 1.5 Days)

| ID | Feature | Domain | Source | Day |
|----|---------|--------|--------|-----|
| F001 | Action CRUD (create, read, update, delete) | DOM-ACT | R02 §2 | D1 AM |
| F002 | 7-status lifecycle (Open → In Progress → Under Review → Done + On Hold / Postponed / Cancelled) | DOM-ACT | R02 §3 | D1 AM |
| F003 | Priority levels (Critical / High / Medium / Low) with color coding | DOM-ACT | R02 §4 | D1 AM |
| F004 | Escalation field (Normal / Escalated / WAR) — manual only | DOM-ACT | R02 §5 | D1 AM |
| F005 | Reference code auto-generation (`ACT-{YYYY}-{SEQ:05d}`) | DOM-ACT | R02 §2.3 | D1 AM |
| F006 | Lead assignment at creation (active immediately) | DOM-ASG | R03 §2 | D1 PM |
| F007 | Inline status update (click badge → dropdown → save) | DOM-ACT | R02 §1 | D1 EVE |
| F008 | Quick-capture floating action button ("+" FAB) | DOM-ACT | R00 §7b | D1 EVE |
| F009 | `last_comment` field on Action (MVP shortcut for comments) | DOM-ACT | R02 §7 | D1 PM |
| F010 | 12 teams seeded at deployment | DOM-TAX | R08 §2.1 | D1 AM |
| F011 | Teams and Categories seeded from Excel analysis | DOM-TAX | R08 §2.2–§2.3 | D1 AM |
| F012 | 8 categories seeded | DOM-TAX | R08 §3.1 | D1 AM |
| F013 | Personal Dashboard — "Today" focus (Overdue / Due This Week / Completed) | DOM-DSH | R05 §3 | D1 EVE |
| F014 | Team Dashboard — KPI cards + overdue table | DOM-DSH | R05 §5 | D2 AM |
| F015 | Excel export from filtered action list | DOM-RPT | R05 §8.5 | D2 AM |
| F016 | Excel import (.xlsx only); no mandatory columns; interactive column mapping; interactive resolution when dept/category not found | DOM-IMP | R07 §4 | D1 PM |
| F017 | Import rollback (delete by import batch) | DOM-IMP | R07 §9 | D1 PM |
| F018 | Duplicate detection — exact title match | DOM-IMP | R07 §8 | D1 PM |
| F019 | User name resolution (exact match) | DOM-IMP | R07 §4.3 | D1 PM |
| F020 | Simple auth — username + bcrypt password | DOM-SEC | R06 §2.1 | D1 AM |
| F021 | Server-side sessions (HttpOnly cookie, 8h timeout) | DOM-SEC | R06 §4 | D1 AM |
| F022 | Account lockout (5 failures / 15 min → 30 min lock) | DOM-SEC | R06 §2.2 | D1 AM |
| F023 | CSRF protection on all state-changing requests | DOM-SEC | R06 §4.2 | D1 AM |
| F024 | Binary Admin/Member role check | DOM-SEC | R06 §1 | D1 AM |
| F025 | Bilingual UI toggle (EN/CN) with JSON translation files | DOM-I18 | R09 §2 | D2 AM |
| F026 | Admin user management page (CRUD accounts) | DOM-SEC | R06 §1 | D1 PM |
| F027 | Action list page with filtering + sorting + pagination | DOM-ACT | R09 §4.1 | D1 PM |
| F028 | Action detail page with activity stream | DOM-ACT | R09 §4.2 | D1 PM |
| F029 | New/Edit action form with cascading dropdowns | DOM-ACT | R09 §4.3 | D1 PM |
| F030 | Dashboard visual indicators (red = overdue, amber = due soon) | DOM-NTF | R04 §1 | D1 EVE |
| F031 | First-login tooltip tour (3 steps) | DOM-I18 | R09 §7 | D2 AM |
| F032 | ActionHistory audit trail (all changes logged, including comment edits/deletes) | DOM-ACT | R01 §2 | D1 AM |
| F033 | Category CRUD screen (Admin + TeamLead only — normal users read-only category list) | DOM-TAX | R08 §4 | D1 PM |
| F034 | ActionComment — create/edit/delete rich-text comments on actions | DOM-CMT | R12 §2 | D1 PM |
| F035 | Comment types: Comment / Achievement / Roadblock (enforced ENUM) | DOM-CMT | R12 §2 | D1 PM |
| F036 | Comment edit/delete rights: Admin, TeamLead, or original author only | DOM-CMT | R12 §3 | D1 PM |
| F039 | Meeting Instance create/view (date, type, category-link); actions linkable to instance | DOM-MTG | R13 §1 | D2 AM |
| F041 | Category dashboard — KPI cards: open / overdue / done / on-time / workload, filtered by category | DOM-DSH | R05 §7 | D2 AM |
| F042 | Gantt timeline view — visual bars for actions by deadline; filterable by dept/category/person | DOM-DSH | R05 §10 | D2 AM |
| F066 | View-by-Person: all authenticated users can browse all actions across all teams | DOM-SEC | R06 §1 | D1 PM |

### Should Have (V1.1 — Week 2)

**Committed V1.1 scope:**

| ID | Feature | Domain | Source |
|----|---------|--------|--------|
| F043 | Meeting minutes upload (.xlsx) linked to MeetingInstance | DOM-MTG | R13 §2 |
| F044 | Full RBAC enforcement (Admin / TeamLead / Member / ReadOnly active checks) | DOM-SEC | R06 §3 |
| F045 | Tags (free-form labels, 10 per action max) | DOM-TAX | R08 §3.2 |
| F046 | Team Dashboard (workload chart, status distribution) | DOM-DSH | R05 §4 |
| F047 | Management Dashboard (org KPIs, escalation board) | DOM-DSH | R05 §6 |

**Additional V1.1 items:**

| ID | Feature | Domain | Source |
|----|---------|--------|--------|
| F050 | Email notifications via SMTP (assignment, deadline, overdue) | DOM-NTF | R04 §3 |
| F051 | In-app notification bell with unread count | DOM-NTF | R04 §6 |
| F052 | Reassignment workflow with audit trail | DOM-ASG | R03 §4 |
| F053 | Self-subscribe as Participant | DOM-ASG | R03 §6.2 |
| F054 | Bulk operations (status change, reassign) | DOM-ACT | R02 §8.3 |
| F055 | Windows AD/LDAP authentication | DOM-SEC | R06 §2.1 |
| F056 | AD user sync (nightly batch) | DOM-SEC | R06 §2.3 |
| F057 | Notification preferences per user | DOM-NTF | R04 §6.2 |
| F058 | Notification log (sent/read status) | DOM-NTF | R04 §7 |
| F059 | Fuzzy duplicate detection (Levenshtein / cosine) | DOM-IMP | R07 §8 |
| F060 | Post-import merge/dedup UI | DOM-IMP | R07 §7 |
| F061 | Status transitions in DB config table (not hardcoded dict) | DOM-WFE | R10 §2.2 |
| F062 | Trend charts (completion velocity, created vs completed) | DOM-DSH | R05 §9 |
| F063 | Full audit logging (auth events, data mods, admin ops) | DOM-SEC | R06 §5 |

### Could Have (V1.2 — Week 3–4)

| ID | Feature | Domain | Source |
|----|---------|--------|--------|
| F070 | Auto-escalation triggers (overdue → escalated based on priority) | DOM-ACT | R02 §5.2 |
| F071 | Action dependencies (blocks / related_to) | DOM-ACT | R02 §6 |
| F072 | Report builder (custom columns, filters, grouping) | DOM-RPT | R05 §8.1 |
| F073 | Scheduled reports + email delivery | DOM-RPT | R05 §8.4 |
| F074 | Daily digest notifications | DOM-NTF | R04 §4.1 |
| F075 | Quiet hours + de-duplication | DOM-NTF | R04 §4.2–§4.3 |
| F076 | Team comparison heatmap | DOM-DSH | R05 §5.1 |
| F077 | Advanced search + saved filters | DOM-ACT | R00 §5 |
| F078 | Management summary with drill-down | DOM-DSH | R05 §6.2 |

### Won't Have (V2+)

| ID | Feature | Domain | Source |
|----|---------|--------|--------|
| F090 | Configurable workflow engine | DOM-WFE | R10 |
| F091 | Visual workflow builder (drag-and-drop) | DOM-WFE | R10 §6 |
| F092 | Agent framework (autonomous task routing) | DOM-AGT | R11 |
| F093 | AI-powered duplicate detection | DOM-AGT | R11 §3.2 |
| F094 | Meeting summarizer (LLM-based) | DOM-AGT | R11 §3.2 |
| F097 | Meeting decision CRUD — record, edit, lifecycle transitions (organizer only) | DOM-MDC | R17 §2–§4 |
| F098 | Decision search page — FTS5 full-text + filters (theme, team, status, tags, date) | DOM-MDC | R17 §5, §8.3 |
| F099 | Decision dashboard widgets — status donut chart + recent list on personal/team/theme dashboards | DOM-MDC | R17 §6, §8.4 |
| F100 | Decision ↔ action linking — optional FK from decision to action; shown on action detail page | DOM-MDC | R17 §2.2, §8.5 |
| F101 | Meeting detail "Decisions" tab — inline CRUD within meeting context | DOM-MDC | R17 §8.1 |
| F102 | Meeting list decision count column | DOM-MDC | R17 §8.2 |
| F103 | Standalone decision search page with navbar entry (📌 Decisions) | DOM-MDC | R17 §8.3 |
| F104 | Action detail "Related Decisions" section | DOM-MDC | R17 §8.5 |
| F105 | Decision revision history — prior title/body snapshots with list/detail revision metadata and history retrieval | DOM-MDC | R17 §4.1, §8.6 |
| F095 | External integrations (SAP, WeChat, Teams) | — | R00 §5 |
| F096 | Mobile-native application | — | R00 §5 |

---

## 3. Feature–Entity Cross-Reference

| Entity | MVP Features | V1.1 Features |
|--------|-------------|---------------|
| Action | F001–F009, F027–F029, F032 | F040, F054 |
| User | F020–F022, F024, F026 | F044, F055–F056 |
| Team | F010, F014 | — |
| Team | F011 | F046 |
| Category | F011, F033, F041 | — |
| Category | F012 | — |
| Assignment | F006 | F040, F052–F053 |
| ActionHistory | F032, F034, F036 | F063 |
| ActionComment | F034, F035, F036 | — |
| MeetingInstance | F039 | F043 |
| MeetingDecision | — | F097–F105 (V3.5) |
| PriorityLevel | F003 | — |
| EscalationLevel | F004 | — |
| Tag | — | F045 |
| NotificationRule | — | F057 |
| NotificationLog | — | F058 |
| ImportLog | F016, F017 | — |

---

## 4. Feature Dependencies

```
F020 (Auth) ──────────────► F001 (Action CRUD)
F010 (Dept seed) ─────────► F001 (Action CRUD)
F001 (Action CRUD) ───────► F006 (Assignment)
F001 (Action CRUD) ───────► F013 (Personal Dashboard)
F001 (Action CRUD) ───────► F027 (Action List page)
F006 (Assignment) ────────► F013 (Personal Dashboard)
F027 (Action List) ───────► F015 (Excel Export)
F013 (Personal Dashboard) ► F014 (Dept Dashboard)
F016 (Import) ────────────► F013 (Personal Dashboard)
F001 (Action CRUD) ───────► F016 (Import)
F025 (i18n) ──────────────► F031 (Tooltip tour)
```

---

## 5. Constraints & Assumptions

| # | Type | Statement | Source |
|---|------|-----------|--------|
| C1 | Constraint | SQLite single-file database, WAL mode, <10 concurrent users | D143 |
| C2 | Constraint | Windows server deployment, LAN only | D2 |
| C3 | Constraint | Temperature = 0 for all generation (deterministic) | SpecForge |
| C4 | Assumption | 12 teams seeded; Admin can add/edit teams at runtime via Admin CRUD screen | D99 |
| C5 | Assumption | Visibility is scoped by creator/assignment/meeting/team-lead rules; authenticated users do not automatically get cross-team action access | R19, R20 |
| C6 | Assumption | Chrome/Edge latest — no IE/Safari support | D119 |
| C7 | Constraint | 1.5-day development window (14 working hours) | D141 |
| C8 | Assumption | Admin user pre-seeded at deployment | D22 |
| C9 | Constraint | No external service dependencies in MVP (no SMTP, no AD) | D144 |
| C10 | Assumption | Users have basic browser literacy (no mobile-first) | D115 |
| C11 | Constraint | Excel import: .xlsx only; no column is mandatory; unknown dept/category resolved interactively (no silent drop) | R07 |
| C12 | Constraint | Categories are global (no team parent); managed only by Admin or TeamLead | R01 §4 |
