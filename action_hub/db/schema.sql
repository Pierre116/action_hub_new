PRAGMA foreign_keys = ON;

-- Workflow engine core tables (added for WF-19, S72)
CREATE TABLE IF NOT EXISTS t_workflow_template (
    wft_id INTEGER PRIMARY KEY AUTOINCREMENT,
    wft_name_en TEXT NOT NULL,
    wft_name_cn TEXT,
    wft_desc TEXT,
    wft_version INTEGER NOT NULL DEFAULT 1,
    wft_is_default INTEGER NOT NULL DEFAULT 0,
    wft_type TEXT NOT NULL DEFAULT 'action' CHECK(wft_type IN ('action', 'request')),
    wft_active INTEGER NOT NULL DEFAULT 1,
    wft_graph TEXT NOT NULL DEFAULT '{}',
    wft_created_by INTEGER NOT NULL,
    wft_created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    wft_updated_at TEXT,
    FOREIGN KEY (wft_created_by) REFERENCES t_user(usr_id)
);

CREATE TABLE IF NOT EXISTS t_workflow_instance (
    wfi_id INTEGER PRIMARY KEY AUTOINCREMENT,
    wfi_template_id INTEGER NOT NULL,
    wfi_action_id INTEGER,
    wfi_status TEXT NOT NULL DEFAULT 'Active',
    wfi_started_by INTEGER,
    wfi_started_at TEXT,
    wfi_completed_at TEXT,
    wfi_outcome TEXT,
    wfi_parent_step_id INTEGER,
    wfi_created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    wfi_updated_at TEXT,
    FOREIGN KEY (wfi_template_id) REFERENCES t_workflow_template(wft_id),
    FOREIGN KEY (wfi_action_id) REFERENCES t_action(act_id),
    FOREIGN KEY (wfi_started_by) REFERENCES t_user(usr_id),
    FOREIGN KEY (wfi_parent_step_id) REFERENCES t_workflow_step_instance(wsi_id)
);

CREATE TABLE IF NOT EXISTS t_workflow_step_instance (
    wsi_id INTEGER PRIMARY KEY AUTOINCREMENT,
    wsi_instance_id INTEGER NOT NULL,
    wsi_step_key TEXT NOT NULL,
    wsi_status TEXT NOT NULL DEFAULT 'Open',
    wsi_assignee_id INTEGER,
    wsi_entered_at TEXT,
    wsi_completed_at TEXT,
    wsi_comment TEXT,
    wsi_sla_deadline TEXT,
    wsi_delegated_from_id INTEGER,
    wsi_child_instance_id INTEGER,
    wsi_child_outcome TEXT,
    wsi_accepted_at TEXT,
    wsi_escalated_at TEXT,
    FOREIGN KEY (wsi_instance_id) REFERENCES t_workflow_instance(wfi_id),
    FOREIGN KEY (wsi_assignee_id) REFERENCES t_user(usr_id),
    FOREIGN KEY (wsi_delegated_from_id) REFERENCES t_workflow_step_instance(wsi_id),
    FOREIGN KEY (wsi_child_instance_id) REFERENCES t_workflow_instance(wfi_id)
);

CREATE TABLE IF NOT EXISTS t_workflow_step_field_value (
    wsf_id INTEGER PRIMARY KEY AUTOINCREMENT,
    wsf_instance_id INTEGER NOT NULL,
    wsf_step_key TEXT NOT NULL,
    wsf_field_code TEXT NOT NULL,
    wsf_value TEXT,
    wsf_filled_by INTEGER,
    wsf_filled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (wsf_instance_id) REFERENCES t_workflow_instance(wfi_id),
    FOREIGN KEY (wsf_filled_by) REFERENCES t_user(usr_id),
    UNIQUE (wsf_instance_id, wsf_step_key, wsf_field_code)
);

CREATE TABLE IF NOT EXISTS t_workflow_approval (
    wap_id INTEGER PRIMARY KEY AUTOINCREMENT,
    wap_step_inst_id INTEGER NOT NULL,
    wap_approver_id INTEGER NOT NULL,
    wap_decision TEXT NOT NULL CHECK(wap_decision IN ('Approved', 'Rejected', 'Abstained')),
    wap_comment TEXT,
    wap_decided_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (wap_step_inst_id) REFERENCES t_workflow_step_instance(wsi_id),
    FOREIGN KEY (wap_approver_id) REFERENCES t_user(usr_id)
);

CREATE TABLE IF NOT EXISTS t_workflow_step_attachment (
    wsa_id INTEGER PRIMARY KEY AUTOINCREMENT,
    wsa_step_inst_id INTEGER NOT NULL,
    wsa_action_id INTEGER,
    wsa_filename TEXT NOT NULL,
    wsa_storage_path TEXT NOT NULL,
    wsa_mime_type TEXT,
    wsa_size_bytes INTEGER NOT NULL,
    wsa_uploaded_by INTEGER NOT NULL,
    wsa_uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    wsa_description TEXT,
    wsa_deleted_at TEXT,
    FOREIGN KEY (wsa_step_inst_id) REFERENCES t_workflow_step_instance(wsi_id),
    FOREIGN KEY (wsa_action_id) REFERENCES t_action(act_id),
    FOREIGN KEY (wsa_uploaded_by) REFERENCES t_user(usr_id)
);

CREATE INDEX IF NOT EXISTS idx_wft_type ON t_workflow_template(wft_type);
CREATE INDEX IF NOT EXISTS idx_wft_active ON t_workflow_template(wft_active);
CREATE INDEX IF NOT EXISTS idx_wfi_template ON t_workflow_instance(wfi_template_id);
CREATE INDEX IF NOT EXISTS idx_wfi_status ON t_workflow_instance(wfi_status);
CREATE INDEX IF NOT EXISTS idx_wsi_instance ON t_workflow_step_instance(wsi_instance_id);
CREATE INDEX IF NOT EXISTS idx_wsi_status ON t_workflow_step_instance(wsi_status);
CREATE INDEX IF NOT EXISTS idx_wsi_assignee ON t_workflow_step_instance(wsi_assignee_id);
CREATE INDEX IF NOT EXISTS idx_wsf_instance_step ON t_workflow_step_field_value(wsf_instance_id, wsf_step_key);
CREATE INDEX IF NOT EXISTS idx_wap_step ON t_workflow_approval(wap_step_inst_id);
CREATE INDEX IF NOT EXISTS idx_wap_approver ON t_workflow_approval(wap_approver_id);
CREATE INDEX IF NOT EXISTS idx_wsa_step ON t_workflow_step_attachment(wsa_step_inst_id);
CREATE INDEX IF NOT EXISTS idx_wsa_action ON t_workflow_step_attachment(wsa_action_id);

CREATE TABLE IF NOT EXISTS t_department (
    dep_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dep_code TEXT NOT NULL UNIQUE,
    dep_name_en TEXT NOT NULL,
    dep_name_cn TEXT NOT NULL,
    dep_desc TEXT,
    dep_active INTEGER NOT NULL DEFAULT 1,
    dep_sort_order INTEGER NOT NULL DEFAULT 0,
    dep_created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS t_team (
    tea_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tea_code TEXT UNIQUE,
    tea_name_en TEXT NOT NULL,
    tea_name_cn TEXT,
    tea_leader_user_id INTEGER,
    tea_active INTEGER NOT NULL DEFAULT 1,
    tea_sort_order INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (tea_leader_user_id) REFERENCES t_user(usr_id)
);

CREATE TABLE IF NOT EXISTS t_user (
    usr_id INTEGER PRIMARY KEY AUTOINCREMENT,
    usr_username TEXT NOT NULL UNIQUE,
    usr_employee_id TEXT UNIQUE,
    usr_pwd_hash TEXT NOT NULL,
    usr_display_name TEXT NOT NULL,
    usr_display_name_cn TEXT,
    usr_email TEXT NOT NULL,
    usr_role TEXT NOT NULL CHECK (usr_role IN ('Admin', 'TeamLead', 'Member', 'ReadOnly')),
    usr_team_id INTEGER,
    usr_lang TEXT NOT NULL DEFAULT 'en' CHECK (usr_lang IN ('en', 'zh')),
    usr_auth_src TEXT NOT NULL DEFAULT 'local',
    usr_active INTEGER NOT NULL DEFAULT 1,
    usr_must_change_pwd INTEGER NOT NULL DEFAULT 1,
    usr_failed_logins INTEGER NOT NULL DEFAULT 0,
    usr_first_failed_at TEXT,
    usr_locked_until TEXT,
    usr_last_login_at TEXT,
    usr_created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    usr_updated_at TEXT,
    FOREIGN KEY (usr_team_id) REFERENCES t_team(tea_id)
);

CREATE TABLE IF NOT EXISTS t_topic (
    top_id INTEGER PRIMARY KEY AUTOINCREMENT,
    top_code CHAR(3) UNIQUE,
    top_name TEXT NOT NULL,
    top_desc TEXT,
    top_active INTEGER NOT NULL DEFAULT 1,
    top_is_global INTEGER NOT NULL DEFAULT 0,
    top_sort INTEGER NOT NULL DEFAULT 0,
    top_created_by INTEGER,
    FOREIGN KEY (top_created_by) REFERENCES t_user(usr_id)
);

CREATE TABLE IF NOT EXISTS t_category (
    cat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cat_name_en TEXT NOT NULL UNIQUE,
    cat_name_cn TEXT,
    cat_color TEXT,
    cat_active INTEGER NOT NULL DEFAULT 1,
    cat_sort INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS t_tag (
    tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_name TEXT NOT NULL UNIQUE,
    tag_created_by INTEGER,
    tag_usage INTEGER NOT NULL DEFAULT 0,
    tag_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS t_action (
    act_id INTEGER PRIMARY KEY AUTOINCREMENT,
    act_ref TEXT NOT NULL UNIQUE,
    act_title TEXT NOT NULL CHECK (length(act_title) BETWEEN 5 AND 200),
    act_desc TEXT,
    act_tags TEXT,
    act_topic_id INTEGER,
    act_category_id INTEGER,
    act_team_id     INTEGER,
    act_priority TEXT NOT NULL CHECK (act_priority IN ('Critical', 'High', 'Medium', 'Low')),
    act_owner_id    INTEGER,
    act_status TEXT NOT NULL DEFAULT 'Open' CHECK (act_status IN ('Open', 'In Progress', 'On Hold', 'Done', 'Cancelled')),
    act_start_date TEXT,
    act_deadline TEXT,
    act_actual_date TEXT,
    act_parent_id INTEGER,
    act_source TEXT NOT NULL DEFAULT 'Manual' CHECK (act_source IN ('Manual', 'Import', 'Meeting')),
    act_source_file TEXT,
    act_source_ref TEXT,
    act_last_comment TEXT,
    act_visibility TEXT NOT NULL DEFAULT 'public' CHECK (act_visibility IN ('public', 'private')),
    act_hold_reason TEXT,
    act_cancel_reason TEXT,
    act_target_reactivation_date TEXT,
    act_escalation_level TEXT NOT NULL DEFAULT 'Normal' CHECK (act_escalation_level IN ('Normal', 'Escalated', 'WAR')),
    act_completion_pct INTEGER NOT NULL DEFAULT 0,
    act_meeting_inst_id INTEGER,
    act_created_by INTEGER NOT NULL,
    act_created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    act_updated_at TEXT,
    act_archived INTEGER NOT NULL DEFAULT 0,
    act_archived_by INTEGER,
    act_archived_at TEXT,
    act_secondary_topic_id INTEGER,
    FOREIGN KEY (act_topic_id) REFERENCES t_topic(top_id),
    FOREIGN KEY (act_secondary_topic_id) REFERENCES t_topic(top_id),
    FOREIGN KEY (act_category_id) REFERENCES t_category(cat_id),
    FOREIGN KEY (act_team_id)     REFERENCES t_team(tea_id),
    FOREIGN KEY (act_owner_id)    REFERENCES t_user(usr_id),
    FOREIGN KEY (act_parent_id) REFERENCES t_action(act_id),
    FOREIGN KEY (act_meeting_inst_id) REFERENCES t_meeting_instance(min_id),
    FOREIGN KEY (act_created_by) REFERENCES t_user(usr_id)
);

CREATE TABLE IF NOT EXISTS t_assignment (
    asg_id INTEGER PRIMARY KEY AUTOINCREMENT,
    asg_action_id INTEGER NOT NULL,
    asg_user_id INTEGER NOT NULL,
    asg_role TEXT NOT NULL,
    asg_status TEXT NOT NULL DEFAULT 'Assigned' CHECK (asg_status IN ('Assigned', 'Reassigned')),
    asg_estimated_hours REAL,
    asg_assigned_by INTEGER,
    asg_assigned_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asg_action_id) REFERENCES t_action(act_id) ON DELETE CASCADE,
    FOREIGN KEY (asg_user_id) REFERENCES t_user(usr_id),
    FOREIGN KEY (asg_assigned_by) REFERENCES t_user(usr_id),
    UNIQUE (asg_action_id, asg_user_id)
);

CREATE TABLE IF NOT EXISTS t_action_history (
    ahi_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ahi_action_id INTEGER NOT NULL,
    ahi_change_type TEXT NOT NULL
        CHECK (ahi_change_type IN (
            'Created', 'Updated', 'StatusChange', 'Reassigned', 'Closed',
            'CommentAdded', 'CommentEdited', 'CommentDeleted', 'Archived'
        )),
    ahi_field TEXT,
    ahi_old_value TEXT,
    ahi_new_value TEXT,
    ahi_changed_by INTEGER,
    ahi_changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ahi_action_id) REFERENCES t_action(act_id) ON DELETE CASCADE,
    FOREIGN KEY (ahi_changed_by) REFERENCES t_user(usr_id)
);

CREATE TABLE IF NOT EXISTS t_action_feedback (
    afb_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    afb_action_id       INTEGER NOT NULL,
    afb_meeting_inst_id INTEGER,
    afb_user_id         INTEGER NOT NULL,
    afb_completion_pct  INTEGER CHECK (afb_completion_pct BETWEEN 0 AND 100),
    afb_status          TEXT CHECK (afb_status IN ('not_started','on_track','late','done','cancelled')),
    afb_comment         TEXT,
    afb_est_date        TEXT,
    afb_blockers        TEXT,
    afb_created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (afb_action_id) REFERENCES t_action(act_id) ON DELETE CASCADE,
    FOREIGN KEY (afb_user_id) REFERENCES t_user(usr_id),
    FOREIGN KEY (afb_meeting_inst_id) REFERENCES t_meeting_instance(min_id)
);

CREATE TABLE IF NOT EXISTS t_import_log (
    iml_id INTEGER PRIMARY KEY AUTOINCREMENT,
    iml_filename TEXT NOT NULL,
    iml_total_rows INTEGER NOT NULL DEFAULT 0,
    iml_imported INTEGER NOT NULL DEFAULT 0,
    iml_skipped INTEGER NOT NULL DEFAULT 0,
    iml_duplicates INTEGER NOT NULL DEFAULT 0,
    iml_warnings INTEGER NOT NULL DEFAULT 0,
    iml_warn_details TEXT,
    iml_status TEXT NOT NULL DEFAULT 'Completed' CHECK (iml_status IN ('Completed', 'Rolled Back', 'Failed')),
    iml_imported_by INTEGER,
    iml_imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (iml_imported_by) REFERENCES t_user(usr_id)
);

CREATE TABLE IF NOT EXISTS t_action_tag (
    atg_action_id INTEGER NOT NULL,
    atg_tag_id INTEGER NOT NULL,
    PRIMARY KEY (atg_action_id, atg_tag_id),
    FOREIGN KEY (atg_action_id) REFERENCES t_action(act_id) ON DELETE CASCADE,
    FOREIGN KEY (atg_tag_id) REFERENCES t_tag(tag_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS t_comment (
    cmt_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    cmt_act_id     INTEGER,
    cmt_type       TEXT NOT NULL DEFAULT 'Comment'
        CHECK (cmt_type IN ('Comment','Achievement','Roadblock')),
    cmt_body       TEXT NOT NULL CHECK (length(cmt_body) BETWEEN 1 AND 2000),
    cmt_created_by INTEGER NOT NULL,
    cmt_created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cmt_edited_at  TEXT,
    cmt_edited_by  INTEGER,
    cmt_meeting_inst_id INTEGER,
    cmt_is_deleted INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (cmt_act_id)     REFERENCES t_action(act_id) ON DELETE CASCADE,
    FOREIGN KEY (cmt_meeting_inst_id) REFERENCES t_meeting_instance(min_id) ON DELETE CASCADE,
    FOREIGN KEY (cmt_created_by) REFERENCES t_user(usr_id),
    FOREIGN KEY (cmt_edited_by)  REFERENCES t_user(usr_id)
);

CREATE TABLE IF NOT EXISTS t_meeting (
    mtg_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mtg_title       TEXT    NOT NULL CHECK(length(mtg_title) >= 2),
    mtg_description TEXT,
    mtg_topic_id    INTEGER,
    mtg_visibility  TEXT    NOT NULL DEFAULT 'public' CHECK (mtg_visibility IN ('public', 'private')),
    mtg_created_by  INTEGER,
    mtg_created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mtg_topic_id) REFERENCES t_topic(top_id),
    FOREIGN KEY (mtg_created_by) REFERENCES t_user(usr_id)
);

CREATE TABLE IF NOT EXISTS t_meeting_instance (
    min_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    min_meeting_id INTEGER,
    min_title      TEXT NOT NULL,
    min_date       TEXT,
    min_type       TEXT,
    min_topic_id   INTEGER,
    min_category_id   INTEGER,
    min_secondary_category_id INTEGER,
    min_notes      TEXT,
    min_visibility TEXT NOT NULL DEFAULT 'public' CHECK (min_visibility IN ('public', 'private')),
    min_created_by INTEGER,
    min_created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    min_archived  INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (min_meeting_id) REFERENCES t_meeting(mtg_id),
    FOREIGN KEY (min_topic_id) REFERENCES t_topic(top_id),
    FOREIGN KEY (min_category_id) REFERENCES t_topic(top_id),
    FOREIGN KEY (min_secondary_category_id) REFERENCES t_topic(top_id),
    FOREIGN KEY (min_created_by) REFERENCES t_user(usr_id)
);

CREATE TABLE IF NOT EXISTS t_meeting_memo (
    mmm_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mmm_instance_id INTEGER NOT NULL REFERENCES t_meeting_instance(min_id),
    mmm_title       TEXT    NOT NULL,
    mmm_body        TEXT    NOT NULL DEFAULT '',
    mmm_sort_order  INTEGER NOT NULL DEFAULT 0,
    mmm_date        TEXT,
    mmm_created_by  INTEGER REFERENCES t_user(usr_id),
    mmm_created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    mmm_updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS t_meeting_summary (
    msm_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    msm_instance_id INTEGER NOT NULL,
    msm_filename    TEXT NOT NULL,
    msm_file_path   TEXT,
    msm_file_data   BLOB,
    msm_file_mime   TEXT,
    msm_file_size   INTEGER,
    msm_uploader_id INTEGER,
    msm_uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (msm_instance_id) REFERENCES t_meeting_instance(min_id) ON DELETE CASCADE,
    FOREIGN KEY (msm_uploader_id) REFERENCES t_user(usr_id)
);

CREATE TABLE IF NOT EXISTS t_meeting_owner (
    mow_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mow_instance_id INTEGER NOT NULL,
    mow_user_id     INTEGER NOT NULL,
    mow_granted_by  INTEGER NOT NULL,
    mow_granted_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mow_instance_id) REFERENCES t_meeting_instance(min_id) ON DELETE CASCADE,
    FOREIGN KEY (mow_user_id)     REFERENCES t_user(usr_id),
    FOREIGN KEY (mow_granted_by)  REFERENCES t_user(usr_id),
    UNIQUE(mow_instance_id, mow_user_id)
);

CREATE TABLE IF NOT EXISTS t_meeting_participant (
    mpa_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mpa_instance_id INTEGER NOT NULL,
    mpa_user_id     INTEGER NOT NULL,
    mpa_added_by    INTEGER NOT NULL,
    mpa_added_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mpa_instance_id) REFERENCES t_meeting_instance(min_id) ON DELETE CASCADE,
    FOREIGN KEY (mpa_user_id)     REFERENCES t_user(usr_id),
    FOREIGN KEY (mpa_added_by)    REFERENCES t_user(usr_id),
    UNIQUE(mpa_instance_id, mpa_user_id)
);

CREATE TABLE IF NOT EXISTS t_meeting_decision (
    mdc_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    mdc_meeting_id      INTEGER,
    mdc_instance_id     INTEGER,
    mdc_title           TEXT NOT NULL,
    mdc_body            TEXT NOT NULL,
    mdc_context         TEXT,
    mdc_reason          TEXT,
    mdc_status          TEXT NOT NULL DEFAULT 'Proposed' 
                        CHECK (mdc_status IN ('Proposed', 'Accepted', 'Approved', 'Rejected', 'Implemented', 'Reversed', 'Deleted')),
    mdc_category_id        INTEGER REFERENCES t_topic(top_id),
    mdc_secondary_category_id INTEGER REFERENCES t_topic(top_id),
    mdc_action_type_id INTEGER REFERENCES t_category(cat_id),
    mdc_linked_action_id INTEGER REFERENCES t_action(act_id),
    mdc_tags            TEXT,
    mdc_decided_at      TEXT,
    mdc_created_by      INTEGER NOT NULL,
    mdc_created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    mdc_updated_at      TEXT,
    mdc_deleted_at      TEXT,
    FOREIGN KEY (mdc_meeting_id) REFERENCES t_meeting_instance(min_id),
    FOREIGN KEY (mdc_instance_id) REFERENCES t_meeting_instance(min_id),
    FOREIGN KEY (mdc_created_by) REFERENCES t_user(usr_id)
);

CREATE TABLE IF NOT EXISTS t_meeting_decision_revision (
    mdr_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    mdr_decision_id     INTEGER NOT NULL,
    mdr_title           TEXT NOT NULL,
    mdr_body            TEXT NOT NULL,
    mdr_updated_by      INTEGER,
    mdr_updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mdr_decision_id) REFERENCES t_meeting_decision(mdc_id) ON DELETE CASCADE,
    FOREIGN KEY (mdr_updated_by) REFERENCES t_user(usr_id)
);

CREATE TABLE IF NOT EXISTS t_notification (
    ntf_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ntf_user_id    INTEGER NOT NULL REFERENCES t_user(usr_id),
    ntf_event_type TEXT    NOT NULL,
    ntf_title      TEXT    NOT NULL,
    ntf_body       TEXT,
    ntf_action_id  INTEGER REFERENCES t_action(act_id),
    ntf_is_read    INTEGER NOT NULL DEFAULT 0,
    ntf_created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS t_user_team (
    utm_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    utm_user_id INTEGER NOT NULL,
    utm_team_id INTEGER NOT NULL,
    FOREIGN KEY (utm_user_id) REFERENCES t_user(usr_id) ON DELETE CASCADE,
    FOREIGN KEY (utm_team_id) REFERENCES t_team(tea_id) ON DELETE CASCADE,
    UNIQUE (utm_user_id, utm_team_id)
);

CREATE TABLE IF NOT EXISTS t_user_dept (
    udp_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    udp_user_id    INTEGER NOT NULL REFERENCES t_user(usr_id) ON DELETE CASCADE,
    udp_dept_id    INTEGER NOT NULL REFERENCES t_department(dep_id) ON DELETE CASCADE,
    udp_primary    INTEGER NOT NULL DEFAULT 0,
    udp_created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(udp_user_id, udp_dept_id)
);

CREATE TABLE IF NOT EXISTS t_feedback (
    fbk_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fbk_user_id         INTEGER NOT NULL REFERENCES t_user(usr_id),
    fbk_category        TEXT    NOT NULL CHECK (fbk_category IN ('Bug','Feature','Usability','General')),
    fbk_page            TEXT,
    fbk_title           TEXT    NOT NULL,
    fbk_description     TEXT    NOT NULL,
    fbk_priority        TEXT    NOT NULL DEFAULT 'Medium' CHECK (fbk_priority IN ('Low','Medium','High')),
    fbk_screenshot      BLOB,
    fbk_screenshot_name TEXT,
    fbk_status          TEXT    NOT NULL DEFAULT 'New' CHECK (fbk_status IN ('New','Acknowledged','In Progress','Resolved','Declined')),
    fbk_admin_response  TEXT,
    fbk_responded_by    INTEGER REFERENCES t_user(usr_id),
    fbk_created_at      TEXT    DEFAULT CURRENT_TIMESTAMP,
    fbk_updated_at      TEXT
);

CREATE TABLE IF NOT EXISTS t_evolution (
    evo_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    evo_version      TEXT    NOT NULL,
    evo_title        TEXT    NOT NULL,
    evo_description  TEXT    NOT NULL,
    evo_category     TEXT    NOT NULL CHECK (evo_category IN ('Feature','Improvement','Bugfix','Security')),
    evo_date         TEXT    NOT NULL,
    evo_is_published INTEGER NOT NULL DEFAULT 0,
    evo_author_id    INTEGER REFERENCES t_user(usr_id),
    evo_created_at   TEXT    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS t_assignment_history (
    ash_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ash_action_id  INTEGER NOT NULL,
    ash_user_id    INTEGER NOT NULL,
    ash_role       TEXT    NOT NULL,
    ash_event      TEXT    NOT NULL CHECK (ash_event IN ('Assigned', 'Accepted', 'Declined', 'Removed')),
    ash_by_user_id INTEGER,
    ash_comment    TEXT,
    ash_created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ash_action_id)  REFERENCES t_action(act_id) ON DELETE CASCADE,
    FOREIGN KEY (ash_user_id)    REFERENCES t_user(usr_id),
    FOREIGN KEY (ash_by_user_id) REFERENCES t_user(usr_id)
);

CREATE INDEX IF NOT EXISTS idx_user_team ON t_user(usr_team_id);
CREATE INDEX IF NOT EXISTS idx_action_status ON t_action(act_status);
CREATE INDEX IF NOT EXISTS idx_action_deadline ON t_action(act_deadline);
CREATE INDEX IF NOT EXISTS idx_action_overdue
ON t_action(act_deadline, act_status)
WHERE act_status NOT IN ('Done', 'Cancelled');
CREATE INDEX IF NOT EXISTS idx_assignment_action ON t_assignment(asg_action_id);
CREATE INDEX IF NOT EXISTS idx_assignment_user ON t_assignment(asg_user_id);
CREATE INDEX IF NOT EXISTS idx_history_action ON t_action_history(ahi_action_id, ahi_changed_at DESC);
CREATE INDEX IF NOT EXISTS idx_afb_action ON t_action_feedback(afb_action_id);
CREATE INDEX IF NOT EXISTS idx_afb_user ON t_action_feedback(afb_user_id);
CREATE INDEX IF NOT EXISTS idx_afb_meeting ON t_action_feedback(afb_meeting_inst_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_employee_id ON t_user(usr_employee_id) WHERE usr_employee_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_feedback_user   ON t_feedback(fbk_user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_status ON t_feedback(fbk_status);
CREATE INDEX IF NOT EXISTS idx_evolution_version ON t_evolution(evo_version);
CREATE INDEX IF NOT EXISTS idx_action_archived_created ON t_action(act_archived, act_created_at DESC);
CREATE INDEX IF NOT EXISTS idx_action_archived_status_deadline ON t_action(act_archived, act_status, act_deadline);
CREATE INDEX IF NOT EXISTS idx_user_team_team ON t_user_team(utm_team_id);
CREATE INDEX IF NOT EXISTS idx_action_secondary_topic ON t_action(act_secondary_topic_id) WHERE act_secondary_topic_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_meeting_secondary_category ON t_meeting_instance(min_secondary_category_id) WHERE min_secondary_category_id IS NOT NULL;


CREATE INDEX IF NOT EXISTS idx_decision_secondary_category ON t_meeting_decision(mdc_secondary_category_id) WHERE mdc_secondary_category_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_decision_revision_decision_updated ON t_meeting_decision_revision(mdr_decision_id, mdr_updated_at DESC);

CREATE TRIGGER IF NOT EXISTS trg_action_done
AFTER UPDATE OF act_status ON t_action
FOR EACH ROW
WHEN NEW.act_status = 'Done' AND OLD.act_status <> 'Done'
BEGIN
    UPDATE t_action
    SET act_actual_date = COALESCE(act_actual_date, date('now')),
        act_updated_at = CURRENT_TIMESTAMP
    WHERE act_id = NEW.act_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_action_updated_at
AFTER UPDATE ON t_action
FOR EACH ROW
WHEN NEW.act_updated_at IS OLD.act_updated_at OR NEW.act_updated_at IS NULL
BEGIN
    UPDATE t_action SET act_updated_at = CURRENT_TIMESTAMP WHERE act_id = NEW.act_id;
END;

CREATE VIEW IF NOT EXISTS v_action_detail AS
SELECT
    a.*,
    tp.top_name,
    tp2.top_name  AS secondary_topic_name,
    c.cat_name_en, c.cat_color,
    o.usr_display_name AS owner_name
FROM t_action a
LEFT JOIN t_topic tp    ON tp.top_id = a.act_topic_id
LEFT JOIN t_topic tp2   ON tp2.top_id = a.act_secondary_topic_id
LEFT JOIN t_category c  ON c.cat_id   = a.act_category_id
LEFT JOIN t_user o      ON o.usr_id   = a.act_owner_id;

CREATE VIEW IF NOT EXISTS v_overdue_actions AS
SELECT *
FROM t_action
WHERE act_status NOT IN ('Done', 'Cancelled')
  AND act_deadline < date('now')
  AND act_deadline IS NOT NULL;

CREATE VIEW IF NOT EXISTS v_user_workload AS
SELECT
    u.usr_id,
    u.usr_display_name,
    COUNT(a.asg_id) AS active_assignments
FROM t_user u
LEFT JOIN t_assignment a ON a.asg_user_id = u.usr_id
LEFT JOIN t_action x ON x.act_id = a.asg_action_id
WHERE (
            INSTR(',' || a.asg_role || ',', ',Lead,') > 0
            OR INSTR(',' || a.asg_role || ',', ',Delegate,') > 0
)
  AND x.act_status NOT IN ('Done', 'Cancelled')
GROUP BY u.usr_id, u.usr_display_name;


CREATE TABLE IF NOT EXISTS t_workflow_service_log (
        wsl_id INTEGER PRIMARY KEY AUTOINCREMENT,
        wsl_instance_id INTEGER NOT NULL, -- t_workflow_instance.wfi_id
        wsl_step_key TEXT NOT NULL,       -- step key in graph
        wsl_handler TEXT NOT NULL,        -- handler name
        wsl_status TEXT NOT NULL CHECK (wsl_status IN ('Success', 'Error', 'Paused', 'Skipped')),
        wsl_inputs TEXT,                  -- JSON string of input mapping
        wsl_outputs TEXT,                 -- JSON string of output mapping
        wsl_error TEXT,                   -- error message if any
        wsl_started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        wsl_completed_at TEXT,
        wsl_triggered_by INTEGER,         -- user id if manual retry
        FOREIGN KEY (wsl_instance_id) REFERENCES t_workflow_instance(wfi_id)
);
-- S72 Migration: Subprocess steps + assignment rules


-- 7. Create round-robin assignment counter
CREATE TABLE IF NOT EXISTS t_workflow_assignment_counter (
    wrc_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    wrc_template_id  INTEGER NOT NULL REFERENCES t_workflow_template(wft_id),
    wrc_step_key     TEXT    NOT NULL,
    wrc_last_user_id INTEGER NOT NULL REFERENCES t_user(usr_id),
    wrc_updated_at   DATETIME NOT NULL DEFAULT (datetime('now')),
    UNIQUE(wrc_template_id, wrc_step_key)
);

-- FTS5 for Meeting Decisions (P8)
CREATE VIRTUAL TABLE IF NOT EXISTS t_meeting_decision_fts USING fts5(
    mdc_title,
    mdc_body,
    mdc_context,
    mdc_reason,
    mdc_tags,
    content='t_meeting_decision',
    content_rowid='mdc_id'
);

-- Triggers to keep FTS5 in sync
CREATE TRIGGER IF NOT EXISTS t_meeting_decision_ai AFTER INSERT ON t_meeting_decision BEGIN
    INSERT INTO t_meeting_decision_fts(rowid, mdc_title, mdc_body, mdc_context, mdc_reason, mdc_tags)
    VALUES (new.mdc_id, new.mdc_title, new.mdc_body, new.mdc_context, new.mdc_reason, new.mdc_tags);
END;

CREATE TRIGGER IF NOT EXISTS t_meeting_decision_ad AFTER DELETE ON t_meeting_decision BEGIN
    INSERT INTO t_meeting_decision_fts(t_meeting_decision_fts, rowid, mdc_title, mdc_body, mdc_context, mdc_reason, mdc_tags)
    VALUES('delete', old.mdc_id, old.mdc_title, old.mdc_body, old.mdc_context, old.mdc_reason, old.mdc_tags);
END;

CREATE TRIGGER IF NOT EXISTS t_meeting_decision_au AFTER UPDATE ON t_meeting_decision BEGIN
    INSERT INTO t_meeting_decision_fts(t_meeting_decision_fts, rowid, mdc_title, mdc_body, mdc_context, mdc_reason, mdc_tags)
    VALUES('delete', old.mdc_id, old.mdc_title, old.mdc_body, old.mdc_context, old.mdc_reason, old.mdc_tags);
    INSERT INTO t_meeting_decision_fts(rowid, mdc_title, mdc_body, mdc_context, mdc_reason, mdc_tags)
    VALUES (new.mdc_id, new.mdc_title, new.mdc_body, new.mdc_context, new.mdc_reason, new.mdc_tags);
END;
