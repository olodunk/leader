
import sqlite3

def check_dept():
    db = sqlite3.connect('evaluation.db')
    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    
    # Check Department Config for Beijing KunGang
    rows = cursor.execute("SELECT * FROM department_config WHERE dept_name LIKE '%昆冈%'").fetchall()
    print(f"Found {len(rows)} KunGang departments:")
    for row in rows:
        print(f"Name: {row['dept_name']}, Code: {row['dept_code']}, Type: {row['dept_type']}")

    # Check existing UP accounts to see if they exist and what dept_code they have
    accounts = cursor.execute("SELECT * FROM evaluation_accounts WHERE username LIKE 'UP%' LIMIT 5").fetchall()
    print(f"\nFound {len(accounts)} UP accounts (sample):")
    for acc in accounts:
        print(f"User: {acc['username']}, DeptCode: {acc['dept_code']}, Type: {acc['account_type']}, DeptName: {acc['dept_name']}")

if __name__ == '__main__':
    check_dept()
