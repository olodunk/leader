
import sqlite3
conn = sqlite3.connect('evaluation.db')
conn.row_factory = sqlite3.Row
db = conn

print("--- Team Scores Samples ---")
rows = db.execute("SELECT * FROM team_scores LIMIT 10").fetchall()
for r in rows:
    print(dict(r))

print("\n--- Team Score Details Samples ---")
rows = db.execute("SELECT * FROM team_score_details LIMIT 10").fetchall()
for r in rows:
    print(dict(r))
