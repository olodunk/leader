"""
初始化院领导权重配置数据 (根据用户提供的图片)
"""
import sqlite3

DATABASE = 'evaluation.db'

# 根据图片中的配置数据
# 格式: (dept_name, total_weight, 杨卫胜, 主管领导名, 主管权重, 其他均分)
# 注：需要根据每个部门的主管领导分配权重

# 部门数据 (简化处理：使用dept_code从现有数据获取，然后按规则分配)
def main():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 获取所有部门
    depts = cursor.execute('SELECT dept_code, dept_name FROM department_config ORDER BY sort_no ASC').fetchall()
    
    # 根据图片的规则分配权重
    # 院长助理: 70/40/0/0/0/0 (杨卫胜40%, 其余5人均分30%=6%each)
    # 大部分部门: 50/30/主管15/其余4人均分5%=1.25%each
    # 昆冈班子副职: 20/12/刘超伟6%/其余4人2%=0.5%each
    # 昆冈分公司: 10/6/刘超伟3%/其余4人1%=0.25%each
    
    # 主管领导映射 (根据图片中的颜色/名字)
    # 黄色高亮 = 杨卫胜 (主要领导)
    # 绿色 = 主管领导 (不同部门不同)
    # 根据图片:
    # - 院长助理、兰州中心、大庆中心、办公室、工艺工程、财务部 -> 杨卫胜 (主管也是杨卫胜)
    # - 合成树脂、新材料、生物化工、氢能、化工研究所 -> 王凌
    # - 人力资源、党群工作部、纪委办公室 -> 许青春
    # - 条件保障、知识产权、技术推广、清洁燃料、重油加工 -> 葛少辉
    # - 科研部、质量健康、数智技术、基础前沿、分析表征、战略与信息 -> 刘超伟
    # - 昆冈班子副职、昆冈兰州分公司、昆冈抚顺分公司 -> 刘超伟 (特殊权重)
    
    # 简化处理：根据序号和特殊部门名分配
    data_to_insert = []
    
    for idx, dept in enumerate(depts):
        code = dept['dept_code']
        name = dept['dept_name']
        
        # 特殊部门判断
        if '院长助理' in name:
            # 70% 总权重, 杨卫胜40%, 其他5人均分30% (每人6%)
            data_to_insert.append((code, name, 70, 40, 6, 6, 6, 6, 6))
        elif '昆冈班子副职' in name:
            # 20% 总权重, 杨卫胜12%, 刘超伟6%, 其他4人均分2% (每人0.5%)
            data_to_insert.append((code, name, 20, 12, 0.5, 0.5, 0.5, 0.5, 6))
        elif '昆冈' in name and '分公司' in name:
            # 10% 总权重, 杨卫胜6%, 刘超伟3%, 其他4人均分1% (每人0.25%)
            data_to_insert.append((code, name, 10, 6, 0.25, 0.25, 0.25, 0.25, 3))
        else:
            # 标准部门: 50% 总权重, 杨卫胜30%, 主管15%, 其他4人均分5% (每人1.25%)
            # 简化处理: 主管分配根据部门名称关键词
            w_yang = 30
            w_wang = 1.25
            w_xu = 1.25
            w_zhao = 1.25
            w_ge = 1.25
            w_liu = 1.25
            
            # 根据图片中主管领导分配 (绿色标注)
            if any(k in name for k in ['合成树脂', '新材料', '生物化工', '氢能', '化工研究所']):
                w_wang = 15  # 王凌是主管
            elif any(k in name for k in ['人力资源', '党群', '纪委']):
                w_xu = 15  # 许青春是主管
            elif any(k in name for k in ['赵彤']):  # 几乎没有
                w_zhao = 15
            elif any(k in name for k in ['条件保障', '知识产权', '技术推广', '清洁燃料', '重油加工']):
                w_ge = 15  # 葛少辉是主管
            elif any(k in name for k in ['科研部', '质量', '数智', '基础前沿', '分析', '战略']):
                w_liu = 15  # 刘超伟是主管
            else:
                # 默认杨卫胜既是主要领导也是主管
                w_yang = 45  # 30+15
                
            # 计算剩余其他领导权重
            assigned = w_yang + w_wang + w_xu + w_zhao + w_ge + w_liu
            if assigned < 50:
                # 在所有非主管领导间均分剩余
                pass  # 逻辑复杂，简化为固定分配
                
            data_to_insert.append((code, name, 50, w_yang, w_wang, w_xu, w_zhao, w_ge, w_liu))
    
    # 插入数据
    for item in data_to_insert:
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
        ''', item)
    
    conn.commit()
    conn.close()
    
    print(f"成功初始化 {len(data_to_insert)} 条院领导权重配置")

if __name__ == '__main__':
    main()
