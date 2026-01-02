
import sys
import os
sys.path.append(os.getcwd())
from app import app, get_db, get_user_rater_roles # Assuming this function is importable or I'll copy it

def check():
    with app.app_context():
        db = get_db()
        
        # 1. Target Dept M
        target_dept_code = 'M' 
        ts_rows = db.execute("SELECT total_score, rater_account FROM team_scores WHERE target_dept_code=?", (target_dept_code,)).fetchall()
        if not ts_rows:
            print("No Team Scores for M")
            return
            
        print(f"Checking Dept: {target_dept_code}, Found {len(ts_rows)} team votes.")
        rater_account = ts_rows[0]['rater_account'] # Pick one for role check
        
        # 2. Find the Principal of this dept
        principal = db.execute('''
            SELECT * FROM middle_managers 
            WHERE dept_code = ? 
            AND role IN ('职能部门正职', '研究所正职', '两中心正职', '中心正职') 
            ORDER BY sort_no ASC LIMIT 1
        ''', (target_dept_code,)).fetchone()
        
        if not principal:
            print(f"No Principal found for dept {target_dept_code}")
            return
            
        print(f"Target Principal: {principal['name']} ({principal['role']})")
        
        # 3. Simulate Logic
        # Team Votes Map
        team_votes = db.execute("SELECT rater_account, total_score FROM team_scores WHERE target_dept_code=?", (target_dept_code,)).fetchall()
        print(f"Found {len(team_votes)} Team Votes for this dept.")
        
        # Democratic Votes
        demo_votes = db.execute("SELECT rater_account, score FROM democratic_score_details WHERE name=?", (principal['name'],)).fetchall()
        print(f"Found {len(demo_votes)} Democratic Votes for this person.")
        
        # 4. Check Rater Role Classification for a Team Voter
        # We need account info for the rater
        rater_full = db.execute("SELECT * FROM evaluation_accounts WHERE username=?", (rater_account,)).fetchone()
        if not rater_full:
            print("Rater account not found in evaluation_accounts!")
        else:
            print(f"Rater Info: {dict(rater_full)}")
            
        # Target Dept Info (for logic context)
        # Note: logic usually constructs 'examinee_dept_info' from middle_managers data + dept_config
        # But wait, app.py examinee_summary_calculate builds it differently?
        # Let's verify 'get_user_rater_roles' behavior.
        
        # Mock Examinee Info for Role Check
        examinee_info = {
            'dept_name': principal['dept_name'],
            'dept_code': principal['dept_code'],
            'dept_type': 'Unknown' # Need to fetch from dept_config
        }
        dept_conf = db.execute("SELECT dept_type FROM department_config WHERE dept_code=?", (target_dept_code,)).fetchone()
        if dept_conf:
            examinee_info['dept_type'] = dept_conf['dept_type']
            
        print(f"Examinee Context: {examinee_info}")
        
        # Check Role Result
        # We might need to import the function strictly or copy its logic if it's not exposed
        # It's likely defined in app.py. I'll attempt import.
        try:
            from app import get_user_rater_roles
            role_res = get_user_rater_roles(dict(rater_full), examinee_info)
            print(f"Calculated Role for {rater_account} vs {principal['name']}: {role_res}")
        except ImportError:
            print("Could not import get_user_rater_roles. Check app.py structure.")

if __name__ == '__main__':
    check()
