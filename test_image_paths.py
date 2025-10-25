#!/usr/bin/env python3
"""
Script de test pour vérifier la résolution des chemins d'images
"""
import sys
import os

# Ajouter le chemin du projet
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.settings import get_absolute_path
from app.domain.repositories.product_repo import ProductRepository
from app.core import settings as core_settings

def test_image_paths():
    """Teste la résolution des chemins d'images"""

    print("🧪 TEST DE RÉSOLUTION DES CHEMINS D'IMAGES")
    print("=" * 70)

    # 1. Test fonction get_absolute_path()
    print("\n📁 TEST 1: Fonction get_absolute_path()")
    print("-" * 70)

    test_paths = [
        "data/product_images/5229892870/TBF-68F38FB7-000001/thumb.jpg",
        "/absolute/path/test.jpg",
        None,
        ""
    ]

    for path in test_paths:
        result = get_absolute_path(path)
        print(f"Input:  {path!r}")
        print(f"Output: {result}")
        if result and os.path.isabs(result):
            print(f"✅ Path is absolute")
        elif result is None:
            print(f"⚪ None (expected for None/empty input)")
        else:
            print(f"❌ Path is NOT absolute!")
        print()

    # 2. Test avec vrais produits
    print("\n📦 TEST 2: Chemins produits réels")
    print("-" * 70)

    product_repo = ProductRepository(core_settings.DATABASE_PATH)
    products = product_repo.get_all_products(limit=3)

    for i, product in enumerate(products, 1):
        print(f"\nProduit #{i}: {product['title'][:40]}")
        print(f"  Product ID: {product['product_id']}")

        # Chemin relatif (stocké en DB)
        thumbnail_rel = product.get('thumbnail_path')
        cover_rel = product.get('cover_image_path')

        print(f"  📄 DB (relatif):")
        print(f"     thumbnail: {thumbnail_rel}")
        print(f"     cover:     {cover_rel}")

        # Conversion en absolu
        if thumbnail_rel:
            thumbnail_abs = get_absolute_path(thumbnail_rel)
            print(f"  📁 Absolu:")
            print(f"     thumbnail: {thumbnail_abs}")

            # Vérifier existence
            if os.path.exists(thumbnail_abs):
                size_kb = os.path.getsize(thumbnail_abs) / 1024
                print(f"     ✅ EXISTS ({size_kb:.1f} KB)")
            else:
                print(f"     ❌ NOT FOUND")
        else:
            print(f"  ⚪ Pas de thumbnail_path en DB")

    # 3. Test depuis différents répertoires
    print("\n\n🔄 TEST 3: Résolution depuis différents répertoires")
    print("-" * 70)

    original_dir = os.getcwd()
    print(f"Répertoire actuel: {original_dir}")

    # Simuler lancement depuis un autre répertoire
    test_dirs = [
        original_dir,  # Normal
        "/tmp",        # Depuis /tmp
        os.path.expanduser("~")  # Depuis home
    ]

    for test_dir in test_dirs:
        try:
            os.chdir(test_dir)
            print(f"\n📍 Depuis: {os.getcwd()}")

            test_path_rel = "data/product_images/5229892870/TBF-68F38FB7-000001/thumb.jpg"
            test_path_abs = get_absolute_path(test_path_rel)

            print(f"   Relatif: {test_path_rel}")
            print(f"   Absolu:  {test_path_abs}")

            if os.path.exists(test_path_abs):
                print(f"   ✅ File EXISTS (résolution correcte!)")
            else:
                print(f"   ❌ File NOT FOUND")

        except Exception as e:
            print(f"   ❌ Erreur: {e}")

    # Retour au répertoire original
    os.chdir(original_dir)

    print("\n" + "=" * 70)
    print("✅ Tests terminés!")
    print("\n💡 RÉSULTAT ATTENDU:")
    print("   • get_absolute_path() doit toujours retourner un chemin absolu")
    print("   • Les fichiers doivent être trouvés quel que soit le répertoire courant")
    print("   • Aucun 'Image not found' ne doit apparaître dans les logs du bot")

if __name__ == "__main__":
    try:
        test_image_paths()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
