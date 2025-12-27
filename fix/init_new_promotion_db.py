
import sqlite3

def migrate_and_check():
    db = sqlite3.connect('evaluation.db')
    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    
    print("--- 1. Check for 'Center Grassroots Leader' ---")
    rows = cursor.execute("SELECT * FROM middle_managers WHERE role='中心基层领导'").fetchall()
    print(f"Found {len(rows)} candidates with role '中心基层领导'.")
    if len(rows) > 0:
        print(f"Sample: {dict(rows[0])}")
        
    print("\n--- 2. Add Missing Columns ---")
    try:
        # Check if exists first (robustness)
        info = cursor.execute("PRAGMA table_info(middle_managers)").fetchall()
        cols = [c['name'] for c in info]
        
        if 'original_position' not in cols:
            cursor.execute("ALTER TABLE middle_managers ADD COLUMN original_position TEXT")
            print("Added 'original_position'.")
            
        if 'promotion_method' not in cols:
            cursor.execute("ALTER TABLE middle_managers ADD COLUMN promotion_method TEXT")
            print("Added 'promotion_method'.")
            
        db.commit()
    except Exception as e:
        print(f"Migration Error: {e}")
        
    print("\n--- 3. Create Storage Table for Project 7 ---")
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluation_new_promotion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rater_account TEXT NOT NULL UNIQUE,
            dept_code TEXT,
            selections TEXT, -- JSON or String: {examinee_id: choice_key, ...}
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        db.commit()
        print("Table 'evaluation_new_promotion' created/verified.")
    except Exception as e:
         print(f"Storage Table Error: {e}")

if __name__ == '__main__':
    migrate_and_check()
