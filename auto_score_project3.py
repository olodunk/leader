
import sqlite3
import re
import random
import os
import sys

# Add current directory to path so we can import app
sys.path.append(os.getcwd())

try:
    from app import app
except ImportError:
    print("Error: Could not import 'app'. Make sure you are running this script from the same directory as app.py")
    sys.exit(1)

DATABASE = 'evaluation.db'

def get_a0_users():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # Assuming 'A0' is the dept_code for College Leaders
    users = cur.execute("SELECT * FROM evaluation_accounts WHERE dept_code = 'A0'").fetchall()
    conn.close()
    return users

def parse_examinees(html_content):
    """
    Extracts examinee info from the HTML string using regex.
    Looking for: <tr class="person-row" data-id="123" data-name="Name" data-role="Role">
    """
    pattern = r'<tr class="person-row"\s+data-id="(\d+)"\s+data-name="(.*?)"\s+data-role="(.*?)">'
    matches = re.findall(pattern, html_content)
    examinees = []
    for m in matches:
        examinees.append({
            'id': m[0],
            'name': m[1],
            'role': m[2]
        })
    return examinees

def generate_random_scores():
    # Dimensions
    dims = ['s_political_ability', 's_political_perf', 's_party_build', 's_professionalism',
            's_leadership', 's_learning_innov', 's_performance', 's_responsibility',
            's_style_image', 's_integrity']
    
    scores = {}
    
    # Strategy: Mostly Excellent (9-10). Ensure at least one is NOT 10.
    # To be safe and "Excellent", we can do mostly 10s and a few 9s.
    # Let's say we pick 1-3 dimensions to be 9, rest 10.
    
    num_non_ten = random.randint(1, 3) # 1 to 3 items will be 9
    non_ten_indices = random.sample(range(len(dims)), num_non_ten)
    
    for i, dim in enumerate(dims):
        if i in non_ten_indices:
            scores[dim] = 9
        else:
            scores[dim] = 10
            
    return scores

def main():
    users = get_a0_users()
    print(f"Found {len(users)} accounts in department A0.")
    
    groups = ['assistant', 'functional', 'institute', 'center_kungang', 'kungang_branch']
    
    success_count = 0
    
    with app.test_client() as client:
        for user in users:
            username = user['username']
            password = user['password']
            print(f"Processing User: {username} ...")
            
            # 1. Login
            resp = client.post('/api/login', json={
                'username': username,
                'password': password,
                'type': 'assessment'
            })
            
            if resp.json.get('success') is not True:
                print(f"  [ERROR] Login failed for {username}: {resp.json.get('msg')}")
                continue
                
            # 2. Iterate Groups
            for group in groups:
                # print(f"  Checking group: {group}")
                resp = client.get(f'/assessment/democratic-evaluation/{group}')
                
                if resp.status_code != 200:
                    # Likely no permission or invalid group for this user
                    # print(f"  - Group {group}: Unreachable (Status {resp.status_code})")
                    continue
                
                html = resp.data.decode('utf-8')
                examinees = parse_examinees(html)
                
                if not examinees:
                    # print(f"  - Group {group}: No candidates found.")
                    continue
                
                print(f"  - Group {group}: Found {len(examinees)} candidates. Scoring...")
                
                # 3. Prepare Payload
                payload_data = []
                for ex in examinees:
                    scores = generate_random_scores()
                    payload_data.append({
                        'id': ex['id'],
                        'role': ex['role'], # Pass role back as required by API
                        'scores': scores,
                        'name': ex['name'] # Optional but good for logging/API consistency
                    })
                
                # 4. Submit
                submit_resp = client.post('/api/assessment/democratic/submit', json={'data': payload_data})
                
                if submit_resp.json.get('success'):
                    print(f"    [SUCCESS] Submitted scores for group {group}.")
                else:
                    print(f"    [FAILED] Submission failed for group {group}: {submit_resp.json.get('msg')}")
            
            # Logout (Optional in test client but good practice)
            client.get('/api/logout?type=assessment')
            success_count += 1
            print(f"Finished User: {username}\n")

    print("All tasks completed.")

if __name__ == "__main__":
    main()
