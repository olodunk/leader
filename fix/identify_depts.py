
import sqlite3

def list_depts():
    db = sqlite3.connect('evaluation.db')
    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    
    # Target Keywords to search for
    keywords = ['兰州', '大庆', '抚顺', '昆冈', '分公司', '中心']
    
    print("--- Listing All Departments ---")
    
    rows = cursor.execute('SELECT dept_name, dept_code FROM department_config').fetchall()
    
    targets = []
    
    for row in rows:
        name = row['dept_name']
        code = row['dept_code']
        print(f"Code: {code}, Name: {name}")
        
    print("\n--- Identifying Targets ---")
    # Manually looking at the previous output, I saw:
    # 'ݷֹ˾': likely Lanzhou Branch? (Code V)
    # 'Ը˳ֹ˾': likely Fushun Branch? (Code W)
    # 'ݻо': likely Lanzhou Research? (Code X)
    # '컯о': likely Daqing Research? (Code Y)
    
    # Let's confirm by exact value if possible using simple python checks
    
    # Based on the garbled output:
    # V: 'ݷֹ˾' -> KunGang Lanzhou Branch? (昆冈兰州分公司)
    # W: 'Ը˳ֹ˾' -> KunGang Fushun Branch? (昆冈抚顺分公司)
    # X: 'ݻо' -> Lanzhou Chemical Research Center? (兰州化工研究中心)
    # Y: '컯о' -> Daqing Chemical Research Center? (大庆化工研究中心)
    
    # I will assume V, W, X, Y are the codes based on their position at the end of the list 
    # and the length of the garbled text matching "分公司" (3 chars + prefix) or "中心" (2 chars).
    
    # Let's print them specifically.

if __name__ == '__main__':
    list_depts()
