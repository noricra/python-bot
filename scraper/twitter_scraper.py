"""
Scraper Twitter/X pour extraire les profils de créateurs et leurs emails
"""

import time
import csv
import re
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright, Page, Browser
from link_parser import BioLinkParser
from config import (
    DELAY_BETWEEN_REQUESTS,
    MIN_FOLLOWERS,
    USER_AGENT,
    OUTPUT_FILE
)


class TwitterScraper:
    """Scraper pour Twitter/X"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.link_parser = BioLinkParser()
        self.scraped_profiles = set()

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
        Parse le nombre de followers depuis le texte Twitter
        Ex: "1.2M" -> 1200000, "500K" -> 500000, "1,234" -> 1234
        """
        if not text:
            return 0

        text = text.strip().upper().replace(',', '').replace(' ', '')

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

    def extract_profile_data(self, username: str) -> Optional[Dict]:
        """
        Visite un profil Twitter et extrait les données
        Retourne: {username, bio, email, links, followers}
        """
        try:
            profile_url = f"https://twitter.com/{username}"
            print(f"   🐦 Visite du profil: @{username}")

            self.page.goto(profile_url, wait_until='networkidle', timeout=30000)
            time.sleep(DELAY_BETWEEN_REQUESTS)

            # Extraire la bio
            bio = ""
            try:
                # Twitter utilise plusieurs sélecteurs possibles pour la bio
                bio_selectors = [
                    '[data-testid="UserDescription"]',
                    '[data-testid="UserProfileHeader_Items"] span'
                ]

                for selector in bio_selectors:
                    bio_element = self.page.query_selector(selector)
                    if bio_element:
                        bio = bio_element.inner_text()
                        if bio:
                            break
            except:
                pass

            # Extraire le nombre de followers
            followers = 0
            try:
                # Chercher le lien "followers"
                followers_link = self.page.query_selector('a[href*="/followers"]')
                if followers_link:
                    followers_text = followers_link.inner_text()
                    # Le texte est genre "1.2K Followers"
                    followers = self.parse_followers_count(followers_text)
            except:
                pass

            # Filtrer si pas assez de followers
            if followers < MIN_FOLLOWERS:
                print(f"   ⏭️  Ignoré ({followers} followers < {MIN_FOLLOWERS})")
                return None

            # Extraire email direct de la bio
            email = self.link_parser.extract_email_from_text(bio)

            # Extraire les liens externes de la bio
            bio_links = []
            try:
                # Les liens dans la bio Twitter
                link_elements = self.page.query_selector_all('[data-testid="UserUrl"] a, [data-testid="UserDescription"] a')
                for link_elem in link_elements:
                    href = link_elem.get_attribute('href')
                    if href and href.startswith('http'):
                        bio_links.append(href)
            except:
                pass

            # Parser aussi les liens trouvés dans le texte de la bio
            text_links = self.link_parser.extract_bio_links(bio)
            bio_links.extend(text_links)
            bio_links = list(set(bio_links))  # Enlever doublons

            # Si pas d'email direct, parser les liens bio
            if not email and bio_links:
                print(f"   🔍 Parsing des liens bio...")
                for link in bio_links[:2]:  # Limiter à 2 liens
                    try:
                        email = self.link_parser.parse_bio_link(link)
                        if email:
                            print(f"   ✅ Email trouvé: {email}")
                            break
                    except Exception as e:
                        print(f"   ❌ Erreur parsing {link}: {e}")
                        continue

            profile_data = {
                'username': username,
                'profile_url': profile_url,
                'bio': bio,
                'email': email if email else "",
                'bio_links': ', '.join(bio_links),
                'followers': followers
            }

            if email:
                print(f"   ✅ Profil scraped: @{username} ({followers} followers) - Email: {email}")
            else:
                print(f"   ⚠️  Profil scraped: @{username} ({followers} followers) - Pas d'email")

            return profile_data

        except Exception as e:
            print(f"   ❌ Erreur extraction profil @{username}: {e}")
            return None

    def search_creators(self, keyword: str, limit: int = 20) -> List[str]:
        """
        Recherche des créateurs par mot-clé et retourne leurs usernames
        """
        print(f"\n🔎 Recherche Twitter: '{keyword}'")

        try:
            # URL de recherche Twitter (people search)
            search_url = f"https://twitter.com/search?q={keyword.replace(' ', '%20')}&f=user"
            self.page.goto(search_url, wait_until='networkidle', timeout=30000)
            time.sleep(3)

            usernames = []

            # Scroller pour charger plus de résultats
            for _ in range(3):
                self.page.evaluate("window.scrollBy(0, 1000)")
                time.sleep(2)

            # Extraire les usernames depuis les profils affichés
            # Twitter structure: <a href="/username">
            profile_links = self.page.query_selector_all('a[href^="/"][href*="/"]')

            for link in profile_links:
                try:
                    href = link.get_attribute('href')
                    if href:
                        # Format: /username ou /username/status/...
                        match = re.match(r'^/([a-zA-Z0-9_]+)$', href)
                        if match:
                            username = match.group(1)
                            # Filtrer les pages système de Twitter
                            if username not in ['home', 'explore', 'notifications', 'messages', 'search', 'settings', 'i']:
                                if username not in self.scraped_profiles:
                                    usernames.append(username)
                                    self.scraped_profiles.add(username)

                                    if len(usernames) >= limit:
                                        break
                except:
                    continue

            print(f"   ✅ {len(usernames)} profils trouvés")
            return usernames[:limit]

        except Exception as e:
            print(f"   ❌ Erreur recherche '{keyword}': {e}")
            return []

    def scrape_all(self, keywords: List[str]) -> List[Dict]:
        """
        Scrape tous les profils pour une liste de mots-clés
        """
        all_profiles = []

        try:
            self.start_browser()

            for keyword in keywords:
                # Rechercher des profils
                usernames = self.search_creators(keyword)

                # Extraire les données de chaque profil
                for username in usernames:
                    profile_data = self.extract_profile_data(username)
                    if profile_data:
                        all_profiles.append(profile_data)

                time.sleep(DELAY_BETWEEN_REQUESTS)

            print(f"\n✅ Total scraped: {len(all_profiles)} profils")
            return all_profiles

        finally:
            self.close_browser()

    def save_to_csv(self, profiles: List[Dict], filename: str = "output/twitter_leads.csv"):
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


# Mots-clés spécifiques Twitter
TWITTER_KEYWORDS = [
    "digital products creator",
    "indie hacker",
    "solopreneur",
    "course creator",
    "ebook author",
    "template designer",
    "notion templates",
    "crypto creator",
    "web3 builder",
    "content monetization",
    "building in public",
    "bootstrapped founder",
    "micro saas",
    "info products"
]


def main():
    """
    Fonction principale
    """
    print("=" * 60)
    print("🐦 TWITTER SCRAPER - Extraction d'emails de créateurs")
    print("=" * 60)

    scraper = TwitterScraper(headless=True)  # headless=False pour voir le navigateur

    # Scraper avec les mots-clés
    profiles = scraper.scrape_all(TWITTER_KEYWORDS)

    # Sauvegarder les résultats
    scraper.save_to_csv(profiles)

    print("\n✅ TERMINÉ!")


if __name__ == "__main__":
    main()
