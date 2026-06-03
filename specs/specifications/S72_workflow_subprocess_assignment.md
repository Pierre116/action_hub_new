# S72 — Workflow Subprocess Steps & Declarative Assignment Rules

**Date:** 2026-03-14
**Version:** 1.1
**Status:** Planned
**Depends On:** S70, S71, S05, S16
**Enables:** B-1 (Subprocess & Dynamic Assignment)

---

## 1. Overview

This specification extends workflow runtime behavior in two areas:

1. Subprocess steps: a parent workflow can launch a child workflow and pause until child completion.
2. Declarative assignment rules: assignees are resolved from JSON rules at runtime.

Assignment-transfer behavior previously drafted in this file is retired from active scope.

---

## 2. Decisions

| ID | Decision | Source |
|----|----------|--------|
| D199 | Add Subprocess step type and pause/resume semantics | B-1 |
| D200 | Limit subprocess depth to 1 (no nested child-of-child) | B-1 |
| D201 | Support declarative assignment rule evaluation order | B-1 |
| D202 | Retired from active scope | B-1 |
| D203 | Retired from active scope | B-1 |
| D204 | Round-robin assignment counter by template + step key | B-1 |
| D205 | Child workflow input/output mapping between parent and child | B-1 |

---

## 3. Subprocess Model

### 3.1 Graph Definition

```json
{
  "type": "Subprocess",
  "subprocess": {
    "template_id": 5,
    "input_mapping": {
      "material_code": "field:material_code"
    },
    "output_mapping": {
      "validation_result": "field:validation_status"
    },
    "on_child_cancel": "pause_and_notify"
  }
}
```

### 3.2 Runtime Rules

- Parent step status becomes `WaitingForChild` after child launch.
- Child instance stores a parent link in `wfi_parent_step_id`.
- Child terminal state updates parent step and applies output mapping.
- Depth check blocks nested subprocess creation.

---

## 4. Assignment Rule Model

### 4.1 Rule Types

- `static_user`
- `role_in_team`
- `prior_step_actor`
- `workflow_creator`
- `round_robin`

### 4.2 Resolution Order

1. Runtime explicit override
2. Rule list first-match evaluation
3. Legacy `role` fallback
4. Workflow creator fallback

### 4.3 Round-Robin Storage

`t_workflow_assignment_counter` tracks the last assigned user for `(template_id, step_key)`.

---

## 5. Data Model Changes

### 5.1 `t_workflow_instance`

- `wfi_parent_step_id` (nullable FK)
- `wfi_started_by` (FK)

### 5.2 `t_workflow_step_instance`

- `wsi_child_instance_id` (nullable FK)
- `wsi_child_outcome` (nullable text)

### 5.3 Status Enum Additions

- `WaitingForChild`

---

## 6. Schema Changes (Summary)

- Add parent/child linkage columns for subprocess tracking.
- Add workflow starter identity column.
- Create `t_workflow_assignment_counter` for round-robin.

Detailed DDL is maintained in S20 and implementation migrations.

---

## 7. API Surface

### New Endpoint

- `GET /api/workflow/instances/<id>/subprocess`: returns child workflow status and progress for parent context.

### Modified Endpoints

- Step advance logic resolves assignees through declarative rules when present.
- Workflow timeline includes subprocess progress metadata.

---

## 8. Implementation Notes

- `assignment.py`: assignment rule evaluator
- `subprocess_handler.py`: child creation/callback logic
- `engine.py`: subprocess and assignment integration points
- `graph.py`: validation rules for subprocess nodes and assignment blocks

---

## 9. Backward Compatibility

- Existing graphs without subprocess nodes remain valid.
- Existing graphs without assignment blocks remain valid (legacy fallback path).
- Newly added columns are nullable where required for safe migration.

---

## 10. Test Plan

- `test_workflow_assignment.py`
- `test_workflow_subprocess.py`

No active tests are defined for retired assignment-transfer behavior.
