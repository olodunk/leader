import sqlite3
import random
import os

# Configuration
DB_PATH = 'evaluation.db'
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

def generate_scores():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database {DB_PATH} not found.")
        return

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    try:
        # 1. Clear existing team_scores
        print("Clearing existing team_scores...")
        cursor.execute("DELETE FROM team_scores")

        # 2. Find eligible departments (dept_type != '院领导')
        depts = cursor.execute("SELECT dept_code FROM department_config WHERE dept_type != '院领导'").fetchall()
        dept_codes = [d['dept_code'] for d in depts]
        print(f"Found {len(dept_codes)} eligible departments.")

        if not dept_codes:
            print("No eligible departments found.")
            return

        # 3. For each department, find accounts grouped by type
        total_generated = 0
        for dept_code in dept_codes:
            accounts = cursor.execute(
                "SELECT username, account_type FROM evaluation_accounts WHERE dept_code = ?", 
                (dept_code,)
            ).fetchall()

            # Group by account_type
            type_to_accounts = {}
            for acc in accounts:
                acc_type = acc['account_type']
                if acc_type not in type_to_accounts:
                    type_to_accounts[acc_type] = []
                type_to_accounts[acc_type].append(acc['username'])

            # Randomly select ONE account per type
            for acc_type, usernames in type_to_accounts.items():
                lucky_username = random.choice(usernames)
                
                # Generate random scores (6-10)
                scores = {}
                all_ten = True
                total_weighted_score = 0
                
                for key, weight in TEAM_SCORE_WEIGHTS.items():
                    val = random.randint(6, 10)
                    if val != 10:
                        all_ten = False
                    scores[key] = val
                    total_weighted_score += val * (weight / 10.0)

                # Fix "all ten" rule
                if all_ten:
                    key_to_fix = random.choice(list(TEAM_SCORE_WEIGHTS.keys()))
                    scores[key_to_fix] = 9
                    # Recalculate total_weighted_score
                    total_weighted_score = sum(scores[k] * (TEAM_SCORE_WEIGHTS[k] / 10.0) for k in TEAM_SCORE_WEIGHTS)

                # Prepare INSERT
                cols = list(scores.keys()) + ['rater_account', 'target_dept_code', 'total_score']
                vals = list(scores.values()) + [lucky_username, dept_code, total_weighted_score]
                
                placeholders = ', '.join(['?'] * len(vals))
                sql = f"INSERT INTO team_scores ({', '.join(cols)}) VALUES ({placeholders})"
                cursor.execute(sql, vals)
                total_generated += 1

        db.commit()
        print(f"Successfully generated {total_generated} random scores in team_scores.")

    except Exception as e:
        db.rollback()
        print(f"Error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    generate_scores()
