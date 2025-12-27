
import os

def fix_app():
    app_path = r'c:\Users\Dennis\Desktop\cadre\leader\app.py'
    part_path = r'c:\Users\Dennis\Desktop\cadre\leader\app_project9_part.py'
    
    # 1. Read app.py (UTF-8)
    with open(app_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        
    # 2. Find cut point (check_assessment_progress)
    cut_index = -1
    for i, line in enumerate(lines):
        if 'def check_assessment_progress(user_row):' in line:
            cut_index = i
            break
            
    if cut_index == -1:
        print("Could not find check_assessment_progress definition. Appending instead?")
        # If not found, maybe it's cleaner to just append? 
        # But user said it IS there (just garbled later).
        # Let's search for "Project 9" comment
        for i, line in enumerate(lines):
            if 'Project 9:' in line:
                cut_index = i
                break
    
    original_part = []
    if cut_index != -1:
        original_part = lines[:cut_index]
        print(f"Found cut point at line {cut_index}")
    else:
        original_part = lines
        print("No cut point found, keeping all lines")

    # 3. Comment out lock logic in team score
    # Look for: db.execute('UPDATE evaluation_accounts SET status = "否" WHERE username = ?', (rater_account,))
    # Inside submit_team_score (approx line 1300)
    fixed_lines = []
    for line in original_part:
        if 'UPDATE evaluation_accounts SET status = "否"' in line and 'submit_team_score' not in line: # Avoid matching the function def if any? No.
            # Check context? No, just comment it out.
            # But wait, final_submit has it too?
            # final_submit is in the NEW part (which we are appending), so it won't be in original_part (if we cut correctly).
            # If we didn't cut correctly, we might comment out the final_submit one too!
            # BUT final_submit is definitely AFTER check_assessment_progress.
            # So if we cut at check_assessment_progress, existing lock logic (team score) IS in original_part.
            if not line.strip().startswith('#'):
                fixed_lines.append('# ' + line)
                print(f"Commented out lock at: {line.strip()}")
                continue
        fixed_lines.append(line)
        
    # 4. Read new part
    with open(part_path, 'r', encoding='utf-8') as f:
        new_lines = f.readlines()
        
    # Skip headers in new part if needed?
    # app_project9_part.py starts with blank lines and comments.
    # We can just append all.
    
    # 5. Write back
    with open(app_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
        f.write('\n')
        f.writelines(new_lines)
        
    print("app.py fixed successfully.")

if __name__ == '__main__':
    fix_app()
