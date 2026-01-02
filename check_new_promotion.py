"""检查新提拔评议表数据完整性"""
import sqlite3
import json

db = sqlite3.connect('evaluation.db')
db.row_factory = sqlite3.Row

# 获取候选人数量
candidates = db.execute(
    "SELECT id FROM center_grassroots_leaders WHERE dept_code IN ('X','Y') AND is_newly_promoted='是'"
).fetchall()
candidate_ids = set(str(c['id']) for c in candidates)
print(f"候选人总数: {len(candidate_ids)}")
print(f"候选人ID: {sorted(candidate_ids)}")

# 检查每条记录
rows = db.execute('SELECT rater_account, selections FROM evaluation_new_promotion').fetchall()
print(f"\n评议记录总数: {len(rows)}")

issues = []
for row in rows:
    account = row['rater_account']
    selections = json.loads(row['selections']) if row['selections'] else {}
    
    # 检查是否所有候选人都有选项
    missing = candidate_ids - set(selections.keys())
    empty_values = [k for k, v in selections.items() if not v]
    
    if missing:
        issues.append(f"{account}: 缺少候选人 {missing}")
    if empty_values:
        issues.append(f"{account}: 空值项 {empty_values}")

if issues:
    print("\n发现问题:")
    for issue in issues[:20]:  # 只显示前20个
        print(f"  - {issue}")
    print(f"\n共 {len(issues)} 个问题")
else:
    print("\n[OK] 所有记录完整，无空值")

db.close()
