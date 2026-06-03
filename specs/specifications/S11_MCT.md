# ActionHub — Conceptual Process Model (MCT)

> **Level**: L1 — Conceptual  
> **Merise Phase**: Modèle Conceptuel des Traitements  
> **Source**: R02_action_lifecycle.md, R03_assignment_workflow.md, R06_security.md, R07_data_import.md  
> **Purpose**: Define **what** business operations exist, triggered by **what** events, without specifying who/where/when

---

## 1. Event–Operation Mapping

| Event | Operation | Success Result | Failure Result | Phase |
|-------|-----------|---------------|----------------|-------|
| User submits login credentials | OP01: Authenticate User | Session created, redirect to dashboard | Error: Invalid credentials / Lockout | MVP |
| Admin creates user account | OP02: Create User | User record created | Error: Duplicate username | MVP |
| User creates action (form, quick-capture, meeting, or topic) | OP03: Create Action | Action + Assignment created, ref generated; action linked to meeting or topic as appropriate | Validation error | MVP |
| User updates action fields | OP04: Update Action | Action updated, history logged | Validation error / Permission denied | MVP |
| User changes action status (inline or detail) | OP05: Transition Status | Status updated, side effects applied | Invalid transition / Missing required field | MVP |
| Lead assigns delegate to action | OP06: Assign User | Assignment created (auto-Accepted in MVP) | Validation error | MVP |
| User views personal dashboard | OP07: Load Personal Dashboard | KPI data + action sections returned | Error loading | MVP |
| User views team dashboard | OP08: Load Team Dashboard | KPI cards + overdue table returned | Error loading | MVP |
| User filters/searches action list | OP09: Query Actions | Filtered, sorted, paginated list returned | Empty result set | MVP |
| User exports action list to Excel | OP10: Export to Excel | .xlsx file generated with current filters | Export error | MVP |
| Admin uploads Excel file for import | OP11: Detect Import Format | File version detected, preview generated | Unrecognized format | MVP |
| Admin confirms import | OP12: Execute Import | Actions + assignments created from Excel data | Import failure / Partial import | MVP |
| Admin rolls back import batch | OP13: Rollback Import | All records from import batch deleted | Rollback error | MVP |
| User changes UI language | OP14: Switch Language | UI re-rendered in target language | — | MVP |
| User logs out | OP15: Terminate Session | Session destroyed | — | MVP |
| Lead sets escalation level | OP16: Escalate Action | Escalation level updated, history logged | Permission denied | MVP |
| Delegate accept/declines assignment | OP17: Respond to Assignment | Assignment status updated, Lead notified | — | V1.1 |
| Lead reassigns delegate | OP18: Reassign | Old assignment closed, new one created | — | V1.1 |
| User sends notification | OP19: Send Notification | Notification logged + delivered | Delivery failure | V1.1 |
| System checks deadlines | OP20: Check Deadlines | Overdue/approaching items flagged | — | V1.1 |
| User adds comment | OP22: Add Comment | Comment stored, assignees notified | — | V1.1 |
| User uploads meeting minutes | OP23: Upload Meeting | File stored, metadata saved | Upload error | V1.1 |
| Admin manages taxonomy | OP24: Update Taxonomy | Entity created/updated/deactivated | Referential integrity error | V1.1 |
| User explicitly starts a workflow from the workflow area or on an existing action | OP25: Create Workflow Instance | Instance + first step(s) activated, SLA computed; optional supporting action linkage preserved where used | Template not found / Binding mismatch | V2.0 |
| User completes current step (click "Done ✓") | OP26: Advance Workflow Step | Step completed, next step(s) activated, SLA computed | Required fields missing / Invalid transition | V2.0 |
| User fills step form fields | OP27: Save Step Field Values | Field values stored per step instance | Validation error (required field empty / type mismatch) | V2.0 |
| Approver approves/rejects gate step | OP28: Record Approval Decision | Decision logged, step advances or rejects | Permission denied / Already decided | V2.1 |
| All parallel branches reach join point | OP29: Resolve Join | Join step auto-completes, next sequential step activated | Race condition (mitigated by `BEGIN IMMEDIATE` — D179) | V2.0 |
| APScheduler checks SLA deadlines | OP30: Check Workflow SLA | Breached steps flagged, in-app notification sent, escalation triggered | — | V2.0-beta |
| Workflow instance reaches End step | OP31: Complete Workflow | Instance status → Completed, optional linked action updated when present | — | V2.0 |
| Admin/TeamLead saves workflow template | OP32: Save Workflow Template | Template created/versioned, `wft_graph` JSON validated | Invalid graph (orphan steps, missing End, circular loops) | V2.3 |
| User/Admin creates standalone workflow request | OP34: Create Workflow Request | Workflow instance spawned; supporting action is optional | Template not found / Required intake fields missing | V2.0 |
| Meeting organizer records a decision | OP35: Create Meeting Decision | Decision record created with status Published | Not organizer / Missing title or body | V3.5 |
| Meeting organizer updates decision fields | OP36: Update Meeting Decision | Decision fields updated (title, body, tags, status) | Not organizer / Invalid transition | V3.5 |
| Meeting organizer transitions decision status | OP37: Transition Decision Status | Status changed per lifecycle FSM; linked action checked if Implemented | Invalid transition / Not organizer | V3.5 |
| User searches decisions | OP38: Search Decisions | Paginated results from FTS5 index + filters | — | V3.5 |
| User opens workflow workbench | OP39: Load Workflow Workbench | Runtime workflow summary, form, attachments, and timeline returned | Instance not found / Permission denied | V3 planned |
| User delegates active workflow step | OP40: Delegate Workflow Step | Delegate assigned with audit trail | Invalid delegate / Missing reason / Permission denied | V3 planned |
| Admin/Lead reassigns active workflow step | OP41: Reassign Workflow Step | New assignee set, prior assignee notified | Permission denied / Invalid assignee | V3 planned |
| User uploads or deletes step attachment | OP42: Manage Workflow Step Attachments | Attachment stored or soft-deleted with history | File policy blocked / Upload failure | V3 planned |

---

## 2. Detailed Operation Specifications

### OP01: Authenticate User

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | User submits username + password on login page |
| **Input Data** | USR_USERNAME, password (plaintext) |
| **Business Rules** | BR20 (lockout after 5 failures/15min) |
| **Preconditions** | User account exists, is_active = true |
| **Output Events** | Success → Create session, redirect to Personal Dashboard |
| **Failure Events** | Invalid credentials → Error message (no detail leak), log attempt |
| **Side Effects** | AUD_LOG entry (V1.1), failed attempt counter updated |

### OP02: Create User

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | Admin fills user creation form |
| **Input Data** | USR_USERNAME, password, USR_DISPLAY, USR_DISPLAY_CN, USR_EMAIL, usr_team_id, USR_TEAM_ID, USR_ROLE |
| **Business Rules** | BR19 (unique username), D22 (role assignment) |
| **Preconditions** | Current user has Admin role |
| **Output Events** | User created with hashed password, default language set |
| **Failure Events** | Duplicate username → Error |

### OP03: Create Action

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | User submits New Action form or Quick-Capture |
| **Input Data** | ACT_TITLE, ACT_DESC, act_team_id, ACT_TEAM_ID, ACT_TOP_ID, ACT_SECONDARY_TOP_ID, ACT_PRIORITY, ACT_DEADLINE, Lead user ID, Delegate user IDs |
| **Business Rules** | BR01 (exactly 1 Lead), BR04 (deadline not in past), BR05 (auto ref code) |
| **Preconditions** | User authenticated, role = Admin/TeamLead/Member |
| **Auto-Generated** | ACT_REF = `ACT-{YYYY}-{SEQ:05d}`, ACT_STATUS = `Open`, ACT_ESC_LEVEL = `Normal`, ACT_CREATED_DATE = now, ACT_CREATED_BY = current user |
| **Output Events** | Action created → Assignment(s) created (auto-Accepted) → ACTION_HISTORY entry (Created) |
| **Failure Events** | Missing required field → Validation error with field list |

### OP04: Update Action

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | User saves changes on Edit Action form |
| **Input Data** | ACT_ID + changed fields (title, description, dept, team, priority, deadline, etc.) |
| **Business Rules** | BR05 (ref immutable), change deadline logs revised_deadline |
| **Preconditions** | User is Lead on action or Admin |
| **Output Events** | Action updated → ACTION_HISTORY entry (Updated) per changed field |
| **Failure Events** | Permission denied / Validation error |

### OP05: Transition Status

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | User clicks status badge → selects new status |
| **Input Data** | ACT_ID, new status value |
| **Business Rules** | BR03 (terminal states), valid transition per FSM, side effects per R02 §3.3 |
| **Preconditions** | Transition is valid per `VALID_TRANSITIONS` dict |
| **Output Events** | Status updated → ACTION_HISTORY entry (StatusChange) |
| **Side Effects** | `→ On Hold`: require hold_reason; `→ Cancelled`: require cancel_reason; `→ Done`: set ACT_ACTUAL_DATE = now |
| **Failure Events** | Invalid transition → Error "Cannot move from {current} to {target}" |

### OP06: Assign User

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | Lead selects delegate(s) in action form |
| **Input Data** | ACT_ID, USR_ID, ASG_ROLE |
| **Business Rules** | BR08 (exactly 1 Lead), BR10 (cross-dept OK), BR11 (auto-accept MVP), D166 (one row per user per action — upsert role) |
| **Preconditions** | User is Lead on action or Admin |
| **Output Events** | Assignment row created (first role for this user on this action) or `asg_role` column updated (role appended to existing row — D166 upsert). Action appears on assignee's dashboard. |
| **Failure Events** | Missing Lead on action |

### OP07: Load Personal Dashboard

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | User navigates to dashboard (or login redirect) |
| **Input Data** | USR_ID (from session) |
| **Business Rules** | D61 (landing page), D153 (MVP: Personal + Team only) |
| **Queries** | 1) Overdue: actions where user is owner or explicitly assigned AND deadline < today AND status NOT IN (Done, Cancelled); 2) Due This Week: same but deadline this week; 3) Recently Completed: status = Done AND actual_date in last 30 days; 4) KPI counts; 5) Decision KPIs + recent decisions (last 30 days) |
| **Output Events** | Dashboard data returned →  rendered with color-coded sections |

### OP08: Load Team Dashboard

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | User navigates to team dashboard |
| **Input Data** | tea_id, optional date range |
| **Queries** | KPI cards (total, open, overdue, completed, completion rate %); Status breakdown per status; Top 10 overdue actions; Priority breakdown; Escalation count |
| **Output Events** | Dashboard data returned → KPI cards + overdue table rendered |

### OP09: Query Actions

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | User views action list or applies filters |
| **Input Data** | Filters (team, status, priority, date range, text search), sort column/direction, page number |
| **Business Rules** | BR18 (all actions visible), pagination 25/50/100 per page |
| **Output Events** | Paginated action list with total count |

### OP10: Export to Excel

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | User clicks "Export to Excel" on action list or dashboard |
| **Input Data** | Current filter state |
| **Business Rules** | D72 (formatted .xlsx with headers, auto-filter, bilingual headers), D74 (ad-hoc) |
| **Output Events** | .xlsx file generated → browser download; includes "Generated on" timestamp + filter summary sheet |

### OP11: Detect Import Format

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | Admin uploads .xlsx file on Import page |
| **Input Data** | Excel file binary |
| **Business Rules** | D91 (detection by sheet name + header pattern) |
| **Detection Rules** | Sheet "Action list" + Col A "Phase" → v1; Sheet "Action Plan" + Row 3 Col B "PLANT AREA" → v2; Sheet "Action Log (2)" + Row 10 Col E "Action" → v3; Sheet "红单" + Col A "Date" → v4 |
| **Output Events** | Format detected → Preview table generated (first 20 rows, column mapping shown) |
| **Failure Events** | Unrecognized format → Error "Unable to detect format" |

### OP12: Execute Import

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | Admin confirms import after resolving owners/depts |
| **Input Data** | Parsed rows with resolved mappings |
| **Business Rules** | BR21 (one-time), BR22 (create only), BR24 (exact title dedup), D92 (skip rows missing title), D89 (user resolution) |
| **Output Events** | Actions + Assignments + History created → ImportLog entry → Summary displayed |
| **Failure Events** | Partial import → ImportLog with warnings |
| **Side Effects** | ACT_SOURCE = `Import`, ACT_SOURCE_FILE = filename |

### OP13: Rollback Import

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | Admin clicks "Rollback" on previous import |
| **Input Data** | IML_ID |
| **Business Rules** | BR23 (reversibility), D98 |
| **Output Events** | All Action + Assignment + History records from batch deleted → ImportLog status updated |

### OP14: Switch Language

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | User clicks EN/CN toggle |
| **Input Data** | Target language (`en` / `zh`) |
| **Side Effects** | USR_LANG updated in profile, session language preference set |
| **Output Events** | UI re-rendered using target language JSON file |

### OP16: Escalate Action

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | Lead manually sets escalation level |
| **Input Data** | ACT_ID, new ACT_ESC_LEVEL |
| **Business Rules** | D32 (escalation rules — manual in MVP) |
| **Preconditions** | User is Lead on action or Admin |
| **Output Events** | Escalation updated → ACTION_HISTORY entry |

---

### OP25: Create Workflow Instance (V2.0)

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | User starts a process workflow from the workflow area, or explicitly starts a compatibility workflow on an existing action |
| **Input Data** | WFT_ID, optional ACT_ID |
| **Business Rules** | BR25 (optional action linkage), BR26 (process-first runtime), BR27 (graph from JSON) |
| **Preconditions** | Template exists and is active; if ACT_ID is provided, that action does not already have an instance |
| **Auto-Generated** | WFI_STATUS = `Active`, WFI_STARTED_AT = now; first step(s) WSI_STATUS = `Active`, WSI_ENTERED_AT = now; SLA deadline computed from `sla_hours` |
| **Output Events** | Instance created → Step instance(s) created → optional action-history entry when an action is linked |
| **Failure Events** | Template not found → Error; Action already has instance → Error |

### OP26: Advance Workflow Step (V2.0)

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | User clicks "Done ✓" on their active step |
| **Input Data** | WSI_ID, optional WSI_COMMENT |
| **Business Rules** | BR29 (join waits for all branches), BR30 (`BEGIN IMMEDIATE`), BR34 (display_status update) |
| **Preconditions** | Step is Active; required form fields are filled; user is step assignee or Admin |
| **Output Events** | Step → Completed; next step(s) → Active with SLA computed; if End step → OP31 |
| **Side Effects** | ACTION_HISTORY entry (`WorkflowAdvance`); if parallel → check join via OP29; SLA deadline set for new active step(s) |
| **Failure Events** | Required fields missing → Validation error; Step not Active → Error |

### OP27: Save Step Field Values / Draft (V2.0, V3 planned extension)

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | User fills form fields on an active step and clicks Save Draft or auto-save point |
| **Input Data** | WSI_ID, optional WSI_COMMENT, array of {SFV_FIELD_KEY, SFV_VALUE} |
| **Business Rules** | BR35 (earlier step values visible read-only) |
| **Preconditions** | Step instance exists and is Pending/Accepted; field keys exist in `wft_graph.steps[].fields` |
| **Output Events** | Field values stored (upsert by step_inst + field_key); optional draft comment saved on step |
| **Failure Events** | Type mismatch → Validation error; Required field empty on advance → blocked by OP26 |

### OP28: Record Approval Decision (V2.1)

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | Approver clicks Approve/Reject on a gate step |
| **Input Data** | WSI_ID, WAP_DECISION, optional WAP_COMMENT |
| **Business Rules** | BR31 (at least 1 approval) |
| **Preconditions** | Step is Approval type and Active; user is designated approver |
| **Output Events** | Approval record created → If gate satisfied: step → Completed → OP26 advances; If rejected: step → Rejected → loop-back per transition |
| **Failure Events** | Not an approver → Permission denied; Already decided → Error |

### OP29: Resolve Join (V2.0)

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | A parallel branch step is completed, and this step feeds into a Join |
| **Input Data** | WSI_ID (the join step instance) |
| **Business Rules** | BR29 (all incoming branches Completed), BR30 (`BEGIN IMMEDIATE` — D179) |
| **Preconditions** | Join step exists; at least 2 incoming branches defined in `wft_graph.transitions` |
| **Output Events** | If all branches Complete → Join auto-completes → next step activated; else → no-op (wait) |
| **Concurrency** | Uses `BEGIN IMMEDIATE` to serialize parallel branch completion checks |

### OP30: Check Workflow SLA (V2.0-beta)

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | APScheduler periodic check (D180 — interval TBD, e.g., every 15 min) |
| **Input Data** | Current timestamp |
| **Business Rules** | BR33 (SLA deadline computation) |
| **Preconditions** | Active step instances with `wsi_sla_deadline < now` |
| **Output Events** | Breached steps flagged → in-app notification to step assignee and instance creator → optional escalation trigger |
| **Side Effects** | ACTION_HISTORY entry if escalation triggered |

### OP31: Complete Workflow (V2.0)

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | An End step is reached (OP26 advances to End step) |
| **Input Data** | WFI_ID |
| **Business Rules** | BR25 (instance may have an optional linked action) |
| **Preconditions** | End step activated |
| **Output Events** | WFI_STATUS → `Completed`; WFI_COMPLETED_AT = now; linked action `act_status` updated only when an action is present |
| **Side Effects** | Optional ACTION_HISTORY entry (`WorkflowAdvance: Completed`) when an action is linked |

### OP34: Create Workflow Request (V2.0)

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | User submits a standalone workflow request form |
| **Input Data** | WFT_ID (template type = `request`), intake form fields (from first step's field definitions) |
| **Business Rules** | BR26 (workflow-area launch is primary), BR27 (graph from JSON) |
| **Preconditions** | Template exists, active, type = `request`; user authenticated |
| **Auto-Generated** | Workflow instance runtime row + first active step set. Supporting action creation is optional and no longer required. |
| **Output Events** | Instance created → First step activated |
| **Failure Events** | Template not found → Error; Required intake fields missing → Validation error |

### OP39: Load Workflow Workbench (V3 planned)

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | User opens the workflow workbench from the workflow dashboard or a dedicated workflow route |
| **Input Data** | WFI_ID |
| **Business Rules** | D206 (single workbench), D209 (show workflow + step + action status together), D210 (include draft values and context fields) |
| **Preconditions** | Workflow instance exists; user may view the workflow instance |
| **Output Events** | Runtime payload returned: instance summary, current step, eligible users, editable fields, context fields, attachments, timeline |
| **Failure Events** | Workflow instance not found → Error; Permission denied → Error |

### OP40: Delegate Workflow Step (V3 planned)

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | Current assignee clicks Delegate and selects a user |
| **Input Data** | WSI_ID, delegate_user_id, mandatory reason |
| **Business Rules** | D208 (assignment actions fully audited) |
| **Preconditions** | Step is human type and active for current assignee or Admin |
| **Output Events** | Step reassignment recorded with history + notification |
| **Failure Events** | Delegate invalid/ineligible → Validation error; Missing reason → Validation error; Permission denied → Error |

### OP41: Reassign Workflow Step (V3 planned)

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | Admin or TeamLead selects Reassign on current step |
| **Input Data** | WSI_ID, new assignee, mandatory reason |
| **Business Rules** | D184 (runtime assignee resolution), D208 (audited reassignment), D209 (status clarity maintained after reassignment) |
| **Preconditions** | Step is active human step; actor has reassignment permission |
| **Output Events** | `wsi_assignee_id` updated; prior assignee and new assignee notified; history event logged |
| **Failure Events** | Invalid assignee → Validation error; Permission denied → Error |

### OP42: Manage Workflow Step Attachments (V3 planned)

| Attribute | Value |
|-----------|-------|
| **Trigger Event** | User uploads attachment or deletes an existing step attachment |
| **Input Data** | WSI_ID, file payload or attachment_id, optional description |
| **Business Rules** | D207 (controlled allowlist uploads), D210 (attachments visible with step context), notification on add/delete |
| **Preconditions** | Step exists; actor may upload/delete for this step; file policy passed |
| **Output Events** | Attachment row created or soft-deleted; action-history event logged; workbench attachment panel refreshed |
| **Failure Events** | File policy blocked → Validation error; Size exceeded → Error; Upload/storage failure → Error |

---

## 3. Operation Dependencies (Synchronization)

| Operation | Depends On | Synchronization Rule |
|-----------|------------|----------------------|
| OP03 (Create Action) | OP01 (Authenticate) | User must be logged in |
| OP03 (Create Action) | OP02 (Create User) | Owner/assignee users must exist |
| OP04 (Update Action) | OP03 (Create Action) | Action must exist |
| OP05 (Transition Status) | OP03 (Create Action) | Action must exist, current status must be valid origin |
| OP06 (Assign User) | OP03 (Create Action) | Action must exist |
| OP06 (Assign User) | OP02 (Create User) | Assignee must exist |
| OP07 (Personal Dashboard) | OP01 (Authenticate) | Session required |
| OP08 (Dept Dashboard) | OP01 (Authenticate) | Session required |
| OP09 (Query Actions) | OP01 (Authenticate) | Session required |
| OP10 (Export) | OP09 (Query Actions) | Filter state from action list |
| OP12 (Execute Import) | OP11 (Detect Format) | Format must be detected first |
| OP13 (Rollback) | OP12 (Execute Import) | Import batch must exist |
| OP17 (Respond Assignment) | OP06 (Assign User) | Assignment must exist (V1.1) |
| OP25 (Create WF Instance) | OP03 (Create Action) | Action must exist; workflow binding must match (V2.0) |
| OP25 (Create WF Instance) | OP32 (Save Template) | Template must exist and be active (V2.0) |
| OP26 (Advance Step) | OP25 (Create Instance) | Instance must be Active; step must be Active (V2.0) |
| OP27 (Save Field Values) | OP25 (Create Instance) | Step instance must exist (V2.0) |
| OP28 (Approval Decision) | OP26 (Advance Step) | Step must be Approval type and Active (V2.1) |
| OP29 (Resolve Join) | OP26 (Advance Step) | All incoming branches must be Completed; uses `BEGIN IMMEDIATE` (V2.0) |
| OP30 (Check WF SLA) | OP25 (Create Instance) | Step instances must exist with SLA deadlines (V2.0-beta) |
| OP31 (Complete Workflow) | OP26 (Advance Step) | End step reached (V2.0) |
| OP32 (Save Template) | OP01 (Authenticate) | User must be Admin or TeamLead (V2.3) |
| OP34 (Create WF Request) | OP01 (Authenticate) | Template must be type `request` and active (V2.0) |
| OP39 (Load Workflow Workbench) | OP25 (Create Instance) | Workflow instance must exist and be visible to user |
| OP40 (Delegate Workflow Step) | OP39 (Load Workflow Workbench) | Current step must be loaded and actor must be eligible |
| OP41 (Reassign Workflow Step) | OP39 (Load Workflow Workbench) | Current step must be loaded and actor must have override rights |
| OP42 (Manage WF Step Attachments) | OP39 (Load Workflow Workbench) | Step must exist and remain upload-eligible |

---

## 4. State Machine: Action Lifecycle

### Valid Transitions

```python
VALID_TRANSITIONS = {
    "Open":        ["In Progress", "On Hold", "Cancelled"],
    "In Progress": ["On Hold", "Done"],
    "On Hold":     ["Open", "In Progress"],
    "Done":        [],       # Terminal
    "Cancelled":   [],       # Terminal
}
```

### Transition Requirements

| Transition | Required Field | Side Effect |
|------------|---------------|-------------|
| Any → On Hold | hold_reason (TEXT) | — |
| Any → Cancelled | cancel_reason (TEXT) | — |
| * → Done | — | ACT_ACTUAL_DATE = now |
| Any transition | — | ACTION_HISTORY entry created |

---

## 5. Derivation to MOT (Next Step)

The MCT defines **what** happens. The MOT (S15) will specify:
- **Who** performs each operation (actor/role)
- **Where** it executes (browser, backend, database)
- **When** it happens (real-time, async, batch)
