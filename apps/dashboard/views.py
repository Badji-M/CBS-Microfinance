from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from decimal import Decimal
import json


@login_required
def dashboard(request):
    """Main dashboard with portfolio KPIs"""
    from apps.loans.models import Loan, RepaymentSchedule, Payment
    from apps.clients.models import Client

    today = timezone.now().date()
    start_of_month = today.replace(day=1)

    # =========================================================
    # Portfolio KPIs
    # =========================================================
    total_clients = Client.objects.filter(is_active=True).count()
    new_clients_month = Client.objects.filter(
        registration_date__gte=start_of_month
    ).count()

    active_loans = Loan.objects.filter(status='active')
    total_portfolio = active_loans.aggregate(
        total=Sum('approved_amount'))['total'] or Decimal('0')

    total_disbursed = Loan.objects.filter(
        status__in=['active', 'completed']
    ).aggregate(total=Sum('approved_amount'))['total'] or Decimal('0')

    total_collected = Payment.objects.filter(
        status='paid'
    ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')

    # Recovery rate
    recovery_rate = 0
    if total_disbursed > 0:
        recovery_rate = round(float(total_collected) / float(total_disbursed) * 100, 2)

    # PAR (Portfolio at Risk > 30 days)
    overdue_loans = []
    par_amount = Decimal('0')
    for loan in active_loans:
        if loan.days_past_due > 30:
            par_amount += Decimal(str(loan.outstanding_balance))
            overdue_loans.append(loan)

    par_30 = 0
    if total_portfolio > 0:
        par_30 = round(float(par_amount) / float(total_portfolio) * 100, 2)

    # Loans by status
    loan_stats = Loan.objects.values('status').annotate(count=Count('id'))
    loans_pending = Loan.objects.filter(status='pending').count()
    loans_active = active_loans.count()
    loans_completed = Loan.objects.filter(status='completed').count()
    loans_defaulted = Loan.objects.filter(status='defaulted').count()

    # Upcoming payments (next 7 days)
    upcoming_payments = RepaymentSchedule.objects.filter(
        due_date__gte=today,
        due_date__lte=today + timezone.timedelta(days=7),
        status__in=['pending', 'partial']
    ).select_related('loan', 'loan__client').order_by('due_date')[:10]

    # Overdue summary
    overdue_schedules = RepaymentSchedule.objects.filter(
        due_date__lt=today,
        status__in=['pending', 'partial']
    )
    overdue_count = overdue_schedules.count()
    overdue_amount = overdue_schedules.aggregate(
        total=Sum(F('amount_due') - F('amount_paid'))
    )['total'] or Decimal('0')

    # Monthly disbursements (last 6 months)
    monthly_data = []
    for i in range(5, -1, -1):
        month_start = (today.replace(day=1) - timezone.timedelta(days=i * 30)).replace(day=1)
        month_end = (month_start + timezone.timedelta(days=32)).replace(day=1)
        amount = Loan.objects.filter(
            disbursement_date__gte=month_start,
            disbursement_date__lt=month_end,
            status__in=['active', 'completed']
        ).aggregate(total=Sum('approved_amount'))['total'] or 0
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'amount': float(amount),
        })

    # Renewal rate (last 12 months)
    renewal_data = []
    for i in range(11, -1, -1):
        month_start = (today.replace(day=1) - timezone.timedelta(days=i * 30)).replace(day=1)
        month_end = (month_start + timezone.timedelta(days=32)).replace(day=1)
        
        # New loans in this month
        new_loans = Loan.objects.filter(
            application_date__gte=month_start,
            application_date__lt=month_end
        ).count()
        
        # Completed loans in this month (based on updated_at)
        completed_loans = Loan.objects.filter(
            status='completed',
            updated_at__gte=month_start,
            updated_at__lt=month_end
        ).count()
        
        # Renewal rate = new loans / (average of (new + completed) / 2, minimum 1)
        # If there are no completed loans, just show new loans as percentage
        if completed_loans > 0 or new_loans > 0:
            renewal_rate = (new_loans * 100) / max(completed_loans, 1)
        else:
            renewal_rate = 0
        renewal_rate = min(renewal_rate, 150)  # Cap at 150%
        
        renewal_data.append({
            'month': month_start.strftime('%b'),
            'rate': round(renewal_rate, 1),
            'new_loans': new_loans,
            'completed': completed_loans,
        })

    # Average credit score
    avg_score = Client.objects.filter(
        credit_score__isnull=False
    ).aggregate(avg=Avg('credit_score'))['avg']

    # Recent loans
    recent_loans = Loan.objects.select_related(
        'client', 'product'
    ).order_by('-created_at')[:8]

    # Alerts
    from apps.alerts.models import Alert
    active_alerts = Alert.objects.filter(
        is_resolved=False
    ).order_by('-created_at')[:5]

    context = {
        'total_clients': total_clients,
        'new_clients_month': new_clients_month,
        'total_portfolio': total_portfolio,
        'total_disbursed': total_disbursed,
        'total_collected': total_collected,
        'recovery_rate': recovery_rate,
        'par_30': par_30,
        'par_amount': par_amount,
        'loans_pending': loans_pending,
        'loans_active': loans_active,
        'loans_completed': loans_completed,
        'loans_defaulted': loans_defaulted,
        'overdue_count': overdue_count,
        'overdue_amount': overdue_amount,
        'upcoming_payments': upcoming_payments,
        'monthly_data': json.dumps(monthly_data),
        'renewal_data': json.dumps(renewal_data),
        'avg_credit_score': round(avg_score * 100, 1) if avg_score else None,
        'recent_loans': recent_loans,
        'active_alerts': active_alerts,
        'today': today,
    }
    return render(request, 'dashboard/index.html', context)


@login_required
def portfolio_report(request):
    """Detailed portfolio performance report"""
    from apps.loans.models import Loan, RepaymentSchedule
    today = timezone.now().date()

    # PAR breakdown
    par_buckets = {'1-30': 0, '31-60': 0, '61-90': 0, '90+': 0}
    par_amounts = {'1-30': 0, '31-60': 0, '61-90': 0, '90+': 0}

    for loan in Loan.objects.filter(status='active'):
        dpd = loan.days_past_due
        balance = float(loan.outstanding_balance)
        
        if dpd == 0:
            # Prêts sains — ne pas compter dans PAR
            continue
        elif 1 <= dpd <= 30:
            par_buckets['1-30'] += 1
            par_amounts['1-30'] += balance
        elif 31 <= dpd <= 60:
            par_buckets['31-60'] += 1
            par_amounts['31-60'] += balance
        elif 61 <= dpd <= 90:
            par_buckets['61-90'] += 1
            par_amounts['61-90'] += balance
        elif dpd > 90:
            par_buckets['90+'] += 1
            par_amounts['90+'] += balance

    context = {
        'par_buckets': par_buckets,
        'par_amounts': par_amounts,
        'par_chart_data': json.dumps({
            'labels': list(par_buckets.keys()),
            'counts': list(par_buckets.values()),
            'amounts': [round(v, 2) for v in par_amounts.values()],
        }),
    }
    return render(request, 'dashboard/portfolio_report.html', context)


@login_required
def api_chart_data(request):
    """API endpoint for chart data"""
    from apps.loans.models import Loan, Payment
    today = timezone.now().date()

    # Monthly collections vs disbursements
    data = []
    for i in range(11, -1, -1):
        month_start = (today.replace(day=1) - timezone.timedelta(days=i * 30)).replace(day=1)
        month_end = (month_start + timezone.timedelta(days=32)).replace(day=1)

        disbursed = Loan.objects.filter(
            disbursement_date__gte=month_start,
            disbursement_date__lt=month_end
        ).aggregate(total=Sum('approved_amount'))['total'] or 0

        collected = Payment.objects.filter(
            payment_date__gte=month_start,
            payment_date__lt=month_end,
            status='paid'
        ).aggregate(total=Sum('amount_paid'))['total'] or 0

        data.append({
            'month': month_start.strftime('%b %Y'),
            'disbursed': float(disbursed),
            'collected': float(collected),
        })

    return JsonResponse({'monthly_data': data})
