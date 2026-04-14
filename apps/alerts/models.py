from django.db import models
from django.utils import timezone


class Alert(models.Model):
    ALERT_TYPE_CHOICES = [
        ('overdue', 'Retard de paiement'),
        ('upcoming', 'Échéance proche'),
        ('high_risk', 'Client à risque élevé'),
        ('par_threshold', 'Seuil PAR atteint'),
        ('new_application', 'Nouvelle demande de prêt'),
        ('loan_completed', 'Prêt soldé'),
        ('system', 'Système'),
    ]
    SEVERITY_CHOICES = [
        ('info', 'Information'),
        ('warning', 'Avertissement'),
        ('critical', 'Critique'),
    ]

    alert_type = models.CharField('Type', max_length=30, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField('Sévérité', max_length=20, choices=SEVERITY_CHOICES, default='info')
    title = models.CharField('Titre', max_length=200)
    message = models.TextField('Message')
    loan = models.ForeignKey('loans.Loan', on_delete=models.CASCADE,
                              null=True, blank=True, related_name='alerts')
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE,
                                null=True, blank=True, related_name='alerts')
    is_resolved = models.BooleanField('Résolu', default=False)
    resolved_at = models.DateTimeField('Résolu le', null=True, blank=True)
    resolved_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL,
                                     null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Alerte'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.title}"

    @property
    def severity_icon(self):
        icons = {'info': '💡', 'warning': '⚠️', 'critical': '🚨'}
        return icons.get(self.severity, '📢')

    @property
    def severity_color(self):
        colors = {'info': 'primary', 'warning': 'warning', 'critical': 'danger'}
        return colors.get(self.severity, 'secondary')
