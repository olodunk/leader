import sqlite3
import hashlib

DATABASE = 'evaluation.db'

def encrypt_password(password):
    return hashlib.md5(password.encode('utf-8')).hexdigest()

def reset_admin_password():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    new_pw = encrypt_password('admin123')
    cursor.execute('UPDATE sys_users SET password = ? WHERE username = ?', (new_pw, 'admin'))
    
    if cursor.rowcount == 0:
        # User might not exist?
        cursor.execute('INSERT INTO sys_users (username, password) VALUES (?, ?)', ('admin', new_pw))
        print("Created admin user.")
    else:
        print("Updated admin password.")
        
    conn.commit()
    conn.close()
    print("重置成功！管理员密码已改为: admin123")

if __name__ == '__main__':
    reset_admin_password()
