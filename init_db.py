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
    # 预置数据
    # --------------------------------------------------------
    # 检查是否已有管理员
    cursor.execute('SELECT count(*) FROM sys_users WHERE username = ?', ('admin',))
    if cursor.fetchone()[0] == 0:
        default_pw = encrypt_password('admin888') 
        cursor.execute('INSERT INTO sys_users (username, password) VALUES (?, ?)', ('admin', default_pw))
        print("已创建默认管理员账号: admin / admin888")

    conn.commit()
    conn.close()
    print("数据库初始化完成! 所有表已就绪。")

if __name__ == '__main__':
    # if os.path.exists(DATABASE): os.remove(DATABASE) # Uncomment to reset
    init_db()