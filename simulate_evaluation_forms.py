"""
评议表数据模拟脚本
- 干部选拔任用工作民主评议表 (V/W/X/Y)
- 新提拔任用干部民主评议表 (X/Y)
"""
import sqlite3
import random
import json

DB_PATH = 'evaluation.db'

# Q5/Q6 建议文本
Q5_SUGGESTIONS = [
    "建议加强对年轻干部的培养力度，建立更完善的后备人才库。",
    "希望选拔干部时更注重基层工作经验和实际业绩考核。",
    "建议加大干部交流轮岗力度，拓宽干部成长通道。",
    "建议进一步完善竞争上岗机制，增强选人用人公信度。",
    "希望加强对新任领导干部的岗前培训和跟踪考核。",
]

Q6_SUGGESTIONS = [
    "建议评议结果公开透明，及时向员工反馈整改情况。",
    "希望缩短评议周期，使反馈更加及时有效。",
    "建议增加匿名渠道，鼓励员工提出真实意见。",
    "希望将评议结果与干部考核挂钩，增强约束力。",
    "建议定期组织选人用人工作座谈会，广泛征求意见。",
]

OPTIONS_Q123 = ['好', '较好', '一般', '差']
OPTIONS_PROMOTION = ['agree', 'basic_agree', 'disagree', 'unknown']


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def simulate_selection_appointment():
    """模拟干部选拔任用工作民主评议表"""
    db = get_db()
    
    # 获取 V/W/X/Y 部门的账号
    accounts = db.execute(
        "SELECT username, dept_code FROM evaluation_accounts WHERE dept_code IN ('V','W','X','Y')"
    ).fetchall()
    
    if not accounts:
        print("未找到 V/W/X/Y 部门账号")
        return
    
    print(f"找到 {len(accounts)} 个选拔任用评议权限账号")
    
    # 随机选择填 q5/q6 的账号 (各5个)
    account_list = [a['username'] for a in accounts]
    q5_accounts = set(random.sample(account_list, min(5, len(account_list))))
    q6_accounts = set(random.sample(account_list, min(5, len(account_list))))
    
    # 20% 填 q4 的账号
    q4_count = max(1, int(len(account_list) * 0.2))
    q4_accounts = set(random.sample(account_list, q4_count))
    
    cursor = db.cursor()
    
    for acc in accounts:
        username = acc['username']
        dept_code = acc['dept_code']
        
        # Q1-Q3 随机选择
        q1 = random.choice(OPTIONS_Q123)
        q2 = random.choice(OPTIONS_Q123)
        q3 = random.choice(OPTIONS_Q123)
        
        # Q4 20%账号随机选2-3个问题
        q4 = ''
        if username in q4_accounts:
            problem_count = random.randint(2, 3)
            problems = random.sample(range(1, 13), problem_count)
            q4 = ','.join(str(p) for p in sorted(problems))
        
        # Q5/Q6 指定账号填写
        q5 = random.choice(Q5_SUGGESTIONS) if username in q5_accounts else ''
        q6 = random.choice(Q6_SUGGESTIONS) if username in q6_accounts else ''
        
        # Upsert
        exist = cursor.execute(
            "SELECT id FROM evaluation_selection_appointment WHERE rater_account=?", 
            (username,)
        ).fetchone()
        
        if exist:
            cursor.execute('''
                UPDATE evaluation_selection_appointment 
                SET q1_overall=?, q2_supervision=?, q3_rectification=?, 
                    q4_problems=?, q5_suggestions_employment=?, q6_suggestions_report=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE rater_account=?
            ''', (q1, q2, q3, q4, q5, q6, username))
        else:
            cursor.execute('''
                INSERT INTO evaluation_selection_appointment 
                (rater_account, dept_code, q1_overall, q2_supervision, q3_rectification, 
                 q4_problems, q5_suggestions_employment, q6_suggestions_report)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (username, dept_code, q1, q2, q3, q4, q5, q6))
    
    db.commit()
    print(f"[OK] 干部选拔任用评议表模拟完成，共 {len(accounts)} 条记录")
    db.close()


def simulate_new_promotion():
    """模拟新提拔任用干部民主评议表"""
    db = get_db()
    
    # 获取 X/Y 部门的账号
    accounts = db.execute(
        "SELECT username, dept_code FROM evaluation_accounts WHERE dept_code IN ('X','Y')"
    ).fetchall()
    
    if not accounts:
        print("未找到 X/Y 部门账号")
        return
    
    print(f"找到 {len(accounts)} 个新提拔评议权限账号")
    
    # 获取候选人 (center_grassroots_leaders 中 X/Y 部门且 is_newly_promoted='是')
    candidates = db.execute(
        "SELECT id FROM center_grassroots_leaders WHERE dept_code IN ('X','Y') AND is_newly_promoted='是'"
    ).fetchall()
    
    if not candidates:
        print("未找到新提拔候选人")
        return
    
    candidate_ids = [c['id'] for c in candidates]
    print(f"找到 {len(candidate_ids)} 个新提拔候选人")
    
    # 80% 账号全选认同
    agree_count = int(len(accounts) * 0.8)
    account_list = [a['username'] for a in accounts]
    random.shuffle(account_list)
    agree_accounts = set(account_list[:agree_count])
    
    cursor = db.cursor()
    
    for acc in accounts:
        username = acc['username']
        dept_code = acc['dept_code']
        
        # 构建 selections JSON
        selections = {}
        for cid in candidate_ids:
            if username in agree_accounts:
                selections[str(cid)] = 'agree'
            else:
                selections[str(cid)] = random.choice(OPTIONS_PROMOTION)
        
        json_str = json.dumps(selections, ensure_ascii=False)
        
        # Upsert
        exist = cursor.execute(
            "SELECT id FROM evaluation_new_promotion WHERE rater_account=?",
            (username,)
        ).fetchone()
        
        if exist:
            cursor.execute('''
                UPDATE evaluation_new_promotion 
                SET selections=?, updated_at=CURRENT_TIMESTAMP
                WHERE rater_account=?
            ''', (json_str, username))
        else:
            cursor.execute('''
                INSERT INTO evaluation_new_promotion (rater_account, dept_code, selections)
                VALUES (?, ?, ?)
            ''', (username, dept_code, json_str))
    
    db.commit()
    print(f"[OK] 新提拔评议表模拟完成，共 {len(accounts)} 条记录")
    db.close()


def verify_results():
    """验证模拟结果"""
    db = get_db()
    
    # 选拔任用表统计
    sa_count = db.execute("SELECT COUNT(*) FROM evaluation_selection_appointment").fetchone()[0]
    sa_q4 = db.execute("SELECT COUNT(*) FROM evaluation_selection_appointment WHERE q4_problems != ''").fetchone()[0]
    sa_q5 = db.execute("SELECT COUNT(*) FROM evaluation_selection_appointment WHERE q5_suggestions_employment != ''").fetchone()[0]
    sa_q6 = db.execute("SELECT COUNT(*) FROM evaluation_selection_appointment WHERE q6_suggestions_report != ''").fetchone()[0]
    
    print("\n=== 验证结果 ===")
    print(f"干部选拔任用评议表: {sa_count} 条")
    print(f"  - Q4有填写: {sa_q4} 条 ({sa_q4/sa_count*100:.1f}%)" if sa_count else "")
    print(f"  - Q5有填写: {sa_q5} 条")
    print(f"  - Q6有填写: {sa_q6} 条")
    
    # 新提拔表统计
    np_count = db.execute("SELECT COUNT(*) FROM evaluation_new_promotion").fetchone()[0]
    print(f"\n新提拔评议表: {np_count} 条")
    
    db.close()


if __name__ == '__main__':
    print("开始模拟评议表数据...\n")
    simulate_selection_appointment()
    print()
    simulate_new_promotion()
    verify_results()
    print("\n模拟完成!")
