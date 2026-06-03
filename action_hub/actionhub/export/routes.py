from datetime import datetime, timezone

from flask import Blueprint, request, send_file

from actionhub.export.excel_writer import build_actions_workbook
from actionhub.middleware.auth_middleware import login_required


export_bp = Blueprint("export", __name__, url_prefix="/api/export")


@export_bp.get("/actions")
@login_required
def export_actions():
    filters = {
        "status": request.args.get("status"),
        "team_id": request.args.get("team_id") or request.args.get("department_id"),
        "priority": request.args.get("priority"),
        "search": request.args.get("search"),
        "sort_by": request.args.get("sort_by", "created_at"),
        "sort_order": request.args.get("sort_order", "desc"),
    }
    stream = build_actions_workbook(filters)
    filename = f"actionhub_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        stream,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
