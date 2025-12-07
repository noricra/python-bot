# Quickstart Cheatsheet - Tunneling pour Telegram Mini Apps

## TL;DR - Démarrage Rapide (5 minutes)

### Option 1: Tailscale Funnel (RECOMMANDÉE)

```bash
# 1. Installer et configurer (une seule fois)
brew install tailscale
tailscale up
# Ouvrir le lien dans le navigateur pour vous authentifier

# 2. Lancer votre serveur (terminal 1)
python3 app.py

# 3. Exposer en HTTPS (terminal 2)
tailscale funnel 8000

# 4. Récupérer l'URL (affichée dans le terminal)
# https://mon-ordinateur.ts.net

# 5. Configurer dans Telegram
# @BotFather -> Manage Bot -> App web link
# https://mon-ordinateur.ts.net
```

### Option 2: localhost.run (Simple & Gratuit)

```bash
# 1. Lancer votre serveur (terminal 1)
python3 app.py

# 2. Créer le tunnel (terminal 2)
ssh -o ServerAliveInterval=60 -R 80:localhost:8000 localhost.run

# 3. Utiliser l'URL affichée dans Telegram
# https://xxxxx.lhr.rocks
```

### Option 3: ngrok (Populaire)

```bash
# 1. Installer ngrok
brew install ngrok

# 2. Créer un compte gratuit
# https://dashboard.ngrok.com/signup
# Copier le token d'auth

# 3. Configurer le token (une seule fois)
ngrok config add-authtoken YOUR_TOKEN_HERE

# 4. Lancer votre serveur (terminal 1)
python3 app.py

# 5. Exposer (terminal 2)
ngrok http 8000

# 6. Utiliser l'URL affichée dans Telegram
# https://xxxxx.ngrok.io
```

---

## Tableau de Comparaison Rapide

```
╔═══════════════════╦═════════╦═════════╦═════════╦══════════╗
║ Solution          ║ URL Fixe║ Gratuit ║ Facile  ║ Pour TMA ║
╠═══════════════════╬═════════╬═════════╬═════════╬══════════╣
║ Tailscale Funnel  ║   ✓     ║   ✓     ║  ✓✓✓   ║   ✓✓✓   ║
║ localhost.run     ║   ✗     ║   ✓     ║  ✓✓✓   ║    ✓     ║
║ ngrok             ║   ✗     ║   ✓*    ║  ✓✓    ║    ✓     ║
║ Pinggy            ║   ✗     ║  ✓ (1h) ║  ✓✓✓   ║    ✓     ║
║ Cloudflare Tunnel ║   ✓     ║   ✓     ║   ✓    ║    ✓     ║
║ Serveo            ║  Demi   ║   ✓     ║  ✓✓✓   ║    ✓     ║
║ Localtunnel       ║   ✗     ║   ✓     ║  ✓✓✓   ║    ✓     ║
╚═══════════════════╩═════════╩═════════╩═════════╩══════════╝

* = URL fixe payant ($15/mois) / gratuit = temporaire
TMA = Telegram Mini App
```

---

## Installation Dépendances (macOS)

```bash
# Homebrew (si pas installé)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Outils principaux
brew install python3 git curl jq

# Tunneling (choisir un ou plusieurs)
brew install tailscale          # Recommandé
brew install ngrok              # Populaire
brew install mkcert             # Certificats locaux

# Optionnel: Node.js
brew install node npm

# Optionnel: Frameworks Python
pip install flask fastapi uvicorn flask-cors requests
```

---

## Serveur Test Minimal

### Python (Flask)

**Fichier**: `minimal_app.py`

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({'status': 'online'})

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print(f'Webhook: {data}')
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(port=8000, debug=True)
```

```bash
pip install flask
python3 minimal_app.py
```

### Node.js (Express)

**Fichier**: `minimal_app.js`

```javascript
const express = require('express');
const app = express();

app.use(express.json());

app.get('/', (req, res) => {
    res.json({ status: 'online' });
});

app.post('/webhook', (req, res) => {
    console.log('Webhook:', req.body);
    res.json({ status: 'ok' });
});

app.listen(8000, () => {
    console.log('Server running on http://localhost:8000');
});
```

```bash
npm init -y
npm install express
node minimal_app.js
```

---

## Commandes Essentielles

### Vérifier un Port

```bash
# Voir ce qui écoute sur 8000
lsof -i :8000

# Tuer un processus sur 8000
kill -9 $(lsof -t -i :8000)
```

### Tester un Tunnel

```bash
# GET simple
curl -I https://votre-url.com

# Avec verbose
curl -vI https://votre-url.com

# POST avec données
curl -X POST https://votre-url.com/webhook \
     -H "Content-Type: application/json" \
     -d '{"test":true}'

# Ignorer erreurs SSL (self-signed)
curl -kI https://votre-url.com
```

### Configurer Telegram

```bash
# Définir le webhook
export TOKEN=YOUR_TOKEN_HERE
curl https://api.telegram.org/bot$TOKEN/setWebhook \
     -d "url=https://votre-url.com/webhook"

# Vérifier le webhook
curl https://api.telegram.org/bot$TOKEN/getWebhookInfo | jq

# Voir les mises à jour en attente
curl https://api.telegram.org/bot$TOKEN/getUpdates | jq
```

---

## Certificats HTTPS Locaux (mkcert)

```bash
# Installer
brew install mkcert

# Créer CA locale (une seule fois)
mkcert -install

# Créer certificat pour localhost
mkcert localhost 127.0.0.1

# Résultat:
# - localhost+2.pem (certificat)
# - localhost+2-key.pem (clé)

# Utiliser dans Flask
from flask import Flask
app = Flask(__name__)
app.run(
    ssl_context=('localhost+2.pem', 'localhost+2-key.pem'),
    host='localhost',
    port=8000
)
```

---

## Fichiers de Configuration Typiques

### .env (Variables d'environnement)

```bash
# .env
TELEGRAM_BOT_TOKEN=1234567890:ABCDEFGHIJKLmnopqrstuvwxyz
TELEGRAM_WEBHOOK_URL=https://mon-app.ts.net/webhook
DEBUG=True
PORT=8000
```

```python
# app.py
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.getenv('TELEGRAM_WEBHOOK_URL')
```

### .gitignore

```
# .gitignore
.env
.DS_Store
__pycache__/
*.py[cod]
.vscode/
node_modules/
venv/
*.log
localhost+*.pem
localhost+*-key.pem
ngrok_url.txt
```

---

## Scripts Rapides

### Démarrer serveur + tunnel (Tailscale)

```bash
#!/bin/bash
# startup.sh

# Terminal 1: Serveur
python3 app.py &
SERVER_PID=$!
sleep 2

# Terminal 2: Tunnel
tailscale funnel 8000

# Afficher les infos
echo "Server PID: $SERVER_PID"
echo "Tunnel actif. Appuyez Ctrl+C pour arrêter"

trap "kill $SERVER_PID" EXIT
```

```bash
chmod +x startup.sh
./startup.sh
```

### Vérifier tout d'un coup

```bash
#!/bin/bash
# check.sh

echo "✓ Serveur local:"
curl -sk https://localhost:8000 && echo " OK" || echo " ERREUR"

echo "✓ Tunnel URL (modifier):"
URL="https://mon-app.ts.net"
curl -sI $URL | head -1

echo "✓ Webhook:"
curl -sX POST $URL/webhook \
     -H "Content-Type: application/json" \
     -d '{}' && echo " OK"
```

```bash
chmod +x check.sh
./check.sh
```

---

## Environnements de Test

### Test Telegram Mini App Sans HTTPS

Utiliser l'environnement de test de Telegram:
https://docs.telegram-mini-apps.com/platform/test-environment

Accepte HTTP://localhost même sans HTTPS valide!

```bash
# Accès au test:
# 1. Ouvrir @BotFather
# 2. /myapps -> Sélectionner l'app
# 3. Test -> Ouvre l'app en mode test
```

### Test en Production (avec HTTPS)

```bash
# 1. Tunnel active (https)
tailscale funnel 8000

# 2. Configurer dans BotFather
# @BotFather -> Manage Bot -> App web link
# https://mon-app.ts.net

# 3. Tester via le lien direct
# https://t.me/BOT_USERNAME/APP_NAME
```

---

## Environnement de Développement Complet

### Structure du Projet

```
telegram-miniapp/
├── app.py                 # Serveur principal
├── requirements.txt       # Dépendances Python
├── .env.example          # Variables d'environnement
├── .gitignore
├── README.md
├── static/
│   ├── index.html        # Mini App HTML
│   ├── style.css
│   └── app.js
├── handlers/
│   └── webhook.py        # Handlers Telegram
└── logs/
    └── app.log           # Logs de l'app
```

### Startup Complet

```bash
#!/bin/bash
# dev_setup.sh

# 1. Créer environment
python3 -m venv venv
source venv/bin/activate

# 2. Installer dépendances
pip install -r requirements.txt

# 3. Charger variables d'environnement
export $(cat .env | xargs)

# 4. Lancer le serveur
python3 app.py &
APP_PID=$!

sleep 2

# 5. Activer le tunnel
echo "Démarrage du tunnel..."
tailscale funnel 8000 &
TUNNEL_PID=$!

sleep 2

# 6. Configurer Telegram
echo "Configuration du webhook..."
curl https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook \
     -d "url=https://$(hostname -s).ts.net/webhook"

echo ""
echo "✓ Tout est prêt!"
echo "Server: http://localhost:8000"
echo "Tunnel: https://$(hostname -s).ts.net"
echo ""
echo "Appuyez Ctrl+C pour arrêter"

trap "kill $APP_PID $TUNNEL_PID" EXIT
wait
```

---

## Troubleshooting Rapide

| Problème | Commande de Test | Solution |
|----------|---|---|
| Serveur ne répond pas | `curl https://localhost:8000` | `python3 app.py` |
| Tunnel ne répond pas | `curl https://votre-url.com` | Vérifier tunnel actif |
| Certificat invalide | `curl -I https://votre-url.com` | Tunnel doit avoir Let's Encrypt |
| Telegram refuse l'URL | Vérifier URL dans `getWebhookInfo` | Utiliser HTTPS, pas HTTP |
| Webhook ne reçoit rien | `curl https://api.telegram.org/bot$TOKEN/getWebhookInfo` | Vérifier URL webhook |
| Port 8000 en utilisation | `lsof -i :8000` | `kill -9 $(lsof -t -i :8000)` |

---

## Support par Framework

### Flask HTTPS

```python
app.run(
    ssl_context=('localhost+2.pem', 'localhost+2-key.pem'),
    host='localhost',
    port=8000
)
```

### FastAPI + Uvicorn

```bash
uvicorn app:app --ssl-keyfile=localhost+2-key.pem \
                 --ssl-certfile=localhost+2.pem
```

### Django

```bash
python manage.py runsslserver localhost:8000 \
    --certificate localhost+2.pem \
    --key localhost+2-key.pem
```

### Express.js

```javascript
const https = require('https');
const fs = require('fs');

const options = {
    key: fs.readFileSync('localhost+2-key.pem'),
    cert: fs.readFileSync('localhost+2.pem')
};

https.createServer(options, app).listen(8000);
```

---

## Liens Rapides

| Service | Site | Docs |
|---------|------|------|
| Tailscale | https://tailscale.com | https://tailscale.com/kb/1223/funnel |
| ngrok | https://ngrok.com | https://ngrok.com/docs |
| localhost.run | https://localhost.run | https://localhost.run/docs |
| Pinggy | https://pinggy.io | https://pinggy.io/docs |
| mkcert | https://github.com/FiloSottile/mkcert | - |
| Telegram Mini Apps | https://telegram.org | https://docs.telegram-mini-apps.com |

---

## Commande Magique (Copy-Paste)

```bash
# Installer tout d'un coup
brew install python3 tailscale mkcert

# Setup Tailscale
tailscale up

# Créer certificats
mkcert localhost 127.0.0.1

# Créer serveur minimal
cat > app.py << 'EOF'
from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({'status': 'ok'})

@app.route('/webhook', methods=['POST'])
def webhook():
    print(request.get_json())
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(port=8000, debug=True)
EOF

# Installer Flask
pip install flask

# Lancer (2 terminaux)
# Terminal 1:
python3 app.py

# Terminal 2:
tailscale funnel 8000

# Copier l'URL affichée et l'utiliser dans @BotFather
```

---

## Résumé: Les 3 Meilleures Options

### 🥇 Meilleur: Tailscale Funnel
- URL fixe gratuitement
- Super simple
- Idéal pour Telegram
- Aucune limite

**Démarrage**:
```bash
brew install tailscale
tailscale up
tailscale funnel 8000
```

### 🥈 Alternatif: localhost.run
- Plus simple possible
- Complètement gratuit
- SSH natif (zéro installation)
- URL changeable mais acceptable

**Démarrage**:
```bash
ssh -o ServerAliveInterval=60 -R 80:localhost:8000 localhost.run
```

### 🥉 Feature-Rich: ngrok
- Dashboard d'inspection
- Très populaire
- Plans payants bon marché
- Excellent support

**Démarrage**:
```bash
brew install ngrok
ngrok config add-authtoken YOUR_TOKEN
ngrok http 8000
```

---

**Dernière mise à jour**: Décembre 2025
**Plateforme**: macOS (applicable Linux avec adaptations mineures)
**Cas d'usage**: Telegram Mini Apps

Pour plus de détails, voir:
- CLOUDFLARE_TUNNEL_ALTERNATIVES.md - Comparaison complète
- SETUP_SCRIPTS.md - Scripts de configuration
- TROUBLESHOOTING_GUIDE.md - Guide de dépannage
