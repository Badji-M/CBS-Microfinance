from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from decimal import Decimal
import json

from .models import Loan, LoanProduct, RepaymentSchedule, Payment
from .forms import (
    LoanApplicationForm, LoanApprovalForm, LoanRejectionForm,
    PaymentForm, GuarantorForm, LoanProductForm, LoanFilterForm
)


@login_required
def loan_list(request):
    form = LoanFilterForm(request.GET)
    loans = Loan.objects.select_related('client', 'product').all()

    if form.is_valid():
        status = form.cleaned_data.get('status')
        q = form.cleaned_data.get('q')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')

        if status:
            loans = loans.filter(status=status)
        if q:
            loans = loans.filter(
                Q(loan_number__icontains=q) |
                Q(client__first_name__icontains=q) |
                Q(client__last_name__icontains=q)
            )
        if date_from:
            loans = loans.filter(application_date__gte=date_from)
        if date_to:
            loans = loans.filter(application_date__lte=date_to)

    loans = loans.order_by('-created_at')
    paginator = Paginator(loans, 20)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'loans/list.html', {
        'form': form,
        'page_obj': page,
        'total_count': loans.count(),
    })


@login_required
def loan_detail(request, pk):
    loan = get_object_or_404(Loan, pk=pk)
    schedule = loan.schedule.all()
    payments = loan.payments.all().order_by('-payment_date')
    amortization = loan.get_amortization_schedule()

    # Score info
    score_info = None
    if loan.credit_score_at_application:
        s = loan.credit_score_at_application
        if s >= 0.80:
            score_info = ('Faible risque', 'success', s)
        elif s >= 0.65:
            score_info = ('Risque modéré', 'info', s)
        elif s >= 0.50:
            score_info = ('Risque élevé', 'warning', s)
        else:
            score_info = ('Risque critique', 'danger', s)

    context = {
        'loan': loan,
        'schedule': schedule,
        'payments': payments,
        'amortization': amortization,
        'payment_form': PaymentForm(),
        'score_info': score_info,
        'today': timezone.now().date(),
    }
    return render(request, 'loans/detail.html', context)


@login_required
def loan_create(request):
    client_pk = request.GET.get('client')
    initial = {}
    if client_pk:
        initial['client'] = client_pk

    if request.method == 'POST':
        form = LoanApplicationForm(request.POST)
        guarantor_form = GuarantorForm(request.POST, prefix='guarantor')
        has_guarantor = request.POST.get('has_guarantor') == 'on'

        if form.is_valid():
            loan = form.save(commit=False)
            loan.status = 'pending'

            # Set interest rate from product
            product = loan.product
            loan.interest_rate = product.annual_interest_rate / 12
            principal = float(loan.requested_amount)
            loan.processing_fee = principal * float(product.processing_fee_rate) / 100
            loan.insurance_amount = principal * float(product.insurance_rate) / 100

            # Guarantor
            if has_guarantor and guarantor_form.is_valid():
                guarantor = guarantor_form.save()
                loan.guarantor = guarantor

            # Credit score
            try:
                from apps.scoring.ml_service import scoring_service
                result = scoring_service.score_client(
                    loan.client,
                    loan_amount=float(loan.requested_amount),
                    loan_duration=loan.duration_months
                )
                loan.credit_score_at_application = result['score']
                loan.risk_level = result['risk_level']
            except Exception:
                pass

            loan.save()

            # Create alert for pending approval
            try:
                from apps.alerts.models import Alert
                Alert.objects.create(
                    alert_type='new_application',
                    severity='info',
                    title=f"Nouvelle demande — {loan.loan_number}",
                    message=f"{loan.client.full_name} demande {float(loan.requested_amount):,.0f} FCFA",
                    loan=loan,
                    client=loan.client,
                )
            except Exception:
                pass

            messages.success(request, f"Demande de prêt {loan.loan_number} soumise avec succès.")
            return redirect('loans:detail', pk=loan.pk)
    else:
        form = LoanApplicationForm(initial=initial)
        guarantor_form = GuarantorForm(prefix='guarantor')

    return render(request, 'loans/form.html', {
        'form': form,
        'guarantor_form': guarantor_form,
        'action': 'Nouvelle demande de prêt',
    })


@login_required
def loan_approve(request, pk):
    loan = get_object_or_404(Loan, pk=pk, status='pending')

    if request.method == 'POST':
        form = LoanApprovalForm(request.POST, instance=loan)
        if form.is_valid():
            loan = form.save(commit=False)
            loan.status = 'approved'
            loan.approval_date = timezone.now().date()
            loan.approved_by = request.user
            loan.save()
            messages.success(request, f"Prêt {loan.loan_number} approuvé.")
            return redirect('loans:detail', pk=loan.pk)
    else:
        form = LoanApprovalForm(instance=loan, initial={
            'approved_amount': loan.requested_amount,
        })

    return render(request, 'loans/approve.html', {'loan': loan, 'form': form})


@login_required
def loan_reject(request, pk):
    loan = get_object_or_404(Loan, pk=pk, status='pending')

    if request.method == 'POST':
        form = LoanRejectionForm(request.POST, instance=loan)
        if form.is_valid():
            loan = form.save(commit=False)
            loan.status = 'rejected'
            loan.save()
            messages.warning(request, f"Prêt {loan.loan_number} rejeté.")
            return redirect('loans:detail', pk=loan.pk)
    else:
        form = LoanRejectionForm(instance=loan)

    return render(request, 'loans/reject.html', {'loan': loan, 'form': form})


@login_required
def loan_disburse(request, pk):
    loan = get_object_or_404(Loan, pk=pk, status='approved')

    if request.method == 'POST':
        loan.status = 'active'
        if not loan.disbursement_date:
            loan.disbursement_date = timezone.now().date()
        loan.save()
        loan.create_repayment_schedule()
        messages.success(request, f"Prêt {loan.loan_number} décaissé. Échéancier créé.")
        return redirect('loans:detail', pk=loan.pk)

    return render(request, 'loans/disburse_confirm.html', {'loan': loan})


@login_required
def record_payment(request, pk):
    loan = get_object_or_404(Loan, pk=pk, status='active')

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.loan = loan
            payment.collected_by = request.user

            # Apply payment to schedule
            amount_remaining = float(payment.amount_paid)
            pending = loan.schedule.filter(
                status__in=['pending', 'partial', 'overdue']
            ).order_by('installment_number')

            principal_paid = 0
            interest_paid = 0

            for item in pending:
                if amount_remaining <= 0:
                    break
                remaining_due = float(item.amount_due) - float(item.amount_paid) + float(item.penalty_amount)
                paid_now = min(amount_remaining, remaining_due)

                # Calculate principal/interest split
                interest_portion = float(item.interest_due) * (paid_now / float(item.amount_due))
                principal_portion = paid_now - interest_portion

                item.amount_paid = float(item.amount_paid) + paid_now
                interest_paid += interest_portion
                principal_paid += principal_portion

                if float(item.amount_paid) >= float(item.amount_due):
                    item.status = 'paid'
                    item.payment_date = payment.payment_date
                    # Calculate days late
                    if payment.payment_date > item.due_date:
                        item.days_late = (payment.payment_date - item.due_date).days
                else:
                    item.status = 'partial'

                item.save()
                amount_remaining -= paid_now
                payment.schedule_item = item

            payment.principal_paid = principal_paid
            payment.interest_paid = interest_paid
            payment.save()

            # Check if loan is fully paid
            if not loan.schedule.filter(status__in=['pending', 'partial', 'overdue']).exists():
                loan.status = 'completed'
                loan.save()
                try:
                    from apps.alerts.models import Alert
                    Alert.objects.create(
                        alert_type='loan_completed',
                        severity='info',
                        title=f"Prêt soldé — {loan.loan_number}",
                        message=f"Le prêt de {loan.client.full_name} a été intégralement remboursé.",
                        loan=loan, client=loan.client,
                    )
                except Exception:
                    pass

            messages.success(request, f"Paiement de {float(payment.amount_paid):,.0f} FCFA enregistré.")
            return redirect('loans:detail', pk=loan.pk)
    else:
        form = PaymentForm()

    # Get next due installment
    next_installment = loan.schedule.filter(
        status__in=['pending', 'partial', 'overdue']
    ).order_by('due_date').first()

    return render(request, 'loans/payment_form.html', {
        'loan': loan,
        'form': form,
        'next_installment': next_installment,
    })


@login_required
def schedule_list(request):
    """All upcoming installments"""
    today = timezone.now().date()
    schedules = RepaymentSchedule.objects.filter(
        status__in=['pending', 'partial', 'overdue']
    ).select_related('loan', 'loan__client').order_by('due_date')

    status_filter = request.GET.get('status', '')
    if status_filter == 'overdue':
        schedules = schedules.filter(due_date__lt=today)
    elif status_filter == 'upcoming':
        schedules = schedules.filter(due_date__gte=today)

    paginator = Paginator(schedules, 25)
    page = paginator.get_page(request.GET.get('page'))

    total_due = schedules.aggregate(total=Sum('amount_due'))['total'] or 0

    return render(request, 'loans/schedule_list.html', {
        'page_obj': page,
        'total_due': total_due,
        'today': today,
        'status_filter': status_filter,
    })


@login_required
def payments_list(request):
    payments = Payment.objects.select_related(
        'loan', 'loan__client', 'collected_by'
    ).order_by('-payment_date')

    paginator = Paginator(payments, 25)
    page = paginator.get_page(request.GET.get('page'))

    total = payments.aggregate(total=Sum('amount_paid'))['total'] or 0

    return render(request, 'loans/payments_list.html', {
        'page_obj': page,
        'total_payments': total,
    })


@login_required
def overdue_loans(request):
    today = timezone.now().date()
    overdue = RepaymentSchedule.objects.filter(
        due_date__lt=today,
        status__in=['pending', 'partial']
    ).select_related('loan', 'loan__client').order_by('loan', 'due_date')

    # Group by loan
    loans_overdue = {}
    for item in overdue:
        lid = item.loan.id
        if lid not in loans_overdue:
            loans_overdue[lid] = {
                'loan': item.loan,
                'items': [],
                'total_due': 0,
                'oldest_date': item.due_date,
            }
        loans_overdue[lid]['items'].append(item)
        loans_overdue[lid]['total_due'] += float(item.amount_due) - float(item.amount_paid)

    return render(request, 'loans/overdue.html', {
        'loans_overdue': loans_overdue.values(),
        'total_overdue': sum(v['total_due'] for v in loans_overdue.values()),
        'today': today,
    })


@login_required
def amortization_preview(request):
    """AJAX endpoint: preview amortization schedule"""
    try:
        amount = float(request.GET.get('amount', 0))
        duration = int(request.GET.get('duration', 12))
        rate = float(request.GET.get('rate', 2))
        amort_type = request.GET.get('type', 'constant')

        if amount <= 0 or duration <= 0:
            return JsonResponse({'error': 'Paramètres invalides'}, status=400)

        monthly_rate = rate / 100
        schedule = []

        if amort_type == 'constant':
            if monthly_rate > 0:
                monthly_payment = amount * (monthly_rate * (1 + monthly_rate) ** duration) / ((1 + monthly_rate) ** duration - 1)
            else:
                monthly_payment = amount / duration
            balance = amount
            for i in range(1, duration + 1):
                interest = balance * monthly_rate
                principal = monthly_payment - interest
                balance -= principal
                schedule.append({
                    'installment': i,
                    'payment': round(monthly_payment, 0),
                    'principal': round(principal, 0),
                    'interest': round(interest, 0),
                    'balance': round(max(balance, 0), 0),
                })
        else:
            principal_per_month = amount / duration
            balance = amount
            for i in range(1, duration + 1):
                interest = balance * monthly_rate
                payment = principal_per_month + interest
                balance -= principal_per_month
                schedule.append({
                    'installment': i,
                    'payment': round(payment, 0),
                    'principal': round(principal_per_month, 0),
                    'interest': round(interest, 0),
                    'balance': round(max(balance, 0), 0),
                })

        total_interest = sum(r['interest'] for r in schedule)
        return JsonResponse({
            'schedule': schedule,
            'total_interest': round(total_interest, 0),
            'total_repayable': round(amount + total_interest, 0),
            'first_payment': schedule[0]['payment'] if schedule else 0,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ===== LOAN PRODUCTS =====
@login_required
def product_list(request):
    products = LoanProduct.objects.annotate(loan_count=Count('loans'))
    return render(request, 'loans/product_list.html', {'products': products})


@login_required
def product_create(request):
    if request.method == 'POST':
        form = LoanProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Produit de prêt créé.")
            return redirect('loans:product_list')
    else:
        form = LoanProductForm()
    return render(request, 'loans/product_form.html', {'form': form, 'action': 'Créer'})


@login_required
def product_edit(request, pk):
    product = get_object_or_404(LoanProduct, pk=pk)
    if request.method == 'POST':
        form = LoanProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Produit mis à jour.")
            return redirect('loans:product_list')
    else:
        form = LoanProductForm(instance=product)
    return render(request, 'loans/product_form.html', {
        'form': form, 'action': 'Modifier', 'product': product
    })
