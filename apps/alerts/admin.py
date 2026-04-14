from django.contrib import admin
from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'alert_type', 'severity', 'loan', 'client',
        'is_resolved', 'created_at'
    ]
    list_filter = ['alert_type', 'severity', 'is_resolved', 'created_at']
    search_fields = ['title', 'message', 'loan__loan_number', 'client__first_name']
    readonly_fields = ['created_at', 'resolved_at', 'resolved_by']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    actions = ['mark_resolved']

    @admin.action(description='Marquer comme résolues')
    def mark_resolved(self, request, queryset):
        from django.utils import timezone
        queryset.update(
            is_resolved=True,
            resolved_at=timezone.now(),
            resolved_by=request.user
        )
        self.message_user(request, f'{queryset.count()} alertes résolues.')
