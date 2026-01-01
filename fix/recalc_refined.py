
import sqlite3
import pandas as pd

def trigger_calculate():
    conn = sqlite3.connect('evaluation.db')
    cursor = conn.cursor()
    
    # 1. Fetch Data
    sql = '''
        SELECT 
            d.dept_name, 
            t.target_dept_code as dept_code, 
            t.rater_account, 
            t.total_score as score,
            d.sort_no as dept_sort_no,
            ea.account_type
        FROM team_scores t
        LEFT JOIN department_config d ON t.target_dept_code = d.dept_code
        LEFT JOIN evaluation_accounts ea ON t.rater_account = ea.username
    '''
    df = pd.read_sql_query(sql, conn)
    
    if df.empty:
        print("No data")
        return

    # EXCLUDE A0/院领导
    df = df[df['dept_code'] != 'A0'].copy()
    df = df[df['account_type'] != '院领导'].copy()

    if df.empty:
        print("No valid records after filtering A0")
        cursor.execute('DELETE FROM team_score_details') # Clear if empty
        conn.commit()
        return

    # Rounding
    df['score'] = df['score'].round(2)

    type_order = {
        '院领导': 1,
        '正职': 2,
        '副职': 3,
        '中心基层领导': 4,
        '其他员工': 5
    }
    
    df['type_rank'] = df['account_type'].map(type_order).fillna(99)
    df['account_num'] = df['rater_account'].str.extract(r'(\d+)$').fillna(0).astype(int)
    df.sort_values(by=['dept_sort_no', 'type_rank', 'account_num'], ascending=[True, True, True], inplace=True)
    df['sort_no'] = range(1, len(df) + 1)
    
    valid_cols = ['dept_name', 'dept_code', 'rater_account', 'score', 'sort_no']
    insert_df = df[valid_cols].copy()
    
    cursor.execute('DELETE FROM team_score_details')
    data_to_insert = insert_df.to_records(index=False).tolist()
    cursor.executemany('''
        INSERT INTO team_score_details (dept_name, dept_code, rater_account, score, sort_no) 
        VALUES (?, ?, ?, ?, ?)
    ''', data_to_insert)
    
    conn.commit()
    print(f"Recalculated {len(data_to_insert)} records (A0 excluded).")
    conn.close()

if __name__ == '__main__':
    trigger_calculate()
