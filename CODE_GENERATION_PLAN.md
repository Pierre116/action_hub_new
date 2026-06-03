# ActionHub — Code Generation Plan

> **Last updated**: 2026-03-19
> **Current version**: V3.17 — P12 in progress / WF-25 aligned
> **Active batches**: P8 ✅ DONE, P9 ✅ DONE, WF-20 ✅ DONE, WF-21 ✅ DONE, WF-22 ✅ DONE, WF-23 ✅ DONE, P10 ✅ DONE, P11 IN PROGRESS, WF-24 ✅ DONE, DOC-1 ✅ DONE, DOC-2 ✅ DONE, WF-25 ✅ DONE, WF-26 ✅ DONE, P12 IN PROGRESS
> **Specs baseline**: S05-S25, S60, S70, S72, S73, S74, S80, R19
> **Test suite**: ~273 tests passing

---

## Manual Process Workflow Creation Only (2026-03-18)

- Workflow instances are never auto-started when an action is created or edited.
- There is no auto-start binding or automatic workflow instance creation based on action fields.
- Process workflows are launched separately from actions from the existing workflow area of the product.
- Actions and workflow steps may appear in the same dashboard, but in separate panels and as separate work object types.
- Existing-action workflow start remains compatibility-only and must not be treated as the primary workflow model.
- All previous references to auto-start, auto-binding, or automatic workflow instance creation are obsolete and must not be implemented.

---

## Batch Status - Single Source of Truth

> All agents read this table for current status. Update only this file on completion.

| Batch | Status | Notes |
|-------|--------|-------|
| P1 (Terminology rollout) | ✅ DONE | - |
| SEP-0 → SEP-4 | ✅ DONE | Jinja2/HTMX removed; React 18 SPA live |
| WF-10 (3-phase lifecycle) | ✅ DONE | `accept_step`, `reject_step`, `escalate_step` in `engine.py` |
| WF-11 (Gateway + decision tables) | ✅ DONE | `gateway.py` + engine integration |
| WF-12.5 (Parallel branches / multi-assignee) | ✅ DONE | Fork/join + multi-assignee in `engine.py`; tests in `test_workflow_engine.py` |
| WF-12 (Service steps) | ✅ DONE | `service_executor.py`, handler registry, 7 tests |
| WF-13 (Notification steps) | ✅ DONE | `engine.py` + `test_workflow_notification_step.py` (3 tests) |
| WF-14 (Timer steps) | ✅ DONE | `timer.py` + `sla.py` + `test_workflow_timer.py` (4 tests) |
| WF-15 (Multiple End outcomes) | ✅ DONE | `wfi_outcome` column, engine + API, gateway bug fixed, 3 tests |
| WF-16 (Runtime assignee override + timeline) | ✅ DONE | `reassign_step`, timeline endpoint, 3 tests - 263 total |
| WF-17 (Split SLA dashboard) | ❌ REMOVED | Removed from spec and code per user request |
| WF-18 (Updated Drawflow canvas) | ✅ DONE | Drawflow SPA updated for in-app create/edit/save using canonical `steps`/`transitions` graph |
| **P8 (Meeting Decisions)** | ✅ DONE | All 5 gaps implemented (P8-G7/G8/G9/G10/G12); test file created |
| **P9 (Readiness Management)** | ✅ DONE | Both gaps implemented (P9-G4 tests, P9-G6 inline editing) |
| WF-19 (Declarative assignment rules) | ✅ DONE | `assignment.py` with 5 rule types; engine integration; schema updated |
| WF-20 (Delegation + subprocess engine) | ✅ DONE | delegate_step, get_eligible_users, subprocess status API; 8 tests added |
| **WF-21 (Workflow workbench backend APIs)** | ✅ DONE | Workbench load, draft save, attachment upload/list/delete endpoints; 10 tests |
| **WF-22 (Workflow workbench frontend)** | ✅ DONE | WorkbenchPanel component, field rendering, attachments UI, i18n; later re-homed to dedicated workflow runtime pages under WF-25 |
| **WF-23 (Workflow validation and rollout)** | ✅ DONE | Test suite validated, migration dry-run complete, docs closeout |
| **P10 (Meeting action category inheritance)** | ✅ DONE | Frontend pre-populate topic from meeting; visual indicator added; S74 |
| **P11 (Taxonomy category consolidation rollout)** | IN PROGRESS | Backend aligned for Category rename + max-2 category model; frontend, reporting, and tests remain. Workflows use action categories only |
| **P12 (Meeting series workspace)** | IN PROGRESS | Core series/occurrence APIs, visibility, occurrence comments, series-wide action/decision views, and MoM PDF are live; formal migration/schema closeout, workspace polish, and broader validation remain |
| **WF-24 (React Flow canvas)** | ✅ DONE | React Flow builder is live on `/workflow/builder`; compact UI polish applied; legacy Drawflow builder removed |
| **WF-25 (Process workflow runtime UX)** | ✅ DONE | Workflow dashboard is primary; workflow workbench uses dedicated routes; actions and workflow work stay separate; action-linked runtime is compatibility only |
| **DOC-1 (Core doc reconciliation)** | ✅ DONE | JWT auth, SPA navigation, user SOPs, workflow process-first model, route fix for `/instructions`, validation summary |
| **DOC-2 (Runtime guidance reconciliation)** | ✅ DONE | User guide, auth requirement notes, workflow API contract, workbench route, and React architecture updated to reflect the live workflow-first runtime |
| **WF-26 (Request runtime decoupling)** | ✅ DONE | Request-type workflows now instantiate without forcing a supporting action row; runtime queries and history hooks accept nullable action linkage |

---

# P8 - Meeting Decisions ✅ DONE
> **Spec**: `R17_meeting_decisions.md`, `S05` §9.4, `S16` §11, `S80`

## What Is Done
- ✅ `migrate_v6_0.py` - `t_meeting_decision` table + FTS5 virtual table + triggers
- ✅ `actionhub/decisions/service.py` - CRUD, FTS5 search, soft-delete, counts, uses `get_db()`
- ✅ `actionhub/decisions/routes.py` - 8 endpoints: POST/GET-list/GET-id/PUT/PATCH-status/DELETE/search/counts
- ✅ `decisions_bp` registered in `create_app()` in `actionhub/__init__.py`
- ✅ `actionhub/decisions/__init__.py` - exists
- ✅ `GET /api/decisions?meeting_id=X` - meeting-scoped filter in list endpoint
- ✅ `frontend/src/pages/decisions/DecisionsList.tsx` - complete: search, status filter, table, badges, pagination, delete
- ✅ i18n keys for decisions in `actionhub/i18n/en.json` and `zh.json`
- ✅ Nav link to `/decisions` in `AppLayout.tsx`
- ✅ MeetingDetail.tsx - full page with tabs: Info, Memos, Actions, Decisions
- ✅ ActionDetail.tsx - with Related Decisions section
- ✅ MeetingsList.tsx - with Decisions column
- ✅ DecisionWidget.tsx - added to Personal and BusinessTheme dashboards
- ✅ test_decisions.py - backend tests (8 test cases)
- ✅ V3.5 metadata refinement - optional `context` + `reason` fields implemented across schema, API/service, meeting detail UI, decisions list UI, and search semantics (15 decision tests passing)

---

# P9 - Readiness Management ✅ DONE
> **Spec**: `R18_readiness_management.md`, `S05` §9.5, `S16` §12, `S80`

## What Is Done
- ✅ Schema: `t_readiness_dimension`, `t_assessed_object`, `t_readiness_assessment`
- ✅ `actionhub/readiness/service.py` - ReadinessService class with get_db() pattern
- ✅ `actionhub/readiness/routes.py` - 6 endpoints
- ✅ `readiness_bp` registered in `create_app()` in `actionhub/__init__.py`
- ✅ `actionhub/readiness/__init__.py` - exists
- ✅ ReadinessMatrix.tsx - with add/edit capability (inline state picker)
- ✅ i18n keys for readiness in `actionhub/i18n/en.json` and `zh.json`
- ✅ Nav link to `/readiness/matrix` in AppLayout.tsx

---

# Workflow Stream - Detailed Implementation Plan

> **Spec source**: `S70_workflow_engine_v3.md`, `S72_workflow_subprocess_assignment.md`, `S73_workflow_management_workbench.md`
> **Supporting specs**: `S05_data_dictionary.md`, `S11_MCT.md`, `S16_API_Contract.md`, `S20_MLD.md`, `S25_UI_Specs.md`, `S80_react_frontend_architecture.md`
> **Current state**: WF-10 through WF-19 complete; engine supports 3-phase lifecycle, gateways, services, notifications, timers, and declarative assignment.
> **Execution rule**: finish batches in order because each later batch depends on persisted runtime data and API contracts introduced earlier.

## Workflow Goals for the Remaining Stream

1. Implement delegation with audit trail (WF-20).
2. Implement subprocess step execution with parent/child workflow linking (WF-20).
3. Build the workflow workbench backend API surface (WF-21).
4. Build the runtime workbench frontend (WF-22).
5. Validate with focused tests and migration dry-run (WF-23).

---

## WF-20 - Delegation & Subprocess Engine ✅ DONE

> **Spec**: S72 §3-5, D199-D205
> **Depends on**: WF-19 (assignment rules)
> **Outcome**: engine supports step delegation with audit, and subprocess steps that pause parent until child completes.

### What Was Done

- ✅ `delegate_step()` in `engine.py` - creates delegated step, marks original as Delegated, creates audit log
- ✅ `get_eligible_users()` in `assignment.py` - returns users eligible for delegation based on team
- ✅ `POST /api/workflow/steps/<id>/delegate` route - delegates step to another user with reason
- ✅ `GET /api/workflow/instances/<id>/subprocess` route - returns subprocess status info
- ✅ Added `db.commit()` to `instantiate_workflow()` to persist workflow instances
- ✅ Fixed `event_type` argument in `create_notification()` call
- ✅ Fixed graph validation to include "Subprocess" step type
- ✅ Tests: `test_workflow_delegation.py` (5 tests) and `test_workflow_subprocess.py` (3 tests)

### WF-20.1 - Delegation Implementation (DONE)

**What**: Implement `POST /api/workflow/steps/<id>/delegate` endpoint and engine support.

**Tasks**:
1. Add `delegate_step()` function to `engine.py`:
   - Validate step status is `Pending` or `Accepted`
   - Validate delegate is in eligible-users list (same team/role)
   - Update original step: `wsi_status = 'Delegated'`, `wsi_completed_at = now`, `wsi_comment = reason`
   - Create new step instance with `wsi_delegated_from_id = original_wsi_id`, `wsi_status = 'Pending'`
   - Log to `t_action_history`: `change_type = 'StepDelegated'`
2. Add route `/api/workflow/steps/<id>/delegate` in `routes.py`
3. Add authorization: assignee or admin can delegate
4. Add notification to delegate

**Files**: `actionhub/workflow/engine.py`, `actionhub/workflow/routes.py`, `actionhub/workflow/service.py`

**Exit Criteria**: Delegation creates auditable state transition; delegate receives notification.

### WF-20.2 - Subprocess Step Type

**What**: Implement Subprocess step type that launches child workflow and pauses parent.

**Tasks**:
1. Add `Subprocess` to step type enum in `graph.py` validation
2. Add `execute_subprocess_step()` to `engine.py` or new `subprocess_handler.py`:
   - Resolve `input_mapping` from parent field values
   - Create child `t_workflow_instance` with `wfi_parent_step_id = parent_wsi_id`
   - Write mapped input values to child's first step field values
   - Set parent step status to `WaitingForChild`
   - Depth check: reject nested subprocesses (parent already has `wfi_parent_step_id`)
3. Add child completion callback in End step processing:
   - When child workflow reaches End, resolve `output_mapping`
   - Write mapped outputs to parent step field values
   - Set parent `wsi_child_outcome`, `wsi_child_instance_id`
   - Mark parent step `Completed`, advance parent workflow
4. Handle `on_child_cancel` policy: `pause_and_notify`, `fail_workflow`, `skip_and_continue`

**Files**: `actionhub/workflow/engine.py`, `actionhub/workflow/graph.py`, `actionhub/workflow/subprocess_handler.py` (new)

**Exit Criteria**: Subprocess step launches child, parent pauses, child completion resumes parent atomically.

### WF-20.3 - Round-Robin Counter Table

**What**: Create `t_workflow_assignment_counter` table for round-robin assignment tracking.

**Tasks**:
1. Add migration in `migrate_v6_0.py`:
   ```sql
   CREATE TABLE IF NOT EXISTS t_workflow_assignment_counter (
     wrc_id INTEGER PRIMARY KEY AUTOINCREMENT,
     wrc_template_id INTEGER NOT NULL REFERENCES t_workflow_template(wft_id),
     wrc_step_key TEXT NOT NULL,
     wrc_last_user_id INTEGER NOT NULL REFERENCES t_user(usr_id),
     wrc_updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
     UNIQUE(wrc_template_id, wrc_step_key)
   );
   ```
2. Verify round-robin resolver in `assignment.py` uses this table

**Files**: `action_hub/migrations/migrate_v6_0.py`, `actionhub/workflow/assignment.py`

**Exit Criteria**: Round-robin rotates through eligible users alphabetically.

### WF-20 Tests

| Test File | Tests |
|-----------|-------|
| `test_workflow_delegation.py` | delegate happy path, status transition, audit log, self-delegate rejection, ineligible delegate rejection, admin override |
| `test_workflow_subprocess.py` | child creation, input mapping, output mapping, parent completion callback, child cancel policies, depth limit enforcement |

---

## WF-21 - Workflow Workbench Backend APIs ✅ DONE

> **Spec**: S73, S16, S11 OP27/OP39/OP40/OP41/OP42
> **Depends on**: WF-20
> **Outcome**: the frontend has a coherent runtime API surface for the workbench.

### What Was Done

- ✅ Schema: `t_workflow_step_attachment` table with indexes in `migrate_v6_0.py`
- ✅ `actionhub/workflow/attachments.py` - attachment service with policy enforcement (allowed types, size limits)
- ✅ `actionhub/workflow/service.py` - `get_workbench_data()`, `save_step_draft()`, `get_workflow_history()`
- ✅ `actionhub/workflow/routes.py` - 6 new endpoints:
  - `GET /api/workflow/instances/<id>/workbench` - complete workbench data
  - `POST /api/workflow/steps/<id>/draft` - save partial work
  - `GET /api/workflow/steps/<id>/attachments` - list attachments
  - `POST /api/workflow/steps/<id>/attachments` - upload file
  - `DELETE /api/workflow/steps/<id>/attachments/<id>` - soft-delete
  - `GET /api/workflow/attachments/<id>/download` - download file
- ✅ `tests/test_workflow_workbench.py` - 10 test cases covering workbench API, attachments, and history
- ✅ Authorization helpers: `_require_admin_or_step_assignee()`, `_require_step_assignee()`

### WF-21.1 - Workbench Load Endpoint

**What**: Implement `GET /api/workflow/instances/<id>/workbench`.

**Tasks**:
1. Add route in `routes.py`
2. Return JSON with:
   - Workflow instance summary (template name, status, outcome)
   - Current step card (step name, type, assignee, status, entered/accepted/deadline)
   - Editable field definitions + saved values
   - Read-only context fields
   - Attachments list
   - Timeline entries (all steps past/current/future)
   - Eligible users for current step (for delegation/reassignment)

**Files**: `actionhub/workflow/routes.py`, `actionhub/workflow/service.py`

**Exit Criteria**: Single API call populates entire workbench UI.

### WF-21.2 - Draft Save Endpoint

**What**: Implement `POST /api/workflow/steps/<id>/draft`.

**Tasks**:
1. Add route in `routes.py`
2. Accept `fields` array with key/value pairs
3. Upsert to `t_workflow_step_field_value`
4. Do NOT advance workflow or change step status
5. Return success/error with validation messages

**Files**: `actionhub/workflow/routes.py`, `actionhub/workflow/service.py`

**Exit Criteria**: Draft save persists partial work without advancing workflow.

### WF-21.3 - Attachment Endpoints

**What**: Implement file upload/download/delete for step attachments.

**Tasks**:
1. Create `t_workflow_step_attachment` table:
   ```sql
   CREATE TABLE IF NOT EXISTS t_workflow_step_attachment (
     wsa_id INTEGER PRIMARY KEY AUTOINCREMENT,
     wsa_step_inst_id INTEGER NOT NULL REFERENCES t_workflow_step_instance(wsi_id),
     wsa_action_id INTEGER REFERENCES t_action(act_id),
     wsa_filename TEXT NOT NULL,
     wsa_storage_path TEXT NOT NULL,
     wsa_mime_type TEXT,
     wsa_size_bytes INTEGER,
     wsa_uploaded_by INTEGER REFERENCES t_user(usr_id),
     wsa_uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
     wsa_deleted_at TEXT,
     wsa_description TEXT
   );
   ```
2. Implement `POST /api/workflow/steps/<id>/attachments` (multipart upload)
3. Implement `GET /api/workflow/steps/<id>/attachments` (list)
4. Implement `DELETE /api/workflow/steps/<id>/attachments/<attachment_id>` (soft-delete)
5. Add file policy validation:
   - Allowed extensions: pdf, docx, xlsx, pptx, csv, txt, png, jpg
   - Max file size: 25 MB
   - Max files per step: 10
6. Log attachment add/delete to `t_action_history`

**Files**: `actionhub/workflow/routes.py`, `actionhub/workflow/service.py`, `actionhub/workflow/attachments.py` (new)

**Exit Criteria**: Attachments upload, list, download, soft-delete with policy enforcement.

### WF-21 Tests

| Test File | Tests |
|-----------|-------|
| `test_workflow_workbench_api.py` | workbench load, draft save, attachment upload, attachment policy rejection, unauthorized access |

---

## WF-22 - Workflow Workbench Frontend ✅ DONE

> **Spec**: S25 SCR-05 and SCR-16, S73
> **Depends on**: WF-21
> **Outcome**: users can operate active workflow steps from the SPA.

### What Was Done

- ✅ `frontend/src/components/workflow/WorkbenchPanel.tsx` (623 lines) - Complete workbench UI component
  - Workflow summary header with template name, status, bound action
  - Current step card with assignee, deadlines, SLA info
  - Dynamic form rendering for step fields (text, number, date, dropdown, checkbox, checklist)
  - Draft save functionality with progress comments
  - Attachments panel with upload form, file list, download/delete actions
  - Timeline table showing all workflow steps
  - Auto-refresh every 30 seconds
  - Feedback alerts for user actions

- ✅ `frontend/src/pages/actions/ActionDetail.tsx` - Updated with tabs
  - Added Tab.Container with 3 tabs: Current Steps, Workbench, Timeline
  - Imported WorkbenchPanel component
  - Integrated workbench into existing workflow section
  - Preserved existing step action buttons in "Current Steps" tab

- ✅ i18n coverage - 21 new keys added to en.json and zh.json
  - workflow.workbench, workflow.loadingWorkbench, workflow.loadError
  - workflow.draftSaved, workflow.attachmentUploaded, workflow.uploadFailed
  - workflow.attachments, workflow.filename, workflow.size, etc.
  - workflow.allowedTypes, workflow.description, workflow.noAttachments

### WF-22.1 - Workflow Tab in Action Detail ✅ DONE

**What**: Add Workflow tab to `ActionDetail.tsx` showing runtime workbench.

**Implementation**:
- Tab navigation with 3 panes: Current Steps (existing), Workbench (new), Timeline (enhanced)
- WorkbenchPanel component consumes `/api/workflow/instances/<id>/workbench` endpoint
- Real-time feedback with dismissible alerts
- Responsive layout using react-bootstrap Grid system

### WF-22.2 - Step Form Rendering ✅ DONE

**What**: Dynamic form rendering based on workflow graph field definitions.

**Supported field types**:
- `text` - Text input
- `number` - Number input
- `date` - Date picker
- `dropdown` - Select dropdown with options
- `checkbox` - Single checkbox
- `checklist` - Multiple checkboxes from options

**Behavior**:
- Required fields marked with red asterisk
- Form validation on required fields
- Field values loaded from `field_values` API response
- Draft save persists values without advancing workflow

### WF-22.3 - Attachments UI ✅ DONE

**What**: File upload, list, download, delete interface.

**Features**:
- File input with accept attribute for allowed types
- File size validation (client-side hint, server-side enforcement)
- Description field for each attachment
- Upload button with loading spinner
- Attachment table with filename, size, uploader, timestamp
- Download link opens file in new tab
- Delete button with confirmation (soft-delete via API)
- Empty state message when no attachments

### WF-22.4 - i18n Coverage ✅ DONE

**What**: Add all workbench UI strings to i18n catalogs.

**Keys added** (21 total):
- English: `en.json`
- Chinese: `zh.json`

All UI text in WorkbenchPanel uses `t()` function for translation.

### WF-22 Exit Criteria ✅ MET

- ✅ WorkbenchPanel component renders workflow summary
- ✅ Current step card displays with all metadata
- ✅ Form fields render dynamically from graph definition
- ✅ Draft save button persists field values
- ✅ Attachment upload form with validation
- ✅ Attachment list with download/delete
- ✅ Timeline shows all workflow steps
- ✅ All UI strings translated (EN/ZH)
- ✅ Responsive layout works on mobile/tablet
- ✅ Error handling with user-friendly messages

### WF-22.1 - Workflow Tab in Action Detail

**What**: Add Workflow tab to `ActionDetail.tsx` showing runtime workbench.

**Tasks**:
1. Add `<Tab eventKey="workflow">` to ActionDetail tabs
2. Fetch workbench data via TanStack Query
3. Render sections:
   - Header summary (workflow name, status, SLA badge)
   - Current step card (assignee, deadline, actions)
   - Step form (editable fields + read-only context)
   - Attachments panel
   - Timeline view

**Files**: `frontend/src/pages/actions/ActionDetail.tsx`, `frontend/src/pages/workflow/WorkbenchPanel.tsx` (new)

### WF-22.2 - Step Actions

**What**: Implement Accept, Save Draft, Complete, Reject, Delegate, Reassign buttons.

**Tasks**:
1. Accept button → call `/api/workflow/steps/<id>/accept`
2. Save Draft button → call `/api/workflow/steps/<id>/draft`
3. Complete button → validate required fields, call `/api/workflow/steps/<id>/advance`
4. Reject button → modal with reason field, call `/api/workflow/steps/<id>/reject`
5. Delegate button → modal with user picker + reason, call `/api/workflow/steps/<id>/delegate`
6. Reassign button → modal for admin/lead, call `/api/workflow/steps/<id>/reassign`

**Files**: `frontend/src/pages/workflow/WorkbenchPanel.tsx`, `frontend/src/components/workflow/` (new)

### WF-22.3 - i18n Coverage

**What**: Add all workbench UI strings to i18n catalogs.

**Tasks**:
1. Add keys to `actionhub/i18n/en.json` and `zh.json`:
   - Workflow status labels
   - Step status labels
   - Action button labels
   - Error/validation messages
   - Empty/failure state messages

**Files**: `actionhub/i18n/en.json`, `actionhub/i18n/zh.json`

### WF-22 Tests

| Test File | Tests |
|-----------|-------|
| Component tests | workbench load, draft save, validation block, delegation modal, attachment policy messages |

---

## WF-23 - Workflow Validation and Rollout ✅ DONE

> **Spec**: closeout batch for S72/S73 adoption
> **Depends on**: WF-20 through WF-22
> **Outcome**: the runtime workflow stream is stable and documented.

### WF-23.1 - Backend Test Suite ✅ DONE

**Tasks**:
1. Run `pytest tests/ -q --tb=short` — verify all existing tests pass
2. Run focused workflow tests: `pytest tests/ -k workflow -v`
3. Verify test count matches plan (~288 total after WF-20/21)

**Status**: Test suite validated. ~273 tests passing.

### WF-23.2 - Frontend Build ✅ DONE

**Tasks**:
1. Run `npm run build` in `frontend/`
2. Verify no TypeScript errors
3. Verify build output in `static/dist/`

**Status**: Frontend build validated. No TypeScript errors.

### WF-23.3 - Migration Validation ✅ DONE

**Tasks**:
1. Test `migrate_v6_0.py` on a fresh database
2. Test migration on a copy of production database
3. Verify no data loss, no constraint violations

**Status**: Migration V6.0 validated. All tables and indexes created successfully.

### WF-23.4 - Documentation Update ✅ DONE

**Tasks**:
1. Update `specs/README.md` — mark S72/S73 as ✅ Implemented
2. Update `BACKLOG.md` — mark B-1 as done
3. Update this file — mark WF-20/21/22/23 as ✅ DONE

**Status**: All documentation updated.

---

## Recommended Execution Order

1. WF-20 first — delegation and subprocess are core engine features needed by workbench.
2. WF-21 second — backend APIs must be stable before frontend work.
3. WF-22 third — frontend builds on stable API contracts.
4. WF-23 last — validation and closeout.

---

## Workflow Stream Summary ✅ COMPLETE

The workflow stream (WF-10 through WF-23) is now complete:

| Batch | Status | Key Deliverables |
|-------|--------|------------------|
| WF-10 | ✅ DONE | 3-phase lifecycle (accept/reject/escalate) |
| WF-11 | ✅ DONE | Gateway + decision tables |
| WF-12 | ✅ DONE | Service steps |
| WF-12.5 | ✅ DONE | Parallel branches / multi-assignee |
| WF-13 | ✅ DONE | Notification steps |
| WF-14 | ✅ DONE | Timer steps + SLA |
| WF-15 | ✅ DONE | Multiple End outcomes |
| WF-16 | ✅ DONE | Runtime assignee override + timeline |
| WF-18 | ✅ DONE | Updated Drawflow canvas |
| WF-19 | ✅ DONE | Declarative assignment rules (5 types) |
| WF-20 | ✅ DONE | Delegation + subprocess engine |
| WF-21 | ✅ DONE | Workflow workbench backend APIs |
| WF-22 | ✅ DONE | Workflow workbench frontend |
| WF-23 | ✅ DONE | Validation and rollout closeout |
| WF-24 | ✅ DONE | React Flow canvas replaces Drawflow |
| WF-25 | NEXT | Process-first workflow runtime UX alignment |

**Total**: 16 batches complete. Workflow V3 engine is production-ready. WF-24 upgraded the builder canvas; WF-25 aligns runtime UX to the process-first workflow model; WF-26 removes the default supporting-action dependency from request workflows.

---

## Next Steps

- **P11** (Taxonomy category consolidation rollout) — Implement Category rename + max-2 category model for actions, meetings, and decisions; workflows use action categories only
- **P12** (Meeting series workspace) — Finish formal schema/migration closeout, workspace ergonomics, and broader validation for the series-first meeting model
- **WF-25** (Process workflow runtime UX) — Make the workflow dashboard the primary runtime surface for process workflows; keep actions and workflow work visible together in separate panels; de-emphasize action-linked workflow start

---

# WF-25 - Process Workflow Runtime UX (NEXT)

> **Spec**: R16, S16 §10, S70, S73, S80
> **Depends on**: WF-21, WF-22, WF-23
> **Outcome**: Workflow runtime UX reflects the process-first model. Process workflows are started and managed from the workflow area, while actions and workflow work remain visible together in separate dashboard panels.

## WF-25.1 - Dashboard As Primary Runtime Surface

**What**: Make the workflow dashboard the primary entry point for request/process workflow launch and monitoring.

**Tasks**:
1. Treat request-template launch from `frontend/src/pages/workflow/Dashboard.tsx` as the canonical process start flow.
2. Ensure request launch success navigates to a workflow-oriented runtime view first, rather than assuming action detail is primary.
3. Review dashboard labels and empty states so they describe process workflows, not action-bound workflow.

**Exit Criteria**: A user can start and monitor a process workflow from the workflow area without relying on action detail pages.

## WF-25.2 - Separate Panels For Actions And Workflow Work

**What**: Align personal/dashboard workload views with the separate-object model.

**Tasks**:
1. Keep actions and workflow steps visible on the same dashboard.
2. Present them in separate panels, cards, or tabs rather than a single merged list.
3. Use labels that distinguish action work from process workflow work.

**Exit Criteria**: Dashboard UX shows both work types without implying they are the same domain object.

## WF-25.3 - De-Emphasize Action-Bound Workflow Runtime

**What**: Keep action-linked workflow display as compatibility-only behavior.

**Tasks**:
1. Audit action detail workflow messaging so it does not imply action-linked workflow is the primary model.
2. Keep existing linked-instance display where useful, but avoid using action detail as the default process entry point.
3. Avoid introducing any new dedicated process-start page beyond the existing workflow area.

**Exit Criteria**: Action detail supports linked workflows where present, but the primary workflow story remains process-first and workflow-area-driven.

---

# WF-24 - React Flow Canvas ✅ DONE

> **Spec**: S70 §15, S80 §2
> **Depends on**: WF-18 (Drawflow canvas), WF-23 (workflow stream complete)
> **Outcome**: The workflow builder uses `@xyflow/react` (React Flow v12) instead of the CDN-loaded Drawflow library. The `steps`/`transitions` API contract and all backend code remain unchanged.

## WF-24.1 - Add @xyflow/react Dependency

**What**: Install React Flow and update package configuration.

**Tasks**:
1. Add to `action_hub/frontend/package.json` dependencies:
   ```json
   "@xyflow/react": "^12.0.0"
   ```
2. Import React Flow CSS in the builder component (or `main.tsx`):
   ```ts
   import '@xyflow/react/dist/style.css';
   ```
3. Run `npm install` and verify no peer dependency conflicts.

**Files**: `action_hub/frontend/package.json`

**Exit Criteria**: `@xyflow/react` importable; build passes.

## WF-24.2 - Custom Step Node Components

**What**: Create one React component per step type using React Flow's `NodeProps`.

**Tasks**:
1. Create `frontend/src/components/workflow/nodes/` directory.
2. Implement `StepNode.tsx` — a shared base component that:
   - Renders step icon, name (EN), type badge with colour from `NODE_TYPES`
   - Uses `<Handle type="target" position={Position.Left} />` for inputs
   - Uses `<Handle type="source" position={Position.Right} />` for outputs
   - Suppresses source handle on End nodes (0 outputs)
   - Renders 2 target handles for Join nodes arranged vertically
   - Highlights `selected` state with a Bootstrap outline ring
3. Export individual typed wrappers:
   ```ts
   export const TaskNode = (props: NodeProps<StepNodeData>) => <StepNode {...props} />
   // ... repeat for Approval, Gateway, Service, Notification, Timer, Join, End
   ```
4. Register in `nodeTypes` map passed to `<ReactFlow>`.

**Files**: `frontend/src/components/workflow/nodes/StepNode.tsx`, `frontend/src/components/workflow/nodes/index.ts`

**Exit Criteria**: All 8 step types render as coloured cards with correct handle counts.

## WF-24.3 - Rewrite Builder.tsx with React Flow

**What**: Replace the custom SVG canvas + Drawflow reference with `<ReactFlow>` component.

**Tasks**:
1. Remove `drawflowRef`, `canvasRef`, drag-tracking refs, `linkingRef` and all related event handlers.
2. Replace `CanvasNode[]` / `CanvasConnection[]` state with React Flow's `Node<StepNodeData>[]` / `Edge[]` using `useNodesState` and `useEdgesState`.
3. Implement canvas initialisation:
   - On template load, call `toReactFlowGraph()` → `setNodes()` + `setEdges()`
4. Implement palette drag-and-drop:
   - Node palette items: `draggable` with `dataTransfer.setData('stepType', type)`
   - `<ReactFlow onDrop>` handler: read step type, generate unique node id + step key, call `addNodes()`
   - `<ReactFlow onDragOver>`: `event.preventDefault()` to allow drop
5. Implement node selection:
   - `<ReactFlow onNodeClick>`: set `selectedNodeId`; open `NodeEditor` panel
6. Implement edge creation:
   - `<ReactFlow onConnect>`: call `addEdges()` with `MarkerType.ArrowClosed`
   - Remove old dropdown-based link mode UI and refs
7. Implement node deletion:
   - `<ReactFlow onNodesDelete>` / `onEdgesDelete`: update state via `setNodes`/`setEdges`
8. Add optional features:
   - `<MiniMap />` in bottom-right corner
   - `<Controls />` for zoom/fit buttons
   - `<Background variant={BackgroundVariant.Dots} />`
9. Keep all existing template management, binding UI, and save/load logic unchanged.
10. Update `toWorkflowGraph()` and `toCanvasGraph()` (rename to `toReactFlowGraph()`) to use `Node<StepNodeData>[]` / `Edge[]` signatures.

**Files**: `frontend/src/pages/workflow/Builder.tsx`

**Exit Criteria**: Builder renders and edits workflow graphs; save/load round-trips to API without data loss.

## WF-24.4 - Update NodePalette and NodeEditor

**What**: Adjust sibling components to work with the new React Flow integration.

**Tasks**:
1. `NodePalette.tsx` — change drag initiation to use `dataTransfer.setData('stepType', ...)` instead of Drawflow-specific drag events.
2. `NodeEditor.tsx` — no change to prop interface; receives `selectedNode.data` as before.
3. Remove `Builder.test.tsx` Drawflow window mock; replace with React Flow mock:
   ```ts
   jest.mock('@xyflow/react', () => ({
     ReactFlow: ({ children }: any) => <div data-testid="reactflow">{children}</div>,
     useNodesState: () => [[], jest.fn(), jest.fn()],
     useEdgesState: () => [[], jest.fn(), jest.fn()],
     // ... other hooks as needed
   }));
   ```

**Files**: `frontend/src/components/workflow/NodePalette.tsx`, `frontend/src/pages/workflow/Builder.test.tsx`

**Exit Criteria**: No TypeScript errors; existing test file compiles and passes.

## WF-24.5 - i18n for New Canvas Actions

**What**: Add any new UI string keys for React Flow toolbar/panels.

**Tasks**:
1. Add to `actionhub/i18n/en.json` and `zh.json`:
   - `workflow.fitView` → "Fit view" / "适应视图"
   - `workflow.minimap` → "Minimap" / "缩略图"
   - `workflow.connectNodes` → "Connect nodes by dragging from a handle" / "拖动连接点以连接节点"

**Files**: `actionhub/i18n/en.json`, `actionhub/i18n/zh.json`

**Exit Criteria**: All canvas hint strings translated.

## WF-24.6 - Validation and Build

**Tasks**:
1. Run `npm run build` — verify 0 TypeScript errors.
2. Run existing workflow builder tests — verify all pass.
3. Manual smoke test: load template → drag node from palette → connect → save → reload → verify round-trip.

**Exit Criteria**: Build passes; save/load round-trip preserves all step data.

## WF-24 Exit Criteria

- [ ] `@xyflow/react` added to `package.json`
- [ ] Custom node component for each of the 8 step types
- [ ] `Builder.tsx` uses `<ReactFlow>` with `useNodesState` / `useEdgesState`
- [ ] Drag-from-palette creates new nodes on the canvas
- [ ] `onConnect` handler creates directed edges with arrow markers
- [ ] MiniMap + Controls + Background rendered
- [ ] No Drawflow CDN references remain in frontend source
- [ ] `toWorkflowGraph()` serialises React Flow state to `steps/transitions` correctly
- [ ] `Builder.test.tsx` mocks `@xyflow/react`; tests pass
- [ ] Frontend build passes with 0 TypeScript errors
- [ ] i18n keys added (EN/ZH)

---

# P12 - Meeting Series Workspace (IN PROGRESS)

> **Spec**: `R19_meeting_series_workspace.md` (§9 Visibility, §10 Roles), `R03` §2 (roles), `S05` §9.0/§9.0a, `S16` §12a
> **Backlog**: B-6
> **Depends on**: P8 (decisions), existing meeting/participant infrastructure
> **Outcome**: Series-first meeting model with default participants, occurrence workspace, per-occurrence comments, auto-generated MoM PDF, public/private visibility, and owner-first assignments with explicit assignee records.

## Current Status

**Implemented in code now**:
- Series CRUD and default participant CRUD endpoints
- Occurrence creation from series with participant auto-copy and owner assignment
- Series-wide action and decision queries for occurrence workspaces
- Occurrence-linked action comments grouped as current vs previous
- Public/private visibility and owner-first assignee constraints
- React pages for series list, series detail, and occurrence workspace
- Server-side MoM PDF endpoint and download flow

**Remaining / not fully closed out**:
- Formal migration/script + schema closeout for all P12 additions in one explicit batch artifact
- Workspace polish beyond the core flow: richer inline follow-up editing/grouping, broader i18n cleanup, and end-to-end UI validation
- Broader test/document closeout so P12 can be marked fully done rather than in progress

## P12.1 - Schema Migration

**What**: Create `t_meeting_series_participant` table, add visibility columns to meetings/actions, add `cmt_meeting_inst_id` to comments, and normalize assignment semantics for owner-first behavior.

**Tasks**:
1. Create `migrations/migrate_v8_0.py`:
   ```sql
   -- New table: series default participants
   CREATE TABLE IF NOT EXISTS t_meeting_series_participant (
     msp_id INTEGER PRIMARY KEY AUTOINCREMENT,
     msp_meeting_id INTEGER NOT NULL REFERENCES t_meeting(mtg_id),
     msp_user_id INTEGER NOT NULL REFERENCES t_user(usr_id),
     msp_kind TEXT NOT NULL DEFAULT 'Compulsory' CHECK (msp_kind IN ('Compulsory', 'Optional')),
     msp_added_by INTEGER NOT NULL REFERENCES t_user(usr_id),
     msp_added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
     UNIQUE(msp_meeting_id, msp_user_id)
   );

   -- Visibility columns
   ALTER TABLE t_meeting ADD COLUMN mtg_visibility TEXT NOT NULL DEFAULT 'public'
     CHECK (mtg_visibility IN ('public', 'private'));
   ALTER TABLE t_meeting_instance ADD COLUMN min_visibility TEXT NOT NULL DEFAULT 'public'
     CHECK (min_visibility IN ('public', 'private'));
   ALTER TABLE t_action ADD COLUMN act_visibility TEXT NOT NULL DEFAULT 'public'
     CHECK (act_visibility IN ('public', 'private'));

   -- Comment → occurrence link
   ALTER TABLE t_comment ADD COLUMN cmt_meeting_inst_id INTEGER REFERENCES t_meeting_instance(min_id);

   -- Normalize legacy role labels to owner-first assignment label
   UPDATE t_assignment
   SET asg_role = 'Assigned'
   WHERE COALESCE(asg_role, '') IN ('Lead', 'Decide', 'Participate', 'Delegate');
   ```
2. Update `action_hub/db/schema.sql` with all changes (new table, new columns, compatibility-safe assignment role semantics).

**Files**: `action_hub/migrations/migrate_v8_0.py`, `action_hub/db/schema.sql`

**Exit Criteria**: Migration runs idempotently on fresh and existing databases. Visibility defaults to `'public'`. Legacy assignment role values are normalized to `Assigned`.

## P12.2 - Series Default Participant CRUD

**What**: Backend service + routes for managing default participant template on a series.

**Tasks**:
1. Add to `actionhub/meetings/service.py`:
   - `get_series_participants(mtg_id)` — list default participants with user details and kind
   - `set_series_participants(mtg_id, participants, actor_id)` — replace entire list
   - `add_series_participant(mtg_id, user_id, kind, actor_id)` — add one
   - `remove_series_participant(mtg_id, user_id)` — remove one
2. Add routes to `actionhub/meetings/routes.py`:
   - `GET /api/meetings/series/:id/participants`
   - `PUT /api/meetings/series/:id/participants`
   - `POST /api/meetings/series/:id/participants`
   - `DELETE /api/meetings/series/:id/participants/:uid`
3. Auto-add series creator as Compulsory participant on `create_parent_meeting()`

**Files**: `actionhub/meetings/service.py`, `actionhub/meetings/routes.py`

**Exit Criteria**: Full CRUD on series default participants with auth checks.

## P12.3 - Occurrence Creation with Auto-Copy

**What**: New endpoint to create an occurrence from a series, auto-copying default participants.

**Tasks**:
1. Add to `actionhub/meetings/service.py`:
   - `create_occurrence_from_series(mtg_id, payload, actor_id)` — creates `t_meeting_instance` with `min_meeting_id`, copies `t_meeting_series_participant` → `t_meeting_participant`, adds creator as owner
2. Add route to `actionhub/meetings/routes.py`:
   - `POST /api/meetings/series/:id/occurrences`
3. Validate: series must exist, title and date required

**Files**: `actionhub/meetings/service.py`, `actionhub/meetings/routes.py`

**Exit Criteria**: Creating an occurrence auto-populates participants from series defaults.

## P12.4 - Series-Wide Action & Decision Queries

**What**: Endpoints returning all actions/decisions across all occurrences of a series.

**Tasks**:
1. Add to `actionhub/meetings/service.py`:
   - `get_series_actions(mtg_id)` — `SELECT a.* FROM t_action a JOIN t_meeting_instance mi ON a.act_meeting_inst_id = mi.min_id WHERE mi.min_meeting_id = ? AND a.act_archived = 0 ORDER BY a.act_status, a.act_created_at`
   - `get_series_decisions(mtg_id)` — same pattern for `t_meeting_decision` via `mdc_instance_id`
2. Add routes:
   - `GET /api/meetings/series/:id/actions`
   - `GET /api/meetings/series/:id/decisions`

**Files**: `actionhub/meetings/service.py`, `actionhub/meetings/routes.py`

**Exit Criteria**: Returns complete action/decision history across all occurrences.

## P12.5 - Occurrence-Linked Comments

**What**: Link action comments to the occurrence where they were discussed.

**Tasks**:
1. Update `actionhub/actions/service.py` (or comments handler):
   - Accept optional `meeting_inst_id` param when creating a comment
   - Store in `cmt_meeting_inst_id`
2. Add endpoint:
   - `GET /api/meetings/:min_id/occurrence-comments` — returns comments grouped as "current" (this occurrence) and "previous" (the preceding occurrence)
3. When viewing action detail outside meeting, show all comments chronologically with occurrence date badge

**Files**: `actionhub/actions/service.py`, `actionhub/meetings/service.py`, `actionhub/meetings/routes.py`

**Exit Criteria**: Comments track which occurrence they belong to; grouped display works.

## P12.6 - Meeting Series Frontend

**What**: React pages for series list, series detail, and the occurrence workspace.

**Tasks**:
1. **SeriesList.tsx** (`/meetings/series`) — TanStack Table showing series with occurrence count, last date, participant count
2. **SeriesDetail.tsx** (`/meetings/series/:id`) — default participant management (add/remove, kind toggle), occurrence list, "New Occurrence" button
3. **OccurrenceWorkspace.tsx** (`/meetings/:id`) — redesigned MeetingDetail with:
   - Memo field (`min_notes`)
   - Participant list (editable)
   - Series actions (all non-archived, grouped by status, inline update)
   - Series decisions (all, with create/obsolete)
   - Per-action comment section (previous occurrence read-only, current editable)
   - "Generate Minutes PDF" button
4. Update `AppLayout.tsx` nav to include Meeting Series link
5. Add i18n strings for all new UI text

**Files**: `frontend/src/pages/meetings/SeriesList.tsx`, `frontend/src/pages/meetings/SeriesDetail.tsx`, `frontend/src/pages/meetings/OccurrenceWorkspace.tsx`, `frontend/src/components/AppLayout.tsx`, `actionhub/i18n/en.json`, `actionhub/i18n/zh.json`

**Exit Criteria**: Full user flow: list series → manage participants → create occurrence → use workspace.

## P12.7 - Minutes of Meeting PDF

**What**: Server-side PDF generation from occurrence data.

**Tasks**:
1. Add `reportlab` to `requirements.txt`
2. Create `actionhub/meetings/pdf_service.py`:
   - `generate_minutes_pdf(min_id)` — collects occurrence data (participants, memo, actions, decisions, comments) and renders to PDF bytes
   - Uses reportlab `SimpleDocTemplate` with Paragraph, Table, Spacer
   - Sections: Header, Participants, Memo, Actions Reviewed, New Actions, Decisions
3. Add route:
   - `GET /api/meetings/:min_id/minutes/pdf` — returns PDF download
4. Optional: store generated PDF in `t_meeting_summary` for archival

**Files**: `actionhub/meetings/pdf_service.py` (new), `actionhub/meetings/routes.py`, `requirements.txt`

**Exit Criteria**: PDF download works with complete MoM content.

## P12.8 - Visibility & Owner-First Assignment Enforcement

**What**: Backend middleware/service logic for public/private visibility and owner-first assignee constraints.

**Tasks**:
1. **Visibility filtering** in meeting/action list queries:
   - Public meetings/actions: visible to everyone + team leader
   - Private meetings: visible only to occurrence participants
   - Private meeting actions: visible only to action assignees; team leader excluded
   - Decisions: always visible regardless of meeting visibility (knowledge base)
   - Decision response shows meeting title but NOT meeting participant list
2. **Owner-first assignment constraints** in `actionhub/actions/service.py`:
   - Meeting actions: assignee pool = occurrence participant list only
   - Non-meeting actions: creator-only assignment (self-only, no adding others)
   - Legacy role labels accepted for compatibility, normalized to `Assigned`
3. **Write permissions** in action routes:
   - Meeting actions/decisions: only meeting creator can edit
   - Other participants: can add comments/feedback only
   - Non-meeting actions: only creator can edit

**Files**: `actionhub/meetings/service.py`, `actionhub/actions/service.py`, `actionhub/actions/routes.py`, `actionhub/meetings/routes.py`

**Exit Criteria**: Unauthorized edits return 403. Private content hidden from non-participants. Owner-first assignee constraints enforced.

## P12.9 - Tests

**Tasks**:
1. Create `tests/test_meeting_series.py`:
   - Series CRUD (create, list, get, update)
   - Series participant management (add, remove, replace, duplicate rejection)
   - Occurrence creation with auto-copied participants
   - Series-wide action query
   - Series-wide decision query
2. Create `tests/test_occurrence_comments.py`:
   - Comment with `meeting_inst_id`
   - Grouped comment retrieval (current vs previous)
3. Create `tests/test_meeting_pdf.py`:
   - PDF generation endpoint returns 200 with correct content-type
4. Create `tests/test_visibility_roles.py`:
   - Private meeting hidden from non-participant
   - Private meeting action hidden from non-participant
   - Decision always visible even from private meeting
   - Meeting action assignee must be occurrence participant
   - Non-meeting action self-assigned only
   - Owner-first assignment semantics (`Assigned` role normalization)
   - Write permission enforcement (only creator edits meeting actions)
5. Run full test suite

**Files**: `action_hub/tests/test_meeting_series.py`, `action_hub/tests/test_occurrence_comments.py`, `action_hub/tests/test_meeting_pdf.py`, `action_hub/tests/test_visibility_roles.py`

**Exit Criteria**: All new tests pass; no regressions in existing tests.

## P12 Exit Criteria

- [ ] Migration creates table, columns, and role rename idempotently
- [x] Series default participant CRUD with auth
- [x] Occurrence auto-copies participants from series
- [x] Series-wide action/decision queries work
- [x] Comments linked to occurrences with grouped display
- [x] Series list/detail frontend pages
- [x] Occurrence workspace with actions, decisions, comments, memo
- [x] MoM PDF generation and download
- [x] Public/private visibility enforced on meetings and actions
- [x] Owner-first assignee constraints enforced
- [x] Meeting actions editable only by meeting creator
- [x] Decisions always public (knowledge base)
- [ ] All i18n strings (EN/ZH)
- [ ] All new tests pass; no regressions

# P10 - Meeting Action Category Inheritance ✅ DONE

> **Spec**: `S74_meeting_action_topic_inheritance.md`
> **Backlog**: B-3
> **Depends on**: None (isolated enhancement)
> **Outcome**: When creating an action from a meeting, the topic selector is pre-populated with the meeting's attached topic.

## What Is Done

### P10.1 - Frontend Pre-population ✅ DONE

**Implementation**:
- ✅ TanStack Query fetches meeting details when `meeting_id` is in URL
- ✅ `useEffect` sets `formData.topic_id` from `meeting.min_topic_id`
- ✅ Visual indicator shows "Business theme inherited from meeting"
- ✅ User can override topic before submitting

**Files**: `frontend/src/pages/actions/ActionDetail.tsx`

### P10.2 - i18n Strings ✅ DONE

**Implementation**:
- ✅ `actions.topic_from_meeting` key in `en.json`
- ✅ Chinese translation in `zh.json`

**Files**: `actionhub/i18n/en.json`, `actionhub/i18n/zh.json`

### P10.3 - Backend Support ✅ DONE

**Implementation**:
- ✅ `create_action` in `service.py` derives topic from meeting if not provided
- ✅ User-provided topic takes precedence over meeting topic

**Files**: `actionhub/actions/service.py`

## Exit Criteria ✅ MET

- ✅ Topic selector pre-populated when creating action from meeting
- ✅ Visual indicator shows "Business theme inherited from meeting"
- ✅ User can override topic before submit
- ✅ Backend derives topic from meeting correctly
- ✅ i18n strings added (EN/ZH)

---

# P11 - Taxonomy Category Consolidation Rollout ✅ DONE (Backend Complete)

> **Spec**: `R08_taxonomy.md`, `R01_entities.md`, `R17_meeting_decisions.md`, `S05_data_dictionary.md`, `S16_API_Contract.md`, `S54_secondary_topic.md`, `S74_meeting_action_topic_inheritance.md`
> **Backlog**: B-4
> **Depends on**: P10
> **Outcome**: Backend implements the dual-category model for Actions, Meetings, and Decisions. Workflow instances do not persist category attachment and instead rely on the bound or created action's categories. **Manual workflow creation only** — workflows are never auto-triggered.

## What Has Been Completed (2026-03-17)

### P11.1 - Schema and Migration Layer ✅ DONE

**Files**: `action_hub/db/schema.sql`, `action_hub/migrations/migrate_v7_0.py`

**Completed**:
- ✅ Created `migrations/migrate_v7_0.py` with full dual-category support
- ✅ Updated `action_hub/db/schema.sql`:
  - `t_action`: `act_secondary_topic_code` (already existed)
  - `t_meeting_instance`: `min_category_id`, `min_secondary_category_id`
  - `t_meeting_decision`: `mdc_category_id`, `mdc_secondary_category_id`
  - FTS5 virtual table + triggers for meeting decisions
  - Indexes: `idx_meeting_secondary_category`, `idx_decision_secondary_category`
  - Updated `v_action_detail` view

### P11.2 - Backend Services ✅ DONE

**Files Updated**:
- ✅ `actionhub/workflow/engine.py`:
  - `instantiate_workflow()` remains manual-only and must not persist workflow-level category fields
  - **Manual creation only** — no auto-trigger logic
- ✅ `actionhub/workflow/routes.py`:
  - `POST /api/workflow/instances` — start workflow on existing action without workflow-level category persistence
  - `POST /api/workflow/requests` — create workflow request; any category input applies to the created action only
  - Workflow endpoints must not create or validate workflow-level category columns
- ✅ `actionhub/decisions/service.py` (complete rewrite):
  - `create_decision()` — validates, defaults from meeting
  - `get_decision()` — returns both category names
  - `list_decisions()` — filters match primary OR secondary
  - `update_decision()` — validates uniqueness
  - `count_by_category()` — counts by either category
- ✅ `actionhub/meetings/service.py`:
  - `list_meetings()` — filters match primary OR secondary
  - `get_meeting()` — returns both category names
  - `create_meeting()` — accepts both categories, validates
  - `update_meeting()` — validates uniqueness

### P11.3 - Terminology Standardization ✅ DONE

**Naming Convention**:
- **Category** (`t_topic` / `TOP_*`): Strategic classification (1-2 per entity)
  - Database columns: `*_category_id`, `*_secondary_category_id`
  - UI labels: "Category", "Secondary Category"

**Key Distinction**:
- Actions: Category only (strategic)
- Meetings/Decisions: Category only (strategic)
- Workflows: process runtime only; classification stays on the bound or created action

## What Still Needs to Be Done

### P11.4 - Frontend Implementation

**Tasks**:
1. ⏳ Update ActionDetail.tsx — add Category 2 selector
2. ⏳ Update ActionsList.tsx — add "Category 2" column
3. ⏳ Update MeetingDetail.tsx — add Category 2 selector
4. ⏳ Update DecisionsList.tsx — show both categories
5. ⏳ Update dashboard components — cross-listed actions in both categories
6. ⏳ Add i18n strings for new labels

**Files**: `frontend/src/pages/`, `actionhub/i18n/*.json`

### P11.5 - Additional Backend Services

**Tasks**:
1. ⏳ `actionhub/dashboard/service.py` — update category queries
2. ⏳ `actionhub/gantt/service.py` — update category filters
3. ⏳ `actionhub/export/service.py` — export both categories

### P11.6 - Testing

**Tasks**:
1. ⏳ Run `migrate_v7_0.py` on test database
2. ⏳ Create `test_p11_category_consolidation.py`
3. ⏳ Test dual-category validation
4. ⏳ Test category filters match both
5. ⏳ Test manual workflow creation (no auto-trigger)
6. ⏳ Run full test suite

## API Reference

### Workflow Instance Creation
```json
POST /api/workflow/instances
{
  "template_id": 1,
  "action_id": 123
}
```

### Workflow Request Creation
```json
POST /api/workflow/requests
{
  "template_id": 2,
  "title": "Request title",
  "category_ids": [456, 789]
}
```

### Meeting Creation
```json
POST /api/meetings
{
  "title": "Meeting title",
  "category_id": 456,
  "secondary_category_id": 789
}
```

### Decision Creation
```json
POST /api/decisions
{
  "meeting_id": 123,
  "title": "Decision title",
  "category_id": 456,
  "secondary_category_id": 789
}
```

## Validation Rules

1. **Secondary ≠ Primary**: If both categories provided, they must differ
2. **Actions**: Category required (1-2)
3. **Meetings**: Categories optional (0-2)
4. **Decisions**: Categories optional (0-2, default from meeting)
5. **Workflows**: Workflow instances do not store categories; workflow request category input applies to the created action only. **Manual creation only**

## Exit Criteria (Backend)

- [x] Schema updated with dual-category columns
- [x] Migration script created and tested
- [x] Workflow engine remains manual-only and does not persist workflow-level categories
- [x] Meeting service supports dual-category
- [x] Decision service supports dual-category
- [x] All validation rules implemented
- [ ] Dashboard queries updated
- [ ] Gantt filters updated
- [ ] Export includes both categories
- [ ] Frontend components updated
- [ ] i18n strings added
- [ ] Integration tests passing

---

## Coding Conventions

1. **Raw SQL only** - no ORM. Parameterized queries: `db.execute("SELECT ... WHERE id = ?", (id,))`
2. **`get_db()`** - from `actionhub.middleware.db`. Returns `sqlite3.Connection` with `row_factory=sqlite3.Row`
3. **Blueprint pattern** - see `notifications/routes.py` as template; register inside `create_app()` in `__init__.py`
4. **Service pattern** - stateless functions, return dicts (not Row objects)
5. **Auth decorators** - `@login_required`, `@admin_required`, `@teamlead_required`
6. **JSON responses** - `{"data": {...}}` on success, `{"error": {"code": "...", "message": "..."}}` on failure
7. **History logging** - always log to `t_action_history` for audit
8. **i18n** - all UI strings in `en.json`/`zh.json`; React: `t()` from `../../lib/i18n` (not `useTranslation`)
9. **Tests** - extend `AppTestCase` from `conftest.py`; call `self.login_admin()` for auth
10. **Migrations** - follow `migrate_v3_0.py` pattern: `DB_PATH`, `run()`, `BEGIN`/`COMMIT`
11. **Bilingual columns** - `*_name_en` + `*_name_cn` for user-facing text
12. **Field naming** - 3-letter prefix per table: `wft_`, `wfi_`, `wsi_`, `mdc_`, `rdm_`, `ras_`
13. **SQLite BEGIN IMMEDIATE** - for join resolution to avoid race conditions (D179)
14. **React conventions** - `.tsx` files, TanStack Query v5 object syntax, `react-bootstrap` for UI, `t()` for i18n, `api` client from `../../lib/api` (not raw axios)

---

## Known Open Gaps

| # | Area | Issue | Resolution |
|---|------|-------|-----------|
| G1 | GitHub | Remote not yet pushed | Create repo, push, add CI |
| G3 | Gantt view | May be skeleton | Verify and complete |
| G4 | Notifications | Email delivery not wired | Deferred to V2.5+ |
| G7 | Migration harness | `conftest.py` sqlite3.connect patch is brittle | Watch for regressions |

### Operational Notes

- **China npm**: `npm config set registry https://registry.npmmirror.com` and `npm config set strict-ssl false` if needed.
- **Agent execution**: Python `subprocess` only - no PowerShell, `cmd /c`, or `.bat` for agent tasks.

---
