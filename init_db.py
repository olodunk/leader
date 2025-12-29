import sqlite3
import os
import hashlib

DATABASE = 'evaluation.db'

def encrypt_password(password):
    """简单的MD5加密（生产环境建议换成SHA256+Salt）"""
    return hashlib.md5(password.encode('utf-8')).hexdigest()

def init_db():
    print(f"开始初始化数据库: {DATABASE} ...")
    
    # 建立连接
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # 1. 核心优化：开启 WAL 模式 (Write-Ahead Logging)
    cursor.execute('PRAGMA journal_mode=WAL;')
    
    # 2. 开启外键约束支持 (SQLite 默认关闭)
    cursor.execute('PRAGMA foreign_keys = ON;')

    # --------------------------------------------------------
    # 表 1: 系统用户表 (sys_users)
    # --------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sys_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL, -- 存储加密后的密码
            role TEXT DEFAULT 'admin', -- admin, viewer
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # --------------------------------------------------------
    # 表 2: 部门配置表 (department_config) - 核心表
    # --------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS department_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- 基础信息
            serial_no INTEGER,          -- 序号
            sort_no INTEGER,            -- 排序号 (用于前端显示顺序)
            dept_name TEXT NOT NULL,    -- 部门名称
            dept_code TEXT NOT NULL,    -- 部门代码
            dept_type TEXT,             -- 部门类型
            
            -- 领导信息
            leader_main TEXT,           -- 部门主管领导
            leader_sub TEXT,            -- 部门分管领导
            
            -- 账号数量配置 (用于生成打分账号)
            count_college_leader INTEGER DEFAULT 0, -- 院领导账号数量
            count_principal INTEGER DEFAULT 0,      -- 正职账号数据量
            count_deputy INTEGER DEFAULT 0,         -- 副职账号数量
            count_other INTEGER DEFAULT 0,          -- 其他员工账号数量
            count_center_leader INTEGER DEFAULT 0,  -- 中心基层领导账号数量
            
            -- 评测名额限制 (逻辑控制用)
            count_excellent INTEGER DEFAULT 0,           -- 可被评为优秀人数
            count_recommend_principal INTEGER DEFAULT 0, -- 推荐正职人数
            count_recommend_deputy INTEGER DEFAULT 0,    -- 推荐副职人数
            
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dept_code ON department_config(dept_code);')

    # --------------------------------------------------------
    # 表 3: 被考核干部表 (cadres)
    # --------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cadres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,         -- 姓名
            dept_id INTEGER,            -- 归属部门ID (外键)
            position TEXT,              -- 职务
            level TEXT,                 -- 级别 (正处/副处等)
            
            FOREIGN KEY(dept_id) REFERENCES department_config(id) ON DELETE SET NULL
        )
    ''')

    # --------------------------------------------------------
    # 表 4: 评分记录表 (scores)
    # --------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rater_type TEXT,            -- 打分人类型
            rater_token TEXT,           -- 打分人标识
            cadre_id INTEGER,           -- 被考核人ID
            
            -- 维度打分
            score_integrity REAL DEFAULT 0, -- 德
            score_ability REAL DEFAULT 0,   -- 能
            score_diligence REAL DEFAULT 0, -- 勤
            score_performance REAL DEFAULT 0, -- 绩
            score_honest REAL DEFAULT 0,    -- 廉
            
            total_score REAL DEFAULT 0,     -- 总分
            comment TEXT,                   -- 评语
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY(cadre_id) REFERENCES cadres(id) ON DELETE CASCADE
        )
    ''')

    # --------------------------------------------------------
    # 表 5: 中层干部/管理人员表 (middle_managers)
    # --------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS middle_managers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            serial_no INTEGER,          -- 序号
            sort_no INTEGER,            -- 部门内排序号
            name TEXT NOT NULL,         -- 姓名
            gender TEXT,                -- 性别
            position TEXT NOT NULL,     -- 现任职务
            
            dept_name TEXT NOT NULL,    -- 部门名称 (用于显示和匹配)
            dept_id INTEGER,            -- 部门ID (外键关联)
            
            rank_level TEXT,            -- 岗位层级
            birth_date TEXT,            -- 出生年月
            education TEXT,             -- 文化程度
            rank_time TEXT,             -- 现职级时间
            role TEXT,                  -- 员工角色
            
            dept_code TEXT,             -- 部门代码 (New)
            tenure_time TEXT,           -- 任职时间 (New)
            is_newly_promoted TEXT,     -- 是否新提拔干部 (New)
            
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # --------------------------------------------------------
    # 表 6: 正职推荐表 (recommend_principal)
    # --------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recommend_principal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sort_no INTEGER,            -- 排序号
            name TEXT NOT NULL,         -- 姓名
            gender TEXT,                -- 性别
            birth_date TEXT,            -- 出生年月
            dept_name TEXT NOT NULL,    -- 部门名称
            dept_code TEXT NOT NULL,    -- 部门代码
            rank_level TEXT,            -- 岗位层级
            education TEXT,             -- 文化程度
            rank_time TEXT,             -- 现职级时间
            current_position TEXT,      -- 现职务
            
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # --------------------------------------------------------
    # 表 7: 副职推荐表 (recommend_deputy)
    # --------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recommend_deputy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sort_no INTEGER,            -- 排序号
            name TEXT NOT NULL,         -- 姓名
            gender TEXT,                -- 性别
            birth_date TEXT,            -- 出生年月
            dept_name TEXT NOT NULL,    -- 部门名称
            dept_code TEXT NOT NULL,    -- 部门代码
            rank_level TEXT,            -- 岗位层级
            education TEXT,             -- 文化程度
            rank_time TEXT,             -- 现职级时间
            current_position TEXT,      -- 现职务
            
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # --------------------------------------------------------
    # 表 8: 测评账号表 (evaluation_accounts)
    # --------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS evaluation_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dept_name TEXT NOT NULL,    -- 部门名称
            dept_code TEXT NOT NULL,    -- 部门代码
            account_type TEXT,          -- 账号类型 (院领导/正职/副职/中心基层/其他)
            username TEXT NOT NULL UNIQUE, -- 账号 (A0L001)
            password TEXT NOT NULL,     -- 密码 (明文显示)
            status TEXT DEFAULT '是',   -- 账号状态 ("是"=未提交, "否"=已提交)
            
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_account_username ON evaluation_accounts(username);')

    # --------------------------------------------------------
    # 表 9: 部门权重配置表 (weight_config_dept)
    # --------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weight_config_dept (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            examinee_role TEXT NOT NULL,  -- 被考核人角色 (列头)
            rater_role TEXT NOT NULL,     -- 考核人角色 (行头)
            weight REAL DEFAULT 0,        -- 权重 (百分比, e.g. 10.0)
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            
            UNIQUE(examinee_role, rater_role)
        )
    ''')

    # --------------------------------------------------------
    # 表 10: 领导班子评分表 (team_scores)
    # --------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS team_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rater_account TEXT,         -- 打分账号 (username)
            target_dept_code TEXT,      -- 被考核部门代码
            
            -- 12项评分
            s_political_resp REAL,
            s_social_resp REAL,
            s_manage_benefit REAL,
            s_manage_effic REAL,
            s_risk_control REAL,
            s_tech_innov REAL,
            s_deep_reform REAL,
            s_talent_strength REAL,
            s_party_build REAL,
            s_party_conduct REAL,
            s_unity REAL,
            s_mass_ties REAL,
            
            total_score REAL,           -- 总分 (后台加权计算后)
            
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # --------------------------------------------------------
    # 预置数据
    # --------------------------------------------------------
    # 检查是否已有管理员
    cursor.execute('SELECT count(*) FROM sys_users WHERE username = ?', ('admin',))
    if cursor.fetchone()[0] == 0:
        default_pw = encrypt_password('admin123') 
        cursor.execute('INSERT INTO sys_users (username, password) VALUES (?, ?)', ('admin', default_pw))
        print("已创建默认管理员账号: admin / admin123")

    # --------------------------------------------------------
    # 表 7: 领导人员综合考核评价表 (personnel_scores)
    # --------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS personnel_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rater_account TEXT NOT NULL,         -- 打分人账号
            target_dept_code TEXT NOT NULL,      -- 被考核部门代码
            examinee_id INTEGER NOT NULL,        -- 被考核人ID (关联 middle_managers)
            examinee_name TEXT,                  -- 被考核人姓名 (冗余)
            
            evaluation_grade TEXT,               -- 评价等次 (优秀/称职/基本称职/不称职)
            
            -- 10个评分维度 (各占 10%)
            s_political_ability REAL DEFAULT 0,  
            s_political_perf REAL DEFAULT 0,     
            s_party_build REAL DEFAULT 0,        
            s_professionalism REAL DEFAULT 0,    
            s_leadership REAL DEFAULT 0,         
            s_learning_innov REAL DEFAULT 0,     
            s_performance REAL DEFAULT 0,        
            s_responsibility REAL DEFAULT 0,     
            s_style_image REAL DEFAULT 0,        
            s_integrity REAL DEFAULT 0,          
            
            total_score REAL DEFAULT 0,          
            
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    print("数据库初始化完成 (包含 personnel_scores)。")
    
    # --------------------------------------------------------
    # 自动 Schema 升级 (Migration) Logic
    # --------------------------------------------------------
    upgrade_schema(cursor)

    conn.commit()
    conn.close()
    print("数据库初始化/升级完成!")

def upgrade_schema(cursor):
    """检测并补全缺失的列 (解决新增功能需删库的问题)"""
    print("正在检查数据库结构更新...")
    
    # helper to check column existence
    def column_exists(table, col_name):
        res = cursor.execute(f"PRAGMA table_info({table})").fetchall()
        for col in res:
            if col[1] == col_name: return True
        return False

    def add_column(table, col_def):
        col_name = col_def.split()[0]
        if not column_exists(table, col_name):
            print(f"  -> 表 {table} 缺少列 {col_name}，正在添加...")
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
            except Exception as e:
                print(f"     更新失败: {e}")

    # 1. department_config 表新增的账号计数列
    dept_cols = [
        "count_college_leader INTEGER DEFAULT 0",
        "count_principal INTEGER DEFAULT 0",
        "count_deputy INTEGER DEFAULT 0",
        "count_other INTEGER DEFAULT 0",
        "count_center_leader INTEGER DEFAULT 0",
        "count_excellent INTEGER DEFAULT 0",
        "count_recommend_principal INTEGER DEFAULT 0",
        "count_recommend_deputy INTEGER DEFAULT 0"
    ]
    for col in dept_cols:
        add_column('department_config', col)
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS democratic_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rater_account TEXT NOT NULL,
            examinee_id INTEGER NOT NULL,
            examinee_name TEXT, -- Added for denormalization
            examinee_role TEXT,
            
            s_political_ability REAL DEFAULT 0,
            s_political_perf REAL DEFAULT 0,
            s_party_build REAL DEFAULT 0,
            s_professionalism REAL DEFAULT 0,
            s_leadership REAL DEFAULT 0,
            s_learning_innov REAL DEFAULT 0,
            s_performance REAL DEFAULT 0,
            s_responsibility REAL DEFAULT 0,
            s_style_image REAL DEFAULT 0,
            s_integrity REAL DEFAULT 0,
            
            total_score REAL DEFAULT 0,
            
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # --------------------------------------------------------
    # 表 11: 民主测评权限配置表 (democratic_rating_config) - V5 New
    # --------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS democratic_rating_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            examinee_role TEXT NOT NULL,  -- 被考核人角色 (列头)
            rater_role TEXT NOT NULL,     -- 考核人角色 (行头)
            is_allowed INTEGER DEFAULT 0, -- 1=允许打分, 0=不允许
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            
            UNIQUE(examinee_role, rater_role)
        )
    ''')

    # --------------------------------------------------------
    # 表 12: 领导班子打分明细表 (team_score_details) - New Snapshot Table
    # --------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS team_score_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dept_name TEXT,             -- 部门名称
            dept_code TEXT,             -- 部门代码
            rater_account TEXT,         -- 打分人账号
            score REAL DEFAULT 0,       -- 得分
            sort_no INTEGER DEFAULT 0,  -- 序号
            
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')


    # --------------------------------------------------------
    # 表 13: 被考核人打分明细表 (democratic_score_details) - New Snapshot
    # --------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS democratic_score_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sort_no INTEGER,            -- 序号
            name TEXT,                  -- 被考核人姓名
            dept_name TEXT,             -- 部门名称
            dept_code TEXT,             -- 部门代码
            score REAL DEFAULT 0,       -- 得分
            rater_account TEXT,         -- 打分人账号
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')


    # 2. middle_managers 表新增列
    mgr_cols = [
        "dept_code TEXT",
        "tenure_time TEXT",
        "is_newly_promoted TEXT"
    ]
    for col in mgr_cols:
        add_column('middle_managers', col)
        
    # 3. democratic_scores 新增 examinee_name
    add_column('democratic_scores', 'examinee_name TEXT')
    
    # --------------------------------------------------------
    # 表 14: 院领导权重配置表 (leader_weight_config) - New
    # --------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leader_weight_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dept_code TEXT NOT NULL UNIQUE,
            dept_name TEXT,
            total_weight REAL DEFAULT 50,   -- 院领导占总比例
            w_yang_weisheng REAL DEFAULT 0, -- 杨卫胜
            w_wang_ling REAL DEFAULT 0,     -- 王凌
            w_xu_qingchun REAL DEFAULT 0,   -- 许青春
            w_zhao_tong REAL DEFAULT 0,     -- 赵彤
            w_ge_shaohui REAL DEFAULT 0,    -- 葛少辉
            w_liu_chaowei REAL DEFAULT 0,   -- 刘超伟
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # --------------------------------------------------------
    # 表 15: 院领导账号分配表 (leader_account_mapping) - New
    # --------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leader_account_mapping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            leader_key TEXT NOT NULL UNIQUE,  -- yang_weisheng, wang_ling, etc.
            leader_name TEXT,                  -- 杨卫胜, 王凌, etc.
            account TEXT,                      -- 分配的打分账号
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    print("数据库结构检查完毕。")

if __name__ == '__main__':
    init_db()