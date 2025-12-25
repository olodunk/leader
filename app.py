import sqlite3
import pandas as pd
import os
import datetime
from io import BytesIO
from flask import Flask, render_template, g, request, jsonify, redirect, url_for, send_file, session
import random
import string
import hashlib
from functools import wraps

from datetime import timedelta

app = Flask(__name__)
# 使用随机密钥：每次重启服务都会导致所有旧 Session 失效（用户需重新登录）
app.secret_key = os.urandom(24)
# 设置 Session 超过 30 分钟无操作自动失效
app.permanent_session_lifetime = timedelta(minutes=30)
DATABASE = 'evaluation.db'

# ==========================================
# 1. 字段映射配置
# ==========================================

DEPT_MAPPING = {
    '排序号': 'sort_no',
    '部门名称': 'dept_name',
    '部门代码': 'dept_code',
    '部门类型': 'dept_type',
    '院领导账号数量': 'count_college_leader',
    '正职账号数据量': 'count_principal',
    '副职账号数量': 'count_deputy',
    '中心基层领导账号数量': 'count_center_leader',
    '其他员工账号数量': 'count_other',
    '可被评为优秀人数': 'count_excellent',
    '推荐正职人数': 'count_recommend_principal',
    '推荐副职人数': 'count_recommend_deputy',
    '部门主管领导': 'leader_main',
    '部门分管领导': 'leader_sub'
}

PERSONNEL_MAPPING = {
    '部门内排序号': 'sort_no',
    '姓名': 'name',
    '性别': 'gender',
    '出生年月': 'birth_date',
    '现任职务': 'position',
    '部门名称': 'dept_name',
    '部门代码': 'dept_code',
    '员工角色': 'role',
    '岗位层级': 'rank_level',
    '任职时间': 'tenure_time',
    '文化程度': 'education',
    '现职级时间': 'rank_time',
    '是否新提拔干部': 'is_newly_promoted'
}

RECOMMEND_PRINCIPAL_MAPPING = {
    '排序号': 'sort_no',
    '姓名': 'name',
    '性别': 'gender',
    '出生年月': 'birth_date',
    '部门名称': 'dept_name',
    '部门代码': 'dept_code',
    '岗位层级': 'rank_level',
    '文化程度': 'education',
    '现职级时间': 'rank_time',
    '现职务': 'current_position'
}

RECOMMEND_DEPUTY_MAPPING = {
    '排序号': 'sort_no',
    '姓名': 'name',
    '性别': 'gender',
    '出生年月': 'birth_date',
    '部门名称': 'dept_name',
    '部门代码': 'dept_code',
    '岗位层级': 'rank_level',
    '文化程度': 'education',
    '现职级时间': 'rank_time',
    '现职务': 'current_position'
}

ALLOWED_ROLES = [
    '院长助理',
    '中心正职',
    '中心副职',
    '中心基层领导',
    '职能部门正职',
    '职能部门副职',
    '研究所正职',
    '研究所副职'
]

# ==========================================
# 2. 数据库连接处理
# ==========================================

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.execute('PRAGMA journal_mode=WAL;')
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# ==========================================
# 3. 权限装饰器 & Auth
# ==========================================

def encrypt_password(password):
    return hashlib.md5(password.encode('utf-8')).hexdigest()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def assessment_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: # Assessor logged in
             return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/login', methods=['POST'])
def login_api():
    req = request.json
    username = req.get('username')
    password = req.get('password')
    login_type = req.get('type') # 'admin' or 'assessment'
    
    db = get_db()
    
    if login_type == 'admin':
        user = db.execute('SELECT * FROM sys_users WHERE username = ?', (username,)).fetchone()
        if user and user['password'] == encrypt_password(password):
            session.permanent = True  # Enable timeout
            session['role'] = 'admin'
            session['user_id'] = user['id']
            return jsonify({'success': True, 'redirect': url_for('admin_dashboard')})
        return jsonify({'success': False, 'msg': '管理员账号或密码错误'})
        
    else: # assessment
        # Check evaluation_accounts (plain password as per plan/requirements)
        user = db.execute('SELECT * FROM evaluation_accounts WHERE username = ?', (username,)).fetchone()
        if user and user['password'] == password:
             session.permanent = True  # Enable timeout
             session['role'] = 'assessor'
             session['user_id'] = user['id']
             session['username'] = user['username']
             return jsonify({'success': True, 'redirect': url_for('assessment_home')})
        return jsonify({'success': False, 'msg': '测评账号或密码错误'})

@app.route('/api/logout')
def logout():
    session.clear()
    return redirect(url_for('admin_login')) # Or index based on where they came from? User said "Click safe exit -> Admin Login"

# ==========================================
# 4. 页面路由 (View Routes)
# ==========================================

@app.route('/')
def index():
    """测评登录页 (Root)"""
    if session.get('role') == 'assessor':
        return redirect(url_for('assessment_home'))
    return render_template('login_assessment.html')

@app.route('/assessment/home')
def assessment_home():
    """测评打分首页 (待完善)"""
    # Simply check session
    if session.get('role') != 'assessor':
        return redirect(url_for('index'))
    return render_template('assessment_home.html')

@app.route('/admin/login')
def admin_login():
    """管理员登录页"""
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    return render_template('login_admin.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """管理后台首页 (原 / )"""
    db = get_db()
    try:
        dept_count = db.execute('SELECT COUNT(*) FROM department_config').fetchone()[0]
    except:
        dept_count = 0
    return render_template('index.html', dept_count=dept_count)

@app.route('/department-config')
@admin_required
def department_config():
    db = get_db()
    depts = db.execute('SELECT * FROM department_config ORDER BY sort_no ASC, serial_no ASC').fetchall()
    return render_template('department_config.html', depts=depts)

@app.route('/personnel-management')
@admin_required
def personnel_management():
    """人员管理页"""
    db = get_db()
    # 【修改点】此处改为按 sort_no (部门内排序号) 升序排列
    managers = db.execute('SELECT * FROM middle_managers ORDER BY sort_no ASC').fetchall()
    return render_template('personnel_management.html', managers=managers)

@app.route('/recommend-principal')
@admin_required
def recommend_principal():
    """正职推荐页"""
    db = get_db()
    data = db.execute('SELECT * FROM recommend_principal ORDER BY sort_no ASC').fetchall()
    return render_template('recommend_principal.html', data=data)

@app.route('/recommend-deputy')
@admin_required
def recommend_deputy():
    """副职推荐页"""
    db = get_db()
    data = db.execute('SELECT * FROM recommend_deputy ORDER BY sort_no ASC').fetchall()
    return render_template('recommend_deputy.html', data=data)

@app.route('/account-generation')
@admin_required
def account_generation():
    """账号生成页"""
    return render_template('account_generation.html')

# ==========================================
# 5. API: 部门配置
# ==========================================

@app.route('/api/department/upload', methods=['POST'])
@admin_required
def upload_department():
    if 'file' not in request.files: return jsonify({'success': False, 'msg': '无文件'})
    file = request.files['file']
    try:
        df = pd.read_excel(file)
        df = df.fillna('')
        if '部门名称' not in df.columns:
            return jsonify({'success': False, 'msg': '缺少"部门名称"列，请检查Excel表头'})

        db = get_db()
        cursor = db.cursor()
        cursor.execute('DELETE FROM department_config')
        for _, row in df.iterrows():
            # Skip invalid rows
            if not str(row.get('部门名称', '')).strip(): continue

            cols, vals = [], []
            for excel_col, db_col in DEPT_MAPPING.items():
                if excel_col in df.columns:
                    cols.append(db_col)
                    val = row[excel_col]
                    if val == '' and ('count_' in db_col or 'no' in db_col): val = 0
                    vals.append(val)
            if cols:
                cursor.execute(f'INSERT INTO department_config ({", ".join(cols)}) VALUES ({", ".join(["?"]*len(cols))})', vals)
        db.commit()
        return jsonify({'success': True, 'msg': f'导入成功: {len(df)} 条'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/department/save', methods=['POST'])
@admin_required
def save_department():
    req = request.json
    if not req or 'data' not in req: return jsonify({'success': False, 'msg': '无数据'})
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute('DELETE FROM department_config')
        for row in req['data']:
            if not row.get('dept_name'): continue
            cols, vals = [], []
            for db_col in DEPT_MAPPING.values():
                cols.append(db_col)
                val = row.get(db_col)
                if val is None or val == '': val = 0 if ('count_' in db_col or 'no' in db_col) else ''
                vals.append(val)
            cursor.execute(f'INSERT INTO department_config ({", ".join(cols)}) VALUES ({", ".join(["?"]*len(cols))})', vals)
        db.commit()
        return jsonify({'success': True, 'msg': '保存成功'})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/department/export')
def export_department():
    try:
        db = get_db()
        df = pd.read_sql_query("SELECT * FROM department_config ORDER BY sort_no ASC, serial_no ASC", db)
        for col in ['id', 'updated_at']:
            if col in df.columns: df = df.drop(columns=[col])
        reverse_map = {v: k for k, v in DEPT_MAPPING.items()}
        df = df.rename(columns=reverse_map)
        df = df[[k for k in DEPT_MAPPING.keys() if k in df.columns]]
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='部门配置')
        output.seek(0)
        return send_file(output, as_attachment=True, download_name='部门配置表.xlsx')
    except Exception as e:
        return str(e)

# ==========================================
# 6. API: 人员管理
# ==========================================

@app.route('/api/personnel/upload', methods=['POST'])
@admin_required
def upload_personnel():
    if 'file' not in request.files: return jsonify({'success': False, 'msg': '无文件'})
    file = request.files['file']
    try:
        df = pd.read_excel(file)
        df = df.fillna('')
        for col in ['出生年月', '现职级时间', '任职时间']:
            if col in df.columns:
                # 统一转为 YYYY/MM 格式
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y/%m').fillna('')
        
        # 校验员工角色
        if '员工角色' in df.columns:
            invalid_roles = df[~df['员工角色'].isin(ALLOWED_ROLES) & (df['员工角色'] != '')]['员工角色'].unique()
            if len(invalid_roles) > 0:
                 return jsonify({'success': False, 'msg': f'发现无效员工角色: {", ".join(invalid_roles)}'})
        
        db = get_db()
        cursor = db.cursor()
        dept_rows = db.execute('SELECT id, dept_name FROM department_config').fetchall()
        dept_map = {row['dept_name']: row['id'] for row in dept_rows}

        cursor.execute('DELETE FROM middle_managers')
        for _, row in df.iterrows():
            cols, vals = [], []
            for excel_col, db_col in PERSONNEL_MAPPING.items():
                if excel_col in df.columns:
                    cols.append(db_col)
                    val = row[excel_col]
                    if val == '' and 'no' in db_col: val = 0
                    vals.append(val)
            if '部门名称' in df.columns and row['部门名称'] in dept_map:
                cols.append('dept_id')
                vals.append(dept_map[row['部门名称']])
            if cols:
                cursor.execute(f'INSERT INTO middle_managers ({", ".join(cols)}) VALUES ({", ".join(["?"]*len(cols))})', vals)
        db.commit()
        return jsonify({'success': True, 'msg': f'导入成功: {len(df)} 人'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/personnel/save', methods=['POST'])
@admin_required
def save_personnel():
    req = request.json
    if not req or 'data' not in req: return jsonify({'success': False, 'msg': '无数据'})
    db = get_db()
    cursor = db.cursor()
    dept_rows = db.execute('SELECT id, dept_name FROM department_config').fetchall()
    dept_map = {row['dept_name']: row['id'] for row in dept_rows}
    try:
        cursor.execute('DELETE FROM middle_managers')
        for row in req['data']:
            if not row.get('name'): continue
            cols, vals = [], []
            for db_col in PERSONNEL_MAPPING.values():
                cols.append(db_col)
                vals.append(row.get(db_col, ''))
            if row.get('dept_name') in dept_map:
                cols.append('dept_id')
                vals.append(dept_map[row.get('dept_name')])
            if row.get('role') and row.get('role') not in ALLOWED_ROLES:
                return jsonify({'success': False, 'msg': f'无效的员工角色: {row.get("role")}'})

            cursor.execute(f'INSERT INTO middle_managers ({", ".join(cols)}) VALUES ({", ".join(["?"]*len(cols))})', vals)
        db.commit()
        return jsonify({'success': True, 'msg': '保存成功'})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/personnel/export')
@admin_required
def export_personnel():
    try:
        db = get_db()
        # 【修改点】此处也改为按 sort_no (部门内排序号) 升序导出
        df = pd.read_sql_query("SELECT * FROM middle_managers ORDER BY sort_no ASC", db)
        for col in ['id', 'dept_id', 'updated_at']:
            if col in df.columns: df = df.drop(columns=[col])
        reverse_map = {v: k for k, v in PERSONNEL_MAPPING.items()}
        df = df.rename(columns=reverse_map)
        df = df[[k for k in PERSONNEL_MAPPING.keys() if k in df.columns]]
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='人员信息')
        output.seek(0)
        return send_file(output, as_attachment=True, download_name='中层干部人员名单.xlsx')
    except Exception as e:
        return str(e)

# ==========================================
# 7. API: 正职推荐
# ==========================================

@app.route('/api/recommend-principal/upload', methods=['POST'])
@admin_required
def upload_recommend_principal():
    if 'file' not in request.files: return jsonify({'success': False, 'msg': '无文件'})
    file = request.files['file']
    try:
        df = pd.read_excel(file)
        df = df.fillna('')
        df.columns = df.columns.str.strip()

        missing = [c for c in ['姓名', '部门名称'] if c not in df.columns]
        if missing:
             return jsonify({'success': False, 'msg': f'缺少必要列: {", ".join(missing)}'})

        for col in ['出生年月', '现职级时间']:
            if col in df.columns:
                 df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y/%m').fillna('')

        db = get_db()
        cursor = db.cursor()
        cursor.execute('DELETE FROM recommend_principal')
        
        for _, row in df.iterrows():
            cols, vals = [], []
            for excel_col, db_col in RECOMMEND_PRINCIPAL_MAPPING.items():
                if excel_col in df.columns:
                    cols.append(db_col)
                    val = row[excel_col]
                    if val == '' and 'no' in db_col: val = 0
                    vals.append(val)
            if cols:
                cursor.execute(f'INSERT INTO recommend_principal ({", ".join(cols)}) VALUES ({", ".join(["?"]*len(cols))})', vals)
        db.commit()
        return jsonify({'success': True, 'msg': f'导入成功: {len(df)} 人'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/recommend-principal/save', methods=['POST'])
@admin_required
def save_recommend_principal():
    req = request.json
    if not req or 'data' not in req: return jsonify({'success': False, 'msg': '无数据'})
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute('DELETE FROM recommend_principal')
        for row in req['data']:
            if not row.get('name'): continue
            cols, vals = [], []
            for db_col in RECOMMEND_PRINCIPAL_MAPPING.values():
                cols.append(db_col)
                vals.append(row.get(db_col, ''))
            cursor.execute(f'INSERT INTO recommend_principal ({", ".join(cols)}) VALUES ({", ".join(["?"]*len(cols))})', vals)
        db.commit()
        return jsonify({'success': True, 'msg': '保存成功'})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/recommend-principal/export')
@admin_required
def export_recommend_principal():
    try:
        db = get_db()
        df = pd.read_sql_query("SELECT * FROM recommend_principal ORDER BY sort_no ASC", db)
        for col in ['id', 'updated_at']:
            if col in df.columns: df = df.drop(columns=[col])
        reverse_map = {v: k for k, v in RECOMMEND_PRINCIPAL_MAPPING.items()}
        df = df.rename(columns=reverse_map)
        df = df[[k for k in RECOMMEND_PRINCIPAL_MAPPING.keys() if k in df.columns]]
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='正职推荐')
        output.seek(0)
        return send_file(output, as_attachment=True, download_name='正职推荐人员名单.xlsx')
    except Exception as e:
        return str(e)

# ==========================================
# 8. API: 副职推荐
# ==========================================

@app.route('/api/recommend-deputy/upload', methods=['POST'])
@admin_required
def upload_recommend_deputy():
    if 'file' not in request.files: return jsonify({'success': False, 'msg': '无文件'})
    file = request.files['file']
    try:
        df = pd.read_excel(file)
        df = df.fillna('')
        df.columns = df.columns.str.strip()

        missing = [c for c in ['姓名', '部门名称'] if c not in df.columns]
        if missing:
             return jsonify({'success': False, 'msg': f'缺少必要列: {", ".join(missing)}'})

        for col in ['出生年月', '现职级时间']:
            if col in df.columns:
                 df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y/%m').fillna('')

        db = get_db()
        cursor = db.cursor()
        cursor.execute('DELETE FROM recommend_deputy')
        
        for _, row in df.iterrows():
            cols, vals = [], []
            for excel_col, db_col in RECOMMEND_DEPUTY_MAPPING.items():
                if excel_col in df.columns:
                    cols.append(db_col)
                    val = row[excel_col]
                    if val == '' and 'no' in db_col: val = 0
                    vals.append(val)
            if cols:
                cursor.execute(f'INSERT INTO recommend_deputy ({", ".join(cols)}) VALUES ({", ".join(["?"]*len(cols))})', vals)
        db.commit()
        return jsonify({'success': True, 'msg': f'导入成功: {len(df)} 人'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/recommend-deputy/save', methods=['POST'])
@admin_required
def save_recommend_deputy():
    req = request.json
    if not req or 'data' not in req: return jsonify({'success': False, 'msg': '无数据'})
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute('DELETE FROM recommend_deputy')
        for row in req['data']:
            if not row.get('name'): continue
            cols, vals = [], []
            for db_col in RECOMMEND_DEPUTY_MAPPING.values():
                cols.append(db_col)
                vals.append(row.get(db_col, ''))
            cursor.execute(f'INSERT INTO recommend_deputy ({", ".join(cols)}) VALUES ({", ".join(["?"]*len(cols))})', vals)
        db.commit()
        return jsonify({'success': True, 'msg': '保存成功'})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/recommend-deputy/export')
@admin_required
def export_recommend_deputy():
    try:
        db = get_db()
        df = pd.read_sql_query("SELECT * FROM recommend_deputy ORDER BY sort_no ASC", db)
        for col in ['id', 'updated_at']:
            if col in df.columns: df = df.drop(columns=[col])
        reverse_map = {v: k for k, v in RECOMMEND_DEPUTY_MAPPING.items()}
        df = df.rename(columns=reverse_map)
        df = df[[k for k in RECOMMEND_DEPUTY_MAPPING.keys() if k in df.columns]]
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='副职推荐')
        output.seek(0)
        return send_file(output, as_attachment=True, download_name='副职推荐人员名单.xlsx')
    except Exception as e:
        return str(e)

# ==========================================
# 9. API: 账号生成
# ==========================================

def generate_password():
    """生成4位数字小写字母混合密码，排除容易混淆的字符 (i, o, 1, l)"""
    chars = 'abcdefghjkmnpqrstuvwxyz234567890' # Excludes i, l, o, 1
    return ''.join(random.choices(chars, k=4))

@app.route('/api/account/generate', methods=['POST'])
@admin_required
def generate_accounts_api():
    try:
        db = get_db()
        cursor = db.cursor()
        
        # 1. 获取部门配置 (仅处理有账号需求的部门)
        depts = db.execute('SELECT * FROM department_config').fetchall()
        if not depts: return jsonify({'success': False, 'msg': '无部门配置数据'})

        # 2. 账号类型映射和前缀
        type_map = [
            # (DB Column, Type Name, Prefix Code)
            ('count_college_leader', '院领导', 'L'),
            ('count_principal', '正职', 'P'),
            ('count_deputy', '副职', 'D'),
            ('count_center_leader', '中心基层领导', 'C'),
            ('count_other', '其他员工', 'E')
        ]
        
        new_accounts = []
        
        # 策略：全量重新生成？还是增量？用户说"一键清空"是单独按钮。
        # 这里实现：检查是否已存在，如果不存在则生成。为避免序号混乱，建议先清空或仅用于初始化。
        # 鉴于序号逻辑 (001, 002)，为了保证连续性，最简单的逻辑是：
        # 对于每个部门+类型，计算需要 N 个。检查已有的 M 个。如果 M < N，生成 N-M 个。
        # Username format: {DeptCode}{TypePrefix}{Seq(3)}
        
        existing_rows = db.execute('SELECT username FROM evaluation_accounts').fetchall()
        existing_usernames = set(r['username'] for r in existing_rows)

        for dept in depts:
            d_code = dept['dept_code']
            if not d_code: continue
            
            for col_count, type_name, prefix in type_map:
                count = dept[col_count]
                if not count or count <= 0: continue
                
                # 尝试生成 Need Count 个账号
                created_count = 0
                for seq in range(1, count + 1):
                    username = f"{d_code}{prefix}{seq:03d}"
                    if username in existing_usernames:
                        continue # Skip existing
                    
                    pw = generate_password()
                    new_accounts.append((dept['dept_name'], d_code, type_name, username, pw))
                    existing_usernames.add(username) # Mark as used

        if new_accounts:
            cursor.executemany('''
                INSERT INTO evaluation_accounts (dept_name, dept_code, account_type, username, password)
                VALUES (?, ?, ?, ?, ?)
            ''', new_accounts)
            db.commit()
            return jsonify({'success': True, 'msg': f'生成成功，新增 {len(new_accounts)} 个账号'})
        else:
            return jsonify({'success': True, 'msg': '无新账号需要生成 (数量已满足配置)'})

    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/account/clear', methods=['POST'])
@admin_required
def clear_accounts_api():
    try:
        db = get_db()
        db.execute('DELETE FROM evaluation_accounts')
        db.commit()
        return jsonify({'success': True, 'msg': '已清空所有生成的账号'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/account/list')
@admin_required
def list_accounts_api():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 30, type=int)
    offset = (page - 1) * limit
    
    # Filters
    f_dept_name = request.args.get('dept_name', '')
    f_type = request.args.get('account_type', '')
    f_dept_code = request.args.get('dept_code', '')
    f_status = request.args.get('status', '')

    db = get_db()
    
    # Base Query
    # We join with department_config to get sort_no.
    # Note: evaluation_accounts stores 'dept_code'. department_config also has 'dept_code'.
    
    where_clauses = []
    params = []
    
    if f_dept_name:
        where_clauses.append("a.dept_name LIKE ?")
        params.append(f"%{f_dept_name}%")
    if f_type:
        where_clauses.append("a.account_type = ?")
        params.append(f_type)
    if f_dept_code:
        where_clauses.append("a.dept_code LIKE ?")
        params.append(f"%{f_dept_code}%")
    if f_status:
        where_clauses.append("a.status = ?")
        params.append(f_status)
        
    where_str = " AND ".join(where_clauses)
    if where_str: where_str = "WHERE " + where_str

    count_sql = f"SELECT count(*) FROM evaluation_accounts a {where_str}"
    data_sql = f'''
        SELECT a.* 
        FROM evaluation_accounts a 
        LEFT JOIN department_config d ON a.dept_code = d.dept_code 
        {where_str}
        ORDER BY d.sort_no ASC, d.serial_no ASC, a.username ASC 
        LIMIT ? OFFSET ?
    '''
    
    total = db.execute(count_sql, params).fetchone()[0]
    rows = db.execute(data_sql, params + [limit, offset]).fetchall()
    
    data = [dict(row) for row in rows]
    return jsonify({'code': 0, 'msg': '', 'count': total, 'data': data})

@app.route('/api/account/save', methods=['POST'])
@admin_required
def save_accounts_api():
    req = request.json
    if not req or 'data' not in req: return jsonify({'success': False, 'msg': '无数据'})
    db = get_db()
    try:
        for row in req['data']:
            if not row.get('id'): continue
            # 仅允许修改 密码 和 状态
            db.execute('UPDATE evaluation_accounts SET password=?, status=? WHERE id=?', (row['password'], row['status'], row['id']))
        db.commit()
        return jsonify({'success': True, 'msg': '保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/account/export')
@admin_required
def export_accounts_api():
    try:
        db = get_db()
        df = pd.read_sql_query("SELECT dept_name, dept_code, account_type, username, password, status FROM evaluation_accounts ORDER BY dept_code ASC, username ASC", db)
        
        # Rename for export validity
        rename_map = {
            'dept_name': '部门名称',
            'dept_code': '部门代码',
            'account_type': '账号类型',
            'username': '账号',
            'password': '密码',
            'status': '状态'
        }
        df = df.rename(columns=rename_map)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='测评账号')
        output.seek(0)
        return send_file(output, as_attachment=True, download_name='测评账号名单.xlsx')
    except Exception as e:
        return str(e)

    except Exception as e:
        return str(e)

# ==========================================
# 10. API: 部门权重配置
# ==========================================

# Default Matrix Configuration
# (Examinee Role -> {Rater Role: Weight})
DEFAULT_DEPT_WEIGHTS = {
    '院长助理': {
        '院领导': 70, '职能部门正职 (含院长助理)': 10, '研究所正职': 10, '中心领导班子 (正职)': 10
    },
    '职能部门正职': {
        '院领导': 50, '职能部门副职': 30, '研究所正职': 10, '中心领导班子 (正职)': 10
    },
    '职能部门副职': {
        '院领导': 50, '职能部门正职 (含院长助理)': 20, '职能部门副职': 30
    },
    '研究所正职': {
        '院领导': 50, '职能部门正职 (含院长助理)': 20, '研究所副职': 30
    },
    '研究所副职': {
        '院领导': 50, '研究所正职': 20, '研究所副职': 30
    },
    '两中心正职': {
        '院领导': 50, '职能部门正职 (含院长助理)': 10, '中心领导班子 (正职)': 10, '职工代表中基层领导人员 (两中心)': 20, '其他职工代表 (两中心)': 10
    },
    '两中心副职': {
        '院领导': 50, '中心领导班子 (正职)': 20, '中心领导班子 (副职)': 10, '职工代表中基层领导人员 (两中心)': 10, '其他职工代表 (两中心)': 10
    },
    '昆冈班子副职 (北京)': {
        '院领导': 20, '职能部门正职 (含院长助理)': 10, '昆冈班子正职': 40, '昆冈班子副职': 10, '所属分公司班子正职': 10, '职工代表中基层领导人员 (昆冈北京)': 10
    },
    '所属分公司 (兰州、抚顺) 班子正职': {
        '院领导': 10, '职能部门正职 (含院长助理)': 10, '昆冈班子正职': 30, '昆冈班子副职': 10, '所属分公司班子副职': 10, '职工代表中基层领导人员 (分公司)': 20, '其他职工代表 (分公司)': 10
    },
    '所属分公司 (兰州、抚顺) 班子副职': {
        '昆冈班子正职': 30, '昆冈班子副职': 10, '所属分公司班子正职': 30, '所属分公司班子副职': 10, '职工代表中基层领导人员 (分公司)': 10, '其他职工代表 (分公司)': 10
    }
}

ROW_HEADERS = [
    '院领导', '职能部门正职 (含院长助理)', '职能部门副职', '本部门其他员工',
    '研究所正职', '研究所副职', '研究所其他员工',
    '中心领导班子 (正职)', '中心领导班子 (副职)',
    '昆冈班子正职', '昆冈班子副职',
    '所属分公司班子正职', '所属分公司班子副职',
    '职工代表中基层领导人员 (两中心)', '其他职工代表 (两中心)',
    '职工代表中基层领导人员 (昆冈北京)', '其他职工代表 (昆冈北京)',
    '职工代表中基层领导人员 (分公司)', '其他职工代表 (分公司)'
]

COL_HEADERS = [
    '院长助理', '职能部门正职', '职能部门副职', 
    '研究所正职', '研究所副职', 
    '两中心正职', '两中心副职', 
    '昆冈班子副职 (北京)', '所属分公司 (兰州、抚顺) 班子正职', '所属分公司 (兰州、抚顺) 班子副职'
]

def init_dept_weights(db):
    """初始化部门权重配置"""
    try:
        # Ensure table exists (Robustness fix)
        db.execute('''
            CREATE TABLE IF NOT EXISTS weight_config_dept (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                examinee_role TEXT NOT NULL,
                rater_role TEXT NOT NULL,
                weight REAL DEFAULT 0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(examinee_role, rater_role)
            )
        ''')

        count = db.execute('SELECT COUNT(*) FROM weight_config_dept').fetchone()[0]
        if count == 0:
            print("初始化部门权重配置数据...")
            data = []
            for col in COL_HEADERS:
                weights = DEFAULT_DEPT_WEIGHTS.get(col, {})
                for row in ROW_HEADERS:
                    val = weights.get(row, 0)
                    data.append((col, row, val))
            
            db.executemany('INSERT INTO weight_config_dept (examinee_role, rater_role, weight) VALUES (?, ?, ?)', data)
            db.commit()
    except Exception as e:
        print(f"Init Weights Failed: {e}")

@app.route('/weight/department')
@admin_required
def weight_config_dept():
    db = get_db()
    init_dept_weights(db) # Ensure valid
    
    rows = db.execute('SELECT * FROM weight_config_dept').fetchall()
    
    # Dictionary {(Examinee, Rater) -> Weight}
    matrix = {}
    for r in rows:
        matrix[(r['examinee_role'], r['rater_role'])] = r['weight']
        
    return render_template('weight_config_dept.html', 
                           matrix=matrix, 
                           row_headers=ROW_HEADERS, 
                           col_headers=COL_HEADERS)

@app.route('/api/weight/dept/save', methods=['POST'])
@admin_required
def save_weight_dept():
    req = request.json
    if not req: return jsonify({'success': False, 'msg': '无数据'})
    
    db = get_db()
    try:
        updates = []
        for item in req.get('data', []):
            updates.append((item['weight'], item['examinee'], item['rater']))
            
        db.executemany('UPDATE weight_config_dept SET weight = ? WHERE examinee_role = ? AND rater_role = ?', updates)
        db.commit()
        return jsonify({'success': True, 'msg': '保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=1111)