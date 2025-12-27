
import sqlite3

def check_k_permissions():
    db = sqlite3.connect('evaluation.db')
    db.row_factory = sqlite3.Row
    
    print("--- 1. Departments with Quota >= 1 ---")
    rows = db.execute("SELECT dept_code, dept_name, count_recommend_principal FROM department_config WHERE count_recommend_principal >= 1").fetchall()
    for r in rows:
        print(f"[{r['dept_code']}] {r['dept_name']}: {r['count_recommend_principal']}")
        
    print("\n--- 2. 'K' Department Configs (Kungang?) ---")
    # Assuming 'K' means dept_code starts with K or name contains 昆冈
    rows = db.execute("SELECT dept_code, dept_name, count_recommend_principal FROM department_config WHERE dept_code LIKE 'K%' OR dept_name LIKE '%昆冈%'").fetchall()
    for r in rows:
        print(f"[{r['dept_code']}] {r['dept_name']}: {r['count_recommend_principal']}")
        
    print("\n--- 3. Account Check for User's Issue ---")
    # Check what accounts exist for these departments
    if rows:
        dept_codes = [r['dept_code'] for r in rows]
        ph = ','.join(['?'] * len(dept_codes))
        accs = db.execute(f"SELECT username, dept_code FROM evaluation_accounts WHERE dept_code IN ({ph}) LIMIT 5", dept_codes).fetchall()
        for a in accs:
            print(f"Account: {a['username']} (Dept: {a['dept_code']})")

if __name__ == '__main__':
    check_k_permissions()
