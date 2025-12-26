from app import app, get_db

def inspect_zhang():
    print("--- Inspecting Zhang Feng ---")
    with app.app_context():
        db = get_db()
        # Try both Chinese and partial match
        rows = db.execute("SELECT * FROM middle_managers WHERE name LIKE '%张峰%'").fetchall()
        
        if not rows:
            print("No '张峰' found.")
        else:
            for r in rows:
                print(f"Name: {r['name']}")
                print(f"Role: '{r['role']}'")
                print(f"Dept Code: '{r['dept_code']}'")
                print(f"Dept Name: '{r['dept_name']}'")
                print(f"Sort No: {r['sort_no']}")
                print("-" * 20)

if __name__ == "__main__":
    inspect_zhang()
