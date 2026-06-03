# ActionHub — Meeting Participants & In-App Notifications

> **Status**: Requirements-level specification  
> **Version**: v3.0  
> **Date**: March 2026  
> **Depends on**: `R04_notifications.md`, `R01_entities.md`

---

## §1 Overview

Meeting participants and in-app notifications deliver lightweight follow-up
without requiring email infrastructure. Meeting owners can maintain a roster of
participants per meeting, then push one-click notifications when memos are
published. A global notification bell in the navbar provides real-time-ish
awareness via 30-second polling.

---

## §2 Meeting Participants

### §2.1 Data Model

| Column | Type | Description |
|--------|------|-------------|
| `mpa_id` | INTEGER PK | Auto-increment ID |
| `mpa_instance_id` | FK → t_meeting_instance | Meeting this participant belongs to |
| `mpa_user_id` | FK → t_user | The participating user |
| `mpa_added_by` | FK → t_user | Who added this participant |
| `mpa_added_at` | TEXT | Timestamp (DEFAULT CURRENT_TIMESTAMP) |

**Constraint**: UNIQUE(mpa_instance_id, mpa_user_id)

### §2.2 Functional Requirements

| ID | Requirement |
|----|-------------|
| REQ-MPA-01 | Admin or meeting owner can add/remove participants |
| REQ-MPA-02 | Participant list shown in Meeting Info card |
| REQ-MPA-03 | "✏ Manage" button opens modal for add/remove |
| REQ-MPA-04 | Participant count badge shown in Meeting Info |
| REQ-MPA-05 | Participants are target recipients for memo notifications |

### §2.3 API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/meetings/<id>/participants` | List participants | Login |
| PUT | `/api/meetings/<id>/participants` | Replace participant list | Owner/Admin |
| POST | `/api/meetings/<id>/participants` | Add a participant | Owner/Admin |
| DELETE | `/api/meetings/<id>/participants/<uid>` | Remove a participant | Owner/Admin |
| POST | `/api/meetings/<id>/notify-memos` | Send memo notification to all participants | Owner/Admin |

---

## §3 In-App Notifications

### §3.1 Data Model

| Column | Type | Description |
|--------|------|-------------|
| `ntf_id` | INTEGER PK | Auto-increment ID |
| `ntf_user_id` | FK → t_user | Recipient |
| `ntf_event_type` | TEXT | `assigned`, `deadline_soon`, `meeting_memos` |
| `ntf_title` | TEXT | Short notification title |
| `ntf_body` | TEXT | Optional detail text |
| `ntf_action_id` | FK → t_action | Optional link to action |
| `ntf_is_read` | INTEGER | 0 = unread, 1 = read |
| `ntf_created_at` | TEXT | Timestamp |

### §3.2 Functional Requirements

| ID | Requirement |
|----|-------------|
| REQ-NTF-01 | Navbar bell icon shows unread count (red pill badge) |
| REQ-NTF-02 | Clicking bell opens dropdown panel of latest notifications |
| REQ-NTF-03 | Browser polls `/api/notifications` every 30 seconds |
| REQ-NTF-04 | Users can mark individual or all notifications as read |
| REQ-NTF-05 | Auto-generated on: action assignment, deadline ≤ 3 days |
| REQ-NTF-06 | Meeting memo notifications sent to all participants (excl. sender) |

### §3.3 API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/notifications` | List notifications (`?unread=true`) | Login |
| POST | `/api/notifications/<id>/read` | Mark one read | Login |
| POST | `/api/notifications/read-all` | Mark all read | Login |

### §3.4 Notification Body Format

**Meeting memos notification:**
```
Title: "Meeting memos: {meeting_title}"
Body:  "Shared by {actor_name}\nMemos: {memo1_title}, {memo2_title}, ... +N more"
```

**Assignment notification:**
```
Title: "You were assigned to: {action_title}"
Body:  "Assigned by {actor_name}"
```

**Deadline notification:**
```
Title: "Due soon: {action_title}"
Body:  "Deadline: {deadline_date}"
```

---

## §4 UI Design Notes

### §4.1 Bell Icon
- Positioned in navbar, between language switcher and user menu
- Red pill badge with count (hidden when 0)
- Dropdown panel: max 320×320 px, scrollable
- Each item: title, body (11px), timestamp (10px)
- Unread items have light blue background
- Click item → mark read + navigate to linked action (if any)

### §4.2 Participants in Meeting Detail
- Shown in Meeting Info card as "Participants" row
- "✏ Manage" link (visible to owners/admin only) opens modal
- Modal has: dropdown to add user + list of current participants with Remove buttons
- "🔔 Notify Participants" button in Memos tab card header

---

## §5 Future Roadmap (Not in v3.0)

| Feature | Status | Notes |
|---------|--------|-------|
| Email notifications (SMTP) | Deferred | Requires IT to configure Exchange relay or IIS SMTP |
| Server-Sent Events (SSE) | Planned v3.1 | Replace polling with push for instant delivery |
| Notification preferences | Planned v3.2 | Per-user opt-in/out for event types |
| Daily digest email | Planned v3.2 | Summary of unread notifications |
