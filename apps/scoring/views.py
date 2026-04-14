"""
Vues du module Scoring ML
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import models
import json


@login_required
def scoring_dashboard(request):
    """Dashboard ML : état des modèles + distribution des scores."""
    from apps.clients.models import Client
    from apps.scoring.ml_service import scoring_service

    status = scoring_service.get_model_status()

    # Distribution des scores clients
    clients_scored = Client.objects.filter(credit_score__isnull=False)
    score_buckets = {
        'excellent': clients_scored.filter(credit_score__gte=0.80).count(),
        'bon':       clients_scored.filter(credit_score__gte=0.60, credit_score__lt=0.80).count(),
        'moyen':     clients_scored.filter(credit_score__gte=0.40, credit_score__lt=0.60).count(),
        'risque':    clients_scored.filter(credit_score__lt=0.40).count(),
    }

    # Scores moyens
    excellent_clients = clients_scored.filter(credit_score__gte=0.80)
    poor_clients = clients_scored.filter(credit_score__lt=0.40)
    
    avg_good_score = excellent_clients.aggregate(avg=models.Avg('credit_score'))['avg']
    avg_bad_score = poor_clients.aggregate(avg=models.Avg('credit_score'))['avg']
    
    if avg_good_score:
        avg_good_score = round(avg_good_score * 100, 1)
    if avg_bad_score:
        avg_bad_score = round(avg_bad_score * 100, 1)

    context = {
        'rf_model_exists':  status['rf_trained'],
        'lr_model_exists':  status['lr_trained'],
        'status':           status,
        'score_buckets':    score_buckets,
        'score_chart_data': json.dumps({
            'labels': ['Excellent (≥80%)', 'Bon (60-80%)', 'Moyen (40-60%)', 'Risqué (<40%)'],
            'values': list(score_buckets.values()),
            'colors': ['#2E7D32', '#1565C0', '#F9A825', '#C62828'],
        }),
        'total_scored':     clients_scored.count(),
        'total_clients':    Client.objects.count(),
        'recent_scored':    clients_scored.order_by('-credit_score_updated_at')[:10],
        'avg_good_score':   avg_good_score,
        'avg_bad_score':    avg_bad_score,
        # Métriques des modèles entraînés
        'rf_metrics': status.get('rf_metrics', {}),
        'lr_metrics': status.get('lr_metrics', {}),
    }
    return render(request, 'scoring/dashboard.html', context)


@login_required
def train_model(request):
    """Lance l'entraînement des deux modèles ML."""
    if request.method == 'POST':
        from apps.scoring.ml_service import scoring_service
        try:
            result = scoring_service.train_models()

            rf = result['rf']
            lr = result['lr']

            messages.success(
                request,
                f"✅ Modèles entraînés sur {result['n_samples']} exemples "
                f"(source : {result['source']}) — "
                f"RF : AUC={rf['auc']} | F1={rf['f1']} | Précision={rf['precision']} | Rappel={rf['recall']} — "
                f"LR : AUC={lr['auc']} | F1={lr['f1']} | Précision={lr['precision']} | Rappel={lr['recall']}"
            )
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Erreur inattendue : {e}")

    return redirect('scoring:dashboard')


@login_required
def score_client_view(request, pk):
    """
    Score un client spécifique et affiche les deux modèles séparément.
    """
    from apps.clients.models import Client
    from apps.scoring.ml_service import scoring_service, ModelNotTrainedError

    client = get_object_or_404(Client, pk=pk)

    loan_amount   = request.GET.get('amount')
    loan_duration = request.GET.get('duration')

    try:
        result = scoring_service.score_client(
            client,
            loan_amount=float(loan_amount)   if loan_amount   else None,
            loan_duration=int(loan_duration) if loan_duration else None,
        )

        # Sauvegarder le score RF comme score principal du client
        # (RF est généralement le plus fiable — mais les deux sont affichés)
        client.credit_score           = result['rf_score']
        client.credit_score_updated_at = timezone.now()
        client.save(update_fields=['credit_score', 'credit_score_updated_at'])

        error = None

    except ModelNotTrainedError as e:
        result = None
        error  = str(e)
    except Exception as e:
        result = None
        error  = f"Erreur lors du scoring : {e}"

    return render(request, 'scoring/score_result.html', {
        'client': client,
        'result': result,
        'error':  error,
    })


@login_required
def batch_score(request):
    """Score tous les clients sans score enregistré."""
    if request.method == 'POST':
        from apps.clients.models import Client
        from apps.scoring.ml_service import scoring_service, ModelNotTrainedError

        try:
            clients = Client.objects.filter(credit_score__isnull=True, is_active=True)
            count, errors = 0, 0

            for client in clients:
                try:
                    result = scoring_service.score_client(client)
                    client.credit_score            = result['rf_score']
                    client.credit_score_updated_at = timezone.now()
                    client.save(update_fields=['credit_score', 'credit_score_updated_at'])
                    count += 1
                except ModelNotTrainedError:
                    messages.error(request, "Les modèles ne sont pas entraînés. Entraînez-les d'abord.")
                    return redirect('scoring:dashboard')
                except Exception:
                    errors += 1

            msg = f"{count} clients scorés avec succès."
            if errors:
                msg += f" ({errors} erreurs ignorées)"
            messages.success(request, msg)

        except Exception as e:
            messages.error(request, f"Erreur : {e}")

    return redirect('scoring:dashboard')
