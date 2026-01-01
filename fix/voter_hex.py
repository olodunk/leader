
import sqlite3
conn = sqlite3.connect('evaluation.db')
conn.row_factory = sqlite3.Row
db = conn

dcode = 'D' # From previous check
voters = db.execute("""
    SELECT DISTINCT s.rater_account, a.account_type 
    FROM recommendation_scores_principal s 
    LEFT JOIN evaluation_accounts a ON s.rater_account = a.username 
    WHERE s.target_dept_code = ?
""", (dcode,)).fetchall()

for v in voters:
    atype = v['account_type']
    if atype:
        print(f"{v['rater_account']}: {atype.encode('utf-8').hex()} ({atype})")
    else:
        print(f"{v['rater_account']}: None")
