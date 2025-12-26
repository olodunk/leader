import sqlite3
from app import app, DATABASE, COL_HEADERS, ROW_HEADERS

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
        
        # Check if already populated
        cnt = cursor.execute('SELECT count(*) FROM democratic_rating_config').fetchone()[0]
        if cnt > 0:
            print(f"Table democratic_rating_config already has {cnt} rows. Resetting...")
            cursor.execute('DELETE FROM democratic_rating_config')
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='democratic_rating_config'")
            conn.commit()

        print("Initializing from weight_config_dept...")
        
        # Logic: Read weight matrix. If weight > 0 -> is_allowed=1. Else 0.
        # We also need to cover ALL cells in the matrix (Col * Row) to ensure the UI renders correctly.
        # So we iterate COL_HEADERS and ROW_HEADERS, query weight, and insert.
        
        # Get Weights Map
        weights_rows = cursor.execute('SELECT examinee_role, rater_role, weight FROM weight_config_dept').fetchall()
        weight_map = {}
        for r in weights_rows:
            weight_map[(r[0], r[1])] = r[2]
            
        data = []
        for col in COL_HEADERS:
            for row in ROW_HEADERS:
                w = weight_map.get((col, row), 0)
                is_allowed = 1 if w > 0 else 0
                data.append((col, row, is_allowed))
        
        cursor.executemany('INSERT INTO democratic_rating_config (examinee_role, rater_role, is_allowed) VALUES (?, ?, ?)', data)
        conn.commit()
        print(f"Inserted {len(data)} rows into democratic_rating_config.")
        conn.close()

if __name__ == "__main__":
    init_democratic_config()
