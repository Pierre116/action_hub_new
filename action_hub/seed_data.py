from pathlib import Path

from actionhub import create_app
from actionhub.auth.service import create_user
from actionhub.middleware.db import get_db


def seed_reference_data() -> None:
    db = get_db()
    seed_path = Path(__file__).resolve().parent / "db" / "seed.sql"
    with open(seed_path, "r", encoding="utf-8") as file_handle:
        sql = file_handle.read()
    db.executescript(sql)
    db.commit()


def seed_admin() -> None:
    create_user(
        username="admin",
        employee_id="000001",
        password="Admin@2026",
        display_name="Administrator",
        email="admin@actionhub.local",
        role="Admin",
        must_change_pwd=0,
    )
    # Add a non-admin user for tests
    create_user(
        username="user1",
        employee_id="000002",
        password="User@2026",
        display_name="Test User",
        email="user1@actionhub.local",
        role="Member",
        must_change_pwd=0,
    )


def main() -> None:
    app = create_app()
    with app.app_context():
        seed_reference_data()
        seed_admin()
    print("Seed data loaded (departments, business themes, admin)")


if __name__ == "__main__":
    main()
