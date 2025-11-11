"""
Classe de base pour les scrapers avec fonctionnalités communes:
- Sauvegarde progressive
- Reprise après crash
- Headers rotatifs anti-détection
- Stats en temps réel
"""

import csv
import json
import os
import random
import time
from typing import List, Dict, Optional
from datetime import datetime
from playwright.sync_api import Browser, Page


class BaseScraper:
    """Classe de base pour tous les scrapers"""

    def __init__(self, platform: str, headless: bool = True):
        self.platform = platform
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.scraped_profiles = set()
        self.stats = {
            'total_searched': 0,
            'total_scraped': 0,
            'with_email': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }

        # Fichiers pour sauvegarde progressive
        self.progress_file = f"output/{platform}_progress.json"
        self.temp_csv_file = f"output/{platform}_temp_leads.csv"

        # Load progress si reprise
        self.load_progress()

    def get_random_user_agent(self) -> str:
        """Retourne un User-Agent aléatoire pour anti-détection"""
        user_agents = [
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            # Chrome on Mac
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            # Firefox
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
            # Safari
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        ]
        return random.choice(user_agents)

    def random_delay(self, min_seconds: float = 2.0, max_seconds: float = 5.0):
        """Délai aléatoire pour paraître plus humain"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)

    def save_progress(self):
        """Sauvegarde la progression actuelle"""
        progress_data = {
            'scraped_profiles': list(self.scraped_profiles),
            'stats': self.stats,
            'timestamp': datetime.now().isoformat()
        }

        os.makedirs('output', exist_ok=True)
        with open(self.progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)

    def load_progress(self):
        """Charge la progression depuis un fichier (reprise après crash)"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    progress_data = json.load(f)
                    self.scraped_profiles = set(progress_data.get('scraped_profiles', []))
                    self.stats = progress_data.get('stats', self.stats)

                    print(f"📂 Reprise depuis sauvegarde:")
                    print(f"   - Profils déjà scrapés: {len(self.scraped_profiles)}")
                    print(f"   - Stats: {self.stats}")
                    return True
            except Exception as e:
                print(f"⚠️  Erreur chargement progression: {e}")
                return False
        return False

    def clear_progress(self):
        """Efface les fichiers de progression (nouveau démarrage)"""
        for file in [self.progress_file, self.temp_csv_file]:
            if os.path.exists(file):
                os.remove(file)
                print(f"🗑️  Supprimé: {file}")

    def save_profile_incremental(self, profile_data: Dict):
        """
        Sauvegarde un profil immédiatement (progressif)
        Si crash, les données ne sont pas perdues
        """
        os.makedirs('output', exist_ok=True)

        # Créer le fichier avec headers si première écriture
        file_exists = os.path.exists(self.temp_csv_file)

        fieldnames = ['username', 'profile_url', 'bio', 'email', 'bio_links', 'followers']

        with open(self.temp_csv_file, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            writer.writerow(profile_data)

    def finalize_csv(self, final_output_file: str):
        """
        Finalise le CSV en renommant le fichier temporaire
        """
        if os.path.exists(self.temp_csv_file):
            # Lire tous les profils du temp file
            profiles = []
            with open(self.temp_csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                profiles = list(reader)

            # Sauvegarder dans le fichier final
            if profiles:
                fieldnames = ['username', 'profile_url', 'bio', 'email', 'bio_links', 'followers']
                with open(final_output_file, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(profiles)

                print(f"✅ Fichier final: {final_output_file}")

                # Supprimer le fichier temporaire
                os.remove(self.temp_csv_file)

                return profiles

        return []

    def print_stats(self):
        """Affiche les statistiques de scraping"""
        print("\n" + "=" * 60)
        print(f"📊 STATISTIQUES {self.platform.upper()}")
        print("=" * 60)

        total = self.stats['total_scraped']
        with_email = self.stats['with_email']
        failed = self.stats['failed']

        print(f"Total recherché: {self.stats['total_searched']}")
        print(f"Total scraped: {total}")
        print(f"  ├─ Avec email: {with_email} ({with_email/total*100 if total > 0 else 0:.1f}%)")
        print(f"  ├─ Sans email: {total - with_email}")
        print(f"  └─ Échecs: {failed}")

        if self.stats['start_time']:
            elapsed = time.time() - self.stats['start_time']
            print(f"\nTemps écoulé: {elapsed/60:.1f} minutes")
            if total > 0:
                print(f"Vitesse: {total/(elapsed/60):.1f} profils/minute")

        print("=" * 60)

    def update_stats(self, scraped: bool = False, has_email: bool = False, failed: bool = False):
        """Met à jour les statistiques"""
        if scraped:
            self.stats['total_scraped'] += 1
            if has_email:
                self.stats['with_email'] += 1
        if failed:
            self.stats['failed'] += 1

    def start_timer(self):
        """Démarre le chronomètre"""
        self.stats['start_time'] = time.time()

    def stop_timer(self):
        """Arrête le chronomètre"""
        self.stats['end_time'] = time.time()

    def get_viewport_size(self) -> Dict[str, int]:
        """Retourne une taille de viewport aléatoire (anti-détection)"""
        viewports = [
            {'width': 1920, 'height': 1080},  # Full HD
            {'width': 1366, 'height': 768},   # Laptop commun
            {'width': 1536, 'height': 864},   # Laptop HD+
            {'width': 2560, 'height': 1440},  # 2K
        ]
        return random.choice(viewports)

    def should_skip_profile(self, profile_identifier: str) -> bool:
        """Vérifie si un profil doit être ignoré (déjà scraped)"""
        return profile_identifier in self.scraped_profiles

    def mark_profile_scraped(self, profile_identifier: str):
        """Marque un profil comme scraped"""
        self.scraped_profiles.add(profile_identifier)

        # Sauvegarde tous les 10 profils
        if len(self.scraped_profiles) % 10 == 0:
            self.save_progress()


# Exemple d'utilisation
if __name__ == "__main__":
    scraper = BaseScraper("test")

    print("Test User-Agent aléatoire:")
    for i in range(3):
        print(f"  {i+1}. {scraper.get_random_user_agent()}")

    print("\nTest viewport aléatoire:")
    for i in range(3):
        print(f"  {i+1}. {scraper.get_viewport_size()}")

    print("\nTest sauvegarde progressive:")
    test_profile = {
        'username': 'testuser',
        'profile_url': 'https://test.com/testuser',
        'bio': 'Test bio',
        'email': 'test@test.com',
        'bio_links': '',
        'followers': 1000
    }
    scraper.save_profile_incremental(test_profile)
    print(f"  ✅ Profil sauvegardé dans {scraper.temp_csv_file}")
