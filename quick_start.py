#!/usr/bin/env python3
"""
Script de démarrage rapide pour tester le bot refactorisé.
"""

import os
import sys
import logging
from pathlib import Path

def check_environment():
    """Vérifier que l'environnement est prêt."""
    print("🔍 Vérification de l'environnement...")
    
    # Vérifier .env
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ Fichier .env manquant")
        print("📝 Créez le fichier .env à partir de .env.example")
        print("   cp .env.example .env")
        print("   # Puis éditez .env avec vos configurations")
        return False
    
    # Charger .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("❌ python-dotenv non installé")
        print("📦 Installez avec: pip install python-dotenv")
        return False
    
    # Vérifier token Telegram
    token = os.getenv("TELEGRAM_TOKEN")
    if not token or token == "your_telegram_bot_token_here":
        print("❌ TELEGRAM_TOKEN non configuré dans .env")
        print("🤖 Obtenez un token via @BotFather sur Telegram")
        return False
    
    print("✅ Configuration trouvée")
    return True

def check_dependencies():
    """Vérifier les dépendances."""
    print("📦 Vérification des dépendances...")
    
    required_modules = [
        "telegram",
        "dotenv", 
        "requests",
        "sqlite3"  # Built-in
    ]
    
    missing = []
    for module in required_modules:
        try:
            if module == "sqlite3":
                import sqlite3
            elif module == "telegram":
                import telegram
            elif module == "dotenv":
                from dotenv import load_dotenv
            elif module == "requests":
                import requests
        except ImportError:
            missing.append(module)
    
    if missing:
        print(f"❌ Modules manquants: {', '.join(missing)}")
        print("📦 Installez avec:")
        print("   pip install python-telegram-bot python-dotenv requests")
        return False
    
    print("✅ Toutes les dépendances sont présentes")
    return True

def setup_directories():
    """Créer les dossiers nécessaires."""
    print("📁 Création des dossiers...")
    
    directories = ["logs", "uploads", "wallets"]
    for dir_name in directories:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"✅ {dir_name}/")
    
    return True

def test_bot_import():
    """Tester l'import du bot."""
    print("🤖 Test d'import du bot...")
    
    try:
        # Test import version refactorisée
        sys.path.insert(0, os.getcwd())
        
        # Test imports étape par étape
        print("  📦 Test core...")
        from app.core import settings
        
        print("  📦 Test entities...")
        # Test sans base58 pour l'instant
        
        print("  📦 Test bot principal...")
        # Import simple sans exécution
        with open("marketplace_bot_refactored.py", "r") as f:
            content = f.read()
            if "class MarketplaceBotRefactored" in content:
                print("✅ Bot refactorisé trouvé")
            else:
                print("❌ Structure du bot incorrecte")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur d'import: {e}")
        print("💡 Certaines dépendances peuvent manquer (base58, etc.)")
        return False

def show_launch_options():
    """Afficher les options de lancement."""
    print("\n🚀 OPTIONS DE LANCEMENT")
    print("=" * 50)
    
    print("\n1️⃣ BOT REFACTORISÉ (Recommandé)")
    print("   python3 marketplace_bot_refactored.py")
    print("   ✅ Architecture clean")
    print("   ✅ Code maintenable") 
    print("   ⚠️ Fonctionnalités de base uniquement")
    
    print("\n2️⃣ BOT LEGACY (Complet)")
    print("   python3 bot_mlt.py")
    print("   ✅ Toutes les fonctionnalités")
    print("   ❌ Code monolithique")
    print("   ❌ Difficile à maintenir")
    
    print("\n3️⃣ TESTS")
    print("   python3 test_refactoring.py")
    print("   ✅ Vérification de l'architecture")
    
    print("\n📝 CONFIGURATION MINIMALE")
    print("   Dans .env, il vous faut au minimum:")
    print("   - TELEGRAM_TOKEN=votre_token_bot")
    print("   - ADMIN_USER_ID=votre_user_id")

def main():
    """Script principal."""
    print("🎯 TECHBOT MARKETPLACE - DÉMARRAGE RAPIDE")
    print("=" * 50)
    
    checks = [
        ("Environment", check_environment),
        ("Dependencies", check_dependencies), 
        ("Directories", setup_directories),
        ("Bot Import", test_bot_import)
    ]
    
    all_good = True
    for name, check_func in checks:
        print(f"\n📋 {name}:")
        if not check_func():
            all_good = False
    
    print("\n" + "=" * 50)
    
    if all_good:
        print("✅ ENVIRONNEMENT PRÊT !")
        show_launch_options()
        
        print("\n🔥 COMMANDE RAPIDE:")
        print("   python3 marketplace_bot_refactored.py")
        
    else:
        print("❌ PROBLÈMES DÉTECTÉS")
        print("\n🔧 SOLUTION RAPIDE:")
        print("1. Copiez .env.example vers .env")
        print("2. Éditez .env avec votre token Telegram")
        print("3. Installez les dépendances:")
        print("   pip install python-telegram-bot python-dotenv requests")
        print("4. Relancez ce script")
    
    print("\n💡 AIDE:")
    print("   - Token Telegram: @BotFather")
    print("   - User ID: @userinfobot") 
    print("   - Documentation: README_REFACTORED.md")

if __name__ == "__main__":
    main()