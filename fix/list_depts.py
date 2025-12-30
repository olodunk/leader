import sqlite3

conn = sqlite3.connect('evaluation.db')
cursor = conn.cursor()

print("=== Department Config ===")
depts = cursor.execute('SELECT dept_code, dept_name FROM department_config ORDER BY sort_no ASC').fetchall()
for d in depts:
    print(f"  {d[0]}: {d[1]}")

conn.close()
