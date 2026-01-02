
import sys
import os
sys.path.append(os.getcwd())
from app import app, get_db

def verify():
    print("Starting Team Score Summary Verification...")
    
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['admin_role'] = 'admin'
            sess['username'] = 'admin'
        
        # 1. Calculate Examinee Summary
        print("POST /api/examinee-summary/calculate...")
        resp = client.post('/api/examinee-summary/calculate')
        print(f"Status: {resp.status_code}")
        
        # 2. Calculate Team Score Summary
        print("POST /api/team-score-summary/calculate...")
        resp = client.post('/api/team-score-summary/calculate')
        print(f"Status: {resp.status_code}, Result: {resp.get_json()}")
        
        if resp.status_code != 200:
            print("FAILED: Calculation Error")
            return
        
        # 3. Compare Scores for a Functional Dept
        with app.app_context():
            db = get_db()
            
            # Find a Functional Dept (e.g., I = 数智技术中心)
            for test_dept_type in ['职能部门', '研究所', '两中心', '昆冈分公司']:
                if test_dept_type == '两中心':
                    ts_row = db.execute('''
                        SELECT ts.*, dc.dept_type 
                        FROM team_score_summary ts
                        JOIN department_config dc ON ts.dept_code = dc.dept_code
                        WHERE ts.dept_name IN ('大庆化工研究中心', '兰州化工研究中心') LIMIT 1
                    ''').fetchone()
                elif test_dept_type == '昆冈分公司':
                    ts_row = db.execute('''
                        SELECT ts.*, dc.dept_type 
                        FROM team_score_summary ts
                        JOIN department_config dc ON ts.dept_code = dc.dept_code
                        WHERE ts.dept_name IN ('昆冈兰州分公司', '昆冈抚顺分公司') LIMIT 1
                    ''').fetchone()
                else:
                    ts_row = db.execute('''
                        SELECT ts.*, dc.dept_type 
                        FROM team_score_summary ts
                        JOIN department_config dc ON ts.dept_code = dc.dept_code
                        WHERE dc.dept_type = ? LIMIT 1
                    ''', (test_dept_type,)).fetchone()
                
                if not ts_row:
                    print(f"No {test_dept_type} found in team_score_summary")
                    continue
                
                dept_code = ts_row['dept_code']
                if test_dept_type == '职能部门':
                    ts_abc = ts_row['score_func_abc_weighted']
                elif test_dept_type == '研究所':
                    ts_abc = ts_row['score_inst_abc_weighted']
                elif test_dept_type == '两中心':
                    ts_abc = ts_row['score_center_kungang']
                else:  # 昆冈分公司
                    ts_abc = ts_row['score_branch_weighted']
                ts_total = ts_row['total_score']
                
                # Find corresponding Principal in Examinee Summary
                es_row = db.execute('''
                    SELECT e.score_func_abc_weighted, e.score_inst_abc_weighted, e.score_center_kungang, e.score_branch_weighted, e.total_score
                    FROM examinee_score_summary e
                    JOIN middle_managers m ON e.examinee_id = m.id
                    WHERE m.dept_code = ? AND m.sort_no = 1
                ''', (dept_code,)).fetchone()
                
                if not es_row:
                    print(f"No Examinee found for dept {dept_code}")
                    continue
                
                if test_dept_type == '职能部门':
                    es_abc = es_row['score_func_abc_weighted']
                elif test_dept_type == '研究所':
                    es_abc = es_row['score_inst_abc_weighted']
                elif test_dept_type == '两中心':
                    es_abc = es_row['score_center_kungang']
                else:  # 昆冈分公司
                    es_abc = es_row['score_branch_weighted']
                es_total = es_row['total_score']
                
                print(f"\n--- Comparison for Dept {dept_code} ({test_dept_type}) ---")
                print(f"Team Summary:    Score={ts_abc:.4f}, Total={ts_total:.4f}")
                print(f"Examinee (正职): Score={es_abc:.4f}, Total={es_total:.4f}")
                
                if abs(ts_abc - es_abc) > 0.01:
                    print(f"SUCCESS: Weighted scores are DIFFERENT ({test_dept_type} Fusion worked)")
                else:
                    print(f"WARNING: Weighted scores are SAME ({test_dept_type} Fusion may not be effective)")

if __name__ == '__main__':
    verify()
