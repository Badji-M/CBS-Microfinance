from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Client(models.Model):
    """Modèle client pour la microfinance"""

    GENDER_CHOICES = [('M', 'Masculin'), ('F', 'Féminin')]
    MARITAL_STATUS_CHOICES = [
        ('single', 'Célibataire'),
        ('married', 'Marié(e)'),
        ('divorced', 'Divorcé(e)'),
        ('widowed', 'Veuf/Veuve'),
    ]
    EMPLOYMENT_TYPE_CHOICES = [
        ('employed', 'Salarié'),
        ('self_employed', 'Indépendant'),
        ('business_owner', 'Chef d\'entreprise'),
        ('farmer', 'Agriculteur'),
        ('unemployed', 'Sans emploi'),
        ('retired', 'Retraité'),
    ]
    EDUCATION_CHOICES = [
        ('none', 'Aucun'),
        ('primary', 'Primaire'),
        ('secondary', 'Secondaire'),
        ('university', 'Universitaire'),
        ('postgraduate', 'Post-universitaire'),
    ]

    # Personal Info
    first_name = models.CharField('Prénom', max_length=100)
    last_name = models.CharField('Nom', max_length=100)
    national_id = models.CharField('CNI/Passeport', max_length=50, unique=True)
    date_of_birth = models.DateField('Date de naissance')
    gender = models.CharField('Genre', max_length=1, choices=GENDER_CHOICES)
    marital_status = models.CharField('Statut matrimonial', max_length=20, choices=MARITAL_STATUS_CHOICES)
    number_of_dependents = models.PositiveIntegerField('Nombre de personnes à charge', default=0)

    # Contact
    phone = models.CharField('Téléphone', max_length=20)
    email = models.EmailField('Email', blank=True, null=True)
    address = models.TextField('Adresse')
    city = models.CharField('Ville', max_length=100)
    region = models.CharField('Région', max_length=100)

    # Professional
    employment_type = models.CharField('Type d\'emploi', max_length=30, choices=EMPLOYMENT_TYPE_CHOICES)
    employer = models.CharField('Employeur/Activité', max_length=200, blank=True)
    monthly_income = models.DecimalField('Revenu mensuel (FCFA)', max_digits=15, decimal_places=2)
    years_employed = models.PositiveIntegerField('Années d\'activité', default=0)
    education_level = models.CharField('Niveau d\'éducation', max_length=30, choices=EDUCATION_CHOICES)

    # Financial Profile
    has_bank_account = models.BooleanField('Possède un compte bancaire', default=False)
    monthly_expenses = models.DecimalField('Dépenses mensuelles (FCFA)', max_digits=15, decimal_places=2, default=0)
    other_loan_outstanding = models.DecimalField('Autres dettes en cours (FCFA)', max_digits=15, decimal_places=2, default=0)

    # Client Status
    is_active = models.BooleanField('Actif', default=True)
    registration_date = models.DateField('Date d\'enregistrement', default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Credit Score (computed)
    credit_score = models.FloatField('Score de crédit', null=True, blank=True)
    credit_score_updated_at = models.DateTimeField('Dernière évaluation', null=True, blank=True)

    class Meta:
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.last_name} {self.first_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        today = timezone.now().date()
        return (today - self.date_of_birth).days // 365

    @property
    def debt_to_income_ratio(self):
        if self.monthly_income > 0:
            return float(self.other_loan_outstanding) / (float(self.monthly_income) * 12)
        return 0

    @property
    def disposable_income(self):
        return float(self.monthly_income) - float(self.monthly_expenses)

    @property
    def loan_count(self):
        return self.loans.count()

    @property
    def active_loan_count(self):
        return self.loans.filter(status='active').count()

    @property
    def active_loan_count(self):
        return self.loans.filter(status__in=['active', 'approved']).count()

    @property
    def credit_score_label(self):
        if self.credit_score is None:
            return ('Non évalué', 'secondary')
        score = self.credit_score
        if score >= 0.8:
            return ('Excellent', 'success')
        elif score >= 0.6:
            return ('Bon', 'info')
        elif score >= 0.4:
            return ('Moyen', 'warning')
        else:
            return ('Risqué', 'danger')


class ClientDocument(models.Model):
    """Documents justificatifs du client"""
    DOC_TYPE_CHOICES = [
        ('id_card', 'Carte nationale d\'identité'),
        ('passport', 'Passeport'),
        ('income_proof', 'Justificatif de revenus'),
        ('address_proof', 'Justificatif de domicile'),
        ('bank_statement', 'Relevé bancaire'),
        ('business_license', 'Registre de commerce'),
        ('other', 'Autre'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField('Type de document', max_length=30, choices=DOC_TYPE_CHOICES)
    file = models.FileField('Fichier', upload_to='client_documents/')
    description = models.CharField('Description', max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField('Vérifié', default=False)

    class Meta:
        verbose_name = 'Document client'

    def __str__(self):
        return f"{self.client} - {self.get_doc_type_display()}"
