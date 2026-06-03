from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from typing import Iterable

from actionhub.decisions.service import DecisionService
from actionhub.meetings.memo_text_service import list_text_memos
from actionhub.meetings.service import (
    get_meeting,
    get_meeting_actions,
    get_meeting_participants,
    get_occurrence_comments,
)
from actionhub.middleware.db import get_db

try:  # pragma: no cover - exercised indirectly when dependency is available
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import os as _os

    # Register a CJK-capable font so Chinese characters render correctly.
    # Prefer SimHei (plain TTF, ships with Windows); fall back to other common paths.
    _CJK_FONT_NAME = "SimHei"
    _CJK_FONT_CANDIDATES = [
        r"C:\Windows\Fonts\simhei.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # fallback on Linux (Latin only)
        "/System/Library/Fonts/PingFang.ttc",               # macOS fallback
    ]
    _cjk_registered = False
    for _font_path in _CJK_FONT_CANDIDATES:
        if _os.path.isfile(_font_path):
            try:
                pdfmetrics.registerFont(TTFont(_CJK_FONT_NAME, _font_path))
                _cjk_registered = True
            except Exception:
                pass
            break

    REPORTLAB_AVAILABLE = True
except Exception:  # pragma: no cover - fallback path
    REPORTLAB_AVAILABLE = False
    _cjk_registered = False
    _CJK_FONT_NAME = "Helvetica"


def _sanitize_filename(text: str) -> str:
    # Restrict to ASCII alphanumeric only so the result is safe as an HTTP header value.
    cleaned = "".join(ch if (ch.isalnum() and ord(ch) < 128) or ch in ("-", "_") else "_" for ch in text.strip())
    return cleaned or "MoM"


def _rl_escape(text: str) -> str:
    """Escape XML special characters for reportlab Paragraph."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _build_reportlab_pdf(lines: list[str], title: str) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    # Override fonts to CJK-capable variant when available so Chinese renders correctly.
    if _cjk_registered:
        title_style = ParagraphStyle(
            "CjkTitle",
            parent=styles["Title"],
            fontName=_CJK_FONT_NAME,
            fontSize=16,
            leading=22,
        )
        body_style = ParagraphStyle(
            "CjkBody",
            parent=styles["BodyText"],
            fontName=_CJK_FONT_NAME,
            fontSize=10,
            leading=14,
        )
    else:
        title_style = styles["Title"]
        body_style = styles["BodyText"]

    story = [Paragraph(_rl_escape(title), title_style), Spacer(1, 12)]
    for line in lines:
        story.append(Paragraph(_rl_escape(line), body_style))
        story.append(Spacer(1, 4))
    doc.build(story)
    return buffer.getvalue()


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_basic_pdf(lines: Iterable[str], title: str) -> bytes:
    # Minimal one-page PDF that is valid enough for download/preview.
    content_lines = [f"({ _pdf_escape(title) }) Tj", "0 -20 Td"]
    for line in lines:
        content_lines.append(f"({ _pdf_escape(line) }) Tj")
        content_lines.append("0 -14 Td")
    stream = "BT /F1 12 Tf 50 780 Td " + " ".join(content_lines) + " ET"
    stream_bytes = stream.encode("latin-1", errors="replace")

    objects: list[bytes] = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    objects.append(b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n")
    objects.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
    objects.append(b"5 0 obj << /Length " + str(len(stream_bytes)).encode("ascii") + b" >> stream\n" + stream_bytes + b"\nendstream endobj\n")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode("ascii")
    )
    return bytes(pdf)


def generate_minutes_pdf(min_id: int, lang: str = "en") -> tuple[bytes, str]:
    meeting = get_meeting(min_id)
    participants = get_meeting_participants(min_id)
    new_actions = get_meeting_actions(min_id)
    decisions = DecisionService.list_decisions(meeting_id=min_id, limit=500, offset=0)
    occurrence_comments = get_occurrence_comments(min_id)
    text_memos = list_text_memos(min_id)

    db = get_db()
    series_title = meeting.get("min_title") or "Meeting"
    parent_id = meeting.get("min_meeting_id")
    if parent_id:
        parent = db.execute("SELECT mtg_title FROM t_meeting WHERE mtg_id = ?", (parent_id,)).fetchone()
        if parent and parent["mtg_title"]:
            series_title = parent["mtg_title"]

    occurrence_title = meeting.get("min_title") or series_title
    date_value = meeting.get("min_date") or datetime.now(UTC).date().isoformat()
    filename = f"MoM_{_sanitize_filename(series_title)}_{date_value}.pdf"

    # Build follow-up lookup (latest per action for this occurrence)
    follow_up_map: dict[int, dict] = {}
    for row in occurrence_comments.get("follow_up_current", []):
        aid = row.get("action_id")
        if aid and aid not in follow_up_map:
            follow_up_map[int(aid)] = row

    reviewed_action_map: dict[int, dict] = {}
    for comment in occurrence_comments.get("current", []):
        action_id = comment.get("action_id")
        if not action_id or action_id in reviewed_action_map:
            continue
        reviewed_action_map[int(action_id)] = comment
    reviewed_actions = list(reviewed_action_map.values())

    lines: list[str] = [
        f"Series: {series_title}",
        f"Occurrence: {occurrence_title}",
        f"Date: {date_value}",
        f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "Participants:",
    ]
    for participant in participants:
        lines.append(f"- {participant.get('usr_display_name') or participant.get('mpa_user_id')} ({participant.get('mpa_kind') or 'Optional'})")

    # ── Memo (meeting notes + text memos combined) ──
    lines.extend(["", "Memo:"])
    has_memo_content = False
    notes = str(meeting.get("min_notes") or "").strip()
    if notes:
        lines.append(notes)
        has_memo_content = True
    if text_memos:
        for memo in text_memos:
            title = memo.get("mmm_title") or "Untitled"
            body = str(memo.get("mmm_body") or "-")
            if len(body) > 500:
                body = body[:500] + "..."
            lines.append(f"- {title}")
            lines.append(f"  {body}")
            has_memo_content = True
    if not has_memo_content:
        lines.append("- None")

    # ── Actions Reviewed (with follow-up details) ──
    lines.extend(["", "Actions Reviewed:"])
    if reviewed_actions:
        for action in reviewed_actions:
            action_title = action.get("action_title") or "Untitled action"
            lines.append(f"- {action_title}")
            aid = action.get("action_id")
            fu = follow_up_map.get(int(aid)) if aid else None
            if fu:
                fu_parts = []
                if fu.get("afb_status"):
                    fu_parts.append(f"Status: {fu['afb_status']}")
                if fu.get("afb_completion_pct") is not None:
                    fu_parts.append(f"Completion: {fu['afb_completion_pct']}%")
                if fu.get("afb_comment"):
                    fu_parts.append(f"Comment: {fu['afb_comment']}")
                if fu.get("afb_blockers"):
                    fu_parts.append(f"Blockers: {fu['afb_blockers']}")
                if fu_parts:
                    lines.append(f"  Follow-up: {' | '.join(fu_parts)}")
    else:
        lines.append("- None")

    # ── New Actions (full detail) ──
    lines.extend(["", "New Actions:"])
    if new_actions:
        for action in new_actions:
            ref = action.get("act_ref_code") or action.get("act_ref") or ""
            title = action.get("act_title") or "Untitled"
            status = action.get("act_status") or "-"
            lines.append(f"- {ref}: {title} [{status}]")
            detail_parts = []
            if action.get("act_deadline") or action.get("act_due_date"):
                detail_parts.append(f"Deadline: {action.get('act_deadline') or action.get('act_due_date')}")
            if action.get("lead_name"):
                detail_parts.append(f"Lead: {action['lead_name']}")
            if action.get("act_completion_pct") is not None:
                detail_parts.append(f"Completion: {action['act_completion_pct']}%")
            if detail_parts:
                lines.append(f"  {' | '.join(detail_parts)}")
            if action.get("act_desc"):
                desc = str(action["act_desc"])
                if len(desc) > 200:
                    desc = desc[:200] + "..."
                lines.append(f"  Description: {desc}")
            # Follow-up for this action
            fu = follow_up_map.get(int(action.get("act_id", 0)))
            if fu:
                fu_parts = []
                if fu.get("afb_status"):
                    fu_parts.append(f"Status: {fu['afb_status']}")
                if fu.get("afb_completion_pct") is not None:
                    fu_parts.append(f"{fu['afb_completion_pct']}%")
                if fu.get("afb_comment"):
                    fu_parts.append(fu["afb_comment"])
                if fu.get("afb_blockers"):
                    fu_parts.append(f"Blockers: {fu['afb_blockers']}")
                if fu_parts:
                    lines.append(f"  Follow-up: {' | '.join(fu_parts)}")
    else:
        lines.append("- None")

    # ── Decisions (full detail) ──
    lines.extend(["", "Decisions:"])
    if decisions:
        for decision in decisions:
            title = decision.get("mdc_title") or "Untitled"
            status = decision.get("mdc_status") or "-"
            lines.append(f"- {title} [{status}]")
            detail_parts = []
            if decision.get("category_name"):
                detail_parts.append(f"Category: {decision['category_name']}")
            if decision.get("creator_name"):
                detail_parts.append(f"Created by: {decision['creator_name']}")
            if decision.get("mdc_decided_at"):
                detail_parts.append(f"Decided: {decision['mdc_decided_at']}")
            if decision.get("mdc_tags"):
                detail_parts.append(f"Tags: {decision['mdc_tags']}")
            if detail_parts:
                lines.append(f"  {' | '.join(detail_parts)}")
            if decision.get("mdc_body"):
                body = str(decision["mdc_body"])
                if len(body) > 200:
                    body = body[:200] + "..."
                lines.append(f"  Body: {body}")
            if decision.get("mdc_context"):
                ctx = str(decision["mdc_context"])
                if len(ctx) > 200:
                    ctx = ctx[:200] + "..."
                lines.append(f"  Context: {ctx}")
            if decision.get("mdc_reason"):
                reason = str(decision["mdc_reason"])
                if len(reason) > 200:
                    reason = reason[:200] + "..."
                lines.append(f"  Reason: {reason}")
    else:
        lines.append("- None")

    # ── Conversation Comments ──
    conversation = [
        c for c in occurrence_comments.get("current", [])
        if c.get("comment_body") and not c.get("action_id")
    ]
    if conversation:
        lines.extend(["", "Comments:"])
        for comment in conversation:
            author = comment.get("usr_display_name") or "Unknown"
            body = str(comment["comment_body"])
            if len(body) > 300:
                body = body[:300] + "..."
            lines.append(f"- {author}: {body}")

    pdf_title = f"会议纪要 — {series_title}" if lang == "zh" else f"Minutes of Meeting — {series_title}"

    if REPORTLAB_AVAILABLE:
        pdf_bytes = _build_reportlab_pdf(lines, pdf_title)
    else:
        pdf_bytes = _build_basic_pdf(lines, pdf_title)

    return pdf_bytes, filename
