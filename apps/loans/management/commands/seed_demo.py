"""
Management command to create demo data for the microfinance platform.
Usage: python manage.py seed_demo
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from decimal import Decimal
import random
from datetime import date, timedelta


class Command(BaseCommand):
    help = 'Crée des données de démonstration pour la plateforme'

    def add_arguments(self, parser):
        parser.add_argument('--clients', type=int, default=30, help='Nombre de clients')
        parser.add_argument('--loans', type=int, default=50, help='Nombre de prêts')
        parser.add_argument('--clear', action='store_true', help='Vider les données existantes')

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('🗑️  Suppression des données existantes...')
            from apps.loans.models import Payment, RepaymentSchedule, Loan, LoanProduct, Guarantor
            from apps.clients.models import Client, ClientDocument
            from apps.alerts.models import Alert
            Alert.objects.all().delete()
            Payment.objects.all().delete()
            RepaymentSchedule.objects.all().delete()
            Loan.objects.all().delete()
            LoanProduct.objects.all().delete()
            Guarantor.objects.all().delete()
            Client.objects.all().delete()

        self.stdout.write('🚀 Création des données de démonstration...')

        # 1. Create superuser if needed
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@microfinance.sn', 'admin123')
            self.stdout.write(self.style.SUCCESS('✅ Superuser créé: admin / admin123'))

        # 2. Create loan products
        from apps.loans.models import LoanProduct
        products = self._create_products()
        self.stdout.write(f'✅ {len(products)} produits de prêt créés')

        # 3. Create clients
        from apps.clients.models import Client
        clients = self._create_clients(options['clients'])
        self.stdout.write(f'✅ {len(clients)} clients créés')

        # 4. Score clients
        from apps.scoring.ml_service import scoring_service
        scored = 0
        for client in clients:
            try:
                result = scoring_service.score_client(client)
                client.credit_score = result['score']
                client.credit_score_updated_at = timezone.now()
                client.save(update_fields=['credit_score', 'credit_score_updated_at'])
                scored += 1
            except Exception:
                pass
        self.stdout.write(f'✅ {scored} clients scorés')

        # 5. Create loans
        loans = self._create_loans(clients, products, options['loans'])
        self.stdout.write(f'✅ {len(loans)} prêts créés')

        # 6. Create payments for active/completed loans
        payments_created = self._create_payments(loans)
        self.stdout.write(f'✅ {payments_created} paiements enregistrés')

        # 7. Create alerts
        alerts_created = self._create_alerts(loans)
        self.stdout.write(f'✅ {alerts_created} alertes créées')

        self.stdout.write(self.style.SUCCESS(
            '\n🎉 Données de démonstration créées avec succès!\n'
            '   Connectez-vous sur http://localhost:8000 avec admin / admin123'
        ))

    def _create_products(self):
        from apps.loans.models import LoanProduct
        products_data = [
            {
                'name': 'Microcrédit Rural',
                'description': 'Prêt pour activités agricoles et rurales',
                'min_amount': 50000, 'max_amount': 500000,
                'min_duration_months': 3, 'max_duration_months': 18,
                'annual_interest_rate': 24, 'processing_fee_rate': 1,
                'amortization_type': 'constant',
                'min_credit_score': 0.30,
            },
            {
                'name': 'Prêt Commerce',
                'description': 'Financement pour activités commerciales',
                'min_amount': 100000, 'max_amount': 2000000,
                'min_duration_months': 6, 'max_duration_months': 36,
                'annual_interest_rate': 20, 'processing_fee_rate': 2,
                'amortization_type': 'constant',
                'min_credit_score': 0.40,
            },
            {
                'name': 'Prêt PME',
                'description': 'Financement des petites et moyennes entreprises',
                'min_amount': 500000, 'max_amount': 10000000,
                'min_duration_months': 12, 'max_duration_months': 60,
                'annual_interest_rate': 18, 'processing_fee_rate': 2,
                'insurance_rate': 0.5,
                'amortization_type': 'degressive',
                'requires_guarantor': True,
                'min_credit_score': 0.55,
            },
            {
                'name': 'Crédit Solidaire',
                'description': 'Prêt groupes solidaires (femmes)',
                'min_amount': 25000, 'max_amount': 200000,
                'min_duration_months': 3, 'max_duration_months': 12,
                'annual_interest_rate': 22, 'processing_fee_rate': 0.5,
                'amortization_type': 'constant',
                'min_credit_score': 0.25,
            },
        ]

        products = []
        for data in products_data:
            p, _ = LoanProduct.objects.get_or_create(name=data['name'], defaults=data)
            products.append(p)
        return products

    def _create_clients(self, count):
        from apps.clients.models import Client

        prenoms_h = ['Mamadou', 'Ibrahima', 'Ousmane', 'Cheikh', 'Modou', 'Abdou', 'Serigne', 'Aliou']
        prenoms_f = ['Fatou', 'Aminata', 'Mariama', 'Aissatou', 'Rokhaya', 'Ndèye', 'Coumba', 'Awa']
        noms = ['Diallo', 'Ndiaye', 'Sow', 'Ba', 'Diop', 'Fall', 'Thiam', 'Mbaye', 'Gueye', 'Sy']
        villes = ['Dakar', 'Thiès', 'Saint-Louis', 'Kaolack', 'Ziguinchor', 'Diourbel', 'Tambacounda']
        employments = ['employed', 'self_employed', 'business_owner', 'farmer', 'unemployed']
        employment_weights = [0.25, 0.30, 0.20, 0.15, 0.10]
        education_levels = ['none', 'primary', 'secondary', 'university']
        marital_statuses = ['single', 'married', 'divorced', 'widowed']

        clients = []
        for i in range(count):
            gender = random.choice(['M', 'F'])
            if gender == 'M':
                first_name = random.choice(prenoms_h)
            else:
                first_name = random.choice(prenoms_f)

            last_name = random.choice(noms)
            birth_year = random.randint(1965, 2000)
            birth_date = date(birth_year, random.randint(1, 12), random.randint(1, 28))
            employment = random.choices(employments, weights=employment_weights)[0]

            income_map = {
                'employed': random.uniform(80000, 400000),
                'self_employed': random.uniform(50000, 300000),
                'business_owner': random.uniform(200000, 1000000),
                'farmer': random.uniform(30000, 150000),
                'unemployed': random.uniform(20000, 80000),
            }
            income = income_map[employment]

            city = random.choice(villes)
            client = Client(
                first_name=first_name,
                last_name=last_name,
                national_id=f"SN{random.randint(1000000, 9999999)}",
                date_of_birth=birth_date,
                gender=gender,
                marital_status=random.choice(marital_statuses),
                number_of_dependents=random.randint(0, 6),
                phone=f"+221 7{random.randint(0,9)} {random.randint(100,999)} {random.randint(10,99)} {random.randint(10,99)}",
                email=f"{first_name.lower()}.{last_name.lower()}{i}@email.sn" if random.random() > 0.4 else None,
                address=f"{random.randint(1, 200)}, Rue {random.randint(1, 50)}",
                city=city,
                region=city,
                employment_type=employment,
                employer=f"{'Entreprise' if employment in ['employed', 'business_owner'] else 'Indépendant'} {random.randint(1,100)}",
                monthly_income=Decimal(str(round(income, -2))),
                years_employed=random.randint(0, 20),
                education_level=random.choice(education_levels),
                has_bank_account=random.random() > 0.4,
                monthly_expenses=Decimal(str(round(income * random.uniform(0.3, 0.75), -2))),
                other_loan_outstanding=Decimal(str(round(random.uniform(0, income * 6), -2))),
                registration_date=date.today() - timedelta(days=random.randint(0, 730)),
            )
            client.save()
            clients.append(client)

        return clients

    def _create_loans(self, clients, products, count):
        from apps.loans.models import Loan
        from apps.scoring.ml_service import scoring_service

        statuses_with_weights = [
            ('completed', 0.25), ('active', 0.40), ('pending', 0.15),
            ('rejected', 0.10), ('defaulted', 0.10)
        ]
        statuses = [s for s, _ in statuses_with_weights]
        weights = [w for _, w in statuses_with_weights]

        loans = []
        admin_user = User.objects.filter(is_superuser=True).first()

        for i in range(min(count, len(clients) * 2)):
            client = random.choice(clients)
            product = random.choice(products)
            status = random.choices(statuses, weights=weights)[0]

            amount_range = (float(product.min_amount), float(product.max_amount))
            amount = round(random.uniform(*amount_range), -3)
            duration = random.randint(product.min_duration_months, product.max_duration_months)

            app_date = date.today() - timedelta(days=random.randint(30, 720))

            monthly_rate = float(product.annual_interest_rate) / 100 / 12

            loan = Loan(
                client=client,
                product=product,
                requested_amount=Decimal(str(amount)),
                duration_months=duration,
                interest_rate=Decimal(str(round(monthly_rate * 100, 4))),
                processing_fee=Decimal(str(round(amount * float(product.processing_fee_rate) / 100, 0))),
                insurance_amount=Decimal(str(round(amount * float(product.insurance_rate) / 100, 0))),
                purpose=random.choice([
                    'Achat de marchandises', 'Équipement agricole',
                    'Fonds de roulement', 'Expansion de commerce',
                    'Matériel de production', 'Construction boutique',
                    'Achat de bétail', 'Financement récolte',
                ]),
                status=status,
                application_date=app_date,
                credit_score_at_application=client.credit_score,
                risk_level='Modéré' if client.credit_score and client.credit_score >= 0.5 else 'Élevé',
            )

            if status in ('active', 'completed', 'defaulted', 'approved'):
                loan.approved_amount = Decimal(str(amount))
                loan.approval_date = app_date + timedelta(days=random.randint(3, 10))
                loan.approved_by = admin_user

            if status in ('active', 'completed', 'defaulted'):
                loan.disbursement_date = loan.approval_date + timedelta(days=random.randint(1, 7))
                from dateutil.relativedelta import relativedelta
                loan.first_payment_date = loan.disbursement_date + relativedelta(months=1)
                loan.maturity_date = loan.disbursement_date + relativedelta(months=duration)

            if status == 'rejected':
                loan.rejection_reason = random.choice([
                    'Score de crédit insuffisant',
                    'Revenus insuffisants pour couvrir les mensualités',
                    'Trop d\'endettement en cours',
                    'Documents incomplets',
                ])

            loan.save()

            # Create schedule for active/completed/defaulted
            if status in ('active', 'completed', 'defaulted') and loan.disbursement_date:
                loan.create_repayment_schedule()

            loans.append(loan)

        return loans

    def _create_payments(self, loans):
        from apps.loans.models import Payment, RepaymentSchedule
        from decimal import Decimal

        admin_user = User.objects.filter(is_superuser=True).first()
        payment_methods = ['cash', 'mobile_money', 'bank_transfer', 'check']
        total_payments = 0

        for loan in loans:
            if loan.status not in ('active', 'completed', 'defaulted'):
                continue

            schedule = loan.schedule.filter(
                status__in=['pending', 'partial', 'overdue']
            ).order_by('installment_number')

            if not schedule.exists():
                continue

            # Pay some installments based on status
            if loan.status == 'completed':
                pay_all = True
                pay_count = schedule.count()
            elif loan.status == 'defaulted':
                pay_count = max(0, int(schedule.count() * random.uniform(0.1, 0.4)))
                pay_all = False
            else:
                pay_count = max(0, int(schedule.count() * random.uniform(0.2, 0.8)))
                pay_all = False

            for item in list(schedule)[:pay_count]:
                payment_date = item.due_date + timedelta(days=random.randint(-2, 15))
                payment_date = min(payment_date, date.today())

                payment = Payment(
                    loan=loan,
                    schedule_item=item,
                    payment_date=payment_date,
                    amount_paid=item.amount_due,
                    principal_paid=item.principal_due,
                    interest_paid=item.interest_due,
                    payment_method=random.choice(payment_methods),
                    reference=f"REF{random.randint(100000, 999999)}",
                    collected_by=admin_user,
                )
                payment.save()

                days_late = max(0, (payment_date - item.due_date).days)
                item.amount_paid = item.amount_due
                item.payment_date = payment_date
                item.days_late = days_late
                item.status = 'paid'
                item.save()
                total_payments += 1

            # Mark remaining as overdue for defaulted/active
            today = date.today()
            for item in loan.schedule.filter(
                status__in=['pending', 'partial'],
                due_date__lt=today
            ):
                item.status = 'overdue'
                item.days_late = (today - item.due_date).days
                item.save()

        return total_payments

    def _create_alerts(self, loans):
        from apps.alerts.models import Alert

        count = 0
        for loan in loans:
            if loan.status == 'defaulted':
                Alert.objects.create(
                    alert_type='overdue',
                    severity='critical',
                    title=f"Prêt en défaut — {loan.loan_number}",
                    message=f"{loan.client.full_name} — Encours : {float(loan.outstanding_balance):,.0f} FCFA",
                    loan=loan, client=loan.client,
                )
                count += 1
            elif loan.status == 'active' and loan.days_past_due > 0:
                Alert.objects.create(
                    alert_type='overdue',
                    severity='warning' if loan.days_past_due < 30 else 'critical',
                    title=f"Retard {loan.days_past_due}j — {loan.loan_number}",
                    message=f"{loan.client.full_name} — {loan.days_past_due} jours de retard",
                    loan=loan, client=loan.client,
                )
                count += 1

        return count
