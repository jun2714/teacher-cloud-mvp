#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
(
  cd backend
  python manage.py makemigrations core learning community
  python manage.py migrate
  python manage.py seed_demo
  python manage.py runserver
) &
(
  cd frontend
  npm install
  npm run dev
)
