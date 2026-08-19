#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp -n .env.example .env || true
python manage.py migrate
python manage.py seed_demo
echo "Backend: http://127.0.0.1:8000"
exec python manage.py runserver 0.0.0.0:8000
