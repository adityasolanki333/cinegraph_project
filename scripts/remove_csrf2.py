import os
import re

d = 'movies'
count = 0
for f in os.listdir(d):
    if f.endswith('.py') and ('_api' in f or f == 'auth.py'):
        p = os.path.join(d, f)
        with open(p, 'r', encoding='utf-8') as file:
            content = file.read()
            
        o_len = len(content)
        content = re.sub(r'^\s*@csrf_exempt\s*[\r\n]+', '', content, flags=re.MULTILINE)
        
        if len(content) != o_len:
            with open(p, 'w', encoding='utf-8') as file:
                file.write(content)
            print(f'Removed @csrf_exempt from {f}')
            count += 1

print(f'Done. Updated {count} files.')
