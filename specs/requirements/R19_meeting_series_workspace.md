# ActionHub — Meeting Series Workspace

> **Status**: 🚧 In Progress  
> **Depends on**: R15 (participants & notifications), R17 (meeting decisions), R01 (entities)  
> **Consumed by**: S05, S16, S25, S80 updates  
> **Version target**: V3.14 (P12)

---

## §1 Objectives

| # | Objective |
|---|-----------|
| MS1 | Promote the meeting **series** as the primary organizational unit for recurring meetings |
| MS2 | Maintain a **default participant list** on the series template that auto-populates new occurrences |
| MS3 | Make each **occurrence a workspace** showing memo, participants, and all series actions/decisions |
| MS4 | Link **action comments to the occurrence** where they were discussed, enabling per-meeting context |
| MS5 | Auto-generate **Minutes of Meeting (MoM) PDF** from occurrence data for distribution |

---

## §2 Meeting Series (Parent Meeting)

### §2.1 Existing Model

The `t_meeting` table already serves as a series parent, with `t_meeting_instance` records linked via `min_meeting_id`. This relationship is fully functional in the backend but has **no frontend exposure**.

### §2.2 Series Default Participants

Each series has a template participant list. When a new occurrence is created, these participants are automatically copied to the occurrence.

| Field | Description | Required |
|-------|-------------|----------|
| Series ID | FK → `t_meeting.mtg_id` | Yes |
| User ID | FK → `t_user.usr_id` | Yes |
| Kind | `Compulsory` or `Optional` | Yes (default: `Compulsory`) |
| Added By | FK → `t_user.usr_id` — who added | Yes |
| Added At | Timestamp | Auto |

**Business rules:**
- Series creator is auto-added as a Compulsory participant.
- Admins and series creator can add/remove default participants.
- Changing the default list does **not** retroactively change existing occurrences.

### §2.3 Series Management UI

| Requirement ID | Description |
|----------------|-------------|
| REQ-MS-01 | Meeting Series list page showing all series with occurrence count, last occurrence date, and default participant count |
| REQ-MS-02 | Series detail page with default participant management (add/remove, kind toggle) |
| REQ-MS-03 | "New Occurrence" button on series detail page that pre-populates participants from the series default list |
| REQ-MS-03a | Occurrence title is auto-generated from the series title plus occurrence date; users only provide the date unless an admin override is added later |
| REQ-MS-03b | New occurrence date defaults to the current day in the UI |
| REQ-MS-04 | Existing standalone meetings (those without `min_meeting_id`) continue to work as before |

---

## §3 Occurrence Workspace

### §3.1 Overview

Each occurrence is a workspace where the meeting actually happens. It shows:

1. **Memo** — the `min_notes` field (rich text area)
2. **Participants** — copied from series defaults, editable per-occurrence
3. **Actions from the series** — all non-archived actions across all occurrences of the parent series
4. **Decisions from the series** — all decisions across all occurrences of the parent series
5. **Comments** — per-action comments grouped by occurrence (previous meeting vs. current)

The occurrence workspace is the primary follow-up surface for a recurring meeting series. A user entering the current occurrence should not need to open the previous occurrence just to understand ongoing work. The workspace must therefore show:

- all series actions with their **current live status**
- all series decisions with their **current live status**
- the **previous occurrence comment context** for each discussed action when available

### §3.2 Action Display in Occurrence

| Requirement ID | Description |
|----------------|-------------|
| REQ-MS-10 | Show all non-archived actions where `act_meeting_inst_id` belongs to any occurrence of the series |
| REQ-MS-11 | Actions are grouped: Open/In Progress first, then recently completed, Done/Cancelled collapsed |
| REQ-MS-12 | Each action shows which occurrence it was created in (date badge) |
| REQ-MS-13 | Each action row shows the action's **current live status** so follow-up can happen from the current occurrence without opening the previous one |
| REQ-MS-14 | "Create Action" button links the new action to the current occurrence (`act_meeting_inst_id`) |
| REQ-MS-15 | When an action has comments from the immediately previous occurrence, the current occurrence workspace shows that previous-occurrence comment context inline |

### §3.3 Decision Display in Occurrence

| Requirement ID | Description |
|----------------|-------------|
| REQ-MS-20 | Show all decisions where `mdc_instance_id` belongs to any occurrence of the series |
| REQ-MS-21 | Decisions display title, **current live status**, category, and which occurrence they were created in |
| REQ-MS-22 | "Create Decision" button links the new decision to the current occurrence |
| REQ-MS-23 | Users can mark decisions as Obsolete from the occurrence workspace |

### §3.4 Comment Display in Occurrence

| Requirement ID | Description |
|----------------|-------------|
| REQ-MS-30 | Action comments are tagged with the occurrence they were made in (`cmt_meeting_inst_id`) |
| REQ-MS-31 | In the occurrence workspace, each action shows: (a) comments from the previous occurrence (read-only), (b) comments from the current occurrence (editable) |
| REQ-MS-32 | When viewing an action outside the meeting context (action detail page), all comments show chronologically with occurrence badges |
| REQ-MS-33 | "Add Comment" button in the occurrence workspace auto-sets `cmt_meeting_inst_id` to the current occurrence |

**Clarification:** Comments are the per-occurrence follow-up record. Actions and decisions themselves remain single entities linked to one source occurrence, but the occurrence workspace must surface the latest series-wide state plus the previous occurrence's follow-up comment context.

---

## §4 Minutes of Meeting (MoM) PDF

### §4.1 Content

The MoM PDF is auto-generated from the occurrence data:

| Section | Content |
|---------|---------|
| Header | Series title, occurrence date, generated timestamp |
| Participants | List of all participants for this occurrence |
| Memo | The `min_notes` field content |
| Actions Reviewed | All series actions that were updated/commented during this occurrence |
| New Actions | Actions created in this occurrence |
| Decisions | All decisions created or updated in this occurrence |

### §4.2 Functional Requirements

| Requirement ID | Description |
|----------------|-------------|
| REQ-MS-40 | "Generate Minutes" button on the occurrence workspace |
| REQ-MS-41 | PDF includes header, participant list, memo, actions reviewed, new actions, and decisions |
| REQ-MS-42 | PDF is generated server-side using reportlab (no external system dependencies) |
| REQ-MS-43 | PDF is returned as a download (Content-Disposition: attachment) |
| REQ-MS-44 | PDF can optionally be stored as a meeting summary (blob in `t_meeting_summary`) |

---

## §5 Permissions

| Operation | Who |
|-----------|-----|
| View series list | Any authenticated user (public series) or series participants only (private series) |
| Create series | Admin |
| Manage series default participants | Admin or series creator |
| Create occurrence from series | Admin or series creator |
| Edit occurrence (memo, participants) | Meeting creator only |
| Create action from occurrence | Meeting creator only |
| Edit action from occurrence | Meeting creator only |
| Create decision from occurrence | Meeting creator only |
| Edit decision from occurrence | Meeting creator only |
| Add comment (feedback) in occurrence | Any occurrence participant |
| Generate MoM PDF | Any occurrence participant |

---

## §9 Meeting Visibility (Public / Private)

### §9.1 Meeting Visibility Flag

Each meeting series and occurrence has a visibility flag:

| Value | Default | Description |
|-------|---------|-------------|
| `public` | ✅ Yes | Meeting info, actions, and decisions visible to all authenticated users |
| `private` | | Meeting info and actions visible only to meeting participants |

**Business rules:**
- Visibility is set at series level and inherited by new occurrences (can be overridden per-occurrence).
- Meeting creator sets visibility when creating the series.

### §9.2 Private Meeting Access Control

| Data | Who can see | Notes |
|------|-------------|-------|
| Meeting detail (memo, participants, occurrence list) | Meeting participants + creator only | Team leaders CANNOT see private meetings of their members |
| Actions from private meeting | Action creator + Lead only | Team leaders CANNOT see private actions of their team members |
| Decisions from private meeting | **All authenticated users** | Decisions are always public for knowledge base purposes |
| Decision → meeting title | Visible | The meeting title IS disclosed on the decision |
| Decision → meeting participants | **Not disclosed** | Participant list is never exposed via decision queries |


### §9.3 Public Meeting / Non-Meeting Action Access

| Data | Who can see |
|------|-------------|
| Public meeting detail | All authenticated users |
| Actions from public meeting | Action creator, assignees, team members of creator/lead/assignee, and any meeting participant |
| Actions from private meeting | Action creator, assignees, and any meeting participant |
| Non-meeting actions | Creator, assigned participants, and team members of creator/lead/assignee |

---

## §10 Action Assignment Roles in Meeting Context

### §10.1 Role Definitions

Terminology:

- **Created by** = action audit/source user (`act_created_by`).
- **Lead** = accountable action role (`act_owner_id`).

| Role | Cardinality | Required | Description |
|------|-------------|----------|-------------|
| **Lead** | Exactly 1 | Yes | Accountable action role. Creates, validates, closes. Lead maps to `act_owner_id`. |

### §10.2 Assignment Pool Rules

| Context | Pool for Lead |
|---------|---------------|
| **Action from meeting** | Meeting occurrence participants only |
| **Action outside meeting** | Creator only (auto-assigned) |

### §10.3 Write Permissions

| Context | Who can edit action (title, status, deadline, priority) | Who can add comments/feedback |
|---------|--------------------------------------------------------|-------------------------------|
| **Meeting action** | Action Lead or meeting creator | Action Lead or meeting creator |
| **Non-meeting action** | Action Lead only | Action Lead only |

Progress feedback behavior:

- Feedback entries are append-only and timestamped.
- Timestamp is shown in UI as locale date+time (latest update and history entries).
- If a new feedback entry is saved with empty blockers, the previous non-empty blockers value is carried forward.

### §10.4 Key Invariants

- For meeting actions, the default Lead must be a current occurrence participant. If the creator is a participant, they are the default Lead; otherwise the user must choose a participant or the system falls back to the first valid participant.
- Non-meeting actions: creator is Lead, no adding other people later.
- Meeting actions: Lead must be a current occurrence participant. If a participant is removed from the meeting, their action assignment remains (no cascading delete) but they lose meeting access.

---

## §6 Schema Changes Summary

| Change | Type | Detail |
|--------|------|--------|
| `t_meeting_series_participant` | New table | Default participant list for the series template |
| `cmt_meeting_inst_id` | New column on `t_comment` | Nullable FK → `t_meeting_instance.min_id` — links comment to occurrence |
| `mtg_visibility` | New column on `t_meeting` | `TEXT NOT NULL DEFAULT 'public' CHECK (mtg_visibility IN ('public','private'))` |
| `min_visibility` | New column on `t_meeting_instance` | `TEXT NOT NULL DEFAULT 'public' CHECK (min_visibility IN ('public','private'))` — inherited from series, overridable |
| `act_visibility` | New column on `t_action` | `TEXT NOT NULL DEFAULT 'public' CHECK (act_visibility IN ('public','private'))` — inherited from meeting if linked |

**Existing columns reused** — `act_meeting_inst_id`, `mdc_instance_id`, `min_notes`, `t_meeting_participant`, `t_meeting` (series parent), `asg_role` (updated values).

---

## §7 API Endpoints (New / Modified)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/meetings/series` | List all series with metadata |
| POST | `/api/meetings/series` | Create a new series |
| GET | `/api/meetings/series/:id` | Get series detail with default participants |
| PUT | `/api/meetings/series/:id` | Update series title/description |
| GET | `/api/meetings/series/:id/participants` | List default participants |
| PUT | `/api/meetings/series/:id/participants` | Replace default participant list |
| POST | `/api/meetings/series/:id/participants` | Add a default participant |
| DELETE | `/api/meetings/series/:id/participants/:uid` | Remove a default participant |
| POST | `/api/meetings/series/:id/occurrences` | Create occurrence with auto-copied participants |
| GET | `/api/meetings/series/:id/actions` | All actions across series occurrences |
| GET | `/api/meetings/series/:id/decisions` | All decisions across series occurrences |
| GET | `/api/meetings/:min_id/occurrence-comments` | Comments on series actions grouped by occurrence |
| GET | `/api/meetings/:min_id/minutes/pdf` | Generate MoM PDF for the occurrence |

---

## §8 UI Pages

| Page | Route | Description |
|------|-------|-------------|
| Meeting Series List | `/meetings/series` | Series list with occurrence count and last date |
| Series Detail | `/meetings/series/:id` | Default participants, occurrence list, create occurrence |
| Occurrence Workspace | `/meetings/:id` | Memo, participants, actions, decisions, comments, generate MoM |
