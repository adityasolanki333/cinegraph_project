@echo off
echo ==========================================
echo       CineSuggest Production Server
echo ==========================================

REM Set Environment Variables
set DEBUG=False
set DJANGO_SETTINGS_MODULE=movieflix.settings

echo starting server...
echo Note: For true production, consider using 'waitress-serve' or 'gunicorn'.
echo Currently running with Django development server in non-debug mode.

call .venv\Scripts\python manage.py runserver 0.0.0.0:8000 --insecure
