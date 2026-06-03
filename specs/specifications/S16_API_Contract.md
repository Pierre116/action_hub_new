# ActionHub — API Contract

> **Level**: L2 — Organizational  
> **Merise Phase**: Contrat d'Interface (API REST)  
> **Source**: S11_MCT.md (operations), S15_MOT.md (actors), S05_data_dictionary.md (fields)  
> **Purpose**: Define every HTTP endpoint the backend exposes — method, path, auth, request/response schemas, errors

---

## 0. Global Conventions

| Aspect | Convention |
|--------|-----------|
| Content-Type | `application/json` for API; `multipart/form-data` for file upload |
| Authentication | JWT Bearer token in `Authorization` header; refresh token exchange via `/api/auth/refresh` |
| Error envelope | `{ "error": { "code": "<code>", "message": "<human string>" } }` |
| Date format | ISO 8601: `YYYY-MM-DDTHH:MM:SS` |
| Pagination | `?page=1&per_page=25` (default 25, max 100) |
| Language | Accept-Language header or `?lang=en|zh` |
| Rate limiting | None in MVP (LAN, <10 users) |
| Max request body | 10 MB (import endpoint) |
| ID type | Integer (SQLite ROWID) |

---

## 1. Authentication

### POST `/api/auth/login`

**Operation**: OP01 — Authenticate  
**Auth**: None (public)

**Request:**
```json
{
  "username": "string (required, 3-50 chars)",
  "password": "string (required, 8-128 chars)"
}
```

**Response 200:**
```json
{
  "data": {
    "id": 1,
    "username": "john.doe",
    "employee_id": "000001",
    "display_name": "John Doe",
    "role": "Member",
    "lang": "en",
    "must_change_pwd": false,
    "access_token": "jwt-access-token",
    "refresh_token": "jwt-refresh-token"
  }
}
```

Notes:

- Request may use `employee_id` or `username` as the login identifier.
- The SPA stores tokens client-side and attaches the access token on subsequent API calls.

| Error Code | HTTP | Condition |
|------------|------|-----------|
| AUTH_INVALID | 401 | Wrong username or password |
| AUTH_LOCKED | 423 | Account locked (5 failed attempts in 15 min) |
| AUTH_DISABLED | 403 | Account deactivated |

---

### DELETE `/api/auth/logout`

**Operation**: Token/session teardown  
**Auth**: Authenticated

**Response 200:**
```json
{ "data": { "message": "Logged out" } }
```

If a Bearer token is supplied, the backend blacklists it before returning success.

---

### GET `/api/auth/me`

**Operation**: Session check  
**Auth**: Authenticated

**Response 200:**

```json
{
  "data": {
    "id": 1,
    "username": "john.doe",
    "role": "Member"
  }
}
```

**Response 401:** `{ "error": "AUTH_REQUIRED" }`

### POST `/api/auth/refresh`

**Operation**: Access token refresh  
**Auth**: None (valid refresh token required)

**Request:**
```json
{
  "refresh_token": "jwt-refresh-token"
}
```

**Response 200:**
```json
{
  "data": {
    "access_token": "new-jwt-access-token"
  }
}
```

---

## 2. Actions

### GET `/api/actions`

**Operation**: OP09 — Query Actions  
**Auth**: Authenticated

**Visibility Policy:**
Returned actions are limited to:
1. Actions created by, owned by, or assigned to the current user
2. Actions of the user's team members, but only from non-private meetings
3. Actions from meetings (public or private) where the user is a participant

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | int | 1 | Page number |
| per_page | int | 25 | Items per page (max 100) |
| status | string | — | Filter: `Not started,On-track,Late,Completed,Cancelled` |
| priority | string | — | Filter: `Critical,High,Medium,Low` |
| team_id | int | — | Filter by team |
| team_id | int | — | Filter by team |
| assigned_to | int | — | Filter by assigned user ID |
| created_by | int | — | Filter by creator |
| category_id | int | — | Filter by category (matches primary OR secondary category) |
| overdue | bool | — | `true` = deadline < now AND status ∉ {Completed, Cancelled} |
| search | string | — | Full-text search on reference + title + description + tags |
| sort | string | `deadline_asc` | Sort: `deadline_asc`, `deadline_desc`, `created_desc`, `priority_desc` |
| date_from | date | — | Actions created after this date |
| date_to | date | — | Actions created before this date |

**Response 200:**
```json
{
  "data": [
    {
      "id": 42,
      "ref": "ACT-2026-00042",
      "title": "Calibrate line 3 sensors",
      "description": "Quarterly calibration...",
      "tags": "MAINTENANCE, LINE3",
      "status": "On-track",
      "priority": "High",
      "team": { "id": 3, "name_en": "Production", "name_cn": "生产部" },
      "team": { "id": 7, "name_en": "Line 3" },
      "category_1": { "code": "KOM", "name_en": "Maintenance" },
      "category_2": { "code": "SAF", "name_en": "Safety" },
      "category": { "id": 2, "name_en": "Corrective" },
      "deadline": "2026-02-15",
      "actual_date": null,
      "is_overdue": true,
      "lead": { "id": 12, "display_name": "Alice Wang" },
      "delegate_count": 2,
      "created_by": { "id": 12, "display_name": "Alice Wang" },
      "created_at": "2026-01-20T09:15:00",
      "updated_at": "2026-02-01T14:30:00",
      "source": "Manual",
      "last_comment": "Parts ordered, ETA Feb 10",
      "escalation_level": 0
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 25,
    "total": 142,
    "total_pages": 6
  }
}
```

---

### GET `/api/actions/:id`

**Operation**: Load single action detail  
**Auth**: Authenticated

**Response 200:**
```json
{
  "id": 42,
  "ref": "ACT-2026-00042",
  "title": "Calibrate line 3 sensors",
  "description": "Quarterly calibration of all sensors on Line 3",
  "tags": "MAINTENANCE, LINE3",
  "status": "On-track",
  "priority": "High",
  "team": { "id": 3, "name_en": "Production", "name_cn": "生产部" },
  "team": { "id": 7, "name_en": "Line 3", "name_cn": "3号线" },
  "category_1": { "code": "KOM", "name_en": "Maintenance", "name_cn": "维护" },
  "category_2": { "code": "SAF", "name_en": "Safety", "name_cn": "安全" },
  "category": { "id": 2, "name_en": "Corrective", "name_cn": "纠正" },
  "tags": [
    { "id": 1, "name": "sensor" },
    { "id": 3, "name": "quarterly" }
  ],
  "deadline": "2026-02-15",
  "actual_date": null,
  "is_overdue": true,
  "escalation_level": 0,
  "escalation_date": null,
  "hold_reason": null,
  "cancel_reason": null,
  "postpone_target_date": null,
  "last_comment": "Parts ordered, ETA Feb 10",
  "source": "Manual",
  "source_file": null,
  "meeting_id": null,
  "creator_name": "Zhang Wei",
  "lead": { "id": 12, "display_name": "Alice Wang", "display_name_cn": "王爱丽" },
  "delegates": [
    { "id": 15, "display_name": "Bob Li" },
    { "id": 18, "display_name": "Carol Zhang" }
  ],
  "asg_total": 3,
  "sub_actions": [
    { "id": 101, "ref": "ACT-2026-00101", "title": "Order replacement parts", "status": "Completed" },
    { "id": 102, "ref": "ACT-2026-00102", "title": "Schedule shutdown window", "status": "Not started" }
  ],
  "history": [
    {
      "id": 1,
      "field": "status",
      "old_value": "Not started",
      "new_value": "On-track",
      "changed_by": { "id": 12, "display_name": "Alice Wang" },
      "changed_at": "2026-01-25T10:00:00",
      "reason": null
    }
  ],
  "created_by": { "id": 12, "display_name": "Alice Wang" },
  "created_at": "2026-01-20T09:15:00",
  "updated_at": "2026-02-01T14:30:00"
}
```

| Error Code | HTTP | Condition |
|------------|------|-----------|
| NOT_FOUND | 404 | Action ID does not exist |

Tag formatting notes:

- `POST /api/actions` and `PATCH /api/actions/:id` accept optional `tags: string | null`.
- Blank tags are normalized to `null`.
- Tags are normalized to uppercase comma-separated values.
- UI surfaces render each tag with a leading `#`.

---

## 8. Decisions

Tag formatting notes:

- `GET /api/decisions/` accepts optional `search`, which matches decision title, body, and tags.
- `GET /api/decisions/` supports filters: `search`, `status`, `category_id`, `series_id`, `owner_id`, `meeting_id`. All filters are optional; all authenticated decisions are returned by default.
- `POST /api/decisions/` and `PATCH /api/decisions/:id` accept optional `tags: string | null`.
- Decision responses include normalized `mdc_tags`.
- UI surfaces render each tag with a leading `#`.
- The `team_projects_only` filter has been removed; all decisions within the authenticated user's visibility scope are shown.

---

### POST `/api/actions`

**Operation**: OP03 — Create Action  
**Auth**: Authenticated

**Request:**
```json
{
  "title": "string (required, 5-200 chars)",
  "description": "string (optional, max 2000 chars)",
  "category_ids": "[string] (required, 1..2 category codes; values must be unique)",
  "category_id": "int (optional)",
  "priority": "string (default: 'Medium'). Enum: Critical|High|Medium|Low",
  "deadline": "date (required, YYYY-MM-DD, must be >= today)",
  "parent_id": "int (optional)",
  "lead_user_id": "int (optional, default = current user)",
  "delegate_user_ids": "[int] (optional)",
  "tag_ids": "[int] (optional)",
  "last_comment": "string (optional, max 1000 chars)",
  "meeting_id": "int (optional)"
}
```

**Response 201:**
```json
{
  "id": 43,
  "ref": "ACT-2026-00043",
  "status": "Open",
  "message": "Action created"
}
```

| Error Code | HTTP | Condition |
|------------|------|-----------|
| VALIDATION_ERROR | 422 | Missing required fields or invalid values |
| USER_NOT_FOUND | 422 | lead_user_id or delegate not found |

Notes:

- Non-meeting action creation locks Lead (`act_owner_id`) to the authenticated user.
- `team_id` is legacy and ignored for new action creation.

---

### PATCH `/api/actions/:id`

**Operation**: OP04 — Update Action  
**Auth**: Authenticated (Action Lead or Admin)

Permission notes:

- Non-meeting action: only Action Lead (`act_owner_id`) (or Admin) may update.
- Meeting action: Action Lead (`act_owner_id`) or meeting creator (or Admin) may update.

**Request:** Partial update — only changed fields sent.
```json
{
  "title": "string (optional)",
  "description": "string (optional)",
  "category_ids": "[string] (optional, 1..2 category codes; replace full category attachment set)",
  "category_id": "int (optional)",
  "deadline": "date (optional)",
  "last_comment": "string (optional)",
  "meeting_id": "int (optional)"
}
```

**Response 200:**
```json
{
  "id": 43,
  "updated_fields": ["priority", "deadline"],
  "message": "Action updated"
}
```

| Error Code | HTTP | Condition |
|------------|------|-----------|
| NOT_FOUND | 404 | Action not found |
| FORBIDDEN | 403 | Caller is not permitted by lead/meeting-creator policy |
| VALIDATION_ERROR | 422 | Invalid field values |

---

### POST `/api/actions/:id/status`

**Operation**: OP05 — Transition Status  
**Auth**: Authenticated (Action Lead, meeting creator for meeting actions, or Admin)

**Request:**
```json
{
  "new_status": "string (required). Enum: Not started|On-track|Late|Completed|Cancelled",
  "reason": "string (required if → Cancelled)"
}
```

**Response 200:**
```json
{
  "id": 43,
  "old_status": "Not started",
  "new_status": "On-track",
  "message": "Status updated"
}
```

| Error Code | HTTP | Condition |
|------------|------|-----------|
| INVALID_TRANSITION | 422 | Transition not in VALID_TRANSITIONS[current] |
| REASON_REQUIRED | 422 | Missing reason for Cancelled |
| NOT_FOUND | 404 | Action not found |
| FORBIDDEN | 403 | Not authorized to change status |

> Compatibility note:
> - The backend still accepts legacy stored values such as `Open`, `In Progress`, `Done`, and `Closed` for existing records.
> - New UI filtering and dashboard contracts use the business status families above.

---

### POST `/api/actions/:id/feedback`

**Operation**: OP05A — Submit Progress Feedback  
**Auth**: Authenticated (Action Lead, meeting creator for meeting actions, or Admin)

**Request:**
```json
{
  "meeting_inst_id": "int (optional)",
  "completion_pct": "int (optional, 0..100)",
  "status": "string (optional). Enum: on_track|at_risk|blocked|done",
  "comment": "string (optional)",
  "blockers": "string (optional)",
  "est_date": "date (optional)"
}
```

Behavior notes:

- Feedback is append-only; each submission creates a new row in `t_action_feedback`.
- If `blockers` is omitted/blank, the latest non-empty blockers value for that action is carried forward.
- Status sync rule: whenever a feedback (follow-up) is submitted with a status, the action main status (`act_status`) is synced from the latest feedback using DB-valid mapping only: `on_track` -> `In Progress`, `at_risk` -> `In Progress`, `blocked` -> `On Hold`, `done` -> `Done`.
- Response includes `afb_created_at`; UI should display full locale date+time for update timestamp.

| Error Code | HTTP | Condition |
|------------|------|-----------|
| FORBIDDEN | 403 | Caller is not permitted by lead/meeting-creator policy |
| VALIDATION_ERROR | 400/422 | Invalid payload values |

---

### POST `/api/actions/:id/assign`

**Operation**: OP06 — Assign User  
**Auth**: Authenticated (Lead or Admin)

**Request:**
```json
{
  "user_id": "int (required)",
  "role": "string (default: 'Lead'). Only 'Lead' is supported.",
  "estimated_hours": "float (optional, ≥ 0) — hours this person is expected to contribute. Stored as asg_estimated_hours."
}
```

> **Owner sync rule:** when `role = Lead`, `t_action.act_owner_id` is updated to `user_id`.

> **One-row-per-user rule (D166):** If the user already has an assignment row for this action, the specified `role` is **added** to the existing comma-separated `asg_role` list (idempotent — no error if already present). A new row is only created when the user has no prior assignment on this action.

**Response 200:**
```json
{
  "action_id": 43,
  "user_id": 15,
  "role": "Lead",
  "estimated_hours": 4.0,
  "message": "User assigned"
}
```

| Error Code | HTTP | Condition |
|------------|------|-----------|
| USER_NOT_FOUND | 404 | user_id not found |
| NOT_FOUND | 404 | Action not found |

---

### DELETE `/api/actions/:id/assign/:user_id`

**Operation**: Remove assignment  
**Auth**: Authenticated (Lead or Admin)

**Response 200:**
```json
{ "message": "Assignment removed" }
```

---

### PATCH `/api/actions/:id/assignments/:asg_id`

**Operation**: Update assignment (estimated hours)  
**Auth**: Authenticated (Lead, Admin, or the assigned user)

**Request:**
```json
{
  "estimated_hours": "float (optional, ≥ 0 or null to clear)"
}
```

**Response 200:**
```json
{
  "asg_id": 12,
  "estimated_hours": 4.5,
  "message": "Assignment updated"
}
```

| Error Code | HTTP | Condition |
|------------|------|-----------|
| NOT_FOUND | 404 | Assignment or action not found |
| FORBIDDEN | 403 | Caller is not Lead, Admin, or the assigned user |

---

## 3. Dashboards

### GET `/api/dashboard/personal`

**Operation**: OP07 — Load Personal Dashboard  
**Auth**: Authenticated

**Query params:**
- `user_id` (optional): available to `Admin` and `TeamLead` for read-only employee switching.

**Action Visibility**: Returns actions where the authenticated user is **assigned** OR is the **creator** (`act_created_by`). Actions where the user has **declined** all assignments and is **not** the creator are excluded.

**Response 200:**
```json
{
  "kpis": {
    "total": 24,
    "open": 13,
    "overdue": 3,
    "due_this_week": 5,
    "done": 8
  },
  "overdue_actions": [ /* action summary objects */ ],
  "due_this_week": [ /* action summary objects */ ],
  "recent_completed": [ /* action summary objects, last 7 days */ ],
  "status_distribution": {
    "Not started": 4,
    "On-track": 7,
    "Late": 3,
    "Completed": 8,
    "Cancelled": 0
  },
  "all_actions": [ /* all personal actions sorted by deadline for the By Deadline tab */ ],
  "by_topic": [ /* topic-grouped action collections for the By Category tab */ ],
  "workload_forecast": [
    {
      "label": "W10",
      "label_full": "Mar 8–14",
      "week_start": "2026-03-08",
      "week_end": "2026-03-14",
      "total_hours": 6.5,
      "count": 3
    }
  ]
}
```

> **Notes:**
> - `due_soon_actions` may also be present as a compatibility alias for `due_this_week`.
> - Action summary objects in dashboard, topic, meeting, and admin action-list endpoints expose `asg_total`, the number of assigned users.
> - Personal dashboard action summary objects (in `overdue_actions`, `due_this_week`, `recent_completed`, and `all_actions`) include presentation fields required by the decision-style table layout:
>   - `act_ref`, `act_title`, `act_desc`
>   - `creator_name`
>   - `act_updated_at`
>   - `topic_name`, `meeting_title`, `act_deadline`, `act_status`
> - In Personal Dashboard action tables, the `Meeting` column renders `meeting_title` as the meeting series title or occurrence title fallback, not the raw meeting instance id.
> - This `meeting_title` rendering rule applies to Overview, By Deadline, and By Category personal dashboard action tables.

> **`workload_forecast` notes (personal dashboard):**
> - Array of 16 weekly buckets (current week + next 15).
> - `total_hours` = sum of `asg_estimated_hours / n_overlap_weeks` for the logged-in user's assignments with hours set, spread across each action's `[effective_start, effective_end]` range.
> - Actions without `asg_estimated_hours` are excluded.
> - See R05 §4.3 for the full spreading rule.

---

### GET `/api/dashboard/team/:dept_id` (team-lead view: `/api/dashboard/team-lead?team_id=N`)

**Operation**: OP08 — Load Team Dashboard  
**Auth**: Authenticated (team leaders see their team's data)

**Response 200:**
```json
{
  "team": { "dep_id": 3, "dep_code": "PROD", "dep_name_en": "Production" },
  "kpis": { "total": 86, "open": 40, "done": 34, "overdue": 12 },
  "members": [
    { "usr_id": 15, "usr_display_name": "Alice Wang", "total": 12, "open": 6, "overdue": 2, "due_this_week": 1 }
  ],
  "all_actions": [{ "act_id": 1, "act_title": "...", "act_status": "...", "act_deadline": "2026-04-01", "owner_name": "Alice Wang", "topic_name": "Quality", "assignees": "Alice Wang, Bob Lee" }],
  "overdue_actions": [ /* top 10 */ ],
  "overdue_by_deadline": [ /* overdue rows sorted by deadline */ ],
  "overdue_by_owner": [ /* overdue rows sorted by owner name */ ],
  "overdue_by_category": [ /* overdue rows sorted by topic name */ ],
  "by_lead": [
    { "lead_name": "Alice Wang", "open": 5, "overdue": 2, "actions": [ /* TeamAction objects */ ] }
  ],
  "by_category": [
    { "topic_name": "Quality", "open": 8, "overdue": 3, "actions": [ /* TeamAction objects */ ] }
  ]
}
```

> **`by_lead`**: All team actions grouped by `owner_name`. Groups sorted by overdue count desc, then alphabetically. Cancelled actions are included in the actions array but excluded from open/overdue counts.
> **`by_category`**: All team actions grouped by `topic_name`. Groups sorted by named topics first (unnamed last), then by overdue count desc, then alphabetically.


---

### GET `/api/dashboard/admin`

**Operation**: Global KPI view  
**Auth**: Admin only

**Response 200:**
```json
{
  "kpis": {
    "total_actions": 422,
    "total_users": 35,
    "active_teams": 12,
    "global_completion_rate": 0.68,
    "global_overdue": 28
  },
  "by_team": [
    { "team": "Production", "total": 86, "overdue": 12, "completion_rate": 0.65 }
  ]
}
```

---

## 4. Export

### GET `/api/export/actions`

**Operation**: OP10 — Export to Excel  
**Auth**: Authenticated

**Query Parameters:** Same filters as `GET /api/actions` (without pagination).

**Response 200:**
- Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Content-Disposition: `attachment; filename="ActionHub_Export_2026-02-01.xlsx"`
- Body: Binary .xlsx file

---

## 5. Import

### POST `/api/import/upload`

**Operation**: OP11 — Detect Format  
**Auth**: Admin

**Request:** `multipart/form-data`
- `file`: .xlsx file (max 10 MB)

**Response 200:**
```json
{
  "import_id": "uuid",
  "detected_version": "v3",
  "sheet_name": "Actions 2025",
  "total_rows": 212,
  "preview_rows": [ /* first 20 rows as arrays */ ],
  "column_mapping": {
    "title": "Column B",
    "team": "Column C",
    "owner": "Column E",
    "deadline": "Column F",
    "status": "Column G"
  },
  "unresolved_owners": ["张伟", "Li Wei"],
  "unresolved_teams": [],
  "duplicate_candidates": [
    { "row": 45, "title": "Calibrate sensors", "match_id": 42 }
  ]
}
```

| Error Code | HTTP | Condition |
|------------|------|-----------|
| INVALID_FILE | 422 | Not an .xlsx file |
| FILE_TOO_LARGE | 413 | Exceeds 10 MB |
| FORMAT_UNKNOWN | 422 | Cannot detect logbook version |

---

### POST `/api/import/execute`

**Operation**: OP12 — Execute Import  
**Auth**: Admin

**Request:**
```json
{
  "import_id": "uuid (from upload response)",
  "owner_mappings": {
    "张伟": 15,
    "Li Wei": null
  },
  "team_mappings": {},
  "skip_duplicates": true
}
```

**Response 200:**
```json
{
  "imported": 86,
  "skipped": 2,
  "duplicates_skipped": 1,
  "errors": [],
  "import_log_id": 7
}
```

---

### DELETE `/api/import/:import_log_id`

**Operation**: OP13 — Rollback Import  
**Auth**: Admin

**Response 200:**
```json
{
  "rolled_back": 86,
  "import_log_id": 7,
  "message": "Import rolled back"
}
```

| Error Code | HTTP | Condition |
|------------|------|----------|
| NOT_FOUND | 404 | Import log ID not found |
| ROLLBACK_EXPIRED | 422 | Import older than 24 hours (D98) |

---

## 6. Taxonomy (Reference Data)

### GET `/api/teams`

**Auth**: Authenticated  
**Response 200:**
```json
{
  "data": [
    { "id": 1, "name_en": "Production", "name_cn": "生产部", "code": "PROD", "active": true }
  ]
}
```

### GET `/api/teams/:id/teams`

**Auth**: Authenticated  
**Response 200:**
```json
{
  "data": [
    { "id": 1, "name_en": "Line 1", "name_cn": "1号线", "team_id": 1 }
  ]
}
```

### GET `/api/topics`

**Auth**: Authenticated
**Response 200:**
```json
{
  "data": [
    { "code": "KOM", "name_en": "Maintenance", "name_cn": "维护", "active": true }
  ]
}
```

### GET `/api/categories`

**Auth**: Authenticated

### GET `/api/tags`

**Auth**: Authenticated

*All taxonomy endpoints follow same response shape: `{ "data": [ { id, name_en, name_cn, ... } ] }`*

---

## 7. Users (Admin)

### GET `/api/admin/users`

**Auth**: Admin

**Response 200:**
```json
{
  "data": [
    {
      "id": 1,
      "username": "john.doe",
      "display_name": "John Doe",
      "display_name_cn": "约翰",
      "email": "john@example.com",
      "team_id": 3,
      "role": "Member",
      "active": true,
      "lang": "en",
      "last_login": "2026-02-01T08:30:00"
    }
  ]
}
```

### POST `/api/admin/users`

**Operation**: OP02 — Create User  
**Auth**: Admin

**Request:**
```json
{
  "username": "string (required, 3-50 chars, unique)",
  "password": "string (required, 8-128 chars)",
  "display_name": "string (required)",
  "display_name_cn": "string (optional)",
  "email": "string (optional)",
  "team_id": "int (required)",
  "role": "string (default: 'Member'). Enum: Admin|TeamLead|Member|ReadOnly"
}
```

> **MVP Note (D160)**: MVP enforces binary Admin/Member check only. TeamLead and ReadOnly are stored but treated as Member until V1.1 full RBAC.
```

**Response 201:**
```json
{
  "id": 36,
  "username": "new.user",
  "message": "User created"
}
```

| Error Code | HTTP | Condition |
|------------|------|-----------|
| USERNAME_EXISTS | 409 | Username already taken |
| VALIDATION_ERROR | 422 | Missing/invalid fields |

### PATCH `/api/admin/users/:id`

**Auth**: Admin  
**Request:** Partial update (same fields as POST, minus password).

### POST `/api/admin/users/:id/reset-password`

**Auth**: Admin  
**Request:** `{ "new_password": "string" }`  
**Response 200:** `{ "message": "Password reset" }`

### PATCH `/api/admin/users/:id/deactivate`

**Auth**: Admin  
**Response 200:** `{ "message": "User deactivated" }`

---

## 8. Language

### POST `/api/user/language`

**Operation**: OP14 — Switch Language  
**Auth**: Authenticated

**Request:**
```json
{
  "lang": "string (required). Enum: en|zh"
}
```

**Response 200:**
```json
{
  "lang": "zh",
  "message": "Language updated"
}
```

---

## 9. Health

### GET `/api/health`

**Auth**: None (public)

**Response 200:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "database": "connected",
  "uptime_seconds": 86400
}
```

---

## 10. Workflow (V2)

### Model Note

- Process workflows are the primary workflow model.
- They are started from the existing workflow area of the product, not by automatically binding workflows to actions.
- Existing-action workflow start is a compatibility API pattern only and is not the primary business flow.

### POST `/api/workflow/instances`

**Operation**: Compatibility start of a workflow on an existing action  
**Auth**: Authenticated

**Request:**
```json
{
  "template_id": "int (required, action-type template)",
  "action_id": "int (required)",
  "category_id": "int (optional)",
  "secondary_category_id": "int (optional, must differ from category_id)"
}
```

**Behavior:**
- Manually instantiates a workflow on an existing action.
- Does not imply or restore any automatic workflow start behavior for actions.
- Exists for compatibility and exceptional use cases only.

**Response 201:**
```json
{
  "instance_id": 12,
  "action_id": 104,
  "message": "Workflow started successfully"
}
```

### POST `/api/workflow/requests`

**Operation**: OP34 — Create standalone workflow request  
**Auth**: Authenticated

**Request:**
```json
{
  "template_id": "int (required, request-type template)",
  "title": "string (required, >= 5 chars)",
  "description": "string (optional)",
  "owner_user_id": "int (optional, defaults to current user)",
  "category_id": "int (optional, classification metadata)",
  "secondary_category_id": "int (optional, secondary classification metadata; must differ from category_id)",
  "fields": { "<step_field_key>": "value" }
}
```

**Behavior:**
- Instantiates a workflow instance directly, without forcing creation of a supporting `t_action` row.
- Uses `owner_user_id` as request ownership metadata for startup and future workflow logic; the workflow runtime itself remains the primary work surface.
- Accepts optional classification metadata at request creation time.
- Creates the initial workflow step set and returns the current runtime steps.
- This is the primary runtime entry pattern for process workflows.
- The current SPA uses the returned `instance_id` to open the workflow workbench directly after launch.
- Workflow templates are not auto-linked or auto-started for actions. Linkage must be explicitly set via the workflow API or UI. Bindings only control which templates are available for selection.

**Response 201:**
```json
{
  "instance_id": 12,
  "action_id": null,
  "active_steps": [
    { "id": 301, "key": "request" }
  ]
}
```

| Error Code | HTTP | Condition |
|------------|------|-----------|
| VALIDATION_ERROR | 400 | Missing template/title, title too short, invalid fields |
| NOT_FOUND | 404 | Template not found |
| VALIDATION_ERROR | 400 | `owner_user_id` not found or inactive |

---

### GET `/api/workflow/instances/:id/workbench`

**Operation**: Workflow workbench bootstrap load  
**Auth**: Authenticated

**Response 200:**
```json
{
  "instance": {
    "id": 12,
    "template_name": "OT User Creation",
    "status": "Active",
    "action_id": 104,
    "action_ref": "ACT-2026-0104",
    "display_status": "Facility",
    "sla_state": "DueSoon"
  },
  "current_step": {
    "id": 301,
    "key": "facility",
    "name_en": "Facility",
    "type": "Task",
    "status": "Accepted",
    "assignee": { "id": 22, "display_name": "Alice Chen" },
    "eligible_users": [
      { "id": 22, "display_name": "Alice Chen" },
      { "id": 24, "display_name": "Ben Li" }
    ],
    "entered_at": "2026-03-16T09:00:00",
    "accepted_at": "2026-03-16T09:12:00",
    "sla_deadline": "2026-03-17T09:00:00",
    "comment": null
  },
  "form": {
    "editable_fields": [
      { "key": "badge_code", "type": "text", "label_en": "Badge Code", "required": true, "value": "A-1029" }
    ],
    "context_fields": [
      { "from_step": "request", "field_key": "employee_name", "label_en": "Employee Name", "value": "John Zhang" }
    ]
  },
  "attachments": [
    {
      "id": 8,
      "filename": "badge-request.pdf",
      "mime_type": "application/pdf",
      "size_bytes": 183442,
      "description": "Signed facility request",
      "uploaded_by": { "id": 22, "display_name": "Alice Chen" },
      "uploaded_at": "2026-03-16T09:14:00"
    }
  ],
  "timeline": [
    { "step_key": "request", "name_en": "Request", "status": "Completed", "actor_name": "Workshop Lead", "completed_at": "2026-03-16T08:55:00" },
    { "step_key": "facility", "name_en": "Facility", "status": "Accepted", "actor_name": "Alice Chen", "completed_at": null },
    { "step_key": "hse_validation", "name_en": "HSE Validation", "status": "Pending", "actor_name": null, "completed_at": null }
  ]
}
```

| Error Code | HTTP | Condition |
|------------|------|-----------|
| NOT_FOUND | 404 | Workflow instance not found |
| FORBIDDEN | 403 | User may not view the workbench |

---

### POST `/api/workflow/steps/:id/draft`

**Operation**: Save step draft  
**Auth**: Current step assignee, Admin, or TeamLead with override permission

**Request:**
```json
{
  "comment": "Waiting for signature",
  "fields": [
    { "key": "badge_code", "value": "A-1029" },
    { "key": "card_printed", "value": true }
  ]
}
```

**Behavior:**
- Upserts field values for the step instance.
- Saves partial progress without advancing the workflow.
  "data": {
    "workflow_summary": {
      "id": 12,
      "template_id": 5,
      "template_name": "OT User Creation",
      "type": "request",
      "status": "Active",
      "action": {
        "act_id": 104,
        "act_title": "New OT user request",
        "act_status": "Open"
      }
    },
    "current_steps": [
      {
        "step_id": 301,
        "step_key": "facility",
        "step_name": "Facility",
        "step_type": "Task",
        "status": "Accepted"
      }
    ],
    "field_definitions": [
      { "step_id": 301, "step_key": "facility", "key": "badge_code", "type": "text", "label_en": "Badge Code", "required": true }
    ],
    "field_values": {
      "301": { "badge_code": "A-1029" }
    },
    "attachments": [],
    "timeline": [],
    "eligible_users": []
  "message": "Step reassigned",
  "step_id": 301,
  "delegate_user": { "id": 24, "display_name": "Ben Li" }
}
```

| Error Code | HTTP | Condition |
|------------|------|-----------|
| FORBIDDEN | 403 | User cannot delegate this step |
| VALIDATION_ERROR | 400 | Missing reason or invalid delegate |

---

### POST `/api/workflow/steps/:id/reassign`

**Operation**: Administrative reassignment  
**Auth**: Admin or TeamLead with reassignment permission

**Request:**
```json
{
  "assignee_user_id": 24,
  "reason": "Load balancing"
}
```

**Response 200:**
```json
{
  "message": "Step reassigned",
  "step_id": 301,
  "assignee": { "id": 24, "display_name": "Ben Li" }
}
```

---

### POST `/api/workflow/steps/:id/attachments`

**Operation**: Upload step attachment  
**Auth**: Current step assignee, Admin, or TeamLead with upload permission  
**Content-Type**: `multipart/form-data`

**Form Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | binary | Yes | Attachment payload |
| `description` | string | No | User-entered description |

**Behavior:**
- Validates file extension and MIME type against the step-attachment allowlist.
- Rejects blocked file classes such as CAD, archives, executables, and scripts.
- Stores a `WorkflowStepAttachment` row and writes an audit/history event.

**Response 201:**
```json
{
  "id": 8,
  "filename": "badge-request.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 183442,
  "description": "Signed facility request",
  "uploaded_at": "2026-03-16T09:14:00"
}
```

| Error Code | HTTP | Condition |
|------------|------|-----------|
| FILE_POLICY_BLOCKED | 400 | File type or MIME type not allowed |
| PAYLOAD_TOO_LARGE | 413 | Per-file or cumulative limit exceeded |

---

### DELETE `/api/workflow/steps/:step_id/attachments/:attachment_id`

**Operation**: Soft-delete step attachment  
**Auth**: Attachment uploader, Admin, or TeamLead with delete permission

**Response 200:**
```json
{
  "message": "Attachment deleted",
  "attachment_id": 8
}
```

---

## 11. Meeting Decisions (V3.5)

### GET `/api/decisions`

**Operation**: OP38 — Search Decisions  
**Auth**: Authenticated

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `q` | string | Full-text search query (FTS5 — title + body) |
| `meeting_id` | int | Filter by meeting instance |
| `category_id` | int | Filter by category (matches either attached category) |
| `team_id` | int | Filter by team |
| `status` | string | Comma-separated statuses (Published,Expired) |
| `tags` | string | Partial match on tags field |
| `created_by` | int | Filter by creator user ID |
| `from_date` | date | Decided-at range start (ISO 8601) |
| `to_date` | date | Decided-at range end (ISO 8601) |
| `page` | int | Page number (default 1) |
| `per_page` | int | Items per page (default 25, max 100) |
| `sort` | string | Sort field: `decided_at` (default), `title`, `status`, `created_at` |
| `order` | string | `desc` (default) or `asc` |

**Response 200:**
```json
{
  "data": [
    {
      "id": 1,
      "title": "Migrate to new supplier for raw material X",
      "body": "Agreed to switch from SupplierA to SupplierB due to...",
      "status": "Published",
      "meeting_id": 42,
      "meeting_title": "Weekly Production Review",
      "category_ids": [5, 8],
      "category_names": ["Supply Chain", "Quality"],
      "action_id": null,
      "tags": "supplier,procurement",
      "decided_at": "2026-03-10T10:00:00",
      "created_by": 3,
      "creator_name": "John Doe",
      "created_at": "2026-03-10T10:15:00",
      "updated_at": "2026-03-10T10:15:00"
    }
  ],
  "pagination": { "page": 1, "per_page": 25, "total": 1 }
}
```

---

### GET `/api/decisions/:id`

**Operation**: Read single decision  
**Auth**: Authenticated

**Response 200:**
```json
{
  "data": {
    "id": 1,
    "title": "...",
    "body": "...",
    "status": "Published",
    "meeting_id": 42,
    "meeting_title": "Weekly Production Review",
    "category_ids": [5, 8],
    "category_names": ["Supply Chain", "Quality"],
    "action_id": 104,
    "action_ref": "ACT-2026-0104",
    "tags": "supplier,procurement",
    "decided_at": "2026-03-10T10:00:00",
    "created_by": 3,
    "creator_name": "John Doe",
    "created_at": "2026-03-10T10:15:00",
    "updated_at": "2026-03-10T10:15:00"
  }
}
```

| Error Code | HTTP | Condition |
|------------|------|----------|
| NOT_FOUND | 404 | Decision not found or soft-deleted |

---

### POST `/api/decisions`

**Operation**: OP35 — Create Meeting Decision  
**Auth**: Authenticated (must be meeting organizer/owner or Admin)

**Request:**
```json
{
  "meeting_id": "int (required)",
  "title": "string (required, 2-255 chars)",
  "body": "string (required)",
  "status": "string (optional, default: Published)",
  "category_ids": "[int] (optional, defaults to the meeting's attached categories; max 2)",
  "action_id": "int (optional)",
  "tags": "string (optional, comma-separated)",
  "decided_at": "datetime (optional, defaults to meeting date)"
}
```

**Response 201:**
```json
{
  "data": { "id": 1, "title": "...", "status": "Published", "...":  "..." }
}
```

| Error Code | HTTP | Condition |
|------------|------|----------|
| VALIDATION_ERROR | 400 | Missing required fields, title too short, or more than 2 categories |
| FORBIDDEN | 403 | User is not a meeting organizer/owner |
| NOT_FOUND | 404 | Meeting, topic, or action not found |

---

### PATCH `/api/decisions/:id`

**Operation**: OP36 — Update Meeting Decision  
**Auth**: Authenticated (meeting organizer/owner or Admin)

**Request:**
```json
{
  "title": "string (optional)",
  "body": "string (optional)",
  "tags": "string (optional)",
  "category_ids": "[int] (optional, max 2)",
  "action_id": "int (optional, null to unlink)"
}
```

**Response 200:**
```json
{
  "data": { "id": 1, "title": "...", "...":  "..." }
}
```

| Error Code | HTTP | Condition |
|------------|------|----------|
| FORBIDDEN | 403 | Not organizer/owner |
| NOT_FOUND | 404 | Decision not found |

---

### POST `/api/decisions/:id/status`

**Operation**: OP37 — Transition Decision Status  
**Auth**: Authenticated (meeting organizer/owner or Admin)

**Request:**
```json
{
  "status": "string (required: Published|Expired)"
}
```

**Response 200:**
```json
{
  "data": { "id": 1, "status": "Expired", "...":  "..." }
}
```

| Error Code | HTTP | Condition |
|------------|------|----------|
| VALIDATION_ERROR | 400 | Invalid status transition |
| FORBIDDEN | 403 | Not organizer/owner |
| NOT_FOUND | 404 | Decision not found |

---

### GET `/api/meetings/:id/decisions`

**Operation**: List decisions for a specific meeting  
**Auth**: Authenticated

**Response 200:**
```json
{
  "data": [ { "id": 1, "title": "...", "status": "Published", "...":  "..." } ],
  "pagination": { "page": 1, "per_page": 25, "total": 1 }
}
```

---

### GET `/api/dashboard/decisions`

**Operation**: Decision counts for dashboard widgets  
**Auth**: Authenticated

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `scope` | string | `personal` (default), `team`, `topic`, `all` |
| `team_id` | int | Required when scope=team |
| `topic_id` | int | Required when scope=topic |

**Response 200:**
```json
{
  "data": {
    "scope": "personal",
    "kpis": {
      "total": 18,
      "active": 15,
      "closed": 3,
      "published": 15,
      "expired": 3
    },
    "recent": [
      { "id": 5, "title": "...", "status": "Published", "status_family": "Active", "decided_at": "...", "meeting_title": "Weekly Production Review" }
    ]
  }
}
```

Notes:
- Dashboard-facing decision summary KPIs use status families `active` and `closed`.
- Compatibility aliases `published` and `expired` remain in the payload for existing clients.
- Recent decision rows expose the meeting series title in `meeting_title` / `series_title`; Personal Dashboard renders the series title in the Meeting column.

---

## 12a. Meeting Series Workspace (V3.14)

> **Spec**: R19 — Meeting Series Workspace
>
> **Visibility model** (R19 §9, R03 §2):
> - Meetings & occurrences have `visibility` = `public` (default) or `private`.
> - **Public** meetings/actions: visible to all authenticated users. Non-private actions also visible to user's team leader.
> - **Private** meetings: visible only to occurrence participants. Team leader excluded.
> - **Actions from private meetings**: visible only to action participants (Lead/Decide/Participate). Team leader excluded.
> - **Decisions**: always visible to all authenticated users regardless of meeting visibility (knowledge base). Response includes meeting title but NOT meeting participant list.
>
> **Assignment roles** (R03 §2):
> - `Lead` (exactly 1, compulsory = owner). Legacy roles (Decide, Participate) removed.
> - **Meeting actions**: assignees from occurrence participant list only.
> - **Non-meeting actions**: creator = Lead (self-only, no adding others later).
>
> **Write permissions**:
> - Meeting actions/decisions: only meeting creator can edit. Other participants can add comments/feedback only.
> - Non-meeting actions: only creator can edit.
>
> **Workspace behavior**:
> - Opening an occurrence workspace must show **all series actions** and **all series decisions**, not only items created in the current occurrence.
> - Action and decision rows show the **current live status** of each entity.
> - For actions, the current occurrence workspace also surfaces **previous-occurrence comment context** so users do not need to open the previous meeting just to continue follow-up.

### GET `/api/meetings/series`

**Operation**: List all meeting series  
**Auth**: Authenticated  
**Visibility**: Public series visible to all. Private series visible only to users who are participants of at least one occurrence.

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `topic_id` | int | Filter by category |
| `visibility` | string | Filter by `public` or `private` (optional) |

**Response 200:**
```json
{
  "data": [
    {
      "id": 1,
      "title": "Weekly Operations Review",
      "description": "...",
      "topic_id": 5,
      "topic_name": "Operations",
      "created_by": 1,
      "creator_name": "Admin",
      "occurrence_count": 12,
      "last_occurrence_date": "2026-03-18",
      "default_participant_count": 5
    }
  ]
}
```

---

### POST `/api/meetings/series`

**Operation**: Create a new meeting series  
**Auth**: Admin

**Request:**
```json
{
  "title": "string (required, min 2 chars)",
  "description": "string (optional)",
  "topic_id": "int (optional)"
}
```

**Response 201:**
```json
{
  "data": { "id": 1, "title": "...", "created_by": 1 }
}
```

---

### GET `/api/meetings/series/:id`

**Operation**: Get series detail with default participants  
**Auth**: Authenticated (private series: must be participant)

**Response 200:**
```json
{
  "data": {
    "id": 1,
    "title": "Weekly Operations Review",
    "description": "...",
    "topic_id": 5,
    "topic_name": "Operations",
    "created_by": 1,
    "creator_name": "Admin",
    "default_participants": [
      { "user_id": 2, "username": "alice", "display_name": "Alice", "kind": "Compulsory" },
      { "user_id": 3, "username": "bob", "display_name": "Bob", "kind": "Optional" }
    ],
    "occurrences": [
      { "id": 101, "title": "Week 12", "date": "2026-03-18", "created_at": "2026-03-18T09:30:00", "participant_count": 5 },
      { "id": 100, "title": "Week 11", "date": "2026-03-11", "created_at": "2026-03-11T09:30:00", "participant_count": 4 }
    ]
  }
}
```

Notes:
- In Meeting Series detail UI, the occurrence Date column displays the occurrence creation datetime (`created_at` / `min_created_at`) in China-local format without seconds.
- If `created_at` is unavailable, UI falls back to `date`.

---

### PUT `/api/meetings/series/:id`

**Operation**: Update series title/description  
**Auth**: Admin or series creator

**Request:**
```json
{
  "title": "string (optional)",
  "description": "string (optional)",
  "topic_id": "int (optional)"
}
```

---

### GET `/api/meetings/series/:id/participants`

**Operation**: List default participants  
**Auth**: Authenticated

**Response 200:**
```json
{
  "data": [
    { "id": 1, "user_id": 2, "username": "alice", "display_name": "Alice", "kind": "Compulsory", "added_by": 1, "added_at": "..." }
  ]
}
```

---

### PUT `/api/meetings/series/:id/participants`

**Operation**: Replace default participant list  
**Auth**: Admin or series creator

**Request:**
```json
{
  "participants": [
    { "user_id": 2, "kind": "Compulsory" },
    { "user_id": 3, "kind": "Optional" }
  ]
}
```

---

### POST `/api/meetings/series/:id/participants`

**Operation**: Add a default participant  
**Auth**: Admin or series creator

**Request:**
```json
{
  "user_id": "int (required)",
  "kind": "string (optional, default: Compulsory)"
}
```

---

### DELETE `/api/meetings/series/:id/participants/:uid`

**Operation**: Remove a default participant  
**Auth**: Admin or series creator

---

### POST `/api/meetings/series/:id/occurrences`

**Operation**: Create occurrence with auto-copied participants  
**Auth**: Admin or series creator

**Request:**
```json
{
  "date": "date (optional, ISO 8601; defaults to current date)",
  "notes": "string (optional)"
}
```

**Behavior**: Creates `t_meeting_instance` with `min_meeting_id = series.id`. The occurrence title is auto-generated from the series title and selected date. Auto-copies all series default participants to `t_meeting_participant`. Auto-adds creator as meeting owner.

**Response 201:**
```json
{
  "data": { "id": 101, "title": "Weekly Operations Review - 2026-03-18", "date": "2026-03-18", "meeting_id": 1, "participant_count": 5 }
}
```

---

### GET `/api/meetings/series/:id/actions`

**Operation**: All actions across series occurrences  
**Auth**: Authenticated  
**Visibility**: Actions from private occurrences filtered to action participants only.

**Usage note**: This endpoint powers the occurrence workspace action panel. The workspace uses it to show the full series action backlog with each action's current live status and occurrence provenance.

**Response 200:**
```json
{
  "data": [
    {
      "id": 42,
      "ref": "ACT-2026-0042",
      "title": "Fix pump",
      "status": "Done",
      "occurrence_id": 99,
      "occurrence_date": "2026-03-04",
      "assignees": ["Alice"],
      "priority": "High"
    }
  ]
}
```

**Query**: `SELECT a.* FROM t_action a JOIN t_meeting_instance mi ON a.act_meeting_inst_id = mi.min_id WHERE mi.min_meeting_id = ? AND a.act_archived = 0`

---

### GET `/api/meetings/series/:id/decisions`

**Operation**: All decisions across series occurrences  
**Auth**: Authenticated  
**Visibility**: Always visible (decisions are public knowledge base). Response includes meeting title but excludes meeting participant list.

**Usage note**: This endpoint powers the occurrence workspace decision panel. The workspace uses it to show the full series decision history with each decision's current live status.

**Response 200:**
```json
{
  "data": [
    {
      "id": 10,
      "title": "Budget approved for Q2",
      "status": "Posted",
      "occurrence_id": 99,
      "occurrence_date": "2026-03-04",
      "category_name": "Finance"
    }
  ]
}
```

---

### GET `/api/meetings/:min_id/occurrence-comments`

**Operation**: Comments on series actions grouped by occurrence  
**Auth**: Authenticated

**Usage note**: This endpoint supplies the previous-occurrence follow-up context shown inline on the current occurrence workspace, so users can continue action follow-up without opening the previous meeting.

**Response 200:**
```json
{
  "data": {
    "current": [
      { "comment_id": 5, "action_id": 42, "action_title": "Fix pump", "body": "Quote received", "author": "Charlie", "created_at": "..." }
    ],
    "previous": [
      { "comment_id": 3, "action_id": 42, "action_title": "Fix pump", "body": "Waiting for supplier", "author": "Bob", "created_at": "...", "occurrence_date": "2026-03-11" }
    ]
  }
}
```

---

### GET `/api/meetings/:min_id/minutes/pdf`

**Operation**: Generate Minutes of Meeting PDF  
**Auth**: Authenticated

**Response 200**: Binary PDF file  
**Content-Type**: `application/pdf`  
**Content-Disposition**: `attachment; filename="MoM_WeeklyOpsReview_2026-03-18.pdf"`

**PDF Sections**: Header (series title, date), Participants, Memo, Actions Reviewed, New Actions, Decisions.

---

## 12. Error Code Reference

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| AUTH_REQUIRED | 401 | No valid session |
| AUTH_INVALID | 401 | Wrong credentials |
| AUTH_LOCKED | 423 | Account locked |
| AUTH_DISABLED | 403 | Account deactivated |
| FORBIDDEN | 403 | Insufficient role |
| NOT_FOUND | 404 | Resource not found |
| VALIDATION_ERROR | 422 | Request validation failed |
| INVALID_TRANSITION | 422 | Status transition not allowed |
| REASON_REQUIRED | 422 | Missing reason field |
| DATE_REQUIRED | 422 | Missing date field |
| USERNAME_EXISTS | 409 | Duplicate username |
| ALREADY_ASSIGNED | 409 | Duplicate assignment |
| INVALID_FILE | 422 | Bad file format |
| FILE_TOO_LARGE | 413 | File exceeds limit |
| FORMAT_UNKNOWN | 422 | Unrecognized import format |
| INTERNAL_ERROR | 500 | Server error |
