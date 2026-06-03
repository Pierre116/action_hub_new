# ActionHub — Action Lead Model

> Status: Requirements-level specification
> Depends on: R01_entities.md, R02_action_lifecycle.md, R19_meeting_series_workspace.md
> Consumed by: S05_data_dictionary.md, S16_API_Contract.md

---

## 1. Overview

Terminology used in this specification:

- **Created by** = `act_created_by` (audit/source of record).
- **Lead** = `act_owner_id` (single accountable person; owner in database field naming).

ActionHub uses a single-Lead model for actions.

- Every action has exactly one Lead.
- For non-meeting actions, Lead is the creator.
- For meeting actions, action is created by the meeting creator and Lead must be selected from occurrence participants.
- Legacy multi-role assignment labels are not used for action accountability.

---

## 2. Lead Rules

| Rule | Requirement |
|------|-------------|
| Lead cardinality | Exactly 1 Lead per action |
| Non-meeting create | Creator becomes Lead automatically |
| Meeting create | Only meeting creator (or Admin) can create action |
| Meeting Lead eligibility | Lead must be a participant of the current occurrence |
| Meeting participant removed later | Action remains valid; removed user loses meeting-content access per visibility policy |

---

## 3. Write Permissions

| Context | Who can edit action fields | Who can add feedback/comments |
|---------|----------------------------|-------------------------------|
| Non-meeting action | Lead (or Admin) | Lead (or Admin) |
| Meeting action | Lead, meeting creator, or Admin | Lead, meeting creator, or Admin |

---

## 4. Visibility Relationship

Ownership is independent from visibility checks.

A user can view an action when at least one of these is true:

- the user is the action Lead
- the user is explicitly assigned in assignment records where applicable
- the user is a participant of the linked meeting occurrence (for meeting actions)
- the user is within team-leader scoped visibility rules

Private meeting/action masking and detailed access follow R19 and R20.

---

## 5. Audit Expectations

Action Lead changes (when allowed by product policy) must be audit logged in action history.

Minimum audit fields:

- action_id
- old_lead_id (stored in `act_owner_id` history fields)
- new_lead_id (stored in `act_owner_id` history fields)
- changed_by
- changed_at
- reason (optional)

---

## 6. Compatibility Note

Legacy records may still contain historical role values in assignment tables. Active runtime policy and all new records use Lead-based accountability semantics for action control.
