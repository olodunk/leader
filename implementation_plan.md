# 实施计划 - 被考核人打分明细功能

本计划概述了在后台实现“被考核人打分明细”页面的步骤。

## 用户审查要求
> [!IMPORTANT]
> 排序逻辑将严格遵循用户要求：`部门代码` -> `打分人角色` -> `打分人序号`。这意味着同一部门内，按打分人群体层级排序，同一群体的打分记录会聚集在一起（可能涉及该部门多位被考核人）。

## 建议变更

### 数据库
#### [NEW] 表 `democratic_score_details`
创建一个新表用于存储计算后的民主测评打分快照。
字段:
- `id`: 主键
- `sort_no`: 整数 (序号, 1开始)
- `name`: 文本 (被考核人姓名)
- `dept_name`: 文本 (被考核人部门名称)
- `dept_code`: 文本 (被考核人部门代码)
- `score`: 实数 (得分)
- `rater_account`: 文本 (打分人账号)
- `created_at`: 时间戳

### 后端 (`app.py`)
#### [NEW] 民主测评明细相关路由
- `GET /admin/democratic-score-details`: 渲染页面。
- `GET /api/democratic-score-details/list`: 获取列表数据，支持分页和筛选（部门名称、部门代码、姓名、打分人账号）。
- `POST /api/democratic-score-details/calculate`:
    - **关联查询**: 
    1. **源1**: `democratic_scores` (关联 `middle_managers`, `electronic_accounts`)
    2. **源2**: `personnel_scores` (关联 `middle_managers`, `electronic_accounts`)
    - 将两份数据合并 (UNION ALL 或在代码中拼接列表)。
    - **注意**: `personnel_scores` 也有 `total_score`，直接映射到 `score`.
    - 应用排序:
        1. `middle_managers.dept_code` (升序)
        2. `evaluation_accounts.account_type` (自定义顺序: 院领导 > 正职 > 副职 > 中心基层领导 > 其他员工)
        3. `evaluation_accounts.username` 数字后缀 (升序)
    - 填充 `democratic_score_details` 表。
- `POST /api/democratic-score-details/clear`: 清空表。
- `GET /api/democratic-score-details/export`: 导出 Excel，使用自定义表头（序号, 姓名, ...）。

### 前端
#### [NEW] `templates/democratic_score_details.html`
- 复制自 `team_score_details.html` 并修改。
- 更新表格列: 序号, 姓名, 部门, 部门代码, 得分, 打分人账号。
- 在筛选栏增加“姓名”搜索输入框。
- 连接到新的 API 接口。

## 验证计划

### 手动验证
1. **一键计算**: 点击“一键计算”按钮，验证是否提示成功。
2. **列表显示**: 验证表格中是否正确显示了序号、姓名、部门、得分等信息。
3. **排序检查**: 检查行数据是否按 部门 -> 打分人角色 -> 打分人序号 的顺序排列。
4. **筛选测试**: 测试按照“姓名”和“部门”进行搜索。
5. **导出测试**: 点击“导出”按钮，验证 Excel 文件内容与表格一致。
