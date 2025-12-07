# Scripts de Configuration Pratiques

## Table des matières
1. [Scripts Shell pour Tunneling](#scripts-shell)
2. [Serveurs Python HTTPS](#serveurs-python)
3. [Serveurs Node.js HTTPS](#serveurs-nodejs)
4. [Configuration Telegram Bot](#telegram-bot)
5. [Scripts Automatisés](#scripts-automatisés)

---

## Scripts Shell pour Tunneling

### 1. ngrok - Launcher avec Sauvegarde d'URL

**Fichier**: `start_ngrok.sh`

```bash
#!/bin/bash

# Configuration
PORT=8000
OUTPUT_FILE="ngrok_url.txt"
LOG_FILE="ngrok.log"

echo "Démarrage de ngrok sur le port $PORT..."

# Lancer ngrok et sauvegarder l'URL
ngrok http $PORT > $LOG_FILE 2>&1 &
NGROK_PID=$!

# Attendre que ngrok démarre et récupère l'URL
sleep 3

# Récupérer l'URL depuis l'API de ngrok
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url')

if [ -z "$NGROK_URL" ] || [ "$NGROK_URL" = "null" ]; then
    echo "❌ Erreur: Impossible de récupérer l'URL ngrok"
    kill $NGROK_PID
    exit 1
fi

echo "✓ ngrok active!"
echo "URL HTTPS: $NGROK_URL"
echo "$NGROK_URL" > $OUTPUT_FILE
echo "URL sauvegardée dans: $OUTPUT_FILE"

# Afficher le tableau de bord
echo ""
echo "Dashboard ngrok: http://localhost:4040"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter"

wait $NGROK_PID
```

**Utilisation**:
```bash
chmod +x start_ngrok.sh
./start_ngrok.sh

# Récupérer l'URL dans un autre terminal
cat ngrok_url.txt
```

---

### 2. localhost.run - Tunnel Persistant

**Fichier**: `start_localhost_run.sh`

```bash
#!/bin/bash

# Configuration
PORT=8000
KEEPALIVE_INTERVAL=60
OUTPUT_FILE="localhost_run_url.txt"

echo "Connexion à localhost.run sur le port $PORT..."
echo "Tips: Appuyez sur Ctrl+C pour arrêter"

# Lancer le tunnel avec keepalive
ssh -o ServerAliveInterval=$KEEPALIVE_INTERVAL \
    -o ConnectTimeout=10 \
    -R 80:localhost:$PORT \
    localhost.run 2>&1 | tee localhost_run.log | while read line; do

    # Extraire l'URL si elle est affichée
    if [[ $line =~ https://.*\.lhr\.rocks ]]; then
        URL=$(echo "$line" | grep -oE 'https://[^[:space:]]+')
        echo "$URL" > $OUTPUT_FILE
        echo "✓ URL sauvegardée: $URL"
    fi

    echo "$line"
done
```

**Utilisation**:
```bash
chmod +x start_localhost_run.sh
./start_localhost_run.sh
```

---

### 3. Tailscale Funnel - Configuration Complète

**Fichier**: `setup_tailscale_funnel.sh`

```bash
#!/bin/bash

set -e

PORT=8000

echo "=== Configuration Tailscale Funnel ==="
echo ""

# 1. Vérifier si Tailscale est installé
if ! command -v tailscale &> /dev/null; then
    echo "Installation de Tailscale..."
    brew install tailscale
fi

# 2. Vérifier si connecté
if ! tailscale status > /dev/null 2>&1; then
    echo "❌ Tailscale n'est pas connecté"
    echo "Veuillez exécuter: tailscale up"
    exit 1
fi

echo "✓ Tailscale connecté"
TAILSCALE_NAME=$(tailscale status | grep -E "^\w+" | head -1 | awk '{print $1}')
echo "Appareil: $TAILSCALE_NAME"
echo ""

# 3. Vérifier MagicDNS
echo "Vérification de MagicDNS..."
MAGIC_DNS=$(tailscale status | grep -i "magicDNS" || echo "")
if [ -z "$MAGIC_DNS" ]; then
    echo "⚠️  MagicDNS ne semble pas activé"
    echo "Activez-le à: https://login.tailscale.com/admin/dns"
fi

# 4. Activer Funnel
echo ""
echo "Activation de Funnel sur le port $PORT..."
echo ""

# Arrêter les anciens funnels
tailscale funnel reset 2>/dev/null || true

# Démarrer le nouveau funnel
if tailscale funnel $PORT; then
    echo ""
    echo "✓ Funnel activé avec succès!"
    echo ""
    echo "Votre application est accessible à:"
    echo "https://${TAILSCALE_NAME}.ts.net"
    echo ""
    echo "Utilisez cette URL dans BotFather pour votre Mini App Telegram"
    echo ""
    echo "Appuyez sur Ctrl+C pour arrêter le funnel"
    echo ""
else
    echo "❌ Erreur lors de l'activation de Funnel"
    exit 1
fi

# Garder la session active
tail -f /dev/null
```

**Utilisation**:
```bash
chmod +x setup_tailscale_funnel.sh
./setup_tailscale_funnel.sh
```

---

### 4. Pinggy - Tunnel SSH Persistant

**Fichier**: `start_pinggy.sh`

```bash
#!/bin/bash

PORT=8000
OUTPUT_FILE="pinggy_url.txt"

echo "Démarrage du tunnel Pinggy..."
echo "Timeout: 60 minutes (gratuit)"
echo ""

# Lancer le tunnel Pinggy
ssh -p 443 \
    -o ServerAliveInterval=60 \
    -o ConnectTimeout=10 \
    -R0:localhost:$PORT \
    qr@free.pinggy.io 2>&1 | tee pinggy.log | while read line; do

    # Extraire l'URL
    if [[ $line =~ https://.*\.pinggy\.link ]]; then
        URL=$(echo "$line" | grep -oE 'https://[^[:space:]]+')
        echo "$URL" > $OUTPUT_FILE
        echo "✓ URL: $URL"
    fi

    echo "$line"
done

echo ""
echo "⚠️  Tunnel Pinggy fermé (timeout 60 min atteint)"
```

**Utilisation**:
```bash
chmod +x start_pinggy.sh
./start_pinggy.sh
```

---

### 5. Script Multi-Tunnels (Comparer les Services)

**Fichier**: `compare_tunnels.sh`

```bash
#!/bin/bash

PORT=8000

echo "╔════════════════════════════════════════════════════════╗"
echo "║  Comparateur de Tunneling Services pour localhost:$PORT║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Fonction pour tester un tunnel
test_tunnel() {
    local service=$1
    local command=$2
    local description=$3

    echo "---"
    echo "Service: $service"
    echo "Description: $description"
    echo "Commande: $command"
    echo ""
}

# ngrok
test_tunnel "ngrok" \
    "ngrok http $PORT" \
    "URL temporaire (gratuit), fixe (payant)"

# localhost.run
test_tunnel "localhost.run" \
    "ssh -R 80:localhost:$PORT localhost.run" \
    "URL temporaire (gratuit), fixe avec domaine (payant)"

# Tailscale Funnel
test_tunnel "Tailscale Funnel" \
    "tailscale funnel $PORT" \
    "URL fixe (gratuit), HTTPS obligatoire"

# Pinggy
test_tunnel "Pinggy" \
    "ssh -p 443 -R0:localhost:$PORT qr@free.pinggy.io" \
    "URL temporaire (gratuit), timeout 60 min"

# Localtunnel
test_tunnel "Localtunnel" \
    "lt --port $PORT" \
    "URL temporaire, serveur public partagé"

# Serveo
test_tunnel "Serveo" \
    "ssh -R 80:localhost:$PORT serveo.net" \
    "URL semi-fixe avec sous-domaine (gratuit)"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "RECOMMANDATION POUR TELEGRAM MINI APP:"
echo "✓ Tailscale Funnel (URL fixe gratuit)"
echo "✓ localhost.run (simple, gratuit mais URL temporaire)"
echo "═══════════════════════════════════════════════════════"
```

**Utilisation**:
```bash
chmod +x compare_tunnels.sh
./compare_tunnels.sh
```

---

### 6. Script de Startup Automatique

**Fichier**: `auto_tunnel.sh`

```bash
#!/bin/bash

# Configuration
PORT=8000
TUNNEL_SERVICE="tailscale"  # Options: tailscale, ngrok, localhost_run, pinggy
SERVER_SCRIPT="app.py"  # Votre script serveur

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERREUR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[AVERTISSEMENT]${NC} $1"
}

# 1. Vérifier que le serveur n'est pas déjà en cours d'exécution
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    log_warn "Le port $PORT est déjà en utilisation"
    read -p "Continuer quand même? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 2. Lancer le serveur en background
log_info "Démarrage du serveur $SERVER_SCRIPT..."
python3 "$SERVER_SCRIPT" &
SERVER_PID=$!

# Attendre que le serveur démarre
sleep 2

# 3. Vérifier que le serveur écoute
if ! lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null; then
    log_error "Le serveur n'écoute pas sur le port $PORT"
    kill $SERVER_PID
    exit 1
fi

log_info "Serveur en cours d'exécution (PID: $SERVER_PID)"

# 4. Démarrer le tunnel
log_info "Démarrage du tunnel $TUNNEL_SERVICE..."
echo ""

case $TUNNEL_SERVICE in
    tailscale)
        log_info "URL: https://\$(hostname -s).ts.net"
        tailscale funnel $PORT
        ;;
    ngrok)
        log_info "Récupération de l'URL..."
        ngrok http $PORT
        ;;
    localhost_run)
        ssh -o ServerAliveInterval=60 -R 80:localhost:$PORT localhost.run
        ;;
    pinggy)
        ssh -p 443 -o ServerAliveInterval=60 -R0:localhost:$PORT qr@free.pinggy.io
        ;;
    *)
        log_error "Service $TUNNEL_SERVICE non reconnu"
        kill $SERVER_PID
        exit 1
        ;;
esac

# Nettoyage en cas d'interruption
trap "log_info 'Arrêt du serveur...' && kill $SERVER_PID" EXIT
```

**Utilisation**:
```bash
chmod +x auto_tunnel.sh
TUNNEL_SERVICE=tailscale ./auto_tunnel.sh
```

---

## Serveurs Python HTTPS

### 1. Serveur Basique avec mkcert

**Fichier**: `server_basic_https.py`

```python
#!/usr/bin/env python3

import http.server
import ssl
import os
import sys

PORT = 8000

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            html = b"""
            <html>
                <head><title>Local HTTPS Test</title></head>
                <body>
                    <h1>Serveur HTTPS Local</h1>
                    <p>Fonctionnant sur https://localhost:8000</p>
                    <p>Timestamp: """ + str(os.popen('date').read()).encode() + b"""</p>
                </body>
            </html>
            """
            self.wfile.write(html)
        else:
            super().do_GET()

def main():
    # Créer le serveur
    server = http.server.HTTPServer(('localhost', PORT), RequestHandler)

    # Configurer SSL avec les certificats mkcert
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    cert_file = 'localhost+2.pem'
    key_file = 'localhost+2-key.pem'

    # Vérifier que les certificats existent
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        print(f"❌ Erreur: Certificats non trouvés")
        print(f"Créez-les avec: mkcert localhost 127.0.0.1")
        sys.exit(1)

    context.load_cert_chain(certfile=cert_file, keyfile=key_file)
    server.socket = context.wrap_socket(server.socket, server_side=True)

    print(f"✓ Serveur HTTPS démarré")
    print(f"🔗 https://localhost:{PORT}")
    print(f"❌ Appuyez sur Ctrl+C pour arrêter")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n✓ Serveur arrêté")
        sys.exit(0)

if __name__ == '__main__':
    main()
```

**Utilisation**:
```bash
# Créer les certificats (une seule fois)
mkcert localhost 127.0.0.1

# Lancer le serveur
python3 server_basic_https.py
```

---

### 2. Serveur Flask HTTPS avec JSON

**Fichier**: `server_flask_https.py`

```python
#!/usr/bin/env python3

from flask import Flask, jsonify, request
import ssl
import os
import sys
from datetime import datetime

app = Flask(__name__)
PORT = 8000

@app.route('/')
def hello():
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'message': 'Serveur Flask HTTPS local'
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint pour tester les webhooks Telegram"""
    data = request.get_json()
    print(f"Webhook reçu: {data}")
    return jsonify({'status': 'received'}), 200

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

def main():
    # Vérifier les certificats
    cert_file = 'localhost+2.pem'
    key_file = 'localhost+2-key.pem'

    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        print(f"❌ Erreur: Certificats non trouvés")
        print(f"Créez-les avec: mkcert localhost 127.0.0.1")
        sys.exit(1)

    # Créer le contexte SSL
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=cert_file, keyfile=key_file)

    print(f"✓ Serveur Flask HTTPS démarré")
    print(f"🔗 https://localhost:{PORT}")
    print(f"🔗 https://localhost:{PORT}/webhook (POST)")
    print(f"❌ Appuyez sur Ctrl+C pour arrêter")

    try:
        app.run(
            host='localhost',
            port=PORT,
            ssl_context=context,
            debug=True
        )
    except KeyboardInterrupt:
        print("\n✓ Serveur arrêté")
        sys.exit(0)

if __name__ == '__main__':
    main()
```

**Utilisation**:
```bash
# Installer Flask
pip install flask

# Créer les certificats
mkcert localhost 127.0.0.1

# Lancer le serveur
python3 server_flask_https.py
```

---

### 3. Serveur FastAPI HTTPS avec Uvicorn

**Fichier**: `server_fastapi_https.py`

```python
#!/usr/bin/env python3

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import ssl
import os
from datetime import datetime

app = FastAPI()
PORT = 8000

@app.get("/")
def root():
    return {
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "message": "FastAPI HTTPS Server"
    }

@app.post("/webhook")
async def webhook(data: dict):
    """Telegram webhook endpoint"""
    print(f"Webhook received: {data}")
    return JSONResponse({"status": "received"})

@app.get("/health")
def health():
    return {"status": "healthy"}

def main():
    cert_file = 'localhost+2.pem'
    key_file = 'localhost+2-key.pem'

    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        print(f"❌ Certificats non trouvés")
        print(f"Créez-les avec: mkcert localhost 127.0.0.1")
        return

    print(f"✓ Serveur FastAPI HTTPS démarré")
    print(f"🔗 https://localhost:{PORT}")
    print(f"📖 https://localhost:{PORT}/docs (Swagger UI)")

    uvicorn.run(
        app,
        host="localhost",
        port=PORT,
        ssl_keyfile=key_file,
        ssl_certfile=cert_file
    )

if __name__ == '__main__':
    main()
```

**Utilisation**:
```bash
# Installer FastAPI et Uvicorn
pip install fastapi uvicorn

# Créer les certificats
mkcert localhost 127.0.0.1

# Lancer le serveur
python3 server_fastapi_https.py
```

---

## Serveurs Node.js HTTPS

### 1. Serveur Express HTTPS

**Fichier**: `server_express_https.js`

```javascript
const express = require('express');
const https = require('https');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 8000;

// Middleware
app.use(express.json());

// Routes
app.get('/', (req, res) => {
    res.json({
        status: 'online',
        timestamp: new Date().toISOString(),
        message: 'Express HTTPS Server'
    });
});

app.post('/webhook', (req, res) => {
    console.log('Webhook received:', req.body);
    res.json({ status: 'received' });
});

app.get('/health', (req, res) => {
    res.json({ status: 'healthy' });
});

// Charger les certificats mkcert
const options = {
    key: fs.readFileSync(path.join(__dirname, 'localhost+2-key.pem')),
    cert: fs.readFileSync(path.join(__dirname, 'localhost+2.pem'))
};

// Créer le serveur HTTPS
https.createServer(options, app).listen(PORT, () => {
    console.log(`✓ Serveur Express HTTPS démarré`);
    console.log(`🔗 https://localhost:${PORT}`);
    console.log(`🔗 https://localhost:${PORT}/webhook (POST)`);
    console.log(`❌ Appuyez sur Ctrl+C pour arrêter`);
});
```

**Utilisation**:
```bash
# Créer les certificats
mkcert localhost 127.0.0.1

# Installer Express
npm install express

# Lancer le serveur
node server_express_https.js
```

---

### 2. Serveur Fastify HTTPS

**Fichier**: `server_fastify_https.js`

```javascript
const fastify = require('fastify');
const fs = require('fs');
const path = require('path');

const PORT = 8000;

const options = {
    https: {
        key: fs.readFileSync(path.join(__dirname, 'localhost+2-key.pem')),
        cert: fs.readFileSync(path.join(__dirname, 'localhost+2.pem'))
    }
};

const app = fastify(options);

// Routes
app.get('/', async () => {
    return {
        status: 'online',
        timestamp: new Date().toISOString(),
        message: 'Fastify HTTPS Server'
    };
});

app.post('/webhook', async (request, reply) => {
    console.log('Webhook received:', request.body);
    return { status: 'received' };
});

app.get('/health', async () => {
    return { status: 'healthy' };
});

// Démarrer le serveur
const start = async () => {
    try {
        await app.listen({ port: PORT, host: '127.0.0.1' });
        console.log(`✓ Serveur Fastify HTTPS démarré`);
        console.log(`🔗 https://localhost:${PORT}`);
    } catch (err) {
        console.error(err);
        process.exit(1);
    }
};

start();
```

**Utilisation**:
```bash
# Créer les certificats
mkcert localhost 127.0.0.1

# Installer Fastify
npm install fastify

# Lancer le serveur
node server_fastify_https.js
```

---

## Configuration Telegram Bot

### 1. Script pour Enregistrer le Webhook

**Fichier**: `setup_telegram_webhook.py`

```python
#!/usr/bin/env python3

import requests
import sys
import os

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # Exporter TOKEN avant
WEBHOOK_URL = sys.argv[1] if len(sys.argv) > 1 else None

if not TOKEN:
    print("❌ Erreur: TELEGRAM_BOT_TOKEN non défini")
    print("Exécutez: export TELEGRAM_BOT_TOKEN='votre_token'")
    sys.exit(1)

if not WEBHOOK_URL:
    print("❌ Erreur: URL du webhook manquante")
    print("Usage: python setup_telegram_webhook.py https://votre-url.com")
    sys.exit(1)

# URL de l'API Telegram
API_URL = f"https://api.telegram.org/bot{TOKEN}"

print(f"Configuration du webhook Telegram...")
print(f"URL: {WEBHOOK_URL}")
print()

# 1. Supprimer l'ancien webhook
print("1️⃣  Suppression de l'ancien webhook...")
response = requests.get(f"{API_URL}/deleteWebhook")
print(f"   ✓ Réponse: {response.json()}")
print()

# 2. Configurer le nouveau webhook
print("2️⃣  Configuration du nouveau webhook...")
response = requests.get(
    f"{API_URL}/setWebhook",
    params={'url': WEBHOOK_URL}
)
result = response.json()
print(f"   ✓ Réponse: {result}")
print()

# 3. Vérifier la configuration
print("3️⃣  Vérification...")
response = requests.get(f"{API_URL}/getWebhookInfo")
webhook_info = response.json()

if webhook_info.get('ok'):
    info = webhook_info.get('result', {})
    print(f"   ✓ URL actuelle: {info.get('url', 'Aucun webhook')}")
    print(f"   ✓ Certificat ping pending: {info.get('pending_update_count', 0)}")
else:
    print(f"   ❌ Erreur: {webhook_info}")
    sys.exit(1)

print()
print("✓ Configuration complète!")
```

**Utilisation**:
```bash
# Exporter le token
export TELEGRAM_BOT_TOKEN="1234567890:ABCDEFGHIJKLmnopqrstuv-xyz"

# Configurer le webhook
python3 setup_telegram_webhook.py https://votre-url.com/webhook

# Ou après lancement du tunnel
python3 setup_telegram_webhook.py https://mon-app.ts.net/webhook
```

---

### 2. Handler de Webhook Telegram Simple

**Fichier**: `telegram_webhook_handler.py`

```python
#!/usr/bin/env python3

from flask import Flask, request, jsonify
import requests
import json
import os

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Reçoit les mises à jour de Telegram"""
    try:
        update = request.get_json()

        if not update:
            return jsonify({'status': 'ok'}), 200

        print(f"Update reçue: {json.dumps(update, indent=2)}")

        # Traiter les messages
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            text = message.get('text', '')

            print(f"Message de {message['from']['first_name']}: {text}")

            # Répondre au message
            send_message(chat_id, f"Vous avez dit: {text}")

        # Traiter les inline queries
        if 'inline_query' in update:
            inline_query = update['inline_query']
            query_id = inline_query['id']
            query_text = inline_query.get('query', '')

            print(f"Inline query: {query_text}")

            # Répondre à la query
            answer_inline_query(query_id, query_text)

        return jsonify({'status': 'ok'}), 200

    except Exception as e:
        print(f"❌ Erreur: {e}")
        return jsonify({'error': str(e)}), 500

def send_message(chat_id, text):
    """Envoyer un message via l'API Telegram"""
    response = requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={
            'chat_id': chat_id,
            'text': text
        }
    )
    return response.json()

def answer_inline_query(query_id, query_text):
    """Répondre à une inline query"""
    results = [
        {
            'type': 'article',
            'id': '1',
            'title': f"Résultat: {query_text}",
            'input_message_content': {
                'message_text': f"Vous avez cherché: {query_text}"
            }
        }
    ]

    response = requests.post(
        f"{TELEGRAM_API}/answerInlineQuery",
        json={
            'inline_query_id': query_id,
            'results': results,
            'cache_time': 0
        }
    )
    return response.json()

if __name__ == '__main__':
    if not TELEGRAM_TOKEN:
        print("❌ Erreur: TELEGRAM_BOT_TOKEN non défini")
        exit(1)

    print("✓ Webhook handler Telegram prêt")
    print("🔗 POST /webhook")

    # Configuration HTTPS
    app.run(
        host='localhost',
        port=8000,
        ssl_context=('localhost+2.pem', 'localhost+2-key.pem')
    )
```

**Utilisation**:
```bash
# Installer Flask et requests
pip install flask requests

# Créer certificats
mkcert localhost 127.0.0.1

# Exporter le token
export TELEGRAM_BOT_TOKEN="votre_token"

# Lancer le serveur
python3 telegram_webhook_handler.py

# Dans un autre terminal, configurer le webhook
python3 setup_telegram_webhook.py https://localhost:8000/webhook
```

---

## Scripts Automatisés

### 1. Suite Complète de Démarrage

**Fichier**: `full_setup.sh`

```bash
#!/bin/bash

set -e

# Configuration
PORT=8000
TUNNEL_SERVICE="tailscale"  # Options: tailscale, ngrok, localhost_run
SERVER_SCRIPT="app.py"
TELEGRAM_TOKEN_ENV="TELEGRAM_BOT_TOKEN"

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}▶${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1" >&2
    exit 1
}

info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# 1. Vérifier les dépendances
log "Vérification des dépendances..."

if ! command -v python3 &> /dev/null; then
    error "Python3 non installé"
fi

if [ "$TUNNEL_SERVICE" = "tailscale" ]; then
    if ! command -v tailscale &> /dev/null; then
        log "Installation de Tailscale..."
        brew install tailscale
    fi
elif [ "$TUNNEL_SERVICE" = "ngrok" ]; then
    if ! command -v ngrok &> /dev/null; then
        log "Installation de ngrok..."
        brew install ngrok
    fi
fi

# 2. Préparer les certificats (optionnel)
if [ -f "$SERVER_SCRIPT" ]; then
    if grep -q "ssl_context\|https://" "$SERVER_SCRIPT"; then
        if [ ! -f "localhost+2.pem" ]; then
            log "Création des certificats HTTPS..."
            if ! command -v mkcert &> /dev/null; then
                brew install mkcert
            fi
            mkcert localhost 127.0.0.1
        fi
    fi
fi

# 3. Lancer le serveur
log "Démarrage du serveur..."
python3 "$SERVER_SCRIPT" &
SERVER_PID=$!

sleep 2

if ! kill -0 $SERVER_PID 2>/dev/null; then
    error "Le serveur n'a pas pu démarrer"
fi

log "Serveur en cours d'exécution (PID: $SERVER_PID)"

# 4. Démarrer le tunnel
log "Démarrage du tunnel $TUNNEL_SERVICE..."

case $TUNNEL_SERVICE in
    tailscale)
        if ! tailscale status > /dev/null 2>&1; then
            error "Tailscale non connecté. Exécutez: tailscale up"
        fi
        TAILSCALE_NAME=$(hostname -s)
        TUNNEL_URL="https://${TAILSCALE_NAME}.ts.net"
        tailscale funnel $PORT &
        TUNNEL_PID=$!
        ;;
    ngrok)
        ngrok http $PORT &
        TUNNEL_PID=$!
        sleep 3
        TUNNEL_URL=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url')
        ;;
    localhost_run)
        ssh -o ServerAliveInterval=60 -R 80:localhost:$PORT localhost.run &
        TUNNEL_PID=$!
        sleep 2
        # L'URL s'affiche directement
        TUNNEL_URL="(voir terminal)"
        ;;
    *)
        error "Service $TUNNEL_SERVICE non reconnu"
        ;;
esac

log "Tunnel en cours d'exécution"

# 5. Configurer Telegram (si token disponible)
if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
    log "Configuration du webhook Telegram..."
    WEBHOOK_URL="${TUNNEL_URL}/webhook"

    if [ -f "setup_telegram_webhook.py" ]; then
        python3 setup_telegram_webhook.py "$WEBHOOK_URL"
    fi
fi

# 6. Afficher les informations
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}  Serveur et Tunnel Démarrés avec Succès"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""
info "Serveur local: http://localhost:$PORT"
info "URL publique: $TUNNEL_URL"
info "Server PID: $SERVER_PID"
info "Tunnel PID: $TUNNEL_PID"
echo ""
info "Appuyez sur Ctrl+C pour arrêter"
echo ""

# 7. Nettoyage en cas d'interruption
cleanup() {
    log "Arrêt en cours..."
    kill $SERVER_PID $TUNNEL_PID 2>/dev/null || true
    log "Serveur et tunnel arrêtés"
}

trap cleanup EXIT
wait $SERVER_PID $TUNNEL_PID
```

**Utilisation**:
```bash
chmod +x full_setup.sh

# Avec Tailscale
TUNNEL_SERVICE=tailscale ./full_setup.sh

# Avec ngrok
TUNNEL_SERVICE=ngrok ./full_setup.sh

# Avec Telegram
export TELEGRAM_BOT_TOKEN="votre_token"
TUNNEL_SERVICE=tailscale ./full_setup.sh
```

---

## Checklist de Configuration Complète

```bash
# 1. Installer Tailscale (recommandé)
brew install tailscale
tailscale up

# 2. Créer certificats (optionnel, si HTTPS local)
brew install mkcert
mkcert localhost 127.0.0.1

# 3. Installer dépendances Python
pip install flask requests fastapi uvicorn

# 4. Créer le serveur
cat > app.py << 'EOF'
from flask import Flask
import json

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    return json.dumps({'status': 'ok'})

if __name__ == '__main__':
    app.run(port=8000)
EOF

# 5. Lancer le tunnel
tailscale funnel 8000

# 6. Récupérer l'URL
TUNNEL_URL="https://$(hostname -s).ts.net"
echo "URL: $TUNNEL_URL"

# 7. Configurer Telegram
export TELEGRAM_BOT_TOKEN="votre_token"
python3 setup_telegram_webhook.py "$TUNNEL_URL/webhook"
```

---

**Créé**: Décembre 2025
