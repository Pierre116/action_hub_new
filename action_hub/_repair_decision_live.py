import os
from pathlib import Path

from actionhub import create_app
from actionhub.decisions.service import DecisionService
from actionhub.middleware.db import get_db


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    os.environ.setdefault("ACTIONHUB_ENV", "development")
    os.environ.setdefault("DATABASE", str(repo_root / "action_hub" / "db" / "actionhub.db"))

    app = create_app()
    with app.app_context():
        db = get_db()
        DecisionService._rebuild_fts_artifacts(db)
        db.commit()
        print(app.config["DATABASE"])


if __name__ == "__main__":
    main()