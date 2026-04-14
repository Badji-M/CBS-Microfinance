"""
API REST pour MicroFinance Platform
Endpoints JSON pour intégration externe / dashboard dynamique
"""
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q
from decimal import Decimal
import json


def _json_ok(data, status=200):
    return JsonResponse({'status': 'ok', **data}, status=status)


def _json_err(message, status=400):
    return JsonResponse({'status': 'error', 'message': message}, status=status)


# ─────────────────────────────────────────────
# DASHBOARD KPIs
# ─────────────────────────────────────────────

@login_required
@require_GET
def api_dashboard_kpis(request):
    """GET /api/kpis/ — métriques globales du portefeuille"""
    from apps.loans.models import Loan, Payment
    from apps.clients.models import Client

    today = timezone.now().date()
    active = Loan.objects.filter(status='active')

    total_portfolio = float(
        active.aggregate(t=Sum('approved_amount'))['t'] or 0
    )
    total_clients = Client.objects.filter(is_active=True).count()
    total_collected = float(
        Payment.objects.filter(status='paid')
        .aggregate(t=Sum('amount_paid'))['t'] or 0
    )
    total_disbursed = float(
        Loan.objects.filter(status__in=['active', 'completed'])
        .aggregate(t=Sum('approved_amount'))['t'] or 0
    )

    # PAR 30
    par_amount = sum(l.par_contribution for l in active)
    par_30 = round(par_amount / total_portfolio * 100, 2) if total_portfolio else 0

    recovery_rate = round(total_collected / total_disbursed * 100, 2) if total_disbursed else 0

    loans_by_status = dict(
        Loan.objects.values('status')
        .annotate(n=Count('id'))
        .values_list('status', 'n')
    )

    return _json_ok({
        'portfolio': {
            'total_clients': total_clients,
            'total_portfolio_fcfa': total_portfolio,
            'total_disbursed_fcfa': total_disbursed,
            'total_collected_fcfa': total_collected,
            'recovery_rate_pct': recovery_rate,
            'par_30_pct': par_30,
            'par_amount_fcfa': par_amount,
        },
        'loans_by_status': loans_by_status,
        'generated_at': timezone.now().isoformat(),
    })


@login_required
@require_GET
def api_monthly_trend(request):
    """GET /api/trend/?months=12 — tendance mensuelle des décaissements et recouvrements"""
    from apps.loans.models import Loan, Payment

    months = min(int(request.GET.get('months', 12)), 24)
    today = timezone.now().date()
    data = []

    for i in range(months - 1, -1, -1):
        # Premier jour du mois i mois en arrière
        m_start = (today.replace(day=1) - timezone.timedelta(days=i * 30)).replace(day=1)
        m_end = (m_start.replace(day=28) + timezone.timedelta(days=4)).replace(day=1)

        disbursed = float(
            Loan.objects.filter(
                disbursement_date__gte=m_start,
                disbursement_date__lt=m_end,
            ).aggregate(t=Sum('approved_amount'))['t'] or 0
        )
        collected = float(
            Payment.objects.filter(
                payment_date__gte=m_start,
                payment_date__lt=m_end,
                status='paid',
            ).aggregate(t=Sum('amount_paid'))['t'] or 0
        )
        new_clients = int(
            __import__('apps.clients.models', fromlist=['Client'])
            .Client.objects.filter(
                registration_date__gte=m_start,
                registration_date__lt=m_end,
            ).count()
        )

        data.append({
            'month': m_start.strftime('%Y-%m'),
            'label': m_start.strftime('%b %Y'),
            'disbursed_fcfa': disbursed,
            'collected_fcfa': collected,
            'new_clients': new_clients,
        })

    return _json_ok({'months': data})


# ─────────────────────────────────────────────
# CLIENTS API
# ─────────────────────────────────────────────

@login_required
@require_GET
def api_client_search(request):
    """GET /api/clients/search/?q=... — recherche rapide de clients"""
    from apps.clients.models import Client

    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return _json_ok({'results': []})

    clients = Client.objects.filter(
        Q(first_name__icontains=q) |
        Q(last_name__icontains=q) |
        Q(national_id__icontains=q) |
        Q(phone__icontains=q)
    ).filter(is_active=True)[:10]

    results = [{
        'id': c.pk,
        'full_name': c.full_name,
        'national_id': c.national_id,
        'phone': c.phone,
        'monthly_income': float(c.monthly_income),
        'credit_score': round(c.credit_score * 100, 1) if c.credit_score else None,
        'active_loans': c.active_loan_count,
        'url': f'/clients/{c.pk}/',
    } for c in clients]

    return _json_ok({'results': results, 'count': len(results)})


@login_required
@require_GET
def api_client_detail(request, pk):
    """GET /api/clients/<pk>/ — détail JSON d'un client"""
    from apps.clients.models import Client
    from django.shortcuts import get_object_or_404

    c = get_object_or_404(Client, pk=pk)
    label, color = c.credit_score_label

    return _json_ok({
        'client': {
            'id': c.pk,
            'full_name': c.full_name,
            'national_id': c.national_id,
            'age': c.age,
            'phone': c.phone,
            'city': c.city,
            'employment_type': c.get_employment_type_display(),
            'monthly_income': float(c.monthly_income),
            'monthly_expenses': float(c.monthly_expenses),
            'disposable_income': c.disposable_income,
            'debt_to_income_ratio': round(c.debt_to_income_ratio, 4),
            'has_bank_account': c.has_bank_account,
            'credit_score': round(c.credit_score * 100, 1) if c.credit_score else None,
            'credit_score_label': label,
            'credit_score_color': color,
            'loan_count': c.loan_count,
            'active_loan_count': c.active_loan_count,
        }
    })


# ─────────────────────────────────────────────
# LOANS API
# ─────────────────────────────────────────────

@login_required
@require_GET
def api_loan_detail(request, pk):
    """GET /api/loans/<pk>/ — détail JSON d'un prêt"""
    from apps.loans.models import Loan
    from django.shortcuts import get_object_or_404

    loan = get_object_or_404(Loan, pk=pk)
    schedule = [
        {
            'installment': s.installment_number,
            'due_date': s.due_date.isoformat(),
            'amount_due': float(s.amount_due),
            'principal_due': float(s.principal_due),
            'interest_due': float(s.interest_due),
            'amount_paid': float(s.amount_paid),
            'balance_after': float(s.balance_after),
            'status': s.status,
            'days_late': s.days_late,
        }
        for s in loan.schedule.all().order_by('installment_number')
    ]

    payments = [
        {
            'date': p.payment_date.isoformat(),
            'amount': float(p.amount_paid),
            'method': p.get_payment_method_display(),
            'reference': p.reference,
        }
        for p in loan.payments.all().order_by('-payment_date')
    ]

    return _json_ok({
        'loan': {
            'loan_number': loan.loan_number,
            'client': loan.client.full_name,
            'product': loan.product.name,
            'principal': float(loan.principal),
            'duration_months': loan.duration_months,
            'interest_rate_monthly': float(loan.interest_rate),
            'status': loan.status,
            'status_display': loan.get_status_display(),
            'total_interest': loan.total_interest,
            'total_paid': loan.total_paid,
            'outstanding_balance': loan.outstanding_balance,
            'recovery_rate': round(loan.recovery_rate, 2),
            'days_past_due': loan.days_past_due,
            'credit_score': round(loan.credit_score_at_application * 100, 1) if loan.credit_score_at_application else None,
            'disbursement_date': loan.disbursement_date.isoformat() if loan.disbursement_date else None,
            'maturity_date': loan.maturity_date.isoformat() if loan.maturity_date else None,
        },
        'schedule': schedule,
        'payments': payments,
    })


@login_required
@require_GET
def api_amortization(request):
    """
    GET /api/amortization/?amount=&duration=&rate=&type=
    Calcul d'échéancier côté serveur (utilisé par le simulateur)
    """
    try:
        amount = float(request.GET.get('amount', 0))
        duration = int(request.GET.get('duration', 12))
        rate_monthly = float(request.GET.get('rate', 2)) / 100  # En %
        amort_type = request.GET.get('type', 'constant')

        if amount <= 0 or duration <= 0:
            return _json_err('Paramètres invalides')

        schedule = []
        balance = amount

        if amort_type == 'constant':
            if rate_monthly > 0:
                monthly = amount * (rate_monthly * (1 + rate_monthly) ** duration) / ((1 + rate_monthly) ** duration - 1)
            else:
                monthly = amount / duration

            for i in range(1, duration + 1):
                interest = balance * rate_monthly
                principal = monthly - interest
                balance = max(balance - principal, 0)
                schedule.append({
                    'n': i,
                    'payment': round(monthly, 2),
                    'principal': round(principal, 2),
                    'interest': round(interest, 2),
                    'balance': round(balance, 2),
                })
        else:
            principal_month = amount / duration
            for i in range(1, duration + 1):
                interest = balance * rate_monthly
                payment = principal_month + interest
                balance = max(balance - principal_month, 0)
                schedule.append({
                    'n': i,
                    'payment': round(payment, 2),
                    'principal': round(principal_month, 2),
                    'interest': round(interest, 2),
                    'balance': round(balance, 2),
                })

        total_interest = sum(r['interest'] for r in schedule)
        return _json_ok({
            'schedule': schedule,
            'summary': {
                'principal': amount,
                'total_interest': round(total_interest, 2),
                'total_repayable': round(amount + total_interest, 2),
                'first_payment': schedule[0]['payment'] if schedule else 0,
                'last_payment': schedule[-1]['payment'] if schedule else 0,
            }
        })
    except (ValueError, ZeroDivisionError) as e:
        return _json_err(str(e))


# ─────────────────────────────────────────────
# SCORING API
# ─────────────────────────────────────────────

@login_required
def api_score_client(request, pk):
    """
    GET  /api/score/<pk>/           — score avec paramètres par défaut
    GET  /api/score/<pk>/?amount=&duration=  — score pour montant/durée spécifiques
    POST /api/score/<pk>/           — idem + sauvegarde
    """
    from apps.clients.models import Client
    from apps.scoring.ml_service import scoring_service
    from django.shortcuts import get_object_or_404

    client = get_object_or_404(Client, pk=pk)

    amount = request.GET.get('amount') or request.POST.get('amount')
    duration = request.GET.get('duration') or request.POST.get('duration')

    result = scoring_service.score_client(
        client,
        loan_amount=float(amount) if amount else None,
        loan_duration=int(duration) if duration else None,
    )

    if request.method == 'POST':
        client.credit_score = result['score']
        client.credit_score_updated_at = timezone.now()
        client.save(update_fields=['credit_score', 'credit_score_updated_at'])

    return _json_ok({
        'client_id': pk,
        'client_name': client.full_name,
        'score': result['score'],
        'score_pct': result['score_percentage'],
        'risk_level': result['risk_level'],
        'recommendation': result['recommendation'],
        'rf_score': result.get('rf_score'),
        'lr_score': result.get('lr_score'),
        'top_features': dict(list(result.get('feature_importance', {}).items())[:5]),
    })


# ─────────────────────────────────────────────
# EXPORT API
# ─────────────────────────────────────────────

@login_required
@require_GET
def api_export_loans_csv(request):
    """GET /api/export/loans.csv — export CSV du portefeuille"""
    import csv
    from django.http import HttpResponse
    from apps.loans.models import Loan

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="portefeuille_prets.csv"'
    response.write('\ufeff')  # BOM UTF-8 pour Excel

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'N° Prêt', 'Client', 'Téléphone', 'Produit',
        'Montant approuvé (FCFA)', 'Durée (mois)', 'Taux mensuel (%)',
        'Statut', 'Date demande', 'Date décaissement', 'Date échéance finale',
        'Score crédit (%)', 'Niveau risque',
        'Total payé (FCFA)', 'Solde restant (FCFA)', 'Taux recouvrement (%)',
        'Jours de retard',
    ])

    status_filter = request.GET.get('status', '')
    loans = Loan.objects.select_related('client', 'product').all()
    if status_filter:
        loans = loans.filter(status=status_filter)

    for loan in loans.order_by('-application_date'):
        writer.writerow([
            loan.loan_number,
            loan.client.full_name,
            loan.client.phone,
            loan.product.name,
            float(loan.principal),
            loan.duration_months,
            float(loan.interest_rate),
            loan.get_status_display(),
            loan.application_date.strftime('%d/%m/%Y'),
            loan.disbursement_date.strftime('%d/%m/%Y') if loan.disbursement_date else '',
            loan.maturity_date.strftime('%d/%m/%Y') if loan.maturity_date else '',
            round(loan.credit_score_at_application * 100, 1) if loan.credit_score_at_application else '',
            loan.risk_level,
            round(loan.total_paid, 2),
            round(loan.outstanding_balance, 2),
            round(loan.recovery_rate, 2),
            loan.days_past_due,
        ])

    return response


@login_required
@require_GET
def api_export_clients_csv(request):
    """GET /api/export/clients.csv — export CSV des clients"""
    import csv
    from django.http import HttpResponse
    from apps.clients.models import Client

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="clients_microfinance.csv"'
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'ID', 'Nom complet', 'CNI', 'Date naissance', 'Âge', 'Genre',
        'Téléphone', 'Email', 'Ville',
        'Type emploi', 'Années activité', 'Niveau éducation',
        'Revenus mensuels (FCFA)', 'Dépenses mensuelles (FCFA)',
        'Revenu disponible (FCFA)', 'Ratio dette/revenu',
        'Autres dettes (FCFA)', 'Compte bancaire',
        'Score crédit (%)', 'Nb prêts total', 'Nb prêts actifs',
        'Date enregistrement', 'Statut',
    ])

    for c in Client.objects.all().order_by('-registration_date'):
        writer.writerow([
            c.pk, c.full_name, c.national_id,
            c.date_of_birth.strftime('%d/%m/%Y'), c.age,
            c.get_gender_display(),
            c.phone, c.email or '', c.city,
            c.get_employment_type_display(), c.years_employed,
            c.get_education_level_display(),
            float(c.monthly_income), float(c.monthly_expenses),
            round(c.disposable_income, 2),
            round(c.debt_to_income_ratio, 4),
            float(c.other_loan_outstanding),
            'Oui' if c.has_bank_account else 'Non',
            round(c.credit_score * 100, 1) if c.credit_score else '',
            c.loan_count, c.active_loan_count,
            c.registration_date.strftime('%d/%m/%Y'),
            'Actif' if c.is_active else 'Inactif',
        ])

    return response


@login_required
@require_GET
def api_export_schedule_csv(request, loan_pk):
    """GET /api/export/schedule/<loan_pk>.csv — export CSV d'un échéancier"""
    import csv
    from django.http import HttpResponse
    from apps.loans.models import Loan
    from django.shortcuts import get_object_or_404

    loan = get_object_or_404(Loan, pk=loan_pk)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="echeancier_{loan.loan_number}.csv"'
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'N° Échéance', 'Date échéance', 'Mensualité (FCFA)',
        'Principal (FCFA)', 'Intérêt (FCFA)', 'Solde restant (FCFA)',
        'Montant payé (FCFA)', 'Date paiement', 'Jours retard',
        'Pénalité (FCFA)', 'Statut',
    ])

    for item in loan.schedule.all().order_by('installment_number'):
        writer.writerow([
            item.installment_number,
            item.due_date.strftime('%d/%m/%Y'),
            float(item.amount_due),
            float(item.principal_due),
            float(item.interest_due),
            float(item.balance_after),
            float(item.amount_paid),
            item.payment_date.strftime('%d/%m/%Y') if item.payment_date else '',
            item.days_late,
            float(item.penalty_amount),
            item.get_status_display(),
        ])

    # Total row
    writer.writerow([
        'TOTAL', '',
        round(loan.total_amount_due, 2),
        float(loan.principal),
        round(loan.total_interest, 2),
        '', round(loan.total_paid, 2), '', '', '', '',
    ])

    return response
