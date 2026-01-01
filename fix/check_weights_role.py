import sqlite3

conn = sqlite3.connect('evaluation.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
print("Checking Weight Config (Role-based):")
rows = c.execute("SELECT * FROM weight_config_dept WHERE examinee_role LIKE '%分公司%' OR examinee_role LIKE '%昆冈%'").fetchall()
if not rows:
    print("No weight config found for Branch/Kungang roles.")
else:
    for r in rows:
        print(dict(r))
