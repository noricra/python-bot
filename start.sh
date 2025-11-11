#!/bin/bash
# Start script for Railway deployment
# Launches Marketplace Bot (which starts both Telegram bot and IPN server)

set -e  # Exit on error

echo "🚀 Starting Uzeur Marketplace..."
echo ""
echo "📡 IPN Server will start on port ${PORT:-8000}"
echo "🤖 Telegram Bot will start in polling mode"
echo ""

# Launch app.main which handles both IPN server and Telegram bot
python3 -m app.main
