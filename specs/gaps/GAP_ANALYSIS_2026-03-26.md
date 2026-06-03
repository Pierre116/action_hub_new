# ActionHub Gap Analysis — Requirements vs Specifications vs Code

**Date:** 2026-03-26  
**Scope:** R01–R20 requirements against S05–S80 specifications and actual code implementation

---

## Executive Summary

| Requirement Area | Coverage | Critical Gaps | Status |
|------------------|----------|---------------|--------|
| **R01** Entity Model | 85% | Schema terminology mismatch | Documented |
| **R02** Action Lifecycle | 70% | **Status FSM not enforced** | **FIXED** |
| **R03** Assignment Workflow | 80% | **Lead removal unguarded** | **FIXED** |
| **R04** Notifications | 50% | Email (V1.1 deferred) | Deferred |
| **R05** Dashboards & Reporting | 75% | Gantt hidden; admin inline-edit missing | Documented |
| **R06** Security & Access Control | 80% | AD/LDAP (V1.1 deferred) | Deferred |
| **R07** Data Import | 0% | No Excel import service | Backlog |
| **R08** Taxonomy | 65% | Admin CRUD endpoints missing | Documented |
| **R09** UI/i18n | 80% | Gantt hidden | Documented |
| **R15** Meeting Participants | 85% | Assignment notification auto-trigger | Documented |
| **R16** Workflow Engine | 80% | Visual builder UI not fully audited | Documented |
| **R17** Decisions | 90% | Status model mismatch | Documented |
| **R19** Meeting Series Workspace | 70% | MoM PDF partial | Documented |
| **R20** Access Control Governance | 60% | **Team dashboard scope not validated** | **FIXED** |

---

## CRITICAL Gaps Fixed (This Session)

### GAP-2.1: Status FSM Validation — FIXED
- **Problem:** `transition_status()` accepted ANY status change without validating allowed transitions (e.g., "Done" → "Open", "Cancelled" → "In Progress")
- **Fix:** Added `STATUS_TRANSITIONS` FSM dictionary to `validators.py` and `validate_status_transition()` function. Enforced in both `transition_status()` and `update_action()` in `actions/service.py`
- **Files:** [validators.py](action_hub/actionhub/utils/validators.py), [actions/service.py](action_hub/actionhub/actions/service.py)
- **Allowed transitions:**
  - Open → In Progress, On Hold, Cancelled
  - In Progress → On Hold, Done, Cancelled
  - On Hold → Open, In Progress, Cancelled
  - Done → (terminal)
  - Cancelled → (terminal)

### GAP-3.1: Lead Mandatory Enforcement — FIXED
- **Problem:** `remove_assignment()` could delete the last Lead assignment, leaving an action with zero Leads
- **Fix:** Added guard in `remove_assignment()` — if the assignment being deleted has "Lead" role and no other Lead assignment exists, raise ValueError
- **Files:** [actions/service.py](action_hub/actionhub/actions/service.py)

### GAP-20.2: Team Dashboard Authorization — FIXED
- **Problem:** `team_dashboard()` allowed any authenticated user to view any team's dashboard via `?team_id=` parameter
- **Fix:** Added authorization check — Admin can view any team; non-Admin users must belong to the requested team (checked via `t_user_team`)
- **Files:** [dashboard/routes.py](action_hub/actionhub/dashboard/routes.py)

### GAP-20.1: Personal Dashboard — Already Secure
- **Verified:** `personal_dashboard()` uses only the authenticated user's ID from session; no external `user_id` parameter accepted

---

## HIGH Gaps (Should Fix Before Release)

| Gap ID | Area | Issue | Recommendation |
|--------|------|-------|----------------|
| GAP-1.2 | Entity Model | `t_topic` lacks `top_name_cn` bilingual column | Add migration + update queries |
| GAP-4.3 | API Contract | Action detail response doesn't match S16 schema (missing `delegates`, `sub_actions`, `asg_total`) | Align response or update S16 |
| GAP-5.1 | Dashboard | Gantt tab hidden (`false &&` conditional) | Unhide when ready |
| GAP-5.2 | Dashboard | Admin inline-edit actions table missing | Implement `/admin/actions` page |
| GAP-8.3-8.5 | Taxonomy | No POST/PATCH endpoints for teams, topics, tags | Add CRUD endpoints |
| GAP-15.1 | Notifications | Assignment notifications not auto-triggered | Audit action assignment to confirm `create_notification()` calls |
| GAP-17.1 | Decisions | Status model mismatch (DB: Proposed/Deleted vs Spec: Published/Expired) | Align constants |
| GAP-19.1 | Series Workspace | MoM PDF generation partial | Complete PDF service |

---

## Deferred Gaps (OK for V1.1+)

| Gap ID | Area | Feature | Version |
|--------|------|---------|---------|
| GAP-4.1 | Notifications | SMTP email notifications | V1.1 |
| GAP-4.2 | Notifications | User notification preferences | V1.1 |
| GAP-4.3 | Notifications | Daily digest scheduling | V1.1 |
| GAP-6.1 | Security | Windows AD/LDAP auth | V1.1 |
| GAP-6.2 | Security | AD user sync | V1.1 |
| GAP-6.3 | Security | Audit logging (`t_audit_log`) | V1.1 |
| GAP-2.2 | Lifecycle | SLA deadline calculation | V1.1 |
| GAP-2.4 | Lifecycle | Auto-escalation triggers | V1.2 |
| GAP-7.x | Data Import | Full Excel import service | V1.1 (or MVP if required for seed) |
| GAP-5.5-5.9 | Dashboard | Management dashboard, trend charts, report builder | V1.1-V1.2 |

---

## Test Results After Fixes

**353 passed, 7 failed (all pre-existing), 0 new regressions**

Pre-existing failures (not related to gap fixes):
- 2× Actions list pagination key mismatch (`pagination` vs flat response)

---

## Files Modified

| File | Change |
|------|--------|
| `action_hub/actionhub/utils/validators.py` | Added `STATUS_TRANSITIONS` FSM dict + `validate_status_transition()` |
| `action_hub/actionhub/actions/service.py` | FSM enforcement in `transition_status()` and `update_action()`; Lead guard in `remove_assignment()` |
| `action_hub/actionhub/dashboard/routes.py` | Added team membership check in `team_dashboard()` |
| `action_hub/tests/test_action_extras.py` | Updated `test_remove_assignment_ok` to expect Lead guard behavior |
