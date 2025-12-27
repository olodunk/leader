
import sqlite3

def init_db():
    db = sqlite3.connect('evaluation.db')
    cursor = db.cursor()
    
    # Project 6: Cadre Selection and Appointment Evaluation
    table_sql = """
    CREATE TABLE IF NOT EXISTS evaluation_selection_appointment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rater_account TEXT NOT NULL UNIQUE,
        dept_code TEXT,
        q1_overall TEXT,
        q2_supervision TEXT,
        q3_rectification TEXT,
        q4_problems TEXT,
        q5_suggestions_employment TEXT,
        q6_suggestions_report TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    try:
        cursor.execute(table_sql)
        db.commit()
        print("Table 'evaluation_selection_appointment' created successfully.")
    except Exception as e:
        print(f"Error creating table: {e}")
    finally:
        db.close()

if __name__ == '__main__':
    init_db()
