
import sqlite3

def check_schema():
    db = sqlite3.connect('evaluation.db')
    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    
    # 1. Check department_config columns
    print("--- department_config ---")
    rows = cursor.execute("PRAGMA table_info(department_config)").fetchall()
    for r in rows:
        print(f"{r['name']} ({r['type']})")
        
    # 2. Check recommend_principal columns
    print("\n--- recommend_principal ---")
    rows = cursor.execute("PRAGMA table_info(recommend_principal)").fetchall()
    for r in rows:
        print(f"{r['name']} ({r['type']})")

if __name__ == '__main__':
    check_schema()
