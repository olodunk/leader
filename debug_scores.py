from app import get_db, app

with app.app_context():
    db = get_db()
    
    # Check team score summary for 纪委
    rows = db.execute('''
        SELECT ts.*
        FROM team_score_summary ts
        WHERE ts.dept_name LIKE '%纪委%'
    ''').fetchall()
    
    print("=== Team Score Summary (纪委) ===")
    for r in rows:
        d = dict(r)
        print(f"Dept: {d.get('dept_name')}")
        print(f"  score_func_abc_weighted: {d.get('score_func_abc_weighted')}")
        print(f"  total_score: {d.get('total_score')}")
    
    # Compare with examinee
    rows2 = db.execute('''
        SELECT e.name, e.total_score
        FROM examinee_score_summary e
        WHERE e.dept_name LIKE '%纪委%'
    ''').fetchall()
    
    print("\n=== Examinee Summary (纪委) ===")
    for r in rows2:
        print(dict(r))
