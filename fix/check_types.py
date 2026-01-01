
import sqlite3
conn = sqlite3.connect('evaluation.db')
conn.row_factory = sqlite3.Row
db = conn

print("--- Accounts starting with DE ---")
rows = db.execute("SELECT username, account_type FROM evaluation_accounts WHERE username LIKE 'DE%' LIMIT 10").fetchall()
for r in rows:
    print(f"{r['username']}: {r['account_type']}")

print("\n--- Summary of account types ---")
rows = db.execute("SELECT account_type, COUNT(*) FROM evaluation_accounts GROUP BY account_type").fetchall()
for r in rows:
    print(f"{r[0]}: {r[1]}")
