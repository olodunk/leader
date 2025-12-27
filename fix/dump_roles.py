from app import app, get_db

def dump_roles():
    print("--- Distinct Roles in Middle Managers ---")
    with app.app_context():
        db = get_db()
        rows = db.execute("SELECT DISTINCT role FROM middle_managers").fetchall()
        for r in rows:
            print(f"Role: '{r[0]}'")

if __name__ == "__main__":
    dump_roles()
