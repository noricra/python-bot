# Guide de Dépannage - Tunneling et Telegram Mini Apps

## Table des matières
1. [Problèmes Courants](#problèmes-courants)
2. [Diagnostic des Tunnels](#diagnostic-des-tunnels)
3. [Problèmes Telegram Spécifiques](#problèmes-telegram-spécifiques)
4. [Problèmes HTTPS/SSL](#problèmes-httpsssl)
5. [Problèmes de Performance](#problèmes-de-performance)
6. [Commandes de Test Utiles](#commandes-de-test-utiles)

---

## Problèmes Courants

### Problème: "Connection refused" / "Cannot connect to localhost:8000"

**Symptômes**:
- Le tunnel démarre mais retourne une erreur
- `curl https://tunnel-url.com` retourne "Connection refused"
- Le dashboard du tunnel affiche des erreurs

**Causes possibles**:
1. Le serveur local n'écoute pas sur le port 8000
2. Le serveur s'est crashé
3. Mauvais port dans la commande du tunnel

**Solutions**:

```bash
# 1. Vérifier que le serveur écoute
lsof -i :8000
# Doit afficher quelque chose comme: python3 xxx LISTEN

# 2. Si vide, lancer le serveur
python3 app.py &

# 3. Vérifier qu'il démarre bien
sleep 2
lsof -i :8000

# 4. Tester localement
curl -k https://localhost:8000  # -k ignore les erreurs SSL

# 5. Si ça fonctionne, redémarrer le tunnel
# Pour ngrok
ngrok http 8000

# Pour localhost.run
ssh -R 80:localhost:8000 localhost.run

# Pour Tailscale
tailscale funnel 8000
```

---

### Problème: URL du tunnel change à chaque redémarrage

**Symptômes**:
- L'URL publiée change constamment
- Telegram Mini App URL devient invalide après restart
- Impossible d'utiliser avec des webhooks stables

**Causes possibles**:
- Service gratuit avec URLs temporaires (ngrok free, Pinggy, Localtunnel)
- Tunnel qui se ferme et redémarre

**Solutions**:

```bash
# Option 1: Utiliser Tailscale Funnel (URL fixe gratuit)
tailscale funnel 8000
# URL stable: https://monapp.ts.net

# Option 2: Garder le tunnel actif (localhost.run avec keepalive)
ssh -o ServerAliveInterval=60 -R 80:localhost:8000 localhost.run

# Option 3: Boucle de reconnexion (Pinggy)
while true; do
  ssh -p 443 -o ServerAliveInterval=60 -R0:localhost:8000 qr@free.pinggy.io
  sleep 2
done

# Option 4: Passer à un plan payant (URL fixe)
# ngrok: $15/mois
# localhost.run: $9/an
# Pinggy: $2.50/mois
```

---

### Problème: "Tunnel se ferme après 60 minutes"

**Symptômes**:
- Tunnel fonctionne pendant une heure puis se ferme
- Erreur "Session timeout"
- Besoin de redémarrer régulièrement

**Service concerné**: Pinggy (gratuit = 60 min)

**Solutions**:

```bash
# Option 1: Script de reconnexion automatique
cat > restart_pinggy.sh << 'EOF'
#!/bin/bash
while true; do
  echo "Démarrage du tunnel Pinggy..."
  ssh -p 443 -o ServerAliveInterval=60 \
      -R0:localhost:8000 qr@free.pinggy.io
  echo "Tunnel fermé, reconnexion en 2 secondes..."
  sleep 2
done
EOF

chmod +x restart_pinggy.sh
./restart_pinggy.sh

# Option 2: Passer à Pinggy Pro ($2.50/mois)
# Pas de timeout

# Option 3: Utiliser un autre service
# Tailscale Funnel: gratuit, pas de timeout, URL fixe
# localhost.run: gratuit, pas de timeout
```

---

### Problème: "SSL certificate problem" ou "certificate not trusted"

**Symptômes**:
- Erreur: `curl: (60) SSL certificate problem`
- Telegram retourne: "Certificate verification failed"
- Navigateur affiche: "ERR_CERT_AUTHORITY_INVALID"

**Causes possibles**:
1. Certificat self-signed non reconnu
2. Serveur local utilise mkcert mais tunnel à besoin du certificat réel
3. Certificat expiré

**Solutions**:

```bash
# Cas 1: Serveur local avec mkcert (OK pour localhost)
# Aucun problème, c'est normal

# Cas 2: Exposer via tunnel avec certificat local
# Le tunnel doit servir le HTTPS automatiquement

# Vérifier le certificat du tunnel
curl -kI https://votre-tunnel-url.com
# -k = ignorer les erreurs SSL (test seulement)

# Doit retourner HTTP/2 200 ou 301

# Cas 3: Telegram refuse l'URL
# S'assurer que:
# 1. Le certificat est valide (Let's Encrypt automatique)
curl -I https://votre-tunnel-url.com
# Doit retourner sans erreur

# 2. L'URL est publiquement accessible
curl https://votre-tunnel-url.com/webhook -X GET

# 3. Le statut code est correct (200, 301, 404 OK; 502 NON OK)
```

---

### Problème: "Tunnel URL works locally but fails from internet"

**Symptômes**:
- `curl https://localhost:8000` fonctionne
- `curl https://tunnel-url.com` retourne une erreur
- Telegram Mini App affiche "Network error"

**Causes possibles**:
1. Firewall bloque les connexions entrantes
2. Tunnel n'est pas vraiment actif
3. Serveur ne répond qu'à localhost

**Solutions**:

```bash
# 1. Vérifier que le tunnel est bien actif
# Pour ngrok
curl http://localhost:4040/api/tunnels | jq

# Pour Tailscale
tailscale status
# Doit afficher "funnel active"

# 2. Vérifier que le serveur répond sur 0.0.0.0, pas seulement localhost
# Mauvais:
app.run(host='localhost', port=8000)

# Bon:
app.run(host='0.0.0.0', port=8000)
# Ou pour le tunnel:
app.run(host='127.0.0.1', port=8000)  # OK si tunnel redirige

# 3. Vérifier que aucun firewall ne bloque
# macOS: System Preferences > Security & Privacy > Firewall
# Ou donner la permission à l'application serveur

# 4. Tester depuis un autre réseau
# Utiliser votre téléphone sur données mobiles
# Accéder à https://tunnel-url.com

# 5. Vérifier les logs du tunnel
# ngrok: http://localhost:4040 (Web UI)
# Tailscale: tailscale status, journaux système
# localhost.run: visible dans le terminal
```

---

## Diagnostic des Tunnels

### Script de Test Complet

**Fichier**: `test_tunnel.sh`

```bash
#!/bin/bash

set -e

PORT=8000
TUNNEL_URL=${1:-""}

if [ -z "$TUNNEL_URL" ]; then
    echo "Usage: ./test_tunnel.sh https://your-tunnel-url.com"
    exit 1
fi

echo "╔════════════════════════════════════════════════════╗"
echo "║  Test Diagnostic du Tunnel"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# 1. Tester localhost
echo "1️⃣  Test du serveur local..."
if curl -sk https://localhost:$PORT > /dev/null 2>&1; then
    echo "   ✓ Serveur local répond"
else
    echo "   ❌ Serveur local ne répond pas"
    echo "   Conseil: lancer python3 app.py"
    exit 1
fi
echo ""

# 2. Tester le tunnel
echo "2️⃣  Test de l'URL du tunnel..."
if curl -sI "$TUNNEL_URL" > /dev/null 2>&1; then
    STATUS=$(curl -sI "$TUNNEL_URL" | head -1)
    echo "   ✓ Tunnel répond"
    echo "   ✓ Statut: $STATUS"
else
    echo "   ❌ Tunnel ne répond pas"
    exit 1
fi
echo ""

# 3. Tester webhook (si disponible)
echo "3️⃣  Test du webhook..."
if curl -X POST "$TUNNEL_URL/webhook" \
     -H "Content-Type: application/json" \
     -d '{"test":true}' 2>/dev/null; then
    echo "   ✓ Webhook répond"
else
    echo "   ⚠️  Endpoint /webhook non trouvé (normal)"
fi
echo ""

# 4. Tester le certificat SSL
echo "4️⃣  Test du certificat SSL..."
if echo | openssl s_client -connect $(echo $TUNNEL_URL | sed 's|https://||' | sed 's|/||g'):443 2>/dev/null | grep "Verify return code"; then
    echo "   ✓ Certificat SSL valide"
else
    echo "   ❌ Certificat SSL invalide"
fi
echo ""

# 5. Vérifier la redirection HTTP -> HTTPS
echo "5️⃣  Test redirection HTTP -> HTTPS..."
HTTP_URL=$(echo "$TUNNEL_URL" | sed 's|https://|http://|')
LOCATION=$(curl -sI "$HTTP_URL" | grep -i location || echo "")
if [ -n "$LOCATION" ]; then
    echo "   ✓ Redirection détectée: $LOCATION"
else
    echo "   ⚠️  Pas de redirection HTTP -> HTTPS (peut être normal)"
fi
echo ""

echo "═════════════════════════════════════════════════════"
echo "✓ Test diagnostic terminé"
echo "═════════════════════════════════════════════════════"
```

**Utilisation**:
```bash
chmod +x test_tunnel.sh
./test_tunnel.sh https://mon-app.ts.net
```

---

## Problèmes Telegram Spécifiques

### Problème: "Invalid URL" dans BotFather

**Symptômes**:
- BotFather refuse l'URL
- Erreur: "Invalid app_link"
- Message: "HTTPS link required"

**Causes possibles**:
1. URL n'utilise pas HTTPS
2. Certificat invalide/auto-signé
3. URL pointe vers localhost (127.0.0.1 vs localhost)
4. Serveur retourne 502/503/504

**Solutions**:

```bash
# 1. S'assurer que c'est bien HTTPS
# Mauvais: http://mon-app.ts.net
# Bon: https://mon-app.ts.net

# 2. Vérifier le certificat
curl -I https://mon-app.ts.net
# Doit retourner HTTP/2 200 (ou redirection)
# Pas d'erreur SSL

# 3. Utiliser 127.0.0.1, pas localhost
# Dans le test d'URL (pas sur Telegram):
curl -I https://127.0.0.1:8000
# Ajouter --insecure (-k) pour self-signed:
curl -Ik https://127.0.0.1:8000

# 4. Vérifier que le serveur ne retourne pas d'erreur
curl -v https://mon-app.ts.net
# Chercher la première ligne de statut
# < HTTP/2 200  ✓
# < HTTP/2 502  ✗

# 5. Vérifier que le endpoint /webhook existe
curl -X POST https://mon-app.ts.net/webhook \
     -H "Content-Type: application/json" \
     -d '{"message":"test"}'

# Doit retourner une réponse (même si c'est une erreur)
# Pas 404 ou 502
```

**En cas d'erreur persistante**:

```bash
# 1. Tester dans l'environnement de test Telegram (HTTP accepté)
# Voir: https://docs.telegram-mini-apps.com/platform/test-environment

# 2. Utiliser @BotFather -> App web link
# /myapp -> App web link:
# https://mon-app.ts.net/miniapp

# 3. Attendre quelques minutes (cache Telegram)

# 4. Vérifier les logs du serveur
# Voir si Telegram envoie des requêtes
tail -f app.log | grep webhook

# 5. En dernier recours: redémarrer le tunnel
# Parfois le certificat cache cause des problèmes
tailscale funnel reset
tailscale funnel 8000
```

---

### Problème: Mini App s'ouvre mais affiche une erreur blanche

**Symptômes**:
- Mini App s'ouvre dans Telegram
- Puis affiche une page blanche ou erreur
- Console JavaScript pleine d'erreurs CORS

**Causes possibles**:
1. CORS non configuré (serveur refuse l'accès)
2. Erreur JavaScript côté client
3. Requête vers un endpoint inexistant

**Solutions**:

```python
# Configuration CORS pour Flask
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Accepter les requêtes de tous les origins

@app.route('/miniapp')
def miniapp():
    return '''
    <!DOCTYPE html>
    <html>
    <body>
        <h1>Mini App Telegram</h1>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <script>
            const tg = window.Telegram.WebApp;
            tg.ready();
            console.log('Utilisateur:', tg.initData);
        </script>
    </body>
    </html>
    '''

# Ou avec Flask-CORS explicite
@app.route('/api/data')
@CORS()
def get_data():
    return {'data': 'test'}
```

```javascript
// Configuration CORS côté client
fetch('https://mon-app.ts.net/api/data', {
    method: 'GET',
    headers: {
        'Content-Type': 'application/json'
    },
    credentials: 'include'  // Envoyer les cookies
})
.then(r => r.json())
.catch(e => console.error('CORS Error:', e));
```

---

### Problème: Webhook ne reçoit pas les mises à jour

**Symptômes**:
- Configuré correctement avec `setWebhook`
- Telegram ne reçoit rien
- `/getWebhookInfo` affiche 0 pending updates

**Causes possibles**:
1. Webhook URL inatteignable
2. Serveur retourne erreur 4xx ou 5xx
3. Délai entre la configuration et le test
4. Pas de logique de traitement du webhook

**Solutions**:

```bash
# 1. Vérifier que le webhook est configuré
curl https://api.telegram.org/bot$TOKEN/getWebhookInfo

# Doit afficher:
# "ok": true
# "result": {
#   "url": "https://votre-url.com/webhook",
#   "has_custom_certificate": false,
#   "pending_update_count": 0

# 2. Tester manuellement
# Envoyer un message au bot depuis Telegram

# 3. Vérifier les logs du serveur
tail -f app.log

# Doit afficher une requête POST

# 4. Si rien, vérifier que le endpoint répond
curl -X POST https://votre-url.com/webhook \
     -H "Content-Type: application/json" \
     -d '{"update_id":123,"message":{"text":"test"}}'

# 5. Checker le statut du webhook
curl https://api.telegram.org/bot$TOKEN/getWebhookInfo | jq

# Chercher "last_error_message" pour les erreurs

# 6. Redéfinir le webhook
curl https://api.telegram.org/bot$TOKEN/deleteWebhook

sleep 2

curl https://api.telegram.org/bot$TOKEN/setWebhook \
     -d "url=https://votre-url.com/webhook" \
     -d "max_connections=40" \
     -d "allowed_updates=message,inline_query"

# 7. Attendre 30 secondes et tester

sleep 30
# Envoyer un message depuis Telegram
```

---

## Problèmes HTTPS/SSL

### Problème: "mkcert not found" après `mkcert -install`

**Symptômes**:
- `mkcert -install` fonctionne
- Mais Keychain n'est pas mis à jour
- Safari/Chrome refuse le certificat

**Solutions**:

```bash
# 1. Réinstaller mkcert
brew uninstall mkcert
brew install mkcert

# 2. Exécuter à nouveau mkcert -install
mkcert -install

# 3. Vérifier dans Keychain Access
# Applications > Keychain Access
# Chercher "mkcert"

# 4. Si toujours pas reconnu, ajouter manuellement
# Importer le certificat:
mkcert -CAROOT
# Ouvrir le fichier root_ca.crt dans Keychain Access
# Double-clic > Trust > Always Trust

# 5. Redémarrer le navigateur
```

---

### Problème: Certificat self-signed n'est pas reconnu par Telegram

**Symptômes**:
- Serveur local fonctionne en HTTPS
- Tunnel aussi mais refuse le certificat self-signed
- Telegram dit: "Certificate not trusted"

**Cause**: Telegram n'accepte que des certificats Let's Encrypt valides

**Solutions**:

```bash
# Option 1: Utiliser un service tunnel avec Let's Encrypt automatique
# Tous les services listés offrent cela (sauf mkcert local)

# Option 2: Si self-signed absolument nécessaire
# Combiner mkcert + tunnel HTTPS:

# 1. Créer certificat local mkcert
mkcert localhost 127.0.0.1

# 2. Lancer serveur local HTTPS
python3 app.py  # Avec SSL context configuré

# 3. Lancer tunnel (il fournira le certificat Let's Encrypt)
ngrok http https://localhost:8000 --host-header=localhost:8000

# 4. Utiliser l'URL du tunnel dans Telegram
# L'URL du tunnel aura un certificat valide

# Option 3: Utiliser Telegram Test Environment (accepte HTTP)
# https://docs.telegram-mini-apps.com/platform/test-environment
```

---

## Problèmes de Performance

### Problème: Tunnel très lent ou timeout

**Symptômes**:
- Requête très lente (30+ secondes)
- Timeout lors de l'accès
- Connexions intermittentes

**Causes possibles**:
1. Service tunnel surchargé
2. Mauvaise connexion internet
3. Serveur local lent
4. Trop de reconnexions

**Solutions**:

```bash
# 1. Tester la connexion locale d'abord
time curl -k https://localhost:8000

# Si c'est lent, c'est le serveur local
# Si c'est rapide, c'est le tunnel

# 2. Vérifier la connexion internet
ping -c 5 8.8.8.8

# 3. Changer de serveur tunnel si possible
# Essayer un autre service avec meilleur débit

# 4. Optimiser le serveur local
# Python: ajouter du caching, optimiser les requêtes BD
# Node: utiliser clustering, worker threads

# 5. Monitorer la performance
# ngrok: http://localhost:4040
# Voir le temps de réponse pour chaque requête

# 6. Redémarrer le tunnel
# Parfois une connexion "pourrie" bloque
```

---

### Problème: Connexion SSH du tunnel s'interrompt

**Symptômes**:
- `ssh -R` se déconnecte après quelques minutes
- Erreur: "Broken pipe"
- Connexion SSH reste inactive

**Solutions**:

```bash
# 1. Ajouter le paramètre ServerAliveInterval
# Envoie un ping toutes les 60 secondes

ssh -o ServerAliveInterval=60 \
    -o ServerAliveCountMax=3 \
    -R 80:localhost:8000 localhost.run

# 2. Si le serveur ne répond pas au keepalive
# Ajouter TCPKeepAlive

ssh -o TCPKeepAlive=yes \
    -o ServerAliveInterval=60 \
    -R 80:localhost:8000 localhost.run

# 3. Augmenter le timeout de connexion
ssh -o ConnectTimeout=10 \
    -o ServerAliveInterval=60 \
    -R 80:localhost:8000 localhost.run

# 4. Vérifier la config SSH
cat ~/.ssh/config

# Ajouter si nécessaire:
# Host localhost.run
#     ServerAliveInterval 60
#     ServerAliveCountMax 3
```

---

## Commandes de Test Utiles

### Tester un tunnel

```bash
# Tester basique
curl -I https://votre-url.com

# Avec certificat auto-signé
curl -kI https://votre-url.com

# Avec verbose (voir tous les détails)
curl -vI https://votre-url.com

# Tester POST
curl -X POST https://votre-url.com/webhook \
     -H "Content-Type: application/json" \
     -d '{"test": true}'

# Tester avec timeout
curl --connect-timeout 5 https://votre-url.com

# Voir les headers de réponse
curl -i https://votre-url.com

# Télécharger le certificat et l'inspecter
openssl s_client -connect votre-url.com:443 -showcerts
```

---

### Monitorer les ports

```bash
# Lister les processus écoutant sur un port
lsof -i :8000

# Ou avec netstat
netstat -an | grep LISTEN | grep 8000

# Tuer un processus sur un port
kill -9 $(lsof -t -i :8000)

# Ou utiliser fuser
fuser -k 8000/tcp
```

---

### Tester Telegram

```bash
# Récupérer info du webhook
curl https://api.telegram.org/bot$TOKEN/getWebhookInfo | jq

# Voir les mises à jour en attente
curl https://api.telegram.org/bot$TOKEN/getUpdates | jq

# Supprimer le webhook
curl https://api.telegram.org/bot$TOKEN/deleteWebhook

# Définir un nouveau webhook
curl -X POST https://api.telegram.org/bot$TOKEN/setWebhook \
     -d "url=https://votre-url.com/webhook"

# Vérifier que tout est bien configuré
curl https://api.telegram.org/bot$TOKEN/getMe | jq
```

---

### Monitorer les logs

```bash
# Logs en temps réel
tail -f app.log

# Derniers 50 lignes
tail -n 50 app.log

# Chercher des erreurs
grep -i error app.log

# Nombre de requêtes
wc -l app.log

# Requêtes par seconde (avec timestamp)
tail -f app.log | grep webhook
```

---

## Checklist de Diagnostic

Avant de demander de l'aide, vérifiez:

- [ ] Serveur local écoute: `lsof -i :8000`
- [ ] Tunnel actif: `curl $TUNNEL_URL`
- [ ] Certificat valide: `curl -I $TUNNEL_URL` (pas d'erreur SSL)
- [ ] Endpoint existe: `curl -I $TUNNEL_URL/webhook`
- [ ] Webhook configuré: `curl $TG_API/getWebhookInfo`
- [ ] URL est HTTPS: `echo $TUNNEL_URL | grep https`
- [ ] URL pas localhost: `echo $TUNNEL_URL | grep -v localhost`
- [ ] Serveur responded: `curl -v $TUNNEL_URL` (voir le statut)
- [ ] Logs du serveur: `tail -f app.log` (voir les erreurs)
- [ ] Logs Telegram: vérifier pending_update_count dans getWebhookInfo

---

**Créé**: Décembre 2025
