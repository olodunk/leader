import sqlite3

conn = sqlite3.connect('evaluation.db')
cursor = conn.cursor()

print("=== Account Types (evaluation_accounts) ===")
for row in cursor.execute('SELECT DISTINCT account_type FROM evaluation_accounts').fetchall():
    print(f"  '{row[0]}'")

print("\n=== Rater Roles (democratic_rating_config) ===")
for row in cursor.execute('SELECT DISTINCT rater_role FROM democratic_rating_config WHERE is_allowed=1').fetchall():
    print(f"  '{row[0]}'")

conn.close()
