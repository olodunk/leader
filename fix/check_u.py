
import sqlite3
conn = sqlite3.connect('evaluation.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

name = '项伟'
print(f"Searching for {name}...")
row = cursor.execute("SELECT * FROM recommend_deputy WHERE name=?", (name,)).fetchone()

if row:
    print("Found:")
    for k in row.keys():
        print(f"{k}: {row[k]}")
else:
    print("Not found")

print("\n--- Checking U departments ---")
rows = cursor.execute("SELECT * FROM department_config WHERE dept_code LIKE 'U%'").fetchall()
for r in rows:
    print(f"{r['dept_code']} - {r['dept_name']}")
