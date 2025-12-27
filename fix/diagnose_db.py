from app import app, get_user_rater_roles, get_db

def diagnose():
    print("--- Diagnostic: Center Principal Role Resolution (Code X/Y) ---")
    with app.app_context():
        db = get_db()
        
        # 1. Find potential users by Dept Code X or Y
        print("Checking users in Dept codes X, Y...")
        users = db.execute('''
            SELECT a.username, a.dept_code, d.dept_name, d.dept_type, a.account_type 
            FROM evaluation_accounts a
            LEFT JOIN department_config d ON a.dept_code = d.dept_code
            WHERE a.dept_code IN ('X', 'Y')
            LIMIT 10
        ''').fetchall()
        
        target_user_info = None
        
        for u in users:
            u_dict = dict(u)
            print(f"- User: {u['username']} | Type: {u['account_type']} | DeptCode: {u['dept_code']}")
            
            # Resolve Roles
            roles = get_user_rater_roles(u_dict, u_dict)
            print(f"  -> Roles: {roles}")
            
            if '中心领导班子 (正职)' in roles:
                print(f"  *** MATCH FOUND! This user is a Center Principal. ***")
                target_user_info = u_dict
                break
                
        if not target_user_info:
             print("\n[FAILURE] No user resolved to '中心领导班子 (正职)'. The fix might not be working or no 'Principal' account exists in X/Y.")
             return

        # 2. Check Permissions for '院长助理'
        print("\n--- Checking Permissions for this User ---")
        my_roles = get_user_rater_roles(target_user_info, target_user_info)
        target_role = '院长助理'
        
        placeholders = ','.join(['?'] * len(my_roles))
        allowed = db.execute(f'''
            SELECT count(*) FROM democratic_rating_config 
            WHERE rater_role IN ({placeholders}) AND examinee_role=? AND is_allowed=1
        ''', (*my_roles, target_role)).fetchone()[0]
        
        print(f"Access to '{target_role}': {'ALLOWED' if allowed else 'DENIED'}")

if __name__ == "__main__":
    diagnose()
