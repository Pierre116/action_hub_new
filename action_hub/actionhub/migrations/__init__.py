"""Database migration runner with version tracking.

Usage from init_db() or init_app():
    from actionhub.migrations import run_pending_migrations
    run_pending_migrations(db)

Each migration module must expose:
    VERSION: int       — unique sequential version number
    DESCRIPTION: str   — human-readable description
    def up(db):        — apply migration (receives sqlite3.Connection)
"""
from __future__ import annotations

import importlib
import pkgutil
import sqlite3
from pathlib import Path


_MIGRATIONS_PACKAGE = "actionhub.migrations"


def _ensure_version_table(db: sqlite3.Connection) -> None:
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS t_schema_version (
            sv_version     INTEGER PRIMARY KEY,
            sv_description TEXT NOT NULL,
            sv_applied_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.commit()


def _current_version(db: sqlite3.Connection) -> int:
    row = db.execute(
        "SELECT MAX(sv_version) AS v FROM t_schema_version"
    ).fetchone()
    return int(row[0] or row["v"] or 0) if row else 0


def _discover_migrations() -> list[tuple[int, str, object]]:
    """Return sorted list of (version, description, module)."""
    package_path = str(Path(__file__).resolve().parent)
    found: list[tuple[int, str, object]] = []
    for importer, modname, ispkg in pkgutil.iter_modules([package_path]):
        if not modname.startswith("m") or not modname[1:4].isdigit():
            continue
        mod = importlib.import_module(f"{_MIGRATIONS_PACKAGE}.{modname}")
        version = getattr(mod, "VERSION", None)
        description = getattr(mod, "DESCRIPTION", modname)
        if version is None or not callable(getattr(mod, "up", None)):
            continue
        found.append((int(version), str(description), mod))
    found.sort(key=lambda x: x[0])
    return found


def run_pending_migrations(db: sqlite3.Connection) -> list[int]:
    """Apply all pending migrations. Returns list of applied version numbers."""
    _ensure_version_table(db)
    current = _current_version(db)
    applied: list[int] = []
    for version, description, mod in _discover_migrations():
        if version <= current:
            continue
        mod.up(db)  # type: ignore[union-attr]
        db.execute(
            "INSERT INTO t_schema_version (sv_version, sv_description) VALUES (?, ?)",
            (version, description),
        )
        db.commit()
        applied.append(version)
    return applied
