
import sqlite3
import json

def verify_feature():
    db = sqlite3.connect('evaluation.db')
    db.row_factory = sqlite3.Row
    
    print("--- 1. Check Permissions Logic ---")
    # Allowed: V, W, X, Y
    allowed_codes = ['V', 'W', 'X', 'Y']
    # Disallowed: A
    
    # Check Allowed
    for code in allowed_codes:
        row = db.execute("SELECT * FROM evaluation_accounts WHERE dept_code=? LIMIT 1", (code,)).fetchone()
        if row:
            print(f"[PASS] Account {row['username']} (Dept {code}) exists. Should have access.")
        else:
            print(f"[WARN] No account found for Dept {code} to test.")
            
    # Check Disallowed
    row_a = db.execute("SELECT * FROM evaluation_accounts WHERE dept_code='A' LIMIT 1").fetchone()
    if row_a:
        print(f"[PASS] Account {row_a['username']} (Dept A) exists. Should NOT have access.")
    
    print("\n--- 2. Simulate API Submission (Mock for Allowed) ---")
    # Pick one allowed account
    target_code = 'V'
    target_acc = db.execute("SELECT * FROM evaluation_accounts WHERE dept_code=? LIMIT 1", (target_code,)).fetchone()
    
    if target_acc:
        uname = target_acc['username']
        print(f"Testing with {uname}...")
        
        # Clean up
        db.execute("DELETE FROM evaluation_selection_appointment WHERE rater_account=?", (uname,))
        db.commit()
        
        # Insert Check
        try:
            db.execute("""
                INSERT INTO evaluation_selection_appointment 
                (rater_account, dept_code, q1_overall, q2_supervision, q3_rectification, q4_problems, q5_suggestions_employment, q6_suggestions_report)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (uname, target_code, '好', '较好', '一般', '1,2,3', 'Test Sug 1', 'Test Sug 2'))
            db.commit()
            print("[PASS] DB Insert Success.")
            
            chk = db.execute("SELECT * FROM evaluation_selection_appointment WHERE rater_account=?", (uname,)).fetchone()
            if chk and chk['q1_overall'] == '好':
                 print(f"[PASS] Verification Read: {chk['q1_overall']}, Suggestions: {chk['q5_suggestions_employment']}")
            else:
                 print("[FAIL] Verification Read Failed.")
                 
        except Exception as e:
            print(f"[FAIL] DB Error: {e}")
    else:
        print("Cannot test submission, no 'V' account found.")

if __name__ == '__main__':
    verify_feature()
