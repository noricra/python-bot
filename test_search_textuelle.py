#!/usr/bin/env python3
"""
Script de test pour la recherche textuelle
"""
import sys
import os

# Ajouter le chemin du projet
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.domain.repositories.product_repo import ProductRepository
from app.core import settings as core_settings

def test_search():
    """Teste la recherche textuelle"""

    print("🔍 TEST RECHERCHE TEXTUELLE")
    print("=" * 70)

    # Initialiser le repository
    product_repo = ProductRepository(core_settings.DATABASE_PATH)

    # Tests de recherche
    test_queries = [
        "trading",
        "marketing",
        "finance",
        "formation",
        "crypto",
        "guide",
        "TBF-68FBF8EF-000013",  # Test recherche par ID
        "ebook",
        "python"
    ]

    for query in test_queries:
        print(f"\n🔎 Recherche: \"{query}\"")
        print("-" * 70)

        results = product_repo.search_products(query, limit=10)

        if results:
            print(f"✅ {len(results)} résultat(s) trouvé(s)\n")
            for i, product in enumerate(results, 1):
                print(f"   {i}. {product['title'][:50]}")
                print(f"      ID: {product['product_id']}")
                print(f"      Prix: {product['price_eur']}€")
                print(f"      Ventes: {product.get('sales_count', 0)}")
                print(f"      Rating: {product.get('rating', 0):.1f}/5")
                print()
        else:
            print(f"❌ Aucun résultat\n")

    print("=" * 70)
    print("\n✅ Tests terminés!")

    # Test stratégie ID vs texte
    print("\n\n📋 TEST STRATÉGIE DE RECHERCHE")
    print("=" * 70)

    test_cases = [
        ("TBF-68FBF8EF-000013", "Devrait chercher par ID"),
        ("trading crypto", "Devrait chercher par texte"),
        ("guide-complet", "Devrait chercher par texte (contient tiret mais pas TBF)"),
    ]

    for search_input, expected_strategy in test_cases:
        print(f"\n🧪 Input: \"{search_input}\"")
        print(f"   Stratégie attendue: {expected_strategy}")

        # Simuler la logique de process_product_search
        product_id_upper = search_input.strip().upper()
        if 'TBF-' in product_id_upper or '-' in search_input:
            print(f"   ✅ Essai recherche par ID: {product_id_upper}")
        else:
            print(f"   ✅ Recherche textuelle directe")

        results = product_repo.search_products(search_input, limit=3)
        if results:
            print(f"   📊 {len(results)} résultats textuels disponibles")
        else:
            print(f"   📊 Aucun résultat textuel")

if __name__ == "__main__":
    try:
        test_search()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
