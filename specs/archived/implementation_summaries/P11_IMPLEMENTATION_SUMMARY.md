# P11 Taxonomy Category Consolidation — Implementation Summary

**Date**: 2026-03-17  
**Status**: 🔄 In Progress (Schema + Decision/Meeting services complete)

---

## Overview

P11 implements the dual-category model across ActionHub, allowing entities to have up to 2 attached categories (stored in `t_topic` / `TOP_*`). This ensures Actions, Meetings, Decisions, and Workflow Instances can be classified under multiple strategic categories for better reporting and dashboard visibility.

---

## What Has Been Completed

### 1. Schema Changes ✅

**File**: `action_hub/db/schema.sql`

#### t_meeting_instance
```sql
ALTER TABLE t_meeting_instance 
  ADD COLUMN min_secondary_topic_id INTEGER REFERENCES t_topic(top_code);
```

#### t_workflow_instance
```sql
ALTER TABLE t_workflow_instance
  ADD COLUMN wfi_topic_id INTEGER REFERENCES t_topic(top_code),
  ADD COLUMN wfi_secondary_top_id INTEGER REFERENCES t_topic(top_code);
```

#### t_meeting_decision (new table definition)
```sql
CREATE TABLE t_meeting_decision (
    mdc_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    mdc_instance_id     INTEGER NOT NULL,
    mdc_title           TEXT NOT NULL,
    mdc_body            TEXT NOT NULL,
    mdc_status          TEXT NOT NULL DEFAULT 'Proposed',
    mdc_topic_id        INTEGER REFERENCES t_topic(top_code),
    mdc_secondary_top_id INTEGER REFERENCES t_topic(top_code),
    mdc_linked_action_id INTEGER REFERENCES t_action(act_id),
    mdc_tags            TEXT,
    mdc_decided_at      TEXT,
    mdc_created_by      INTEGER NOT NULL,
    mdc_created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    mdc_updated_at      TEXT,
    mdc_deleted_at      TEXT
);
```

#### Indexes Created
```sql
CREATE INDEX idx_meeting_secondary_topic ON t_meeting_instance(min_secondary_topic_id) 
    WHERE min_secondary_topic_id IS NOT NULL;

CREATE INDEX idx_workflow_topic ON t_workflow_instance(wfi_topic_id) 
    WHERE wfi_topic_id IS NOT NULL;

CREATE INDEX idx_workflow_secondary_topic ON t_workflow_instance(wfi_secondary_top_id) 
    WHERE wfi_secondary_top_id IS NOT NULL;

CREATE INDEX idx_decision_secondary_topic ON t_meeting_decision(mdc_secondary_top_id) 
    WHERE mdc_secondary_top_id IS NOT NULL;
```

#### FTS5 for Meeting Decisions
```sql
CREATE VIRTUAL TABLE t_meeting_decision_fts USING fts5(
    mdc_title, mdc_body, mdc_tags,
    content='t_meeting_decision',
    content_rowid='mdc_id'
);
-- Plus triggers to keep FTS5 in sync
```

---

### 2. Migration Script ✅

**File**: `action_hub/migrations/migrate_v7_0.py`

The migration script:
1. Adds `min_secondary_topic_id` to `t_meeting_instance`
2. Adds `wfi_topic_id` and `wfi_secondary_top_id` to `t_workflow_instance`
3. Adds `mdc_topic_id` and `mdc_secondary_top_id` to `t_meeting_decision` (if missing)
4. Creates all required indexes
5. Recreates `v_action_detail` view

**How to run**:
```bash
cd action_hub
..\.venv\Scripts\python.exe migrations/migrate_v7_0.py
```

---

### 3. Backend Services Updated ✅

#### actionhub/decisions/service.py (Complete Rewrite)

**Key Changes**:
- `create_decision()`: 
  - Accepts `topic_id` and `secondary_topic_id`
  - Validates secondary ≠ primary
  - Defaults from meeting if not provided
- `get_decision()`: Returns both topic names via JOIN
- `list_decisions()`: 
  - New `topic_id` filter matches primary OR secondary
  - Returns both topic names
- `update_decision()`: Validates topic uniqueness
- `count_by_topic()`: New method to count decisions by category

**API Pattern**:
```python
data = {
    "title": "Decision title",
    "body": "Decision description",
    "meeting_id": 123,
    "topic_id": 456,              # Optional
    "secondary_topic_id": 789,     # Optional, must differ from topic_id
    "linked_action_id": 101,
    "tags": "tag1,tag2",
    "created_by": 1
}
decision_id = DecisionService.create_decision(data)
```

#### actionhub/meetings/service.py (Updated)

**Key Changes**:
- `list_meetings(topic_id)`: Filter matches primary OR secondary topic
- `get_meeting()`: Returns both `topic_name` and `secondary_topic_name`
- `create_meeting()`: 
  - Accepts `topic_id` and `secondary_topic_id`
  - Validates secondary ≠ primary
- `update_meeting()`: Validates topic uniqueness

**API Pattern**:
```python
payload = {
    "title": "Meeting title",
    "topic_id": 456,
    "secondary_topic_id": 789,  # Optional
    "notes": "Meeting notes",
    "date": "2026-03-20",
    "type": "Weekly"
}
meeting = create_meeting(payload, actor_id=1)
```

---

## What Still Needs to Be Done

### Backend Services (Remaining)

1. **actionhub/workflow/service.py**:
   - Add `topic_id` and `secondary_topic_id` parameters to `instantiate_workflow()`
   - Validate topic uniqueness
   - Persist topics when creating workflow instance

2. **actionhub/actions/service.py**:
   - Verify `act_secondary_topic_code` is properly handled in create/update
   - Add `category_ids` array pattern for backward compatibility
   - Update list queries to resolve both topic names

3. **actionhub/dashboard/service.py**:
   - Update "By Category" grouping to duplicate actions in both categories
   - Update category summary counts to include secondary category matches
   - Update personal dashboard queries

4. **actionhub/gantt/service.py**:
   - Update `topic_id` filter to match either category

5. **actionhub/export/service.py**:
   - Add "Category 2" column to Excel exports

---

### Frontend Components

1. **frontend/src/pages/actions/ActionDetail.tsx**:
   - Add Category 2 dropdown below Category 1
   - Validate secondary ≠ primary
   - Display both categories

2. **frontend/src/pages/actions/ActionsList.tsx**:
   - Add "Category 2" column to table
   - Include Category 2 in filter

3. **frontend/src/pages/meetings/MeetingDetail.tsx**:
   - Add secondary category selector
   - Display both categories

4. **frontend/src/pages/decisions/DecisionsList.tsx**:
   - Show both categories in table
   - Filter by category (matches either)

5. **frontend/src/pages/dashboard/Category.tsx**:
   - Show "Also in: CategoryName" indicator for cross-listed actions

6. **frontend/src/pages/dashboard/Personal.tsx**:
   - Actions appear in both category groups

7. **actionhub/i18n/en.json** and **zh.json**:
   - Add keys for "Category 2", "Secondary Category", etc.

---

### Testing

1. **action_hub/tests/test_p11_category_consolidation.py**:
   - Test dual-category creation/validation
   - Test secondary ≠ primary validation
   - Test category filters match both categories
   - Test dashboard counts include both categories
   - Test meeting → action topic inheritance (both categories)

2. **Migration Testing**:
   - Run `migrate_v7_0.py` on test database
   - Verify no data loss
   - Verify indexes created correctly

---

## Validation Rules

### Primary + Secondary Category Constraints

1. **Actions**: 
   - Primary category: **Required**
   - Secondary category: **Optional**
   - Rule: `secondary_topic_code != topic_code`

2. **Meetings**:
   - Primary category: **Optional**
   - Secondary category: **Optional**
   - Rule: `secondary_topic_id != topic_id` (if both set)

3. **Meeting Decisions**:
   - Primary category: **Optional** (defaults from meeting)
   - Secondary category: **Optional** (defaults from meeting)
   - Rule: `secondary_top_id != topic_id` (if both set)

4. **Workflow Instances**:
   - Primary category: **Optional**
   - Secondary category: **Optional**
   - Rule: `secondary_top_id != topic_id` (if both set)

---

## API Changes

### Backward Compatibility

The dual-category model is **backward compatible**:
- Existing single-category entities continue to work
- Secondary category columns are nullable
- Old API calls without `secondary_topic_id` work as before

### New API Patterns

#### Action Create/Update
```json
{
  "title": "Action title",
  "category_ids": [456, 789],  // 1-2 category IDs
  // OR (backward compatible)
  "topic_id": 456,
  "secondary_topic_id": 789
}
```

#### Meeting Create/Update
```json
{
  "title": "Meeting title",
  "topic_id": 456,
  "secondary_topic_id": 789
}
```

#### Decision Create/Update
```json
{
  "title": "Decision title",
  "meeting_id": 123,
  "topic_id": 456,
  "secondary_topic_id": 789
}
```

#### Workflow Instance Creation
```json
{
  "template_id": 1,
  "action_id": 123,
  "topic_id": 456,
  "secondary_topic_id": 789
}
```

---

## Dashboard Behavior

### Category Dashboard (`/api/dashboard/category?category_id=X`)

- Returns actions where `act_topic_id = X OR act_secondary_topic_id = X`
- Actions with 2 categories appear in **both** category dashboards
- Cross-listed actions show "Also in: CategoryName" indicator

### Categories Summary (`/api/dashboard/categories/summary`)

- Counts actions under every attached category
- Actions with 2 categories are counted **twice** (once per category)

### Personal Dashboard (`/api/dashboard/personal`)

- "By Category" tab: Actions appear in both category groups
- Overview table: Shows both categories as comma-separated list

---

## Next Steps

1. **Complete backend services** (workflow, actions, dashboard, gantt, export)
2. **Update frontend components** (ActionDetail, ActionsList, MeetingDetail, etc.)
3. **Add i18n strings** for new UI labels
4. **Write integration tests**
5. **Run migration on test database**
6. **Validate with user acceptance testing**

---

## Files Modified

| File | Status | Changes |
|------|--------|---------|
| `action_hub/db/schema.sql` | ✅ Done | Added dual-category columns, indexes, FTS5 |
| `action_hub/migrations/migrate_v7_0.py` | ✅ Done | Migration script |
| `actionhub/decisions/service.py` | ✅ Done | Complete rewrite for dual-category |
| `actionhub/meetings/service.py` | ✅ Done | Updated list/get/create/update |
| `actionhub/workflow/service.py` | ⏳ Pending | Add topic support to instantiate |
| `actionhub/actions/service.py` | ⏳ Pending | Verify secondary topic handling |
| `actionhub/dashboard/service.py` | ⏳ Pending | Update category queries |
| `actionhub/gantt/service.py` | ⏳ Pending | Update topic filters |
| `actionhub/export/service.py` | ⏳ Pending | Add Category 2 column |
| `frontend/src/pages/actions/ActionDetail.tsx` | ⏳ Pending | Add Category 2 selector |
| `frontend/src/pages/actions/ActionsList.tsx` | ⏳ Pending | Add Category 2 column |
| `frontend/src/pages/meetings/MeetingDetail.tsx` | ⏳ Pending | Add secondary category |
| `frontend/src/pages/decisions/DecisionsList.tsx` | ⏳ Pending | Show both categories |
| `frontend/src/pages/dashboard/Category.tsx` | ⏳ Pending | Cross-listed indicator |
| `actionhub/i18n/en.json` | ⏳ Pending | Add new keys |
| `actionhub/i18n/zh.json` | ⏳ Pending | Add new keys |
| `action_hub/tests/test_p11_category_consolidation.py` | ⏳ Pending | Integration tests |

---

## Estimated Completion

- **Backend services**: 2-3 hours
- **Frontend components**: 3-4 hours
- **i18n**: 30 minutes
- **Testing**: 1-2 hours
- **Total**: 7-10 hours remaining

---

## Questions or Issues

If you encounter any issues during implementation:
1. Check that migration V7.0 has been applied
2. Verify secondary ≠ primary validation is working
3. Ensure category filters match BOTH primary and secondary
4. Confirm dashboard counts include both categories

For questions about the dual-category model, refer to:
- `specs/requirements/R08_taxonomy.md`
- `specs/specifications/S54_secondary_topic.md`
- `specs/specifications/S05_data_dictionary.md`
