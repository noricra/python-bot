"""
Parser pour extraire les emails depuis les liens bio (linktree, beacons, etc.)
"""

import re
import requests
from bs4 import BeautifulSoup
from typing import Optional
import time
from config import USER_AGENT, TIMEOUT, DELAY_BETWEEN_REQUESTS


class BioLinkParser:
    """Parse les liens bio pour extraire les emails"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})

    def extract_email_from_text(self, text: str) -> Optional[str]:
        """Extrait un email depuis du texte avec regex"""
        if not text:
            return None

        # Pattern email amélioré
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(email_pattern, text)

        if matches:
            # Filtrer les emails communs/faux
            ignore_emails = ['example.com', 'test.com', 'noreply']
            for email in matches:
                if not any(ignore in email.lower() for ignore in ignore_emails):
                    return email

        return None

    def parse_linktree(self, url: str) -> Optional[str]:
        """Parse un profil Linktree pour trouver un email"""
        try:
            time.sleep(DELAY_BETWEEN_REQUESTS)
            response = self.session.get(url, timeout=TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Chercher dans tous les liens
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text()

                # Email dans href
                if 'mailto:' in href:
                    return href.replace('mailto:', '').strip()

                # Email dans le texte
                email = self.extract_email_from_text(text)
                if email:
                    return email

            # Chercher dans le texte brut de la page
            email = self.extract_email_from_text(response.text)
            if email:
                return email

        except Exception as e:
            print(f"Erreur parsing Linktree {url}: {e}")

        return None

    def parse_beacons(self, url: str) -> Optional[str]:
        """Parse un profil Beacons.ai pour trouver un email"""
        try:
            time.sleep(DELAY_BETWEEN_REQUESTS)
            response = self.session.get(url, timeout=TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Beacons a souvent un bouton "Email"
            for link in soup.find_all(['a', 'button']):
                text = link.get_text().lower()
                href = link.get('href', '')

                if 'email' in text or 'contact' in text:
                    if 'mailto:' in href:
                        return href.replace('mailto:', '').strip()

                # Email dans le texte
                email = self.extract_email_from_text(link.get_text())
                if email:
                    return email

            # Chercher dans toute la page
            email = self.extract_email_from_text(response.text)
            if email:
                return email

        except Exception as e:
            print(f"Erreur parsing Beacons {url}: {e}")

        return None

    def parse_generic_bio_link(self, url: str) -> Optional[str]:
        """Parse n'importe quel lien bio de manière générique"""
        try:
            time.sleep(DELAY_BETWEEN_REQUESTS)
            response = self.session.get(url, timeout=TIMEOUT, allow_redirects=True)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # 1. Chercher les mailto: links
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if 'mailto:' in href:
                    return href.replace('mailto:', '').split('?')[0].strip()

            # 2. Chercher dans les meta tags
            for meta in soup.find_all('meta'):
                content = meta.get('content', '')
                email = self.extract_email_from_text(content)
                if email:
                    return email

            # 3. Chercher dans tous les textes visibles
            email = self.extract_email_from_text(response.text)
            if email:
                return email

        except Exception as e:
            print(f"Erreur parsing {url}: {e}")

        return None

    def parse_bio_link(self, url: str) -> Optional[str]:
        """
        Parse n'importe quel type de lien bio
        Détecte automatiquement le type et utilise le parser approprié
        """
        if not url:
            return None

        # Normaliser l'URL
        if not url.startswith('http'):
            url = 'https://' + url

        url_lower = url.lower()

        # Router vers le parser approprié
        if 'linktree' in url_lower or 'linktr.ee' in url_lower:
            return self.parse_linktree(url)
        elif 'beacons.ai' in url_lower or 'beacons.page' in url_lower:
            return self.parse_beacons(url)
        else:
            # Parser générique pour tous les autres
            return self.parse_generic_bio_link(url)

    def extract_bio_links(self, bio_text: str) -> list:
        """
        Extrait tous les liens depuis une bio TikTok
        Retourne une liste d'URLs
        """
        if not bio_text:
            return []

        # Pattern pour détecter les URLs
        url_pattern = r'https?://[^\s]+|(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?'
        urls = re.findall(url_pattern, bio_text)

        # Nettoyer les URLs
        cleaned_urls = []
        for url in urls:
            # Enlever les caractères de fin indésirables
            url = re.sub(r'[,.\)]+$', '', url)
            if url:
                cleaned_urls.append(url)

        return cleaned_urls


# Fonction helper pour usage simple
def get_email_from_bio_link(url: str) -> Optional[str]:
    """
    Fonction helper pour extraire un email depuis un lien bio
    Usage: email = get_email_from_bio_link('https://linktr.ee/username')
    """
    parser = BioLinkParser()
    return parser.parse_bio_link(url)


if __name__ == "__main__":
    # Tests
    parser = BioLinkParser()

    # Test extraction email
    test_text = "Contact me at john.doe@example.com for business inquiries"
    print(f"Email trouvé: {parser.extract_email_from_text(test_text)}")

    # Test extraction liens
    test_bio = "Check out my links: https://linktr.ee/testuser and www.mywebsite.com"
    print(f"Liens trouvés: {parser.extract_bio_links(test_bio)}")
