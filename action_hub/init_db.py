from pathlib import Path

from actionhub import create_app
from actionhub.middleware.db import init_db


def main() -> None:
    app = create_app()
    db_path = Path(app.config["DATABASE"])
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with app.app_context():
        init_db()
    print(f"Database initialized at {db_path}")


if __name__ == "__main__":
    main()
