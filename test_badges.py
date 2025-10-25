#!/usr/bin/env python3
"""
Script de test pour vérifier l'affichage des badges automatiques
"""
import sys
import os
from datetime import datetime, timedelta

# Ajouter le chemin du projet
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.domain.repositories.product_repo import ProductRepository
from app.core import settings as core_settings

def test_badges():
    """Teste la génération et l'affichage des badges"""

    print("🧪 TEST DES BADGES AUTOMATIQUES")
    print("=" * 60)

    # Initialiser le repository
    product_repo = ProductRepository(core_settings.DATABASE_PATH)

    # Récupérer quelques produits
    products = product_repo.get_all_products(limit=5)

    if not products:
        print("❌ Aucun produit trouvé dans la base de données")
        return

    print(f"\n✅ {len(products)} produits trouvés\n")

    # Fonction de génération de badges (copie de buy_handlers.py)
    def get_product_badges(product):
        """Generate badges for product based on stats"""
        badges = []

        # Best seller (50+ sales)
        if product.get('sales_count', 0) >= 50:
            badges.append("🏆 Best-seller")

        # Nouveauté (< 7 days)
        created_at = product.get('created_at')
        if created_at:
            try:
                if isinstance(created_at, str):
                    created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    created_date = created_at

                days_since_creation = (datetime.now() - created_date).days
                if days_since_creation < 7:
                    badges.append("🆕 Nouveau")
            except Exception as e:
                pass

        # Top rated (4.5+ stars with 10+ reviews)
        if product.get('rating', 0) >= 4.5 and product.get('reviews_count', 0) >= 10:
            badges.append("⭐ Top noté")

        # Trending (high views recently)
        if product.get('views_count', 0) >= 100:
            badges.append("🔥 Populaire")

        return badges

    # Tester chaque produit
    for i, product in enumerate(products, 1):
        print(f"📦 PRODUIT #{i}: {product['title'][:50]}")
        print(f"   ID: {product['product_id']}")
        print(f"   Stats:")
        print(f"     • Ventes: {product.get('sales_count', 0)}")
        print(f"     • Rating: {product.get('rating', 0):.1f}/5 ({product.get('reviews_count', 0)} avis)")
        print(f"     • Vues: {product.get('views_count', 0)}")
        print(f"     • Créé: {product.get('created_at', 'N/A')}")

        # Générer badges
        badges = get_product_badges(product)

        if badges:
            badge_line = " | ".join(badges)
            print(f"   ✨ Badges: {badge_line}")
        else:
            print(f"   ⚪ Badges: Aucun (conditions non remplies)")

        print()

    print("=" * 60)
    print("\n📋 CRITÈRES DES BADGES:")
    print("   🏆 Best-seller: 50+ ventes")
    print("   🆕 Nouveau: Créé il y a moins de 7 jours")
    print("   ⭐ Top noté: Rating 4.5+/5 ET 10+ avis")
    print("   🔥 Populaire: 100+ vues")
    print("\n💡 Pour tester avec de vraies données:")
    print("   1. Créer un produit récent (badge 🆕)")
    print("   2. Simuler 50+ ventes sur un produit (badge 🏆)")
    print("   3. Ajouter 10+ reviews avec rating 4.5+ (badge ⭐)")
    print("   4. Produits avec 100+ vues auront badge 🔥")

if __name__ == "__main__":
    try:
        test_badges()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
