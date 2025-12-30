import os

def fix_encoding(filename):
    encodings = ['utf-8', 'gb18030', 'gbk', 'latin1']
    content = None
    for enc in encodings:
        try:
            with open(filename, 'rb') as f:
                data = f.read()
                content = data.decode(enc)
                print(f"Read {filename} with {enc}")
                break
        except Exception:
            continue
    
    if content:
        with open(filename, 'w', encoding='utf-8', newline='') as f:
            f.write(content)
        print(f"Saved {filename} as UTF-8")
    else:
        print(f"Failed to decode {filename}")

if __name__ == "__main__":
    fix_encoding('app.py')
