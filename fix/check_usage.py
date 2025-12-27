import sqlite3

conn = sqlite3.connect('evaluation.db')
cursor = conn.cursor()

print("--- Check evaluation_accounts ---")
rows = cursor.execute("SELECT DISTINCT account_type FROM evaluation_accounts").fetchall()
print("Account Types:", rows)

print("\n--- Check scores (rater_type) ---")
rows = cursor.execute("SELECT DISTINCT rater_type FROM scores").fetchall()
print("Rater Types:", rows)

conn.close()
