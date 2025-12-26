import sqlite3
import os

DATABASE = 'evaluation.db'

def update_db():
    if not os.path.exists(DATABASE):
        print(f"Database {DATABASE} not found.")
        return

    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Check current data
        cursor.execute("SELECT count(*) FROM weight_config_dept WHERE rater_role = '本部门其他员工'")
        count = cursor.fetchone()[0]
        print(f"Found {count} rows with old name '本部门其他员工'...")

        if count > 0:
            cursor.execute("UPDATE weight_config_dept SET rater_role = '职能部门其他员工' WHERE rater_role = '本部门其他员工'")
            conn.commit()
            print(f"Updated {cursor.rowcount} rows to '职能部门其他员工'.")
        else:
            print("No rows needed updating.")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_db()
