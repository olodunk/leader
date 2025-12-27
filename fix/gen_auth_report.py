
import sqlite3

def generate_report():
    db = sqlite3.connect('evaluation.db')
    db.row_factory = sqlite3.Row
    
    print("# 具备“优秀干部民主推荐-正职”权限的账号列表\n")
    print("以下账号所在的部门配置了 `count_recommend_principal >= 1`，因此应能在侧边栏看到推荐入口。\n")
    
    # 1. Get Valid Departments
    dept_rows = db.execute("SELECT dept_code, dept_name, count_recommend_principal FROM department_config WHERE count_recommend_principal >= 1 ORDER BY dept_code").fetchall()
    
    valid_depts = {r['dept_code']: r for r in dept_rows}
    
    if not valid_depts:
        print("**当前系统没有任何部门配置了推荐名额！**")
        return

    print("| 部门代码 | 部门名称 | 推荐名额 | 账号示例 (前5个) |")
    print("| :--- | :--- | :--- | :--- |")
    
    for d_code, d_info in valid_depts.items():
        # Get Accounts
        accs = db.execute("SELECT username FROM evaluation_accounts WHERE dept_code=? ORDER BY username", (d_code,)).fetchall()
        acc_list = [a['username'] for a in accs]
        
        example_str = ', '.join(acc_list[:5])
        if len(acc_list) > 5:
            example_str += f" 等共{len(acc_list)}个"
            
        print(f"| {d_code} | {d_info['dept_name']} | {d_info['count_recommend_principal']} | {example_str} |")

if __name__ == '__main__':
    generate_report()
