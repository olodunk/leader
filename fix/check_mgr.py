import sqlite3

conn = sqlite3.connect('evaluation.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
print("Checking Kungang Managers:")
rows = c.execute("SELECT id, name, dept_name, role, dept_code FROM middle_managers WHERE dept_code='U' OR dept_name LIKE '%昆冈%'").fetchall()
for r in rows:
    print(dict(r))
print(f"Total found: {len(rows)}")
