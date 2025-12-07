#!/bin/bash
# Development start script with Cloudflare Tunnel
# Launches Marketplace Bot + Cloudflare Tunnel for HTTPS

set -e  # Exit on error

echo "🚀 Starting Uzeur Marketplace (DEV MODE with Tunnel)"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo -e "${YELLOW}⚠️  cloudflared not installed. Installing...${NC}"
    brew install cloudflared
fi

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Stopping services...${NC}"
    if [ -f .tunnel_pid ]; then
        kill $(cat .tunnel_pid) 2>/dev/null || true
        rm .tunnel_pid
    fi
    pkill -f cloudflared 2>/dev/null || true
    rm -f tunnel.log
    echo -e "${GREEN}✅ Clean shutdown${NC}"
    exit 0
}

# Trap Ctrl+C
trap cleanup INT TERM

# 1. Start Cloudflare Tunnel in background
echo -e "${BLUE}🌐 Starting Cloudflare Tunnel...${NC}"
cloudflared tunnel --url http://localhost:8000 > tunnel.log 2>&1 &
TUNNEL_PID=$!
echo $TUNNEL_PID > .tunnel_pid
echo "   Tunnel PID: $TUNNEL_PID"

# Wait for tunnel to be ready
echo "   Waiting for tunnel to establish..."
sleep 8

# Extract URL from log
TUNNEL_URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' tunnel.log | head -1)

if [ -z "$TUNNEL_URL" ]; then
    echo -e "${YELLOW}⚠️  Could not get tunnel URL${NC}"
    echo "   Check tunnel.log for details"
    cat tunnel.log
    cleanup
fi

echo ""
echo -e "${GREEN}✅ Tunnel active:${NC}"
echo -e "${GREEN}   $TUNNEL_URL${NC}"
echo ""

# 2. Update .env with tunnel URL
echo -e "${BLUE}📝 Updating WEBAPP_URL in .env...${NC}"
if [ -f .env ]; then
    # Backup .env
    cp .env .env.backup

    # Update WEBAPP_URL
    if grep -q "WEBAPP_URL=" .env; then
        sed -i '' "s|WEBAPP_URL=.*|WEBAPP_URL=$TUNNEL_URL|g" .env
    else
        echo "WEBAPP_URL=$TUNNEL_URL" >> .env
    fi

    echo -e "${GREEN}   ✅ WEBAPP_URL updated${NC}"
else
    echo -e "${YELLOW}   ⚠️  .env file not found${NC}"
fi

echo ""
echo -e "${GREEN}📱 Mini App URL:${NC}"
echo -e "${GREEN}   $TUNNEL_URL/static/upload.html${NC}"
echo ""
echo -e "${YELLOW}💡 Use this URL in your Telegram Mini App button${NC}"
echo ""

# 3. Start the bot
echo -e "${BLUE}🤖 Starting Telegram Bot...${NC}"
echo ""
echo "📡 IPN Server will start on port 8000"
echo "🤖 Telegram Bot will start in polling mode"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run bot (this blocks)
python3 -m app.main

# If bot exits, cleanup
cleanup
