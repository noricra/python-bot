#!/usr/bin/env python3
"""
🔍 CHECKPOINT INTÉGRATION PHASE 1
Détection de problèmes dans le flow complet de création de produit avec images
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

def check_database_init():
    """✅ Check 1: database_init.py définit bien les colonnes"""
    print("\n" + "="*60)
    print("CHECK 1: database_init.py - Définition Schéma")
    print("="*60)

    from app.core.database_init import DatabaseInitService

    # Vérifier si la méthode _create_products_table contient les colonnes
    import inspect
    source = inspect.getsource(DatabaseInitService._create_products_table)

    issues = []

    if 'cover_image_path TEXT' in source:
        print("   ✅ cover_image_path défini dans CREATE TABLE")
    else:
        print("   ❌ cover_image_path MANQUANT dans CREATE TABLE")
        issues.append("cover_image_path not in CREATE TABLE")

    if 'thumbnail_path TEXT' in source:
        print("   ✅ thumbnail_path défini dans CREATE TABLE")
    else:
        print("   ❌ thumbnail_path MANQUANT dans CREATE TABLE")
        issues.append("thumbnail_path not in CREATE TABLE")

    # Vérifier si la migration existe
    migrate_source = inspect.getsource(DatabaseInitService._migrate_products_table)

    if 'cover_image_path' in migrate_source and 'thumbnail_path' in migrate_source:
        print("   ✅ Migration _migrate_products_table présente")
    else:
        print("   ❌ Migration _migrate_products_table INCOMPLETE")
        issues.append("Migration missing image columns")

    return len(issues) == 0, issues


def check_product_repo_insert():
    """🚨 Check 2: product_repo.insert_product() intègre les colonnes images"""
    print("\n" + "="*60)
    print("CHECK 2: product_repo.py - INSERT Product Query")
    print("="*60)

    from app.domain.repositories.product_repo import ProductRepository
    import inspect

    source = inspect.getsource(ProductRepository.insert_product)

    issues = []

    # Vérifier si l'INSERT inclut cover_image_path et thumbnail_path
    if 'cover_image_path' in source:
        print("   ✅ cover_image_path dans INSERT query")
    else:
        print("   🚨 PROBLÈME CRITIQUE: cover_image_path ABSENT de INSERT")
        issues.append("insert_product() ne gère pas cover_image_path")

    if 'thumbnail_path' in source:
        print("   ✅ thumbnail_path dans INSERT query")
    else:
        print("   🚨 PROBLÈME CRITIQUE: thumbnail_path ABSENT de INSERT")
        issues.append("insert_product() ne gère pas thumbnail_path")

    # Vérifier le nombre de colonnes dans INSERT
    if 'INSERT INTO products' in source:
        # Extraire la liste des colonnes
        start = source.find('(product_id')
        end = source.find('VALUES', start)
        columns_section = source[start:end] if start != -1 and end != -1 else ""

        print(f"\n   📋 Colonnes dans INSERT:")
        print(f"      {columns_section[:200]}...")

    return len(issues) == 0, issues


def check_product_repo_create():
    """🚨 Check 3: product_repo.create_product() passe les chemins d'images"""
    print("\n" + "="*60)
    print("CHECK 3: product_repo.py - create_product() Method")
    print("="*60)

    from app.domain.repositories.product_repo import ProductRepository
    import inspect

    source = inspect.getsource(ProductRepository.create_product)

    issues = []

    # Vérifier si create_product() récupère les chemins depuis product_data
    if 'cover_image_path' in source or "get('cover_image_path')" in source:
        print("   ✅ create_product() récupère cover_image_path")
    else:
        print("   🚨 PROBLÈME CRITIQUE: create_product() N'extrait PAS cover_image_path de product_data")
        issues.append("create_product() ne passe pas cover_image_path")

    if 'thumbnail_path' in source or "get('thumbnail_path')" in source:
        print("   ✅ create_product() récupère thumbnail_path")
    else:
        print("   🚨 PROBLÈME CRITIQUE: create_product() N'extrait PAS thumbnail_path de product_data")
        issues.append("create_product() ne passe pas thumbnail_path")

    print(f"\n   📋 Extrait de create_product():")
    lines = source.split('\n')[15:30]  # Afficher la partie où le dict est construit
    for line in lines:
        print(f"      {line}")

    return len(issues) == 0, issues


def check_sell_handlers_flow():
    """✅ Check 4: sell_handlers.py gère bien le state + upload"""
    print("\n" + "="*60)
    print("CHECK 4: sell_handlers.py - State Management + Upload")
    print("="*60)

    from app.integrations.telegram.handlers.sell_handlers import SellHandlers
    import inspect

    issues = []

    # Check process_product_addition
    add_source = inspect.getsource(SellHandlers.process_product_addition)

    if "step = 'cover_image'" in add_source or "['step'] = 'cover_image'" in add_source:
        print("   ✅ process_product_addition() définit step='cover_image'")
    else:
        print("   ❌ process_product_addition() ne passe pas à cover_image")
        issues.append("Missing step transition to cover_image")

    # Check process_cover_image_upload
    upload_source = inspect.getsource(SellHandlers.process_cover_image_upload)

    if "product_data['cover_image_path']" in upload_source:
        print("   ✅ process_cover_image_upload() stocke cover_image_path dans product_data")
    else:
        print("   ❌ process_cover_image_upload() ne stocke pas cover_image_path")
        issues.append("process_cover_image_upload doesn't store cover_image_path")

    if "product_data['thumbnail_path']" in upload_source:
        print("   ✅ process_cover_image_upload() stocke thumbnail_path dans product_data")
    else:
        print("   ❌ process_cover_image_upload() ne stocke pas thumbnail_path")
        issues.append("process_cover_image_upload doesn't store thumbnail_path")

    # Check process_file_upload - final product creation
    file_source = inspect.getsource(SellHandlers.process_file_upload)

    if 'create_product' in file_source:
        print("   ✅ process_file_upload() appelle create_product()")

        # Vérifier si temp_product_id est renommé
        if '_rename_product_images' in file_source:
            print("   ✅ process_file_upload() renomme les images temp → final")
        else:
            print("   ⚠️  process_file_upload() ne renomme pas les images (peut causer des chemins invalides)")
            issues.append("Missing image rename from temp to final product_id")
    else:
        print("   ❌ process_file_upload() n'appelle pas create_product()")
        issues.append("process_file_upload doesn't create product")

    return len(issues) == 0, issues


def check_buy_handlers_display():
    """✅ Check 5: buy_handlers.py utilise send_product_card()"""
    print("\n" + "="*60)
    print("CHECK 5: buy_handlers.py - Visual Card Display")
    print("="*60)

    from app.integrations.telegram.handlers.buy_handlers import BuyHandlers
    import inspect

    issues = []

    # Check send_product_card exists
    try:
        card_source = inspect.getsource(BuyHandlers.send_product_card)
        print("   ✅ send_product_card() existe")

        if 'thumbnail_path' in card_source:
            print("   ✅ send_product_card() utilise thumbnail_path")
        else:
            print("   ❌ send_product_card() n'utilise pas thumbnail_path")
            issues.append("send_product_card doesn't use thumbnail_path")

        if 'ImageUtils' in card_source:
            print("   ✅ send_product_card() importe ImageUtils")
        else:
            print("   ⚠️  send_product_card() n'importe pas ImageUtils")

        if 'create_or_get_placeholder' in card_source:
            print("   ✅ send_product_card() génère placeholder si pas d'image")
        else:
            print("   ❌ send_product_card() ne génère pas de placeholder")
            issues.append("No placeholder fallback in send_product_card")

    except AttributeError:
        print("   ❌ send_product_card() N'EXISTE PAS")
        issues.append("send_product_card method missing")
        return False, issues

    # Check show_category_products uses send_product_card
    cat_source = inspect.getsource(BuyHandlers.show_category_products)

    if 'send_product_card' in cat_source:
        print("   ✅ show_category_products() appelle send_product_card()")
    else:
        print("   ❌ show_category_products() N'utilise PAS send_product_card()")
        issues.append("show_category_products doesn't use visual cards")

    return len(issues) == 0, issues


def main():
    """Exécute tous les checkpoints"""
    print("\n" + "🔍"*30)
    print("CHECKPOINT INTÉGRATION PHASE 1 - AUDIT COMPLET")
    print("🔍"*30)

    checks = [
        ("database_init.py Schema", check_database_init),
        ("product_repo.insert_product()", check_product_repo_insert),
        ("product_repo.create_product()", check_product_repo_create),
        ("sell_handlers.py Flow", check_sell_handlers_flow),
        ("buy_handlers.py Display", check_buy_handlers_display),
    ]

    results = []
    all_issues = []

    for check_name, check_func in checks:
        try:
            success, issues = check_func()
            results.append((check_name, success))
            if issues:
                all_issues.extend([(check_name, issue) for issue in issues])
        except Exception as e:
            print(f"\n❌ ERREUR dans {check_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((check_name, False))
            all_issues.append((check_name, str(e)))

    # Rapport Final
    print("\n" + "="*60)
    print("RAPPORT FINAL")
    print("="*60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for check_name, success in results:
        status = "✅ OK" if success else "🚨 PROBLÈME"
        print(f"{status:12} - {check_name}")

    print(f"\n📊 Score: {passed}/{total} checks passed")

    if all_issues:
        print("\n🚨 PROBLÈMES DÉTECTÉS:")
        for check_name, issue in all_issues:
            print(f"   • [{check_name}] {issue}")

        print("\n💡 ACTIONS REQUISES:")
        print("   1. Corriger product_repo.py pour inclure cover_image_path et thumbnail_path")
        print("   2. Vérifier que create_product() extrait ces champs de product_data")
        print("   3. Tester le flow complet de création de produit")

        return 1
    else:
        print("\n✅ TOUS LES CHECKS PASSÉS - Phase 1 est bien intégrée!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
