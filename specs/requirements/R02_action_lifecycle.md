# ActionHub — Action Lifecycle & Business Logic

> **Status**: Requirements-level specification  
> **Depends on**: `R01_entities.md` (entity model), `R00_initial_vision.md` (scope)  
> **Decisions**: D26–D38 in `DECISIONS.md`  
> **Consumed by**: SpecForge for `05_data_dictionary.md`, `11_MCT.md`, `15_MOT.md`

---

## §1 Overview

This document defines the complete lifecycle of Action items — from creation through completion or cancellation — including priority management, escalation rules, dependency handling, and closure validation.

### MVP (1.5-day) Scope

| Feature | MVP | V1.1 | V1.2 |
|---------|:---:|:----:|:----:|
| Action CRUD + status lifecycle | ✅ | | |
| Priority levels (4) | ✅ | | |
| Inline status update (click badge) | ✅ | | |
| Quick-capture ("+" button) | ✅ | | |
| Auto-escalation triggers | | | ✅ |
| Action dependencies (blocks/related) | | | ✅ |
| Bulk operations | | ✅ | |
| Activity stream (comments) | | ✅ (full) | |
| `last_comment` field on Action | ✅ (MVP shortcut) | | |

---

## §2 Action Creation

### §2.1 Creation Channels

| Channel | Description | Source Field Value |
|---------|-------------|--------------------|
| Manual | User creates via "New Action" form | `Manual` |
| Import | Seed data from Excel logbooks | `Import` |
| Meeting | Created while attaching meeting minutes | `MeetingSummary` |
| Workflow | Created as part of a workflow step or process | `Workflow` (future) |
| Category | Created and linked to one or two categories, not tied to a meeting | `Category` |

> **Unified Action Management:** Actions may originate from meetings, workflows, or direct category-driven work. All actions are managed in a single pool, with assignment, notification, and lifecycle rules applied consistently. See `ACT_MTG_INST_ID`, `ACT_TOP_ID`, and `ACT_SECONDARY_TOP_ID` for category linkage.

### §2.2 Required Fields at Creation

| Field | Mandatory | Default |
|-------|-----------|---------|
| Title | Yes | — |
| Description | No | — |
| Team | Yes | Creator's team |
| Team | No | Creator's team |
| Primary Category | Yes | — |
| Secondary Category | No | — |
| Priority | Yes | Medium (D26) |
| Deadline | Yes | — |
| Lead assignment | Yes | Creator (D27) |

### §2.3 Auto-Generated Fields

| Field | Value |
|-------|-------|
| reference_code | `ACT-{YYYY}-{SEQ:05d}` (e.g., ACT-2026-00142) |
| status | Open |
| escalation_level | Normal |
| created_date | Now |
| created_by | Current user |

## §3 Status Management

### §3.1 Status Definitions

| Status | Meaning | Who Can Set |
|--------|---------|-------------|
| **Open** | Action created, not yet started | System (auto), Lead |
| **In Progress** | Work actively underway | Assignee (Delegate), Lead |
| **On Hold** | Temporarily paused | Lead only |
| **Done** | Completed and validated | Lead (approves) |
| **Cancelled** | Abandoned, no longer needed | Lead, Admin |

### §3.2 Transition Rules

```python
VALID_TRANSITIONS = {
    "Open":        ["In Progress", "On Hold", "Cancelled"],
    "In Progress": ["On Hold", "Done"],
    "On Hold":     ["Open", "In Progress"],
    "Done":        [],                          # terminal
    "Cancelled":   [],                          # terminal
}
```

### §3.3 Transition Side Effects

| Transition | Side Effect |
|------------|-------------|
| Any → On Hold | Require `hold_reason` text |
| Any → Cancelled | Require `cancel_reason` text |
| Any → Done | Set `actual_completion_date` = now |
| Any transition | Create `ActionHistory` entry |
| Any transition | Notify affected assignees |

## §4 Priority Management

### §4.1 Priority Levels

| Level | Label | Label (CN) | Color | SLA (D30) |
|-------|-------|------------|-------|-----------|
| 1 | Critical | 紧急 | Red | 3 business days |
| 2 | High | 高 | Orange | 7 business days |
| 3 | Medium | 中 | Yellow | 14 business days |
| 4 | Low | 低 | Green | 30 business days |

### §4.2 Priority Change Rules

- Any user with Lead role on the action can change priority
- Admin can change any action's priority
- Priority changes are logged in ActionHistory
- Priority upgrade triggers notification to all assignees (D31)

---

## §5 Escalation Rules

> **MVP**: Escalation levels exist as a field on Action (Normal/Escalated/WAR) and can be set manually. Auto-escalation triggers (§5.2) are **V1.2 scope**. In MVP, a Lead manually sets escalation_level when needed.

### §5.1 Escalation Levels

| Level | Label | Trigger | Visible To |
|-------|-------|---------|------------|
| Normal | Normal | Default | Standard views |
| Escalated | Escalated 升级 | Manual by Lead or auto-trigger (D32) | Team dashboard + management |
| WAR | WAR 战报 | Manual by management | Management summary, red highlight |

### §5.2 Auto-Escalation Triggers (D32)

```python
def check_auto_escalation(action):
    days_overdue = (today - action.deadline).days
    
    if action.priority == "Critical" and days_overdue >= 1:
        escalate(action, "Escalated")
    elif action.priority == "High" and days_overdue >= 3:
        escalate(action, "Escalated")
    elif action.priority in ("Medium", "Low") and days_overdue >= 7:
        escalate(action, "Escalated")
```

### §5.3 De-escalation

- Escalated → Normal: when action is completed (Done) or rescheduled with new deadline
- WAR → Normal: manual by management only
- All escalation changes logged in ActionHistory

---

## §6 Action Dependencies

> **⚠️ V1.2 scope** — Not implemented in MVP or V1.1. Designed here for forward compatibility. MVP actions are independent; the schema can accommodate FK columns but the UI and enforcement are deferred.

### §6.1 Dependency Types (D33)

| Type | Meaning | Constraint |
|------|---------|------------|
| blocks | Action A blocks Action B | B cannot move to "Done" while A is not Done |
| related_to | Informational link | No constraint, display only |

### §6.2 Dependency Rules

- Circular dependency detection: system rejects if adding dependency creates a cycle (D34)
- When a blocking action is completed, system notifies all blocked actions' assignees
- Dashboard shows blocked actions with a distinct icon/indicator
- Dependency graph is viewable from action detail page

---

## §7 Comments & Activity Stream

> **MVP shortcut**: The full `ActionComment` entity is V1.1. In MVP, the `Action.last_comment` TEXT field stores the latest comment. The action detail page shows the `last_comment` field as editable text. Full comment history is built in V1.1 when the `ActionComment` entity is activated.

### §7.1 Comment Types

| Type | Description |
|------|-------------|
| User comment | Free-text comment by any user |
| System comment | Auto-generated (status change, reassignment, escalation) |
| Meeting note | Comment linked to a meeting summary |

### §7.2 Activity Stream

Each Action has a chronological activity stream showing:
- All comments (user + system)
- All status transitions
- All assignment changes
- All priority/escalation changes
- File attachments

Displayed newest-first with timestamp and author metadata (D35).

---

## §8 Closure Validation

### §8.1 Closure Prerequisites (D36)

**MVP (simplified):**
- Lead or Delegate can set status to Done (no mandatory review gate)
- `actual_completion_date` auto-set to now
- Optional completion comment stored in `last_comment`

**V1.1 (full):**

| Check | Rule |
|-------|------|
| Lead approval | Lead assignment must validate (explicit approve action) |
| No blocking dependencies | All blocking predecessors must be Done |
| Completion comment | Optional but prompted — "What was the outcome?" |

### §8.2 Reopening (D37)

- Done actions **cannot** be reopened (terminal state per D25)
- If follow-up is needed, a new Action should be created with a `related_to` dependency to the original
- This preserves audit integrity

### §8.3 Bulk Operations (D38)

> **V1.1 scope** — Not in MVP. MVP handles one action at a time.

| Operation | Who | Scope |
|-----------|-----|-------|
| Bulk status change | Lead, Admin | Actions within same team |
| Bulk reassignment | Lead, Admin | Actions within same team |
| Bulk priority change | Admin | Any actions |
| Bulk cancel | Admin | Any actions (requires reason) |

All bulk operations create individual ActionHistory entries per action.
