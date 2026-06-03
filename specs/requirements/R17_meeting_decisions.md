# ActionHub — Meeting Decisions Management

> **Status**: ✅ Current  
> **Depends on**: R01 (entities), R13 (meetings/testing)  
> **Consumed by**: SpecForge for S05, S10, S11, S16 updates  
> **Version target**: V3.8 (P8 - IMPLEMENTED)

---

## §1 Objectives

| # | Objective |
|---|-----------|
| MD1 | Centralize all decisions made during meetings in a single, searchable repository |
| MD2 | Provide a lifecycle for decisions so their status can be tracked over time |
| MD3 | Link decisions to meetings, actions, and up to 2 categories for full traceability |
| MD4 | Enable fast retrieval via full-text search, filters, and tags (wiki / mini-RAG style) |
| MD5 | Surface decisions in dashboards alongside actions for a unified operational view |

---

## §2 Decision Entity

### §2.1 Core Fields

| Field | Description | Required |
|-------|-------------|----------|
| Title | Short summary of the decision (≤ 255 chars) | Yes |
| Body | Detailed description, rationale, context (rich text) | Yes |
| Status | Lifecycle status (see §3) | Yes (default: Published) |
| Meeting Instance | Which meeting the decision was recorded in | Yes (FK) |
| Categories | Up to 2 strategic categories | Optional (0..2 FKs, inherited from meeting if not specified) |
| Linked Action | Action spawned by or related to this decision | Optional (FK) |
| Tags | Comma-separated keywords for search/retrieval | Optional |
| Decided At | Date/time the decision was formally agreed | Optional (defaults to meeting date) |
| Created By | User who recorded the decision | Auto (must be meeting organizer or owner) |
| Created At | Record creation timestamp | Auto |
| Updated At | Last modification timestamp | Auto |
| Expires At | Date/time the decision entered Expired state | Auto on Published → Expired transition |
| Status Changed At | Latest status transition timestamp | Auto on any status transition |

### §2.2 Cardinality

- One **meeting instance** can have 0..N decisions.
- One **decision** belongs to exactly 1 meeting instance.
- One **decision** can optionally link to 0..1 actions.
- One **action** can be linked from 0..N decisions.
- One **decision** can optionally link to 0..2 categories.

---

## §3 Decision Lifecycle

Decisions follow the runtime 2-status lifecycle:

```
Published ──► Expired
```

| Status | Description |
|--------|-------------|
| Published | Decision is active and visible in the knowledge base |
| Expired | Decision is no longer active (superseded/retired/archive state) |

### §3.1 Valid Transitions

| From | To | Trigger |
|------|----|---------|
| Published | Expired | Admin transition or expiration governance |

---

## §4 Permissions

| Operation | Who |
|-----------|-----|
| Create decision | Meeting organizer (creator or owner via `t_meeting_owner`) |
| Edit decision title/body | Decision owner (`mdc_created_by`) or meeting organizer or Admin |
| Edit decision metadata/status | Meeting organizer or Admin |
| View decision | Any authenticated user (read-only) |
| Delete decision | Admin only (soft-delete) |

### §4.1 Revision Tracking

- When decision title or body is updated, the previous title/body snapshot is recorded in `t_meeting_decision_revision`.
- `GET /api/decisions/:id/revisions` returns revision snapshots newest first, including who saved the edit and when it was saved.
- Decision list displays revision metadata (`revision_count`, `last_revised_at`) so revised decisions are visible in normal listings.

---

## §5 Search & Retrieval (Wiki / Mini-RAG)

### §5.1 Full-Text Search

- Search across decision **title** and **body** fields.
- SQLite FTS5 virtual table for fast full-text indexing.
- Supports prefix matching, phrase queries, and Boolean operators.

### §5.2 Filters

| Filter | Type |
|--------|------|
| category_id | Dropdown / multi-select (matches either attached category) |
| Meeting | Dropdown (FK to `t_meeting_instance`) |
| Status | Multi-select (Published / Expired) |
| Date range | From–To on `decided_at` |
| Tags | Text input (partial match) |
| Created by | User dropdown |

> **Note:** The "Team projects only" filter has been removed. All decisions within the authenticated user's visibility scope are shown by default.

### §5.3 Results Display

- Paginated list with title, status badge, meeting name, date, categories, tags.
- Click to expand full body text inline.
- Sort by: date (default newest first), title, status, meeting date.

---

## §6 Dashboard Integration

| Dashboard | What to show |
|-----------|-------------|
| Personal | Decisions from meetings the user organized |
| Team | Decisions linked to the team's categories |
| Category | Decisions classified under that category |

Each dashboard widget shows:
- Count of decisions by status (Published / Expired).
- Recent decisions list (last 5 within last 30 days, linked to full search page). Personal dashboard Overview tab only.

---

## §7 Relationship to Existing Features

| Feature | Integration |
|---------|-------------|
| Meeting detail page | "Decisions" tab showing decisions recorded in that meeting |
| Action detail page | "Related decisions" section if any decision links to the action |
| Meeting creation | No decisions at creation time — added during/after the meeting |
| Export | Decisions exportable to Excel alongside actions |

---

## §8 UI Integration

### §8.1 Meeting Detail Page — New "Decisions" Tab

Add a 6th tab **📌 Decisions** to the meeting detail tab bar (after Memos).

| Element | Description |
|---------|-------------|
| Decision list | Table within the tab: Title, Status (badge), Decided At, Tags, Linked Action (link or "—") |
| Add button | "+ New Decision" button (visible only to meeting organizer/owner) opens inline form or modal |
| Inline form | Fields: Title (required), Body (rich text, required), Status (dropdown, default Published), Tags (text), Linked Action (search/select), Categories (up to 2, pre-filled from meeting) |
| Status transitions | Dropdown or button group on each decision row for valid transitions (organizer/owner only) |
| Expand/collapse | Click a row to expand the full body text inline |
| Edit | Pencil icon on each row (organizer/owner only) opens the same form pre-filled |
| Delete | Trash icon (Admin only), soft-deletes with confirmation dialog |

### §8.2 Meeting List Page — Decision Count Column

Add a **"Decisions"** count column to the meetings list table, next to the existing "Actions" count.

### §8.3 Standalone Decision Search Page

A new top-level page accessible from the navbar for cross-meeting decision search (wiki / mini-RAG).

| Element | Description |
|---------|-------------|
| URL | `/decisions` (React route) |
| Nav entry | **📌 Decisions** — new item in the top navbar, between "Meetings" and "My Workflow" |
| Search bar | Full-text search input (FTS5 query) with instant results |
| Filter panel | Collapsible sidebar or top-bar filters: Categories, Team, Meeting, Status, Date range, Tags, Created By |
| Results table | Title, Status badge, Meeting name (link), Categories, Decided At, Tags, Creator |
| Sort controls | Click column headers to sort |
| Expand | Click a row to show full body inline |
| Pagination | Standard pagination (25 per page) |

### §8.4 Dashboard Widgets

Add a **"Meeting Decisions"** card/widget to each dashboard:

| Dashboard | Widget placement |
|-----------|------------------|
| Personal (`/dashboard/personal`, Overview tab) | Below existing KPI cards — shows decisions from meetings the user organized; KPI cards + recent decisions table (last 30 days) |
| Personal (`/dashboard/personal`, By Deadline / By Category tabs) | No decision widget; these tabs are action-focused only |
| Team (`/dashboard/team`) | Decision KPI summary only (published/expired counts), no recent-decision table |
| Category (`/dashboard/category`) | Decision KPI summary only (published/expired counts), no recent-decision table |

Widget content:
- **Status donut chart**: Published / Expired counts.
- **Recent decisions**: shown on Personal dashboard Overview tab only (last 5 within last 30 days, with title, content preview, category, decision owner, **meeting series** name, and date). Links to standalone search page with pre-applied filter.
- **Decision reference format**: all user-facing decision identifiers must use `DEC-YYYY-xxxxx` (5-digit sequence based on decision PK), including Personal dashboard recent decisions and Decisions list.
- Decision search KPI labels for status cards must explicitly show the 30-day window, e.g. **Published (last 30 days)** and **Expired (last 30 days)**.

### §8.6 Decision Detail Navigation

- SPA route `/decisions/:id` provides read-focused decision details.
- Decision detail page includes a revision history section that lists prior title/body snapshots when revisions exist.
- Decision detail page includes a **Back** action that returns to the previous screen when browser history exists; otherwise it falls back to `/decisions`.
- Action detail page includes the same back behavior (previous screen fallback, then `/actions`).

### §8.5 Action Detail Page — Related Decisions

Add a **"Related Decisions"** section to the action detail page (below comments or in a new tab).

| Element | Description |
|---------|-------------|
| Condition | Only shown if ≥ 1 decision links to this action |
| Content | List of decisions: Title (link to meeting detail Decisions tab), Status badge, Meeting name, Decided At |
| Empty state | Section hidden entirely if no decisions link to the action |
