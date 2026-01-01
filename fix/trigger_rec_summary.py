
import sqlite3

def trigger_rec_summary():
    conn = sqlite3.connect('evaluation.db')
    cursor = conn.cursor()
    
    # We call the logic for handle_rec_summary_request('principal', 'calculate') 
    # and handle_rec_summary_request('deputy', 'calculate')
    # Since I cannot easily import app.py due to flask dependencies, I will extract the logic.
    
    group_map = {
        '正职': ('A(正职)', 1),
        '副职': ('B(副职)', 2),
        '中心基层领导': ('C(中心基层领导)', 3),
        '其他': ('D(员工)', 4),
        '员工': ('D(员工)', 4),
        '其他员工': ('D(员工)', 4),
        '院领导': ('L(院领导)', 5)
    }
    special_subsidiary_codes = ['U', 'V', 'W', 'X', 'Y']
    
    # Fetch Dept Config Map
    cursor.execute("SELECT dept_code, dept_name FROM department_config")
    dept_name_map = {r[0]: r[1] for r in cursor.fetchall()}

    for rec_type in ['principal', 'deputy']:
        table_name = f'recommendation_summary_{rec_type}'
        score_table = f'recommendation_scores_{rec_type}'
        cand_table = f'recommend_{rec_type}'
        
        cursor.execute(f"DELETE FROM {table_name}")
        
        # Fetch Candidates
        cursor.execute(f"SELECT * FROM {cand_table} ORDER BY dept_code ASC, sort_no ASC")
        candidates = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
        
        dept_codes = sorted(list(set([c['dept_code'] for c in candidates])))
        
        for dcode in dept_codes:
            dept_candidates = [c for c in candidates if c['dept_code'] == dcode]
            if not dept_candidates: continue
            
            display_dept_name = dept_candidates[0]['dept_name']
            if dcode in special_subsidiary_codes and dcode in dept_name_map:
                display_dept_name = dept_name_map[dcode]
                
            # Voters
            cursor.execute(f"SELECT DISTINCT s.rater_account, a.account_type FROM {score_table} s LEFT JOIN evaluation_accounts a ON s.rater_account = a.username WHERE s.target_dept_code = ?", (dcode,))
            voters = cursor.fetchall()
            
            group_voter_counts = {}
            for v_acc, atype in voters:
                if atype in group_map:
                    gname, gsort = group_map[atype]
                    if gname not in group_voter_counts:
                        group_voter_counts[gname] = {'sort': gsort, 'count': 0}
                    group_voter_counts[gname]['count'] += 1
            
            active_group_names = sorted(group_voter_counts.keys(), key=lambda n: group_voter_counts[n]['sort'])
            
            for cand in dept_candidates:
                cid = cand['id']
                cursor.execute(f"SELECT a.account_type, COUNT(*) as cnt FROM {score_table} s LEFT JOIN evaluation_accounts a ON s.rater_account = a.username WHERE s.target_dept_code = ? AND s.examinee_id = ? AND s.is_recommended = 1 GROUP BY a.account_type", (dcode, cid))
                rec_counts_rows = cursor.fetchall()
                
                group_rec_counts = {gn: 0 for gn in active_group_names}
                for atype, count in rec_counts_rows:
                    if atype in group_map:
                        gname, _ = group_map[atype]
                        if gname in group_rec_counts:
                            group_rec_counts[gname] += count
                
                # Insert Group Rows
                for gname in active_group_names:
                    gsort = group_voter_counts[gname]['sort']
                    denom = group_voter_counts[gname]['count']
                    num = group_rec_counts[gname]
                    rate_str = f"{(num / denom * 100):.3f}%"
                    
                    cursor.execute(f"INSERT INTO {table_name} (sort_no, group_name, group_sort, valid_votes, rec_count, rec_rate, name, gender, current_position, rank_level, education, birth_date, rank_time, dept_name, dept_code) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (cand['sort_no'], gname, gsort, denom, num, rate_str, cand['name'], cand['gender'], cand['current_position'], cand['rank_level'], cand['education'], cand['birth_date'], cand['rank_time'], display_dept_name, cand['dept_code']))
                
                # Total
                total_valid_votes = len(voters)
                total_num = sum(group_rec_counts.values())
                total_rate_str = f"{(total_num / total_valid_votes * 100 if total_valid_votes > 0 else 0):.3f}%"
                cursor.execute(f"INSERT INTO {table_name} (sort_no, group_name, group_sort, valid_votes, rec_count, rec_rate, name, gender, current_position, rank_level, education, birth_date, rank_time, dept_name, dept_code) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (cand['sort_no'], '合计', 99, total_valid_votes, total_num, total_rate_str, cand['name'], cand['gender'], cand['current_position'], cand['rank_level'], cand['education'], cand['birth_date'], cand['rank_time'], display_dept_name, cand['dept_code']))

    conn.commit()
    conn.close()
    print("Recommendation summaries recalculated.")

if __name__ == '__main__':
    trigger_rec_summary()
