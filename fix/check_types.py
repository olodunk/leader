
import sqlite3

def check_types():
    db = sqlite3.connect('evaluation.db')
    db.row_factory = sqlite3.Row
    
    print("--- Checking Column Types for Dept K ---")
    row = db.execute("SELECT dept_code, typeof(count_recommend_principal) as type, count_recommend_principal FROM department_config WHERE dept_code='K'").fetchone()
    if row:
        print(f"Dept K: Val={row['count_recommend_principal']}, Type={row['type']}")
    else:
        print("Dept K not found")

if __name__ == '__main__':
    check_types()
