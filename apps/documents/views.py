from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404
import os


@login_required
def document_list(request):
    from apps.loans.models import Loan
    from django.conf import settings

    # List generated contracts
    contract_dir = os.path.join(settings.MEDIA_ROOT, 'contracts')
    contracts = []
    if os.path.exists(contract_dir):
        for fname in sorted(os.listdir(contract_dir), reverse=True):
            if fname.endswith('.pdf'):
                loan_num = fname.replace('contrat_', '').replace('.pdf', '')
                loan = Loan.objects.filter(loan_number=loan_num).first()
                contracts.append({
                    'filename': fname,
                    'loan': loan,
                    'path': f"contracts/{fname}",
                    'size': os.path.getsize(os.path.join(contract_dir, fname)),
                })

    return render(request, 'documents/list.html', {'contracts': contracts})


@login_required
def generate_contract(request, loan_pk):
    from apps.loans.models import Loan
    loan = get_object_or_404(Loan, pk=loan_pk)

    if loan.status not in ('approved', 'active', 'completed'):
        messages.error(request, "Le contrat ne peut être généré que pour un prêt approuvé ou actif.")
        return redirect('loans:detail', pk=loan_pk)

    try:
        from apps.documents.pdf_service import generate_loan_contract
        filepath, media_path = generate_loan_contract(loan)
        messages.success(request, f"Contrat {loan.loan_number} généré avec succès.")
    except Exception as e:
        messages.error(request, f"Erreur lors de la génération du contrat: {str(e)}")

    return redirect('documents:list')


@login_required
def download_contract(request, loan_pk):
    from apps.loans.models import Loan
    from django.conf import settings

    loan = get_object_or_404(Loan, pk=loan_pk)
    filename = f"contrat_{loan.loan_number}.pdf"
    filepath = os.path.join(settings.MEDIA_ROOT, 'contracts', filename)

    if not os.path.exists(filepath):
        # Try to generate it
        try:
            from apps.documents.pdf_service import generate_loan_contract
            filepath, _ = generate_loan_contract(loan)
        except Exception:
            raise Http404("Contrat non trouvé")

    response = FileResponse(
        open(filepath, 'rb'),
        content_type='application/pdf',
        as_attachment=True,
        filename=filename
    )
    return response
