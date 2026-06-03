# WF-21 Implementation Summary

**Date**: 2026-03-17  
**Status**: ✅ DONE  
**Test Count**: 10 new tests in `test_workflow_workbench.py`

---

## Overview

WF-21 implements the backend API surface for the Workflow Management Workbench as specified in S73. This provides the frontend with all necessary data and operations to render and operate the workbench UI.

---

## Files Created/Modified

### New Files

1. **`action_hub/actionhub/workflow/attachments.py`** (382 lines)
   - Attachment management service with policy enforcement
   - Functions: `upload_attachment()`, `get_step_attachments()`, `get_attachment()`, `delete_attachment()`
   - Policy: 25MB max file size, 10 files per step, 100MB per workflow
   - Allowed types: pdf, docx, xlsx, pptx, csv, txt, png, jpg

2. **`action_hub/tests/test_workflow_workbench.py`** (523 lines)
   - Test class: `TestWorkflowWorkbenchAPI` (8 tests)
   - Test class: `TestWorkflowHistory` (1 test)
   - Test class: `TestWorkbenchService` (1 test)
   - Coverage: workbench load, draft save, attachment CRUD, history timeline

3. **`action_hub/run_wf21_tests.py`** (38 lines)
   - Test runner script with log capture

### Modified Files

1. **`action_hub/migrations/migrate_v6_0.py`**
   - Added `t_workflow_step_attachment` table DDL
   - Added indexes for step_id and action_id

2. **`action_hub/actionhub/workflow/service.py`**
   - Added `get_workflow_history()` - timeline/history retrieval
   - Added `get_workbench_data()` - comprehensive workbench data loader
   - Added `save_step_draft()` - partial field value persistence

3. **`action_hub/actionhub/workflow/routes.py`**
   - Added 6 new endpoints (see API section below)
   - Added helper functions: `_require_admin_or_step_assignee()`, `_require_step_assignee()`, `get_step_instance()`

---

## API Endpoints Implemented

### 1. GET `/api/workflow/instances/<instance_id>/workbench`

**Purpose**: Load complete workbench data in single call

**Response**:
```json
{
  "data": {
    "workflow_summary": {
      "id": 1,
      "template_id": 1,
      "template_name": "OT Request",
      "status": "Active",
      "outcome": null,
      "started_at": "2026-03-17T10:00:00",
      "action": {"id": 42, "title": "...", "status": "In Progress"}
    },
    "current_steps": [
      {
        "step_id": 10,
        "step_key": "hse_review",
        "step_name": "HSE Review",
        "step_type": "Task",
        "status": "Accepted",
        "assignee": "John Doe",
        "entered_at": "2026-03-17T10:00:00",
        "accepted_at": "2026-03-17T10:05:00",
        "sla_deadline": "2026-03-19T10:00:00"
      }
    ],
    "field_definitions": [
      {"key": "safety_checklist", "type": "checklist", "label_en": "Safety Checklist", "required": true}
    ],
    "field_values": {
      "10": {"safety_checklist": "item1,item2"}
    },
    "attachments": [...],
    "timeline": [...],
    "eligible_users": [...]
  }
}
```

**Authorization**: Authenticated user with access to step

---

### 2. POST `/api/workflow/steps/<step_instance_id>/draft`

**Purpose**: Save partial work without advancing workflow

**Request**:
```json
{
  "fields": [
    {"key": "field1", "value": "value1"},
    {"key": "field2", "value": "value2"}
  ],
  "comment": "Progress note"
}
```

**Response**:
```json
{
  "data": {
    "success": true,
    "step_id": 10,
    "fields_saved": 2,
    "comment_updated": true
  }
}
```

**Authorization**: Step assignee or admin

---

### 3. GET `/api/workflow/steps/<step_instance_id>/attachments`

**Purpose**: List active attachments for a step

**Response**:
```json
{
  "data": [
    {
      "id": 1,
      "filename": "safety_report.pdf",
      "size_bytes": 102400,
      "mime_type": "application/pdf",
      "uploaded_by": 1,
      "uploaded_by_name": "John Doe",
      "uploaded_at": "2026-03-17T11:00:00",
      "description": "Safety inspection report"
    }
  ]
}
```

**Authorization**: Step assignee or admin

---

### 4. POST `/api/workflow/steps/<step_instance_id>/attachments`

**Purpose**: Upload file attachment

**Request**: `multipart/form-data`
- `file`: File binary (required)
- `description`: Text description (optional)

**Response** (201 Created):
```json
{
  "data": {
    "id": 1,
    "filename": "safety_report.pdf",
    "size_bytes": 102400,
    "mime_type": "application/pdf",
    "uploaded_at": "2026-03-17T11:00:00"
  }
}
```

**Policy Enforcement**:
- Allowed extensions: pdf, docx, xlsx, pptx, csv, txt, png, jpg
- Max file size: 25 MB
- Max files per step: 10
- Max cumulative per workflow: 100 MB

**Authorization**: Step assignee or admin

---

### 5. DELETE `/api/workflow/steps/<step_instance_id>/attachments/<attachment_id>`

**Purpose**: Soft-delete an attachment

**Response**:
```json
{
  "data": {
    "success": true,
    "attachment_id": 1
  }
}
```

**Authorization**: Uploader, admin, or team lead

---

### 6. GET `/api/workflow/attachments/<attachment_id>/download`

**Purpose**: Download attachment file

**Response**: File download with appropriate `Content-Type` and `Content-Disposition` headers

**Authorization**: Step assignee or admin

---

## Database Schema Changes

### t_workflow_step_attachment

```sql
CREATE TABLE t_workflow_step_attachment (
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

CREATE INDEX idx_attachment_step ON t_workflow_step_attachment(wsa_step_inst_id);
CREATE INDEX idx_attachment_action ON t_workflow_step_attachment(wsa_action_id) WHERE wsa_deleted_at IS NULL;
```

**Storage**: Files stored in `action_hub/attachments/workflow/<year>/<month>/<uuid>.<ext>`

---

## Key Implementation Details

### 1. Authorization Model

All workbench endpoints enforce access control:
- **Step assignee**: Full access to their assigned steps
- **Admin**: Full access to all steps
- **TeamLead**: Full access (via `_require_admin_or_step_assignee`)
- **Other users**: No access (read-only via separate mechanism if needed)

### 2. File Storage Strategy

- Files stored with UUID filenames to prevent collisions
- Organized by year/month for filesystem performance
- Soft-delete preserves file on disk (can implement cleanup later)
- Path: `action_hub/attachments/workflow/2026/03/a1b2c3d4.pdf`

### 3. Draft Save Pattern

- Uses `INSERT ... ON CONFLICT DO UPDATE` for upsert
- Does NOT trigger workflow advancement
- Does NOT change step status
- Validates field types but not required fields
- Optional comment stored in `wsi_comment`

### 4. Workbench Data Aggregation

The `get_workbench_data()` function performs 8 queries:
1. Workflow instance + template info
2. Action info (if bound)
3. Current active steps
4. Step field definitions (from graph JSON)
5. Saved field values
6. Attachments for first active step
7. Timeline/history
8. Eligible users for delegation

This provides a single API call to populate the entire workbench UI.

---

## Test Coverage

### Test Classes

1. **TestWorkflowWorkbenchAPI** (8 tests)
   - `test_workbench_load_no_instance` - 404 handling
   - `test_workbench_load_with_instance` - successful load
   - `test_draft_save_success` - field persistence
   - `test_draft_save_unauthorized` - access control
   - `test_attachment_upload_success` - file upload
   - `test_attachment_upload_invalid_type` - policy enforcement
   - `test_attachment_list` - list retrieval
   - `test_attachment_delete` - soft-delete

2. **TestWorkflowHistory** (1 test)
   - `test_get_workflow_history` - timeline retrieval

3. **TestWorkbenchService** (1 test)
   - `test_save_step_draft` - service function test

### Running Tests

```bash
cd action_hub
..\..\.venv\Scripts\python.exe -m pytest tests/test_workflow_workbench.py -v
```

---

## Dependencies

- **WF-10**: 3-phase lifecycle (step statuses)
- **WF-16**: Timeline endpoint foundation
- **WF-19**: Assignment rules
- **WF-20**: Delegation and eligible users

---

## Next Steps (WF-22)

WF-22 will implement the frontend workbench UI:
1. Workflow tab in `ActionDetail.tsx`
2. `WorkbenchPanel.tsx` component
3. Step action buttons (Accept, Complete, Reject, Delegate)
4. Form rendering with field validation
5. Attachment upload UI with drag-drop
6. Timeline visualization
7. i18n strings for all workbench UI elements

---

## Known Limitations

1. **No email notifications** for attachment events (deferred to V2.5+)
2. **No virus scanning** on uploads (LAN environment assumption)
3. **No file versioning** - new upload replaces old (by design)
4. **No attachment preview** - download only (frontend to implement preview in WF-22)
5. **Storage cleanup** - deleted files remain on disk (future enhancement)

---

## Compliance

- ✅ S73 §4 (Workbench Screen Model) - API supports all sections
- ✅ S73 §5 (Step Assignment) - delegation/reassignment ready
- ✅ S73 §6 (Status) - multi-layer status exposed
- ✅ S73 §7 (Step Form) - draft save and field definitions
- ✅ S73 §8 (Attachments) - full CRUD with policy
- ✅ S16 API Contract - follows REST conventions
- ✅ Security - parameterized SQL, authorization checks, file validation
