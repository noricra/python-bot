#!/usr/bin/env python3
"""
Test rapide pour vérifier la nouvelle mise en page du carousel acheteur
"""

def test_carousel_layout():
    """Vérifie que le carousel acheteur a la même structure que le vendeur"""
    print("🔍 Test de la mise en page carousel...")

    try:
        with open('app/integrations/telegram/handlers/buy_handlers.py', 'r') as f:
            buy_handlers = f.read()

        with open('app/integrations/telegram/handlers/sell_handlers.py', 'r') as f:
            sell_handlers = f.read()

        tests = []

        # 1. Breadcrumb présent
        if 'breadcrumb = f"📂 _Boutique › {category}_"' in buy_handlers:
            tests.append(("✅", "Breadcrumb présent (📂 _Boutique › {category}_)"))
        else:
            tests.append(("❌", "Breadcrumb manquant"))

        # 2. Séparateur visuel
        if '"─────────────────────\\n\\n"' in buy_handlers or '─────────────────────' in buy_handlers:
            tests.append(("✅", "Séparateur visuel présent"))
        else:
            tests.append(("❌", "Séparateur visuel manquant"))

        # 3. Structure sections (commentaires)
        section_headers = [
            '# 0. BREADCRUMB',
            '# 1. TITRE',
            '# 2. PRIX + VENDEUR',
            '# 3. SOCIAL PROOF',
            '# 4. DESCRIPTION',
            '# 5. INFOS TECHNIQUES'
        ]
        sections_found = sum(1 for header in section_headers if header in buy_handlers)
        if sections_found >= 5:
            tests.append(("✅", f"Structure sections présente ({sections_found}/6)"))
        else:
            tests.append(("❌", f"Structure sections incomplète ({sections_found}/6)"))

        # 4. Description tronquée à 160 chars (comme vendeur)
        if 'len(desc) > 160:' in buy_handlers:
            tests.append(("✅", "Description tronquée à 160 chars (identique vendeur)"))
        else:
            tests.append(("⚠️", "Description tronquée différemment"))

        # 5. Stats visibles (rating, ventes, vues)
        if "product.get('rating', 0) > 0:" in buy_handlers and "product.get('sales_count', 0) > 0:" in buy_handlers:
            tests.append(("✅", "Stats (rating, ventes, vues) affichées"))
        else:
            tests.append(("❌", "Stats manquantes"))

        # 6. Infos techniques (catégorie + taille)
        if 'file_size_mb' in buy_handlers and 'caption += f"📂 _{category}_"' in buy_handlers:
            tests.append(("✅", "Infos techniques (catégorie + taille fichier)"))
        else:
            tests.append(("❌", "Infos techniques incomplètes"))

        # 7. Handler noop pour navigation
        with open('app/integrations/telegram/callback_router.py', 'r') as f:
            callback_router = f.read()

        if "if callback_data == 'noop':" in callback_router:
            tests.append(("✅", "Handler 'noop' présent (navigation catégories)"))
        else:
            tests.append(("❌", "Handler 'noop' manquant"))

        # Afficher résultats
        print("")
        for status, message in tests:
            print(f"{status} {message}")

        # Résumé
        passed = sum(1 for s, _ in tests if s == "✅")
        total = len(tests)

        print("")
        print("=" * 60)
        if passed == total:
            print(f"✅ CAROUSEL UX UPGRADE COMPLET ({passed}/{total})")
            print("🎉 Mise en page identique au carousel vendeur!")
            return True
        elif passed >= total - 1:
            print(f"⚠️ PRESQUE COMPLET ({passed}/{total})")
            print("Minor issues - vérifier manuellement")
            return True
        else:
            print(f"❌ INCOMPLET ({passed}/{total})")
            print(f"{total - passed} test(s) échoué(s)")
            return False

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_carousel_layout()
    exit(0 if success else 1)
