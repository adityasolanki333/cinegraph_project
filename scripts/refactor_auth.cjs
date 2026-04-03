const fs = require('fs');

function refactorFile(filepath) {
    console.log(`Processing ${filepath}`);
    let data = fs.readFileSync(filepath, 'utf8');
    let lines = data.split('\n');
    let out = [];
    
    // Default to handling \r\n properly if needed
    lines = lines.map(l => l.replace(/\r$/, ''));
    
    let hasImport = lines.some(line => line.includes('api_auth_required'));
    if (!hasImport) {
        for (let i = 0; i < lines.length; i++) {
            if (lines[i].startsWith('from .decorators import') && !lines[i].includes('api_auth_required')) {
                lines[i] = lines[i].replace('from .decorators import ', 'from .decorators import api_auth_required, ');
                hasImport = true;
                break;
            }
        }
        if (!hasImport) {
            for (let i = 0; i < lines.length; i++) {
                if (lines[i].startsWith('from .models') || lines[i].includes('from .decorators')) {
                    lines.splice(i, 0, 'from .decorators import api_auth_required');
                    hasImport = true;
                    break;
                }
            }
        }
    }
    
    let skipNext = false;
    for (let i = 0; i < lines.length; i++) {
        if (skipNext) {
            skipNext = false;
            continue;
        }
        
        if (lines[i].trim() === 'if not request.user.is_authenticated:') {
            if (i + 1 < lines.length && lines[i+1].includes('return JsonResponse') && lines[i+1].includes('401')) {
                skipNext = true;
                
                // Add explicit spacing check and insertion
                for (let j = out.length - 1; j >= 0; j--) {
                    if (out[j].trimLeft().startsWith('def ')) {
                        // check upward if already has @api_auth_required
                        let hasAuth = false;
                        if (j > 0 && out[j-1].includes('@api_auth_required')) hasAuth = true;
                        if (j > 1 && out[j-2].includes('@api_auth_required')) hasAuth = true;
                        if (j > 2 && out[j-3].includes('@api_auth_required')) hasAuth = true;
                        
                        if (!hasAuth) {
                            let spaces = out[j].length - out[j].trimLeft().length;
                            out.splice(j, 0, ' '.repeat(spaces) + '@api_auth_required');
                        }
                        break;
                    }
                }
                continue;
            }
        }
        out.push(lines[i]);
    }
    
    fs.writeFileSync(filepath, out.join('\n'));
}

['movies/social_api.py', 'movies/users_api.py', 'movies/clubs_api.py', 'movies/api.py', 'movies/ml_api.py'].forEach(f => {
    if (fs.existsSync(f)) refactorFile(f);
});

console.log("Done refactoring auth");
