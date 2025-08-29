# 🚀 GUIDE DE LANCEMENT - TechBot Marketplace

## ⚡ LANCEMENT RAPIDE (5 minutes)

### 1️⃣ Configuration du Token

**Créer un bot Telegram :**
```bash
# 1. Allez sur Telegram et cherchez @BotFather
# 2. Tapez /newbot et suivez les instructions
# 3. Récupérez votre token (ex: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz)
```

**Configurer l'environnement :**
```bash
# Copier le fichier de configuration
cp .env.example .env

# Éditer le fichier .env
nano .env  # ou votre éditeur préféré
```

**Dans le fichier .env, modifiez au minimum :**
```env
TELEGRAM_TOKEN=votre_token_ici
ADMIN_USER_ID=votre_user_id_telegram
```

> 💡 **Obtenir votre User ID :** Envoyez un message à @userinfobot sur Telegram

### 2️⃣ Installation des Dépendances

**Option A - Installation simple :**
```bash
pip install python-telegram-bot python-dotenv requests
```

**Option B - Installation complète :**
```bash
pip install -r requirements.txt
```

### 3️⃣ Lancement du Bot

**🎯 Version Refactorisée (Recommandée) :**
```bash
python3 marketplace_bot_refactored.py
```

**📱 Version Legacy (Toutes fonctionnalités) :**
```bash
python3 bot_mlt.py
```

### 4️⃣ Test du Bot

1. **Ouvrez Telegram**
2. **Cherchez votre bot** (nom donné à @BotFather)
3. **Tapez `/start`**
4. **Vous devriez voir le menu principal !**

---

## 🔍 DIAGNOSTIC ET DÉPANNAGE

### 🩺 Script de Diagnostic
```bash
# Vérification complète de l'environnement
python3 quick_start.py

# Test rapide de l'architecture
python3 launch_test.py

# Test de la refactorisation
python3 test_refactoring.py
```

### ❌ Problèmes Courants

**1. "ModuleNotFoundError: No module named 'telegram'"**
```bash
pip install python-telegram-bot
```

**2. "TELEGRAM_TOKEN manquant"**
```bash
# Vérifiez que .env existe et contient votre token
cat .env | grep TELEGRAM_TOKEN
```

**3. "Bot ne répond pas"**
- ✅ Vérifiez que le token est correct
- ✅ Vérifiez que le bot n'est pas déjà lancé ailleurs
- ✅ Regardez les logs : `tail -f logs/marketplace.log`

**4. "Permission denied"**
```bash
chmod +x marketplace_bot_refactored.py
python3 marketplace_bot_refactored.py
```

---

## 🎮 FONCTIONNALITÉS DISPONIBLES

### 🤖 Version Refactorisée (marketplace_bot_refactored.py)
- ✅ **Menu principal** fonctionnel
- ✅ **Navigation** entre les sections
- ✅ **Création de vendeur** (interface)
- ✅ **Parcours de catégories** (interface)
- ✅ **Architecture propre** et maintenable
- ⚠️ **Fonctionnalités limitées** (version de base)

### 🏪 Version Legacy (bot_mlt.py)
- ✅ **Toutes les fonctionnalités** complètes
- ✅ **Paiements crypto** complets
- ✅ **Upload de fichiers**
- ✅ **Panel administrateur**
- ✅ **Système de wallet**
- ❌ **Code difficile à maintenir**

---

## 🔧 DÉVELOPPEMENT

### 📝 Modifier le Bot Refactorisé

**Structure du code :**
```
app/
├── interfaces/telegram/handlers/  ← Modifiez ici pour l'interface
├── application/use_cases/         ← Logique métier ici
├── domain/entities/              ← Modèles de données
└── infrastructure/database/      ← Base de données
```

**Ajouter une nouvelle fonctionnalité :**
1. **Entité** dans `app/domain/entities/`
2. **Service** dans `app/application/use_cases/`
3. **Handler** dans `app/interfaces/telegram/handlers/`
4. **Connecter** dans `marketplace_bot_refactored.py`

### 🧪 Tests

```bash
# Tests unitaires (nécessite pytest)
make test

# Vérification qualité
make qa

# Formatage du code
make format
```

---

## 🐳 DOCKER (Optionnel)

### Lancement avec Docker
```bash
# Build de l'image
docker build -t techbot-marketplace .

# Lancement
docker run --env-file .env techbot-marketplace
```

---

## 📊 MONITORING

### 📈 Logs
```bash
# Voir les logs en temps réel
tail -f logs/marketplace.log

# Logs d'erreur uniquement
grep ERROR logs/marketplace.log
```

### 🔍 Debug
```bash
# Mode debug (plus de logs)
export LOG_LEVEL=DEBUG
python3 marketplace_bot_refactored.py
```

---

## 🆘 SUPPORT

### 📞 Aide Rapide
- **Token Telegram :** @BotFather sur Telegram
- **User ID :** @userinfobot sur Telegram  
- **Test connexion :** @my_id_bot sur Telegram

### 🐛 Problèmes
1. **Vérifiez** les logs : `logs/marketplace.log`
2. **Lancez** le diagnostic : `python3 quick_start.py`
3. **Comparez** avec la version legacy : `python3 bot_mlt.py`

### 📚 Documentation
- `README_REFACTORED.md` - Documentation technique complète
- `REFACTORING_SUMMARY.md` - Résumé des améliorations
- `pyproject.toml` - Configuration du projet

---

## 🎯 RÉCAPITULATIF

**✅ Configuration minimale :**
1. Token Telegram dans `.env`
2. Dépendances Python installées
3. Lancement : `python3 marketplace_bot_refactored.py`

**🚀 En 1 minute :**
```bash
cp .env.example .env
# Éditez .env avec votre TELEGRAM_TOKEN
pip install python-telegram-bot python-dotenv requests
python3 marketplace_bot_refactored.py
```

**🎉 Et voilà ! Votre bot marketplace est en ligne !**