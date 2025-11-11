#!/bin/bash

echo "======================================"
echo "🎯 SCRAPER - Installation rapide"
echo "======================================"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé"
    exit 1
fi

echo "✅ Python détecté"

# Install dependencies
echo ""
echo "📦 Installation des dépendances..."
pip install -r requirements.txt

# Install Playwright
echo ""
echo "🌐 Installation de Playwright..."
playwright install chromium

echo ""
echo "======================================"
echo "✅ Installation terminée!"
echo "======================================"
echo ""
echo "🚀 Pour lancer le scraper:"
echo "   python main.py"
echo ""
echo "📖 Pour plus d'options:"
echo "   python main.py --help"
echo ""
