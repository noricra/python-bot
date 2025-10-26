#!/usr/bin/env python3
"""
Script de test pour le workflow vendeur simplifié (email + Solana uniquement)
"""
import sys
import os

# Ajouter le chemin du projet
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.seller_service import SellerService
from app.core import settings as core_settings

def test_simplified_seller_creation():
    """Teste la création de compte vendeur simplifié"""

    print("🧪 TEST CRÉATION VENDEUR SIMPLIFIÉ")
    print("=" * 70)

    seller_service = SellerService(core_settings.DATABASE_PATH)

    # Test 1: Création compte vendeur valide
    print("\n✅ Test 1: Création compte vendeur valide")
    print("-" * 70)

    test_user_id = 999999001  # User ID de test
    test_seller_name = "TestVendeur"  # Du Telegram
    test_email = "test_vendor@example.com"
    test_solana = "DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK"  # Adresse Solana valide

    result = seller_service.create_seller_account_simple(
        user_id=test_user_id,
        seller_name=test_seller_name,
        email=test_email,
        solana_address=test_solana
    )

    print(f"   Résultat: {result}")
    if result['success']:
        print("   ✅ Compte vendeur créé avec succès!")

        # Vérifier que le vendeur existe
        seller_info = seller_service.get_seller_info(test_user_id)
        print(f"   📊 Info vendeur: {seller_info}")

        # Vérifier authentification
        is_authenticated = seller_service.authenticate_seller(test_user_id)
        print(f"   🔐 Authentifié: {is_authenticated}")
    else:
        print(f"   ❌ Échec: {result.get('error')}")

    # Test 2: Email invalide
    print("\n❌ Test 2: Email invalide (devrait échouer)")
    print("-" * 70)

    result = seller_service.create_seller_account_simple(
        user_id=999999002,
        seller_name="TestVendeur2",
        email="email_sans_arobase",
        solana_address=test_solana
    )

    print(f"   Résultat: {result}")
    if not result['success']:
        print(f"   ✅ Échec attendu: {result.get('error')}")
    else:
        print("   ❌ ERREUR: Devrait avoir échoué!")

    # Test 3: Adresse Solana invalide
    print("\n❌ Test 3: Adresse Solana invalide (devrait échouer)")
    print("-" * 70)

    result = seller_service.create_seller_account_simple(
        user_id=999999003,
        seller_name="TestVendeur3",
        email="test3@example.com",
        solana_address="INVALID_SOLANA_ADDRESS"
    )

    print(f"   Résultat: {result}")
    if not result['success']:
        print(f"   ✅ Échec attendu: {result.get('error')}")
    else:
        print("   ❌ ERREUR: Devrait avoir échoué!")

    # Test 4: Email en double
    print("\n❌ Test 4: Email déjà utilisé (devrait échouer)")
    print("-" * 70)

    result = seller_service.create_seller_account_simple(
        user_id=999999004,
        seller_name="TestVendeur4",
        email=test_email,  # Même email que Test 1
        solana_address=test_solana
    )

    print(f"   Résultat: {result}")
    if not result['success']:
        print(f"   ✅ Échec attendu: {result.get('error')}")
    else:
        print("   ❌ ERREUR: Devrait avoir échoué!")

    # Test 5: Vérifier que password_hash et seller_bio sont NULL
    print("\n🔍 Test 5: Vérifier champs NULL (pas de password, pas de bio)")
    print("-" * 70)

    import sqlite3
    from app.core import get_sqlite_connection

    conn = get_sqlite_connection(core_settings.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT seller_name, email, seller_solana_address,
               seller_bio, password_hash, password_salt
        FROM users
        WHERE user_id = ?
    ''', (test_user_id,))

    row = cursor.fetchone()
    conn.close()

    if row:
        print(f"   Nom: {row[0]}")
        print(f"   Email: {row[1]}")
        print(f"   Solana: {row[2]}")
        print(f"   Bio: {row[3]} (devrait être NULL)")
        print(f"   Password Hash: {row[4]} (devrait être NULL)")
        print(f"   Password Salt: {row[5]} (devrait être NULL)")

        if row[3] is None and row[4] is None and row[5] is None:
            print("   ✅ Tous les champs optionnels sont NULL comme prévu!")
        else:
            print("   ❌ ERREUR: Certains champs devraient être NULL!")
    else:
        print("   ❌ Utilisateur non trouvé!")

    print("\n" + "=" * 70)
    print("✅ Tests terminés!")

    # Nettoyage
    print("\n🧹 Nettoyage des données de test...")
    conn = get_sqlite_connection(core_settings.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE user_id BETWEEN 999999001 AND 999999010')
    conn.commit()
    conn.close()
    print("✅ Nettoyage terminé!")

if __name__ == "__main__":
    try:
        test_simplified_seller_creation()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
