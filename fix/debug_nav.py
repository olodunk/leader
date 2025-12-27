
import sqlite3

def test_injection_logic(username):
    db = sqlite3.connect('evaluation.db')
    db.row_factory = sqlite3.Row
    
    print(f"--- Debugging for user: {username} ---")
    
    # 1. Fetch User Row
    user_row = db.execute('SELECT * FROM evaluation_accounts WHERE username=?', (username,)).fetchone()
    if not user_row:
        print("User not found")
        return
        
    dept_code = user_row['dept_code']
    print(f"Dept Code: {dept_code}")
    
    # 2. Fetch Dept Config
    d_row = db.execute('SELECT * FROM department_config WHERE dept_code=?', (dept_code,)).fetchone()
    if not d_row:
        print("Dept Config not found")
        return
        
    print(f"Dept Name: {d_row['dept_name']}")
    
    # 3. Check value
    # Replicate EXACT code from app.py
    # if d_row and d_row['count_recommend_principal'] and d_row['count_recommend_principal'] >= 1:
    
    val = d_row['count_recommend_principal']
    print(f"count_recommend_principal (raw): {val!r}")
    print(f"Type: {type(val)}")
    
    enabled = False
    if d_row and d_row['count_recommend_principal'] and d_row['count_recommend_principal'] >= 1:
        enabled = True
        
    print(f"Logic Result (enabled): {enabled}")

if __name__ == '__main__':
    test_injection_logic('KP001')
