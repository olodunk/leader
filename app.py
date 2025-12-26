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
        if session.get('admin_role') != 'admin': # Changed key
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def assessment_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('assessor_role') != 'assessor': # Changed key
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
            # Namespace: Admin
            session['admin_role'] = 'admin'
            session['admin_user_id'] = user['id']
            return jsonify({'success': True, 'redirect': url_for('admin_dashboard')})
        return jsonify({'success': False, 'msg': '管理员账号或密码错误'})
        
    else: # assessment
        # Check evaluation_accounts (plain password as per plan/requirements)
        # Fetch Dept Info by joining or separate query
        # Since evaluation_accounts has dept_code, we can join or query again.
        # Let's do a join to get dept_type and dept_name immediately.
        sql = '''
            SELECT a.*, d.dept_type 
            FROM evaluation_accounts a 
            LEFT JOIN department_config d ON a.dept_code = d.dept_code 
            WHERE a.username = ?
        '''
        user = db.execute(sql, (username,)).fetchone()
        
        if user and user['password'] == password:
             session.permanent = True  # Enable timeout
             # Namespace: Assessor
             session['assessor_role'] = 'assessor'
             session['assessor_user_id'] = user['id']
             session['assessor_username'] = user['username']
             session['assessor_dept_name'] = user['dept_name']
             session['assessor_dept_type'] = user['dept_type']
             
             return jsonify({'success': True, 'redirect': url_for('assessment_home')})
        return jsonify({'success': False, 'msg': '测评账号或密码错误'})

@app.route('/api/logout')
def logout():
    logout_type = request.args.get('type') # 'admin' or 'assessment'
    
    if logout_type == 'admin':
        session.pop('admin_role', None)
        session.pop('admin_user_id', None)
        return redirect(url_for('admin_login'))
        
    elif logout_type == 'assessment':
        session.pop('assessor_role', None)
        session.pop('assessor_user_id', None)
        session.pop('assessor_username', None)
        session.pop('assessor_dept_name', None)
        session.pop('assessor_dept_type', None)
        return redirect(url_for('index'))
        
    else:
        # Fallback: Clear all? Or just redirect?
        # Maybe user manually hit /api/logout
        session.clear()
        return redirect(url_for('index'))

# ==========================================
# 4. 页面路由 (View Routes)
# ==========================================

@app.route('/')
def index():
    """测评登录页 (Root)"""
    if session.get('assessor_role') == 'assessor':
        return redirect(url_for('assessment_home'))
    return render_template('login_assessment.html')

@app.route('/assessment/home')
def assessment_home():
    """测评打分首页"""
    if session.get('assessor_role') != 'assessor':
        return redirect(url_for('index'))
    return render_template('assessment_home.html')

@app.route('/assessment/team-evaluation')
def assessment_team():
    """领导班子综合考核评价"""
    if session.get('assessor_role') != 'assessor':
        return redirect(url_for('index'))
        
    # Access Control: Exclude '院领导'
    if session.get('assessor_dept_type') == '院领导':
        return "您的账号无权访问此页面", 403

    # Fetch existing scores if any
    db = get_db()
    rater_account = session.get('assessor_username')
    
    # We need target_dept_code to look up. 
    # Fetch it from evaluation_accounts associated with this user.
    user_row = db.execute('SELECT dept_code, dept_name FROM evaluation_accounts WHERE username=?', (rater_account,)).fetchone()
    
    existing_scores = None
    if user_row:
        target_dept_code = user_row['dept_code']
        # Query team_scores
        row = db.execute('SELECT * FROM team_scores WHERE rater_account = ? AND target_dept_code = ? ORDER BY id DESC LIMIT 1', 
                         (rater_account, target_dept_code)).fetchone()
        if row:
            existing_scores = dict(row)

    return render_template('assessment_team.html', existing_scores=existing_scores)

@app.route('/admin/login')
def admin_login():
    """管理员登录页"""
    if session.get('admin_role') == 'admin':
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
        '院领导': 50, '职能部门正职 (含院长助理)': 0, '职能部门副职': 0, '职能部门其他员工': 30, '研究所正职': 10, '中心领导班子 (正职)': 10
    },
    '职能部门副职': {
        '院领导': 50, '职能部门正职 (含院长助理)': 0, '职能部门副职': 0, '职能部门其他员工': 30
    },
    '研究所正职': {
        '院领导': 50, '职能部门正职 (含院长助理)': 20, '研究所正职': 0, '研究所副职': 0, '研究所其他员工': 30
    },
    '研究所副职': {
        '院领导': 50, '研究所正职': 0, '研究所副职': 0, '研究所其他员工': 30
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
    '院领导', '职能部门正职 (含院长助理)', '职能部门副职', '职能部门其他员工',
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

# ==========================================
# 映射配置：打分角色 (Rater Role) -> 账号规则
# 逻辑：Role -> [Rule1, Rule2, ...] (Satisfy ANY rule)
# ==========================================
# Rater Rules: Map (Department Type + Account Type) -> Rater Role
# Account Types: L=Leader(院领导), P=Principal(正职), D=Deputy(副职), E=Employee(员工), S=StaffRep(职工代表)
# Note: DB might store Chinese '院领导', '正职', '副职', '员工', '职工代表'
RATER_RULES = {
    # 1. 院领导
    '院领导': [
        {'dept_names': ['院领导'], 'types': ['L', '院领导']}
    ],
    
    # 2. 职能部门正职 (含院长助理)
    '职能部门正职 (含院长助理)': [
        {'dept_type': '职能部门', 'types': ['P', '正职']},
        {'dept_names': ['院长助理'], 'dept_codes': ['A0'], 'types': []} 
    ],
    
    # 3. 职能部门副职
    '职能部门副职': [
        {'dept_type': '职能部门', 'types': ['D', '副职']}
    ],
    
    # 4. 职能部门其他员工
    '职能部门其他员工': [], # Handled dynamically in get_user_rater_roles
    
    # 5-7. 研究所
    '研究所正职': [{'dept_type': '研究所', 'types': ['P', '正职']}],
    '研究所副职': [{'dept_type': '研究所', 'types': ['D', '副职']}],
    '研究所其他员工': [{'dept_type': '研究所', 'types': ['E', '员工']}],
    
    # 8-9. 两中心
    '中心领导班子 (正职)': [{'dept_type': '两中心', 'types': ['P', '正职']}],
    '中心领导班子 (副职)': [{'dept_type': '两中心', 'types': ['D', '副职']}],
    
    # 10-11. 昆冈
    '昆冈班子正职': [{'dept_type': '昆冈', 'types': ['P', '正职']}],
    '昆冈班子副职': [{'dept_type': '昆冈', 'types': ['D', '副职']}],
    
    # 12-13. 分公司 (兰州/抚顺)
    '所属分公司班子正职': [{'dept_names': ['兰州分公司', '抚顺分公司'], 'types': ['P', '正职']}],
    '所属分公司班子副职': [{'dept_names': ['兰州分公司', '抚顺分公司'], 'types': ['D', '副职']}],
    
    # 14-19. 职工代表
    '职工代表中基层领导人员 (两中心)': [{'dept_type': '两中心', 'types': ['C', '职工代表']}], 
    '其他职工代表 (两中心)': [{'dept_type': '两中心', 'types': ['E', '员工']}], # Usually E in Center
    
    '职工代表中基层领导人员 (昆冈北京)': [{'dept_names': ['昆冈北京'], 'types': ['C', '职工代表']}],
    '其他职工代表 (昆冈北京)': [{'dept_names': ['昆冈北京'], 'types': ['E', '员工']}],
    
    '职工代表中基层领导人员 (分公司)': [{'dept_names': ['兰州分公司', '抚顺分公司'], 'types': ['C', '职工代表']}],
    '其他职工代表 (分公司)': [{'dept_names': ['兰州分公司', '抚顺分公司'], 'types': ['E', '员工']}]
}

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

def get_user_rater_roles(user_account, user_dept_info):
    """
    根据用户账号信息(类型)和部门信息，返回该用户对应的 Rater Roles (List)
    user_account: dict {'account_type': 'P', ...}
    user_dept_info: dict {'dept_name': '...', 'dept_type': '...', 'dept_code': '...'}
    """
    matched_roles = []
    
    acc_type = user_account.get('account_type', '')
    d_name = user_dept_info.get('dept_name', '')
    d_type = user_dept_info.get('dept_type', '')
    d_code = user_dept_info.get('dept_code', '') # Add dept_code support
    
    for rater_role, rules_list in RATER_RULES.items():
        # Special handling for '职能部门其他员工'
        if rater_role == '职能部门其他员工':
             # E类账号 / 员工 才有可能是职能部门其他员工
             # Logic: If Type is E or '员工' AND Dept Type is Functional -> Match.
             if (acc_type == 'E' or acc_type == '员工') and d_type == '职能部门':
                 matched_roles.append(rater_role)
             continue
             
        role_matched = False
        for rule in rules_list:
            # 1. Check Types
            # If rule specifies types, acc_type MUST be in it.
            if 'types' in rule and rule['types']:
                if acc_type not in rule['types']:
                    continue

            # 2. Check Dept (Name or Type or Code)
            # Default to False if any constraint is present
            match_dept = True 
            
            # Constraint A: Dept Type
            if 'dept_type' in rule:
                if d_type != rule['dept_type']:
                    match_dept = False
            
            # Constraint B: Dept Name
            if 'dept_names' in rule:
                if d_name not in rule['dept_names']:
                    match_dept = False

            # Constraint C: Dept Code (Allow override if matches?)
            # Logic: If Code matches, we consider it a specific override even if Name differs (encoding).
            # But if Code is WRONG, we fail.
            if 'dept_codes' in rule:
                 if d_code in rule['dept_codes']:
                     match_dept = True # Explicit Code Match -> Force True (overriding potential name mismatch)
                 else:
                     match_dept = False
            
            # Special case for A0: 
            # If rule has dept_codes=['A0'], and d_code is A0 -> Match.
            # My logic above handles it: if d_code matches, match_dept=True.
            
            # Wait, if I have multiple constraints (Type + Name), they act as AND.
            # But 'dept_codes' I added as an OR/Override for Name?
            # Let's simplify: 
            # IF rule has `dept_codes`, use it.
            # ELIF rule has `dept_names`, use it.
            # ELIF rule has `dept_type`, use it.
            # (Priority Order)
            
            match_dept = False
            if 'dept_codes' in rule and d_code in rule['dept_codes']:
                match_dept = True
            elif 'dept_names' in rule and d_name in rule['dept_names']:
                match_dept = True
            elif 'dept_type' in rule and d_type == rule['dept_type']:
                match_dept = True
            
            # If validated
            if match_dept:
                role_matched = True
                break
        
        if role_matched:
            matched_roles.append(rater_role)
            
    return matched_roles


def get_examinee_role_key(person_role, dept_name):
    """
    根据中层人员的“角色”和“部门”，识别其对应的权重表列头 (Column Header)
    """
    # 1. 直接匹配基础角色
    if person_role in ['院长助理', '职能部门正职', '职能部门副职', '研究所正职', '研究所副职']:
        return person_role
        
    # 2. 复合角色：两中心 (兰州/大庆)
    if '中心' in person_role: # 中心正职 / 中心副职
        if dept_name in ['兰州化工研究中心', '大庆化工研究中心']:
            if '正职' in person_role: return '两中心正职'
            if '副职' in person_role: return '两中心副职'
            
        # 3. 复合角色：昆冈 (北京)
        if dept_name == '昆冈公司':
            if '副职' in person_role: return '昆冈班子副职 (北京)'
            
        # 4. 复合角色：分公司 (兰州/抚顺)
        # 注意：这里包括 “昆冈兰州分公司” 和 “昆冈抚顺分公司”
        if dept_name in ['昆冈兰州分公司', '昆冈抚顺分公司']:
            if '正职' in person_role: return '所属分公司 (兰州、抚顺) 班子正职'
            if '副职' in person_role: return '所属分公司 (兰州、抚顺) 班子副职'
            
    return None

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
        # Temporary dict to enforce consistency before saving
        # Key: (Examinee, Rater) -> Weight
        pending_changes = {}
        
        for item in req.get('data', []):
            pending_changes[(item['examinee'], item['rater'])] = float(item['weight'])
            
        # ---------------------------------------------------------
        # 特殊权重逻辑校验 (Special Weight Logic)
        # 场景：职能部门正职考被核时，中心正职 与 分公司正职 权重需保持一致
        # ---------------------------------------------------------
        target_col = '职能部门正职 (含院长助理)' # Wait, Header name is '职能部门正职 (含院长助理)' ?? No, Examinee Header is '职能部门正职' (Column)
        # Check COL_HEADERS definition: '职能部门正职'
        
        # Define the shared group: (Column, [Row1, Row2])
        # Column: '职能部门正职' (Examinee)
        # Rows: '中心领导班子 (正职)', '所属分公司班子正职'
        
        shared_col = '职能部门正职'
        row_a = '中心领导班子 (正职)'
        row_b = '所属分公司班子正职'
        
        if (shared_col, row_a) in pending_changes and (shared_col, row_b) in pending_changes:
             val_a = pending_changes[(shared_col, row_a)]
             val_b = pending_changes[(shared_col, row_b)]
             
             # If mismatch, force them to be the same? Or error?
             # Strategy: Use the value from the UI (assuming UI binds them). 
             # But if malicious/buggy, just force consistency (e.g. use A).
             if val_a != val_b:
                 # Warning: inconsistency detected, syncing B to A
                 pending_changes[(shared_col, row_b)] = val_a
                 
        # Convert back to list for DB update
        for (exam, rater), weight in pending_changes.items():
            updates.append((weight, exam, rater))
            
        db.executemany('UPDATE weight_config_dept SET weight = ? WHERE examinee_role = ? AND rater_role = ?', updates)
        db.commit()
        return jsonify({'success': True, 'msg': '保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

# ==========================================
# 10. API: 部门权重配置
# ==========================================

# ... (Previous Code)

# ==========================================
# 11. API: 领导班子打分提交 (New)
# ==========================================

TEAM_SCORE_WEIGHTS = {
    's_political_resp': 10,
    's_social_resp': 5,
    's_manage_benefit': 10,
    's_manage_effic': 10,
    's_risk_control': 10,
    's_tech_innov': 10,
    's_deep_reform': 10,
    's_talent_strength': 10,
    's_party_build': 7.5,
    's_party_conduct': 7.5,
    's_unity': 5,
    's_mass_ties': 5
}

@app.route('/api/assessment/team/submit', methods=['POST'])
def submit_team_score():
    if session.get('assessor_role') != 'assessor':
        return jsonify({'success': False, 'msg': '未登录'})

    req = request.json
    scores_dict = req.get('scores', {})
    
    # 1. Backend Validation
    all_ten = True
    total_score = 0
    
    try:
        rater_account = session.get('assessor_username')
        db = get_db()
        
        user_row = db.execute('SELECT dept_code FROM evaluation_accounts WHERE username=?', (rater_account,)).fetchone()
        if not user_row: return jsonify({'success': False, 'msg': '账号异常'})
        target_dept_code = user_row['dept_code']
        
        cols = []
        vals = []
        update_clauses = []
        update_vals = []
        
        for key, weight in TEAM_SCORE_WEIGHTS.items():
            raw_val = float(scores_dict.get(key, 0))
            
            # Integer Check
            if not raw_val.is_integer() or raw_val < 0 or raw_val > 10:
                return jsonify({'success': False, 'msg': f'分数必须为0-10整数: {key}'})
                
            if raw_val != 10: all_ten = False
            
            # Calculate Weighted Score
            weighted_val = raw_val * (weight / 10.0)
            total_score += weighted_val
            
            cols.append(key)
            vals.append(raw_val)
            update_clauses.append(f"{key} = ?")
            update_vals.append(raw_val)
            
        if all_ten:
            return jsonify({'success': False, 'msg': '无效评分：不能全为10分'})
            
        # Check if exists
        exist_row = db.execute('SELECT id FROM team_scores WHERE rater_account=? AND target_dept_code=?', 
                               (rater_account, target_dept_code)).fetchone()
        
        if exist_row:
            # UPDATE
            update_clauses.append("total_score = ?")
            update_vals.append(total_score)
            update_vals.append(exist_row['id']) # WHERE id = ?
            
            sql = f"UPDATE team_scores SET {', '.join(update_clauses)} WHERE id = ?"
            db.execute(sql, update_vals)
        else:
            # INSERT
            cols += ['rater_account', 'target_dept_code', 'total_score']
            vals += [rater_account, target_dept_code, total_score]
            
            q_marks = ', '.join(['?'] * len(cols))
            col_names = ', '.join(cols)
            db.execute(f'INSERT INTO team_scores ({col_names}) VALUES ({q_marks})', vals)
        
        # Update Account Status to "Submitted" ("否")
        db.execute('UPDATE evaluation_accounts SET status = "否" WHERE username = ?', (rater_account,))
        
        db.commit()
        
        return jsonify({'success': True, 'msg': '提交成功'})
        
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

# ==========================================
# 12. API: 领导人员综合考核评价 (New)
# ==========================================

PERSONNEL_WEIGHTS = {
    's_political_ability': 10,
    's_political_perf': 10,
    's_party_build': 10,
    's_professionalism': 10,
    's_leadership': 10,
    's_learning_innov': 10,
    's_performance': 10,
    's_responsibility': 10,
    's_style_image': 10,
    's_integrity': 10
}

@app.route('/assessment/personnel-evaluation')
def assessment_personnel():
    """领导人员综合考核评价"""
    if session.get('assessor_role') != 'assessor':
        return redirect(url_for('index'))
        
    rater_account = session.get('assessor_username')
    db = get_db()
    
    # 1. Get Dept Info
    user_row = db.execute('''
        SELECT a.dept_code, d.count_excellent, d.dept_name
        FROM evaluation_accounts a
        LEFT JOIN department_config d ON a.dept_code = d.dept_code
        WHERE a.username=?
    ''', (rater_account,)).fetchone()
    
    if not user_row:
        return "账号信息异常", 403
        
    dept_code = user_row['dept_code']
    count_excellent = user_row['count_excellent'] or 0
    dept_name = user_row['dept_name']
    
    # Requirement: "可被评为优秀人数不为0"
    if count_excellent <= 0:
        return render_template('assessment_error.html', msg="该部门无优秀评选名额，无需进行此项考核。")

    # 2. Get Examinees (Principals & Deputies of this Dept)
    managers = db.execute('SELECT * FROM middle_managers WHERE dept_code=? ORDER BY sort_no ASC', (dept_code,)).fetchall()
    
    # 3. Get Existing Scores
    existing_rows = db.execute('SELECT * FROM personnel_scores WHERE rater_account=? AND target_dept_code=?', 
                              (rater_account, dept_code)).fetchall()
    
    scores_map = {}
    for r in existing_rows:
        scores_map[r['examinee_id']] = dict(r)
        
    return render_template('assessment_personnel.html', 
                           managers=managers, 
                           count_excellent=count_excellent,
                           scores_map=scores_map,
                           dept_name=dept_name)

@app.route('/api/assessment/personnel/submit', methods=['POST'])
def submit_personnel_score():
    if session.get('assessor_role') != 'assessor':
        return jsonify({'success': False, 'msg': '未登录'})

    req = request.json
    scores_list = req.get('data', [])
    if not scores_list:
        return jsonify({'success': False, 'msg': '无提交数据'})

    rater_account = session.get('assessor_username')
    db = get_db()
    
    # Verify Dept & Excellent Count Limit
    user_row = db.execute('''
        SELECT a.dept_code, d.count_excellent 
        FROM evaluation_accounts a
        LEFT JOIN department_config d ON a.dept_code = d.dept_code
        WHERE a.username=?
    ''', (rater_account,)).fetchone()
    
    if not user_row: return jsonify({'success': False, 'msg': '账号异常'})
    
    dept_code = user_row['dept_code']
    limit_excellent = user_row['count_excellent'] or 0
    
    # ---------------------------
    # Validation Logic
    # ---------------------------
    count_selected_excellent = 0
    
    for item in scores_list:
        name = item.get('name', '某人')
        pid = item.get('id')
        grade = item.get('grade') # 优秀/称职/基本称职/不称职
        
        # Count Excellent
        if grade == '优秀':
            count_selected_excellent += 1
            
        # Check Scores
        scores = item.get('scores', {})
        ten_count = 0
        all_below_eight = True
        
        # We need validation per person
        for k in PERSONNEL_WEIGHTS.keys():
            val = float(scores.get(k, 0))
            if not val.is_integer() or val < 0 or val > 10:
                return jsonify({'success': False, 'msg': f'{name}: 分数必须为0-10整数'})
            
            if val == 10: ten_count += 1
            if val >= 8: all_below_eight = False
            
        # Rule: 称职 -> 10分数量 <= 6
        if grade == '称职' and ten_count > 6:
            return jsonify({'success': False, 'msg': f'{name}: 评价为“称职”时，10分项不能超过6个'})
            
        # Rule: 基本称职 -> 不能有10分
        if grade == '基本称职' and ten_count > 0:
            return jsonify({'success': False, 'msg': f'{name}: 评价为“基本称职”时，不能有10分项'})
            
        # Rule: 不称职 -> 全部分数 < 8
        if grade == '不称职' and not all_below_eight:
            return jsonify({'success': False, 'msg': f'{name}: 评价为“不称职”时，各项评分需在8分以下'})

    # Excellent Limit Check
    if count_selected_excellent > limit_excellent:
        return jsonify({'success': False, 'msg': f'评价为“优秀”的人数不能超过 {limit_excellent} 人 (当前 {count_selected_excellent} 人)'})

    # ---------------------------
    # Save to DB (UPSERT)
    # ---------------------------
    try:
        cur = db.cursor()
        for item in scores_list:
            examinee_id = item.get('id')
            grade = item.get('grade')
            scores = item.get('scores', {})
            
            # Calculate Total
            total = 0
            for k, w in PERSONNEL_WEIGHTS.items():
                val = float(scores.get(k, 0))
                total += val * (w / 10.0) 
                
            # Check exist
            exist = cur.execute('SELECT id FROM personnel_scores WHERE rater_account=? AND examinee_id=?', 
                                (rater_account, examinee_id)).fetchone()
                                
            score_cols = list(PERSONNEL_WEIGHTS.keys())
            score_vals = [float(scores.get(k, 0)) for k in score_cols]
            
            if exist:
                # Update
                set_clause = ', '.join([f"{k}=?" for k in score_cols])
                set_clause += ", evaluation_grade=?, total_score=?, updated_at=CURRENT_TIMESTAMP"
                params = score_vals + [grade, total, exist['id']]
                cur.execute(f'UPDATE personnel_scores SET {set_clause} WHERE id=?', params)
            else:
                # Insert
                cols = ['rater_account', 'target_dept_code', 'examinee_id', 'examinee_name', 'evaluation_grade', 'total_score'] + score_cols
                q = ', '.join(['?'] * len(cols))
                vals = [rater_account, dept_code, examinee_id, item.get('name'), grade, total] + score_vals
                cur.execute(f'INSERT INTO personnel_scores ({", ".join(cols)}) VALUES ({q})', vals)

        db.commit()
        return jsonify({'success': True, 'msg': '提交成功'})
        
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'msg': str(e)})

# Special Headers for Democratic Config (Splitting Principal and Assistant)
DEMOCRATIC_ROW_HEADERS = [
    '院领导', 
    '院长助理', '职能部门正职', # Split here
    '职能部门副职', '职能部门其他员工',
    '研究所正职', '研究所副职', '研究所其他员工',
    '中心领导班子 (正职)', '中心领导班子 (副职)',
    '昆冈班子正职', '昆冈班子副职',
    '所属分公司班子正职', '所属分公司班子副职',
    '职工代表中基层领导人员 (两中心)', '其他职工代表 (两中心)',
    '职工代表中基层领导人员 (昆冈北京)', '其他职工代表 (昆冈北京)',
    '职工代表中基层领导人员 (分公司)', '其他职工代表 (分公司)'
]

@app.route('/admin/democratic-config')
@admin_required
def democratic_config():
    """中层干部测评打分对应配置页面"""
    db = get_db()
    
    # Check if we need to migrate the combined role to split roles
    # Check if '职能部门正职 (含院长助理)' exists in table
    combined_check = db.execute("SELECT count(*) FROM democratic_rating_config WHERE rater_role='职能部门正职 (含院长助理)'").fetchone()[0]
    if combined_check > 0:
        # Perform Migration: Copy permissions to new roles and delete old
        old_rows = db.execute("SELECT * FROM democratic_rating_config WHERE rater_role='职能部门正职 (含院长助理)'").fetchall()
        for row in old_rows:
            # Insert for Assistant
            db.execute("INSERT OR IGNORE INTO democratic_rating_config (examinee_role, rater_role, is_allowed) VALUES (?, ?, ?)", 
                       (row['examinee_role'], '院长助理', row['is_allowed']))
            # Insert for Functional Principal
            db.execute("INSERT OR IGNORE INTO democratic_rating_config (examinee_role, rater_role, is_allowed) VALUES (?, ?, ?)", 
                       (row['examinee_role'], '职能部门正职', row['is_allowed']))
        
        # Delete old
        db.execute("DELETE FROM democratic_rating_config WHERE rater_role='职能部门正职 (含院长助理)'")
        db.commit()
    
    # Ensure initialized (Robustness)
    cnt = db.execute('SELECT count(*) FROM democratic_rating_config').fetchone()[0]
    if cnt == 0:
        from init_democratic_config import init_democratic_config
        init_democratic_config()
        # Re-run migration logic if init script inserted the old combined key (it likely did if it uses ROW_HEADERS)
        # But for now let's assume valid state or user saves.
    
    # Query all configs
    rows = db.execute('SELECT * FROM democratic_rating_config').fetchall()
    
    # Transform to matrix dict: config_map[examinee][rater] = is_allowed (1/0)
    config_map = {}
    for r in rows:
        if r['examinee_role'] not in config_map:
            config_map[r['examinee_role']] = {}
        config_map[r['examinee_role']][r['rater_role']] = r['is_allowed']
        
    return render_template('democratic_config.html', 
                           col_headers=COL_HEADERS, 
                           row_headers=DEMOCRATIC_ROW_HEADERS, 
                           config_map=config_map)

@app.route('/api/admin/democratic-config', methods=['POST'])
@admin_required
def save_democratic_config():
    """保存打分对应配置"""
    data = request.json
    updates = data.get('updates', [])
    
    if not updates:
        return jsonify({'success': True, 'msg': '无变更'})
        
    db = get_db()
    try:
        for item in updates:
            db.execute('''
                INSERT INTO democratic_rating_config (examinee_role, rater_role, is_allowed, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(examinee_role, rater_role) DO UPDATE SET
                is_allowed=excluded.is_allowed,
                updated_at=CURRENT_TIMESTAMP
            ''', (item['examinee_role'], item['rater_role'], int(item['is_allowed'])))
            
        db.commit()
        return jsonify({'success': True, 'msg': '保存成功'})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'msg': str(e)}), 500

# ==========================================
# 4.3 民主测评 (Project 3)
# ==========================================

# ==========================================
# 4.3 民主测评 (Project 3)
# ==========================================

def get_democratic_nav(user_row):
    """
    Helper to calculate available democratic evaluation groups for the sidebar.
    Returns: list of dict {'key': '...', 'title': '...', 'active': bool}
    """
    if not user_row: return []
    
    db = get_db()
    rater_account = user_row['username']
    rater_dept_code = user_row['dept_code']
    
    # User Info Dict
    user_info = {
        'account_type': user_row['account_type'],
        'dept_type': user_row['dept_type'],
        'dept_name': user_row['dept_name'],
        'dept_code': user_row['dept_code']
    }
    
    # 1. Get My Roles
    raw_roles = get_user_rater_roles(user_info, user_info)
    if not raw_roles: return []
    
    # Project 3 Specific Role Refinement (Split Combined Role)
    my_rater_roles = []
    for r in raw_roles:
        if r == '职能部门正职 (含院长助理)':
            # Determine specific identity
            if user_info['dept_name'] == '院长助理' or user_info['dept_code'] == 'A0':
                my_rater_roles.append('院长助理')
            else:
                my_rater_roles.append('职能部门正职')
        else:
            my_rater_roles.append(r)
    
    # 2. Get Whitelist Roles (Allowed Examinee Roles)
    # [V5 Update] Use democratic_rating_config instead of weight > 0
    placeholders = ','.join(['?'] * len(my_rater_roles))
    query = f'''
        SELECT DISTINCT examinee_role 
        FROM democratic_rating_config 
        WHERE rater_role IN ({placeholders}) AND is_allowed = 1
    '''
    allowed_roles = [r[0] for r in db.execute(query, my_rater_roles).fetchall()]
    if not allowed_roles: return []
    
    # 3. Define Universe of Groups
    # Order matters for display
    # Titles updated per user request (V4)
    all_groups = [
        {'key': 'assistant', 'title': '院长助理', 'roles': ['院长助理']},
        {'key': 'functional', 'title': '职能部门与直属机构中级管理人员', 'roles': ['职能部门正职', '职能部门副职']},
        {'key': 'institute', 'title': '研究所中级管理人员', 'roles': ['研究所正职', '研究所副职']},
        {'key': 'center_kungang', 'title': '中心及昆冈中级管理人员', 'roles': ['两中心正职', '两中心副职', '昆冈班子副职 (北京)', '所属分公司 (兰州、抚顺) 班子正职', '所属分公司 (兰州、抚顺) 班子副职']},
        {'key': 'kungang_branch', 'title': '昆冈制造分公司中级管理人员', 'roles': ['所属分公司 (兰州、抚顺) 班子正职', '所属分公司 (兰州、抚顺) 班子副职']} 
    ]
    
    # 4. Check Availability & Dynamic Renaming
    is_kungang_rater = any(r in ['昆冈班子正职', '昆冈班子副职', '所属分公司班子正职'] for r in my_rater_roles)
    allowed_set = set(allowed_roles)
    
    available_groups = []
    
    for g in all_groups:
        effective_roles = g['roles'][:] # Copy
        
        # Special Logic: KunGang Rater restrictions
        if is_kungang_rater:
            if g['key'] == 'center_kungang':
                # Filter out Branch roles & Beijing Deputy
                effective_roles = [r for r in effective_roles if '分公司' not in r and r != '昆冈班子副职 (北京)']
            
            if g['key'] == 'kungang_branch':
                 # Standard checks apply
                 pass
        else:
             if g['key'] == 'kungang_branch': continue # Hide
        
        # Identify intersection (What roles can I ACTUALLY rate in this group?)
        my_group_roles = [r for r in effective_roles if r in allowed_set]
        
        if not my_group_roles:
            continue
            
        # Group is available. Now Apply Dynamic Title Logic.
        # Check if purity exists (Only Principals or Only Deputies)
        # Assuming Roles have '正职' or '副职' in their name string
        
        has_principal = any('正职' in r for r in my_group_roles)
        has_deputy = any('副职' in r for r in my_group_roles)
        
        # We modify the title copy for this instance
        display_title = g['title']
        
        # Specific overrides requested by User
        if g['key'] == 'functional':
            if has_principal and not has_deputy:
                display_title = '职能部门与直属机构正职'
            elif has_deputy and not has_principal:
                display_title = '职能部门与直属机构副职'
                
        elif g['key'] == 'institute':
             if has_principal and not has_deputy:
                display_title = '研究所正职'
             elif has_deputy and not has_principal:
                display_title = '研究所副职'
        
        # Add to list with possibly modified title
        g_copy = g.copy()
        g_copy['title'] = display_title
        available_groups.append(g_copy)
        
    return available_groups

@app.context_processor
def inject_democratic_nav():
    """Inject democratic evaluation menu items into all templates"""
    if session.get('assessor_role') != 'assessor':
        return {}
    
    username = session.get('assessor_username')
    # We need user row. To avoid DB hit on every static asset request, maybe cache?
    # For now, just query. SQLite is fast.
    db = get_db()
    user_row = db.execute('SELECT * FROM evaluation_accounts WHERE username=?', (username,)).fetchone()
    # Need dept info too
    if user_row:
        # Join logic manual or simple
        d_row = db.execute('SELECT * FROM department_config WHERE dept_code=?', (user_row['dept_code'],)).fetchone()
        full_row = dict(user_row)
        if d_row: full_row.update(d_row)
        
        nav_items = get_democratic_nav(full_row)
        return {'democratic_nav_items': nav_items}
    
    return {}

@app.route('/assessment/democratic-evaluation/<group_key>')
def assessment_democratic(group_key):
    """中层干部民主测评 (按分组显示)"""
    if session.get('assessor_role') != 'assessor':
        return redirect(url_for('index'))
        
    rater_account = session.get('assessor_username')
    db = get_db()
    
    user_row = db.execute('''
        SELECT a.username, a.dept_code, d.dept_name, d.dept_type, a.account_type
        FROM evaluation_accounts a
        LEFT JOIN department_config d ON a.dept_code = d.dept_code
        WHERE a.username=?
    ''', (rater_account,)).fetchone()
    
    if not user_row: return "无效账号", 403
    
    # 1. Validation: Is this group_key allowed for me?
    nav_items = get_democratic_nav(user_row)
    target_group = next((g for g in nav_items if g['key'] == group_key), None)
    
    if not target_group:
        return render_template('assessment_error.html', msg="无效的测评组或无访问权限")
    
    # 2. Fetch Candidates for THIS group only
    # [V5 Fix]: We must intersect Group Roles with User's Permission (Allowed Roles)
    # Otherwise, even if I can only rate Principals, I see everyone in the group.
    
    # Re-fetch allowed roles for this specific user (logic similar to nav but for this specific group context)
    placeholders = ','.join(['?'] * len(my_rater_roles))
    query = f'''
        SELECT DISTINCT examinee_role 
        FROM democratic_rating_config 
        WHERE rater_role IN ({placeholders}) AND is_allowed = 1
    '''
    allowed_db_roles = [r[0] for r in db.execute(query, my_rater_roles).fetchall()]
    allowed_set = set(allowed_db_roles)
    
    # Intersection
    effective_roles = [r for r in target_group['roles'] if r in allowed_set]
    
    if not effective_roles:
         # Should not happen if they clicked the link, but for safety
         return render_template('assessment_error.html', error_message="没有可评价的人员")
    
    # [Fix for Role Mismatch] Map '两中心...' (Config Key) to '中心...' (DB Value)
    db_roles = []
    for r in effective_roles:
        if r == '两中心正职': db_roles.append('中心正职')
        elif r == '两中心副职': db_roles.append('中心副职')
        else: db_roles.append(r)
        
    ph = ','.join(['?'] * len(db_roles))
    
    # Fetch all candidates in these roles
    mgrs = db.execute(f'SELECT * FROM middle_managers WHERE role IN ({ph}) ORDER BY sort_no ASC', db_roles).fetchall()
    
    full_user_for_roles = dict(user_row) # helper
    my_rater_roles = get_user_rater_roles(full_user_for_roles, full_user_for_roles)
    is_kungang_rater = any(r in ['昆冈班子正职', '昆冈班子副职', '所属分公司班子正职'] for r in my_rater_roles)
    is_college_leader = (user_row['dept_type'] == '院领导')
    
    valid_members = []
    for m in mgrs:
        c_role = m['role']
        c_dept = m['dept_code']
        
        # Exclusion 1: Same Dept (unless Leader)
        if not is_college_leader and c_dept == user_row['dept_code']:
            continue
            
        # Exclusion 2: KunGang Rater -> Exclude KunGang Deputy (Beijing)
        # (Even if role matches group, exclude specific person/role combo)
        if is_kungang_rater and c_role == '昆冈班子副职 (北京)':
            continue
            
        valid_members.append(dict(m))
        
    # 3. Construct Display Group
    # The template expects a list of groups. We provide just one.
    group_data = {
        'title': target_group['title'],
        'members': valid_members
    }
    
    # 4. Scores
    existing_rows = db.execute('SELECT * FROM democratic_scores WHERE rater_account=?', (rater_account,)).fetchall()
    scores_map = {r['examinee_id']: dict(r) for r in existing_rows}
    
    page_title = f"{target_group['title']}测评" # Dynamic title based on group name
    
    return render_template('assessment_democratic.html', 
                           groups=[group_data], # Single group list
                           page_title=page_title,
                           scores_map=scores_map,
                           current_group_key=group_key)


# API: Submit Democratic Scores
@app.route('/api/assessment/democratic/submit', methods=['POST'])
def submit_democratic_score():
    if session.get('assessor_role') != 'assessor':
        return jsonify({'success': False, 'msg': '未登录'})

    req = request.json
    data_list = req.get('data', [])
    if not data_list:
        return jsonify({'success': False, 'msg': '无提交数据'})

    rater_account = session.get('assessor_username')
    db = get_db()
    
    try:
        cur = db.cursor()
        
        # 10 Dimensions
        dims = ['s_political_ability', 's_political_perf', 's_party_build', 's_professionalism', 
                's_leadership', 's_learning_innov', 's_performance', 's_responsibility', 
                's_style_image', 's_integrity']

        for item in data_list:
            examinee_id = item.get('id')
            role = item.get('role') # Passed from frontend for convenience
            scores = item.get('scores', {})
            
            # Validation: Simple range check
            # User didn't specify strict logic for this project like Proj 2 (count limits).
            # Assuming just value inputs 0-10.
            
            score_vals = []
            total = 0
            for d in dims:
                val = float(scores.get(d, 0))
                if val < 0 or val > 10: raise ValueError(f"分数必须在 0-10 之间")
                score_vals.append(val)
                total += val # Simple Sum? Or Weighted? Plan said "Assuming sum"
            
            # Save (UPSERT)
            exist = cur.execute('SELECT id FROM democratic_scores WHERE rater_account=? AND examinee_id=?',
                                (rater_account, examinee_id)).fetchone()
            
            if exist:
                # Update
                set_clause = ', '.join([f"{d}=?" for d in dims])
                set_clause += ", total_score=?, updated_at=CURRENT_TIMESTAMP"
                params = score_vals + [total, exist['id']]
                cur.execute(f'UPDATE democratic_scores SET {set_clause} WHERE id=?', params)
            else:
                # Insert
                cols = ['rater_account', 'examinee_id', 'examinee_role', 'total_score'] + dims
                q = ', '.join(['?'] * len(cols))
                vals = [rater_account, examinee_id, role, total] + score_vals
                cur.execute(f'INSERT INTO democratic_scores ({", ".join(cols)}) VALUES ({q})', vals)
                
        db.commit()
        return jsonify({'success': True, 'msg': '提交成功'})
        
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'msg': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)