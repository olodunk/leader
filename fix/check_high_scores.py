
import sqlite3
conn = sqlite3.connect('evaluation.db')
conn.row_factory = sqlite3.Row
db = conn

print("--- Check Scores > 100 ---")
rows = db.execute("SELECT * FROM team_scores WHERE total_score > 100").fetchall()
for r in rows:
    print(f"ID: {r['id']}, Rater: {r['rater_account']}, Score: {r['total_score']}")
    # Print detail to see why
    vals = [r[k] for k in r.keys() if k.startswith('s_')]
    print(f"  Values: {vals}")
    print(f"  Sum Vals: {sum(vals)}")
