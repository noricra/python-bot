#!/usr/bin/env python3
"""
Script de vérification pré-déploiement
Vérifie que tous les modules s'importent correctement
"""

import sys

def check_imports():
    """Vérifie tous les imports critiques"""
    checks = []

    print("🔍 Vérification des imports critiques...\n")

    # Check 1: Settings
    try:
        from app.core import settings
        print("✅ app.core.settings")
        checks.append(True)
    except Exception as e:
        print(f"❌ app.core.settings: {e}")
        checks.append(False)

    # Check 2: PostgreSQL
    try:
        from app.core.database_init import get_postgresql_connection
        print("✅ PostgreSQL connection")
        checks.append(True)
    except Exception as e:
        print(f"❌ PostgreSQL connection: {e}")
        checks.append(False)

    # Check 3: Backblaze B2
    try:
        from app.services.b2_storage_service import B2StorageService
        print("✅ Backblaze B2 Service")
        checks.append(True)
    except Exception as e:
        print(f"❌ Backblaze B2 Service: {e}")
        checks.append(False)

    # Check 4: File Utils B2
    try:
        from app.core.file_utils import (
            upload_product_file_to_b2,
            download_product_file_from_b2,
            get_b2_presigned_url,
            delete_product_file_from_b2
        )
        print("✅ File Utils B2 functions")
        checks.append(True)
    except Exception as e:
        print(f"❌ File Utils B2 functions: {e}")
        checks.append(False)

    # Check 5: Handlers
    try:
        from app.integrations.telegram.handlers.buy_handlers import BuyHandlers
        from app.integrations.telegram.handlers.sell_handlers import SellHandlers
        from app.integrations.telegram.handlers.admin_handlers import AdminHandlers
        print("✅ Telegram Handlers")
        checks.append(True)
    except Exception as e:
        print(f"❌ Telegram Handlers: {e}")
        checks.append(False)

    # Check 6: IPN Server
    try:
        from app.integrations.ipn_server import app as ipn_app
        print("✅ IPN Server")
        checks.append(True)
    except Exception as e:
        print(f"❌ IPN Server: {e}")
        checks.append(False)

    # Check 7: Bot Main (syntax only, can't import without PostgreSQL)
    try:
        import ast
        with open('bot_mlt.py', 'r') as f:
            ast.parse(f.read())
        print("✅ Bot Main Syntax")
        checks.append(True)
    except Exception as e:
        print(f"❌ Bot Main Syntax: {e}")
        checks.append(False)

    print("\n" + "="*50)

    if all(checks):
        print("🎉 TOUS LES CHECKS RÉUSSIS !")
        print("✅ Le code est prêt pour le déploiement Railway")
        print("\n📝 Prochaines étapes:")
        print("   1. Créer projet PostgreSQL sur Railway")
        print("   2. Configurer variables d'environnement")
        print("   3. Déployer le bot")
        print("\n📖 Voir DEPLOYMENT_GUIDE.md pour les instructions complètes")
        return 0
    else:
        print("❌ CERTAINS CHECKS ONT ÉCHOUÉ")
        print(f"   {sum(checks)}/{len(checks)} checks réussis")
        print("\n⚠️  Corrigez les erreurs avant de déployer")
        return 1

def check_env_vars():
    """Vérifie les variables d'environnement critiques"""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    print("\n🔍 Vérification des variables d'environnement...\n")

    required_vars = {
        'TELEGRAM_TOKEN': 'Token Telegram Bot',
        'ADMIN_USER_ID': 'ID Admin Telegram',
        'B2_KEY_ID': 'Backblaze B2 Key ID',
        'B2_APPLICATION_KEY': 'Backblaze B2 App Key',
        'B2_BUCKET_NAME': 'Backblaze B2 Bucket',
        'B2_ENDPOINT': 'Backblaze B2 Endpoint',
    }

    optional_vars = {
        'NOWPAYMENTS_API_KEY': 'NowPayments API Key',
        'SMTP_USERNAME': 'SMTP Email',
    }

    missing_required = []
    missing_optional = []

    for var, description in required_vars.items():
        if os.getenv(var):
            print(f"✅ {var} ({description})")
        else:
            print(f"❌ {var} ({description}) - MANQUANT")
            missing_required.append(var)

    for var, description in optional_vars.items():
        if os.getenv(var):
            print(f"✅ {var} ({description})")
        else:
            print(f"⚠️  {var} ({description}) - Optionnel")
            missing_optional.append(var)

    print("\n" + "="*50)

    if missing_required:
        print(f"❌ Variables requises manquantes: {', '.join(missing_required)}")
        print("⚠️  Ajoutez-les dans .env avant de déployer")
        return 1
    else:
        print("✅ Toutes les variables requises sont présentes")
        if missing_optional:
            print(f"⚠️  Variables optionnelles manquantes: {', '.join(missing_optional)}")
        return 0

if __name__ == "__main__":
    print("="*50)
    print("   VÉRIFICATION PRÉ-DÉPLOIEMENT")
    print("="*50)
    print()

    # Check imports
    imports_ok = check_imports()

    # Check env vars
    env_ok = check_env_vars()

    print("\n" + "="*50)

    if imports_ok == 0 and env_ok == 0:
        print("🚀 LE BOT EST PRÊT POUR LE DÉPLOIEMENT !")
        print("\n📚 Lisez DEPLOYMENT_GUIDE.md pour déployer sur Railway")
        sys.exit(0)
    else:
        print("⚠️  CORRIGEZ LES ERREURS CI-DESSUS AVANT DE DÉPLOYER")
        sys.exit(1)
