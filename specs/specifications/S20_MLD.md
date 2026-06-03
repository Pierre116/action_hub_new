# ActionHub — Logical Data Model (MLD)

> **Level**: L3 — Logical  
> **Merise Phase**: Modèle Logique des Données  
> **Source**: S10_MCD.md (entities/relationships), S05_data_dictionary.md (field definitions)  
> **Purpose**: Translate MCD into 3NF relational schema with foreign keys, indexes, and constraints  
> **DBMS**: SQLite 3.x (WAL mode)

---

## 0. Naming Conventions

| Concept | Convention | Example |
|---------|-----------|---------|
| Table | `t_` prefix + entity name (snake_case) | `t_action` |
| Column | Entity prefix code + field name | `act_title` |
| Primary key | `<prefix>_id` | `act_id` |
| Foreign key | Referenced entity prefix + `_id` | `act_team_id` |
| Index | `idx_<table>_<column(s)>` | `idx_action_status` |
| Unique index | `uq_<table>_<column>` | `uq_user_username` |

---

## 1. DDL — Foundation Tables

### 1.1 t_team

```sql
CREATE TABLE t_team (
    tea_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tea_name_en     TEXT    NOT NULL,
    tea_name_cn     TEXT    NOT NULL,
    tea_code        TEXT    NOT NULL UNIQUE,
    tea_desc        TEXT,
    dep_active      INTEGER NOT NULL DEFAULT 1,  -- boolean
    tea_sort_order  INTEGER NOT NULL DEFAULT 0,
    dep_created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    dep_updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE UNIQUE INDEX uq_team_code ON t_team(tea_code);
```

**Seed data**: 12 organization teams per R08/D99:

| Code | Name (EN) | Name (CN) |
|------|-----------|----------|
| FAC | Factory Management | 工厂管理 |
| IE | Industrial Engineering | 工业工程 |
| CI | Continuous Improvement | 持续改进 |
| QA | Quality Assurance | 质量保证 |
| HP | Human Performance | 人力绩效 |
| WH | Warehouse | 仓库 |
| LOG | Logistics | 物流 |
| SRC | Sourcing | 采购 |
| PROC | Process Engineering | 工艺工程 |
| MM | Maintenance Management | 维修管理 |
| ESL | EHS & Sustainability | 环境健康安全 |
| PLAN | Planning | 计划 |

---

### 1.2 t_team

```sql
CREATE TABLE t_team (
    tea_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tea_name_en     TEXT    NOT NULL,
    tea_name_cn     TEXT,
    tea_dept_id     INTEGER NOT NULL REFERENCES t_team(tea_id),
    tea_active      INTEGER NOT NULL DEFAULT 1,
    tea_sort_order  INTEGER NOT NULL DEFAULT 0,
    tea_created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    tea_updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE INDEX idx_team_dept ON t_team(tea_dept_id);
```

---

### 1.3 t_user

```sql
CREATE TABLE t_user (
    usr_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    usr_username      TEXT    NOT NULL UNIQUE,
    usr_pwd_hash      TEXT    NOT NULL,
    usr_display_name  TEXT    NOT NULL,
    usr_display_cn    TEXT,
    usr_email         TEXT    NOT NULL,
    usr_team_id       INTEGER NOT NULL REFERENCES t_team(tea_id),
    usr_team_id       INTEGER REFERENCES t_team(tea_id),
    usr_role          TEXT    NOT NULL DEFAULT 'Member'
                      CHECK(usr_role IN ('Admin','TeamLead','Member','ReadOnly')),
    usr_lang          TEXT    NOT NULL DEFAULT 'en' CHECK(usr_lang IN ('en','zh')),
    usr_active        INTEGER NOT NULL DEFAULT 1,
    usr_auth_source   TEXT    NOT NULL DEFAULT 'local' CHECK(usr_auth_source IN ('local','ldap')),
    usr_failed_logins INTEGER NOT NULL DEFAULT 0,
    usr_locked_until  TEXT,
    usr_last_login    TEXT,
    usr_created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    usr_updated_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE UNIQUE INDEX uq_user_username ON t_user(usr_username);
CREATE INDEX idx_user_dept ON t_user(usr_team_id);
CREATE INDEX idx_user_team ON t_user(usr_team_id);
CREATE INDEX idx_user_active ON t_user(usr_active);
```

---

### 1.4 t_topic (Global)

```sql
CREATE TABLE t_topic (
    top_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    top_name_en     TEXT    NOT NULL,
    top_name_cn     TEXT,
    top_desc        TEXT,
    top_active      INTEGER NOT NULL DEFAULT 1,  -- boolean soft-delete
    top_sort_order  INTEGER NOT NULL DEFAULT 0,
    top_created_by  INTEGER NOT NULL REFERENCES t_user(usr_id),
    top_created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    top_updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);
-- Categories are GLOBAL — no team or team parent.
-- Create/Edit/Delete: Admin and TeamLead only.
-- Read: all authenticated users.
```

---

### 1.5 t_category

```sql
CREATE TABLE t_category (
    cat_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cat_name_en     TEXT    NOT NULL,
    cat_name_cn     TEXT,
    cat_color       TEXT,             -- hex color e.g. '#E53935'
    cat_active      INTEGER NOT NULL DEFAULT 1,
    cat_sort_order  INTEGER NOT NULL DEFAULT 0,
    cat_created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);
```

**Seed data**: 8 categories per R08/D102:

| Name (EN) | Name (CN) | Color |
|-----------|----------|-------|
| Supplier Issue | 供应商问题 | #E53935 |
| Internal Process | 内部流程 | #1E88E5 |
| Design Change | 设计变更 | #7B1FA2 |
| Quality Issue | 质量问题 | #F57F17 |
| Material Shortage | 物料短缺 | #D84315 |
| System/Tool | 系统/工具 | #00897B |
| Training | 培训 | #43A047 |
| General | 综合 | #757575 |

---

### 1.6 t_tag

```sql
CREATE TABLE t_tag (
    tag_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_name        TEXT    NOT NULL UNIQUE,
    tag_created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE UNIQUE INDEX uq_tag_name ON t_tag(tag_name);
```

---

## 2. DDL — Core Tables

### 2.1 t_action

```sql
CREATE TABLE t_action (
    act_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    act_ref             TEXT    NOT NULL UNIQUE,  -- ACT-YYYY-NNNNN
    act_title           TEXT    NOT NULL CHECK(length(act_title) BETWEEN 5 AND 200),
    act_desc            TEXT,
    act_status          TEXT    NOT NULL DEFAULT 'Open'
                        CHECK(act_status IN ('Open','In Progress','On Hold','Done','Cancelled')),
    act_priority        TEXT    NOT NULL DEFAULT 'Medium'
                        CHECK(act_priority IN ('Critical','High','Medium','Low')),
    act_team_id         INTEGER NOT NULL DEFAULT 1 REFERENCES t_team(tea_id),  -- DEPRECATED v2.6, hardcoded to 1
    act_team_id         INTEGER NOT NULL REFERENCES t_team(tea_id),  -- PRIMARY org unit since v2.6
    act_topic_id        INTEGER REFERENCES t_topic(top_id),
    act_secondary_topic_id INTEGER REFERENCES t_topic(top_id),
    act_category_id     INTEGER REFERENCES t_category(cat_id),
    act_deadline        TEXT    NOT NULL,  -- YYYY-MM-DD
    act_start_date      TEXT,              -- planned/actual start (YYYY-MM-DD), v2.7
    act_actual_date     TEXT,              -- set on Done
    act_escalation_level TEXT   NOT NULL DEFAULT 'Normal'
                        CHECK(act_escalation_level IN ('Normal','Escalated','WAR')),
    act_escalation_date TEXT,
    act_hold_reason     TEXT,
    act_cancel_reason   TEXT,
    act_postpone_date   TEXT,
    act_last_comment    TEXT,
    act_parent_id       INTEGER REFERENCES t_action(act_id),
    act_source          TEXT    NOT NULL DEFAULT 'Manual'
                        CHECK(act_source IN ('Manual','Import','Meeting')),
    act_source_file     TEXT,
    act_source_ref      TEXT,             -- original row/item # from Excel import
    act_meeting_inst_id INTEGER REFERENCES t_meeting_instance(min_id),  -- link to specific meeting occurrence
    act_created_by      INTEGER NOT NULL REFERENCES t_user(usr_id),
    act_created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    act_updated_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

-- Performance indexes
CREATE UNIQUE INDEX uq_action_ref ON t_action(act_ref);
CREATE INDEX idx_action_status ON t_action(act_status);
CREATE INDEX idx_action_priority ON t_action(act_priority);
CREATE INDEX idx_action_dept ON t_action(act_team_id);
CREATE INDEX idx_action_team ON t_action(act_team_id);
CREATE INDEX idx_action_deadline ON t_action(act_deadline);
CREATE INDEX idx_action_created_by ON t_action(act_created_by);
CREATE INDEX idx_action_parent ON t_action(act_parent_id);
CREATE INDEX idx_action_overdue ON t_action(act_status, act_deadline)
    WHERE act_status NOT IN ('Done','Cancelled');
CREATE INDEX idx_action_source ON t_action(act_source);
```

---

### 2.2 t_action_tag (Junction)

```sql
CREATE TABLE t_action_tag (
    atg_action_id   INTEGER NOT NULL REFERENCES t_action(act_id) ON DELETE CASCADE,
    atg_tag_id      INTEGER NOT NULL REFERENCES t_tag(tag_id) ON DELETE CASCADE,
    PRIMARY KEY (atg_action_id, atg_tag_id)
);

CREATE INDEX idx_action_tag_tag ON t_action_tag(atg_tag_id);
```

---

### 2.3 t_assignment

```sql
CREATE TABLE t_assignment (
    asg_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    asg_action_id   INTEGER NOT NULL REFERENCES t_action(act_id) ON DELETE CASCADE,
    asg_user_id     INTEGER NOT NULL REFERENCES t_user(usr_id),
    asg_role        TEXT    NOT NULL DEFAULT 'assignee',
                    -- Legacy compatibility field for assignment semantics.
                    -- Active responsibility uses t_action.act_owner_id.
                    -- One row per (action, user).
    asg_status      TEXT    NOT NULL DEFAULT 'Assigned'
                    CHECK(asg_status IN ('Assigned','Reassigned')),
                    -- Assignment is active immediately; status is used for tracking reassignment.
    asg_estimated_hours REAL,            -- hours this person is expected to contribute
    asg_assigned_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    asg_assigned_by INTEGER NOT NULL REFERENCES t_user(usr_id),
    UNIQUE(asg_action_id, asg_user_id)  -- D166: one row per user per action
);

CREATE INDEX idx_assignment_action ON t_assignment(asg_action_id);
CREATE INDEX idx_assignment_user ON t_assignment(asg_user_id);
```

---

### 2.4 t_comment (MVP — ActionComment)

```sql
CREATE TABLE t_comment (
    cmt_id          INTEGER PRIMARY KEY AUTOINCREMENT,
        cmt_act_id      INTEGER NOT NULL REFERENCES t_action(act_id) ON DELETE CASCADE,
    cmt_type        TEXT    NOT NULL DEFAULT 'comment'
                    CHECK(cmt_type IN ('comment','achievement','roadblock')),
    cmt_body        TEXT    NOT NULL,  -- HTML sanitized rich text
    cmt_created_by  INTEGER NOT NULL REFERENCES t_user(usr_id),
    cmt_created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    cmt_edited_at   TEXT,              -- set when body is updated
    cmt_edited_by   INTEGER REFERENCES t_user(usr_id),
    cmt_deleted     INTEGER NOT NULL DEFAULT 0  -- soft delete
);

CREATE INDEX idx_comment_action ON t_comment(cmt_act_id);
CREATE INDEX idx_comment_created ON t_comment(cmt_created_at);
CREATE INDEX idx_comment_type   ON t_comment(cmt_type);
```

> **Rights**: Edit / Delete allowed for `Admin`, `TeamLead`, or `cmt_created_by`. Every mutation writes a `t_action_history` row (`CommentEdited` / `CommentDeleted`).

---

## 3. DDL — History & Audit Tables

### 3.1 t_action_history

```sql
CREATE TABLE t_action_history (
    ahi_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ahi_action_id   INTEGER NOT NULL REFERENCES t_action(act_id) ON DELETE CASCADE,
    ahi_field       TEXT    NOT NULL,  -- 'status', 'priority', 'title', etc.
    ahi_old_value   TEXT,
    ahi_new_value   TEXT,
    ahi_reason      TEXT,             -- for status transitions
    ahi_change_type TEXT    NOT NULL DEFAULT 'Updated'
                    CHECK(ahi_change_type IN ('Created','Updated','StatusChange','Reassigned','Closed','CommentAdded','CommentEdited','CommentDeleted')),
    ahi_changed_by  INTEGER NOT NULL REFERENCES t_user(usr_id),
    ahi_changed_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE INDEX idx_history_action ON t_action_history(ahi_action_id);
CREATE INDEX idx_history_changed_at ON t_action_history(ahi_changed_at);
CREATE INDEX idx_history_field ON t_action_history(ahi_field);
```

---

### 3.2 t_audit_log (Backlog, post-V1.1)

```sql
CREATE TABLE t_audit_log (
    aud_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    aud_user_id     INTEGER REFERENCES t_user(usr_id),
    aud_action_type TEXT    NOT NULL,  -- 'LOGIN','LOGOUT','CREATE','UPDATE','DELETE','IMPORT','EXPORT'
    aud_entity      TEXT,             -- 'action','user','team'
    aud_entity_id   INTEGER,
    aud_details     TEXT,             -- JSON blob
    aud_ip_address  TEXT,
    aud_created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE INDEX idx_audit_user ON t_audit_log(aud_user_id);
CREATE INDEX idx_audit_type ON t_audit_log(aud_action_type);
CREATE INDEX idx_audit_created ON t_audit_log(aud_created_at);
```

---

## 4. DDL — Import Tables

### 4.1 t_import_log

```sql
CREATE TABLE t_import_log (
    iml_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    iml_filename        TEXT    NOT NULL,
    iml_version         TEXT    NOT NULL,  -- 'v1','v2','v3','v4'
    iml_total_rows      INTEGER NOT NULL DEFAULT 0,
    iml_imported        INTEGER NOT NULL DEFAULT 0,
    iml_skipped         INTEGER NOT NULL DEFAULT 0,
    iml_duplicates      INTEGER NOT NULL DEFAULT 0,
    iml_warnings        INTEGER NOT NULL DEFAULT 0,
    iml_errors          INTEGER NOT NULL DEFAULT 0,
    iml_warn_details    TEXT,  -- JSON array [{row, field, message}]
    iml_error_details   TEXT,  -- JSON array
    iml_status          TEXT    NOT NULL DEFAULT 'success'
                        CHECK(iml_status IN ('success','partial','failed')),
    iml_imported_by     INTEGER NOT NULL REFERENCES t_user(usr_id),
    iml_imported_at     TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE INDEX idx_import_by ON t_import_log(iml_imported_by);
```

---

## 5. DDL — Meeting Tables

### 5.1 t_meeting_instance (MVP)

```sql
CREATE TABLE t_meeting_instance (
    min_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    min_title       TEXT    NOT NULL,
    min_type        TEXT,   -- free text: "Weekly review", "Kick-off", "Ad-hoc", etc.
    min_date        TEXT    NOT NULL,  -- YYYY-MM-DD
    min_topic_id    INTEGER REFERENCES t_topic(top_id),  -- optional primary category link
    min_secondary_topic_id INTEGER REFERENCES t_topic(top_id),  -- optional secondary category link
    min_created_by  INTEGER NOT NULL REFERENCES t_user(usr_id),
    min_created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);
-- Actions link to a specific meeting instance via act_meeting_inst_id.
-- Meeting type is free text (no enum constraint) to support ad-hoc naming.

CREATE INDEX idx_meeting_inst_date  ON t_meeting_instance(min_date);
CREATE INDEX idx_meeting_inst_topic ON t_meeting_instance(min_topic_id);
CREATE INDEX idx_meeting_inst_secondary_topic ON t_meeting_instance(min_secondary_topic_id);
```

---

### 5.2 t_meeting_summary (V1.1 — file upload)

```sql
CREATE TABLE t_meeting_summary (
    mtg_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mtg_inst_id     INTEGER NOT NULL REFERENCES t_meeting_instance(min_id) ON DELETE CASCADE,
    mtg_file        TEXT    NOT NULL,   -- path to uploaded .xlsx
    mtg_uploaded_by INTEGER NOT NULL REFERENCES t_user(usr_id),
    mtg_upload_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE INDEX idx_meeting_sum_inst ON t_meeting_summary(mtg_inst_id);
```

---

## 6. DDL — Notification Table

### 6.1 t_notification

```sql
CREATE TABLE t_notification (
    ntf_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ntf_user_id    INTEGER NOT NULL REFERENCES t_user(usr_id),
    ntf_event_type TEXT    NOT NULL,
    ntf_title      TEXT    NOT NULL,
    ntf_body       TEXT,
    ntf_action_id  INTEGER REFERENCES t_action(act_id),
    ntf_is_read    INTEGER NOT NULL DEFAULT 0,
    ntf_created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notif_user ON t_notification(ntf_user_id);
CREATE INDEX idx_notif_read ON t_notification(ntf_user_id, ntf_is_read);
CREATE INDEX idx_notif_action ON t_notification(ntf_action_id);
```

---

## 7. DDL — Workflow Tables (V2 — D167–D180)

> **Design-time**: 1 table with JSON graph (O3). **Runtime**: 5 normalized tables.  
> See R16 §5 for full rationale and JSON schema.

### 7.1 t_workflow_template (Design-Time)

```sql
CREATE TABLE t_workflow_template (
    wft_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    wft_name_en     TEXT    NOT NULL,
    wft_name_cn     TEXT,
    wft_desc        TEXT,
    wft_version     INTEGER NOT NULL DEFAULT 1,
    wft_is_default  INTEGER NOT NULL DEFAULT 0,  -- "Simple Action" default template
    wft_type        TEXT    NOT NULL DEFAULT 'action'
                    CHECK(wft_type IN ('action', 'request')),  -- D167: action-bound or standalone
    wft_active      INTEGER NOT NULL DEFAULT 1,
    wft_graph       TEXT    NOT NULL DEFAULT '{}',  -- O3/D176: JSON graph of steps, transitions, triggers, fields
    wft_created_by  INTEGER NOT NULL REFERENCES t_user(usr_id),
    wft_created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    wft_updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE INDEX idx_wft_type ON t_workflow_template(wft_type);
CREATE INDEX idx_wft_active ON t_workflow_template(wft_active);
```

---

### 7.2 t_workflow_instance (Runtime)

```sql
CREATE TABLE t_workflow_instance (
    wfi_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    wfi_template_id INTEGER NOT NULL REFERENCES t_workflow_template(wft_id),
    wfi_action_id   INTEGER UNIQUE REFERENCES t_action(act_id) ON DELETE CASCADE,
                    -- Optional supporting action for compatibility/runtime integration; request workflows may keep this null
    wfi_status      TEXT    NOT NULL DEFAULT 'Active'
                    CHECK(wfi_status IN ('Active', 'Completed', 'Cancelled', 'Paused', 'WaitingForChild')),
    wfi_parent_step_id INTEGER REFERENCES t_workflow_step_instance(wsi_id),
    wfi_started_by  INTEGER REFERENCES t_user(usr_id),
    wfi_started_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    wfi_completed_at TEXT,
    wfi_outcome     TEXT
);

CREATE UNIQUE INDEX uq_wfi_action ON t_workflow_instance(wfi_action_id);
CREATE INDEX idx_wfi_template ON t_workflow_instance(wfi_template_id);
CREATE INDEX idx_wfi_status ON t_workflow_instance(wfi_status);
CREATE INDEX idx_wfi_parent_step ON t_workflow_instance(wfi_parent_step_id);
```

---

### 7.3 t_workflow_step_instance (Runtime)

```sql
CREATE TABLE t_workflow_step_instance (
    wsi_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    wsi_instance_id INTEGER NOT NULL REFERENCES t_workflow_instance(wfi_id) ON DELETE CASCADE,
    wsi_step_key    TEXT    NOT NULL,  -- key into wft_graph.steps (e.g., "hse_validation")
    wsi_status      TEXT    NOT NULL DEFAULT 'Pending'
                    CHECK(wsi_status IN ('Pending', 'Accepted', 'Completed', 'Skipped', 'Rejected', 'Paused', 'WaitingForChild')),
    wsi_assignee_id INTEGER REFERENCES t_user(usr_id),
    wsi_entered_at  TEXT,
    wsi_accepted_at TEXT,
    wsi_completed_at TEXT,
    wsi_sla_deadline TEXT,  -- computed: wsi_entered_at + step.sla_hours
    wsi_comment     TEXT,
    wsi_escalated_at TEXT,
    wsi_child_instance_id INTEGER REFERENCES t_workflow_instance(wfi_id),
    wsi_child_outcome TEXT
);

CREATE INDEX idx_wsi_instance ON t_workflow_step_instance(wsi_instance_id);
CREATE INDEX idx_wsi_status ON t_workflow_step_instance(wsi_status);
CREATE INDEX idx_wsi_assignee ON t_workflow_step_instance(wsi_assignee_id);
CREATE INDEX idx_wsi_child_instance ON t_workflow_step_instance(wsi_child_instance_id);
CREATE INDEX idx_wsi_sla ON t_workflow_step_instance(wsi_sla_deadline)
    WHERE wsi_status IN ('Pending', 'Accepted');
```

---

### 7.4 t_workflow_step_field_value (Runtime Form Data)

```sql
CREATE TABLE t_workflow_step_field_value (
    sfv_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sfv_step_inst_id INTEGER NOT NULL REFERENCES t_workflow_step_instance(wsi_id) ON DELETE CASCADE,
    sfv_field_key    TEXT    NOT NULL,  -- key into wft_graph.steps[].fields (e.g., "badge_code")
    sfv_value        TEXT,              -- stored as text; JSON for checklist values
    sfv_filled_by    INTEGER REFERENCES t_user(usr_id),
    sfv_filled_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE INDEX idx_sfv_step_inst ON t_workflow_step_field_value(sfv_step_inst_id);
CREATE UNIQUE INDEX uq_sfv_step_field ON t_workflow_step_field_value(sfv_step_inst_id, sfv_field_key);
```

---

### 7.4A t_workflow_step_attachment (Runtime Attachment Data)

```sql
CREATE TABLE t_workflow_step_attachment (
    wsa_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    wsa_step_inst_id  INTEGER NOT NULL REFERENCES t_workflow_step_instance(wsi_id) ON DELETE CASCADE,
    wsa_action_id     INTEGER NOT NULL REFERENCES t_action(act_id) ON DELETE CASCADE,
    wsa_filename      TEXT    NOT NULL,
    wsa_storage_path  TEXT    NOT NULL UNIQUE,
    wsa_mime_type     TEXT    NOT NULL,
    wsa_size_bytes    INTEGER NOT NULL CHECK(wsa_size_bytes >= 0),
    wsa_description   TEXT,
    wsa_uploaded_by   INTEGER NOT NULL REFERENCES t_user(usr_id),
    wsa_uploaded_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    wsa_deleted_at    TEXT
);

CREATE INDEX idx_wsa_step_inst ON t_workflow_step_attachment(wsa_step_inst_id);
CREATE INDEX idx_wsa_action ON t_workflow_step_attachment(wsa_action_id);
CREATE INDEX idx_wsa_uploaded_by ON t_workflow_step_attachment(wsa_uploaded_by);
CREATE INDEX idx_wsa_active ON t_workflow_step_attachment(wsa_deleted_at)
    WHERE wsa_deleted_at IS NULL;
```

---

### 7.5 t_workflow_approval (V2.1)

```sql
CREATE TABLE t_workflow_approval (
    wap_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    wap_step_inst_id INTEGER NOT NULL REFERENCES t_workflow_step_instance(wsi_id) ON DELETE CASCADE,
    wap_approver_id  INTEGER NOT NULL REFERENCES t_user(usr_id),
    wap_decision     TEXT    NOT NULL CHECK(wap_decision IN ('Approved', 'Rejected', 'Abstained')),
    wap_comment      TEXT,
    wap_decided_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE INDEX idx_wap_step ON t_workflow_approval(wap_step_inst_id);
CREATE INDEX idx_wap_approver ON t_workflow_approval(wap_approver_id);
```

---

### 7.6 Changes to t_action (V2)

```sql
-- Add 'WorkflowRequest' to act_source CHECK constraint
-- (applied via ALTER TABLE or migration script)
ALTER TABLE t_action ADD COLUMN act_source TEXT NOT NULL DEFAULT 'Manual'
    CHECK(act_source IN ('Manual', 'Import', 'Meeting', 'WorkflowRequest'));
-- Note: SQLite cannot modify CHECK constraints in-place.
-- Migration strategy: recreate table or use app-layer validation.
```

### 7.7 Changes to t_action_history (V2)

```sql
-- Add workflow change types to ahi_change_type CHECK
-- New values: 'WorkflowAdvance', 'ApprovalDecision'
```

---

## 8. Views

### 8.1 v_action_detail

```sql
CREATE VIEW v_action_detail AS
SELECT
    a.act_id,
    a.act_ref,
    a.act_title,
    a.act_desc,
    a.act_status,
    a.act_priority,
    a.act_deadline,
    a.act_actual_date,
    a.act_escalation_level,
    a.act_last_comment,
    a.act_source,
    a.act_created_at,
    a.act_updated_at,
    -- Team
    d.tea_id,
    d.tea_name_en AS dept_name_en,
    d.tea_name_cn AS dept_name_cn,
    -- Team
    t.tea_id,
    t.tea_name_en AS team_name_en,
    t.tea_name_cn AS team_name_cn,
    -- Topic
    tp.top_name_en AS topic_name_en,
    tp.top_name_cn AS topic_name_cn,
    -- Category
    c.cat_name_en AS category_name_en,
    c.cat_name_cn AS category_name_cn,
    -- Creator
    u.usr_display_name AS created_by_name,
    -- Lead (subquery)
    (SELECT lu.usr_display_name
     FROM t_assignment la
     JOIN t_user lu ON la.asg_user_id = lu.usr_id
     WHERE la.asg_action_id = a.act_id AND la.asg_role = 'Lead'
     LIMIT 1) AS lead_name,
    -- Overdue flag
    CASE
        WHEN a.act_status NOT IN ('Done','Cancelled')
             AND a.act_deadline < date('now')
        THEN 1 ELSE 0
    END AS is_overdue
FROM t_action a
LEFT JOIN t_team d ON a.act_team_id = d.tea_id
LEFT JOIN t_team t ON a.act_team_id = t.tea_id
LEFT JOIN t_topic tp ON a.act_topic_id = tp.top_id
LEFT JOIN t_category c ON a.act_category_id = c.cat_id
LEFT JOIN t_user u ON a.act_created_by = u.usr_id;
```

### 8.2 v_overdue_actions

```sql
CREATE VIEW v_overdue_actions AS
SELECT *
FROM v_action_detail
WHERE is_overdue = 1
ORDER BY act_deadline ASC;
```

### 8.3 v_user_workload

```sql
CREATE VIEW v_user_workload AS
SELECT
    u.usr_id,
    u.usr_display_name,
    u.usr_team_id,
    COUNT(DISTINCT a.act_id) AS total_assigned,
    SUM(CASE WHEN a.act_status NOT IN ('Done','Cancelled') AND a.act_deadline < date('now') THEN 1 ELSE 0 END) AS overdue_count,
    SUM(CASE WHEN a.act_status = 'Done' THEN 1 ELSE 0 END) AS completed_count,
    ROUND(
        CAST(SUM(CASE WHEN a.act_status = 'Done' THEN 1 ELSE 0 END) AS REAL) /
        NULLIF(COUNT(DISTINCT a.act_id), 0),
        2
    ) AS completion_rate
FROM t_user u
LEFT JOIN t_assignment asg ON u.usr_id = asg.asg_user_id
LEFT JOIN t_action a ON asg.asg_action_id = a.act_id
WHERE u.usr_active = 1
GROUP BY u.usr_id;
```

---

## 9. Triggers

### 9.1 Auto-update timestamps

```sql
CREATE TRIGGER trg_action_updated AFTER UPDATE ON t_action
BEGIN
    UPDATE t_action SET act_updated_at = strftime('%Y-%m-%dT%H:%M:%S','now')
    WHERE act_id = NEW.act_id;
END;

CREATE TRIGGER trg_user_updated AFTER UPDATE ON t_user
BEGIN
    UPDATE t_user SET usr_updated_at = strftime('%Y-%m-%dT%H:%M:%S','now')
    WHERE usr_id = NEW.usr_id;
END;

CREATE TRIGGER trg_team_updated AFTER UPDATE ON t_team
BEGIN
    UPDATE t_team SET dep_updated_at = strftime('%Y-%m-%dT%H:%M:%S','now')
    WHERE tea_id = NEW.tea_id;
END;

CREATE TRIGGER trg_team_updated AFTER UPDATE ON t_team
BEGIN
    UPDATE t_team SET tea_updated_at = strftime('%Y-%m-%dT%H:%M:%S','now')
    WHERE tea_id = NEW.tea_id;
END;
```

### 9.2 Auto-set actual_date on Done

```sql
CREATE TRIGGER trg_action_done AFTER UPDATE OF act_status ON t_action
WHEN NEW.act_status = 'Done' AND OLD.act_status != 'Done'
BEGIN
    UPDATE t_action SET act_actual_date = date('now')
    WHERE act_id = NEW.act_id;
END;
```

---

## 10. Constraint Summary

| Constraint | Table | Type | Rule |
|------------|-------|------|------|
| One Lead per action | t_assignment | App-level | Enforced in OP06 logic |
| Comment action linkage | t_comment | App-level | Each comment must belong to one action via cmt_act_id |
| Username unique | t_user | DB-level | UNIQUE index |
| Action ref unique | t_action | DB-level | UNIQUE index |
| Tag name unique | t_tag | DB-level | UNIQUE index |
| Assignment unique | t_assignment | DB-level | UNIQUE(action, user) |
| Valid status enum | t_action | DB-level | CHECK constraint |
| Valid priority enum | t_action | DB-level | CHECK constraint |
| Valid role enum | t_user / t_assignment | DB-level | CHECK constraint |
| Comment type enum | t_comment | DB-level | CHECK constraint (comment/achievement/roadblock) |
| Referential integrity | All FKs | DB-level | REFERENCES + ON DELETE CASCADE where appropriate |
| Workflow instance unique per linked action | t_workflow_instance | DB-level | UNIQUE(wfi_action_id) when non-null |
| Workflow field value unique per step+field | t_workflow_step_field_value | DB-level | UNIQUE(sfv_step_inst_id, sfv_field_key) |
| Workflow step attachment storage path unique | t_workflow_step_attachment | DB-level | UNIQUE(wsa_storage_path) |
| Workflow template type enum | t_workflow_template | DB-level | CHECK(wft_type IN ('action', 'request')) |
| Workflow instance status enum | t_workflow_instance | DB-level | CHECK(wfi_status IN (...)) |
| Workflow step status enum | t_workflow_step_instance | DB-level | CHECK(wsi_status IN (...)) |
| Workflow attachment file size valid | t_workflow_step_attachment | DB-level | CHECK(wsa_size_bytes >= 0) |
| Approval decision enum | t_workflow_approval | DB-level | CHECK(wap_decision IN (...)) |
| Parallel join atomicity | t_workflow_step_instance | App-level | `BEGIN IMMEDIATE` before join check (D179) |

---

## 10. SQLite-Specific Configuration

```sql
-- Enable at connection time (every flask request)
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
PRAGMA cache_size = -8000;  -- 8MB
PRAGMA synchronous = NORMAL;
```

---

## 11. Entity → Table Mapping

| MCD Entity | Table | Phase |
| Action | t_action | MVP |
| ActionComment | t_comment | MVP |
| User | t_user | MVP |
| Team | t_team | MVP |
| Team | t_team | MVP |
| Assignment | t_assignment | MVP |
| Category (global) | t_topic | MVP |
| Category | t_category | MVP |
| Tag | t_tag | MVP |
| ActionTag | t_action_tag | MVP |
| ActionHistory | t_action_history | MVP |
| ImportLog | t_import_log | MVP |
| MeetingInstance | t_meeting_instance | MVP |
| MeetingSummary | t_meeting_summary | MVP |
| ImportLog | t_import_log | MVP |
| Meeting | t_meeting | V1.1 |
| AuditLog | t_audit_log | Backlog (post-V1.1) |
| Notification | t_notification | V1.1 |
| WorkflowTemplate | t_workflow_template | V2.0 |
| WorkflowInstance | t_workflow_instance | V2.0 |
| WorkflowStepInstance | t_workflow_step_instance | V2.0 |
| WorkflowStepFieldValue | t_workflow_step_field_value | V2.0 |
| WorkflowStepAttachment | t_workflow_step_attachment | V3 planned |
| WorkflowApproval | t_workflow_approval | V2.1 |
