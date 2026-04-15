from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dashboard'
    verbose_name = 'Tableau de bord'

    def ready(self):
        from django.db.models.signals import post_migrate
        post_migrate.connect(_create_default_superuser, sender=self)


def _create_default_superuser(sender, **kwargs):
    """Create the default admin superuser after migrations, if not present."""
    try:
        from django.contrib.auth.models import User
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123',
            )
            print('Default superuser created: admin / admin123')
    except Exception:
        # Database may not be ready yet (e.g. during initial migrate --run-syncdb).
        # The management command can be run manually in that case.
        pass
