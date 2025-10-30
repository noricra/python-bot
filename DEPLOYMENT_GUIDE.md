# 🚀 Guide de Déploiement - Bot Marketplace Telegram

## Étape 1 : Préparer Railway

### 1.1 Créer un compte Railway
1. Allez sur https://railway.app
2. Inscrivez-vous avec GitHub
3. Vérifiez votre email

### 1.2 Créer un nouveau projet
1. Cliquez sur "New Project"
2. Choisissez "Deploy from GitHub repo"
3. Connectez votre repository GitHub `Python-bot`
4. Railway va détecter automatiquement le projet Python

### 1.3 Ajouter PostgreSQL
1. Dans votre projet Railway, cliquez sur "New"
2. Sélectionnez "Database" → "PostgreSQL"
3. Railway va créer une base de données et générer automatiquement :
   - `PGHOST`
   - `PGPORT`
   - `PGDATABASE`
   - `PGUSER`
   - `PGPASSWORD`

---

## Étape 2 : Configurer les Variables d'Environnement

### 2.1 Dans Railway, allez dans l'onglet "Variables"

Ajoutez toutes ces variables :

```bash
# Telegram Bot
TELEGRAM_TOKEN=your_telegram_bot_token_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
ADMIN_USER_ID=your_telegram_user_id_here

# NowPayments
NOWPAYMENTS_API_KEY=your_nowpayments_api_key_here
NOWPAYMENTS_IPN_SECRET=your_nowpayments_ipn_secret_here
IPN_CALLBACK_URL=https://VOTRE-DOMAINE.railway.app/ipn/nowpayments

# Backblaze B2 Storage
B2_KEY_ID=your_b2_key_id_here
B2_APPLICATION_KEY=your_b2_application_key_here
B2_BUCKET_NAME=Uzeur-bot
B2_ENDPOINT=https://s3.eu-central-003.backblazeb2.com

# SMTP Email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_email_app_password_here
FROM_EMAIL=your_email@gmail.com
ADMIN_EMAIL=ferustech@proton.me

# IPN Settings
IPN_HOST=0.0.0.0
IPN_PORT=8000

# Directories
UPLOADS_DIR=uploads
LOG_DIR=logs
```

⚠️ **IMPORTANT** : Remplacez `VOTRE-DOMAINE` dans `IPN_CALLBACK_URL` par votre URL Railway (ex: `python-bot-production-xxxx.railway.app`)

### 2.2 Variables PostgreSQL (automatiques)

Railway va ajouter automatiquement ces variables quand vous liez la base de données :
- `PGHOST`
- `PGPORT`
- `PGDATABASE`
- `PGUSER`
- `PGPASSWORD`

---

## Étape 3 : Configurer le Déploiement

### 3.1 Créer un `Procfile`

Railway détecte automatiquement Python, mais pour être sûr, créez un fichier `Procfile` à la racine :

```
web: python bot_mlt.py
```

### 3.2 Vérifier `requirements.txt`

Assurez-vous que tous les packages sont présents :

```
python-telegram-bot==20.7
psycopg2-binary==2.9.9
boto3==1.34.34
fastapi==0.104.1
uvicorn==0.24.0
python-dotenv==1.0.0
requests==2.31.0
```

---

## Étape 4 : Configurer NowPayments

### 4.1 Configurer l'IPN Callback

1. Allez sur https://account.nowpayments.io
2. Cliquez sur "Settings" → "IPN Settings"
3. Ajoutez votre URL IPN :
   ```
   https://VOTRE-DOMAINE.railway.app/ipn/nowpayments
   ```
4. Vérifiez que l'IPN Secret correspond : `your_nowpayments_ipn_secret_here`

---

## Étape 5 : Déployer sur Railway

### 5.1 Lier le Repository

1. Dans Railway, allez dans "Settings" → "Service"
2. Connectez votre repository GitHub
3. Railway va automatiquement détecter les changements et déployer

### 5.2 Premier Déploiement

1. Railway va :
   - Installer les dépendances (`pip install -r requirements.txt`)
   - Lancer le bot (`python bot_mlt.py`)
   - Initialiser la base PostgreSQL automatiquement

2. Vérifiez les logs :
   - Cliquez sur "Deployments" → "View Logs"
   - Cherchez "✅ B2 Storage Service initialized"
   - Cherchez "Bot started"

---

## Étape 6 : Tests Post-Déploiement

### 6.1 Test de Base
```
1. Envoyez /start au bot
2. Vérifiez que le menu s'affiche
```

### 6.2 Test Backblaze B2
```
1. Devenez vendeur (/vendre)
2. Ajoutez un produit avec un fichier
3. Vérifiez dans votre dashboard B2 que le fichier est uploadé
4. Achetez le produit (mode test)
5. Vérifiez que vous recevez le fichier
```

### 6.3 Test Commandes Slash
```
/achat   → Doit ouvrir le menu achat
/vendre  → Doit ouvrir le menu vendeur
/library → Doit ouvrir la bibliothèque
/stats   → Doit ouvrir le dashboard vendeur
```

### 6.4 Test Boutique Vendeur
```
1. Voir détails d'un produit
2. Cliquer "🏪 Boutique vendeur"
3. Vérifier affichage bio + tous les produits
```

### 6.5 Test Stockage Dashboard
```
1. Aller dans /stats
2. Vérifier affichage "📦 Stockage: X.X / 100 MB"
3. Vérifier barre de progression
```

### 6.6 Test IPN (Paiement Réel)
```
1. Faire un paiement test avec NowPayments
2. Vérifier que le fichier est livré automatiquement
3. Vérifier dans les logs : "✅ Formation automatically sent"
```

---

## Étape 7 : Monitoring et Logs

### 7.1 Logs Railway

Dans Railway, onglet "Deployments" → "View Logs"

Logs à surveiller :
```
✅ B2 Storage Service initialized
✅ PostgreSQL connection successful
✅ Bot started
✅ File uploaded to B2: {product_id}
✅ Formation automatically sent to user {user_id}
```

### 7.2 Logs Backblaze B2

1. Allez sur https://www.backblaze.com
2. Cliquez sur "Buckets" → "Uzeur-bot"
3. Vérifiez les fichiers uploadés dans `products/`

### 7.3 Métriques à surveiller

- **Stockage B2** : Surveillez que personne ne dépasse 100MB
- **Base PostgreSQL** : Vérifiez l'utilisation disque sur Railway
- **Logs erreurs** : Cherchez "❌" dans les logs Railway

---

## Étape 8 : Maintenance

### 8.1 Backups PostgreSQL

Railway fait des backups automatiques, mais pour être sûr :

```bash
# Backup manuel (depuis Railway CLI)
railway run pg_dump > backup.sql
```

### 8.2 Nettoyage Backblaze B2

Si un vendeur dépasse 100MB, vous pouvez nettoyer manuellement :
1. Dashboard B2 → "Uzeur-bot" → "Browse Files"
2. Cherchez `products/{seller_id}/`
3. Supprimez les vieux fichiers

### 8.3 Monitoring Stockage

Ajoutez un script pour monitorer les vendeurs qui approchent la limite :

```sql
SELECT
    seller_user_id,
    SUM(file_size_mb) as total_storage_mb
FROM products
GROUP BY seller_user_id
HAVING total_storage_mb > 90
ORDER BY total_storage_mb DESC;
```

---

## 🔥 Troubleshooting

### Problème : Bot ne démarre pas

**Solution** :
1. Vérifiez les logs Railway
2. Cherchez l'erreur exacte
3. Vérifiez que toutes les variables d'environnement sont définies

### Problème : Erreur PostgreSQL

**Solution** :
1. Vérifiez que la base PostgreSQL est liée au service
2. Vérifiez les variables `PGHOST`, `PGPORT`, etc.
3. Testez la connexion : `railway run python -c "from app.core.database_init import get_postgresql_connection; get_postgresql_connection()"`

### Problème : Fichiers B2 ne s'uploadent pas

**Solution** :
1. Vérifiez les credentials B2 dans les variables
2. Vérifiez le bucket name : `Uzeur-bot`
3. Vérifiez l'endpoint : `https://s3.eu-central-003.backblazeb2.com`
4. Testez manuellement : `railway run python -c "from app.services.b2_storage_service import B2StorageService; B2StorageService()"`

### Problème : IPN ne fonctionne pas

**Solution** :
1. Vérifiez que l'URL IPN est correcte dans NowPayments
2. Vérifiez que le port 8000 est accessible
3. Testez l'endpoint : `curl https://votre-domaine.railway.app/ipn/nowpayments`

### Problème : Emails ne partent pas

**Solution** :
1. Vérifiez SMTP credentials
2. Si Gmail, activez "App Passwords" : https://myaccount.google.com/apppasswords
3. Testez : `railway run python -c "from app.core.email_service import EmailService; EmailService().test_connection()"`

---

## 📊 Coûts Estimés

### Railway (Plan gratuit → Pro)
- **Gratuit** : 5$/mois de crédit (suffisant pour tester)
- **Pro** : 20$/mois (recommandé en production)

### Backblaze B2
- **10 GB gratuits**
- Après : $0.005/GB/mois
- Exemple : 50GB = 0.25$/mois

### NowPayments
- Commission variable selon crypto (1-2%)
- Pas de frais fixes

**Total estimé** : ~20-25$/mois en production

---

## ✅ Checklist de Déploiement

- [ ] Compte Railway créé
- [ ] PostgreSQL ajouté au projet
- [ ] Variables d'environnement configurées
- [ ] Repository GitHub lié
- [ ] Bot déployé et démarré
- [ ] Logs vérifiés (pas d'erreurs)
- [ ] Test /start fonctionne
- [ ] Test upload B2 fonctionne
- [ ] Test commandes slash fonctionnent
- [ ] Test boutique vendeur fonctionne
- [ ] Test stockage dashboard fonctionne
- [ ] IPN callback URL configuré sur NowPayments
- [ ] Test paiement réel effectué
- [ ] Monitoring activé

---

## 🎉 Félicitations !

Votre bot est maintenant déployé et fonctionnel ! 🚀

Pour toute question, consultez :
- Railway Docs : https://docs.railway.app
- Backblaze B2 Docs : https://www.backblaze.com/b2/docs/
- NowPayments API : https://documenter.getpostman.com/view/7907941/S1a32n38
