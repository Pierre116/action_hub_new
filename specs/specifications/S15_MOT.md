# ActionHub — Organizational Process Model (MOT)

> **Level**: L2 — Organizational  
> **Merise Phase**: Modèle Organisationnel des Traitements  
> **Source**: S11_MCT.md, S05_data_dictionary.md, R03_assignment_workflow.md, R06_security.md  
> **Purpose**: For each MCT operation, specify **who** performs it, **where** it executes, **when** it happens

---

## 1. Process: Authentication

**Goal**: User logs in, obtains server-side session, accesses ActionHub.

| Step | Operation | Actor | Nature | Place | Datapoints | Sync |
|------|-----------|-------|--------|-------|------------|------|
| 1 | Submit credentials | End User | Manual (Write) | Browser → Login page | USR_USERNAME, password | Human → Machine |
| 2 | OP01: Authenticate | System | Real-time (Sync) | Backend Service | USR_PWD_HASH (bcrypt verify) | Machine Internal |
| 3 | Create session | System | Real-time (Sync) | Backend Service | Session ID (256-bit random), HttpOnly cookie | Machine → Human |
| 4 | Redirect to dashboard | System | Real-time | Browser | OP07 trigger | Machine → Human |

**Organizational Rules:**
- Step 2: 5 failed attempts in 15 minutes → 30-minute lockout (D78)
- Step 3: Session timeout = 8 hours (business day) (D77)
- Step 3: Cookie flags: HttpOnly, Secure (if HTTPS), SameSite=Lax (D84)
- Concurrent sessions allowed (same user, multiple browsers)

---

## 2. Process: User Management

**Goal**: Admin creates and manages user accounts.

| Step | Operation | Actor | Nature | Place | Datapoints | Sync |
|------|-----------|-------|--------|-------|------------|------|
| 1 | Navigate to Admin > Users | Admin | Manual (Read) | Browser | — | Human → Machine |
| 2 | Fill user creation form | Admin | Manual (Write) | Browser | USR_USERNAME, password, USR_DISPLAY, USR_EMAIL, usr_team_id, USR_ROLE | Human Action |
| 3 | OP02: Create User | System | Real-time (Sync) | Backend Service | Bcrypt hash, User record | Machine Internal |
| 4 | Confirm creation | System | Real-time | Browser | Toast "User created" | Machine → Human |

**Organizational Rules:**
- Step 2: Admin-only access (binary Admin/Member check in MVP)
- Step 3: Password hashed with bcrypt before storage
- Step 3: Default USR_LANG = `en`, USR_AUTH_SRC = `local`, USR_ACTIVE = true

---

## 3. Process: Action Creation

**Goal**: User creates a new action item, either via full form or quick-capture.

### 3.1 Full Form Path

| Step | Operation | Actor | Nature | Place | Datapoints | Sync |
|------|-----------|-------|--------|-------|------------|------|
| 1 | Navigate to New Action | Member+ | Manual | Browser | — | Human → Machine |
| 2 | Load form data (depts, teams, users) | System | Real-time (Read) | Backend | DEP list, TEA list, USR list, CAT list | Machine → Human |
| 3 | Fill action form | Member+ | Manual (Write) | Browser | ACT_TITLE, ACT_DESC, act_team_id, ACT_DEADLINE, ACT_PRIORITY, Lead, Delegates | Human Action |
| 4 | Submit form | Member+ | Manual | Browser → Backend | Form data | Human → Machine |
| 5 | OP03: Create Action | System | Real-time (Sync) | Backend Service | Auto-generate ACT_REF, set defaults | Machine Internal |
| 6 | OP06: Assign Users | System | Real-time (Sync) | Backend Service | Create Assignment records (auto-Accepted) | Machine Internal |
| 7 | Log creation | System | Real-time (Sync) | Backend Service | ACTION_HISTORY entry (Created) | Machine Internal |
| 8 | Redirect to action detail | System | Real-time | Browser | ACT_ID | Machine → Human |

### 3.2 Quick-Capture Path

| Step | Operation | Actor | Nature | Place | Datapoints | Sync |
|------|-----------|-------|--------|-------|------------|------|
| 1 | Click "+" FAB | Member+ | Manual | Browser (any page) | — | Human Action |
| 2 | Show modal form | System | Real-time | Browser (overlay) | Dept pre-filled from user profile | Machine → Human |
| 3 | Fill minimal fields | Member+ | Manual (Write) | Browser | ACT_TITLE, ACT_DEADLINE, ACT_PRIORITY (default: Medium) | Human Action |
| 4 | Submit | Member+ | Manual | Browser → Backend | Minimal form data | Human → Machine |
| 5 | OP03: Create Action | System | Real-time (Sync) | Backend Service | Lead = creator (D27, D41) | Machine Internal |
| 6 | Close modal + toast | System | Real-time | Browser | "Action created — ACT-2026-XXXXX" | Machine → Human |

**Organizational Rules:**
- Step 3 (full form): Cascading dropdowns: Team → filtered Teams → filtered Categories
- Step 3 (quick-capture): Team pre-filled from usr_team_id
- Step 5: ACT_CREATED_BY = session user, ACT_SOURCE = `Manual`

---

## 4. Process: Action Status Update

**Goal**: User changes action status from list/detail UI (modal-based control) backed by OP05 API validation.

### 4.1 UI + API Path (Current MVP)

| Step | Operation | Actor | Nature | Place | Datapoints | Sync |
|------|-----------|-------|--------|-------|------------|------|
| 1 | Click status badge/control on list or detail | Authenticated user | Manual | Browser | ACT_ID, current status | Human Action |
| 2 | Validate transition and required fields | System | Real-time (Sync) | Backend Service | VALID_TRANSITIONS[current] + payload | Machine Internal |
| 3 | Apply status + side effects | System | Real-time (Sync) | Backend Service | status update, ACT_ACTUAL_DATE / hold/cancel/postpone fields | Machine Internal |
| 4 | Log action history | System | Real-time (Sync) | Backend Service | ACTION_HISTORY status event | Machine Internal |
| 5 | Refresh list row or detail section | System | Real-time | Browser | Updated status badge + latest history | Machine → Human |

### 4.2 Future UX Enhancement (Optional)

| Step | Operation | Actor | Nature | Place | Datapoints | Sync |
|------|-----------|-------|--------|-------|------------|------|
| 1 | Upgrade modal UX to inline dropdown/embedded form | Any User | Manual | Browser / Action List or Detail | ACT_ID | Human Action |
| 2 | Render transitions contextually | System | Real-time | Browser | VALID_TRANSITIONS[current] | Machine → Human |
| 3 | Keep reason/date fields inline in form | Any User | Manual | Browser | Status + reason/date | Human → Machine |
| 4 | OP05: Transition Status | System | Real-time (Sync) | Backend Service | Status + side effects + ACTION_HISTORY | Machine Internal |
| 5 | Apply richer micro-interactions | System | Real-time | Browser | Optional animation/polish | Machine → Human |

**Organizational Rules:**
- Step 2: Only valid transitions shown (no invalid options)
- Step 3: `→ On Hold` requires hold_reason text; `→ Cancelled` requires cancel_reason
- Step 4: `→ Done` auto-sets ACT_ACTUAL_DATE = now
- Step 5: MVP currently uses standard UI refresh only; animation is optional polish for later increment

---

## 5. Process: Data Import

**Goal**: Admin imports historical action data from Excel logbooks.

| Step | Operation | Actor | Nature | Place | Datapoints | Sync |
|------|-----------|-------|--------|-------|------------|------|
| 1 | Navigate to Admin > Import | Admin | Manual | Browser | — | Human → Machine |
| 2 | Upload .xlsx file (drag-drop or browse) | Admin | Manual (Write) | Browser | File binary (.xlsx, max 10MB) | Human → Machine |
| 3 | OP11: Detect Format | System | Real-time (Sync) | Backend Service | Sheet name + header analysis → version (v1/v2/v3/v4) | Machine Internal |
| 4 | Generate preview + mapping | System | Real-time | Backend → Browser | First 20 rows, column mapping, unresolved owners | Machine → Human |
| 5 | Resolve unresolved owners | Admin | Manual | Browser | Map unknown names to existing users or skip | Human Action |
| 6 | Resolve unresolved teams | Admin | Manual | Browser | Map or skip unknown teams | Human Action |
| 7 | Review duplicates | Admin | Manual | Browser | Accept or skip flagged duplicates | Human Action |
| 8 | Click "Import" | Admin | Manual | Browser → Backend | Confirmed mappings | Human → Machine |
| 9 | OP12: Execute Import | System | Real-time (Sync) | Backend Service | Create Action + Assignment + History records in batch | Machine Internal |
| 10 | Display summary | System | Real-time | Browser | "86 imported, 2 skipped, 1 duplicate" | Machine → Human |

**Organizational Rules:**
- Step 3: Detection by sheet name + header row pattern (D91)
- Step 5: User name resolution: exact match against USR_DISPLAY / USR_DISPLAY_CN (D89)
- Step 7: Duplicate detection: exact title + team match (D163)
- Step 9: ACT_SOURCE = `Import`, ACT_SOURCE_FILE = filename
- Import priority order: v3 + v4 first (422 rows = most value), then v1 + v2

### 5.1 Import Rollback (OP13)

**Goal**: Admin reverses a batch import that introduced incorrect data.

| Step | Operation | Actor | Nature | Place | Datapoints | Sync |
|------|-----------|-------|--------|-------|------------|------|
| 1 | Navigate to Admin > Import History | Admin | Manual (Read) | Browser | — | Human → Machine |
| 2 | Select import record | Admin | Manual | Browser | IML_ID, IML_FILENAME, IML_IMPORTED count | Human → Machine |
| 3 | Click "Rollback" + confirm dialog | Admin | Manual (Write) | Browser | "Are you sure? This will delete N actions." | Human → Machine |
| 4 | OP13: Rollback Import | System | Real-time (Sync) | Backend Service | Delete all t_action WHERE act_source_ref = IML_ID + cascading assignments/history | Machine Internal |
| 5 | Update import log status | System | Real-time (Sync) | Backend Service | IML_STATUS = 'Rolled Back' | Machine Internal |
| 6 | Display confirmation | System | Real-time | Browser | Toast "Import rolled back: N actions removed" | Machine → Human |

**Organizational Rules:**
- Step 3: Confirmation dialog with count of actions to be deleted (D98)
- Step 4: Rollback is atomic — all-or-nothing within a single transaction
- Step 4: Cascading deletes: assignments, history entries, tags linked to imported actions
- Step 5: Rolled-back imports remain visible in Import History with status = 'Rolled Back'

---

## 6. Process: Escalation & Assignment Status (OP16)

**Goal**: Define target escalation and assignment-response workflows; this section is deferred beyond current MVP baseline.

### 6.1 Manual Escalation (Deferred)

| Step | Operation | Actor | Nature | Place | Datapoints | Sync |
|------|-----------|-------|--------|-------|------------|------|
| 1 | View overdue or critical action | TeamLead/Admin | Manual | Browser / Action Detail | ACT_ID | Human → Machine |
| 2 | Click "Escalate" | TeamLead/Admin | Manual | Browser | — | Human → Machine |
| 3 | Select escalation level | TeamLead/Admin | Manual | Browser | `Escalated` or `WAR` (D165) | Human → Machine |
| 4 | OP16: Escalate Action | System | Real-time (Sync) | Backend Service | ACT_ESCALATION_LEVEL updated, history logged | Machine Internal |
| 5 | Update action header badge | System | Real-time | Browser | Red "ESCALATED" or "WAR" badge | Machine → Human |

### 6.2 Assignment Response (V1.1)

| Step | Operation | Actor | Nature | Place | Datapoints | Sync |
|------|-----------|-------|--------|-------|------------|------|
| 1 | User sees assignment notification | Assignee | Manual | Browser / Notification | ASG_ID, action title | Human → Machine |
| 2 | View assignment detail | Assignee | Manual | Browser / Action Detail | Assignment role, action description | Machine → Human |
| 3 | Accept or decline | Assignee | Manual | Browser | Accept / Decline + decline_reason | Human → Machine |
| 4 | Update assignment status | System | Real-time (Sync) | Backend Service | ASG_STATUS = 'Accepted'/'Declined', ASG_RESPONSE_DATE = now | Machine Internal |
| 5 | If declined, notify action Lead | System | Real-time | Backend Service | Notification to Lead for reassignment | Machine → Human |

**Organizational Rules:**
- Step 3 (6.1): Only TeamLead or Admin can escalate
- Step 3 (6.2): Decline requires decline_reason text (min 10 chars)
- Step 5 (6.2): Declined assignment triggers notification for Lead to reassign

---

## 7. Process: Dashboard & Reporting

**Goal**: Users view dashboards and export data.

### 6.1 Personal Dashboard

| Step | Operation | Actor | Nature | Place | Datapoints | Sync |
|------|-----------|-------|--------|-------|------------|------|
| 1 | Login / navigate to Dashboard | Any User | Auto/Manual | Browser | USR_ID from session | Human → Machine |
| 2 | OP07: Load Personal Dashboard | System | Real-time (Sync) | Backend Service | 4 queries: overdue, due this week, completed, KPIs | Machine Internal |
| 3 | Render dashboard | System | Real-time | Browser | Red cards (overdue), amber cards (due soon), green cards (completed), KPI bar | Machine → Human |
| 4 | Navigate to action details for follow-up | Any User | Manual | Browser | Open action record for context/history | Human → Machine |

### 6.2 Team Dashboard

| Step | Operation | Actor | Nature | Place | Datapoints | Sync |
|------|-----------|-------|--------|-------|------------|------|
| 1 | Navigate to Dept Dashboard | Any User | Manual | Browser | Select team | Human → Machine |
| 2 | OP08: Load Team Dashboard | System | Real-time (Sync) | Backend Service | KPI aggregation queries | Machine Internal |
| 3 | Render dashboard | System | Real-time | Browser | KPI cards, status badges, overdue table | Machine → Human |

### 6.3 Excel Export

| Step | Operation | Actor | Nature | Place | Datapoints | Sync |
|------|-----------|-------|--------|-------|------------|------|
| 1 | Click "Export to Excel" | Any User | Manual | Browser | Current filter state | Human → Machine |
| 2 | OP10: Export to Excel | System | Real-time (Sync) | Backend Service | Generate .xlsx with openpyxl | Machine Internal |
| 3 | Browser download | System | Real-time | Browser | File download prompt | Machine → Human |

### 7.4 Category Dashboard

| Step | Operation | Actor | Nature | Place | Datapoints | Sync |
|------|-----------|-------|--------|-------|------------|------|
| 1 | Navigate to Category Dashboard | Any User | Manual | Browser | Select Category | Human → Machine |
| 2 | OP17: Load Category KPIs | System | Real-time (Sync) | Backend Service | K50–K54 aggregation queries by category_id across primary + secondary category links | Machine Internal |
| 3 | Render KPI cards | System | Real-time | Browser | Open (blue), Overdue (red), Done (green), On-Time Rate, Workload/user | Machine → Human |
| 4 | Filter action list by category | Any User | Manual | Browser | Select status / date range | Human → Machine |
| 5 | Render filtered list | System | Real-time | Backend → Browser | Paginated action rows scoped to category | Machine → Human |

**Organizational Rules:**
- Step 1: Categories are global — any authenticated user can view any Category Dashboard
- Step 3: Overdue card = red if overdue_count > 0, amber if overdue_count = 0 but open_count > 0, green if all Done
- Step 4: Filter state preserved in URL query parameters

---

## 8. Process: Action Editing

| Step | Operation | Actor | Nature | Place | Datapoints | Sync |
|------|-----------|-------|--------|-------|------------|------|
| 1 | Click "Edit" on action detail | Lead/Admin | Manual | Browser | ACT_ID | Human → Machine |
| 2 | Load edit form with current values | System | Real-time | Backend → Browser | All ACT_* fields pre-filled | Machine → Human |
| 3 | Modify fields | Lead/Admin | Manual (Write) | Browser | Changed fields only | Human Action |
| 4 | Submit | Lead/Admin | Manual | Browser → Backend | Changed field set | Human → Machine |
| 5 | OP04: Update Action | System | Real-time (Sync) | Backend Service | Per-field ACTION_HISTORY entries | Machine Internal |
| 6 | Redirect to action detail | System | Real-time | Browser | Updated field values | Machine → Human |

**Organizational Rules:**
- Step 1: Only Lead or Admin may edit core action fields
- Step 5: Each changed field produces an individual ActionHistory record (field, old_value, new_value)
- Structured comments (Comment/Achievement/Roadblock) are managed in §9 below

---

## 9. Process: Comment Management

**Goal**: Authenticated users post, edit, and soft-delete typed comments on actions.

### 9.1 Post Comment

| Step | Operation | Actor | Nature | Place | Datapoints | Sync |
|------|-----------|-------|--------|-------|------------|------|
| 1 | Click comment area on action detail | Any authenticated user | Manual | Browser / Action Detail | ACT_ID | Human → Machine |
| 2 | Select comment type + enter rich text | Any authenticated user | Manual (Write) | Browser | CMT_TYPE (Comment or Achievement or Roadblock), CMT_BODY | Human Action |
| 3 | Submit comment | Any authenticated user | Manual | Browser → Backend | CMT_TYPE, CMT_BODY, parent refs | Human → Machine |
| 4 | OP18: Create Comment | System | Real-time (Sync) | Backend Service | Insert t_comment, log ActionHistory (CommentAdded) | Machine Internal |
| 5 | Append comment to thread | System | Real-time | Browser | New comment card in thread | Machine → Human |

### 9.2 Edit Comment

| Step | Operation | Actor | Nature | Place | Datapoints | Sync |
|------|-----------|-------|--------|-------|------------|------|
| 1 | Click "Edit" on own comment | Admin/TeamLead/Author | Manual | Browser | CMT_ID | Human → Machine |
| 2 | Modify rich-text body | Admin/TeamLead/Author | Manual (Write) | Browser (inline) | Updated CMT_BODY | Human Action |
| 3 | Save edit | Admin/TeamLead/Author | Manual | Browser → Backend | CMT_ID, new CMT_BODY | Human → Machine |
| 4 | OP19: Update Comment | System | Real-time (Sync) | Backend Service | Update CMT_BODY, set CMT_EDITED_AT, CMT_EDITED_BY; log ActionHistory (CommentEdited) | Machine Internal |
| 5 | Re-render comment with "Edited" badge | System | Real-time | Browser | (edited) label shown next to timestamp | Machine → Human |

### 9.3 Delete Comment (Soft)

| Step | Operation | Actor | Nature | Place | Datapoints | Sync |
|------|-----------|-------|--------|-------|------------|------|
| 1 | Click "Delete" on comment | Admin/TeamLead/Author | Manual | Browser | CMT_ID | Human → Machine |
| 2 | Confirm deletion dialog | Admin/TeamLead/Author | Manual | Browser | "Remove this comment?" | Human → Machine |
| 3 | OP20: Soft-Delete Comment | System | Real-time (Sync) | Backend Service | Set CMT_IS_DELETED = 1; log ActionHistory (CommentDeleted) | Machine Internal |
| 4 | Replace comment text with placeholder | System | Real-time | Browser | "Comment removed" | Machine → Human |

**Organizational Rules:**
- §9.1: All authenticated users can post comments; no restriction by role
- §9.2/9.3: Only Admin, TeamLead, or the comment author may edit/delete
- CMT_TYPE must be one of `Comment`, `Achievement`, `Roadblock` (CHECK constraint)
- CMT_BODY: min 1 char, max 2000 chars
- Soft delete: deleted comments display placeholder; physical records retained for audit

---

## 10. Process: Action Hierarchy Management

**Status**: Retired from active scope.

---

## 11. Process: Category Management

**Goal**: Admin or TeamLead creates and manages global Categories used to group actions.

| Step | Operation | Actor | Nature | Place | Datapoints | Sync |
|------|-----------|-------|--------|-------|------------|------|
| 1 | Navigate to Admin > Categories | Admin/TeamLead | Manual | Browser | — | Human → Machine |
| 2 | Click "New Category" | Admin/TeamLead | Manual | Browser | — | Human → Machine |
| 3 | Fill category form | Admin/TeamLead | Manual (Write) | Browser | TOP_NAME_EN, TOP_NAME_CN, TOP_DESC | Human Action |
| 4 | Submit | Admin/TeamLead | Manual | Browser → Backend | Form payload | Human → Machine |
| 5 | OP23: Create Category | System | Real-time (Sync) | Backend Service | Insert t_topic, set TOP_CREATED_BY, TOP_IS_GLOBAL = 1 | Machine Internal |
| 6 | Confirm + redirect to category list | System | Real-time | Browser | Toast "Category created" | Machine → Human |
| 7 | Edit/Delete Category | Admin/TeamLead | Manual | Browser | TOP_ID | Human → Machine |
| 8 | OP24: Update/Archive Category | System | Real-time (Sync) | Backend Service | Update fields or set TOP_IS_ACTIVE = 0 | Machine Internal |

**Organizational Rules:**
- Categories are global — not scoped to any team or team
- Only Admin or TeamLead may create/edit/delete categories
- Archived categories remain on existing actions; no new actions can be assigned to them
- Category name must be unique (case-insensitive)

---

## 12. Process: Meeting Instance Management

**Goal**: Admin or TeamLead records a meeting occurrence and links related actions.

| Step | Operation | Actor | Nature | Place | Datapoints | Sync |
|------|-----------|-------|--------|-------|------------|------|
| 1 | Navigate to Meetings | Admin/TeamLead | Manual | Browser | — | Human → Machine |
| 2 | Click "New Meeting" | Admin/TeamLead | Manual | Browser | — | Human → Machine |
| 3 | Fill meeting form | Admin/TeamLead | Manual (Write) | Browser | MIN_DATE, MIN_TITLE, MIN_TYPE (free text), MIN_TOP_ID (optional), MIN_SECONDARY_TOP_ID (optional) | Human Action |
| 4 | Submit | Admin/TeamLead | Manual | Browser → Backend | Form payload | Human → Machine |
| 5 | OP25: Create Meeting Instance | System | Real-time (Sync) | Backend Service | Insert t_meeting_instance | Machine Internal |
| 6 | Link actions to instance | Admin/TeamLead | Manual | Browser | Select action refs | Human → Machine |
| 7 | OP26: Link Actions | System | Real-time (Sync) | Backend Service | Batch update t_action.act_meeting_inst_id | Machine Internal |
| 8 | Confirm + show meeting detail | System | Real-time | Browser | Meeting card with linked actions list | Machine → Human |

**V1.1 Extension — Meeting Summary Upload:**
- Step 9: Upload summary file (.pdf/.docx/.xlsx)
- Step 10: OP27: Store in t_meeting_summary (MSM_FILE_PATH, MSM_UPLOADER_ID)

**Organizational Rules:**
- Meeting type is free text (not restricted to weekly/monthly)
- Only Admin or TeamLead may create/edit meetings
- Multiple actions may be linked to one meeting instance
- Meeting summary upload is deferred to V1.1

---

## 13. Process: Language Toggle

| Step | Operation | Actor | Nature | Place | Datapoints | Sync |
|------|-----------|-------|--------|-------|------------|------|
| 1 | Click EN/CN toggle | Any User | Manual | Browser (top nav) | Target language | Human Action |
| 2 | OP14: Switch Language | System | Real-time | Backend (update USR_LANG) + Browser (swap JSON) | en.json or zh.json loaded | Machine Internal |
| 3 | Re-render page | System | Real-time | Browser | All UI strings switched, taxonomy uses name_en/name_cn | Machine → Human |

---

## 14. Actor Summary

| Actor | Type | Operations (MVP) | Auth Level |
|-------|------|-----------------|------------|
| **End User (Member)** | Human | OP01, OP03–OP10, OP14–OP16, OP18 (post comment) | Authenticated (session) |
| **TeamLead** | Human | All Member ops + OP17 (category dashboard), OP19 (edit comment), OP20 (delete comment), OP23–OP27 (category/meeting mgmt) | Authenticated + TeamLead role |
| **Admin** | Human | All operations (OP01–OP27) | Authenticated + Admin role |
| **System (Backend)** | Machine | Session management, auto-generation, history logging, status rollup | Internal |
| **System (Scheduler)** | Machine | Deadline check cron (V1.1) | Internal (no session) |

---

## 15. Derivation to API Contract & MLD

The MOT specifies **who/where/when**. The next steps:
- **S16_API_Contract.md**: HTTP endpoints mapping to each operation, with methods, auth, request/response schemas
- **S20_MLD.md**: Physical table definitions translating MCD entities into SQLite DDL
