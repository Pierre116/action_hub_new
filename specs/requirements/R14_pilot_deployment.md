# ActionHub — R14: Pilot Deployment Requirements

> **Status**: Requirements — Pilot V2.5  
> **Date**: 2026-03-02  
> **Depends on**: R06 (Security), R09 (UI), R01 (Entities)  
> **Purpose**: Prepare ActionHub for management team pilot trial

---

## §1 Overview

Before rolling out ActionHub to the full organization, a pilot version is deployed for the management team (~10 users). This phase introduces three changes:

1. **User identity overhaul** — 6-digit employee IDs replace free-text usernames
2. **Feedback collection** — Built-in UI for pilot users to submit feedback
3. **Product evolution log** — Visible changelog so pilot users see what is improving

---

## §2 User Identity — 6-Digit Employee ID

### §2.1 Employee ID as Login Credential

| Aspect | Specification |
|--------|---------------|
| Format | Exactly 6 digits, zero-padded (e.g. `001234`) |
| Uniqueness | Enforced at database level (UNIQUE constraint) |
| Login field | User enters Employee ID (not username) in the login form |
| Display | All user references show **Employee ID + Display Name** (e.g. `001234 — John Doe`) |

### §2.2 User Record Fields

The `t_user` table gains a new column and changes login semantics:

| Column | Change | Description |
|--------|--------|-------------|
| `usr_employee_id` | **NEW** — `TEXT NOT NULL UNIQUE` | 6-digit employee ID (e.g. `001234`) |
| `usr_username` | Repurposed | Now stores the employee ID (kept for backward compat) |
| `usr_display_name` | Unchanged | Full name (English) |
| `usr_display_name_cn` | Unchanged | Full name (Chinese) |
| `usr_must_change_pwd` | **NEW** — `INTEGER DEFAULT 1` | `1` = user must set password at first login |

### §2.3 Login Flow

```
User opens ActionHub
 → Login page: Employee ID + Password
 → First login (usr_must_change_pwd = 1):
    → After successful auth with temp password
    → Redirect to "Set Your Password" page
    → User sets new password (min 8 chars, must confirm)
    → usr_must_change_pwd → 0
    → Redirect to Dashboard
 → Subsequent logins:
    → Normal flow (direct to Dashboard)
```

### §2.4 Admin Password Reset

| Rule | Description |
|------|-------------|
| Any Admin can reset any user's password | Sets a temporary password and `usr_must_change_pwd = 1` |
| User must set their own password on next login | Forced redirect to password-change page |
| Admin cannot see current passwords | Only hash is stored |

### §2.5 User Creation (Admin)

When Admin creates a user:
1. Enter **Employee ID** (6 digits, validated)
2. Enter **Display Name** (English, required) and **Display Name CN** (optional)
3. Enter **Email** (required)
4. Select **Role**, **Team**, **Team**
5. System generates a **temporary password** (displayed once to Admin)
6. `usr_must_change_pwd` = 1

---

## §3 Feedback Collection

### §3.1 Feedback Menu

A new top-level menu item **"Feedback"** visible to all logged-in users.

| Aspect | Specification |
|--------|---------------|
| Menu position | After "Meetings", before "Help" |
| Icon | 💬 (speech bubble) or `bi-chat-dots` |
| Route | `/feedback` |

### §3.2 Feedback Form

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Category | Dropdown | Yes | Bug Report / Feature Request / Usability Issue / General Comment |
| Page/Feature | Dropdown | No | Which page or feature is this about (auto-populated from routes) |
| Title | Text (5–100 chars) | Yes | Short summary |
| Description | Textarea (max 2000 chars) | Yes | Detailed feedback |
| Priority | Radio | Yes | Low / Medium / High |
| Screenshot | File upload (.png/.jpg, max 5MB) | No | Optional screenshot |

### §3.3 Feedback Data Model

**New table: `t_feedback`**

| Column | Type | Description |
|--------|------|-------------|
| `fbk_id` | INTEGER PK AUTOINCREMENT | |
| `fbk_user_id` | INTEGER NOT NULL FK→t_user | Submitter |
| `fbk_category` | TEXT NOT NULL | CHECK IN ('Bug', 'Feature', 'Usability', 'General') |
| `fbk_page` | TEXT | Page/feature reference |
| `fbk_title` | TEXT NOT NULL | Short summary |
| `fbk_description` | TEXT NOT NULL | Detailed text |
| `fbk_priority` | TEXT NOT NULL DEFAULT 'Medium' | CHECK IN ('Low', 'Medium', 'High') |
| `fbk_screenshot` | BLOB | Optional image data |
| `fbk_screenshot_name` | TEXT | Original filename |
| `fbk_status` | TEXT NOT NULL DEFAULT 'New' | CHECK IN ('New', 'Acknowledged', 'In Progress', 'Resolved', 'Declined') |
| `fbk_admin_response` | TEXT | Admin's reply |
| `fbk_created_at` | TEXT DEFAULT CURRENT_TIMESTAMP | |
| `fbk_updated_at` | TEXT | |

### §3.4 Feedback Views

**User view** (`/feedback`):
- List of own submitted feedback with status
- "New Feedback" button → opens form
- Can view admin response when status changes

**Admin view** (`/admin/feedback`):
- Table of all feedback from all users, sortable/filterable
- Inline status update (New → Acknowledged → In Progress → Resolved / Declined)
- Admin response text field
- Export to Excel

### §3.5 Feedback API

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/feedback` | Login | List user's own feedback |
| POST | `/api/feedback` | Login | Submit new feedback |
| GET | `/api/feedback/:id` | Login | View single feedback (own or Admin) |
| GET | `/api/admin/feedback` | Admin | List all feedback |
| PATCH | `/api/admin/feedback/:id` | Admin | Update status, add response |
| GET | `/api/admin/feedback/export` | Admin | Export feedback to Excel |

---

## §4 Product Evolution Log

### §4.1 Evolution Menu

A new section accessible from Help menu or standalone: **"What's New"**

| Aspect | Specification |
|--------|---------------|
| Menu position | Under Help dropdown: "What's New" |
| Icon | `bi-rocket-takeoff` or 🚀 |
| Route | `/whatsnew` |

### §4.2 Evolution Entry Data Model

**New table: `t_evolution`**

| Column | Type | Description |
|--------|------|-------------|
| `evo_id` | INTEGER PK AUTOINCREMENT | |
| `evo_version` | TEXT NOT NULL | Version tag (e.g. "2.5", "2.6") |
| `evo_title` | TEXT NOT NULL | Entry title |
| `evo_description` | TEXT NOT NULL | Markdown-supported description |
| `evo_category` | TEXT NOT NULL | CHECK IN ('Feature', 'Improvement', 'Bugfix', 'Security') |
| `evo_date` | TEXT NOT NULL | Release date |
| `evo_author_id` | INTEGER FK→t_user | Who posted it |
| `evo_created_at` | TEXT DEFAULT CURRENT_TIMESTAMP | |

### §4.3 Evolution Views

**User view** (`/whatsnew`):
- Chronological list grouped by version
- Each entry shows: version badge, category tag, title, description, date
- Read-only for non-admin users

**Admin management** (`/admin/whatsnew`):
- CRUD evolution entries
- Markdown preview for description field

### §4.4 Evolution API

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/evolution` | Login | List all entries (paginated) |
| GET | `/api/evolution/:id` | Login | Single entry |
| POST | `/api/admin/evolution` | Admin | Create entry |
| PATCH | `/api/admin/evolution/:id` | Admin | Update entry |
| DELETE | `/api/admin/evolution/:id` | Admin | Delete entry |

---

## §5 Pre-Pilot Bug Fixes

Issues identified during audit that must be resolved before pilot:

| # | Issue | Severity | Fix |
|---|-------|----------|-----|
| B1 | `usr_failed_logins` not incremented on failure | Medium | Add `UPDATE` in `authenticate_user()` |
| B2 | `usr_locked_until` not enforced in login | Medium | Add lockout check in `authenticate_user()` |
| B3 | Admin pages served to non-admin (403 only on API) | Low | Add `@admin_required` to web routes |
| B4 | `t_user_team` missing from base schema.sql | High | Add table to schema or consolidate migrations |

---

## §6 Pilot User Setup

### §6.1 Initial Pilot Users

Admin will create ~10 management accounts:

| Employee ID | Name | Role | Team |
|-------------|------|------|------------|
| (provided by Admin) | (management team members) | Admin or TeamLead | (respective depts) |

### §6.2 Pilot Timeline

| Phase | Duration | Activity |
|-------|----------|----------|
| Setup | 1 day | Deploy, create accounts, seed demo data |
| Trial | 2 weeks | Management team uses the system |
| Feedback review | 1 week | Collect & analyze feedback, plan V2.6 |
