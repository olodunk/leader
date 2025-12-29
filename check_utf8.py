with open('app.py', 'rb') as f:
    for i, line in enumerate(f):
        try:
            line.decode('utf-8')
        except UnicodeDecodeError:
            print(f"Line {i+1} in app.py has invalid UTF-8: {line}")
