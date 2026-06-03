# ActionHub — Data Dictionary

> **Level**: L0 — Foundation  
> **Merise Phase**: Dictionnaire des Données  
> **Source**: R01_entities.md, R02_action_lifecycle.md, R03_assignment_workflow.md, R08_taxonomy.md  
> **Decisions**: D16–D25, D89–D108

---


## Manual Workflow Instance Creation Only (2026-03-17)

- Workflow instances are never auto-started when an action is created or edited.
- There is no auto-start binding or automatic workflow instance creation based on action fields.
- Workflow instances can only be started manually by the user from a dedicated workflow page or endpoint, where the user selects the template and (optionally) the action to link.
- Workflow instances do not carry their own Categories. Any category selection at workflow request time applies to the bound or created action. Team is not linkable at workflow creation.
- All previous references to auto-start, auto-binding, or automatic workflow instance creation are obsolete and must not be implemented.

---

## 0.1 Binding and Linking Rules (2026-03-17)

- **Actions**: May be linked to a meeting (`ACT_MTG_INST_ID`) and 1..2 Categories (`ACT_TOP_ID`, `ACT_SECONDARY_TOP_ID`). `ACT_TEAM_ID` remains a legacy compatibility column and is not set for new actions. If a workflow instance references an action, that linkage is represented on workflow runtime via `WFI_ACTION_ID`, not by making action detail the primary workflow surface.
- **Meeting actions**: Must support inheriting up to 2 Categories from the meeting.
- **Workflow steps**: Steps that create or update actions must allow specifying or inheriting Categories from the parent context.
- **Decisions**: May be linked to a team, meeting, and up to 2 Categories, using the same conventions as actions.
- **Workflow instances**: Must not store their own Category fields; category classification lives on the bound action.

> These rules ensure consistent classification and flexible reporting for all action and decision records.

---

## 1. Action Domain

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `ACT_ID` | Action ID | INTEGER | PK, Auto-increment | Unique action identifier | R01 §2 |
| `ACT_REF` | Reference Code | VARCHAR(20) | Unique, Required, Immutable | Auto-generated: `ACT-{YYYY}-{SEQ:05d}` | R02 §2.3 |
| `ACT_TITLE` | Title | VARCHAR(255) | Required | Action headline (bilingual content) | R01 §2 |
| `ACT_DESC` | Description | TEXT | Optional | Rich text description | R01 §2 |
| `ACT_TAGS` | Tags | VARCHAR(500) | Optional | Comma-separated business tags for search and traceability; stored uppercase and rendered with `#` prefix in UI | R01 §2 |
| `act_team_id` | Team | INTEGER | FK → tea_id, ~~Required~~ **Deprecated v2.6** | Legacy — hardcoded to 1; use `ACT_TEAM_ID` | R01 §2 |
| `ACT_TEAM_ID` | Team | INTEGER | FK → TEA_ID, Optional (legacy) | Legacy compatibility field; not set on new actions | R01 §2 |
| `ACT_TOP_CODE` | Category 1 | CHAR(3) | FK → TOP_CODE, Required | Primary strategic category. User-facing term: Category. | R01 §2, R08 |
| `ACT_SECONDARY_TOP_CODE` | Category 2 | CHAR(3) | FK → TOP_CODE, Optional | Optional second strategic category. Must differ from `ACT_TOP_CODE`. | S54 |
| `ACT_PRIORITY` | Priority | ENUM | Required, Values: `Critical`, `High`, `Medium`, `Low` | Urgency level (D18). **Not exposed in Meeting Action Edit modal** — field is retained in DB and API but hidden from the meeting-context UI. | R02 §4 |
| `ACT_ESC_LEVEL` | Escalation Level | ENUM | Required, Values: `Normal`, `Escalated`, `WAR`, Default: `Normal` | Escalation tier (D19) | R02 §5 |
| `ACT_STATUS` | Status | ENUM | Required, Values: `Open`, `In Progress`, `On Hold`, `Done`, `Cancelled` | Lifecycle state (runtime SQLite CHECK-constrained set) | R02 §3 |
| `ACT_CREATED_DATE` | Created Date | DATETIME | Auto, Immutable | Creation timestamp | R01 §2 |
| `ACT_START_DATE` | Start Date | DATE | Optional | Planned or actual start date (v2.7) | S53 |
| `ACT_DEADLINE` | Deadline | DATE | Required | Target completion date | R01 §2 |
| `ACT_ACTUAL_DATE` | Actual Completion | DATE | Optional | Set when status → Done | R02 §3.3 |
| `ACT_CREATED_BY` | Created By | INTEGER | FK → USR_ID, Required | User who created | R01 §2 |
| `ACT_SOURCE` | Source | ENUM | Optional, Values: `Manual`, `Import`, `MeetingSummary`, `Workflow`, `Topic` | How action was created (meeting, workflow, topic/category, etc.) | R01 §2 |
| `ACT_SOURCE_FILE` | Source File | VARCHAR(255) | Optional | Original Excel filename if imported | R01 §2 |
| `ACT_MTG_INST_ID` | Meeting Instance | INTEGER | FK → MIN_ID, Optional | Link to specific meeting occurrence | R13 §1 |
| `ACT_LAST_COMMENT` | Last Comment | TEXT | Optional | MVP quick-display shortcut: latest comment text | R12 §1 |
| `ACT_VISIBILITY` | Visibility | ENUM | Required, Default: `public`, Values: `public`, `private` | Access control. Private: visible to Created by (`ACT_CREATED_BY`), Lead (`ACT_OWNER_ID`), explicitly assigned users, and authorized meeting participants. Public: additionally visible via team-leader scope rules. Inherited from meeting if linked. | R19 §9 |

## 2b. ActionComment Domain (MVP)

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `CMT_ID` | Comment ID | INTEGER | PK, Auto-increment | Unique comment identifier | R12 §2 |
| `CMT_ACT_ID` | Action | INTEGER | FK → ACT_ID, Required | Owning action | R12 §2 |
| `CMT_TYPE` | Comment Type | ENUM | Required, Values: `comment`, `achievement`, `roadblock` | Nature of the comment | R12 §2 |
| `CMT_BODY` | Body | TEXT | Required | Rich text (HTML sanitized on server) | R12 §2 |
| `CMT_CREATED_BY` | Created By | INTEGER | FK → USR_ID, Required | Author | R12 §2 |
| `CMT_CREATED_AT` | Created At | DATETIME | Auto, Immutable | Creation timestamp | R12 §2 |
| `CMT_EDITED_AT` | Edited At | DATETIME | Optional | Set when body is modified | R12 §3 |
| `CMT_EDITED_BY` | Edited By | INTEGER | FK → USR_ID, Optional | Who last edited the comment | R12 §3 |
| `CMT_MEETING_INST_ID` | Meeting Occurrence | INTEGER | FK → MIN_ID, Optional | Links comment to the meeting occurrence where it was discussed | R19 §3.4 |
| `CMT_DELETED` | Soft Deleted | BOOLEAN | Required, Default: false | Soft delete flag | R12 §3 |

> **Edit/delete rights**: Admin, TeamLead, or the original author (`CMT_CREATED_BY`). Every edit and deletion writes an `ActionHistory` entry with `change_type = 'CommentEdited'` or `'CommentDeleted'`.

> **Meeting occurrence link**: When a comment is added from a meeting occurrence workspace, `CMT_MEETING_INST_ID` is set automatically. In the occurrence workspace, comments from the previous occurrence are shown read-only, and comments from the current occurrence are editable. Outside the meeting context, all comments display chronologically with occurrence badges.

---

## 3. Assignment Domain

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `ASG_ID` | Assignment ID | INTEGER | PK, Auto-increment | Unique assignment record | R01 §2 |
| `ASG_ACT_ID` | Action | INTEGER | FK → ACT_ID, Required | Assigned action | R01 §2 |
| `ASG_USR_ID` | User | INTEGER | FK → USR_ID, Required | Assigned user | R01 §2 |
| `ASG_ROLE` | Role | TEXT | Optional (legacy compatibility) | Legacy role token field kept for backward compatibility. Active action control is owner-based (`ACT_OWNER_ID`). | R03 §6 |
| `ASG_STATUS` | Status | ENUM | Required, Values: `Assigned`, `Reassigned`, Default: `Assigned` | Assignment tracking state. Assignment rows are active immediately when created. | R03 §1 |
| `ASG_DATE` | Assigned Date | DATETIME | Required, Auto | When assignment was made | R01 §2 |
| `ASG_BY` | Assigned By | INTEGER | FK → USR_ID, Required | Who made the assignment | R01 §2 |
| `ASG_EST_HOURS` | Estimated Hours | REAL | Optional, Default: NULL, ≥ 0 | Hours this person is expected to contribute to this action. Used for per-resource workload forecasting (§4.3 R05). Entered per assignee. | R05 §4.3 |

### 3.1 Assignment Roles

| Role | Multiplicity | Meaning |
|------|-------------|---------|
| **Lead** | Exactly 1 per action (mandatory) | Primary accountable person. Mapped to `ACT_OWNER_ID`. Auto-assigned to creator if not explicitly set. |

> **Lead is mandatory**: Every action MUST have exactly one Lead assignment at all times. On creation, if no `lead_user_id` is provided, the system auto-assigns the creator. Migration v8_4 backfills historical data. Legacy roles (Decide, Participate) have been removed — only Lead is managed.

### 3.2 Action Status — Canonical Vocabulary

**Persisted (DB CHECK constraint — 5 values):**

| DB Value | UI Display | Badge Color | Description |
|----------|-----------|-------------|-------------|
| `Open` | Not started | primary | Newly created, no work begun |
| `In Progress` | On-track | info | Active work underway, on schedule |
| `On Hold` | Late | warning | Paused — requires `hold_reason` |
| `Done` | Done | success | Completed — sets `act_actual_date` |
| `Cancelled` | Cancelled | danger | Abandoned — requires `cancel_reason` |

> **Legacy aliases** accepted on input and mapped automatically: `Completed` → `Done`, `Closed` → `Done`, `Ongoing` → `In Progress`. These are NEVER persisted.

### 3.3 Action Permission Matrix

| Operation | Admin | Creator (`ACT_CREATED_BY`) | Lead (`ACT_OWNER_ID`) | Meeting Creator | Assigned User | Team Leader | Other |
|-----------|:-----:|:--------------------------:|:---------------------:|:---------------:|:-------------:|:-----------:|:-----:|
| **View (public)** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **View (private)** | ✓ | ✓ | ✓ | — | ✓ (assigned) | — | — |
| **View (private meeting)** | ✓ | — | — | ✓ | ✓ (assigned) | — | — |
| **Edit** | ✓ | ✓ | ✓ | ✓ (meeting actions) | — | — | — |
| **Change status** | ✓ | ✓ | ✓ | ✓ (meeting actions) | — | — | — |
| **Delete** | ✓ | — | — | — | — | — | — |
| **Comment (create)** | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| **Edit/delete comment** | ✓ | — | — | — | — | — | Author only |

> **Comment access**: Only users with a direct relationship to the action can add comments — Admin, action creator, action lead/owner, any assigned user, or meeting participants (occurrence or series). Team leaders and other users without a relationship cannot comment. This prevents unsolicited comments on actions the user is not involved in.

> **Creator vs Lead**: The creator (`ACT_CREATED_BY`) is the user who opened the action. The lead (`ACT_OWNER_ID`) is the accountable assignee. Both have edit rights. They may be the same person (and usually are for non-meeting actions).

---

## 4. User Domain

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `USR_ID` | User ID | INTEGER | PK, Auto-increment | Unique user identifier | R01 §2 |
| `USR_USERNAME` | Username | VARCHAR(100) | Required, Unique, **Auto-generated (v2.7)** | Internal only — derived from employee_id or display_name | R01 §2 |
| `USR_PWD_HASH` | Password Hash | VARCHAR(255) | Required (Day 1), Nullable (V1.1 AD) | Bcrypt hashed password | R06 §2.1 |
| `USR_DISPLAY` | Display Name | VARCHAR(255) | Required | Full name (English) | R01 §2 |
| `USR_DISPLAY_CN` | Display Name CN | VARCHAR(255) | Optional | Chinese name 中文名 | R01 §2 |
| `USR_EMAIL` | Email | VARCHAR(255) | Required | Contact email for notifications | R01 §2 |
| `USR_EMPLOYEE_ID` | Employee ID | VARCHAR(6) | Optional, Unique | 6-digit employee badge number (v2.5). Used as login and display Employee ID in UI. | S50 |
| **UI Label** | Employee ID | | Must be unique for each user. Used for login. | |
| `usr_team_id` | Team | INTEGER | FK → tea_id, ~~Required~~ **Deprecated v2.6** | Legacy — kept for SQLite compat; use `t_user_team` | R01 §2 |
| `USR_TEAM_ID` | Team | INTEGER | FK → TEA_ID, **Deprecated** | Legacy — use `t_user_team` for M:N relationship | R01 §2 |
| `USR_ROLE` | Role | ENUM | Required, Values: `Admin`, `TeamLead`, `Member`, `ReadOnly` | System role (D22) | R06 §3.1 |
| `USR_ACTIVE` | Is Active | BOOLEAN | Required, Default: true | Account status | R01 §2 |
| `USR_LANG` | Preferred Language | ENUM | Required, Values: `en`, `zh`, Default: `en` | UI language preference (D23) | R01 §2 |
| `USR_AUTH_SRC` | Auth Source | ENUM | Required, Values: `local`, `ad`, Default: `local` | Authentication method (D76a) | R06 §2.1 |

---

## 5. Organization Domain

### 5.1 Team (**DEPRECATED v2.6** — see S52)

> **Note**: The Team entity is deprecated since v2.6. Teams are now the primary organisational unit. The `t_team` table remains in the database for SQLite compatibility but is no longer used by the application.

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `tea_id` | Team ID | INTEGER | PK, Auto-increment | Unique team | R01 §2 |
| `tea_name_en` | Name (EN) | VARCHAR(100) | Required | English name | R08 §2.1 |
| `tea_name_cn` | Name (CN) | VARCHAR(100) | Required | Chinese name 中文名 | R08 §2.1 |
| `tea_code` | Code | VARCHAR(10) | Required, Unique | Short code (e.g., `FAC`, `IE`) | R08 §2.1 |
| `tea_desc` | Description | TEXT | Optional | Team description | R08 §2.1 |
| `DEP_ACTIVE` | Is Active | BOOLEAN | Required, Default: true | Soft delete flag | R08 §5.1 |
| `DEP_SORT` | Sort Order | INTEGER | Required, Default: 0 | Display ordering | R08 §2.1 |

### 5.2 Team

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `TEA_ID` | Team ID | INTEGER | PK, Auto-increment | Unique team | R01 §2 |
| `TEA_CODE` | Code | VARCHAR(20) | Required, Unique | Short code (e.g., `FAC`, `IE`) — added v2.6 | S52 |
| `TEA_NAME_EN` | Name (EN) | VARCHAR(100) | Required | English name | R08 §2.2 |
| `TEA_NAME_CN` | Name (CN) | VARCHAR(100) | Required | Chinese name | R08 §2.2 |
| `TEA_DEPT_ID` | Team | INTEGER | FK → tea_id, ~~Required~~ **Deprecated v2.6** | Legacy — kept in DB for compatibility | R08 §2.2 |
| `TEA_ACTIVE` | Is Active | BOOLEAN | Required, Default: true | Soft delete flag | R08 §5.1 |
| `TEA_SORT` | Sort Order | INTEGER | Required, Default: 0 | Display ordering | R08 §2.2 |

### 5.3 Category (Strategic)

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `TOP_CODE` | Category Code | CHAR(3) | PK, Unique, Required | Unique 3-character code (e.g., 'KOM', 'TRN') | R01 §2 |
| `TOP_NAME_EN` | Name (EN) | VARCHAR(100) | Required | English name | R08 §2.3 |
| `TOP_NAME_CN` | Name (CN) | VARCHAR(100) | Required | Chinese name | R08 §2.3 |
| `TOP_DESC` | Description | TEXT | Optional | Category description | R08 §2.3 |
| `TOP_IS_GLOBAL` | Is Global | BOOLEAN | Required, Default: true | Always true — categories are not scoped to any team | R01 §4 |
| `TOP_ACTIVE` | Is Active | BOOLEAN | Required, Default: true | Soft delete flag | R08 §5.1 |
| `TOP_SORT` | Sort Order | INTEGER | Required, Default: 0 | Display ordering | R08 §2.3 |
| `TOP_CREATED_BY` | Created By | INTEGER | FK → USR_ID, Required | Admin or TeamLead who created the category | R01 §4 |

> **Access rule**: Create / Edit / Delete is restricted to `Admin` and `TeamLead`. `Member` and `ReadOnly` users see the Category list but cannot modify it.

---

## 6. Taxonomy Domain

### 6.1 Category

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `CAT_ID` | Category ID | INTEGER | PK, Auto-increment | Unique category | R01 §2 |
| `CAT_NAME_EN` | Name (EN) | VARCHAR(100) | Required | English label | R08 §3.1 |
| `CAT_NAME_CN` | Name (CN) | VARCHAR(100) | Required | Chinese label | R08 §3.1 |
| `CAT_COLOR` | Color | VARCHAR(7) | Optional | Hex color for UI badge | R08 §3.1 |
| `CAT_ACTIVE` | Is Active | BOOLEAN | Required, Default: true | Soft delete flag | R08 §5.1 |
| `CAT_SORT` | Sort Order | INTEGER | Required, Default: 0 | Display ordering | R08 §3.1 |

### 6.2 Tag (V1.1)

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `TAG_ID` | Tag ID | INTEGER | PK, Auto-increment | Unique tag | R08 §3.2 |
| `TAG_NAME` | Name | VARCHAR(50) | Required, Unique (case-insensitive) | Normalized to lowercase | R08 §3.2 |
| `TAG_CREATED_BY` | Created By | INTEGER | FK → USR_ID, Required | Tag creator | R08 §3.2 |
| `TAG_USAGE` | Usage Count | INTEGER | Required, Default: 0 | Auto-maintained count | R08 §3.2 |
| `TAG_ACTIVE` | Is Active | BOOLEAN | Required, Default: true | Soft delete flag | R08 §3.2 |

### 6.3 ActionTag (V1.1 — Junction)

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `ATG_ACT_ID` | Action | INTEGER | FK → ACT_ID, PK | Action reference | R08 §3.2 |
| `ATG_TAG_ID` | Tag | INTEGER | FK → TAG_ID, PK | Tag reference | R08 §3.2 |

---

## 7. Audit Domain

### 7.1 ActionHistory

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `AHI_ID` | History ID | INTEGER | PK, Auto-increment | Unique audit entry | R01 §2 |
| `AHI_ACT_ID` | Action | INTEGER | FK → ACT_ID, Required | Audited action | R01 §2 |
| `AHI_FIELD` | Field Changed | VARCHAR(100) | Required | Which field was modified | R01 §2 |
| `AHI_OLD_VAL` | Old Value | TEXT | Optional | Previous value | R01 §2 |
| `AHI_NEW_VAL` | New Value | TEXT | Optional | New value | R01 §2 |
| `AHI_CHG_BY` | Changed By | INTEGER | FK → USR_ID, Required | User who made change | R01 §2 |
| `AHI_CHG_DATE` | Changed Date | DATETIME | Required, Auto | Timestamp of change | R01 §2 |
| `AHI_CHG_TYPE` | Change Type | ENUM | Required, Values: `Created`, `Updated`, `StatusChange`, `Reassigned`, `Closed`, `CommentAdded`, `CommentEdited`, `CommentDeleted` | Nature of change | R01 §2 |

### 7.2 AuditLog (V1.1)

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `AUD_ID` | Audit ID | INTEGER | PK, Auto-increment | Unique audit log entry | R06 §5 |
| `AUD_TIMESTAMP` | Timestamp | DATETIME | Required, Auto | Event timestamp | R06 §5.2 |
| `AUD_USR_ID` | User | INTEGER | FK → USR_ID, Optional | Acting user | R06 §5.2 |
| `AUD_IP` | IP Address | VARCHAR(45) | Optional | Client IP | R06 §5.2 |
| `AUD_CATEGORY` | Category | ENUM | Required, Values: `Authentication`, `Authorization`, `DataModification`, `AdminOperation`, `ReportAccess` | Event category | R06 §5.1 |
| `AUD_EVENT` | Event Type | VARCHAR(100) | Required | Specific event | R06 §5.2 |
| `AUD_RESOURCE` | Resource Type | VARCHAR(50) | Optional | Entity type affected | R06 §5.2 |
| `AUD_RESOURCE_ID` | Resource ID | INTEGER | Optional | Entity ID affected | R06 §5.2 |
| `AUD_DETAILS` | Details | JSON | Optional | Structured event details | R06 §5.2 |
| `AUD_SUCCESS` | Success | BOOLEAN | Required | Whether operation succeeded | R06 §5.2 |

---

## 8. Import Domain

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `IML_ID` | Import Log ID | INTEGER | PK, Auto-increment | Unique import record | R07 §6 |
| `IML_FILE` | File Name | VARCHAR(255) | Required | Uploaded filename | R07 §6 |
| `IML_VERSION` | File Version | ENUM | Required, Values: `v1`, `v2`, `v3`, `v4` | Detected format | R07 §6 |
| `IML_BY` | Imported By | INTEGER | FK → USR_ID, Required | Admin who imported | R07 §6 |
| `IML_DATE` | Import Date | DATETIME | Required, Auto | Import timestamp | R07 §6 |
| `IML_TOTAL` | Total Rows | INTEGER | Required | Rows found in file | R07 §6 |
| `IML_IMPORTED` | Imported Count | INTEGER | Required | Successfully imported | R07 §6 |
| `IML_SKIPPED` | Skipped Count | INTEGER | Required | Rows skipped | R07 §6 |
| `IML_WARNINGS` | Warning Count | INTEGER | Required | Rows with warnings | R07 §6 |
| `IML_WARN_DETAIL` | Warning Details | JSON | Optional | Array of {row, field, message} | R07 §6 |
| `IML_STATUS` | Status | ENUM | Required, Values: `success`, `partial`, `failed` | Import outcome | R07 §6 |

---

## 9. Meeting Domain

### 9.0 MeetingSeries (V3.14 — Series Parent)

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `MTG_ID` | Series ID | INTEGER | PK, Auto-increment | Unique meeting series | R19 §2 |
| `MTG_TITLE` | Title | VARCHAR(255) | Required, min 2 chars | Series name (e.g., "Weekly Operations Review") | R19 §2 |
| `MTG_DESCRIPTION` | Description | TEXT | Optional | Series purpose / scope | R19 §2 |
| `MTG_TOPIC_ID` | Category | INTEGER | FK → TOP_ID, Optional | Default category for occurrences created from this series | R19 §2 |
| `MTG_CREATED_BY` | Created By | INTEGER | FK → USR_ID, Required | Series creator | R19 §2 |
| `MTG_CREATED_AT` | Created At | DATETIME | Auto, Immutable | Creation timestamp | R19 §2 |
| `MTG_VISIBILITY` | Visibility | ENUM | Required, Default: `public`, Values: `public`, `private` | Series-level access control. Private: info visible only to participants. | R19 §9 |

### 9.0a MeetingSeriesParticipant (V3.14 — Default Participant Template)

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `MSP_ID` | Series Participant ID | INTEGER | PK, Auto-increment | Unique record | R19 §2.2 |
| `MSP_MEETING_ID` | Series | INTEGER | FK → MTG_ID, Required | Which series this default participant belongs to | R19 §2.2 |
| `MSP_USER_ID` | User | INTEGER | FK → USR_ID, Required | Default participant | R19 §2.2 |
| `MSP_KIND` | Kind | ENUM | Required, Default: `Compulsory`, Values: `Compulsory`, `Optional` | Attendance classification | R19 §2.2 |
| `MSP_ADDED_BY` | Added By | INTEGER | FK → USR_ID, Required | Who added this default participant | R19 §2.2 |
| `MSP_ADDED_AT` | Added At | DATETIME | Auto, Immutable | When added | R19 §2.2 |

**Unique constraint**: (MSP_MEETING_ID, MSP_USER_ID) — a user can only be default participant once per series.

**Business rules**:
- Series creator is auto-added as a Compulsory participant.
- When creating a new occurrence from the series, all default participants are copied to `t_meeting_participant`.
- Changing defaults does not retroactively update existing occurrences.

### 9.1 MeetingInstance (MVP)

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `MIN_ID` | Meeting Instance ID | INTEGER | PK, Auto-increment | Unique meeting occurrence | R13 §1 |
| `MIN_TITLE` | Title | VARCHAR(255) | Required | Meeting name / label | R13 §1 |
| `MIN_TYPE` | Meeting Type | VARCHAR(100) | Optional | Free text — e.g., "Weekly review", "Kick-off", "Ad-hoc" | R13 §1 |
| `MIN_DATE` | Meeting Date | DATE | Required | Date of the specific occurrence | R13 §1 |
| `MIN_TOP_ID` | Category 1 | INTEGER | FK → TOP_ID, Optional | Optional primary category for the meeting | R13 §1 |
| `MIN_SECONDARY_TOP_ID` | Category 2 | INTEGER | FK → TOP_ID, Optional | Optional secondary category for the meeting; must differ from `MIN_TOP_ID` | R13 §1 |
| `MIN_CREATED_BY` | Created By | INTEGER | FK → USR_ID, Required | Who logged the meeting instance | R13 §1 |
| `MIN_CREATED_AT` | Created At | DATETIME | Auto, Immutable | Record creation timestamp | R13 §1 |
| `MIN_VISIBILITY` | Visibility | ENUM | Required, Default: `public`, Values: `public`, `private` | Inherited from series, overridable per occurrence. | R19 §9 |

### 9.2 MeetingSummary (V1.1 — File Upload)

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `MTG_ID` | Meeting Summary ID | INTEGER | PK, Auto-increment | Unique file record | R13 §2 |
| `MTG_INST_ID` | Meeting Instance | INTEGER | FK → MIN_ID, Required | Which meeting instance this file belongs to | R13 §2 |
| `MTG_FILE` | File Path | VARCHAR(500) | Required | Path to uploaded .xlsx document | R13 §2 |
| `MTG_UPLOADED_BY` | Uploaded By | INTEGER | FK → USR_ID, Required | Uploader | R13 §2 |
| `MTG_UPLOAD_DATE` | Upload Date | DATETIME | Required, Auto | Upload timestamp | R13 §2 |

### 9.3 MeetingOwner (V2.16 — Multi-owner permissions)

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `MOW_ID` | Meeting Owner ID | INTEGER | PK, Auto-increment | Unique owner grant record | v2.16 |
| `MOW_INSTANCE_ID` | Meeting Instance | INTEGER | FK → MIN_ID, Required | Which meeting instance this ownership applies to | v2.16 |
| `MOW_USER_ID` | Owner User | INTEGER | FK → USR_ID, Required | User granted owner permissions | v2.16 |
| `MOW_GRANTED_BY` | Granted By | INTEGER | FK → USR_ID, Required | Who granted ownership | v2.16 |
| `MOW_GRANTED_AT` | Granted At | DATETIME | Auto, Immutable | When ownership was granted | v2.16 |

**Unique constraint**: (MOW_INSTANCE_ID, MOW_USER_ID) — a user can only be owner once per meeting.

**Business rule**: Meeting owners (and Admins) can edit meeting properties, manage memos, and change the status of actions linked to that meeting. The meeting creator is automatically added as an owner.

### 9.4 MeetingDecision (V3.5)

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `MDC_ID` | Decision ID | INTEGER | PK, Auto-increment | Unique decision record | R17 §2 |
| `MDC_INSTANCE_ID` | Meeting Instance | INTEGER | FK → MIN_ID, Required | Meeting where the decision was recorded | R17 §2 |
| `MDC_TITLE` | Title | VARCHAR(255) | Required | Short summary of the decision | R17 §2 |
| `MDC_BODY` | Body | TEXT | Required | Core decision content/statement. Does not replace `MDC_CONTEXT`/`MDC_REASON` semantics. | R17 §2 |
| `MDC_CONTEXT` | Context | TEXT | Optional | Factual background, situation, scope, or trigger for the decision | R17 §2 |
| `MDC_REASON` | Why | TEXT | Optional | Rationale, trade-off, or justification for selecting the decision | R17 §2 |
| `MDC_STATUS` | Status | ENUM | Required, Default: `Published`, Values: `Published`, `Expired` | Decision lifecycle status | R17 §3 |
| `MDC_TOP_ID` | Category 1 | INTEGER | FK → TOP_ID, Optional | Optional primary category for the decision (defaults from meeting when omitted) | R17 §2 |
| `MDC_SECONDARY_TOP_ID` | Category 2 | INTEGER | FK → TOP_ID, Optional | Optional secondary category for the decision; must differ from `MDC_TOP_ID` | R17 §2 |
| `MDC_ACT_ID` | Linked Action | INTEGER | FK → ACT_ID, Optional | Action spawned by or related to this decision | R17 §2 |
| `MDC_TAGS` | Tags | VARCHAR(500) | Optional | Comma-separated keywords for search/retrieval; stored uppercase and rendered with `#` prefix in UI | R17 §5 |
| `MDC_DECIDED_AT` | Decided At | DATETIME | Optional, Default: meeting date | When the decision was formally agreed | R17 §2 |
| `MDC_CREATED_BY` | Created By | INTEGER | FK → USR_ID, Required | Must be meeting organizer or owner | R17 §4 |
| `MDC_CREATED_AT` | Created At | DATETIME | Auto, Immutable | Record creation timestamp | R17 §2 |
| `MDC_UPDATED_AT` | Updated At | DATETIME | Auto | Last modification timestamp | R17 §2 |
| `MDC_DELETED_AT` | Deleted At | DATETIME | Optional, Null = active | Soft-delete timestamp (Admin only) | R17 §4 |

**Business rules**:
- Only meeting organizers (creator or `t_meeting_owner`) and Admins can create/edit decisions.
- `MDC_TOP_ID` defaults to `MIN_TOP_ID` of the parent meeting instance when not explicitly set.
- `MDC_SECONDARY_TOP_ID` defaults to `MIN_SECONDARY_TOP_ID` of the parent meeting instance when not explicitly set.
- Full-text search via FTS5 virtual table on `MDC_TITLE` + `MDC_BODY` + `MDC_TAGS` for wiki/mini-RAG retrieval.
- `MDC_CONTEXT` and `MDC_REASON` are independent optional fields. `MDC_CONTEXT` MUST NOT be interpreted as equivalent to `MDC_REASON` in analytics.
- If one of `MDC_CONTEXT` or `MDC_REASON` is missing, analytics SHOULD treat the missing counterpart as unknown.
- Updating `MDC_TITLE` or `MDC_BODY` MUST create a prior-value snapshot row in `t_meeting_decision_revision`.

### 9.5 MeetingDecisionRevision (V3.5)

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `MDR_ID` | Decision Revision ID | INTEGER | PK, Auto-increment | Unique revision snapshot row | R17 §4.1 |
| `MDR_DECISION_ID` | Decision ID | INTEGER | FK → MDC_ID, Required | Decision whose previous content was captured | R17 §4.1 |
| `MDR_TITLE` | Previous Title | VARCHAR(255) | Required | Decision title before the edit was saved | R17 §4.1 |
| `MDR_BODY` | Previous Body | TEXT | Required | Decision body before the edit was saved | R17 §4.1 |
| `MDR_UPDATED_BY` | Revised By | INTEGER | FK → USR_ID, Optional | User who saved the edit that created this snapshot | R17 §4.1 |
| `MDR_UPDATED_AT` | Revised At | DATETIME | Auto | Timestamp when the revision snapshot was recorded | R17 §4.1 |

**Business rules**:
- Rows in `t_meeting_decision_revision` store the prior title/body state, not the post-update content.
- Revision snapshots are created only when `MDC_TITLE` or `MDC_BODY` changes.
- Revision history retrieval is ordered newest first by `MDR_UPDATED_AT`, then `MDR_ID`.

---

## 10. Notification Domain (V1.1)

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `NTR_ID` | Rule ID | INTEGER | PK, Auto-increment | Notification rule | R04 §3 |
| `NTR_EVENT` | Event Type | ENUM | Required | Trigger event | R04 §3 |
| `NTR_CHANNEL` | Channel | ENUM | Required, Values: `email`, `in_app` | Delivery channel | R04 §2 |
| `NTR_ACTIVE` | Is Active | BOOLEAN | Required, Default: true | Rule enabled | R04 §3 |
| `NTL_ID` | Log ID | INTEGER | PK, Auto-increment | Notification log entry | R04 §7 |
| `NTL_USR_ID` | User | INTEGER | FK → USR_ID, Required | Recipient | R04 §7 |
| `NTL_ACT_ID` | Action | INTEGER | FK → ACT_ID, Required | Related action | R04 §7 |
| `NTL_TYPE` | Type | ENUM | Required, Values: `email`, `in_app` | Delivery channel | R04 §7 |
| `NTL_EVENT` | Event | ENUM | Required | Trigger event type | R04 §7 |
| `NTL_SUBJECT` | Subject | VARCHAR(255) | Required | Message subject | R04 §7 |
| `NTL_PREVIEW` | Preview | VARCHAR(500) | Optional | Body preview text | R04 §7 |
| `NTL_SENT` | Sent Date | DATETIME | Required, Auto | When sent | R04 §7 |
| `NTL_READ` | Read Date | DATETIME | Optional | When read (null = unread) | R04 §7 |

---

## 11. Workflow Domain (V2)

> **Decisions**: D167–D180, R16. Design-time graph in JSON (O3); runtime tables normalized.

### 11.1 WorkflowTemplate (Design-Time)

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `WFT_ID` | Template ID | INTEGER | PK, Auto-increment | Unique workflow template | R16 §5 |
| `WFT_NAME_EN` | Name (EN) | VARCHAR(255) | Required | English template name | R16 §5 |
| `WFT_NAME_CN` | Name (CN) | VARCHAR(255) | Optional | Chinese template name | R16 §5 |
| `WFT_DESC` | Description | TEXT | Optional | Template description | R16 §5 |
| `WFT_VERSION` | Version | INTEGER | Required, Default: 1 | Incremented on each save; in-flight instances keep old version | R16 §7 |
| `WFT_IS_DEFAULT` | Is Default | BOOLEAN | Required, Default: false | True for "Simple Action" default template | R16 §4.3 |
| `WFT_TYPE` | Type | ENUM | Required, Values: `action`, `request` | `action` = bound to existing actions; `request` = standalone (D167) | R16 §4.1 |
| `WFT_ACTIVE` | Is Active | BOOLEAN | Required, Default: true | Active/draft toggle | R16 §5 |
| `WFT_GRAPH` | Graph JSON | TEXT (JSON) | Required, Default: `'{}'` | Full workflow definition: steps, transitions, triggers, fields, bindings (D176/O3). See R16 §5.3 for schema. | R16 §5.3 |
| `WFT_CREATED_BY` | Created By | INTEGER | FK → USR_ID, Required | Template author | R16 §5 |
| `WFT_CREATED_AT` | Created At | DATETIME | Auto, Immutable | Creation timestamp | R16 §5 |
| `WFT_UPDATED_AT` | Updated At | DATETIME | Optional | Last modification | R16 §5 |

### 11.2 WorkflowInstance (Runtime)

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `WFI_ID` | Instance ID | INTEGER | PK, Auto-increment | Unique running instance | R16 §5 |
| `WFI_TEMPLATE_ID` | Template | INTEGER | FK → WFT_ID, Required | Which template this instance runs | R16 §5 |
| `WFI_ACTION_ID` | Action | INTEGER | FK → ACT_ID, Optional, Unique when present | Optional supporting action for compatibility/runtime integration. Standalone request workflows may keep this field null. | R16 §5 |
| `WFI_STATUS` | Status | ENUM | Required, Values: `Active`, `Completed`, `Cancelled`, `Paused`, `WaitingForChild` | Instance lifecycle | S70, S73 |
| `WFI_STARTED_AT` | Started At | DATETIME | Auto, Immutable | When the instance was created | R16 §5 |
| `WFI_COMPLETED_AT` | Completed At | DATETIME | Optional | Set when status → Completed | R16 §5 |

### 11.3 WorkflowStepInstance (Runtime)

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `WSI_ID` | Step Instance ID | INTEGER | PK, Auto-increment | Unique step execution record | R16 §5 |
| `WSI_INSTANCE_ID` | Instance | INTEGER | FK → WFI_ID, Required | Parent workflow instance | R16 §5 |
| `WSI_STEP_KEY` | Step Key | TEXT | Required | Key into `wft_graph.steps` (e.g., `"hse_validation"`) | R16 §5 |
| `WSI_STATUS` | Status | ENUM | Required, Values: `Pending`, `Accepted`, `Completed`, `Skipped`, `Rejected`, `Paused`, `WaitingForChild` | Step lifecycle | S70, S72, S73 |
| `WSI_ASSIGNEE_ID` | Assignee | INTEGER | FK → USR_ID, Optional | User working on this step | R16 §5 |
| `WSI_ENTERED_AT` | Entered At | DATETIME | Optional | When step became Active | R16 §5 |
| `WSI_ACCEPTED_AT` | Accepted At | DATETIME | Optional | When assignee explicitly accepted the step | S70 §3 |
| `WSI_COMPLETED_AT` | Completed At | DATETIME | Optional | When step was completed | R16 §5 |
| `WSI_SLA_DEADLINE` | SLA Deadline | DATETIME | Optional | Computed from `wft_graph.steps[].sla_hours` + `wsi_entered_at` | R16 §5 |
| `WSI_COMMENT` | Comment | TEXT | Optional | Comment when completing/rejecting step | R16 §5 |
| `WSI_ESCALATED_AT` | Escalated At | DATETIME | Optional | When SLA/manual escalation changed routing or assignee | S73 §5 |

### 11.4 WorkflowStepFieldValue (Runtime Form Data)

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `SFV_ID` | Field Value ID | INTEGER | PK, Auto-increment | Unique form value | R16 §5 |
| `SFV_STEP_INST_ID` | Step Instance | INTEGER | FK → WSI_ID, Required | Which step this value belongs to | R16 §5 |
| `SFV_FIELD_KEY` | Field Key | TEXT | Required | Key into `wft_graph.steps[].fields` (e.g., `"badge_code"`) | R16 §5 |
| `SFV_VALUE` | Value | TEXT | Optional | Stored as text; JSON for checklist values | R16 §5 |
| `SFV_FILLED_BY` | Filled By | INTEGER | FK → USR_ID, Optional | User who entered the value | R16 §5 |
| `SFV_FILLED_AT` | Filled At | DATETIME | Auto | When the value was entered | R16 §5 |

### 11.4A WorkflowStepAttachment (Runtime Attachment Data)

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `WSA_ID` | Step Attachment ID | INTEGER | PK, Auto-increment | Unique attachment record | S73 §8 |
| `WSA_STEP_INST_ID` | Step Instance | INTEGER | FK → WSI_ID, Required | Step instance owning the file | S73 §8 |
| `WSA_ACTION_ID` | Action | INTEGER | FK → ACT_ID, Required | Parent action/workflow request for visibility and audit joins | S73 §8 |
| `WSA_FILENAME` | File Name | TEXT | Required | Original uploaded filename | S73 §8 |
| `WSA_STORAGE_PATH` | Storage Path | TEXT | Required, Unique | Internal storage path or object key | S73 §8 |
| `WSA_MIME_TYPE` | MIME Type | TEXT | Required | Detected/stored MIME type after allowlist validation | S73 §8 |
| `WSA_SIZE_BYTES` | File Size | INTEGER | Required, >= 0 | Uploaded file size in bytes | S73 §8 |
| `WSA_DESCRIPTION` | Description | TEXT | Optional | Short user-supplied description of the evidence/document | S73 §8 |
| `WSA_UPLOADED_BY` | Uploaded By | INTEGER | FK → USR_ID, Required | User who uploaded the file | S73 §8 |
| `WSA_UPLOADED_AT` | Uploaded At | DATETIME | Auto, Immutable | Upload timestamp | S73 §8 |
| `WSA_DELETED_AT` | Deleted At | DATETIME | Optional | Soft-delete timestamp | S73 §8 |

### 11.5 WorkflowApproval (V2.1)

| Code | Label | Format | Constraints | Description | Source |
|------|-------|--------|-------------|-------------|--------|
| `WAP_ID` | Approval ID | INTEGER | PK, Auto-increment | Unique approval record | R16 §5 |
| `WAP_STEP_INST_ID` | Step Instance | INTEGER | FK → WSI_ID, Required | The approval gate step | R16 §5 |
| `WAP_APPROVER_ID` | Approver | INTEGER | FK → USR_ID, Required | Who approved/rejected | R16 §5 |
| `WAP_DECISION` | Decision | ENUM | Required, Values: `Approved`, `Rejected`, `Abstained` | Approval outcome | R16 §5 |
| `WAP_COMMENT` | Comment | TEXT | Optional | Justification for decision | R16 §5 |
| `WAP_DECIDED_AT` | Decided At | DATETIME | Auto | When decision was made | R16 §5 |

## 12. Enumeration Reference

### 12.1 Action Status Values

| Value | Label EN | Label CN | Color | Terminal? |
|-------|----------|----------|-------|-----------|
| `Open` | Open | 待处理 | Blue #2563EB | No |
| `In Progress` | In Progress | 进行中 | Cyan #0891B2 | No |
| `On Hold` | On Hold | 暂停 | Gray #6B7280 | No |
| `Under Review` | Under Review | 审核中 | Purple #7C3AED | No |
| `Done` | Done | 完成 | Green #16A34A | Yes |
| `Postponed` | Postponed | 推迟 | Amber #D97706 | No |
| `Cancelled` | Cancelled | 取消 | Slate #94A3B8 | Yes |

### 12.2 Priority Values

> **Note:** Priority is retained internally but **hidden from the Meeting Action Edit modal**. It is only editable from the standalone Action Detail page.

| Value | Label EN | Label CN | Color | SLA (D30) |
|-------|----------|----------|-------|-----------|
| `Critical` | Critical | 紧急 | Red #DC2626 | 3 business days |
| `High` | High | 高 | Orange #D97706 | 7 business days |
| `Medium` | Medium | 中 | Yellow #EAB308 | 14 business days |
| `Low` | Low | 低 | Green #16A34A | 30 business days |

### 12.3 Escalation Values

| Value | Label EN | Label CN |
|-------|----------|----------|
| `Normal` | Normal | 正常 |
| `Escalated` | Escalated | 升级 |
| `WAR` | WAR | 战报 |

### 12.4 Assignment Role Values

| Value | Label EN | Label CN | Constraint |
|-------|----------|----------|------------|
| `Lead` | Lead | 负责人 | Exactly 1 per action (accountable role; mapped to `ACT_OWNER_ID`) |

### 12.5 User Role Values

| Value | Label EN | Label CN | MVP Behavior |
|-------|----------|----------|-------------|
| `Admin` | Admin | 管理员 | Full access |
| `TeamLead` | Team Lead | 组长 | Treated as Member in MVP |
| `Member` | Member | 成员 | Standard access |
| `ReadOnly` | Read Only | 只读 | Treated as Member in MVP |

### 12.6 Workflow Instance Status Values (V3)

| Value | Label EN | Label CN |
|-------|----------|----------|
| `Active` | Active | 进行中 |
| `Completed` | Completed | 已完成 |
| `Cancelled` | Cancelled | 已取消 |
| `Paused` | Paused | 已暂停 |
| `WaitingForChild` | Waiting for Child | 等待子流程 |

### 12.7 Workflow Step Instance Status Values (V3)

| Value | Label EN | Label CN |
|-------|----------|----------|
| `Pending` | Pending | 待处理 |
| `Accepted` | Accepted | 已接受 |
| `Completed` | Completed | 已完成 |
| `Skipped` | Skipped | 已跳过 |
| `Rejected` | Rejected | 已拒绝 |
| `Paused` | Paused | 已暂停 |
| `WaitingForChild` | Waiting for Child | 等待子流程 |

### 12.8 Workflow Step Type Values (V3)

| Value | Label EN | Label CN | Description |
|-------|----------|----------|-------------|
| `Task` | Task | 任务 | Normal work step with form fields and assignee |
| `Approval` | Approval | 审批 | Gate requiring approval decision (V2.1) |
| `Gateway` | Gateway | 网关 | Conditional routing step driven by decision-table rules |
| `Service` | Service | 服务 | Engine-executed service handler with mapped inputs/outputs |
| `Notification` | Notification | 通知 | Engine step that sends in-app notification and auto-advances |
| `Timer` | Timer | 计时器 | Delayed system step for timeout and escalation behavior |
| `Join` | Join | 合并 | Synchronization point for parallel branches |
| `End` | End | 结束 | Terminal step — workflow completes |

### 12.9 Workflow Template Type Values (V2)

| Value | Label EN | Label CN | Description |
|-------|----------|----------|-------------|
| `action` | Action-Bound | 关联操作 | Workflow attached to an existing action |
| `request` | Standalone Request | 独立请求 | Workflow request started from the workflow area; may run without creating or binding an action |

### 12.10 Approval Decision Values (V2.1)

| Value | Label EN | Label CN |
|-------|----------|----------|
| `Approved` | Approved | 已批准 |
| `Rejected` | Rejected | 已拒绝 |
| `Abstained` | Abstained | 弃权 |

### 12.11 Meeting Decision Status Values (V3.5)

| Value | Label EN | Label CN | Description |
|-------|----------|----------|-------------|
| `Published` | Published | 已发布 | Decision is active and visible in the knowledge base |
| `Expired` | Expired | 已过期 | Decision is no longer active (superseded/retired/archive state) |

---

## 13. Seed Data Reference

### 13.1 Teams (12)

| Code | EN | CN |
|------|----|----|
| FAC | Facility | 设施 |
| IE | Industrial Engineering | 工业工程 |
| CI | Continuous Improvement | 持续改善 |
| QA | Quality | 质量 |
| HP | Heavy Parts | 重件 |
| WH | Warehouse | 仓库 |
| LOG | Logistic | 物流 |
| SRC | Sourcing | 寻源 |
| PROC | Procurement | 采购 |
| MM | Material Management | 物料管理 |
| ESL | Equipment Supply Leader | 设备供应主管 |
| PLAN | Planning | 计划 |

### 13.2 Categories (8)

| EN | CN | Color |
|----|----|-------|
| Supplier Issue | 供应商问题 | #E74C3C |
| Internal Process | 内部流程 | #3498DB |
| Design Change | 设计变更 | #9B59B6 |
| Quality Issue | 质量问题 | #E67E22 |
| Material Shortage | 物料短缺 | #F39C12 |
| System/Tool | 系统/工具 | #2ECC71 |
| Training | 培训 | #1ABC9C |
| General | 通用 | #95A5A6 |
