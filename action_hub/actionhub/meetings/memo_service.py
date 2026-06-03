"""Meeting memo blob upload/download service."""
from __future__ import annotations

import mimetypes

from actionhub.middleware.db import get_db

MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB


def upload_memo(meeting_id: int, filename: str, file_bytes: bytes,
                uploader_id: int) -> dict:
    if len(file_bytes) > MAX_FILE_BYTES:
        raise ValueError(f"File too large (max {MAX_FILE_BYTES // 1024 // 1024} MB)")
    if not filename.strip():
        raise ValueError("filename is required")

    db = get_db()
    # Verify meeting exists
    if not db.execute("SELECT 1 FROM t_meeting_instance WHERE min_id = ?", (meeting_id,)).fetchone():
        raise ValueError("meeting not found")

    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    cur = db.execute(
        """
        INSERT INTO t_meeting_summary
            (msm_instance_id, msm_filename, msm_file_path, msm_file_data, msm_file_mime,
             msm_file_size, msm_uploader_id)
        VALUES (?, ?, '', ?, ?, ?, ?)
        """,
        (meeting_id, filename, file_bytes, mime_type, len(file_bytes), uploader_id),
    )
    db.commit()
    return get_memos(meeting_id)[-1]


def get_memos(meeting_id: int) -> list[dict]:
    db = get_db()
    rows = db.execute(
        """
        SELECT m.msm_id, m.msm_instance_id, m.msm_filename,
               m.msm_file_mime, m.msm_file_size, m.msm_uploaded_at,
               u.usr_display_name AS uploader_name
        FROM t_meeting_summary m
        JOIN t_user u ON u.usr_id = m.msm_uploader_id
        WHERE m.msm_instance_id = ?
        ORDER BY m.msm_uploaded_at DESC
        """,
        (meeting_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_memo_blob(msm_id: int) -> dict | None:
    """Returns dict with filename, mime, data bytes — for streaming download."""
    db = get_db()
    row = db.execute(
        "SELECT msm_instance_id, msm_filename, msm_file_mime, msm_file_data FROM t_meeting_summary WHERE msm_id = ?",
        (msm_id,),
    ).fetchone()
    return dict(row) if row else None


def delete_memo(msm_id: int) -> None:
    db = get_db()
    db.execute("DELETE FROM t_meeting_summary WHERE msm_id = ?", (msm_id,))
    db.commit()
