"""
Script de test complet pour valider toutes les fonctionnalités
"""

import sys


def test_link_parser():
    """Test du link parser optimisé"""
    print("\n" + "=" * 60)
    print("🧪 TEST 1: Link Parser")
    print("=" * 60)

    from link_parser import BioLinkParser

    parser = BioLinkParser(verbose=False)

    # Test emails
    test_cases = [
        ("Email: contact@business.com", "contact@business.com", "Email simple"),
        ("📧 hello@startup.io", "hello@startup.io", "Email avec emoji"),
        ("noreply@test.com", None, "Email noreply (doit être filtré)"),
        ("Contact: john.doe@company.org", "john.doe@company.org", "Email avec point"),
    ]

    passed = 0
    for text, expected, description in test_cases:
        result = parser.extract_email_from_text(text)
        if result == expected:
            print(f"   ✅ {description}")
            passed += 1
        else:
            print(f"   ❌ {description} - Attendu: {expected}, Reçu: {result}")

    # Test liens bio
    bio = "Links: https://linktr.ee/user and beacons.ai/creator"
    links = parser.extract_bio_links(bio)
    if len(links) >= 2:
        print(f"   ✅ Extraction liens bio ({len(links)} liens trouvés)")
        passed += 1
    else:
        print(f"   ❌ Extraction liens bio - Attendu: >= 2, Reçu: {len(links)}")

    print(f"\n   Résultat: {passed}/{len(test_cases) + 1} tests passés")
    return passed == len(test_cases) + 1


def test_scraper_base():
    """Test de la classe de base des scrapers"""
    print("\n" + "=" * 60)
    print("🧪 TEST 2: Scraper Base")
    print("=" * 60)

    from scraper_base import BaseScraper
    import os

    scraper = BaseScraper("test", headless=True)

    passed = 0

    # Test 1: User-Agent aléatoire
    ua1 = scraper.get_random_user_agent()
    ua2 = scraper.get_random_user_agent()
    if "Mozilla" in ua1 and "Mozilla" in ua2:
        print("   ✅ User-Agent aléatoire")
        passed += 1
    else:
        print("   ❌ User-Agent aléatoire")

    # Test 2: Viewport aléatoire
    vp = scraper.get_viewport_size()
    if 'width' in vp and 'height' in vp:
        print("   ✅ Viewport aléatoire")
        passed += 1
    else:
        print("   ❌ Viewport aléatoire")

    # Test 3: Sauvegarde progressive
    test_profile = {
        'username': 'testuser',
        'profile_url': 'https://test.com/testuser',
        'bio': 'Test bio',
        'email': 'test@test.com',
        'bio_links': '',
        'followers': 1000
    }
    scraper.save_profile_incremental(test_profile)
    if os.path.exists(scraper.temp_csv_file):
        print("   ✅ Sauvegarde progressive")
        passed += 1
        # Cleanup
        os.remove(scraper.temp_csv_file)
    else:
        print("   ❌ Sauvegarde progressive")

    # Test 4: Stats
    scraper.update_stats(scraped=True, has_email=True)
    if scraper.stats['total_scraped'] == 1 and scraper.stats['with_email'] == 1:
        print("   ✅ Système de stats")
        passed += 1
    else:
        print("   ❌ Système de stats")

    # Test 5: Cache de profils
    scraper.mark_profile_scraped("test_profile_1")
    if scraper.should_skip_profile("test_profile_1"):
        print("   ✅ Cache de profils")
        passed += 1
    else:
        print("   ❌ Cache de profils")

    # Cleanup
    scraper.clear_progress()

    print(f"\n   Résultat: {passed}/5 tests passés")
    return passed == 5


def test_config():
    """Test de la configuration"""
    print("\n" + "=" * 60)
    print("🧪 TEST 3: Configuration")
    print("=" * 60)

    from config import (
        SEARCH_KEYWORDS,
        PROFILES_PER_KEYWORD,
        MIN_FOLLOWERS,
        DELAY_BETWEEN_REQUESTS,
        BIO_LINK_PLATFORMS
    )

    passed = 0

    # Test 1: Mots-clés configurés
    if len(SEARCH_KEYWORDS) > 0:
        print(f"   ✅ Mots-clés configurés ({len(SEARCH_KEYWORDS)} mots-clés)")
        passed += 1
    else:
        print("   ❌ Aucun mot-clé configuré")

    # Test 2: Paramètres numériques valides
    if PROFILES_PER_KEYWORD > 0 and MIN_FOLLOWERS >= 0 and DELAY_BETWEEN_REQUESTS > 0:
        print("   ✅ Paramètres numériques valides")
        passed += 1
    else:
        print("   ❌ Paramètres numériques invalides")

    # Test 3: Plateformes bio link
    if len(BIO_LINK_PLATFORMS) > 0:
        print(f"   ✅ Plateformes bio ({len(BIO_LINK_PLATFORMS)} plateformes)")
        passed += 1
    else:
        print("   ❌ Aucune plateforme bio configurée")

    print(f"\n   Résultat: {passed}/3 tests passés")
    return passed == 3


def run_all_tests():
    """Lance tous les tests"""
    print("\n" + "=" * 60)
    print("🚀 SUITE DE TESTS COMPLÈTE")
    print("=" * 60)

    results = {
        "Link Parser": test_link_parser(),
        "Scraper Base": test_scraper_base(),
        "Configuration": test_config(),
    }

    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status} - {test_name}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 Tous les tests sont passés ! Le scraper est prêt.")
        print("\n💡 Prochaine étape:")
        print("   python3 main.py --platform tiktok")
        return 0
    else:
        print("\n❌ Certains tests ont échoué. Vérifiez les erreurs ci-dessus.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
