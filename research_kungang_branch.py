import sqlite3

conn = sqlite3.connect('evaluation.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("--- Dept Info ---")
depts = c.execute("SELECT dept_name, dept_code FROM department_config WHERE dept_name LIKE '%昆冈%'").fetchall()
for d in depts:
    print(f"Name: {d['dept_name']}, Code: {d['dept_code']}")

print("\n--- Weight Config (leader_weight_config) ---")
# Assuming codes V and W based on prior knowledge, but will confirm from above output.
# Also print columns to see what fields are available if needed, but selecting * is fine for research.
weights = c.execute("SELECT * FROM leader_weight_config WHERE dept_code IN ('U', 'V', 'W')").fetchall()
columns = [desc[0] for desc in c.description]
for w in weights:
    print(f"\nDept Code: {w['dept_code']}")
    for col in columns:
        if w[col] not in [None, 0]:
             print(f"  {col}: {w[col]}")

print("\n--- Target Personnel ---")
targets = c.execute("SELECT id, name, dept_name, role, dept_code FROM middle_managers WHERE dept_code IN ('V', 'W') AND role='中心正职'").fetchall()
for t in targets:
    print(dict(t))
