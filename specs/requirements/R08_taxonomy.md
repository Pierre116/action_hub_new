# ActionHub — Taxonomy & Classification

> **Status**: Requirements-level specification  
> **Depends on**: `R01_entities.md` (taxonomy entities), `R00_initial_vision.md` (scope)  
> **Decisions**: D99–D108 in `DECISIONS.md`  
> **Consumed by**: SpecForge for `05_data_dictionary.md`, `10_MCD.md`

---

## §1 Overview

ActionHub uses an admin-configurable taxonomy system to classify work. The taxonomy has one primary strategic classification dimension, **Category**, plus **Tags** for optional free-form labeling. All taxonomy items are bilingual (English + Chinese).

> **Taxonomy consolidation (2026-03-17):** The former user-facing term **Business Theme** is replaced by **Category**. The storage model remains `t_topic` / `TOP_*` until a later physical migration.

> **Unified classification rule:**
> - Actions carry **1 or 2 Categories**.
> - Meetings and Meeting Decisions may carry **0, 1, or 2 Categories**.
> - Workflow Instances do **not** carry Categories; workflows operate on the bound action's classification instead.

### Terminology

| Term | DB Prefix | Chinese | Description |
|------|-----------|---------|-------------|
| **Category** | `TOP_*` | 类别 | Strategic subject classification for actions, meetings, and decisions |

### MVP (1.5-day) Scope

| Feature | MVP | V1.1 |
|---------|:---:|:----:|
| Teams (12 seeded) | ✅ | |
| Teams (seeded or admin-created via simple form) | ✅ | |
| Categories (seeded from Excel analysis) | ✅ | |
| Categories (8 seeded) | ✅ | |
| Tags (free-form) | | ✅ |
| Admin taxonomy tree view + drag-drop | | ✅ |
| Tag management (merge/rename/cleanup) | | ✅ |
| Bulk CSV import for taxonomy | | ✅ |

> **MVP approach**: Taxonomy is **seeded at deployment** (SQL script or migration). Admin can add new categories via a simple form. The full tree view admin panel is V1.1.

---

## §2 Taxonomy Hierarchy

```
Category (strategic dimension) — global, admin-configurable
```

### §2.1 Team (D99)

| Field | Type | Required |
|-------|------|----------|
| id | INT (PK) | Yes |
| name_en | VARCHAR(100) | Yes |
| name_cn | VARCHAR(100) | Yes |
| code | VARCHAR(10) | Yes |
| description | TEXT | No |
| is_active | BOOLEAN | Yes (default: true) |
| sort_order | INT | Yes (default: 0) |

**Seed teams** (from stakeholder input):

| Code | English | Chinese |
|------|---------|----------|
| FAC | Facility | 设施 |
| IE | Industrial Engineering | 工业工程 |
| CI | Continuous Improvement | 持续改善 |
| QA | Quality | 质量 |
| HP | Heavy Parts | 重件 |
| WH | Warehouse | 仓库 |
| LOG | Logistic | 物流 |
| SRC | Sourcing | 寻源 |
| PROC | Procurement | 采购 |
| MM | Material Management | 物料管理 |
| ESL | Equipment Supply Leader | 设备供应主管 |
| PLAN | Planning | 计划 |

### §2.2 Team (D100)

| Field | Type | Required |
|-------|------|----------|
| id | INT (PK) | Yes |
| team_id | FK → Team | Yes |
| name_en | VARCHAR(100) | Yes |
| name_cn | VARCHAR(100) | Yes |
| is_active | BOOLEAN | Yes |
| sort_order | INT | Yes |

### §2.3 Category / 类别 (D101)

Categories are the primary strategic classification for actions, meetings, and decisions. They are admin-configurable and seeded at deployment.

| Field | Type | Required |
|-------|------|----------|
| id | INT (PK) | Yes |
| name_en | VARCHAR(100) | Yes |
| name_cn | VARCHAR(100) | Yes |
| description | TEXT | No |
| is_active | BOOLEAN | Yes |
| sort_order | INT | Yes |

**Seed categories** (from Excel analysis):

| Category EN | Category CN | Source |
|----------|----------|--------|
| Equipment KOM | 设备开工会 | v3 |
| 1st BOM | 首次BOM | v3 |
| Sourcing List | 采购清单 | v3 |
| CTO + Procurement | CTO+采购 | v3 |
| LT Reduction | 交期缩短 | v3 |
| Training | 人员培训 | v1 |
| Project Display | 项目展示 | v1 |
| Red Ticket | 红单 | v4 |

### §2.4 Category Attachment Rules

| Entity | Minimum | Maximum | Notes |
|-------|---------|---------|-------|
| Action | 1 | 2 | Stored as primary + optional secondary category |
| Meeting | 0 | 2 | Optional classification context for meeting scope |
| Meeting Decision | 0 | 2 | Defaults from meeting when omitted |

**Rules:**
- Category #2 must differ from Category #1.
- Filters by Category must match either attached category.
- Dashboard and summary counts include an entity in every attached category.
- Workflow instances never store their own categories; workflow-created or workflow-bound actions remain the reporting unit for category analytics.

---

## §3 Orthogonal Classification

### §3.1 Tags (D103)

Free-form labels that any user can create and apply to actions.

| Field | Type | Required |
|-------|------|----------|
| id | INT (PK) | Yes |
| name | VARCHAR(50) | Yes |
| created_by | FK → User | Yes |
| usage_count | INT | Yes (auto-maintained) |
| is_active | BOOLEAN | Yes |

**Rules:**
- Tags are case-insensitive; normalized to lowercase
- Duplicate detection: "SAP" and "sap" are the same tag
- Admin can merge, rename, or deactivate tags
- Tag auto-complete from existing tags when typing
- Maximum 10 tags per action (D104)

**Seed tags** (from Excel analysis): `SAP`, `BOM`, `ASME`, `blower`, `filler`, `aseptic`, `国产化`, `WAR`, `routing`

---

## §4 Admin Configuration Interface

### §4.1 Taxonomy Management Page (D105)

| Feature | Description |
|---------|-------------|
| Tree view | Category list |
| Add/Edit/Deactivate | CRUD for all taxonomy levels |
| Drag-and-drop reorder | Change sort_order visually |
| Bilingual input | Side-by-side EN/CN fields |
| Usage count | Show how many actions reference each item |
| Bulk import | CSV upload for initial taxonomy setup |

### §4.2 Tag Management Page (D106)

| Feature | Description |
|---------|-------------|
| List view | Table sorted by usage_count descending |
| Merge | Select 2+ tags → merge into one (reassign all actions) |
| Rename | Change tag name (all references updated) |
| Deactivate | Hide tag from auto-complete (keep existing references) |
| Cleanup | Identify tags with usage_count = 0 |

---

## §5 Taxonomy Constraints

### §5.1 Soft Delete (D107)

All taxonomy items use soft-delete (`is_active = false`). Deactivated items:
- Hidden from dropdown lists for new actions
- Still visible on existing actions that reference them
- Shown with "Archived" badge in admin panel
- Can be reactivated

### §5.2 Referential Integrity (D108)

| Scenario | Behavior |
|----------|----------|
| Delete category referenced by actions/meetings/decisions/workflows | Soft-delete only |
| Delete category with actions | Soft-delete only (actions keep reference) |
| Merge teams | Not supported in V1 — use manual reassignment |

---

## §6 Search & Filter Integration

All taxonomy dimensions are available as filters throughout the app:

| Location | Available Filters |
|----------|------------------|
| Action list page | Team, Category, Tags, Status, Priority, Owner, Date range |
| Dashboard charts | Category, Team, Date range |
| Report builder | All of the above |
| Global search | Text search across action title, description, tags, comments |
