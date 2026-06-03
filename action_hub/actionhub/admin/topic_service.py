"""Category admin service for global categories."""
from __future__ import annotations

from actionhub.middleware.db import get_db


def _normalize_business_theme_code(value: object) -> str:
    return str(value or "").strip().upper()


def _table_columns(db, table_name: str) -> set[str]:
    rows = db.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def _ensure_optional_business_theme_columns(db) -> set[str]:
    columns = _table_columns(db, "t_topic")
    if "top_code" not in columns:
        db.execute("ALTER TABLE t_topic ADD COLUMN top_code TEXT")
        columns.add("top_code")
    if "top_name_en" not in columns:
        db.execute("ALTER TABLE t_topic ADD COLUMN top_name_en TEXT")
        columns.add("top_name_en")
    if "top_name_cn" not in columns:
        db.execute("ALTER TABLE t_topic ADD COLUMN top_name_cn TEXT")
        columns.add("top_name_cn")
    return columns


def _business_theme_to_dict(row) -> dict:
    business_theme = dict(row)
    business_theme["top_code"] = business_theme.get("top_code") or str(business_theme.get("top_id") or "")
    business_theme["top_name_en"] = business_theme.get("top_name_en") or business_theme.get("top_name") or ""
    business_theme["top_name_cn"] = business_theme.get("top_name_cn") or ""
    return business_theme


def _get_business_theme_row(db, identifier: str, columns: set[str]):
    row = None
    if "top_code" in columns:
        row = db.execute("SELECT * FROM t_topic WHERE top_code = ?", (identifier,)).fetchone()
    if row is None and "top_id" in columns:
        try:
            business_theme_id = int(identifier)
        except (TypeError, ValueError):
            business_theme_id = None
        if business_theme_id is not None:
            row = db.execute("SELECT * FROM t_topic WHERE top_id = ?", (business_theme_id,)).fetchone()
    return row


def _get_business_theme_names(payload: dict, current_row: dict | None = None) -> tuple[str, str, str]:
    name_en = str(payload.get("name_en") or payload.get("top_name_en") or "").strip()
    name_cn = str(payload.get("name_cn") or payload.get("top_name_cn") or "").strip()
    fallback_name = str(payload.get("name") or payload.get("top_name") or "").strip()

    if current_row is not None:
        name_en = name_en or str(current_row.get("top_name_en") or current_row.get("top_name") or "").strip()
        name_cn = name_cn or str(current_row.get("top_name_cn") or "").strip()
        fallback_name = fallback_name or str(current_row.get("top_name") or "").strip()

    top_name = fallback_name or name_en or name_cn
    return top_name, name_en, name_cn


def list_business_themes(include_inactive: bool = False) -> list[dict]:
    db = get_db()
    _ensure_optional_business_theme_columns(db)
    sql = "SELECT t.*, u.usr_display_name AS creator_name FROM t_topic t LEFT JOIN t_user u ON u.usr_id = t.top_created_by"
    if not include_inactive:
        sql += " WHERE t.top_active = 1"
    sql += " ORDER BY t.top_name"
    rows = db.execute(sql).fetchall()
    return [_business_theme_to_dict(r) for r in rows]


def create_business_theme(payload: dict, actor_id: int) -> dict:
    db = get_db()
    columns = _ensure_optional_business_theme_columns(db)
    code = _normalize_business_theme_code(payload.get("code") or payload.get("top_code"))
    name, name_en, name_cn = _get_business_theme_names(payload)

    if len(name) < 2:
        raise ValueError("name must be at least 2 characters")

    duplicate = db.execute(
        "SELECT 1 FROM t_topic WHERE top_name = ? OR (top_code IS NOT NULL AND top_code = ?)",
        (name, code or None),
    ).fetchone()
    if duplicate:
        raise ValueError("category already exists")

    insert_columns = ["top_name", "top_desc", "top_is_global", "top_created_by"]
    insert_values = [name, str(payload.get("desc", "")).strip() or None, 1, actor_id]
    if "top_code" in columns:
        insert_columns.insert(0, "top_code")
        insert_values.insert(0, code or None)
    if "top_name_en" in columns:
        insert_columns.append("top_name_en")
        insert_values.append(name_en or None)
    if "top_name_cn" in columns:
        insert_columns.append("top_name_cn")
        insert_values.append(name_cn or None)

    placeholders = ", ".join(["?"] * len(insert_columns))
    db.execute(
        f"INSERT INTO t_topic ({', '.join(insert_columns)}) VALUES ({placeholders})",
        tuple(insert_values),
    )
    db.commit()
    if "top_id" in columns:
        row = db.execute("SELECT * FROM t_topic ORDER BY top_id DESC LIMIT 1").fetchone()
    else:
        row = db.execute("SELECT * FROM t_topic WHERE top_code = ?", (code,)).fetchone()
    return _business_theme_to_dict(row)


def update_business_theme(business_theme_code: str, payload: dict, actor_id: int) -> dict:
    del actor_id

    db = get_db()
    columns = _ensure_optional_business_theme_columns(db)
    current_code = _normalize_business_theme_code(business_theme_code)
    row = _get_business_theme_row(db, current_code, columns)
    if not row:
        raise ValueError("category not found")

    row_dict = dict(row)
    new_code = _normalize_business_theme_code(payload.get("code") or payload.get("top_code")) if ("code" in payload or "top_code" in payload) else (row_dict.get("top_code") or current_code)

    new_name = row["top_name"]
    new_name_en = row["top_name_en"] if "top_name_en" in row.keys() else None
    new_name_cn = row["top_name_cn"] if "top_name_cn" in row.keys() else None
    if any(key in payload for key in ("name", "top_name", "name_en", "top_name_en", "name_cn", "top_name_cn")):
        new_name, new_name_en, new_name_cn = _get_business_theme_names(payload, row_dict)

    new_desc = row["top_desc"]
    if "desc" in payload:
        new_desc = str(payload["desc"]).strip() or None

    if any(key in payload for key in ("name", "top_name", "name_en", "top_name_en", "name_cn", "top_name_cn")) and len(new_name) < 2:
        raise ValueError("name must be at least 2 characters")

    new_active = row["top_active"]
    if "active" in payload:
        new_active = 1 if payload["active"] else 0

    set_parts = ["top_name = ?", "top_desc = ?", "top_active = ?"]
    params: list[object] = [new_name, new_desc, new_active]
    if "top_code" in columns:
        set_parts.append("top_code = ?")
        params.append(new_code or None)
    if "top_name_en" in columns:
        set_parts.append("top_name_en = ?")
        params.append(new_name_en or None)
    if "top_name_cn" in columns:
        set_parts.append("top_name_cn = ?")
        params.append(new_name_cn or None)

    if "top_id" in columns:
        params.append(row_dict["top_id"])
        db.execute(f"UPDATE t_topic SET {', '.join(set_parts)} WHERE top_id = ?", tuple(params))
    else:
        params.append(row_dict["top_code"])
        db.execute(f"UPDATE t_topic SET {', '.join(set_parts)} WHERE top_code = ?", tuple(params))

    db.commit()
    updated = _get_business_theme_row(db, new_code or str(row_dict.get("top_id") or ""), columns)
    return _business_theme_to_dict(updated)


def delete_business_theme(business_theme_code: str) -> dict:
    db = get_db()
    columns = _ensure_optional_business_theme_columns(db)
    code = _normalize_business_theme_code(business_theme_code)
    row = _get_business_theme_row(db, code, columns)
    if not row:
        raise ValueError("category not found")

    row_dict = dict(row)

    action_columns = _table_columns(db, "t_action")
    meeting_columns = _table_columns(db, "t_meeting")
    meeting_instance_columns = _table_columns(db, "t_meeting_instance")
    ref_count = 0
    if "act_topic_id" in action_columns:
        ref_count += int(db.execute("SELECT COUNT(1) FROM t_action WHERE act_topic_id = ?", (row_dict["top_id"],)).fetchone()[0] or 0)
    if "act_secondary_topic_id" in action_columns:
        ref_count += int(db.execute("SELECT COUNT(1) FROM t_action WHERE act_secondary_topic_id = ?", (row_dict["top_id"],)).fetchone()[0] or 0)
    if "act_topic_code" in action_columns:
        ref_count += int(db.execute("SELECT COUNT(1) FROM t_action WHERE act_topic_code = ?", (row_dict.get("top_code") or code,)).fetchone()[0] or 0)
    if "act_secondary_topic_code" in action_columns:
        ref_count += int(db.execute("SELECT COUNT(1) FROM t_action WHERE act_secondary_topic_code = ?", (row_dict.get("top_code") or code,)).fetchone()[0] or 0)

    if "mtg_topic_id" in meeting_columns:
        ref_count += int(db.execute("SELECT COUNT(1) FROM t_meeting WHERE mtg_topic_id = ?", (row_dict["top_id"],)).fetchone()[0] or 0)
    if "mtg_topic_code" in meeting_columns:
        ref_count += int(db.execute("SELECT COUNT(1) FROM t_meeting WHERE mtg_topic_code = ?", (row_dict.get("top_code") or code,)).fetchone()[0] or 0)

    if "min_topic_id" in meeting_instance_columns:
        ref_count += int(db.execute("SELECT COUNT(1) FROM t_meeting_instance WHERE min_topic_id = ?", (row_dict["top_id"],)).fetchone()[0] or 0)
    if "min_topic_code" in meeting_instance_columns:
        ref_count += int(db.execute("SELECT COUNT(1) FROM t_meeting_instance WHERE min_topic_code = ?", (row_dict.get("top_code") or code,)).fetchone()[0] or 0)

    if ref_count > 0:
        raise ValueError("category is referenced and cannot be deleted")

    if "top_id" in columns:
        db.execute("DELETE FROM t_topic WHERE top_id = ?", (row_dict["top_id"],))
    else:
        db.execute("DELETE FROM t_topic WHERE top_code = ?", (row_dict.get("top_code") or code,))
    db.commit()
    return {"deleted": True, "top_code": row_dict.get("top_code") or str(row_dict.get("top_id") or "")}


def list_topics(include_inactive: bool = False) -> list[dict]:
    return list_business_themes(include_inactive=include_inactive)


def create_topic(payload: dict, actor_id: int | None = None) -> dict:
    return create_business_theme(payload, actor_id or 0)


def update_topic(topic_id: int | str, payload: dict, actor_id: int | None = None) -> dict:
    return update_business_theme(str(topic_id), payload, actor_id or 0)


def delete_topic(topic_id: int | str) -> dict:
    return delete_business_theme(str(topic_id))
