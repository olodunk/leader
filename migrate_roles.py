import sqlite3
import os

DATABASE = 'evaluation.db'

def migrate_roles():
    if not os.path.exists(DATABASE):
        print(f"Database {DATABASE} not found!")
        return

    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Update '机关正职' -> '职能部门正职'
        print("Migrating '机关正职' -> '职能部门正职'...")
        cursor.execute("UPDATE middle_managers SET role = '职能部门正职' WHERE role = '机关正职'")
        print(f"Updated {cursor.rowcount} rows.")
        
        # Update '机关副职' -> '职能部门副职'
        print("Migrating '机关副职' -> '职能部门副职'...")
        cursor.execute("UPDATE middle_managers SET role = '职能部门副职' WHERE role = '机关副职'")
        print(f"Updated {cursor.rowcount} rows.")
        
        conn.commit()
        conn.close()
        print("Migration complete!")
        
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate_roles()
