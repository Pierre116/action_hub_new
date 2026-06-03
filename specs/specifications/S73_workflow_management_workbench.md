# S73 — Workflow Management Workbench

**Date:** 2026-03-16
**Version:** 1.0
**Status:** 📋 Planned
**Depends On:** R16, S25, S16, S70, S72
**Enables:** Runtime workflow management after builder MVP

---

## 1. Overview

This spec defines the runtime **Workflow Management Workbench** used by end users, team leads, and admins to manage an active workflow instance.

It closes the current gap between:

- engine-level workflow behavior already specified in S70,
- assignment-rule extensions already specified in S72,
- and the actual user-facing workflow management experience still missing from the product spec.

The workbench covers four operational areas in one screen model:

1. **Step assignment** — who owns the current step, who can take over, who can delegate or reassign.
2. **Step and workflow status** — workflow instance status, current step lifecycle, derived action display status, SLA state.
3. **Step form** — editable fields, read-only context fields, draft saving, validation on completion.
4. **Step attachments** — controlled evidence/document uploads linked to a step instance.

This spec is product-facing. It does not change the core workflow engine rules already defined in S70 unless explicitly called out here.

---

## 2. Objectives

### 2.1 Business Goals

- Make workflow execution manageable without opening multiple tabs or unrelated pages.
- Reduce ambiguity between action status and workflow step status.
- Give assignees a single place to accept, work, attach evidence, complete, reject, or delegate.
- Give leads/admins operational control over stalled or misassigned steps.

### 2.2 Non-Goals

- No redesign of the workflow builder.
- No email-based attachment exchange.
- No unrestricted binary uploads.
- No full document-management system.

---

## 3. Actors and Permissions

| Actor | View Workbench | Edit Form | Upload Attachments | Accept / Complete | Delegate | Reassign | Override Next Assignee |
|------|----------------|-----------|--------------------|-------------------|----------|----------|------------------------|
| Current step assignee | Yes | Yes | Yes | Yes | Yes | No | Yes on completion |
| Admin | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| TeamLead of owning team | Yes | Optional by template/policy | Yes | Optional by policy | Yes | Yes | Yes |
| Other authenticated users | Read-only timeline only | No | No | No | No | No | No |

### 3.1 Authorization Rules

- Human-step actions apply only to `Task` and `Approval` steps unless a later spec extends them.
- `Gateway`, `Service`, `Notification`, `Timer`, `Join`, and `End` remain engine-driven and read-only in the workbench.
- Admin may override assignment eligibility rules defined in S72.

---

## 4. Workbench Screen Model

### 4.1 Layout

The workbench is primarily embedded in workflow-oriented runtime surfaces such as the workflow dashboard, workflow request detail, or workflow instance detail views.

Action Detail embedding is a compatibility pattern only where an action happens to have a linked workflow instance.

It is composed of five sections:

1. **Header Summary**
2. **Current Step Card**
3. **Step Form + Context**
4. **Step Attachments Panel**
5. **Workflow Timeline**

### 4.2 Header Summary

Shows the runtime summary for the active workflow instance:

- Workflow template name
- Workflow instance status
- Current step name
- Current step status
- Current assignee
- SLA badge: `On Time`, `Due Soon`, `Breached`
- Derived display status for the workflow work item; action-derived display status is optional compatibility metadata only

### 4.3 Current Step Card

Shows:

- step name and type
- assignee
- entered time
- accepted time
- deadline
- completion/rejection comment
- available actions for the current actor

Available actions may include:

- `Accept`
- `Save Draft`
- `Complete`
- `Reject`
- `Delegate`
- `Reassign`
- `Escalate`

---

## 5. Step Assignment Specification

### 5.1 Assignment States

The workbench must expose the following assignment-related states:

- `Unresolved` — no assignee resolved yet
- `Assigned` — assignee determined, step waiting for action
- `Accepted` — assignee acknowledged ownership
- `Escalated` — SLA breach or manual escalation changed the responsible user/team
- `Reassigned` — admin/team lead changed assignee directly

These are operational assignment states layered on top of the step lifecycle in S70.

### 5.2 Assignment Actions

| Action | Trigger | Who Can Do It | Result |
|-------|---------|---------------|--------|
| Assign | Step becomes active with no resolved assignee | Engine / Admin | `wsi_assignee_id` populated |
| Accept | User clicks Accept | Assignee / Admin | Step status moves to `Accepted` |
| Reassign | Admin/lead selects a new assignee | Admin / TeamLead | Current assignee replaced; notification sent |
| Override Next Assignee | Completing current step | Assignee / Admin / TeamLead | Next step assignee overridden before activation |
| Escalate | Manual click or SLA breach | Admin / TeamLead / Engine | Escalation target assigned and logged |

### 5.3 Assignment Resolution Order

When a human step activates, assignee resolution uses this precedence:

1. explicit runtime override from previous step
2. runtime carry-over after an escalation/reassignment branch
3. S72 assignment rule resolution
4. static template role/user fallback
5. workflow creator fallback

### 5.4 Audit Requirements

Every assignment mutation writes an action-history event with:

- old assignee
- new assignee
- actor performing the change
- reason/comment
- timestamp
- source: `engine`, `assignee`, `teamlead`, `admin`

---

## 6. Status Specification

### 6.1 Status Layers

The workbench must show three separate statuses at all times:

| Layer | Source | Example |
|------|--------|---------|
| Workflow instance status | `wfi_status` | `Active`, `Completed`, `Cancelled`, `Paused` |
| Step status | `wsi_status` | `Pending`, `Accepted`, `Completed`, `Rejected`, `Skipped`, `Paused`, `WaitingForChild` |
| Action display status | derived UI status | `HSE Validation`, `Finance Review`, `Completed` |

### 6.2 Status Rules

- Action display status never hides the true step status in the workbench.
- Human steps use the 3-phase V3 lifecycle from S70.
- Non-human steps appear as system-driven badges and are read-only.
- A breached SLA adds a separate urgency badge and does not replace the base step status.

### 6.3 Timeline Requirements

The timeline must display:

- all past steps with timestamps and actors
- current active step with SLA state
- future planned steps in read-only form
- branch/join structure for parallel steps where possible

---

## 7. Step Form Specification

### 7.1 Form Model

Step forms are derived from `wft_graph.steps[].fields` and rendered dynamically.

Supported field types in this spec:

- `text`
- `number`
- `date`
- `dropdown`
- `checkbox`
- `checklist`
- `link`

### 7.2 Context Data

The form may also display read-only `context_fields` from prior steps, as introduced by D194/S71.

Context fields must render separately from editable fields and be visually labeled as read-only.

### 7.3 Save Modes

| Mode | Purpose | Validation |
|------|---------|-----------|
| Save Draft | Persist partial work without completing the step | Type validation only |
| Complete Step | Finish the step and advance the workflow | Full required-field validation |
| Reject Step | Reject and bounce/route per engine rules | Rejection reason mandatory |

### 7.4 Form Behavior

- Field values are upserted to `t_workflow_step_field_value`.
- Saving draft must not advance the workflow.
- Completing a step must fail if any required field is empty or invalid.
- Later steps may read prior values, but may not silently mutate prior-step records.

---

## 8. Step Attachment Specification

### 8.1 Scope

Attachments in this spec are **step-instance attachments**, not generic action attachments.

They are intended for:

- evidence files
- signed forms
- screenshots
- exported reports
- supporting business documents

### 8.2 Security Policy

Allowed uploads must be controlled by both extension and MIME-type allowlist.

Allowed examples:

- `pdf`
- `docx`
- `xlsx`
- `pptx`
- `csv`
- `txt`
- `png`
- `jpg`

Blocked examples:

- CAD formats
- archives such as `zip`, `rar`, `7z`
- executables and scripts
- arbitrary binary blobs

### 8.3 Attachment Entity

Add a new runtime entity:

`WorkflowStepAttachment`

Proposed fields:

- `wsa_id`
- `wsa_step_inst_id`
- `wsa_action_id`
- `wsa_filename`
- `wsa_storage_path`
- `wsa_mime_type`
- `wsa_size_bytes`
- `wsa_uploaded_by`
- `wsa_uploaded_at`
- `wsa_deleted_at`
- `wsa_description`

### 8.4 Attachment Rules

- Attachments inherit the visibility model of the parent action/workflow.
- Upload is allowed only while the step is active for authorized users.
- Download is allowed for any authorized viewer of the workbench.
- Delete is soft-delete and limited to uploader, Admin, or TeamLead.
- Attachment add/delete events create action-history entries and in-app notifications.

### 8.5 Size and Count Limits

Default policy:

- max 10 files per step instance
- max 25 MB per file
- max 100 MB cumulative per workflow instance

These limits remain configurable in application settings later, but are fixed in V1 of this spec.

---

## 9. API Additions

### 9.1 Workbench Load

`GET /api/workflow/instances/<id>/workbench`

Returns:

- workflow instance summary
- current step summary
- current assignee + eligible users
- editable field definitions
- saved field values
- context field values
- attachments
- timeline entries

### 9.2 Save Draft

`POST /api/workflow/steps/<id>/draft`

Body:

```json
{
  "comment": "optional progress note",
  "fields": [
    {"key": "badge_code", "value": "A-1029"}
  ]
}
```

### 9.3 Delegate Step

`POST /api/workflow/steps/<id>/delegate`

Body:

```json
{
  "delegate_user_id": 42,
  "reason": "On leave until Friday"
}
```

### 9.4 Reassign Step

`POST /api/workflow/steps/<id>/reassign`

### 9.5 Upload Attachment

`POST /api/workflow/steps/<id>/attachments`

Multipart form upload with metadata.

### 9.6 Delete Attachment

`DELETE /api/workflow/steps/<id>/attachments/<attachment_id>`

---

## 10. UI States

### 10.1 Empty States

- no workflow bound
- workflow exists but no active human step
- step assigned to another user
- attachment list empty

### 10.2 Failure States

- assignee resolution failed
- save draft failed
- complete blocked by validation
- upload blocked by file policy
- SLA breach escalation in progress

---

## 11. Acceptance Criteria

1. A user can open one workbench and understand the current workflow step, assignee, SLA, and timeline without navigating elsewhere.
2. A current assignee can save form drafts and later complete the step with validation.
3. A current assignee can request reassignment with reason, and the change is audited.
4. An admin or team lead can reassign a step and the new assignee is notified.
5. The workbench distinguishes workflow status, step status, and derived action display status.
6. Controlled attachments can be uploaded to a step instance, listed, downloaded, and soft-deleted with audit history.
7. Blocked file types are rejected with a clear policy error.
8. Later steps can display configured context fields and earlier attachment references in read-only mode.

---

## 12. Implementation Notes

This spec intentionally builds on existing docs rather than replacing them:

- S70 remains the source of truth for engine lifecycle and step-type behavior.
- S72 remains the source of truth for assignment rule resolution and runtime transfer semantics.
- S73 defines the runtime product surface and the missing API/UI/data-contract glue around those capabilities.
