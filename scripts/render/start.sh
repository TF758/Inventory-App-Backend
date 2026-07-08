#!/bin/sh
set -eu

DJANGO_SETTINGS="${DJANGO_SETTINGS_MODULE:-inventory.settings.staging}"

echo "Using Django settings: ${DJANGO_SETTINGS}"

echo "Collecting static files..."
python manage.py collectstatic --settings="${DJANGO_SETTINGS}" --noinput

echo "Starting Daphne..."
exec daphne -b 0.0.0.0 -p "${PORT}" inventory.asgi:application
