# UZEUR Marketplace Bot

Bot Telegram de marketplace pour produits numériques avec paiements crypto (NowPayments).

## 🚀 Déploiement sur Railway

### Prérequis
- Compte Railway avec PostgreSQL plugin activé
- Token Telegram Bot (via @BotFather)
- Compte NOWPayments avec API key
- Compte SMTP (Gmail recommandé)

### Étapes de déploiement

#### 1. Créer un nouveau projet Railway
```bash
# Depuis la racine du projet
railway login
railway init
```

#### 2. Ajouter PostgreSQL
Dans le dashboard Railway:
- Cliquer sur "New" → "Database" → "PostgreSQL"
- Railway va automatiquement fournir les variables d'environnement (PGHOST, PGPORT, etc.)

#### 3. Configurer les variables d'environnement
Dans Settings → Variables, ajouter:

```
TELEGRAM_BOT_TOKEN=<votre-token>
ADMIN_USER_ID=<votre-id>
ADMIN_USER_IDS=<ids-séparés-par-virgules>
NOWPAYMENTS_API_KEY=<votre-clé>
NOWPAYMENTS_IPN_SECRET=<votre-secret>
IPN_CALLBACK_URL=https://votre-domaine.railway.app/ipn/nowpayments
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=<votre-email>
SMTP_PASSWORD=<votre-mot-de-passe-app>
FROM_EMAIL=<votre-email>
```

**Note:** Les variables PostgreSQL (PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD) sont automatiquement fournies par Railway.

#### 4. Initialiser la base de données

Après le premier déploiement, exécuter dans le terminal Railway:

```bash
python3 -c "from app.core.database_init import DatabaseInitService; DatabaseInitService().init_all_tables()"
```

#### 5. Déployer
```bash
railway up
```

Le bot démarre automatiquement avec `bot_mlt.py`.

---

## 📁 Structure du projet

```
app/
├── core/               # Configuration et utilitaires
│   ├── database_init.py   # PostgreSQL schema
│   ├── email_service.py   # Service d'emails
│   ├── settings.py        # Configuration
│   └── ...
├── domain/
│   └── repositories/   # Data access layer (PostgreSQL)
├── integrations/
│   ├── telegram/
│   │   └── handlers/   # Bot handlers
│   ├── ipn_server.py   # IPN callbacks NowPayments
│   └── nowpayments_client.py
└── services/           # Business logic
```

---

## 💾 Base de données (PostgreSQL)

### Tables principales

- **users**: Utilisateurs et vendeurs
- **products**: Produits numériques (URLs object storage)
- **orders**: Commandes et paiements
- **reviews**: Avis clients
- **seller_payouts**: Paiements vendeurs
- **categories**: Catégories de produits

Voir `MIGRATION_SUMMARY.md` pour le schéma complet.

---

## 🛠️ Développement local

### Installation
```bash
# Cloner le repo
git clone <repo-url>
cd Python-bot

# Installer les dépendances
pip install -r requirements.txt

# Configurer .env (copier .env.example)
cp .env.example .env
# Éditer .env avec vos credentials
```

### Lancer le bot en local

**⚠️ Important:** En local, vous devez avoir PostgreSQL installé et configuré.

```bash
# Avec PostgreSQL local
python3 bot_mlt.py
```

---

## 📝 Logs et monitoring

Les logs sont disponibles dans Railway via:
```bash
railway logs
```

Ou localement dans `logs/marketplace.log`.

---

## 🔧 Configuration NowPayments IPN

1. Aller sur [NOWPayments Dashboard](https://account.nowpayments.io/)
2. Settings → IPN Settings
3. Ajouter votre URL IPN: `https://votre-domaine.railway.app/ipn/nowpayments`
4. Activer IPN callbacks

---

## 📧 Support

Pour toute question, consulter `CLAUDE.md` pour les instructions complètes.

---

## 📜 Licence

Propriétaire - UZEUR Marketplace 2025
