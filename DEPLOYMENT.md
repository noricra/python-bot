# 🚀 GUIDE DE DÉPLOIEMENT RAILWAY

## FICHIERS PRÉPARÉS ✅

Tous les fichiers nécessaires ont été créés :
- ✅ `.gitignore` - Fichiers à exclure de Git
- ✅ `Procfile` - Commande de démarrage
- ✅ `runtime.txt` - Version Python
- ✅ `requirements.txt` - Dépendances Python
- ✅ `railway.json` - Configuration Railway
- ✅ `.env.example` - Template des variables d'environnement

---

## ÉTAPE 1 : PUSH SUR GITHUB

### 1.1 Initialiser Git (si pas déjà fait)

```bash
cd /Users/noricra/Python-bot
git init
git add .
git commit -m "Ready for Railway deployment - Beta v1.0"
```

### 1.2 Créer un repo GitHub

1. Aller sur https://github.com
2. Cliquer sur **"New repository"**
3. **Nom** : `telegram-marketplace-bot` (ou autre)
4. **Visibilité** : **PRIVÉ** ⚠️ (Important pour protéger vos secrets)
5. Ne pas initialiser avec README/LICENSE/.gitignore
6. Cliquer sur **"Create repository"**

### 1.3 Push vers GitHub

```bash
# Remplacer USERNAME par votre nom d'utilisateur GitHub
git remote add origin https://github.com/USERNAME/telegram-marketplace-bot.git
git branch -M main
git push -u origin main
```

---

## ÉTAPE 2 : CRÉER LE PROJET RAILWAY

### 2.1 Créer un compte Railway

1. Aller sur https://railway.app
2. Cliquer sur **"Start a New Project"**
3. Se connecter avec GitHub (recommandé)
4. Autoriser Railway à accéder à vos repos

### 2.2 Déployer depuis GitHub

1. Dashboard Railway → **"New Project"**
2. Sélectionner **"Deploy from GitHub repo"**
3. Choisir votre repo `telegram-marketplace-bot`
4. Railway détecte automatiquement Python et installe les dépendances
5. **Attendre la fin du build** (2-3 minutes)

---

## ÉTAPE 3 : AJOUTER POSTGRESQL

### 3.1 Créer la base de données

1. Dans votre projet Railway → Cliquer sur **"New"**
2. Sélectionner **"Database"** → **"Add PostgreSQL"**
3. Railway crée automatiquement la base et la variable **`DATABASE_URL`**
4. Votre bot détecte automatiquement cette variable ! ✅

### 3.2 Vérifier la connexion

Railway → PostgreSQL → **"Connect"** → Voir les détails :
```
Host: containers-us-west-xxx.railway.app
Port: 5432
Database: railway
User: postgres
Password: [généré automatiquement]
```

---

## ÉTAPE 4 : CONFIGURER LES VARIABLES D'ENVIRONNEMENT

### 4.1 Ajouter les variables

Railway → Votre service (bot) → **"Variables"** → Ajouter :

```env
# Telegram Bot
BOT_TOKEN=6794560459:AAGcinWevRKFqy4A6IHy9MUms1LxtAYEs3Q
ADMIN_USER_ID=5229892870

# NOWPayments
NOWPAYMENTS_API_KEY=[votre clé NOWPayments]
NOWPAYMENTS_IPN_SECRET=[votre secret IPN]

# Backblaze B2
B2_KEY_ID=[votre B2 Key ID]
B2_APPLICATION_KEY=[votre B2 App Key]
B2_BUCKET_NAME=[votre bucket name]

# Email (Gmail SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=[votre.email@gmail.com]
SMTP_PASSWORD=[mot de passe d'application Gmail]
```

### 4.2 Variables fournies automatiquement par Railway

❌ **NE PAS ajouter** (Railway les gère automatiquement) :
- `DATABASE_URL` ✅ Auto-ajouté par PostgreSQL
- `PORT` ✅ Auto-défini par Railway
- `RAILWAY_ENVIRONMENT` ✅ Auto-défini

### 4.3 Redéployer après ajout de variables

Railway redéploie automatiquement quand vous ajoutez des variables.

---

## ÉTAPE 5 : INITIALISER LA BASE DE DONNÉES

### 5.1 Récupérer l'URL PostgreSQL

Railway → PostgreSQL → **"Connect"** → Copier **"Postgres Connection URL"**

Format :
```
postgresql://postgres:PASSWORD@HOST:PORT/railway
```

### 5.2 Créer les tables

**Option A : Via psql (local)**

```bash
# Se connecter à Railway PostgreSQL
psql "postgresql://postgres:PASSWORD@HOST:PORT/railway"

# Créer les tables
\i database_init.sql

# Vérifier
\dt
```

**Option B : Copier depuis votre DB locale**

```bash
# Export de votre DB locale
pg_dump -h localhost -U noricra -d marketplace_bot > backup.sql

# Import sur Railway
psql "postgresql://postgres:PASSWORD@HOST:PORT/railway" < backup.sql
```

---

## ÉTAPE 6 : VÉRIFIER LE DÉPLOIEMENT

### 6.1 Consulter les logs

Railway → Votre service → **"Deployments"** → Dernière version → **"View Logs"**

**Logs attendus** :
```
🔌 Using DATABASE_URL for connection...
🔌 Initializing PostgreSQL connection pool (2-10 connections)
✅ PostgreSQL connection pool initialized successfully
🤖 Bot Telegram démarré avec succès
📧 Service email initialisé
💳 Service de paiement initialisé
🌐 Serveur IPN démarré sur le port 8000
```

### 6.2 Tester le bot

1. Ouvrir Telegram
2. Rechercher votre bot `@YourBotName`
3. Envoyer `/start`
4. Vérifier que le menu s'affiche correctement

---

## ÉTAPE 7 : CONFIGURER LE WEBHOOK IPN

### 7.1 Générer un domaine Railway

Railway → Votre service → **"Settings"** → **"Networking"** → **"Generate Domain"**

Vous obtenez :
```
https://telegram-marketplace-bot-production.up.railway.app
```

### 7.2 Configurer NOWPayments IPN

1. Dashboard NOWPayments → **"Settings"** → **"IPN Settings"**
2. **IPN Callback URL** :
   ```
   https://telegram-marketplace-bot-production.up.railway.app/ipn
   ```
3. **IPN Secret** : (même que dans vos variables Railway)
4. Cliquer sur **"Save"**

### 7.3 Tester l'IPN

NOWPayments Dashboard → **"API"** → **"Test IPN"**

Vérifier les logs Railway pour confirmer la réception.

---

## ÉTAPE 8 : OPTIMISATION (Recommandé)

### 8.1 Ajuster le pool de connexions

Éditer `app/main.py` (ligne où vous initialisez le pool) :

```python
# Configuration optimale pour Railway Hobby Plan
init_connection_pool(
    min_connections=2,
    max_connections=8  # Max 8 pour laisser de la marge
)
```

Commit et push :
```bash
git add app/main.py
git commit -m "Optimize connection pool for Railway"
git push
```

Railway redéploie automatiquement.

### 8.2 Configurer les alertes

Railway → Projet → **"Settings"** → **"Notifications"**
- Activer les notifications par email
- Recevoir des alertes en cas de crash

---

## MONITORING ET MAINTENANCE

### Consulter les métriques

Railway → Votre service → **"Metrics"**
- CPU Usage
- Memory Usage
- Network I/O
- Restart Count

### Consulter les logs en temps réel

```bash
# Installer Railway CLI
npm install -g @railway/cli

# Se connecter
railway login

# Voir les logs en temps réel
railway logs
```

### Redéployer manuellement

Railway → Votre service → **"Deployments"** → **"Redeploy"**

---

## TROUBLESHOOTING

### ❌ Erreur : "Connection pool not initialized"

**Cause** : `DATABASE_URL` non détectée

**Solution** :
1. Vérifier que PostgreSQL est bien ajouté au projet
2. Vérifier que les deux services sont dans le même projet
3. Redéployer le bot

### ❌ Erreur : "Too many connections"

**Cause** : Pool trop grand pour Railway Hobby (max 20)

**Solution** : Réduire `max_connections` à 8 (voir Étape 8.1)

### ❌ Erreur : "Module not found"

**Cause** : Dépendance manquante dans `requirements.txt`

**Solution** :
```bash
# Ajouter la dépendance
echo "nom-du-package==version" >> requirements.txt
git add requirements.txt
git commit -m "Add missing dependency"
git push
```

### ❌ Bot ne répond pas

**Causes possibles** :
1. Bot crashé (voir les logs)
2. Variables d'environnement manquantes
3. Base de données non initialisée

**Solution** : Consulter les logs Railway et vérifier la checklist ci-dessous

---

## CHECKLIST DE DÉPLOIEMENT ✅

Avant de considérer le déploiement terminé :

**Code et Git**
- [ ] `.gitignore` créé (`.env` exclu)
- [ ] Code pushé sur GitHub (repo privé)
- [ ] Dernières modifications commitées

**Railway**
- [ ] Projet créé et déployé depuis GitHub
- [ ] PostgreSQL ajouté au projet
- [ ] Toutes les variables d'environnement configurées
- [ ] Domaine généré

**Base de données**
- [ ] Tables créées (via database_init.sql ou backup)
- [ ] Données migrées (si applicable)
- [ ] Connexion testée

**Intégrations**
- [ ] NOWPayments IPN configuré
- [ ] Backblaze B2 configuré et testé
- [ ] Email SMTP testé

**Tests**
- [ ] `/start` fonctionne
- [ ] Navigation des menus OK
- [ ] Recherche de produits OK
- [ ] Dashboard vendeur OK
- [ ] Test d'achat complet (optionnel pour l'instant)

**Monitoring**
- [ ] Logs consultés (pas d'erreurs)
- [ ] Métriques normales (CPU < 50%, Memory < 200MB)
- [ ] Alertes configurées

---

## COMMANDES UTILES

```bash
# Voir le statut Git
git status

# Voir les logs du dernier commit
git log -1

# Push des modifications
git add .
git commit -m "Description des changements"
git push

# Voir la différence avant commit
git diff

# Créer une branche de test
git checkout -b feature/test
```

---

## SUPPORT

**En cas de problème :**
1. Consulter les logs Railway
2. Vérifier la checklist ci-dessus
3. Tester en local d'abord
4. Consulter la documentation Railway : https://docs.railway.app

---

**Déploiement terminé ! 🎉**

Votre bot Telegram est maintenant en production sur Railway !
