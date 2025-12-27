
import sqlite3
import pandas as pd
import os
import json

# Setup
DB_PATH = 'evaluation.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def verify():
    db = get_db()
    print("--- 1. Verify Table ---")
    try:
        db.execute('SELECT * FROM evaluation_new_promotion LIMIT 1')
        print("Table 'evaluation_new_promotion' exists.")
    except Exception as e:
        print(f"FAILED: Table check: {e}")
        return

    print("\n--- 2. Verify Permissions Logic (Simulation) ---")
    # Mock Logic from app.py
    def check_access(dept_code):
        allowed_depts_p7 = ['X', 'Y']
        return dept_code in allowed_depts_p7

    print(f"Dept X Access: {check_access('X')} (Expected True)")
    print(f"Dept Y Access: {check_access('Y')} (Expected True)")
    print(f"Dept A Access: {check_access('A')} (Expected False)")
    
    print("\n--- 3. Verify Candidate Data ---")
    # Clean up X candidates first
    candidates = db.execute("SELECT * FROM middle_managers WHERE role='中心基层领导' AND dept_code='X'").fetchall()
    print(f"Dept X has {len(candidates)} candidates.")
    if len(candidates) > 0:
        c = candidates[0]
        print(f"Sample: {c['name']}, Original: {c['original_position']}, Promo: {c['promotion_method']}")
        
    print("\n--- 4. Verify Submission (Write to DB) ---")
    rater = 'user_x_test'
    dept = 'X'
    
    # Clean old
    db.execute("DELETE FROM evaluation_new_promotion WHERE rater_account=?", (rater,))
    db.commit()
    
    # Write
    selections = {"1": "agree", "2": "disagree"}
    json_str = json.dumps(selections)
    
    db.execute("INSERT INTO evaluation_new_promotion (rater_account, dept_code, selections) VALUES (?, ?, ?)",
               (rater, dept, json_str))
    db.commit()
    print("Inserted mock data.")
    
    # Read back
    row = db.execute("SELECT * FROM evaluation_new_promotion WHERE rater_account=?", (rater,)).fetchone()
    if row:
        print(f"Read back selections: {row['selections']}")
        assert 'agree' in row['selections']
    else:
        print("FAILED: Could not read back data.")
        
    print("\nVerification Complete.")

if __name__ == '__main__':
    verify()
