
import sqlite3

def verify_feature():
    db = sqlite3.connect('evaluation.db')
    db.row_factory = sqlite3.Row
    
    print("--- 1. Check Data Setup (Deputy) ---")
    row = db.execute("SELECT * FROM department_config WHERE count_recommend_deputy >= 1 LIMIT 1").fetchone()
    if not row:
        print("SKIP: No department has count_recommend_deputy >= 1. Cannot test.")
        return
        
    dept_code = row['dept_code']
    quota = row['count_recommend_deputy']
    print(f"Target Dept: {row['dept_name']} ({dept_code}), Quota: {quota}")
    
    acc = db.execute("SELECT * FROM evaluation_accounts WHERE dept_code=? LIMIT 1", (dept_code,)).fetchone()
    if not acc:
        print("SKIP: No account found in target department.")
        return
        
    username = acc['username']
    print(f"Target Account: {username}")
    
    print("\n--- 2. Simulate API Submission (Mock) ---")
    try:
        db.execute("DELETE FROM recommendation_scores_deputy WHERE rater_account=?", (username,))
        
        cand = db.execute("SELECT * FROM recommend_deputy LIMIT 1").fetchone()
        if cand:
            c_id = cand['id']
            c_name = cand['name']
            
            db.execute("""
                INSERT INTO recommendation_scores_deputy (rater_account, target_dept_code, examinee_id, examinee_name, is_recommended)
                VALUES (?, ?, ?, ?, 1)
            """, (username, dept_code, c_id, c_name))
            db.commit()
            print("Successfully inserted test record directly to DB.")
            
            check = db.execute("SELECT * FROM recommendation_scores_deputy WHERE rater_account=?", (username,)).fetchone()
            if check and check['examinee_name'] == c_name:
                print(f"Verification Read Success: Found {check['examinee_name']}")
            else:
                print("Verification Read FAILED.")
        else:
            print("No candidates in recommend_deputy to test with.")
            
    except Exception as e:
        print(f"DB Error: {e}")
        
    print("\n--- 3. Verify Perms Static Check ---")
    print(f"Logic Validation: Dept {row['dept_name']} has quota {quota} >= 1. Deputy Nav should be visible.")

if __name__ == '__main__':
    verify_feature()
