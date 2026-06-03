# S70 — Workflow Engine V3: Advanced Step Types, Decision Tables & Runtime Assignees

> **Last updated**: 2026-03-12
> **Source**: R16, S05 §11, S11 OP25-OP34, S20 §7, D167-D180
> **Supersedes**: V2.0-V2.4 workflow engine (WF-1 through WF-9)
> **Decisions**: D181-D192 (new)

> **Consolidation Note (2026-03-24)**: This document is the canonical workflow specification. Content formerly split across S71-S73 is now maintained under S70 for implementation guidance.

---


## Manual Process Workflow Creation Only (2026-03-18)

- Workflow instances are never auto-started when an action is created or edited.
- There is no auto-start binding or automatic workflow instance creation based on action fields.
- In the target operating model, process workflows are launched separately from actions from the existing workflow area of the product, without introducing a separate dedicated process-start feature.
- Process workflows are first-class work units for business processes such as ECO, ID creation, approvals, and other request-driven procedures.
- Actions and workflow steps may appear in the same user dashboard for workload visibility, but they remain distinct work objects and must not be merged into a single domain record.
- The preferred dashboard UX is a shared dashboard with separate panels: one for actions and one for workflow steps / process tasks.
- Workflow instances themselves do not carry team linkage at creation time. Category selection at request time classifies the process request, not an existing action.
- Existing-action workflow start is a compatibility mechanism only. It is not the primary operating model and must not be treated as the default workflow entry pattern.
- All previous references to auto-start, auto-binding, action-followed-by-workflow as the default model, or automatic workflow instance creation are obsolete and must not be implemented.

---

## 1. Overview

V3 upgrades the workflow engine from a linear/fork-join executor to a full process engine with:

- **3-phase step lifecycle** (Pending → Accepted → Completed/Rejected)
- **8 step types** (Task, Approval, Gateway, Service, Notification, Timer, Join, End)
- **Decision tables** for conditional routing (XOR/OR gateways)
- **Python service callables** executed by the engine (whitelisted registry)
- **Multiple distinct End outcomes** mapping to different action statuses (**WF-15: Complete, tested, and API-exposed as of 2026-03-14**)
- **Timer-driven auto-escalation** (not just notification)
- **Rejection bounce-back** with mandatory reason and escalation path
- **Runtime assignee override** by the completing user

V3 is intended to support separate process workflows that are launched independently of the action lifecycle. Actions remain action-tracking records; workflows remain process-execution records. Shared dashboard visibility is a presentation concern, not a data-model merge.

All changes are backward-compatible with existing V2.x graph structures. Existing templates continue to work without modification.

---

## 2. Decisions

| ID | Decision | Source | Affects |
|----|----------|--------|---------|
| **D181** | Steps use 3-phase lifecycle: Pending → Accepted → Completed/Rejected. Explicit accept required before work begins. | V3 Q1 | S05 §11.3, engine.py |
| **D182** | Rejection bounces step back to previous step assignee with mandatory reason in `wsi_comment`. Previous assignee can escalate to workflow creator. | V3 Q2 | engine.py, approval_service.py |
| **D183** | After step completion, user sees full read-only timeline of all steps (past, current, future) and can override the next step's assignee from an eligible-user dropdown. | V3 Q3 | routes.py, templates |
| **D184** | Runtime assignee resolution via dropdown of eligible team members; completing user may override template default. | V3 Q4 | engine.py, routes.py |
| **D185** | Gateway decision tables evaluate **prior step field values** from `t_workflow_step_field_value`; field values take precedence. | V3 Q5 | gateway.py |
| **D186** | Service steps execute registered Python callables from a whitelist registry. Handlers receive mapped inputs from prior step fields and produce mapped outputs. On error: pause step and notify workflow creator. | V3 Q6 | service_executor.py |
| **D187** | Multiple End steps allowed per graph. Each End has a distinct `outcome` label and maps to a specific `action_status` (Done, Cancelled, Postponed, etc.). | V3 Q7 | graph.py validation, engine.py |
| **D188** | Timer steps auto-escalate to team lead and reassign the timed-out step. Escalation logged as `change_type='SLAEscalation'`. | V3 Q8 | timer.py, sla.py |
| **D189** | Step types expanded from 4 to 8: Task, Approval, Gateway, Service, Notification, Timer, Join, End. | V3 Q9 | graph.py, engine.py |
| **D190** | Transition types: `normal` (default), `rejection`, `timeout`, `condition`. Engine uses type to select correct path. | V3 Q10 | graph.py, engine.py |
| **D192** | Graph validation relaxed: ≥1 End step (not exactly 1). Reachability, decision table input validation, and service handler registry checks added. | V3 Q12 | graph.py |

---

## 3. Step Lifecycle (3-Phase)

### 3.1 Status Transitions

```
                   ┌──────────────┐
                   │   Pending    │  (step created, assignee notified)
                   └──────┬───────┘
                          │ user clicks "Accept"
                   ┌──────▼───────┐
                   │   Accepted   │  (assignee acknowledged, work begins)
                   └──────┬───────┘
                          │
            ┌─────────────┼─────────────┐
            │                           │
     ┌──────▼───────┐           ┌──────▼───────┐
     │  Completed   │           │   Rejected   │
     └──────────────┘           └──────────────┘
                                  (reason mandatory)
                                  (bounces to previous step)
```

### 3.2 Valid Transitions

| From | To | Trigger | Auth |
|------|----|---------|------|
| Pending | Accepted | `POST /api/workflow/steps/<id>/accept` | Assignee only |
| Accepted | Completed | `POST /api/workflow/steps/<id>/advance` | Assignee only |
| Accepted | Rejected | `POST /api/workflow/steps/<id>/reject` | Assignee only |
| Pending | Skipped | Workflow cancelled or timer escalation | System / Admin |
| Accepted | Skipped | Workflow cancelled | System / Admin |

Non-human step types (Gateway, Service, Notification, Timer, Join) skip the Accepted phase — they transition directly from Pending to Completed by the engine.

---

## 4. Step Types (D189)

### 4.1 Type Reference

| Type | Human? | Auto-advance? | Has Fields? | Description |
|------|--------|--------------|-------------|-------------|
| **Task** | Yes | No | Yes | Standard work step. Assignee fills form, clicks Accept → Complete. |
| **Approval** | Yes | No | Optional | Gate requiring explicit Approve/Reject decision. |
| **Gateway** | No | Yes | No | XOR or OR routing based on decision table evaluating prior field values (D185). |
| **Service** | No | Yes | No | Executes a registered Python callable. Maps inputs/outputs to step fields (D186). |
| **Notification** | No | Yes | No | Creates an in-app notification for a target user/role, then auto-advances. |
| **Timer** | No | Delayed | No | Waits N hours, then auto-escalates to team lead and reassigns (D188). |
| **Join** | No | Conditional | No | AND synchronization — waits for all incoming branches to complete (D172). |
| **End** | No | Terminal | No | Terminates workflow. Sets action to specified `action_status` (D187). |

### 4.2 Task Step

```json
{
  "type": "Task",
  "name_en": "Fill Badge Request",
  "name_cn": "填写工牌申请",
  "order": 2,
  "role": "Facility",
  "sla_hours": 24,
  "fields": [
    {"key": "badge_code", "label_en": "Badge Code", "label_cn": "工牌编号",
     "type": "text", "required": true}
  ]
}
```

Lifecycle: Pending → **(Accept)** → Accepted → **(Complete with fields)** → Completed

### 4.3 Approval Step

```json
{
  "type": "Approval",
  "name_en": "QA Verification",
  "name_cn": "QA验证",
  "order": 5,
  "role": "QA_Lead",
  "sla_hours": 48,
  "fields": [
    {"key": "verification_notes", "label_en": "Notes", "label_cn": "备注",
     "type": "text", "required": false}
  ]
}
```

Lifecycle: Pending → **(Accept)** → Accepted → **(Approve / Reject)** → Completed or Rejected

On Reject: mandatory comment in `wsi_comment`, step bounces back to previous step's assignee per rejection transition.

### 4.4 Gateway Step (D185)

```json
{
  "type": "Gateway",
  "name_en": "Route by Role",
  "name_cn": "按角色路由",
  "gateway_mode": "exclusive",
  "decision_table": {
    "inputs": ["role", "workshop_zone"],
    "rules": [
      {
        "conditions": {"role": "Operator", "workshop_zone": "Zone A"},
        "output": "hse_validation"
      },
      {
        "conditions": {"role": "Engineer"},
        "output": "finance"
      },
      {
        "conditions": {"_default": true},
        "output": "facility"
      }
    ]
  }
}
```

**Gateway modes:**

| Mode | Behavior | BPMN Equivalent |
|------|----------|-----------------|
| `exclusive` | First matching rule wins; exactly one output path activated. | Exclusive Gateway (XOR) |
| `inclusive` | All matching rules fire; one or more output paths activated. | Inclusive Gateway (OR) |

**Rule evaluation:**

1. Load all `t_workflow_step_field_value` rows for the current workflow instance.
2. Build a flat dict `{field_key: value}` across all completed steps.
3. For each rule in order, check if all `conditions` match the dict.
4. `_default: true` matches if no prior rule matched (exclusive) or always (inclusive).
5. Activate the target step(s) indicated by `output`.

If no rule matches and no `_default` exists → workflow pauses, notification sent to creator.

### 4.5 Service Step (D186)

```json
{
  "type": "Service",
  "name_en": "Create SAP User",
  "name_cn": "创建SAP用户",
  "service": {
    "handler": "sap_user_creation",
    "input_mapping": {
      "employee_name": "field:employee_name",
      "role": "field:role",
      "start_date": "field:start_date"
    },
    "output_mapping": {
      "sap_user_code": "field:sap_user_code"
    },
    "on_error": "pause_and_notify"
  }
}
```

**Handler registry** (`action_hub/actionhub/workflow/service_registry.py`):

```python
SERVICE_REGISTRY: dict[str, Callable] = {}

def register_service(name: str, handler: Callable):
    """Register a service handler by name. Called at app startup."""
    SERVICE_REGISTRY[name] = handler

def get_service(name: str) -> Callable:
    """Lookup handler. Raises KeyError if not registered."""
    return SERVICE_REGISTRY[name]
```

**Execution:**

1. Engine encounters Service step → reads `service.handler` from graph.
2. Looks up handler in `SERVICE_REGISTRY` (whitelist — no arbitrary code).
3. Resolves `input_mapping`: for each key, reads value from `t_workflow_step_field_value` (prefix `field:`) or from action metadata (prefix `action:`).
4. Calls `handler(inputs)` → returns `dict` of outputs.
5. Writes outputs to `t_workflow_step_field_value` via `output_mapping`.
6. Marks step Completed and advances.
7. On exception: marks step status `Paused`, creates notification for workflow creator with error details.

**Error policy** (`on_error`):

| Value | Behavior |
|-------|----------|
| `pause_and_notify` | Pause step, notify workflow creator. Manual retry via API. |
| `skip_and_continue` | Log error, mark step Skipped, advance to next step. |
| `fail_workflow` | Cancel entire workflow with error reason. |

### 4.6 Notification Step

```json
{
  "type": "Notification",
  "name_en": "Notify HR",
  "name_cn": "通知HR",
  "notification": {
    "target_role": "HR_Manager",
    "title_en": "New employee onboarding started",
    "title_cn": "新员工入职流程已启动",
    "body_template": "Employee {employee_name} joining on {start_date}"
  }
}
```

Engine creates the notification via existing `create_notification()`, then auto-advances. No human interaction.

**Implementation Note (WF-13, 2026-03-14):**
- When a Notification step is encountered, the engine must:
  1. Render the notification title/body using available workflow field values (variable substitution, e.g., `{employee_name}`).
  2. Resolve the target user(s) for the specified role in the workflow context.
  3. Call `create_notification()` for each target user.
  4. Immediately mark the step as Completed and advance the workflow.
- No API endpoint is exposed for Notification steps; all logic is internal to the engine.
- Tests must verify notification creation, template rendering, and auto-advance behavior.

### 4.7 Timer Step (D188)

```json
{
  "type": "Timer",
  "name_en": "Wait for Approval Window",
  "name_cn": "等待审批窗口",
  "timer_hours": 48,
  "on_expire": "escalate",
  "escalate_to": "team_lead"
}
```

**Timer behavior:**

1. Engine creates Timer step instance with `wsi_sla_deadline = entered_at + timer_hours`.
2. SLA check job (APScheduler, every 15 min) detects expired timers.
3. On expiry:

| `on_expire` | Action |
|-------------|--------|
| `escalate` | Reassign the **preceding human step** (if still Active/Accepted) to team lead. Create escalation notification. Log `SLAEscalation`. |
| `advance` | Mark timer Completed, activate next step. (Auto-advance after wait period.) |

Timer steps do not require human interaction. They are always auto-resolved.

### 4.8 Join Step

Unchanged from V2. AND-join waits for all incoming branches. Uses `BEGIN IMMEDIATE` for race safety (D179).

### 4.9 End Step (D187)

```json
{
  "end_completed": {
    "type": "End",
    "name_en": "Completed",
    "name_cn": "已完成",
    "outcome": "completed",
    "action_status": "Done"
  },
  "end_rejected": {
    "type": "End",
    "name_en": "Rejected",
    "name_cn": "已拒绝",
    "outcome": "rejected",
    "action_status": "Cancelled"
  },
  "end_timeout": {
    "type": "End",
    "name_en": "Timed Out",
    "name_cn": "已超时",
    "outcome": "timeout",
    "action_status": "Postponed"
  }
}
```

Multiple End steps allowed. Each must have:
- `outcome`: machine-readable label stored on `wfi_outcome` (new column)
- `action_status`: one of the 7 canonical statuses applied to the action

Graph validation: ≥1 End step required (relaxed from exactly 1).

---

## 5. Transition Types (D190)

### 5.1 Transition Schema

```json
{
  "from": "step_a",
  "to": "step_b",
  "type": "normal",
  "label_en": "Proceed",
  "label_cn": "继续",
  "condition": null
}
```

| Type | When Used | Selected By |
|------|-----------|-------------|
| `normal` | Default forward flow | `advance_step()` |
| `rejection` | When step is rejected (D182) | `reject_step()` |
| `timeout` | When timer expires | `handle_timer_expiry()` |
| `condition` | For Gateway evaluation | `evaluate_gateway()` |

### 5.2 Rejection Transition

```json
{"from": "approval_gate", "to": "investigation", "type": "rejection",
 "label_en": "Rejected — return to investigation", "label_cn": "已拒绝 — 返回调查"}
```

If no explicit `rejection` transition exists for a step, the engine defaults to bouncing back to the immediately preceding step (the step whose completion activated the current one).

### 5.3 Condition Transition

Used between a Gateway and its target steps. The Gateway's decision table determines which condition transitions fire.

```json
{"from": "route_by_role", "to": "hse_validation", "type": "condition",
 "condition": {"rule_index": 0}}
```

### 5.4 Timeout Transition

Used from a Timer step to specify what happens on expiry.

```json
{"from": "approval_timer", "to": "escalation_end", "type": "timeout"}
```

---

## 6. Runtime Assignee Override (D183, D184)

### 6.1 Default Assignment

When a step instance is created, the assignee is resolved in order:

1. **Override from completing user** — if the previous step's user selected someone via the assignee dropdown.
2. **Template role binding** — `step.role` maps to a team function (e.g., `"HSE"` → HSE officer for the action's team).
3. **Workflow creator** — fallback if no role mapping exists.

### 6.2 Advance Response with Timeline

`POST /api/workflow/steps/<id>/advance` returns:

```json
{
  "completed": "facility",
  "activated": ["join"],
  "workflow_completed": false,
  "timeline": [
    {"step_key": "request", "name_en": "Request", "status": "Completed",
     "assignee": "Zhang Wei", "completed_at": "2026-03-10T09:00:00"},
    {"step_key": "facility", "name_en": "Facility", "status": "Completed",
     "assignee": "Li Ming", "completed_at": "2026-03-11T14:30:00"},
    {"step_key": "hse_validation", "name_en": "HSE Validation", "status": "Accepted",
     "assignee": "Wang Fang", "accepted_at": "2026-03-11T10:00:00"},
    {"step_key": "join", "name_en": "Join", "status": "Pending"},
    {"step_key": "finance", "name_en": "Finance", "status": "Future",
     "default_assignee": "Chen Li", "eligible_users": [
       {"id": 5, "name": "Chen Li", "role": "Finance"},
       {"id": 12, "name": "Zhao Ying", "role": "Finance"}
     ]},
    {"step_key": "ot_admin", "name_en": "OT Admin", "status": "Future"},
    {"step_key": "active", "name_en": "Active", "status": "Future", "type": "End"}
  ],
  "next_step": {
    "step_key": "finance",
    "default_assignee_id": 5,
    "eligible_users": [{"id": 5, "name": "Chen Li"}, {"id": 12, "name": "Zhao Ying"}]
  }
}
```

### 6.3 Assignee Override Endpoint

```
POST /api/workflow/steps/<id>/advance
Body: {
  "comment": "Badge issued",
  "next_assignee_id": 12    ← optional override; null = use default
}
```

If `next_assignee_id` is provided and is in the eligible-users list, use it instead of the template default. Log override in `t_action_history` with `change_type='AssigneeOverride'`.

---

## 7. Rejection Flow (D182)

### 7.1 Reject Endpoint

```
POST /api/workflow/steps/<id>/reject
Body: {
  "reason": "Badge photo does not meet quality standards"   ← mandatory
}
```

### 7.2 Rejection Algorithm

1. Verify step status is `Accepted` (cannot reject a Pending step).
2. Require non-empty `reason` in body.
3. Update step: `wsi_status = 'Rejected'`, `wsi_comment = reason`, `wsi_completed_at = now`.
4. Find rejection target:
   a. Check transitions with `type: "rejection"` from this step → use that target.
   b. If none: find the step instance that was completed immediately before this one was created → use that step_key.
5. Create new step instance for the target step_key with `status = 'Pending'`, assigned to the original assignee of that step.
6. Notify the target assignee: "Step '{step_name}' was rejected by {rejector}. Reason: {reason}".
7. Log to `t_action_history`: `change_type='StepRejected'`, `old_value=step_key`, `new_value=reason`.

### 7.3 Escalation by Previous Assignee

When the previous assignee receives a bounced-back step, they can:

1. **Fix and re-advance** — normal flow resumes from that step.
2. **Escalate to workflow creator** — via:

```
POST /api/workflow/steps/<id>/escalate
Body: {
  "reason": "Cannot resolve badge quality issue — need manager input"
}
```

Escalation reassigns the step to the workflow instance creator (`wfi_started_by` — new column or derived from first step's `wsi_assignee_id`) and creates an escalation notification.

---

## 8. Data Model Changes

### 8.1 New/Modified Columns on `t_workflow_step_instance` (S05 §11.3)

| Column | Type | Purpose | Source |
|--------|------|---------|--------|
| `wsi_accepted_at` | DATETIME | When assignee accepted the step (Pending → Accepted) | D181 |
| `wsi_status` | ENUM | Add `'Accepted'` to allowed values: Pending, **Accepted**, Active→removed, Completed, Rejected, Skipped, **Paused** | D181, D186 |

> **Migration note**: Existing `'Active'` status maps to new `'Accepted'` semantically. Migration renames `Active → Accepted` in existing rows where `wsi_accepted_at` will be backfilled from `wsi_entered_at`.

### 8.2 New Column on `t_workflow_instance`

| Column | Type | Purpose | Source |
|--------|------|---------|--------|
| `wfi_outcome` | VARCHAR(50) | End outcome label (e.g., `'completed'`, `'rejected'`, `'timeout'`) | D187 |

### 8.3 New Table: `t_workflow_service_log`

| Column | Type | Purpose |
|--------|------|---------|
| `wsl_id` | INTEGER PK | Auto-increment |
| `wsl_step_inst_id` | INTEGER FK → `t_workflow_step_instance` | Which step triggered the service |
| `wsl_handler` | VARCHAR(100) | Registry handler name |
| `wsl_inputs` | TEXT (JSON) | Resolved input values |
| `wsl_outputs` | TEXT (JSON) | Handler return values (null on error) |
| `wsl_status` | ENUM(`'Success'`, `'Error'`) | Execution result |
| `wsl_error_message` | TEXT | Error details (null on success) |
| `wsl_executed_at` | DATETIME | Execution timestamp |

### 8.4 Step Status Enum (Updated)

| Value | Label EN | Label CN | Usage |
|-------|----------|----------|-------|
| `Pending` | Pending | 待处理 | Step created, waiting for assignee to accept |
| `Accepted` | Accepted | 已接受 | Assignee acknowledged, work in progress |
| `Completed` | Completed | 已完成 | Step finished successfully |
| `Rejected` | Rejected | 已拒绝 | Step rejected with reason (human steps only) |
| `Skipped` | Skipped | 已跳过 | Workflow cancelled or step bypassed |
| `Paused` | Paused | 已暂停 | Service step error; awaiting manual retry |

### 8.5 Workflow Instance Status Enum (Updated)

| Value | Label EN | Label CN | Usage |
|-------|----------|----------|-------|
| `Active` | Active | 活跃 | Workflow in progress |
| `Completed` | Completed | 已完成 | Reached an End step |
| `Cancelled` | Cancelled | 已取消 | Manually cancelled |
| `Suspended` | Suspended | 已暂停 | Service error or manual pause |

---

## 9. Graph Validation Updates (D192)

### 9.1 Existing Rules (Preserved)

- Must have `steps` dict with ≥2 entries
- Must have `transitions` list with ≥1 entry
- Every transition `from`/`to` must reference existing step keys
- At least one step with `order=1` (start step)
- Join steps must have ≥2 incoming transitions
- No orphan steps (all reachable from start)

### 9.2 Updated Rules

| Rule | Old | New | Decision |
|------|-----|-----|----------|
| End step count | Exactly 1 | ≥1 | D192 |
| Valid step types | Task, Approval, Join, End | Task, Approval, Gateway, Service, Notification, Timer, Join, End | D189 |
| Transition types | Not validated | Must be `normal`, `rejection`, `timeout`, or `condition` | D190 |

### 9.3 New Rules

| Rule | Validation |
|------|-----------|
| Workflow instance category fields | Not allowed. `t_workflow_instance` must not persist category attachment columns. |
| Gateway must have `decision_table` | If `type=Gateway`, `decision_table` must have `inputs` (list of strings) and `rules` (list with ≥1 entry) |
| Gateway rules must reference reachable steps | Each rule `output` must be a valid step_key with a `condition` transition from the gateway |
| Decision table must have `_default` | At least one rule must have `{"_default": true}` for each exclusive gateway |
| Service handler must exist | If `type=Service`, `service.handler` must be a key in `SERVICE_REGISTRY` at graph validation time |
| Timer must have `timer_hours` | If `type=Timer`, `timer_hours` must be a positive number |
| Timer must have `on_expire` | Value must be `escalate` or `advance` |
| End must have `outcome` and `action_status` | Both required; `action_status` must be one of the 7 canonical statuses |
| Rejection transitions | Every human step (Task, Approval) should have either an explicit `rejection` transition or a predecessors (engine falls back to bounce-back) |

---

## 10. API Changes

### 10.1 New Endpoints

| Method | Path | Operation | Auth | Purpose |
|--------|------|-----------|------|---------|
| POST | `/api/workflow/steps/<id>/accept` | OP35 | Assignee | Accept step (Pending → Accepted) |
| POST | `/api/workflow/steps/<id>/reject` | OP36 | Assignee | Reject step (Accepted → Rejected) with reason |
| POST | `/api/workflow/steps/<id>/escalate` | OP37 | Assignee | Escalate to workflow creator |
| POST | `/api/workflow/steps/<id>/retry` | OP38 | Admin | Retry failed Service step |
| GET | `/api/workflow/instances/<id>/timeline` | OP39 | Auth | Full timeline with future steps and eligible assignees |
| POST | `/api/workflow/services/register` | — | Admin | Register/list service handlers (admin diagnostic) |

### 10.2 Modified Endpoints

| Endpoint | Change |
|----------|--------|
| `POST /api/workflow/steps/<id>/advance` | Add optional `next_assignee_id` in body; response includes `timeline` and `next_step.eligible_users` |
| `GET /api/workflow/instances/<id>` | Include `wfi_outcome` in response |
| `GET /api/workflow/my-steps` | Include `wsi_accepted_at` and step lifecycle phase |
| `GET /api/workflow/dashboard/sla` | Return overall SLA compliance summary |

### 10.3 Accept Step (OP35)

```
POST /api/workflow/steps/<id>/accept

Response 200:
{
  "step_key": "facility",
  "status": "Accepted",
  "accepted_at": "2026-03-11T10:30:00",
  "sla_deadline": "2026-03-12T10:30:00"
}

Response 400:
{"error": {"code": "INVALID_STATUS", "message": "Step is not in Pending status"}}

Response 403:
{"error": {"code": "NOT_ASSIGNEE", "message": "Only the assigned user can accept this step"}}
```

### 10.4 Reject Step (OP36)

```
POST /api/workflow/steps/<id>/reject
Body: {"reason": "Badge photo quality insufficient"}

Response 200:
{
  "rejected_step": "approval_gate",
  "reason": "Badge photo quality insufficient",
  "bounced_to": {
    "step_key": "investigation",
    "assignee": "Zhang Wei",
    "assignee_id": 3
  }
}

Response 400:
{"error": {"code": "REASON_REQUIRED", "message": "Rejection reason is required"}}
```

---

## 11. Engine Execution Changes

### 11.1 Step Processing Matrix

| Step Type | On Creation | On Accept | On Advance/Complete | On Reject |
|-----------|-------------|-----------|--------------------|-----------| 
| Task | Create Pending, notify assignee | Mark Accepted, start work SLA | Mark Completed, activate next | Bounce to previous |
| Approval | Create Pending, notify assignee | Mark Accepted | Approve → Completed + advance; Reject → bounce back | Bounce to previous |
| Gateway | Create Pending → immediately evaluate | N/A | Route to output step(s) | N/A |
| Service | Create Pending → immediately execute | N/A | Store outputs, advance | N/A (on_error handles) |
| Notification | Create Pending → immediately send + advance | N/A | Auto | N/A |
| Timer | Create Pending, set deadline | N/A | APScheduler triggers on_expire | N/A |
| Join | Create Pending, check if all inputs done | N/A | Auto-advance when all inputs Completed | N/A |
| End | Create Completed, set wfi_outcome, update action status | N/A | N/A | N/A |

### 11.2 Advance Step (Updated OP26)

```python
def advance_step(step_instance_id: int, completed_by: int,
                 comment: str = None, next_assignee_id: int = None) -> dict:
    """
    1. Verify step status is 'Accepted' (was 'Active' in V2)
    2. Mark Completed
    3. For each next step, based on type:
       - Task/Approval: create Pending (with next_assignee_id override if provided)
       - Gateway: evaluate decision table → route
       - Service: execute handler → store outputs → advance
       - Notification: send → advance
       - Timer: create with deadline → wait
       - Join: check resolution
       - End: complete workflow with outcome
    4. Return timeline + next_step info
    """
```

### 11.3 Gateway Evaluation

```python
def evaluate_gateway(instance_id: int, gateway_step_key: str, graph: dict) -> list[str]:
    """
    1. Load all field values for the instance (across all completed steps)
    2. Read decision_table from graph step definition
    3. For each rule in order:
       a. Check all conditions against field values
       b. If match and mode='exclusive': return [rule.output], stop
       c. If match and mode='inclusive': add rule.output to results
    4. If no match and _default exists: use _default.output
    5. If no match and no _default: raise WorkflowPausedError
    Returns: list of next step keys to activate
    """
```

### 11.4 Service Execution

```python
def execute_service_step(instance_id: int, step_key: str, graph: dict) -> dict:
    """
    1. Load service config from graph step definition
    2. Look up handler in SERVICE_REGISTRY
    3. Resolve input_mapping → dict of actual values
    4. Call handler(inputs)
    5. Write output_mapping → t_workflow_step_field_value
    6. Log to t_workflow_service_log
    7. On success: mark Completed, advance
    8. On error: mark Paused, log error, notify creator
    """
```

---

## 12. Migration Plan

### 12.1 Database Migration `migrate_v5_0.sql`

```sql
-- 1. Add wsi_accepted_at column
ALTER TABLE t_workflow_step_instance ADD COLUMN wsi_accepted_at DATETIME;

-- 2. Rename Active → Accepted in existing step instances
UPDATE t_workflow_step_instance
   SET wsi_status = 'Accepted', wsi_accepted_at = wsi_entered_at
 WHERE wsi_status = 'Active';

-- 3. Update CHECK constraint on wsi_status (SQLite: recreate table)
--    New values: Pending, Accepted, Completed, Rejected, Skipped, Paused

-- 4. Add wfi_outcome column
ALTER TABLE t_workflow_instance ADD COLUMN wfi_outcome VARCHAR(50);

-- 5. Create t_workflow_service_log table

-- 6. Add new action_history change types: StepRejected, SLAEscalation,
--    AssigneeOverride, StepAccepted, ServiceExecuted
```

### 12.2 Code Migration

| File | Change |
|------|--------|
| `engine.py` | Replace `'Active'` checks with `'Accepted'`; add accept/reject/escalate functions; add gateway/service/notification/timer processing |
| `graph.py` | Update `validate_graph()` for new types and rules; add decision table validation |
| `routes.py` | Add OP35-OP39 endpoints; modify OP26 response |
| `sla.py` | Add timer expiry handling |
| `approval_service.py` | Update to use `'Accepted'` status |
| `forms.py` | No changes |
| `service.py` | Add timeline query; add eligible-users resolver |
| `dashboard_service.py` | Add overall SLA compliance metrics |
| **New** `gateway.py` | Decision table evaluator |
| **New** `service_executor.py` | Service step handler + registry |
| **New** `service_registry.py` | Handler whitelist registry |
| **New** `timer.py` | Timer expiry handling |

### 12.3 Implementation Phases

| Phase | ID | Scope | Depends On |
|-------|----|-------|------------|
| V3.0-alpha | WF-10 | 3-phase lifecycle (accept/reject), rejection flow, status rename | WF-9 |
| V3.0-beta | WF-11 | Gateway + decision tables | WF-10 |
| V3.1 | WF-12 | Service steps + handler registry | WF-11 |
| V3.1 | WF-13 | Notification steps | WF-11 |
| V3.2 | WF-14 | Timer steps + auto-escalation | WF-10 |
| V3.2 | WF-15 | Multiple End outcomes | WF-10 |
| V3.3 | WF-16 | Runtime assignee override + timeline UI | WF-10 |
| V3.4 | WF-18 | Updated Drawflow canvas (8 node types) | WF-11, WF-12, WF-13 |
| V3.5 | WF-24 | React Flow canvas replaces Drawflow | WF-18 |

---

## 13. Test Plan

| Test File | Tests | Phase |
|-----------|-------|-------|
| `test_workflow_engine_v3.py` | accept_step, reject_step, escalate_step, 3-phase lifecycle | WF-10 |
| `test_workflow_gateway.py` | exclusive routing, inclusive routing, default rule, no-match pause | WF-11 |
| `test_workflow_service.py` | handler execution, input/output mapping, error handling, retry | WF-12 |
| `test_workflow_notification_step.py` | auto-send, auto-advance | WF-13 |
| `test_workflow_timer.py` | timer creation, expiry detection, auto-escalation, advance mode | WF-14 |
| `test_workflow_end_outcomes.py` | multiple ends, outcome stored, correct action_status | WF-15 | ✅ DONE 2026-03-14 |
| `test_workflow_assignee.py` | default assignment, override, eligible-user list, timeline | WF-16 |
| **Estimated total** | **~40 new tests** | |

---

## 14. Backward Compatibility

| Concern | Resolution |
|---------|------------|
| Existing V2 graphs with 4 types | Continue to work — Task/Approval/Join/End unchanged. `Active` status auto-mapped to `Accepted`. |
| Existing `advance_step()` calls | Still work — `Accepted` replaces `Active` check. V2 callers don't send `next_assignee_id`. |
| Graphs without Gateway/Service/Timer | Valid — these types are optional additions. |
| Graphs with exactly 1 End | Still valid — ≥1 is the new minimum. |
| File import/export | Not supported in the active builder UI; templates are created and maintained in-app. |
| Drawflow canvas | Replaced by `@xyflow/react` (React Flow) canvas in WF-24. All existing step/transition data structures are preserved; only the renderer changes. |

---

---

## 15. Canvas Technology (WF-24)

> Detailed builder UI, interaction, validation, and migration requirements are specified in `S75_workflow_ui_react_flow_update.md`.

### 15.1 Decision

The workflow builder canvas uses **`@xyflow/react`** (React Flow v12) instead of the Drawflow vanilla-JS library loaded via CDN. This gives the builder first-class React component integration, TypeScript types, and a full programmatic API.

### 15.2 React Flow Concepts Mapped to ActionHub

| Drawflow concept | React Flow equivalent | Notes |
|-----------------|----------------------|-------|
| `CanvasNode` | `Node<StepNodeData>` | Position and step metadata held in React Flow node |
| `CanvasConnection` | `Edge` | `source` / `target` map to `output_id` / `input_id` |
| Custom node HTML | `nodeTypes` registry | One custom component per step type |
| Port logic | `sourceHandle` / `targetHandle` | End nodes: no source handle; Join: 2 target handles |
| Drag from palette | `onDragOver` + `onDrop` on `<ReactFlow>` | Drop event creates a new `Node` via `addNodes()` |
| Canvas export | `getNodes()` + `getEdges()` | Serialised to `steps`/`transitions` for the API |

### 15.3 Custom Node Types

Each of the 8 step types has a dedicated React component registered in `nodeTypes`:

```tsx
const nodeTypes = {
  Task:         TaskNode,
  Approval:     ApprovalNode,
  Gateway:      GatewayNode,
  Service:      ServiceNode,
  Notification: NotificationNode,
  Timer:        TimerNode,
  Join:         JoinNode,
  End:          EndNode,
};
```

Each node component:
- Accepts `NodeProps<StepNodeData>` from React Flow
- Renders the step icon, name, type badge
- Uses `<Handle>` components from `@xyflow/react` for port connection points
- Highlights `selected` state with a border ring

### 15.4 Graph Serialisation (unchanged)

The data contract between the canvas and the API (`steps`/`transitions` JSON) is **unchanged**. React Flow state (`Node[]` + `Edge[]`) is converted to/from the existing format:

```ts
// Canvas → API
function toWorkflowGraph(nodes: Node<StepNodeData>[], edges: Edge[]): WorkflowGraph { ... }

// API → Canvas
function toReactFlowGraph(graph: WorkflowGraph): { nodes: Node<StepNodeData>[]; edges: Edge[] } { ... }
```

### 15.5 Package Dependency

```json
"@xyflow/react": "^12.0.0"
```

Added to `action_hub/frontend/package.json` `dependencies`.

---

## 16. Glossary

| Term | Definition |
|------|-----------|
| **Decision Table** | Ordered list of rules mapping input field values to output step routing (Camunda DMN-inspired) |
| **Gateway** | Automated routing step that evaluates conditions and directs flow to one or more branches |
| **Service Step** | Automated step that executes a registered Python function with mapped inputs/outputs |
| **Handler Registry** | Whitelist of allowed Python callables for Service steps, populated at app startup |
| **Escalation** | Manual or automatic reassignment of a step to a higher authority (team lead or workflow creator) |
| **Bounce-back** | Rejection behavior where a step returns to its predecessor for correction |
| **Wait-time** | Duration between step creation (Pending) and step acceptance (Accepted) |
| **Work-time** | Duration between step acceptance (Accepted) and step completion (Completed) |
| **Outcome** | Named terminal state of a workflow (e.g., "completed", "rejected", "timeout") |
