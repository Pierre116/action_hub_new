# ActionHub — Semantic Layer

> **Level**: L4 — Physical  
> **Merise Phase**: Couche Sémantique  
> **Source**: S05_data_dictionary.md (fields), S20_MLD.md (tables), R05_kpi_reporting.md  
> **Purpose**: Map technical schema to business language — entity meanings, field synonyms, KPI definitions, query patterns

---

## 1. Entity Business Mappings

| Technical Entity | Business Name (EN) | Business Name (CN) | Description |
|-----------------|-------------------|-------------------|-------------|
| `t_action` | Action Item | 行动项 | A tracked task requiring follow-up, from creation to completion |
| `t_user` | User / Team Member | 用户 / 团队成员 | A person with access to ActionHub |
| `t_team` | Team | 部门 | An organizational unit within the company |
| `t_assignment` | Assignment | 分配 | The link between a user and an action for explicit visibility/workload assignment |
| `t_assignment_history` | Assignment History | 分配历史 | A record of assignment/reassignment events for traceability |
| `t_topic` | Category | 类别 | A global subject matter area managed by Admin/TeamLead |
| `t_comment` | Comment / Update | 评论 / 更新 | A typed annotation on an action (Comment, Achievement, Roadblock) |
| `t_category` | Category | 类别 | A cross-cutting classification (Safety, Quality, etc.) |
| `t_tag` | Tag | 标签 | A free-form label for grouping actions |
| `t_action_tag` | Action-Tag Link | 行动-标签关联 | A many-to-many relation linking actions and tags |
| `t_action_history` | Activity Log | 活动日志 | A timestamped record of changes to an action |
| `t_action_feedback` | Action Feedback | 行动反馈 | Structured feedback records tied to actions/meetings |
| `t_import_log` | Import Record | 导入记录 | A summary of a batch Excel import |
| `t_meeting_instance` | Meeting Instance | 会议实例 | A specific meeting occurrence linked to actions (MVP) |
| `t_meeting_memo` | Meeting Memo | 会议记录 | Rich-text memo entries for a meeting instance |
| `t_meeting_summary` | Meeting Summary | 会议纪要 | An uploaded summary file for a meeting instance (V1.1) |
| `t_meeting_owner` | Meeting Owner | 会议所有者 | Users granted owner-level access to a meeting instance |
| `t_meeting_participant` | Meeting Participant | 会议参与者 | Users participating in a meeting instance |
| `t_meeting_decision` | Meeting Decision | 会议决策 | Decision records captured during meetings |
| `t_audit_log` | Audit Trail | 审计追踪 | A security-oriented log of all user operations (Backlog, post-V1.1) |
| `t_notification` | Notification | 通知 | An individual notification sent to a user |

---

## 2. Field Business Synonyms

### 2.1 Action Fields

| Technical Field | Business Label (EN) | Business Label (CN) | Synonyms |
|----------------|--------------------|--------------------|----------|
| `act_ref` | Reference Number | 编号 | Action ID, Ref, Number |
| `act_title` | Title | 标题 | Name, Subject, Action Description |
| `act_desc` | Description | 描述 | Details, Notes, Context |
| `act_status` | Status | 状态 | State, Progress |
| `act_priority` | Priority | 优先级 | Urgency, Importance |
| `act_deadline` | Deadline | 截止日期 | Due Date, Target Date |
| `act_actual_date` | Completion Date | 完成日期 | Closed Date, Done Date |
| `act_escalation_level` | Escalation Level | 升级级别 | Alert Level |
| `act_last_comment` | Latest Update | 最新更新 | Comment, Progress Note |
| `act_source` | Source | 来源 | Origin, Created From |
| `act_hold_reason` | Hold Reason | 暂停原因 | Why paused |
| `act_cancel_reason` | Cancellation Reason | 取消原因 | Why cancelled |
| `act_meeting_inst_id` | Meeting Instance | 会议实例 | Linked meeting occurrence |
| `act_topic_id` | Category | 类别 | Subject area grouping |
| `act_secondary_topic_id` | Category 2 | 第二类别 | Optional second subject area grouping |

### 2.5 Comment Fields

| Technical Field | Business Label (EN) | Business Label (CN) | Synonyms |
|----------------|--------------------|--------------------|----------|
| `cmt_type` | Comment Type | 评论类型 | Category (Comment / Achievement / Roadblock) |
| `cmt_body` | Content | 内容 | Text, Rich Text Body |
| `cmt_created_by` | Author | 作者 | Posted By |
| `cmt_created_at` | Posted At | 发布时间 | Timestamp |
| `cmt_edited_at` | Last Edited | 最后编辑 | Modified At |
| `cmt_is_deleted` | Deleted | 已删除 | Soft-removed |

### 2.2 Status Values

| Technical Value | Business Meaning (EN) | Business Meaning (CN) | Color |
|----------------|----------------------|----------------------|-------|
| `Open` | Not yet started | 未开始 | Blue |
| `In Progress` | Work underway | 进行中 | Orange |
| `On Hold` | Temporarily paused | 暂停 | Purple |
| `Done` | Completed successfully | 已完成 | Green |
| `Cancelled` | No longer needed | 已取消 | Brown |

### 2.3 Priority Values

| Technical Value | Business Meaning (EN) | Business Meaning (CN) | SLA (D30) |
|----------------|----------------------|----------------------|-----------|
| `Critical` | Must be resolved immediately | 紧急 | ≤3 days |
| `High` | Needs attention this week | 高 | ≤7 days |
| `Medium` | Normal priority | 中 | ≤14 days |
| `Low` | Address when possible | 低 | ≤30 days |

---

## 3. KPI Definitions

### 3.1 Individual KPIs

| KPI ID | Name (EN) | Name (CN) | Formula | Unit |
|--------|----------|----------|---------|------|
| K01 | Completion Rate | 完成率 | `COUNT(status='Done') / COUNT(status NOT IN ('Cancelled')) × 100` | % |
| K02 | Overdue Count | 逾期数量 | `COUNT(deadline < today AND status NOT IN ('Done','Cancelled'))` | # |
| K03 | On-Time Rate | 准时率 | `COUNT(actual_date <= deadline) / COUNT(status='Done') × 100` | % |
| K04 | Average Resolution Time | 平均解决时间 | `AVG(actual_date - created_at)` for Done actions | days |
| K05 | Actions Due This Week | 本周到期 | `COUNT(deadline BETWEEN today AND today+7 AND status NOT IN ('Done','Cancelled'))` | # |
| K06 | Completed This Month | 本月完成 | `COUNT(actual_date IN current_month AND status='Done')` | # |
| K07 | Overdue Rate | 逾期率 | `K02 / COUNT(status NOT IN ('Done','Cancelled')) × 100` | % |

### 3.2 Team KPIs

| KPI ID | Name (EN) | Name (CN) | Formula | Granularity |
|--------|----------|----------|---------|-------------|
| K10 | Team Completion Rate | 部门完成率 | `COUNT(dept_done) / COUNT(dept_non_cancelled) × 100` | Per team |
| K11 | Team Overdue Count | 部门逾期数 | Overdue actions in team | Per team |
| K12 | Team On-Time Rate | 部门准时率 | On-time completions in team | Per team |
| K13 | Team Avg Resolution | 部门平均解决时间 | Avg time for dept actions | Per team |
| K14 | Top Contributors | 优秀贡献者 | Top 5 users by completed actions | Per team |
| K15 | Overdue by Team | 各团队逾期 | Overdue grouped by team | Per dept × team |
| K16 | Backlog per Team | 部门积压 | `COUNT(status IN ('Open','In Progress'))` by dept | Per team |

### 3.3 Global KPIs (Admin)

| KPI ID | Name (EN) | Name (CN) | Formula |
|--------|----------|----------|---------|
| K20 | Total Actions | 总行动数 | `COUNT(*)` in t_action |
| K21 | Total Users | 用户总数 | `COUNT(active=1)` in t_user |
| K22 | Active Teams | 活跃部门 | Teams with actions in last 30 days |
| K23 | Global Completion Rate | 全局完成率 | All actions completion rate |
| K24 | Global Overdue | 全局逾期数 | All overdue actions |

### 3.4 Workload KPIs (R05 §7.2)

| KPI ID | Name (EN) | Name (CN) | Formula | Unit |
|--------|----------|----------|---------|------|
| K30 | Actions per User | 每用户行动数 | Active owner/explicit-assignment records per user | # |
| K31 | New Actions per Period | 新增行动 | `COUNT(created_at IN period)` | #/period |
| K32 | Closed per Period | 关闭行动 | `COUNT(actual_date IN period)` | #/period |
| K33 | Net Change | 净变化 | `K31 - K32` | #/period |

### 3.6 Category Dashboard KPIs

| KPI ID | Name (EN) | Name (CN) | Formula | Unit |
|--------|----------|----------|---------|------|
| K50 | Category Open Count | 类别开放数 | `COUNT(act_status NOT IN ('Done','Cancelled'))` WHERE `(act_topic_id = :category_id OR act_secondary_topic_id = :category_id)` | # |
| K51 | Category Overdue Count | 类别逾期数 | `COUNT(act_deadline < today AND act_status NOT IN ('Done','Cancelled'))` by category across both category links | # |
| K52 | Category Done Count | 类别完成数 | `COUNT(act_status = 'Done')` by category across both category links | # |
| K53 | Category On-Time Rate | 类别准时率 | `COUNT(actual_date <= deadline AND status='Done') / COUNT(status='Done') × 100` by category across both category links | % |
| K54 | Category Workload | 类别工作量 | `COUNT(status NOT IN ('Done','Cancelled'))` per assignee for a category across both category links | #/user |

### 3.6 Assignment KPIs

| KPI ID | Name (EN) | Name (CN) | Formula | Unit |
|--------|----------|----------|---------|------|
| K40 | Assigned Users | 已分配人数 | `COUNT(DISTINCT asg_user_id)` per action | # |
| K42 | Reassignment Rate | 重新分配率 | `COUNT(Reassigned) / COUNT(Assigned) × 100` | % |

---

## 4. Query Patterns

### 4.1 Overdue Actions

```sql
-- "Show me all overdue actions"
SELECT * FROM v_overdue_actions;

-- "Show overdue actions for Production team"
SELECT * FROM v_overdue_actions
WHERE tea_id = (SELECT tea_id FROM t_team WHERE tea_code = 'PROD');
```

**Business Translation**: "Actions past their deadline that haven't been completed or cancelled"

### 4.2 Personal Dashboard

```sql
-- K01: Completion Rate
SELECT
    ROUND(
        CAST(SUM(CASE WHEN a.act_status = 'Done' THEN 1 ELSE 0 END) AS REAL) /
        NULLIF(COUNT(*), 0) * 100, 1
    ) AS completion_rate
FROM t_assignment asg
JOIN t_action a ON asg.asg_action_id = a.act_id
WHERE asg.asg_user_id = :user_id;

-- K02: My Overdue Count
SELECT COUNT(*) AS overdue_count
FROM t_assignment asg
JOIN t_action a ON asg.asg_action_id = a.act_id
WHERE asg.asg_user_id = :user_id
  AND a.act_status NOT IN ('Done', 'Cancelled')
  AND a.act_deadline < date('now');

-- K05: Due This Week
SELECT COUNT(*) AS due_this_week
FROM t_assignment asg
JOIN t_action a ON asg.asg_action_id = a.act_id
WHERE asg.asg_user_id = :user_id
  AND a.act_status NOT IN ('Done', 'Cancelled')
  AND a.act_deadline BETWEEN date('now') AND date('now', '+7 days');
```

### 4.3 Team Dashboard

```sql
-- K10: Team Completion Rate
SELECT
    d.tea_name_en,
    COUNT(*) AS total,
    SUM(CASE WHEN a.act_status = 'Done' THEN 1 ELSE 0 END) AS done,
    ROUND(
        CAST(SUM(CASE WHEN a.act_status = 'Done' THEN 1 ELSE 0 END) AS REAL) /
        NULLIF(COUNT(*), 0) * 100, 1
    ) AS completion_rate
FROM t_action a
JOIN t_team d ON a.act_team_id = d.tea_id
WHERE d.tea_id = :dept_id
GROUP BY d.tea_id;

-- K15: Overdue by Team
SELECT
    t.tea_name_en AS team_name,
    COUNT(*) AS overdue_count
FROM t_action a
JOIN t_team t ON a.act_team_id = t.tea_id
WHERE a.act_team_id = :dept_id
  AND a.act_status NOT IN ('Done', 'Cancelled')
  AND a.act_deadline < date('now')
GROUP BY a.act_team_id
ORDER BY overdue_count DESC;
```

### 4.4 Action Search

```sql
-- Full-text search on title + description
SELECT * FROM v_action_detail
WHERE (act_title LIKE '%' || :search || '%'
    OR act_desc LIKE '%' || :search || '%')
  AND (:status IS NULL OR act_status = :status)
  AND (:dept_id IS NULL OR tea_id = :dept_id)
  AND (:priority IS NULL OR act_priority = :priority)
ORDER BY
    CASE WHEN :sort = 'deadline_asc' THEN act_deadline END ASC,
    CASE WHEN :sort = 'deadline_desc' THEN act_deadline END DESC,
    CASE WHEN :sort = 'created_desc' THEN act_created_at END DESC,
    CASE WHEN :sort = 'priority_desc' THEN 
        CASE act_priority 
            WHEN 'Critical' THEN 4
            WHEN 'High' THEN 3
            WHEN 'Medium' THEN 2
            WHEN 'Low' THEN 1
        END 
    END DESC
LIMIT :per_page OFFSET (:page - 1) * :per_page;
```

### 4.5 Import Analysis

```sql
-- "How many actions were imported vs manually created?"
SELECT
    act_source,
    COUNT(*) AS count,
    ROUND(CAST(COUNT(*) AS REAL) / (SELECT COUNT(*) FROM t_action) * 100, 1) AS pct
FROM t_action
GROUP BY act_source;

-- "Import success rate"
SELECT
    iml_filename,
    iml_total_rows,
    iml_imported,
    iml_skipped,
    ROUND(CAST(iml_imported AS REAL) / NULLIF(iml_total_rows, 0) * 100, 1) AS success_rate
FROM t_import_log
ORDER BY iml_imported_at DESC;
```

---

## 5. Business Rule → Query Mapping

| Business Rule | Rule ID | Query Implementation |
|--------------|---------|---------------------|
| One Lead per action | BR10 | `SELECT COUNT(*) FROM t_assignment WHERE asg_action_id = ? AND INSTR(',' \|\| asg_role \|\| ',', ',Lead,') > 0` → must be ≤ 1 (D166: `asg_role` may contain comma-separated roles, e.g. `'Lead,Delegate'`) |
| Valid status transition | BR01 | Python dict `VALID_TRANSITIONS[current]` checked before UPDATE |
| Overdue = missed deadline | BR04 | `act_deadline < date('now') AND act_status NOT IN ('Done','Cancelled')` |
| Auto-set actual_date | BR03 | Trigger `trg_action_done` on status → Done |
| Duplicate detection (import) | BR24 | `SELECT act_id FROM t_action WHERE act_title = :title AND act_team_id = :dept_id` |
| Lockout after 5 failures | — | `usr_failed_logins >= 5 AND usr_locked_until > datetime('now')` |

---

## 6. Reporting Dimensions

| Dimension | Source Table | Fields | Usage |
|-----------|-------------|--------|-------|
| Time | t_action | act_created_at, act_deadline, act_actual_date | Trend analysis, due date grouping |
| Team | t_team | tea_name_en, tea_name_cn, tea_code | Team-level KPIs |
| Status | t_action | act_status | Status distribution |
| Priority | t_action | act_priority | Priority distribution |
| Source | t_action | act_source | Manual vs Import vs Meeting |
| User | t_user via t_assignment | usr_display_name | Individual performance |
| Category | t_category | cat_name_en | Cross-cutting analysis |
| Category | t_topic | top_name_en | Subject area analysis (global) |
| Meeting Instance | t_meeting_instance | min_date, min_title | Meeting-linked actions |
| Comment Type | t_comment | cmt_type | Comment / Achievement / Roadblock distribution |
| Gantt Timeline | t_action | act_deadline, act_created_at | Timeline/Gantt view |

---

## 7. Chart Specifications (R05 §9, D75)

> **Note**: MVP uses KPI cards + colored badges only. Charts are introduced in V1.1 (Team Dashboard) and V1.2 (Trends).

| Chart ID | Name | Type | X-Axis | Y-Axis | Scope | Library |
|----------|------|------|--------|--------|-------|---------|
| CH01 | Status Distribution | Stacked Bar | Status | Count | Team / Team | Chart.js |
| CH02 | Workload Distribution | Horizontal Bar | User | Action count (sorted desc) | Team | Chart.js |
| CH03 | Completion Trend | Line | Week | Completed count | Team (12-week rolling) | Chart.js |
| CH04 | Created vs Completed | Dual-axis Line | Month | Count (new / closed) | Team (6-month) | Chart.js |
| CH05 | Priority Breakdown | Donut | Priority | Count | Team / Personal | Chart.js |
| CH06 | Team Heatmap | Matrix | Team | Status | Management (intensity = count) | Chart.js + plugin |
| CH07 | Overdue Trend | Area | Month | Overdue count | Management (red gradient) | Chart.js |
| CH08 | Gantt Timeline | Horizontal Bar | Action | Start→Deadline span | All users, filterable by dept/category/person | Chart.js / CSS |
| CH09 | Category KPI Cards | KPI Cards | Category | Open / Overdue / Done / On-Time / Workload | Category Dashboard | Bootstrap cards |

### Chart Color Palette

| Series | Color | Usage |
|--------|-------|-------|
| Open | `#1E88E5` (Blue) | Status charts |
| In Progress | `#FB8C00` (Orange) | Status charts |
| On Hold | `#8E24AA` (Purple) | Status charts |
| Done | `#43A047` (Green) | Status charts |
| Cancelled | `#757575` (Grey) | Status charts |
| Critical | `#D32F2F` (Red) | Priority charts |
| High | `#F57C00` (Orange) | Priority charts |
| Medium | `#FBC02D` (Yellow) | Priority charts |
| Low | `#388E3C` (Green) | Priority charts |

---

## 8. Data Quality Rules

| Rule | Check | Implementation |
|------|-------|---------------|
| No orphan assignments | Every assignment→action exists | FK constraint |
| No orphan teams | Every team→team exists | FK constraint |
| Consistent status dates | Done actions have actual_date | Trigger `trg_action_done` |
| Unique references | No duplicate ACT-YYYY-NNNNN | UNIQUE index on act_ref |
| Valid enums | Status/Priority in allowed values | CHECK constraints |
| Non-empty titles | Titles are 5-200 chars | CHECK constraint on act_title |
| Future deadlines (create) | New action deadline ≥ today | Application-level validation |
