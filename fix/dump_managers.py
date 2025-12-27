import sqlite3
import sys

def dump_managers():
    try:
        conn = sqlite3.connect('evaluation.db')
        c = conn.cursor()
        rows = c.execute("SELECT name, role, dept_code FROM middle_managers").fetchall()
        
        with open('managers_dump.txt', 'w', encoding='utf-8') as f:
            for r in rows:
                f.write(f"Name: {r[0]}, Role: {r[1]}, Dept: {r[2]}\n")
                
        print("Dumped to managers_dump.txt")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    dump_managers()
