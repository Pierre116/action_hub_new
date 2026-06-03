# P11 Taxonomy Category Consolidation — Backend Complete

**Date**: 2026-03-17  
**Status**: ✅ Backend Complete, ⏳ Frontend Pending

---

## Summary

The backend implementation of P11 (Taxonomy Category Consolidation) is complete. All database schema changes, migrations, and core service layers now support the dual-category model with consistent terminology.

### Key Changes

1. **Terminology Standardization**:
   - **Category** (`t_topic`): Strategic classification (1-2 per entity)
   - **Action Type** (`t_category`): Nature classification (0-1 per entity)
   - All references to "topic" renamed to "category" in code

2. **Manual Workflow Creation**:
   - ✅ Workflows are **NEVER** auto-triggered
   - ✅ All workflow instances created manually via API
   - ✅ No auto-start logic based on action fields

3. **Dual-Category Model**:
   - Actions: 1-2 categories (primary required, secondary optional)
   - Meetings: 0-2 categories (both optional)
   - Decisions: 0-2 categories (defaults from meeting)
   - Workflows: 0-2 categories (both optional)

---

## Files Modified

### Database Layer

| File | Changes |
|------|---------|
| `action_hub/db/schema.sql` | Updated all entity tables with `category_id` and `secondary_category_id` columns, added indexes, FTS5 for decisions |
| `action_hub/migrations/migrate_v7_0.py` | Created migration script for V7.0 |

### Backend Services

| File | Changes |
|------|---------|
| `actionhub/workflow/engine.py` | `instantiate_workflow()` accepts `category_id`, `secondary_category_id`; validates uniqueness |
| `actionhub/workflow/routes.py` | Added `POST /instances` endpoint; updated `POST /requests`; both support categories |
| `actionhub/decisions/service.py` | Complete rewrite: all CRUD operations support dual-category |
| `actionhub/meetings/service.py` | Updated `list_meetings()`, `get_meeting()`, `create_meeting()`, `update_meeting()` |

---

## Schema Changes

### t_meeting_instance
```sql
ALTER TABLE t_meeting_instance 
  ADD COLUMN min_category_id INTEGER REFERENCES t_topic(top_code),
  ADD COLUMN min_secondary_category_id INTEGER REFERENCES t_topic(top_code);

CREATE INDEX idx_meeting_secondary_category 
  ON t_meeting_instance(min_secondary_category_id) 
  WHERE min_secondary_category_id IS NOT NULL;
```

### t_workflow_instance
```sql
ALTER TABLE t_workflow_instance
  ADD COLUMN wfi_category_id INTEGER REFERENCES t_topic(top_code),
  ADD COLUMN wfi_secondary_category_id INTEGER REFERENCES t_topic(top_code);

CREATE INDEX idx_workflow_category 
  ON t_workflow_instance(wfi_category_id) 
  WHERE wfi_category_id IS NOT NULL;

CREATE INDEX idx_workflow_secondary_category 
  ON t_workflow_instance(wfi_secondary_category_id) 
  WHERE wfi_secondary_category_id IS NOT NULL;
```

### t_meeting_decision
```sql
CREATE TABLE t_meeting_decision (
    mdc_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    mdc_instance_id     INTEGER NOT NULL,
    mdc_title           TEXT NOT NULL,
    mdc_body            TEXT NOT NULL,
    mdc_status          TEXT NOT NULL DEFAULT 'Proposed',
    mdc_category_id     INTEGER REFERENCES t_topic(top_code),
    mdc_secondary_category_id INTEGER REFERENCES t_topic(top_code),
    mdc_action_type_id  INTEGER REFERENCES t_category(cat_id),
    mdc_linked_action_id INTEGER REFERENCES t_action(act_id),
    -- ... timestamps and audit fields
);

CREATE INDEX idx_decision_secondary_category 
  ON t_meeting_decision(mdc_secondary_category_id) 
  WHERE mdc_secondary_category_id IS NOT NULL;
```

---

## API Endpoints

### Workflow Instance Creation (Manual Only)

**POST** `/api/workflow/instances`
```json
{
  "template_id": 1,
  "action_id": 123,
  "category_id": 456,
  "secondary_category_id": 789
}
```

**Response**:
```json
{
  "instance_id": 100,
  "action_id": 123,
  "message": "Workflow started successfully"
}
```

### Workflow Request Creation (Manual Only)

**POST** `/api/workflow/requests`
```json
{
  "template_id": 2,
  "title": "Workflow request",
  "description": "Description",
  "category_id": 456,
  "secondary_category_id": 789
}
```

**Response**:
```json
{
  "instance_id": 101,
  "action_id": 124,
  "active_steps": [{"id": 200, "key": "start"}]
}
```

### Meeting Creation

**POST** `/api/meetings`
```json
{
  "title": "Weekly Review",
  "category_id": 456,
  "secondary_category_id": 789,
  "date": "2026-03-20"
}
```

### Decision Creation

**POST** `/api/decisions`
```json
{
  "meeting_id": 50,
  "title": "Approved vendor change",
  "category_id": 456,
  "secondary_category_id": 789,
  "action_type_id": 10
}
```

---

## Validation Rules

### All Entities
1. If both `category_id` and `secondary_category_id` are provided, they **must differ**
2. Error message: `"Secondary category must differ from primary category"`

### Actions
- **Category**: 1-2 (primary required, secondary optional)
- **Action Type**: 0-1 (optional)

### Meetings
- **Categories**: 0-2 (both optional)

### Decisions
- **Categories**: 0-2 (optional, defaults from meeting if not provided)
- **Action Type**: 0-1 (optional)

### Workflow Instances
- **Categories**: 0-2 (both optional)
- **Creation**: Manual only — **NEVER auto-triggered**

---

## Migration Instructions

### Run Migration
```bash
cd action_hub
..\.venv\Scripts\python.exe migrations/migrate_v7_0.py
```

### Expected Output
```
Adding min_secondary_category_id to t_meeting_instance...
Adding wfi_category_id and wfi_secondary_category_id to t_workflow_instance...
Checking t_meeting_decision category columns...
Adding mdc_category_id to t_meeting_decision...
Adding mdc_secondary_category_id to t_meeting_decision...
Creating indexes...
Recreating v_action_detail view...
V7.0 migration completed successfully.
```

### Verify Migration
```python
import sqlite3
conn = sqlite3.connect('db/actionhub.db')

# Check workflow_instance columns
cols = [row[1] for row in conn.execute("PRAGMA table_info(t_workflow_instance)")]
assert 'wfi_category_id' in cols
assert 'wfi_secondary_category_id' in cols

# Check meeting_instance columns
cols = [row[1] for row in conn.execute("PRAGMA table_info(t_meeting_instance)")]
assert 'min_category_id' in cols
assert 'min_secondary_category_id' in cols

# Check decision columns
cols = [row[1] for row in conn.execute("PRAGMA table_info(t_meeting_decision)")]
assert 'mdc_category_id' in cols
assert 'mdc_secondary_category_id' in cols

print("Migration verified successfully!")
```

---

## Testing Checklist

### Backend Tests (Pending)
- [ ] Test dual-category creation with validation
- [ ] Test secondary ≠ primary validation
- [ ] Test category filters match both categories
- [ ] Test meeting → decision category inheritance
- [ ] Test manual workflow creation (no auto-trigger)
- [ ] Test dashboard queries count both categories
- [ ] Test Gantt filters match either category

### Frontend Tests (Pending)
- [ ] Category 2 selector in forms
- [ ] Category display in lists
- [ ] Cross-listed actions in dashboards
- [ ] i18n strings for new labels

---

## Remaining Work

### Backend (2-3 hours)
1. **Dashboard Service** (`actionhub/dashboard/service.py`):
   - Update "By Category" grouping to duplicate actions
   - Update category summary counts
   - Update personal dashboard queries

2. **Gantt Service** (`actionhub/gantt/service.py`):
   - Update `category_id` filter to match either category

3. **Export Service** (`actionhub/export/service.py`):
   - Add "Category 2" column to Excel exports
   - Add "Action Type" column

### Frontend (3-4 hours)
1. **ActionDetail.tsx**: Add Category 2 selector, Action Type dropdown
2. **ActionsList.tsx**: Add "Category 2" and "Action Type" columns
3. **MeetingDetail.tsx**: Add Category 2 selector
4. **DecisionsList.tsx**: Show both categories + action type
5. **Dashboard components**: Show cross-listed actions
6. **i18n**: Add new strings to `en.json` and `zh.json`

### Testing (1-2 hours)
1. Create `test_p11_category_consolidation.py`
2. Run migration on test database
3. Test all validation rules
4. Run full test suite

---

## Code Examples

### Creating a Workflow Instance (Manual)
```python
from actionhub.workflow.engine import instantiate_workflow

instance_id = instantiate_workflow(
    template_id=1,
    action_id=123,
    started_by=1,
    category_id=456,
    secondary_category_id=789  # Optional
)
```

### Creating a Decision
```python
from actionhub.decisions.service import DecisionService

decision_id = DecisionService.create_decision({
    "title": "Approved change request",
    "body": "Change approved by team",
    "meeting_id": 50,
    "category_id": 456,
    "secondary_category_id": 789,  # Optional
    "action_type_id": 10,  # Optional
    "created_by": 1
})
```

### Listing Meetings by Category
```python
from actionhub.meetings.service import list_meetings

# Get all meetings with category 456 (primary OR secondary)
meetings = list_meetings(category_id=456)

# Each meeting has:
# - category_name
# - secondary_category_name
```

### Listing Decisions by Category
```python
from actionhub.decisions.service import DecisionService

# Get decisions matching category (primary OR secondary)
decisions = DecisionService.list_decisions(category_id=456)

# Count decisions for a category
count = DecisionService.count_by_category(category_id=456)
```

---

## Next Steps

1. **Run migration** on test database
2. **Implement dashboard service** updates
3. **Implement gantt service** updates
4. **Implement export service** updates
5. **Create integration tests**
6. **Implement frontend components**
7. **Add i18n strings**
8. **Run full test suite**
9. **User acceptance testing**

---

## Questions or Issues

For questions about the dual-category model or implementation:
- See `specs/requirements/R08_taxonomy.md`
- See `specs/specifications/S54_secondary_topic.md`
- See `P11_IMPLEMENTATION_SUMMARY.md` for detailed implementation notes

---

**Estimated Time to Complete**: 6-9 hours remaining (backend services + frontend + testing)
