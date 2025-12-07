#!/bin/bash
# Script de démarrage : Bot + Tunnel HTTPS pour Mini App
# Usage: ./start-with-tunnel.sh

set -e

echo "🚀 Démarrage Uzeur Marketplace avec Mini App (Dev Mode)"
echo ""

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Vérifier que cloudflared est installé
if ! command -v cloudflared &> /dev/null; then
    echo -e "${YELLOW}⚠️  cloudflared non installé. Installation...${NC}"
    brew install cloudflared
fi

# 2. Lancer le bot en arrière-plan
echo -e "${BLUE}📱 Démarrage du bot Telegram...${NC}"
python3 -m app.main &
BOT_PID=$!
echo "   Bot PID: $BOT_PID"

# Attendre que le serveur démarre
sleep 5

# 3. Lancer le tunnel Cloudflare
echo -e "${BLUE}🌐 Création du tunnel HTTPS...${NC}"
cloudflared tunnel --url http://localhost:8000 > tunnel.log 2>&1 &
TUNNEL_PID=$!
echo "   Tunnel PID: $TUNNEL_PID"

# Attendre que le tunnel soit prêt
sleep 5

# 4. Extraire l'URL du tunnel
TUNNEL_URL=$(grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' tunnel.log | head -1)

if [ -z "$TUNNEL_URL" ]; then
    echo -e "${YELLOW}⚠️  Impossible de récupérer l'URL du tunnel${NC}"
    echo "   Vérifiez tunnel.log pour plus d'infos"
else
    echo ""
    echo -e "${GREEN}✅ Mini App accessible à :${NC}"
    echo -e "${GREEN}   $TUNNEL_URL/static/upload.html${NC}"
    echo ""
    echo -e "${YELLOW}📝 Mets à jour WEBAPP_URL dans .env :${NC}"
    echo -e "${YELLOW}   WEBAPP_URL=$TUNNEL_URL${NC}"
    echo ""
fi

# 5. Sauvegarder les PIDs pour cleanup
echo "$BOT_PID $TUNNEL_PID" > .dev_pids

echo -e "${BLUE}📊 Logs en temps réel (Ctrl+C pour arrêter) :${NC}"
echo ""

# Fonction de cleanup
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Arrêt des services...${NC}"
    if [ -f .dev_pids ]; then
        read -r BOT_PID TUNNEL_PID < .dev_pids
        kill $BOT_PID $TUNNEL_PID 2>/dev/null || true
        rm .dev_pids
    fi
    rm -f tunnel.log
    echo -e "${GREEN}✅ Arrêt propre${NC}"
    exit 0
}

trap cleanup INT TERM

# Suivre les logs
tail -f tunnel.log
