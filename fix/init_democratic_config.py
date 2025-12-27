import sqlite3
from app import app, DATABASE, COL_HEADERS, ROW_HEADERS, DEFAULT_DEMOCRATIC_CONFIG

def init_democratic_config():
    with app.app_context():
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Ensure table exists (in case init_db wasn't run yet)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS democratic_rating_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                examinee_role TEXT NOT NULL,
                rater_role TEXT NOT NULL,
                is_allowed INTEGER DEFAULT 0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(examinee_role, rater_role)
            )
        ''')
        
        # Always reset since user requested independent config
        print(f"Resetting democratic_rating_config...")
        cursor.execute('DELETE FROM democratic_rating_config')
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='democratic_rating_config'")
        conn.commit()

        print("Initializing from DEFAULT_DEMOCRATIC_CONFIG (Independent)...")
        
        data = []
        for examinee, raters in DEFAULT_DEMOCRATIC_CONFIG.items():
            for rater in raters:
                # is_allowed = 1 for explicitly listed pairs
                data.append((examinee, rater, 1))
                
        # Also need to ensure ROW_HEADERS x COL_HEADERS coverage? 
        # The previous logic covered ALL pairs with 0 or 1.
        # If we only insert 1s, the query `SELECT * FROM ... WHERE is_allowed = 1` works fine.
        # But if the UI expects a full matrix for rendering checkboxes (if used), we might need 0s.
        # Assuming current UI/Logic only queries for allowed.
        # Wait, get_democratic_nav checks `is_allowed=1`. Correct.
        
        cursor.executemany('INSERT INTO democratic_rating_config (examinee_role, rater_role, is_allowed) VALUES (?, ?, ?)', data)
        conn.commit()
        print(f"Inserted {len(data)} rows into democratic_rating_config.")
        conn.close()

if __name__ == "__main__":
    init_democratic_config()
