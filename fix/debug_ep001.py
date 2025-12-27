import sqlite3
import unicodedata

def debug_db():
    try:
        conn = sqlite3.connect('evaluation.db')
        c = conn.cursor()
        
        print('-- User EP001 --')
        user = c.execute("SELECT username, dept_code, account_type FROM evaluation_accounts WHERE username='EP001'").fetchone()
        print(user)
        
        print('-- Target Config (Two Center Principal) --')
        # Use LIKE to avoid strict encoding matching for now, or ensure string is correct
        configs = c.execute("SELECT * FROM democratic_rating_config WHERE examinee_role LIKE '%两中心正职%' AND is_allowed=1").fetchall()
        print(f"Configs found: {len(configs)}")
        for cfg in configs:
            print(cfg)
            
        print('-- Candidates (Two Center Principal) --')
        candidates = c.execute("SELECT id, name, role FROM middle_managers WHERE role LIKE '%两中心正职%'").fetchall()
        print(f"Candidates found: {len(candidates)}")
        for cand in candidates:
            print(cand)
            
        # Check permissions for Functional Principal
        print('-- Permissions for Functional Principal --')
        perms = c.execute("SELECT * FROM democratic_rating_config WHERE rater_role='职能部门正职' AND is_allowed=1").fetchall()
        print([p[1] for p in perms]) # Print target roles
        
        conn.close()
    except Exception as e:
        print(e)

if __name__ == "__main__":
    debug_db()
