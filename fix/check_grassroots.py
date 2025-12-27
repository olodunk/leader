from app import app, get_db

def check_grassroots():
    print("--- Checking Grassroots Personnel ---")
    with app.app_context():
        db = get_db()
        # Find anyone with '基层' in role
        rows = db.execute("SELECT * FROM middle_managers WHERE role LIKE '%基层%'").fetchall()
        
        if not rows:
            print("No users with '基层' found in middle_managers.")
        else:
            for r in rows:
                print(f"Name: {r['name']}, Role: '{r['role']}', Dept: '{r['dept_name']}'")

if __name__ == "__main__":
    check_grassroots()
