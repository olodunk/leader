
import sqlite3

def inspect():
    db = sqlite3.connect('evaluation.db')
    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    
    print("--- Tables ---")
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    for t in tables:
        print(f"- {t['name']}")
        
    # Check suspicious tables for columns
    candidates = ['personnel', 'cadres', 'users', 'examinees', 'employees']
    
    print("\n--- Inspecting Potential Tables ---")
    for t in tables:
        tname = t['name']
        # Heuristic to check tables that might hold personnel info
        if any(c in tname for c in ['user', 'account', 'person', 'candidate', 'recommend', 'evaluation_accounts']):
             print(f"\nSchema for {tname}:")
             try:
                 cols = cursor.execute(f"PRAGMA table_info({tname})").fetchall()
                 for c in cols:
                     print(f"  {c['name']} ({c['type']})")
             except:
                 pass

    # Check for 'Center Grassroots Leader' role
    # Assuming 'evaluation_accounts' or similar might hold it?
    # Or maybe there is no central table and it's scatterd?
    
if __name__ == '__main__':
    inspect()
