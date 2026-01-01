import sqlite3

conn = sqlite3.connect('evaluation.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
print("Checking Scores:")
rows = c.execute("SELECT name, score_branch_principal, total_score FROM examinee_score_summary WHERE dept_name LIKE '%昆冈%'").fetchall()
for r in rows:
    print(dict(r))
