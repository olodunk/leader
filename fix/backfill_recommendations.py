
import sqlite3
from app import app, get_db

def backfill_recommendations():
    print("开始补全推荐数据...")
    with app.app_context():
        db = get_db()
        cur = db.cursor()

        # Helper to process a table pair
        def process_type(score_table, candidate_table, type_name):
            print(f"正在处理: {type_name}...")
            
            # 1. 找出所有已提交的打分人及其部门信息
            # 我们需要 join account table 或者 department config? 
            # 最好直接从 score table 拿 rater + dept.
            # 但 score table 可能存在 id=0 的 dummy record.
            
            raters = db.execute(f"SELECT DISTINCT rater_account, target_dept_code FROM {score_table}").fetchall()
            
            count_processed = 0
            for r in raters:
                account = r['rater_account']
                dept_code = r['target_dept_code']
                
                # 2. 获取该部门所有候选人
                candidates = db.execute(f"SELECT id, name FROM {candidate_table} WHERE dept_code=?", (dept_code,)).fetchall()
                if not candidates:
                    continue

                # 3. 获取该人已存在的记录
                existing = db.execute(f"SELECT examinee_id FROM {score_table} WHERE rater_account=?", (account,)).fetchall()
                existing_ids = {row['examinee_id'] for row in existing}
                
                # 4. 补全缺失数据
                for cand in candidates:
                    cid = cand['id']
                    cname = cand['name']
                    
                    if cid not in existing_ids:
                        # 插入 0
                        cur.execute(f'''
                            INSERT INTO {score_table} 
                            (rater_account, target_dept_code, examinee_id, examinee_name, is_recommended)
                            VALUES (?, ?, ?, ?, 0)
                        ''', (account, dept_code, cid, cname))
                
                # 5. 清理 dummy record (id=0)
                cur.execute(f"DELETE FROM {score_table} WHERE rater_account=? AND examinee_id=0", (account,))
                
                count_processed += 1
                if count_processed % 50 == 0:
                    print(f"  已处理 {count_processed} 个用户...")
            
            print(f"  {type_name} 处理完成。")

        # 执行
        process_type('recommendation_scores_principal', 'recommend_principal', '正职推荐')
        process_type('recommendation_scores_deputy', 'recommend_deputy', '副职推荐')
        
        db.commit()
        print("数据补全完成！")

if __name__ == '__main__':
    backfill_recommendations()
