
import sqlite3
import random
from app import app, get_db

def simulate_data():
    print("开始生成测试数据...")
    with app.app_context():
        db = get_db()
        cur = db.cursor()

        # 1. 获取所有未提交的账号
        accounts = db.execute("SELECT * FROM evaluation_accounts WHERE status != '否'").fetchall()
        print(f"找到 {len(accounts)} 个未提交账号。")

        for idx, acc in enumerate(accounts):
            username = acc['username']
            dept_code = acc['dept_code']
            
            print(f"[{idx+1}/{len(accounts)}] 处理账号: {username} ({acc['dept_name']})...")

            # ==========================================
            # 模块一：领导班子综合考核评价 (Project 1)
            # ==========================================
            # 生成 12 个维度的随机分数 (8.0 - 10.0)
            team_dims = [
                's_political_resp', 's_social_resp', 's_manage_benefit', 's_manage_effic',
                's_risk_control', 's_tech_innov', 's_deep_reform', 's_talent_strength',
                's_party_build', 's_party_conduct', 's_unity', 's_mass_ties'
            ]
            
            team_scores = {}
            total_team_score = 0
            for dim in team_dims:
                # 随机 8.0 - 10.0，保留1位小数
                score = round(random.uniform(8.0, 10.0), 1)
                team_scores[dim] = score
                total_team_score += score
            
            # 计算总分 (简单求和，或者按权重？app.py里是求和后再处理，这里先直接存各项和)
            # 实际上 app.py 的 submit_team_score 是存了各项，然后 total_score 是由后端计算的。
            # 这里简单处理，模拟 app.py logic，app.py 似乎是直接求和存入 total_score? 
            # 检查 app.py: submit_team_score -> total_score = sum(values). 
            # 其实 app.py 里的 total_score 字段有些是一个计算后的加权分，有些是总分。
            # 在 team_scores 表定义里： total_score REAL
            # 我们就存 sum 吧。
            
            # 插入 team_scores
            cols = ['rater_account', 'target_dept_code', 'total_score'] + team_dims
            q = ', '.join(['?'] * len(cols))
            vals = [username, dept_code, total_team_score] + [team_scores[d] for d in team_dims]
            
            cur.execute(f'INSERT INTO team_scores ({", ".join(cols)}) VALUES ({q})', vals)


            # ==========================================
            # 模块二：优秀干部民主推荐 (Project 4 & 5)
            # ==========================================
            
            # 2.1 准备配置
            dept_config = db.execute("SELECT * FROM department_config WHERE dept_code=?", (dept_code,)).fetchone()
            if not dept_config:
                print(f"  ->警告: 找不到部门配置 {dept_code}，跳过推荐模块")
            else:
                # -----------------------
                # 正职推荐
                # -----------------------
                limit_prin = dept_config['count_recommend_principal'] or 0
                if limit_prin > 0:
                    # 清理旧数据 (防止重跑时主键冲突)
                    cur.execute("DELETE FROM recommendation_scores_principal WHERE rater_account=?", (username,))
                    
                    # 获取候选人
                    candidates_prin = db.execute("SELECT * FROM recommend_principal WHERE dept_code=?", (dept_code,)).fetchall()
                    
                    # 20% 概率放弃推荐
                    if random.random() < 0.2:

                        # 放弃推荐
                        cur.execute('''
                            INSERT INTO recommendation_scores_principal (rater_account, target_dept_code, examinee_id, examinee_name, is_recommended)
                            VALUES (?, ?, 0, '放弃推荐', 0)
                        ''', (username, dept_code))
                        # print("  -> 正职: 放弃推荐")
                    else:
                        # 随机选择 1 到 limit_prin 个 (如果 candidates 够)
                        # 如果 count < limit, 全选? 或者是 0? 
                        # 逻辑：随机选择不超过上限。
                        max_select = min(limit_prin, len(candidates_prin))
                        if max_select > 0:
                            num_to_select = random.randint(1, max_select) # 至少选1个，否则就是放弃推荐了
                            selected = random.sample(candidates_prin, num_to_select)
                            for cand in selected:
                                cur.execute('''
                                    INSERT INTO recommendation_scores_principal (rater_account, target_dept_code, examinee_id, examinee_name, is_recommended)
                                    VALUES (?, ?, ?, ?, 1)
                                ''', (username, dept_code, cand['id'], cand['name']))
                            # print(f"  -> 正职: 推荐了 {num_to_select} 人")
                
                # -----------------------
                # 副职推荐
                # -----------------------
                limit_deputy = dept_config['count_recommend_deputy'] or 0
                if limit_deputy > 0:
                    # 清理旧数据
                    cur.execute("DELETE FROM recommendation_scores_deputy WHERE rater_account=?", (username,))
                    
                    # 获取候选人
                    candidates_deputy = db.execute("SELECT * FROM recommend_deputy WHERE dept_code=?", (dept_code,)).fetchall()
                    
                    # 20% 概率放弃推荐
                    if random.random() < 0.2:
                         cur.execute('''
                            INSERT INTO recommendation_scores_deputy (rater_account, target_dept_code, examinee_id, examinee_name, is_recommended)
                            VALUES (?, ?, 0, '放弃推荐', 0)
                        ''', (username, dept_code))
                         # print("  -> 副职: 放弃推荐")
                    else:
                        max_select = min(limit_deputy, len(candidates_deputy))
                        if max_select > 0:
                            num_to_select = random.randint(1, max_select)
                            selected = random.sample(candidates_deputy, num_to_select)
                            for cand in selected:
                                cur.execute('''
                                    INSERT INTO recommendation_scores_deputy (rater_account, target_dept_code, examinee_id, examinee_name, is_recommended)
                                    VALUES (?, ?, ?, ?, 1)
                                ''', (username, dept_code, cand['id'], cand['name']))
                            # print(f"  -> 副职: 推荐了 {num_to_select} 人")

            # ==========================================
            # 状态更新
            # ==========================================
            cur.execute("UPDATE evaluation_accounts SET status='否' WHERE username=?", (username,))
        
        db.commit()
        print("所有数据生成完毕！")

if __name__ == '__main__':
    simulate_data()
