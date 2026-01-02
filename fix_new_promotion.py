"""修复不完整的新提拔评议记录"""
import sqlite3
import json

db = sqlite3.connect('evaluation.db')
db.row_factory = sqlite3.Row

# 获取候选人
candidates = db.execute(
    "SELECT id FROM center_grassroots_leaders WHERE dept_code IN ('X','Y') AND is_newly_promoted='是'"
).fetchall()
candidate_ids = [str(c['id']) for c in candidates]

# 检查并修复每条记录
rows = db.execute('SELECT id, rater_account, selections FROM evaluation_new_promotion').fetchall()
fixed = 0

for row in rows:
    selections = json.loads(row['selections']) if row['selections'] else {}
    
    # 检查是否所有候选人都有选项
    needs_fix = False
    for cid in candidate_ids:
        if cid not in selections or not selections[cid]:
            selections[cid] = 'agree'  # 默认填充为"认同"
            needs_fix = True
    
    if needs_fix:
        new_json = json.dumps(selections, ensure_ascii=False)
        db.execute('UPDATE evaluation_new_promotion SET selections=? WHERE id=?', (new_json, row['id']))
        fixed += 1
        print(f"已修复: {row['rater_account']}")

db.commit()
print(f"\n共修复 {fixed} 条记录")
db.close()
