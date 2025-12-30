import sqlite3

def migrate():
    db = sqlite3.connect('evaluation.db')
    cursor = db.cursor()
    
    print("Starting migration for democratic_scores...")
    # Update democratic_scores
    cursor.execute('''
        UPDATE democratic_scores
        SET examinee_name = (
            SELECT name FROM middle_managers 
            WHERE middle_managers.id = democratic_scores.examinee_id
        )
        WHERE examinee_name IS NULL
    ''')
    print(f"Updated {db.total_changes} records in democratic_scores.")
    
    print("Starting migration for personnel_scores...")
    # Update personnel_scores (examinee_name might be missing in some older records)
    cursor.execute('''
        UPDATE personnel_scores
        SET examinee_name = (
            SELECT name FROM middle_managers 
            WHERE middle_managers.id = personnel_scores.examinee_id
        )
        WHERE examinee_name IS NULL
    ''')
    print(f"Updated {db.total_changes} records in personnel_scores.")
    
    db.commit()
    db.close()
    print("Migration completed.")

if __name__ == '__main__':
    migrate()
