"""
Management command to create a default superuser on first deployment.
Usage: python manage.py create_default_superuser
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Creates a default superuser (admin/admin123) if one does not already exist'

    def handle(self, *args, **options):
        if User.objects.filter(username='admin').exists():
            self.stdout.write('Default superuser already exists — skipping creation.')
            return

        User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123',
        )
        self.stdout.write(self.style.SUCCESS(
            'Default superuser created: admin / admin123'
        ))
