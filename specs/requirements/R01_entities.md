# ActionHub — Entity Inventory

> **Status**: Requirements-level specification  
> **Depends on**: `R00_initial_vision.md` (project scope)  
> **Decisions**: D16–D25 in `DECISIONS.md`  
> **Consumed by**: SpecForge for `05_data_dictionary.md`, `10_MCD.md`

---

## Manual Workflow Instance Creation Only (2026-03-17)

- Workflow instances are never auto-started when an action is created or edited.
- There is no auto-start binding or automatic workflow instance creation based on action fields.
- Workflow instances can only be started manually by the user from a dedicated workflow page or endpoint, where the user selects the template and (optionally) the action to link.
- All previous references to auto-start, auto-binding, or automatic workflow instance creation are obsolete and must not be implemented.

---

## §0 MVP vs V1.1 Entity Scope

| Phase | Entities |
|-------|----------|
| **MVP (1.5d)** | Action, User, Team, Team, Category (global), Category, Assignment, ActionHistory, PriorityLevel, EscalationLevel, ActionComment, MeetingInstance |
| **V1.1** | ActionAttachment, MeetingSummary (upload), AssignmentHistory, NotificationRule, NotificationLog, Tag |
| **V1.2** | ActionDependency, ReportTemplate, ScheduledReport |
| **V2.0** | WorkflowTemplate, WorkflowInstance, WorkflowStepInstance, WorkflowStepFieldValue, WorkflowApproval |

> **Rule**: MVP entities must be schema-complete on Day 1 AM. V1.1 entities are designed now but table creation is deferred.

---

## §1 Entity Inventory (by Domain)

### Core Domain

| Entity | Description | Cardinality Hint | Phase |
|--------|-------------|------------------|-------|
| **Action** | Primary work item tracked by the system. Actions can originate from meetings, manual/direct category-driven work, and compatibility or service-step workflow flows. Workflow runtime remains a distinct work object type even when a workflow optionally references an action. Each action carries 1 primary category and may carry 1 secondary category. | High (~500+) | MVP |
| **ActionComment** | Rich-text comment on an Action; 3 types: Comment / Achievement / Roadblock | Very high | MVP |
| **ActionDependency** | Link between two Actions (blocks/blocked-by) | Medium | V1.2 |
| **ActionAttachment** | File attached to an Action | Medium | V1.1 |
| **ActionHistory** | Audit trail entry for every change to an Action (including comments) | Very high | MVP |

> **Unified Action Management:** Actions may be linked to meetings and 1..2 Categories. Workflow linkage, where present, is represented from workflow runtime via `WFI_ACTION_ID` and remains optional/compatibility-oriented rather than the primary operating model. Storage compatibility continues to use `ACT_TOP_ID` / `ACT_SECONDARY_TOP_ID` until a later physical rename.

### Organization Domain

| Entity | Description | Cardinality Hint | Phase |
|--------|-------------|------------------|-------|
| **Team** | Organizational team (12) | Low, static | MVP |
| **Team** | Sub-group within a team | Low–Medium | MVP |
| **User** | System user (Day 1: local accounts; V1.1: synced from AD) | Low (<50) | MVP |

### Taxonomy Domain

| Entity | Description | Cardinality Hint | Phase |
|--------|-------------|------------------|-------|
| **Category** | Global strategic classification for actions, meetings, decisions, and workflows (e.g., Equipment KOM, Training); managed by Admin/TeamLead only; normal users read-only. Chinese: 类别 | Medium | MVP |
| **Tag** | Free-form label applied to actions | Medium | V1.1 |
| **ActionType** | Classification of the nature of an action (e.g., "Supplier issue", "Internal"). Chinese: 行动类型 | Low–Medium | MVP |
| **PriorityLevel** | Enumeration: Critical, High, Medium, Low | Fixed (4) | MVP |
| **EscalationLevel** | Escalation tier (Normal, Escalated, WAR) | Fixed (3) | MVP |

### Assignment Domain

| Entity | Description | Cardinality Hint | Phase |
|--------|-------------|------------------|-------|
| **Assignment** | Relationship: User ↔ Action with role | High | MVP |
| **AssignmentHistory** | Audit trail for assignment changes (reassign, accept, decline) | High | V1.1 |

### Meeting Domain

| Entity | Description | Cardinality Hint | Phase |
|--------|-------------|------------------|-------|
| **MeetingInstance** | A specific meeting occurrence with date, type, and up to 2 attached categories; actions can reference a specific instance | Medium | MVP |
| **MeetingSummary** | Uploaded meeting memo (any file type) stored as binary blob in SQLite, linked to a MeetingInstance | Medium | **MVP** |

### Notification Domain (V1.1)

| Entity | Description | Cardinality Hint | Phase |
|--------|-------------|------------------|-------|
| **NotificationRule** | Configurable notification trigger (deadline, overdue, etc.) | Low | V1.1 |
| **NotificationLog** | Record of sent notifications | Very high | V1.1 |

### Reporting Domain (V1.2)

| Entity | Description | Cardinality Hint | Phase |
|--------|-------------|------------------|-------|
| **ReportTemplate** | Saved report configuration (filters, columns, schedule) | Low | V1.2 |
| **ScheduledReport** | Auto-delivery schedule for a report template | Low | V1.2 |

### Workflow Domain (V2)

> **Decisions**: D167–D180, R16. Design-time graph stored as JSON (O3); runtime tables normalized.

| Entity | Description | Cardinality Hint | Phase |
|--------|-------------|------------------|-------|
| **WorkflowTemplate** | Versioned process definition with JSON graph of steps, transitions, triggers, and form fields (D176) | Low (~10–20) | V2.0 |
| **WorkflowInstance** | Running copy of a template. A workflow instance may optionally reference one supporting `t_action` row for compatibility flows, but request workflows can run without a bound action. | Medium (~100s) | V2.0 |
| **WorkflowStepInstance** | Runtime state of a specific step within an instance; tracks assignee, status, SLA deadline | High | V2.0 |
| **WorkflowStepFieldValue** | Runtime form data filled by users at each step instance | High | V2.0 |
| **WorkflowApproval** | Approval/rejection record for gate steps | Medium | V2.1 |

---

## §2 Key Entity Field Stubs

> **Database**: SQLite with WAL mode. All types below use SQLite-native types (TEXT, INTEGER, REAL). VARCHAR(N) annotations indicate application-level validation length, not DB constraints.

### Action

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | INT (PK) | Yes | Auto-increment |
| reference_code | VARCHAR(20) | Yes | Auto-generated: `ACT-{YYYY}-{SEQ}` |
| title | VARCHAR(255) | Yes | Bilingual support |
| description | TEXT | No | Rich text |
| team_id | FK → Team | No | **Deprecated — not set on new actions.** Historically auto-assigned from the Lead's primary team; team dashboards now query Lead membership directly instead. |
| category_1_id | FK → Category | **Yes** | Required primary category; stored today as `ACT_TOP_ID` |
| category_2_id | FK → Category | No | Optional secondary category; stored today as `ACT_SECONDARY_TOP_ID` |
| owner_id | FK → User | Yes | Primary responsible owner (single responsible person shown in table/cards) |
| priority | ENUM | Yes | Critical / High / Medium / Low (D18) |
| escalation_level | ENUM | Yes | Normal / Escalated / WAR (D19) |
| status | ENUM | Yes | See §3 lifecycle |
| created_date | DATETIME | Yes | Auto |
| deadline | DATE | Yes | |
| revised_deadline | DATE | No | When deadline is changed |
| actual_completion_date | DATE | No | Set when status → Done |
| created_by | FK → User | Yes | |
| source | ENUM | No | Manual / Import / MeetingSummary / Workflow / Category |
| source_file | VARCHAR(255) | No | Original Excel filename if imported |
| tags | VARCHAR(500) | No | Comma-separated business tags used for traceability and search; stored uppercase and displayed with leading `#` |
| meeting_instance_id | FK → MeetingInstance | No | Link to specific meeting occurrence |
| last_comment | TEXT | No | MVP shortcut: latest comment text (kept for quick display) |

### ActionComment

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | INT (PK) | Yes | |
| action_id | FK → Action | Yes | Owning action |
| comment_type | ENUM | Yes | `comment` / `achievement` / `roadblock` |
| body | TEXT | Yes | Rich text (HTML sanitized) |
| created_by | FK → User | Yes | Author |
| created_at | DATETIME | Yes | Auto |
| edited_at | DATETIME | No | Set when body is modified |
| edited_by | FK → User | No | Who last edited |
| is_deleted | BOOLEAN | Yes | Default false — soft delete |

> **Edit / delete rights**: Admin, TeamLead, or the original author (`created_by`). Every edit and deletion creates an `ActionHistory` entry with `change_type = 'CommentEdited'` / `'CommentDeleted'`.

### Assignment

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | INT (PK) | Yes | |
| action_id | FK → Action | Yes | |
| user_id | FK → User | Yes | |
| role | TEXT | No | Legacy compatibility field in assignment rows. Action control is owner-based (`owner_id`). |
| status | ENUM | Yes | MVP: auto-set to Accepted; V1.1: Pending / Accepted / Declined / Reassigned. **One status per user per action** regardless of number of roles held. |
| assigned_date | DATETIME | Yes | |
| response_date | DATETIME | No | V1.1 — when accepted/declined |
| decline_reason | TEXT | No | V1.1 |
| assigned_by | FK → User | Yes | |

> **Uniqueness constraint**: `UNIQUE(action_id, user_id)` — enforced at the database level (D166).

### User

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | INT (PK) | Yes | |
| username | VARCHAR(100) | Yes | Login username (Day 1: manual; V1.1: AD sAMAccountName) |
| password_hash | VARCHAR(255) | Yes* | Bcrypt hash (Day 1 only; NULL when using AD in V1.1) |
| display_name | VARCHAR(255) | Yes | Full name |
| display_name_cn | VARCHAR(255) | No | Chinese name |
| email | VARCHAR(255) | Yes | For notifications |
| team_id | FK → Team | **Yes** | Single team (exactly one); mandatory; Admin selects from team dropdown when creating or editing a user |
| team_id | FK → Team | No | Legacy field — not actively maintained. |
| role | ENUM | Yes | Admin / TeamLead / Member / ReadOnly (D22) |
| is_active | BOOLEAN | Yes | Day 1: manual; V1.1: synced from AD |
| preferred_language | ENUM | Yes | en / zh (D23) |
| auth_source | ENUM | Yes | local / ad (D76a) |

> **Admin UI rule**: The user create/edit form must render `team_id` as a dropdown populated from the active Team list, not a free-text field.

#### User ↔ Team membership (`t_user_team`)

A user may belong to **zero or more teams**. The membership table carries:

| Field | Notes |
|-------|-------|
| utm_user_id | FK → User |
| utm_team_id | FK → Team |

An action is visible on a team's dashboard when its **owner is a member of that team**. A user on multiple teams will have their actions counted on all those dashboards, enabling cross-team workload visibility.

### Team

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | INT (PK) | Yes | |
| name_en | VARCHAR(100) | Yes | English name |
| name_cn | VARCHAR(100) | Yes | Chinese name 中文名 |
| code | VARCHAR(10) | Yes | Short code (e.g., "FAC", "IE", "PROC") |
| is_active | BOOLEAN | Yes | Soft delete |

### MeetingSummary (MVP)

| Field | Type | Required | Notes |
|-------|------|----------|---------|
| id | INT (PK) | Yes | |
| meeting_instance_id | FK → MeetingInstance | Yes | Which meeting this file belongs to |
| file_name | VARCHAR(500) | Yes | Original filename as uploaded |
| file_mime | VARCHAR(100) | No | MIME type detected at upload |
| file_data | BLOB | Yes | Binary content stored directly in SQLite (any file type) |
| file_size_bytes | INTEGER | Yes | Used for display and quota checks |
| uploaded_by | FK → User | Yes | |
| uploaded_at | DATETIME | Yes | Auto |

> **Storage decision**: Files stored as SQLite BLOB (not filesystem). This avoids path-management issues on Windows and keeps the system single-file. Practical limit: individual files ≤20 MB; total DB size monitored.

### MeetingInstance (MVP)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | INT (PK) | Yes | |
| category_1_id | FK → Category | No | Optional primary category |
| category_2_id | FK → Category | No | Optional secondary category |
| title | VARCHAR(255) | Yes | Meeting name / label |
| meeting_type | VARCHAR(100) | No | e.g., "Weekly review", "Kick-off", "Ad-hoc" — free text |
| meeting_date | DATE | Yes | Date of the occurrence |
| created_by | FK → User | Yes | |
| created_at | DATETIME | Yes | Auto |

### ActionHistory

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | INT (PK) | Yes | |
| action_id | FK → Action | Yes | |
| field_changed | VARCHAR(100) | Yes | Which field was modified |
| old_value | TEXT | No | |
| new_value | TEXT | No | |
| changed_by | FK → User | Yes | |
| changed_date | DATETIME | Yes | |
| change_type | ENUM | Yes | Created / Updated / StatusChange / Reassigned / Closed |

---

## §3 Lifecycle State Machines

### Action Status Lifecycle

```
                    ┌──────────────┐
                    │              │
         ┌────────►│   On Hold    │◄──────────┐
         │         │              │            │
         │         └──────┬───────┘            │
         │                │ resume             │
         │                ▼                    │
┌────────┴──┐      ┌─────────────┐      ┌─────┴──────┐
│           │      │             │      │            │
│   Open    ├─────►│ In Progress ├─────►│Under Review│
│           │      │             │      │            │
└─────┬─────┘      └──────┬──────┘      └─────┬──────┘
      │                   │                    │
      │                   │                    │ approve
      │                   │                    ▼
      │                   │              ┌──────────┐
      │                   │              │          │
      │                   └─────────────►│   Done   │
      │                                  │          │
      │                                  └──────────┘
      │
      ├───────────────────────────────►  Postponed
      │                                  (can reopen → Open)
      │
      └───────────────────────────────►  Cancelled
                                         (terminal)
```

**Valid Transitions:**

| From | To | Trigger | Notes |
|------|----|---------|-------|
| Open | In Progress | Assignee starts work | |
| Open | On Hold | Lead pauses action | Requires reason |
| Open | Postponed | Lead defers action | Requires new target date |
| Open | Cancelled | Lead cancels | Requires reason |
| In Progress | Under Review | Assignee submits for review | |
| In Progress | On Hold | Lead pauses | |
| In Progress | Done | Direct completion (skip review) | Only if no review required (D24) |
| Under Review | Done | Lead approves | |
| Under Review | In Progress | Lead requests changes | May add comment |
| On Hold | Open | Lead resumes | |
| On Hold | In Progress | Lead resumes directly | |
| Postponed | Open | Lead reactivates | New deadline required |
| Cancelled | — | Terminal state | No transitions out |
| Done | — | Terminal state | No transitions out (D25) |

### Assignment Status Lifecycle

```
Pending → Accepted → (active until action closes)
Pending → Declined → (notifies creator + lead, suggests alternatives)
Accepted → Reassigned → new Assignment(Pending) created
```

### Escalation Lifecycle

```
Normal → Escalated (manual or auto after N days overdue)
Escalated → WAR (manual escalation by management)
WAR → Normal (resolution confirmed)
Escalated → Normal (resolution confirmed)
```

---

## §4 Taxonomy / Hierarchy

```
Team (L1)
 └── Team (L2)
      └── Action (entity)

Category (GLOBAL, not scoped under Team)
 └── Action (entity)            ← action belongs to one or two Categories
 └── MeetingInstance (entity)   ← meeting is optionally linked to up to 2 Categories

Tag (free-form, cross-cutting — e.g., "SAP", "quality", "urgent") [V1.1]
```

**Category management rules:**
- Categories are global (no team parent)
- Only Admin and TeamLead can create / edit / delete Categories
- Normal users (Member, ReadOnly) are read-only on the Category list
- Each Action belongs to at least one and at most two Categories
- TeamLead can manage Categories but NOT Teams (teams are Admin-only)

---

## §1.1 Binding and Linking Rules (2026-03-17)

- **Actions** may optionally be linked to:
  - A team (`team_id` / `ACT_TEAM_ID`)
  - A meeting instance (`meeting_instance_id` / `ACT_MTG_INST_ID`)
  - One or two categories (`category_1_id` / `ACT_TOP_ID`, `category_2_id` / `ACT_SECONDARY_TOP_ID`)
- All such links are optional and may be set independently.
- Workflow linkage, when present, is represented from workflow runtime through optional `WFI_ACTION_ID` on the workflow instance rather than a primary action-side field.
- **Meeting actions** must support inheriting up to 2 categories from the meeting.
- **Workflow instances** may be launched with category classification remaining on the bound or created action.
- **Workflow steps** that create or update actions must allow specifying or inheriting categories from the parent context.
- **Decisions** may optionally be linked to a team, meeting, and up to 2 categories, using the same conventions as actions.

> This ensures consistent classification, filtering, and reporting across all action sources and decision records.
