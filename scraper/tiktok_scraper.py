"""
Scraper TikTok pour extraire les profils de créateurs et leurs emails
"""

import time
import csv
import re
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright, Page, Browser
from link_parser import BioLinkParser
from config import (
    SEARCH_KEYWORDS,
    PROFILES_PER_KEYWORD,
    DELAY_BETWEEN_REQUESTS,
    MIN_FOLLOWERS,
    USER_AGENT,
    OUTPUT_FILE,
    BIO_LINK_PLATFORMS
)


class TikTokScraper:
    """Scraper pour TikTok"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.link_parser = BioLinkParser()
        self.scraped_profiles = set()  # Pour éviter les doublons

    def start_browser(self):
        """Démarre le navigateur Playwright"""
        print("🚀 Démarrage du navigateur...")
        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(headless=self.headless)
        context = self.browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = context.new_page()
        print("✅ Navigateur prêt")

    def close_browser(self):
        """Ferme le navigateur"""
        if self.browser:
            self.browser.close()
            print("🔴 Navigateur fermé")

    def parse_followers_count(self, text: str) -> int:
        """
        Parse le nombre de followers depuis le texte TikTok
        Ex: "1.2M" -> 1200000, "500K" -> 500000, "1234" -> 1234
        """
        if not text:
            return 0

        text = text.strip().upper().replace(',', '')

        # Extraire les chiffres et la lettre (M/K)
        match = re.search(r'([\d.]+)([MK]?)', text)
        if not match:
            return 0

        number = float(match.group(1))
        suffix = match.group(2)

        if suffix == 'M':
            return int(number * 1_000_000)
        elif suffix == 'K':
            return int(number * 1_000)
        else:
            return int(number)

    def extract_profile_data(self, profile_url: str) -> Optional[Dict]:
        """
        Visite un profil TikTok et extrait les données
        Retourne: {username, bio, email, links, followers}
        """
        try:
            print(f"   📱 Visite du profil: {profile_url}")

            if not profile_url.startswith('http'):
                profile_url = f"https://www.tiktok.com{profile_url}"
                print(f"   🔧 URL corrigée: {profile_url}")
            
            self.page.goto(profile_url, wait_until='networkidle', timeout=30000)
            time.sleep(DELAY_BETWEEN_REQUESTS)

            # Extraire le username
            username = profile_url.rstrip('/').split('/')[-1].replace('@', '')

            # Extraire la bio
            bio = ""
            try:
                bio_element = self.page.query_selector('[data-e2e="user-bio"]')
                if bio_element:
                    bio = bio_element.inner_text()
            except:
                pass

            # Extraire le nombre de followers
            followers = 0
            try:
                followers_element = self.page.query_selector('[data-e2e="followers-count"]')
                if followers_element:
                    followers_text = followers_element.inner_text()
                    followers = self.parse_followers_count(followers_text)
            except:
                pass

            # Filtrer si pas assez de followers
            if followers < MIN_FOLLOWERS:
                print(f"   ⏭️  Ignoré ({followers} followers < {MIN_FOLLOWERS})")
                return None

            # Extraire email direct de la bio
            email = self.link_parser.extract_email_from_text(bio)

            # Extraire les liens bio
            bio_links = self.link_parser.extract_bio_links(bio)

            # Si pas d'email direct, parser les liens bio
            if not email and bio_links:
                print(f"   🔍 Parsing des liens bio...")
                for link in bio_links[:2]:  # Limiter à 2 liens pour éviter trop de temps
                    try:
                        email = self.link_parser.parse_bio_link(link)
                        if email:
                            print(f"   ✅ Email trouvé: {email}")
                            break
                    except Exception as e:
                        print(f"   ❌ Erreur parsing {link}: {e}")
                        continue

                    # CORRECTION - Avant de créer le dictionnaire
            if not profile_url.startswith('http'):
                profile_url = f"https://www.tiktok.com{profile_url}"

            profile_data = {
                'username': username,
                'profile_url': profile_url,  # Maintenant l'URL est corrigée
                'bio': bio,
                'email': email if email else "",
                'bio_links': ', '.join(bio_links),
                'followers': followers
            }
            if profile_data:  # Si on a des données
                self.save_to_csv([profile_data], "output/tiktok_temp.csv")  # ⬅️ SOLUTION SIMPLE



    
            if email:
                print(f"   ✅ Profil scraped: @{username} ({followers} followers) - Email: {email}")
            else:
                print(f"   ⚠️  Profil scraped: @{username} ({followers} followers) - Pas d'email")

            return profile_data

        except Exception as e:
            print(f"   ❌ Erreur extraction profil {profile_url}: {e}")
            return None

    def search_creators(self, keyword: str, limit: int = PROFILES_PER_KEYWORD) -> List[str]:
        """
        Recherche des créateurs par mot-clé et retourne leurs URLs de profil
        """
        print(f"\n🔎 Recherche: '{keyword}'")

        try:
            # URL de recherche TikTok
            search_url = f"https://www.tiktok.com/search/user?q={keyword.replace(' ', '%20')}"
            self.page.goto(search_url, wait_until='networkidle', timeout=30000)
            time.sleep(3)

            profile_urls = []

            # Scroller pour charger plus de résultats
            for _ in range(3):  # 3 scrolls
                self.page.evaluate("window.scrollBy(0, 1000)")
                time.sleep(2)

            # Extraire les liens de profils
            profile_links = self.page.query_selector_all('a[href*="/@"]')

            for link in profile_links:
                try:
                    href = link.get_attribute('href')
                    if href and '/@' in href:
                        # Nettoyer l'URL
                        profile_url = href.split('?')[0]  # Enlever les query params
                        if profile_url not in self.scraped_profiles:
                            profile_urls.append(profile_url)
                            self.scraped_profiles.add(profile_url)

                        if len(profile_urls) >= limit:
                            break
                except:
                    continue

            print(f"   ✅ {len(profile_urls)} profils trouvés")
            return profile_urls[:limit]

        except Exception as e:
            print(f"   ❌ Erreur recherche '{keyword}': {e}")
            return []

    def scrape_all(self, keywords: List[str] = None) -> List[Dict]:
        """
        Scrape tous les profils pour une liste de mots-clés
        """
        if keywords is None:
            keywords = SEARCH_KEYWORDS

        all_profiles = []

        try:
            self.start_browser()

            for keyword in keywords:
                # Rechercher des profils
                profile_urls = self.search_creators(keyword)

                # Extraire les données de chaque profil
                for profile_url in profile_urls:
                    profile_data = self.extract_profile_data(profile_url)
                    if profile_data:
                        all_profiles.append(profile_data)

                time.sleep(DELAY_BETWEEN_REQUESTS)

            print(f"\n✅ Total scraped: {len(all_profiles)} profils")
            return all_profiles

        finally:
            self.close_browser()

    def save_to_csv(self, profiles: List[Dict], filename: str = OUTPUT_FILE):
        """
        Sauvegarde les profils dans un fichier CSV
        """
        if not profiles:
            print("⚠️  Aucun profil à sauvegarder")
            return

        print(f"\n💾 Sauvegarde dans {filename}...")

        fieldnames = ['username', 'profile_url', 'bio', 'email', 'bio_links', 'followers']

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(profiles)

        # Stats
        total = len(profiles)
        with_email = len([p for p in profiles if p.get('email')])

        print(f"✅ {total} profils sauvegardés")
        print(f"📧 {with_email} profils avec email ({with_email/total*100:.1f}%)")
        print(f"📂 Fichier: {filename}")


def main():
    """
    Fonction principale
    """
    print("=" * 60)
    print("🎯 TIKTOK SCRAPER - Extraction d'emails de créateurs")
    print("=" * 60)

    scraper = TikTokScraper(headless=True)  # headless=False pour voir le navigateur

    # Scraper avec les mots-clés par défaut
    profiles = scraper.scrape_all()

    # Sauvegarder les résultats
    scraper.save_to_csv(profiles)

    print("\n✅ TERMINÉ!")


if __name__ == "__main__":
    main()
