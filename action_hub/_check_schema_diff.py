import sqlite3
src = sqlite3.connect(r'C:\Users\leung\Documents\GitHub\actionhub\db\actionhub.db')
dst = sqlite3.connect(r'C:\Users\leung\Documents\GitHub\actionhub\action_hub\db\actionhub.db')
src_tables = [r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
for table in src_tables:
    sc = [r[1] for r in src.execute(f"PRAGMA table_info({table})").fetchall()]
    try:
        dc = [r[1] for r in dst.execute(f"PRAGMA table_info({table})").fetchall()]
    except Exception:
        dc = []
    diff = set(sc) - set(dc)
    if diff:
        print(table, "extra cols in source:", diff)
src.close()
dst.close()
