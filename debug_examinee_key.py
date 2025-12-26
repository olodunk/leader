from app import app, get_db, get_examinee_role_key

def sim_check():
    print("--- Simulating get_examinee_role_key ---")
    with app.app_context():
        db = get_db()
        # Fetch Zhang Feng
        row = db.execute("SELECT * FROM middle_managers WHERE name LIKE '%张峰%'").fetchone()
        if not row:
            print("Zhang Feng not found.")
            return
            
        role = row['role']
        dept_name = row['dept_name']
        print(f"User: {row['name']}")
        print(f"Role (Raw): {repr(role)}")
        print(f"Dept Name: {dept_name}")
        
        # Test 1: Direct '基层' check
        if '基层' in role:
            print("MATCH: '基层' is in role.")
        else:
            print("NO MATCH: '基层' NOT in role.")
            
        # Test 2: Call Function
        res = get_examinee_role_key(role, dept_name)
        print(f"Result from get_examinee_role_key: {res}")

if __name__ == "__main__":
    sim_check()
