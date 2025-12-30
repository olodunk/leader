"""
中层干部民主测评模拟打分 V3
逻辑：遍历所有部门 × 所有账号类型，每组合选1个账号，完成所有有权限的打分
"""
import sqlite3
import random

DATABASE = 'evaluation.db'

DEMOCRATIC_DIMS = [
    's_political_ability', 's_political_perf', 's_party_build', 's_professionalism',
    's_leadership', 's_learning_innov', 's_performance', 's_responsibility',
    's_style_image', 's_integrity'
]

def get_random_score():
    return round(random.uniform(8.0, 10.0), 1)

def main():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. 清空旧的民主测评数据
    print("清空旧的 democratic_scores...")
    cursor.execute('DELETE FROM democratic_scores')
    conn.commit()
    
    # 2. 获取所有部门
    depts = cursor.execute('SELECT dept_code, dept_name FROM department_config').fetchall()
    print(f"共 {len(depts)} 个部门")
    
    # 3. 获取所有账号类型
    acc_types = cursor.execute('SELECT DISTINCT account_type FROM evaluation_accounts').fetchall()
    acc_types = [r[0] for r in acc_types]
    print(f"账号类型: {acc_types}")
    
    # 4. 获取权限矩阵: rater_role -> [allowed examinee_roles]
    # Note: account_type (正职/副职) needs to be matched to rater_role (职能部门正职/研究所正职 etc.)
    perms_raw = cursor.execute('SELECT rater_role, examinee_role FROM democratic_rating_config WHERE is_allowed=1').fetchall()
    perms = {}
    for rr, er in perms_raw:
        if rr not in perms:
            perms[rr] = []
        perms[rr].append(er)
    print(f"权限矩阵: {len(perms)} 种打分人角色有权限")
    
    # Map generic account_type to specific rater_roles
    def get_matching_rater_roles(acc_type):
        """Return list of rater_roles that match this account_type"""
        matching = []
        for rr in perms.keys():
            if acc_type == '院领导' and rr == '院领导':
                matching.append(rr)
            elif acc_type == '正职' and '正职' in rr and '副职' not in rr:
                matching.append(rr)
            elif acc_type == '副职' and '副职' in rr:
                matching.append(rr)
            elif acc_type == '其他员工' and ('员工' in rr or '其他' in rr):
                matching.append(rr)
            elif acc_type == '中心基层领导' and '基层' in rr:
                matching.append(rr)
        return matching
    
    # 5. 获取所有中层干部 (被考核人)
    all_managers = cursor.execute('SELECT id, name, role, dept_code, dept_name FROM middle_managers').fetchall()
    print(f"共 {len(all_managers)} 名被考核人")
    
    total_scores = 0
    selected_accounts = []
    
    # 6. 遍历 部门 × 账号类型
    for dept in depts:
        dept_code = dept['dept_code']
        
        for acc_type in acc_types:
            # 检查该类型是否有民主测评权限 (使用映射)
            matching_roles = get_matching_rater_roles(acc_type)
            if not matching_roles:
                continue  # 该类型无权限，跳过
            
            # 合并所有匹配角色的权限
            allowed_roles = []
            for mr in matching_roles:
                allowed_roles.extend(perms.get(mr, []))
            allowed_roles = list(set(allowed_roles))  # 去重
            
            if not allowed_roles:
                continue
            
            # 从该部门该类型中选取1个账号
            accounts = cursor.execute(
                'SELECT username FROM evaluation_accounts WHERE dept_code=? AND account_type=?',
                (dept_code, acc_type)
            ).fetchall()
            
            if not accounts:
                continue  # 该部门该类型无账号
                
            selected = random.choice(accounts)['username']
            selected_accounts.append((dept_code, acc_type, selected))
            
            # 该账号对所有有权限的被考核人进行打分
            for target_role in allowed_roles:
                # 找到所有该角色的被考核人
                # 注意：这里需要处理角色名称的差异（如"职能部门正职" vs "正职"）
                # 简化处理：使用 LIKE 匹配
                if target_role == '院领导':
                    candidates = [m for m in all_managers if m['role'] == '院领导']
                elif '正职' in target_role and '副职' not in target_role:
                    candidates = [m for m in all_managers if '正职' in m['role'] and '副职' not in m['role']]
                elif '副职' in target_role:
                    candidates = [m for m in all_managers if '副职' in m['role']]
                else:
                    # 尝试精确匹配
                    candidates = [m for m in all_managers if m['role'] == target_role]
                
                # 排除自己部门（如果不是院领导）
                is_college_leader = (acc_type == '院领导')
                if not is_college_leader:
                    candidates = [c for c in candidates if c['dept_code'] != dept_code]
                
                for cand in candidates:
                    cand_id = cand['id']
                    cand_name = cand['name']
                    
                    # 生成分数
                    scores = [get_random_score() for _ in range(10)]
                    total = sum(scores)
                    
                    # 插入记录
                    cols = ['rater_account', 'examinee_id', 'examinee_name', 'examinee_role', 'total_score'] + DEMOCRATIC_DIMS
                    q = ', '.join(['?'] * len(cols))
                    vals = [selected, cand_id, cand_name, target_role, total] + scores
                    cursor.execute(f'INSERT INTO democratic_scores ({", ".join(cols)}) VALUES ({q})', vals)
                    total_scores += 1
    
    conn.commit()
    conn.close()
    
    print(f"\n--- 模拟完成 ---")
    print(f"选取账号数: {len(selected_accounts)}")
    print(f"生成评分数: {total_scores}")
    print(f"部分选取的账号: {selected_accounts[:10]}")

if __name__ == '__main__':
    main()
