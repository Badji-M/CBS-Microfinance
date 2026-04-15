#!/bin/bash
set -e

echo "============================================================"
echo "Starting application initialization..."
echo "============================================================"

cd /app

echo "Step 1: Checking database connection..."
python -c "import os; print(f'DATABASE_URL: {os.getenv(\"DATABASE_URL\", \"NOT SET\")[:50]}...')" || true

echo "Step 2: Applying migrations for migrated apps (auth, admin, etc)..."
python manage.py migrate 2>&1 || echo "⚠️  Migration failed, continuing..."

echo "Step 3: Creating tables for unmigrated apps..."
python manage.py migrate --run-syncdb 2>&1 || echo "⚠️  Sync failed, continuing..."

echo "Step 4: Creating superuser if needed..."
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
try:
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@microfinance.local', 'admin123')
        print('✅ Superuser admin created with password: admin123')
    else:
        user = User.objects.get(username='admin')
        user.set_password('admin123')
        user.save()
        print('✅ Superuser admin already exists, password updated: admin123')
except Exception as e:
    print(f'⚠️  Error with superuser: {e}')
" 2>&1 || echo "⚠️  Superuser creation attempt finished"

echo "============================================================"
echo "Initialization complete! Starting gunicorn..."
echo "============================================================"

exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 4 --timeout 120 --access-logfile -
