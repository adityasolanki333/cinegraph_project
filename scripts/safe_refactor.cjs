const fs = require('fs');

function refactorFile(filepath) {
    let content = fs.readFileSync(filepath, 'utf8');
    
    if (content.includes('django.http import JsonResponse') && !content.includes('api_auth_required')) {
        content = content.replace('from django.http import JsonResponse', "from django.http import JsonResponse\nfrom .decorators import api_auth_required");
    } else if (!content.includes('api_auth_required')) {
        content = "from .decorators import api_auth_required\n" + content;
    }

    let out = [];
    let lines = content.split('\n');
    let skipLines = 0;

    for (let i = 0; i < lines.length; i++) {
        if (skipLines > 0) {
            skipLines--;
            continue;
        }

        if (lines[i].trim() === 'if not request.user.is_authenticated:') {
            if (i+1 < lines.length && lines[i+1].includes('return JsonResponse') && lines[i+1].includes('401')) {
                skipLines = 1;

                for (let j = out.length - 1; j >= 0; j--) {
                    if (out[j].trimLeft().startsWith('def ')) {
                        let hasAuth = false;
                        for (let k = j - 1; k >= Math.max(0, j - 3); k--) {
                            if (out[k].includes('@api_auth_required') || out[k].includes('mock_demo_user_auth')) {
                                hasAuth = true;
                            }
                        }
                        if (!hasAuth) {
                            let indentMatch = out[j].match(/^(\s*)/);
                            let indent = indentMatch ? indentMatch[1] : '';
                            out.splice(j, 0, indent + '@api_auth_required');
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

console.log("Refactoring complete.");
