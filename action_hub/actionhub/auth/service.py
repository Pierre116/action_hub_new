import bcrypt
from datetime import datetime, timedelta, UTC

from actionhub.middleware.db import get_db

LOCKOUT_FAILURES = 5
LOCKOUT_WINDOW_MINUTES = 15
LOCKOUT_DURATION_MINUTES = 30


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def _check_password(password: str, hashed_value: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_value.encode("utf-8"))


def create_user(
    password: str,
    display_name: str,
    email: str,
    role: str = "Member",
    employee_id: str | None = None,
    must_change_pwd: int = 1,
    username: str | None = None,
) -> int:
    """Create a user. Username is auto-generated from employee_id if not given.
    Returns existing usr_id if employee_id already exists."""
    db = get_db()

    # Check for existing employee_id first
    if employee_id:
        existing = db.execute("SELECT usr_id FROM t_user WHERE usr_employee_id = ?", (employee_id,)).fetchone()
        if existing:
            return int(existing["usr_id"])

    # Auto-generate username from employee_id or display_name
    auto_username = username or employee_id or display_name.lower().replace(" ", "_")
    existing = db.execute("SELECT usr_id FROM t_user WHERE usr_username = ?", (auto_username,)).fetchone()
    if existing:
        return int(existing["usr_id"])

    # Derive employee_id from auto-increment if not provided
    # We insert first then backfill if needed
    cursor = db.execute(
        """
        INSERT INTO t_user (
            usr_username, usr_employee_id, usr_pwd_hash, usr_display_name,
            usr_email, usr_role,
            usr_lang, usr_auth_src, usr_active, usr_must_change_pwd
        ) VALUES (?, ?, ?, ?, ?, ?, 'en', 'local', 1, ?)
        """,
        (
            auto_username,
            employee_id,
            _hash_password(password),
            display_name,
            email,
            role,
            must_change_pwd,
        ),
    )
    new_id = int(cursor.lastrowid)

    # If no employee_id provided, generate zero-padded from usr_id
    if not employee_id:
        generated = f"{new_id:06d}"
        db.execute(
            "UPDATE t_user SET usr_employee_id = ? WHERE usr_id = ?",
            (generated, new_id),
        )

    db.commit()
    return new_id


def force_change_password(user_id: int, new_password: str) -> None:
    """Set a new password chosen by the user themselves. Clears must_change_pwd flag."""
    if len(new_password) < 6:
        raise ValueError("Password must be at least 6 characters")
    db = get_db()
    db.execute(
        """
        UPDATE t_user
        SET usr_pwd_hash = ?,
            usr_must_change_pwd = 0,
            usr_updated_at = CURRENT_TIMESTAMP
        WHERE usr_id = ?
        """,
        (_hash_password(new_password), user_id),
    )
    db.commit()


def reset_user_password(user_id: int, temp_password: str) -> None:
    """Admin resets a user's password. Forces the user to change it on next login."""
    if len(temp_password) < 6:
        raise ValueError("Temporary password must be at least 6 characters")
    db = get_db()
    if not db.execute("SELECT usr_id FROM t_user WHERE usr_id = ?", (user_id,)).fetchone():
        raise ValueError("user not found")
    db.execute(
        """
        UPDATE t_user
        SET usr_pwd_hash = ?,
            usr_must_change_pwd = 1,
            usr_failed_logins = 0,
            usr_locked_until = NULL,
            usr_updated_at = CURRENT_TIMESTAMP
        WHERE usr_id = ?
        """,
        (_hash_password(temp_password), user_id),
    )
    db.commit()


def authenticate_user(username: str, password: str) -> dict | None:
    """Authenticate by username or employee_id.

    Returns user dict on success, or None on failure.
    Raises ValueError with code 'LOCKED' if account is locked.
    Raises ValueError with code 'DISABLED' if account is inactive.
    """
    db = get_db()
    user = db.execute(
        """
        SELECT usr_id, usr_username, usr_employee_id, usr_pwd_hash,
               usr_display_name, usr_role, usr_active,
             usr_failed_logins, usr_first_failed_at, usr_locked_until,
               COALESCE(usr_lang, 'en') AS usr_lang,
               COALESCE(usr_must_change_pwd, 0) AS usr_must_change_pwd
        FROM t_user
        WHERE usr_username = ? OR usr_employee_id = ?
        """,
        (username, username),
    ).fetchone()

    if not user:
        return None

    if not user["usr_active"]:
        raise ValueError("DISABLED")

    # Enforce lockout
    if user["usr_locked_until"]:
        locked_until = datetime.fromisoformat(user["usr_locked_until"])
        if datetime.now(UTC) < locked_until:
            raise ValueError("LOCKED")

    if not _check_password(password, user["usr_pwd_hash"]):
        # Enforce 15-minute sliding window for failed attempts per spec
        now = datetime.now(UTC)
        first_failed = user["usr_first_failed_at"]
        prior_failures = user["usr_failed_logins"] or 0

        # Reset counter if the window has expired
        if first_failed:
            window_start = datetime.fromisoformat(first_failed)
            if (now - window_start).total_seconds() > LOCKOUT_WINDOW_MINUTES * 60:
                prior_failures = 0
                first_failed = None

        new_failures = prior_failures + 1
        first_failed_val = first_failed if first_failed else now.isoformat()
        locked_until = None
        if new_failures >= LOCKOUT_FAILURES:
            locked_until = (now + timedelta(minutes=LOCKOUT_DURATION_MINUTES)).isoformat()
        db.execute(
            """
            UPDATE t_user
            SET usr_failed_logins = ?,
                usr_first_failed_at = ?,
                usr_locked_until = ?
            WHERE usr_id = ?
            """,
            (new_failures, first_failed_val, locked_until, user["usr_id"]),
        )
        db.commit()
        return None

    db.execute(
        """
        UPDATE t_user
        SET usr_failed_logins = 0,
            usr_first_failed_at = NULL,
            usr_locked_until = NULL,
            usr_last_login_at = CURRENT_TIMESTAMP
        WHERE usr_id = ?
        """,
        (user["usr_id"],),
    )
    db.commit()

    # Check teams this user leads
    leads = db.execute(
        "SELECT tea_id, tea_name_en FROM t_team WHERE tea_leader_user_id = ? AND tea_active = 1",
        (user["usr_id"],),
    ).fetchall()
    leads_teams = [{"id": r["tea_id"], "name": r["tea_name_en"]} for r in leads]

    return {
        "id": int(user["usr_id"]),
        "username": user["usr_username"],
        "employee_id": user["usr_employee_id"],
        "display_name": user["usr_display_name"],
        "role": user["usr_role"],
        "lang": user["usr_lang"],
        "must_change_pwd": bool(user["usr_must_change_pwd"]),
        "leads_teams": leads_teams,
    }
