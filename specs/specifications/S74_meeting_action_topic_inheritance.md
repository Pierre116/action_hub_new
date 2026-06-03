# S74 — Meeting Action Category Inheritance

> **Status**: ✅ Current  
> **Date**: 2026-03-19  
> **Version**: 1.1  
> **Depends on**: S05 (Data Dictionary), S16 (API Contract), S25 (UI Specs), S80 (React Architecture)  
> **Related**: R15 (Participants & Notifications)

---

## 1. Overview

### 1.1 Problem Statement

When creating an action from within a meeting or occurrence workspace, the action inherits the meeting’s attached Categories and the frontend pre-populates the relevant selectors.

- **Backend**: The create-action flow can derive the primary category from `min_topic_id`, but the dual-category rule is not documented consistently.
- **Frontend**: Category selectors are pre-populated from the meeting context so users can confirm or override the values before saving.

This removes the earlier gap where the backend derived values but the user could not see them clearly during creation.

### 1.2 Desired Outcome

1. When a user clicks "Add Action" from a meeting, the Category selectors are pre-populated with the meeting’s attached Categories.
2. The user can still override either category before submitting.
3. The behavior is clearly documented in the API contract.

### 1.3 Scope

| In Scope | Out of Scope |
|----------|--------------|
| Frontend pre-population of categories from meeting | Changes to meeting creation |
| API documentation update | Changes to category cardinality beyond max 2 |
| User override capability | Any secondary taxonomy beyond Category |

---

## 2. Current Implementation (Backend)

### 2.1 Existing Logic

The backend already implements topic derivation in `actionhub/actions/service.py`:

```python
def create_action(payload: dict, actor_user_id: int) -> dict:
    # ...
    # Derive topic from meeting if not explicitly set
    topic_id = data.get("topic_id")
    meeting_id = data.get("meeting_id")
    if not topic_id and meeting_id:
        m_row = db.execute(
            "SELECT min_topic_id FROM t_meeting_instance WHERE min_id = ?", (meeting_id,)
        ).fetchone()
        if m_row:
            topic_id = m_row["min_topic_id"]

    if not topic_id:
        raise ValueError("topic_id is required — every action must belong to a topic")
```

### 2.2 Behavior Matrix

| `topic_id` provided | `meeting_id` provided | Result |
|---------------------|----------------------|--------|
| Yes | No | Use provided `topic_id` |
| Yes | Yes | Use provided `topic_id` (user override) |
| No | No | Error: topic required |
| No | Yes | Derive from `min_topic_id` |

---

## 3. Specification

### 3.1 Frontend Changes (S80)

#### 3.1.1 ActionDetail.tsx — Pre-populate Categories

**File**: `frontend/src/pages/actions/ActionDetail.tsx`

**Current behavior**:
- Form initializes with empty category selectors.
- When `meeting_id` is in URL, only `meeting_id` is set in form data.

**New behavior**:
- When `meeting_id` is in URL (new action from meeting), fetch the meeting's `min_topic_id` and `min_secondary_topic_id`.
- Pre-populate `formData.category_ids` with the meeting’s categories.

**Implementation**:

```tsx
// Add query to fetch meeting details when creating new action from meeting
const { data: meetingForNewAction } = useQuery({
  queryKey: ['meeting-for-new-action', meetingIdParam],
  queryFn: async () => {
    if (!meetingIdParam) return null
    const response = await api.get(`/api/meetings/${meetingIdParam}`)
    return response.data.data as { min_topic_id: number; topic_name: string }
  },
  enabled: isNewAction && !!meetingIdParam,
})

// Update form initialization effect
useEffect(() => {
  if (isNewAction && meetingForNewAction) {
    setFormData(prev => ({
      ...prev,
      topic_id: meetingForNewAction.min_topic_id ? String(meetingForNewAction.min_topic_id) : prev.topic_id,
    }))
  }
}, [isNewAction, meetingForNewAction])
```

#### 3.1.2 Visual Indicator

Display a subtle indicator when categories are inherited from a meeting:

```tsx
{meetingIdParam && formData.category_ids?.length > 0 && (
  <Form.Text className="text-muted">
    {t('actions.categories_from_meeting', 'Categories inherited from meeting')}
  </Form.Text>
)}
```

### 3.2 API Contract Update (S16)

#### 3.2.1 POST /api/actions

Update the request schema documentation:

**Current**:
```
category_ids: "[int] (optional)"
meeting_id: "int (optional)"
```

**Updated**:
```
category_ids: "[int] (optional) — required unless meeting_id is provided, in which case it defaults to the meeting's attached categories (max 2)"
meeting_id: "int (optional) — when provided, category_ids default to the meeting's attached categories"
```

**Response enhancement** (optional):
When an action is created with `meeting_id` and derived `category_ids`, return the derived values:

```json
{
  "id": 43,
  "ref": "ACT-2026-00043",
  "category_ids": [5, 8],
  "categories_derived_from_meeting": true,
  "message": "Action created"
}
```

### 3.3 i18n Strings

Add to `actionhub/i18n/en.json`:
```json
{
  "actions": {
    "categories_from_meeting": "Categories inherited from meeting"
  }
}
```

Add to `actionhub/i18n/zh.json`:
```json
{
  "actions": {
    "categories_from_meeting": "类别继承自会议"
  }
}
```

---

## 4. Data Model

No schema changes required. The existing columns are sufficient:

| Table | Column | Usage |
|-------|--------|-------|
| `t_meeting_instance` | `min_topic_id`, `min_secondary_topic_id` | Meeting's attached categories |
| `t_action` | `act_topic_id`, `act_secondary_topic_id` | Action's attached categories |
| `t_action` | `act_meeting_inst_id` | Reference to source meeting |

---

## 5. Test Plan

### 5.1 Backend Tests

| Test | Description | Expected Result |
|------|-------------|-----------------|
| `test_create_action_with_meeting_derives_categories` | POST `/api/actions` with `meeting_id` but no `category_ids` | Action created with meeting categories |
| `test_create_action_with_meeting_category_override` | POST `/api/actions` with both `meeting_id` and `category_ids` | Action uses provided categories |
| `test_create_action_without_meeting_or_category` | POST `/api/actions` without `meeting_id` or `category_ids` | Returns 400 error |
| `test_create_action_with_invalid_meeting_id` | POST `/api/actions` with non-existent `meeting_id` | Returns 400 error |

### 5.2 Frontend Tests

| Test | Description | Expected Result |
|------|-------------|-----------------|
| `ActionForm_meeting_categories_prepopulated` | Navigate to `/actions/new?meeting_id=1` | Category selectors show meeting categories pre-selected |
| `ActionForm_meeting_category_override` | User changes categories, then submits | Action uses user-selected categories |
| `ActionForm_meeting_category_clearable` | User clears categories | Validation error on submit (primary category required) |

### 5.3 Integration Tests

| Test | Description | Expected Result |
|------|-------------|-----------------|
| `MeetingDetail_to_ActionCreate_flow` | Click "Add Action" from meeting, verify form, submit | Action created with correct categories, linked to meeting |

---

## 6. Migration Plan

### 6.1 Implementation Order

1. **Frontend change** (ActionDetail.tsx) — pre-populate categories from meeting
2. **i18n strings** — add new translation keys
3. **API documentation** — update S16 with inheritance behavior
4. **Tests** — add backend and frontend tests

### 6.2 Rollback

No database changes, so rollback is simple:
- Revert frontend change
- Remove i18n strings

### 6.3 Compatibility

- Backward compatible — existing API calls without `meeting_id` work unchanged
- Frontend enhancement is purely additive (pre-population)

---

## 7. Future Considerations

### 7.1 Team Inheritance

Meetings are already associated with a team (via `min_topic_id` → topic assignments). Future enhancement could derive `team_id` from the meeting's topic.

---

## 8. Glossary

| Term | Definition |
|------|------------|
| Category | Primary strategic classification for actions and meetings (stored in `t_topic`, UI label `类别`) |
| Meeting Instance | A specific occurrence of a meeting (stored in `t_meeting_instance`) |
| Category Inheritance | Automatic derivation of `act_topic_id` / `act_secondary_topic_id` from meeting categories when creating an action from a meeting |
