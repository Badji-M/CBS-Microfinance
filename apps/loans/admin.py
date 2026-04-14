from django.contrib import admin
from django.utils.html import format_html
from .models import Loan, LoanProduct, RepaymentSchedule, Payment, Guarantor


@admin.register(LoanProduct)
class LoanProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'annual_interest_rate', 'min_amount', 'max_amount',
        'min_duration_months', 'max_duration_months', 'amortization_type', 'is_active'
    ]
    list_filter = ['amortization_type', 'is_active', 'requires_guarantor']
    search_fields = ['name']


class RepaymentScheduleInline(admin.TabularInline):
    model = RepaymentSchedule
    extra = 0
    readonly_fields = ['installment_number', 'due_date', 'amount_due',
                       'principal_due', 'interest_due', 'balance_after', 'status']
    fields = ['installment_number', 'due_date', 'amount_due', 'principal_due',
              'interest_due', 'balance_after', 'amount_paid', 'status']
    can_delete = False
    max_num = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ['created_at']
    fields = ['payment_date', 'amount_paid', 'payment_method', 'reference', 'collected_by', 'created_at']


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = [
        'loan_number', 'client', 'product', 'approved_amount',
        'duration_months', 'status_badge', 'disbursement_date',
        'credit_score_at_application', 'application_date'
    ]
    list_filter = ['status', 'product', 'application_date']
    search_fields = ['loan_number', 'client__first_name', 'client__last_name']
    readonly_fields = [
        'loan_number', 'credit_score_at_application', 'risk_level',
        'created_at', 'updated_at', 'approved_by'
    ]
    inlines = [RepaymentScheduleInline, PaymentInline]
    date_hierarchy = 'application_date'
    ordering = ['-created_at']

    fieldsets = (
        ('Identification', {
            'fields': ('loan_number', 'client', 'product', 'guarantor')
        }),
        ('Montants', {
            'fields': ('requested_amount', 'approved_amount', 'duration_months',
                       'interest_rate', 'processing_fee', 'insurance_amount')
        }),
        ('Objet & Garantie', {
            'fields': ('purpose', 'collateral_description', 'collateral_value')
        }),
        ('Statut & Dates', {
            'fields': ('status', 'application_date', 'approval_date',
                       'disbursement_date', 'first_payment_date', 'maturity_date')
        }),
        ('Scoring ML', {
            'fields': ('credit_score_at_application', 'risk_level')
        }),
        ('Approbation', {
            'fields': ('approved_by', 'rejection_reason', 'notes')
        }),
    )

    def status_badge(self, obj):
        colors = {
            'draft': '#9E9E9E', 'pending': '#F9A825', 'approved': '#00695C',
            'active': '#1565C0', 'completed': '#2E7D32',
            'rejected': '#C62828', 'defaulted': '#AD1457', 'cancelled': '#616161'
        }
        color = colors.get(obj.status, '#9E9E9E')
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;'
            'border-radius:12px;font-size:11px">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Statut'

    actions = ['generate_schedule']

    @admin.action(description='Générer l\'échéancier')
    def generate_schedule(self, request, queryset):
        count = 0
        for loan in queryset.filter(status='active'):
            loan.create_repayment_schedule()
            count += 1
        self.message_user(request, f'{count} échéanciers générés.')


@admin.register(RepaymentSchedule)
class RepaymentScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'loan', 'installment_number', 'due_date', 'amount_due',
        'amount_paid', 'days_late', 'status'
    ]
    list_filter = ['status', 'due_date']
    search_fields = ['loan__loan_number', 'loan__client__first_name']
    ordering = ['due_date']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'loan', 'payment_date', 'amount_paid', 'payment_method',
        'reference', 'collected_by'
    ]
    list_filter = ['payment_method', 'payment_date']
    search_fields = ['loan__loan_number', 'reference']
    date_hierarchy = 'payment_date'


@admin.register(Guarantor)
class GuarantorAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'national_id', 'phone', 'relationship', 'monthly_income']
    search_fields = ['full_name', 'national_id', 'phone']
