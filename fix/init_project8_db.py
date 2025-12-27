
import sqlite3

DB_PATH = 'evaluation.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Creating table 'center_grassroots_leaders'...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS center_grassroots_leaders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            serial_no INTEGER,
            sort_no INTEGER,
            name TEXT NOT NULL,
            gender TEXT,
            position TEXT NOT NULL,
            dept_name TEXT NOT NULL,
            dept_id INTEGER,
            rank_level TEXT,
            birth_date TEXT,
            education TEXT,
            rank_time TEXT,
            role TEXT,
            dept_code TEXT,
            tenure_time TEXT,
            
            -- Extra Columns for Project 8
            original_position TEXT,
            promotion_method TEXT,
            is_newly_promoted TEXT,
            
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialization for Project 8 complete.")

if __name__ == '__main__':
    init_db()
