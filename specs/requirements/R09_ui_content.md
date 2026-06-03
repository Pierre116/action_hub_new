# ActionHub — UI/UX & Bilingual Interface

> **Status**: Requirements-level specification  
> **Current-state note**: The live product is a React SPA. Older MVP/V1.1 staging language and page inventory below are historical planning notes unless restated in the current-state sections.  
> **Depends on**: `R05_dashboards_reporting.md` (dashboard layout), `R08_taxonomy.md` (filters), `R16_workflow_app_extension.md`  
> **Decisions**: D109–D120 in `DECISIONS.md`  
> **Consumed by**: `S25_UI_Specs.md`, `S80_react_frontend_architecture.md`, user guidance docs

---

## §1 Overview

ActionHub is a browser-based React application with a bilingual UI (English + Chinese). The live UI must let administrators, managers, contributors, and process owners find their daily work without needing support.

### Current-state navigation baseline

The live authenticated navigation must cover:

- Dashboard
- Actions
- Meeting Series
- Decisions
- Instructions
- Workflow
- Admin

The in-app `Instructions` link must resolve to a real route in the SPA.

### Historical delivery staging note

The MVP/V1.1 tables below are historical planning artifacts. Current user guidance must come from the live route structure in `S80`, `README.md`, `HOW_TO.md`, and the in-app instructions surface.

### MVP (1.5-day) Scope

| Feature | MVP | V1.1 |
|---------|:---:|:----:|
| Login page | ✅ | |
| Personal Dashboard (“Today” view) | ✅ | |
| Action List (with filter/sort/search) | ✅ | |
| Action Detail page | ✅ | |
| New/Edit Action form | ✅ | |
| Quick-capture ("+" FAB) | ✅ | |
| Team Dashboard | ✅ | |
| Admin: User Management | ✅ | |
| Admin: Import page | ✅ | |
| Bilingual toggle (EN/CN) | ✅ | |
| Inline status update | ✅ | |
| First-login tooltip tour | ✅ | |
| Team/Management dashboards | | ✅ |
| Category Dashboard | | ✅ |
| Report builder + scheduled | | V1.2 |
| Admin: Taxonomy tree view | | ✅ |
| Notification history page | | ✅ |
| User Settings page | | ✅ |

> **MVP = 10 pages** (Login + Personal Dashboard + Action List + Action Detail + New Action + Edit Action + Team Dashboard + Admin Users + Admin Import + Quick-capture modal). V1.1 adds ~8 more pages.

**V1.1**: Admin panels, notification preferences, meeting pages, full responsive polish.

---

## §2 Language & Internationalization

### §2.1 Bilingual Strategy (D109)

| Aspect | Implementation |
|--------|----------------|
| UI chrome | Fully translated (menus, labels, buttons, tooltips) |
| User content | Stored as-is (mixed language); not translated |
| Toggle | Language switcher in top navigation bar |
| Default | Based on user's `preferred_language` setting |
| Persistence | Language preference stored in User profile |
| Date format | EN: `YYYY-MM-DD` / CN: `YYYY年MM月DD日` (D110) |
| Number format | Consistent: `1,234.56` (no CN variant needed) |

### §2.2 Translation Files

- i18n resource files: `en.json`, `zh.json`
- All UI strings keyed (no hardcoded text)
- Admin labels bilingual in entity data (name_en + name_cn)
- Reports: column headers bilingual `Status / 状态`

---

## §3 Page Map

### §3.1 Navigation Structure (D111)

```
┌──────────────────────────────────────────────────────┐
│ [Logo] ActionHub    [Search]   [🔔 3] [CN/EN] [User]│
├──────────┬───────────────────────────────────────────┤
│          │                                           │
│ Dashboard│  Main Content Area                        │
│  ├ My    │                                           │
│  ├ Team  │                                           │
│  ├ Dept  │                                           │
│  └ Mgmt  │                                           │
│          │                                           │
│ Actions  │                                           │
│  ├ All   │                                           │
│  ├ My    │                                           │
│  └ New   │                                           │
│          │                                           │
│ Meetings │                                           │
│  └ List  │                                           │
│          │                                           │
│ Reports  │                                           │
│  ├ Build │                                           │
│  └ Sched │                                           │
│          │                                           │
│ Admin    │  (Admin only)                             │
│  ├ Users │                                           │
│  ├ Taxon │                                           │
│  ├ Import│                                           │
│  └ Config│                                           │
│          │                                           │
└──────────┴───────────────────────────────────────────┘
```

### §3.2 Page Inventory

**MVP Pages (10):**

| # | Page | URL Pattern | Access | Day |
|---|------|-------------|--------|-----|
| 1 | Login | `/login` | Public | Day 1 |
| 2 | Personal Dashboard | `/dashboard` | All authenticated | Day 1 EVE |
| 3 | Action List | `/actions` | All authenticated | Day 1 EVE |
| 4 | Action Detail | `/actions/{id}` | All authenticated | Day 1 EVE |
| 5 | New Action | `/actions/new` | Member+ | Day 1 EVE |
| 6 | Edit Action | `/actions/{id}/edit` | Lead/Admin | Day 1 EVE |
| 7 | Team Dashboard | `/dashboard/team/{id}` | All authenticated | Day 2 AM |
| 8 | Admin: Users | `/admin/users` | Admin | Day 1 PM |
| 9 | Admin: Import | `/admin/import` | Admin | Day 1 PM |
| 10 | Quick-Capture Modal | (overlay, any page) | Member+ | Day 1 EVE |

**V1.1 Pages (+11):**

| # | Page | URL Pattern | Access |
|---|------|-------------|--------|
| 11 | Team Dashboard | `/dashboard/team/{id}` | All authenticated |
| 12 | Management Dashboard | `/dashboard/management` | All authenticated |
| 13 | My Actions | `/actions/mine` | All authenticated |
| 14 | Meeting List | `/meetings` | All authenticated |
| 15 | Meeting Detail | `/meetings/{id}` | All authenticated |
| 16 | Upload Meeting | `/meetings/upload` | Member+ |
| 17 | Admin: Taxonomy | `/admin/taxonomy` | Admin |
| 18 | Admin: Settings | `/admin/settings` | Admin |
| 19 | Notification History | `/notifications` | All authenticated |
| 20 | User Settings | `/settings` | All authenticated |
| 21 | Report Builder | `/reports/builder` | All authenticated |

---

## §4 Key Page Specifications

### §4.1 Action List Page (D112)

| Element | Specification | MVP |
|---------|---------------|:---:|
| Layout | Data table with pagination (25/50/100 per page) | ✅ |
| Columns | Reference, Title, Team, Owner, Priority, Status, Deadline | ✅ |
| Sorting | Click column header to sort (asc/desc toggle) | ✅ |
| Filtering | Filter bar: Team, Status, Priority, Date range | ✅ |
| Search | Real-time text search across title | ✅ |
| Color coding | Priority colors on left border; overdue rows highlighted red | ✅ |
| **Inline status update** | Click status badge → dropdown of valid transitions → instant save | ✅ |
| Export | "Export to Excel" button applies current filters | Day 2 |
| Quick actions | Status change inline, click title to open detail | ✅ |
| Bulk select | Checkbox per row + bulk action bar | V1.1 |
| Tags column | Tag chips (filterable) | V1.1 |

### §4.2 Action Detail Page (D113)

| Section | Content | MVP |
|---------|---------|:---:|
| Header | Reference code, title, status badge (clickable), priority badge, escalation badge | ✅ |
| Info panel | Team, Team, Category, Category, Deadline, Created by/date | ✅ |
| Assignments | Table: User, Role, Status | ✅ |
| Last Comment | Editable text field (MVP shortcut vs full comment entity) | ✅ |
| Dependencies | Visual list of blocking/blocked-by/related actions | V1.2 |
| Activity stream | Chronological list of all changes from ActionHistory | ✅ (basic) |
| Comment box | Rich text input with @mention support | V1.1 |
| Attachments | File list with upload button (meeting minutes, docs) | V1.1 |
| Sidebar | Quick stats: days open, days to deadline, assignment count | ✅ |

### §4.3 New/Edit Action Form (D114)

| Field | Input Type | Notes |
|-------|-----------|-------|
| Title | Text input | Required, max 255 chars |
| Description | Rich text editor | Optional |
| Team | Dropdown (cascading) | Pre-filled with user's dept |
| Team | Dropdown (filtered by dept) | |
| Category | Dropdown (filtered by team) | |
| Category | Dropdown | |
| Priority | Radio buttons (4 options) | Default: Medium |
| Deadline | Date picker | Required |
| Lead | User search/dropdown | Default: current user |
| Delegates | Multi-select user search | |
| Participants | Multi-select user search | |
| Tags | Tag input with auto-complete | Max 10 |
| Meeting link | Dropdown of recent meetings | Optional |

### §4.4 Admin: Import Page (MVP — Day 1 PM)

The import page is essential for MVP go-live. Users must see their existing data in the system immediately.

| Step | UI Element | Behavior |
|------|-----------|----------|
| **1. Upload** | Drag-and-drop zone + "Browse" button | Accept `.xlsx` files only; max 10MB; show filename + size after selection |
| **2. Detect** | Auto-detection badge | System detects format (v1/v2/v3/v4) and shows: "Detected: Action Logbook v3 — 89 rows" |
| **3. Preview** | Data table (first 20 rows) | Columns mapped to ActionHub fields; color-coded: green = mapped, amber = needs review, red = unmappable |
| **4. Resolve** | Inline resolution panel | Unknown owners → dropdown to pick existing User or "Create new user"; Unknown teams → dropdown to pick or skip |
| **5. Confirm** | Summary + "Import" button | "89 rows ready, 3 need review, 2 likely duplicates — Import All / Skip Duplicates" |
| **6. Result** | Import summary card | "✅ 86 imported, ⚠ 2 skipped (no title), 1 duplicate skipped — View imported actions" |

**Layout:**

```
┌─────────────────────────────────────────────────────┐
│  Admin > Import Seed Data                           │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │  📁 Drop Excel file here or [Browse]        │    │
│  │     Supported: v1, v2, v3, v4 formats       │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  Format detected: Action Logbook v3  ✅              │
│  Rows found: 89 | Mappable: 86 | Warnings: 3       │
│                                                     │
│  ┌─── Preview ────────────────────────────────┐     │
│  │ # │ Title          │ Dept │ Owner  │ Status│     │
│  │ 1 │ Fix valve...   │ FAC  │ Zhang  │ Open  │     │
│  │ 2 │ Update BOM...  │ IE   │ ⚠ ???  │ Done  │     │
│  │ ...                                        │     │
│  └────────────────────────────────────────────┘     │
│                                                     │
│  ⚠ 2 unresolved owners: [Map now]                   │
│  ⚠ 1 likely duplicate: [Review]                     │
│                                                     │
│  [Cancel]                        [Import 86 rows]   │
│                                                     │
│  ── Previous Imports ──                             │
│  │ v4 红单 │ 333 rows │ 2026-02-26 │ [Rollback]   │
│  │ v3 log  │ 89 rows  │ 2026-02-26 │ [Rollback]   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Key UX details:**
- Previous imports shown at bottom with rollback option (D98)
- Progress bar during import (for v4 with 333 rows, ~5 seconds)
- After successful import, "View imported actions" link goes to Action List filtered by `source=Import`
- Multiple files can be imported sequentially (one at a time)

---

## §5 Responsive Design (D115)

| Breakpoint | Layout |
|------------|--------|
| ≥1200px (desktop) | Full sidebar + content |
| 768–1199px (tablet) | Collapsible sidebar, content fills width |
| <768px (mobile) | Hamburger menu, single column content |

V1 priority is desktop (90% usage expected). Tablet and mobile should be functional but not optimized (D115).

---

## §6 Design System (D116)

### §6.1 Color Palette

| Usage | Color | Hex |
|-------|-------|-----|
| Primary | Blue | #2563EB |
| Success / Done | Green | #16A34A |
| Warning / Overdue approaching | Amber | #D97706 |
| Danger / Overdue / Critical | Red | #DC2626 |
| Info / In Progress | Cyan | #0891B2 |
| Neutral / On Hold | Gray | #6B7280 |
| Cancelled | Slate | #94A3B8 |

### §6.2 Typography

| Element | Font | Size |
|---------|------|------|
| Headings | System sans-serif (Segoe UI + PingFang SC) | H1: 24px, H2: 20px, H3: 16px |
| Body text | System sans-serif | 14px |
| Table data | System monospace for codes | 13px |
| CJK fallback | PingFang SC, Microsoft YaHei, SimHei | Same sizes |

### §6.3 Component Library (D117)

| Component | Notes |
|-----------|-------|
| Data table | Sortable, filterable, paginated, bulk-selectable |
| Form fields | Label (bilingual) + input + validation message |
| Status badge | Pill shape with status color |
| Priority badge | Colored dot + label |
| Tag chips | Removable chips with auto-complete input |
| Date picker | Calendar popup with "Today" shortcut |
| User select | Searchable dropdown with avatar + name |
| Notification bell | Badge count + dropdown panel |
| Modal dialogs | Confirmation, form submission, detail view |
| Toast messages | Success/Error/Warning/Info auto-dismiss |

---

## §7 Accessibility & Performance (D118–D120)

| Aspect | Target |
|--------|--------|
| Page load | < 2 seconds on LAN (D118) |
| Table rendering | Handle 500+ rows with pagination (no infinite scroll V1) |
| Keyboard navigation | Tab through form fields, Enter to submit |
| Color contrast | WCAG AA minimum (4.5:1 ratio) |
| Loading states | Skeleton screens for dashboard charts, spinners for data fetches |
| Error states | Inline validation on forms, toast for server errors |
| Empty states | Helpful message + CTA: “No overdue actions — great job! 🎉” / “No actions yet — create your first one” |
| Browser support | Chrome 90+, Edge 90+ (D119) |
| Print | Dashboard views printable with CSS print styles (D120) |
| **Onboarding** | First-login 3-step tooltip tour: "Your actions" → "Filters" → "Quick capture +" |
| **Progress feedback** | Action status change shows brief confetti/checkmark animation on completion |
| **Keyboard shortcuts** | `N` = new action, `F` = focus search, `Esc` = close modal (V1.1) |
