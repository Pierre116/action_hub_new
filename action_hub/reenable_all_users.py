import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "db" / "actionhub.db"

def reenable_all_users():
    db = sqlite3.connect(DB_PATH)
    db.execute("UPDATE t_user SET usr_active = 1")
    db.commit()
    count = db.execute("SELECT COUNT(*) FROM t_user WHERE usr_active = 1").fetchone()[0]
    db.close()
    print(f"Re-enabled {count} user accounts.")

if __name__ == "__main__":
    reenable_all_users()
