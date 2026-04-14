# 🏦 MicroFinance Platform

> Plateforme complète de gestion des prêts de microfinance avec scoring de crédit par Machine Learning, génération automatique de contrats PDF et tableau de bord temps réel.

---

## 📋 Table des matières

- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Démarrage rapide](#démarrage-rapide)
- [Fonctionnalités](#fonctionnalités)
- [API REST](#api-rest)
- [Machine Learning](#machine-learning)
- [Gestion des tâches Celery](#celery)
- [Tests](#tests)
- [Déploiement production](#déploiement-production)

---

## 🏗️ Architecture

```
microfinance/
├── config/                    # Configuration Django
│   ├── settings.py            # Paramètres (BDD, Celery, ML, PDF)
│   ├── urls.py                # Routage principal
│   ├── celery.py              # Tâches asynchrones planifiées
│   └── wsgi.py
│
├── apps/
│   ├── clients/               # Gestion des clients
│   │   ├── models.py          # Client, ClientDocument
│   │   ├── views.py           # CRUD + scoring
│   │   └── forms.py
│   │
│   ├── loans/                 # Cycle de vie des prêts
│   │   ├── models.py          # Loan, LoanProduct, RepaymentSchedule, Payment, Guarantor
│   │   ├── views.py           # Création, approbation, décaissement, paiements
│   │   ├── tasks.py           # Tâches Celery (impayés, pénalités)
│   │   └── management/
│   │       └── commands/
│   │           └── seed_demo.py   # Données de démonstration
│   │
│   ├── scoring/               # Machine Learning
│   │   ├── ml_service.py      # Random Forest + Régression Logistique
│   │   └── views.py           # Dashboard ML, entraînement, scoring batch
│   │
│   ├── dashboard/             # Tableau de bord
│   │   ├── views.py           # KPIs, PAR, taux de recouvrement
│   │   ├── api_views.py       # Endpoints REST (KPIs, export CSV)
│   │   └── templatetags/
│   │       └── dashboard_tags.py
│   │
│   ├── documents/             # Génération PDF
│   │   └── pdf_service.py     # ReportLab — contrats professionnels
│   │
│   └── alerts/                # Système d'alertes
│       ├── models.py
│       └── tasks.py           # Rappels, surveillance PAR
│
├── templates/                 # Templates HTML (Bootstrap 5)
│   ├── base/base.html         # Layout principal avec sidebar
│   ├── registration/login.html
│   ├── dashboard/
│   ├── clients/
│   ├── loans/
│   ├── scoring/
│   ├── alerts/
│   └── documents/
│
├── static/                    # Assets statiques
├── media/                     # Uploads + contrats PDF générés
│   └── contracts/             # PDFs auto-générés
├── ml_models/                 # Modèles ML sauvegardés (.pkl)
│
├── tests.py                   # Suite de tests (60+ tests)
└── requirements.txt
```

---

## ⚙️ Installation

### Prérequis

- Python 3.10+
- pip
- Redis (pour Celery — optionnel en dev)

### 1. Cloner et créer l'environnement

```bash
git clone <repo>
cd microfinance

python -m venv .venv
source .venv/bin/activate        # Linux/Mac
# .venv\Scripts\activate         # Windows
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Variables d'environnement

Créer un fichier `.env` à la racine :

```env
# Django
SECRET_KEY=votre-clé-secrète-très-longue-et-aléatoire
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Base de données (SQLite par défaut, PostgreSQL en prod)
# DATABASE_URL=postgresql://user:password@localhost:5432/microfinance

# Celery (Redis)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Chemins
ML_MODELS_PATH=/chemin/absolu/vers/ml_models
```

---

## 🚀 Démarrage rapide

```bash
# 1. Migrations
python manage.py migrate

# 2. Données de démonstration (30 clients, 50 prêts, alertes)
python manage.py seed_demo

# 3. Lancer le serveur
python manage.py runserver
```

Accès : **http://localhost:8000** — Identifiants : `admin` / `admin123`

---

## ✨ Fonctionnalités

### 👥 Gestion des clients
- Fiche client complète : données socio-démographiques, profil financier, historique
- Score de crédit ML affiché avec jauge circulaire SVG dynamique
- Upload de documents justificatifs (CNI, justificatifs de revenus...)
- Filtres : emploi, ville, statut, recherche fulltext

### 💳 Cycle de vie complet des prêts

```
Brouillon → En attente → Approuvé → Actif (décaissé) → Soldé
                  ↓
               Rejeté / Annulé / En défaut
```

- **Calcul d'échéancier** : amortissement constant (annuité fixe) ou dégressif (capital fixe)
- **Simulateur en temps réel** dans le formulaire de demande
- **Gestion des paiements** : application automatique à l'échéancier, calcul principal/intérêts
- **Suivi des impayés** : jours de retard, pénalités 2%/mois
- **Passage en défaut** automatique après 90 jours

### 🤖 Scoring ML (21 features)

**Random Forest (100 arbres) + Régression Logistique — Ensemble 60/40**

| Catégorie | Features |
|-----------|----------|
| Démographie | Âge, genre, statut matrimonial, personnes à charge |
| Emploi | Type, années d'activité, niveau d'éducation |
| Financier | Revenu mensuel, dépenses, revenu disponible, ratio DTI |
| Historique | Taux de défaut, retards moyens, nb de prêts |
| Prêt demandé | Montant, durée, ratio revenu/prêt |

```python
# Exemple d'utilisation
from apps.scoring.ml_service import scoring_service

result = scoring_service.score_client(client, loan_amount=500000, loan_duration=12)
# → {'score': 0.73, 'risk_level': 'Modéré', 'recommendation': 'Approuver avec conditions', ...}
```

### 📊 Tableau de bord

KPIs temps réel :
- **Portefeuille total** (encours actifs)
- **Taux de recouvrement** = Total collecté / Total décaissé
- **PAR 30** (Portfolio at Risk > 30 jours) avec seuil d'alerte
- Graphiques mensuel des décaissements (Chart.js)
- Répartition du portefeuille par statut (donut)
- Liste des échéances à venir (7 jours)

### 📄 Contrats PDF

Générés avec ReportLab, chaque contrat inclut :
- En-tête avec numéro de contrat sur chaque page
- Identification des parties (établissement + emprunteur + garant)
- Résumé des conditions financières
- Tableau d'amortissement complet
- Clauses contractuelles (remboursement anticipé, défaut, litiges)
- Zone de signatures

### 🔔 Alertes automatiques

| Alerte | Déclencheur | Sévérité |
|--------|-------------|----------|
| Échéance J-7 | 7 jours avant | Info |
| Échéance J-3 | 3 jours avant | Info |
| Retard 1 jour | Lendemain de la date due | Avertissement |
| PAR 30 atteint | 30 jours de retard | Critique |
| Défaut | 90 jours de retard | Critique |
| PAR > 5% | Surveillance quotidienne | Avertissement |
| PAR > 10% | Surveillance quotidienne | Critique |

---

## 🔌 API REST

Base URL : `/api/`

### Endpoints disponibles

| Méthode | URL | Description |
|---------|-----|-------------|
| GET | `/api/kpis/` | Métriques globales du portefeuille |
| GET | `/api/trend/?months=12` | Tendance mensuelle (décaissements + recouvrements) |
| GET | `/api/clients/search/?q=...` | Recherche rapide de clients |
| GET | `/api/clients/<pk>/` | Détail JSON d'un client |
| GET | `/api/loans/<pk>/` | Détail JSON d'un prêt + échéancier |
| GET | `/api/amortization/?amount=&duration=&rate=&type=` | Calcul d'échéancier |
| GET/POST | `/api/score/<pk>/` | Score ML d'un client |
| GET | `/api/export/loans.csv` | Export CSV du portefeuille |
| GET | `/api/export/clients.csv` | Export CSV des clients |
| GET | `/api/export/schedule/<pk>.csv` | Export CSV d'un échéancier |

### Exemple de réponse `/api/kpis/`

```json
{
  "status": "ok",
  "portfolio": {
    "total_clients": 45,
    "total_portfolio_fcfa": 125000000,
    "recovery_rate_pct": 87.3,
    "par_30_pct": 4.2,
    "par_amount_fcfa": 5250000
  },
  "loans_by_status": {
    "active": 32, "completed": 18, "pending": 5, "defaulted": 3
  }
}
```

---

## 🤖 Machine Learning

### Entraîner les modèles

Via l'interface : **Scoring ML → Entraîner les modèles**

Ou via l'API :
```python
from apps.scoring.ml_service import scoring_service
result = scoring_service.train_models()
# → {'rf_auc': 0.84, 'lr_auc': 0.79, 'n_samples': 450}
```

### Fallback rule-based

Si les modèles ne sont pas encore entraînés, le système utilise automatiquement un scoring basé sur des règles métier :
- Revenu disponible > seuil → +points
- Ratio DTI < 0.3 → +points
- Historique de défaut → -points
- Jours de retard moyen → -points

### Scorer en batch

```bash
# Via interface : Scoring ML → Scorer tous les clients
# Via commande :
python manage.py shell -c "
from apps.scoring.ml_service import scoring_service
from apps.clients.models import Client
from django.utils import timezone
for c in Client.objects.filter(credit_score__isnull=True):
    r = scoring_service.score_client(c)
    c.credit_score = r['score']
    c.credit_score_updated_at = timezone.now()
    c.save(update_fields=['credit_score', 'credit_score_updated_at'])
print('Done')
"
```

---

## ⏰ Celery — Tâches planifiées

```bash
# Terminal 1 — Worker
celery -A config worker --loglevel=info

# Terminal 2 — Scheduler (Beat)
celery -A config beat --loglevel=info

# Terminal 3 — Monitoring (optionnel)
celery -A config flower
```

| Tâche | Fréquence | Description |
|-------|-----------|-------------|
| `update_overdue_payments` | Toutes les heures | Détecte et marque les impayés |
| `apply_late_penalties` | Quotidien 00:30 | Calcule les pénalités de retard |
| `check_upcoming_payments` | Quotidien 08:00 | Alertes J-3 et J-7 |
| `monitor_par` | Quotidien 07:00 | Surveillance du PAR global |
| `refresh_credit_scores` | Hebdomadaire dim. 02:00 | Re-score les clients actifs |

---

## 🧪 Tests

```bash
# Tous les tests
python manage.py test tests

# Tests par catégorie
python manage.py test tests.ClientModelTest
python manage.py test tests.LoanAmortizationTest
python manage.py test tests.CreditScoringTest
python manage.py test tests.APITest
python manage.py test tests.PDFGenerationTest
python manage.py test tests.FinancialCalculationsTest

# Avec coverage
pip install coverage
coverage run manage.py test tests
coverage report -m
coverage html  # → htmlcov/index.html
```

**60+ tests unitaires et d'intégration** couvrant :
- ✅ Modèles (Client, Loan, RepaymentSchedule, Payment, Alert)
- ✅ Calculs financiers (amortissement constant et dégressif)
- ✅ Scoring ML (21 features, Random Forest, Régression Logistique)
- ✅ Vues (authentification, CRUD, filtres)
- ✅ API REST (tous les endpoints)
- ✅ Génération PDF

---

## 🚀 Déploiement production

### PostgreSQL

```env
DATABASE_URL=postgresql://microfinance:password@db:5432/microfinance_prod
```

```python
# settings.py — ajouter :
import dj_database_url
DATABASES = {'default': dj_database_url.config()}
```

### Nginx + Gunicorn

```bash
pip install gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

```nginx
# /etc/nginx/sites-available/microfinance
server {
    listen 80;
    server_name microfinance.votre-domaine.sn;

    location /static/ { root /var/www/microfinance; }
    location /media/  { root /var/www/microfinance; }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Docker Compose

```yaml
version: '3.9'
services:
  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
    volumes:
      - ./media:/app/media
      - ./ml_models:/app/ml_models
    env_file: .env
    depends_on: [db, redis]

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: microfinance
      POSTGRES_USER: microfinance
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  celery:
    build: .
    command: celery -A config worker --loglevel=info

  celery-beat:
    build: .
    command: celery -A config beat --loglevel=info

volumes:
  postgres_data:
```

### Checklist production

```bash
# 1. Collecte des fichiers statiques
python manage.py collectstatic --noinput

# 2. Migrations
python manage.py migrate

# 3. Créer le superuser
python manage.py createsuperuser

# 4. Entraîner les modèles ML
python manage.py shell -c "
from apps.scoring.ml_service import scoring_service
result = scoring_service.train_models()
print(f'RF AUC: {result[\"rf_auc\"]} | LR AUC: {result[\"lr_auc\"]}')
"

# 5. Variables d'environnement production
DEBUG=False
SECRET_KEY=<clé-longue-et-aléatoire>
ALLOWED_HOSTS=microfinance.votre-domaine.sn
```

---

## 📈 Métriques clés à surveiller

| Indicateur | Formule | Seuil d'alerte |
|------------|---------|----------------|
| **PAR 30** | Encours en retard >30j / Portefeuille total | > 5% |
| **PAR 90** | Encours en retard >90j / Portefeuille total | > 2% |
| **Taux de recouvrement** | Total collecté / Total décaissé | < 85% |
| **Taux de défaut** | Prêts en défaut / Total prêts | > 3% |
| **Score moyen** | Moyenne des scores ML | < 55% |

---

## 🛠️ Stack technique

| Composant | Technologie |
|-----------|-------------|
| Backend | Django 4.2 |
| ML | scikit-learn (Random Forest + Logistic Regression) |
| PDF | ReportLab |
| Frontend | Bootstrap 5 + Chart.js |
| Tâches async | Celery + Redis |
| BDD dev | SQLite |
| BDD prod | PostgreSQL |
| Fonts | DM Sans + Space Mono |

---

## 📄 Licence

MIT — Libre d'utilisation pour projets éducatifs et commerciaux.

---

*Développé pour le contexte de la microfinance en Afrique de l'Ouest (FCFA, Dakar, Sénégal)*
