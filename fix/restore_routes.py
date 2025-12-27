
import os

def restore():
    backup_path = r'c:\Users\Dennis\Desktop\cadre\leader\app_backup_utf8.py'
    app_path = r'c:\Users\Dennis\Desktop\cadre\leader\app.py'
    
    # 1. Get missing chunk from backup
    with open(backup_path, 'r', encoding='utf-8') as f:
        backup_lines = f.readlines()
        
    start_idx = -1
    for i, line in enumerate(backup_lines):
        if "@app.route('/assessment/recommend-principal')" in line:
            # Go back to capture header if possible (approx 5 lines)
            # Check safely
            if i > 5 and '====' in backup_lines[i-4]:
                start_idx = i - 4
            else:
                start_idx = i
            break
            
    if start_idx == -1:
        print("Could not find start of missing chunk (route) in backup.")
        return

    # Assuming we take everything from there to end?
    # Yes, backup ends with Project 8.
    missing_chunk = backup_lines[start_idx:]
    print(f"Extracted {len(missing_chunk)} lines from backup.")
    
    # 2. Read app.py
    with open(app_path, 'r', encoding='utf-8') as f:
        app_lines = f.readlines()
        
    # 3. Find insertion point: "if __name__ == '__main__':"
    # This block is currently essentially garbage in the middle.
    insert_idx = -1
    for i, line in enumerate(app_lines):
        if "if __name__ == '__main__':" in line:
            insert_idx = i
            break
            
    if insert_idx == -1:
        print("Could not find insertion point (if __name__) in app.py")
        return
        
    print(f"Insertion point found at line {insert_idx}")
    
    # 4. Construct new content
    # content = [lines before insert] + [missing chunk] + [lines after app.run block]
    # The current app.run block is approx 3-4 lines?
    # 3967: if __name__ == '__main__':
    # 3968: 
    # 3969:     app.run(debug=True, host='0.0.0.0', port=5000)
    
    # Let's find where Project 9 starts (header) to skip the old main block clearly
    p9_idx = -1
    for i in range(insert_idx, len(app_lines)):
        if "17. Project 9:" in app_lines[i] or "check_assessment_progress" in app_lines[i]:
            p9_idx = i
            break
            
    # Or just look for the first real code after main?
    # Let's assume we remove from `insert_idx` up to `p9_idx` (exclusive).
    # If p9_idx is elusive, we can just replace lines insert_idx to insert_idx+4?
    
    pre_content = app_lines[:insert_idx]
    
    if p9_idx != -1:
        post_content = app_lines[p9_idx:]
    else:
        # If we can't find P9 start, just blindly assume it starts after the main block (e.g. +5 lines)
        post_content = app_lines[insert_idx+5:] 
        
    # 5. Append correct main block at the VERY end
    main_block = [
        "\n",
        "if __name__ == '__main__':\n",
        "    app.run(debug=True, host='0.0.0.0', port=5000)\n"
    ]
    
    final_lines = pre_content + ["\n"] + missing_chunk + ["\n"] + post_content + main_block
    
    # 6. Write back
    with open(app_path, 'w', encoding='utf-8') as f:
        f.writelines(final_lines)
        
    print("app.py restored successfully.")

if __name__ == '__main__':
    restore()
