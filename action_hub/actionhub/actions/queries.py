from math import ceil

from actionhub.middleware.db import get_db


SORT_FIELDS = {
    "created_at": "a.act_created_at",
    "updated_at": "a.act_updated_at",
    "deadline": "a.act_deadline",
    "title": "a.act_title",
    "priority": "a.act_priority",
    "status": "a.act_status",
}


def list_actions(filters: dict) -> dict:
    db = get_db()
    # Ensure series participant table exists for the privacy subquery
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS t_meeting_series_participant (
            msp_id INTEGER PRIMARY KEY AUTOINCREMENT,
            msp_meeting_id INTEGER NOT NULL REFERENCES t_meeting(mtg_id) ON DELETE CASCADE,
            msp_user_id INTEGER NOT NULL REFERENCES t_user(usr_id),
            msp_kind TEXT NOT NULL DEFAULT 'Compulsory' CHECK (msp_kind IN ('Compulsory', 'Optional')),
            msp_added_by INTEGER NOT NULL REFERENCES t_user(usr_id),
            msp_added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(msp_meeting_id, msp_user_id)
        )
        """
    )
    action_columns = {row[1] for row in db.execute("PRAGMA table_info(t_action)").fetchall()}
    if "act_tags" not in action_columns:
        db.execute("ALTER TABLE t_action ADD COLUMN act_tags TEXT")
        action_columns.add("act_tags")
    if "act_machine_serial" in action_columns:
        db.execute(
            "UPDATE t_action SET act_tags = COALESCE(NULLIF(act_tags, ''), UPPER(TRIM(act_machine_serial))) WHERE COALESCE(act_machine_serial, '') <> ''"
        )
    page = max(1, int(filters.get("page", 1)))
    per_page = min(100, max(1, int(filters.get("per_page", 20))))
    sort_by = SORT_FIELDS.get(filters.get("sort_by", "created_at"), "a.act_created_at")
    sort_order = "DESC" if str(filters.get("sort_order", "asc")).lower() == "desc" else "ASC"
    current_user_id = filters.get("current_user_id")
    current_user_role = str(filters.get("current_user_role") or "Member")

    where_parts: list[str] = ["a.act_archived = 0"]
    params: list[object] = []

    business_status_expr = """
    CASE
        WHEN a.act_status = 'Cancelled' THEN 'Cancelled'
        WHEN a.act_status = 'Done' THEN 'Done'
        WHEN a.act_status = 'Open' THEN 'Not started'
        WHEN a.act_deadline IS NOT NULL
             AND DATE(a.act_deadline) < DATE('now')
             AND a.act_status NOT IN ('Done', 'Cancelled') THEN 'Late'
        ELSE 'On-track'
    END
    """

    if filters.get("priority"):
        where_parts.append("a.act_priority = ?")
        params.append(filters["priority"])

    # Filter by owner (creator or assignee)
    owner_filter = filters.get("owner_id")
    if owner_filter not in (None, ""):
        uid = int(owner_filter)
        where_parts.append(
            "(a.act_created_by = ? OR EXISTS (SELECT 1 FROM t_assignment x WHERE x.asg_action_id = a.act_id AND x.asg_user_id = ?))"
        )
        params.extend([uid, uid])

    # Filter for actions where current user is Lead (act_owner_id)
    lead_only = str(filters.get("lead_only", "")).strip().lower() in ("1", "true", "yes")
    if lead_only and current_user_id is not None:
        where_parts.append("a.act_owner_id = ?")
        params.append(int(current_user_id))

    # Filter by specific lead user id
    lead_id_filter = filters.get("lead_id")
    if lead_id_filter not in (None, ""):
        where_parts.append("a.act_owner_id = ?")
        params.append(int(lead_id_filter))

    # Filter by status (support comma-separated exclusion via status_not)
    status_filter = filters.get("status")
    if status_filter not in (None, ""):
        where_parts.append("a.act_status = ?")
        params.append(status_filter)
    status_family_filter = filters.get("status_family")
    if status_family_filter not in (None, ""):
        where_parts.append(f"({business_status_expr}) = ?")
        params.append(str(status_family_filter).strip())

    status_not_filter = filters.get("status_not")
    if status_not_filter not in (None, ""):
        excluded = [s.strip() for s in str(status_not_filter).split(",") if s.strip()]
        if excluded:
            placeholders = ",".join(["?"] * len(excluded))
            where_parts.append(f"a.act_status NOT IN ({placeholders})")
            params.extend(excluded)
    status_family_not_filter = filters.get("status_family_not")
    if status_family_not_filter not in (None, ""):
        excluded_family = [s.strip() for s in str(status_family_not_filter).split(",") if s.strip()]
        if excluded_family:
            placeholders = ",".join(["?"] * len(excluded_family))
            where_parts.append(f"({business_status_expr}) NOT IN ({placeholders})")
            params.extend(excluded_family)

    meeting_filter = filters.get("meeting_id")
    if meeting_filter not in (None, ""):
        where_parts.append("a.act_meeting_inst_id = ?")
        params.append(int(meeting_filter))

    # Filter by meeting series (parent meeting id)
    series_filter = filters.get("series_id")
    if series_filter not in (None, ""):
        where_parts.append("mi.min_meeting_id = ?")
        params.append(int(series_filter))

    topic_filter = filters.get("topic_id") or filters.get("topic_code") or filters.get("category_id")
    if topic_filter not in (None, ""):
        topic_id = None
        topic_filter_str = str(topic_filter).strip()
        try:
            topic_id = int(topic_filter_str)
        except (TypeError, ValueError):
            if ":" in topic_filter_str:
                suffix = topic_filter_str.rsplit(":", 1)[-1].strip()
                if suffix.isdigit():
                    topic_id = int(suffix)
            row = db.execute(
                "SELECT top_id FROM t_topic WHERE top_code = ? OR top_name = ? OR CAST(top_id AS TEXT) = ?",
                (topic_filter_str, topic_filter_str, topic_filter_str),
            ).fetchone()
            if row:
                topic_id = int(row["top_id"])
        if topic_id is not None:
            where_parts.append("(a.act_topic_id = ? OR a.act_secondary_topic_id = ?)")
            params.append(topic_id)
            params.append(topic_id)

    if filters.get("search"):
        where_parts.append("(a.act_title LIKE ? OR COALESCE(a.act_desc, '') LIKE ? OR a.act_ref LIKE ? OR COALESCE(a.act_tags, '') LIKE ?)")
        term = f"%{str(filters['search']).strip()}%"
        params.extend([term, term, term, term])

    # ── New visibility logic for non-admin users ──
    # Only show:
    # 1. Actions where user is creator, owner, or assignee
    # 2. Actions from meetings (public or private) where user is a participant
    # 3. For non-private meetings, actions where creator/owner/assignee is a team member
    if (
        current_user_role != "Admin"
        and current_user_id is not None
        and not filters.get("meeting_id")
        and not filters.get("series_id")
    ):
        user_team_rows = db.execute(
            """
            SELECT tea_id FROM t_team WHERE tea_id IN (
                SELECT usr_team_id FROM t_user WHERE usr_id = ?
                UNION
                SELECT utm_team_id FROM t_user_team WHERE utm_user_id = ?
            )
            """,
            (int(current_user_id), int(current_user_id)),
        ).fetchall()
        user_team_ids = [int(r["tea_id"]) for r in user_team_rows]
        uid = int(current_user_id)
        team_placeholders = ",".join(["?"] * len(user_team_ids)) if user_team_ids else None
        # 1. My actions (creator, owner, assignee)
        my_actions = "(a.act_created_by = ? OR a.act_owner_id = ? OR EXISTS (SELECT 1 FROM t_assignment x WHERE x.asg_action_id = a.act_id AND x.asg_user_id = ?))"
        params_my = [uid, uid, uid]
        # 2. Actions from meetings where I am a participant
        meeting_participant = "(a.act_meeting_inst_id IS NOT NULL AND EXISTS (SELECT 1 FROM t_meeting_participant mp WHERE mp.mpa_instance_id = a.act_meeting_inst_id AND mp.mpa_user_id = ?))"
        params_meeting = [uid]
        # 3. For non-private meetings, actions by my team members (creator/owner/assignee)
        if user_team_ids:
            team_member_actions = f"(a.act_meeting_inst_id IS NOT NULL AND COALESCE(mi.min_visibility, 'public') <> 'private' AND (a.act_created_by IN (SELECT usr_id FROM t_user WHERE usr_team_id IN ({team_placeholders})) OR a.act_owner_id IN (SELECT usr_id FROM t_user WHERE usr_team_id IN ({team_placeholders})) OR EXISTS (SELECT 1 FROM t_assignment ax WHERE ax.asg_action_id = a.act_id AND ax.asg_user_id IN (SELECT usr_id FROM t_user WHERE usr_team_id IN ({team_placeholders})))))"
            params_team = user_team_ids * 3
        else:
            team_member_actions = None
            params_team = []
        clause_parts = [my_actions, meeting_participant]
        clause_params = params_my + params_meeting
        if team_member_actions:
            clause_parts.append(team_member_actions)
            clause_params += params_team
        where_parts.append(f"(" + " OR ".join(clause_parts) + ")")
        params.extend(clause_params)

    where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    visibility_sql = ""
    visibility_params: list[object] = []
    if current_user_role != "Admin" and current_user_id is not None:
        visibility_sql = """
        AND (
            (
                mi.min_id IS NOT NULL
                AND COALESCE(mi.min_visibility, 'public') = 'private'
                AND (
                    a.act_created_by = ?
                    OR a.act_owner_id = ?
                    OR EXISTS (SELECT 1 FROM t_assignment ap WHERE ap.asg_action_id = a.act_id AND ap.asg_user_id = ?)
                    OR mi.min_created_by = ?
                    OR EXISTS (
                        SELECT 1
                        FROM t_meeting_participant mp
                        WHERE mp.mpa_instance_id = mi.min_id
                          AND mp.mpa_user_id = ?
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM t_team tt
                        WHERE tt.tea_leader_user_id = ?
                          AND (
                              EXISTS (
                                  SELECT 1
                                  FROM t_user_team ut
                                  WHERE ut.utm_team_id = tt.tea_id
                                    AND ut.utm_user_id = a.act_created_by
                              )
                              OR EXISTS (
                                  SELECT 1
                                  FROM t_user cu
                                  WHERE cu.usr_id = a.act_created_by
                                    AND cu.usr_team_id = tt.tea_id
                              )
                          )
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM t_assignment ax
                        JOIN t_team tt ON tt.tea_leader_user_id = ?
                        WHERE ax.asg_action_id = a.act_id
                          AND (
                              EXISTS (
                                  SELECT 1
                                  FROM t_user_team ut
                                  WHERE ut.utm_team_id = tt.tea_id
                                    AND ut.utm_user_id = ax.asg_user_id
                              )
                              OR EXISTS (
                                  SELECT 1
                                  FROM t_user au
                                  WHERE au.usr_id = ax.asg_user_id
                                    AND au.usr_team_id = tt.tea_id
                              )
                          )
                    )
                )
            )
            OR (
                mi.min_id IS NULL
                AND COALESCE(a.act_visibility, 'public') = 'private'
                AND (
                    a.act_created_by = ?
                    OR a.act_owner_id = ?
                    OR EXISTS (SELECT 1 FROM t_assignment ap WHERE ap.asg_action_id = a.act_id AND ap.asg_user_id = ?)
                )
            )
            OR (
                COALESCE(mi.min_visibility, 'public') <> 'private'
                AND COALESCE(a.act_visibility, 'public') = 'public'
                AND (
                    a.act_created_by = ?
                    OR a.act_owner_id = ?
                    OR EXISTS (SELECT 1 FROM t_assignment ap WHERE ap.asg_action_id = a.act_id AND ap.asg_user_id = ?)
                    OR mi.min_created_by = ?
                    OR EXISTS (
                        SELECT 1
                        FROM t_meeting_participant mp
                        WHERE mp.mpa_instance_id = mi.min_id
                          AND mp.mpa_user_id = ?
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM t_meeting_participant mp
                        JOIN t_user pu ON pu.usr_id = mp.mpa_user_id
                        JOIN t_team tt ON tt.tea_id = pu.usr_team_id
                        WHERE mp.mpa_instance_id = mi.min_id AND tt.tea_leader_user_id = ?
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM t_team tt
                        WHERE tt.tea_leader_user_id = ?
                          AND (
                              EXISTS (
                                  SELECT 1
                                  FROM t_user_team ut
                                  WHERE ut.utm_team_id = tt.tea_id
                                    AND ut.utm_user_id = a.act_created_by
                              )
                              OR EXISTS (
                                  SELECT 1
                                  FROM t_user cu
                                  WHERE cu.usr_id = a.act_created_by
                                    AND cu.usr_team_id = tt.tea_id
                              )
                          )
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM t_assignment ax
                        JOIN t_team tt ON tt.tea_leader_user_id = ?
                        WHERE ax.asg_action_id = a.act_id
                          AND (
                              EXISTS (
                                  SELECT 1
                                  FROM t_user_team ut
                                  WHERE ut.utm_team_id = tt.tea_id
                                    AND ut.utm_user_id = ax.asg_user_id
                              )
                              OR EXISTS (
                                  SELECT 1
                                  FROM t_user au
                                  WHERE au.usr_id = ax.asg_user_id
                                    AND au.usr_team_id = tt.tea_id
                              )
                          )
                    )
                )
            )
        )
        """
        visibility_params = [
            int(current_user_id),
            int(current_user_id),
            int(current_user_id),
            int(current_user_id),
            int(current_user_id),
            int(current_user_id),
            int(current_user_id),
            int(current_user_id),
            int(current_user_id),
            int(current_user_id),
            int(current_user_id),
            int(current_user_id),
            int(current_user_id),
            int(current_user_id),
            int(current_user_id),
            int(current_user_id),
            int(current_user_id),
            int(current_user_id),
        ]

    total_row = db.execute(
        f"SELECT COUNT(*) AS total FROM t_action a LEFT JOIN t_meeting_instance mi ON mi.min_id = a.act_meeting_inst_id {where_sql} {visibility_sql}",
        [*params, *visibility_params],
    ).fetchone()
    total = int(total_row["total"]) if total_row else 0

    offset = (page - 1) * per_page

    rows = db.execute(
        f"""
        SELECT
            a.act_id,
            a.act_ref,
            a.act_title,
            a.act_tags,
            a.act_priority,
            a.act_status,
            ({business_status_expr}) AS act_business_status,
            a.act_deadline,
            a.act_actual_date,
            a.act_created_at,
            a.act_updated_at,
            a.act_start_date,
            a.act_team_id,
            a.act_topic_id,
            a.act_secondary_topic_id,
            a.act_owner_id,
            a.act_visibility,
            tm.tea_name_en AS team_name,
            t.top_name AS topic_name,
            tp2.top_name AS secondary_topic_name,
            ow.usr_display_name AS owner_name,
            cr.usr_display_name AS creator_name,
            a.act_meeting_inst_id,
            mi.min_title AS meeting_title,
            mi.min_date AS meeting_date,
            mi.min_visibility AS meeting_visibility,
            mtg.mtg_title AS series_name,
            mi.min_meeting_id AS series_id,
            COALESCE(mtg.mtg_visibility, 'public') AS series_visibility,
            CASE
                WHEN mi.min_id IS NOT NULL
                     AND (COALESCE(mi.min_visibility, 'public') = 'private'
                          OR COALESCE(mtg.mtg_visibility, 'public') = 'private')
                     AND (
                        a.act_created_by = ?
                                OR a.act_owner_id = ?
                        OR EXISTS (SELECT 1 FROM t_assignment ap WHERE ap.asg_action_id = a.act_id AND ap.asg_user_id = ?)
                        OR mi.min_created_by = ?
                                OR EXISTS (
                                     SELECT 1
                                     FROM t_meeting_participant mp
                                     WHERE mp.mpa_instance_id = mi.min_id
                                        AND mp.mpa_user_id = ?
                                )
                        OR (mtg.mtg_id IS NOT NULL AND mtg.mtg_created_by = ?)
                        OR EXISTS (
                            SELECT 1
                            FROM t_meeting_series_participant msp
                            WHERE msp.msp_meeting_id = mtg.mtg_id
                              AND msp.msp_user_id = ?
                        )
                     ) THEN 1
                ELSE 0
            END AS can_view_private_details
        FROM t_action a
        LEFT JOIN t_team tm ON tm.tea_id = a.act_team_id
        LEFT JOIN t_topic t ON t.top_id = a.act_topic_id
        LEFT JOIN t_topic tp2 ON tp2.top_id = a.act_secondary_topic_id
        LEFT JOIN t_user ow ON ow.usr_id = a.act_owner_id
        LEFT JOIN t_user cr ON cr.usr_id = a.act_created_by
        LEFT JOIN t_meeting_instance mi ON mi.min_id = a.act_meeting_inst_id
        LEFT JOIN t_meeting mtg ON mtg.mtg_id = mi.min_meeting_id
        {where_sql}
        {visibility_sql}
        ORDER BY {sort_by} {sort_order}
        LIMIT ? OFFSET ?
        """,
        [int(current_user_id or 0), int(current_user_id or 0), int(current_user_id or 0), int(current_user_id or 0), int(current_user_id or 0), int(current_user_id or 0), int(current_user_id or 0), *params, *visibility_params, per_page, offset],
    ).fetchall()

    items = [dict(row) for row in rows]
    if current_user_role != "Admin":
        for item in items:
            is_private_meeting = str(item.get("meeting_visibility") or "public").strip().lower() == "private"
            is_private_series = str(item.get("series_visibility") or "public").strip().lower() == "private"
            can_view_private_details = bool(int(item.get("can_view_private_details") or 0))
            masked = (is_private_meeting or is_private_series) and not can_view_private_details
            if masked:
                item["act_title"] = "Private action"
                item["act_tags"] = None
            item["is_masked_private"] = masked
            item["is_private_series"] = is_private_series and not can_view_private_details
            item.pop("can_view_private_details", None)
    total_pages = ceil(total / per_page) if total else 1
    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
    }
