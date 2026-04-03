@echo off
echo ==========================================
echo       CineSuggest Production Build
echo ==========================================

if exist requirements.txt (
    echo [1/5] Installing Python Dependencies...
    call .venv\Scripts\pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Python dependencies installation failed.
        exit /b %errorlevel%
    )
) else (
    echo [1/5] requirements.txt not found, skipping Python dependencies installation.
    echo       Ensure dependencies are installed in .venv.
)

echo [2/5] Installing Frontend Dependencies...
call npm install
if %errorlevel% neq 0 (
    echo [ERROR] Frontend dependencies installation failed.
    exit /b %errorlevel%
)

echo [3/5] Building Frontend...
call npm run build
if %errorlevel% neq 0 (
    echo [ERROR] Frontend build failed.
    exit /b %errorlevel%
)

echo [4/5] Collecting Static Files...
call .venv\Scripts\python manage.py collectstatic --noinput
if %errorlevel% neq 0 (
    echo [ERROR] Collectstatic failed.
    exit /b %errorlevel%
)

echo [5/5] Running Migrations...
call .venv\Scripts\python manage.py migrate
if %errorlevel% neq 0 (
    echo [ERROR] Migrations failed.
    exit /b %errorlevel%
)

echo ==========================================
echo        Build Complete Successfully!
echo ==========================================
