import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "db" / "actionhub.db"

def replace_teamlead_with_member():
    db = sqlite3.connect(DB_PATH)
    db.execute("UPDATE t_user SET usr_role = 'Member' WHERE usr_role = 'TeamLead'")
    db.commit()
    count = db.execute("SELECT COUNT(*) FROM t_user WHERE usr_role = 'TeamLead'").fetchone()[0]
    db.close()
    print(f"All TeamLead roles replaced with Member. Remaining TeamLead count: {count}")

if __name__ == "__main__":
    replace_teamlead_with_member()
