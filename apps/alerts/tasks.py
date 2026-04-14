"""
Tâches Celery pour les alertes
- Rappels d'échéances à venir
- Surveillance du PAR global
"""
from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task(name='apps.alerts.tasks.check_upcoming_payments')
def check_upcoming_payments():
    """
    Tâche quotidienne : crée des alertes pour les échéances
    à venir dans les 3 et 7 prochains jours
    """
    from apps.loans.models import RepaymentSchedule
    from apps.alerts.models import Alert

    today = timezone.now().date()
    created = 0

    for days_ahead in [3, 7]:
        target_date = today + timezone.timedelta(days=days_ahead)
        upcoming = RepaymentSchedule.objects.filter(
            due_date=target_date,
            status__in=['pending', 'partial'],
            loan__status='active'
        ).select_related('loan', 'loan__client')

        for item in upcoming:
            _, was_created = Alert.objects.get_or_create(
                loan=item.loan,
                alert_type='upcoming',
                created_at__date=today,
                defaults={
                    'severity': 'info',
                    'title': f"Échéance dans {days_ahead} jours — {item.loan.loan_number}",
                    'message': (
                        f"Rappel : l'échéance N°{item.installment_number} de "
                        f"{item.loan.client.full_name} est prévue le "
                        f"{target_date.strftime('%d/%m/%Y')}. "
                        f"Montant : {float(item.amount_due):,.0f} FCFA"
                    ),
                    'client': item.loan.client,
                }
            )
            if was_created:
                created += 1

    logger.info(f"check_upcoming_payments: {created} alertes créées")
    return {'created': created}


@shared_task(name='apps.alerts.tasks.monitor_par')
def monitor_par():
    """
    Surveille le PAR global et crée une alerte si > 10%
    """
    from apps.loans.models import Loan
    from apps.alerts.models import Alert
    from django.db.models import Sum
    from decimal import Decimal

    active_loans = Loan.objects.filter(status='active')
    total_portfolio = active_loans.aggregate(
        t=Sum('approved_amount')
    )['t'] or Decimal('0')

    if total_portfolio == 0:
        return {'par': 0}

    par_amount = sum(
        loan.par_contribution for loan in active_loans
    )
    par_pct = (par_amount / float(total_portfolio)) * 100

    if par_pct > 10:
        Alert.objects.create(
            alert_type='par_threshold',
            severity='critical',
            title=f"PAR > 10% — Seuil critique atteint ({par_pct:.1f}%)",
            message=(
                f"Le Portfolio at Risk dépasse le seuil d'alerte : {par_pct:.1f}% "
                f"({par_amount:,.0f} FCFA à risque sur {float(total_portfolio):,.0f} FCFA). "
                f"Une revue du portefeuille est nécessaire."
            ),
        )
        logger.warning(f"PAR critique: {par_pct:.1f}%")
    elif par_pct > 5:
        Alert.objects.create(
            alert_type='par_threshold',
            severity='warning',
            title=f"PAR > 5% — Vigilance requise ({par_pct:.1f}%)",
            message=(
                f"Le PAR atteint {par_pct:.1f}% ({par_amount:,.0f} FCFA). "
                f"Renforcement du recouvrement recommandé."
            ),
        )

    logger.info(f"monitor_par: PAR = {par_pct:.2f}%")
    return {'par_pct': round(par_pct, 2), 'par_amount': par_amount}
