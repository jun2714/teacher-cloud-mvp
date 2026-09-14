@echo off
setlocal
cd /d %~dp0

if not exist backend\.venv (
  python -m venv backend\.venv
)
call backend\.venv\Scripts\activate
pip install -r backend\requirements.txt
cd backend
python manage.py makemigrations core learning community
python manage.py migrate
python manage.py seed_demo
start "教研云后端" cmd /k "call .venv\Scripts\activate 2>nul & python manage.py runserver"
cd ..\frontend
if not exist node_modules npm install
start "教研云前端" cmd /k "npm run dev"
echo.
echo 已启动：后端 http://127.0.0.1:8000  前端 http://127.0.0.1:6060
endlocal
