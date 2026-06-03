import sqlite3
c = sqlite3.connect("db/actionhub.db")
rows = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print([r[0] for r in rows])
n = c.execute("SELECT COUNT(*) FROM t_user").fetchone()
print("t_user rows:", n)
c.close()
