from app import get_db, app

with app.app_context():
    db = get_db()
    cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print("Tables in database:")
    for t in tables:
        print(f" - {t}")
