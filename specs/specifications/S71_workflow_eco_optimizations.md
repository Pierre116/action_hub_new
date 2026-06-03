# S71 — Workflow Engine: ECO Process Optimizations

> **Last updated**: 2026-03-12  
> **Source**: S70 gap analysis for Engineering Change Order (ECO) workflows  
> **Depends on**: S70 (V3 engine), S05 §11 (workflow data model)  
> **Decisions**: D193–D198 (new)

---

## 1. Purpose

S70 defines a general-purpose workflow engine with 8 step types, decision tables, and 3-phase lifecycle. This spec identifies **6 targeted optimizations** that close gaps when applying S70 to an industrial **Engineering Change Order (ECO)** process — the primary complex workflow at the organization.

All optimizations are backward-compatible additive changes. No existing S70 behaviour is modified.

---

## 2. ECO Process Reference

A typical ECO lifecycle starting from **ECO Release** (change request already approved):

```
ECO Release
   │
   ▼
┌──────────────────┐
│  Impact Assessment│  (Engineering: scope teams, affected lines, risk score)
└────────┬─────────┘
         │
   ┌─────▼─────┐
   │  Gateway   │  Inclusive: which teams need review?
   └──┬──┬──┬──┘
      │  │  │           ← parallel branches (0–4 teams)
  ┌───┘  │  └───┐
  ▼      ▼      ▼
 Prod  Quality  HSE   Maintenance
Review  Review  Review  Review
  │      │      │       │
  └──┬───┘──┬───┘───┬───┘
     │      │       │
   ┌─▼──────▼───────▼─┐
   │       Join        │  Wait for all activated reviews
   └────────┬──────────┘
            │
     ┌──────▼──────┐
     │  Approval   │  Engineering Mgr / Plant Mgr (severity-based)
     └──────┬──────┘
            │
   ┌────────▼─────────┐
   │  Implementation   │  Maintenance executes change
   └────────┬─────────┘
            │
   ┌────────▼─────────┐
   │   Verification    │  Quality validates effectiveness
   └────────┬─────────┘
            │  ← may loop back to Implementation on failure
   ┌────────▼─────────┐
   │     Closure       │  Engineering updates docs, captures lessons
   └────────┬─────────┘
            │
     ┌──────▼──────┐
     │     End      │  Approved / Rejected / Deferred
     └─────────────┘
```

### 2.1 Gap Summary

| # | Gap | ECO Impact | S70 Status | Optimization |
|---|-----|-----------|------------|-------------|
| O1 | No `link` field type for document references | Cannot reference ECO package (drawings, test reports, CAD files) | Missing | Add `link` field type |
| O2 | No read-only display of prior step fields | Reviewers can't see impact assessment data in their step | Missing | Add `context_fields` to step definition |
| O3 | Join waits for ALL branches; no cancel-on-reject | One reviewer rejects → other reviews run uselessly | Missing | Add Join `first_reject` mode |
| O4 | No rework loop iteration limit | Verification ↔ Implementation can loop forever | Missing | Add `max_iterations` on back-edge transitions |
| O5 | `wsi_comment` only used on rejection | No structured audit trail for approvals/completions | Partial | Enable comments on all step completions |
| O6 | No ECO reference template | Admins must build ECO from scratch in the workflow builder | Missing | Provide pilot ECO template |

---

## 3. Decisions

| ID | Decision | Rationale | Affects |
|----|----------|-----------|---------|
| **D193** | Add `link` field type to step fields. Renders as clickable URL; validated client-side as well-formed URL. No file upload — references external storage only. | ECO packages live on file server / SharePoint. Text fields lose semantics. | S05 §11.4, templates, JS |
| **D194** | Steps may declare `context_fields`: a list of `{step_key, field_key}` pairs displayed read-only above the step form. Engine populates values from `t_workflow_step_field_value`. | Reviewers need impact assessment data (scope, affected lines, risk) without navigating away. | engine.py, templates |
| **D195** | Join step gains optional `mode` property: `all` (default, current behaviour) or `first_reject`. In `first_reject` mode, if any incoming branch is Rejected, the Join immediately cancels all other incomplete incoming branches and propagates the rejection. | Parallel ECO reviews: if HSE rejects, no point continuing Production/Quality reviews. Saves reviewer time. | engine.py, graph.py |
| **D196** | Rejection transitions may declare `max_iterations` (positive integer). Engine tracks iteration count per back-edge. When limit reached, instead of looping back, engine escalates to workflow creator with notification "Max rework cycles reached". | Prevents infinite Verification ↔ Implementation loop. Typical limit: 3. | engine.py, schema |
| **D197** | `wsi_comment` is accepted on all step completions (Task advance, Approval approve), not only on rejection. Comment is optional for non-rejection actions. | ECO audit trail: every step should record "why this decision was made" for compliance. | engine.py, routes.py |
| **D198** | Provide a built-in ECO pilot template graph (like the existing OT User Creation pilot). Seeded via migration, editable by admin. | Reduces ECO setup time from hours to minutes. Demonstrates all V3 features in a real use case. | pilot.py, seed |

---

## 4. O1 — `link` Field Type (D193)

### 4.1 Schema Addition

Extends the step field `type` enum:

```
Existing: text | dropdown | date | number | checkbox | checklist
New:      text | dropdown | date | number | checkbox | checklist | link
```

### 4.2 Field Definition

```json
{
  "key": "eco_package_url",
  "label_en": "ECO Package",
  "label_cn": "ECO文件包",
  "type": "link",
  "required": true,
  "placeholder": "https://files.company.local/eco/ECO-2026-042"
}
```

### 4.3 Behaviour

| Aspect | Specification |
|--------|--------------|
| **Storage** | Stored as string in `t_workflow_step_field_value.wsfv_value` |
| **Validation** | Must start with `http://` or `https://`. Max 2048 chars. |
| **Rendering** | Displayed as clickable `<a>` with `target="_blank"` and `rel="noopener noreferrer"` |
| **Read-only** | In `context_fields` display, rendered as clickable link |
| **Gateway** | Can be used in decision table conditions (string match) |

### 4.4 Graph Validation

- If `type: "link"`, `options` is not allowed (unlike dropdown/checklist).
- `placeholder` is optional (string).

### 4.5 Security

- Server sanitizes URL — reject `javascript:`, `data:`, `file:` URI schemes.
- Display via Jinja2 `|e` auto-escaping (XSS prevention).
- No server-side fetch of the URL (no SSRF risk).

---

## 5. O2 — Read-Only Context Fields (D194)

### 5.1 Problem

A Quality reviewer opening the "Quality Review" step in an ECO has no visibility into what the Impact Assessment step recorded (affected lines, risk score, ECO package link). They must navigate away to find this data.

### 5.2 Step Definition Extension

```json
{
  "type": "Task",
  "name_en": "Quality Review",
  "role": "Quality",
  "sla_hours": 48,
  "context_fields": [
    {"from_step": "impact_assessment", "field_key": "affected_lines"},
    {"from_step": "impact_assessment", "field_key": "risk_score"},
    {"from_step": "impact_assessment", "field_key": "eco_package_url"},
    {"from_step": "intake", "field_key": "eco_number"}
  ],
  "fields": [
    {"key": "qc_approval", "label_en": "QC Approval", "type": "dropdown",
     "options": ["Approved", "Requires rework", "Deferred"], "required": true},
    {"key": "qc_notes", "label_en": "Review Notes", "type": "text", "required": false}
  ]
}
```

### 5.3 Engine Behaviour

1. When building step form data for a human step (Task/Approval), engine reads `context_fields`.
2. For each entry, queries `t_workflow_step_field_value` for the matching `(instance, from_step, field_key)`.
3. Returns these values alongside the step form fields, marked `readonly: true`.
4. Template renders them in a "Context" panel above the editable form.

### 5.4 API Response

`GET /api/workflow/steps/<id>` response includes:

```json
{
  "step_key": "quality_review",
  "status": "Pending",
  "context": [
    {"from_step": "impact_assessment", "field_key": "affected_lines",
     "label_en": "Affected Production Lines", "value": "Line 3, Line 7"},
    {"from_step": "impact_assessment", "field_key": "risk_score",
     "label_en": "Risk Score (1-10)", "value": "8"},
    {"from_step": "impact_assessment", "field_key": "eco_package_url",
     "label_en": "ECO Package", "value": "https://files.company.local/eco/ECO-2026-042",
     "type": "link"}
  ],
  "fields": [ ... ]
}
```

### 5.5 Graph Validation

- Each `context_fields` entry must reference a valid `from_step` key in the graph.
- Each `field_key` must exist in the referenced step's `fields` array.
- Only steps reachable **before** the current step are valid `from_step` targets (no forward references).

---

## 6. O3 — Join `first_reject` Mode (D195)

### 6.1 Problem

In ECO parallel reviews, if HSE rejects the change (safety concern), the Production, Quality, and Maintenance reviews continue running uselessly. Reviewers waste time, and the workflow can't proceed to rejection handling until everyone finishes.

### 6.2 Join Mode Extension

```json
{
  "type": "Join",
  "name_en": "Wait for all reviews",
  "mode": "all"
}
```

| Mode | Behaviour | Use Case |
|------|-----------|----------|
| `all` | Wait for every incoming branch to reach Completed. (Default — current S70 behaviour.) | Standard fork-join |
| `first_reject` | If any incoming branch step is Rejected, immediately: (1) cancel all other Pending/Accepted steps in sibling branches, (2) mark Join as Rejected, (3) follow the Join's rejection transition. If all complete without rejection, behave like `all`. | ECO parallel reviews with fail-fast |

### 6.3 Engine Logic

```python
def resolve_join_v3(instance_id: int, join_step_key: str, graph: dict) -> str:
    """
    Returns: 'waiting' | 'completed' | 'rejected'
    """
    mode = graph['steps'][join_step_key].get('mode', 'all')
    incoming = get_incoming_branch_steps(instance_id, join_step_key, graph)

    if mode == 'first_reject':
        # Check if any incoming step is Rejected
        rejected = [s for s in incoming if s['wsi_status'] == 'Rejected']
        if rejected:
            # Cancel remaining incomplete sibling steps
            cancel_incomplete_siblings(instance_id, incoming)
            return 'rejected'

    # Standard: all must be Completed
    all_done = all(s['wsi_status'] in ('Completed', 'Skipped') for s in incoming)
    return 'completed' if all_done else 'waiting'
```

### 6.4 Cancellation Cascade

When `first_reject` triggers:

1. All Pending/Accepted step instances in sibling parallel branches → status set to `Cancelled`.
2. A `StepCancelled` entry is logged in `t_action_history` for each cancelled step.
3. Cancelled assignees receive a notification: "ECO review cancelled — {rejector_step} was rejected."
4. The Join step follows its `rejection` transition (or bounces back to the fork source if none defined).

### 6.5 Graph Validation

- `mode` must be `all` or `first_reject` (default: `all`).
- If `mode: "first_reject"`, the Join step should have a `rejection` transition defined (warning if missing — engine falls back to bounce-back).

---

## 7. O4 — Loop Iteration Limit (D196)

### 7.1 Problem

ECO Verification step can reject → bounce back to Implementation → re-execute → re-verify, creating a rework loop. Without a guard, this loops indefinitely.

### 7.2 Transition Extension

```json
{
  "from": "verification",
  "to": "implementation",
  "type": "rejection",
  "label_en": "Rework needed",
  "max_iterations": 3
}
```

### 7.3 Engine Behaviour

1. When following a rejection transition that has `max_iterations`, engine counts how many times this specific `(from, to)` pair has been traversed for this workflow instance.
2. Count is derived from `t_workflow_step_instance`: number of existing instances of the target step for this workflow instance.
3. If count ≥ `max_iterations`:
   - Do NOT follow the rejection transition.
   - Instead, create a notification to the workflow creator: "Max rework cycles ({N}) reached for step '{from_step}'. Manual intervention required."
   - Set the step to `Paused` status.
   - Log `MaxIterationsReached` in `t_action_history`.

### 7.4 Data Model

No new columns needed. Iteration count is computed at runtime from existing `t_workflow_step_instance` rows (count of rows with matching `wsi_step_key` for the same `wsi_wfi_id`).

### 7.5 Escalation Path

When max iterations is reached, the workflow creator has three options via existing API:

1. **Override and loop again** — admin endpoint resets the iteration context and re-triggers the rejection transition.
2. **Re-assign** — escalate to a different person (plant manager) via assignee override.
3. **Cancel the workflow** — if the ECO is no longer viable.

### 7.6 Graph Validation

- `max_iterations` is optional on rejection transitions only (ignored on other types).
- Must be a positive integer ≥ 1 if specified.

---

## 8. O5 — Step Completion Comments (D197)

### 8.1 Current State

S70 § 10.4 specifies `wsi_comment` as required on rejection (`POST /steps/<id>/reject`). But `POST /steps/<id>/advance` has no `comment` field in the body.

### 8.2 Change

| Endpoint | Current | Updated |
|----------|---------|---------|
| `POST /steps/<id>/advance` | Body: `{field_values, next_assignee_id}` | Body: `{field_values, next_assignee_id, comment}` |
| `POST /steps/<id>/accept` | No body | Body: `{comment}` (optional) |

### 8.3 Storage

`wsi_comment` column already exists. For multi-comment scenarios (accept comment + complete comment), use JSON array:

```json
[
  {"phase": "accept", "text": "Taking this review.", "at": "2026-03-12T10:00:00"},
  {"phase": "complete", "text": "Approved — no HSE concerns.", "at": "2026-03-12T14:30:00"}
]
```

If only one comment exists, store as plain string (backward-compatible).

### 8.4 Timeline Display

The timeline response (OP39) now includes comments for each step:

```json
{
  "step_key": "hse_review",
  "status": "Completed",
  "comments": [
    {"phase": "complete", "text": "Approved — no HSE concerns.", "at": "2026-03-12T14:30:00"}
  ]
}
```

### 8.5 ECO Audit Value

Every ECO step now has a traceable justification:
- Impact Assessment: "Scope limited to Line 3 — no CNC impact"
- HSE Review: "Approved — change does not affect lockout/tagout procedures"
- Verification: "All 4 checklist items passed. Baseline comparison attached."
- Closure: "Drawing Rev D published. Training completed 2026-03-15."

---

## 9. O6 — ECO Pilot Template (D198)

### 9.1 Template Graph

```json
{
  "name_en": "Engineering Change Order (ECO)",
  "name_cn": "工程变更单 (ECO)",
  "version": 1,
  "steps": {
    "intake": {
      "type": "Task",
      "name_en": "ECO Intake",
      "name_cn": "ECO 登记",
      "order": 1,
      "role": "Engineering",
      "sla_hours": null,
      "fields": [
        {"key": "eco_number", "label_en": "ECO Number", "label_cn": "ECO编号",
         "type": "text", "required": true},
        {"key": "impact_level", "label_en": "Impact Level", "label_cn": "影响级别",
         "type": "dropdown", "options": ["Critical", "High", "Normal", "Low"],
         "required": true},
        {"key": "affected_lines", "label_en": "Affected Production Lines",
         "label_cn": "受影响生产线", "type": "text", "required": true},
        {"key": "eco_package_url", "label_en": "ECO Package Link",
         "label_cn": "ECO文件包链接", "type": "link", "required": true},
        {"key": "justification", "label_en": "Change Justification",
         "label_cn": "变更理由", "type": "text", "required": true}
      ]
    },
    "impact_assessment": {
      "type": "Task",
      "name_en": "Impact Assessment",
      "name_cn": "影响评估",
      "order": 2,
      "role": "Engineering",
      "sla_hours": 24,
      "context_fields": [
        {"from_step": "intake", "field_key": "eco_number"},
        {"from_step": "intake", "field_key": "eco_package_url"}
      ],
      "fields": [
        {"key": "teams_affected", "label_en": "Teams Affected",
         "label_cn": "受影响部门", "type": "checklist",
         "options": ["Production", "Quality", "HSE", "Maintenance"],
         "required": true},
        {"key": "risk_score", "label_en": "Risk Score (1–10)",
         "label_cn": "风险评分 (1–10)", "type": "number", "required": true}
      ]
    },
    "route_by_impact": {
      "type": "Gateway",
      "name_en": "Route by Impact Level",
      "name_cn": "按影响级别路由",
      "gateway_mode": "exclusive",
      "decision_table": {
        "inputs": ["impact_level"],
        "rules": [
          {"conditions": {"impact_level": "Critical"},
           "output": "plant_mgr_approval"},
          {"conditions": {"_default": true},
           "output": "production_review"}
        ]
      }
    },
    "production_review": {
      "type": "Task",
      "name_en": "Production Review",
      "name_cn": "生产评审",
      "order": 3,
      "role": "Production",
      "sla_hours": 24,
      "context_fields": [
        {"from_step": "intake", "field_key": "eco_number"},
        {"from_step": "impact_assessment", "field_key": "teams_affected"},
        {"from_step": "impact_assessment", "field_key": "risk_score"},
        {"from_step": "intake", "field_key": "eco_package_url"}
      ],
      "fields": [
        {"key": "prod_approval", "label_en": "Production Approval",
         "label_cn": "生产审批", "type": "dropdown",
         "options": ["Approved", "Needs changes", "Defer"], "required": true},
        {"key": "prod_notes", "label_en": "Production Notes",
         "label_cn": "生产备注", "type": "text", "required": false}
      ]
    },
    "quality_review": {
      "type": "Task",
      "name_en": "Quality Review",
      "name_cn": "质量评审",
      "order": 3,
      "role": "Quality",
      "sla_hours": 48,
      "context_fields": [
        {"from_step": "intake", "field_key": "eco_number"},
        {"from_step": "impact_assessment", "field_key": "teams_affected"},
        {"from_step": "intake", "field_key": "eco_package_url"}
      ],
      "fields": [
        {"key": "qc_approval", "label_en": "QC Approval",
         "label_cn": "质量审批", "type": "dropdown",
         "options": ["Approved", "Requires rework", "Deferred"], "required": true}
      ]
    },
    "hse_review": {
      "type": "Approval",
      "name_en": "HSE Review",
      "name_cn": "HSE评审",
      "order": 3,
      "role": "HSE",
      "sla_hours": 48,
      "context_fields": [
        {"from_step": "intake", "field_key": "eco_number"},
        {"from_step": "intake", "field_key": "eco_package_url"}
      ],
      "fields": [
        {"key": "hse_clearance", "label_en": "HSE Clearance",
         "label_cn": "HSE许可", "type": "checkbox", "required": true}
      ]
    },
    "maintenance_review": {
      "type": "Task",
      "name_en": "Maintenance Review",
      "name_cn": "维护评审",
      "order": 3,
      "role": "Maintenance",
      "sla_hours": 24,
      "context_fields": [
        {"from_step": "intake", "field_key": "eco_number"},
        {"from_step": "impact_assessment", "field_key": "teams_affected"},
        {"from_step": "intake", "field_key": "eco_package_url"}
      ],
      "fields": [
        {"key": "maint_approval", "label_en": "Can Execute?",
         "label_cn": "是否可执行?", "type": "dropdown",
         "options": ["Ready", "Needs planning", "Not feasible"], "required": true}
      ]
    },
    "join_reviews": {
      "type": "Join",
      "name_en": "Wait for All Reviews",
      "name_cn": "等待所有评审完成",
      "mode": "first_reject"
    },
    "plant_mgr_approval": {
      "type": "Approval",
      "name_en": "Plant Manager Approval",
      "name_cn": "工厂经理审批",
      "order": 4,
      "role": "Admin",
      "sla_hours": 12,
      "context_fields": [
        {"from_step": "intake", "field_key": "eco_number"},
        {"from_step": "intake", "field_key": "impact_level"},
        {"from_step": "impact_assessment", "field_key": "risk_score"},
        {"from_step": "intake", "field_key": "eco_package_url"}
      ],
      "fields": [
        {"key": "mgr_decision", "label_en": "Decision",
         "label_cn": "审批决定", "type": "dropdown",
         "options": ["Approve", "Reject", "Defer"], "required": true}
      ]
    },
    "implementation": {
      "type": "Task",
      "name_en": "Execute Change",
      "name_cn": "执行变更",
      "order": 5,
      "role": "Maintenance",
      "sla_hours": 72,
      "context_fields": [
        {"from_step": "intake", "field_key": "eco_number"},
        {"from_step": "intake", "field_key": "affected_lines"},
        {"from_step": "intake", "field_key": "eco_package_url"}
      ],
      "fields": [
        {"key": "execution_date", "label_en": "Execution Date",
         "label_cn": "执行日期", "type": "date", "required": true},
        {"key": "deviation_notes", "label_en": "Deviations / Issues",
         "label_cn": "偏差/问题", "type": "text", "required": false}
      ]
    },
    "verification": {
      "type": "Task",
      "name_en": "Verify & Validate",
      "name_cn": "验证与确认",
      "order": 6,
      "role": "Quality",
      "sla_hours": 48,
      "context_fields": [
        {"from_step": "intake", "field_key": "eco_number"},
        {"from_step": "implementation", "field_key": "execution_date"},
        {"from_step": "implementation", "field_key": "deviation_notes"}
      ],
      "fields": [
        {"key": "test_checklist", "label_en": "Verification Checklist",
         "label_cn": "验证清单", "type": "checklist",
         "options": [
           "Pre-change baseline OK",
           "Post-change baseline OK",
           "No regression detected",
           "Performance within spec"
         ], "required": true},
        {"key": "verified_by", "label_en": "Verified By",
         "label_cn": "验证人", "type": "text", "required": true}
      ]
    },
    "closure": {
      "type": "Task",
      "name_en": "Document & Close",
      "name_cn": "归档与关闭",
      "order": 7,
      "role": "Engineering",
      "sla_hours": 24,
      "context_fields": [
        {"from_step": "intake", "field_key": "eco_number"},
        {"from_step": "verification", "field_key": "test_checklist"},
        {"from_step": "verification", "field_key": "verified_by"}
      ],
      "fields": [
        {"key": "drawing_rev", "label_en": "Drawing Revision",
         "label_cn": "图纸版本", "type": "text", "required": true},
        {"key": "lessons_learned", "label_en": "Lessons Learned",
         "label_cn": "经验教训", "type": "text", "required": false}
      ]
    },
    "notify_production": {
      "type": "Notification",
      "name_en": "Notify Production — ECO Closed",
      "name_cn": "通知生产部 — ECO已关闭",
      "notification": {
        "target_role": "Production",
        "title_en": "ECO {eco_number} has been closed",
        "title_cn": "ECO {eco_number} 已关闭",
        "body_template": "Drawing revision {drawing_rev} is now effective."
      }
    },
    "end_approved": {
      "type": "End",
      "name_en": "ECO Approved & Closed",
      "name_cn": "ECO 批准并关闭",
      "outcome": "approved_closed",
      "action_status": "Done"
    },
    "end_rejected": {
      "type": "End",
      "name_en": "ECO Rejected",
      "name_cn": "ECO 被拒绝",
      "outcome": "rejected",
      "action_status": "Cancelled"
    },
    "end_deferred": {
      "type": "End",
      "name_en": "ECO Deferred",
      "name_cn": "ECO 延期",
      "outcome": "deferred",
      "action_status": "Postponed"
    }
  },
  "transitions": [
    {"from": "intake", "to": "impact_assessment", "type": "normal"},
    {"from": "impact_assessment", "to": "route_by_impact", "type": "normal"},
    {"from": "route_by_impact", "to": "production_review", "type": "condition"},
    {"from": "route_by_impact", "to": "quality_review", "type": "condition"},
    {"from": "route_by_impact", "to": "hse_review", "type": "condition"},
    {"from": "route_by_impact", "to": "maintenance_review", "type": "condition"},
    {"from": "route_by_impact", "to": "plant_mgr_approval", "type": "condition"},
    {"from": "production_review", "to": "join_reviews", "type": "normal"},
    {"from": "quality_review", "to": "join_reviews", "type": "normal"},
    {"from": "hse_review", "to": "join_reviews", "type": "normal"},
    {"from": "maintenance_review", "to": "join_reviews", "type": "normal"},
    {"from": "join_reviews", "to": "plant_mgr_approval", "type": "normal"},
    {"from": "join_reviews", "to": "impact_assessment", "type": "rejection",
     "label_en": "Review rejected — reassess impact"},
    {"from": "plant_mgr_approval", "to": "implementation", "type": "normal"},
    {"from": "plant_mgr_approval", "to": "end_rejected", "type": "rejection",
     "label_en": "Plant Manager rejected ECO"},
    {"from": "implementation", "to": "verification", "type": "normal"},
    {"from": "verification", "to": "closure", "type": "normal"},
    {"from": "verification", "to": "implementation", "type": "rejection",
     "label_en": "Rework needed", "max_iterations": 3},
    {"from": "closure", "to": "notify_production", "type": "normal"},
    {"from": "notify_production", "to": "end_approved", "type": "normal"},
    {"from": "impact_assessment", "to": "end_deferred", "type": "rejection",
     "label_en": "ECO deferred during assessment"}
  ]
}
```

### 9.2 Template Characteristics

| Feature | ECO Pilot Uses |
|---------|---------------|
| All 8 step types | Task (6), Approval (2), Gateway (1), Notification (1), Join (1), End (3) — Service & Timer not included in base template (admin can add) |
| `link` field (O1) | `eco_package_url` on intake |
| `context_fields` (O2) | Every review step shows ECO number + package link + assessment data |
| `first_reject` Join (O3) | `join_reviews` cancels parallel reviews on any rejection |
| `max_iterations` (O4) | Verification → Implementation limited to 3 rework cycles |
| Step comments (O5) | All steps accept comments via updated API |
| Decision table | Gateway routes Critical ECOs directly to Plant Manager |
| Multiple End outcomes | 3 end states: Approved, Rejected, Deferred |
| Rejection transitions | 4 rejection paths for different failure scenarios |

### 9.3 Seeding

Add to `migrate_v5_0.py` (or dedicated ECO migration):

```python
ECO_TEMPLATE_GRAPH = { ... }  # JSON above

def seed_eco_template(db):
    """Insert ECO pilot template if not exists."""
    existing = db.execute(
        "SELECT wft_id FROM t_workflow_template WHERE wft_name_en = ?",
        ("Engineering Change Order (ECO)",)
    ).fetchone()
    if not existing:
        db.execute("""
            INSERT INTO t_workflow_template
                (wft_name_en, wft_name_cn, wft_description_en, wft_description_cn,
                 wft_graph, wft_is_active, wft_version, wft_created_at, wft_updated_at)
            VALUES (?, ?, ?, ?, ?, 1, 1, datetime('now'), datetime('now'))
        """, (
            "Engineering Change Order (ECO)",
            "工程变更单 (ECO)",
            "Standard ECO workflow: intake → assessment → parallel reviews → approval → implementation → verification → closure",
            "标准ECO流程：登记 → 评估 → 并行评审 → 审批 → 执行 → 验证 → 归档",
            json.dumps(ECO_TEMPLATE_GRAPH),
        ))
```

---

## 10. Implementation Impact

### 10.1 Files Affected

| Optimization | Files |
|-------------|-------|
| O1 (`link` field) | `graph.py` (validation), `engine.py` (no change), step form template, step form JS |
| O2 (`context_fields`) | `graph.py` (validation), `engine.py` (populate context), step form template, routes.py (API response) |
| O3 (`first_reject` Join) | `engine.py` (`resolve_join`), `graph.py` (validate mode) |
| O4 (`max_iterations`) | `engine.py` (rejection handler), `graph.py` (validate transition prop) |
| O5 (completion comments) | `engine.py` (`advance_step`), `routes.py` (accept body), step form template |
| O6 (ECO pilot) | `pilot.py` (new graph), migration seed |

### 10.2 Database Changes

None. All optimizations use existing columns (`wsi_comment`, `t_workflow_step_field_value`) or compute at runtime. The `link` field type is a value in `wsfv_value` (string column). Join `mode` and `max_iterations` are graph JSON properties — no schema change.

### 10.3 Test Plan

| Test | Count | Covers |
|------|-------|--------|
| `link` field validation (valid URL, reject javascript:, reject data:) | 4 | O1 |
| `context_fields` population + template rendering | 3 | O2 |
| Join `first_reject`: one branch rejects → others cancelled | 2 | O3 |
| Join `first_reject`: all complete → normal advance | 1 | O3 |
| `max_iterations` reached → pause + notify | 2 | O4 |
| `max_iterations` not reached → normal loop | 1 | O4 |
| Step advance with comment | 2 | O5 |
| Step accept with comment | 1 | O5 |
| ECO pilot template seed + validate graph | 1 | O6 |
| ECO pilot E2E: intake → reviews → approval → closure | 1 | O6 |
| **Total** | **18** | |

---

## 11. Dependency on S70

All 6 optimizations require S70 V3 engine to be implemented first:

```
S70 WF-10 (3-phase lifecycle)
  └── O5 (completion comments — extends accept/advance)
S70 WF-11 (Gateway + decision tables)
  └── O1 (link field type — extends field validation)
  └── O2 (context_fields — extends step data loading)
S70 WF-12 (Service steps)
  └── O6 (ECO pilot — uses all step types)
S70 WF-13 (Notification steps)
  └── O6 (ECO pilot — notify_production step)
S70 WF-15 (Multiple End outcomes)
  └── O6 (ECO pilot — 3 End steps)
S70 WF-10 (Join resolution)
  └── O3 (first_reject mode — extends resolve_join)
Engine rejection handler
  └── O4 (max_iterations — extends rejection transition processing)
```

**Recommended implementation order**: O1 → O5 → O2 → O3 → O4 → O6 (pilot is the integration test).

---

## 12. Out of Scope

| Feature | Reason | Future |
|---------|--------|--------|
| File upload / attachment storage | Security policy; the organization uses external file server | Integrate via `link` field + SharePoint API in Service step |
| Cross-ECO dependencies ("ECO A blocks ECO B") | Requires workflow orchestration layer | V4 |
| AI-driven impact routing | Requires R11 Agent framework | Post-V3 |
| Automatic verification re-entry (non-rejection) | Over-engineering; manual rejection loop is sufficient | Evaluate after ECO pilot feedback |
| RACI matrix per step | Template role assignment is sufficient for 10-user plant | Enterprise feature |
