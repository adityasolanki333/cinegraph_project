from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.http import HttpResponse
from django.views.static import serve
import os

def serve_react_app(request):
    """Serve React SPA index.html for production"""
    index_path = settings.FRONTEND_BUILD_DIR / 'index.html'
    if index_path.exists():
        with open(index_path, 'r', encoding='utf-8') as f:
            return HttpResponse(f.read(), content_type='text/html; charset=utf-8')  # type: ignore[arg-type]
    return HttpResponse('App not built. Run npm run build first.', status=404, content_type='text/plain; charset=utf-8')  # type: ignore[arg-type]

def serve_static_file(request, path):
    """Serve static files from React build directory"""
    file_path = settings.FRONTEND_BUILD_DIR / path
    if file_path.exists() and file_path.is_file():
        return serve(request, path, document_root=settings.FRONTEND_BUILD_DIR)
    return serve_react_app(request)

urlpatterns = [
    path('', lambda r: HttpResponse('CineGraph Backend is running', content_type='text/plain')),
    path('admin/', admin.site.urls),
    path('api/', include('movies.api_urls')),
]

# In production, serve React build files
if not settings.DEBUG or os.environ.get('SERVE_STATIC'):
    urlpatterns += [
        re_path(r'^assets/(?P<path>.*)$', serve_static_file),
        re_path(r'^(?!api/)(?P<path>.*)$', serve_static_file),
    ]
