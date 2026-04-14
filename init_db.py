#!/usr/bin/env python
import os
import sys
import django
from django.core.management import execute_from_command_line
from django.contrib.auth.models import User

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

print("=" * 60)
print("Starting application initialization...")
print("=" * 60)

# 1. Apply all migrations
print("\nApplying migrations...")
execute_from_command_line(['manage.py', 'migrate', '--run-syncdb'])

# 2. Create superuser
print("\nCreating superuser if needed...")
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@microfinance.local', 'admin123')
    print('Superuser admin created')
else:
    print('Superuser admin already exists')

# 3. Collect static files (if needed)
print("\nDone! Starting Django server...")
print("=" * 60)
