#!/usr/bin/env python3
"""
Script de test rapide pour BUYER_WORKFLOW_V2
Vérifie que tous les imports et classes fonctionnent
"""

import sys

def test_imports():
    """Test tous les imports nécessaires"""
    print("🔍 Test des imports...")

    try:
        from app.domain.repositories.review_repo import ReviewRepository
        print("✅ ReviewRepository importé")
    except Exception as e:
        print(f"❌ Erreur ReviewRepository: {e}")
        return False

    try:
        from app.integrations.telegram.handlers.buy_handlers import BuyHandlers
        print("✅ BuyHandlers importé")
    except Exception as e:
        print(f"❌ Erreur BuyHandlers: {e}")
        return False

    try:
        from app.integrations.telegram.callback_router import CallbackRouter
        print("✅ CallbackRouter importé")
    except Exception as e:
        print(f"❌ Erreur CallbackRouter: {e}")
        return False

    return True

def test_review_repo():
    """Test ReviewRepository fonctionne avec DB"""
    print("\n📊 Test ReviewRepository...")

    try:
        from app.domain.repositories.review_repo import ReviewRepository

        repo = ReviewRepository('marketplace.db')
        print("✅ ReviewRepository initialisé")

        # Test get_review_count (should not crash even if table empty)
        count = repo.get_review_count('TEST-PRODUCT')
        print(f"✅ get_review_count() fonctionne (count={count})")

        # Test get_product_rating_summary
        summary = repo.get_product_rating_summary('TEST-PRODUCT')
        print(f"✅ get_product_rating_summary() fonctionne")
        print(f"   Average rating: {summary['average_rating']}")
        print(f"   Total reviews: {summary['total_reviews']}")

        return True
    except Exception as e:
        print(f"❌ Erreur test ReviewRepository: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_buy_handlers_init():
    """Test BuyHandlers peut être initialisé avec review_repo"""
    print("\n🛒 Test BuyHandlers avec review_repo...")

    try:
        from app.integrations.telegram.handlers.buy_handlers import BuyHandlers
        from app.domain.repositories.product_repo import ProductRepository
        from app.domain.repositories.order_repo import OrderRepository
        from app.domain.repositories.review_repo import ReviewRepository
        from app.services.payment_service import PaymentService

        product_repo = ProductRepository('marketplace.db')
        order_repo = OrderRepository('marketplace.db')
        review_repo = ReviewRepository('marketplace.db')
        payment_service = PaymentService()

        buy_handlers = BuyHandlers(product_repo, order_repo, payment_service, review_repo)
        print("✅ BuyHandlers initialisé avec review_repo")

        # Check helpers exist
        assert hasattr(buy_handlers, '_build_product_caption'), "❌ Helper _build_product_caption manquant"
        assert hasattr(buy_handlers, '_get_product_image_or_placeholder'), "❌ Helper _get_product_image_or_placeholder manquant"
        assert hasattr(buy_handlers, '_build_product_keyboard'), "❌ Helper _build_product_keyboard manquant"
        print("✅ Helpers internes présents")

        # Check V2 functions exist
        assert hasattr(buy_handlers, 'show_product_reviews'), "❌ Fonction show_product_reviews manquante"
        assert hasattr(buy_handlers, 'collapse_product_details'), "❌ Fonction collapse_product_details manquante"
        assert hasattr(buy_handlers, 'navigate_categories'), "❌ Fonction navigate_categories manquante"
        print("✅ Fonctions V2 présentes")

        return True
    except Exception as e:
        print(f"❌ Erreur test BuyHandlers: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_callback_routes():
    """Test que les nouveaux callbacks sont bien enregistrés"""
    print("\n🔀 Test Callback Router...")

    try:
        # Just check the file has the new routes
        with open('app/integrations/telegram/callback_router.py', 'r') as f:
            content = f.read()

        assert 'reviews_' in content, "❌ Callback 'reviews_' manquant"
        assert 'collapse_' in content, "❌ Callback 'collapse_' manquant"
        assert 'navcat_' in content, "❌ Callback 'navcat_' manquant"
        assert 'V2 WORKFLOW CALLBACKS' in content, "❌ Section V2 WORKFLOW manquante"

        print("✅ Tous les nouveaux callbacks présents dans router")
        return True
    except Exception as e:
        print(f"❌ Erreur test callbacks: {e}")
        return False

def test_crypto_layout():
    """Test que le layout crypto a été modifié"""
    print("\n💰 Test Layout Crypto...")

    try:
        with open('app/integrations/telegram/handlers/buy_handlers.py', 'r') as f:
            content = f.read()

        assert 'V2 SPEC: Layout crypto en grille 2x2' in content, "❌ Commentaire grille 2x2 manquant"
        assert '₿ BTC' in content and '⟠ ETH' in content, "❌ Layout BTC/ETH manquant"
        assert '◎ SOLANA' in content, "❌ Layout Solana pleine largeur manquant"
        assert 'USDC' in content and 'USDT' in content, "❌ Layout stablecoins manquant"

        print("✅ Layout crypto en grille 2x2 implémenté")
        return True
    except Exception as e:
        print(f"❌ Erreur test layout crypto: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("TEST BUYER WORKFLOW V2 - VÉRIFICATION POST-IMPLÉMENTATION")
    print("=" * 60)

    results = []

    results.append(("Imports", test_imports()))
    results.append(("ReviewRepository", test_review_repo()))
    results.append(("BuyHandlers Init", test_buy_handlers_init()))
    results.append(("Callback Routes", test_callback_routes()))
    results.append(("Layout Crypto", test_crypto_layout()))

    print("\n" + "=" * 60)
    print("RÉSULTATS")
    print("=" * 60)

    all_passed = True
    for test_name, result in results:
        status = "✅ PASSÉ" if result else "❌ ÉCHOUÉ"
        print(f"{test_name:.<40} {status}")
        if not result:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 TOUS LES TESTS PASSENT !")
        print("✅ Le workflow V2 est prêt à être testé manuellement")
        print("\n📝 Prochaines étapes:")
        print("   1. Lancer le bot: python3 bot_mlt.py")
        print("   2. Tester /start → Acheter → Parcourir catégories")
        print("   3. Tester navigation carousel avec ⬅️ ➡️")
        print("   4. Tester page Détails → Avis")
        print("   5. Tester bouton Réduire")
        print("   6. Tester sélection crypto (grille 2x2)")
        return 0
    else:
        print("\n⚠️ CERTAINS TESTS ONT ÉCHOUÉ")
        print("❌ Vérifiez les erreurs ci-dessus avant de tester le bot")
        return 1

if __name__ == '__main__':
    sys.exit(main())
