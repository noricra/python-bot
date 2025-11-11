"""
Parser OPTIMISÉ pour extraire les emails depuis les liens bio (linktree, beacons, etc.)
Améliorations: cache, retry, meilleure extraction, logging
"""

import re
import requests
from bs4 import BeautifulSoup
from typing import Optional, List, Dict
import time
from functools import lru_cache
from config import USER_AGENT, TIMEOUT, DELAY_BETWEEN_REQUESTS


class BioLinkParser:
    """Parser optimisé pour liens bio"""

    def __init__(self, verbose: bool = False):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.verbose = verbose
        self.cache: Dict[str, Optional[str]] = {}  # Cache URL -> email
        self.failed_urls = set()  # URLs qui ont échoué (ne pas re-essayer)

    def log(self, message: str):
        """Log si verbose activé"""
        if self.verbose:
            print(f"  [Parser] {message}")

    def extract_email_from_text(self, text: str) -> Optional[str]:
        """
        Extrait un email depuis du texte avec regex améliorée
        Filtre les emails invalides/spam
        """
        if not text:
            return None

        # Pattern email amélioré (RFC 5322 simplifié)
        email_pattern = r'\b[A-Za-z0-9]([A-Za-z0-9._%+-]){0,63}@[A-Za-z0-9]([A-Za-z0-9.-]){0,253}\.[A-Za-z]{2,}\b'
        matches = re.findall(email_pattern, text, re.IGNORECASE)

        if not matches:
            return None

        # Reconstruire les emails complets (findall avec groupes retourne des tuples)
        emails = []
        for match in re.finditer(email_pattern, text, re.IGNORECASE):
            emails.append(match.group(0))

        # Patterns à ignorer (dans le username OU le domaine)
        ignore_patterns = [
            r'^noreply@',
            r'^no-reply@',
            r'^donotreply@',
            r'^bounce@',
            r'^mailer-daemon@',
            r'@noreply\.',
            r'@example\.',
            r'@test\.',
            r'@localhost',
            r'^support@(gmail|yahoo|outlook|hotmail)',  # Support emails génériques
            # Note: "info@" peut être valide, on ne filtre que les cas évidents
        ]

        # Filtrer les emails
        for email in emails:
            email_lower = email.lower()

            # Vérifier si l'email correspond à un pattern à ignorer
            should_ignore = False
            for pattern in ignore_patterns:
                if re.search(pattern, email_lower):
                    should_ignore = True
                    self.log(f"Email ignoré (pattern match): {email}")
                    break

            if not should_ignore:
                return email

        return None

    def get_with_retry(self, url: str, max_retries: int = 3) -> Optional[requests.Response]:
        """
        Effectue une requête HTTP avec retry automatique
        """
        for attempt in range(max_retries):
            try:
                time.sleep(DELAY_BETWEEN_REQUESTS)
                response = self.session.get(
                    url,
                    timeout=TIMEOUT,
                    allow_redirects=True,
                    verify=True
                )
                response.raise_for_status()
                return response

            except requests.exceptions.Timeout:
                self.log(f"Timeout {url} (tentative {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    return None
                time.sleep(2 ** attempt)  # Backoff exponentiel

            except requests.exceptions.RequestException as e:
                self.log(f"Erreur requête {url}: {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(2 ** attempt)

        return None

    def parse_linktree(self, url: str) -> Optional[str]:
        """Parse un profil Linktree"""
        response = self.get_with_retry(url)
        if not response:
            return None

        try:
            soup = BeautifulSoup(response.text, 'html.parser')

            # 1. Chercher mailto: links
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if 'mailto:' in href:
                    email = href.replace('mailto:', '').split('?')[0].strip()
                    if self.extract_email_from_text(email):  # Valider
                        return email

            # 2. Chercher dans le texte visible
            text_content = soup.get_text()
            email = self.extract_email_from_text(text_content)
            if email:
                return email

            # 3. Chercher dans les data attributes
            for elem in soup.find_all(attrs={'data-email': True}):
                email = elem.get('data-email')
                if self.extract_email_from_text(email):
                    return email

        except Exception as e:
            self.log(f"Erreur parsing Linktree: {e}")

        return None

    def parse_beacons(self, url: str) -> Optional[str]:
        """Parse un profil Beacons.ai"""
        response = self.get_with_retry(url)
        if not response:
            return None

        try:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Beacons utilise des boutons avec icônes email
            email_buttons = soup.find_all(['a', 'button'], class_=re.compile(r'email|contact', re.I))
            for btn in email_buttons:
                href = btn.get('href', '')
                if 'mailto:' in href:
                    email = href.replace('mailto:', '').split('?')[0].strip()
                    if self.extract_email_from_text(email):
                        return email

            # Fallback: chercher dans tout le texte
            email = self.extract_email_from_text(response.text)
            if email:
                return email

        except Exception as e:
            self.log(f"Erreur parsing Beacons: {e}")

        return None

    def parse_generic_bio_link(self, url: str) -> Optional[str]:
        """Parse n'importe quel lien bio de manière générique"""
        response = self.get_with_retry(url)
        if not response:
            return None

        try:
            soup = BeautifulSoup(response.text, 'html.parser')

            # 1. Mailto links (priorité haute)
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if 'mailto:' in href:
                    email = href.replace('mailto:', '').split('?')[0].strip()
                    if self.extract_email_from_text(email):
                        return email

            # 2. Meta tags
            for meta in soup.find_all('meta', content=True):
                content = meta.get('content', '')
                email = self.extract_email_from_text(content)
                if email:
                    return email

            # 3. Links avec "email" ou "contact" dans le texte
            for link in soup.find_all('a', href=True):
                text = link.get_text().lower()
                if 'email' in text or 'contact' in text or '@' in text:
                    email = self.extract_email_from_text(link.get_text())
                    if email:
                        return email

            # 4. Fallback: tout le texte de la page
            email = self.extract_email_from_text(response.text)
            if email:
                return email

        except Exception as e:
            self.log(f"Erreur parsing generic: {e}")

        return None

    def parse_bio_link(self, url: str) -> Optional[str]:
        """
        Parse n'importe quel type de lien bio avec CACHE
        """
        if not url:
            return None

        # Normaliser l'URL
        if not url.startswith('http'):
            url = 'https://' + url

        # Check cache
        if url in self.cache:
            self.log(f"Cache hit: {url}")
            return self.cache[url]

        # Check failed URLs
        if url in self.failed_urls:
            self.log(f"URL déjà échouée, skip: {url}")
            return None

        url_lower = url.lower()

        # Router vers le parser approprié
        try:
            if 'linktree' in url_lower or 'linktr.ee' in url_lower:
                email = self.parse_linktree(url)
            elif 'beacons.ai' in url_lower or 'beacons.page' in url_lower:
                email = self.parse_beacons(url)
            else:
                email = self.parse_generic_bio_link(url)

            # Mettre en cache
            self.cache[url] = email

            if not email:
                self.failed_urls.add(url)

            return email

        except Exception as e:
            self.log(f"Erreur parse_bio_link {url}: {e}")
            self.failed_urls.add(url)
            return None

    def extract_bio_links(self, bio_text: str) -> List[str]:
        """
        Extrait tous les liens depuis une bio TikTok/Twitter
        Retourne une liste d'URLs
        """
        if not bio_text:
            return []

        # Pattern amélioré pour détecter les URLs
        url_patterns = [
            # URLs complètes
            r'https?://[^\s<>"{}|\\^`\[\]]+',
            # URLs sans http
            r'(?:www\.)?[a-zA-Z0-9-]+\.(?:com|net|org|io|co|ai|link|store|bio|page)/[^\s<>"{}|\\^`\[\]]*',
            # Domaines simples (linktr.ee/user)
            r'(?:linktr\.ee|beacons\.ai|bio\.link|stan\.store|hoo\.be|solo\.to|lnk\.bio)/[a-zA-Z0-9._-]+',
        ]

        urls = []
        for pattern in url_patterns:
            matches = re.findall(pattern, bio_text, re.IGNORECASE)
            urls.extend(matches)

        # Nettoyer les URLs
        cleaned_urls = []
        for url in urls:
            # Enlever les caractères de fin indésirables
            url = re.sub(r'[,.\)!?;:]+$', '', url)
            # Enlever les emojis de fin
            url = url.strip()
            if url and len(url) > 5:  # URL minimum valide
                cleaned_urls.append(url)

        # Enlever les doublons tout en gardant l'ordre
        seen = set()
        unique_urls = []
        for url in cleaned_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        return unique_urls

    def get_cache_stats(self) -> Dict:
        """Retourne les stats du cache"""
        return {
            'cached_urls': len(self.cache),
            'failed_urls': len(self.failed_urls),
            'success_rate': len([v for v in self.cache.values() if v]) / len(self.cache) if self.cache else 0
        }


# Fonction helper pour usage simple
def get_email_from_bio_link(url: str, verbose: bool = False) -> Optional[str]:
    """
    Fonction helper pour extraire un email depuis un lien bio
    Usage: email = get_email_from_bio_link('https://linktr.ee/username')
    """
    parser = BioLinkParser(verbose=verbose)
    return parser.parse_bio_link(url)


if __name__ == "__main__":
    # Tests rapides
    print("=" * 60)
    print("🧪 TESTS LINK_PARSER V2")
    print("=" * 60)

    parser = BioLinkParser(verbose=True)

    # Test 1: Extraction email
    test_texts = [
        "Contact: john.doe@business.com",
        "Email me at hello@startup.io for collabs",
        "Don't email noreply@test.com",  # Devrait être ignoré
        "📧 reach.me@company.co",
    ]

    print("\n1. Test extraction emails:")
    for text in test_texts:
        email = parser.extract_email_from_text(text)
        print(f"   '{text}' -> {email}")

    # Test 2: Extraction liens
    test_bio = "Check my links: https://linktr.ee/user and beacons.ai/creator plus www.site.com/about"
    links = parser.extract_bio_links(test_bio)
    print(f"\n2. Test extraction liens:")
    print(f"   Bio: {test_bio}")
    print(f"   Liens trouvés: {links}")

    # Test 3: Cache stats
    stats = parser.get_cache_stats()
    print(f"\n3. Cache stats: {stats}")

    print("\n✅ Tests terminés")
