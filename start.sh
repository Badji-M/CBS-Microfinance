#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# MicroFinance Platform — Script d'initialisation et démarrage
# Usage: bash start.sh [dev|prod|docker|test]
# ═══════════════════════════════════════════════════════════════

set -e

COLOR_GREEN='\033[0;32m'
COLOR_BLUE='\033[0;34m'
COLOR_YELLOW='\033[1;33m'
COLOR_RED='\033[0;31m'
COLOR_RESET='\033[0m'

info()    { echo -e "${COLOR_BLUE}ℹ  $1${COLOR_RESET}"; }
success() { echo -e "${COLOR_GREEN}✅ $1${COLOR_RESET}"; }
warn()    { echo -e "${COLOR_YELLOW}⚠  $1${COLOR_RESET}"; }
error()   { echo -e "${COLOR_RED}❌ $1${COLOR_RESET}"; exit 1; }

MODE=${1:-dev}

echo ""
echo -e "${COLOR_BLUE}╔══════════════════════════════════════════════╗${COLOR_RESET}"
echo -e "${COLOR_BLUE}║   🏦  MicroFinance Platform — Démarrage       ║${COLOR_RESET}"
echo -e "${COLOR_BLUE}╚══════════════════════════════════════════════╝${COLOR_RESET}"
echo ""

# ── Vérifications préalables ────────────────────────────────────
check_python() {
    if ! command -v python3 &> /dev/null; then
        error "Python 3 non trouvé. Installez Python 3.10+"
    fi
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    success "Python $PYTHON_VERSION détecté"
}

check_venv() {
    if [ ! -d ".venv" ]; then
        info "Création de l'environnement virtuel..."
        python3 -m venv .venv
        success "Environnement virtuel créé"
    fi
    source .venv/bin/activate
    success "Environnement virtuel activé"
}

install_deps() {
    info "Installation des dépendances..."
    pip install -q -r requirements.txt
    success "Dépendances installées"
}

setup_env() {
    if [ ! -f ".env" ]; then
        info "Création du fichier .env..."
        cat > .env << 'EOF'
SECRET_KEY=microfinance-dev-key-change-in-production-$(openssl rand -hex 32)
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
EOF
        warn "Fichier .env créé. Modifiez SECRET_KEY pour la production!"
    fi
}

run_migrations() {
    info "Application des migrations..."
    python manage.py migrate --run-syncdb
    success "Base de données prête"
}

seed_data() {
    info "Création des données de démonstration..."
    python manage.py seed_demo --clients 30 --loans 50
    success "Données de démo créées (admin/admin123)"
}

train_ml() {
    info "Entraînement des modèles ML..."
    python manage.py shell << 'PYEOF'
from apps.scoring.ml_service import scoring_service
result = scoring_service.train_models()
if 'error' in result:
    print(f"⚠  {result['error']}")
else:
    print(f"✅ Random Forest AUC: {result['rf_auc']} | LR AUC: {result['lr_auc']} | {result['n_samples']} exemples")
PYEOF
}

collect_static() {
    info "Collecte des fichiers statiques..."
    python manage.py collectstatic --noinput -v 0
    success "Fichiers statiques collectés"
}

# ── Mode DEV ────────────────────────────────────────────────────
run_dev() {
    check_python
    check_venv
    install_deps
    setup_env
    run_migrations

    # Seed si la BDD est vide
    CLIENT_COUNT=$(python manage.py shell -c "
from apps.clients.models import Client
print(Client.objects.count())
" 2>/dev/null || echo "0")

    if [ "$CLIENT_COUNT" = "0" ]; then
        seed_data
        train_ml
    fi

    echo ""
    success "MicroFinance Platform prêt!"
    echo ""
    echo -e "  🌐 URL      : ${COLOR_GREEN}http://localhost:8000${COLOR_RESET}"
    echo -e "  👤 Admin    : ${COLOR_GREEN}admin / admin123${COLOR_RESET}"
    echo -e "  📊 Admin UI : ${COLOR_GREEN}http://localhost:8000/admin/${COLOR_RESET}"
    echo ""

    python manage.py runserver 0.0.0.0:8000
}

# ── Mode TEST ───────────────────────────────────────────────────
run_tests() {
    check_python
    check_venv
    install_deps

    info "Lancement des tests..."
    python manage.py test tests --verbosity=2

    # Coverage si disponible
    if python -c "import coverage" 2>/dev/null; then
        info "Rapport de couverture..."
        coverage run manage.py test tests
        coverage report -m --include="apps/*"
    fi
}

# ── Mode DOCKER ─────────────────────────────────────────────────
run_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker non trouvé. Installez Docker."
    fi

    info "Construction et démarrage des conteneurs..."
    docker-compose up --build -d

    info "Attente de la base de données..."
    sleep 8

    info "Migrations..."
    docker-compose exec web python manage.py migrate

    info "Données de démonstration..."
    docker-compose exec web python manage.py seed_demo

    info "Entraînement ML..."
    docker-compose exec web python manage.py shell -c "
from apps.scoring.ml_service import scoring_service
scoring_service.train_models()
print('ML OK')
"

    echo ""
    success "Stack Docker démarrée!"
    echo -e "  🌐 URL : ${COLOR_GREEN}http://localhost${COLOR_RESET}"
    echo -e "  👤 Admin : admin / admin123"
    docker-compose ps
}

# ── Dispatcher ──────────────────────────────────────────────────
case "$MODE" in
    dev)    run_dev ;;
    test)   run_tests ;;
    docker) run_docker ;;
    prod)
        check_python
        check_venv
        install_deps
        collect_static
        run_migrations
        warn "Mode production: lancez gunicorn manuellement"
        ;;
    *)
        echo "Usage: bash start.sh [dev|test|docker|prod]"
        echo ""
        echo "  dev    — Serveur de développement (défaut)"
        echo "  test   — Lance la suite de tests"
        echo "  docker — Déploiement Docker Compose"
        echo "  prod   — Prépare pour la production"
        exit 1
        ;;
esac
