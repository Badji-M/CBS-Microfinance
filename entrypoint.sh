#!/bin/bash
set -e

echo "============================================================"
echo "Starting application initialization..."
echo "============================================================"

cd /app

echo "Step 1: Applying migrations for migrated apps (auth, admin, etc)..."
python manage.py migrate

echo "Step 2: Creating tables for unmigrated apps..."
python manage.py migrate --run-syncdb

echo "Creating superuser if needed..."
python manage.py shell << EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@microfinance.local', 'admin123')
    print('Superuser admin created')
else:
    print('Superuser admin already exists')
EOF

echo "============================================================"
echo "Initialization complete! Starting gunicorn..."
echo "============================================================"

exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120 --access-logfile -
