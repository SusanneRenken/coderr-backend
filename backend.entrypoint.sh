#!/bin/sh
set -e

echo "Waiting for database..."

until python manage.py migrate --check >/dev/null 2>&1; do
  sleep 2
done

echo "Database ready"

echo "Running migrations"
python manage.py migrate

echo "Collecting static files"
python manage.py collectstatic --noinput

echo "Starting Gunicorn"
exec gunicorn core.wsgi:application --bind 0.0.0.0:8000
