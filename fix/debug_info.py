import sqlite3
import pandas as pd

conn = sqlite3.connect('evaluation.db')
cursor = conn.cursor()

print("--- RP001 Info ---")
rp001 = cursor.execute("SELECT * FROM evaluation_accounts WHERE username='RP001'").fetchone()
print(rp001)

print("\n--- Account Types ---")
types = cursor.execute("SELECT DISTINCT account_type FROM evaluation_accounts").fetchall()
print(types)

print("\n--- Rater Roles in Config ---")
roles = cursor.execute("SELECT DISTINCT rater_role FROM democratic_rating_config").fetchall()
print(roles)

print("\n--- Sample Depts ---")
depts = cursor.execute("SELECT dept_code, dept_name FROM department_config LIMIT 5").fetchall()
print(depts)

conn.close()
