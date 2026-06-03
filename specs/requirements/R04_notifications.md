# ActionHub — Notifications & Follow-Up

> **Status**: Requirements-level specification  
> **Depends on**: `R02_action_lifecycle.md` (triggers), `R03_assignment_workflow.md` (assignment events)  
> **Decisions**: D51–D60 in `DECISIONS.md`  
> **Consumed by**: SpecForge for `15_MOT.md`, `30_physical_specs.md`

---

## §1 Overview

ActionHub sends automated notifications for action lifecycle events. This document defines all notification triggers, templates, scheduling, and delivery rules.

### MVP (1.5-day) Scope

| Feature | MVP | V1.1 | V1.2 |
|---------|:---:|:----:|:----:|
| Dashboard visual indicators (overdue = red, due soon = amber) | ✅ | | |
| Personal dashboard "Overdue" / "Due This Week" sections | ✅ | | |
| In-app notification bell + unread count | | ✅ | |
| Email notifications (SMTP) | | ✅ | |
| Notification preferences per user | | ✅ | |
| Daily digest | | | ✅ |
| Quiet hours + de-duplication | | | ✅ |
| Notification log with retry | | ✅ | |

> **MVP approach**: Instead of building a notification engine, the MVP uses **passive visual indicators**: overdue actions glow red on the personal dashboard, due-this-week items appear in amber. This delivers 80% of the follow-up value ("what’s overdue?") with zero infrastructure (no SMTP, no cron). Email notifications are the #1 V1.1 priority.

**V1.1**: Full email notifications (assignment + deadline + overdue) + in-app badge count.  
**V1.2**: Configurable preferences, quiet hours, daily digest, notification log with retry logic.

---

## §2 Notification Channels

| Channel | Description | V1 | V2+ |
|---------|-------------|-----|------|
| **Email** | SMTP-based email to user's AD email address | Yes | Yes |
| **In-App Badge** | Dashboard badge count + notification panel | Yes | Yes |
| **WeChat** | WeChat Work integration | No | Possible |
| **SMS** | SMS gateway | No | Possible |

---

## §3 Notification Triggers

### §3.1 Action Lifecycle Notifications

| Event | Recipients | Email? | In-App? |
|-------|-----------|--------|---------|
| Action created | All assignees (Lead, Delegates, Participants) | Yes | Yes |
| Status changed | All assignees | Yes | Yes |
| Priority changed | All assignees | Yes | Yes |
| Escalation level changed | All assignees + team head | Yes | Yes |
| Action cancelled | All assignees | Yes | Yes |
| Action completed (Done) | All assignees + creator | Yes | Yes |
| Comment added | All assignees (except commenter) | Configurable (D51) | Yes |
| Attachment added | All assignees | No | Yes |

### §3.2 Assignment Notifications

| Event | Recipients | Email? | In-App? |
|-------|-----------|--------|---------|
| New assignment | Assignee | Yes | Yes |
| Assignment accepted | Lead + creator | No | Yes |
| Assignment declined | Lead + creator | Yes | Yes |
| Reassignment (old) | Previous assignee | Yes | Yes |
| Reassignment (new) | New assignee | Yes | Yes |
| No response (24h) | Assignee (reminder) | Yes | Yes |
| No response (48h) | Lead (escalation) | Yes | Yes |

### §3.3 Deadline Notifications (D52)

| Trigger | Timing | Recipients |
|---------|--------|-----------|
| Approaching deadline | 3 business days before deadline | Lead + all Delegates |
| Deadline today | On the deadline date, morning (D53) | Lead + all Delegates |
| Overdue (daily) | Every business day while overdue | Lead + all Delegates |
| Overdue escalation | After auto-escalation trigger | Lead + team head |

### §3.4 Dependency Notifications

| Event | Recipients |
|-------|-----------|
| Blocking action completed | All assignees of the unblocked action |
| New dependency created | Lead of the dependent action |

---

## §4 Notification Scheduling

### §4.1 Daily Digest vs. Instant (D54)

| Notification Type | Delivery Mode |
|-------------------|---------------|
| Assignment events | Instant |
| Status changes | Instant |
| Deadline reminders | Daily batch (morning, 08:00) |
| Overdue reminders | Daily batch (morning, 08:00) |
| Comments | Configurable per-user: Instant or Daily digest |

### §4.2 Quiet Hours (D55)

- No emails sent outside business hours (08:00–18:00 local time)
- Queued notifications delivered at next business morning
- Weekend notifications queued to Monday morning

### §4.3 De-duplication

- If multiple status changes happen to the same action within 1 hour, only the final state is emailed
- In-app badge shows latest state immediately

---

## §5 Email Templates

### §5.1 Template Structure (D56)

All emails follow a consistent bilingual structure:

```
Subject: [ActionHub] {event_type_en} — {action_reference} / {event_type_cn}

Body:
─────────────────────────────────
ActionHub Notification / 行动中心通知
─────────────────────────────────

Action: {reference_code} — {title}
行动项: {reference_code} — {title}

Event: {event description}
事件: {event description CN}

Details:
  Status: {old_status} → {new_status}
  Priority: {priority}
  Deadline: {deadline}
  Team: {team}
  Lead: {lead_name}

{action_link}

─────────────────────────────────
This is an automated message from ActionHub.
此邮件由行动中心自动发送。
```

### §5.2 Email Templates by Event

| Template | Subject Line |
|----------|-------------|
| New assignment | `[ActionHub] New Assignment — ACT-2026-00142` |
| Deadline reminder | `[ActionHub] ⚠ Deadline in 3 days — ACT-2026-00142` |
| Overdue alert | `[ActionHub] 🔴 OVERDUE — ACT-2026-00142` |
| Assignment declined | `[ActionHub] Assignment Declined — ACT-2026-00142` |
| Status change | `[ActionHub] Status → In Progress — ACT-2026-00142` |
| Escalation | `[ActionHub] 🔺 Escalated — ACT-2026-00142` |
| Weekly summary | `[ActionHub] Weekly Summary — {user_name} — W{week_number}` |

---

## §6 In-App Notification Panel

### §6.1 UI Behavior

- Bell icon in top navigation bar with unread count badge
- Click → dropdown panel showing latest 20 notifications
- Each notification: icon + title + timestamp + "Mark as read"
- "View all" link → full notification history page
- Notifications auto-mark as read when user opens the related action

### §6.2 Notification Preferences (D57)

Each user can configure via Settings:

| Setting | Options | Default |
|---------|---------|---------|
| Email for comments | On / Off | Off |
| Email language | English / Chinese / Both | Based on `preferred_language` |
| Daily digest time | 08:00–10:00 range | 08:00 |
| Browser push notifications | On / Off | Off (V2+) |

---

## §7 Notification Log (D58)

Every notification (email + in-app) is logged:

| Field | Type |
|-------|------|
| id | INT (PK) |
| user_id | FK → User |
| action_id | FK → Action |
| notification_type | ENUM (email / in_app) |
| event_type | ENUM (list from §3) |
| subject | VARCHAR(255) |
| body_preview | VARCHAR(500) |
| sent_date | DATETIME |
| read_date | DATETIME (nullable) |
| delivery_status | ENUM (queued / sent / failed / read) |
| retry_count | INT |

### §7.1 Retry Logic (D59)

- Failed email: retry 3 times with exponential backoff (5min, 30min, 2h)
- After 3 failures: mark as failed, log error, continue (no blocking)

### §7.2 Notification Purge (D60)

- Read notifications: purge after 90 days
- Unread notifications: keep indefinitely (or until read)
- Notification log (for audit): keep 1 year
