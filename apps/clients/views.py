from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count, Avg
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import Client, ClientDocument
from .forms import ClientForm, ClientSearchForm, ClientDocumentForm


@login_required
def client_list(request):
    form = ClientSearchForm(request.GET)
    clients = Client.objects.all()

    if form.is_valid():
        q = form.cleaned_data.get('q')
        if q:
            clients = clients.filter(
                Q(first_name__icontains=q) | Q(last_name__icontains=q) |
                Q(national_id__icontains=q) | Q(phone__icontains=q) |
                Q(email__icontains=q)
            )
        employment = form.cleaned_data.get('employment_type')
        if employment:
            clients = clients.filter(employment_type=employment)
        city = form.cleaned_data.get('city')
        if city:
            clients = clients.filter(city__icontains=city)
        is_active = form.cleaned_data.get('is_active')
        if is_active == 'true':
            clients = clients.filter(is_active=True)
        elif is_active == 'false':
            clients = clients.filter(is_active=False)

    clients = clients.annotate(
        loans_count=Count('loans'),
        active_loans=Count('loans', filter=Q(loans__status='active'))
    ).order_by('-created_at')

    paginator = Paginator(clients, 20)
    page = paginator.get_page(request.GET.get('page'))

    context = {
        'form': form,
        'page_obj': page,
        'total_count': clients.count(),
    }
    return render(request, 'clients/list.html', context)


@login_required
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    loans = client.loans.select_related('product').order_by('-created_at')
    documents = client.documents.all()

    # Financial summary
    from apps.loans.models import Payment
    total_borrowed = loans.filter(
        status__in=['active', 'completed']
    ).aggregate(total=Sum('approved_amount'))['total'] or 0

    total_paid = Payment.objects.filter(
        loan__client=client, status='paid'
    ).aggregate(total=Sum('amount_paid'))['total'] or 0

    # Credit score info
    score_data = None
    if client.credit_score is not None:
        score_data = client.credit_score_label

    context = {
        'client': client,
        'loans': loans,
        'documents': documents,
        'total_borrowed': total_borrowed,
        'total_paid': total_paid,
        'score_data': score_data,
        'doc_form': ClientDocumentForm(),
    }
    return render(request, 'clients/detail.html', context)


@login_required
def client_create(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            # Auto-compute credit score
            try:
                from apps.scoring.ml_service import scoring_service
                result = scoring_service.score_client(client)
                from django.utils import timezone
                client.credit_score = result['score']
                client.credit_score_updated_at = timezone.now()
                client.save(update_fields=['credit_score', 'credit_score_updated_at'])
            except Exception:
                pass
            messages.success(request, f"Client {client.full_name} créé avec succès.")
            return redirect('clients:detail', pk=client.pk)
    else:
        form = ClientForm()
    return render(request, 'clients/form.html', {'form': form, 'action': 'Créer'})


@login_required
def client_edit(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, "Client mis à jour avec succès.")
            return redirect('clients:detail', pk=client.pk)
    else:
        form = ClientForm(instance=client)
    return render(request, 'clients/form.html', {
        'form': form, 'action': 'Modifier', 'client': client
    })


@login_required
def client_score(request, pk):
    """Compute/refresh credit score for a client"""
    client = get_object_or_404(Client, pk=pk)
    from apps.scoring.ml_service import scoring_service
    from django.utils import timezone

    loan_amount = request.GET.get('amount')
    loan_duration = request.GET.get('duration')

    result = scoring_service.score_client(
        client,
        loan_amount=float(loan_amount) if loan_amount else None,
        loan_duration=int(loan_duration) if loan_duration else None,
    )

    # Save to client
    client.credit_score = result['score']
    client.credit_score_updated_at = timezone.now()
    client.save(update_fields=['credit_score', 'credit_score_updated_at'])

    if request.headers.get('Accept') == 'application/json':
        return JsonResponse(result)

    return render(request, 'clients/score_detail.html', {
        'client': client,
        'result': result,
    })


@login_required
def upload_document(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        form = ClientDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.client = client
            doc.save()
            messages.success(request, "Document ajouté avec succès.")
    return redirect('clients:detail', pk=pk)
