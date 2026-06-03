"""Evolution / What's New service — manages product changelog entries."""
from __future__ import annotations

from actionhub.middleware.db import get_db

CATEGORIES = ["Feature", "Improvement", "Bugfix", "Security"]


def list_entries(page: int = 1, per_page: int = 50, *, published_only: bool = False) -> dict:
    db = get_db()
    where = "WHERE e.evo_is_published = 1" if published_only else ""
    total = db.execute(
        f"SELECT COUNT(*) FROM t_evolution e {where}"
    ).fetchone()[0]
    offset = (page - 1) * per_page
    rows = db.execute(
        f"""
        SELECT e.evo_id, e.evo_version, e.evo_title, e.evo_description,
               e.evo_category, e.evo_date, e.evo_is_published,
               e.evo_created_at,
               u.usr_display_name AS author_name
        FROM t_evolution e
        LEFT JOIN t_user u ON u.usr_id = e.evo_author_id
        {where}
        ORDER BY e.evo_date DESC, e.evo_id DESC
        LIMIT ? OFFSET ?
        """,
        (per_page, offset),
    ).fetchall()
    return {
        "items": [dict(r) for r in rows],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": max(1, (total + per_page - 1) // per_page),
        },
    }


def get_entry(evo_id: int) -> dict:
    db = get_db()
    row = db.execute(
        """
        SELECT e.*, u.usr_display_name AS author_name
        FROM t_evolution e
        LEFT JOIN t_user u ON u.usr_id = e.evo_author_id
        WHERE e.evo_id = ?
        """,
        (evo_id,),
    ).fetchone()
    if not row:
        raise ValueError("entry not found")
    return dict(row)


def create_entry(author_id: int, payload: dict) -> dict:
    version = str(payload.get("version", "")).strip()
    title = str(payload.get("title", "")).strip()
    description = str(payload.get("description", "")).strip()
    category = str(payload.get("category", "")).strip()
    date = str(payload.get("date", "")).strip()

    if not all([version, title, description, category, date]):
        raise ValueError("version, title, description, category and date are required")
    if category not in CATEGORIES:
        raise ValueError(f"category must be one of {CATEGORIES}")

    db = get_db()
    cur = db.execute(
        """
        INSERT INTO t_evolution (evo_version, evo_title, evo_description, evo_category, evo_date, evo_author_id, evo_is_published)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (version, title, description, category, date, author_id,
         1 if payload.get("is_published", False) else 0),
    )
    db.commit()
    return get_entry(int(cur.lastrowid))


def update_entry(evo_id: int, payload: dict) -> dict:
    db = get_db()
    if not db.execute("SELECT evo_id FROM t_evolution WHERE evo_id = ?", (evo_id,)).fetchone():
        raise ValueError("entry not found")

    field_map = {
        "version": "evo_version",
        "title": "evo_title",
        "description": "evo_description",
        "category": "evo_category",
        "date": "evo_date",
        "is_published": "evo_is_published",
    }
    parts: list[str] = []
    vals: list = []
    for key, col in field_map.items():
        if key in payload:
            if key == "category" and payload[key] not in CATEGORIES:
                raise ValueError(f"category must be one of {CATEGORIES}")
            parts.append(f"{col} = ?")
            vals.append(payload[key])

    if parts:
        db.execute(
            f"UPDATE t_evolution SET {', '.join(parts)} WHERE evo_id = ?",
            [*vals, evo_id],
        )
        db.commit()
    return get_entry(evo_id)


def delete_entry(evo_id: int) -> None:
    db = get_db()
    if not db.execute("SELECT evo_id FROM t_evolution WHERE evo_id = ?", (evo_id,)).fetchone():
        raise ValueError("entry not found")
    db.execute("DELETE FROM t_evolution WHERE evo_id = ?", (evo_id,))
    db.commit()
