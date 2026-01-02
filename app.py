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
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

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
             
             # Check status: if '否', deny login
             if user['status'] == '否':
                  return jsonify({'success': False, 'msg': '您已完成本次测评，无法再次登录'})

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
    """管理后台首页"""
    return render_template('index.html')

@app.route('/api/dashboard/stats')
@admin_required
def dashboard_stats():
    """仪表盘统计数据API"""
    db = get_db()
    try:
        dept_count = db.execute('SELECT COUNT(*) FROM department_config').fetchone()[0]
        examinee_count = db.execute('SELECT COUNT(*) FROM middle_managers').fetchone()[0]
        account_total = db.execute('SELECT COUNT(*) FROM evaluation_accounts').fetchone()[0]
        account_submitted = db.execute("SELECT COUNT(*) FROM evaluation_accounts WHERE status='否'").fetchone()[0]
        
        # 各模块完成人数
        democratic_done = db.execute('SELECT COUNT(DISTINCT rater_account) FROM democratic_scores').fetchone()[0]
        team_done = db.execute('SELECT COUNT(DISTINCT rater_account) FROM team_scores').fetchone()[0]
        rec_principal_done = db.execute('SELECT COUNT(DISTINCT rater_account) FROM recommendation_scores_principal').fetchone()[0]
        rec_deputy_done = db.execute('SELECT COUNT(DISTINCT rater_account) FROM recommendation_scores_deputy').fetchone()[0]
        
        return jsonify({
            'success': True,
            'dept_count': dept_count,
            'examinee_count': examinee_count,
            'account_total': account_total,
            'account_submitted': account_submitted,
            'progress_percent': round(account_submitted / account_total * 100, 1) if account_total > 0 else 0,
            'modules': {
                'democratic': democratic_done,
                'team': team_done,
                'rec_principal': rec_principal_done,
                'rec_deputy': rec_deputy_done
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})



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

        for col in ['出生年月', '现职级时间', '任职时间']:

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
# 6. API: 领导班子打分明细
# ==========================================

@app.route('/team-score-details')
@admin_required
def team_score_details():
    """领导班子打分明细页"""
    return render_template('team_score_details.html')

@app.route('/api/team-score-details/list')
@admin_required
def team_score_details_list():
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 30))
    dept_name = request.args.get('dept_name', '')
    dept_code = request.args.get('dept_code', '')
    
    offset = (page - 1) * limit
    db = get_db()
    
    where = []
    params = []
    
    if dept_name:
        where.append("dept_name LIKE ?")
        params.append(f"%{dept_name}%")
    if dept_code:
        where.append("dept_code LIKE ?")
        params.append(f"%{dept_code}%")
        
    where_clause = "WHERE " + " AND ".join(where) if where else ""
    
    count = db.execute(f'SELECT count(*) FROM team_score_details {where_clause}', params).fetchone()[0]
    data = db.execute(f'SELECT * FROM team_score_details {where_clause} ORDER BY sort_no ASC, id ASC LIMIT ? OFFSET ?', params + [limit, offset]).fetchall()
    
    return jsonify({'count': count, 'data': [dict(row) for row in data]})

@app.route('/api/team-score-details/calculate', methods=['POST'])
@admin_required
def team_score_details_calculate():
    """一键计算：清空原表，从 team_scores 聚合计算并插入 snapshot"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # 1. Fetch Data
        sql = '''
            SELECT 
                d.dept_name, 
                t.target_dept_code as dept_code, 
                t.rater_account, 
                t.total_score as score,
                d.sort_no as dept_sort_no,
                ea.account_type
            FROM team_scores t
            LEFT JOIN department_config d ON t.target_dept_code = d.dept_code
            LEFT JOIN evaluation_accounts ea ON t.rater_account = ea.username
        '''
        df = pd.read_sql_query(sql, db)
        
        # 排除院领导打分记录
        if not df.empty:
            df = df[df['dept_code'] != 'A0'].copy()
            df = df[df['account_type'] != '院领导'].copy()
        
        if df.empty:
            return jsonify({'success': False, 'msg': '无有效评分数据'})

        # 分数保留两位小数
        df['score'] = df['score'].round(2)

        # 2. Sorting Logic
        # Account Type Mapping
        type_order = {
            '院领导': 1,
            '正职': 2,
            '副职': 3,
            '中心基层领导': 4,
            '其他员工': 5
        } # Fallback for unknown: 99
        
        df['type_rank'] = df['account_type'].map(type_order).fillna(99)
        
        # Account Number Extraction (Regex)
        # Extract the trailing numbers from username (e.g. A0L001 -> 001 -> 1)
        # If no number, use 0
        df['account_num'] = df['rater_account'].str.extract(r'(\d+)$').fillna(0).astype(int)
        
        # Sort: Dept sort_no ASC, Type Rank ASC, Account Num ASC
        df.sort_values(by=['dept_sort_no', 'type_rank', 'account_num'], ascending=[True, True, True], inplace=True)
        
        # 3. Generate Serial No (1...N)
        df['sort_no'] = range(1, len(df) + 1)
        
        # 4. Insert into snapshot table
        # Prepare valid columns
        valid_cols = ['dept_name', 'dept_code', 'rater_account', 'score', 'sort_no']
        insert_df = df[valid_cols].copy()
        
        cursor.execute('DELETE FROM team_score_details')
        
        # Bulk Insert
        data_to_insert = insert_df.to_records(index=False).tolist()
        cursor.executemany('''
            INSERT INTO team_score_details (dept_name, dept_code, rater_account, score, sort_no) 
            VALUES (?, ?, ?, ?, ?)
        ''', data_to_insert)
        
        row_count = cursor.rowcount
        db.commit()
        
        return jsonify({'success': True, 'msg': f'计算完成，已生成 {len(data_to_insert)} 条记录'})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/team-score-details/clear', methods=['POST'])
@admin_required
def team_score_details_clear():
    try:
        db = get_db()
        db.execute('DELETE FROM team_score_details')
        db.commit()
        return jsonify({'success': True, 'msg': '已清空打分明细'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/team-score-details/save', methods=['POST'])
@admin_required
def team_score_details_save():
    req = request.json
    if not req or 'data' not in req: return jsonify({'success': False, 'msg': '无数据'})
    
    db = get_db()
    try:
        cursor = db.cursor()
        for item in req['data']:
            cursor.execute('UPDATE team_score_details SET score = ? WHERE id = ?', (item['score'], item['id']))
        db.commit()
        return jsonify({'success': True, 'msg': '保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/team-score-details/export')
@admin_required
def team_score_details_export():
    try:
        db = get_db()
        df = pd.read_sql_query("SELECT sort_no, dept_name, dept_code, score, rater_account FROM team_score_details ORDER BY sort_no ASC, id ASC", db)
        
        # Resize/Rename columns for user friendliness
        df.rename(columns={
            'sort_no': '序号',
            'dept_name': '部门名称',
            'dept_code': '部门代码',
            'score': '得分',
            'rater_account': '打分人账号'
        }, inplace=True)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='领导班子打分明细')
            
        output.seek(0)
        return send_file(output, as_attachment=True, download_name='领导班子打分明细.xlsx')
    except Exception as e:
        return str(e)

# ==========================================
# 4.2 API: 被考核人打分明细 (Democratic Score Details)
# ==========================================

@app.route('/admin/democratic-score-details')
@admin_required
def democratic_score_details():
    """被考核人打分明细页"""
    return render_template('democratic_score_details.html')

@app.route('/api/democratic-score-details/list')
@admin_required
def democratic_score_details_list():
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 30))
    dept_name = request.args.get('dept_name', '')
    dept_code = request.args.get('dept_code', '')
    name = request.args.get('name', '')
    rater_account = request.args.get('rater_account', '')
    
    offset = (page - 1) * limit
    db = get_db()
    
    where = []
    params = []
    
    if dept_name:
        where.append("dept_name LIKE ?")
        params.append(f"%{dept_name}%")
    if dept_code:
        where.append("dept_code LIKE ?")
        params.append(f"%{dept_code}%")
    if name:
        where.append("name LIKE ?")
        params.append(f"%{name}%")
    if rater_account:
        where.append("rater_account LIKE ?")
        params.append(f"%{rater_account}%")
        
    where_clause = "WHERE " + " AND ".join(where) if where else ""
    
    count = db.execute(f'SELECT count(*) FROM democratic_score_details {where_clause}', params).fetchone()[0]
    data = db.execute(f'SELECT * FROM democratic_score_details {where_clause} ORDER BY sort_no ASC, id ASC LIMIT ? OFFSET ?', params + [limit, offset]).fetchall()
    
    return jsonify({'count': count, 'data': [dict(row) for row in data]})

@app.route('/api/democratic-score-details/calculate', methods=['POST'])
@admin_required
def democratic_score_details_calculate():
    """一键计算：合并 democratic_scores 和 personnel_scores"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # 1. Fetch Data from both sources
        sql_democratic = '''
            SELECT 
                d.examinee_name as name,
                m.dept_name,
                m.dept_code,
                d.total_score as score,
                d.rater_account,
                ea.account_type
            FROM democratic_scores d
            JOIN middle_managers m ON d.examinee_id = m.id
            LEFT JOIN evaluation_accounts ea ON d.rater_account = ea.username
        '''
        sql_personnel = '''
            SELECT 
                p.examinee_name as name,
                m.dept_name,
                m.dept_code,
                p.total_score as score,
                p.rater_account,
                ea.account_type
            FROM personnel_scores p
            JOIN middle_managers m ON p.examinee_id = m.id
            LEFT JOIN evaluation_accounts ea ON p.rater_account = ea.username
        '''
        
        df_dem = pd.read_sql_query(sql_democratic, db)
        df_per = pd.read_sql_query(sql_personnel, db)
        
        df = pd.concat([df_dem, df_per], ignore_index=True)
        
        if df.empty:
            return jsonify({'success': False, 'msg': '无评分数据'})

        # 2. Sorting Logic
        type_order = {
            '院领导': 1,
            '正职': 2,
            '副职': 3,
            '中心基层领导': 4,
            '其他员工': 5
        }
        
        df['type_rank'] = df['account_type'].map(type_order).fillna(99)
        df['account_num'] = df['rater_account'].str.extract(r'(\d+)$').fillna(0).astype(int)
        
        # Sort: Examinee Dept Code ASC, Type Rank ASC, Account Num ASC
        df.sort_values(by=['dept_code', 'type_rank', 'account_num'], ascending=[True, True, True], inplace=True)
        
        # 3. Generate Serial No
        df['sort_no'] = range(1, len(df) + 1)
        
        # 4. Insert into snapshot table
        valid_cols = ['sort_no', 'name', 'dept_name', 'dept_code', 'score', 'rater_account']
        insert_df = df[valid_cols].copy()
        
        cursor.execute('DELETE FROM democratic_score_details')
        
        data_to_insert = insert_df.to_records(index=False).tolist()
        cursor.executemany('''
            INSERT INTO democratic_score_details (sort_no, name, dept_name, dept_code, score, rater_account) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', data_to_insert)
        
        db.commit()
        return jsonify({'success': True, 'msg': f'计算完成，已生成 {len(data_to_insert)} 条记录'})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/democratic-score-details/clear', methods=['POST'])
@admin_required
def democratic_score_details_clear():
    try:
        db = get_db()
        db.execute('DELETE FROM democratic_score_details')
        db.commit()
        return jsonify({'success': True, 'msg': '已清空打分明细'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/democratic-score-details/export')
@admin_required
def democratic_score_details_export():
    try:
        db = get_db()
        df = pd.read_sql_query("SELECT sort_no, name, dept_name, dept_code, score, rater_account FROM democratic_score_details ORDER BY sort_no ASC", db)
        
        df.rename(columns={
            'sort_no': '序号',
            'name': '姓名',
            'dept_name': '部门名称',
            'dept_code': '部门代码',
            'score': '得分',
            'rater_account': '打分人账号'
        }, inplace=True)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='被考核人打分明细')
            
        output.seek(0)
        return send_file(output, as_attachment=True, download_name='被考核人打分明细.xlsx')
    except Exception as e:
        return str(e)

@app.route('/api/democratic-score-details/save', methods=['POST'])
@admin_required
def democratic_score_details_save():
    try:
        db = get_db()
        data = request.json.get('data', [])
        if not data:
            return jsonify({'success': False, 'msg': '无更新数据'})
            
        cursor = db.cursor()
        for item in data:
            detail_id = item.get('id')
            score = item.get('score')
            if detail_id is not None and score is not None:
                cursor.execute('UPDATE democratic_score_details SET score=?, updated_at=CURRENT_TIMESTAMP WHERE id=?', (score, detail_id))
        
        db.commit()
        return jsonify({'success': True, 'msg': f'成功保存 {len(data)} 条修改'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})


# ==========================================
# 6.4.5 API: 被考核人汇总得分 (Examinee Score Summary)
# ==========================================

@app.route('/team-score-summary')
@admin_required
def team_score_summary_page():
    return render_template('team_score_summary.html')

@app.route('/admin/examinee-summary')
@admin_required
def examinee_summary_page():
    """被考核人汇总得分页面"""
    return render_template('examinee_summary.html')

@app.route('/api/examinee-summary/list')
@admin_required
def examinee_summary_list():
    """获取汇总得分列表"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 30))
        offset = (page - 1) * limit

        db = get_db()
        count = db.execute('SELECT COUNT(*) FROM examinee_score_summary').fetchone()[0]
        rows = db.execute('SELECT * FROM examinee_score_summary ORDER BY id ASC LIMIT ? OFFSET ?', (limit, offset)).fetchall()
        
        return jsonify({
            'success': True, 
            'count': count,
            'data': [dict(row) for row in rows]
        })
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/examinee-summary/calculate', methods=['POST'])
@admin_required
def examinee_summary_calculate():
    """一键计算被考核人汇总得分 - 支持院长助理和职能部门正职"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # 1. 获取要计算的被考核人
        examinees = db.execute('''
            SELECT id, name, dept_name, role, dept_code FROM middle_managers 
            WHERE role IN ('院长助理', '职能部门正职', '职能部门副职', '研究所正职', '研究所副职', '两中心正职', '中心正职', '中心副职') ORDER BY id ASC
        ''').fetchall()
        
        if not examinees:
            return jsonify({'success': False, 'msg': '没有找到可计算的被考核人'})
        
        # 2. 获取院领导账号映射 (account -> leader_key)
        leader_mappings = db.execute('SELECT leader_key, account FROM leader_account_mapping').fetchall()
        leader_account_map = {m['account']: m['leader_key'] for m in leader_mappings if m['account']}
        
        # 3. 获取所有账号信息
        accounts = db.execute('''
            SELECT ea.username, ea.account_type, ea.dept_code, ea.dept_name, dc.dept_type
            FROM evaluation_accounts ea
            LEFT JOIN department_config dc ON ea.dept_code = dc.dept_code
        ''').fetchall()
        account_info = {(a['username'] or '').strip(): dict(a) for a in accounts if a['username']}
        
        # 4. 获取打分明细数据
        score_details = db.execute('SELECT name, score, rater_account FROM democratic_score_details').fetchall()
        
        # 4.1 获取领导班子打分明细数据 (用于融合计算 - NEW SOURCE)
        # Use team_score_details for granular fusion (Account Type matches)
        tsd_rows = db.execute('SELECT dept_code, rater_account, score FROM team_score_details').fetchall()
        team_details_map = {} # dept_code -> list of {rater_account, score}
        for row in tsd_rows:
            dcode = (row['dept_code'] or '').strip()
            if dcode:
                if dcode not in team_details_map: team_details_map[dcode] = []
                # Rater account key needs to match account_info keys (stripped)
                r_acc = (row['rater_account'] or '').strip()
                team_details_map[dcode].append({'rater_account': r_acc, 'score': row['score']})
        
        # 5. 清空并重新计算
        cursor.execute('DELETE FROM examinee_score_summary')
        
        inserted_count = 0
        for examinee in examinees:
            eid = examinee['id']
            name = examinee['name']
            dept_name = examinee['dept_name']
            role = examinee['role']
            dept_code = examinee['dept_code']
            
            # 过滤：如果是'中心正职'、'两中心正职'或'中心副职'，必须属于两中心或昆冈北京
            if role in ['两中心正职', '中心正职', '中心副职']:
                if dept_name not in ['兰州化工研究中心', '大庆化工研究中心'] and dept_code not in ['U', 'V', 'W']:
                    continue
            
            # 获取院领导权重配置（根据被考核人所属部门）
            # 院长助理 -> dept_code='A1', 职能部门正职 -> 根据dept_name查找
            if role == '院长助理':
                leader_weight_row = db.execute('''
                    SELECT w_yang_weisheng, w_wang_ling, w_xu_qingchun, w_zhao_tong, w_ge_shaohui, w_liu_chaowei
                    FROM leader_weight_config WHERE dept_code = 'A1'
                ''').fetchone()
            else:
                # 职能部门/研究所/两中心/昆冈 - 优先使用dept_code查找，其次根据部门名称查找
                leader_weight_row = None
                if dept_code:
                    leader_weight_row = db.execute('''
                        SELECT w_yang_weisheng, w_wang_ling, w_xu_qingchun, w_zhao_tong, w_ge_shaohui, w_liu_chaowei
                        FROM leader_weight_config WHERE dept_code = ?
                    ''', (dept_code,)).fetchone()
                
                if not leader_weight_row:
                    leader_weight_row = db.execute('''
                        SELECT w_yang_weisheng, w_wang_ling, w_xu_qingchun, w_zhao_tong, w_ge_shaohui, w_liu_chaowei
                        FROM leader_weight_config 
                        WHERE dept_name = ? OR ? LIKE '%' || dept_name || '%' OR dept_name LIKE '%' || ? || '%'
                    ''', (dept_name, dept_name, dept_name)).fetchone()
            
            leader_weights = {}
            if leader_weight_row:
                leader_weights = {
                    'yang_weisheng': leader_weight_row['w_yang_weisheng'] or 0,
                    'wang_ling': leader_weight_row['w_wang_ling'] or 0,
                    'xu_qingchun': leader_weight_row['w_xu_qingchun'] or 0,
                    'zhao_tong': leader_weight_row['w_zhao_tong'] or 0,
                    'ge_shaohui': leader_weight_row['w_ge_shaohui'] or 0,
                    'liu_chaowei': leader_weight_row['w_liu_chaowei'] or 0,
                }
            
            # 获取该被考核人的所有评分 (民主测评)
            examinee_scores_raw = [dict(sd) for sd in score_details if sd['name'] == name]
            
            # --- FUSION REFACTORED (2025-01-02) ---
            # 融合规则：
            # 1. 职能/研究所: P/D/E -> 对应票箱 (影响ABC加权)
            # 2. 两中心: P/D -> P/D列表, C -> 基层列表, E -> 员工列表 (影响各单项及加权)
            # 3. 昆冈: P/D -> 分公司P/D列表, 影响分公司加权; C/E -> 中心库 (影响中心员工/基层分)
            
            should_merge_team_score = False
            if role in ['院长助理', '职能部门正职', '研究所正职', '两中心正职', '中心正职']:
                 should_merge_team_score = True
            
            if should_merge_team_score and dept_code:
                tsd_votes = team_details_map.get(dept_code, []) # Use stripped dept_code
                for tv in tsd_votes:
                    # Construct a vote object behaving like democratic_score_details row
                    # This allows the subsequent logic (lines 1320+) to process it naturally based on rater's role
                    examinee_scores_raw.append({
                        'name': name,
                        'score': tv['score'],
                        'rater_account': tv['rater_account'] # Already stripped above
                    })
            # -----------------------------------------------
            
            # 分组：按考核人类型分类评分
            leader_scores = {}  # {leader_key: [scores]}
            func_principal_scores = []  # 职能部门正职
            func_deputy_scores = []  # 职能部门副职
            func_employee_scores = []  # 职能部门员工
            func_assistant_scores = []  # 院长助理账号
            inst_principal_scores = []  # 研究所正职
            inst_deputy_scores = []  # 研究所副职
            inst_employee_scores = []  # 研究所员工
            center_kungang_scores = []  # 两中心正职 + 昆冈分公司正职 (Principal scores)
            center_kungang_deputy_scores = []  # 两中心副职 + 昆冈分公司副职
            center_grassroots_scores = []  # 两中心基层领导
            center_employee_scores = []  # 两中心其他员工
            
            # 昆冈北京专用列表
            kungang_principal_scores = []      # 昆冈班子正职 (U, V, W)
            kungang_deputy_scores = []         # 昆冈班子副职 (U)
            kungang_beijing_grassroots = []
            kungang_beijing_employees = []
            
            # 分公司 (V, W) 专有列表
            branch_principal_scores = []
            branch_deputy_scores = []
            branch_leadership_pooled_scores = [] # 正职+副职合并用于加权
            branch_grassroots_scores = []
            branch_employee_scores = []
            
            score_college_leader = 0
            score_func_principal = score_func_deputy = score_func_employee = 0
            score_func_abc = score_func_bc = 0
            score_inst_principal = score_inst_deputy = score_inst_employee = 0
            score_inst_abc = score_inst_bc = 0
            score_center_principal = score_center_deputy = score_center_grassroot = score_center_employee = 0
            score_center_kungang = 0
            score_kungang_principal = score_kungang_deputy = score_branch_principal = score_branch_deputy = 0
            score_branch_weighted = 0 # 新增加权字段
            _w_branch_principal = _w_center_grassroot = _w_center_employee = 0
            total_score = 0

            for sd in examinee_scores_raw:
                rater_acc = sd['rater_account']
                score = sd['score'] or 0
                acc = account_info.get(rater_acc, {})
                
                # --- Fallback: Deduce Role from Username if Account Info Missing (2025-01-02) ---
                acc_type = acc.get('account_type', '')
                dept_type = acc.get('dept_type', '')
                acc_dept_name = acc.get('dept_name', '')
                
                if not acc_type or not dept_type:
                    # Try to deduce from rater_acc pattern (e.g., MP001 -> M dept, P role)
                    # P: 正职, D: 副职, E: 其他员工, C: 基层领导(两中心)
                    import re
                    match = re.match(r'^([A-Z]+)([PDEC])\d+$', rater_acc)
                    if match:
                        code_part = match.group(1) # e.g. M, U, V
                        role_char = match.group(2) # e.g. P
                        
                        # Map Role Char
                        if role_char == 'P': acc_type = '正职'
                        elif role_char == 'D': acc_type = '副职'
                        elif role_char == 'E': acc_type = '其他员工'
                        elif role_char == 'C': acc_type = '中心基层领导' # Special for Centers
                        
                        # Map Dept Type based on Code
                        # A-K: 职能部门 (Usually)
                        # L-S: 研究所 (M is Institute)
                        # T, U, V, W, X, Y: Centers/Branches
                        # We can try to look up Dept Type from department_config using code_part
                        if not dept_type:
                            dc_row = db.execute('SELECT dept_type, dept_name FROM department_config WHERE dept_code = ?', (code_part,)).fetchone()
                            if dc_row:
                                dept_type = dc_row['dept_type']
                                acc_dept_name = dc_row['dept_name']
                # -----------------------------------------------------------------------------
                
                # 院领导
                if rater_acc in leader_account_map:
                    lkey = leader_account_map[rater_acc]
                    if lkey not in leader_scores:
                        leader_scores[lkey] = []
                    leader_scores[lkey].append(score)
                    continue
                
                # 职能部门正职
                if acc_type == '正职' and dept_type == '职能部门':
                    func_principal_scores.append(score)
                    continue
                
                # 职能部门副职
                if acc_type == '副职' and dept_type == '职能部门':
                    func_deputy_scores.append(score)
                    continue
                
                # 职能部门员工
                if acc_type == '其他员工' and dept_type == '职能部门':
                    func_employee_scores.append(score)
                    continue
                
                # 院长助理账号
                if acc_type == '院长助理':
                    func_assistant_scores.append(score)
                    continue
                
                # 研究所正职
                if acc_type == '正职' and dept_type == '研究所':
                    inst_principal_scores.append(score)
                    continue
                
                # 研究所副职
                if acc_type == '副职' and dept_type == '研究所':
                    inst_deputy_scores.append(score)
                    continue
                
                # 研究所员工
                if acc_type == '其他员工' and dept_type == '研究所':
                    inst_employee_scores.append(score)
                    continue
                
                # 两中心正职 + 昆冈分公司正职
                if acc_type == '正职':
                    if acc_dept_name in ['兰州化工研究中心', '大庆化工研究中心']:
                        center_kungang_scores.append(score)
                        continue
                    if '昆冈' in acc_dept_name and '分公司' in acc_dept_name:
                         # 同时也加入 center_kungang_scores (两中心正职需用到)
                         center_kungang_scores.append(score)
                         # 不continue，让后续昆冈专用逻辑也能捕获
                
                # 两中心副职 + 昆冈分公司副职
                # 两中心副职 + 昆冈分公司副职
                if acc_type == '副职':
                    if acc_dept_name in ['兰州化工研究中心', '大庆化工研究中心']:
                        center_kungang_deputy_scores.append(score)
                        continue
                    if '昆冈' in acc_dept_name and '分公司' in acc_dept_name:
                        center_kungang_deputy_scores.append(score)
                        # 不continue
                
                # 两中心基层领导
                if acc_type == '中心基层领导' and acc_dept_name in ['兰州化工研究中心', '大庆化工研究中心']:
                         center_grassroots_scores.append(score)
                         continue
                
                # 两中心其他员工
                if acc_type == '其他员工' and acc_dept_name in ['兰州化工研究中心', '大庆化工研究中心']:
                         center_employee_scores.append(score)
                         continue

                # 昆冈相关账号分类 (U, V, W)
                acc_dept_code = acc.get('dept_code', '')
                if acc_dept_code in ['U', 'V', 'W']:
                    # 昆冈班子正职 (U, V, W)
                    if acc_type == '正职':
                        # 如果是U，计入大班子正职
                        if acc_dept_code == 'U':
                            kungang_principal_scores.append(score)
                        # 如果是V, W，计入分公司正职
                        if acc_dept_code in ['V', 'W']:
                            branch_principal_scores.append(score)
                            branch_leadership_pooled_scores.append(score)
                        continue
                    
                    # 昆冈班子副职 (U, V, W)
                    if acc_type == '副职':
                        if acc_dept_code == 'U':
                            kungang_deputy_scores.append(score)
                        if acc_dept_code in ['V', 'W']:
                            branch_deputy_scores.append(score)
                            branch_leadership_pooled_scores.append(score)
                        continue
                        
                    # 昆冈基层领导 (U, V, W)
                    if acc_type == '中心基层领导':
                        if acc_dept_code == 'U':
                            kungang_beijing_grassroots.append(score)
                        if acc_dept_code in ['V', 'W']:
                            branch_grassroots_scores.append(score)
                        continue
                        
                    # 昆冈其他员工 (U, V, W)
                    if acc_type == '其他员工':
                        if acc_dept_code == 'U':
                            kungang_beijing_employees.append(score)
                        if acc_dept_code in ['V', 'W']:
                            branch_employee_scores.append(score)
                        continue

            # ===== 计算各项得分 =====
            
            # 1. 院领导评分 = Σ(院领导i的评分 × 院领导i的个人权重%)
            score_college_leader = 0
            for lkey, weight in leader_weights.items():
                if lkey in leader_scores and leader_scores[lkey]:
                    avg = sum(leader_scores[lkey]) / len(leader_scores[lkey])
                    score_college_leader += avg * (weight / 100.0)
            
            # 根据角色不同，计算方式不同
            if role == '院长助理':
                # === 院长助理计算逻辑 ===
                # 职能部门正职评分 = (正职+院长助理)平均分 × 10%
                all_func = func_principal_scores + func_assistant_scores
                score_func_principal = (sum(all_func) / len(all_func) * 0.10) if all_func else 0
                score_func_deputy = 0
                score_func_employee = 0
                score_func_abc = 0
                score_func_bc = 0
                
                # 研究所正职评分 = 平均分 × 10%
                score_inst_principal = (sum(inst_principal_scores) / len(inst_principal_scores) * 0.10) if inst_principal_scores else 0
                score_inst_deputy = 0
                score_inst_employee = 0
                score_inst_abc = 0
                score_inst_bc = 0
                score_center_principal = 0
                score_center_deputy = 0
                score_center_grassroot = 0
                score_center_employee = 0
                
                # 中心及昆冈加权 = 平均分 × 10%
                score_center_kungang = (sum(center_kungang_scores) / len(center_kungang_scores) * 0.10) if center_kungang_scores else 0
                
                # 总分 = 四项相加
                total_score = score_college_leader + score_func_principal + score_inst_principal + score_center_kungang
                
            elif role == '职能部门正职':
                # === 职能部门正职计算逻辑 ===
                # 原始分数（用于展示）
                score_func_principal = (sum(func_principal_scores) / len(func_principal_scores)) if func_principal_scores else 0
                score_func_deputy = (sum(func_deputy_scores) / len(func_deputy_scores)) if func_deputy_scores else 0
                score_func_employee = (sum(func_employee_scores) / len(func_employee_scores)) if func_employee_scores else 0
                
                # ABC票加权 = (正职+副职+员工+院长助理)平均分 × 30%
                all_abc = func_principal_scores + func_deputy_scores + func_employee_scores + func_assistant_scores
                score_func_abc = (sum(all_abc) / len(all_abc) * 0.30) if all_abc else 0
                score_func_bc = 0
                
                # 研究所正职评分 = 平均分 × 权重% (暂定10%)
                score_inst_principal = (sum(inst_principal_scores) / len(inst_principal_scores) * 0.10) if inst_principal_scores else 0
                score_inst_deputy = 0
                score_inst_employee = 0
                score_inst_abc = 0
                score_inst_bc = 0
                
                # 中心及昆冈加权 = 平均分 × 权重% (暂定10%)
                score_center_kungang = (sum(center_kungang_scores) / len(center_kungang_scores) * 0.10) if center_kungang_scores else 0
                
                score_center_principal = 0
                score_center_deputy = 0
                score_center_grassroot = 0
                score_center_employee = 0
                
                # 总分 = 院领导 + ABC加权 + 研究所 + 中心昆冈
                total_score = score_college_leader + score_func_abc + score_inst_principal + score_center_kungang
            
            elif role == '职能部门副职':
                # === 职能部门副职计算逻辑 ===
                # 原始分数（用于展示）
                score_func_deputy = (sum(func_deputy_scores) / len(func_deputy_scores)) if func_deputy_scores else 0
                score_func_employee = (sum(func_employee_scores) / len(func_employee_scores)) if func_employee_scores else 0
                
                # 职能部门正职评分 = (正职+院长助理)平均分 × 20%
                all_principal = func_principal_scores + func_assistant_scores
                score_func_principal = (sum(all_principal) / len(all_principal) * 0.20) if all_principal else 0
                
                # BC票加权 = (副职+员工)平均分 × 30%
                all_bc = func_deputy_scores + func_employee_scores
                score_func_bc = (sum(all_bc) / len(all_bc) * 0.30) if all_bc else 0
                score_func_abc = 0
                
                score_inst_principal = 0
                score_inst_deputy = 0
                score_inst_employee = 0
                score_inst_abc = 0
                score_inst_bc = 0
                score_center_principal = 0
                score_center_deputy = 0
                score_center_grassroot = 0
                score_center_employee = 0
                score_center_kungang = 0
                
                # 总分 = 院领导 + 正职加权 + BC加权
                total_score = score_college_leader + score_func_principal + score_func_bc
            
            elif role == '研究所正职':
                # === 研究所正职计算逻辑 ===
                # 原始分数（用于展示）
                score_inst_principal = (sum(inst_principal_scores) / len(inst_principal_scores)) if inst_principal_scores else 0
                score_inst_deputy = (sum(inst_deputy_scores) / len(inst_deputy_scores)) if inst_deputy_scores else 0
                score_inst_employee = (sum(inst_employee_scores) / len(inst_employee_scores)) if inst_employee_scores else 0
                
                # 职能部门正职评分 = (正职+院长助理)平均分 × 20%
                all_func = func_principal_scores + func_assistant_scores
                score_func_principal = (sum(all_func) / len(all_func) * 0.20) if all_func else 0
                score_func_deputy = 0
                score_func_employee = 0
                score_func_abc = 0
                score_func_bc = 0
                
                # 研究所ABC票加权 = (正职+副职+员工)平均分 × 30%
                all_inst_abc = inst_principal_scores + inst_deputy_scores + inst_employee_scores
                score_inst_abc = (sum(all_inst_abc) / len(all_inst_abc) * 0.30) if all_inst_abc else 0
                score_inst_bc = 0
                
                score_center_principal = 0
                score_center_deputy = 0
                score_center_grassroot = 0
                score_center_employee = 0
                
                score_center_kungang = 0
                
                # 总分 = 院领导 + 职能正职加权 + 研究所ABC加权
                total_score = score_college_leader + score_func_principal + score_inst_abc
            
            elif role == '研究所副职':
                # === 研究所副职计算逻辑 ===
                # 原始分数（用于展示）
                score_inst_deputy = (sum(inst_deputy_scores) / len(inst_deputy_scores)) if inst_deputy_scores else 0
                score_inst_employee = (sum(inst_employee_scores) / len(inst_employee_scores)) if inst_employee_scores else 0
                
                # 研究所正职评分 = 平均分 × 20%
                score_inst_principal = (sum(inst_principal_scores) / len(inst_principal_scores) * 0.20) if inst_principal_scores else 0
                
                # 研究所BC票加权 = (副职+员工)平均分 × 30%
                all_inst_bc = inst_deputy_scores + inst_employee_scores
                score_inst_bc = (sum(all_inst_bc) / len(all_inst_bc) * 0.30) if all_inst_bc else 0
                score_inst_abc = 0
                
                score_func_principal = 0
                score_func_deputy = 0
                score_func_employee = 0
                
                # 总分 = 院领导 + 研究所正职加权 + BC加权
                total_score = score_college_leader + score_inst_principal + score_inst_bc
            
            elif role in ['两中心正职', '中心正职'] and dept_name in ['兰州化工研究中心', '大庆化工研究中心']:
                # === 两中心正职计算逻辑 ===
                # 原始分数（用于展示）
                # 'center_kungang_scores' 收集的是所有两中心/昆冈正职
                score_center_principal = (sum(center_kungang_scores) / len(center_kungang_scores)) if center_kungang_scores else 0
                score_center_deputy = (sum(center_kungang_deputy_scores) / len(center_kungang_deputy_scores)) if center_kungang_deputy_scores else 0
                # 基层领导和员工加权分（用于总分）
                _score_center_grassroot_raw = (sum(center_grassroots_scores) / len(center_grassroots_scores)) if center_grassroots_scores else 0
                _score_center_employee_raw = (sum(center_employee_scores) / len(center_employee_scores)) if center_employee_scores else 0
                
                # 用于数据库存储（加权值）
                score_center_grassroot = _score_center_grassroot_raw * 0.20
                score_center_employee = _score_center_employee_raw * 0.10
                
                # 职能部门正职评分 = (正职+院长助理)平均分 × 10%
                all_func = func_principal_scores + func_assistant_scores
                score_func_principal = (sum(all_func) / len(all_func) * 0.10) if all_func else 0
                
                # 中心及昆冈加权 = (所有两中心,昆冈分公司正副职)平均分 × 10% (共享10%)
                all_center_kungang = center_kungang_scores + center_kungang_deputy_scores
                score_center_kungang = (sum(all_center_kungang) / len(all_center_kungang) * 0.10) if all_center_kungang else 0
                
                # 中心及昆冈加权 = (所有两中心,昆冈分公司正副职)平均分 × 10% (共享10%)
                all_center_kungang = center_kungang_scores + center_kungang_deputy_scores
                score_center_kungang = (sum(all_center_kungang) / len(all_center_kungang) * 0.10) if all_center_kungang else 0
                
                # 总分 = 院领导 + 职能正职 + 中心加权 + 基层领导 + 其他员工
                total_score = score_college_leader + score_func_principal + score_center_kungang + score_center_grassroot + score_center_employee

            elif role == '中心副职' and dept_name in ['兰州化工研究中心', '大庆化工研究中心']:
                # === 中心副职计算逻辑 ===
                # 1. 院领导评分 (score_college_leader) 已在上方通用逻辑中计算完毕（权重50%）

                # 2. 中心及昆冈正职评分 (权重 20%)
                # 原始分数用于展示
                score_center_principal = (sum(center_kungang_scores) / len(center_kungang_scores)) if center_kungang_scores else 0
                _score_center_principal_weighted = score_center_principal * 0.20

                # 3. 中心及昆冈副职评分 (权重 10%)
                # 原始分数用于展示
                score_center_deputy = (sum(center_kungang_deputy_scores) / len(center_kungang_deputy_scores)) if center_kungang_deputy_scores else 0
                _score_center_deputy_weighted = score_center_deputy * 0.10

                # 4. 基层领导评分（两中心） (权重 10%)
                # 原始分数用于展示
                _score_center_grassroot_avg = (sum(center_grassroots_scores) / len(center_grassroots_scores)) if center_grassroots_scores else 0
                score_center_grassroot = _score_center_grassroot_avg * 0.10

                # 5. 中心及昆冈其他员工评分 (权重 10%)
                # 原始分数用于展示
                _score_center_employee_avg = (sum(center_employee_scores) / len(center_employee_scores)) if center_employee_scores else 0
                score_center_employee = _score_center_employee_avg * 0.10

                # 总分 = 院领导加权 + 正职加权 + 副职加权 + 基层加权 + 其他员工加权
                total_score = score_college_leader + _score_center_principal_weighted + _score_center_deputy_weighted + score_center_grassroot + score_center_employee

            elif role == '中心副职' and dept_code == 'U':
                # === 昆冈班子副职 (北京) 计算逻辑 ===
                # 1. 院领导 (20%) - 已计算

                # 2. 中心及昆冈正职评分 (40%) -> 来源: 昆冈班子正职 (U, V, W)
                score_center_principal = (sum(kungang_principal_scores) / len(kungang_principal_scores)) if kungang_principal_scores else 0
                _w_center_principal = score_center_principal * 0.40

                # 3. 中心及昆冈副职评分 (10%) -> 来源: 昆冈班子副职 (U)
                score_center_deputy = (sum(kungang_deputy_scores) / len(kungang_deputy_scores)) if kungang_deputy_scores else 0
                _w_center_deputy = score_center_deputy * 0.10

                # 4. 昆冈分公司正职评分 (10%) -> 来源: 昆冈分公司正职 (V, W)
                # 存入 score_branch_principal (存储加权分)
                _score_branch_principal_raw = (sum(branch_principal_scores) / len(branch_principal_scores)) if branch_principal_scores else 0
                score_branch_principal = _score_branch_principal_raw * 0.10
                _w_branch_principal = score_branch_principal # Keep for compatibility if used elsewhere

                # 5. 基层领导评分（两中心及昆冈） (10%) -> 来源: 昆冈北京基层领导 (U)
                # 复用 score_center_grassroot (存储加权分)
                _score_center_grassroot_raw = (sum(kungang_beijing_grassroots) / len(kungang_beijing_grassroots)) if kungang_beijing_grassroots else 0
                score_center_grassroot = _score_center_grassroot_raw * 0.10
                
                # 6. 中心及昆冈其他员工评分 (10%) -> 来源: 昆冈北京其他员工 (U)
                # 复用 score_center_employee (存储加权分)
                _score_center_employee_raw = (sum(kungang_beijing_employees) / len(kungang_beijing_employees)) if kungang_beijing_employees else 0
                score_center_employee = _score_center_employee_raw * 0.10

                total_score = score_college_leader + _w_center_principal + _w_center_deputy + score_branch_principal + score_center_grassroot + score_center_employee
                # 注意: score_branch_principal 需要在 INSERT SQL 中有对应列

            elif role == '中心正职' and dept_code in ['V', 'W']:
                # === 昆冈所属分公司 (兰州/抚顺) 班子正职计算逻辑 ===
                # 1. 院领导 (10%) - 已计算
                
                # 2. 职能部门正职评分 (10%) -> 含院长助理
                _all_func = func_principal_scores + func_assistant_scores
                score_func_principal = ((sum(_all_func) / len(_all_func)) * 0.10) if _all_func else 0
                
                # 3. 昆冈班子正职评分 (30%) -> 仅 U
                _kungang_p_avg = (sum(kungang_principal_scores) / len(kungang_principal_scores)) if kungang_principal_scores else 0
                score_kungang_principal = _kungang_p_avg * 0.30
                
                # 4. 昆冈班子副职评分 (10%) -> 仅 U
                _kungang_d_avg = (sum(kungang_deputy_scores) / len(kungang_deputy_scores)) if kungang_deputy_scores else 0
                score_kungang_deputy = _kungang_d_avg * 0.10
                
                # 5. 分公司正职 & 副职 原始分展示
                score_branch_principal = (sum(branch_principal_scores) / len(branch_principal_scores)) if branch_principal_scores else 0
                score_branch_deputy = (sum(branch_deputy_scores) / len(branch_deputy_scores)) if branch_deputy_scores else 0
                
                # 6. 昆冈分公司加权 (10%) -> 正副职共享
                _branch_joint_avg = (sum(branch_leadership_pooled_scores) / len(branch_leadership_pooled_scores)) if branch_leadership_pooled_scores else 0
                score_branch_weighted = _branch_joint_avg * 0.10
                
                # 7. 基层领导评分 (20%) -> 来源: 分公司基层
                _branch_grass_avg = (sum(branch_grassroots_scores) / len(branch_grassroots_scores)) if branch_grassroots_scores else 0
                score_center_grassroot = _branch_grass_avg * 0.20
                
                # 8. 中心及昆冈其他员工评分 (10%) -> 来源: 分公司员工
                _branch_emp_avg = (sum(branch_employee_scores) / len(branch_employee_scores)) if branch_employee_scores else 0
                score_center_employee = _branch_emp_avg * 0.10
                
                total_score = score_college_leader + score_func_principal + score_kungang_principal + score_kungang_deputy + score_branch_weighted + score_center_grassroot + score_center_employee

            elif role == '中心副职' and dept_code in ['V', 'W']:
                # === 昆冈所属分公司 (兰州/抚顺) 班子副职 ===
                # 1. 院领导 (0%) - 用户指定
                score_college_leader = 0
                
                # 2. 昆冈班子正职评分 (30%) -> 仅 U
                _kungang_p_avg = (sum(kungang_principal_scores) / len(kungang_principal_scores)) if kungang_principal_scores else 0
                score_kungang_principal = _kungang_p_avg * 0.30
                
                # 3. 昆冈班子副职评分 (10%) -> 仅 U
                _kungang_d_avg = (sum(kungang_deputy_scores) / len(kungang_deputy_scores)) if kungang_deputy_scores else 0
                score_kungang_deputy = _kungang_d_avg * 0.10
                
                # 4. 分公司正职评分 (30%) -> V/W
                _branch_p_avg = (sum(branch_principal_scores) / len(branch_principal_scores)) if branch_principal_scores else 0
                score_branch_principal = _branch_p_avg * 0.30
                
                # 5. 分公司副职评分 (10%) -> V/W
                _branch_d_avg = (sum(branch_deputy_scores) / len(branch_deputy_scores)) if branch_deputy_scores else 0
                score_branch_deputy = _branch_d_avg * 0.10
                
                # 6. 基层领导评分 (10%) -> 分公司基层
                _branch_grass_avg = (sum(branch_grassroots_scores) / len(branch_grassroots_scores)) if branch_grassroots_scores else 0
                score_center_grassroot = _branch_grass_avg * 0.10
                
                # 7. 员工评分 (10%) -> 分公司员工
                _branch_emp_avg = (sum(branch_employee_scores) / len(branch_employee_scores)) if branch_employee_scores else 0
                score_center_employee = _branch_emp_avg * 0.10
                
                # 不使用的字段置0
                score_func_principal = 0
                score_branch_weighted = 0
                
                total_score = score_college_leader + score_kungang_principal + score_kungang_deputy + score_branch_principal + score_branch_deputy + score_center_grassroot + score_center_employee

            else:
                 # 其他角色暂未实现
                 total_score = 0
            
            cursor.execute('''
                INSERT INTO examinee_score_summary (
                    examinee_id, name, dept_name,
                    score_college_leader, 
                    score_func_principal, score_func_deputy, score_func_employee, 
                    score_func_abc_weighted, score_func_bc_weighted,
                    score_inst_principal, score_inst_deputy, score_inst_employee,
                    score_inst_abc_weighted, score_inst_bc_weighted, 
                    score_center_principal, score_center_deputy, score_center_grassroot, score_center_employee,
                    score_center_kungang, 
                    score_kungang_principal, score_kungang_deputy, score_branch_principal, score_branch_deputy,
                    total_score,
                    score_branch_weighted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                eid, name, dept_name,
                score_college_leader,
                score_func_principal, score_func_deputy, score_func_employee,
                score_func_abc, score_func_bc,
                score_inst_principal, score_inst_deputy, score_inst_employee,
                score_inst_abc, score_inst_bc,
                score_center_principal, score_center_deputy, score_center_grassroot, score_center_employee,
                score_center_kungang, 
                score_kungang_principal, score_kungang_deputy, score_branch_principal, score_branch_deputy,
                total_score,
                score_branch_weighted
            ))
            inserted_count += 1
        
        db.commit()
        return jsonify({'success': True, 'msg': f'计算完成，已生成 {inserted_count} 条记录'})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/examinee-summary/clear', methods=['POST'])
@admin_required
def examinee_summary_clear():
    """清空汇总得分数据"""
    try:
        db = get_db()
        db.execute('DELETE FROM examinee_score_summary')
        db.commit()
        return jsonify({'success': True, 'msg': '已清空所有汇总数据'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

def _get_rater_roles_simple(acc_info):
    """
    简化版考核人角色识别
    根据账号类型和部门类型确定考核人角色
    """
    roles = []
    acc_type = acc_info.get('account_type', '')
    dept_type = acc_info.get('dept_type', '')
    dept_name = acc_info.get('dept_name', '')
    dept_code = acc_info.get('dept_code', '')
    
    if acc_type == '院领导' or dept_code == 'A0':
        roles.append('院领导')
    
    if acc_type == '正职':
        if dept_type == '职能部门':
            roles.append('职能部门正职 (含院长助理)')
        elif dept_type == '研究所':
            roles.append('研究所正职')
        elif '中心' in dept_name:
            roles.append('中心领导班子 (正职)')
        elif '昆冈' in dept_name and '分公司' in dept_name:
            roles.append('所属分公司班子正职')
        elif '昆冈' in dept_name:
            roles.append('昆冈班子正职')
    
    if acc_type == '副职':
        if dept_type == '职能部门':
            roles.append('职能部门副职')
        elif dept_type == '研究所':
            roles.append('研究所副职')
        elif '中心' in dept_name:
            roles.append('中心领导班子 (副职)')
        elif '昆冈' in dept_name and '分公司' in dept_name:
            roles.append('所属分公司班子副职')
        elif '昆冈' in dept_name:
            roles.append('昆冈班子副职')
    
    if acc_type == '其他员工':
        if dept_type == '职能部门':
            roles.append('职能部门其他员工')
        elif dept_type == '研究所':
            roles.append('研究所其他员工')
    
    if acc_type == '中心基层领导':
        roles.append('职工代表中基层领导人员 (两中心)')
    
    return roles

@app.route('/api/examinee-summary/save', methods=['POST'])
@admin_required
def examinee_summary_save():
    """保存编辑的汇总数据"""
    try:
        db = get_db()
        data = request.json.get('data', [])
        if not data:
            return jsonify({'success': False, 'msg': '无更新数据'})
        
        cursor = db.cursor()
        for item in data:
            row_id = item.get('id')
            if row_id:
                # 动态构建更新语句
                update_fields = []
                values = []
                for field in ['score_college_leader', 
                              'score_func_principal', 'score_func_deputy', 'score_func_employee',
                              'score_func_abc_weighted', 'score_func_bc_weighted',
                              'score_inst_principal', 'score_inst_deputy', 'score_inst_employee',
                              'score_inst_abc_weighted', 'score_inst_bc_weighted',
                              'score_center_principal', 'score_center_deputy', 'score_center_kungang',
                              'score_center_grassroot', 'score_center_employee',
                              'score_kungang_principal', 'score_kungang_deputy',
                              'score_branch_principal', 'score_branch_deputy', 'total_score']:
                    if field in item:
                        update_fields.append(f'{field}=?')
                        values.append(item[field])
                
                if update_fields:
                    values.append(row_id)
                    sql = f'UPDATE examinee_score_summary SET {", ".join(update_fields)}, updated_at=CURRENT_TIMESTAMP WHERE id=?'
                    cursor.execute(sql, values)
        
        db.commit()
        return jsonify({'success': True, 'msg': f'保存成功 ({len(data)} 条)'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})





# ==========================================
# 6.5. API: 院领导权重配置 (Leader Weight Config)
# ==========================================

@app.route('/admin/leader-weight-config')
@admin_required
def leader_weight_config_page():
    return render_template('leader_weight_config.html')

@app.route('/api/leader-weight-config/list')
@admin_required
def leader_weight_config_list():
    try:
        db = get_db()
        # Only return departments that have been configured in leader_weight_config
        configs = db.execute('SELECT * FROM leader_weight_config ORDER BY id ASC').fetchall()
        result = [dict(c) for c in configs]
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/leader-weight-config/save', methods=['POST'])
@admin_required
def leader_weight_config_save():
    try:
        db = get_db()
        data = request.json.get('data', [])
        
        cursor = db.cursor()
        for item in data:
            cursor.execute('''
                INSERT INTO leader_weight_config 
                    (dept_code, dept_name, total_weight, w_yang_weisheng, w_wang_ling, w_xu_qingchun, w_zhao_tong, w_ge_shaohui, w_liu_chaowei)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(dept_code) DO UPDATE SET
                    dept_name=excluded.dept_name,
                    total_weight=excluded.total_weight,
                    w_yang_weisheng=excluded.w_yang_weisheng,
                    w_wang_ling=excluded.w_wang_ling,
                    w_xu_qingchun=excluded.w_xu_qingchun,
                    w_zhao_tong=excluded.w_zhao_tong,
                    w_ge_shaohui=excluded.w_ge_shaohui,
                    w_liu_chaowei=excluded.w_liu_chaowei,
                    updated_at=CURRENT_TIMESTAMP
            ''', (
                item.get('dept_code'),
                item.get('dept_name'),
                item.get('total_weight', 50),
                item.get('w_yang_weisheng', 0),
                item.get('w_wang_ling', 0),
                item.get('w_xu_qingchun', 0),
                item.get('w_zhao_tong', 0),
                item.get('w_ge_shaohui', 0),
                item.get('w_liu_chaowei', 0)
            ))
        
        db.commit()
        return jsonify({'success': True, 'msg': f'保存成功 ({len(data)} 条)'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

# ==========================================
# 6.6. API: 院领导账号分配 (Leader Account Mapping)
# ==========================================

LEADER_KEYS = [
    ('yang_weisheng', '杨卫胜'),
    ('wang_ling', '王凌'),
    ('xu_qingchun', '许青春'),
    ('zhao_tong', '赵彤'),
    ('ge_shaohui', '葛少辉'),
    ('liu_chaowei', '刘超伟'),
]

@app.route('/admin/leader-account-mapping')
@admin_required
def leader_account_mapping_page():
    return render_template('leader_account_mapping.html')

@app.route('/api/leader-account-mapping/list')
@admin_required
def leader_account_mapping_list():
    try:
        db = get_db()
        mappings = db.execute('SELECT * FROM leader_account_mapping').fetchall()
        mapping_dict = {m['leader_key']: m['account'] for m in mappings}
        
        result = []
        for key, name in LEADER_KEYS:
            result.append({
                'leader_key': key,
                'leader_name': name,
                'account': mapping_dict.get(key, '')
            })
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/leader-account-mapping/save', methods=['POST'])
@admin_required
def leader_account_mapping_save():
    try:
        db = get_db()
        data = request.json.get('data', [])
        
        cursor = db.cursor()
        for item in data:
            cursor.execute('''
                INSERT INTO leader_account_mapping (leader_key, leader_name, account)
                VALUES (?, ?, ?)
                ON CONFLICT(leader_key) DO UPDATE SET
                    leader_name=excluded.leader_name,
                    account=excluded.account,
                    updated_at=CURRENT_TIMESTAMP
            ''', (item.get('leader_key'), item.get('leader_name'), item.get('account', '')))
        
        db.commit()
        return jsonify({'success': True, 'msg': '保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/accounts-a0')
@admin_required
def get_accounts_a0():
    try:
        db = get_db()
        accounts = db.execute("SELECT username FROM evaluation_accounts WHERE dept_code='A0' ORDER BY username ASC").fetchall()
        result = [a['username'] for a in accounts]
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

# ==========================================
# 7. API: 人员管理 (Renumbered)
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

        for col in ['出生年月', '现职级时间', '任职时间']:

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



        for col in ['出生年月', '现职级时间', '任职时间']:

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

        for col in ['出生年月', '现职级时间', '任职时间']:

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



        for col in ['出生年月', '现职级时间', '任职时间']:

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

        for col in ['出生年月', '现职级时间', '任职时间']:

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

        ORDER BY d.sort_no ASC, d.serial_no ASC, a.id ASC 

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



# Democratic Assessment Permission Config (Independent of Weights)

# Format: Examinee Role -> List of Allowed Rater Roles

DEFAULT_DEMOCRATIC_CONFIG = {

    '院长助理': ['院领导', '职能部门正职 (含院长助理)', '研究所正职', '中心领导班子 (正职)'],

    '职能部门正职': ['院领导', '职能部门正职 (含院长助理)', '职能部门副职', '职能部门其他员工', '研究所正职', '中心领导班子 (正职)'],

    '职能部门副职': ['院领导', '职能部门正职 (含院长助理)', '职能部门副职', '职能部门其他员工'],

    

    # [Updated] Institute Rules

    '研究所正职': [

        '院领导', '职能部门正职 (含院长助理)', '研究所其他员工',

        '研究所正职', # Mutual

        '研究所副职'  # Deputy rates Principal

    ],

    '研究所副职': [

        '院领导', '研究所其他员工',

        '研究所正职', # Principal rates Deputy

        '研究所副职'  # Mutual

    ],

    

    '两中心正职': ['院领导', '职能部门正职 (含院长助理)', '中心领导班子 (正职)', '职工代表中基层领导人员 (两中心)', '其他职工代表 (两中心)'],

    '两中心副职': ['院领导', '中心领导班子 (正职)', '中心领导班子 (副职)', '职工代表中基层领导人员 (两中心)', '其他职工代表 (两中心)'],

    

    '昆冈班子副职 (北京)': [

        '院领导', '职能部门正职 (含院长助理)', 

        '昆冈班子正职', '昆冈班子副职', 

        '所属分公司班子正职', 

        '职工代表中基层领导人员 (昆冈北京)'

    ],

    

    '所属分公司 (兰州、抚顺) 班子正职': [

        '院领导', '职能部门正职 (含院长助理)', 

        '昆冈班子正职', '昆冈班子副职', 

        '所属分公司班子副职', 

        '职工代表中基层领导人员 (分公司)', '其他职工代表 (分公司)'

    ],

    '所属分公司 (兰州、抚顺) 班子副职': [

        '昆冈班子正职', '昆冈班子副职', 

        '所属分公司班子正职', '所属分公司班子副职', 

        '职工代表中基层领导人员 (分公司)', '其他职工代表 (分公司)'

    ]

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

    '中心领导班子 (正职)': [

        {'dept_type': '两中心', 'types': ['P', '正职']},

        {'dept_codes': ['X', 'Y'], 'types': ['P', '正职']}

    ],

    '中心领导班子 (副职)': [

        {'dept_type': '两中心', 'types': ['D', '副职']},

        {'dept_codes': ['X', 'Y'], 'types': ['D', '副职']}

    ],

    

    # 10-11. 昆冈

    '昆冈班子正职': [

        {'dept_type': '昆冈', 'types': ['P', '正职']},

        {'dept_names': ['昆冈先进制造（北京）有限公司'], 'dept_codes': ['U'], 'types': ['P', '正职']}

    ],

    '昆冈班子副职': [

        {'dept_type': '昆冈', 'types': ['D', '副职']},

        {'dept_names': ['昆冈先进制造（北京）有限公司'], 'types': ['D', '副职']}

    ],

    

    # 12-13. 分公司 (兰州/抚顺)

    '所属分公司班子正职': [{'dept_names': ['昆冈兰州分公司', '昆冈抚顺分公司'], 'types': ['P', '正职']}],

    '所属分公司班子副职': [{'dept_names': ['昆冈兰州分公司', '昆冈抚顺分公司'], 'types': ['D', '副职']}],

    

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

    

    acc_type = user_account.get('account_type', '').strip()

    d_name = user_dept_info.get('dept_name', '').strip()

    d_type = user_dept_info.get('dept_type', '').strip()

    d_code = user_dept_info.get('dept_code', '').strip()

    

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

    if not person_role: return None

    person_role = person_role.strip()

    





    # [Exclusion] Grassroots leaders should NOT be examinees (Global Check)

    if '基层' in person_role: 

        return 'EXCLUDED'



    # 1. 直接匹配基础角色

    if person_role in ['院长助理', '职能部门正职', '职能部门副职', '研究所正职', '研究所副职']:

        return person_role

        

    # 2. 复合角色：两中心 (兰州/大庆)

    if '中心' in person_role: # 中心正职 / 中心副职

        if dept_name in ['兰州化工研究中心', '大庆化工研究中心']:

            if '正职' in person_role: return '两中心正职'

            if '副职' in person_role: return '两中心副职'

            if '副职' in person_role: return '两中心副职'

            

        # 3. 复合角色：昆冈 (北京)

        if dept_name == '昆冈先进制造（北京）有限公司':

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
        
        # 院领导不参与领导班子打分
        if user_row['dept_code'] == 'A0':
            return jsonify({'success': False, 'msg': '院领导无需打领导班子分'})
        
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

#         db.execute('UPDATE evaluation_accounts SET status = "否" WHERE username = ?', (rater_account,))

        

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

    raw_managers = db.execute('SELECT * FROM middle_managers WHERE dept_code=? ORDER BY sort_no ASC', (dept_code,)).fetchall()

    managers = []

    for m in raw_managers:

        # [Exclusion] Grassroots leaders check

        # Use simple string check to ensure consistency with Global Rule

        r_name = m['role'] or ''

        if '基层' in r_name:

            continue

        managers.append(m)

    

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

        

        # [NEW] Recommend Principal Nav Item

        recommend_principal_enabled = False

        if d_row and d_row['count_recommend_principal'] and d_row['count_recommend_principal'] >= 1:

            recommend_principal_enabled = True

            

        # [NEW] Recommend Deputy Nav Item

        recommend_deputy_enabled = False

        if d_row and d_row['count_recommend_deputy'] and d_row['count_recommend_deputy'] >= 1:

            recommend_deputy_enabled = True



        # [NEW] Project 6: Cadre Selection and Appointment Evaluation

        # Permissions: V, W, X, Y

        selection_appointment_enabled = False

        allowed_depts_p6 = ['V', 'W', 'X', 'Y']

        if user_row and user_row['dept_code'] in allowed_depts_p6:

             selection_appointment_enabled = True



        # [NEW] Project 7: New Promotion Evaluation

        # Permissions: X, Y

        new_promotion_enabled = False

        allowed_depts_p7 = ['X', 'Y']

        if user_row and user_row['dept_code'] in allowed_depts_p7:

             new_promotion_enabled = True



        return {

            'democratic_nav_items': nav_items,

            'recommend_principal_enabled': recommend_principal_enabled,

            'recommend_deputy_enabled': recommend_deputy_enabled,

            'selection_appointment_enabled': selection_appointment_enabled,

            'new_promotion_enabled': new_promotion_enabled

        }

    

    return {}



@app.route('/assessment/democratic-evaluation/<group_key>')

def assessment_democratic(group_key):

    # Democratic Assessment (Grouped)

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

    

    full_user_for_roles = dict(user_row) # helper

    raw_roles = get_user_rater_roles(full_user_for_roles, full_user_for_roles)

    

    # [Fix for KP001]: Apply Split Logic similar to get_democratic_nav

    # Because democratic_rating_config uses split keys (functional vs assistant), but RATER_RULES returns combined.

    my_rater_roles = []

    for r in raw_roles:

        if r == '职能部门正职 (含院长助理)':

            if user_row['dept_name'] == '院长助理' or user_row['dept_code'] == 'A0':

                my_rater_roles.append('院长助理')

            else:

                my_rater_roles.append('职能部门正职')

        else:

            my_rater_roles.append(r)

    

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

        elif r == '所属分公司 (兰州、抚顺) 班子正职': db_roles.append('中心正职')

        elif r == '所属分公司 (兰州、抚顺) 班子副职': db_roles.append('中心副职')

        elif r == '昆冈班子副职 (北京)': db_roles.append('中心副职')

        else: db_roles.append(r)

        

    ph = ','.join(['?'] * len(db_roles))

    

    # Fetch all candidates in these roles

    mgrs = db.execute(f'SELECT * FROM middle_managers WHERE role IN ({ph}) ORDER BY dept_code ASC, sort_no ASC', db_roles).fetchall()

    

    is_kungang_rater = any(r in ['昆冈班子正职', '昆冈班子副职', '所属分公司班子正职'] for r in my_rater_roles)

    is_college_leader = (user_row['dept_type'] == '院领导')

    

    valid_members = []

    for m in mgrs:

        c_role = m['role']

        c_dept = m['dept_code'] # Use code or dept_name

        # Careful: get_examinee_role_key uses dept_name. 

        # m['dept_name'] is available from SELECT *? Yes, middle_managers has it.

        c_dept_name = m['dept_name']

        

        # [Fix for College Leader Issue]: 

        # Even if 'center_deputy' is in db_roles, we must ensure THIS specific person maps to an allowed role.

        # e.g. 'Center Deputy' + 'Lanzhou Branch' -> 'Branch Deputy' (which might NOT be allowed for College Leader)

        

        derived_role = get_examinee_role_key(c_role, c_dept_name)

        

        # [V5 Fix] Explicit Exclusion Check

        if derived_role == 'EXCLUDED':

            continue

            

        if not derived_role: derived_role = c_role # Fallback

        

        # Check if derived_role is in the Whitelist (allowed_set) AND in the Target Group (effective_roles)

        # Actually effective_roles is already intersect(target_group, allowed_set).

        # So we just check effective_roles.

        if derived_role not in effective_roles:

            continue

            

        # Exclusion 1: Same Dept (unless Leader)

        if not is_college_leader and c_dept == user_row['dept_code']:

            continue

            

        # Exclusion 2: KunGang Rater -> Exclude KunGang Deputy (Beijing)

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

    

    # Dimensions

    dims = ['s_political_ability', 's_political_perf', 's_party_build', 's_professionalism', 

            's_leadership', 's_learning_innov', 's_performance', 's_responsibility', 

            's_style_image', 's_integrity']



    # ---------------------------

    # Global Validation

    # ---------------------------

    # Requirement: At least one score must NOT be 10 across the entire submission

    has_non_ten = False

    

    for item in data_list:

        scores = item.get('scores', {})

        for d in dims:

            try:

                val = float(scores.get(d, 0))

            except (ValueError, TypeError):

                return jsonify({'success': False, 'msg': '分数格式错误'})

                

            if val < 0 or val > 10: 

                return jsonify({'success': False, 'msg': '分数必须在 0-10 之间'})

            

            if val != 10:

                has_non_ten = True

                

    if not has_non_ten:

        return jsonify({'success': False, 'msg': '无效提交：所有评分均为10分。请至少对某一项给出非10分的评价。'})



    # ---------------------------

    # Save to DB

    # ---------------------------

    try:

        cur = db.cursor()



        for item in data_list:

            try:
                examinee_id = int(item.get('id'))
            except (ValueError, TypeError):
                continue # Skip invalid IDs

            role = item.get('role') # Passed from frontend for convenience
            scores = item.get('scores', {})
            
            score_vals = []
            total = 0
            for d in dims:
                val = float(scores.get(d, 0))
                score_vals.append(val)
                total += val 
            
            # Save (UPSERT)
            try:
                # 1. Try Insert
                # Get name for denormalization
                mgr_row = cur.execute('SELECT name FROM middle_managers WHERE id=?', (examinee_id,)).fetchone()
                examinee_name = mgr_row['name'] if mgr_row else 'Unknown'

                cols = ['rater_account', 'examinee_id', 'examinee_name', 'examinee_role', 'total_score'] + dims
                q = ', '.join(['?'] * len(cols))
                vals = [rater_account, examinee_id, examinee_name, role, total] + score_vals
                cur.execute(f'INSERT INTO democratic_scores ({", ".join(cols)}) VALUES ({q})', vals)
            
            except sqlite3.IntegrityError:
                # 2. Conflict -> Update
                set_clause = ', '.join([f"{d}=?" for d in dims])
                set_clause += ", total_score=?, updated_at=CURRENT_TIMESTAMP"
                params = score_vals + [total, rater_account, examinee_id]
                cur.execute(f'UPDATE democratic_scores SET {set_clause} WHERE rater_account=? AND examinee_id=?', params)

                

        db.commit()

        return jsonify({'success': True, 'msg': '提交成功'})

        

    except Exception as e:

        db.rollback()

        return jsonify({'success': False, 'msg': str(e)})




# ==========================================



@app.route('/assessment/recommend-principal')

def assessment_recommend_principal():

    # Recommend Principal Page

    if session.get('assessor_role') != 'assessor':

        return redirect(url_for('index'))

        

    rater_account = session.get('assessor_username')

    db = get_db()

    

    # 1. Permission & Config Check

    user_row = db.execute('''

        SELECT a.username, a.dept_code, d.dept_name, d.count_recommend_principal

        FROM evaluation_accounts a

        LEFT JOIN department_config d ON a.dept_code = d.dept_code

        WHERE a.username=?

    ''', (rater_account,)).fetchone()

    

    if not user_row: return "无效账号", 403

    

    limit_count = user_row['count_recommend_principal'] or 0

    dept_name = user_row['dept_name']

    

    if limit_count < 1:

        return render_template('assessment_error.html', msg="贵部门无此项推荐名额")

        

    # 2. Fetch Candidates (recommend_principal table)

    # [FILTER] Only show candidates from the same department

    dept_code = user_row['dept_code']

    candidates = db.execute('SELECT * FROM recommend_principal WHERE dept_code=? ORDER BY sort_no ASC', (dept_code,)).fetchall()

    

    # 3. Fetch Existing Selections

    recs = db.execute('SELECT examinee_id FROM recommendation_scores_principal WHERE rater_account=?', 

                      (rater_account,)).fetchall()

    selected_ids = [r['examinee_id'] for r in recs]

    

    page_title = f"{dept_name}优秀干部民主推荐-正职"

    

    return render_template('assessment_recommend_principal.html',

                           page_title=page_title,

                           limit_count=limit_count,

                           candidates=candidates,

                           selected_ids=selected_ids)



@app.route('/api/assessment/recommend-principal/submit', methods=['POST'])

def submit_recommend_principal():

    if session.get('assessor_role') != 'assessor':

        return jsonify({'success': False, 'msg': '未登录'})



    req = request.json

    selected_ids = req.get('selected_ids', []) # List of IDs

    

    rater_account = session.get('assessor_username')

    db = get_db()

    

    # 1. Validation: Limit Check

    user_row = db.execute('''

        SELECT a.dept_code, d.count_recommend_principal 

        FROM evaluation_accounts a

        LEFT JOIN department_config d ON a.dept_code = d.dept_code

        WHERE a.username=?

    ''', (rater_account,)).fetchone()

    

    if not user_row: return jsonify({'success': False, 'msg': '璐﹀彿寮傚父'})

    

    limit_count = user_row['count_recommend_principal'] or 0

    

    if len(selected_ids) > limit_count:

        return jsonify({'success': False, 'msg': f'推荐人数超过限制锛佹渶澶氭帹鑽?{limit_count} 浜猴紝褰撳墠閫夋嫨浜?{len(selected_ids)} 浜恒€'})

        

    # 2. Save (Replace All logic)
    # New Logic: Record status for ALL candidates (1 for selected, 0 for others)
    try:
        cur = db.cursor()
        dept_code = user_row['dept_code']

        # 1. Fetch ALL candidates for this department
        all_candidates = db.execute('SELECT id, name FROM recommend_principal WHERE dept_code=?', (dept_code,)).fetchall()
        
        # 2. Clear old records for this user (Idempotency)
        cur.execute('DELETE FROM recommendation_scores_principal WHERE rater_account=?', (rater_account,))
        
        # 3. Convert selected_ids to set of ints for O(1) lookup
        selected_set = set()
        for sid in selected_ids:
            try:
                selected_set.add(int(sid))
            except (ValueError, TypeError):
                pass

        # 4. Insert record for EVERY candidate
        for cand in all_candidates:
            cid = cand['id']
            cname = cand['name']
            
            is_rec = 1 if cid in selected_set else 0
            
            cur.execute('''
                INSERT INTO recommendation_scores_principal (rater_account, target_dept_code, examinee_id, examinee_name, is_recommended)
                VALUES (?, ?, ?, ?, ?)
            ''', (rater_account, dept_code, cid, cname, is_rec))

        db.commit()
        return jsonify({'success': True, 'msg': '提交成功'})

        

    except Exception as e:

        db.rollback()

        return jsonify({'success': False, 'msg': str(e)})



# ==========================================

# 14. API: 浼樼骞查儴姘戜富鎺ㄨ崘-鍓亴 (New & Independent)

# ==========================================



@app.route('/assessment/recommend-deputy')

def assessment_recommend_deputy():

    # Recommend Deputy Page

    if session.get('assessor_role') != 'assessor':

        return redirect(url_for('index'))

        

    rater_account = session.get('assessor_username')

    db = get_db()

    

    # 1. Permission & Config Check

    user_row = db.execute('''

        SELECT a.username, a.dept_code, d.dept_name, d.count_recommend_deputy

        FROM evaluation_accounts a

        LEFT JOIN department_config d ON a.dept_code = d.dept_code

        WHERE a.username=?

    ''', (rater_account,)).fetchone()

    

    if not user_row: return "无效账号", 403

    

    limit_count = user_row['count_recommend_deputy'] or 0

    dept_name = user_row['dept_name']

    

    if limit_count < 1:

        return render_template('assessment_error.html', msg="贵部门无此项推荐名额")

        

    # 2. Fetch Candidates (recommend_deputy table)

    # [FILTER] Only show candidates from the same department

    dept_code = user_row['dept_code']

    candidates = db.execute('SELECT * FROM recommend_deputy WHERE dept_code=? ORDER BY sort_no ASC', (dept_code,)).fetchall()

    

    # 3. Fetch Existing Selections

    recs = db.execute('SELECT examinee_id FROM recommendation_scores_deputy WHERE rater_account=?', 

                      (rater_account,)).fetchall()

    selected_ids = [r['examinee_id'] for r in recs]

    

    page_title = f"{dept_name}优秀干部民主推荐-副职"

    

    return render_template('assessment_recommend_deputy.html',

                           page_title=page_title,

                           limit_count=limit_count,

                           candidates=candidates,

                           selected_ids=selected_ids)



@app.route('/api/assessment/recommend-deputy/submit', methods=['POST'])

def submit_recommend_deputy():

    if session.get('assessor_role') != 'assessor':

        return jsonify({'success': False, 'msg': '未登录'})



    req = request.json

    selected_ids = req.get('selected_ids', []) # List of IDs

    

    rater_account = session.get('assessor_username')

    db = get_db()

    

    # 1. Validation: Limit Check

    user_row = db.execute('''

        SELECT a.dept_code, d.count_recommend_deputy 

        FROM evaluation_accounts a

        LEFT JOIN department_config d ON a.dept_code = d.dept_code

        WHERE a.username=?

    ''', (rater_account,)).fetchone()

    

    if not user_row: return jsonify({'success': False, 'msg': '璐﹀彿寮傚父'})

    

    limit_count = user_row['count_recommend_deputy'] or 0

    

    if len(selected_ids) > limit_count:

        return jsonify({'success': False, 'msg': f'推荐人数超过限制锛佹渶澶氭帹鑽?{limit_count} 浜猴紝褰撳墠閫夋嫨浜?{len(selected_ids)} 浜恒€'})

        

    # 2. Save (Replace All logic)
    # New Logic: Record for ALL candidates
    try:
        cur = db.cursor()
        dept_code = user_row['dept_code']

        # 1. Fetch ALL candidates
        all_candidates = db.execute('SELECT id, name FROM recommend_deputy WHERE dept_code=?', (dept_code,)).fetchall()
        
        # 2. Clear old
        cur.execute('DELETE FROM recommendation_scores_deputy WHERE rater_account=?', (rater_account,))
        
        # 3. Process selection
        selected_set = set()
        for sid in selected_ids:
            try:
                selected_set.add(int(sid))
            except (ValueError, TypeError):
                pass
        
        # 4. Insert
        for cand in all_candidates:
            cid = cand['id']
            cname = cand['name']
            is_rec = 1 if cid in selected_set else 0
            
            cur.execute('''
                INSERT INTO recommendation_scores_deputy (rater_account, target_dept_code, examinee_id, examinee_name, is_recommended)
                VALUES (?, ?, ?, ?, ?)
            ''', (rater_account, dept_code, cid, cname, is_rec))

        db.commit()
        return jsonify({'success': True, 'msg': '提交成功'})

        

    except Exception as e:

        db.rollback()

        return jsonify({'success': False, 'msg': str(e)})



# ==========================================

# 15. API: 干部选拔任用工作民主评议表"(Project 6)

# ==========================================



@app.route('/assessment/selection-appointment')

def assessment_selection_appointment():

    # Selection Appointment Page

    if session.get('assessor_role') != 'assessor':

        return redirect(url_for('index'))

        

    rater_account = session.get('assessor_username')

    db = get_db()

    

    # 1. Permission Check

    user_row = db.execute('SELECT username, dept_code FROM evaluation_accounts WHERE username=?', (rater_account,)).fetchone()

    if not user_row: return "无效账号", 403

    

    # Allowed: V, W, X, Y

    allowed_depts = ['V', 'W', 'X', 'Y']

    if user_row['dept_code'] not in allowed_depts:

        return render_template('assessment_error.html', msg="鎮ㄧ殑璐﹀彿无权访问姝よ瘎璁〃")

        

    # 2. Fetch Existing Data

    existing = db.execute('SELECT * FROM evaluation_selection_appointment WHERE rater_account=?', (rater_account,)).fetchone()

    

    d_row = db.execute('SELECT dept_name FROM department_config WHERE dept_code=?', (user_row['dept_code'],)).fetchone()

    dept_name = d_row['dept_name'] if d_row else ""

    

    return render_template('assessment_selection_appointment.html',

                           page_title=f"{dept_name}干部选拔任用工作民主评议表",

                           data=existing)



@app.route('/api/assessment/selection-appointment/submit', methods=['POST'])

def submit_selection_appointment():

    if session.get('assessor_role') != 'assessor':

        return jsonify({'success': False, 'msg': '未登录'})



    req = request.json

    rater_account = session.get('assessor_username')

    db = get_db()

    

    # 1. Permission Check

    user_row = db.execute('SELECT username, dept_code FROM evaluation_accounts WHERE username=?', (rater_account,)).fetchone()

    if not user_row or user_row['dept_code'] not in ['V', 'W', 'X', 'Y']:

        return jsonify({'success': False, 'msg': '无权操作'})

        

    # 2. Extract Data

    q1 = req.get('q1_overall')

    q2 = req.get('q2_supervision')

    q3 = req.get('q3_rectification')

    # q1-q3 are required

    if not all([q1, q2, q3]):

         return jsonify({'success': False, 'msg': '请完成前三项必填评价锛'})

         

    q4 = req.get('q4_problems', '') # String? JSON? Frontend sends comma-separated string likely.

    q5 = req.get('q5_suggestions_employment', '')

    q6 = req.get('q6_suggestions_report', '')

    

    dept_code = user_row['dept_code']

    

    try:

        cur = db.cursor()

        # Check exist

        exist = cur.execute('SELECT id FROM evaluation_selection_appointment WHERE rater_account=?', (rater_account,)).fetchone()

        

        if exist:

            cur.execute('''

                UPDATE evaluation_selection_appointment 

                SET q1_overall=?, q2_supervision=?, q3_rectification=?, 

                    q4_problems=?, q5_suggestions_employment=?, q6_suggestions_report=?, updated_at=CURRENT_TIMESTAMP

                WHERE rater_account=?

            ''', (q1, q2, q3, q4, q5, q6, rater_account))

        else:

            cur.execute('''

                INSERT INTO evaluation_selection_appointment 

                (rater_account, dept_code, q1_overall, q2_supervision, q3_rectification, q4_problems, q5_suggestions_employment, q6_suggestions_report)

                VALUES (?, ?, ?, ?, ?, ?, ?, ?)

            ''', (rater_account, dept_code, q1, q2, q3, q4, q5, q6))

            

        db.commit()

        return jsonify({'success': True, 'msg': '提交成功'})

        

    except Exception as e:

        db.rollback()

        return jsonify({'success': False, 'msg': str(e)})



# ==========================================

# 16. API: 新提拔任用干部民主评议表 (Project 7)

# ==========================================



@app.route('/assessment/new-promotion')

def assessment_new_promotion():

    # New Promotion Page

    if session.get('assessor_role') != 'assessor':

        return redirect(url_for('index'))

        

    rater_account = session.get('assessor_username')

    db = get_db()

    

    # 1. Permission Check (X, Y)

    user_row = db.execute('SELECT username, dept_code FROM evaluation_accounts WHERE username=?', (rater_account,)).fetchone()

    if not user_row: return "无效账号", 403

    

    allowed_depts = ['X', 'Y']

    if user_row['dept_code'] not in allowed_depts:

        return render_template('assessment_error.html', msg="鎮ㄧ殑璐﹀彿无权访问姝よ瘎璁〃")

        

    # 2. Fetch Candidates

    # [UPDATED Project 8]: Source from `center_grassroots_leaders` table now.

    # Criteria: dept_code matches user's dept_code (X or Y)

    # The table `center_grassroots_leaders` stores all needed info. 

    # Logic: simple SELECT * WHERE dept_code=?

    

    candidates = db.execute('''

        SELECT * FROM center_grassroots_leaders 

        WHERE dept_code=? AND is_newly_promoted='是'

        ORDER BY sort_no ASC, id ASC

    ''', (user_row['dept_code'],)).fetchall()

    

    # 3. Fetch Existing Selections

    existing_row = db.execute('SELECT selections FROM evaluation_new_promotion WHERE rater_account=?', (rater_account,)).fetchone()

    existing_data = {}

    if existing_row and existing_row['selections']:

        import json

        try:

            existing_data = json.loads(existing_row['selections'])

        except:

            existing_data = {}

    

    d_row = db.execute('SELECT dept_name FROM department_config WHERE dept_code=?', (user_row['dept_code'],)).fetchone()

    dept_name = d_row['dept_name'] if d_row else ""

    

    return render_template('assessment_new_promotion.html',

                           page_title=f"{dept_name}新提拔任用干部民主评议表",

                           candidates=candidates,

                           existing_data=existing_data)



@app.route('/api/assessment/new-promotion/submit', methods=['POST'])

def submit_new_promotion():

    if session.get('assessor_role') != 'assessor':

        return jsonify({'success': False, 'msg': '未登录'})



    req = request.json

    selections = req.get('selections', {}) # Dict {id: value}

    

    rater_account = session.get('assessor_username')

    db = get_db()

    

    # Permission Check

    user_row = db.execute('SELECT username, dept_code FROM evaluation_accounts WHERE username=?', (rater_account,)).fetchone()

    if not user_row or user_row['dept_code'] not in ['X', 'Y']:

        return jsonify({'success': False, 'msg': '无权操作'})

        

    dept_code = user_row['dept_code']

    

    try:

        cur = db.cursor()

        import json

        json_str = json.dumps(selections, ensure_ascii=False)

        

        # Upsert

        exist = cur.execute('SELECT id FROM evaluation_new_promotion WHERE rater_account=?', (rater_account,)).fetchone()

        

        if exist:

            cur.execute('''

                UPDATE evaluation_new_promotion 

                SET selections=?, updated_at=CURRENT_TIMESTAMP

                WHERE rater_account=?

            ''', (json_str, rater_account))

        else:

            cur.execute('''

                INSERT INTO evaluation_new_promotion (rater_account, dept_code, selections)

                VALUES (?, ?, ?)

            ''', (rater_account, dept_code, json_str))

            

        db.commit()

        return jsonify({'success': True, 'msg': '提交成功'})

        

    except Exception as e:

        db.rollback()

        return jsonify({'success': False, 'msg': str(e)})



# ==========================================

# 17. API: 涓績鍩哄眰棰嗗绠＄悊 (Project 8)

# ==========================================



ALLOWED_ROLES_CGL = ['涓績鍩哄眰棰嗗'] # Or any validation we want? Maybe reuse or just loose check.



CENTER_GRASSROOTS_MAPPING = {

    # '搴忓彿' removed as not in user list, optional anyway

    '部门内排序号': 'sort_no',

    '姓名': 'name',

    '性别': 'gender',

    '出生年月': 'birth_date',

    '现任职务': 'position',      # Was '鑱屽姟'

    '部门名称': 'dept_name',

    '部门代码': 'dept_code',     # Was '閮ㄩ棬缂栫爜'

    '员工角色': 'role',

    '岗位层级': 'rank_level',

    '任职时间': 'tenure_time',

    '文化程度': 'education',

    '现职级时间': 'rank_time',

    

    # New Columns

    '原任职务': 'original_position',

    '提拔方式': 'promotion_method',

    '是否新提拔干部': 'is_newly_promoted'

}



@app.route('/center-grassroots-management')

@admin_required

def center_grassroots_management():

    # Center Grassroots Management Page

    db = get_db()

    managers = db.execute('SELECT * FROM center_grassroots_leaders ORDER BY dept_code ASC, sort_no ASC').fetchall()

    return render_template('center_grassroots_management.html', managers=managers)



@app.route('/api/center-grassroots/upload', methods=['POST'])

@admin_required

def upload_center_grassroots():

    if 'file' not in request.files: return jsonify({'success': False, 'msg': '无文件'})

    file = request.files['file']

    try:

        df = pd.read_excel(file)

        df = df.fillna('')

        # Strip whitespace from columns

        df.columns = df.columns.str.strip()

        

        # Validation: Check required columns

        required_cols = ['姓名', '现任职务', '部门名称']

        missing = [c for c in required_cols if c not in df.columns]

        if missing:

             return jsonify({'success': False, 'msg': f'导入失败锛氱己灏戝繀瑕佸垪 {", ".join(missing)}'})

             

        for col in ['出生年月', '现职级时间', '任职时间']:

            if col in df.columns:

                df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y/%m').fillna('')

        

        db = get_db()

        cursor = db.cursor()

        

        # Dept Map for automated dept_id filling

        dept_rows = db.execute('SELECT id, dept_name FROM department_config').fetchall()

        dept_map = {row['dept_name']: row['id'] for row in dept_rows}



        # Replace All

        cursor.execute('DELETE FROM center_grassroots_leaders')

        

        for _, row in df.iterrows():

            cols, vals = [], []

            for excel_col, db_col in CENTER_GRASSROOTS_MAPPING.items():

                if excel_col in df.columns:

                    cols.append(db_col)

                    val = row[excel_col]

                    if val == '' and 'no' in db_col: val = 0

                    vals.append(val)

            

            # Auto-fill dept_id if possible

            if '部门名称' in df.columns and row['部门名称'] in dept_map:

                cols.append('dept_id')

                vals.append(dept_map[row['部门名称']])

                

            if cols:

                cursor.execute(f'INSERT INTO center_grassroots_leaders ({", ".join(cols)}) VALUES ({", ".join(["?"]*len(cols))})', vals)

                

        db.commit()

        return jsonify({'success': True, 'msg': f'导入成功: {len(df)} 浜'})

    except Exception as e:

        return jsonify({'success': False, 'msg': str(e)})



@app.route('/api/center-grassroots/save', methods=['POST'])

@admin_required

def save_center_grassroots():

    req = request.json

    if not req or 'data' not in req: return jsonify({'success': False, 'msg': '无数据'})

    db = get_db()

    cursor = db.cursor()

    

    dept_rows = db.execute('SELECT id, dept_name FROM department_config').fetchall()

    dept_map = {row['dept_name']: row['id'] for row in dept_rows}

    

    try:

        cursor.execute('DELETE FROM center_grassroots_leaders')

        for row in req['data']:

            if not row.get('name'): continue

            cols, vals = [], []

            for db_col in CENTER_GRASSROOTS_MAPPING.values():

                cols.append(db_col)

                vals.append(row.get(db_col, ''))

                

            if row.get('dept_name') in dept_map:

                cols.append('dept_id')

                vals.append(dept_map[row.get('dept_name')])



            cursor.execute(f'INSERT INTO center_grassroots_leaders ({", ".join(cols)}) VALUES ({", ".join(["?"]*len(cols))})', vals)

            

        db.commit()

        return jsonify({'success': True, 'msg': '保存成功'})

    except Exception as e:

        db.rollback()

        return jsonify({'success': False, 'msg': str(e)})



@app.route('/api/center-grassroots/export')

@admin_required

def export_center_grassroots():

    try:

        db = get_db()

        df = pd.read_sql_query("SELECT * FROM center_grassroots_leaders ORDER BY dept_code ASC, sort_no ASC", db)

        for col in ['出生年月', '现职级时间', '任职时间']:

            if col in df.columns: df = df.drop(columns=[col])

            

        reverse_map = {v: k for k, v in CENTER_GRASSROOTS_MAPPING.items()}

        df = df.rename(columns=reverse_map)

        

        # Ensure order of columns if possible, but map keys sort is randomish.

        # We can enforce a list logic if we really want, but Excel output usually OK.

        

        output = BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:

            df.to_excel(writer, index=False, sheet_name='涓績鍩哄眰棰嗗浜哄憳')

        output.seek(0)

        return send_file(output, as_attachment=True, download_name='涓績鍩哄眰棰嗗鍚嶅崟.xlsx')

    except Exception as e:

        return str(e)


# 17. Project 9: Unified Submission System (Overview & Final Submit)

# ==========================================





# ==========================================
# 17. Project 9: Unified Submission System (Overview & Final Submit)
# ==========================================

def check_assessment_progress(user_row):
    """
    Helper to check which projects are required and their completion status.
    Returns: list of dicts {'key': '...', 'name': '...', 'url': '...', 'completed': bool}
    """
    if not user_row: return []
    
    # Fix: Convert Row to dict to allow .get()
    user_row = dict(user_row)
    
    db = get_db()
    rater_account = user_row['username']
    dept_code = user_row['dept_code']
    dept_type = user_row.get('dept_type', '')
    
    projects = []
    
    # helper
    def add_proj(key, name, url, completed, **kwargs):
        target = '#'
        if url:
            try:
                target = url_for(url, **kwargs)
            except Exception:
                target = '#'
        projects.append({'key': key, 'name': name, 'url': target, 'completed': completed})

    # --- 1. Team Evaluation (Project 2) ---
    # Everyone except college leader? Usually all assessors do this unless restricted.
    # Base template logic: `if session.get('assessor_dept_type') != '院领导'`
    if dept_type != '院领导':
        # Check if score exists
        row = db.execute('SELECT id FROM team_scores WHERE rater_account=?', (rater_account,)).fetchone()
        add_proj('team', '领导班子综合考核评价', 'assessment_team', bool(row))
        
        # --- 2. Personnel Evaluation (Project 2/General) ---
        # Same condition. Also depends on 'count_excellent' > 0?
        # App logic: if count_excellent <= 0, page shows error.
        # Check config:
        d_conf = db.execute('SELECT count_excellent FROM department_config WHERE dept_code=?', (dept_code,)).fetchone()
        if d_conf and d_conf['count_excellent'] > 0:
            # Check if scores exist. 
            # Strict rule: Must rate ALL valid managers in dept?
            # Or just "submitted something"?
            # Let's check if they have rated at least one person? Or verify counts.
            # Simplified: Check if any row exists.
            p_row = db.execute('SELECT id FROM personnel_scores WHERE rater_account=?', (rater_account,)).fetchone()
            add_proj('personnel', '领导人员综合考核评价', 'assessment_personnel', bool(p_row))

    # --- 3. Democratic Evaluation (Project 1/3) ---
    nav_items = get_democratic_nav(user_row)
    if nav_items:
        # Check completion for ALL sub-items (groups)
        all_subs_done = True
        target_jump_key = nav_items[0]['key']
        found_incomplete = False
        
        for item in nav_items:
            # Check DB for this specific group
            # match by roles defined in nav_item
            roles = item.get('roles', [])
            if not roles:
                has_score = False
            else:
                # Map roles to DB values (Logic copied from assessment_democratic route)
                db_roles = []
                for r in roles:
                    if r == '两中心正职': db_roles.append('中心正职')
                    elif r == '两中心副职': db_roles.append('中心副职')
                    elif r == '所属分公司 (兰州、抚顺) 班子正职': db_roles.append('中心正职')
                    elif r == '所属分公司 (兰州、抚顺) 班子副职': db_roles.append('中心副职')
                    elif r == '昆冈班子副职 (北京)': db_roles.append('中心副职')
                    elif r == '昆冈班子正职': db_roles.append('中心正职') # Assuming mapping if exists
                    else: db_roles.append(r)
                
                db_roles = list(set(db_roles)) # Unique
                
                placeholders = ','.join(['?'] * len(db_roles))
                # Check directly in democratic_scores which stores examinee_role (mapped)
                query = f"SELECT 1 FROM democratic_scores WHERE rater_account=? AND examinee_role IN ({placeholders}) LIMIT 1"
                params = [rater_account] + db_roles
                has_score = db.execute(query, params).fetchone()
            
            if not has_score:
                all_subs_done = False
                if not found_incomplete:
                    target_jump_key = item['key']
                    found_incomplete = True
        
        # Add single project item, completed only if ALL sub-groups are done
        # Link jumps to the first incomplete group (or the first group if all done)
        add_proj('democratic', '中层干部民主测评', 'assessment_democratic', all_subs_done, group_key=target_jump_key)

    # --- 4. Recommend Principal (Project 3/Standard) ---
    d_conf = db.execute('SELECT count_recommend_principal FROM department_config WHERE dept_code=?', (dept_code,)).fetchone()
    if d_conf and d_conf['count_recommend_principal'] and d_conf['count_recommend_principal'] >= 1:
        # Check existing
        row = db.execute('SELECT id FROM recommendation_scores_principal WHERE rater_account=?', (rater_account,)).fetchone()
        add_proj('rec_principal', '优秀干部民主推荐-正职', 'assessment_recommend_principal', bool(row))

    # --- 5. Recommend Deputy (Project 4) ---
    d_conf = db.execute('SELECT count_recommend_deputy FROM department_config WHERE dept_code=?', (dept_code,)).fetchone()
    if d_conf and d_conf['count_recommend_deputy'] and d_conf['count_recommend_deputy'] >= 1:
         row = db.execute('SELECT id FROM recommendation_scores_deputy WHERE rater_account=?', (rater_account,)).fetchone()
         add_proj('rec_deputy', '优秀干部民主推荐-副职', 'assessment_recommend_deputy', bool(row))

    # --- 6. Selection Appointment (Project 6) ---
    if dept_code in ['V', 'W', 'X', 'Y']:
        row = db.execute('SELECT id FROM evaluation_selection_appointment WHERE rater_account=?', (rater_account,)).fetchone()
        add_proj('selection', '干部选拔任用工作民主评议表', 'assessment_selection_appointment', bool(row))

    # --- 7. New Promotion (Project 7) ---
    if dept_code in ['X', 'Y']:
        # This page uses `evaluation_new_promotion`
        row = db.execute('SELECT id FROM evaluation_new_promotion WHERE rater_account=?', (rater_account,)).fetchone()
        add_proj('new_promotion', '新提拔任用干部民主评议表', 'assessment_new_promotion', bool(row))

    return projects

@app.route('/assessment/overview')
def assessment_overview():
    # Assessment Overview Page
    if session.get('assessor_role') != 'assessor':
        return redirect(url_for('index'))
        
    rater_account = session.get('assessor_username')
    db = get_db()
    
    # Get User Info
    user_row = db.execute('''
        SELECT a.username, a.dept_code, a.account_type, d.dept_name, d.dept_type
        FROM evaluation_accounts a
        LEFT JOIN department_config d ON a.dept_code = d.dept_code
        WHERE a.username=?
    ''', (rater_account,)).fetchone()
    
    if not user_row: return "无效账号", 403
    
    # Check if already submitted
    acc_status = db.execute('SELECT status FROM evaluation_accounts WHERE username=?', (rater_account,)).fetchone()['status']
    is_submitted = (acc_status == '否')
    
    # Get Progress
    projects = check_assessment_progress(user_row)
    
    all_completed = all(p['completed'] for p in projects)
    
    return render_template('assessment_overview.html', 
                           projects=projects, 
                           all_completed=all_completed,
                           is_submitted=is_submitted)

@app.route('/api/assessment/final-submit', methods=['POST'])
def final_submit_assessment():
    # Final Submit API
    if session.get('assessor_role') != 'assessor':
        return jsonify({'success': False, 'msg': '未登录'})
        
    rater_account = session.get('assessor_username')
    db = get_db()
    
    # 1. Check if already submitted
    curr_status = db.execute('SELECT status FROM evaluation_accounts WHERE username=?', (rater_account,)).fetchone()['status']
    if curr_status == '否':
        return jsonify({'success': False, 'msg': '您已完成提交，请勿重复操作'})
        
    # 2. Re-validate Progress
    user_row = db.execute('''
        SELECT a.username, a.dept_code, a.account_type, d.dept_name, d.dept_type
        FROM evaluation_accounts a
        LEFT JOIN department_config d ON a.dept_code = d.dept_code
        WHERE a.username=?
    ''', (rater_account,)).fetchone()
    
    projects = check_assessment_progress(user_row)
    missing = [p['name'] for p in projects if not p['completed']]
    
    if missing:
        return jsonify({'success': False, 'msg': f'以下项目未完成或未保存：<br/>' + '<br/>'.join(missing)})
        
    # 3. Log and Lock
    try:
        ip_addr = request.remote_addr
        
        # Log
        db.execute('''
            INSERT INTO submission_logs (rater_account, ip_address)
            VALUES (?, ?)
        ''', (rater_account, ip_addr))
        
        # Lock Account
        db.execute('UPDATE evaluation_accounts SET status="否", updated_at=CURRENT_TIMESTAMP WHERE username=?', (rater_account,))
        
        db.commit()
        
        # Optional: Clear session? User might want to see success page.
        # User requirement: "submitted... record db...".
        # We process logout or simple success.
        
        return jsonify({'success': True, 'msg': '提交成功！感谢您的参与。'})
        
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'msg': str(e)})


# ==========================================
# 18. Account Management Implementation
# ==========================================

@app.route('/api/account/list')
@admin_required
def account_list():
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 30))
    offset = (page - 1) * limit
    
    dept_name = request.args.get('dept_name', '')
    dept_code = request.args.get('dept_code', '')
    atype = request.args.get('account_type', '')
    status = request.args.get('status', '')
    
    db = get_db()
    
    # Build Query
    where = []
    params = []
    
    if dept_name:
        where.append("dept_name LIKE ?")
        params.append(f"%{dept_name}%")
    if dept_code:
        where.append("dept_code LIKE ?")
        params.append(f"%{dept_code}%")
    if atype:
        where.append("account_type = ?")
        params.append(atype)
    if status:
        where.append("status = ?")
        params.append(status)
        
    where_sql = " AND ".join(where) if where else "1=1"
    
    # Count
    count_sql = f"SELECT count(*) FROM evaluation_accounts WHERE {where_sql}"
    total = db.execute(count_sql, params).fetchone()[0]
    
    # Data
    sql = f"SELECT * FROM evaluation_accounts WHERE {where_sql} ORDER BY dept_code ASC, account_type ASC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    rows = db.execute(sql, params).fetchall()
    data = [dict(r) for r in rows]
    
    return jsonify({'code': 0, 'msg': '', 'count': total, 'data': data})

@app.route('/api/account/generate', methods=['POST'])
@admin_required
def account_generate():
    db = get_db()
    
    # 1. Get Dept Configs
    depts = db.execute('SELECT * FROM department_config').fetchall()
    
    generated_count = 0
    
    # Define Types and Suffixes
    # Map: DB Column -> (Type Name, Suffix)
    type_map = {
        'count_college_leader': ('院领导', 'L'),
        'count_principal': ('正职', 'Z'),
        'count_deputy': ('副职', 'F'),
        'count_center_leader': ('中心基层领导', 'C'),
        'count_other': ('其他员工', 'E')
    }
    
    try:
        for d in depts:
            d_code = d['dept_code']
            d_name = d['dept_name']
            
            for col, (type_name, suffix) in type_map.items():
                count = d[col]
                if not count or count <= 0: continue
                
                for i in range(1, count + 1):
                    # Format: Code + Suffix + 2 digit index (e.g., A01L01)
                    username = f"{d_code}{suffix}{i:02d}"
                    
                    # Check existence
                    exists = db.execute('SELECT id FROM evaluation_accounts WHERE username=?', (username,)).fetchone()
                    if exists: continue
                    
                    # Create
                    password = ''.join(random.choices(string.digits, k=6)) # Random 6 digits
                    
                    db.execute('''
                        INSERT INTO evaluation_accounts (username, password, dept_code, dept_name, account_type, status)
                        VALUES (?, ?, ?, ?, ?, '是')
                    ''', (username, password, d_code, d_name, type_name))
                    
                    generated_count += 1
                    
        db.commit()
        return jsonify({'success': True, 'msg': f'生成成功，新增 {generated_count} 个账号'})
        
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/account/clear', methods=['POST'])
@admin_required
def account_clear():
    db = get_db()
    try:
        db.execute('DELETE FROM evaluation_accounts')
        db.commit()
        return jsonify({'success': True, 'msg': '已清空所有生成的账号'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/account/save', methods=['POST'])
@admin_required
def account_save():
    req = request.json
    if not req or 'data' not in req: return jsonify({'success': False, 'msg': '无数据'})
    
    updates = req['data']
    db = get_db()
    
    try:
        count = 0
        for item in updates:
            aid = item.get('id')
            pwd = item.get('password')
            status = item.get('status')
            
            if aid and pwd and status:
                db.execute('UPDATE evaluation_accounts SET password=?, status=? WHERE id=?', (pwd, status, aid))
                count += 1
                
        db.commit()
        return jsonify({'success': True, 'msg': f'保存成功，更新 {count} 条记录'})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/examinee-summary/export')
@admin_required
def examinee_summary_export():
    """导出汇总得分"""
    try:
        db = get_db()
        data = db.execute('SELECT * FROM examinee_score_summary ORDER BY id ASC').fetchall()
        
        # ... (Existing export logic, or simplified)
        # Use pandas for easy export
        df = pd.DataFrame([dict(row) for row in data])
        # Columns mapping... (omitted for brevity, assume simple dump or can be improved)
        
        # Create a BytesIO buffer
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        output.seek(0)
        
        return send_file(output, download_name='被考核人汇总得分.xlsx', as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})


# ==========================================
# Team Score Summary APIs (Department Level)
# ==========================================

@app.route('/api/team-score-summary/list')
@admin_required
def team_score_summary_list():
    """获取领导班子汇总得分列表"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 30))
        offset = (page - 1) * limit
        
        db = get_db()
        count = db.execute('SELECT COUNT(*) FROM team_score_summary').fetchone()[0]
        rows = db.execute('SELECT * FROM team_score_summary ORDER BY id ASC LIMIT ? OFFSET ?', (limit, offset)).fetchall()
        
        return jsonify({
            'success': True,
            'count': count,
            'data': [dict(row) for row in rows]
        })
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/team-score-summary/calculate', methods=['POST'])
@admin_required
def team_score_summary_calculate():
    """计算领导班子汇总得分 - 职能部门专用 (融合版)"""
    import re
    try:
        db = get_db()
        cursor = db.cursor()
        
        # 1. Clear Table
        cursor.execute('DELETE FROM team_score_summary')
        
        # 2. Load Data Sources
        # 2.1 Examinee Summary (for direct copy fields)
        examinee_rows = db.execute('''
            SELECT s.*, m.dept_code, m.role, m.sort_no, dc.dept_type
            FROM examinee_score_summary s
            JOIN middle_managers m ON s.examinee_id = m.id
            LEFT JOIN department_config dc ON m.dept_code = dc.dept_code
            WHERE m.dept_code NOT IN ('A0', 'A1', 'M1', 'M2', 'U')
        ''').fetchall()
        
        # 2.2 Democratic Score Details (for fusion)
        demo_details = db.execute('SELECT name, score, rater_account FROM democratic_score_details').fetchall()
        demo_map = {} # name -> list of {rater_account, score}
        for d in demo_details:
            n = d['name']
            if n not in demo_map: demo_map[n] = []
            demo_map[n].append({'rater_account': d['rater_account'], 'score': d['score']})
        
        # 2.3 Team Score Details (for fusion)
        tsd_rows = db.execute('SELECT dept_code, rater_account, score FROM team_score_details').fetchall()
        tsd_map = {} # dept_code -> list of {rater_account, score}
        for t in tsd_rows:
            dc = (t['dept_code'] or '').strip()
            if dc:
                if dc not in tsd_map: tsd_map[dc] = []
                tsd_map[dc].append({'rater_account': (t['rater_account'] or '').strip(), 'score': t['score']})
        
        # 2.4 Account Info (for role deduction)
        accounts = db.execute('''
            SELECT ea.username, ea.account_type, ea.dept_code, ea.dept_name, dc.dept_type
            FROM evaluation_accounts ea
            LEFT JOIN department_config dc ON ea.dept_code = dc.dept_code
        ''').fetchall()
        account_info = {(a['username'] or '').strip(): dict(a) for a in accounts if a['username']}
        
        # Helper: Deduce Role from Username
        def get_role_char(rater_acc):
            acc = account_info.get(rater_acc, {})
            acc_type = acc.get('account_type', '')
            if acc_type == '正职': return 'P'
            if acc_type == '副职': return 'D'
            if acc_type == '其他员工': return 'E'
            # Fallback: Parse Username
            match = re.match(r'^([A-Z]+)([PDEC])\d+$', rater_acc)
            if match:
                return match.group(2)
            return None
        
        # 3. Group Examinees by Dept, pick Principal (sort_no=1 or min)
        dept_principal_map = {} # dept_code -> row (first principal)
        for row in examinee_rows:
            dc = row['dept_code']
            if dc not in dept_principal_map:
                dept_principal_map[dc] = dict(row)
            elif row['sort_no'] < dept_principal_map[dc].get('sort_no', 999):
                dept_principal_map[dc] = dict(row)
        
        # 4. Calculate for Each Department
        insert_list = []
        for dept_code, principal_row in dept_principal_map.items():
            dept_type = principal_row.get('dept_type', '')
            dept_name = principal_row.get('dept_name', '')
            principal_name = principal_row.get('name', '')
            
            # Direct Copy Fields (from principal's examinee summary)
            score_college_leader = principal_row.get('score_college_leader', 0)
            score_inst_principal = principal_row.get('score_inst_principal', 0)
            score_center_kungang = principal_row.get('score_center_kungang', 0)
            # Other fields for non-functional depts (will be overwritten if applicable)
            score_func_principal = principal_row.get('score_func_principal', 0)
            score_inst_abc_weighted = principal_row.get('score_inst_abc_weighted', 0)
            score_center_principal = principal_row.get('score_center_principal', 0)
            score_center_deputy = principal_row.get('score_center_deputy', 0)
            score_center_grassroot = principal_row.get('score_center_grassroot', 0)
            score_center_employee = principal_row.get('score_center_employee', 0)
            score_branch_principal = principal_row.get('score_branch_principal', 0)
            score_branch_deputy = principal_row.get('score_branch_deputy', 0)
            score_branch_weighted = principal_row.get('score_branch_weighted', 0)
            
            # FUSION CALCULATION (for 职能部门)
            if dept_type == '职能部门':
                # Merge Democratic (for principal) + Team Score (for dept)
                p_scores = []
                d_scores = []
                e_scores = []
                
                # Democratic
                for vote in demo_map.get(principal_name, []):
                    role = get_role_char(vote['rater_account'])
                    if role == 'P': p_scores.append(vote['score'])
                    elif role == 'D': d_scores.append(vote['score'])
                    elif role == 'E': e_scores.append(vote['score'])
                    # Ignore other roles
                    
                # Team Score
                for vote in tsd_map.get(dept_code, []):
                    role = get_role_char(vote['rater_account'])
                    if role == 'P': p_scores.append(vote['score'])
                    elif role == 'D': d_scores.append(vote['score'])
                    elif role == 'E': e_scores.append(vote['score'])
                
                # Fused ABC Weighted
                all_abc = p_scores + d_scores + e_scores
                score_func_abc_weighted = (sum(all_abc) / len(all_abc) * 0.30) if all_abc else 0
                
                # Get original examinee total components and recalculate with fused ABC
                # Original: total = college_leader + abc + inst_principal + center_kungang
                # New: replace abc with fused abc
                original_abc = principal_row.get('score_func_abc_weighted', 0) or 0
                original_bc = principal_row.get('score_func_bc_weighted', 0) or 0
                original_total = principal_row.get('total_score', 0) or 0
                
                # Calculate difference and adjust
                # If original used ABC, replace; if used BC (副职), replace BC
                if original_abc > 0:
                    total_score = original_total - original_abc + score_func_abc_weighted
                elif original_bc > 0:
                    # For 副职, also recalculate with fusion
                    total_score = original_total - original_bc + score_func_abc_weighted
                else:
                    # Use fused ABC + direct copy fields
                    total_score = score_college_leader + score_func_abc_weighted + score_inst_principal + score_center_kungang
            
            elif dept_type == '研究所':
                # FUSION CALCULATION (for 研究所)
                p_scores = []
                d_scores = []
                e_scores = []
                
                # Democratic
                for vote in demo_map.get(principal_name, []):
                    role = get_role_char(vote['rater_account'])
                    if role == 'P': p_scores.append(vote['score'])
                    elif role == 'D': d_scores.append(vote['score'])
                    elif role == 'E': e_scores.append(vote['score'])
                    
                # Team Score
                for vote in tsd_map.get(dept_code, []):
                    role = get_role_char(vote['rater_account'])
                    if role == 'P': p_scores.append(vote['score'])
                    elif role == 'D': d_scores.append(vote['score'])
                    elif role == 'E': e_scores.append(vote['score'])
                
                # Fused Institute ABC Weighted
                all_abc = p_scores + d_scores + e_scores
                score_inst_abc_weighted = (sum(all_abc) / len(all_abc) * 0.30) if all_abc else 0
                
                # Total Score (Institute)
                total_score = score_college_leader + score_func_principal + score_inst_abc_weighted + score_center_kungang
            
            elif dept_name in ['大庆化工研究中心', '兰州化工研究中心']:
                # FUSION CALCULATION (for 两中心)
                p_scores = []
                d_scores = []
                e_scores = []
                c_scores = []
                
                # Democratic
                for vote in demo_map.get(principal_name, []):
                    role = get_role_char(vote['rater_account'])
                    if role == 'P': p_scores.append(vote['score'])
                    elif role == 'D': d_scores.append(vote['score'])
                    elif role == 'E': e_scores.append(vote['score'])
                    elif role == 'C': c_scores.append(vote['score'])
                    
                # Team Score
                for vote in tsd_map.get(dept_code, []):
                    role = get_role_char(vote['rater_account'])
                    if role == 'P': p_scores.append(vote['score'])
                    elif role == 'D': d_scores.append(vote['score'])
                    elif role == 'E': e_scores.append(vote['score'])
                    elif role == 'C': c_scores.append(vote['score'])
                
                # Fused Scores
                all_pd = p_scores + d_scores
                score_center_kungang = (sum(all_pd) / len(all_pd) * 0.10) if all_pd else 0
                score_center_grassroot = (sum(c_scores) / len(c_scores) * 0.20) if c_scores else 0
                score_center_employee = (sum(e_scores) / len(e_scores) * 0.10) if e_scores else 0
                
                # Total Score (Two Centers)
                total_score = score_college_leader + score_func_principal + score_center_kungang + score_center_grassroot + score_center_employee
            
            elif dept_name in ['昆冈兰州分公司', '昆冈抚顺分公司']:
                # FUSION CALCULATION (for 昆冈分公司)
                p_scores = []
                d_scores = []
                e_scores = []
                c_scores = []
                
                # Democratic
                for vote in demo_map.get(principal_name, []):
                    role = get_role_char(vote['rater_account'])
                    if role == 'P': p_scores.append(vote['score'])
                    elif role == 'D': d_scores.append(vote['score'])
                    elif role == 'E': e_scores.append(vote['score'])
                    elif role == 'C': c_scores.append(vote['score'])
                    
                # Team Score
                for vote in tsd_map.get(dept_code, []):
                    role = get_role_char(vote['rater_account'])
                    if role == 'P': p_scores.append(vote['score'])
                    elif role == 'D': d_scores.append(vote['score'])
                    elif role == 'E': e_scores.append(vote['score'])
                    elif role == 'C': c_scores.append(vote['score'])
                
                # Fused Scores
                all_pd = p_scores + d_scores
                score_branch_weighted = (sum(all_pd) / len(all_pd) * 0.10) if all_pd else 0
                score_center_grassroot = (sum(c_scores) / len(c_scores) * 0.20) if c_scores else 0
                score_center_employee = (sum(e_scores) / len(e_scores) * 0.10) if e_scores else 0
                
                # Keep direct copy fields
                score_kungang_principal = principal_row.get('score_kungang_principal', 0)
                score_kungang_deputy = principal_row.get('score_kungang_deputy', 0)
                
                # Total Score (Kungang Branch)
                total_score = (score_college_leader + score_func_principal 
                             + score_kungang_principal + score_kungang_deputy
                             + score_center_grassroot + score_center_employee + score_branch_weighted)
            
            else:
                # For other depts, just copy total from principal (for now)
                score_func_abc_weighted = principal_row.get('score_func_abc_weighted', 0)
                total_score = principal_row.get('total_score', 0)
            
            # Insert
            insert_list.append((
                dept_code, dept_name,
                score_college_leader, score_func_principal, round(score_func_abc_weighted, 2),
                score_inst_principal, score_inst_abc_weighted,
                score_center_principal, score_center_deputy, score_center_kungang,
                score_center_grassroot, score_center_employee,
                score_branch_principal, score_branch_deputy, score_branch_weighted,
                round(total_score, 2)
            ))
        
        cursor.executemany('''
            INSERT INTO team_score_summary (
                dept_code, dept_name, 
                score_college_leader, score_func_principal, score_func_abc_weighted,
                score_inst_principal, score_inst_abc_weighted,
                score_center_principal, score_center_deputy, score_center_kungang,
                score_center_grassroot, score_center_employee,
                score_branch_principal, score_branch_deputy, score_branch_weighted,
                total_score
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', insert_list)
        
        db.commit()
        return jsonify({'success': True, 'msg': f'计算完成，生成 {len(insert_list)} 条部门汇总'})
        
        
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/team-score-summary/clear', methods=['POST'])
@admin_required
def team_score_summary_clear():
    try:
        db = get_db()
        db.execute('DELETE FROM team_score_summary')
        db.commit()
        return jsonify({'success': True, 'msg': '已清空'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/team-score-summary/export')
@admin_required
def team_score_summary_export():
    try:
        db = get_db()
        data = db.execute('SELECT * FROM team_score_summary ORDER BY id ASC').fetchall()
        df = pd.DataFrame([dict(r) for r in data])
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        output.seek(0)
        
        return send_file(output, download_name='领导班子汇总得分.xlsx', as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})




# ==========================================
# 4.4 被考核人打分汇总 (Democratic Summary)
# ==========================================

# Summary Headers Configuration
SUMMARY_HEADERS = [
    # (Header Key, Header Display, Weight Key in DB)
    ('college_leader', '院领导评分', '院领导'),
    ('func_principal', '职能部门正职评分', '职能部门正职 (含院长助理)'), # Uses legacy key or new split key? Plan says '职能部门正职'
    ('func_deputy', '职能部门副职评分', '职能部门副职'),
    ('func_employee', '职能部门员工评分', '职能部门其他员工'),
    ('inst_principal', '研究所正职评分', '研究所正职'),
    ('inst_deputy', '研究所副职评分', '研究所副职'),
    ('inst_employee', '研究所其他员工评分', '研究所其他员工'),
    
    # Shared Columns
    ('center_kungang_principal', '中心及昆冈正职评分', '中心领导班子 (正职)'), # Key acts as representative
    ('center_kungang_deputy', '中心及昆冈副职评分', '中心领导班子 (副职)'),
    
    ('branch_principal', '昆冈分公司正职评分', '所属分公司班子正职'),
    ('branch_deputy', '昆冈分公司副职评分', '所属分公司班子副职')
]

# Detailed Mapping: Header Key -> List of Account Match Rules
# Rules: List of tuples (ConstraintType, Value)
# Constraint Types: 'dept_name', 'dept_type', 'dept_code', 'acc_type', 'acc_type_in'
SUMMARY_MAPPING_RULES = {
    'college_leader': [
        {'dept_name': '院领导', 'acc_type': '院领导'}
    ],
    'func_principal': [
        {'dept_type': '职能部门', 'acc_type': '正职'},
        {'dept_name': '院长助理', 'dept_code': 'A0'} # Special Case for A0
    ],
    'func_deputy': [
        {'dept_type': '职能部门', 'acc_type': '副职'}
    ],
    'func_employee': [
        {'dept_type': '职能部门', 'acc_type': '员工'},
        {'dept_type': '职能部门', 'acc_type': '其他员工'}
    ],
    'inst_principal': [
        {'dept_type': '研究所', 'acc_type': '正职'}
    ],
    'inst_deputy': [
        {'dept_type': '研究所', 'acc_type': '副职'}
    ],
    'inst_employee': [
        {'dept_type': '研究所', 'acc_type': '员工'},
        {'dept_type': '研究所', 'acc_type': '其他员工'}
    ],
    # Center + Kungang (Excluding Branch)
    'center_kungang_principal': [
        {'dept_type': '两中心', 'acc_type': '正职'},
        {'dept_type': '昆冈', 'acc_type': '正职'} # Includes Kungang Beijing
    ],
    'center_kungang_deputy': [
        {'dept_type': '两中心', 'acc_type': '副职'},
        {'dept_type': '昆冈', 'acc_type': '副职'}
    ],
    # Branch
    'branch_principal': [
         {'dept_name_contains': '分公司', 'acc_type': '正职'}
    ],
    'branch_deputy': [
         {'dept_name_contains': '分公司', 'acc_type': '副职'}
    ]
}

@app.route('/admin/democratic-summary')
@admin_required
def democratic_summary_page():
    return render_template('democratic_summary.html')

@app.route('/api/admin/democratic-summary/data')
@admin_required
def democratic_summary_data():
    db = get_db()
    
    # 1. Get all Examinees (Middle Managers)
    examinees = db.execute('SELECT m.id, m.name, m.dept_name, m.role, m.dept_code, m.sort_no FROM middle_managers m ORDER BY m.dept_code, m.sort_no').fetchall()
    
    # 2. Get all Scores
    sql = '''
        SELECT s.*, 
               a.dept_name as rater_dept_name, 
               a.dept_code as rater_dept_code,
               a.account_type as rater_acc_type,
               d.dept_type as rater_dept_type
        FROM democratic_scores s
        LEFT JOIN evaluation_accounts a ON s.rater_account = a.username
        LEFT JOIN department_config d ON a.dept_code = d.dept_code
    '''
    all_scores = db.execute(sql).fetchall()
    
    # Index scores by examinee_id
    scores_by_examinee = {}
    for s in all_scores:
        eid = s['examinee_id']
        if eid not in scores_by_examinee: scores_by_examinee[eid] = []
        scores_by_examinee[eid].append(s)
        
    # 3. Get Weights Config (Pre-load all)
    weight_rows = db.execute('SELECT * FROM weight_config_dept').fetchall()
    weight_map = {}
    for w in weight_rows:
        e_role = w['examinee_role']
        r_role = w['rater_role']
        val = w['weight']
        if e_role not in weight_map: weight_map[e_role] = {}
        weight_map[e_role][r_role] = val

    # --- NEW: Leader Individual Weights Config ---
    # 3a. Leader Account Mapping: username -> weight_key (e.g. A0L001 -> yang_weisheng)
    leader_map_rows = db.execute('SELECT account, leader_key FROM leader_account_mapping').fetchall()
    leader_acc_map = {r['account']: r['leader_key'] for r in leader_map_rows}

    # 3b. Leader Weights by Dept: dept_code -> { weight_key_X: val, ... }
    # columns in leader_weight_config: id, dept_code, dept_name, total_weight, w_yang_weisheng, ...
    leader_weight_rows = db.execute('SELECT * FROM leader_weight_config').fetchall()
    leader_dept_weights = {} 
    for r in leader_weight_rows:
        d_code = r['dept_code']
        # Convert row to dict, handling key linkage
        # Keys in DB are 'w_yang_weisheng', but map has 'yang_weisheng'. We need to be careful.
        leader_dept_weights[d_code] = dict(r)

    # Helper to check if a score matches a rule set
    def match_rule(score_row, rules):
        for rule in rules:
            match = True
            for k, v in rule.items():
                if k == 'dept_name' and score_row['rater_dept_name'] != v: match = False; break
                if k == 'dept_type' and score_row['rater_dept_type'] != v: match = False; break
                if k == 'dept_code': # Exact match or 'A0' special
                    if v == 'A0' and score_row['rater_dept_code'] == 'A0': pass
                    elif score_row['rater_dept_code'] != v: match = False; break
                if k == 'acc_type':
                    actual = score_row['rater_acc_type']
                    if actual != v and actual not in ['P','D','L','E','C']: 
                         if v=='正职' and actual=='P': pass
                         elif v=='副职' and actual=='D': pass
                         elif v=='院领导' and actual=='L': pass
                         elif (v=='员工' or v=='其他员工') and actual=='E': pass
                         elif v=='职工代表' and actual=='C': pass
                         else: match = False; break
                
                if k == 'dept_name_contains' and v not in (score_row['rater_dept_name'] or ''): match = False; break
                
            if match: return True
        return False

    # 4. Process Each Examinee
    results = []
    
    for ex in examinees:
        eid = ex['id']
        # Determine Config Role (for Weight Lookup)
        real_config_role = ex['role'] 
        if ex['dept_name'] == '院长助理': real_config_role = '院长助理'
        elif '职能' in str(ex['dept_name']) and '正职' in ex['role']: real_config_role = '职能部门正职'
        
        my_weights = weight_map.get(real_config_role)
        if not my_weights:
            if '院长助理' in str(ex['dept_name']): my_weights = weight_map.get('院长助理', {})
            elif '正职' in str(ex['role']) and '因为' not in str(ex['role']): pass
        if not my_weights: my_weights = {}

        my_scores = scores_by_examinee.get(eid, [])
        my_dept_code = ex['dept_code'] # For leader weight lookup

        row_data = {
            'id': eid,
            'name': ex['name'],
            'dept_name': ex['dept_name'],
            'total_score': 0
        }
        
        current_total = 0
        
        # Calculate Columns
        for col_key, col_name, weight_db_key in SUMMARY_HEADERS:
            mapping_rules = SUMMARY_MAPPING_RULES.get(col_key, [])
            
            # Find matching scores
            matched_scores_objs = [s for s in my_scores if match_rule(s, mapping_rules)]
            matched_vals = [s['total_score'] for s in matched_scores_objs]
            
            count = len(matched_vals)
            avg = sum(matched_vals) / count if count > 0 else 0
            
            weighted_score = 0
            w_display = 0 
            
            # --- Special Logic for College Leader ---
            if col_key == 'college_leader':
                # Individual Weight Calculation
                # Sum( Score * IndividualWeight% )
                # Find weights for this examinee's department
                l_weights = leader_dept_weights.get(my_dept_code, {})
                
                sum_weighted = 0
                total_w_used = 0
                
                for s_obj in matched_scores_objs:
                    rater_acc = s_obj['rater_account']
                    w_key_base = leader_acc_map.get(rater_acc) # e.g. 'yang_weisheng'
                    
                    if w_key_base:
                        # DB column is 'w_' + key
                        w_col = 'w_' + w_key_base
                        ind_w = l_weights.get(w_col, 0)
                    else:
                        ind_w = 0 # No mapping?
                        
                    sum_weighted += s_obj['total_score'] * (ind_w / 100.0)
                    total_w_used += ind_w
                
                weighted_score = sum_weighted
                w_display = total_w_used # Show total weight applied (e.g. 70 or 40+6+...)
                
            else:
                # Standard Logic
                w_val = my_weights.get(weight_db_key, 0)
                weighted_score = avg * (w_val / 100.0)
                w_display = w_val
            
            row_data[col_key] = {
                'avg': round(avg, 2),
                'count': count,
                'weight': w_display,
                'weighted_score': weighted_score
            }
            
            # Add to total ONLY if count>0 or specifically expected?
            # Usually only if scores exist. 
            # Exception: if weight is set but no scores, it's 0.
            current_total += weighted_score
                
        row_data['final_total'] = round(current_total, 2)
        results.append(row_data)
        
    return jsonify({'code': 0, 'data': results})

# ==========================================
# 19. API: 推荐明细查询 (Refactored for Snapshot Tables)
# ==========================================

# --- 页面路由 ---

@app.route('/admin/stats/recommendation/principal/details')
@admin_required
def recommendation_details_principal():
    return render_template('recommendation_details_advanced.html', 
                         page_title='后备干部推荐（正职）明细',
                         api_base='/api/recommendation-details/principal',
                         rec_title='是否推荐为单位（部门）正职')

@app.route('/admin/stats/recommendation/deputy/details')
@admin_required
def recommendation_details_deputy():
    return render_template('recommendation_details_advanced.html', 
                         page_title='后备干部推荐（副职）明细',
                         api_base='/api/recommendation-details/deputy',
                         rec_title='是否推荐为单位（部门）副职')

# --- 通用处理逻辑 (Factory Pattern) ---

def handle_rec_details_request(rec_type, action):
    # rec_type: 'principal' or 'deputy'
    # action: list, calculate, clear, save, export
    
    db = get_db()
    
    table_name = f'recommendation_details_{rec_type}'
    source_score_table = f'recommendation_scores_{rec_type}'
    source_person_table = f'recommend_people_{rec_type}' # WRONG NAME in DB, check DB.
    # Check initiate_db.py: 
    # Tables are: recommend_principal / recommend_deputy
    source_person_table = f'recommend_{rec_type}'
    
    if action == 'list':
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 30))
        offset = (page - 1) * limit
        
        # Filters
        name = request.args.get('name', '')
        dept_name = request.args.get('dept_name', '')
        rater = request.args.get('rater_account', '')
        
        where = []
        params = []
        if name:
            where.append("name LIKE ?")
            params.append(f"%{name}%")
        if dept_name:
            where.append("dept_name LIKE ?")
            params.append(f"%{dept_name}%")
        if rater:
            where.append("rater_account LIKE ?")
            params.append(f"%{rater}%")
            
        where_clause = "WHERE " + " AND ".join(where) if where else ""
        
        count = db.execute(f'SELECT count(*) FROM {table_name} {where_clause}', params).fetchone()[0]
        rows = db.execute(f'SELECT * FROM {table_name} {where_clause} ORDER BY dept_code ASC, rater_account ASC, sort_no ASC LIMIT ? OFFSET ?', params + [limit, offset]).fetchall()
        return jsonify({'count': count, 'data': [dict(r) for r in rows]})
        
    elif action == 'calculate':
        try:
            cur = db.cursor()
            cur.execute(f'DELETE FROM {table_name}') # Clear Snapshot
            
            # Join Logic:
            # We need to join Score Table (S) with Person Table (P).
            # S has: rater_account, examinee_id, is_recommended (0/1)
            # P has: id, name, gender, current_position, rank_level, education, birth_date, rank_time...
            
            # We insert into Snapshot Table.
            # is_recommended in snapshot should be '推荐' if S.is_recommended=1 else '' 
            
            sql = f'''
                INSERT INTO {table_name} (
                    sort_no, name, gender, current_position, rank_level, education, birth_date, rank_time,
                    is_recommended,
                    dept_name, dept_code, rater_account
                )
                SELECT 
                    ROW_NUMBER() OVER (ORDER BY p.dept_code ASC, s.rater_account ASC, p.sort_no ASC),
                    p.name, p.gender, p.current_position, p.rank_level, p.education, p.birth_date, p.rank_time,
                    CASE WHEN s.is_recommended = 1 THEN '推荐' ELSE '' END,
                    p.dept_name, p.dept_code, s.rater_account
                FROM {source_score_table} s
                JOIN {source_person_table} p ON s.examinee_id = p.id
            '''
            cur.execute(sql)
            db.commit()
            return jsonify({'success': True, 'msg': '计算完成'})
        except Exception as e:
            return jsonify({'success': False, 'msg': str(e)})

    elif action == 'clear':
        db.execute(f'DELETE FROM {table_name}')
        db.commit()
        return jsonify({'success': True, 'msg': '已清空'})
        
    elif action == 'save':
        try:
            data = request.json.get('data', [])
            cur = db.cursor()
            for item in data:
                # item: {id: 123, is_recommended: '推荐' or ''}
                val = item.get('is_recommended', '')
                cur.execute(f'UPDATE {table_name} SET is_recommended=? WHERE id=?', (val, item['id']))
            db.commit()
            return jsonify({'success': True, 'msg': '保存成功'})
        except Exception as e:
            return jsonify({'success': False, 'msg': str(e)})
            
    elif action == 'export':
        import pandas as pd
        from io import BytesIO
        
        rows = db.execute(f'SELECT * FROM {table_name} ORDER BY dept_code ASC, rater_account ASC, sort_no ASC').fetchall()
        if not rows: return "No Data", 404
        
        df = pd.DataFrame([dict(r) for r in rows])
        
        # Clean columns
        cols_map = {
            'sort_no': '序号',
            'name': '姓名', 
            'gender': '性别', 
            'current_position': '现职务', 
            'rank_level': '岗位层级', 
            'education': '文化程度', 
            'birth_date': '出生年月', 
            'rank_time': '现职级时间',
            'is_recommended': '是否推荐', # Title depends on type but simple is fine
            'dept_name': '部门名称', 
            'rater_account': '打分人'
        }
        
        # Title specific
        rec_title = '是否推荐为单位（部门）正职' if rec_type == 'principal' else '是否推荐为单位（部门）副职'
        cols_map['is_recommended'] = rec_title
        
        target_cols = ['sort_no', 'name', 'gender', 'current_position', 'rank_level', 'education', 
                       'birth_date', 'rank_time', 'is_recommended', 'dept_name', 'rater_account']
                       
        df = df[target_cols].rename(columns=cols_map)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        output.seek(0)
        
        filename = f'后备干部推荐_{"正职" if rec_type=="principal" else "副职"}_明细.xlsx'
        return send_file(output, as_attachment=True, download_name=filename)


# --- 路由绑定 ---

@app.route('/api/recommendation-details/<rec_type>/<action>', methods=['GET', 'POST'])
@admin_required
def api_recommendation_details_router(rec_type, action):
    if rec_type not in ['principal', 'deputy']: return "Invalid Type", 400
    if action not in ['list', 'calculate', 'clear', 'save', 'export']: return "Invalid Action", 400
    
    return handle_rec_details_request(rec_type, action)


# ==========================================
# 20. API: 推荐汇总 (Summary Snapshot)
# ==========================================

@app.route('/admin/stats/recommendation/principal/summary')
@admin_required
def recommendation_summary_principal():
    return render_template('recommendation_summary.html', 
                         page_title='后备干部推荐（正职）汇总',
                         api_base='/api/recommendation-summary/principal')

@app.route('/admin/stats/recommendation/deputy/summary')
@admin_required
def recommendation_summary_deputy():
    return render_template('recommendation_summary.html', 
                         page_title='后备干部推荐（副职）汇总',
                         api_base='/api/recommendation-summary/deputy')

# --- Summary Factory Logic ---

def handle_rec_summary_request(rec_type, action):
    db = get_db()
    table_name = f'recommendation_summary_{rec_type}'
    score_table = f'recommendation_scores_{rec_type}'
    person_table = f'recommend_{rec_type}'
    
    if action == 'list':
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 30))
        offset = (page - 1) * limit
        
        dept_name = request.args.get('dept_name', '')
        name = request.args.get('name', '')
        
        where = []
        params = []
        if dept_name:
            where.append("dept_name LIKE ?")
            params.append(f"%{dept_name}%")
        if name:
            where.append("name LIKE ?")
            params.append(f"%{name}%")
            
        where_clause = "WHERE " + " AND ".join(where) if where else ""
        
        # Order by Department -> Group (A/B/C/D/Total) -> Candidate (SortNo)
        # As requested: "先将评委分组为正职的显示完，再显示评委分组为副职的"
        orderby = "ORDER BY dept_code ASC, group_sort ASC, sort_no ASC"
        
        count = db.execute(f'SELECT count(*) FROM {table_name} {where_clause}', params).fetchone()[0]
        rows = db.execute(f'SELECT * FROM {table_name} {where_clause} {orderby} LIMIT ? OFFSET ?', params + [limit, offset]).fetchall()
        return jsonify({'count': count, 'data': [dict(r) for r in rows]})
        
    elif action == 'calculate':
        try:
            # 1. Clear old data
            db.execute(f'DELETE FROM {table_name}')
            
            # 2. Define Groups
            group_map = {
                '正职': ('A(正职)', 1),
                '副职': ('B(副职)', 2),
                '中心基层领导': ('C(中心基层领导)', 3),
                '其他': ('D(员工)', 4),
                '员工': ('D(员工)', 4),
                '其他员工': ('D(员工)', 4), # Logic fix: database uses '其他员工'
                '院领导': ('L(院领导)', 5)
            }
            
            # 3. Get all candidates grouped by department
            candidates = db.execute(f'SELECT * FROM {person_table} ORDER BY dept_code ASC, sort_no ASC').fetchall()
            if not candidates:
                return jsonify({'success': True, 'msg': '无候选人数据'})
                
            # Iterate distinct departments
            dept_codes = sorted(list(set([c['dept_code'] for c in candidates])))
            
            # Map Dept Code -> proper Dept Name (from department_config)
            # This is crucial for U, V, W, X, Y subsidiaries to show the Company Name, not "Marketing Dept"
            dept_config_rows = db.execute("SELECT dept_code, dept_name FROM department_config").fetchall()
            dept_name_map = {r['dept_code']: r['dept_name'] for r in dept_config_rows}
            special_subsidiary_codes = ['U', 'V', 'W', 'X', 'Y']

            cur = db.cursor()
            global_serial = 1
            
            for dcode in dept_codes:
                # Filter candidates for this dept
                dept_candidates = [c for c in candidates if c['dept_code'] == dcode]
                if not dept_candidates: continue 
                
                # Determine Display Dept Name
                display_dept_name = dept_candidates[0]['dept_name'] 
                if dcode in special_subsidiary_codes and dcode in dept_name_map:
                    display_dept_name = dept_name_map[dcode]
                
                # Get all VALID voters in this department
                voters_query = f'''
                    SELECT DISTINCT s.rater_account, a.account_type
                    FROM {score_table} s
                    LEFT JOIN evaluation_accounts a ON s.rater_account = a.username
                    WHERE s.target_dept_code = ?
                '''
                voters = db.execute(voters_query, (dcode,)).fetchall()
                
                total_valid_votes = len(voters)
                
                # Identify Active Groups
                group_voter_counts = {}
                for v in voters:
                    atype = v['account_type']
                    if atype in group_map:
                        gname, gsort = group_map[atype]
                        if gname not in group_voter_counts:
                            group_voter_counts[gname] = {'sort': gsort, 'count': 0}
                        group_voter_counts[gname]['count'] += 1
                
                active_group_names = sorted(group_voter_counts.keys(), key=lambda n: group_voter_counts[n]['sort'])
                
                # 1. Pre-calculate results for all candidates in this dept
                cand_results = []
                for cand in dept_candidates:
                    cid = cand['id']
                    
                    # Get recommendation counts
                    rec_query = f'''
                        SELECT a.account_type, COUNT(*) as cnt
                        FROM {score_table} s
                        LEFT JOIN evaluation_accounts a ON s.rater_account = a.username
                        WHERE s.target_dept_code = ? AND s.examinee_id = ? AND s.is_recommended = 1
                        GROUP BY a.account_type
                    '''
                    rec_counts_rows = db.execute(rec_query, (dcode, cid)).fetchall()
                    
                    group_rec_counts = {gn: 0 for gn in active_group_names}
                    for r in rec_counts_rows:
                        atype = r['account_type']
                        if atype in group_map:
                            gname, _ = group_map[atype]
                            if gname in group_rec_counts:
                                group_rec_counts[gname] += r['cnt']
                    
                    total_num = sum(group_rec_counts.values())
                    total_rate_str = "0.000%"
                    if total_valid_votes > 0:
                        total_rate_str = f"{(total_num / total_valid_votes * 100):.3f}%"
                    
                    cand_results.append({
                        'cand': cand,
                        'group_rec_counts': group_rec_counts,
                        'total_num': total_num,
                        'total_rate_str': total_rate_str
                    })

                # 2. Insert rows in display order: Group 1 (All Candidates), Group 2... Total (All Candidates)
                
                # Group Rows
                for gname in active_group_names:
                    gsort = group_voter_counts[gname]['sort']
                    denom = group_voter_counts[gname]['count']
                    for res in cand_results:
                        cand = res['cand']
                        num = res['group_rec_counts'][gname]
                        rate_str = f"{(num / denom * 100):.3f}%"
                        
                        cur.execute(f'''
                            INSERT INTO {table_name} 
                            (sort_no, group_name, group_sort, valid_votes, rec_count, rec_rate,
                             name, gender, current_position, rank_level, education, birth_date, rank_time,
                             dept_name, dept_code)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            global_serial, gname, gsort, denom, num, rate_str,
                            cand['name'], cand['gender'], cand['current_position'], cand['rank_level'], cand['education'], cand['birth_date'], cand['rank_time'],
                            display_dept_name, cand['dept_code']
                        ))
                        global_serial += 1
                
                # Subtotal (合计) Rows
                for res in cand_results:
                    cand = res['cand']
                    cur.execute(f'''
                        INSERT INTO {table_name} 
                        (sort_no, group_name, group_sort, valid_votes, rec_count, rec_rate,
                            name, gender, current_position, rank_level, education, birth_date, rank_time,
                            dept_name, dept_code)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        global_serial, '合计', 99, total_valid_votes, res['total_num'], res['total_rate_str'],
                        cand['name'], cand['gender'], cand['current_position'], cand['rank_level'], cand['education'], cand['birth_date'], cand['rank_time'],
                        display_dept_name, cand['dept_code']
                    ))
                    global_serial += 1
            
            db.commit()
            return jsonify({'success': True, 'msg': '汇总计算完成'})
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'msg': str(e)})

    elif action == 'clear':
        db.execute(f'DELETE FROM {table_name}')
        db.commit()
        return jsonify({'success': True, 'msg': '已清空'})
        
    elif action == 'export':
        import pandas as pd
        from io import BytesIO
        
        # Consistent ordering for export
        rows = db.execute(f'SELECT * FROM {table_name} ORDER BY dept_code ASC, group_sort ASC, sort_no ASC').fetchall()
        if not rows: return "No Data", 404
        
        df = pd.DataFrame([dict(r) for r in rows])
        
        if 'id' in df.columns: del df['id']
        
        # Rename Cols for Excel
        rename_map = {
            'sort_no': '序号', # Or Candidate Sort
            'group_name': '评委分组',
            'valid_votes': '有效票数',
            'name': '姓名',
            'dept_name': '部门',
            'gender': '性别',
            'current_position': '职务',
            'rank_level': '职务级别',
            'birth_date': '出生年月',
            'education': '文化程度',
            'rank_time': '职级时间',
            'rec_count': '推荐',
            'rec_rate': '推荐率'
        }
        
        col_order = ['sort_no', 'group_name', 'valid_votes', 'name', 'dept_name', 'gender', 'current_position', 'rank_level', 'birth_date', 'education', 'rank_time', 'rec_count', 'rec_rate']
        
        # Filter existing cols
        final_cols = [c for c in col_order if c in df.columns]
        df = df[final_cols].rename(columns=rename_map)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Summary')
        output.seek(0)
        
        filename = f'后备干部推荐_{"正职" if rec_type=="principal" else "副职"}_汇总.xlsx'
        return send_file(output, as_attachment=True, download_name=filename)
        
    return "Unknown Action", 400

@app.route('/api/recommendation-summary/<rec_type>/<action>', methods=['GET', 'POST'])
@admin_required
def api_recommendation_summary_router(rec_type, action):
    if rec_type not in ['principal', 'deputy']: return "Invalid Type", 400
    return handle_rec_summary_request(rec_type, action)

# ==========================================
# 21. 干部选拔任用民主评议表统计
# ==========================================

@app.route('/admin/stats/selection-appointment')
@admin_required
def selection_stats_page():
    return render_template('selection_stats.html')

@app.route('/api/selection-stats/calculate', methods=['POST'])
@admin_required
def selection_stats_calculate():
    """一键计算统计数据"""
    db = get_db()
    try:
        cursor = db.cursor()
        
        # 清空旧数据
        cursor.execute('DELETE FROM selection_stats_q123')
        cursor.execute('DELETE FROM selection_stats_q4')
        cursor.execute('DELETE FROM selection_stats_text')
        
        # 获取部门映射
        dept_map = {}
        for row in db.execute("SELECT dept_code, dept_name FROM department_config WHERE dept_code IN ('V','W','X','Y')").fetchall():
            dept_map[row['dept_code']] = row['dept_name']
        
        # ========== Q1-Q3 统计 ==========
        for q_field, q_name in [('q1_overall', 'q1'), ('q2_supervision', 'q2'), ('q3_rectification', 'q3')]:
            for dept_code in ['V', 'W', 'X', 'Y']:
                dept_name = dept_map.get(dept_code, dept_code)
                
                # 统计各选项数量
                counts = {'好': 0, '较好': 0, '一般': 0, '差': 0}
                rows = db.execute(f"SELECT {q_field} FROM evaluation_selection_appointment WHERE dept_code=?", (dept_code,)).fetchall()
                
                for r in rows:
                    val = r[0]
                    if val in counts:
                        counts[val] += 1
                
                total = sum(counts.values())
                
                cursor.execute('''
                    INSERT INTO selection_stats_q123 (question, dept_code, dept_name, count_good, count_fair, count_average, count_poor, count_total)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (q_name, dept_code, dept_name, counts['好'], counts['较好'], counts['一般'], counts['差'], total))
        
        # ========== Q4 统计 ==========
        for dept_code in ['V', 'W', 'X', 'Y']:
            dept_name = dept_map.get(dept_code, dept_code)
            p_counts = {i: 0 for i in range(1, 13)}
            
            rows = db.execute("SELECT q4_problems FROM evaluation_selection_appointment WHERE dept_code=?", (dept_code,)).fetchall()
            for r in rows:
                if r['q4_problems']:
                    for p in r['q4_problems'].split(','):
                        p = p.strip()
                        if p.isdigit() and 1 <= int(p) <= 12:
                            p_counts[int(p)] += 1
            
            cursor.execute('''
                INSERT INTO selection_stats_q4 (dept_code, dept_name, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (dept_code, dept_name, p_counts[1], p_counts[2], p_counts[3], p_counts[4], p_counts[5], p_counts[6],
                  p_counts[7], p_counts[8], p_counts[9], p_counts[10], p_counts[11], p_counts[12]))
        
        # ========== Q5/Q6 文本汇总 ==========
        for q_field, q_name in [('q5_suggestions_employment', 'q5'), ('q6_suggestions_report', 'q6')]:
            rows = db.execute(f"SELECT dept_code, {q_field} FROM evaluation_selection_appointment WHERE {q_field} IS NOT NULL AND {q_field} != ''").fetchall()
            for r in rows:
                dept_name = dept_map.get(r['dept_code'], r['dept_code'])
                cursor.execute('''
                    INSERT INTO selection_stats_text (question, dept_code, dept_name, suggestion)
                    VALUES (?, ?, ?, ?)
                ''', (q_name, r['dept_code'], dept_name, r[q_field]))
        
        db.commit()
        return jsonify({'success': True, 'msg': '计算完成'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/selection-stats/clear', methods=['POST'])
@admin_required
def selection_stats_clear():
    """一键清空"""
    db = get_db()
    try:
        db.execute('DELETE FROM selection_stats_q123')
        db.execute('DELETE FROM selection_stats_q4')
        db.execute('DELETE FROM selection_stats_text')
        db.commit()
        return jsonify({'success': True, 'msg': '已清空'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/selection-stats/q123')
@admin_required
def selection_stats_q123():
    """获取Q1-Q3统计数据"""
    db = get_db()
    question = request.args.get('question', 'q1')
    
    rows = db.execute('SELECT * FROM selection_stats_q123 WHERE question=? ORDER BY dept_code', (question,)).fetchall()
    data = [dict(r) for r in rows]
    
    # 计算总计行
    totals = {'dept_name': '总计', 'count_good': 0, 'count_fair': 0, 'count_average': 0, 'count_poor': 0, 'count_total': 0}
    for d in data:
        totals['count_good'] += d['count_good']
        totals['count_fair'] += d['count_fair']
        totals['count_average'] += d['count_average']
        totals['count_poor'] += d['count_poor']
        totals['count_total'] += d['count_total']
    
    data.append(totals)
    return jsonify({'data': data})

@app.route('/api/selection-stats/q4')
@admin_required
def selection_stats_q4():
    """获取Q4统计数据"""
    db = get_db()
    rows = db.execute('SELECT * FROM selection_stats_q4 ORDER BY dept_code').fetchall()
    data = [dict(r) for r in rows]
    
    # 计算总计行
    totals = {'dept_name': '总计'}
    for i in range(1, 13):
        totals[f'p{i}'] = sum(d[f'p{i}'] for d in data)
    
    data.append(totals)
    return jsonify({'data': data})

@app.route('/api/selection-stats/text')
@admin_required
def selection_stats_text():
    """获取Q5/Q6文本数据"""
    db = get_db()
    question = request.args.get('question', 'q5')
    
    rows = db.execute('SELECT * FROM selection_stats_text WHERE question=? ORDER BY dept_code', (question,)).fetchall()
    return jsonify({'data': [dict(r) for r in rows]})

@app.route('/api/selection-stats/export')
@admin_required
def selection_stats_export():
    """导出Excel"""
    db = get_db()
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Q1-Q3
        for q in ['q1', 'q2', 'q3']:
            rows = db.execute('SELECT dept_name as 归属单位, count_good as 好, count_fair as 较好, count_average as 一般, count_poor as 差, count_total as 总计 FROM selection_stats_q123 WHERE question=?', (q,)).fetchall()
            if rows:
                df = pd.DataFrame([dict(r) for r in rows])
                # 添加总计行
                totals = df.sum(numeric_only=True).to_dict()
                totals['归属单位'] = '总计'
                df = pd.concat([df, pd.DataFrame([totals])], ignore_index=True)
                sheet_name = {'q1': 'Q1-总体评价', 'q2': 'Q2-监督评价', 'q3': 'Q3-整改评价'}[q]
                df.to_excel(writer, index=False, sheet_name=sheet_name)
        
        # Q4
        rows = db.execute('SELECT dept_name as 归属单位, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12 FROM selection_stats_q4').fetchall()
        if rows:
            df = pd.DataFrame([dict(r) for r in rows])
            # 重命名列
            cols = {'p1': '问题1', 'p2': '问题2', 'p3': '问题3', 'p4': '问题4', 'p5': '问题5', 'p6': '问题6',
                    'p7': '问题7', 'p8': '问题8', 'p9': '问题9', 'p10': '问题10', 'p11': '问题11', 'p12': '问题12'}
            df = df.rename(columns=cols)
            # 添加总计行
            totals = df.select_dtypes(include=['number']).sum().to_dict()
            totals['归属单位'] = '总计'
            df = pd.concat([df, pd.DataFrame([totals])], ignore_index=True)
            df.to_excel(writer, index=False, sheet_name='Q4-问题统计')
        
        # Q5/Q6
        for q, sheet in [('q5', 'Q5-选人用人建议'), ('q6', 'Q6-一报告两评议建议')]:
            rows = db.execute('SELECT dept_name as 归属单位, suggestion as 建议内容 FROM selection_stats_text WHERE question=?', (q,)).fetchall()
            if rows:
                df = pd.DataFrame([dict(r) for r in rows])
                df.to_excel(writer, index=False, sheet_name=sheet)
    
    output.seek(0)
    return send_file(output, as_attachment=True, download_name='干部选拔任用评议表统计.xlsx')

# ==========================================
# 22. 新提拔任用干部民主评议表统计
# ==========================================

UNIT_NAME_MAP = {
    'X': '兰州化工研究中心',
    'Y': '大庆化工研究中心'
}

@app.route('/admin/stats/new-promotion')
@admin_required
def new_promotion_stats_page():
    return render_template('new_promotion_stats.html')

@app.route('/api/new-promotion-stats/calculate', methods=['POST'])
@admin_required
def new_promotion_stats_calculate():
    """一键计算统计数据"""
    db = get_db()
    try:
        import json
        cursor = db.cursor()
        cursor.execute('DELETE FROM new_promotion_stats')
        
        # 获取候选人列表
        candidates = db.execute(
            "SELECT id, name, dept_name, dept_code FROM center_grassroots_leaders WHERE dept_code IN ('X','Y') AND is_newly_promoted='是'"
        ).fetchall()
        
        if not candidates:
            return jsonify({'success': True, 'msg': '无候选人数据'})
        
        # 获取所有评议数据（包含部门信息）
        evaluations = db.execute('SELECT dept_code, selections FROM evaluation_new_promotion').fetchall()
        
        # 统计每个候选人的票数（只统计同部门的投票）
        for cand in candidates:
            cid = str(cand['id'])
            cand_dept = cand['dept_code']
            counts = {'agree': 0, 'basic_agree': 0, 'disagree': 0, 'unknown': 0}
            
            for ev in evaluations:
                # 只统计同部门账号的投票
                if ev['dept_code'] != cand_dept:
                    continue
                    
                if ev['selections']:
                    selections = json.loads(ev['selections'])
                    if cid in selections:
                        val = selections[cid]
                        if val in counts:
                            counts[val] += 1
            
            total = sum(counts.values())
            unit_name = UNIT_NAME_MAP.get(cand['dept_code'], cand['dept_code'])
            
            cursor.execute('''
                INSERT INTO new_promotion_stats 
                (candidate_id, name, dept_name, unit_name, dept_code, count_agree, count_basic_agree, count_disagree, count_unknown, count_total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (cand['id'], cand['name'], cand['dept_name'], unit_name, cand['dept_code'],
                  counts['agree'], counts['basic_agree'], counts['disagree'], counts['unknown'], total))
        
        db.commit()
        return jsonify({'success': True, 'msg': f'计算完成，共 {len(candidates)} 条记录'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/new-promotion-stats/clear', methods=['POST'])
@admin_required
def new_promotion_stats_clear():
    """一键清空"""
    db = get_db()
    try:
        db.execute('DELETE FROM new_promotion_stats')
        db.commit()
        return jsonify({'success': True, 'msg': '已清空'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/new-promotion-stats/list')
@admin_required
def new_promotion_stats_list():
    """获取统计数据"""
    db = get_db()
    rows = db.execute('SELECT * FROM new_promotion_stats ORDER BY dept_code, id').fetchall()
    return jsonify({'data': [dict(r) for r in rows]})

@app.route('/api/new-promotion-stats/export')
@admin_required
def new_promotion_stats_export():
    """导出Excel"""
    db = get_db()
    
    rows = db.execute('''
        SELECT name as 姓名, dept_name as 部门, unit_name as 单位, 
               count_agree as 认同, count_basic_agree as 基本认同, 
               count_disagree as 不认同, count_unknown as 不了解, count_total as 总计
        FROM new_promotion_stats ORDER BY dept_code, id
    ''').fetchall()
    
    if not rows:
        return "暂无数据", 404
    
    df = pd.DataFrame([dict(r) for r in rows])
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='新提拔干部评议统计')
    output.seek(0)
    
    return send_file(output, as_attachment=True, download_name='新提拔干部评议表统计.xlsx')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

