
import sqlite3
conn = sqlite3.connect('evaluation.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("--- Dept Names for U, V, W, X, Y ---")
rows = cursor.execute("SELECT * FROM department_config WHERE dept_code IN ('U', 'V', 'W', 'X', 'Y')").fetchall()
for r in rows:
    print(f"{r['dept_code']}: {r['dept_name']}")
