"""Workflow step attachment management.

This module provides file upload, download, and deletion operations
for workflow step attachments with policy enforcement.
"""
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from werkzeug.utils import secure_filename

from actionhub.middleware.db import get_db

# Allowed file extensions and their MIME types
ALLOWED_EXTENSIONS = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "csv": "text/csv",
    "txt": "text/plain",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}

# Policy limits
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
MAX_FILES_PER_STEP = 10
MAX_CUMULATIVE_PER_WORKFLOW = 100 * 1024 * 1024  # 100 MB

# Storage directory
ATTACHMENT_STORAGE_DIR = Path(__file__).parent.parent.parent / "attachments" / "workflow"


def get_extension(filename: str) -> str:
    """Extract file extension in lowercase without dot."""
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def is_allowed_file(filename: str) -> bool:
    """Check if file extension is in the allowed list."""
    ext = get_extension(filename)
    return ext in ALLOWED_EXTENSIONS


def validate_attachment_policy(
    step_instance_id: int,
    file_size: int,
    current_count: Optional[int] = None,
    cumulative_size: Optional[int] = None,
) -> Dict[str, Any]:
    """Validate attachment against policy limits.

    Args:
        step_instance_id: The step instance ID.
        file_size: Size of the file being uploaded.
        current_count: Current attachment count (optional, will query if not provided).
        cumulative_size: Current cumulative size for workflow (optional).

    Returns:
        Dict with 'valid' boolean and 'error' message if invalid.
    """
    db = get_db()

    # Check file size
    if file_size > MAX_FILE_SIZE_BYTES:
        return {
            "valid": False,
            "error": f"File size exceeds maximum limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB",
        }

    # Check count per step
    if current_count is None:
        count_row = db.execute(
            """
            SELECT COUNT(*) as cnt
            FROM t_workflow_step_attachment
            WHERE wsa_step_inst_id = ? AND wsa_deleted_at IS NULL
            """,
            (step_instance_id,),
        ).fetchone()
        current_count = count_row["cnt"]

    if current_count >= MAX_FILES_PER_STEP:
        return {
            "valid": False,
            "error": f"Maximum {MAX_FILES_PER_STEP} attachments allowed per step",
        }

    # Check cumulative size per workflow
    if cumulative_size is None:
        cumulative_row = db.execute(
            """
            SELECT COALESCE(SUM(a.wsa_size_bytes), 0) as total
            FROM t_workflow_step_attachment a
            JOIN t_workflow_step_instance s ON s.wsi_id = a.wsa_step_inst_id
            WHERE a.wsa_deleted_at IS NULL
              AND s.wsi_instance_id = (
                  SELECT wsi_instance_id
                  FROM t_workflow_step_instance
                  WHERE wsi_id = ?
              )
            """,
            (step_instance_id,),
        ).fetchone()
        cumulative_size = cumulative_row["total"]

    if cumulative_size + file_size > MAX_CUMULATIVE_PER_WORKFLOW:
        return {
            "valid": False,
            "error": f"Total attachment size would exceed {MAX_CUMULATIVE_PER_WORKFLOW // (1024 * 1024)} MB per workflow",
        }

    return {"valid": True}


def ensure_storage_dir() -> Path:
    """Ensure the attachment storage directory exists."""
    ATTACHMENT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    return ATTACHMENT_STORAGE_DIR


def generate_storage_path(filename: str) -> str:
    """Generate a unique storage path for the file.

    Uses UUID to prevent filename collisions.
    """
    ext = get_extension(filename)
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    # Organize by year/month for better file system performance
    now = datetime.now()
    subdir = f"{now.year}/{now.month:02d}"
    return f"{subdir}/{unique_name}"


def upload_attachment(
    step_instance_id: int,
    filename: str,
    file_data: bytes,
    mime_type: Optional[str],
    uploaded_by: int,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Upload a file attachment for a workflow step.

    Args:
        step_instance_id: The step instance ID.
        filename: Original filename.
        file_data: Binary file data.
        mime_type: MIME type of the file.
        uploaded_by: User ID uploading the file.
        description: Optional description.

    Returns:
        Dict with attachment info or error.

    Raises:
        ValueError: If validation fails.
    """
    db = get_db()

    # Validate filename
    if not filename or not is_allowed_file(filename):
        raise ValueError(
            f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS.keys())}"
        )

    # Secure the filename
    safe_filename = secure_filename(filename)
    if not safe_filename:
        raise ValueError("Invalid filename")

    # Validate policy
    file_size = len(file_data)
    policy = validate_attachment_policy(step_instance_id, file_size)
    if not policy["valid"]:
        raise ValueError(policy["error"])

    # Get action_id from step instance
    step = db.execute(
        """
        SELECT wsi_instance_id
        FROM t_workflow_step_instance
        WHERE wsi_id = ?
        """,
        (step_instance_id,),
    ).fetchone()

    if not step:
        raise ValueError("Step instance not found")

    instance = db.execute(
        """
        SELECT wfi_action_id
        FROM t_workflow_instance
        WHERE wfi_id = ?
        """,
        (step["wsi_instance_id"],),
    ).fetchone()

    action_id = instance["wfi_action_id"] if instance else None

    # Generate storage path and save file
    ensure_storage_dir()
    storage_path = generate_storage_path(safe_filename)
    full_path = ATTACHMENT_STORAGE_DIR / storage_path
    full_path.parent.mkdir(parents=True, exist_ok=True)

    with open(full_path, "wb") as f:
        f.write(file_data)

    # Insert attachment record
    now = datetime.now()
    cursor = db.execute(
        """
        INSERT INTO t_workflow_step_attachment
        (wsa_step_inst_id, wsa_action_id, wsa_filename, wsa_storage_path,
         wsa_mime_type, wsa_size_bytes, wsa_uploaded_by, wsa_uploaded_at, wsa_description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            step_instance_id,
            action_id,
            safe_filename,
            storage_path,
            mime_type or get_extension(safe_filename),
            file_size,
            uploaded_by,
            now,
            description,
        ),
    )
    db.commit()

    attachment_id = cursor.lastrowid

    # Log to action history
    from actionhub.utils.history import log_action_history

    if action_id:
        log_action_history(
            action_id=action_id,
            user_id=uploaded_by,
            change_type="AttachmentAdded",
            field_name="attachment",
            old_value=None,
            new_value=safe_filename,
        )

    return {
        "id": attachment_id,
        "filename": safe_filename,
        "size_bytes": file_size,
        "mime_type": mime_type,
        "uploaded_at": now.isoformat(),
        "uploaded_by": uploaded_by,
    }


def get_step_attachments(step_instance_id: int) -> List[Dict[str, Any]]:
    """Get all active attachments for a step instance.

    Args:
        step_instance_id: The step instance ID.

    Returns:
        List of attachment dictionaries.
    """
    db = get_db()

    rows = db.execute(
        """
        SELECT
            a.wsa_id,
            a.wsa_filename,
            a.wsa_storage_path,
            a.wsa_mime_type,
            a.wsa_size_bytes,
            a.wsa_uploaded_by,
            a.wsa_uploaded_at,
            a.wsa_description,
            u.usr_display_name as uploaded_by_name
        FROM t_workflow_step_attachment a
        LEFT JOIN t_user u ON u.usr_id = a.wsa_uploaded_by
        WHERE a.wsa_step_inst_id = ? AND a.wsa_deleted_at IS NULL
        ORDER BY a.wsa_uploaded_at DESC
        """,
        (step_instance_id,),
    ).fetchall()

    return [dict(row) for row in rows]


def get_attachment(attachment_id: int) -> Optional[Dict[str, Any]]:
    """Get attachment metadata by ID.

    Args:
        attachment_id: The attachment ID.

    Returns:
        Attachment dictionary or None if not found/deleted.
    """
    db = get_db()

    row = db.execute(
        """
        SELECT
            a.wsa_id,
            a.wsa_filename,
            a.wsa_storage_path,
            a.wsa_mime_type,
            a.wsa_size_bytes,
            a.wsa_uploaded_by,
            a.wsa_uploaded_at,
            a.wsa_description,
            a.wsa_step_inst_id,
            a.wsa_action_id
        FROM t_workflow_step_attachment a
        WHERE a.wsa_id = ? AND a.wsa_deleted_at IS NULL
        """,
        (attachment_id,),
    ).fetchone()

    return dict(row) if row else None


def get_attachment_file_path(attachment_id: int) -> Optional[Path]:
    """Get the filesystem path for an attachment.

    Args:
        attachment_id: The attachment ID.

    Returns:
        Path object or None if file doesn't exist.
    """
    attachment = get_attachment(attachment_id)
    if not attachment:
        return None

    file_path = ATTACHMENT_STORAGE_DIR / attachment["wsa_storage_path"]
    if not file_path.exists():
        return None

    return file_path


def delete_attachment(attachment_id: int, deleted_by: int) -> bool:
    """Soft-delete an attachment.

    Args:
        attachment_id: The attachment ID.
        deleted_by: User ID performing the deletion.

    Returns:
        True if deleted, False if not found.

    Raises:
        ValueError: If user is not authorized to delete.
    """
    db = get_db()

    # Get attachment info
    attachment = db.execute(
        """
        SELECT wsa_id, wsa_filename, wsa_uploaded_by, wsa_action_id
        FROM t_workflow_step_attachment
        WHERE wsa_id = ? AND wsa_deleted_at IS NULL
        """,
        (attachment_id,),
    ).fetchone()

    if not attachment:
        return False

    # Check authorization: uploader, admin, or team lead
    user = db.execute(
        """
        SELECT usr_role FROM t_user WHERE usr_id = ?
        """,
        (deleted_by,),
    ).fetchone()

    if not user:
        raise ValueError("User not found")

    if (
        user["usr_role"] not in ("Admin", "TeamLead")
        and user["usr_id"] != attachment["wsa_uploaded_by"]
    ):
        raise ValueError("Not authorized to delete this attachment")

    # Soft delete
    now = datetime.now()
    db.execute(
        """
        UPDATE t_workflow_step_attachment
        SET wsa_deleted_at = ?
        WHERE wsa_id = ?
        """,
        (now, attachment_id),
    )
    db.commit()

    # Log to action history
    from actionhub.utils.history import log_action_history

    if attachment["wsa_action_id"]:
        log_action_history(
            action_id=attachment["wsa_action_id"],
            user_id=deleted_by,
            change_type="AttachmentDeleted",
            field_name="attachment",
            old_value=attachment["wsa_filename"],
            new_value=None,
        )

    return True
