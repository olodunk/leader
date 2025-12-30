import sqlite3

conn = sqlite3.connect('evaluation.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
print("Checking Weight Config for V/W:")
rows = c.execute("SELECT * FROM weight_config_dept WHERE dept_code IN ('V', 'W')").fetchall()
if not rows:
    print("No weight config found for V/W.")
else:
    for r in rows:
        print(dict(r))
