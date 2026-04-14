"""
Management command to add payment delays to some loans for PAR reporting.
Usage: python manage.py add_delays
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Max
from apps.loans.models import Loan, RepaymentSchedule
from decimal import Decimal
from datetime import datetime, timedelta
import random


class Command(BaseCommand):
    help = 'Ajoute des retards de paiement à certains prêts pour démonstration du PAR'

    def handle(self, *args, **options):
        """
        Crée des retards en changeant le statut de certaines échéances payées
        en partial et en ajoutant des éléments pending avec dates passées
        """
        active_loans = Loan.objects.filter(status='active')
        
        if not active_loans.exists():
            self.stdout.write(self.style.ERROR('Aucun prêt actif trouvé'))
            return

        today = timezone.now().date()
        delays = [15, 45, 75, 120]  # jours de retard
        
        count = 0
        for loan in active_loans[:len(delays)]:
            delay_days = delays[count % len(delays)]
            
            # Créer une nouvelle échéance non payée avec date passée
            due_date = today - timedelta(days=delay_days)
            
            # Trouver le numéro d'échéance suivant
            last_installment = loan.schedule.aggregate(
                max_num=Max('installment_number')
            )['max_num'] or 0
            
            # Créer nouvelle échéance "pending" avec date passée
            new_installment = RepaymentSchedule.objects.create(
                loan=loan,
                installment_number=last_installment + 1,
                due_date=due_date,
                amount_due=Decimal('10000'),  # Montant sympathique
                status='pending',
            )
            
            count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'Prêt {loan.loan_number} — {loan.client.full_name}: '
                    f'{delay_days} jours de retard'
                )
            )
        
        self.stdout.write(self.style.SUCCESS(
            f'\n{count} prêts marqués en retard pour le PAR'
        ))
