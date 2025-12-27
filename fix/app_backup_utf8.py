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
# 浣跨敤闅忔満瀵嗛挜锛氭瘡娆￠噸鍚湇鍔￠兘浼氬鑷存墍鏈夋棫 Session 澶辨晥锛堢敤鎴烽渶閲嶆柊鐧诲綍锛?
app.secret_key = os.urandom(24)
# 璁剧疆 Session 瓒呰繃 30 鍒嗛挓鏃犳搷浣滆嚜鍔ㄥけ鏁?
app.permanent_session_lifetime = timedelta(minutes=30)
DATABASE = 'evaluation.db'

# ==========================================
# 1. 瀛楁鏄犲皠閰嶇疆
# ==========================================

DEPT_MAPPING = {
    '鎺掑簭鍙?: 'sort_no',
    '閮ㄩ棬鍚嶇О': 'dept_name',
    '閮ㄩ棬浠ｇ爜': 'dept_code',
    '閮ㄩ棬绫诲瀷': 'dept_type',
    '闄㈤瀵艰处鍙锋暟閲?: 'count_college_leader',
    '姝ｈ亴璐﹀彿鏁版嵁閲?: 'count_principal',
    '鍓亴璐﹀彿鏁伴噺': 'count_deputy',
    '涓績鍩哄眰棰嗗璐﹀彿鏁伴噺': 'count_center_leader',
    '鍏朵粬鍛樺伐璐﹀彿鏁伴噺': 'count_other',
    '鍙璇勪负浼樼浜烘暟': 'count_excellent',
    '鎺ㄨ崘姝ｈ亴浜烘暟': 'count_recommend_principal',
    '鎺ㄨ崘鍓亴浜烘暟': 'count_recommend_deputy',
    '閮ㄩ棬涓荤棰嗗': 'leader_main',
    '閮ㄩ棬鍒嗙棰嗗': 'leader_sub'
}

PERSONNEL_MAPPING = {
    '閮ㄩ棬鍐呮帓搴忓彿': 'sort_no',
    '濮撳悕': 'name',
    '鎬у埆': 'gender',
    '鍑虹敓骞存湀': 'birth_date',
    '鐜颁换鑱屽姟': 'position',
    '閮ㄩ棬鍚嶇О': 'dept_name',
    '閮ㄩ棬浠ｇ爜': 'dept_code',
    '鍛樺伐瑙掕壊': 'role',
    '宀椾綅灞傜骇': 'rank_level',
    '浠昏亴鏃堕棿': 'tenure_time',
    '鏂囧寲绋嬪害': 'education',
    '鐜拌亴绾ф椂闂?: 'rank_time',
    '鏄惁鏂版彁鎷斿共閮?: 'is_newly_promoted'
}

RECOMMEND_PRINCIPAL_MAPPING = {
    '鎺掑簭鍙?: 'sort_no',
    '濮撳悕': 'name',
    '鎬у埆': 'gender',
    '鍑虹敓骞存湀': 'birth_date',
    '閮ㄩ棬鍚嶇О': 'dept_name',
    '閮ㄩ棬浠ｇ爜': 'dept_code',
    '宀椾綅灞傜骇': 'rank_level',
    '鏂囧寲绋嬪害': 'education',
    '鐜拌亴绾ф椂闂?: 'rank_time',
    '鐜拌亴鍔?: 'current_position'
}

RECOMMEND_DEPUTY_MAPPING = {
    '鎺掑簭鍙?: 'sort_no',
    '濮撳悕': 'name',
    '鎬у埆': 'gender',
    '鍑虹敓骞存湀': 'birth_date',
    '閮ㄩ棬鍚嶇О': 'dept_name',
    '閮ㄩ棬浠ｇ爜': 'dept_code',
    '宀椾綅灞傜骇': 'rank_level',
    '鏂囧寲绋嬪害': 'education',
    '鐜拌亴绾ф椂闂?: 'rank_time',
    '鐜拌亴鍔?: 'current_position'
}

ALLOWED_ROLES = [
    '闄㈤暱鍔╃悊',
    '涓績姝ｈ亴',
    '涓績鍓亴',
    '涓績鍩哄眰棰嗗',
    '鑱岃兘閮ㄩ棬姝ｈ亴',
    '鑱岃兘閮ㄩ棬鍓亴',
    '鐮旂┒鎵€姝ｈ亴',
    '鐮旂┒鎵€鍓亴'
]

# ==========================================
# 2. 鏁版嵁搴撹繛鎺ュ鐞?
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
# 3. 鏉冮檺瑁呴グ鍣?& Auth
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
        return jsonify({'success': False, 'msg': '绠＄悊鍛樿处鍙锋垨瀵嗙爜閿欒'})
        
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
        return jsonify({'success': False, 'msg': '娴嬭瘎璐﹀彿鎴栧瘑鐮侀敊璇?})

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
# 4. 椤甸潰璺敱 (View Routes)
# ==========================================

@app.route('/')
def index():
    """娴嬭瘎鐧诲綍椤?(Root)"""
    if session.get('assessor_role') == 'assessor':
        return redirect(url_for('assessment_home'))
    return render_template('login_assessment.html')

@app.route('/assessment/home')
def assessment_home():
    """娴嬭瘎鎵撳垎棣栭〉"""
    if session.get('assessor_role') != 'assessor':
        return redirect(url_for('index'))
    return render_template('assessment_home.html')

@app.route('/assessment/team-evaluation')
def assessment_team():
    """棰嗗鐝瓙缁煎悎鑰冩牳璇勪环"""
    if session.get('assessor_role') != 'assessor':
        return redirect(url_for('index'))
        
    # Access Control: Exclude '闄㈤瀵?
    if session.get('assessor_dept_type') == '闄㈤瀵?:
        return "鎮ㄧ殑璐﹀彿鏃犳潈璁块棶姝ら〉闈?, 403

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
    """绠＄悊鍛樼櫥褰曢〉"""
    if session.get('admin_role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    return render_template('login_admin.html')
    


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """绠＄悊鍚庡彴棣栭〉 (鍘?/ )"""
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
    """浜哄憳绠＄悊椤?""
    db = get_db()
    # 銆愪慨鏀圭偣銆戞澶勬敼涓烘寜 sort_no (閮ㄩ棬鍐呮帓搴忓彿) 鍗囧簭鎺掑垪
    managers = db.execute('SELECT * FROM middle_managers ORDER BY sort_no ASC').fetchall()
    return render_template('personnel_management.html', managers=managers)

@app.route('/recommend-principal')
@admin_required
def recommend_principal():
    """姝ｈ亴鎺ㄨ崘椤?""
    db = get_db()
    data = db.execute('SELECT * FROM recommend_principal ORDER BY sort_no ASC').fetchall()
    return render_template('recommend_principal.html', data=data)

@app.route('/recommend-deputy')
@admin_required
def recommend_deputy():
    """鍓亴鎺ㄨ崘椤?""
    db = get_db()
    data = db.execute('SELECT * FROM recommend_deputy ORDER BY sort_no ASC').fetchall()
    return render_template('recommend_deputy.html', data=data)

@app.route('/account-generation')
@admin_required
def account_generation():
    """璐﹀彿鐢熸垚椤?""
    return render_template('account_generation.html')

# ==========================================
# 5. API: 閮ㄩ棬閰嶇疆
# ==========================================

@app.route('/api/department/upload', methods=['POST'])
@admin_required
def upload_department():
    if 'file' not in request.files: return jsonify({'success': False, 'msg': '鏃犳枃浠?})
    file = request.files['file']
    try:
        df = pd.read_excel(file)
        df = df.fillna('')
        if '閮ㄩ棬鍚嶇О' not in df.columns:
            return jsonify({'success': False, 'msg': '缂哄皯"閮ㄩ棬鍚嶇О"鍒楋紝璇锋鏌xcel琛ㄥご'})

        db = get_db()
        cursor = db.cursor()
        cursor.execute('DELETE FROM department_config')
        for _, row in df.iterrows():
            # Skip invalid rows
            if not str(row.get('閮ㄩ棬鍚嶇О', '')).strip(): continue

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
        return jsonify({'success': True, 'msg': f'瀵煎叆鎴愬姛: {len(df)} 鏉?})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/department/save', methods=['POST'])
@admin_required
def save_department():
    req = request.json
    if not req or 'data' not in req: return jsonify({'success': False, 'msg': '鏃犳暟鎹?})
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
        return jsonify({'success': True, 'msg': '淇濆瓨鎴愬姛'})
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
            df.to_excel(writer, index=False, sheet_name='閮ㄩ棬閰嶇疆')
        output.seek(0)
        return send_file(output, as_attachment=True, download_name='閮ㄩ棬閰嶇疆琛?xlsx')
    except Exception as e:
        return str(e)

# ==========================================
# 6. API: 浜哄憳绠＄悊
# ==========================================

@app.route('/api/personnel/upload', methods=['POST'])
@admin_required
def upload_personnel():
    if 'file' not in request.files: return jsonify({'success': False, 'msg': '鏃犳枃浠?})
    file = request.files['file']
    try:
        df = pd.read_excel(file)
        df = df.fillna('')
        for col in ['鍑虹敓骞存湀', '鐜拌亴绾ф椂闂?, '浠昏亴鏃堕棿']:
            if col in df.columns:
                # 缁熶竴杞负 YYYY/MM 鏍煎紡
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y/%m').fillna('')
        
        # 鏍￠獙鍛樺伐瑙掕壊
        if '鍛樺伐瑙掕壊' in df.columns:
            invalid_roles = df[~df['鍛樺伐瑙掕壊'].isin(ALLOWED_ROLES) & (df['鍛樺伐瑙掕壊'] != '')]['鍛樺伐瑙掕壊'].unique()
            if len(invalid_roles) > 0:
                 return jsonify({'success': False, 'msg': f'鍙戠幇鏃犳晥鍛樺伐瑙掕壊: {", ".join(invalid_roles)}'})
        
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
            if '閮ㄩ棬鍚嶇О' in df.columns and row['閮ㄩ棬鍚嶇О'] in dept_map:
                cols.append('dept_id')
                vals.append(dept_map[row['閮ㄩ棬鍚嶇О']])
            if cols:
                cursor.execute(f'INSERT INTO middle_managers ({", ".join(cols)}) VALUES ({", ".join(["?"]*len(cols))})', vals)
        db.commit()
        return jsonify({'success': True, 'msg': f'瀵煎叆鎴愬姛: {len(df)} 浜?})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/personnel/save', methods=['POST'])
@admin_required
def save_personnel():
    req = request.json
    if not req or 'data' not in req: return jsonify({'success': False, 'msg': '鏃犳暟鎹?})
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
                return jsonify({'success': False, 'msg': f'鏃犳晥鐨勫憳宸ヨ鑹? {row.get("role")}'})

            cursor.execute(f'INSERT INTO middle_managers ({", ".join(cols)}) VALUES ({", ".join(["?"]*len(cols))})', vals)
        db.commit()
        return jsonify({'success': True, 'msg': '淇濆瓨鎴愬姛'})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/personnel/export')
@admin_required
def export_personnel():
    try:
        db = get_db()
        # 銆愪慨鏀圭偣銆戞澶勪篃鏀逛负鎸?sort_no (閮ㄩ棬鍐呮帓搴忓彿) 鍗囧簭瀵煎嚭
        df = pd.read_sql_query("SELECT * FROM middle_managers ORDER BY sort_no ASC", db)
        for col in ['id', 'dept_id', 'updated_at']:
            if col in df.columns: df = df.drop(columns=[col])
        reverse_map = {v: k for k, v in PERSONNEL_MAPPING.items()}
        df = df.rename(columns=reverse_map)
        df = df[[k for k in PERSONNEL_MAPPING.keys() if k in df.columns]]
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='浜哄憳淇℃伅')
        output.seek(0)
        return send_file(output, as_attachment=True, download_name='涓眰骞查儴浜哄憳鍚嶅崟.xlsx')
    except Exception as e:
        return str(e)

# ==========================================
# 7. API: 姝ｈ亴鎺ㄨ崘
# ==========================================

@app.route('/api/recommend-principal/upload', methods=['POST'])
@admin_required
def upload_recommend_principal():
    if 'file' not in request.files: return jsonify({'success': False, 'msg': '鏃犳枃浠?})
    file = request.files['file']
    try:
        df = pd.read_excel(file)
        df = df.fillna('')
        df.columns = df.columns.str.strip()

        missing = [c for c in ['濮撳悕', '閮ㄩ棬鍚嶇О'] if c not in df.columns]
        if missing:
             return jsonify({'success': False, 'msg': f'缂哄皯蹇呰鍒? {", ".join(missing)}'})

        for col in ['鍑虹敓骞存湀', '鐜拌亴绾ф椂闂?]:
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
        return jsonify({'success': True, 'msg': f'瀵煎叆鎴愬姛: {len(df)} 浜?})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/recommend-principal/save', methods=['POST'])
@admin_required
def save_recommend_principal():
    req = request.json
    if not req or 'data' not in req: return jsonify({'success': False, 'msg': '鏃犳暟鎹?})
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
        return jsonify({'success': True, 'msg': '淇濆瓨鎴愬姛'})
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
            df.to_excel(writer, index=False, sheet_name='姝ｈ亴鎺ㄨ崘')
        output.seek(0)
        return send_file(output, as_attachment=True, download_name='姝ｈ亴鎺ㄨ崘浜哄憳鍚嶅崟.xlsx')
    except Exception as e:
        return str(e)

# ==========================================
# 8. API: 鍓亴鎺ㄨ崘
# ==========================================

@app.route('/api/recommend-deputy/upload', methods=['POST'])
@admin_required
def upload_recommend_deputy():
    if 'file' not in request.files: return jsonify({'success': False, 'msg': '鏃犳枃浠?})
    file = request.files['file']
    try:
        df = pd.read_excel(file)
        df = df.fillna('')
        df.columns = df.columns.str.strip()

        missing = [c for c in ['濮撳悕', '閮ㄩ棬鍚嶇О'] if c not in df.columns]
        if missing:
             return jsonify({'success': False, 'msg': f'缂哄皯蹇呰鍒? {", ".join(missing)}'})

        for col in ['鍑虹敓骞存湀', '鐜拌亴绾ф椂闂?]:
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
        return jsonify({'success': True, 'msg': f'瀵煎叆鎴愬姛: {len(df)} 浜?})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/recommend-deputy/save', methods=['POST'])
@admin_required
def save_recommend_deputy():
    req = request.json
    if not req or 'data' not in req: return jsonify({'success': False, 'msg': '鏃犳暟鎹?})
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
        return jsonify({'success': True, 'msg': '淇濆瓨鎴愬姛'})
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
            df.to_excel(writer, index=False, sheet_name='鍓亴鎺ㄨ崘')
        output.seek(0)
        return send_file(output, as_attachment=True, download_name='鍓亴鎺ㄨ崘浜哄憳鍚嶅崟.xlsx')
    except Exception as e:
        return str(e)

# ==========================================
# 9. API: 璐﹀彿鐢熸垚
# ==========================================

def generate_password():
    """鐢熸垚4浣嶆暟瀛楀皬鍐欏瓧姣嶆贩鍚堝瘑鐮侊紝鎺掗櫎瀹规槗娣锋穯鐨勫瓧绗?(i, o, 1, l)"""
    chars = 'abcdefghjkmnpqrstuvwxyz234567890' # Excludes i, l, o, 1
    return ''.join(random.choices(chars, k=4))

@app.route('/api/account/generate', methods=['POST'])
@admin_required
def generate_accounts_api():
    try:
        db = get_db()
        cursor = db.cursor()
        
        # 1. 鑾峰彇閮ㄩ棬閰嶇疆 (浠呭鐞嗘湁璐﹀彿闇€姹傜殑閮ㄩ棬)
        depts = db.execute('SELECT * FROM department_config').fetchall()
        if not depts: return jsonify({'success': False, 'msg': '鏃犻儴闂ㄩ厤缃暟鎹?})

        # 2. 璐﹀彿绫诲瀷鏄犲皠鍜屽墠缂€
        type_map = [
            # (DB Column, Type Name, Prefix Code)
            ('count_college_leader', '闄㈤瀵?, 'L'),
            ('count_principal', '姝ｈ亴', 'P'),
            ('count_deputy', '鍓亴', 'D'),
            ('count_center_leader', '涓績鍩哄眰棰嗗', 'C'),
            ('count_other', '鍏朵粬鍛樺伐', 'E')
        ]
        
        new_accounts = []
        
        # 绛栫暐锛氬叏閲忛噸鏂扮敓鎴愶紵杩樻槸澧為噺锛熺敤鎴疯"涓€閿竻绌?鏄崟鐙寜閽€?
        # 杩欓噷瀹炵幇锛氭鏌ユ槸鍚﹀凡瀛樺湪锛屽鏋滀笉瀛樺湪鍒欑敓鎴愩€備负閬垮厤搴忓彿娣蜂贡锛屽缓璁厛娓呯┖鎴栦粎鐢ㄤ簬鍒濆鍖栥€?
        # 閴翠簬搴忓彿閫昏緫 (001, 002)锛屼负浜嗕繚璇佽繛缁€э紝鏈€绠€鍗曠殑閫昏緫鏄細
        # 瀵逛簬姣忎釜閮ㄩ棬+绫诲瀷锛岃绠楅渶瑕?N 涓€傛鏌ュ凡鏈夌殑 M 涓€傚鏋?M < N锛岀敓鎴?N-M 涓€?
        # Username format: {DeptCode}{TypePrefix}{Seq(3)}
        
        existing_rows = db.execute('SELECT username FROM evaluation_accounts').fetchall()
        existing_usernames = set(r['username'] for r in existing_rows)

        for dept in depts:
            d_code = dept['dept_code']
            if not d_code: continue
            
            for col_count, type_name, prefix in type_map:
                count = dept[col_count]
                if not count or count <= 0: continue
                
                # 灏濊瘯鐢熸垚 Need Count 涓处鍙?
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
            return jsonify({'success': True, 'msg': f'鐢熸垚鎴愬姛锛屾柊澧?{len(new_accounts)} 涓处鍙?})
        else:
            return jsonify({'success': True, 'msg': '鏃犳柊璐﹀彿闇€瑕佺敓鎴?(鏁伴噺宸叉弧瓒抽厤缃?'})

    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/account/clear', methods=['POST'])
@admin_required
def clear_accounts_api():
    try:
        db = get_db()
        db.execute('DELETE FROM evaluation_accounts')
        db.commit()
        return jsonify({'success': True, 'msg': '宸叉竻绌烘墍鏈夌敓鎴愮殑璐﹀彿'})
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
    if not req or 'data' not in req: return jsonify({'success': False, 'msg': '鏃犳暟鎹?})
    db = get_db()
    try:
        for row in req['data']:
            if not row.get('id'): continue
            # 浠呭厑璁镐慨鏀?瀵嗙爜 鍜?鐘舵€?
            db.execute('UPDATE evaluation_accounts SET password=?, status=? WHERE id=?', (row['password'], row['status'], row['id']))
        db.commit()
        return jsonify({'success': True, 'msg': '淇濆瓨鎴愬姛'})
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
            'dept_name': '閮ㄩ棬鍚嶇О',
            'dept_code': '閮ㄩ棬浠ｇ爜',
            'account_type': '璐﹀彿绫诲瀷',
            'username': '璐﹀彿',
            'password': '瀵嗙爜',
            'status': '鐘舵€?
        }
        df = df.rename(columns=rename_map)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='娴嬭瘎璐﹀彿')
        output.seek(0)
        return send_file(output, as_attachment=True, download_name='娴嬭瘎璐﹀彿鍚嶅崟.xlsx')
    except Exception as e:
        return str(e)

    except Exception as e:
        return str(e)

# ==========================================
# 10. API: 閮ㄩ棬鏉冮噸閰嶇疆
# ==========================================

# Default Matrix Configuration
# (Examinee Role -> {Rater Role: Weight})
DEFAULT_DEPT_WEIGHTS = {
    '闄㈤暱鍔╃悊': {
        '闄㈤瀵?: 70, '鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?': 10, '鐮旂┒鎵€姝ｈ亴': 10, '涓績棰嗗鐝瓙 (姝ｈ亴)': 10
    },
    '鑱岃兘閮ㄩ棬姝ｈ亴': {
        '闄㈤瀵?: 50, '鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?': 0, '鑱岃兘閮ㄩ棬鍓亴': 0, '鑱岃兘閮ㄩ棬鍏朵粬鍛樺伐': 30, '鐮旂┒鎵€姝ｈ亴': 10, '涓績棰嗗鐝瓙 (姝ｈ亴)': 10
    },
    '鑱岃兘閮ㄩ棬鍓亴': {
        '闄㈤瀵?: 50, '鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?': 0, '鑱岃兘閮ㄩ棬鍓亴': 0, '鑱岃兘閮ㄩ棬鍏朵粬鍛樺伐': 30
    },
    '鐮旂┒鎵€姝ｈ亴': {
        '闄㈤瀵?: 50, '鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?': 20, '鐮旂┒鎵€姝ｈ亴': 0, '鐮旂┒鎵€鍓亴': 0, '鐮旂┒鎵€鍏朵粬鍛樺伐': 30
    },
    '鐮旂┒鎵€鍓亴': {
        '闄㈤瀵?: 50, '鐮旂┒鎵€姝ｈ亴': 0, '鐮旂┒鎵€鍓亴': 0, '鐮旂┒鎵€鍏朵粬鍛樺伐': 30
    },
    '涓や腑蹇冩鑱?: {
        '闄㈤瀵?: 50, '鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?': 10, '涓績棰嗗鐝瓙 (姝ｈ亴)': 10, '鑱屽伐浠ｈ〃涓熀灞傞瀵间汉鍛?(涓や腑蹇?': 20, '鍏朵粬鑱屽伐浠ｈ〃 (涓や腑蹇?': 10
    },
    '涓や腑蹇冨壇鑱?: {
        '闄㈤瀵?: 50, '涓績棰嗗鐝瓙 (姝ｈ亴)': 20, '涓績棰嗗鐝瓙 (鍓亴)': 10, '鑱屽伐浠ｈ〃涓熀灞傞瀵间汉鍛?(涓や腑蹇?': 10, '鍏朵粬鑱屽伐浠ｈ〃 (涓や腑蹇?': 10
    },
    '鏄嗗唸鐝瓙鍓亴 (鍖椾含)': {
        '闄㈤瀵?: 20, '鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?': 10, '鏄嗗唸鐝瓙姝ｈ亴': 40, '鏄嗗唸鐝瓙鍓亴': 10, '鎵€灞炲垎鍏徃鐝瓙姝ｈ亴': 10, '鑱屽伐浠ｈ〃涓熀灞傞瀵间汉鍛?(鏄嗗唸鍖椾含)': 10
    },
    '鎵€灞炲垎鍏徃 (鍏板窞銆佹姎椤? 鐝瓙姝ｈ亴': {
        '闄㈤瀵?: 10, '鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?': 10, '鏄嗗唸鐝瓙姝ｈ亴': 30, '鏄嗗唸鐝瓙鍓亴': 10, '鎵€灞炲垎鍏徃鐝瓙鍓亴': 10, '鑱屽伐浠ｈ〃涓熀灞傞瀵间汉鍛?(鍒嗗叕鍙?': 20, '鍏朵粬鑱屽伐浠ｈ〃 (鍒嗗叕鍙?': 10
    },
    '鎵€灞炲垎鍏徃 (鍏板窞銆佹姎椤? 鐝瓙鍓亴': {
        '鏄嗗唸鐝瓙姝ｈ亴': 30, '鏄嗗唸鐝瓙鍓亴': 10, '鎵€灞炲垎鍏徃鐝瓙姝ｈ亴': 30, '鎵€灞炲垎鍏徃鐝瓙鍓亴': 10, '鑱屽伐浠ｈ〃涓熀灞傞瀵间汉鍛?(鍒嗗叕鍙?': 10, '鍏朵粬鑱屽伐浠ｈ〃 (鍒嗗叕鍙?': 10
    }
}

# Democratic Assessment Permission Config (Independent of Weights)
# Format: Examinee Role -> List of Allowed Rater Roles
DEFAULT_DEMOCRATIC_CONFIG = {
    '闄㈤暱鍔╃悊': ['闄㈤瀵?, '鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?', '鐮旂┒鎵€姝ｈ亴', '涓績棰嗗鐝瓙 (姝ｈ亴)'],
    '鑱岃兘閮ㄩ棬姝ｈ亴': ['闄㈤瀵?, '鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?', '鑱岃兘閮ㄩ棬鍓亴', '鑱岃兘閮ㄩ棬鍏朵粬鍛樺伐', '鐮旂┒鎵€姝ｈ亴', '涓績棰嗗鐝瓙 (姝ｈ亴)'],
    '鑱岃兘閮ㄩ棬鍓亴': ['闄㈤瀵?, '鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?', '鑱岃兘閮ㄩ棬鍓亴', '鑱岃兘閮ㄩ棬鍏朵粬鍛樺伐'],
    
    # [Updated] Institute Rules
    '鐮旂┒鎵€姝ｈ亴': [
        '闄㈤瀵?, '鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?', '鐮旂┒鎵€鍏朵粬鍛樺伐',
        '鐮旂┒鎵€姝ｈ亴', # Mutual
        '鐮旂┒鎵€鍓亴'  # Deputy rates Principal
    ],
    '鐮旂┒鎵€鍓亴': [
        '闄㈤瀵?, '鐮旂┒鎵€鍏朵粬鍛樺伐',
        '鐮旂┒鎵€姝ｈ亴', # Principal rates Deputy
        '鐮旂┒鎵€鍓亴'  # Mutual
    ],
    
    '涓や腑蹇冩鑱?: ['闄㈤瀵?, '鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?', '涓績棰嗗鐝瓙 (姝ｈ亴)', '鑱屽伐浠ｈ〃涓熀灞傞瀵间汉鍛?(涓や腑蹇?', '鍏朵粬鑱屽伐浠ｈ〃 (涓や腑蹇?'],
    '涓や腑蹇冨壇鑱?: ['闄㈤瀵?, '涓績棰嗗鐝瓙 (姝ｈ亴)', '涓績棰嗗鐝瓙 (鍓亴)', '鑱屽伐浠ｈ〃涓熀灞傞瀵间汉鍛?(涓や腑蹇?', '鍏朵粬鑱屽伐浠ｈ〃 (涓や腑蹇?'],
    
    '鏄嗗唸鐝瓙鍓亴 (鍖椾含)': [
        '闄㈤瀵?, '鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?', 
        '鏄嗗唸鐝瓙姝ｈ亴', '鏄嗗唸鐝瓙鍓亴', 
        '鎵€灞炲垎鍏徃鐝瓙姝ｈ亴', 
        '鑱屽伐浠ｈ〃涓熀灞傞瀵间汉鍛?(鏄嗗唸鍖椾含)'
    ],
    
    '鎵€灞炲垎鍏徃 (鍏板窞銆佹姎椤? 鐝瓙姝ｈ亴': [
        '闄㈤瀵?, '鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?', 
        '鏄嗗唸鐝瓙姝ｈ亴', '鏄嗗唸鐝瓙鍓亴', 
        '鎵€灞炲垎鍏徃鐝瓙鍓亴', 
        '鑱屽伐浠ｈ〃涓熀灞傞瀵间汉鍛?(鍒嗗叕鍙?', '鍏朵粬鑱屽伐浠ｈ〃 (鍒嗗叕鍙?'
    ],
    '鎵€灞炲垎鍏徃 (鍏板窞銆佹姎椤? 鐝瓙鍓亴': [
        '鏄嗗唸鐝瓙姝ｈ亴', '鏄嗗唸鐝瓙鍓亴', 
        '鎵€灞炲垎鍏徃鐝瓙姝ｈ亴', '鎵€灞炲垎鍏徃鐝瓙鍓亴', 
        '鑱屽伐浠ｈ〃涓熀灞傞瀵间汉鍛?(鍒嗗叕鍙?', '鍏朵粬鑱屽伐浠ｈ〃 (鍒嗗叕鍙?'
    ]
}

ROW_HEADERS = [
    '闄㈤瀵?, '鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?', '鑱岃兘閮ㄩ棬鍓亴', '鑱岃兘閮ㄩ棬鍏朵粬鍛樺伐',
    '鐮旂┒鎵€姝ｈ亴', '鐮旂┒鎵€鍓亴', '鐮旂┒鎵€鍏朵粬鍛樺伐',
    '涓績棰嗗鐝瓙 (姝ｈ亴)', '涓績棰嗗鐝瓙 (鍓亴)',
    '鏄嗗唸鐝瓙姝ｈ亴', '鏄嗗唸鐝瓙鍓亴',
    '鎵€灞炲垎鍏徃鐝瓙姝ｈ亴', '鎵€灞炲垎鍏徃鐝瓙鍓亴',
    '鑱屽伐浠ｈ〃涓熀灞傞瀵间汉鍛?(涓や腑蹇?', '鍏朵粬鑱屽伐浠ｈ〃 (涓や腑蹇?',
    '鑱屽伐浠ｈ〃涓熀灞傞瀵间汉鍛?(鏄嗗唸鍖椾含)', '鍏朵粬鑱屽伐浠ｈ〃 (鏄嗗唸鍖椾含)',
    '鑱屽伐浠ｈ〃涓熀灞傞瀵间汉鍛?(鍒嗗叕鍙?', '鍏朵粬鑱屽伐浠ｈ〃 (鍒嗗叕鍙?'
]

COL_HEADERS = [
    '闄㈤暱鍔╃悊', '鑱岃兘閮ㄩ棬姝ｈ亴', '鑱岃兘閮ㄩ棬鍓亴', 
    '鐮旂┒鎵€姝ｈ亴', '鐮旂┒鎵€鍓亴', 
    '涓や腑蹇冩鑱?, '涓や腑蹇冨壇鑱?, 
    '鏄嗗唸鐝瓙鍓亴 (鍖椾含)', '鎵€灞炲垎鍏徃 (鍏板窞銆佹姎椤? 鐝瓙姝ｈ亴', '鎵€灞炲垎鍏徃 (鍏板窞銆佹姎椤? 鐝瓙鍓亴'
]

# ==========================================
# 鏄犲皠閰嶇疆锛氭墦鍒嗚鑹?(Rater Role) -> 璐﹀彿瑙勫垯
# 閫昏緫锛歊ole -> [Rule1, Rule2, ...] (Satisfy ANY rule)
# ==========================================
# Rater Rules: Map (Department Type + Account Type) -> Rater Role
# Account Types: L=Leader(闄㈤瀵?, P=Principal(姝ｈ亴), D=Deputy(鍓亴), E=Employee(鍛樺伐), S=StaffRep(鑱屽伐浠ｈ〃)
# Note: DB might store Chinese '闄㈤瀵?, '姝ｈ亴', '鍓亴', '鍛樺伐', '鑱屽伐浠ｈ〃'
RATER_RULES = {
    # 1. 闄㈤瀵?
    '闄㈤瀵?: [
        {'dept_names': ['闄㈤瀵?], 'types': ['L', '闄㈤瀵?]}
    ],
    
    # 2. 鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?
    '鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?': [
        {'dept_type': '鑱岃兘閮ㄩ棬', 'types': ['P', '姝ｈ亴']},
        {'dept_names': ['闄㈤暱鍔╃悊'], 'dept_codes': ['A0'], 'types': []} 
    ],
    
    # 3. 鑱岃兘閮ㄩ棬鍓亴
    '鑱岃兘閮ㄩ棬鍓亴': [
        {'dept_type': '鑱岃兘閮ㄩ棬', 'types': ['D', '鍓亴']}
    ],
    
    # 4. 鑱岃兘閮ㄩ棬鍏朵粬鍛樺伐
    '鑱岃兘閮ㄩ棬鍏朵粬鍛樺伐': [], # Handled dynamically in get_user_rater_roles
    
    # 5-7. 鐮旂┒鎵€
    '鐮旂┒鎵€姝ｈ亴': [{'dept_type': '鐮旂┒鎵€', 'types': ['P', '姝ｈ亴']}],
    '鐮旂┒鎵€鍓亴': [{'dept_type': '鐮旂┒鎵€', 'types': ['D', '鍓亴']}],
    '鐮旂┒鎵€鍏朵粬鍛樺伐': [{'dept_type': '鐮旂┒鎵€', 'types': ['E', '鍛樺伐']}],
    
    # 8-9. 涓や腑蹇?
    '涓績棰嗗鐝瓙 (姝ｈ亴)': [
        {'dept_type': '涓や腑蹇?, 'types': ['P', '姝ｈ亴']},
        {'dept_codes': ['X', 'Y'], 'types': ['P', '姝ｈ亴']}
    ],
    '涓績棰嗗鐝瓙 (鍓亴)': [
        {'dept_type': '涓や腑蹇?, 'types': ['D', '鍓亴']},
        {'dept_codes': ['X', 'Y'], 'types': ['D', '鍓亴']}
    ],
    
    # 10-11. 鏄嗗唸
    '鏄嗗唸鐝瓙姝ｈ亴': [
        {'dept_type': '鏄嗗唸', 'types': ['P', '姝ｈ亴']},
        {'dept_names': ['鏄嗗唸鍏堣繘鍒堕€狅紙鍖椾含锛夋湁闄愬叕鍙?], 'dept_codes': ['U'], 'types': ['P', '姝ｈ亴']}
    ],
    '鏄嗗唸鐝瓙鍓亴': [
        {'dept_type': '鏄嗗唸', 'types': ['D', '鍓亴']},
        {'dept_names': ['鏄嗗唸鍏堣繘鍒堕€狅紙鍖椾含锛夋湁闄愬叕鍙?], 'types': ['D', '鍓亴']}
    ],
    
    # 12-13. 鍒嗗叕鍙?(鍏板窞/鎶氶『)
    '鎵€灞炲垎鍏徃鐝瓙姝ｈ亴': [{'dept_names': ['鏄嗗唸鍏板窞鍒嗗叕鍙?, '鏄嗗唸鎶氶『鍒嗗叕鍙?], 'types': ['P', '姝ｈ亴']}],
    '鎵€灞炲垎鍏徃鐝瓙鍓亴': [{'dept_names': ['鏄嗗唸鍏板窞鍒嗗叕鍙?, '鏄嗗唸鎶氶『鍒嗗叕鍙?], 'types': ['D', '鍓亴']}],
    
    # 14-19. 鑱屽伐浠ｈ〃
    '鑱屽伐浠ｈ〃涓熀灞傞瀵间汉鍛?(涓や腑蹇?': [{'dept_type': '涓や腑蹇?, 'types': ['C', '鑱屽伐浠ｈ〃']}], 
    '鍏朵粬鑱屽伐浠ｈ〃 (涓や腑蹇?': [{'dept_type': '涓や腑蹇?, 'types': ['E', '鍛樺伐']}], # Usually E in Center
    
    '鑱屽伐浠ｈ〃涓熀灞傞瀵间汉鍛?(鏄嗗唸鍖椾含)': [{'dept_names': ['鏄嗗唸鍖椾含'], 'types': ['C', '鑱屽伐浠ｈ〃']}],
    '鍏朵粬鑱屽伐浠ｈ〃 (鏄嗗唸鍖椾含)': [{'dept_names': ['鏄嗗唸鍖椾含'], 'types': ['E', '鍛樺伐']}],
    
    '鑱屽伐浠ｈ〃涓熀灞傞瀵间汉鍛?(鍒嗗叕鍙?': [{'dept_names': ['鍏板窞鍒嗗叕鍙?, '鎶氶『鍒嗗叕鍙?], 'types': ['C', '鑱屽伐浠ｈ〃']}],
    '鍏朵粬鑱屽伐浠ｈ〃 (鍒嗗叕鍙?': [{'dept_names': ['鍏板窞鍒嗗叕鍙?, '鎶氶『鍒嗗叕鍙?], 'types': ['E', '鍛樺伐']}]
}

def init_dept_weights(db):
    """鍒濆鍖栭儴闂ㄦ潈閲嶉厤缃?""
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
            print("鍒濆鍖栭儴闂ㄦ潈閲嶉厤缃暟鎹?..")
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
    鏍规嵁鐢ㄦ埛璐﹀彿淇℃伅(绫诲瀷)鍜岄儴闂ㄤ俊鎭紝杩斿洖璇ョ敤鎴峰搴旂殑 Rater Roles (List)
    user_account: dict {'account_type': 'P', ...}
    user_dept_info: dict {'dept_name': '...', 'dept_type': '...', 'dept_code': '...'}
    """
    matched_roles = []
    
    acc_type = user_account.get('account_type', '').strip()
    d_name = user_dept_info.get('dept_name', '').strip()
    d_type = user_dept_info.get('dept_type', '').strip()
    d_code = user_dept_info.get('dept_code', '').strip()
    
    for rater_role, rules_list in RATER_RULES.items():
        # Special handling for '鑱岃兘閮ㄩ棬鍏朵粬鍛樺伐'
        if rater_role == '鑱岃兘閮ㄩ棬鍏朵粬鍛樺伐':
             # E绫昏处鍙?/ 鍛樺伐 鎵嶆湁鍙兘鏄亴鑳介儴闂ㄥ叾浠栧憳宸?
             # Logic: If Type is E or '鍛樺伐' AND Dept Type is Functional -> Match.
             if (acc_type == 'E' or acc_type == '鍛樺伐') and d_type == '鑱岃兘閮ㄩ棬':
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
    鏍规嵁涓眰浜哄憳鐨勨€滆鑹测€濆拰鈥滈儴闂ㄢ€濓紝璇嗗埆鍏跺搴旂殑鏉冮噸琛ㄥ垪澶?(Column Header)
    """
    if not person_role: return None
    person_role = person_role.strip()
    


    # [Exclusion] Grassroots leaders should NOT be examinees (Global Check)
    if '鍩哄眰' in person_role: 
        return 'EXCLUDED'

    # 1. 鐩存帴鍖归厤鍩虹瑙掕壊
    if person_role in ['闄㈤暱鍔╃悊', '鑱岃兘閮ㄩ棬姝ｈ亴', '鑱岃兘閮ㄩ棬鍓亴', '鐮旂┒鎵€姝ｈ亴', '鐮旂┒鎵€鍓亴']:
        return person_role
        
    # 2. 澶嶅悎瑙掕壊锛氫袱涓績 (鍏板窞/澶у簡)
    if '涓績' in person_role: # 涓績姝ｈ亴 / 涓績鍓亴
        if dept_name in ['鍏板窞鍖栧伐鐮旂┒涓績', '澶у簡鍖栧伐鐮旂┒涓績']:
            if '姝ｈ亴' in person_role: return '涓や腑蹇冩鑱?
            if '鍓亴' in person_role: return '涓や腑蹇冨壇鑱?
            if '鍓亴' in person_role: return '涓や腑蹇冨壇鑱?
            
        # 3. 澶嶅悎瑙掕壊锛氭槅鍐?(鍖椾含)
        if dept_name == '鏄嗗唸鍏堣繘鍒堕€狅紙鍖椾含锛夋湁闄愬叕鍙?:
            if '鍓亴' in person_role: return '鏄嗗唸鐝瓙鍓亴 (鍖椾含)'
            
        # 4. 澶嶅悎瑙掕壊锛氬垎鍏徃 (鍏板窞/鎶氶『)
        # 娉ㄦ剰锛氳繖閲屽寘鎷?鈥滄槅鍐堝叞宸炲垎鍏徃鈥?鍜?鈥滄槅鍐堟姎椤哄垎鍏徃鈥?
        if dept_name in ['鏄嗗唸鍏板窞鍒嗗叕鍙?, '鏄嗗唸鎶氶『鍒嗗叕鍙?]:
            if '姝ｈ亴' in person_role: return '鎵€灞炲垎鍏徃 (鍏板窞銆佹姎椤? 鐝瓙姝ｈ亴'
            if '鍓亴' in person_role: return '鎵€灞炲垎鍏徃 (鍏板窞銆佹姎椤? 鐝瓙鍓亴'
            
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
    if not req: return jsonify({'success': False, 'msg': '鏃犳暟鎹?})
    
    db = get_db()
    try:
        updates = []
        # Temporary dict to enforce consistency before saving
        # Key: (Examinee, Rater) -> Weight
        pending_changes = {}
        
        for item in req.get('data', []):
            pending_changes[(item['examinee'], item['rater'])] = float(item['weight'])
            
        # ---------------------------------------------------------
        # 鐗规畩鏉冮噸閫昏緫鏍￠獙 (Special Weight Logic)
        # 鍦烘櫙锛氳亴鑳介儴闂ㄦ鑱岃€冭鏍告椂锛屼腑蹇冩鑱?涓?鍒嗗叕鍙告鑱?鏉冮噸闇€淇濇寔涓€鑷?
        # ---------------------------------------------------------
        target_col = '鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?' # Wait, Header name is '鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?' ?? No, Examinee Header is '鑱岃兘閮ㄩ棬姝ｈ亴' (Column)
        # Check COL_HEADERS definition: '鑱岃兘閮ㄩ棬姝ｈ亴'
        
        # Define the shared group: (Column, [Row1, Row2])
        # Column: '鑱岃兘閮ㄩ棬姝ｈ亴' (Examinee)
        # Rows: '涓績棰嗗鐝瓙 (姝ｈ亴)', '鎵€灞炲垎鍏徃鐝瓙姝ｈ亴'
        
        shared_col = '鑱岃兘閮ㄩ棬姝ｈ亴'
        row_a = '涓績棰嗗鐝瓙 (姝ｈ亴)'
        row_b = '鎵€灞炲垎鍏徃鐝瓙姝ｈ亴'
        
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
        return jsonify({'success': True, 'msg': '淇濆瓨鎴愬姛'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

# ==========================================
# 10. API: 閮ㄩ棬鏉冮噸閰嶇疆
# ==========================================

# ... (Previous Code)

# ==========================================
# 11. API: 棰嗗鐝瓙鎵撳垎鎻愪氦 (New)
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
        return jsonify({'success': False, 'msg': '鏈櫥褰?})

    req = request.json
    scores_dict = req.get('scores', {})
    
    # 1. Backend Validation
    all_ten = True
    total_score = 0
    
    try:
        rater_account = session.get('assessor_username')
        db = get_db()
        
        user_row = db.execute('SELECT dept_code FROM evaluation_accounts WHERE username=?', (rater_account,)).fetchone()
        if not user_row: return jsonify({'success': False, 'msg': '璐﹀彿寮傚父'})
        target_dept_code = user_row['dept_code']
        
        cols = []
        vals = []
        update_clauses = []
        update_vals = []
        
        for key, weight in TEAM_SCORE_WEIGHTS.items():
            raw_val = float(scores_dict.get(key, 0))
            
            # Integer Check
            if not raw_val.is_integer() or raw_val < 0 or raw_val > 10:
                return jsonify({'success': False, 'msg': f'鍒嗘暟蹇呴』涓?-10鏁存暟: {key}'})
                
            if raw_val != 10: all_ten = False
            
            # Calculate Weighted Score
            weighted_val = raw_val * (weight / 10.0)
            total_score += weighted_val
            
            cols.append(key)
            vals.append(raw_val)
            update_clauses.append(f"{key} = ?")
            update_vals.append(raw_val)
            
        if all_ten:
            return jsonify({'success': False, 'msg': '鏃犳晥璇勫垎锛氫笉鑳藉叏涓?0鍒?})
            
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
        
        # Update Account Status to "Submitted" ("鍚?)
        db.execute('UPDATE evaluation_accounts SET status = "鍚? WHERE username = ?', (rater_account,))
        
        db.commit()
        
        return jsonify({'success': True, 'msg': '鎻愪氦鎴愬姛'})
        
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

# ==========================================
# 12. API: 棰嗗浜哄憳缁煎悎鑰冩牳璇勪环 (New)
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
    """棰嗗浜哄憳缁煎悎鑰冩牳璇勪环"""
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
        return "璐﹀彿淇℃伅寮傚父", 403
        
    dept_code = user_row['dept_code']
    count_excellent = user_row['count_excellent'] or 0
    dept_name = user_row['dept_name']
    
    # Requirement: "鍙璇勪负浼樼浜烘暟涓嶄负0"
    if count_excellent <= 0:
        return render_template('assessment_error.html', msg="璇ラ儴闂ㄦ棤浼樼璇勯€夊悕棰濓紝鏃犻渶杩涜姝ら」鑰冩牳銆?)

    # 2. Get Examinees (Principals & Deputies of this Dept)
    raw_managers = db.execute('SELECT * FROM middle_managers WHERE dept_code=? ORDER BY sort_no ASC', (dept_code,)).fetchall()
    managers = []
    for m in raw_managers:
        # [Exclusion] Grassroots leaders check
        # Use simple string check to ensure consistency with Global Rule
        r_name = m['role'] or ''
        if '鍩哄眰' in r_name:
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
        return jsonify({'success': False, 'msg': '鏈櫥褰?})

    req = request.json
    scores_list = req.get('data', [])
    if not scores_list:
        return jsonify({'success': False, 'msg': '鏃犳彁浜ゆ暟鎹?})

    rater_account = session.get('assessor_username')
    db = get_db()
    
    # Verify Dept & Excellent Count Limit
    user_row = db.execute('''
        SELECT a.dept_code, d.count_excellent 
        FROM evaluation_accounts a
        LEFT JOIN department_config d ON a.dept_code = d.dept_code
        WHERE a.username=?
    ''', (rater_account,)).fetchone()
    
    if not user_row: return jsonify({'success': False, 'msg': '璐﹀彿寮傚父'})
    
    dept_code = user_row['dept_code']
    limit_excellent = user_row['count_excellent'] or 0
    
    # ---------------------------
    # Validation Logic
    # ---------------------------
    count_selected_excellent = 0
    
    for item in scores_list:
        name = item.get('name', '鏌愪汉')
        pid = item.get('id')
        grade = item.get('grade') # 浼樼/绉拌亴/鍩烘湰绉拌亴/涓嶇О鑱?
        
        # Count Excellent
        if grade == '浼樼':
            count_selected_excellent += 1
            
        # Check Scores
        scores = item.get('scores', {})
        ten_count = 0
        all_below_eight = True
        
        # We need validation per person
        for k in PERSONNEL_WEIGHTS.keys():
            val = float(scores.get(k, 0))
            if not val.is_integer() or val < 0 or val > 10:
                return jsonify({'success': False, 'msg': f'{name}: 鍒嗘暟蹇呴』涓?-10鏁存暟'})
            
            if val == 10: ten_count += 1
            if val >= 8: all_below_eight = False
            
        # Rule: 绉拌亴 -> 10鍒嗘暟閲?<= 6
        if grade == '绉拌亴' and ten_count > 6:
            return jsonify({'success': False, 'msg': f'{name}: 璇勪环涓衡€滅О鑱屸€濇椂锛?0鍒嗛」涓嶈兘瓒呰繃6涓?})
            
        # Rule: 鍩烘湰绉拌亴 -> 涓嶈兘鏈?0鍒?
        if grade == '鍩烘湰绉拌亴' and ten_count > 0:
            return jsonify({'success': False, 'msg': f'{name}: 璇勪环涓衡€滃熀鏈О鑱屸€濇椂锛屼笉鑳芥湁10鍒嗛」'})
            
        # Rule: 涓嶇О鑱?-> 鍏ㄩ儴鍒嗘暟 < 8
        if grade == '涓嶇О鑱? and not all_below_eight:
            return jsonify({'success': False, 'msg': f'{name}: 璇勪环涓衡€滀笉绉拌亴鈥濇椂锛屽悇椤硅瘎鍒嗛渶鍦?鍒嗕互涓?})

    # Excellent Limit Check
    if count_selected_excellent > limit_excellent:
        return jsonify({'success': False, 'msg': f'璇勪环涓衡€滀紭绉€鈥濈殑浜烘暟涓嶈兘瓒呰繃 {limit_excellent} 浜?(褰撳墠 {count_selected_excellent} 浜?'})

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
        return jsonify({'success': True, 'msg': '鎻愪氦鎴愬姛'})
        
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'msg': str(e)})

# Special Headers for Democratic Config (Splitting Principal and Assistant)
DEMOCRATIC_ROW_HEADERS = [
    '闄㈤瀵?, 
    '闄㈤暱鍔╃悊', '鑱岃兘閮ㄩ棬姝ｈ亴', # Split here
    '鑱岃兘閮ㄩ棬鍓亴', '鑱岃兘閮ㄩ棬鍏朵粬鍛樺伐',
    '鐮旂┒鎵€姝ｈ亴', '鐮旂┒鎵€鍓亴', '鐮旂┒鎵€鍏朵粬鍛樺伐',
    '涓績棰嗗鐝瓙 (姝ｈ亴)', '涓績棰嗗鐝瓙 (鍓亴)',
    '鏄嗗唸鐝瓙姝ｈ亴', '鏄嗗唸鐝瓙鍓亴',
    '鎵€灞炲垎鍏徃鐝瓙姝ｈ亴', '鎵€灞炲垎鍏徃鐝瓙鍓亴',
    '鑱屽伐浠ｈ〃涓熀灞傞瀵间汉鍛?(涓や腑蹇?', '鍏朵粬鑱屽伐浠ｈ〃 (涓や腑蹇?',
    '鑱屽伐浠ｈ〃涓熀灞傞瀵间汉鍛?(鏄嗗唸鍖椾含)', '鍏朵粬鑱屽伐浠ｈ〃 (鏄嗗唸鍖椾含)',
    '鑱屽伐浠ｈ〃涓熀灞傞瀵间汉鍛?(鍒嗗叕鍙?', '鍏朵粬鑱屽伐浠ｈ〃 (鍒嗗叕鍙?'
]

@app.route('/admin/democratic-config')
@admin_required
def democratic_config():
    """涓眰骞查儴娴嬭瘎鎵撳垎瀵瑰簲閰嶇疆椤甸潰"""
    db = get_db()
    
    # Check if we need to migrate the combined role to split roles
    # Check if '鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?' exists in table
    combined_check = db.execute("SELECT count(*) FROM democratic_rating_config WHERE rater_role='鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?'").fetchone()[0]
    if combined_check > 0:
        # Perform Migration: Copy permissions to new roles and delete old
        old_rows = db.execute("SELECT * FROM democratic_rating_config WHERE rater_role='鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?'").fetchall()
        for row in old_rows:
            # Insert for Assistant
            db.execute("INSERT OR IGNORE INTO democratic_rating_config (examinee_role, rater_role, is_allowed) VALUES (?, ?, ?)", 
                       (row['examinee_role'], '闄㈤暱鍔╃悊', row['is_allowed']))
            # Insert for Functional Principal
            db.execute("INSERT OR IGNORE INTO democratic_rating_config (examinee_role, rater_role, is_allowed) VALUES (?, ?, ?)", 
                       (row['examinee_role'], '鑱岃兘閮ㄩ棬姝ｈ亴', row['is_allowed']))
        
        # Delete old
        db.execute("DELETE FROM democratic_rating_config WHERE rater_role='鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?'")
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
    """淇濆瓨鎵撳垎瀵瑰簲閰嶇疆"""
    data = request.json
    updates = data.get('updates', [])
    
    if not updates:
        return jsonify({'success': True, 'msg': '鏃犲彉鏇?})
        
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
        return jsonify({'success': True, 'msg': '淇濆瓨鎴愬姛'})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'msg': str(e)}), 500

# ==========================================
# 4.3 姘戜富娴嬭瘎 (Project 3)
# ==========================================

# ==========================================
# 4.3 姘戜富娴嬭瘎 (Project 3)
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
        if r == '鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?':
            # Determine specific identity
            if user_info['dept_name'] == '闄㈤暱鍔╃悊' or user_info['dept_code'] == 'A0':
                my_rater_roles.append('闄㈤暱鍔╃悊')
            else:
                my_rater_roles.append('鑱岃兘閮ㄩ棬姝ｈ亴')
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
        {'key': 'assistant', 'title': '闄㈤暱鍔╃悊', 'roles': ['闄㈤暱鍔╃悊']},
        {'key': 'functional', 'title': '鑱岃兘閮ㄩ棬涓庣洿灞炴満鏋勪腑绾х鐞嗕汉鍛?, 'roles': ['鑱岃兘閮ㄩ棬姝ｈ亴', '鑱岃兘閮ㄩ棬鍓亴']},
        {'key': 'institute', 'title': '鐮旂┒鎵€涓骇绠＄悊浜哄憳', 'roles': ['鐮旂┒鎵€姝ｈ亴', '鐮旂┒鎵€鍓亴']},
        {'key': 'center_kungang', 'title': '涓績鍙婃槅鍐堜腑绾х鐞嗕汉鍛?, 'roles': ['涓や腑蹇冩鑱?, '涓や腑蹇冨壇鑱?, '鏄嗗唸鐝瓙鍓亴 (鍖椾含)', '鎵€灞炲垎鍏徃 (鍏板窞銆佹姎椤? 鐝瓙姝ｈ亴', '鎵€灞炲垎鍏徃 (鍏板窞銆佹姎椤? 鐝瓙鍓亴']},
        {'key': 'kungang_branch', 'title': '鏄嗗唸鍒堕€犲垎鍏徃涓骇绠＄悊浜哄憳', 'roles': ['鎵€灞炲垎鍏徃 (鍏板窞銆佹姎椤? 鐝瓙姝ｈ亴', '鎵€灞炲垎鍏徃 (鍏板窞銆佹姎椤? 鐝瓙鍓亴']} 
    ]
    
    # 4. Check Availability & Dynamic Renaming
    is_kungang_rater = any(r in ['鏄嗗唸鐝瓙姝ｈ亴', '鏄嗗唸鐝瓙鍓亴', '鎵€灞炲垎鍏徃鐝瓙姝ｈ亴'] for r in my_rater_roles)
    allowed_set = set(allowed_roles)
    
    available_groups = []
    
    for g in all_groups:
        effective_roles = g['roles'][:] # Copy
        
        # Special Logic: KunGang Rater restrictions
        if is_kungang_rater:
            if g['key'] == 'center_kungang':
                # Filter out Branch roles & Beijing Deputy
                effective_roles = [r for r in effective_roles if '鍒嗗叕鍙? not in r and r != '鏄嗗唸鐝瓙鍓亴 (鍖椾含)']
            
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
        # Assuming Roles have '姝ｈ亴' or '鍓亴' in their name string
        
        has_principal = any('姝ｈ亴' in r for r in my_group_roles)
        has_deputy = any('鍓亴' in r for r in my_group_roles)
        
        # We modify the title copy for this instance
        display_title = g['title']
        
        # Specific overrides requested by User
        if g['key'] == 'functional':
            if has_principal and not has_deputy:
                display_title = '鑱岃兘閮ㄩ棬涓庣洿灞炴満鏋勬鑱?
            elif has_deputy and not has_principal:
                display_title = '鑱岃兘閮ㄩ棬涓庣洿灞炴満鏋勫壇鑱?
                
        elif g['key'] == 'institute':
             if has_principal and not has_deputy:
                display_title = '鐮旂┒鎵€姝ｈ亴'
             elif has_deputy and not has_principal:
                display_title = '鐮旂┒鎵€鍓亴'
        
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
    """涓眰骞查儴姘戜富娴嬭瘎 (鎸夊垎缁勬樉绀?"""
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
    
    if not user_row: return "鏃犳晥璐﹀彿", 403
    
    full_user_for_roles = dict(user_row) # helper
    raw_roles = get_user_rater_roles(full_user_for_roles, full_user_for_roles)
    
    # [Fix for KP001]: Apply Split Logic similar to get_democratic_nav
    # Because democratic_rating_config uses split keys (functional vs assistant), but RATER_RULES returns combined.
    my_rater_roles = []
    for r in raw_roles:
        if r == '鑱岃兘閮ㄩ棬姝ｈ亴 (鍚櫌闀垮姪鐞?':
            if user_row['dept_name'] == '闄㈤暱鍔╃悊' or user_row['dept_code'] == 'A0':
                my_rater_roles.append('闄㈤暱鍔╃悊')
            else:
                my_rater_roles.append('鑱岃兘閮ㄩ棬姝ｈ亴')
        else:
            my_rater_roles.append(r)
    
    # 1. Validation: Is this group_key allowed for me?
    nav_items = get_democratic_nav(user_row)
    target_group = next((g for g in nav_items if g['key'] == group_key), None)
    
    if not target_group:
        return render_template('assessment_error.html', msg="鏃犳晥鐨勬祴璇勭粍鎴栨棤璁块棶鏉冮檺")
    
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
         return render_template('assessment_error.html', error_message="娌℃湁鍙瘎浠风殑浜哄憳")
    
    # [Fix for Role Mismatch] Map '涓や腑蹇?..' (Config Key) to '涓績...' (DB Value)
    db_roles = []
    for r in effective_roles:
        if r == '涓や腑蹇冩鑱?: db_roles.append('涓績姝ｈ亴')
        elif r == '涓や腑蹇冨壇鑱?: db_roles.append('涓績鍓亴')
        elif r == '鎵€灞炲垎鍏徃 (鍏板窞銆佹姎椤? 鐝瓙姝ｈ亴': db_roles.append('涓績姝ｈ亴')
        elif r == '鎵€灞炲垎鍏徃 (鍏板窞銆佹姎椤? 鐝瓙鍓亴': db_roles.append('涓績鍓亴')
        elif r == '鏄嗗唸鐝瓙鍓亴 (鍖椾含)': db_roles.append('涓績鍓亴')
        else: db_roles.append(r)
        
    ph = ','.join(['?'] * len(db_roles))
    
    # Fetch all candidates in these roles
    mgrs = db.execute(f'SELECT * FROM middle_managers WHERE role IN ({ph}) ORDER BY dept_code ASC, sort_no ASC', db_roles).fetchall()
    
    is_kungang_rater = any(r in ['鏄嗗唸鐝瓙姝ｈ亴', '鏄嗗唸鐝瓙鍓亴', '鎵€灞炲垎鍏徃鐝瓙姝ｈ亴'] for r in my_rater_roles)
    is_college_leader = (user_row['dept_type'] == '闄㈤瀵?)
    
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
        if is_kungang_rater and c_role == '鏄嗗唸鐝瓙鍓亴 (鍖椾含)':
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
    
    page_title = f"{target_group['title']}娴嬭瘎" # Dynamic title based on group name
    
    return render_template('assessment_democratic.html', 
                           groups=[group_data], # Single group list
                           page_title=page_title,
                           scores_map=scores_map,
                           current_group_key=group_key)


# API: Submit Democratic Scores
@app.route('/api/assessment/democratic/submit', methods=['POST'])
def submit_democratic_score():
    if session.get('assessor_role') != 'assessor':
        return jsonify({'success': False, 'msg': '鏈櫥褰?})

    req = request.json
    data_list = req.get('data', [])
    if not data_list:
        return jsonify({'success': False, 'msg': '鏃犳彁浜ゆ暟鎹?})

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
                return jsonify({'success': False, 'msg': '鍒嗘暟鏍煎紡閿欒'})
                
            if val < 0 or val > 10: 
                return jsonify({'success': False, 'msg': '鍒嗘暟蹇呴』鍦?0-10 涔嬮棿'})
            
            if val != 10:
                has_non_ten = True
                
    if not has_non_ten:
        return jsonify({'success': False, 'msg': '鏃犳晥鎻愪氦锛氭墍鏈夎瘎鍒嗗潎涓?0鍒嗐€傝鑷冲皯瀵规煇涓€椤圭粰鍑洪潪10鍒嗙殑璇勪环銆?})

    # ---------------------------
    # Save to DB
    # ---------------------------
    try:
        cur = db.cursor()

        for item in data_list:
            examinee_id = item.get('id')
            role = item.get('role') # Passed from frontend for convenience
            scores = item.get('scores', {})
            
            score_vals = []
            total = 0
            for d in dims:
                val = float(scores.get(d, 0))
                score_vals.append(val)
                total += val 
            
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
        return jsonify({'success': True, 'msg': '鎻愪氦鎴愬姛'})
        
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'msg': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

# ==========================================
# 13. API: 浼樼骞查儴姘戜富鎺ㄨ崘-姝ｈ亴 (New & Independent)
# ==========================================

@app.route('/assessment/recommend-principal')
def assessment_recommend_principal():
    """浼樼骞查儴姘戜富鎺ㄨ崘-姝ｈ亴 椤甸潰"""
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
    
    if not user_row: return "鏃犳晥璐﹀彿", 403
    
    limit_count = user_row['count_recommend_principal'] or 0
    dept_name = user_row['dept_name']
    
    if limit_count < 1:
        return render_template('assessment_error.html', msg="璐甸儴闂ㄦ棤姝ら」鎺ㄨ崘鍚嶉")
        
    # 2. Fetch Candidates (recommend_principal table)
    # [FILTER] Only show candidates from the same department
    dept_code = user_row['dept_code']
    candidates = db.execute('SELECT * FROM recommend_principal WHERE dept_code=? ORDER BY sort_no ASC', (dept_code,)).fetchall()
    
    # 3. Fetch Existing Selections
    recs = db.execute('SELECT examinee_id FROM recommendation_scores_principal WHERE rater_account=?', 
                      (rater_account,)).fetchall()
    selected_ids = [r['examinee_id'] for r in recs]
    
    page_title = f"{dept_name}浼樼骞查儴姘戜富鎺ㄨ崘-姝ｈ亴"
    
    return render_template('assessment_recommend_principal.html',
                           page_title=page_title,
                           limit_count=limit_count,
                           candidates=candidates,
                           selected_ids=selected_ids)

@app.route('/api/assessment/recommend-principal/submit', methods=['POST'])
def submit_recommend_principal():
    if session.get('assessor_role') != 'assessor':
        return jsonify({'success': False, 'msg': '鏈櫥褰?})

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
        return jsonify({'success': False, 'msg': f'鎺ㄨ崘浜烘暟瓒呰繃闄愬埗锛佹渶澶氭帹鑽?{limit_count} 浜猴紝褰撳墠閫夋嫨浜?{len(selected_ids)} 浜恒€?})
        
    # 2. Save (Replace All logic)
    # Since this is a simple "select N from M", we can clear old recommendations for this user and insert new ones.
    try:
        cur = db.cursor()
        
        # Clear old
        cur.execute('DELETE FROM recommendation_scores_principal WHERE rater_account=?', (rater_account,))
        
        # Insert new
        dept_code = user_row['dept_code']
        
        if selected_ids:
             # Fetch names for redundancy? Or just IDs. User requirement said "associate personnel info". 
             # For storage, name might be useful but ID is critical.
             # Let's fetch names to store them as plan suggested.
             
             placeholders = ','.join(['?'] * len(selected_ids))
             name_map_rows = db.execute(f'SELECT id, name FROM recommend_principal WHERE id IN ({placeholders})', selected_ids).fetchall()
             name_map = {r['id']: r['name'] for r in name_map_rows}
             
             for uid in selected_ids:
                 uid_int = int(uid)
                 u_name = name_map.get(uid_int, '')
                 cur.execute('''
                    INSERT INTO recommendation_scores_principal (rater_account, target_dept_code, examinee_id, examinee_name, is_recommended)
                    VALUES (?, ?, ?, ?, 1)
                 ''', (rater_account, dept_code, uid_int, u_name))
        
        db.commit()
        return jsonify({'success': True, 'msg': '鎻愪氦鎴愬姛'})
        
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'msg': str(e)})

# ==========================================
# 14. API: 浼樼骞查儴姘戜富鎺ㄨ崘-鍓亴 (New & Independent)
# ==========================================

@app.route('/assessment/recommend-deputy')
def assessment_recommend_deputy():
    """浼樼骞查儴姘戜富鎺ㄨ崘-鍓亴 椤甸潰"""
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
    
    if not user_row: return "鏃犳晥璐﹀彿", 403
    
    limit_count = user_row['count_recommend_deputy'] or 0
    dept_name = user_row['dept_name']
    
    if limit_count < 1:
        return render_template('assessment_error.html', msg="璐甸儴闂ㄦ棤姝ら」鎺ㄨ崘鍚嶉")
        
    # 2. Fetch Candidates (recommend_deputy table)
    # [FILTER] Only show candidates from the same department
    dept_code = user_row['dept_code']
    candidates = db.execute('SELECT * FROM recommend_deputy WHERE dept_code=? ORDER BY sort_no ASC', (dept_code,)).fetchall()
    
    # 3. Fetch Existing Selections
    recs = db.execute('SELECT examinee_id FROM recommendation_scores_deputy WHERE rater_account=?', 
                      (rater_account,)).fetchall()
    selected_ids = [r['examinee_id'] for r in recs]
    
    page_title = f"{dept_name}浼樼骞查儴姘戜富鎺ㄨ崘-鍓亴"
    
    return render_template('assessment_recommend_deputy.html',
                           page_title=page_title,
                           limit_count=limit_count,
                           candidates=candidates,
                           selected_ids=selected_ids)

@app.route('/api/assessment/recommend-deputy/submit', methods=['POST'])
def submit_recommend_deputy():
    if session.get('assessor_role') != 'assessor':
        return jsonify({'success': False, 'msg': '鏈櫥褰?})

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
        return jsonify({'success': False, 'msg': f'鎺ㄨ崘浜烘暟瓒呰繃闄愬埗锛佹渶澶氭帹鑽?{limit_count} 浜猴紝褰撳墠閫夋嫨浜?{len(selected_ids)} 浜恒€?})
        
    # 2. Save (Replace All logic)
    try:
        cur = db.cursor()
        
        # Clear old
        cur.execute('DELETE FROM recommendation_scores_deputy WHERE rater_account=?', (rater_account,))
        
        # Insert new
        dept_code = user_row['dept_code']
        
        if selected_ids:
             placeholders = ','.join(['?'] * len(selected_ids))
             name_map_rows = db.execute(f'SELECT id, name FROM recommend_deputy WHERE id IN ({placeholders})', selected_ids).fetchall()
             name_map = {r['id']: r['name'] for r in name_map_rows}
             
             for uid in selected_ids:
                 uid_int = int(uid)
                 u_name = name_map.get(uid_int, '')
                 cur.execute('''
                    INSERT INTO recommendation_scores_deputy (rater_account, target_dept_code, examinee_id, examinee_name, is_recommended)
                    VALUES (?, ?, ?, ?, 1)
                 ''', (rater_account, dept_code, uid_int, u_name))
        
        db.commit()
        return jsonify({'success': True, 'msg': '鎻愪氦鎴愬姛'})
        
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'msg': str(e)})

# ==========================================
# 15. API: 骞查儴閫夋嫈浠荤敤宸ヤ綔姘戜富璇勮琛?(Project 6)
# ==========================================

@app.route('/assessment/selection-appointment')
def assessment_selection_appointment():
    """骞查儴閫夋嫈浠荤敤宸ヤ綔姘戜富璇勮琛?椤甸潰"""
    if session.get('assessor_role') != 'assessor':
        return redirect(url_for('index'))
        
    rater_account = session.get('assessor_username')
    db = get_db()
    
    # 1. Permission Check
    user_row = db.execute('SELECT username, dept_code FROM evaluation_accounts WHERE username=?', (rater_account,)).fetchone()
    if not user_row: return "鏃犳晥璐﹀彿", 403
    
    # Allowed: V, W, X, Y
    allowed_depts = ['V', 'W', 'X', 'Y']
    if user_row['dept_code'] not in allowed_depts:
        return render_template('assessment_error.html', msg="鎮ㄧ殑璐﹀彿鏃犳潈璁块棶姝よ瘎璁〃")
        
    # 2. Fetch Existing Data
    existing = db.execute('SELECT * FROM evaluation_selection_appointment WHERE rater_account=?', (rater_account,)).fetchone()
    
    d_row = db.execute('SELECT dept_name FROM department_config WHERE dept_code=?', (user_row['dept_code'],)).fetchone()
    dept_name = d_row['dept_name'] if d_row else ""
    
    return render_template('assessment_selection_appointment.html',
                           page_title=f"{dept_name}骞查儴閫夋嫈浠荤敤宸ヤ綔姘戜富璇勮琛?,
                           data=existing)

@app.route('/api/assessment/selection-appointment/submit', methods=['POST'])
def submit_selection_appointment():
    if session.get('assessor_role') != 'assessor':
        return jsonify({'success': False, 'msg': '鏈櫥褰?})

    req = request.json
    rater_account = session.get('assessor_username')
    db = get_db()
    
    # 1. Permission Check
    user_row = db.execute('SELECT username, dept_code FROM evaluation_accounts WHERE username=?', (rater_account,)).fetchone()
    if not user_row or user_row['dept_code'] not in ['V', 'W', 'X', 'Y']:
        return jsonify({'success': False, 'msg': '鏃犳潈鎿嶄綔'})
        
    # 2. Extract Data
    q1 = req.get('q1_overall')
    q2 = req.get('q2_supervision')
    q3 = req.get('q3_rectification')
    # q1-q3 are required
    if not all([q1, q2, q3]):
         return jsonify({'success': False, 'msg': '璇峰畬鎴愬墠涓夐」蹇呭～璇勪环锛?})
         
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
        return jsonify({'success': True, 'msg': '鎻愪氦鎴愬姛'})
        
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'msg': str(e)})

# ==========================================
# 16. API: 鏂版彁鎷斾换鐢ㄥ共閮ㄦ皯涓昏瘎璁〃 (Project 7)
# ==========================================

@app.route('/assessment/new-promotion')
def assessment_new_promotion():
    """鏂版彁鎷斾换鐢ㄥ共閮ㄦ皯涓昏瘎璁〃 椤甸潰"""
    if session.get('assessor_role') != 'assessor':
        return redirect(url_for('index'))
        
    rater_account = session.get('assessor_username')
    db = get_db()
    
    # 1. Permission Check (X, Y)
    user_row = db.execute('SELECT username, dept_code FROM evaluation_accounts WHERE username=?', (rater_account,)).fetchone()
    if not user_row: return "鏃犳晥璐﹀彿", 403
    
    allowed_depts = ['X', 'Y']
    if user_row['dept_code'] not in allowed_depts:
        return render_template('assessment_error.html', msg="鎮ㄧ殑璐﹀彿鏃犳潈璁块棶姝よ瘎璁〃")
        
    # 2. Fetch Candidates
    # [UPDATED Project 8]: Source from `center_grassroots_leaders` table now.
    # Criteria: dept_code matches user's dept_code (X or Y)
    # The table `center_grassroots_leaders` stores all needed info. 
    # Logic: simple SELECT * WHERE dept_code=?
    
    candidates = db.execute('''
        SELECT * FROM center_grassroots_leaders 
        WHERE dept_code=? 
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
                           page_title=f"{dept_name}鏂版彁鎷斾换鐢ㄥ共閮ㄦ皯涓昏瘎璁〃",
                           candidates=candidates,
                           existing_data=existing_data)

@app.route('/api/assessment/new-promotion/submit', methods=['POST'])
def submit_new_promotion():
    if session.get('assessor_role') != 'assessor':
        return jsonify({'success': False, 'msg': '鏈櫥褰?})

    req = request.json
    selections = req.get('selections', {}) # Dict {id: value}
    
    rater_account = session.get('assessor_username')
    db = get_db()
    
    # Permission Check
    user_row = db.execute('SELECT username, dept_code FROM evaluation_accounts WHERE username=?', (rater_account,)).fetchone()
    if not user_row or user_row['dept_code'] not in ['X', 'Y']:
        return jsonify({'success': False, 'msg': '鏃犳潈鎿嶄綔'})
        
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
        return jsonify({'success': True, 'msg': '鎻愪氦鎴愬姛'})
        
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'msg': str(e)})

# ==========================================
# 17. API: 涓績鍩哄眰棰嗗绠＄悊 (Project 8)
# ==========================================

ALLOWED_ROLES_CGL = ['涓績鍩哄眰棰嗗'] # Or any validation we want? Maybe reuse or just loose check.

CENTER_GRASSROOTS_MAPPING = {
    # '搴忓彿' removed as not in user list, optional anyway
    '閮ㄩ棬鍐呮帓搴忓彿': 'sort_no',
    '濮撳悕': 'name',
    '鎬у埆': 'gender',
    '鍑虹敓骞存湀': 'birth_date',
    '鐜颁换鑱屽姟': 'position',      # Was '鑱屽姟'
    '閮ㄩ棬鍚嶇О': 'dept_name',
    '閮ㄩ棬浠ｇ爜': 'dept_code',     # Was '閮ㄩ棬缂栫爜'
    '鍛樺伐瑙掕壊': 'role',
    '宀椾綅灞傜骇': 'rank_level',    # Was '鑱岀骇'
    '浠昏亴鏃堕棿': 'tenure_time',
    '鏂囧寲绋嬪害': 'education',     # Was '瀛﹀巻'
    '鐜拌亴绾ф椂闂?: 'rank_time',
    
    # New Columns
    '鍘熶换鑱屽姟': 'original_position',
    '鎻愭嫈鏂瑰紡': 'promotion_method',
    '鏄惁鏂版彁鎷斿共閮?: 'is_newly_promoted'
}

@app.route('/center-grassroots-management')
@admin_required
def center_grassroots_management():
    """涓績鍩哄眰棰嗗绠＄悊椤?""
    db = get_db()
    managers = db.execute('SELECT * FROM center_grassroots_leaders ORDER BY dept_code ASC, sort_no ASC').fetchall()
    return render_template('center_grassroots_management.html', managers=managers)

@app.route('/api/center-grassroots/upload', methods=['POST'])
@admin_required
def upload_center_grassroots():
    if 'file' not in request.files: return jsonify({'success': False, 'msg': '鏃犳枃浠?})
    file = request.files['file']
    try:
        df = pd.read_excel(file)
        df = df.fillna('')
        # Strip whitespace from columns
        df.columns = df.columns.str.strip()
        
        # Validation: Check required columns
        required_cols = ['濮撳悕', '鐜颁换鑱屽姟', '閮ㄩ棬鍚嶇О']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
             return jsonify({'success': False, 'msg': f'瀵煎叆澶辫触锛氱己灏戝繀瑕佸垪 {", ".join(missing)}'})
             
        for col in ['鍑虹敓骞存湀', '鐜拌亴绾ф椂闂?, '浠昏亴鏃堕棿']:
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
            if '閮ㄩ棬鍚嶇О' in df.columns and row['閮ㄩ棬鍚嶇О'] in dept_map:
                cols.append('dept_id')
                vals.append(dept_map[row['閮ㄩ棬鍚嶇О']])
                
            if cols:
                cursor.execute(f'INSERT INTO center_grassroots_leaders ({", ".join(cols)}) VALUES ({", ".join(["?"]*len(cols))})', vals)
                
        db.commit()
        return jsonify({'success': True, 'msg': f'瀵煎叆鎴愬姛: {len(df)} 浜?})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/center-grassroots/save', methods=['POST'])
@admin_required
def save_center_grassroots():
    req = request.json
    if not req or 'data' not in req: return jsonify({'success': False, 'msg': '鏃犳暟鎹?})
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
        return jsonify({'success': True, 'msg': '淇濆瓨鎴愬姛'})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/center-grassroots/export')
@admin_required
def export_center_grassroots():
    try:
        db = get_db()
        df = pd.read_sql_query("SELECT * FROM center_grassroots_leaders ORDER BY dept_code ASC, sort_no ASC", db)
        for col in ['id', 'dept_id', 'updated_at']:
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
