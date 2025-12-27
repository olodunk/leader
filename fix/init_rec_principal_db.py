
import sqlite3

def init_db():
    db = sqlite3.connect('evaluation.db')
    cursor = db.cursor()
    
    table_sql = """
    CREATE TABLE IF NOT EXISTS recommendation_scores_principal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rater_account TEXT NOT NULL,
        target_dept_code TEXT,
        examinee_id INTEGER,
        examinee_name TEXT,
        is_recommended INTEGER DEFAULT 0,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(rater_account, examinee_id)
    );
    """
    
    try:
        cursor.execute(table_sql)
        db.commit()
        print("Table 'recommendation_scores_principal' created successfully.")
    except Exception as e:
        print(f"Error creating table: {e}")
    finally:
        db.close()

if __name__ == '__main__':
    init_db()
