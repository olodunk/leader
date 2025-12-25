import sqlite3
import pandas as pd

conn = sqlite3.connect('evaluation.db')
cursor = conn.cursor()

print("Checking 'weight_config_dept' for old role names...")
rows = cursor.execute("SELECT * FROM weight_config_dept WHERE examinee_role IN ('机关正职', '机关副职') OR rater_role IN ('机关正职', '机关副职')").fetchall()
if rows:
    print(f"Found {len(rows)} rows with old names.")
    for r in rows:
        print(r)
else:
    print("No old names found in weight_config_dept.")

conn.close()
