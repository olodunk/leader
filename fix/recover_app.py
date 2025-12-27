
import os

def recover():
    # Read as binary to avoid decoding errors
    with open('app.py', 'rb') as f:
        data = f.read()

    marker = b'#\x00 \x00=\x00'
    idx = data.find(marker)
    
    if idx == -1:
        # Fallback: End Marker Strategy
        end_marker = b"port=5000)"
        end_idx = data.find(end_marker)
        
        if end_idx != -1:
            part1_end = end_idx + len(end_marker)
            while part1_end < len(data) and data[part1_end] in b'\r\n \t':
                part1_end += 1
            
            part1 = data[:part1_end]
            text1 = part1.decode('utf-8', errors='replace')
            
            rest = data[part1_end:]
            m2_idx = rest.find(marker)
            if m2_idx != -1:
                 part2 = rest[m2_idx:]
                 text2 = part2.decode('utf-16-le', errors='ignore')
            else:
                 try:
                     text2 = rest.decode('utf-8')
                 except:
                     text2 = rest.decode('utf-16-le', errors='ignore')
                     
            with open('app_recovered.py', 'w', encoding='utf-8') as f:
                f.write(text1)
                f.write('\n\n')
                f.write(text2)
            print("Recovered content written to app_recovered.py (End Marker Strategy)")
            return
        else:
            print("CRITICAL: Original end marker not found.")
            return

    # If marker found (idx != -1)
    print(f"Marker found at index {idx}. Splitting logic...")
    
    # Text before marker should be UTF-8. 
    cutoff = idx
    # Move cutoff backwards if needed? No, let's assume marker is clean start of new block.
    # But wait, the marker is inside the appended block.
    # We want to find the split point between UTF-8 and UTF-16LE.
    # The UTF-16LE block starts with BOM or just bytes.
    # If we found the marker, it means the marker is UTF-16LE encoded.
    
    # Try end marker anyway, it is safer to find the end of the original file.
    end_marker = b"port=5000)"
    end_idx = data.find(end_marker)
    
    if end_idx != -1:
        part1_end = end_idx + len(end_marker)
        while part1_end < len(data) and data[part1_end] in b'\r\n \t':
            part1_end += 1
        
        part1 = data[:part1_end]
        text1 = part1.decode('utf-8', errors='replace')
        
        rest = data[part1_end:]
        # Find marker in rest
        m2_idx = rest.find(marker)
        if m2_idx != -1:
             part2 = rest[m2_idx:]
             text2 = part2.decode('utf-16-le', errors='ignore')
        else:
             # Should be caught by top if idx!=-1.
             text2 = rest.decode('utf-16-le', errors='ignore')
             
        with open('app_recovered.py', 'w', encoding='utf-8') as f:
            f.write(text1)
            f.write('\n\n')
            f.write(text2)
        print("Recovered content written to app_recovered.py")
        return

if __name__ == '__main__':
    recover()