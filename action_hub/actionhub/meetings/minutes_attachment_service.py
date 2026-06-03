"""Local file-backed minutes-of-meeting attachments."""
from __future__ import annotations

import mimetypes
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from werkzeug.utils import secure_filename

from actionhub.middleware.db import get_db

MAX_MINUTES_ATTACHMENTS = 3
MAX_MINUTES_ATTACHMENT_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt"}
STORAGE_DIR = Path(__file__).resolve().parents[2] / "attachments" / "meeting_minutes"


def ensure_minutes_attachment_table(db) -> None:
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS t_meeting_minutes_attachment (
            mma_id INTEGER PRIMARY KEY AUTOINCREMENT,
            mma_instance_id INTEGER NOT NULL,
            mma_original_filename TEXT NOT NULL,
            mma_display_filename TEXT NOT NULL,
            mma_storage_path TEXT NOT NULL,
            mma_mime_type TEXT,
            mma_size_bytes INTEGER NOT NULL,
            mma_uploaded_by INTEGER NOT NULL,
            mma_uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            mma_deleted_at TEXT,
            mma_deleted_by INTEGER,
            FOREIGN KEY (mma_instance_id) REFERENCES t_meeting_instance(min_id) ON DELETE CASCADE,
            FOREIGN KEY (mma_uploaded_by) REFERENCES t_user(usr_id),
            FOREIGN KEY (mma_deleted_by) REFERENCES t_user(usr_id)
        )
        """
    )
    db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_meeting_minutes_attachment_instance
        ON t_meeting_minutes_attachment(mma_instance_id, mma_deleted_at)
        """
    )
    db.commit()


def _extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def _safe_component(value: Any, fallback: str) -> str:
    text = str(value or "").strip() or fallback
    text = re.sub(r"\s+", "_", text)
    safe = secure_filename(text)
    return safe[:80] or fallback


def _meeting_context(db, meeting_id: int) -> dict[str, Any]:
    row = db.execute(
        """
        SELECT mi.min_id, mi.min_title, mi.min_meeting_id, mi.min_created_by,
               mtg.mtg_title AS series_title
        FROM t_meeting_instance mi
        LEFT JOIN t_meeting mtg ON mtg.mtg_id = mi.min_meeting_id
        WHERE mi.min_id = ?
        """,
        (meeting_id,),
    ).fetchone()
    if not row:
        raise ValueError("meeting not found")
    return dict(row)


def _uploader_name(db, user_id: int) -> str:
    row = db.execute("SELECT usr_display_name FROM t_user WHERE usr_id = ?", (user_id,)).fetchone()
    return row["usr_display_name"] if row else f"user_{user_id}"


def build_display_filename(db, meeting_id: int, original_filename: str, uploaded_by: int) -> str:
    context = _meeting_context(db, meeting_id)
    safe_original = secure_filename(original_filename)
    if not safe_original:
        raise ValueError("invalid filename")
    prefix_parts = [
        _safe_component(_uploader_name(db, uploaded_by), "user"),
        _safe_component(context.get("series_title") or f"series_{context.get('min_meeting_id') or 'none'}", "series"),
        _safe_component(f"meeting_{context.get('min_id')}_{context.get('min_title') or ''}", "meeting"),
    ]
    return "__".join(prefix_parts + [safe_original])


def _generate_storage_path(filename: str) -> str:
    extension = _extension(filename)
    now = datetime.now()
    unique_name = f"{uuid.uuid4().hex}.{extension}" if extension else uuid.uuid4().hex
    return f"{now.year}/{now.month:02d}/{unique_name}"


def _row_to_attachment(row) -> dict[str, Any]:
    item = dict(row)
    return {
        "id": item["mma_id"],
        "meeting_id": item["mma_instance_id"],
        "original_filename": item["mma_original_filename"],
        "filename": item["mma_display_filename"],
        "mime_type": item["mma_mime_type"],
        "size_bytes": item["mma_size_bytes"],
        "uploaded_by": item["mma_uploaded_by"],
        "uploaded_by_name": item.get("uploaded_by_name"),
        "uploaded_at": item["mma_uploaded_at"],
    }


def list_minutes_attachments(meeting_id: int) -> list[dict[str, Any]]:
    db = get_db()
    ensure_minutes_attachment_table(db)
    rows = db.execute(
        """
        SELECT mma.*, u.usr_display_name AS uploaded_by_name
        FROM t_meeting_minutes_attachment mma
        LEFT JOIN t_user u ON u.usr_id = mma.mma_uploaded_by
        WHERE mma.mma_instance_id = ? AND mma.mma_deleted_at IS NULL
        ORDER BY mma.mma_uploaded_at DESC, mma.mma_id DESC
        """,
        (meeting_id,),
    ).fetchall()
    return [_row_to_attachment(row) for row in rows]


def upload_minutes_attachment(meeting_id: int, filename: str, file_bytes: bytes, mime_type: str | None, uploaded_by: int) -> dict[str, Any]:
    if not filename or not filename.strip():
        raise ValueError("filename is required")
    if not file_bytes:
        raise ValueError("empty file")
    if len(file_bytes) > MAX_MINUTES_ATTACHMENT_BYTES:
        raise ValueError("file size exceeds 5 MB")
    extension = _extension(filename)
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("file type not allowed")

    db = get_db()
    ensure_minutes_attachment_table(db)
    context = _meeting_context(db, meeting_id)
    active_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM t_meeting_minutes_attachment
        WHERE mma_instance_id = ? AND mma_deleted_at IS NULL
        """,
        (meeting_id,),
    ).fetchone()["count"]
    if active_count >= MAX_MINUTES_ATTACHMENTS:
        raise ValueError("maximum 3 minutes attachments allowed")

    display_filename = build_display_filename(db, meeting_id, filename, uploaded_by)
    storage_path = _generate_storage_path(display_filename)
    full_path = STORAGE_DIR / storage_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(file_bytes)

    detected_mime_type = mime_type or mimetypes.guess_type(display_filename)[0] or "application/octet-stream"
    cursor = db.execute(
        """
        INSERT INTO t_meeting_minutes_attachment
            (mma_instance_id, mma_original_filename, mma_display_filename, mma_storage_path,
             mma_mime_type, mma_size_bytes, mma_uploaded_by, mma_uploaded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            context["min_id"],
            secure_filename(filename),
            display_filename,
            storage_path,
            detected_mime_type,
            len(file_bytes),
            uploaded_by,
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    db.commit()
    attachment_id = int(cursor.lastrowid)
    return get_minutes_attachment(attachment_id) or {}


def get_minutes_attachment(attachment_id: int) -> dict[str, Any] | None:
    db = get_db()
    ensure_minutes_attachment_table(db)
    row = db.execute(
        """
        SELECT mma.*, u.usr_display_name AS uploaded_by_name
        FROM t_meeting_minutes_attachment mma
        LEFT JOIN t_user u ON u.usr_id = mma.mma_uploaded_by
        WHERE mma.mma_id = ? AND mma.mma_deleted_at IS NULL
        """,
        (attachment_id,),
    ).fetchone()
    return _row_to_attachment(row) if row else None


def get_minutes_attachment_file_path(attachment_id: int) -> Path | None:
    db = get_db()
    ensure_minutes_attachment_table(db)
    row = db.execute(
        """
        SELECT mma_storage_path
        FROM t_meeting_minutes_attachment
        WHERE mma_id = ? AND mma_deleted_at IS NULL
        """,
        (attachment_id,),
    ).fetchone()
    if not row:
        return None
    path = STORAGE_DIR / row["mma_storage_path"]
    return path if path.exists() else None


def delete_minutes_attachment(attachment_id: int, deleted_by: int) -> bool:
    db = get_db()
    ensure_minutes_attachment_table(db)
    row = db.execute(
        """
        SELECT mma_id
        FROM t_meeting_minutes_attachment
        WHERE mma_id = ? AND mma_deleted_at IS NULL
        """,
        (attachment_id,),
    ).fetchone()
    if not row:
        return False
    db.execute(
        """
        UPDATE t_meeting_minutes_attachment
        SET mma_deleted_at = ?, mma_deleted_by = ?
        WHERE mma_id = ?
        """,
        (datetime.now().isoformat(timespec="seconds"), deleted_by, attachment_id),
    )
    db.commit()
    return True
