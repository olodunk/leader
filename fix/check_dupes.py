
import sqlite3
conn = sqlite3.connect('evaluation.db')
conn.row_factory = sqlite3.Row
db = conn

print("--- team_scores for A0L001 ---")
rows = db.execute("SELECT * FROM team_scores WHERE rater_account='A0L001'").fetchall()
for r in rows:
    print(dict(r))

print("\n--- team_scores Count Duplicates ---")
rows = db.execute("""
    SELECT rater_account, target_dept_code, COUNT(*) 
    FROM team_scores 
    GROUP BY rater_account, target_dept_code 
    HAVING COUNT(*) > 1
""").fetchall()
if not rows:
    print("No duplicates found unique by rater+dept")
else:
    for r in rows:
        print(f"{r['rater_account']} - {r['target_dept_code']}: {r[2]}")
