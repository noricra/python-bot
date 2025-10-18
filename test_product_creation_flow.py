#!/usr/bin/env python3
"""
Test du flow complet de création de produit étape par étape
Simule exactement ce qui se passe quand un utilisateur crée un produit
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.state_manager import StateManager
from app.core.settings import settings

def test_product_creation_state_flow():
    """Simule le flow de création de produit étape par étape"""

    print("\n" + "="*60)
    print("TEST: Product Creation State Flow")
    print("="*60)

    state_manager = StateManager()
    test_user_id = 999999  # Test user

    print(f"\n📋 Simulating product creation for user {test_user_id}")

    # Step 1: Initier l'ajout de produit
    print("\n1️⃣ STEP: add_product_prompt()")
    state_manager.update_state(
        test_user_id,
        adding_product=True,
        step='title',
        product_data={},
        lang='fr'
    )
    current_state = state_manager.get_state(test_user_id)
    print(f"   État: {current_state}")
    assert current_state['adding_product'] == True
    assert current_state['step'] == 'title'
    print("   ✅ OK")

    # Step 2: Titre
    print("\n2️⃣ STEP: process_product_addition(title)")
    product_data = current_state.get('product_data', {})
    product_data['title'] = "Guide Trading Crypto 2025"
    current_state['step'] = 'description'
    state_manager.update_state(test_user_id, **current_state)
    current_state = state_manager.get_state(test_user_id)
    print(f"   État: {current_state}")
    assert current_state['step'] == 'description'
    print("   ✅ OK")

    # Step 3: Description
    print("\n3️⃣ STEP: process_product_addition(description)")
    product_data['description'] = "Formation complète sur le trading crypto"
    current_state['step'] = 'category'
    state_manager.update_state(test_user_id, **current_state)
    current_state = state_manager.get_state(test_user_id)
    print(f"   État: {current_state}")
    assert current_state['step'] == 'category'
    print("   ✅ OK")

    # Step 4: Catégorie (via callback)
    print("\n4️⃣ STEP: handle_category_selection('Finance & Crypto')")
    product_data['category'] = "Finance & Crypto"
    current_state['step'] = 'price'
    state_manager.update_state(test_user_id, **current_state)
    current_state = state_manager.get_state(test_user_id)
    print(f"   État: {current_state}")
    assert current_state['step'] == 'price'
    print("   ✅ OK")

    # Step 5: Prix
    print("\n5️⃣ STEP: process_product_addition(price='49.99')")
    print("   📝 Code dans sell_handlers.py:492-516")
    product_data['price_eur'] = 49.99
    product_data['price_usd'] = 49.99 * 1.1  # Mock exchange rate
    current_state['step'] = 'cover_image'  # ← CRITIQUE
    current_state['product_data'] = product_data
    state_manager.update_state(test_user_id, **current_state)
    current_state = state_manager.get_state(test_user_id)
    print(f"   État: {current_state}")
    print(f"   adding_product: {current_state.get('adding_product')}")
    print(f"   step: {current_state.get('step')}")
    print(f"   product_data: {current_state.get('product_data')}")

    # VÉRIFICATION CRITIQUE
    if current_state.get('adding_product') and current_state.get('step') == 'cover_image':
        print("   ✅ État correct pour upload photo!")
        print("\n   📸 Le bot devrait maintenant accepter:")
        print("      - Photos (MessageHandler filters.PHOTO)")
        print("      - Callback 'skip_cover_image'")
    else:
        print(f"   ❌ PROBLÈME: step='{current_state.get('step')}' (attendu 'cover_image')")
        return False

    # Step 6: Upload photo (simulé)
    print("\n6️⃣ STEP: process_cover_image_upload(photo)")
    print("   Condition handler: adding_product=True AND step='cover_image'")

    # Vérifier que le handler photo accepterait cette requête
    would_accept = current_state.get('adding_product') and current_state.get('step') == 'cover_image'
    print(f"   Handler accepterait: {would_accept}")

    if would_accept:
        print("   ✅ Le handler photo ACCEPTERAIT cette requête")

        # Simuler upload
        product_data['cover_image_path'] = 'data/product_images/999999/TEMP_abc123/cover.jpg'
        product_data['thumbnail_path'] = 'data/product_images/999999/TEMP_abc123/thumb.jpg'
        product_data['temp_product_id'] = 'TEMP_abc123'
        current_state['step'] = 'file'
        current_state['product_data'] = product_data
        state_manager.update_state(test_user_id, **current_state)
        print("   ✅ Photo uploadée, transition vers step='file'")
    else:
        print("   ❌ Le handler photo REJETTERAIT cette requête")
        return False

    # Step 7: Skip photo (alternative)
    print("\n7️⃣ STEP ALTERNATIF: handle_skip_cover_image()")
    print("   Si user clique 'skip', step='file' directement")

    # Step 8: Upload fichier final
    print("\n8️⃣ STEP: process_file_upload(document)")
    print("   Condition: adding_product=True AND step='file'")
    current_state = state_manager.get_state(test_user_id)
    would_accept = current_state.get('adding_product') and current_state.get('step') == 'file'
    print(f"   Handler accepterait: {would_accept}")

    if would_accept:
        print("   ✅ OK - Création produit finale")
    else:
        print(f"   ❌ REJETÉ - step='{current_state.get('step')}'")
        return False

    # Cleanup
    state_manager.reset_state(test_user_id)

    print("\n" + "="*60)
    print("✅ FLOW COMPLET VALIDÉ")
    print("="*60)
    print("\n💡 Le problème que vous rencontrez peut venir de:")
    print("   1. StateManager non partagé entre les appels")
    print("   2. État perdu entre étapes (bot_instance.state_manager différent)")
    print("   3. update_state() non appelé après modification")
    print("   4. État écrasé par un autre handler")

    return True


def test_state_manager_persistence():
    """Vérifie que StateManager garde bien l'état entre les appels"""
    print("\n" + "="*60)
    print("TEST: StateManager Persistence")
    print("="*60)

    sm1 = StateManager()
    sm2 = StateManager()

    test_user = 123456

    # Instance 1 définit l'état
    sm1.update_state(test_user, adding_product=True, step='price', test_value=42)

    # Instance 2 récupère l'état
    state = sm2.get_state(test_user)

    print(f"\nÉtat défini par sm1: adding_product=True, step='price', test_value=42")
    print(f"État récupéré par sm2: {state}")

    if state.get('adding_product') and state.get('step') == 'price' and state.get('test_value') == 42:
        print("✅ StateManager partage bien l'état entre instances")
        return True
    else:
        print("❌ PROBLÈME: StateManager ne partage PAS l'état")
        print("   → Chaque instance a son propre dict user_states")
        print("   → Solution: Utiliser une instance UNIQUE dans bot_instance")
        return False


if __name__ == "__main__":
    print("🧪 DIAGNOSTIC: Product Creation Flow Phase 1")
    print("="*60)

    success1 = test_product_creation_state_flow()
    success2 = test_state_manager_persistence()

    if success1 and success2:
        print("\n✅ Tous les tests passés - Le flow est correct en théorie")
        print("\n📝 Si vous rencontrez toujours l'erreur:")
        print("   1. Vérifiez les logs du bot (ligne 670 dans bot_mlt.py)")
        print("   2. L'état devrait afficher: adding_product=True, step='cover_image'")
        print("   3. Si step != 'cover_image', c'est que update_state() n'a pas été appelé")
    else:
        print("\n❌ Des problèmes ont été détectés")
