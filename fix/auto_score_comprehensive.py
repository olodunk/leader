import urllib.request
import urllib.parse
import http.cookiejar
import sqlite3
import random
import re
import json

# Configuration
BASE_URL = 'http://127.0.0.1:1111'
DB_PATH = 'evaluation.db'

# Keys for Project 1
# From previous context
TEAM_SCORE_KEYS = [
    'good_team', 'political_perf', 'unity', 'reform', 'performance', 'party_building'
]
# Keys for Project 2
PERSONNEL_SCORE_KEYS = [
    's_political_ability', 's_political_perf', 's_party_build', 's_professionalism',
    's_leadership', 's_learning_innov', 's_performance', 's_responsibility',
    's_style_image', 's_integrity'
]
DEMOCRATIC_GROUPS = ['assistant', 'functional', 'institute', 'center_kungang', 'kungang_branch']

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_all_accounts():
    conn = get_db_connection()
    accounts = conn.execute('SELECT * FROM evaluation_accounts').fetchall()
    conn.close()
    return accounts

def get_managers_by_dept(dept_code):
    conn = get_db_connection()
    managers = conn.execute('SELECT * FROM middle_managers WHERE dept_code=?', (dept_code,)).fetchall()
    conn.close()
    return managers

def get_excellent_limit(dept_code):
    conn = get_db_connection()
    res = conn.execute('SELECT count_excellent FROM department_config WHERE dept_code=?', (dept_code,)).fetchone()
    conn.close()
    return res['count_excellent'] if res else 0

class Session:
    def __init__(self):
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar))
    
    def post(self, url, json_data):
        data_bytes = json.dumps(json_data).encode('utf-8')
        req = urllib.request.Request(url, data=data_bytes, headers={'Content-Type': 'application/json'})
        return self._open(req)
        
    def get(self, url):
        req = urllib.request.Request(url)
        return self._open(req)
        
    def _open(self, req):
        try:
            with self.opener.open(req) as response:
                return Response(response.read(), response.status)
        except urllib.error.HTTPError as e:
            return Response(e.read(), e.code)
        except Exception as e:
            return Response(str(e).encode(), 500)

class Response:
    def __init__(self, content, status):
        self.content = content
        self.status_code = status
    
    def json(self):
        try:
            return json.loads(self.content.decode('utf-8'))
        except:
            return {}
            
    @property
    def text(self):
        return self.content.decode('utf-8', errors='ignore')

def run_automation():
    accounts = get_all_accounts()
    print(f"Total Accounts to Process: {len(accounts)}")
    
    for idx, acc in enumerate(accounts):
        username = acc['username']
        session = Session()
        print(f"[{idx+1}/{len(accounts)}] Processing {username}...")

        # 1. Login
        try:
            resp = session.post(f'{BASE_URL}/api/login', {
                'username': username,
                'password': acc['password'],
                'type': 'assessment'
            })
            if resp.json().get('success') is not True:
                # If submitted, output message but don't hard stop? 
                # Actually, if status is 'Submitted', app prevents login.
                # If status is 'No', app prevents login.
                pass
        except Exception as e:
            print(f"  Login Error: {e}")
            continue

        # 2. Project 1: Team Evaluation
        try:
            scores = {}
            for k in TEAM_SCORE_KEYS:
                scores[k] = random.randint(8, 10)
            
            resp = session.post(f'{BASE_URL}/api/assessment/team/submit', scores)
            if resp.json().get('success'):
                pass # print("  [Team] Submitted.")
            else:
                pass # print(f"  [Team] Msg: {resp.json().get('msg')}")
                
        except Exception:
            pass

        # 3. Project 2: Personnel Assessment
        try:
            dept_code = acc['dept_code']
            managers = get_managers_by_dept(dept_code)
            valid_managers = [m for m in managers if '基层' not in (m['role'] or '')]
            
            if valid_managers:
                count_excellent = get_excellent_limit(dept_code)
                random.shuffle(valid_managers)
                submission_list = []
                
                for i, m in enumerate(valid_managers):
                    is_excellent = (i < count_excellent)
                    grade = '优秀' if is_excellent else '称职'
                    p_scores = {}
                    
                    if is_excellent:
                        keys = list(PERSONNEL_SCORE_KEYS)
                        random.shuffle(keys)
                        nine_key = keys[0]
                        for k in keys:
                            p_scores[k] = 9 if k == nine_key else 10
                    else:
                        for k in PERSONNEL_SCORE_KEYS:
                            p_scores[k] = random.randint(8, 10)
                            
                    submission_list.append({
                        'id': m['id'],
                        'name': m['name'],
                        'grade': grade,
                        'scores': p_scores
                    })
                
                resp = session.post(f'{BASE_URL}/api/assessment/personnel/submit', {'data': submission_list})
                if resp.json().get('success'):
                    pass # print(f"  [Personnel] Submitted ({len(valid_managers)}).")
        except Exception:
            pass

        # 4. Project 3: Democratic Evaluation
        for grp in DEMOCRATIC_GROUPS:
            try:
                page_resp = session.get(f'{BASE_URL}/assessment/democratic-evaluation/{grp}')
                if page_resp.status_code != 200: continue
                html = page_resp.text
                
                ids = re.findall(r'data-id="(\d+)"', html)
                if not ids: continue
                
                input_names = sorted(list(set(re.findall(r'name="(d_[a-z_]+)"', html))))
                if not input_names: continue
                
                submit_data = []
                for eid in ids:
                    s_map = {}
                    for k in input_names:
                        s_map[k] = random.randint(8, 10)
                        
                    submit_data.append({
                        'id': eid,
                        'scores': s_map
                    })
                    
                resp = session.post(f'{BASE_URL}/api/assessment/democratic/submit', {'data': submit_data})
                if resp.json().get('success'):
                    pass # print(f"  [Democratic-{grp}] Submitted.")
                    
            except Exception:
                pass

if __name__ == '__main__':
    run_automation()
