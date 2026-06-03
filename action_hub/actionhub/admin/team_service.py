"""
Team service for activation/deactivation and admin CRUD.
"""
import logging
from actionhub.utils.db import get_db

def set_team_active(team_id: int, active: bool) -> dict:
    db = get_db()
    tea_active_val = 1 if active else 0
    db.execute(
        "UPDATE t_team SET tea_active = ?, tea_sort_order = tea_sort_order WHERE tea_id = ?",
        (tea_active_val, team_id)
    )
    db.commit()
    logging.info(f"Team {team_id} set active={tea_active_val}")
    row = db.execute(
        "SELECT tea_id, tea_name_en, tea_code, tea_active FROM t_team WHERE tea_id = ?",
        (team_id,)
    ).fetchone()
    return dict(row) if row else {}

def get_team(team_id: int) -> dict:
    db = get_db()
    row = db.execute(
        "SELECT tea_id, tea_name_en, tea_code, tea_active FROM t_team WHERE tea_id = ?",
        (team_id,)
    ).fetchone()
    return dict(row) if row else {}

def list_teams(include_inactive: bool = False) -> list[dict]:
    db = get_db()
    sql = "SELECT tea_id, tea_name_en, tea_code, tea_active FROM t_team"
    if not include_inactive:
        sql += " WHERE tea_active = 1"
    rows = db.execute(sql).fetchall()
    return [dict(row) for row in rows]
