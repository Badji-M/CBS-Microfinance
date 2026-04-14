"""
Tâches Celery pour la gestion des prêts
- Mise à jour automatique des statuts d'impayés
- Calcul des pénalités de retard
"""
from celery import shared_task
from django.utils import timezone
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)


@shared_task(name='apps.loans.tasks.update_overdue_payments')
def update_overdue_payments():
    """
    Tâche horaire : marque les échéances dépassées comme 'overdue'
    et met à jour le nombre de jours de retard
    """
    from apps.loans.models import RepaymentSchedule, Loan
    from apps.alerts.models import Alert

    today = timezone.now().date()
    updated_count = 0
    alert_count = 0

    # Trouver toutes les échéances en retard non encore marquées
    overdue_items = RepaymentSchedule.objects.filter(
        due_date__lt=today,
        status__in=['pending', 'partial'],
        loan__status='active'
    ).select_related('loan', 'loan__client')

    for item in overdue_items:
        days_late = (today - item.due_date).days
        item.days_late = days_late
        item.status = 'overdue'
        item.save(update_fields=['status', 'days_late'])
        updated_count += 1

        # Créer une alerte si premier jour de retard
        if days_late == 1:
            Alert.objects.get_or_create(
                loan=item.loan,
                alert_type='overdue',
                is_resolved=False,
                defaults={
                    'severity': 'warning',
                    'title': f"Retard de paiement — {item.loan.loan_number}",
                    'message': (
                        f"L'échéance N°{item.installment_number} de "
                        f"{item.loan.client.full_name} était due le "
                        f"{item.due_date.strftime('%d/%m/%Y')}. "
                        f"Montant : {float(item.amount_due):,.0f} FCFA"
                    ),
                    'client': item.loan.client,
                }
            )
            alert_count += 1

        # Alerte critique après 30 jours
        if days_late == 30:
            Alert.objects.create(
                alert_type='overdue',
                severity='critical',
                title=f"PAR 30 — {item.loan.loan_number} en souffrance",
                message=(
                    f"{item.loan.client.full_name} — {days_late} jours de retard. "
                    f"Solde restant : {item.loan.outstanding_balance:,.0f} FCFA. "
                    f"Action urgente requise."
                ),
                loan=item.loan,
                client=item.loan.client,
            )
            alert_count += 1

        # Marquer le prêt en défaut après 90 jours
        if days_late >= 90 and item.loan.status == 'active':
            loan = item.loan
            loan.status = 'defaulted'
            loan.save(update_fields=['status'])
            Alert.objects.create(
                alert_type='overdue',
                severity='critical',
                title=f"Prêt en défaut — {loan.loan_number}",
                message=(
                    f"Le prêt de {loan.client.full_name} est classé en défaut "
                    f"après {days_late} jours de retard. "
                    f"Encours : {loan.outstanding_balance:,.0f} FCFA"
                ),
                loan=loan,
                client=loan.client,
            )

    logger.info(
        f"update_overdue_payments: {updated_count} échéances mises à jour, "
        f"{alert_count} alertes créées"
    )
    return {'updated': updated_count, 'alerts': alert_count}


@shared_task(name='apps.loans.tasks.apply_late_penalties')
def apply_late_penalties():
    """
    Calcule et applique les pénalités de retard (2%/mois)
    """
    from apps.loans.models import RepaymentSchedule
    from decimal import Decimal

    today = timezone.now().date()
    PENALTY_RATE = Decimal('0.02')  # 2% par mois
    updated = 0

    overdue = RepaymentSchedule.objects.filter(
        status='overdue',
        loan__status='active'
    )

    for item in overdue:
        days_late = (today - item.due_date).days
        months_late = Decimal(str(days_late)) / Decimal('30')
        remaining = item.amount_due - item.amount_paid
        penalty = remaining * PENALTY_RATE * months_late

        if penalty != item.penalty_amount:
            item.penalty_amount = penalty
            item.save(update_fields=['penalty_amount'])
            updated += 1

    logger.info(f"apply_late_penalties: {updated} pénalités recalculées")
    return {'updated': updated}


@shared_task(name='apps.loans.tasks.refresh_credit_scores')
def refresh_credit_scores():
    """
    Recalcule les scores de crédit des clients avec des prêts actifs
    """
    from apps.clients.models import Client
    from apps.scoring.ml_service import scoring_service

    clients = Client.objects.filter(
        is_active=True,
        loans__status='active'
    ).distinct()

    updated = 0
    for client in clients:
        try:
            result = scoring_service.score_client(client)
            client.credit_score = result['score']
            client.credit_score_updated_at = timezone.now()
            client.save(update_fields=['credit_score', 'credit_score_updated_at'])
            updated += 1
        except Exception as e:
            logger.warning(f"Erreur scoring client {client.pk}: {e}")

    logger.info(f"refresh_credit_scores: {updated} clients mis à jour")
    return {'updated': updated}
