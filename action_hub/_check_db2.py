import sqlite3

paths = [
    r"c:\Users\leung\Documents\GitHub\actionhub\db\actionhub.db",
    r"c:\Users\leung\Documents\GitHub\actionhub\action_hub\db\actionhub.db",
]
for p in paths:
    c = sqlite3.connect(p)
    n = c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    try:
        u = c.execute("SELECT COUNT(*) FROM t_user").fetchone()[0]
    except Exception:
        u = "no t_user"
    print(p[-40:], "| tables:", n, "| users:", u)
    c.close()
