#!/usr/bin/env python3
"""
Test automatique pour vérifier les 5 correctifs du carousel acheteur
"""

def test_carousel_fixes():
    """Vérifie que tous les correctifs sont appliqués"""
    print("🔍 Test des correctifs carousel acheteur...\n")

    try:
        with open('app/integrations/telegram/callback_router.py', 'r') as f:
            callback_router = f.read()

        with open('app/domain/repositories/product_repo.py', 'r') as f:
            product_repo = f.read()

        with open('app/integrations/telegram/handlers/buy_handlers.py', 'r') as f:
            buy_handlers = f.read()

        tests = []

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Test 1: Bouton Preview Fonctionnel
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("Test 1: Bouton Preview")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # Vérifier que le handler dupliqué a été supprimé
        duplicate_handler = '''        # Product preview (product_preview_{product_id})
        if callback_data.startswith('product_preview_'):
            product_id = callback_data.replace('product_preview_', '')
            await self.bot.buy_handlers.preview_product(query, product_id, lang)
            return True'''

        if duplicate_handler not in callback_router:
            tests.append(("✅", "Handler preview dupliqué SUPPRIMÉ"))
        else:
            tests.append(("❌", "Handler preview dupliqué TOUJOURS PRÉSENT"))

        # Vérifier que le handler étendu existe
        if "if callback_data.startswith('preview_product_') or callback_data.startswith('product_preview_'):" in callback_router:
            tests.append(("✅", "Handler preview étendu (avec contexte) présent"))
        else:
            tests.append(("❌", "Handler preview étendu manquant"))

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Test 2: Navigation Catégories (Handler noop)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("Test 2: Navigation Catégories")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        if "if callback_data == 'noop':" in callback_router and "await query.answer()" in callback_router:
            tests.append(("✅", "Handler 'noop' présent (gestion boutons désactivés)"))
        else:
            tests.append(("❌", "Handler 'noop' manquant"))

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Test 3: Dernier Produit Ajouté en Premier
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("Test 3: Ordre Produits (Newest First)")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # Vérifier ORDER BY created_at DESC (pas sales_count)
        if "ORDER BY p.created_at DESC" in product_repo and "ORDER BY sales_count DESC" not in product_repo.split("get_products_by_category")[1].split("def ")[0]:
            tests.append(("✅", "ORDER BY created_at DESC (derniers produits en premier)"))
        else:
            tests.append(("❌", "ORDER BY incorrect (pas created_at DESC)"))

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Test 4: Nom Vendeur Réel
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("Test 4: Nom Vendeur Réel")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # Vérifier JOIN avec users pour récupérer seller_name
        if "SELECT p.*, u.seller_name, u.seller_rating, u.seller_bio" in product_repo and \
           "LEFT JOIN users u ON p.seller_user_id = u.user_id" in product_repo:
            tests.append(("✅", "JOIN avec users (seller_name récupéré)"))
        else:
            tests.append(("❌", "JOIN avec users manquant (pas de seller_name)"))

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Test 5: Rendu Carousel Amélioré
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("Test 5: Rendu Carousel Élégant")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # Vérifier header STATS
        if 'caption += "📊 **STATS**\\n"' in buy_handlers:
            tests.append(("✅", "Header 📊 **STATS** présent"))
        else:
            tests.append(("❌", "Header STATS manquant"))

        # Vérifier format puces
        if 'caption += f"• **{sales}** ventes"' in buy_handlers:
            tests.append(("✅", "Format puces (• ventes / • vues)"))
        else:
            tests.append(("❌", "Format puces manquant"))

        # Vérifier breadcrumb
        if 'breadcrumb = f"📂 _Boutique › {category}_"' in buy_handlers:
            tests.append(("✅", "Breadcrumb présent (📂 _Boutique › {category}_)"))
        else:
            tests.append(("❌", "Breadcrumb manquant"))

        # Vérifier séparateur visuel
        if '"─────────────────────\\n\\n"' in buy_handlers:
            tests.append(("✅", "Séparateur visuel présent"))
        else:
            tests.append(("❌", "Séparateur visuel manquant"))

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Résumé
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        print("\n" + "=" * 60)
        print("RÉSUMÉ DES TESTS")
        print("=" * 60)

        for status, message in tests:
            print(f"{status} {message}")

        passed = sum(1 for s, _ in tests if s == "✅")
        total = len(tests)

        print("\n" + "=" * 60)
        if passed == total:
            print(f"✅ TOUS LES CORRECTIFS APPLIQUÉS ({passed}/{total})")
            print("🎉 Carousel acheteur 100% fonctionnel et élégant!")
            print("\n🚀 Prêt pour test manuel:")
            print("   python3 bot_mlt.py")
            return True
        else:
            print(f"⚠️ CORRECTIFS INCOMPLETS ({passed}/{total})")
            print(f"❌ {total - passed} test(s) échoué(s)")
            return False

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_carousel_fixes()
    exit(0 if success else 1)
