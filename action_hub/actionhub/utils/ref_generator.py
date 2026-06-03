from datetime import datetime, timezone

from actionhub.middleware.db import get_db


def generate_action_ref() -> str:
    year = datetime.now(timezone.utc).year
    prefix = f"ACT-{year}-"
    db = get_db()
    row = db.execute(
        """
        SELECT act_ref
        FROM t_action
        WHERE act_ref LIKE ?
        ORDER BY act_ref DESC
        LIMIT 1
        """,
        (f"{prefix}%",),
    ).fetchone()

    next_seq = 1
    if row and row["act_ref"]:
        try:
            next_seq = int(str(row["act_ref"]).split("-")[-1]) + 1
        except ValueError:
            next_seq = 1
    return f"{prefix}{next_seq:05d}"
