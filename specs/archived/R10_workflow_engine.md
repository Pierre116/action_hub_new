# ActionHub — Workflow Engine (V2+ Vision)

> **⚠️ ARCHIVED 2026-03-12** — Superseded by `R16_workflow_app_extension.md` (V2 workflow) and `S70_workflow_engine_v3.md` (V3 engine). Kept for historical reference only.

> **Status**: Requirements-level specification — **FUTURE / NOT IN V1 SCOPE**  
> **Depends on**: `R02_action_lifecycle.md`, `R03_assignment_workflow.md`  
> **Decisions**: D121–D130 in `DECISIONS.md`  
> **Consumed by**: V2+ planning only

---

## §1 Overview

The Workflow Engine extends ActionHub from a linear action tracker into a configurable process automation platform. It allows admins to define multi-step workflows that actions pass through, with conditional routing, approval gates, and automatic triggers.

> **Unified Action Management:** Workflow steps can generate actions, which are tracked in the unified action pool. Actions created by workflows are linked to workflow instances (future: `ACT_WFI_ID`). Assignment, notification, and lifecycle rules apply to all actions, regardless of origin.

**This is V2+ scope** — V1 lays the architectural groundwork but does not implement this module. The V1 action lifecycle (R02) should be designed to accommodate future workflow injection.

---

## §2 Architectural Preparation (V1)

### §2.1 V1 Design Hooks (D121)

The following design decisions enable future workflow integration:

| V1 Element | Future-Ready Design | MVP? |
|------------|---------------------|:----:|
| Status transitions | Python dict in code (MVP); config table in DB (V1.1) (D121) | Dict |
| ActionHistory | Generic event log pattern, extensible to workflow events | ✅ |
| Assignment | Role-based assignment compatible with workflow step roles | ✅ |
| Notification triggers | Event-driven architecture, decoupled from action logic | V1.1 |
| API design | RESTful endpoints that can be called by workflow engine | ✅ |

> **Risk mitigation**: The MVP uses a simple Python `VALID_TRANSITIONS` dict (per R02 §3.2). Moving transitions to a DB table is a V1.1 refactor that takes ~2 hours and enables V2 workflow injection. This avoids over-engineering Day 1.

### §2.2 Status Transition Table Pattern (D122)

Instead of hardcoding transitions in application code, V1 stores them in a config table:

```sql
CREATE TABLE status_transition (
    id INT PRIMARY KEY,
    from_status VARCHAR(20),
    to_status VARCHAR(20),
    required_role VARCHAR(20),   -- Lead, Delegate, Admin
    requires_comment BOOLEAN,
    requires_field VARCHAR(50),  -- e.g., "target_reactivation_date"
    is_active BOOLEAN DEFAULT TRUE,
    workflow_id INT NULL         -- NULL = default workflow (V1)
);
```

This allows V2 to add workflow-specific transitions without schema changes.

---

## §3 V2 Workflow Concepts

### §3.1 Workflow Definition (D123)

| Concept | Description |
|---------|-------------|
| Workflow Template | Named sequence of steps with routing rules |
| Step | A stage in the workflow (e.g., "Draft", "Review", "Approve", "Deploy") |
| Transition | Link between steps with conditions |
| Gate | Approval checkpoint (one or more approvers must sign off) |
| Trigger | Automatic action at step entry/exit (send email, set field, etc.) |
| SLA | Time limit per step with escalation |

### §3.2 Example Workflows

**Workflow: Change Request**
```
Draft → Technical Review → Impact Assessment → Approval → Implementation → Verification → Done
         (CTO team)         (cross-dept)        (Manager)    (Assignee)      (QA)
```

**Workflow: Red Ticket (红单)**
```
Reported → Triage → Investigation → Resolution → Verification → Done
            (Lead)    (Delegate)      (Delegate)    (QA + Lead)
   └── Escalate to WAR ──→ WAR Meeting → Resolution Plan → ...
```

**Workflow: Simple Action (default)**
```
Open → In Progress → Done
```

### §3.3 Routing Logic (D124)

| Type | Description |
|------|-------------|
| Sequential | Step A → Step B → Step C |
| Conditional | If priority = Critical → fast-track path |
| Parallel | Step B and Step C execute simultaneously |
| Loop back | Rejection returns to previous step |
| Sub-workflow | Step triggers a child workflow for sub-actions |

---

## §4 V2 Approval Gates (D125)

| Gate Type | Rule |
|-----------|------|
| Single approver | One designated user must approve |
| Any of N | Any one of N designated approvers |
| All of N | All N approvers must approve |
| Majority | >50% of approvers |
| Hierarchical | Approver is the assignee's manager (from AD) |

---

## §5 V2 Automation Triggers (D126)

| Event | Trigger Action |
|-------|---------------|
| Step entered | Send notification, set field, create sub-action |
| Step SLA breached | Escalate, notify manager, auto-route to backup |
| Gate approved | Move to next step, log approval |
| Gate rejected | Move back, set status, require revision comment |
| Workflow completed | Update action status, send summary, archive |

---

## §6 V2 Configuration UI (D127)

| Feature | Description |
|---------|-------------|
| Visual workflow builder | Drag-and-drop step canvas (or YAML config for advanced) |
| Step editor | Configure: name, required role, SLA, triggers, gates |
| Transition editor | Configure: conditions, routing logic |
| Workflow assignment | Map workflow templates to team/category/category |
| Workflow versioning | New version doesn't affect in-flight actions |

---

## §7 Migration Path (D128–D130)

| Phase | Action |
|-------|--------|
| V1 → V2 prep | Store transitions in DB table (D122); keep ActionHistory flexible |
| V2 alpha | Implement workflow engine with 2–3 hardcoded templates |
| V2 beta | Add visual builder + custom transition configuration |
| V2 GA | Full self-service workflow configuration by Admin |
