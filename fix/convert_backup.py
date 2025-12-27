
import codecs

def convert():
    src = r'c:\Users\Dennis\Desktop\cadre\leader\app_backup.py'
    dst = r'c:\Users\Dennis\Desktop\cadre\leader\app_backup_utf8.py'
    
    try:
        # Try finding the bom or just read as utf-16
        with open(src, 'rb') as f:
            content = f.read()
        
        # Heuristic: try utf-16-le
        try:
            text = content.decode('utf-16-le')
        except:
            # Maybe it's active mix?
            text = content.decode('utf-8', errors='ignore')

        with open(dst, 'w', encoding='utf-8') as f:
            f.write(text)
            
        print("Converted successfully")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    convert()
