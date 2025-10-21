#!/usr/bin/env python3
"""
Test rapide pour vérifier que le circuit fermé est complet
"""

def test_closed_circuit():
    """Vérifie que tous les callbacks passent le contexte correctement"""
    print("🔍 Test du circuit fermé...")

    try:
        with open('app/integrations/telegram/handlers/buy_handlers.py', 'r') as f:
            buy_handlers = f.read()

        with open('app/integrations/telegram/callback_router.py', 'r') as f:
            callback_router = f.read()

        tests = []

        # 1. show_product_reviews accepte category_key et index
        if 'async def show_product_reviews(self, bot, query, product_id: str, page: int = 0, lang: str = \'fr\', category_key: str = None, index: int = None)' in buy_handlers:
            tests.append(("✅", "show_product_reviews() accepte contexte"))
        else:
            tests.append(("❌", "show_product_reviews() signature incorrecte"))

        # 2. Reviews ACHETER button passe contexte
        if 'buy_callback = f\'buy_product_{product_id}_{category_key}_{index}\'' in buy_handlers and 'show_product_reviews' in buy_handlers[:buy_handlers.index('buy_callback = f\'buy_product_{product_id}_{category_key}_{index}\'')]:
            tests.append(("✅", "Reviews ACHETER passe contexte"))
        else:
            tests.append(("⚠️", "Reviews ACHETER contexte à vérifier"))

        # 3. Reviews Précédent passe contexte
        if 'back_callback = f\'product_details_{product_id}_{category_key}_{index}\'' in buy_handlers:
            tests.append(("✅", "Reviews Précédent passe contexte"))
        else:
            tests.append(("❌", "Reviews Précédent ne passe pas contexte"))

        # 4. Avis button dans Détails passe contexte
        if 'reviews_callback = f\'reviews_{product_id}_0_{category_key}_{index}\'' in buy_handlers:
            tests.append(("✅", "Détails → Avis passe contexte"))
        else:
            tests.append(("❌", "Détails → Avis ne passe pas contexte"))

        # 5. Preview button passe contexte
        if 'preview_callback = f\'product_preview_{product_id}_{category_key}_{index}\'' in buy_handlers:
            tests.append(("✅", "Détails → Preview passe contexte"))
        else:
            tests.append(("❌", "Détails → Preview ne passe pas contexte"))

        # 6. Réduire button existe
        if 'Réduire' in buy_handlers and 'collapse_' in buy_handlers:
            tests.append(("✅", "Bouton Réduire implémenté"))
        else:
            tests.append(("❌", "Bouton Réduire manquant"))

        # 7. Callback router parse reviews étendu
        if 'if len(parts) >= 4:' in callback_router and 'reviews_' in callback_router:
            tests.append(("✅", "Router parse reviews_{id}_{page}_{cat}_{idx}"))
        else:
            tests.append(("❌", "Router ne parse pas format étendu"))

        # 8. Acheter → Carousel (collapse)
        if 'buy_product_{product_id}_{category_key}_{index}' in buy_handlers:
            tests.append(("✅", "Carousel → Acheter passe contexte"))
        else:
            tests.append(("❌", "Carousel → Acheter ne passe pas contexte"))

        # Afficher résultats
        print("")
        for status, message in tests:
            print(f"{status} {message}")

        # Résumé
        passed = sum(1 for s, _ in tests if s == "✅")
        total = len(tests)

        print("")
        print("=" * 50)
        if passed == total:
            print(f"✅ CIRCUIT FERMÉ COMPLET ({passed}/{total})")
            print("🎉 Tous les tests passent!")
            return True
        else:
            print(f"⚠️ CIRCUIT INCOMPLET ({passed}/{total})")
            print(f"❌ {total - passed} test(s) échoué(s)")
            return False

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_closed_circuit()
    exit(0 if success else 1)
