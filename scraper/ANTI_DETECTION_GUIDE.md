# 🕵️ GUIDE ANTI-DÉTECTION AVANCÉE

**Objectif :** Faire passer ton bot pour un humain réel

---

# 🎯 LES 7 NIVEAUX DE DÉTECTION

## Niveau 1 : User-Agent ✅ (Déjà implémenté)
```python
# TON CODE ACTUEL
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
    # etc.
]
```

**Status :** ✅ OK mais pas suffisant

---

## Niveau 2 : Headers HTTP Complets ✅ (Déjà implémenté)
```python
# TON CODE ACTUEL
headers = {
    'User-Agent': UA,
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'en-US,en;q=0.5',
    'DNT': '1',
}
```

**Status :** ✅ OK

---

## Niveau 3 : Browser Fingerprinting ❌ **MANQUANT - CRITIQUE**

### **C'est quoi ?**
TikTok/Twitter analysent :
- Canvas fingerprint (rendu graphique unique)
- WebGL fingerprint (carte graphique)
- Audio context fingerprint
- Fonts installées
- Timezone & langue
- Screen resolution
- Plugins navigateur

**Problème :** Playwright sans config = fingerprint identique pour tous les bots

### **Solution : playwright-extra + stealth plugin**

```bash
# Installation
pip install playwright-stealth
```

```python
# tiktok_scraper_v2.py
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

def start_browser(self):
    playwright = sync_playwright().start()

    # Lancer avec args anti-détection
    self.browser = playwright.chromium.launch(
        headless=self.headless,
        args=[
            '--disable-blink-features=AutomationControlled',  # Cache "Je suis un bot"
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ]
    )

    context = self.browser.new_context(
        viewport=self.get_viewport_size(),
        user_agent=self.get_random_user_agent(),
        locale='en-US',  # Change selon géo
        timezone_id='America/New_York',  # Cohérent avec IP proxy
        geolocation={'latitude': 40.7128, 'longitude': -74.0060},  # NYC
        permissions=['geolocation'],
    )

    self.page = context.new_page()

    # ANTI-DÉTECTION : Inject scripts
    stealth_sync(self.page)

    # Override navigator.webdriver
    self.page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)

    return self.page
```

---

## Niveau 4 : Comportement Humain ❌ **MANQUANT - IMPORTANT**

### **Problème :**
Ton bot fait :
```
Page load → Scroll instantané au pixel 1000 → Click profil → Extraire data (0.1s)
```

Un humain fait :
```
Page load → Attendre 2s → Scroll lent 200px → Pause 1s → Scroll 300px →
Hover sur profil → Click → Lire bio 3s → Copier email
```

### **Solution : Simuler comportement humain**

```python
# human_behavior.py
import random
import time

class HumanBehavior:
    """Simule des actions humaines"""

    @staticmethod
    def random_delay(min_sec=1.0, max_sec=3.0):
        """Délai aléatoire"""
        time.sleep(random.uniform(min_sec, max_sec))

    @staticmethod
    def human_scroll(page, distance: int = 500):
        """Scroll progressif comme un humain"""
        scrolled = 0
        while scrolled < distance:
            step = random.randint(80, 150)
            page.evaluate(f"window.scrollBy(0, {step})")
            time.sleep(random.uniform(0.1, 0.3))
            scrolled += step

    @staticmethod
    def human_type(page, selector: str, text: str):
        """Tape du texte avec délai entre chaque lettre"""
        element = page.query_selector(selector)
        element.click()
        for char in text:
            element.type(char)
            time.sleep(random.uniform(0.05, 0.15))

    @staticmethod
    def random_mouse_movement(page):
        """Mouvement aléatoire de souris"""
        x = random.randint(100, 800)
        y = random.randint(100, 600)
        page.mouse.move(x, y)
        time.sleep(random.uniform(0.1, 0.3))

    @staticmethod
    def simulate_reading(min_sec=2, max_sec=5):
        """Simule la lecture d'un texte"""
        time.sleep(random.uniform(min_sec, max_sec))


# Usage dans scraper
from human_behavior import HumanBehavior

def extract_profile_data(self, profile_url: str):
    self.page.goto(profile_url)

    # ❌ AVANT : Instantané
    # bio = self.page.query_selector('[data-e2e="user-bio"]').inner_text()

    # ✅ APRÈS : Humain-like
    HumanBehavior.random_delay(1, 2)  # Attendre chargement
    HumanBehavior.human_scroll(self.page, 300)  # Scroll un peu
    HumanBehavior.random_delay(0.5, 1.5)  # Pause

    bio_element = self.page.query_selector('[data-e2e="user-bio"]')
    if bio_element:
        HumanBehavior.simulate_reading(1, 3)  # "Lire" la bio
        bio = bio_element.inner_text()

    # ... reste du code
```

---

## Niveau 5 : Session Persistence ❌ **MANQUANT**

### **Problème :**
Chaque lancement = nouvelle session vierge = suspect

### **Solution : Cookies persistants**

```python
# session_manager.py
import json
import os

class SessionManager:
    """Gère les cookies entre sessions"""

    def __init__(self, session_file='session_cookies.json'):
        self.session_file = session_file

    def save_cookies(self, context):
        """Sauvegarde les cookies"""
        cookies = context.cookies()
        with open(self.session_file, 'w') as f:
            json.dump(cookies, f)
        print(f"✅ Cookies sauvegardés: {len(cookies)} cookies")

    def load_cookies(self, context):
        """Charge les cookies"""
        if os.path.exists(self.session_file):
            with open(self.session_file, 'r') as f:
                cookies = json.load(f)
                context.add_cookies(cookies)
            print(f"✅ Cookies chargés: {len(cookies)} cookies")
            return True
        return False


# Usage
session_mgr = SessionManager('tiktok_session.json')

def start_browser(self):
    # ... context creation
    session_mgr.load_cookies(context)  # Charger anciens cookies
    self.page = context.new_page()

    # Après scraping
    session_mgr.save_cookies(context)  # Sauver pour prochaine fois
```

**Impact :** TikTok te reconnaît comme "visiteur qui revient" = +confiance

---

## Niveau 6 : Rate Limiting Intelligent ⚠️ **PARTIEL**

### **Ton code actuel :**
```python
DELAY_BETWEEN_REQUESTS = 3  # Fixe
```

### **Problème :** Un humain ne fait pas 1 action toutes les 3.000 secondes exactement

### **Solution : Delays variables + pauses aléatoires**

```python
# smart_rate_limiter.py
import random
import time
from datetime import datetime, timedelta

class SmartRateLimiter:
    """Rate limiting intelligent qui mime un humain"""

    def __init__(self):
        self.request_times = []
        self.break_every = random.randint(15, 25)  # Pause tous les 15-25 profils
        self.requests_since_break = 0

    def wait(self):
        """Attend un temps variable"""
        # Base delay : 3-8 secondes
        delay = random.uniform(3, 8)

        # Augmente le délai si trop de requêtes récentes
        recent = [t for t in self.request_times if t > datetime.now() - timedelta(minutes=5)]
        if len(recent) > 20:
            delay *= 1.5  # Ralentit

        time.sleep(delay)
        self.request_times.append(datetime.now())
        self.requests_since_break += 1

        # Pause longue tous les X profils (humain fait des pauses)
        if self.requests_since_break >= self.break_every:
            pause = random.randint(60, 180)  # 1-3 minutes
            print(f"☕ Pause humaine: {pause}s")
            time.sleep(pause)
            self.requests_since_break = 0
            self.break_every = random.randint(15, 25)

    def get_stats(self):
        """Stats de requêtes"""
        now = datetime.now()
        last_hour = [t for t in self.request_times if t > now - timedelta(hours=1)]
        return {
            'total': len(self.request_times),
            'last_hour': len(last_hour),
            'rate': len(last_hour),  # req/h
        }


# Usage
rate_limiter = SmartRateLimiter()

for profile_url in profile_urls:
    rate_limiter.wait()  # Attend intelligemment
    extract_profile_data(profile_url)
```

---

## Niveau 7 : CAPTCHA Detection ❌ **MANQUANT - CRUCIAL**

### **Problème :**
Si TikTok détecte un bot → CAPTCHA → Ton script crash

### **Solution : Détecter et gérer les CAPTCHAs**

```python
# captcha_detector.py

class CaptchaDetector:
    """Détecte les CAPTCHAs et arrête le scraping"""

    @staticmethod
    def check_for_captcha(page) -> bool:
        """Vérifie si un CAPTCHA est présent"""

        # Patterns TikTok
        captcha_selectors = [
            'iframe[src*="captcha"]',
            'div[class*="captcha"]',
            'div[class*="verify"]',
            '#px-captcha',
            '.recaptcha',
        ]

        for selector in captcha_selectors:
            if page.query_selector(selector):
                return True

        # Check text
        text = page.text_content('body').lower()
        if 'verify you are human' in text or 'captcha' in text:
            return True

        return False

    @staticmethod
    def handle_captcha(page, scraper):
        """Gestion du CAPTCHA"""
        print("🚨 CAPTCHA DÉTECTÉ!")
        print("Options:")
        print("1. Attendre et résoudre manuellement (mode --no-headless)")
        print("2. Changer de proxy")
        print("3. Arrêter le scraping pour 24h")

        # Sauvegarder progression
        scraper.save_progress()

        # Screenshot pour debug
        page.screenshot(path='captcha_detected.png')

        # Arrêter le scraping
        raise Exception("CAPTCHA détecté - Arrêt du scraping")


# Dans ton scraper
def extract_profile_data(self, profile_url):
    self.page.goto(profile_url)

    # CHECK CAPTCHA
    if CaptchaDetector.check_for_captcha(self.page):
        CaptchaDetector.handle_captcha(self.page, self)

    # Continue normalement...
```

---

# 🔥 CONFIGURATION ANTI-DÉTECTION ULTIME

## Setup Complet (Copie-Colle Ready)

```python
# anti_detection_config.py

"""
Configuration anti-détection complète pour scraping TikTok/Twitter
"""

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from playwright_stealth import stealth_sync
import random
from typing import Dict, Tuple

class AntiDetectionBrowser:
    """
    Navigateur configuré avec toutes les techniques anti-détection
    """

    # Pool de configurations réalistes
    PROFILES = [
        {
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'viewport': {'width': 1920, 'height': 1080},
            'locale': 'en-US',
            'timezone': 'America/New_York',
            'geo': {'latitude': 40.7128, 'longitude': -74.0060},
        },
        {
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'viewport': {'width': 1440, 'height': 900},
            'locale': 'en-US',
            'timezone': 'America/Los_Angeles',
            'geo': {'latitude': 34.0522, 'longitude': -118.2437},
        },
        {
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'viewport': {'width': 1366, 'height': 768},
            'locale': 'en-GB',
            'timezone': 'Europe/London',
            'geo': {'latitude': 51.5074, 'longitude': -0.1278},
        },
    ]

    def __init__(self, headless: bool = True, proxy: Dict = None):
        self.headless = headless
        self.proxy = proxy
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None

    def get_random_profile(self) -> Dict:
        """Retourne un profil aléatoire"""
        return random.choice(self.PROFILES)

    def launch(self):
        """Lance le navigateur avec configuration anti-détection"""

        profile = self.get_random_profile()

        playwright = sync_playwright().start()

        # Args Chrome anti-détection
        args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-site-isolation-trials',
            f'--window-size={profile["viewport"]["width"]},{profile["viewport"]["height"]}',
        ]

        # Lancer avec ou sans proxy
        launch_options = {
            'headless': self.headless,
            'args': args,
        }

        if self.proxy:
            launch_options['proxy'] = self.proxy

        self.browser = playwright.chromium.launch(**launch_options)

        # Context avec empreinte humaine
        self.context = self.browser.new_context(
            viewport=profile['viewport'],
            user_agent=profile['user_agent'],
            locale=profile['locale'],
            timezone_id=profile['timezone'],
            geolocation=profile['geo'],
            permissions=['geolocation'],
            color_scheme='light',  # ou 'dark' aléatoire
            has_touch=False,
            is_mobile=False,
        )

        # Page
        self.page = self.context.new_page()

        # Inject anti-détection scripts
        self._inject_anti_detection_scripts()

        print(f"🌐 Navigateur lancé: {profile['locale']} | {profile['timezone']}")

        return self.page

    def _inject_anti_detection_scripts(self):
        """Injecte des scripts pour masquer l'automatisation"""

        # 1. Stealth plugin
        stealth_sync(self.page)

        # 2. Override navigator.webdriver
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # 3. Override Chrome detection
        self.page.add_init_script("""
            window.navigator.chrome = {
                runtime: {},
            };
        """)

        # 4. Override permissions
        self.page.add_init_script("""
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

        # 5. Override plugins
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
        """)

    def close(self):
        """Ferme le navigateur"""
        if self.browser:
            self.browser.close()


# USAGE
if __name__ == "__main__":
    # Sans proxy
    browser = AntiDetectionBrowser(headless=False)
    page = browser.launch()

    # Test
    page.goto('https://bot.sannysoft.com/')
    input("Appuie sur Entrée pour fermer...")

    browser.close()
```

**Test ce script sur https://bot.sannysoft.com/ pour voir si détecté**

---

# 📊 SCORING : Niveau de Protection

| Technique | Sans | Basique | Ton Code | Anti-Detect Pro |
|-----------|------|---------|----------|-----------------|
| User-Agent rotation | ❌ | ✅ | ✅ | ✅ |
| Headers HTTP | ❌ | ✅ | ✅ | ✅ |
| Fingerprint masking | ❌ | ❌ | ❌ | ✅ |
| Human behavior | ❌ | ❌ | ❌ | ✅ |
| Cookie persistence | ❌ | ❌ | ❌ | ✅ |
| Smart rate limit | ❌ | Fixe | Fixe | ✅ |
| CAPTCHA detection | ❌ | ❌ | ❌ | ✅ |
| **Taux de détection** | 100% | 70% | 50% | 5-10% |

---

# ✅ CHECKLIST ANTI-DÉTECTION

Avant de lancer en production :

- [ ] Proxies résidentiels/mobiles activés
- [ ] User-Agent rotation (7+ UAs)
- [ ] Viewport aléatoire
- [ ] Timezone cohérent avec IP proxy
- [ ] playwright-stealth installé
- [ ] Scripts anti-fingerprinting injectés
- [ ] Comportement humain (scroll, pauses)
- [ ] Rate limiting intelligent (pauses)
- [ ] Cookies persistants entre sessions
- [ ] CAPTCHA detection
- [ ] Session rotation tous les 20-30 profils

---

**PROCHAINE SECTION : Infrastructure & Scaling →**
