"""
Script principal - Lance les scrapers TikTok et Twitter
"""

import csv
import argparse
from typing import List, Dict
from tiktok_scraper import TikTokScraper, SEARCH_KEYWORDS
from twitter_scraper import TwitterScraper, TWITTER_KEYWORDS


def merge_and_save(tiktok_profiles: List[Dict], twitter_profiles: List[Dict], output_file: str = "output/all_leads.csv"):
    """
    Fusionne les résultats TikTok et Twitter dans un seul CSV
    """
    print("\n" + "=" * 60)
    print("📊 FUSION DES RÉSULTATS")
    print("=" * 60)

    # Ajouter la source pour identifier d'où vient chaque lead
    for profile in tiktok_profiles:
        profile['source'] = 'TikTok'

    for profile in twitter_profiles:
        profile['source'] = 'Twitter'

    # Combiner
    all_profiles = tiktok_profiles + twitter_profiles

    if not all_profiles:
        print("⚠️  Aucun profil à sauvegarder")
        return

    # Sauvegarder
    print(f"💾 Sauvegarde de {len(all_profiles)} profils dans {output_file}...")

    fieldnames = ['source', 'username', 'profile_url', 'bio', 'email', 'bio_links', 'followers']

    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_profiles)

    # Stats finales
    total = len(all_profiles)
    tiktok_count = len(tiktok_profiles)
    twitter_count = len(twitter_profiles)
    with_email = len([p for p in all_profiles if p.get('email')])

    print("\n" + "=" * 60)
    print("📈 STATISTIQUES FINALES")
    print("=" * 60)
    print(f"Total profils scraped: {total}")
    print(f"  ├─ TikTok: {tiktok_count}")
    print(f"  └─ Twitter: {twitter_count}")
    print(f"\nProfils avec email: {with_email} ({with_email/total*100 if total > 0 else 0:.1f}%)")
    print(f"Profils sans email: {total - with_email}")
    print(f"\n📂 Fichier final: {output_file}")
    print("=" * 60)


def main():
    """
    Fonction principale - Lance les scrapers selon les options
    """
    parser = argparse.ArgumentParser(description='Scraper TikTok et Twitter pour acquisition de créateurs')
    parser.add_argument(
        '--platform',
        choices=['tiktok', 'twitter', 'both'],
        default='both',
        help='Plateforme à scraper (default: both)'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        default=True,
        help='Mode headless (sans interface navigateur)'
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Voir le navigateur pendant le scraping'
    )

    args = parser.parse_args()

    headless = not args.no_headless if args.no_headless else args.headless

    print("=" * 60)
    print("🎯 SCRAPER MULTI-PLATEFORMES")
    print("=" * 60)
    print(f"Plateforme(s): {args.platform.upper()}")
    print(f"Mode: {'Headless' if headless else 'Visible'}")
    print("=" * 60)

    tiktok_profiles = []
    twitter_profiles = []

    # TikTok
    if args.platform in ['tiktok', 'both']:
        print("\n🎵 LANCEMENT SCRAPER TIKTOK")
        print("=" * 60)
        tiktok_scraper = TikTokScraper(headless=headless)
        tiktok_profiles = tiktok_scraper.scrape_all(SEARCH_KEYWORDS)
        tiktok_scraper.save_to_csv(tiktok_profiles, "output/tiktok_leads.csv")

    # Twitter
    if args.platform in ['twitter', 'both']:
        print("\n🐦 LANCEMENT SCRAPER TWITTER")
        print("=" * 60)
        twitter_scraper = TwitterScraper(headless=headless)
        twitter_profiles = twitter_scraper.scrape_all(TWITTER_KEYWORDS)
        twitter_scraper.save_to_csv(twitter_profiles, "output/twitter_leads.csv")

    # Fusionner si les deux plateformes
    if args.platform == 'both':
        merge_and_save(tiktok_profiles, twitter_profiles)

    print("\n✅ SCRAPING TERMINÉ!\n")


if __name__ == "__main__":
    main()
