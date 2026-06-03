from actionhub.middleware.db import get_db


def _week_start_sunday(d):
    from datetime import timedelta
    return d - timedelta(days=(d.weekday() + 1) % 7)


def _parse_iso_date(value):
    from datetime import date
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _build_week_buckets(weeks: int):
    from datetime import date, timedelta

    cn_epoch = date(2026, 1, 4)
    current_ws = _week_start_sunday(date.today())
    bucket_keys = [current_ws + timedelta(weeks=i) for i in range(weeks)]
    buckets = {}
    for ws in bucket_keys:
        we = ws + timedelta(days=6)
        delta = (ws - cn_epoch).days
        week_num = delta // 7 + 1 if delta >= 0 else None
        label = f"W{week_num}" if week_num is not None else ws.strftime("%m/%d")
        label_full = f"{ws.strftime('%b')} {ws.day}–{we.day}"
        buckets[ws] = {
            "label": label,
            "label_full": label_full,
            "week_start": ws.isoformat(),
            "week_end": we.isoformat(),
            "total_hours": 0.0,
            "count": 0,
            "actions": {},
        }
    return bucket_keys, buckets


def _spread_hours_into_buckets(buckets, hours: float, start_date, end_date, action_meta=None) -> int:
    if hours is None:
        return 0
    try:
        total_hours = float(hours)
    except (TypeError, ValueError):
        return 0
    if total_hours <= 0 or not end_date:
        return 0

    effective_start = start_date or end_date
    if effective_start > end_date:
        effective_start, end_date = end_date, effective_start

    overlap_keys = []
    for ws in buckets.keys():
        we = _parse_iso_date(buckets[ws]["week_end"])
        if ws <= end_date and we >= effective_start:
            overlap_keys.append(ws)

    if not overlap_keys:
        return 0

    per_week = round(total_hours / len(overlap_keys), 2)
    for ws in overlap_keys:
        buckets[ws]["total_hours"] = round(buckets[ws]["total_hours"] + per_week, 2)
        buckets[ws]["count"] += 1
        if action_meta and "actions" in buckets[ws]:
            aid = action_meta["act_id"]
            if aid not in buckets[ws]["actions"]:
                buckets[ws]["actions"][aid] = {
                    "act_id": aid,
                    "act_ref": action_meta["act_ref"],
                    "act_title": action_meta["act_title"],
                    "hours": 0.0,
                }
            buckets[ws]["actions"][aid]["hours"] = round(
                buckets[ws]["actions"][aid]["hours"] + per_week, 2
            )
    return len(overlap_keys)


def get_personal_dashboard(user_id: int) -> dict:
    db = get_db()
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

    kpi = db.execute(
        """
        SELECT
            COUNT(DISTINCT CASE WHEN a.act_status != 'Cancelled' THEN a.act_id END) AS total,
            SUM(CASE WHEN a.act_status NOT IN ('Done', 'Cancelled') THEN 1 ELSE 0 END) AS open_count,
            SUM(CASE WHEN a.act_status = 'Done' THEN 1 ELSE 0 END) AS done_count,
            SUM(CASE WHEN a.act_deadline < date('now') AND a.act_status NOT IN ('Done', 'Cancelled') THEN 1 ELSE 0 END) AS overdue_count,
            SUM(CASE WHEN a.act_deadline BETWEEN date('now') AND date('now', '+7 days') AND a.act_status NOT IN ('Done', 'Cancelled') THEN 1 ELSE 0 END) AS due_week_count
        FROM t_action a
        WHERE a.act_archived = 0
          AND (
            a.act_owner_id = ?
            OR EXISTS (SELECT 1 FROM t_assignment x WHERE x.asg_action_id = a.act_id AND x.asg_user_id = ?)
          )
        """,
        (user_id, user_id),
    ).fetchone()

    overdue_rows = db.execute(
        """
        SELECT DISTINCT
            a.act_id, a.act_ref, a.act_title, COALESCE(a.act_desc, '') AS act_desc,
            a.act_priority, a.act_status, a.act_deadline,
            a.act_created_at, a.act_updated_at,
            a.act_meeting_inst_id,
            COALESCE(t.top_name, '\u2014') AS topic_name,
            COALESCE(mtg.mtg_title, mi.min_title, '\u2014') AS meeting_title,
            COALESCE(ow.usr_display_name, '-') AS creator_name
        FROM t_action a
        LEFT JOIN t_topic t ON t.top_id = a.act_topic_id
        LEFT JOIN t_meeting_instance mi ON mi.min_id = a.act_meeting_inst_id
        LEFT JOIN t_meeting mtg ON mtg.mtg_id = mi.min_meeting_id
        LEFT JOIN t_user ow ON ow.usr_id = a.act_created_by
        WHERE a.act_archived = 0
          AND a.act_deadline < date('now')
          AND a.act_status NOT IN ('Done', 'Cancelled')
          AND (
            a.act_owner_id = ?
            OR EXISTS (SELECT 1 FROM t_assignment x WHERE x.asg_action_id = a.act_id AND x.asg_user_id = ?)
          )
        ORDER BY a.act_deadline ASC
        LIMIT 10
        """,
        (user_id, user_id),
    ).fetchall()

    due_soon_rows = db.execute(
        """
        SELECT DISTINCT
            a.act_id, a.act_ref, a.act_title, COALESCE(a.act_desc, '') AS act_desc,
            a.act_priority, a.act_status, a.act_deadline,
            a.act_created_at, a.act_updated_at,
            a.act_meeting_inst_id,
            COALESCE(t.top_name, '\u2014') AS topic_name,
            COALESCE(mtg.mtg_title, mi.min_title, '\u2014') AS meeting_title,
            COALESCE(ow.usr_display_name, '-') AS creator_name
        FROM t_action a
        LEFT JOIN t_topic t ON t.top_id = a.act_topic_id
        LEFT JOIN t_meeting_instance mi ON mi.min_id = a.act_meeting_inst_id
        LEFT JOIN t_meeting mtg ON mtg.mtg_id = mi.min_meeting_id
        LEFT JOIN t_user ow ON ow.usr_id = a.act_created_by
        WHERE a.act_archived = 0
          AND a.act_deadline BETWEEN date('now') AND date('now', '+7 day')
          AND a.act_status NOT IN ('Done', 'Cancelled')
          AND (
            a.act_owner_id = ?
            OR EXISTS (SELECT 1 FROM t_assignment x WHERE x.asg_action_id = a.act_id AND x.asg_user_id = ?)
          )
        ORDER BY a.act_deadline ASC
        LIMIT 10
        """,
        (user_id, user_id),
    ).fetchall()

    # All actions sorted by deadline for "By Deadline" tab
    # Show actions where the user is the Lead (act_owner_id) or is assigned.
    all_rows = db.execute(
        """
        SELECT DISTINCT
            a.act_id, a.act_ref, a.act_title, COALESCE(a.act_desc, '') AS act_desc,
            a.act_status, a.act_priority,
            a.act_deadline, a.act_completion_pct, a.act_start_date,
            a.act_topic_id, a.act_secondary_topic_id, a.act_created_at, a.act_updated_at,
            COALESCE(t.top_name, '\u2014') AS topic_name,
            tp2.top_name AS secondary_topic_name,
            m.min_title AS meeting_title,
            m.min_date  AS meeting_date,
            ow.usr_display_name AS creator_name,
            (SELECT COUNT(DISTINCT z.asg_user_id) FROM t_assignment z WHERE z.asg_action_id = a.act_id) AS asg_total
        FROM t_action a
        LEFT JOIN t_topic t ON t.top_id = a.act_topic_id
        LEFT JOIN t_topic tp2 ON tp2.top_id = a.act_secondary_topic_id
        LEFT JOIN t_meeting_instance m ON m.min_id = a.act_meeting_inst_id
        LEFT JOIN t_user ow ON ow.usr_id = a.act_created_by
        WHERE a.act_archived = 0
              AND (
                a.act_owner_id = ?
                OR EXISTS (SELECT 1 FROM t_assignment z2 WHERE z2.asg_action_id = a.act_id AND z2.asg_user_id = ?)
              )
        ORDER BY CASE WHEN a.act_deadline IS NULL THEN 1 ELSE 0 END,
                 a.act_deadline ASC
        """,
        (user_id, user_id),
    ).fetchall()

    recent_completed_rows = db.execute(
        """
        SELECT DISTINCT
            a.act_id, a.act_ref, a.act_title, COALESCE(a.act_desc, '') AS act_desc,
            a.act_status, a.act_priority,
            a.act_deadline, a.act_actual_date, a.act_updated_at,
            a.act_created_at,
            a.act_meeting_inst_id,
            COALESCE(t.top_name, '\u2014') AS topic_name,
            COALESCE(mtg.mtg_title, mi.min_title, '\u2014') AS meeting_title,
            COALESCE(ow.usr_display_name, '-') AS creator_name
        FROM t_action a
        LEFT JOIN t_topic t ON t.top_id = a.act_topic_id
        LEFT JOIN t_meeting_instance mi ON mi.min_id = a.act_meeting_inst_id
        LEFT JOIN t_meeting mtg ON mtg.mtg_id = mi.min_meeting_id
        LEFT JOIN t_user ow ON ow.usr_id = a.act_created_by
        WHERE a.act_archived = 0
          AND a.act_status = 'Done'
          AND DATE(COALESCE(a.act_actual_date, a.act_updated_at, a.act_created_at)) >= DATE('now', '-30 day')
          AND (
            a.act_owner_id = ?
            OR EXISTS (SELECT 1 FROM t_assignment x WHERE x.asg_action_id = a.act_id AND x.asg_user_id = ?)
          )
        ORDER BY COALESCE(a.act_actual_date, a.act_updated_at, a.act_created_at) DESC
        LIMIT 10
        """,
        (user_id, user_id),
    ).fetchall()

    status_rows = db.execute(
        f"""
        SELECT ({business_status_expr}) AS business_status, COUNT(*) AS count
        FROM t_action a
        WHERE a.act_archived = 0
          AND (
            a.act_owner_id = ?
            OR EXISTS (SELECT 1 FROM t_assignment x WHERE x.asg_action_id = a.act_id AND x.asg_user_id = ?)
          )
        GROUP BY ({business_status_expr})
        ORDER BY count DESC
        """,
        (user_id, user_id),
    ).fetchall()

    all_actions = [dict(r) for r in all_rows]


    # Group by topic for "By Topic" tab.
    from collections import defaultdict
    topic_groups: dict[str, dict] = {}

    def _add_to_group(row, key, topic_id):
        if key not in topic_groups:
            topic_groups[key] = {
                "topic_name": key,
                "topic_id": topic_id,
                "open": 0,
                "overdue": 0,
                "actions": [],
            }
        g = topic_groups[key]
        if row["act_status"] not in ("Done", "Cancelled"):
            g["open"] += 1
            if row["act_deadline"] and row["act_deadline"] < _today():
                g["overdue"] += 1
        g["actions"].append(row)

    for row in all_actions:
        _add_to_group(row, row["topic_name"], row["act_topic_id"])
        if row.get("act_secondary_topic_id"):
            sec_name = row.get("secondary_topic_name") or "\u2014"
            _add_to_group(row, sec_name, row["act_secondary_topic_id"])

    # Sort: named topics first, "—" last; within each, by overdue desc
    by_topic = sorted(
        topic_groups.values(),
        key=lambda g: (g["topic_name"] == "—", -g["overdue"], g["topic_name"]),
    )

    return {
        "kpis": {
            "total": int(kpi["total"] or 0),
            "open": int(kpi["open_count"] or 0),
            "done": int(kpi["done_count"] or 0),
            "overdue": int(kpi["overdue_count"] or 0),
            "due_this_week": int(kpi["due_week_count"] or 0),
        },
        "overdue_actions": [dict(row) for row in overdue_rows],
        "due_this_week": [dict(row) for row in due_soon_rows],
        "due_soon_actions": [dict(row) for row in due_soon_rows],
        "recent_completed": [dict(row) for row in recent_completed_rows],
        "status_distribution": {row["business_status"]: int(row["count"] or 0) for row in status_rows},
        "all_actions": all_actions,
        "by_topic": by_topic,
        "workload_forecast": get_workload_forecast(user_id),
    }


def _today() -> str:
    from datetime import date
    return date.today().isoformat()


def get_workload_forecast(user_id: int, weeks: int = 16) -> list[dict]:
    """Return forecasted workload in hours per week for the next `weeks` weeks."""
    from datetime import date

    db = get_db()
    rows = db.execute(
        """
        SELECT
            a.act_id, a.act_ref, a.act_title,
            a.act_status,
            a.act_start_date AS effective_start,
            a.act_deadline AS effective_end,
            x.asg_estimated_hours
        FROM t_action a
        JOIN t_assignment x
          ON x.asg_action_id = a.act_id
         AND x.asg_user_id = ?
        WHERE a.act_archived = 0
          AND a.act_status NOT IN ('Done', 'Cancelled')
          AND a.act_deadline IS NOT NULL
          AND x.asg_estimated_hours IS NOT NULL
        """,
        (user_id,),
    ).fetchall()

    bucket_keys, buckets = _build_week_buckets(weeks)
    today = date.today()

    for row in rows:
        end_date = _parse_iso_date(row["effective_end"])
        if not end_date:
            continue

        start_date = _parse_iso_date(row["effective_start"]) or today
        hours = row["asg_estimated_hours"]

        action_meta = {
            "act_id": row["act_id"],
            "act_ref": row["act_ref"],
            "act_title": row["act_title"],
        }
        _spread_hours_into_buckets(buckets, hours, start_date, end_date, action_meta)

    result = []
    for ws in bucket_keys:
        b = buckets[ws]
        result.append({
            **b,
            "actions": list(b["actions"].values()),
        })
    return result


def get_team_workload_forecast(team_id: int, weeks: int = 16) -> list:
    """Return per-action workload aggregated across team members only."""
    from datetime import date

    db = get_db()

    # Sum hours from team members only, grouped by action
    rows = db.execute(
        """
        SELECT
            a.act_id,
            a.act_ref,
            a.act_title,
            SUM(asg.asg_estimated_hours) AS total_hours,
            a.act_start_date AS effective_start,
            a.act_deadline   AS effective_end
        FROM t_user_team utm
        JOIN t_user u ON u.usr_id = utm.utm_user_id
        JOIN t_assignment asg
          ON asg.asg_user_id = u.usr_id
        JOIN t_action a ON a.act_id = asg.asg_action_id
        WHERE utm.utm_team_id = ?
          AND u.usr_active = 1
          AND a.act_archived = 0
          AND a.act_status NOT IN ('Done', 'Cancelled')
          AND a.act_deadline IS NOT NULL
          AND asg.asg_estimated_hours IS NOT NULL
        GROUP BY a.act_id, a.act_ref, a.act_title
        """,
        (team_id,),
    ).fetchall()

    bucket_keys, buckets = _build_week_buckets(weeks)
    today = date.today()

    for row in rows:
        end_date = _parse_iso_date(row["effective_end"])
        if not end_date:
            continue
        start_date = _parse_iso_date(row["effective_start"]) or today
        hours = float(row["total_hours"] or 0)
        if hours <= 0:
            continue
        action_meta = {
            "act_id":    row["act_id"],
            "act_ref":   row["act_ref"],
            "act_title": row["act_title"],
        }
        _spread_hours_into_buckets(buckets, hours, start_date, end_date, action_meta)

    result = []
    for ws in bucket_keys:
        b = buckets[ws]
        result.append({
            **b,
            "actions": list(b["actions"].values()),
        })
    return result


def get_team_dashboard(team_id: int) -> dict:
    db = get_db()
    # Use t_team (departments were replaced by teams in v2.6)
    dept = db.execute(
        "SELECT tea_id AS dep_id, tea_code AS dep_code, tea_name_en AS dep_name_en, tea_name_cn AS dep_name_cn FROM t_team WHERE tea_id = ?",
        (team_id,),
    ).fetchone()
    if not dept:
        raise ValueError("team not found")

    # Exclude actions from private meeting series / private occurrences
    _private_excl = """
        AND NOT EXISTS (
            SELECT 1 FROM t_meeting_instance mi2
            LEFT JOIN t_meeting ms2 ON ms2.mtg_id = mi2.min_meeting_id
            WHERE mi2.min_id = a.act_meeting_inst_id
              AND (COALESCE(mi2.min_visibility, 'public') = 'private'
                   OR COALESCE(ms2.mtg_visibility, 'public') = 'private')
        )
    """

    kpi = db.execute(
        f"""
        SELECT
            COUNT(CASE WHEN act_status != 'Cancelled' THEN 1 END) AS total,
            SUM(CASE WHEN act_status NOT IN ('Done', 'Cancelled') THEN 1 ELSE 0 END) AS open_count,
            SUM(CASE WHEN act_status = 'Done' THEN 1 ELSE 0 END) AS done_count,
            SUM(CASE WHEN act_deadline < date('now') AND act_status NOT IN ('Done', 'Cancelled') THEN 1 ELSE 0 END) AS overdue_count
                FROM t_action a
                WHERE a.act_archived = 0
                    {_private_excl}
                    AND (
                        NOT EXISTS (
                            SELECT 1 FROM t_assignment al
                            WHERE al.asg_action_id = a.act_id AND INSTR(',' || al.asg_role || ',', ',Lead,') > 0
                        )
                        OR EXISTS (
                            SELECT 1 FROM t_assignment al
                            JOIN t_user_team ut ON ut.utm_user_id = al.asg_user_id
                            WHERE al.asg_action_id = a.act_id
                              AND INSTR(',' || al.asg_role || ',', ',Lead,') > 0
                              AND ut.utm_team_id = ?
                        )
                    )
        """,
        (team_id,),
    ).fetchone()

    status_rows = db.execute(
        f"""
                SELECT a.act_status, COUNT(*) AS count
                FROM t_action a
                WHERE a.act_archived = 0
                    AND a.act_status != 'Cancelled'
                    {_private_excl}
                    AND (
                        NOT EXISTS (
                            SELECT 1 FROM t_assignment al
                            WHERE al.asg_action_id = a.act_id AND INSTR(',' || al.asg_role || ',', ',Lead,') > 0
                        )
                        OR EXISTS (
                            SELECT 1 FROM t_assignment al
                            JOIN t_user_team ut ON ut.utm_user_id = al.asg_user_id
                            WHERE al.asg_action_id = a.act_id
                              AND INSTR(',' || al.asg_role || ',', ',Lead,') > 0
                              AND ut.utm_team_id = ?
                        )
                    )
                GROUP BY a.act_status
        ORDER BY count DESC
        """,
        (team_id,),
    ).fetchall()

    priority_rows = db.execute(
        f"""
                SELECT a.act_priority, COUNT(*) AS count
                FROM t_action a
                WHERE a.act_archived = 0
                    AND a.act_status != 'Cancelled'
                    {_private_excl}
                    AND (
                        NOT EXISTS (
                            SELECT 1 FROM t_assignment al
                            WHERE al.asg_action_id = a.act_id AND INSTR(',' || al.asg_role || ',', ',Lead,') > 0
                        )
                        OR EXISTS (
                            SELECT 1 FROM t_assignment al
                            JOIN t_user_team ut ON ut.utm_user_id = al.asg_user_id
                            WHERE al.asg_action_id = a.act_id
                              AND INSTR(',' || al.asg_role || ',', ',Lead,') > 0
                              AND ut.utm_team_id = ?
                        )
                    )
                GROUP BY a.act_priority
                ORDER BY CASE a.act_priority
            WHEN 'Critical' THEN 1
            WHEN 'High' THEN 2
            WHEN 'Medium' THEN 3
            ELSE 4
        END
        """,
        (team_id,),
    ).fetchall()

    overdue_rows = db.execute(
        f"""
                SELECT a.act_id, a.act_ref, a.act_title, a.act_priority, a.act_status, a.act_deadline
                FROM t_action a
                WHERE a.act_archived = 0
                    AND a.act_deadline < date('now')
                    AND a.act_status NOT IN ('Done', 'Cancelled')
                    {_private_excl}
                    AND (
                        NOT EXISTS (
                            SELECT 1 FROM t_assignment al
                            WHERE al.asg_action_id = a.act_id AND INSTR(',' || al.asg_role || ',', ',Lead,') > 0
                        )
                        OR EXISTS (
                            SELECT 1 FROM t_assignment al
                            JOIN t_user_team ut ON ut.utm_user_id = al.asg_user_id
                            WHERE al.asg_action_id = a.act_id
                              AND INSTR(',' || al.asg_role || ',', ',Lead,') > 0
                              AND ut.utm_team_id = ?
                        )
                    )
                ORDER BY a.act_deadline ASC
        LIMIT 10
        """,
        (team_id,),
    ).fetchall()

    # Per-member breakdown via t_user_team
    member_rows = db.execute(
        f"""
        SELECT
            u.usr_id,
            u.usr_display_name,
            COUNT(DISTINCT CASE WHEN a.act_status != 'Cancelled' THEN a.act_id END) AS total,
            SUM(CASE WHEN a.act_status NOT IN ('Done','Cancelled') THEN 1 ELSE 0 END) AS open,
            SUM(CASE WHEN a.act_deadline < date('now') AND a.act_status NOT IN ('Done','Cancelled') THEN 1 ELSE 0 END) AS overdue,
            SUM(CASE WHEN a.act_deadline BETWEEN date('now') AND date('now','+7 days') AND a.act_status NOT IN ('Done','Cancelled') THEN 1 ELSE 0 END) AS due_this_week
        FROM t_user_team utm
        JOIN t_user u ON u.usr_id = utm.utm_user_id
        LEFT JOIN t_assignment x ON x.asg_user_id = u.usr_id
        LEFT JOIN t_action a ON a.act_id = x.asg_action_id AND a.act_archived = 0
            AND NOT EXISTS (
                SELECT 1 FROM t_meeting_instance mi2
                LEFT JOIN t_meeting ms2 ON ms2.mtg_id = mi2.min_meeting_id
                WHERE mi2.min_id = a.act_meeting_inst_id
                  AND (COALESCE(mi2.min_visibility, 'public') = 'private'
                       OR COALESCE(ms2.mtg_visibility, 'public') = 'private')
            )
        WHERE utm.utm_team_id = ? AND u.usr_active = 1
        GROUP BY u.usr_id, u.usr_display_name
        ORDER BY overdue DESC, open DESC
        """,
        (team_id,),
    ).fetchall()

    # All actions in the team with assigned member names
    all_action_rows = db.execute(
        f"""
        SELECT
            a.act_id, a.act_ref, a.act_title, a.act_status, a.act_priority,
            a.act_deadline, a.act_completion_pct,
            a.act_topic_id, a.act_created_at,
            m.min_title AS meeting_title,
            m.min_date  AS meeting_date,
            tp.top_name AS topic,
            GROUP_CONCAT(u.usr_display_name, ', ') AS assignees,
            (SELECT COUNT(DISTINCT z.asg_user_id) FROM t_assignment z WHERE z.asg_action_id = a.act_id) AS asg_total
        FROM t_action a
        LEFT JOIN t_topic tp ON tp.top_id = a.act_topic_id
        LEFT JOIN t_meeting_instance m ON m.min_id = a.act_meeting_inst_id
        LEFT JOIN t_assignment x ON x.asg_action_id = a.act_id
        LEFT JOIN t_user u ON u.usr_id = x.asg_user_id
        WHERE a.act_archived = 0
          AND a.act_status != 'Cancelled'
          {_private_excl}
          AND (
                NOT EXISTS (
                    SELECT 1 FROM t_assignment al
                    WHERE al.asg_action_id = a.act_id AND INSTR(',' || al.asg_role || ',', ',Lead,') > 0
                )
                OR EXISTS (
                    SELECT 1 FROM t_assignment al
                    JOIN t_user_team ut ON ut.utm_user_id = al.asg_user_id
                    WHERE al.asg_action_id = a.act_id
                      AND INSTR(',' || al.asg_role || ',', ',Lead,') > 0
                      AND ut.utm_team_id = ?
                )
          )
        GROUP BY a.act_id
        ORDER BY a.act_deadline ASC NULLS LAST
        """,
        (team_id,),
    ).fetchall()

    return {
        "team": dict(dept),
        "kpis": {
            "total": int(kpi["total"] or 0),
            "open": int(kpi["open_count"] or 0),
            "done": int(kpi["done_count"] or 0),
            "overdue": int(kpi["overdue_count"] or 0),
        },
        "status_distribution": {row["act_status"]: int(row["count"] or 0) for row in status_rows},
        "priority_distribution": {row["act_priority"]: int(row["count"] or 0) for row in priority_rows},
        "overdue_actions": [dict(row) for row in overdue_rows],
        "members": [dict(row) for row in member_rows],
        "all_actions": [dict(row) for row in all_action_rows],
        "workload_forecast": get_team_workload_forecast(team_id),
    }


def get_team_leader_dashboard(team_id: int, viewer_user_id: int) -> dict:
    """Return team dashboard data with masking for private actions not visible to the team leader."""
    db = get_db()
    team = db.execute(
        "SELECT tea_id AS dep_id, tea_code AS dep_code, tea_name_en AS dep_name_en, tea_name_cn AS dep_name_cn FROM t_team WHERE tea_id = ?",
        (team_id,),
    ).fetchone()
    if not team:
        raise ValueError("team not found")

    team_scope_sql = """
      (
          (
              a.act_created_by IN (SELECT utm_user_id FROM t_user_team WHERE utm_team_id = ?)
              AND NOT EXISTS (
                  SELECT 1 FROM t_assignment al
                  WHERE al.asg_action_id = a.act_id
                    AND INSTR(',' || al.asg_role || ',', ',Lead,') > 0
              )
          )
          OR EXISTS (
              SELECT 1
              FROM t_assignment al
              JOIN t_user_team ut ON ut.utm_user_id = al.asg_user_id
              WHERE al.asg_action_id = a.act_id
                AND INSTR(',' || al.asg_role || ',', ',Lead,') > 0
                AND ut.utm_team_id = ?
          )
      )
    """

    kpi = db.execute(
        f"""
        SELECT
            COUNT(DISTINCT CASE WHEN a.act_status != 'Cancelled' THEN a.act_id END) AS total,
            SUM(CASE WHEN a.act_status NOT IN ('Done', 'Cancelled') THEN 1 ELSE 0 END) AS open_count,
            SUM(CASE WHEN a.act_status = 'Done' THEN 1 ELSE 0 END) AS done_count,
            SUM(CASE WHEN a.act_deadline < date('now') AND a.act_status NOT IN ('Done', 'Cancelled') THEN 1 ELSE 0 END) AS overdue_count
        FROM t_action a
        WHERE a.act_archived = 0
          AND {team_scope_sql}
        """,
        (team_id, team_id),
    ).fetchone()

    member_rows = db.execute(
        """
        SELECT
            u.usr_id,
            u.usr_display_name,
            COUNT(DISTINCT CASE WHEN a.act_status != 'Cancelled' THEN a.act_id END) AS total,
            SUM(CASE WHEN a.act_status NOT IN ('Done','Cancelled') THEN 1 ELSE 0 END) AS open,
            SUM(CASE WHEN a.act_deadline < date('now') AND a.act_status NOT IN ('Done','Cancelled') THEN 1 ELSE 0 END) AS overdue,
            SUM(CASE WHEN a.act_deadline BETWEEN date('now') AND date('now','+7 days') AND a.act_status NOT IN ('Done','Cancelled') THEN 1 ELSE 0 END) AS due_this_week
        FROM t_user_team utm
        JOIN t_user u ON u.usr_id = utm.utm_user_id
        LEFT JOIN t_assignment x ON x.asg_user_id = u.usr_id
        LEFT JOIN t_action a ON a.act_id = x.asg_action_id AND a.act_archived = 0
        WHERE utm.utm_team_id = ? AND u.usr_active = 1
        GROUP BY u.usr_id, u.usr_display_name
        ORDER BY overdue DESC, open DESC
        """,
        (team_id,),
    ).fetchall()

    all_rows = db.execute(
        f"""
        SELECT
            a.act_id,
            a.act_ref,
            a.act_title,
            COALESCE(a.act_desc, '') AS act_desc,
            a.act_status,
            a.act_priority,
            a.act_deadline,
            a.act_meeting_inst_id,
            COALESCE(tp.top_name, '-') AS topic_name,
            COALESCE(ow.usr_display_name, '-') AS owner_name,
            COALESCE(ms.mtg_title, m.min_title, '-') AS meeting_series_title,
            COALESCE(m.min_visibility, 'public') AS meeting_visibility,
            CASE
                WHEN a.act_meeting_inst_id IS NULL THEN 1
                WHEN COALESCE(m.min_visibility, 'public') <> 'private' THEN 1
                WHEN m.min_created_by = ? THEN 1
                WHEN a.act_created_by = ? THEN 1
                WHEN EXISTS (
                    SELECT 1 FROM t_assignment ap
                    WHERE ap.asg_action_id = a.act_id AND ap.asg_user_id = ?
                ) THEN 1
                WHEN EXISTS (
                    SELECT 1 FROM t_meeting_participant mp
                    WHERE mp.mpa_instance_id = m.min_id AND mp.mpa_user_id = ?
                ) THEN 1
                ELSE 0
            END AS can_view_details,
            GROUP_CONCAT(DISTINCT u.usr_display_name) AS assignees
        FROM t_action a
        LEFT JOIN t_meeting_instance m ON m.min_id = a.act_meeting_inst_id
        LEFT JOIN t_meeting ms ON ms.mtg_id = m.min_meeting_id
        LEFT JOIN t_topic tp ON tp.top_id = a.act_topic_id
        LEFT JOIN t_user ow ON ow.usr_id = a.act_created_by
        LEFT JOIN t_assignment x ON x.asg_action_id = a.act_id
        LEFT JOIN t_user u ON u.usr_id = x.asg_user_id
        WHERE a.act_archived = 0
          AND a.act_status != 'Cancelled'
          AND {team_scope_sql}
        GROUP BY a.act_id
        ORDER BY CASE WHEN a.act_deadline IS NULL THEN 1 ELSE 0 END, a.act_deadline ASC, a.act_id DESC
        """,
        (viewer_user_id, viewer_user_id, viewer_user_id, viewer_user_id, team_id, team_id),
    ).fetchall()

    overdue_rows = []
    all_actions = []
    for row in all_rows:
        entry = dict(row)
        is_private_meeting = str(entry.get("meeting_visibility") or "public") == "private"
        can_view = bool(entry.get("can_view_details"))
        masked = is_private_meeting and not can_view
        if masked:
            entry["act_title"] = "Private action"
            entry["act_desc"] = "Private action details are hidden"
            entry["assignees"] = None
            entry["owner_name"] = "-"
            entry["topic_name"] = "-"
        entry["is_masked_private"] = masked
        all_actions.append(entry)

        if entry.get("act_deadline") and entry.get("act_status") not in ("Done", "Cancelled") and entry["act_deadline"] < _today():
            overdue_rows.append({
                "act_id": entry["act_id"],
                "act_ref": entry["act_ref"],
                "act_title": entry["act_title"],
                "act_desc": entry["act_desc"],
                "act_priority": entry["act_priority"],
                "act_status": entry["act_status"],
                "act_deadline": entry["act_deadline"],
                "act_meeting_inst_id": entry.get("act_meeting_inst_id"),
                "meeting_series_title": entry.get("meeting_series_title"),
                "topic_name": entry.get("topic_name") or "-",
                "owner_name": entry.get("owner_name") or "-",
                "assignees": entry.get("assignees"),
                "is_masked_private": entry["is_masked_private"],
            })

    overdue_by_deadline = sorted(
        overdue_rows,
        key=lambda row: ((row.get("act_deadline") is None), row.get("act_deadline") or "", int(row.get("act_id") or 0)),
    )
    overdue_by_owner = sorted(
        overdue_rows,
        key=lambda row: (str(row.get("owner_name") or "-").lower(), row.get("act_deadline") or "", int(row.get("act_id") or 0)),
    )
    overdue_by_category = sorted(
        overdue_rows,
        key=lambda row: (str(row.get("topic_name") or "-").lower(), row.get("act_deadline") or "", int(row.get("act_id") or 0)),
    )

    # Group all actions by lead (owner_name)
    lead_groups: dict[str, dict] = {}
    for entry in all_actions:
        lead_name = str(entry.get("owner_name") or "-")
        if lead_name not in lead_groups:
            lead_groups[lead_name] = {"lead_name": lead_name, "open": 0, "overdue": 0, "actions": []}
        g = lead_groups[lead_name]
        if entry.get("act_status") not in ("Done", "Cancelled"):
            g["open"] += 1
            if entry.get("act_deadline") and entry["act_deadline"] < _today():
                g["overdue"] += 1
        g["actions"].append(entry)
    by_lead = sorted(lead_groups.values(), key=lambda g: (-g["overdue"], g["lead_name"].lower()))

    # Group all actions by category (topic_name)
    category_groups: dict[str, dict] = {}
    for entry in all_actions:
        topic_name = str(entry.get("topic_name") or "-")
        if topic_name not in category_groups:
            category_groups[topic_name] = {"topic_name": topic_name, "open": 0, "overdue": 0, "actions": []}
        g = category_groups[topic_name]
        if entry.get("act_status") not in ("Done", "Cancelled"):
            g["open"] += 1
            if entry.get("act_deadline") and entry["act_deadline"] < _today():
                g["overdue"] += 1
        g["actions"].append(entry)
    by_category = sorted(
        category_groups.values(),
        key=lambda g: (g["topic_name"] == "-", -g["overdue"], g["topic_name"].lower()),
    )

    return {
        "team": dict(team),
        "kpis": {
            "total": int(kpi["total"] or 0),
            "open": int(kpi["open_count"] or 0),
            "done": int(kpi["done_count"] or 0),
            "overdue": int(kpi["overdue_count"] or 0),
        },
        "members": [dict(row) for row in member_rows],
        "all_actions": all_actions,
        "overdue_actions": overdue_rows[:10],
        "overdue_by_deadline": overdue_by_deadline,
        "overdue_by_owner": overdue_by_owner,
        "overdue_by_category": overdue_by_category,
        "by_lead": by_lead,
        "by_category": by_category,
    }


def get_all_teams_summary() -> list[dict]:
    """Return KPI snapshot for every active team (for the all-teams overview panel)."""
    db = get_db()
    # Use t_team (departments replaced by teams in v2.6)
    teams = db.execute(
        "SELECT tea_id AS dep_id, tea_code AS dep_code, tea_name_en AS dep_name_en FROM t_team WHERE tea_active = 1 ORDER BY tea_name_en"
    ).fetchall()

    result = []
    for team in teams:
        kpi = db.execute(
            (
                """
                SELECT
                    COUNT(DISTINCT CASE WHEN a.act_status != 'Cancelled' THEN a.act_id END) AS total,
                    COUNT(DISTINCT CASE WHEN a.act_status NOT IN ('Done','Cancelled') THEN a.act_id END) AS open_count,
                    COUNT(DISTINCT CASE WHEN a.act_status = 'Done' THEN a.act_id END) AS done_count,
                    COUNT(DISTINCT CASE WHEN a.act_deadline < date('now') AND a.act_status NOT IN ('Done','Cancelled') THEN a.act_id END) AS overdue_count,
                    (SELECT COUNT(DISTINCT utm2.utm_user_id)
                     FROM t_user_team utm2
                     JOIN t_user u2 ON u2.usr_id = utm2.utm_user_id AND u2.usr_active = 1
                     WHERE utm2.utm_team_id = t.tea_id) AS member_count
                FROM t_team t
                LEFT JOIN t_action a ON a.act_archived = 0
                    AND (
                        NOT EXISTS (
                            SELECT 1 FROM t_assignment al
                            WHERE al.asg_action_id = a.act_id AND INSTR(',' || al.asg_role || ',', ',Lead,') > 0
                        )
                        OR EXISTS (
                            SELECT 1 FROM t_assignment al
                            JOIN t_user_team ut ON ut.utm_user_id = al.asg_user_id
                            WHERE al.asg_action_id = a.act_id
                              AND INSTR(',' || al.asg_role || ',', ',Lead,') > 0
                              AND ut.utm_team_id = t.tea_id
                        )
                    )
                WHERE t.tea_id = ?
                """
            ),
            (team["dep_id"],)
        ).fetchone()

        total = int(kpi["total"] or 0)
        done  = int(kpi["done_count"] or 0)
        pct   = round(done / total * 100) if total else 0

        result.append({
            "team_id":    team["dep_id"],
            "team_code":  team["dep_code"],
            "team_name":  team["dep_name_en"],
            "total":       total,
            "open":        int(kpi["open_count"] or 0),
            "done":        done,
            "overdue":     int(kpi["overdue_count"] or 0),
            "members":     int(kpi["member_count"] or 0),
            "pct_done":    pct,
        })
    return result


def get_all_teams_detail_summary() -> list[dict]:
    """Return all active teams with KPIs, team leader name, and member names."""
    db = get_db()
    teams = db.execute(
        """
        SELECT t.tea_id, t.tea_code, t.tea_name_en, t.tea_name_cn,
               t.tea_leader_user_id,
               COALESCE(u.usr_display_name, '-') AS leader_name
        FROM t_team t
        LEFT JOIN t_user u ON u.usr_id = t.tea_leader_user_id
        WHERE t.tea_active = 1
        ORDER BY t.tea_name_en
        """
    ).fetchall()

    result = []

    for team in teams:
        team_id = team["tea_id"]

        # Count actions assigned to team members (via t_assignment/t_user_team) or with act_team_id = team_id
        # Only count actions linked to a meeting (act_meeting_inst_id IS NOT NULL)
        kpi = db.execute(
            """
            SELECT
                COUNT(DISTINCT CASE WHEN a.act_status != 'Cancelled' THEN a.act_id END) AS total,
                COUNT(DISTINCT CASE WHEN a.act_status NOT IN ('Done','Cancelled') THEN a.act_id END) AS open_count,
                COUNT(DISTINCT CASE WHEN a.act_status = 'Done' THEN a.act_id END) AS done_count,
                COUNT(DISTINCT CASE WHEN a.act_deadline < date('now') AND a.act_status NOT IN ('Done','Cancelled') THEN a.act_id END) AS overdue_count
            FROM t_action a
            WHERE a.act_archived = 0
              AND a.act_meeting_inst_id IS NOT NULL
              AND (
                a.act_team_id = ?
                OR EXISTS (
                    SELECT 1 FROM t_assignment x
                    JOIN t_user_team ut ON ut.utm_user_id = x.asg_user_id
                    WHERE x.asg_action_id = a.act_id AND ut.utm_team_id = ?
                )
              )
            """,
            (team_id, team_id),
        ).fetchone()

        # Decision count for this team (decisions linked to meetings whose actions belong to the team)
        decision_row = db.execute(
            """
            SELECT COUNT(DISTINCT d.mdc_id) AS decision_count
            FROM t_meeting_decision d
            LEFT JOIN t_meeting_instance mi ON mi.min_id = COALESCE(d.mdc_instance_id, d.mdc_meeting_id)
            LEFT JOIN t_action a ON a.act_meeting_inst_id = mi.min_id AND a.act_archived = 0
            WHERE COALESCE(d.mdc_deleted_at, '') = ''
              AND (
                a.act_team_id = ?
                OR EXISTS (
                    SELECT 1 FROM t_assignment x
                    JOIN t_user_team ut ON ut.utm_user_id = x.asg_user_id
                    WHERE x.asg_action_id = a.act_id AND ut.utm_team_id = ?
                )
              )
            """,
            (team_id, team_id),
        ).fetchone()

        member_rows = db.execute(
            """
            SELECT u.usr_display_name
            FROM t_user_team utm
            JOIN t_user u ON u.usr_id = utm.utm_user_id AND u.usr_active = 1
            WHERE utm.utm_team_id = ?
            ORDER BY u.usr_display_name
            """,
            (team_id,),
        ).fetchall()

        total = int(kpi["total"] or 0)
        done = int(kpi["done_count"] or 0)
        pct = round(done / total * 100) if total else 0

        result.append({
            "team_id": team_id,
            "team_code": team["tea_code"],
            "team_name": team["tea_name_en"],
            "team_name_cn": team["tea_name_cn"],
            "leader_name": team["leader_name"],
            "member_names": [r["usr_display_name"] for r in member_rows],
            "member_count": len(member_rows),
            "total": total,
            "open": int(kpi["open_count"] or 0),
            "done": done,
            "overdue": int(kpi["overdue_count"] or 0),
            "decision_count": int(decision_row["decision_count"] or 0),
            "pct_done": pct,
        })
    return result


def get_decision_dashboard(
    scope: str = "personal",
    user_id: int | None = None,
    team_id: int | None = None,
    topic_id: int | None = None,
    limit: int = 8,
) -> dict:
    """Return decision KPIs and recent decisions for dashboard widgets.

    Scope values:
    - personal: decisions created by the current user
    - team: decisions created by users in the given team
    - topic: decisions linked to the given business theme (primary/secondary)
    - all: all visible decisions
    """
    db = get_db()
    decision_cols = {row[1] for row in db.execute("PRAGMA table_info(t_meeting_decision)").fetchall()}
    safe_scope = str(scope or "personal").strip().lower()
    if safe_scope not in {"personal", "team", "topic", "all"}:
        safe_scope = "personal"

    filters: list[str] = [
        "COALESCE(d.mdc_deleted_at, 0) = 0",
        "datetime(COALESCE(d.mdc_created_at, '1970-01-01')) >= datetime('now', '-30 days')",
    ]
    params: list[object] = []

    if safe_scope == "personal":
        if not user_id:
            raise ValueError("user_id is required for personal scope")
        filters.append("d.mdc_created_by = ?")
        params.append(int(user_id))
    elif safe_scope == "team":
        if not team_id:
            raise ValueError("team_id is required for team scope")
        filters.append(
            "EXISTS (SELECT 1 FROM t_user_team ut WHERE ut.utm_user_id = d.mdc_created_by AND ut.utm_team_id = ?)"
        )
        params.append(int(team_id))
    elif safe_scope == "topic":
        if not topic_id:
            raise ValueError("topic_id is required for topic scope")
        filters.append("(d.mdc_category_id = ? OR d.mdc_secondary_category_id = ?)")
        params.extend([int(topic_id), int(topic_id)])

    where_sql = " AND ".join(filters)
    status_expr = "CASE WHEN d.mdc_status IN ('Deleted', 'Cancelled', 'Rejected', 'Withdrawn', 'Obsolete', 'Expired') THEN 'Closed' ELSE 'Active' END"
    expires_expr = "d.mdc_expires_at" if "mdc_expires_at" in decision_cols else "NULL AS mdc_expires_at"
    status_changed_expr = "d.mdc_status_changed_at" if "mdc_status_changed_at" in decision_cols else "NULL AS mdc_status_changed_at"

    kpi_row = db.execute(
        f"""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN {status_expr} = 'Active' THEN 1 ELSE 0 END) AS active,
            SUM(CASE WHEN {status_expr} = 'Closed' THEN 1 ELSE 0 END) AS closed
        FROM t_meeting_decision d
        WHERE {where_sql}
        """,
        tuple(params),
    ).fetchone()

    recent_rows = db.execute(
        f"""
        SELECT
            d.mdc_id,
            d.mdc_title,
            d.mdc_body,
            d.mdc_status AS mdc_status,
            {status_expr} AS mdc_status_family,
            d.mdc_created_at,
            d.mdc_updated_at,
            {expires_expr},
            {status_changed_expr},
            d.mdc_category_id,
            d.mdc_secondary_category_id,
            COALESCE(tc.top_name, ts.top_name, '-') AS category_name,
            COALESCE(u.usr_display_name, '-') AS creator_name,
            COALESCE(mtg.mtg_title, mi.min_title, '-') AS series_title,
            COALESCE(mtg.mtg_title, mi.min_title, '-') AS meeting_title
        FROM t_meeting_decision d
        LEFT JOIN t_user u ON u.usr_id = d.mdc_created_by
        LEFT JOIN t_topic tc ON tc.top_id = d.mdc_category_id
        LEFT JOIN t_topic ts ON ts.top_id = d.mdc_secondary_category_id
        LEFT JOIN t_meeting_instance mi ON mi.min_id = COALESCE(d.mdc_instance_id, d.mdc_meeting_id)
        LEFT JOIN t_meeting mtg ON mtg.mtg_id = mi.min_meeting_id
        WHERE {where_sql}
        ORDER BY d.mdc_created_at DESC, d.mdc_id DESC
        LIMIT ?
        """,
        tuple([*params, max(1, min(int(limit), 30))]),
    ).fetchall()

    return {
        "scope": safe_scope,
        "kpis": {
            "total": int(kpi_row["total"] or 0),
            "active": int(kpi_row["active"] or 0),
            "closed": int(kpi_row["closed"] or 0),
            "published": int(kpi_row["active"] or 0),
            "expired": int(kpi_row["closed"] or 0),
        },
        "recent": [dict(row) for row in recent_rows],
    }