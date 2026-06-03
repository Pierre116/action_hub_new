def delete_user_admin(user_id: int) -> None:
    """Delete a user if not linked to any actions, assignments, or comments."""
    db = get_db()
    # Check for links in actions (owner, created_by)
    act_count = db.execute("SELECT COUNT(1) FROM t_action WHERE act_owner_id = ? OR act_created_by = ?", (user_id, user_id)).fetchone()[0]
    # Check for links in assignments
    asg_count = db.execute("SELECT COUNT(1) FROM t_assignment WHERE asg_user_id = ? OR asg_assigned_by = ?", (user_id, user_id)).fetchone()[0]
    # Check for links in comments
    cmt_count = db.execute("SELECT COUNT(1) FROM t_comment WHERE cmt_created_by = ? OR cmt_edited_by = ?", (user_id, user_id)).fetchone()[0]
    # Check for links in meetings (created_by)
    min_count = db.execute("SELECT COUNT(1) FROM t_meeting_instance WHERE min_created_by = ?", (user_id,)).fetchone()[0]
    # Check for links in teams (user_team)
    utm_count = db.execute("SELECT COUNT(1) FROM t_user_team WHERE utm_user_id = ?", (user_id,)).fetchone()[0]
    # Check for links as a team leader
    tea_count = db.execute("SELECT COUNT(1) FROM t_team WHERE tea_leader_user_id = ?", (user_id,)).fetchone()[0]
    if any([act_count, asg_count, cmt_count, min_count, utm_count, tea_count]):
        raise ValueError("user is linked to other records and cannot be deleted")
    # Actually delete
    res = db.execute("DELETE FROM t_user WHERE usr_id = ?", (user_id,))
    if res.rowcount == 0:
        raise ValueError("user not found")
    db.commit()
from actionhub.auth.service import create_user, reset_user_password
from actionhub.middleware.db import get_db


def list_users() -> list[dict]:
    db = get_db()
    rows = db.execute(
        """
        SELECT
            u.usr_id,
            u.usr_username,
            u.usr_employee_id,
            u.usr_display_name,
            u.usr_email,
            u.usr_role,
            u.usr_active,
            u.usr_lang,
            u.usr_created_at,
            u.usr_last_login_at
        FROM t_user u
        ORDER BY u.usr_display_name
        """
    ).fetchall()
    users = [dict(row) for row in rows]

    # Attach team memberships per user
    team_rows = db.execute(
        """
        SELECT utm.utm_user_id, t.tea_id, t.tea_name_en, t.tea_code
        FROM t_user_team utm
        JOIN t_team t ON t.tea_id = utm.utm_team_id
        """
    ).fetchall()
    from collections import defaultdict
    teams_by_user: dict[int, list] = defaultdict(list)
    for tr in team_rows:
        teams_by_user[tr["utm_user_id"]].append(dict(tr))

    for user in users:
        user["teams"] = teams_by_user.get(user["usr_id"], [])

    return users


def create_user_admin(payload: dict) -> dict:
    password = str(payload.get("password", "")).strip()
    display_name = str(payload.get("display_name", "")).strip()
    email = str(payload.get("email", "")).strip()
    role = str(payload.get("role", "Member")).strip() or "Member"
    employee_id = str(payload.get("employee_id", "")).strip() or None
    username = str(payload.get("username", "")).strip() or None

    if not password or not display_name or not email:
        raise ValueError("password, display_name and email are required")

    if employee_id:
        if not employee_id.isdigit() or len(employee_id) != 6:
            raise ValueError("employee_id must be a 6-digit number")

    db = get_db()
    if employee_id:
        dup = db.execute("SELECT usr_id FROM t_user WHERE usr_employee_id = ?", (employee_id,)).fetchone()
        if dup:
            raise ValueError("employee_id already in use")
    if username:
        dup = db.execute("SELECT usr_id FROM t_user WHERE usr_username = ?", (username,)).fetchone()
        if dup:
            raise ValueError("username already in use")

    user_id = create_user(
        password=password,
        display_name=display_name,
        email=email,
        role=role,
        employee_id=employee_id,
        must_change_pwd=1,
        username=username,
    )
    row = db.execute(
        "SELECT usr_id, usr_username, usr_employee_id, usr_display_name, usr_email, usr_role, usr_active FROM t_user WHERE usr_id = ?",
        (user_id,),
    ).fetchone()
    return dict(row)


def update_user_admin(user_id: int, payload: dict) -> dict:
    import logging
    logging.warning(f"update_user_admin called with user_id={user_id}, payload={payload}")
    
    db = get_db()
    current = db.execute("SELECT * FROM t_user WHERE usr_id = ?", (user_id,)).fetchone()
    if not current:
        raise ValueError("user not found")

    logging.warning(f"Current user state: usr_active={current['usr_active']}, type={type(current['usr_active'])}")

    # Handle usr_active specifically - ensure it's an integer
    if "usr_active" in payload:
        usr_active_val = int(payload["usr_active"])
        logging.warning(f"Direct UPDATE: SET usr_active = {usr_active_val} WHERE usr_id = {user_id}")
        db.execute("UPDATE t_user SET usr_active = ?, usr_updated_at = CURRENT_TIMESTAMP WHERE usr_id = ?", 
                   (usr_active_val, user_id))
        db.commit()
        logging.warning("Commit done, fetching new state...")
        row = db.execute(
            "SELECT usr_id, usr_employee_id, usr_display_name, usr_email, usr_role, usr_active FROM t_user WHERE usr_id = ?",
            (user_id,),
        ).fetchone()
        logging.warning(f"New user state after direct update: usr_active={row['usr_active']}")
        return dict(row)

    mapping = {
        "display_name": "usr_display_name",
        "email": "usr_email",
        "role": "usr_role",
        "team_id": "usr_team_id",
        "active": "usr_active",
        "lang": "usr_lang",
    }

    set_parts: list[str] = []
    values: list[object] = []
    for key, field in mapping.items():
        if key not in payload:
            continue
        logging.warning(f"Processing key={key}, value={payload[key]}")
        set_parts.append(f"{field} = ?")
        values.append(payload[key])

    if not set_parts:
        logging.warning("No fields to update!")
        row = db.execute(
            "SELECT usr_id, usr_employee_id, usr_display_name, usr_email, usr_role, usr_active FROM t_user WHERE usr_id = ?",
            (user_id,),
        ).fetchone()
        return dict(row)

    set_parts.append("usr_updated_at = CURRENT_TIMESTAMP")
    db.execute(
        f"UPDATE t_user SET {', '.join(set_parts)} WHERE usr_id = ?",
        [*values, user_id],
    )
    db.commit()
    logging.warning(f"Updated user {user_id}, checking new state...")
    row = db.execute(
        "SELECT usr_id, usr_employee_id, usr_display_name, usr_email, usr_role, usr_active FROM t_user WHERE usr_id = ?",
        (user_id,),
    ).fetchone()
    logging.warning(f"New user state: usr_active={row['usr_active']}")
    return dict(row)


def reset_password_admin(user_id: int, new_password: str) -> None:
    """Reset a user's password and require them to change it on next login."""
    if len(new_password or "") < 8:
        raise ValueError("password must be at least 8 characters")
    reset_user_password(user_id, new_password)


# ── Multi-team membership ─────────────────────────────────────────────────────

def get_user_teams(user_id: int) -> list[dict]:
    """Return all teams a user belongs to."""
    db = get_db()
    rows = db.execute(
        """
        SELECT t.tea_id, t.tea_name_en, t.tea_code
        FROM t_user_team ut
        JOIN t_team t ON t.tea_id = ut.utm_team_id
        WHERE ut.utm_user_id = ?
        ORDER BY t.tea_name_en
        """,
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def list_teams(include_counts: bool = False) -> list[dict]:
    """All teams (both active and inactive). Optionally include member counts."""
    db = get_db()
    if include_counts:
        rows = db.execute(
            """
            SELECT t.tea_id, t.tea_name_en, t.tea_name_cn, t.tea_code, t.tea_active, t.tea_leader_user_id,
                   u.usr_display_name AS tea_leader_name,
                   COUNT(DISTINCT utm.utm_user_id) AS member_count
            FROM t_team t
            LEFT JOIN t_user u ON u.usr_id = t.tea_leader_user_id
            LEFT JOIN t_user_team utm ON utm.utm_team_id = t.tea_id
            GROUP BY t.tea_id
            ORDER BY t.tea_name_en
            """
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT t.tea_id, t.tea_name_en, t.tea_name_cn, t.tea_code, t.tea_active, t.tea_leader_user_id,
                   u.usr_display_name AS tea_leader_name
            FROM t_team t
            LEFT JOIN t_user u ON u.usr_id = t.tea_leader_user_id
            ORDER BY t.tea_name_en
            """
        ).fetchall()
    return [dict(r) for r in rows]


def create_team(payload: dict) -> dict:
    """Create a new team. Optionally assign a team leader (leader_id)."""
    code = str(payload.get("code", "")).strip().upper()
    name_en = str(payload.get("name_en", "")).strip()
    name_cn = str(payload.get("name_cn", "")).strip() or None
    leader_id = payload.get("leader_id")
    if not code or not name_en:
        raise ValueError("code and name_en are required")
    db = get_db()
    if db.execute("SELECT tea_id FROM t_team WHERE tea_code = ?", (code,)).fetchone():
        raise ValueError(f"team code '{code}' already exists")
    leader_id = None if leader_id in (None, "", "None") else int(leader_id)
    if leader_id is not None and not db.execute("SELECT 1 FROM t_user WHERE usr_id = ?", (leader_id,)).fetchone():
        raise ValueError("leader user not found")
    cur = db.execute(
        "INSERT INTO t_team (tea_code, tea_name_en, tea_name_cn, tea_active, tea_leader_user_id) VALUES (?, ?, ?, 1, ?)",
        (code, name_en, name_cn, leader_id),
    )
    team_id = cur.lastrowid
    # Optionally assign leader
    if leader_id is not None:
        # Insert into t_user_team if not already present
        exists = db.execute(
            "SELECT 1 FROM t_user_team WHERE utm_user_id = ? AND utm_team_id = ?",
            (leader_id, team_id),
        ).fetchone()
        if not exists:
            db.execute(
                "INSERT INTO t_user_team (utm_user_id, utm_team_id) VALUES (?, ?)",
                (leader_id, team_id),
            )
    db.commit()
    row = db.execute("SELECT * FROM t_team WHERE tea_id = ?", (team_id,)).fetchone()
    return dict(row)


def update_team(team_id: int, payload: dict) -> dict:
    """Update an existing team."""
    db = get_db()
    if not db.execute("SELECT tea_id FROM t_team WHERE tea_id = ?", (team_id,)).fetchone():
        raise ValueError("team not found")
    fields = {"name_en": "tea_name_en", "active": "tea_active", "leader_id": "tea_leader_user_id"}
    parts, vals = [], []
    if "name_cn" in payload:
        parts.append("tea_name_cn = ?")
        vals.append(str(payload["name_cn"]).strip() or None)
    for key, col in fields.items():
        if key in payload:
            if key == "leader_id":
                raw_leader_id = payload[key]
                leader_id = None if raw_leader_id in (None, "", "None") else int(raw_leader_id)
                if leader_id is not None and not db.execute("SELECT 1 FROM t_user WHERE usr_id = ?", (leader_id,)).fetchone():
                    raise ValueError("leader user not found")
                parts.append(f"{col} = ?")
                vals.append(leader_id)
            else:
                parts.append(f"{col} = ?")
                vals.append(payload[key])
    if not parts:
        row = db.execute("SELECT * FROM t_team WHERE tea_id = ?", (team_id,)).fetchone()
        return dict(row)
    db.execute(f"UPDATE t_team SET {', '.join(parts)} WHERE tea_id = ?", [*vals, team_id])
    raw_leader_id = payload.get("leader_id")
    leader_id = None if raw_leader_id in (None, "", "None") else int(raw_leader_id)
    if leader_id is not None:
        exists = db.execute(
            "SELECT 1 FROM t_user_team WHERE utm_user_id = ? AND utm_team_id = ?",
            (leader_id, team_id),
        ).fetchone()
        if not exists:
            db.execute(
                "INSERT INTO t_user_team (utm_user_id, utm_team_id) VALUES (?, ?)",
                (leader_id, team_id),
            )
    db.commit()
    row = db.execute("SELECT * FROM t_team WHERE tea_id = ?", (team_id,)).fetchone()
    return dict(row)


def list_team_members(team_id: int) -> list[dict]:
    """List all members of a team."""
    db = get_db()
    rows = db.execute(
        """
        SELECT u.usr_id, u.usr_display_name, u.usr_role, u.usr_active
        FROM t_user_team utm
        JOIN t_user u ON u.usr_id = utm.utm_user_id
        WHERE utm.utm_team_id = ?
        ORDER BY u.usr_display_name
        """,
        (team_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def add_user_team(user_id: int, team_id: int, is_primary: bool = False) -> None:
    db = get_db()
    if not db.execute("SELECT 1 FROM t_user WHERE usr_id = ?", (user_id,)).fetchone():
        raise ValueError("user not found")
    if not db.execute("SELECT 1 FROM t_team WHERE tea_id = ?", (team_id,)).fetchone():
        raise ValueError("team not found")
    existing = db.execute(
        "SELECT 1 FROM t_user_team WHERE utm_user_id = ? AND utm_team_id = ?",
        (user_id, team_id),
    ).fetchone()
    if existing:
        return  # already in team
    db.execute(
        "INSERT INTO t_user_team (utm_user_id, utm_team_id) VALUES (?, ?)",
        (user_id, team_id),
    )
    db.commit()


def remove_user_team(user_id: int, team_id: int) -> None:
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM t_user_team WHERE utm_user_id = ? AND utm_team_id = ?",
        (user_id, team_id),
    ).fetchone():
        raise ValueError("user is not in this team")
    db.execute(
        "DELETE FROM t_user_team WHERE utm_user_id = ? AND utm_team_id = ?",
        (user_id, team_id),
    )
    db.commit()

