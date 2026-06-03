"""Category dashboard service — K50–K54 KPIs."""
from __future__ import annotations

from actionhub.middleware.db import get_db
from actionhub.dashboard.service import (
    _build_week_buckets,
    _parse_iso_date,
)


def get_all_topics_summary() -> list[dict]:
    """Return all active topics with aggregated action/meeting counts."""
    db = get_db()
    # Determine which column to use for meeting-topic linkage
    mi_cols = {row[1] for row in db.execute("PRAGMA table_info(t_meeting_instance)").fetchall()}
    if "min_category_id" in mi_cols and "min_topic_id" in mi_cols:
        meeting_topic_expr = "COALESCE(m.min_category_id, m.min_topic_id)"
    elif "min_category_id" in mi_cols:
        meeting_topic_expr = "m.min_category_id"
    else:
        meeting_topic_expr = "m.min_topic_id"
    rows = db.execute(
        f"""
        SELECT
            t.top_id, COALESCE(t.top_code, CAST(t.top_id AS TEXT), t.top_name) AS top_code, t.top_name, t.top_desc,
            COUNT(DISTINCT CASE WHEN a.act_status != 'Cancelled' THEN a.act_id END)                                    AS total,
            COUNT(DISTINCT CASE WHEN a.act_status NOT IN ('Done','Cancelled') THEN a.act_id END)                     AS open,
                COUNT(DISTINCT CASE WHEN a.act_status = 'In Progress' THEN a.act_id END)                                 AS in_progress,
            COUNT(DISTINCT CASE WHEN a.act_deadline < date('now')
                      AND a.act_status NOT IN ('Done','Cancelled') THEN a.act_id END)                               AS overdue,
            COUNT(DISTINCT CASE WHEN a.act_status = 'Done' THEN a.act_id END)                                        AS done,
            (SELECT COUNT(*) FROM t_meeting_instance m WHERE {meeting_topic_expr} = t.top_id) AS meeting_count,
            (SELECT COUNT(DISTINCT d.mdc_id) FROM t_meeting_decision d
                LEFT JOIN t_meeting_instance mi2 ON mi2.min_id = COALESCE(d.mdc_instance_id, d.mdc_meeting_id)
                WHERE (mi2.min_topic_id = t.top_id OR mi2.min_category_id = t.top_id)
                  AND COALESCE(d.mdc_deleted_at, '') = '') AS decision_count
        FROM t_topic t
        LEFT JOIN t_action a ON (a.act_topic_id = t.top_id OR a.act_secondary_topic_id = t.top_id)
                                AND a.act_archived = 0
                                AND a.act_meeting_inst_id IS NOT NULL
        WHERE t.top_active = 1
        GROUP BY t.top_id
        ORDER BY t.top_name
        """
    ).fetchall()
    return [dict(r) for r in rows]


def get_topic_dashboard(topic_id: int) -> dict:
    db = get_db()

    topic = db.execute(
        "SELECT top_id, COALESCE(top_code, CAST(top_id AS TEXT), top_name) AS top_code, top_name, top_desc FROM t_topic WHERE top_id = ?",
        (topic_id,),
    ).fetchone()
    if not topic:
        raise ValueError("topic not found")

    # K50–K53
    kpi = db.execute(
        """
        SELECT
            SUM(CASE WHEN act_status NOT IN ('Done','Cancelled') THEN 1 ELSE 0 END)  AS k50_open,
            SUM(CASE WHEN act_status = 'In Progress' THEN 1 ELSE 0 END)              AS in_progress,
            SUM(CASE WHEN act_deadline < date('now')
                      AND act_status NOT IN ('Done','Cancelled') THEN 1 ELSE 0 END) AS k51_overdue,
            SUM(CASE WHEN act_status = 'Done' THEN 1 ELSE 0 END)                    AS k52_done,
            SUM(CASE WHEN act_status = 'Done'
                      AND act_actual_date IS NOT NULL
                      AND act_actual_date <= act_deadline THEN 1 ELSE 0 END)        AS k53_on_time_done,
            COUNT(CASE WHEN act_status != 'Cancelled' THEN 1 END)                    AS total
        FROM t_action
                WHERE (act_topic_id = ? OR act_secondary_topic_id = ?)
          AND act_archived = 0
        """,
                (topic_id, topic_id),
    ).fetchone()

    done_count = int(kpi["k52_done"] or 0)
    on_time_done = int(kpi["k53_on_time_done"] or 0)
    on_time_rate = round(on_time_done / done_count * 100, 1) if done_count else None

    # K54 Workload — total assignment hours per assignee in this topic
    workload_rows = db.execute(
        """
        SELECT
            u.usr_display_name AS name,
            ROUND(SUM(asg.asg_estimated_hours), 2) AS total_hours
        FROM t_action a
        JOIN t_assignment asg ON asg.asg_action_id = a.act_id
        JOIN t_user u ON u.usr_id = asg.asg_user_id
                WHERE (a.act_topic_id = ? OR a.act_secondary_topic_id = ?)
          AND a.act_archived = 0
          AND a.act_status NOT IN ('Done','Cancelled')
          AND asg.asg_estimated_hours IS NOT NULL
        GROUP BY u.usr_id
        ORDER BY total_hours DESC
        LIMIT 10
        """,
                (topic_id, topic_id),
    ).fetchall()

    # Recent overdue actions
    overdue_rows = db.execute(
        """
        SELECT act_id, act_ref, act_title, act_priority, act_status, act_deadline,
             NULL AS dept_name,
             m.min_title AS meeting_title,
             m.min_date  AS meeting_date
        FROM t_action a
        LEFT JOIN t_meeting_instance m ON m.min_id = a.act_meeting_inst_id
            WHERE (a.act_topic_id = ? OR a.act_secondary_topic_id = ?)
          AND a.act_archived = 0
          AND a.act_deadline < date('now')
          AND a.act_status NOT IN ('Done','Cancelled')
        ORDER BY a.act_deadline ASC
        LIMIT 15
        """,
            (topic_id, topic_id),
    ).fetchall()

    # All actions in topic (latest 50) for mini-list + Gantt
    action_rows = db.execute(
        """
        SELECT a.act_id, a.act_ref, a.act_title, a.act_status, a.act_priority,
                             a.act_deadline, a.act_completion_pct,
             a.act_created_at, NULL AS dept_name,
             m.min_title AS meeting_title,
             m.min_date  AS meeting_date,
               u.usr_display_name AS lead_name,
                        (SELECT COUNT(DISTINCT z.asg_user_id) FROM t_assignment z WHERE z.asg_action_id = a.act_id) AS asg_total
        FROM t_action a
        LEFT JOIN t_meeting_instance m ON m.min_id = a.act_meeting_inst_id
        LEFT JOIN t_assignment asg ON asg.asg_action_id = a.act_id AND INSTR(',' || asg.asg_role || ',', ',Lead,') > 0
        LEFT JOIN t_user u ON u.usr_id = asg.asg_user_id
            WHERE (a.act_topic_id = ? OR a.act_secondary_topic_id = ?)
          AND a.act_archived = 0
          AND a.act_status != 'Cancelled'
        GROUP BY a.act_id
        ORDER BY a.act_created_at DESC
        LIMIT 50
        """,
            (topic_id, topic_id),
    ).fetchall()

    return {
        "topic": dict(topic),
        "kpis": {
            "open":        int(kpi["k50_open"] or 0),
            "in_progress": int(kpi["in_progress"] or 0),
            "overdue":     int(kpi["k51_overdue"] or 0),
            "done":        int(kpi["k52_done"] or 0),
            "on_time_rate": on_time_rate,
            "total":       int(kpi["total"] or 0),
        },
        "workload": [dict(r) for r in workload_rows],
        "workload_forecast": get_topic_workload_forecast(topic_id),
        "overdue_actions": [dict(r) for r in overdue_rows],
        "recent_actions": [dict(r) for r in action_rows],
    }
def get_topic_workload_forecast(topic_id: int, weeks: int = 16) -> dict:
    """Weekly workload forecast per user for a topic."""
    from datetime import date

    db = get_db()

    rows = db.execute(
        """
        SELECT
            asg.asg_user_id,
            u.usr_display_name,
            a.act_id,
            SUM(asg.asg_estimated_hours) AS asg_est_hours,
            a.act_start_date AS effective_start,
            a.act_deadline AS effective_end
        FROM t_action a
        JOIN t_assignment asg
          ON asg.asg_action_id = a.act_id
        JOIN t_user u ON u.usr_id = asg.asg_user_id
                WHERE (a.act_topic_id = ? OR a.act_secondary_topic_id = ?)
          AND a.act_archived = 0
          AND a.act_status NOT IN ('Done', 'Cancelled')
          AND a.act_deadline IS NOT NULL
          AND asg.asg_estimated_hours IS NOT NULL
        GROUP BY asg.asg_user_id, u.usr_display_name, a.act_id
        """,
                (topic_id, topic_id),
    ).fetchall()

    bucket_keys, buckets_template = _build_week_buckets(weeks)
    today = date.today()

    user_map: dict[int, dict] = {}
    for row in rows:
        uid = int(row["asg_user_id"])
        if uid not in user_map:
            user_map[uid] = {
                "usr_id": uid,
                "name": row["usr_display_name"],
                "buckets": {ws: 0.0 for ws in bucket_keys},
            }

    for row in rows:
        uid = int(row["asg_user_id"])
        end_date = _parse_iso_date(row["effective_end"])
        if not end_date:
            continue
        start_date = _parse_iso_date(row["effective_start"]) or today
        hours = float(row["asg_est_hours"] or 0)
        if hours <= 0:
            continue

        overlap_keys = []
        for ws in bucket_keys:
            we = _parse_iso_date(buckets_template[ws]["week_end"])
            if ws <= end_date and we >= start_date:
                overlap_keys.append(ws)
        if not overlap_keys:
            continue

        per_week = round(hours / len(overlap_keys), 2)
        for ws in overlap_keys:
            user_map[uid]["buckets"][ws] = round(
                user_map[uid]["buckets"][ws] + per_week, 2
            )

    weeks_data = [
        {
            "label": buckets_template[ws]["label"],
            "label_full": buckets_template[ws]["label_full"],
            "week_start": buckets_template[ws]["week_start"],
            "week_end": buckets_template[ws]["week_end"],
        }
        for ws in bucket_keys
    ]

    members_data = [
        {
            "usr_id": item["usr_id"],
            "name": item["name"],
            "hours_by_week": [item["buckets"][ws] for ws in bucket_keys],
        }
        for item in user_map.values()
    ]

    return {"weeks": weeks_data, "members": members_data}
