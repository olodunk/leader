
import sqlite3

DB_PATH = 'evaluation.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Creating table 'submission_logs'...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS submission_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rater_account TEXT NOT NULL UNIQUE, -- One submission per account
            ip_address TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'submitted'
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialization for Project 9 complete.")

if __name__ == '__main__':
    init_db()
