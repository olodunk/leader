# [计划] 修复中层干部民主测评完成状态逻辑 (修正版)

## 问题描述
目前“中层干部民主测评”在“操作结束”页面显示为一个项目，但只要完成了其中任何一个子项目就被标记为完成。即使用户只需完成部分子项目，逻辑也过于宽松。
用户要求：**仍然只显示一个主项目“中层干部民主测评”**，但只有当**所有**子项目全部提交后，该主项目才显示为完成。

## 解决方案
修改 `app.py` 中的 `check_assessment_progress` 函数。
在处理 `Democratic Evaluation` 时：
1.  获取用户所有需要参与的子项目 (`nav_items`).
2.  遍历每一个子项目，检查其是否已在数据库中提交（`democratic_scores` 表中是否存在对应 `target_dept_code` 的记录）。
3.  只有当**所有**子项目都已提交时，`democratic_completed` 状态才为 `True`。否则为 `False`。
4.  链接跳转逻辑优化：
    -   如果有未完成的子项目，点击链接跳转到第一个**未完成**的子项目。
    -   如果全部完成，跳转到第一个子项目。

## 实施步骤

1.  **修改 `app.py`**:
    -   定位到 `check_assessment_progress` 函数。
    -   获取 `nav_items`。
    -   初始化 `all_subs_completed = True`。
    -   初始化 `first_incomplete_key = None`。
    -   遍历 `nav_items`：
        -   查询数据库检查该 `key` 是否有记录。
        -   如果无记录 -> `all_subs_completed = False`，记录 `first_incomplete_key` (如果尚未记录)，并跳出循环(可选，或继续检查以获取完整状态)。
    -   添加项目到 `projects` 列表：
        -   `key`: 'democratic'
        -   `name`: '中层干部民主测评'
        -   `completed`: `all_subs_completed`
        -   `url`: 指向 `first_incomplete_key` (优先) 或 `nav_items[0]['key']`。

## 代码变更详情 (预计)

```python
    # ... inside check_assessment_progress ...
    
    # --- 3. Democratic Evaluation ---
    nav_items = get_democratic_nav(user_row)
    if nav_items:
        all_subs_done = True
        target_jump_key = nav_items[0]['key'] # Default to first
        found_incomplete = False
        
        for item in nav_items:
            # Check DB for this specific group
            # Assuming item['key'] is stored as target_dept_code in democratic_scores
            has_score = db.execute('SELECT 1 FROM democratic_scores WHERE rater_account=? AND target_dept_code=? LIMIT 1', (rater_account, item['key'])).fetchone()
            
            if not has_score:
                all_subs_done = False
                if not found_incomplete:
                    target_jump_key = item['key']
                    found_incomplete = True
        
        add_proj('democratic', '中层干部民主测评', 'assessment_democratic', all_subs_done, group_key=target_jump_key)
```
