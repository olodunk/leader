
import sqlite3
conn = sqlite3.connect('evaluation.db')
conn.row_factory = sqlite3.Row
db = conn

dept_name = '人力资源部/党委组织部'
row = db.execute("SELECT dept_code FROM department_config WHERE dept_name = ?", (dept_name,)).fetchone()
if not row:
    print(f"Dept {dept_name} not found")
    exit()

dcode = row['dept_code']
print(f"Dept Code: {dcode}")

voters = db.execute("""
    SELECT DISTINCT s.rater_account, a.account_type 
    FROM recommendation_scores_principal s 
    LEFT JOIN evaluation_accounts a ON s.rater_account = a.username 
    WHERE s.target_dept_code = ?
""", (dcode,)).fetchall()

for v in voters:
    print(f"{v['rater_account']}: {v['account_type']}")
