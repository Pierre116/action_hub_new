
"""Workflow dashboard metrics and analytics."""
import json
from actionhub.middleware.db import get_db


def get_completion_rates(template_id=None):
    """Completion rate per template."""
    db = get_db()
    if template_id:
        rows = db.execute("""
            SELECT wft_id as tid, wft_name_en as name_en, wft_name_cn as name_cn,
                   COUNT(wfi_id) as total,
                   SUM(CASE WHEN wfi_status = 'Completed' THEN 1 ELSE 0 END) as completed
            FROM t_workflow_template
            LEFT JOIN t_workflow_instance ON wft_id = wfi_template_id
            WHERE wft_id = ?
            GROUP BY wft_id""", (template_id,)).fetchall()
    else:
        rows = db.execute("""
            SELECT wft_id as tid, wft_name_en as name_en, wft_name_cn as name_cn,
                   COUNT(wfi_id) as total,
                   SUM(CASE WHEN wfi_status = 'Completed' THEN 1 ELSE 0 END) as completed
            FROM t_workflow_template
            LEFT JOIN t_workflow_instance ON wft_id = wfi_template_id
            GROUP BY wft_id""").fetchall()
    result = []
    for row in rows:
        total = row["total"] or 0
        completed = row["completed"] or 0
        rate = (completed / total * 100) if total > 0 else 0.0
        result.append({"template_id": row["tid"], "name_en": row["name_en"], "name_cn": row["name_cn"],
                       "total": total, "completed": completed, "rate": round(rate, 1)})
    return result


def get_lead_times(template_id=None):
    """Average end-to-end duration per template."""
    db = get_db()
    if template_id:
        rows = db.execute("""
            SELECT wft_id as tid, wft_name_en as name_en, wft_name_cn as name_cn,
                   AVG((julianday(wfi_completed_at) - julianday(wfi_started_at)) * 24) as avg_h,
                   MIN((julianday(wfi_completed_at) - julianday(wfi_started_at)) * 24) as min_h,
                   MAX((julianday(wfi_completed_at) - julianday(wfi_started_at)) * 24) as max_h
            FROM t_workflow_template
            JOIN t_workflow_instance ON wft_id = wfi_template_id
            WHERE wft_id = ? AND wfi_status = 'Completed' AND wfi_completed_at IS NOT NULL
            GROUP BY wft_id""", (template_id,)).fetchall()
    else:
        rows = db.execute("""
            SELECT wft_id as tid, wft_name_en as name_en, wft_name_cn as name_cn,
                   AVG((julianday(wfi_completed_at) - julianday(wfi_started_at)) * 24) as avg_h,
                   MIN((julianday(wfi_completed_at) - julianday(wfi_started_at)) * 24) as min_h,
                   MAX((julianday(wfi_completed_at) - julianday(wfi_started_at)) * 24) as max_h
            FROM t_workflow_template
            JOIN t_workflow_instance ON wft_id = wfi_template_id
            WHERE wfi_status = 'Completed' AND wfi_completed_at IS NOT NULL
            GROUP BY wft_id""").fetchall()
    result = []
    for row in rows:
        result.append({"template_id": row["tid"], "name_en": row["name_en"], "name_cn": row["name_cn"],
                       "avg_hours": round(row["avg_h"], 1) if row["avg_h"] else None,
                       "min_hours": round(row["min_h"], 1) if row["min_h"] else None,
                       "max_hours": round(row["max_h"], 1) if row["max_h"] else None})
    return result


def get_step_lead_times(template_id):
    """Average time per step vs SLA."""
    db = get_db()
    template = db.execute("SELECT wft_graph FROM t_workflow_template WHERE wft_id = ?", (template_id,)).fetchone()
    if not template:
        return []
    try:
        graph = json.loads(template["wft_graph"])
    except (json.JSONDecodeError, TypeError):
        return []
    steps_def = graph.get("steps", {})
    rows = db.execute("""
        SELECT wsi_step_key as skey,
               AVG((julianday(wsi_completed_at) - julianday(wsi_entered_at)) * 24) as avg_h,
               COUNT(*) as cnt
        FROM t_workflow_step_instance
        JOIN t_workflow_instance ON wsi_instance_id = wfi_id
        WHERE wfi_template_id = ? AND wsi_status = 'Completed'
              AND wsi_completed_at IS NOT NULL AND wsi_entered_at IS NOT NULL
        GROUP BY wsi_step_key""", (template_id,)).fetchall()
    result = []
    for row in rows:
        step_key = row["skey"]
        step_def = steps_def.get(step_key, {})
        sla_hours = step_def.get("sla_hours")
        avg_hours = row["avg_h"] if row["avg_h"] else 0
        compliance_pct = None
        if sla_hours and row["cnt"]:
            on_time = db.execute("""
                SELECT COUNT(*) as cnt FROM t_workflow_step_instance wsi
                JOIN t_workflow_instance wfi ON wsi.wsi_instance_id = wfi.wfi_id
                WHERE wfi.wfi_template_id = ? AND wsi.wsi_step_key = ? AND wsi.wsi_status = 'Completed'
                      AND wsi.wsi_completed_at IS NOT NULL
                      AND (julianday(wsi.wsi_completed_at) - julianday(wsi.wsi_entered_at)) * 24 <= ?""",
                (template_id, step_key, sla_hours)).fetchone()
            if on_time:
                compliance_pct = round(on_time["cnt"] / row["cnt"] * 100, 1)
        result.append({"step_key": step_key, "name_en": step_def.get("name_en", step_key),
                       "name_cn": step_def.get("name_cn", ""), "avg_hours": round(avg_hours, 1),
                       "sla_hours": sla_hours, "compliance_pct": compliance_pct})
    return result


def get_sla_compliance(template_id=None, team_id=None):
    """SLA compliance percentage."""
    db = get_db()
    total = db.execute("""
        SELECT COUNT(*) as cnt FROM t_workflow_step_instance wsi
        JOIN t_workflow_instance wfi ON wsi.wsi_instance_id = wfi.wfi_id
        WHERE wsi.wsi_status = 'Completed' AND wsi.wsi_sla_deadline IS NOT NULL
              AND wsi.wsi_completed_at IS NOT NULL""").fetchone()
    on_time = db.execute("""
        SELECT COUNT(*) as cnt FROM t_workflow_step_instance wsi
        JOIN t_workflow_instance wfi ON wsi.wsi_instance_id = wfi.wfi_id
        WHERE wsi.wsi_status = 'Completed' AND wsi.wsi_sla_deadline IS NOT NULL
              AND wsi.wsi_completed_at IS NOT NULL
              AND wsi.wsi_completed_at <= wsi.wsi_sla_deadline""").fetchone()
    total_cnt = total["cnt"] if total else 0
    on_time_cnt = on_time["cnt"] if on_time else 0
    pct = (on_time_cnt / total_cnt * 100) if total_cnt > 0 else 0.0
    return {"total": total_cnt, "on_time": on_time_cnt, "compliance_pct": round(pct, 1)}


def get_bottlenecks(limit=10):
    """Steps with most items currently waiting."""
    db = get_db()
    rows = db.execute("""
        SELECT wsi_step_key as skey, wft_name_en as tname, COUNT(*) as cnt,
               MIN((julianday('now') - julianday(wsi_entered_at)) * 24) as oldest_hours
        FROM t_workflow_step_instance
        JOIN t_workflow_instance ON wsi_instance_id = wfi_id
        JOIN t_workflow_template ON wfi_template_id = wft_id
        WHERE wsi_status = 'Active'
        GROUP BY wsi_step_key, wft_name_en
        ORDER BY cnt DESC
        LIMIT ?""", (limit,)).fetchall()
    return [{"step_key": r["skey"], "template_name": r["tname"], "count": r["cnt"],
             "oldest_hours": round(r["oldest_hours"], 1) if r["oldest_hours"] else 0} for r in rows]


def get_active_instance_counts():
    """Count of in-flight instances per template."""
    db = get_db()
    rows = db.execute("""
        SELECT wft_id as tid, wft_name_en as name_en, COUNT(*) as active_count
        FROM t_workflow_template
        JOIN t_workflow_instance ON wft_id = wfi_template_id
        WHERE wfi_status = 'Active'
        GROUP BY wft_id""").fetchall()
    return [{"template_id": r["tid"], "name_en": r["name_en"], "active_count": r["active_count"]} for r in rows]
