
import sqlite3

TEAM_SCORE_WEIGHTS = {
    's_political_resp': 10,
    's_social_resp': 5,
    's_manage_benefit': 10,
    's_manage_effic': 10,
    's_risk_control': 10,
    's_tech_innov': 10,
    's_deep_reform': 10,
    's_talent_strength': 10,
    's_party_build': 7.5,
    's_party_conduct': 7.5,
    's_unity': 5,
    's_mass_ties': 5
}

def fix_team_scores():
    conn = sqlite3.connect('evaluation.db')
    conn.row_factory = sqlite3.Row
    db = conn
    
    print("Fetching all team_scores...")
    all_rows = db.execute("SELECT * FROM team_scores ORDER BY id ASC").fetchall()
    
    # Group by rater+dept
    groups = {}
    for r in all_rows:
        key = (r['rater_account'], r['target_dept_code'])
        if key not in groups: groups[key] = []
        groups[key].append(dict(r))
        
    print(f"Total entries: {len(all_rows)}")
    print(f"Unique keys: {len(groups)}")
    
    cursor = db.cursor()
    
    updates = 0
    deletes = 0
    
    for key, rows in groups.items():
        # Keep the one with the latest creation time or max ID
        # Since we sorted by ID ASC, the last one is the latest
        keeper = rows[-1]
        
        # Delete others
        if len(rows) > 1:
            ids_to_delete = [r['id'] for r in rows[:-1]]
            for did in ids_to_delete:
                cursor.execute("DELETE FROM team_scores WHERE id=?", (did,))
                deletes += 1
                
        # Recalculate Score for Keeper
        new_total = 0.0
        details = []
        for k, weight in TEAM_SCORE_WEIGHTS.items():
            raw_val = keeper.get(k, 0.0)
            if raw_val is None: raw_val = 0.0
            weighted_val = float(raw_val) * (weight / 10.0)
            new_total += weighted_val
            # details.append(f"{k}({raw_val})*{weight/10}={weighted_val:.2f}")
            
        # Update Keeper
        cursor.execute("UPDATE team_scores SET total_score=? WHERE id=?", (new_total, keeper['id']))
        updates += 1
        
    db.commit()
    print(f"Done. Deleted {deletes} duplicates. Updated {updates} rows.")
    conn.close()

if __name__ == '__main__':
    fix_team_scores()
