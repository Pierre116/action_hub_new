from __future__ import annotations

from actionhub.middleware.db import get_db


def _category_to_dict(row) -> dict:
    return dict(row)


def list_categories(include_inactive: bool = False) -> list[dict]:
    db = get_db()
    sql = "SELECT * FROM t_category"
    if not include_inactive:
        sql += " WHERE cat_active = 1"
    sql += " ORDER BY cat_sort, cat_name_en"
    rows = db.execute(sql).fetchall()
    return [_category_to_dict(row) for row in rows]


def create_category(payload: dict, actor_id: int | None = None) -> dict:
    del actor_id

    db = get_db()
    name_en = str(payload.get("name_en") or payload.get("cat_name_en") or payload.get("name") or "").strip()
    name_cn = str(payload.get("name_cn") or payload.get("cat_name_cn") or "").strip() or None
    color = str(payload.get("color") or payload.get("cat_color") or "").strip() or None
    active = 1 if payload.get("active", True) else 0
    sort_value = int(payload.get("sort", payload.get("cat_sort", 0)) or 0)

    if len(name_en) < 2:
        raise ValueError("name_en must be at least 2 characters")

    duplicate = db.execute(
        "SELECT 1 FROM t_category WHERE cat_name_en = ?",
        (name_en,),
    ).fetchone()
    if duplicate:
        raise ValueError("category already exists")

    cursor = db.execute(
        """
        INSERT INTO t_category (cat_name_en, cat_name_cn, cat_color, cat_active, cat_sort)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name_en, name_cn, color, active, sort_value),
    )
    db.commit()
    row = db.execute("SELECT * FROM t_category WHERE cat_id = ?", (cursor.lastrowid,)).fetchone()
    return _category_to_dict(row)


def update_category(category_id: int | str, payload: dict, actor_id: int | None = None) -> dict:
    del actor_id

    db = get_db()
    row = db.execute("SELECT * FROM t_category WHERE cat_id = ?", (int(category_id),)).fetchone()
    if not row:
        raise ValueError("category not found")

    name_en = str(payload.get("name_en") or payload.get("cat_name_en") or row["cat_name_en"]).strip()
    name_cn = payload.get("name_cn") if ("name_cn" in payload or "cat_name_cn" in payload) else row["cat_name_cn"]
    color = payload.get("color") if ("color" in payload or "cat_color" in payload) else row["cat_color"]
    active = row["cat_active"]
    if "active" in payload:
        active = 1 if payload["active"] else 0
    sort_value = payload.get("sort", payload.get("cat_sort", row["cat_sort"]))

    if len(name_en) < 2:
        raise ValueError("name_en must be at least 2 characters")

    duplicate = db.execute(
        "SELECT 1 FROM t_category WHERE cat_name_en = ? AND cat_id <> ?",
        (name_en, int(category_id)),
    ).fetchone()
    if duplicate:
        raise ValueError("category already exists")

    db.execute(
        """
        UPDATE t_category
        SET cat_name_en = ?, cat_name_cn = ?, cat_color = ?, cat_active = ?, cat_sort = ?
        WHERE cat_id = ?
        """,
        (name_en, name_cn, color, active, int(sort_value or 0), int(category_id)),
    )
    db.commit()
    updated = db.execute("SELECT * FROM t_category WHERE cat_id = ?", (int(category_id),)).fetchone()
    return _category_to_dict(updated)