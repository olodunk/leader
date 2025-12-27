
import os

def fix_lines():
    path = r'c:\Users\Dennis\Desktop\cadre\leader\app.py'
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        
    new_lines = []
    for line in lines:
        s = line.strip()
        
        # Center Grassroots Mapping Fixes
        if "'rank_time'," in s:
            line = "    '现职级时间': 'rank_time',\n"
        elif "'is_newly_promoted'" in s:
            line = "    '是否新提拔干部': 'is_newly_promoted'\n"
        elif "'sort_no'" in s and "部门内排序号" not in s: # Check context? 
            # sorting can differ? Project 8 uses '部门内排序号'.
            if "CENTER_GRASSROOTS_MAPPING" in "".join(lines[max(0, lines.index(line)-20):lines.index(line)]):
                 # Weak context check but likely OK if unique
                 pass
            # Let's just be specific. 'rank_time' is unique to that mapping?
            # 'sort_no' is common. Be careful.
            # 'rank_time' is definitely specific.
        
        # Mapping fixes based on values
        if "    '閮..." in line or "    '..." in line: # Detect garbage line?
             pass 
             
        # Hardcode replacements for specific values
        if "'rank_level'," in s: line = "    '岗位层级': 'rank_level',\n"
        if "'tenure_time'," in s: line = "    '任职时间': 'tenure_time',\n"
        if "'education'," in s: line = "    '文化程度': 'education',\n"
        if "'original_position'," in s: line = "    '原任职务': 'original_position',\n"
        if "'promotion_method'," in s: line = "    '提拔方式': 'promotion_method',\n"
        
        # Fix f-string quote mismatch
        if 'page_title=f"{dept_name}' in s and '干部选拔任用工作民主评议表' in s:
             if not s.endswith('",'):
                 line = '                           page_title=f"{dept_name}干部选拔任用工作民主评议表",\n'
                 
        if 'page_title=f"{dept_name}' in s and '新提拔任用干部民主评议表' in s:
             if not s.endswith('",'):
                 line = '                           page_title=f"{dept_name}新提拔任用干部民主评议表",\n'
                 
        # Fix upload loop
        if "for col in [" in s and ("''" in s or "时" in s or "for col in ['" in s):
             # Identify by context or weak content match if simpler fails
             if "pd.to_datetime" in "".join(lines[min(len(lines)-1, lines.index(line)+1):lines.index(line)+2]): 
                 # Look ahead next line? fix_lines reads all lines first.
                 # We can check next line in the loop if we use index.
                 # But sticking to simple unique match within reason.
                 # The line likely contains 3 items.
                 # Or just match the Mojibake garbage from error message ''
                 pass
                 
        if "for col in [" in s and ('' in s or '时' in s) and "datetime" not in s:
             # Indent: 8 spaces (likely)
             line = "        for col in ['出生年月', '现职级时间', '任职时间']:\n"

        # Fix add_proj quote mismatch
        if "add_proj('selection'," in s and '干部选拔任用工作民主评议表' in s:
             # Force clean line
             line = "        add_proj('selection', '干部选拔任用工作民主评议表', 'assessment_selection_appointment', bool(row))\n"

        new_lines.append(line)
        
    # Manual catch for tricky ones that might have matched above but need strict indentation
    # ...
    
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("Fixed lines.")

if __name__ == '__main__':
    fix_lines()
