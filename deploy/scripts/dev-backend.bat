@echo off
cd /d %~dp0\..\backend
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt -q
if not exist .env copy .env.example .env
python manage.py migrate
python manage.py seed_demo
echo.
echo Backend: http://127.0.0.1:8000
python manage.py runserver 0.0.0.0:8000
