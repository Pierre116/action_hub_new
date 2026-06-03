# ActionHub — UI Specifications

> **Level**: L3 — Logical  
> **Merise Phase**: Spécifications d'Interface Homme-Machine  
> **Source**: S15_MOT.md (actors/processes), S16_API_Contract.md (endpoints), R09_ui_content.md  
> **Purpose**: Define every screen, its layout zones, data requirements, user interactions, and state machines

> **Updated**: 2026-03-14 — Rewritten post-SEP-4. Design system (§0), screen inventory (§1), and zone/API specs (§2) are framework-agnostic and remain valid. Component list (§7) updated to reference actual React shared components. i18n (§5) updated for custom `useTranslation()` hook implementation.

---

## 0. Design System

### 0.1 Theme & Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--primary` | `#1976D2` (Blue 700) | Primary buttons, active nav, links |
| `--primary-dark` | `#1565C0` | Hover states |
| `--success` | `#2E7D32` (Green 800) | Done status, positive KPIs |
| `--warning` | `#F57F17` (Amber 800) | Due soon, Medium priority |
| `--danger` | `#C62828` (Red 800) | Overdue, Critical priority |
| `--info` | `#0277BD` (Light Blue 800) | Info badges |
| `--bg` | `#F5F5F5` | Page background |
| `--surface` | `#FFFFFF` | Cards, modals |
| `--text` | `#212121` | Primary text |
| `--text-secondary` | `#757575` | Secondary text, labels |
| `--border` | `#E0E0E0` | Card borders, dividers |

### 0.2 Status Badge Colors

| Status | Background | Text |
|--------|-----------|------|
| Open | `#E3F2FD` | `#1565C0` |
| In Progress | `#FFF3E0` | `#E65100` |
| On Hold | `#F3E5F5` | `#7B1FA2` |
| Done | `#E8F5E9` | `#2E7D32` |
| Cancelled | `#EFEBE9` | `#5D4037` |

### 0.3 Priority Indicators

| Priority | Icon | Color |
|----------|------|-------|
| Critical | ▲▲ (double up) | `#C62828` |
| High | ▲ (up) | `#E65100` |
| Medium | ● (dot) | `#F57F17` |
| Low | ▼ (down) | `#757575` |

### 0.4 Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Page title | System sans-serif | 24px | 600 |
| Card title | System sans-serif | 16px | 600 |
| Body text | System sans-serif | 14px | 400 |
| Caption | System sans-serif | 12px | 400 |
| KPI number | System sans-serif | 28px | 700 |

### 0.5 Responsive Breakpoints

| Breakpoint | Width | Columns |
|-----------|-------|---------|
| Desktop | ≥1200px | 12-col grid |
| Tablet | 768–1199px | 8-col grid |
| Mobile | <768px | 4-col grid, stack layout |

---

## 1. Screen Inventory

| # | Screen | Route | Auth | Phase |
|---|--------|-------|------|-------|
| 1 | Login | `/login` | Public | MVP |
| 2 | Personal Dashboard | `/dashboard` | Member+ | MVP |
| 3 | Team Dashboard | `/dashboard/dept/:id` | Member+ | MVP |
| 4 | Action List | `/actions` | Member+ | MVP |
| 5 | Action Detail | `/actions/:id` | Member+ | MVP |
| 6 | Action Create (Full) | `/actions/new` | Member+ | MVP |
| 7 | Quick-Capture Modal | (overlay, any page) | Member+ | MVP |
| 8 | Admin: User Management | `/admin/users` | Admin | MVP |
| 9 | Admin: Import | `/admin/import` | Admin | MVP |
| 10 | Admin: Taxonomy | `/admin/taxonomy` | Admin | MVP |
| 11 | Admin Dashboard | `/admin/dashboard` | Admin | V1.1 |
| 12 | Notifications | `/notifications` | Member+ | V1.1 |
| 13 | Workflow Dashboard + Request Launch | `/workflow` | Member+ | V2 |
| 14 | Workflow Builder | `/workflow/builder` | Admin | V2 |
| 15 | Workflow Workbench | `/workflow/workbench/:instanceId` | Member+ | V3 |

> **Terminology transition (2026-03-17)**: Active specs use **Category** for the strategic classifier previously labelled Business Theme. Existing as-built route names may still use `/dashboard/business-theme` and `/admin/business-themes` until code rename work is scheduled.

---

## 2. Screen Specifications

### SCR-13: Workflow Request Form

**Route**: `/workflow`  
**Layout**: workflow dashboard with embedded request-launch card

#### Zones

| Zone | Content | Data Source |
|------|---------|------------|
| Z1: Template Select | Request-type workflow template dropdown | `GET /api/workflow/templates?type=request` |
| Z2: Core Fields | Title, Description | User input |
| Z3: Owner Selector | Optional owner (Lead) dropdown | `GET /api/admin/users` (active users) |
| Z4: Dynamic Step Fields | Step-1 fields (text/dropdown/date/number/checkbox/checklist) | `GET /api/workflow/templates/:id` |
| Z5: Submit | Submit Request button | `POST /api/workflow/requests` |

#### User Actions

| Action | Trigger | API Call | Result |
|--------|---------|----------|--------|
| Select template | Change template dropdown | `GET /api/workflow/templates/:id` | Renders initial step fields |
| Select owner | Change owner dropdown | — | `owner_user_id` included in submit payload |
| Submit request | Click submit | `POST /api/workflow/requests` | Creates workflow instance, redirects to `/workflow/workbench/:instanceId` |

#### Validation

| Field | Rule | Error Message |
|-------|------|---------------|
| template_id | Required | "Select a workflow template" |
| title | Required, min 5 chars | "Title must be at least 5 characters" |
| owner_user_id | Optional, must be active user if provided | "Owner not found or inactive" |

### SCR-01: Login Page

**Route**: `/login`  
**Layout**: Centered card on background

#### Zones

| Zone | Content | Data Source |
|------|---------|------------|
| Z1: Header | Company logo + "ActionHub" title | Static |
| Z2: Form | Username field, Password field, Login button | User input |
| Z3: Language | EN/CN toggle switch | Local storage |
| Z4: Error | Error message (red alert) | API response |

#### User Actions

| Action | Trigger | API Call | Result |
|--------|---------|----------|--------|
| Submit login | Click button / Enter key | `POST /api/auth/login` | → SCR-02 (success) or Z4 error |
| Toggle language | Click EN/CN | Local storage update | Re-render labels |

#### Validation

| Field | Rule | Error Message |
|-------|------|---------------|
| Username | Required, 3-50 chars | "Username is required" |
| Password | Required, 8+ chars | "Password is required" |

---

### SCR-02: Personal Dashboard

**Route**: `/dashboard` (default landing after login)  
**Layout**: Overview tables + supporting tabs  
**Action scope**: Actions where user is **assigned** OR is the **creator**.

#### Zones

| Zone | Content | Data Source |
|------|---------|------------|
| Z1: Top Nav | Logo, nav links, user menu, language toggle, notification bell | `useAuth()` context |
| Z2: Overdue | Red-bordered table of overdue actions | `.overdue_actions` |
| Z3: Due This Week | Amber-bordered table | `.due_this_week` |
| Z4: Recent Completed | Green-bordered table (last 30 days) | `.recent_completed` |
| Z4a: Recent Decisions | Info table of recent decisions with status family badges | `GET /api/dashboard/decisions?scope=all&limit=5` |
| Z5: Status Donut | Donut chart of status distribution | `.status_distribution` |
| Z6: FAB | "+" floating action button (bottom-right) | — |

#### User Actions

| Action | Trigger | API Call | Result |
|--------|---------|----------|--------|
| Click action card | Click | — | → SCR-05 (Action Detail) |
| Inline status change | Click status badge | `POST /api/actions/:id/status` | Badge color animation |
| Quick-capture | Click FAB "+" | — | → SCR-07 (modal overlay) |
| Export | Click "Export" | `GET /api/export/actions` | File download |

#### Action Table Presentation (Z3/Z4/Z5)

Personal dashboard action sections use a decision-style tabular layout with these columns:

`ID` · `Title` · `Content` · `Category` · `Meeting` · `Created by` · `Updated` · `Deadline` · `Status`

`Meeting` displays the meeting series title or occurrence title fallback, not a numeric meeting id.

The same `Meeting` column behavior applies in Overview, By Deadline, and By Category action tables.

`Updated` is displayed as a China-local date only on Personal Dashboard tables.

#### Recent Decisions Table Presentation (Z5a)

Recent Decisions uses the same fixed-width table rule as the action tables:

- `Content` column = 4x each other visible column
- all other visible columns = equal width

Columns:

`ID` · `Title` · `Content` · `Category` · `Meeting` · `Created by` · `Updated` · `Expired At` · `Status`

`Updated` is displayed as a China-local date only in the Recent Decisions table.

Decision dashboard summary badges use the clearer status families `Active` and `Closed` rather than `Published` and `Expired`.

#### Meeting Series Detail (Occurrences Grid)

In the Meeting Series occurrences table, the `Date` column displays each occurrence creation datetime in China-local format without seconds.

Display rule:

- primary source: `min_created_at` / `created_at`
- fallback: occurrence `date` (`min_date`)

---

#### Meeting Occurrence Detail — Actions Panel Layout

The Actions section in a meeting occurrence detail page uses an **always-expanded per-action row group** (no collapse). Each action is rendered as three consecutive table rows inside the same `<tbody>`:

**Row 1 — Action summary**

| Column | Content |
|--------|---------|
| ACT ID | Formatted reference code (`ACT-YYYY-NNNNN`) |
| Title | Bold link to action detail; description (`act_desc`) shown below in grey |
| Lead | `lead_name` |
| Progress | `ProgressBar` from latest follow-up; shows `%`; color from follow-up status |
| Deadline | `act_deadline`; shown red+bold when overdue |
| Status | `Badge` |

**Row 2 — Lead feedback** (light grey background)

Spans all 6 columns. Displays the most recent follow-up from `currentFollowUpByActionId` (or `previousFollowUpByActionId` as fallback):
- Status badge, completion %, comment text, blocker warning, author + timestamp  
- Label: "Lead feedback:"
- If no feedback: "No lead feedback yet."

**Row 3 — Comment row** (light blue-grey background)

Spans all 6 columns, split into two equal halves:

**Left half — Current meeting update (auto-save)**
- Textarea pre-populated with the user's own current-meeting comment (if any)
- Auto-saves 1.2 s after last keystroke (debounced)  
- Shows "saving…" / "✓ saved" indicator
- If the user did not author the existing comment, textarea is blank (creates a new comment on save)

**Right half — Meeting history browser**

- Header: "Previous meeting" (offset 0) or "N meetings ago" with the occurrence date in parentheses
- Navigation buttons: "← Newer" (hidden at offset 0) / "Older →" (hidden when no older occurrence)
- Offset 0: shows `occurrenceComments.previous` (data already loaded with the page)
- Offset ≥ 1: fetches `/api/meetings/{prevOccurrences[offset].min_id}/occurrence-comments` and shows `.current`
- Displays historical follow-up badge row (if any) above the historical comment text
- Falls back to "No update from this meeting." when no comment exists

**State**

| State | Type | Default | Description |
|-------|------|---------|-------------|
| `histNavOffset` | `number` | `0` | Global offset into `prevOccurrences` list for history panel |
| `commentDrafts` | `Record<number, string>` | `{}` | Per-action textarea draft values |
| `saveStatusById` | `Record<number, 'saving'\|'saved'>` | `{}` | Per-action auto-save indicator |
| `saveTimers` | `ref<Record<number, Timeout>>` | `{}` | Debounce timers for auto-save |

`prevOccurrences` is derived from the `series/{id}/instances` query, filtered to occurrences before the current meeting date and sorted most-recent-first.

---

### SCR-03: Team Dashboard

**Route**: `/dashboard/dept/:id`  
**Layout**: Team selector + KPI cards + tables

#### Zones

| Zone | Content | Data Source |
|------|---------|------------|
| Z1: Dept Selector | Dropdown of teams | `GET /api/teams` |
| Z2: KPI Row | Total, Overdue, Completion Rate, Avg Resolution, On-Time % | `GET /api/dashboard/team/:id` |
| Z3: Status Bars | Horizontal stacked bar per team | `.status_distribution` |
| Z4: Overdue Table | Table of overdue actions with owner, deadline, days overdue | `.overdue_by_team` |
| Z5: Contributors | Top contributors leaderboard | `.top_contributors` |

---


### SCR-04: Action List

**Route**: `/actions`  
**Layout**: Filter bar + sortable table + pagination

**Visibility:**
The action list only shows:
1. Actions created by, owned by, or assigned to the current user
2. Actions of the user's team members, but only from non-private meetings
3. Actions from meetings (public or private) where the user is a participant

#### Zones

| Zone | Content | Data Source |
|------|---------|------------|
| Z1: Filter Bar | Status chips, priority dropdown, team dropdown, search box, date range | Local state |
| Z2: Active Filters | Pill badges showing current filters with × remove | Local state |
| Z3: Results Header | "142 actions" count + sort dropdown + view toggle (table/cards) | API pagination meta |
| Z4: Action Table | Sortable columns (see below) | `GET /api/actions` |
| Z5: Pagination | Page navigation (« 1 2 3 ... 6 ») | API pagination meta |

#### Action Table Columns (Z4)

| Column | Width | Sortable | Content |
|--------|-------|----------|---------|
| Ref | 120px | Yes | `ACT-2026-00042` (link) |
| Title | flex | No | Title text (link) |
| Status | 110px | Yes | Clickable badge (inline OP05) || Assignees | 100px | No | Assigned-user count || Priority | 90px | Yes | Icon + label |
| Team | 120px | Yes (filter) | Name (EN/CN based on lang) |
| Lead | 100px | No | Display name |
| Deadline | 100px | Yes | Date + red if overdue |
| Updated | 100px | Yes | Relative time ("2h ago") |

#### User Actions

| Action | Trigger | API Call | Result |
|--------|---------|----------|--------|
| Filter by status | Click status chip | `GET /api/actions?status=X` | Refresh Z4 |
| Search | Type in search box (300ms debounce) | `GET /api/actions?search=X` | Refresh Z4 |
| Sort | Click column header | `GET /api/actions?sort=X` | Refresh Z4 |
| Inline status | Click status badge | `POST /api/actions/:id/status` | Badge animation |
| Open detail | Click ref/title | — | → SCR-05 |
| New action | Click "New Action" button | — | → SCR-06 |
| Export | Click "Export" | `GET /api/export/actions` | File download |
| Paginate | Click page number | `GET /api/actions?page=X` | Refresh Z4 |

---

### SCR-05: Action Detail

**Route**: `/actions/:id`  
**Layout**: Header card + tabs (Detail / History)

#### Zones

| Zone | Content | Data Source |
|------|---------|------------|
| Z1: Breadcrumb | Actions > ACT-2026-00042 | URL |
| Z2: Header Card | Ref, Title, Status badge (clickable), Priority badge, Team | `GET /api/actions/:id` |
| Z3: Meta Grid | 2×4 grid: Lead, Created by, Deadline, Category, Description, Meeting, Tags, source metadata as available | `GET /api/actions/:id` |
| Z4: Description | Rich text block | `.description` |
| Z5: Comment | Editable text area for last_comment | `.last_comment` |
| Z6: Tab Bar | Detail | History |
| Z7: History Tab | Activity stream (timeline view) | `.history[]` |
| Z8: Actions Bar | Edit, Delete (Admin only) | — |

#### Status Badge State Machine (Z2)

```
Click badge → Dropdown appears
  → Show only VALID_TRANSITIONS[current_status]
  → If On Hold / Cancelled: show reason field
  → Submit → POST /api/actions/:id/status
  → Success: animate badge color transition
  → If → Done: confetti animation (300ms)
```

#### User Actions

| Action | Trigger | API Call | Result |
|--------|---------|----------|--------|
| Change status | Click badge → select | `POST /api/actions/:id/status` | Badge animation |
| Edit action | Click "Edit" | — | Inline edit mode or → SCR-06 prefilled |
| Save comment | Blur on comment field | `PATCH /api/actions/:id` | Toast "Saved" |
| View history | Click History tab | Already loaded | Show Z7 |

---

### SCR-16: Workflow Workbench

**Route**: `/workflow/workbench/:instanceId`  
**Layout**: Summary strip + two-column work area + full-width timeline

#### Zones

| Zone | Content | Data Source |
|------|---------|------------|
| Z1: Summary Strip | Template name, workflow status, current step, SLA badge, derived action display status | `GET /api/workflow/instances/:id/workbench` |
| Z2: Current Step Card | Step type, assignee, entered/accepted timestamps, deadline, available actions | `.current_step` |
| Z3: Editable Form | Current step fields with draft save and completion validation | `.form.editable_fields[]` |
| Z4: Context Panel | Read-only prior-step fields configured via `context_fields` | `.form.context_fields[]` |
| Z5: Attachments Panel | Attachment list, upload button, delete actions, policy hint | `.attachments[]` |
| Z6: Timeline | Past/current/future steps with branch state and actor timestamps | `.timeline[]` |

#### User Actions

| Action | Trigger | API Call | Result |
|--------|---------|----------|--------|
| Accept step | Click Accept | `POST /api/workflow/steps/:id/accept` | Step status becomes Accepted |
| Save draft | Click Save Draft | `POST /api/workflow/steps/:id/draft` | Field values persist without advance |
| Complete step | Click Complete | `POST /api/workflow/steps/:id/advance` | Step validates and advances |
| Reject step | Click Reject | `POST /api/workflow/steps/:id/reject` | Mandatory reason + rejection flow |
| Delegate step | Click Delegate | `POST /api/workflow/steps/:id/delegate` | Delegate becomes responsible |
| Reassign step | Click Reassign | `POST /api/workflow/steps/:id/reassign` | Admin/lead changes assignee |
| Upload attachment | Select file + Upload | `POST /api/workflow/steps/:id/attachments` | Attachment appears in panel |
| Delete attachment | Click Delete | `DELETE /api/workflow/steps/:step_id/attachments/:attachment_id` | Attachment soft-deleted |

#### Validation and States

| Condition | UI Behavior |
|----------|-------------|
| Workbench opened for invalid/non-visible instance | Show error state and hide Z2–Z6 |
| Current user is not acting assignee | Show read-only mode; disable form actions |
| Draft saved | Toast `Draft saved` + timestamp refresh |
| Completion blocked | Inline field errors + sticky summary alert |
| Attachment blocked by policy | Inline alert naming blocked type/limit |
| SLA breached | Red SLA badge + escalation hint in Z2 |

#### Responsive Notes

- Desktop: Z2 and Z3/Z4/Z5 appear side-by-side, timeline below.
- Tablet/mobile: stack Summary, Step Card, Form, Attachments, Timeline vertically.
- Timeline remains readable with horizontal step chips rather than dense tables on narrow screens.

---

### SCR-06: Action Create / Edit (Full Form)

**Route**: `/actions/new` or `/actions/:id/edit`  
**Layout**: Full-width form with sections

#### Zones

| Zone | Content | Data Source |
|------|---------|------------|
| Z1: Form Header | "New Action" or "Edit: ACT-2026-XXXXX" | Mode |
| Z2: Core Fields | Title (text), Description (textarea) | User input |
| Z3: Classification | Team (select → cascading), Team (select), Category (select), Category (select) | `GET /api/teams`, etc. |
| Z4: Assignment | Lead (user select, default = self), Delegates (multi-select), Tags (multi-select) | `GET /api/admin/users` |
| Z5: Scheduling | Priority (radio/select), Deadline (date picker) | User input |
| Z6: Optional | Meeting link (select) | Optional |
| Z7: Actions | "Create" / "Save Changes" button, "Cancel" link | — |

#### Cascading Behavior (Z3)

```
Team selected
  → Filter Teams to team's teams
  → Filter Categories to team's categories (if scoped)
  → Clear team/category selection if previously selected outside new dept
```

#### Validation

| Field | Rule | Error |
|-------|------|-------|
| Title | Required, 5-200 chars | "Title must be 5-200 characters" |
| Team | Required | "Please select a team" |
| Deadline | Required, ≥ today | "Deadline must be today or later" |
| Priority | Required (default: Medium) | Auto-selected |

---

### SCR-07: Quick-Capture Modal

**Trigger**: Click FAB "+" on any page  
**Layout**: Centered modal overlay (480px max-width)

#### Zones

| Zone | Content |
|------|---------|
| Z1: Header | "Quick Action" + × close |
| Z2: Title | Text input (auto-focus) |
| Z3: Priority | 4-button group (Critical/High/Medium/Low, default Medium) |
| Z4: Deadline | Date picker (default: today + 7 days) |
| Z5: Team | Pre-filled from user profile, changeable |
| Z6: Actions | "Create" button (primary) |

#### Behavior

- ESC or click outside = close modal (no save)
- On submit: `POST /api/actions` with minimal fields
- Creator becomes Lead automatically
- Toast: "Action created — ACT-2026-XXXXX" with link
- Modal closes on success

---

### SCR-08: Admin — User Management

**Route**: `/admin/users`  
**Layout**: User table + create/edit panel

#### Zones

| Zone | Content | Data Source |
|------|---------|------------|
| Z1: Header | "User Management" + "Add User" button | — |
| Z2: User Table | Username, Display Name, Team, Role, Active, Last Login | `GET /api/admin/users` |
| Z3: Create/Edit Panel | Slide-in panel with user form | — |

#### User Actions

| Action | Trigger | API Call | Result |
|--------|---------|----------|--------|
| Add user | Click "Add User" | — | Open Z3 panel |
| Edit user | Click row | — | Open Z3 with data |
| Save user | Submit form | `POST/PATCH /api/admin/users` | Close panel, refresh Z2 |
| Reset password | Click "Reset" | `POST /api/admin/users/:id/reset-password` | Prompt for new password |
| Deactivate | Toggle switch | `PATCH /api/admin/users/:id/deactivate` | Row grayed out |

#### Create/Edit User Form

| Field | Control | Notes |
|------|---------|-------|
| Employee ID | Text input | Required on create; immutable on edit |
| Display Name | Text input | Required |
| Email | Email input | Required |
| Role | Dropdown | Options: `Member`, `TeamLead`, `Admin` |
| Password | Password input | Required on create; reset flow on edit |

---

### SCR-09: Admin — Import

**Route**: `/admin/import`  
**Layout**: 3-step wizard (Upload → Preview → Results)

#### Step 1: Upload

| Zone | Content |
|------|---------|
| Z1: Drop Zone | Drag-drop area + "Browse" button, accepts .xlsx only |
| Z2: Instructions | "Upload your Excel logbook. Supported formats: v1, v2, v3, v4" |
| Z3: History | Previous import logs table | 

#### Step 2: Preview

| Zone | Content | Data Source |
|------|---------|------------|
| Z1: Detection | "Detected: v3 format — 212 rows" | `POST /api/import/upload` response |
| Z2: Preview Table | First 20 rows with column mapping | `.preview_rows` |
| Z3: Unresolved Owners | List of unresolved owner names with user dropdown mapping | `.unresolved_owners` |
| Z4: Unresolved Depts | List with team dropdown mapping | `.unresolved_teams` |
| Z5: Duplicates | Flagged rows with "Skip" checkbox | `.duplicate_candidates` |
| Z6: Actions | "Import" (primary), "Cancel" (secondary) | — |

#### Step 3: Results

| Zone | Content |
|------|---------|
| Z1: Summary | "86 imported, 2 skipped, 1 duplicate" |
| Z2: Error Details | Expandable list of failed rows with reasons |
| Z3: Actions | "Import Another" button, "View Actions" link |

---

### SCR-10: Admin — Taxonomy

**Route**: `/admin/taxonomy`  
**Layout**: Tab-based management (Teams, Teams, Categories, Categories, Tags)

#### Zones (per tab)

| Zone | Content |
|------|---------|
| Z1: Tab Bar | Teams / Teams / Categories / Categories / Tags |
| Z2: Item Table | Name (EN), Name (CN), Active toggle, Sort order, Actions |
| Z3: Add/Edit Row | Inline or modal form for adding/editing items |

---

## 3. Navigation Structure

```
Top Nav Bar
├── Logo → /dashboard
├── Dashboard → /dashboard
├── Actions → /actions
├── Teams → /dashboard/dept/:id  (dropdown)
├── [Admin] → /admin/users (dropdown: Users, Import, Taxonomy)
├── Language Toggle (EN/CN)
├── Notification Bell (V1.1)
└── User Menu (Profile, Logout)

FAB "+" (visible on all pages except Login, Admin pages)
```

---

## 4. First-5-Minutes Experience

The first time a user logs in:

| Step | What they see | UX Goal |
|------|--------------|---------|
| 1 | Login page (clean, centered) | "Simple and familiar" |
| 2 | Personal Dashboard with 0 actions | Not empty — show welcome card + "Create your first action" CTA |
| 3 | Click "+" or CTA → Quick-Capture | "That was fast!" (< 10 seconds to create) |
| 4 | Dashboard updates with 1 action card | Instant feedback loop |
| 5 | Click action → Detail page | "I can see everything about this action" |

---

## 5. Internationalization (i18n)

| Aspect | Implementation |
|--------|---------------|
| UI strings | Custom `useTranslation()` hook in `frontend/src/lib/i18n.ts` with inline catalogs (~340 lines per language) |
| Toggle | Top nav EN/CN switch — persisted to `localStorage` + `USR_LANG` in DB |
| Persistence | `USR_LANG` saved to DB on preference change; frontend reads from `localStorage` at startup |
| Taxonomy | `name_en` / `name_cn` columns, display based on current language |
| Dates | ISO format (no locale-specific) |
| Numbers | No locale-specific formatting (use `.` decimal) |
| Direction | LTR only (no RTL) |
| Backend strings | `actionhub/i18n/en.json` / `zh.json` for API error messages and server-generated labels |

---

## 6. Accessibility (MVP Minimum)

| Aspect | Implementation |
|--------|---------------|
| Keyboard nav | Tab order for all interactive elements |
| Focus indicators | Blue outline on focus |
| Color contrast | WCAG AA minimum (4.5:1 text, 3:1 large text) |
| Alt text | All icons have aria-label |
| Form labels | Every input has associated label |
| Screen reader | Status badges announced (aria-live regions) |

---

## 7. Reusable Components (D117)

Shared React components in `frontend/src/components/shared/`:

| # | Component | File | Usage | Key Props |
|---|-----------|------|-------|----------|
| 1 | CrudTable | `CrudTable.tsx` | Action list, user list, meeting list, admin tables | columns, data, sortable, paginated, onRowClick |
| 2 | KpiCard | `KpiCard.tsx` | Dashboard KPI cards | label, value, color, icon, trend |
| 3 | ChartPanel | `ChartPanel.tsx` | Dashboard charts (donut, bar) | type, data, options |
| 4 | StatusBadge | `StatusBadge.tsx` | Everywhere actions appear | status, clickable, size |
| 5 | ConfirmModal | `ConfirmModal.tsx` | Delete confirmations, status changes | title, body, onConfirm, variant |
| 6 | DateField | `DateField.tsx` | Action form, filter bar | value, min, onChange |

Additional layout component:

| # | Component | File | Usage |
|---|-----------|------|-------|
| 7 | AppLayout | `AppLayout.tsx` | Navbar, footer, role-based nav, language toggle |

---

## 8. Onboarding Tour (First Login)

A 3-step tooltip tour triggered on first login (stored in `localStorage`):

| Step | Target Element | Tooltip Content |
|------|---------------|----------------|
| 1 | FAB "+" button | "Create your first action in seconds" |
| 2 | Dashboard KPI cards | "Your key metrics at a glance" |
| 3 | Language toggle | "Switch between English and Chinese" |

User can skip tour at any step. Tour does not repeat after dismissal.
### Unified Action Management UI

- The Action List and dashboards must support filtering and displaying actions by origin: meeting, workflow, or topic/category.
- Actions linked to meetings, workflows, or topics/categories should show their source in the list/detail view (e.g., badge or column).
- UI must allow users to view all actions in a unified pool, regardless of origin, and also filter by specific meeting, workflow instance, or topic.
