# ActionHub — Initial Vision & Objectives

> **SECURITY MODEL / 安全模型**: ActionHub applies scoped visibility for authenticated users. Access is governed by Created-by/Lead rights, explicit assignment, meeting participation, and team-lead policy paths as defined in access-control requirements.
> ActionHub 对已认证用户实施范围化可见性控制。访问依据创建者/负责人权限、显式分配、会议参与关系及团队负责人策略路径。

> **Level**: L0 — Foundation  
> **Merise Phase**: Schéma Directeur  
> **Source**: R00_initial_vision.md, context.md  
> **Decisions**: D1–D15, D141–D165

---

## 1. Project Identity

| Attribute | Value |
|-----------|-------|
| **Name** | ActionHub — Centralized Action Log & Follow-Up Platform |
| **Organization** | ActionHub Organization (Manufacturing / Supply Chain) |
| **Sponsor** | Digitalization Team |
| **Users** | ~50 registered, <10 concurrent |
| **Language** | Bilingual (Chinese 中文 + English) |
| **Timeline** | V1 MVP = 1.5-day sprint |

---

## 2. Problem Statement

The organization's teams track action items across multiple incompatible Excel workbook formats. This fragmentation causes:

| Problem | Impact |
|---------|--------|
| Scattered data across 4 Excel formats | No single source of truth; duplicated/conflicting records |
| No automated follow-up | Overdue items discovered only at biweekly meetings |
| No cross-team visibility | Management lacks consolidated overview |
| No assignment accountability | No formal acceptance or tracking of assignment transfers |
| Inconsistent bilingual data | Chinese/English mixed without standardized taxonomy |
| Manual reporting | Hours spent compiling status reports from spreadsheets |

---

## 3. Solution Overview

A browser-based web application deployed on a local Windows server that:

1. **Centralizes** all action items in a shared SQLite database (zero-config, single-file, WAL mode)
2. **Uses lead-based action accountability** with optional explicit assignee records for visibility/workload
3. **Provides dashboards** — Personal ("What do I do today?") + Team ("How is my team doing?")
4. **Supports bilingual UI** — Chinese + English toggle with instant switch
5. **Imports seed data** — One-time Excel import from 4 existing logbook formats (493 rows)
6. **Exports to Excel** — Ad-hoc filtered exports for meeting preparation
7. **Minimizes friction** — Quick-capture FAB, inline status updates, zero-training onboarding

---

## 4. Strategic Objectives

| # | Objective | Success Criteria | Horizon |
|---|-----------|-----------------|---------|
| O1 | Replace Excel fragmentation | 100% of new actions created in ActionHub within Week 1 | MVP |
| O2 | Instant visibility | Personal dashboard loads in < 3s with overdue items highlighted | MVP |
| O3 | Historical data preserved | All 493 rows from 4 Excel files imported and searchable | MVP |
| O4 | Cross-team transparency | Team dashboard shows KPIs for any team | MVP |
| O5 | Bilingual access | Full UI in both EN and CN with one-click toggle | MVP |
| O6 | Lead accountability | Every action has a defined Lead | MVP |
| O7 | Email-based follow-up | Automated deadline reminders via SMTP | V1.1 |
| O8 | Structured approval flows | Accept/decline workflow for assignments | V1.1 |
| O9 | Configurable workflows | Multi-step approval processes | V2 |
| O10 | Intelligent automation | Agent-based routing and escalation | V3 |

---

## 5. Stakeholder Map

| Stakeholder | Role | Primary Interaction | Phase |
|-------------|------|---------------------|-------|
| Team Heads (12) | Review team dashboards, oversee closures | Weekly dashboard review | MVP |
| Team Leads | Create/assign actions, validate completion | Daily CRUD + assignment | MVP |
| Team Members | Execute actions, update status inline | Daily status updates | MVP |
| Plant Manager | Cross-team oversight, escalation review | Weekly management dashboard | V1.1 |
| IT / Admin | User management, system configuration, import | Setup + maintenance | MVP |
| Digitalization Team | System owner, seed data import, training | Ongoing | MVP |

---

## 6. Scope Boundary

### In-Scope (V1 MVP — 1.5 days)

| Domain | Deliverable |
|--------|------------|
| Action Management | CRUD with 7-status lifecycle, priority levels, escalation field |
| Assignment | Lead-based accountability with explicit assignee compatibility |
| Taxonomy | 12 teams, teams, categories, 8 categories — seeded at deploy |
| Dashboards | Personal ("Today" focus) + Team (KPI cards + overdue table) |
| Reporting | Excel export from any filtered view |
| Data Import | One-time seed from 4 Excel formats with preview + rollback |
| Security | Simple username/password (bcrypt), session-based, binary Admin/Member |
| Bilingual UI | EN/CN toggle, translation JSON files, bilingual taxonomy data |
| Notifications | Passive dashboard indicators (red = overdue, amber = due soon) |

### Out-of-Scope (Acknowledged, Deferred)

| Feature | Target Phase |
|---------|-------------|
| Accept/decline assignment flow | V1.1 |
| Email notifications (SMTP) | V1.1 |
| In-app notification bell | V1.1 |
| Meeting minutes upload | V1.1 |
| Full RBAC (4 roles) | V1.1 |
| Windows AD/LDAP auth | V1.1 |
| Tags (free-form labels) | V1.1 |
| Team + Management dashboards | V1.1 |
| Action dependencies | V1.2 |
| Auto-escalation rules | V1.2 |
| Report builder | V1.2 |
| Scheduled reports | V1.2 |
| Trend charts | V1.2 |
| Configurable workflow engine | V2 |
| Agent framework | V3 |
| External integrations (SAP, WeChat) | V3+ |
| Mobile-native app | Not planned |

---

## 7. Phased Delivery

### V1 MVP Sprint (1.5 Days)

| Phase | Duration | Deliverables | Risk Mitigation |
|-------|----------|-------------|-----------------|
| Day 1 AM | 4h | Scaffold, SQLite schema, auth, dept seed, Action CRUD API | Use proven stack (Flask/Django) |
| Day 1 PM | 4h | Action list + detail pages, forms, assignment, seed import | Import v3+v4 first (largest) |
| Day 1 EVE | 2h | Personal dashboard, user management, quick-capture | Dashboard = 3 queries + template |
| Day 2 AM | 3h | Team dashboard, i18n toggle, inline status, export | i18n = swap JSON; export = openpyxl |
| Day 2 Noon | 1h | Final testing, deployment, go-live | SQLite = copy 1 file to server |

### V1.1 Engagement (Week 2)

Accept/decline workflow, email notifications, meeting minutes, Team + Management dashboards, tags, bulk operations, full RBAC, AD/LDAP integration.

### V1.2 Power Features (Week 3–4)

Scheduled reports, report builder, auto-escalation, dependencies, trend charts.

---

## 8. Non-Functional Requirements

| Category | MVP Target | V1.1 Target |
|----------|-----------|-------------|
| Response time | < 3s page load (LAN) | < 2s page load |
| Concurrent users | 5 | 10 |
| Availability | Business hours (8h × 5d) | Business hours |
| Data retention | 3 years | 5 years |
| Browser support | Chrome, Edge (latest) | + Firefox |
| Backup | Manual SQLite file copy | Daily automated copy |
| Deployment | Single Windows server, on-premise | Same |
| Database | SQLite with WAL mode | Same |
| Transport | HTTPS recommended (self-signed OK for LAN) | Same |

---

## 9. UX Philosophy

### First-5-Minutes Experience

Within 5 minutes of first login, every user must:
1. **See their data** — imported Excel actions already present
2. **Understand what's overdue** — red highlights, overdue count prominent
3. **Update a status** — click badge inline, pick new status, done (2 clicks)
4. **Find anything** — filter by team/status/priority or text search

### Design Principles

| Principle | Implementation |
|-----------|---------------|
| Quick-capture | Persistent "+" FAB → minimal form (title + deadline + dept + priority) |
| "Today" focus | Landing page = 3 sections: Overdue (red) → Due This Week (amber) → Completed (green) |
| Inline updates | Status badge clickable → dropdown → instant save, no page reload |
| Zero-training | First-login 3-step tooltip tour; contextual empty states with CTAs |
| Progress feedback | Confetti/checkmark animation on action completion; pulse on overdue count |

---

## 10. Validation Gates

| Gate | Validates | Blocks |
|------|-----------|--------|
| G1 | Entity model covers all 4 Excel schemas | Data dictionary generation |
| G2 | All statuses and transitions defined | Lifecycle FSM |
| G3 | Lead-based assignment and visibility rules work end-to-end | Action lead workflow |
| G4 | Personal dashboard shows correct KPIs | UI spec generation |
| G5 | Simple auth works; import produces correct records | Go-live |
