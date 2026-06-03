# ActionHub — Data Import (Excel Seed)

> **Status**: Requirements-level specification  
> **Depends on**: `R01_entities.md` (target schema), `R08_taxonomy.md` (classification)  
> **Decisions**: D89–D98 in `DECISIONS.md`  
> **Consumed by**: SpecForge for `05_data_dictionary.md`, `30_physical_specs.md`

---

## §1 Overview

ActionHub imports historical action data from 4 existing Excel logbook formats as one-time seed data. After initial import, all data entry happens through the app UI. The import process maps heterogeneous Excel schemas into the unified ActionHub entity model.

### MVP (1.5-day) Scope

| Feature | MVP | V1.1 |
|---------|:---:|:----:|
| Import v3 (action logbook — 89 rows) | ✅ | |
| Import v4 (红单 — 333 rows) | ✅ | |
| Import v1 (action log — 39 rows) | ✅ | |
| Import v2 (action plan — 32 rows) | ✅ | |
| Auto-format detection | ✅ | |
| Preview before confirm | ✅ | |
| User name resolution (exact match) | ✅ | |
| User name resolution (partial match) | | ✅ |
| Duplicate detection (exact title) | ✅ | |
| Duplicate detection (fuzzy scoring) | | ✅ |
| Post-import merge/dedup UI | | ✅ |
| Import rollback | ✅ | |

> **MVP priority order**: Import v3 and v4 first (largest datasets = most value). v1 and v2 have simpler schemas and fewer rows. If time is tight on Day 1 PM, v1+v2 can slip to Day 2 AM.

**V1.1**: Post-import validation UI, merge/dedup tool, unresolved owner management.

---

## §2 Source File Inventory

| File | Version | Sheet | Rows | Key Structure |
|------|---------|-------|------|---------------|
| Action log-v1.xlsx | v1 | Action list | 39 | Phase, Category, Action, Dept, Owner, Deadline, Status, Comments + meeting-date columns |
| Action plan template-v2.xlsx | v2 | Action Plan | 32 | No, Plant Area, Detail/Sub Actions, Owner, Status, Docs, 52-week Gantt |
| action logbook-v3.xlsx | v3 | Action Log (2) | 89 | #, Date, EQPT, Area, Action, Responsible, Benefit, Initial/Revised/Actual Due Dates, Status, biweekly meeting notes |
| logbook-v4.xlsx | v4 | 红单 | 333 | Date, Impact Phase, WAR, Category, WBS, Machine No, PDS No, Problem, Material No, Qty, SAP routing, Deadline, Owner, Status |

---

## §3 Column Mapping

### §3.1 v1 → ActionHub

| v1 Column | ActionHub Field | Transform |
|-----------|----------------|-----------|
| Phase (短期/中期/长期) | Tag | Create tags: "短期", "中期", "长期" |
| Cat. | Category | Map or create category |
| Action | title + description | First line → title; full text → description |
| Dep | Team | Map to Team entity |
| Owner | Assignment (Lead) | Map to User by name (D89) |
| Deadline | deadline | Date conversion |
| Status | status | Map: "On going" → "In Progress", "Done" → "Done" |
| Comments | ActionComment | Create initial comment |
| Meeting date columns | ActionComment | One comment per meeting date with notes |

### §3.2 v2 → ActionHub

| v2 Column | ActionHub Field | Transform |
|-----------|----------------|-----------|
| No. | source_ref | Original reference number |
| PLANT AREA | Category | Map or create category |
| Detail Actions | title | |
| Owner | Assignment (Lead) | Map to User |
| Status | status | Direct map |
| Documents/Reports | ActionComment | Reference note |
| Week 1–52 (Plan/Actual) | ActionComment | Summarize timeline as comment |
| Memo | ActionComment | |

### §3.3 v3 → ActionHub

| v3 Column | ActionHub Field | Transform |
|-----------|----------------|-----------|
| # | source_ref | Original sequence number |
| Date of Creation | created_date | Date conversion |
| EQPT | Category | Map: "Aseptic Combi", "Filler Aseptic +Blower", etc. |
| Area | Category | Map: "Eqpt KOM", "1° BOM", "Sourcing List", etc. |
| Action | title + description | |
| Responsible | Assignment (Lead) | Map to User |
| Benefit in W | Tag | Create tag with value |
| Initial Due Date | deadline | |
| Revised Date | revised_deadline | |
| Actual Date | actual_completion_date | |
| Status | status | Map: "Open" → "Open", "In progress" → "In Progress", "Done" → "Done" |
| Comments | ActionComment | |
| Biweekly date columns | ActionComment | One comment per meeting date |

### §3.4 v4 → ActionHub

| v4 Column | ActionHub Field | Transform |
|-----------|----------------|-----------|
| Date 哪天提出的 | created_date | |
| 影响阶段 | Tag | "分装", "总装", etc. |
| 是否升级到WAR | escalation_level | "Yes" → WAR, "No" → Normal |
| 归类 | Category | "Supplier issue", etc. |
| WBS | Tag | If present |
| 机器号 | description (append) | Machine reference |
| PDS号 | description (append) | PDS reference |
| 问题描述 | title + description | |
| 物料号 | Tag | Material number(s) |
| 数量 | description (append) | |
| SAP routing时间 | description (append) | |
| Deadline | deadline | |
| 负责人 | Assignment (Lead) | Map to User |
| 状态 | status | Direct map |
| Meeting date columns | ActionComment | |

---

## §4 Import Process

### §4.1 Import Workflow (D90)

```
Admin uploads Excel file via Import page
 → System detects file version (v1/v2/v3/v4) by sheet name and header pattern
 → System parses and displays preview: N rows detected, M mappable
 → Admin reviews mapping and resolves:
    - Unknown owners → map to existing User or skip
    - Unknown teams → create new or map to existing
    - Unknown categories/topics → create new or map to existing
 → Admin confirms import
 → System creates Action + Assignment + Comment records
 → Import summary displayed: N created, M skipped, K warnings
 → Import log saved to ImportLog entity
```

### §4.2 Version Detection (D91)

| Sheet Name | Header Pattern | Detected Version |
|------------|---------------|-----------------|
| "Action list" | Col A = "Phase" | v1 |
| "Action Plan" | Row 3 Col B = "PLANT AREA" | v2 |
| "Action Log (2)" | Row 10 Col E = "Action" | v3 |
| "红单" | Col A = "Date\n哪天提出的" | v4 |

### §4.3 User Name Resolution (D89)

| Source Name | Resolution Strategy |
|-------------|---------------------|
| Exact match | Match against User.display_name or User.display_name_cn |
| Partial match | Try first name, last name separately |
| No match | Mark as "Unresolved" — Admin manually maps or creates User |
| Multiple owners | Split by "/" or "," — create multiple assignments |

---

## §5 Data Quality Rules (D92)

| Rule | Behavior |
|------|----------|
| Missing title | Skip row, log warning |
| Missing deadline | Import with deadline = NULL, flag for review |
| Missing owner | Import with Lead = importing Admin, flag for reassignment |
| Duplicate detection | Match by title + team + deadline; warn if likely duplicate (D93) |
| Encoding | Support UTF-8 and GB2312 for Chinese characters |
| Date formats | Support: YYYY-MM-DD, DD/MM/YYYY, Excel serial dates |
| Status normalization | Map all variants: "On going"/"进行中" → "In Progress", "Done"/"完成" → "Done" |

---

## §6 Import Log (D94)

| Field | Type |
|-------|------|
| id | INT (PK) |
| file_name | VARCHAR(255) |
| file_version | ENUM (v1/v2/v3/v4) |
| imported_by | FK → User |
| import_date | DATETIME |
| total_rows | INT |
| imported_count | INT |
| skipped_count | INT |
| warning_count | INT |
| warnings | JSON (array of {row, field, message}) |
| status | ENUM (success / partial / failed) |

---

## §7 Post-Import Validation (D95)

After import, Admin can:

1. **Review imported actions** — filtered list showing all actions with `source = Import`
2. **Resolve unmatched owners** — bulk reassignment tool for "Unresolved" owners
3. **Merge duplicates** — side-by-side comparison and merge tool
4. **Assign missing taxonomy** — bulk category/category assignment

---

## §8 Merge / Deduplication Rules (D93)

> **MVP**: Exact title match only (case-insensitive). If title + team match an existing action, flag as "Likely Duplicate" in import preview. Admin can skip or force-import.

> **V1.1**: Full fuzzy scoring below.

| Field | Weight | Match if... |
|-------|--------|-------------|
| Title | 40% | Levenshtein distance < 5 or cosine similarity > 0.8 |
| Owner | 20% | Same user |
| Deadline | 20% | Within 7 days |
| Team | 20% | Same team |

Score > 70% → flag as "Likely Duplicate" for Admin review.

---

## §9 Constraints (D96–D98)

| Constraint | Rule |
|------------|------|
| One-time import | Import tool available only to Admin; not a recurring sync (D96) |
| No destructive overwrite | Import creates new records only; never modifies existing (D97) |
| Rollback | Admin can delete all records from a specific import batch by import_log_id (D98) |
| File retention | Uploaded Excel files stored on server for 90 days then auto-deleted |
