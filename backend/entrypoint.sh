#!/bin/sh
set -e

mkdir -p /app/data /app/media /app/cache /app/staticfiles
python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "${SEED_DEMO}" = "1" ]; then
  python manage.py seed_demo
fi

exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-300}" \
  --access-logfile - \
  --error-logfile -
