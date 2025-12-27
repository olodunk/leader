
import re

def fix():
    path = r'c:\Users\Dennis\Desktop\cadre\leader\app.py'
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Map of Mojibake -> Correct
    # Note: Regex to handle potential trailing chars
    
    replacements = [
        ('鏈櫥褰?', "未登录'"), 
        ('鏈櫥褰', "未登录"),
        ('鎻愪氦鎴愬姛', "提交成功"),
        ('淇濆瓨鎴愬姛', "保存成功"),
        ('鏃犳晥璐﹀彿', "无效账号"),
        ('鏃犳潈鎿嶄綔', "无权操作"),
        ('鏃犳潈璁块棶', "无权访问"),
        ('鎻愪氦澶辫触', "提交失败"),
        ('璇峰畬鎴愬墠涓夐」蹇呭～璇勪环', "请完成前三项必填评价"),
        ('骞查儴閫夋嫈浠荤敤宸ヤ綔姘戜富璇勮琛?', '干部选拔任用工作民主评议表"') , 
        # Above: The original starts with f" so we end with "
        # Note: '骞查儴...? ' -> The ? is likely the closing quote.
        
        ('鏂版彁鎷斾换鐢ㄥ共閮ㄦ皯涓昏瘎璁〃', '新提拔任用干部民主评议表'),
        ('鎺ㄨ崘浜烘暟瓒呰繃闄愬埗', "推荐人数超过限制"),
        ('鎺ㄨ崘鍚嶉', "推荐名额"),
        ('璐甸儴闂ㄦ棤姝ら」', "贵部门无此项"),
        ('鏁版嵁鏍煎紡閿欒', "数据格式错误"),
        ('鏃犳枃浠?', "无文件'"),
        ('瀵煎叆澶辫触', "导入失败"),
        ('瀵煎叆鎴愬姛', "导入成功"),
        ('鏃犳暟鎹?', "无数据'"),
        
        
        # Mapping Keys
        ('鐜拌亴绾ф椂闂?:', "现职级时间':"),  # Removed leading '
        ('鏄惁鏂版彁鎷斿共閮?:', "是否新提拔干部':"), # Removed leading '
        ('鍛樺伐瑙掕壊', '员工角色'),
        ('宀椾綅灞傜骇', '岗位层级'),
        ('浠昏亴鏃堕棿', '任职时间'),
        ('鏂囧寲绋嬪害', '文化程度'),
        ('鍘熶换鑱屽姟', '原任职务'),
        ('鎻愭嫈鏂瑰紡', '提拔方式'),
        ('閮ㄩ棬鍐呮帓搴忓彿', '部门内排序号'),
        ('濮撳悕', '姓名'),
        ('鎬у埆', '性别'),
        ('鍑虹敓骞存湀', '出生年月'),
        ('鐜颁换鑱屽姟', '现任职务'),
        ('閮ㄩ棬鍚嶇О', '部门名称'),
        ('閮ㄩ棬浠ｇ爜', '部门代码'),
        
        
        
        # Docstrings -> Comments (Targeting English strings now)
        ('"""Assessment Overview Page"""', '# Assessment Overview Page'),
        ('"""Final Submit API"""', '# Final Submit API'),
        ('"""Democratic Assessment (Grouped)"""', '# Democratic Assessment (Grouped)'),
        ('"""Recommend Principal Page"""', '# Recommend Principal Page'),
        ('"""Recommend Deputy Page"""', '# Recommend Deputy Page'),
        ('"""Selection Appointment Page"""', '# Selection Appointment Page'),
        ('"""New Promotion Page"""', '# New Promotion Page'),
        ('"""Center Grassroots Management Page"""', '# Center Grassroots Management Page'),
        
        # Catch specific leftover mojibake docstrings (exact matches from view_file)
        ('"""涓績鍩哄眰棰嗗绠＄悊椤?""', '# Center Grassroots Management Page'),
        ('"""浼樼骞查儴姘戜富鎺ㄨ崘-姝ｈ亴 椤甸潰"""', '# Recommend Principal Page'),
        ('"""浼樼骞查儴姘戜富鎺ㄨ崘-鍓亴 椤甸潰"""', '# Recommend Deputy Page'),
        ('"""干部选拔任用工作民主评议表"椤甸潰"""', '# Selection Appointment Page'),
        ('"""新提拔任用干部民主评议表 椤甸潰"""', '# New Promotion Page'),

    ]
    
    for bad, good in replacements:
        content = content.replace(bad, good)
        
    # Extra safety: Check for '?})' which implies missing quote and fix
    content = content.replace("?})", "'})")
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Fixed mojibake.")

if __name__ == '__main__':
    fix()
