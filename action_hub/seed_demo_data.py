"""
seed_demo_data.py — Rich demo dataset for ActionHub

Creates:
  - 6 demo users (TeamLeads + Members across departments)
  - 6 topics (global subject areas)
  - 50 actions with varied statuses, priorities, departments, deadlines
  - Assignments (Lead for every action)
  - Some action history entries
  - 3 meeting instances

Run: python seed_demo_data.py
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

# Ensure app root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from actionhub import create_app
from actionhub.auth.service import create_user
from actionhub.middleware.db import get_db


# ── Date helpers ──────────────────────────────────────────────────────────────
TODAY = date.today()


def days(n: int) -> str:
    """Return ISO date string n days from today (negative = past)."""
    return (TODAY + timedelta(days=n)).isoformat()


# ── Users ─────────────────────────────────────────────────────────────────────
USERS: list[dict] = [
    {"username": "lead_qa",    "password": "Demo@2026", "display_name": "Sarah Chen",    "email": "sarah@ah.local",   "role": "Member", "dept": 4},   # QA
    {"username": "lead_hse",   "password": "Demo@2026", "display_name": "Mark Li",       "email": "mark@ah.local",    "role": "Member", "dept": 5},   # HP
    {"username": "mem_ci",     "password": "Demo@2026", "display_name": "Tom Wang",      "email": "tom@ah.local",     "role": "Member",   "dept": 3},   # CI
    {"username": "mem_mm",     "password": "Demo@2026", "display_name": "Alice Zhou",    "email": "alice@ah.local",   "role": "Member",   "dept": 10},  # MM
    {"username": "mem_plan",   "password": "Demo@2026", "display_name": "James Lin",     "email": "james@ah.local",   "role": "Member",   "dept": 12},  # PLAN
    {"username": "mem_log",    "password": "Demo@2026", "display_name": "Lucy Huang",    "email": "lucy@ah.local",    "role": "Member",   "dept": 7},   # LOG
]

# ── Topics ────────────────────────────────────────────────────────────────────
# Using dep_id=1 for all (global concept; old schema requires NOT NULL dep_id)
TOPICS: list[tuple] = [
    ("Safety Initiative",        "安全专项",           1),
    ("Production Efficiency",    "生产效率提升",       2),
    ("Quality Improvement",      "质量改进",           4),
    ("HSE Compliance",           "HSE合规",            5),
    ("Digital Transformation",   "数字化转型",         6),
    ("ESG Reporting",            "ESG报告",            1),
]

# ── Actions ───────────────────────────────────────────────────────────────────
# Format: (title, dept_id, team_id, topic_idx+1, cat_id, priority, status, deadline_days, actual_date_days)
# deadline_days: days from today (negative = past, positive = future)
# actual_date_days: set only if Done (days from today)
ACTIONS: list[tuple] = [
    # Open — future deadlines
    ("Install safety guards on production line A",        5, None, 1, 1, "Critical", "Open",        7,  None),
    ("Update Emergency Response Plan",                    5, None, 4, 2, "High",     "Open",       14,  None),
    ("Conduct raw material traceability audit",           4, None, 3, 4, "High",     "Open",       21,  None),
    ("Deploy forklift speed control devices",             6, None, 1, 6, "Medium",   "Open",       30,  None),
    ("Review supplier qualification documents",           8, None, 3, 1, "Medium",   "Open",       35,  None),
    ("Prepare Q3 ESG sustainability report draft",        3, None, 6, 8, "Low",      "Open",       45,  None),
    ("Upgrade WMS barcode scanning hardware",             6, None, 5, 6, "Medium",   "Open",       28,  None),
    ("Finalize labor cost analysis template",            12, None, 2, 2, "Low",      "Open",       60,  None),
    # Open — overdue (past deadlines)
    ("Complete ISO 45001 gap analysis",                   5, None, 4, 2, "Critical", "Open",       -5,  None),
    ("Submit Q2 EHS incident summary",                    5, None, 4, 8, "High",     "Open",       -3,  None),
    ("Resolve packing material delamination defect",      4, None, 3, 4, "Critical", "Open",       -8,  None),
    ("Fix cycle time deviation on Line B",                2, None, 2, 2, "High",     "Open",      -14,  None),
    # In Progress — future
    ("Implement 5S in warehouse zone C",                  6, None, 2, 2, "High",     "In Progress", 10,  None),
    ("Develop automated KPI reporting dashboard",         3, None, 5, 6, "High",     "In Progress", 18,  None),
    ("Renegotiate packaging supplier contract",           8, None, 3, 1, "Medium",   "In Progress", 25,  None),
    ("Train production team on new SOP v3.2",            11, None, 2, 7, "Medium",   "In Progress", 20,  None),
    ("Execute preventive maintenance on conveyor system", 10, None, 2, 2, "High",     "In Progress", 12,  None),
    ("Validate cold storage temperature logs (Q3)",       6, None, 4, 2, "Medium",   "In Progress", 15,  None),
    # In Progress — overdue
    ("Close CAPA for customer complaint #2024-078",       4, None, 3, 4, "Critical", "In Progress", -2,  None),
    ("Reduce inbound freight cost by 8%",                 7, None, 2, 1, "High",     "In Progress", -7,  None),
    ("Update BOM for model X revision",                  11, None, 3, 3, "Medium",   "In Progress", -4,  None),
    ("Implement two-bin Kanban for fasteners",           12, None, 2, 5, "Medium",   "In Progress", -1,  None),
    # In Progress
    ("Approve revised FMEA for assembly process",         4, None, 3, 4, "High",     "In Progress", 5,  None),
    ("Review Q3 production schedule vs capacity",        12, None, 2, 2, "Medium",   "In Progress", 8,  None),
    ("Validate new cleaning agent compatibility",         5, None, 4, 2, "High",     "In Progress", 3,  None),
    ("Sign off digital work instruction system go-live",  3, None, 5, 6, "High",     "In Progress", 6,  None),
    ("Confirm AGV path layout approval",                 10, None, 2, 6, "Medium",   "In Progress", 9,  None),
    # On Hold
    ("Replace aging PLC controllers (budget pending)",   10, None, 2, 6, "High",     "On Hold",     30,  None),
    ("Expand warehouse mezzanine (awaiting permit)",      6, None, 2, 8, "Medium",   "On Hold",     60,  None),
    ("Integrate ERP with MES (vendor delay)",             3, None, 5, 6, "Critical", "On Hold",     45,  None),
    # Done — completed recently
    ("Complete PPE compliance inspection",                5, None, 4, 2, "High",     "Done",        -3,  -3),
    ("Conduct new employee safety induction",             5, None, 4, 7, "Medium",   "Done",        -7,  -7),
    ("Update chemical storage SDS register",              5, None, 4, 2, "Medium",   "Done",       -10, -10),
    ("Resolve mislabelled PO issue with supplier Y",      9, None, 3, 1, "High",     "Done",        -5,  -5),
    ("Deploy new HR onboarding digital form",             3, None, 5, 6, "Low",      "Done",       -12, -12),
    ("Calibrate torque wrenches Q3",                     10, None, 2, 2, "Medium",   "Done",        -8,  -8),
    ("Complete halogen-free material validation",         4, None, 3, 4, "High",     "Done",       -15, -15),
    ("Review and archive Q2 logistics KPI report",        7, None, 2, 8, "Low",      "Done",        -4,  -4),
    # On Hold (formerly Postponed)
    ("Relayout assembly cell for ergonomics",             2, None, 2, 2, "Medium",   "On Hold",     90,  None),
    ("Migrate legacy QMS to cloud platform",              4, None, 5, 6, "High",     "On Hold",    120,  None),
    ("Commission solar panel energy monitoring system",   1, None, 6, 6, "Low",      "On Hold",    180,  None),
    # Cancelled
    ("Pilot drone-based inventory count",                 6, None, 5, 6, "Low",      "Cancelled",   30,  None),
    ("Evaluate biometric time attendance system",         1, None, 5, 6, "Low",      "Cancelled",   60,  None),
    # Additional mix
    ("Conduct supplier on-site audit — Supplier A",       8, None, 3, 1, "High",     "In Progress", 14,  None),
    ("Reduce packaging material waste by 15%",            9, None, 2, 2, "Medium",   "Open",        40,  None),
    ("Update shift schedule rotation plan",              12, None, 2, 8, "Low",      "In Progress", 22,  None),
    ("Install IoT temperature sensors in cold room",      6, None, 5, 6, "Medium",   "Open",        55,  None),
    ("Investigate root cause of Line C downtime spikes", 10, None, 2, 2, "Critical", "In Progress", -3,  None),
    ("Review and validate production buffer stock",      12, None, 2, 5, "Medium",   "In Progress", 7,  None),
    ("Close NPI action items for product launch P5",      4, None, 3, 4, "High",     "In Progress", -6,  None),
]


def _next_ref(db, year: int) -> str:
    prefix = f"ACT-{year}-"
    row = db.execute(
        "SELECT act_ref FROM t_action WHERE act_ref LIKE ? ORDER BY act_ref DESC LIMIT 1",
        (f"{prefix}%",),
    ).fetchone()
    seq = 1
    if row:
        try:
            seq = int(row["act_ref"].split("-")[-1]) + 1
        except ValueError:
            pass
    return f"{prefix}{seq:05d}"


def seed_demo(app) -> None:
    with app.app_context():
        db = get_db()
        action_columns = {row[1] for row in db.execute("PRAGMA table_info(t_action)").fetchall()}
        if "act_tags" not in action_columns:
            db.execute("ALTER TABLE t_action ADD COLUMN act_tags TEXT")
        year = TODAY.year

        # ── Create users ──────────────────────────────────────────────────────
        user_ids: list[int] = [1]  # admin already exists
        for u in USERS:
            try:
                uid = create_user(
                    username=u["username"],
                    password=u["password"],
                    display_name=u["display_name"],
                    email=u["email"],
                    role=u["role"],
                )
                user_ids.append(uid)
                print(f"  ✓ User created: {u['display_name']} ({u['role']})")
            except Exception as e:
                # May already exist
                row = db.execute(
                    "SELECT usr_id FROM t_user WHERE usr_username = ?",
                    (u["username"],),
                ).fetchone()
                if row:
                    user_ids.append(row["usr_id"])
                    print(f"  – User exists: {u['display_name']}")
                else:
                    print(f"  ✗ Failed to create user {u['username']}: {e}")

        # ── Create topics ─────────────────────────────────────────────────────
        topic_ids: list[int] = []
        for (name_en, name_cn, dep_id) in TOPICS:
            existing = db.execute(
                "SELECT top_id FROM t_topic WHERE top_name = ?", (name_en,)
            ).fetchone()
            if existing:
                topic_ids.append(existing["top_id"])
                print(f"  – Topic exists: {name_en}")
            else:
                cur = db.execute(
                    "INSERT INTO t_topic (top_name) VALUES (?)",
                    (name_en,),
                )
                db.commit()
                topic_ids.append(cur.lastrowid)
                print(f"  ✓ Topic created: {name_en}")

        # ── Create actions ────────────────────────────────────────────────────
        # Round-robin assignees (skip admin for variety)
        assignees = user_ids[1:] if len(user_ids) > 1 else user_ids
        created_count = 0

        for i, (title, dept_id, team_id, topic_idx, cat_id, priority, status, dl_days, act_days) in enumerate(ACTIONS):
            # Check duplicate by title
            dup = db.execute("SELECT act_id FROM t_action WHERE act_title = ?", (title,)).fetchone()
            if dup:
                print(f"  – Skipping (exists): {title[:50]}")
                continue

            ref = _next_ref(db, year)
            deadline = days(dl_days) if dl_days is not None else None
            actual_date = days(act_days) if act_days is not None else None
            topic_id = topic_ids[topic_idx - 1] if topic_idx and topic_idx <= len(topic_ids) else None
            assignee_id = assignees[i % len(assignees)]

            # Insert the action with intended status directly
            db.execute(
                """
                INSERT INTO t_action (
                    act_ref, act_title, act_tags, act_team_id, act_topic_id,
                    act_category_id, act_priority, act_owner_id, act_status,
                    act_deadline, act_actual_date, act_source, act_created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Manual', ?)
                """,
                (ref, title, f"SEED, DEMO-{10000 + i}", dept_id, topic_id, cat_id, priority, assignee_id, status,
                 deadline, actual_date, 1),  # created_by = admin
            )
            action_id = db.execute(
                "SELECT act_id FROM t_action WHERE act_ref = ?", (ref,)
            ).fetchone()["act_id"]

            # On Hold reason
            if status == "On Hold":
                db.execute(
                    "UPDATE t_action SET act_hold_reason = ? WHERE act_id = ?",
                    ("Pending budget approval or external dependency", action_id),
                )

            # Cancelled reason
            if status == "Cancelled":
                db.execute(
                    "UPDATE t_action SET act_cancel_reason = ? WHERE act_id = ?",
                    ("Business priority changed; scope rescoped", action_id),
                )

            # Create assignment (Lead)
            db.execute(
                """
                INSERT OR IGNORE INTO t_assignment (
                    asg_action_id, asg_user_id, asg_role, asg_status, asg_assigned_by
                ) VALUES (?, ?, 'Lead', 'Accepted', 1)
                """,
                (action_id, assignee_id),
            )

            # Log creation history
            db.execute(
                """
                INSERT INTO t_action_history (
                    ahi_action_id, ahi_change_type, ahi_field, ahi_new_value, ahi_changed_by
                ) VALUES (?, 'Created', 'act_id', ?, 1)
                """,
                (action_id, str(action_id)),
            )

            # For non-Open statuses, also log the status change
            if status != "Open":
                db.execute(
                    """
                    INSERT INTO t_action_history (
                        ahi_action_id, ahi_change_type, ahi_field,
                        ahi_old_value, ahi_new_value, ahi_changed_by
                    ) VALUES (?, 'StatusChange', 'act_status', 'Open', ?, ?)
                    """,
                    (action_id, status, assignee_id),
                )

            db.commit()
            created_count += 1

        print(f"\n  ✓ {created_count} actions created (of {len(ACTIONS)} total)")

        # ── Meeting instances ─────────────────────────────────────────────────
        # Only insert if t_meeting_instance exists
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='t_meeting_instance'"
        ).fetchone()
        if tables:
            meetings = [
                (
                    "Weekly Safety Standup",
                    days(-14), "HSE Weekly", topic_ids[0] if topic_ids else None,
                    """Attendees: EHS team, production floor leads\n\n**Key Points:**\n- Reviewed 3 near-miss incidents from previous week; root cause identified as inadequate guarding on Line A\n- PPE compliance audit results: 94% pass rate, 6% non-conformances in warehouse zone\n- Confirmed completion of monthly fire extinguisher inspection\n\n**Decisions:**\n- Immediate installation of safety guards on Line A (ACT-2026-00001 raised)\n- Schedule reinforcement training for warehouse staff on PPE usage\n\n**Next Steps:**\n- EHS lead to submit incident report by Friday\n- Supervisor to verify guard installation by next standup"""
                ),
                (
                    "Q3 Quality Review",
                    days(-7), "QA Quarterly", topic_ids[2] if len(topic_ids) > 2 else None,
                    """Attendees: QA Manager, R&D Lead, Production Manager, Customer Service Rep\n\n**Key Points:**\n- Q3 defect rate: 1.8% (target <2%), improvement from Q2 2.3%\n- Customer complaint #2024-078 on packing delamination — CAPA in progress\n- ISO 9001 internal audit scheduled for next month; 4 open findings from last cycle\n- New supplier qualification process reviewed; 2 suppliers pending final approval\n\n**Decisions:**\n- Extend CAPA deadline for complaint #2024-078 by 2 weeks due to material testing backlog\n- Approve revised inspection checklist v2.4 for production\n\n**Action Items:**\n- QA team to close 4 internal audit findings before external audit (30-day window)\n- Supplier qualification documents to be reviewed by procurement (ACT-2026-00005 updated)"""
                ),
            ]
            for (title, mdate, mtype, tid, notes) in meetings:
                series_row = db.execute(
                    "SELECT mtg_id FROM t_meeting WHERE mtg_title = ?",
                    (title,),
                ).fetchone()
                if series_row:
                    series_id = series_row["mtg_id"]
                else:
                    db.execute(
                        """
                        INSERT INTO t_meeting (mtg_title, mtg_description, mtg_topic_id, mtg_visibility, mtg_created_by)
                        VALUES (?, ?, ?, 'public', 1)
                        """,
                        (title, f"Seeded series for {title}", tid),
                    )
                    series_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

                db.execute(
                    """
                    INSERT OR IGNORE INTO t_meeting_instance
                    (min_meeting_id, min_title, min_date, min_type, min_topic_id, min_notes, min_created_by)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                    """,
                    (series_id, title, mdate, mtype, tid, notes),
                )
            db.commit()
            print(f"  ✓ {len(meetings)} meeting instances created")
        else:
            print("  – t_meeting_instance table not found; skipping meetings (run schema migration)")

        # ── Summary ───────────────────────────────────────────────────────────
        counts = db.execute(
            "SELECT act_status, COUNT(*) AS n FROM t_action GROUP BY act_status ORDER BY act_status"
        ).fetchall()
        print("\n── Action Status Breakdown ──")
        for row in counts:
            print(f"   {row['act_status']:15s} {row['n']:3d}")
        total = db.execute("SELECT COUNT(*) AS n FROM t_action").fetchone()["n"]
        print(f"   {'TOTAL':15s} {total:3d}")

        overdue = db.execute(
            """
            SELECT COUNT(*) AS n FROM t_action
            WHERE act_status NOT IN ('Done', 'Cancelled')
              AND act_deadline < date('now')
            """
        ).fetchone()["n"]
        print(f"\n  Overdue actions: {overdue}")


if __name__ == "__main__":
    app = create_app()
    print("\n=== ActionHub Demo Seed ===\n")
    seed_demo(app)
    print("\n✓ Done! Visit http://127.0.0.1:5000\n")
