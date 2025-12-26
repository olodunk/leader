import sqlite3
from app import app, DEFAULT_DEPT_WEIGHTS, COL_HEADERS, ROW_HEADERS, DATABASE, init_dept_weights

def reset_weights():
    with app.app_context():
        # Connect strictly to DB file to avoid app context issues if any
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        print("Clearing existing weight configuration...")
        cursor.execute("DELETE FROM weight_config_dept")
        # Reset ID sequence
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='weight_config_dept'")
        conn.commit()
        
        print("Re-initializing from DEFAULT_DEPT_WEIGHTS...")
        # We can reuse the logic from init_dept_weights, but let's do it explicitly here to be safe
        data = []
        for col in COL_HEADERS:
            weights = DEFAULT_DEPT_WEIGHTS.get(col, {})
            for row in ROW_HEADERS:
                val = weights.get(row, 0)
                data.append((col, row, val))
        
        cursor.executemany('INSERT INTO weight_config_dept (examinee_role, rater_role, weight) VALUES (?, ?, ?)', data)
        conn.commit()
        print(f"Inserted {len(data)} rows.")
        conn.close()

if __name__ == "__main__":
    reset_weights()
