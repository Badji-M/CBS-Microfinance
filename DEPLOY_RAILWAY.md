# 🚂 Déploiement sur Railway

## Prérequis

- ✅ Compte GitHub (gratuit)
- ✅ Code poussé sur GitHub : https://github.com/Badji-M/CBS-Microfinance.git
- ✅ Compte Railway (création gratuite via GitHub)

## Étape 1️⃣ : Créer un compte Railway

1. Accès à https://railway.app
2. Clic sur **"Login with GitHub"**
3. Autorisez Railway à accéder à vos repos
4. ✅ Compte créé !

## Étape 2️⃣ : Créer un nouveau projet

1. Tableau de bord Railway → **New Project**
2. Sélectionnez **Deploy from GitHub repo**
3. Cherchez et sélectionnez : `CBS-Microfinance`
4. Confirmez et attendez le build initial

## Étape 3️⃣ : Ajouter les services (Plugins)

Dans le projet Railway, ajoutez les plugins :

### A. PostgreSQL
1. Click **"+ Add Service"** → **PostgreSQL**
2. Railway configure automatiquement `DATABASE_URL`
3. ✅ Base de données liée !

### B. Redis
1. Click **"+ Add Service"** → **Redis**
2. Railway configure automatiquement `REDIS_URL`
3. ✅ Cache et broker Celery liés !

## Étape 4️⃣ : Configurer les variables d'environnement

1. Dans le service **Web** :
   - Click sur **Variables**
   - Ajouter les variables (voir `.env.railway.example`) :

```
SECRET_KEY=<générer une clé sécurisée>
DEBUG=False
ALLOWED_HOSTS=yourdomain.railway.app,*.railway.app
CSRF_TRUSTED_ORIGINS=https://yourdomain.railway.app
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

2. PostgreSQL et Redis sont **auto-configurés** par Railway ✅

## Étape 5️⃣ : Générer une SECRET_KEY sécurisée

Si tu n'en as pas, exécute ceci localement :

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copie le résultat dans `SECRET_KEY` sur Railway.

## Étape 6️⃣ : Lanc le déploiement

1. Railway détecte automatiquement le `Dockerfile`
2. Build commence → Attends 5-10 minutes
3. Selon le statut : **Happy Running** = ✅ Succès !

## Étape 7️⃣ : Exécuter les migrations

Une fois le web service running :

1. Click sur le service **web**
2. Onglet **Deployments** → Click sur le dernier déployement
3. Click sur **Canvas** et recherchez le terminal
4. Exécutez :

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py shell -c "from apps.scoring.ml_service import scoring_service; scoring_service.train_models()"
```

## Étape 8️⃣ : Ajouter un domaine personnalisé (optionnel)

1. Click sur le service **web**
2. Onglet **Settings** → **Domain**
3. Ajouter votre domaine personnalisé
4. Configurer les DNS chez votre registraire

## Étape 9️⃣ : URL de votre app

Votre app sera accessible sur :
```
https://your-railway-domain.railway.app
```

Ou via votre domaine personnalisé si configuré.

## 🔥 Troubleshooting

### Service Web ne démarre pas
- **Vérifiez** les logs : `Logs` tab
- **Vérifiez** la SECRET_KEY est définie
- **Vérifiez** DATABASE_URL est créée (PostgreSQL plugin ajouté)

### Erreur de base de données
- ✅ Assurez-vous PostgreSQL plugin est ajouté
- ✅ Exécutez les migrations manuellement (voir Étape 7)

### Mauvaise configuration ALLOWED_HOSTS
- Mettez à jour depuis le dashboard Railway
- Attendez le redéploiement automatique

## 💡 Pro Tips

1. **Logs en direct** : Allez dans **Logs** pour déboguer
2. **Rollback facile** : Allez à **Deployments** et re-déployez une version précédente
3. **Preview Environments** : Railway crée des peenvs pour chaque PR automatiquement
4. **Pricing** : Chaque service utilisé = frais. PostgreSQL ~$5/mois, Redis ~$3/mois

---

**Prêt ?** Accès à https://railway.app et commence ! 🚀
