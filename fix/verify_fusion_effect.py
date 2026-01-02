
import sys
import os
sys.path.append(os.getcwd())
import json
from app import app, get_db

def verify():
    print("Starting Fusion Effect Test...")
    
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['admin_role'] = 'admin'
            sess['username'] = 'admin'
            
        # 1. Calculate Initial State (with whatever team scores exist)
        print("Calculating Initial State...")
        resp = client.post('/api/examinee-summary/calculate')
        if resp.status_code != 200:
             print("Initial Calc Failed")
             return
             
        # Pick a target dept principal to monitor (e.g. M1 or M)
        with app.app_context():
            db = get_db()
            # Find a dept principal with existing team score
            # Table examinee_score_summary doesn't have dept_code (it has dept_name).
            # We can join middle_managers (mm) on name/dept_name or assume dept_name is unique enough
            # But Team Scores uses dept_code.
            row = db.execute('''
                SELECT t.target_dept_code, t.total_score, e.score_func_abc_weighted, e.total_score as final_score
                FROM team_scores t
                JOIN department_config dc ON t.target_dept_code = dc.dept_code
                JOIN examinee_score_summary e ON e.dept_name = dc.dept_name
                WHERE e.score_func_abc_weighted > 0 OR e.score_inst_abc_weighted > 0
                LIMIT 1
            ''').fetchone()
            
            if not row:
                print("No suitable data found to verify (need dept with both Team Score and ABC Score).")
                # Fallback: check ANY dept
                return

            target_dept = row['target_dept_code']
            initial_score = row['final_score']
            print(f"Target Dept: {target_dept}, Initial Final Score: {initial_score}")
            
            # 2. Modify Team Score drastically in team_score_details
            print("Modifying Team Score Details to 100.0 (Extreme Value)...")
            # We assume team_score_details has rows for this dept.
            # If not, we should insert some mock rows to simulate the fusion.
            
            # Check if rows exist
            cnt = db.execute("SELECT COUNT(*) FROM team_score_details WHERE dept_code = ?", (target_dept,)).fetchone()[0]
            if cnt == 0:
                 print("No team_score_details found. Converting team_scores to details for test...")
                 # Mock conversion (simplified)
                 db.execute("INSERT INTO team_score_details (dept_code, rater_account, score) SELECT target_dept_code, rater_account, total_score FROM team_scores WHERE target_dept_code=?", (target_dept,))
            
            db.execute("UPDATE team_score_details SET score = 100.0 WHERE dept_code = ?", (target_dept,))
            db.commit()
            
        # 3. Recalculate
        print("Recalculating...")
        client.post('/api/examinee-summary/calculate')
        
        # 4. Check Difference
        with app.app_context():
            db = get_db()
            new_row = db.execute('''
                SELECT e.total_score 
                FROM examinee_score_summary e
                JOIN department_config dc ON e.dept_name = dc.dept_name
                WHERE dc.dept_code = ?
            ''', (target_dept,)).fetchone()
            new_score = new_row['total_score']
            print(f"New Final Score: {new_score}")
            
            if abs(new_score - initial_score) > 0.01:
                print("SUCCESS: Team Score change affected the Final Score!")
            else:
                print("FAILURE: Final Score did not change despite Team Score update.")

if __name__ == '__main__':
    verify()
