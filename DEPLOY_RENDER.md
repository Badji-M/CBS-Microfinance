# Déploiement sur Render.com

## 📋 Prérequis
- Compte Render.com (free tier disponible)
- Code sur GitHub (BADJI-M)

---

## 🚀 Étapes de déploiement

### 1️⃣ Créer un Web Service sur Render

1. Va sur https://dashboard.render.com
2. Clique **"New" → "Web Service"**
3. **Connecte ton repo GitHub BADJI-M**
4. Sélectionne **CBS-Microfinance**

### 2️⃣ Configurer le Web Service

| Paramètre | Valeur |
|-----------|--------|
| **Name** | `cbs-microfinance` |
| **Runtime** | `Python 3.11` |
| **Build Command** | `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate` |
| **Start Command** | `gunicorn config.wsgi:application --bind 0.0.0.0:10000 --workers 4 --timeout 120` |
| **Plan** | Free (ou Starter) |

### 3️⃣ Ajouter une PostgreSQL Database

1. Dans le dashboard Render, clique **"New" → "PostgreSQL"**
2. **Name**: `microfinance-postgres`
3. **Database**: `microfinance_db`
4. **User**: `microfinance_user`
5. Copie la **Database URL** (format: `postgresql://...`)

### 4️⃣ Ajouter une Redis Cache (optionnel pour Celery)

1. Clique **"New" → "Redis"**
2. **Name**: `redis-cache`
3. Copie la **Redis URL**

### 5️⃣ Configurer les variables d'environnement

Depuis ton Web Service, onglet **"Environment":

```
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=cbs-microfinance.onrender.com
CSRF_TRUSTED_ORIGINS=https://cbs-microfinance.onrender.com
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
DATABASE_URL=postgresql://user:password@host:port/dbname
REDIS_URL=redis://default:password@host:port  (si Celery)
```

### 6️⃣ Créer le superuser après déploiement

Une fois le web service déployé, ouvre un **Shell** dans Render :

```bash
python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin123') if not User.objects.filter(username='admin').exists() else None; print('✅ Admin créé')"
```

---

## 🔗 URL de production

```
https://cbs-microfinance.onrender.com
Login: admin
Password: admin123
```

---

## ⚠️ Notes importants

- **Cold Start** : Le free tier dorme après 15 min d'inactivité. 1ère requête = ~30s
- **Database** : PostgreSQL has 90 jour limit on free PostgreSQL (il faudra ajouter un plan)
- **Redis** : Aussi avec limites free tier
- **Plan payant** : À partir de $7/month pour éviter les limitationsChanges made:
    1. Créé render.yaml
    2. Créé DEPLOY_RENDER.md avec toutes les étapes

Maintenant, je vais pusher sur GitHub (via PMBADJI pour l'instant, tu switcheras après) :
<function_calls>
<invoke name="run_in_terminal">
<parameter name="command">cd 'c:\Users\hp\OneDrive\Bureau\microfinance' ; git add render.yaml DEPLOY_RENDER.md && git commit -m "Add Render deployment configuration" && git push origin main