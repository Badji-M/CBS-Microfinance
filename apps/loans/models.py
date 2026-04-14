from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid
from dateutil.relativedelta import relativedelta


class LoanProduct(models.Model):
    """Produits de prêt disponibles"""
    AMORTIZATION_CHOICES = [
        ('constant', 'Amortissement constant (mensualité fixe)'),
        ('degressive', 'Amortissement dégressif (principal fixe)'),
    ]

    name = models.CharField('Nom du produit', max_length=200)
    description = models.TextField('Description', blank=True)
    min_amount = models.DecimalField('Montant minimum (FCFA)', max_digits=15, decimal_places=2)
    max_amount = models.DecimalField('Montant maximum (FCFA)', max_digits=15, decimal_places=2)
    min_duration_months = models.PositiveIntegerField('Durée minimum (mois)')
    max_duration_months = models.PositiveIntegerField('Durée maximum (mois)')
    annual_interest_rate = models.DecimalField('Taux d\'intérêt annuel (%)', max_digits=5, decimal_places=2)
    processing_fee_rate = models.DecimalField('Frais de dossier (%)', max_digits=5, decimal_places=2, default=0)
    insurance_rate = models.DecimalField('Assurance (%)', max_digits=5, decimal_places=2, default=0)
    amortization_type = models.CharField('Type d\'amortissement', max_length=20, choices=AMORTIZATION_CHOICES, default='constant')
    requires_guarantor = models.BooleanField('Garant requis', default=False)
    requires_collateral = models.BooleanField('Garantie matérielle requise', default=False)
    min_credit_score = models.FloatField('Score minimum requis', default=0.3)
    is_active = models.BooleanField('Actif', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Produit de prêt'
        verbose_name_plural = 'Produits de prêt'

    def __str__(self):
        return self.name

    @property
    def monthly_rate(self):
        return float(self.annual_interest_rate) / 100 / 12


class Guarantor(models.Model):
    """Garant pour un prêt"""
    full_name = models.CharField('Nom complet', max_length=200)
    national_id = models.CharField('CNI', max_length=50)
    phone = models.CharField('Téléphone', max_length=20)
    address = models.TextField('Adresse')
    relationship = models.CharField('Relation avec le client', max_length=100)
    monthly_income = models.DecimalField('Revenu mensuel (FCFA)', max_digits=15, decimal_places=2)

    class Meta:
        verbose_name = 'Garant'

    def __str__(self):
        return self.full_name


class Loan(models.Model):
    """Prêt accordé à un client"""
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('pending', 'En attente d\'approbation'),
        ('approved', 'Approuvé'),
        ('active', 'Actif (décaissé)'),
        ('completed', 'Soldé'),
        ('rejected', 'Rejeté'),
        ('cancelled', 'Annulé'),
        ('defaulted', 'En défaut'),
    ]

    loan_number = models.CharField('Numéro de prêt', max_length=20, unique=True, editable=False)
    client = models.ForeignKey('clients.Client', on_delete=models.PROTECT, related_name='loans', verbose_name='Client')
    product = models.ForeignKey(LoanProduct, on_delete=models.PROTECT, related_name='loans', verbose_name='Produit')
    guarantor = models.ForeignKey(Guarantor, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Garant')

    # Loan Terms
    requested_amount = models.DecimalField('Montant demandé (FCFA)', max_digits=15, decimal_places=2)
    approved_amount = models.DecimalField('Montant approuvé (FCFA)', max_digits=15, decimal_places=2, null=True, blank=True)
    duration_months = models.PositiveIntegerField('Durée (mois)')
    interest_rate = models.DecimalField('Taux d\'intérêt mensuel (%)', max_digits=5, decimal_places=4)
    processing_fee = models.DecimalField('Frais de dossier (FCFA)', max_digits=15, decimal_places=2, default=0)
    insurance_amount = models.DecimalField('Assurance (FCFA)', max_digits=15, decimal_places=2, default=0)
    purpose = models.TextField('Objet du prêt')

    # Status & Dates
    status = models.CharField('Statut', max_length=20, choices=STATUS_CHOICES, default='draft')
    application_date = models.DateField('Date de demande', default=timezone.now)
    approval_date = models.DateField('Date d\'approbation', null=True, blank=True)
    disbursement_date = models.DateField('Date de décaissement', null=True, blank=True)
    first_payment_date = models.DateField('Date 1ère échéance', null=True, blank=True)
    maturity_date = models.DateField('Date d\'échéance finale', null=True, blank=True)

    # Credit Scoring at time of application
    credit_score_at_application = models.FloatField('Score de crédit à la demande', null=True, blank=True)
    risk_level = models.CharField('Niveau de risque', max_length=20, blank=True)

    # Approval/Rejection
    approved_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='approved_loans', verbose_name='Approuvé par')
    rejection_reason = models.TextField('Motif de rejet', blank=True)
    notes = models.TextField('Notes', blank=True)

    # Collateral
    collateral_description = models.TextField('Description de la garantie', blank=True)
    collateral_value = models.DecimalField('Valeur de la garantie (FCFA)', max_digits=15, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Prêt'
        verbose_name_plural = 'Prêts'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.loan_number} - {self.client}"

    def save(self, *args, **kwargs):
        if not self.loan_number:
            self.loan_number = self._generate_loan_number()
        if self.approved_amount and self.disbursement_date and not self.first_payment_date:
            from dateutil.relativedelta import relativedelta
            self.first_payment_date = self.disbursement_date + relativedelta(months=1)
            self.maturity_date = self.disbursement_date + relativedelta(months=self.duration_months)
        super().save(*args, **kwargs)

    def _generate_loan_number(self):
        import random
        year = timezone.now().year
        random_part = random.randint(10000, 99999)
        return f"MF{year}{random_part}"

    @property
    def principal(self):
        return self.approved_amount or self.requested_amount

    @property
    def monthly_rate(self):
        return float(self.interest_rate) / 100

    @property
    def total_interest(self):
        schedule = self.get_amortization_schedule()
        return sum(row['interest'] for row in schedule)

    @property
    def total_amount_due(self):
        return float(self.principal) + self.total_interest + float(self.processing_fee) + float(self.insurance_amount)

    @property
    def total_paid(self):
        return float(self.payments.filter(status='paid').aggregate(
            total=models.Sum('amount_paid'))['total'] or 0)

    @property
    def outstanding_balance(self):
        paid_principal = float(self.payments.filter(status='paid').aggregate(
            total=models.Sum('principal_paid'))['total'] or 0)
        return float(self.principal) - paid_principal

    @property
    def overdue_installments(self):
        today = timezone.now().date()
        return self.schedule.filter(due_date__lt=today, status__in=['pending', 'partial', 'overdue'])

    @property
    def days_past_due(self):
        overdue = self.overdue_installments
        if not overdue.exists():
            return 0
        oldest = overdue.order_by('due_date').first()
        return (timezone.now().date() - oldest.due_date).days

    @property
    def par_contribution(self):
        """Portfolio at Risk contribution"""
        if self.days_past_due > 30 and self.status == 'active':
            return float(self.outstanding_balance)
        return 0

    def get_amortization_schedule(self):
        """Calculate amortization schedule"""
        amount = float(self.principal)
        rate = self.monthly_rate
        n = self.duration_months
        amort_type = self.product.amortization_type

        schedule = []

        if amort_type == 'constant':
            # Constant payment (annuity formula)
            if rate > 0:
                monthly_payment = amount * (rate * (1 + rate) ** n) / ((1 + rate) ** n - 1)
            else:
                monthly_payment = amount / n

            balance = amount
            for i in range(1, n + 1):
                interest = balance * rate
                principal = monthly_payment - interest
                balance -= principal
                schedule.append({
                    'installment': i,
                    'payment': round(monthly_payment, 2),
                    'principal': round(principal, 2),
                    'interest': round(interest, 2),
                    'balance': round(max(balance, 0), 2),
                })
        else:
            # Degressive (constant principal)
            principal_per_month = amount / n
            balance = amount
            for i in range(1, n + 1):
                interest = balance * rate
                payment = principal_per_month + interest
                balance -= principal_per_month
                schedule.append({
                    'installment': i,
                    'payment': round(payment, 2),
                    'principal': round(principal_per_month, 2),
                    'interest': round(interest, 2),
                    'balance': round(max(balance, 0), 2),
                })

        return schedule

    def create_repayment_schedule(self):
        """Create RepaymentSchedule objects from amortization schedule"""
        from dateutil.relativedelta import relativedelta
        schedule = self.get_amortization_schedule()
        self.schedule.all().delete()

        start_date = self.first_payment_date or timezone.now().date()
        items = []
        for row in schedule:
            due_date = start_date + relativedelta(months=row['installment'] - 1)
            items.append(RepaymentSchedule(
                loan=self,
                installment_number=row['installment'],
                due_date=due_date,
                amount_due=row['payment'],
                principal_due=row['principal'],
                interest_due=row['interest'],
                balance_after=row['balance'],
            ))
        RepaymentSchedule.objects.bulk_create(items)

    @property
    def recovery_rate(self):
        if self.total_amount_due > 0:
            return self.total_paid / self.total_amount_due * 100
        return 0


class RepaymentSchedule(models.Model):
    """Échéancier de remboursement"""
    STATUS_CHOICES = [
        ('pending', 'À payer'),
        ('paid', 'Payé'),
        ('partial', 'Partiellement payé'),
        ('overdue', 'En retard'),
        ('waived', 'Annulé'),
    ]

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='schedule')
    installment_number = models.PositiveIntegerField('N° échéance')
    due_date = models.DateField('Date d\'échéance')
    amount_due = models.DecimalField('Montant dû (FCFA)', max_digits=15, decimal_places=2)
    principal_due = models.DecimalField('Principal dû', max_digits=15, decimal_places=2)
    interest_due = models.DecimalField('Intérêt dû', max_digits=15, decimal_places=2)
    balance_after = models.DecimalField('Solde restant après', max_digits=15, decimal_places=2)
    amount_paid = models.DecimalField('Montant payé', max_digits=15, decimal_places=2, default=0)
    payment_date = models.DateField('Date de paiement', null=True, blank=True)
    days_late = models.IntegerField('Jours de retard', default=0)
    penalty_amount = models.DecimalField('Pénalité de retard', max_digits=15, decimal_places=2, default=0)
    status = models.CharField('Statut', max_length=20, choices=STATUS_CHOICES, default='pending')

    class Meta:
        verbose_name = 'Échéance'
        verbose_name_plural = 'Échéancier'
        ordering = ['installment_number']
        unique_together = ['loan', 'installment_number']

    def __str__(self):
        return f"{self.loan.loan_number} - Échéance {self.installment_number}"

    @property
    def remaining_amount(self):
        return float(self.amount_due) - float(self.amount_paid) + float(self.penalty_amount)

    @property
    def is_overdue(self):
        return self.due_date < timezone.now().date() and self.status in ['pending', 'partial']


class Payment(models.Model):
    """Paiement effectué"""
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Espèces'),
        ('mobile_money', 'Mobile Money'),
        ('bank_transfer', 'Virement bancaire'),
        ('check', 'Chèque'),
    ]

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='payments')
    schedule_item = models.ForeignKey(RepaymentSchedule, on_delete=models.SET_NULL, null=True, blank=True)
    payment_date = models.DateField('Date de paiement')
    amount_paid = models.DecimalField('Montant payé', max_digits=15, decimal_places=2)
    principal_paid = models.DecimalField('Principal payé', max_digits=15, decimal_places=2, default=0)
    interest_paid = models.DecimalField('Intérêt payé', max_digits=15, decimal_places=2, default=0)
    penalty_paid = models.DecimalField('Pénalité payée', max_digits=15, decimal_places=2, default=0)
    payment_method = models.CharField('Mode de paiement', max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference = models.CharField('Référence', max_length=100, blank=True)
    status = models.CharField('Statut', max_length=20, default='paid')
    collected_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, verbose_name='Collecté par')
    notes = models.TextField('Notes', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Paiement'
        verbose_name_plural = 'Paiements'
        ordering = ['-payment_date']

    def __str__(self):
        return f"Paiement {self.loan.loan_number} - {self.amount_paid} FCFA le {self.payment_date}"
