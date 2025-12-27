import sqlite3

def check_roles():
    conn = sqlite3.connect('evaluation.db')
    c = conn.cursor()
    roles = c.execute('SELECT DISTINCT role FROM middle_managers').fetchall()
    with open('distinct_roles.txt', 'w', encoding='utf-8') as f:
        for r in roles:
            f.write(r[0] + '\n')
    conn.close()

if __name__ == '__main__':
    check_roles()
