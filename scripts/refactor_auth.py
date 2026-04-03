import sys

def refactor_file(filepath):
    print(f"Processing {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    out = []
    
    # Check if api_auth_required is imported
    has_import = any('api_auth_required' in line for line in lines)
    if not has_import:
        for i, line in enumerate(lines):
            if line.startswith('from .decorators import') and 'api_auth_required' not in line:
                lines[i] = line.replace('from .decorators import ', 'from .decorators import api_auth_required, ')
                has_import = True
                break
        
        # If it still doesn't have the import, we'll insert it at the top after django imports
        if not has_import:
            for i, line in enumerate(lines):
                if line.startswith('from .models') or 'from .decorators' in line:
                    lines.insert(i, 'from .decorators import api_auth_required\n')
                    break
    
    skip_next = False
    
    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue
            
        if line.strip() == 'if not request.user.is_authenticated:':
            if i + 1 < len(lines) and 'return JsonResponse' in lines[i+1] and '401' in lines[i+1]:
                skip_next = True
                # Search backwards for the function definition and insert decorator
                for j in range(len(out)-1, -1, -1):
                    if out[j].lstrip().startswith('def '):
                        # check if previous lines already have the decorator
                        has_auth = False
                        if j > 0 and '@api_auth_required' in out[j-1]:
                            has_auth = True
                        if j > 1 and '@api_auth_required' in out[j-2]:
                            has_auth = True
                        if j > 2 and '@api_auth_required' in out[j-3]:    
                            has_auth = True
                        
                        if not has_auth:
                            indent = ' ' * (len(out[j]) - len(out[j].lstrip()))
                            out.insert(j, indent + '@api_auth_required\n')
                        break
                continue
                
        out.append(line)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(out)
        
files = ['movies/social_api.py', 'movies/users_api.py', 'movies/clubs_api.py']
for filepath in files:
    try:
        refactor_file(filepath)
    except Exception as e:
        print(f"Error on {filepath}: {e}")

print("Done safely")
