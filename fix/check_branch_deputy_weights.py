import sqlite3
import pandas as pd

def check_weights():
    conn = sqlite3.connect('evaluation.db')
    cursor = conn.cursor()
    
    # Check weight_config_dept for Branch Deputy
    print("=== Weight Config for Branch Deputy (examinee_role LIKE '%分公司%副职%') ===")
    rows = cursor.execute("SELECT id, rater_role, weight FROM weight_config_dept WHERE examinee_role LIKE '%分公司%副职%'").fetchall()
    for r in rows:
        print(f"ID: {r[0]}, Rater: {r[1]}, Weight: {r[2]}")

    # Check leader_weight_config for V (Lanzhou) and W (Fushun)
    print("\n=== Leader Weights for V and W ===")
    cols = ['dept_code', 'w_yang_weisheng', 'w_wang_ling', 'w_xu_qingchun', 'w_zhao_tong', 'w_ge_shaohui', 'w_liu_chaowei']
    rows = cursor.execute(f"SELECT {', '.join(cols)} FROM leader_weight_config WHERE dept_code IN ('V', 'W')").fetchall()
    for r in rows:
        print(f"Dept: {r[0]}, Weights: {r[1:]}, Sum: {sum(filter(None, r[1:]))}")

    conn.close()

if __name__ == '__main__':
    check_weights()
