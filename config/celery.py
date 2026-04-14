"""
Configuration Celery pour MicroFinance Platform
"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('microfinance')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Scheduled tasks
app.conf.beat_schedule = {
    # Vérifie les impayés toutes les heures
    'update-overdue-payments': {
        'task': 'apps.loans.tasks.update_overdue_payments',
        'schedule': crontab(minute=0),  # Toutes les heures
    },
    # Rappels d'échéances chaque matin à 8h
    'check-upcoming-payments': {
        'task': 'apps.alerts.tasks.check_upcoming_payments',
        'schedule': crontab(hour=8, minute=0),
    },
    # Pénalités recalculées chaque nuit à minuit
    'apply-late-penalties': {
        'task': 'apps.loans.tasks.apply_late_penalties',
        'schedule': crontab(hour=0, minute=30),
    },
    # Surveillance PAR chaque jour à 7h
    'monitor-par': {
        'task': 'apps.alerts.tasks.monitor_par',
        'schedule': crontab(hour=7, minute=0),
    },
    # Refresh scores chaque dimanche
    'refresh-credit-scores': {
        'task': 'apps.loans.tasks.refresh_credit_scores',
        'schedule': crontab(day_of_week=0, hour=2, minute=0),
    },
}

app.conf.timezone = 'Africa/Dakar'


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
