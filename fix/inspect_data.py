from app import app, get_user_rater_roles, get_db

def inspect_data():
    print("--- Inspecting User Data ---")
    with app.app_context():
        db = get_db()
        
        # 1. Check Department Config Types
        print("\n[Department Types]")
        rows = db.execute("SELECT * FROM department_config").fetchall()
        for r in rows:
            print(f"Code: {r['dept_code']}, Name: {r['dept_name']}, Type: '{r['dept_type']}'")
            
        # 2. Check Accounts and Resolve Roles
        print("\n[Accounts & Roles (First 20)]")
        # Join to get everything
        users = db.execute('''
            SELECT a.username, a.dept_code, a.account_type, d.dept_name, d.dept_type
            FROM evaluation_accounts a
            LEFT JOIN department_config d ON a.dept_code = d.dept_code
            LIMIT 20
        ''').fetchall()
        
        for u in users:
            u_dict = dict(u)
            # Reconstruct d_code/name/type because get_user_rater_roles expects them in the dict or specific structure?
            # get_user_rater_roles(user_account, user_dept_info)
            # user_account needs 'account_type'
            # user_dept_info needs 'dept_name', 'dept_type', 'dept_code'
            
            roles = get_user_rater_roles(u_dict, u_dict)
            print(f"User: {u['username']} | Type: {u['account_type']} | Dept: {u['dept_name']} ({u['dept_type']}) -> Roles: {roles}")

            if '中心领导班子 (正职)' in roles:
                print("   *** FOUND CENTER PRINCIPAL ***")

if __name__ == "__main__":
    inspect_data()
