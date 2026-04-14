#!/bin/bash
set -e

echo "Waiting for migrations to be applied..."
until python manage.py migrate --check &>/dev/null; do
    echo "Migrations not yet applied, waiting..."
    sleep 2
done

echo "Migrations ready, starting Celery worker..."
exec "$@"
