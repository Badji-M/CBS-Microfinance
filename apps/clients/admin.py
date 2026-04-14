from django.contrib import admin
from .models import Client, ClientDocument


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = [
        'full_name', 'national_id', 'phone', 'city',
        'employment_type', 'monthly_income', 'credit_score', 'is_active'
    ]
    list_filter = ['employment_type', 'gender', 'is_active', 'city', 'marital_status']
    search_fields = ['first_name', 'last_name', 'national_id', 'phone', 'email']
    readonly_fields = ['credit_score', 'credit_score_updated_at', 'created_at', 'updated_at']
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('first_name', 'last_name', 'national_id', 'date_of_birth',
                       'gender', 'marital_status', 'number_of_dependents')
        }),
        ('Contact', {
            'fields': ('phone', 'email', 'address', 'city', 'region')
        }),
        ('Profil professionnel', {
            'fields': ('employment_type', 'employer', 'years_employed', 'education_level')
        }),
        ('Profil financier', {
            'fields': ('monthly_income', 'monthly_expenses', 'other_loan_outstanding', 'has_bank_account')
        }),
        ('Score & Statut', {
            'fields': ('credit_score', 'credit_score_updated_at', 'is_active', 'registration_date')
        }),
    )
    date_hierarchy = 'registration_date'
    ordering = ['-created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('loans')


@admin.register(ClientDocument)
class ClientDocumentAdmin(admin.ModelAdmin):
    list_display = ['client', 'doc_type', 'is_verified', 'uploaded_at']
    list_filter = ['doc_type', 'is_verified']
    search_fields = ['client__first_name', 'client__last_name']
    actions = ['mark_verified']

    @admin.action(description='Marquer comme vérifié')
    def mark_verified(self, request, queryset):
        queryset.update(is_verified=True)
