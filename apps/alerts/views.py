from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Alert


@login_required
def alert_list(request):
    alerts = Alert.objects.select_related('loan', 'client').order_by('-created_at')

    severity = request.GET.get('severity', '')
    if severity:
        alerts = alerts.filter(severity=severity)

    resolved = request.GET.get('resolved', 'false')
    if resolved == 'false':
        alerts = alerts.filter(is_resolved=False)

    return render(request, 'alerts/list.html', {
        'alerts': alerts[:50],
        'severity': severity,
        'show_resolved': resolved,
        'unresolved_count': Alert.objects.filter(is_resolved=False).count(),
    })


@login_required
def resolve_alert(request, pk):
    alert = get_object_or_404(Alert, pk=pk)
    from django.utils import timezone
    alert.is_resolved = True
    alert.resolved_at = timezone.now()
    alert.resolved_by = request.user
    alert.save()
    messages.success(request, "Alerte marquée comme résolue.")
    return redirect('alerts:list')
