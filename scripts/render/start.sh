cd "D:\Documents\Inventory System\inventory"

New-Item -ItemType Directory -Force scripts/render | Out-Null

@'
#!/bin/sh
set -e

DJANGO_SETTINGS="${DJANGO_SETTINGS_MODULE:-inventory.settings.staging}"

echo "Using Django settings: $DJANGO_SETTINGS"

echo "Collecting static files..."
python manage.py collectstatic --settings="$DJANGO_SETTINGS" --noinput

echo "Starting Daphne..."
exec daphne -b 0.0.0.0 -p "$PORT" inventory.asgi:application
'@ | Set-Content -Path scripts/render/start.sh -Encoding UTF8