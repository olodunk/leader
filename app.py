import sqlite3
import pandas as pd
import os
import datetime
from io import BytesIO
from flask import Flask, render_template, g, request, jsonify, redirect, url_for, send_file

app = Flask(__name__)
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
    '机关正职',
    '机关副职',
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
# 3. 页面路由 (View Routes)
# ==========================================

@app.route('/')
def index():
    db = get_db()
    try:
        dept_count = db.execute('SELECT COUNT(*) FROM department_config').fetchone()[0]
    except:
        dept_count = 0
    return render_template('index.html', dept_count=dept_count)

@app.route('/department-config')
def department_config():
    db = get_db()
    depts = db.execute('SELECT * FROM department_config ORDER BY sort_no ASC, serial_no ASC').fetchall()
    return render_template('department_config.html', depts=depts)

@app.route('/personnel-management')
def personnel_management():
    """人员管理页"""
    db = get_db()
    # 【修改点】此处改为按 sort_no (部门内排序号) 升序排列
    managers = db.execute('SELECT * FROM middle_managers ORDER BY sort_no ASC').fetchall()
    return render_template('personnel_management.html', managers=managers)

@app.route('/recommend-principal')
def recommend_principal():
    """正职推荐页"""
    db = get_db()
    data = db.execute('SELECT * FROM recommend_principal ORDER BY sort_no ASC').fetchall()
    return render_template('recommend_principal.html', data=data)

@app.route('/recommend-deputy')
def recommend_deputy():
    """副职推荐页"""
    db = get_db()
    data = db.execute('SELECT * FROM recommend_deputy ORDER BY sort_no ASC').fetchall()
    return render_template('recommend_deputy.html', data=data)

# ==========================================
# 4. API: 部门配置
# ==========================================

@app.route('/api/department/upload', methods=['POST'])
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
# 5. API: 人员管理
# ==========================================

@app.route('/api/personnel/upload', methods=['POST'])
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
# 6. API: 正职推荐
# ==========================================

@app.route('/api/recommend-principal/upload', methods=['POST'])
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
# 7. API: 副职推荐
# ==========================================

@app.route('/api/recommend-deputy/upload', methods=['POST'])
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

if __name__ == '__main__':
    app.run(debug=True, port=1111)