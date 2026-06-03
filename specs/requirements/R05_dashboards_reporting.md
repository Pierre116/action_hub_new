# ActionHub — Dashboards & Reporting

> **Status**: Requirements-level specification  
> **Depends on**: `R01_entities.md` (data model), `R02_action_lifecycle.md` (statuses), `R03_assignment_workflow.md` (roles)  
> **Decisions**: D61–D75 in `DECISIONS.md`  
> **Consumed by**: SpecForge for `25_UI_Specs.md`, `16_API_Contract.md`

---

## §1 Overview

ActionHub provides dashboard views and a reporting engine with custom Excel exports.

### MVP (1.5-day) Scope

| Feature | MVP | V1.1 | V1.2 |
|---------|:---:|:----:|:----:|
| Personal Dashboard (“Today” focus) | ✅ | | |
| Team Dashboard (KPI cards + overdue table) | ✅ | | || Team Manager Workload View (cards per employee) | ✅ | | |
| Category Dashboard (K50–K54 KPIs) | ✅ | | |
| Gantt Timeline | ✅ | Filter polish | |
| Admin Inline Actions Table (all 6 fields, 25/page) | ✅ | | |
| In-app Notification Bell (badge + event log) | ✅ | | || Excel export from filtered views | ✅ | | |
| Team Dashboard | | ✅ | |
| Management Dashboard | | ✅ | |
| Report builder (custom columns/filters) | | | ✅ |
| Scheduled reports + auto-email | | | ✅ |
| Trend charts (line/area) | | ✅ | |
| Team comparison heatmap | | | ✅ |

> **MVP design principle**: Two dashboards that answer the two most important questions: "What should **I** do today?" (Personal) and "How is **my team** doing?" (Team). Charts are deferred; KPI cards + color-coded tables deliver the insight.

---

## §2 Dashboard Hierarchy

```
Management Dashboard (plant-wide view)        ← V1.1
 └── Team Dashboard (per team)    ← MVP
      └── Team Dashboard (per team)           ← V1.1
           └── Personal Dashboard (per user)  ← MVP (landing page)
```

Dashboards are available to authenticated users, but data visibility is scope-governed (personal self-scope, team-lead scope, and meeting/action scoped visibility per R19/R20). The default landing page is the user's Personal Dashboard (D61). **MVP ships with Personal + Team only** (D153).

---


## §3 Personal Dashboard

> **This is the MVP landing page** — Every user sees this on login (D61). It must load in <2s and answer "what do I need to do?" at a glance.

### §3.0a Action Visibility Rules

The Personal Dashboard and Action List show only:
1. Actions created by, owned by, or assigned to the current user
2. Actions of the user's team members, but only from non-private meetings
3. Actions from meetings (public or private) where the user is a participant

This ensures users see only their own work, their team's public work, and actions from meetings they participate in.

### §3.0b Employee Switcher

Admin and TeamLead users see a **user dropdown** at the top of the Personal Dashboard that allows viewing any employee's data in read-only mode. The URL becomes `/dashboard/personal?user_id=<id>` when viewing another user. Regular Members see only their own data (no switcher rendered).

### §3.1 Tabs

The Personal Dashboard renders four tabs. The active tab is preserved in the URL hash.

| Tab | Description |
|-----|-------------|
| **Overview** | KPI cards (actions + decisions) + Overdue + Due Soon + Recently Completed (last 30 days) + Recent Decisions (last 30 days) |
| **By Deadline** | all personal actions sorted by deadline ascending |
| **By Category** | actions grouped by category with per-group KPI row |
| **Gantt** | Horizontal bar chart per action; x-axis = date; bars colored by status; grouped by category; today line marker |

### §3.2 Layout — Overview tab

| Section | Content | UX Notes |
|---------|---------|----------|
| **Action KPI Cards** | Total / Open / Overdue (red) / Due in 7 days (amber) | 4 cards horizontal |
| **Decision KPI Cards** | Published Decisions / Expired Decisions (last 30 days) | 2 cards horizontal |
| **🔴 Overdue Actions** | Table sorted oldest-first: Ref, Title, Priority, Deadline | Top 10 |
| **⚠️ Due Soon** | Table sorted by deadline: Ref, Title, Status, Deadline | Within 7 days |
| **✅ Recently Completed** | Table of Done actions: Title, Category, Deadline | Last 30 days |
| **📌 Recent Decisions** | Table: Title, Content, Category, Owner, Meeting Series ID, Date | Last 30 days, Personal dash only |

### §3.3 Layout — By Deadline tab

> **Note**: This tab shows action-focused information only. Recently Completed and Recent Decisions sections are **not** displayed here (Overview only).

Flat list of all personal actions (all statuses), sorted by `act_deadline` ASC, nulls last.

Action and decision KPI cards are not shown in this tab; it is an action-list focused view.

| Column | Content |
|--------|---------|
| Deadline | Date cell, red if overdue |
| Ref | Link to detail |
| Title | Link to detail; strikethrough + reduced opacity if Done/Cancelled |
| Status | Colored badge || Acceptance | Assignment acceptance summary badges (✓ accepted / ⏳ pending / ✗ declined) || Priority | Colored badge |
| Category | Text |

### §3.4 Layout — By Category tab

> **Note**: This tab shows action-focused information only. Recently Completed and Recent Decisions sections are **not** displayed here (Overview only).

Action and decision KPI cards are not shown in this tab; it is a category-grouped action view.

For each category the user has actions in, render a collapsible group:

```
▼ [Topic Name]  •  Open: N  •  Overdue: N
   [actions table — same columns as By Deadline, sorted by deadline]
```

Actions with no category are grouped under **"No Category"** at the bottom.

### §3.5 Layout — Gantt tab

- One horizontal bar per action
- X-axis: date range from earliest deadline − 7 days to latest deadline + 14 days
- Bar width: `created_at` → `deadline` (or today if no deadline)
- Bar color by status (same palette as status badges)
- Y-axis: grouped by category, then sorted by deadline within category
- Today marker: vertical red dashed line
- Click bar → navigate to action detail

### §3.6 Quick Actions (from dashboard)

| Action | Available When | UX |
|--------|---------------|-----|
| View action detail | Any action | Click title → opens detail page |
| Create new action | Always (own user only) | "+ New Action" button top-right |

---

## §4 Team Dashboard

> **V1.1 scope** — Not in MVP. Added in Week 2.

### §4.1 Layout

| Section | Content |
|---------|---------|
| **Team Summary** | KPI cards: Total Actions, Open, Overdue, Done |
| **Status Distribution** | Stacked bar chart by status |
| **Workload Distribution** | Bar chart: action count per team member (D62) |
| **Overdue Actions** | Three detailed tables/tabs over the same overdue dataset: By Deadline, By Owner, By Category |
| **Action detail columns** | Title (+description), Owner, Category, Assignees, Meeting Series, Deadline, Status |
| **Team Actions panel** | Not shown in team dashboard (dedicated action menu is used instead) |

#### Tab Structure

The Team Dashboard uses an outer tab structure mirroring the Personal Dashboard:

| Tab | Content |
|-----|---------|
| **Overview** | KPI cards + Members breakdown table + Overdue Actions card (with By Deadline / Lead / Category sub-tabs) |
| **By Lead** | All team actions grouped by Lead; each group shows a collapsible card with header (Lead name + Open/Overdue badges) and an action table |
| **By Category** | All team actions grouped by Business Theme; each group shows a collapsible card with header (Category name + Open/Overdue badges) and an action table |

Group card header format:
```
▼ [Lead Name / Category Name]  •  Open: N  •  Overdue: N
   [actions table — columns: Title, Lead, Category, Assignees, Meeting, Deadline, Status]
```

Cancelled actions are excluded from group tables. Groups sorted by overdue count descending, then alphabetically.

### §4.2 Filters

| Filter | Options |
|--------|---------|
| Time range | Last 30 / 60 / 90 days / Custom |
| Status | Any combination |
| Priority | Any combination |
| Category | Dropdown from taxonomy |
| Assignee | Team member dropdown |

### §4.3 Resource Workload Forecast *(Implemented v2.17)*

> **All authenticated users** — Shown as the **⏱ Workload** tab on the Team Dashboard alongside Members, All Actions, and Gantt.

**Chart type**: Stacked bar chart
- **X-axis**: Next 16 weeks (Sunday-start ISO weeks, e.g. W10, W11…)
- **Y-axis**: Estimated hours
- **Stacks**: One colored series per team member
- **Tooltip**: Member name · hours · week date range

**Hours spreading rule**:

For each assignment row with `asg_estimated_hours IS NOT NULL`:

$$\text{hours\_per\_week} = \frac{\text{asg\_estimated\_hours}}{n\_overlapping\_weeks}$$

Where `n_overlapping_weeks` = number of 16-week window buckets whose range `[week\_start, week\_end]` overlaps with `[effective\_start, effective\_end]` (minimum 1 to avoid division by zero).

| Date field | Rule |
|------------|------|
| Effective start | `COALESCE(act_start_date, today)` |
| Effective end | `act_deadline` |
| Overlap | Week is included if `week_start ≤ effective_end AND week_end ≥ effective_start` |
| Boundary | Fractional weeks at boundaries receive a full week's share |

**Scope rules**:
- Assignment-based workload counts include users explicitly assigned to an action
- Action filter: `act_archived = 0` AND `act_status NOT IN ('Done', 'Cancelled')`
- Only assignments with `asg_estimated_hours IS NOT NULL` are included

**Data entry**: `asg_estimated_hours` is entered per assignment on the Action Detail page so each assignee can provide their own hours for the action.

**Personal Dashboard consistency**: The personal dashboard Workload tab applies the same spread rule using the logged-in user's own `asg_estimated_hours` values.

---

## §5 Team Dashboard

> **MVP scope** — Available on Day 2 AM. Shows team-level overview for any authenticated user.

### §5.1 Layout

| Section | Content | MVP |
|---------|---------|:---:|
| **Team KPIs** | Cards: Total, Open, Overdue, Completed this period, Completion rate % | ✅ |
| **Status Breakdown** | Colored status badges with counts (simple, no chart in MVP) | ✅ |
| **Overdue Table** | Table: top 10 oldest overdue actions with owner + days overdue | ✅ |
| **Priority Breakdown** | Colored badges: Critical/High/Medium/Low with counts | ✅ |
| **Escalation Summary** | Count of Escalated + WAR items | ✅ |
| **Team Comparison** | Grouped bar chart: action counts by team within team | V1.1 |
| **Trend Charts** | Dual-axis: created vs completed over time (D64) | V1.2 |
| **Team Comparison** | Cross-team heatmap (D65) | V1.2 |

### §5.2 Workload Cards (Team Manager View) *(superseded — see §4.3)*

> **MVP scope** — Originally shown within the Team Dashboard for team managers and Admin as action-count cards. **Superseded in v2.17** by the hours-based Resource Workload Forecast (§4.3), which provides more accurate capacity planning. The per-member action counts remain visible in the **Members** tab.

The Members tab table still shows per-employee:

| Column | Content |
|--------|---------|
| Member | `display_name` |
| Total | COUNT(assigned non-archived) |
| Open | COUNT(non-terminal) |
| Overdue | COUNT(deadline < today, non-terminal) |
| Due This Week | COUNT(deadline within 7 days) |

For hours-based workload distribution, see **§4.3 Resource Workload Forecast**.

---

| Add comments | ✅ (same as Member) |

### §5b.3 Layout additions on Category Dashboard

| Section | Content |
|---------|---------|
| **Pending Overdue** | All overdue actions in category, with inline owner-reassign dropdown |
| **Deadline Editor** | Inline date-picker on deadline column for category actions |
| **Workload summary** | Same K54 workload cards but scoped to this category |

---

## §6 Management Dashboard

> **V1.1 scope** — Not in MVP. Added in Week 2 alongside Team Dashboard.

### §6.1 Layout (D66)

Single-page executive summary:

| Section | Content |
|---------|---------|
| **Organization KPIs** | Cards: Total actions, Completion rate, Avg completion time, Overdue % |
| **Team Heatmap** | Grid: teams × statuses with color intensity |
| **Escalation Board** | All Escalated + WAR actions across all teams |
| **Overdue Trend** | Line chart: overdue count over last 6 months |
| **Completion Velocity** | Line chart: actions completed per week, 12-week rolling |
| **Top Contributors** | Table: users with most completions this period |
| **Risk Radar** | Actions approaching deadline with Critical/High priority |

### §6.2 Drill-Down Navigation

All dashboard elements are clickable:
- Chart segment → filtered action list
- KPI card → relevant filtered view
- Team in heatmap → Team dashboard
- Action in table → Action detail page

---

## §7 KPI Definitions

### §7.1 Completion KPIs (count-based per D12) (D67)

| KPI | Formula | Scope |
|-----|---------|-------|
| Total Actions | COUNT(all actions in scope) | Any |
| Open Actions | COUNT(status IN [Open, In Progress, On Hold, Under Review]) | Any |
| Completion Rate | COUNT(Done) / COUNT(all non-Cancelled) × 100% | Period |
| Overdue Count | COUNT(deadline < today AND status NOT IN [Done, Cancelled]) | Current |
| Overdue Rate | Overdue Count / Open Actions × 100% | Current |
| Avg Completion Time | AVG(actual_completion_date - created_date) in days | Period |
| On-Time Completion | COUNT(Done AND actual ≤ deadline) / COUNT(Done) × 100% | Period |

### §7.2 Workload KPIs (D68)

| KPI | Formula |
|-----|---------|
| Actions per User | COUNT(active assignments by user, any role, non-Declined) |
| Estimated Hours per User per Week | SUM(asg_estimated_hours / n_overlap_weeks) per person per bucket — see §4.3 |
| New Actions this Period | COUNT(created_date IN period) |
| Closed Actions this Period | COUNT(actual_completion_date IN period) |
| Net Change | New - Closed |
| Backlog per Team | COUNT(Open + In Progress by team) |
| Backlog Hours per Team | SUM(asg_estimated_hours) for open non-cancelled actions |

### §7.3 Assignment KPIs (D69)

| KPI | Formula |
|-----|---------|
| Acceptance Rate | COUNT(Accepted) / COUNT(Assigned) × 100% |
| Avg Response Time | AVG(response_date - assigned_date) |
| Reassignment Rate | COUNT(Reassigned) / COUNT(Assigned) × 100% |
| Decline Rate | COUNT(Declined) / COUNT(Assigned) × 100% |

---

## §8 Reporting Engine

### §8.1 Report Builder (D70)

> **V1.2 scope** — Not in MVP or V1.1. MVP provides Excel export from filtered views (ad-hoc). The full report builder with saved templates is V1.2.

Users can create custom reports by selecting:

| Parameter | Options |
|-----------|---------|
| **Columns** | Any action/assignment/user fields |
| **Filters** | Team, Team, Status, Priority, Date range, Owner, Category, Tags |
| **Grouping** | Group by Team, Team, Status, Priority, Owner |
| **Sorting** | Any column, ascending/descending |
| **Aggregation** | Count, Avg (for numeric/date fields) |

### §8.2 Report Templates (D71)

Pre-built templates:

| Template | Description |
|----------|-------------|
| Weekly Status | All open actions by team with status and deadline |
| Overdue Report | All overdue actions with days overdue, sorted by severity |
| Workload Report | Action count per user per team |
| Completion Summary | Completed actions this period with avg completion time |
| Escalation Report | All Escalated + WAR actions |
| Team Comparison | Side-by-side metrics for all teams |

### §8.3 Export Format (D72)

- **Excel (.xlsx)**: Primary format. Formatted with headers, auto-filter, conditional formatting for overdue items (red), summary row.
- Column headers bilingual: `Status / 状态`, `Owner / 负责人`, etc.

### §8.4 Scheduled Reports (D73)

> **V1.2 scope** — Not in MVP or V1.1.

| Field | Description |
|-------|-------------|
| Report template | Which report to run |
| Schedule | Daily / Weekly (day) / Monthly (date) |
| Time | Delivery time (default 08:00) |
| Recipients | List of email addresses (manual or by role) |
| Format | Excel (D72) |
| Active | On/Off toggle |

### §8.5 Ad-Hoc Export (D74)

> **MVP scope** — This is the only reporting feature in MVP. Available from any filtered action list or dashboard view.

From any dashboard or filtered action list view:
- "Export to Excel" button
- Exports current view with applied filters
- Includes a "Generated on" timestamp and filter summary sheet

---

## §10 Admin Inline Actions Table

> **MVP scope** — Accessible only by Admin and TeamLead via the `/admin/actions` page.

### §10.1 Purpose

A paginated, inline-editable table of all actions. Managers can update any action without opening the detail page. Designed for bulk review sessions (e.g., weekly meeting follow-up).

### §10.2 Editable Fields (inline, in-row)

| Field | Widget | Notes |
|-------|--------|-------|
| Title | Text input | Click to edit in place |
| Status | Dropdown | Valid next-state transitions only |
| Owner | User dropdown | All active users, searchable |
| Deadline | Date picker | |
| Priority | Dropdown | Critical / High / Medium / Low |
| Category | Dropdown | Active categories only |

> **Read-only columns (not editable inline):**
> - **Acceptance** — Shows assignment acceptance summary from `t_assignment.asg_status` counts (✓ accepted / ⏳ pending / ✗ declined). Separate from action status.

### §10.3 Pagination

| Parameter | Value |
|-----------|-------|
| Rows per page | 25 |
| Navigation | Previous / Next buttons + page X of Y indicator |
| Sort | Clickable column headers (ascending/descending) |
| Filters | Status, Team, Priority, Category — filter bar above table |

### §10.4 Behaviour

- Each field saves on blur/select (no "Save row" button needed)
- Toast notification confirms each save
- Optimistic update: UI updates immediately, reverts on error
- Every inline edit creates an `ActionHistory` entry

---

## §11 In-App Notification Bell

> **MVP scope** — Visible in the navbar for all logged-in users.

### §11.1 Events that generate a notification

| Event | Recipient |
|-------|-----------|
| Action assigned to user (as Owner, Lead, or Delegate) | Assignee |
| Action deadline within 3 calendar days | Owner + Lead |
| Action becomes overdue (deadline passed, not done) | Owner + Lead |
| Comment posted on an action user is assigned to | Owner + Lead |

### §11.2 Bell UI

| Element | Behaviour |
|---------|-----------|
| Bell icon in navbar | Always visible when logged in |
| Red badge | Shows unread count (max display: 99+) |
| Dropdown panel | Latest 20 notifications, newest first; mark-all-read button |
| Click notification | Navigates to relevant action / comment |
| Auto-refresh | Polls every 60 seconds for new notifications |

---

## §12 Chart Specifications (D75)

| Chart | Type | X-Axis | Y-Axis | Notes |
|-------|------|--------|--------|-------|
| Status Distribution | Stacked Bar | Status | Count | Color-coded by status |
| Workload Distribution | Horizontal Bar | User | Action count | Sorted desc |
| **Resource Workload Forecast** | **Stacked Bar** | **Week (next 16)** | **Hours** | **One stack per team member; hours spread across start–end range (§4.3)** |
| Completion Trend | Line | Week | Count | 12-week rolling window |
| Created vs Completed | Dual-axis Line | Month | Count | 6-month window |
| Priority Breakdown | Donut | Priority | Count | Color: red/orange/yellow/green |
| Team Heatmap | Matrix | Team | Status | Cell intensity = count |
| Overdue Trend | Area | Month | Count | Red gradient |
