import sqlite3
import sys
from app import get_democratic_nav, get_db, app

# Fix encoding
sys.stdout.reconfigure(encoding='utf-8')

def list_data():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()

        rater_account = 'EP001'
        print(f"--- Debugging for User: {rater_account} ---")
        
        # 1. Get User Info
        user = cursor.execute('SELECT * FROM evaluation_accounts WHERE username=?', (rater_account,)).fetchone()
        if not user:
            print("User not found!")
            return

        print(f"User Tuple: {tuple(user)}")
        
        # Mock user row as dict and add missing 'dept_type'
        user_dict = dict(user)
        user_dict['dept_type'] = '职能部门' # Assumption for debug
        
        # 2. Call Nav
        # get_democratic_nav expects a Row or dict-like object
        nav_items = get_democratic_nav(user_dict)
        print(f"\nNav Items Count: {len(nav_items)}")
        for i, item in enumerate(nav_items):
            print(f"[{i}] Key: {item['key']}, Title: {item['title']}")
            print(f"    Roles: {item['roles']}")
            
            # 3. Simulate The Check Logic
            roles = item.get('roles', [])
            if not roles:
                 print("    -> No roles, Check Fails")
            else:
                placeholders = ','.join(['?'] * len(roles))
                query = f"SELECT 1 FROM democratic_scores WHERE rater_account=? AND examinee_role IN ({placeholders}) LIMIT 1"
                params = [rater_account] + roles
                has_score = db.execute(query, params).fetchone()
                print(f"    -> Check Result: {bool(has_score)}")
                
                # If fail, verify what we HAVE stored
                if not has_score:
                    print("    -> Mismatch! Checking stored scores...")
                    all_scores = db.execute('SELECT examinee_role FROM democratic_scores WHERE rater_account=?', (rater_account,)).fetchall()
                    stored = set([r[0] for r in all_scores])
                    print(f"       Stored Roles: {stored}")
                    # Check partial matches?
                    for r in roles:
                        if r in stored: print(f"       !!! Role '{r}' IS in stored set!")
                        else: print(f"       Role '{r}' NOT in stored set.")

if __name__ == '__main__':
    list_data()
