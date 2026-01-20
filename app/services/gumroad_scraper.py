import httpx
import json
import asyncio
import tempfile
import os
import random
import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class GumroadScraperException(Exception):
    """Exception personnalisee pour erreurs Gumroad specifiques"""
    pass


async def scrape_gumroad_profile(profile_url: str) -> List[Dict]:
    """
    Scrape profil Gumroad public via extraction __NEXT_DATA__ (Next.js)
    PUIS deep scraping parallele pour descriptions completes

    Strategie:
    1. Extraction JSON __NEXT_DATA__ depuis page profil (liste produits)
    2. Deep scraping parallele de chaque page produit pour description complete
    3. Fusion des donnees

    Args:
        profile_url: https://username.gumroad.com

    Returns:
        Liste produits avec metadonnees completes + descriptions enrichies

    Raises:
        GumroadScraperException: Si fetch echoue avec message specifique
    """
    products = []

    # Headers anti-detection (moderne, simule Chrome 120 - ULTRA COMPLET)
    # NOTE: Accept-Encoding sans 'br' pour forcer texte clair (brotli peut poser probleme si lib pas installee)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9,fr-FR;q=0.8,fr;q=0.7',
        'Accept-Encoding': 'gzip, deflate',  # Pas 'br' pour eviter probleme decompression Brotli
        'Referer': 'https://www.google.com/',
        'Alt-Used': 'gumroad.com',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
        try:
            logger.info(f"[GUMROAD] Fetching profile: {profile_url}")
            resp = await client.get(profile_url)

            # Gestion erreurs specifiques par status code
            if resp.status_code == 404:
                logger.error(f"[GUMROAD] Profile not found: {profile_url}")
                raise GumroadScraperException("Ce profil Gumroad n'existe pas.")
            elif resp.status_code == 403:
                logger.error(f"[GUMROAD] Access forbidden (bot detection or private): {profile_url}")
                raise GumroadScraperException("Acces refuse par Gumroad (Protection Bot ou profil prive).")
            elif resp.status_code == 429:
                logger.error(f"[GUMROAD] Rate limited: {profile_url}")
                raise GumroadScraperException("Gumroad est surcharge. Reessayez dans 5 minutes.")
            elif resp.status_code >= 500:
                logger.error(f"[GUMROAD] Server error: HTTP {resp.status_code}")
                raise GumroadScraperException(f"Erreur serveur chez Gumroad (HTTP {resp.status_code}).")
            elif resp.status_code != 200:
                logger.error(f"[GUMROAD] Unexpected HTTP {resp.status_code}")
                raise GumroadScraperException(f"Erreur inattendue: HTTP {resp.status_code}")

            html_content = resp.text
            soup = BeautifulSoup(html_content, 'lxml')

            # DEBUG: Logger preview HTML et chercher __NEXT_DATA__
            logger.info(f"[GUMROAD] HTML length: {len(html_content)} chars")
            logger.info(f"[GUMROAD] HTML preview (first 1000 chars): {html_content[:1000]}")

            # Logger aussi les headers de reponse pour detecter redirections
            logger.info(f"[GUMROAD] Response headers: {dict(resp.headers)}")

            # Chercher si __NEXT_DATA__ existe QUELQUE PART dans le HTML
            if '__NEXT_DATA__' in html_content:
                logger.info("[GUMROAD] __NEXT_DATA__ found in HTML content")
            else:
                logger.warning("[GUMROAD] __NEXT_DATA__ NOT found in HTML content at all")

            # Lister tous les script tags pour debug
            all_scripts = soup.find_all('script')
            logger.info(f"[GUMROAD] Found {len(all_scripts)} total script tags")
            for idx, script in enumerate(all_scripts[:10]):  # Limit to 10 pour pas spammer
                script_id = script.get('id', 'no-id')
                script_type = script.get('type', 'no-type')
                script_len = len(script.string) if script.string else 0
                logger.debug(f"[GUMROAD] Script {idx}: id='{script_id}', type='{script_type}', length={script_len}")

            # Strategie 1: __NEXT_DATA__ (Next.js) - LA MINE D'OR
            logger.info("[GUMROAD] Attempting __NEXT_DATA__ extraction (Next.js)")
            script_tag = soup.find('script', id='__NEXT_DATA__', type='application/json')

            # Essayer aussi SANS le type attribute (parfois Gumroad ne l'inclut pas)
            if not script_tag:
                logger.info("[GUMROAD] Trying without type='application/json' attribute...")
                script_tag = soup.find('script', id='__NEXT_DATA__')

            if script_tag:
                try:
                    data = json.loads(script_tag.string)
                    logger.info("[GUMROAD] Successfully parsed __NEXT_DATA__ JSON")

                    # Navigation securisee dans structure JSON
                    # Chemin: props -> pageProps -> products
                    products_raw = data.get('props', {}).get('pageProps', {}).get('products', [])

                    if not products_raw:
                        logger.warning("[GUMROAD] __NEXT_DATA__ found but no products in expected path")
                    else:
                        logger.info(f"[GUMROAD] Found {len(products_raw)} products in __NEXT_DATA__")

                        # Parser liste produits (donnees basiques)
                        for p in products_raw:
                            product = parse_nextjs_product(p, profile_url)
                            if product:
                                products.append(product)

                        # Deep scraping parallele pour descriptions completes
                        if products:
                            logger.info(f"[GUMROAD] Starting parallel deep scraping for {len(products)} products...")
                            products = await enrich_products_parallel(client, products, headers)

                        return products

                except json.JSONDecodeError as e:
                    logger.error(f"[GUMROAD] Failed to parse __NEXT_DATA__ JSON: {e}")

            # Strategie 2: Fallback - Chercher JSON dans TOUS les scripts
            logger.warning("[GUMROAD] __NEXT_DATA__ not found, trying JSON extraction from all scripts...")
            products = extract_products_from_scripts(soup, profile_url)
            if products:
                logger.info(f"[GUMROAD] Found {len(products)} products via script JSON extraction")
                return products

            # Strategie 3: Fallback OpenGraph (page produit unique)
            logger.warning("[GUMROAD] Script JSON extraction failed, trying OpenGraph fallback...")
            og_product = extract_opengraph_product(soup, profile_url)
            if og_product:
                logger.info("[GUMROAD] Found product via OpenGraph meta tags")
                return [og_product]

            # Echec complet - Sauvegarder HTML pour debug
            logger.error("[GUMROAD] No products found via any extraction method")

            # Sauvegarder HTML pour inspection manuelle (debug)
            try:
                debug_file = f"/tmp/gumroad_debug_{profile_url.split('/')[-1]}.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"[GUMROAD] HTML saved to {debug_file} for manual inspection")
            except Exception as e:
                logger.debug(f"[GUMROAD] Could not save debug HTML: {e}")

            raise GumroadScraperException("Aucun produit trouve. Verifiez que le profil est public et contient des produits.")

        except httpx.TimeoutException:
            logger.error(f"[GUMROAD] Timeout fetching {profile_url}")
            raise GumroadScraperException("Delai d'attente depasse - Gumroad est lent ou inaccessible.")
        except GumroadScraperException:
            raise  # Re-raise exceptions personnalisees
        except Exception as e:
            logger.error(f"[GUMROAD] Unexpected error: {e}")
            raise GumroadScraperException(f"Erreur inattendue lors du scraping: {str(e)}")


def parse_nextjs_product(product_data: dict, profile_url: str) -> Optional[Dict]:
    """
    Parser un produit depuis __NEXT_DATA__ JSON (page profil)

    Args:
        product_data: Dict JSON du produit
        profile_url: URL du profil (pour construire URLs completes)

    Returns:
        Dict normalise ou None si invalide
    """
    try:
        # DEBUG: Logger le JSON COMPLET du produit pour debug (identifier champs prix/description)
        logger.info(f"[GUMROAD] ===== PRODUCT JSON COMPLET =====")
        logger.info(f"[GUMROAD] {json.dumps(product_data, indent=2)}")
        logger.info(f"[GUMROAD] ===== FIN PRODUCT JSON =====")

        # Extraire champs Next.js structure
        title = product_data.get('name') or product_data.get('title', 'Sans titre')

        # Prix - Essayer TOUS les champs possibles dans l'ordre de priorité
        price = 0.0

        # Essayer 10+ champs différents
        price_fields = [
            ('price_display', product_data.get('price_display')),           # Ex: "$29"
            ('formatted_price', product_data.get('formatted_price')),       # Ex: "$29.00"
            ('price', product_data.get('price')),                           # Ex: 29.0 ou "$29"
            ('price_cents', product_data.get('price_cents')),               # Ex: 2900
            ('amount', product_data.get('amount')),                         # Alternative
            ('cost', product_data.get('cost')),                             # Alternative
            ('suggested_price', product_data.get('suggested_price')),       # Prix suggéré
            ('minimum_price', product_data.get('minimum_price')),           # Prix minimum
            ('base_price', product_data.get('base_price')),                 # Prix de base
            ('price_in_cents', product_data.get('price_in_cents')),         # En centimes
        ]

        logger.info(f"[GUMROAD] Prix - Recherche dans {len(price_fields)} champs possibles...")

        for field_name, field_value in price_fields:
            if field_value is not None:
                logger.info(f"[GUMROAD] Prix - Champ '{field_name}' trouvé: {field_value} (type: {type(field_value).__name__})")

                # Si c'est un nombre entier (centimes)
                if isinstance(field_value, int) and field_value > 100:
                    price = float(field_value) / 100.0
                    logger.info(f"[GUMROAD] Prix - Converti depuis centimes: ${price:.2f}")
                    break

                # Si c'est un float
                elif isinstance(field_value, (float, int)):
                    price = float(field_value)
                    logger.info(f"[GUMROAD] Prix - Valeur numérique directe: ${price:.2f}")
                    break

                # Si c'est une string, parser
                elif isinstance(field_value, str):
                    price = parse_price(field_value)
                    if price > 0:
                        logger.info(f"[GUMROAD] Prix - Parsé depuis string: ${price:.2f}")
                        break

        if price == 0.0:
            logger.warning(f"[GUMROAD] AUCUN PRIX TROUVÉ - Tous les champs sont None ou invalides")
        else:
            logger.info(f"[GUMROAD] ✅ Prix final extrait: ${price:.2f}")

        # Description - Essayer plusieurs champs possibles
        description_fields = [
            ('description', product_data.get('description')),
            ('short_description', product_data.get('short_description')),
            ('summary', product_data.get('summary')),
            ('description_html', product_data.get('description_html')),
            ('content', product_data.get('content')),
            ('preview_text', product_data.get('preview_text')),
        ]

        description = ''
        for field_name, field_value in description_fields:
            if field_value and isinstance(field_value, str) and len(field_value.strip()) > 0:
                description = field_value
                logger.info(f"[GUMROAD] Description trouvée dans champ '{field_name}': {len(description)} caractères")
                logger.debug(f"[GUMROAD] Description preview: {description[:200]}...")
                break

        if not description:
            logger.warning(f"[GUMROAD] AUCUNE DESCRIPTION TROUVÉE - Tous les champs description vides")

        # Image
        image_url = (
            product_data.get('thumbnail_url') or
            product_data.get('cover_image_url') or
            product_data.get('preview_url')
        )

        # URL produit
        permalink = product_data.get('permalink')
        if permalink:
            # Extraire username depuis profile_url
            # Ex: https://tallguytycoon.gumroad.com -> tallguytycoon
            if '.gumroad.com' in profile_url:
                username = profile_url.split('//')[1].split('.gumroad.com')[0]
                product_url = f"https://{username}.gumroad.com/l/{permalink}"
            else:
                # Fallback pour format https://gumroad.com/username
                product_url = f"https://gumroad.com/l/{permalink}"
        else:
            product_url = None

        # Metadonnees additionnelles
        product_id = product_data.get('id')

        # Rating et avis
        rating = product_data.get('average_rating', 0) or product_data.get('rating', 0)
        reviews_count = product_data.get('reviews_count', 0) or product_data.get('ratings_count', 0)

        # Ventes - Essayer plusieurs champs possibles
        sales_count = (
            product_data.get('sales_count') or
            product_data.get('sales') or
            product_data.get('purchases_count') or
            0
        )

        # Vues (si disponible)
        views_count = product_data.get('views_count', 0) or product_data.get('views', 0)

        logger.debug(f"[GUMROAD] Extracted stats: sales={sales_count}, rating={rating}, reviews={reviews_count}, views={views_count}")

        # Categorisation automatique par mots-cles
        category = auto_categorize(title, description)

        return {
            'title': title,
            'price': price,
            'description': description,  # Description courte (sera enrichie)
            'image_url': image_url,
            'gumroad_url': product_url,
            'product_id': product_id,
            'rating': rating,
            'reviews_count': reviews_count,
            'sales_count': sales_count,
            'views_count': views_count,
            'category': category
        }

    except Exception as e:
        logger.warning(f"[GUMROAD] Failed to parse product: {e}")
        return None


def auto_categorize(title: str, description: str) -> str:
    """
    Categorisation automatique basee sur mots-cles

    Args:
        title: Titre du produit
        description: Description du produit

    Returns:
        Categorie detectee
    """
    # Combiner titre et description en minuscules
    text = f"{title} {description}".lower()

    # Categories avec mots-cles
    categories = {
        'Outils & Tech': ['bot', 'python', 'script', 'code', 'api', 'tool', 'automation', 'software', 'app', 'plugin', 'extension', 'telegram', 'discord'],
        'Finance & Crypto': ['invest', 'trading', 'crypto', 'bitcoin', 'ethereum', 'solana', 'nft', 'defi', 'forex', 'stock', 'finance'],
        'Formation': ['course', 'training', 'tutorial', 'guide', 'learn', 'formation', 'masterclass', 'ebook', 'pdf', 'video'],
        'Design & Graphisme': ['design', 'template', 'graphic', 'logo', 'ui', 'ux', 'figma', 'photoshop', 'illustrator', 'mockup'],
        'Marketing': ['marketing', 'seo', 'ads', 'social media', 'growth', 'email', 'funnel', 'landing page'],
    }

    # Chercher correspondances
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in text:
                logger.debug(f"[GUMROAD] Auto-categorized as '{category}' (keyword: '{keyword}')")
                return category

    # Categorie par defaut
    return 'Autre'


async def enrich_products_parallel(client: httpx.AsyncClient, products: List[Dict], headers: dict) -> List[Dict]:
    """
    Deep scraping parallele pour enrichir produits avec descriptions completes

    Utilise asyncio.gather pour fetch TOUTES les pages produits en parallele

    Args:
        client: httpx client (reutilise pour performance)
        products: Liste produits avec donnees basiques
        headers: HTTP headers

    Returns:
        Liste produits enrichis avec descriptions completes
    """
    logger.info(f"[GUMROAD] Launching {len(products)} parallel requests for full descriptions...")

    # Creer taches paralleles
    tasks = []
    for product in products:
        product_url = product.get('gumroad_url')
        if product_url:
            tasks.append(fetch_full_description(client, product_url, headers))
        else:
            tasks.append(asyncio.sleep(0))  # Placeholder pour garder meme index

    # Executer TOUTES les requetes en parallele
    full_descriptions = await asyncio.gather(*tasks, return_exceptions=True)

    # Fusionner descriptions avec produits
    enriched_products = []
    for idx, product in enumerate(products):
        desc = full_descriptions[idx]

        # Si erreur ou pas de description, garder description courte
        if isinstance(desc, Exception):
            logger.warning(f"[GUMROAD] Failed to fetch description for {product.get('title')}: {desc}")
            product['full_description'] = product.get('description', '')
        elif desc:
            product['full_description'] = desc
            # Remplacer description courte par complete
            product['description'] = clean_html_for_telegram(desc)
        else:
            product['full_description'] = product.get('description', '')

        enriched_products.append(product)

    logger.info(f"[GUMROAD] Successfully enriched {len(enriched_products)} products")
    return enriched_products


async def fetch_full_description(client: httpx.AsyncClient, product_url: str, headers: dict) -> str:
    """
    Fetch description complete depuis page produit individuelle

    Args:
        client: httpx client
        product_url: URL du produit
        headers: HTTP headers

    Returns:
        Description HTML complete
    """
    try:
        # Jitter pour eviter detection pattern (delai aleatoire 0.5-2s)
        await asyncio.sleep(random.uniform(0.5, 2.0))

        logger.debug(f"[GUMROAD] Fetching description from: {product_url}")
        resp = await client.get(product_url, timeout=15.0)

        if resp.status_code != 200:
            logger.warning(f"[GUMROAD] HTTP {resp.status_code} for product page: {product_url}")
            return ""

        soup = BeautifulSoup(resp.text, 'lxml')

        # Chercher __NEXT_DATA__ dans page produit
        script_tag = soup.find('script', id='__NEXT_DATA__', type='application/json')

        if script_tag:
            data = json.loads(script_tag.string)

            # Dans page produit, structure est: props.pageProps.product (singulier)
            product_data = data.get('props', {}).get('pageProps', {}).get('product', {})

            # Description HTML complete
            description_html = (
                product_data.get('description_html') or
                product_data.get('description') or
                ""
            )

            if description_html:
                logger.debug(f"[GUMROAD] Found description ({len(description_html)} chars)")
                return description_html

        # Fallback: Chercher dans HTML
        desc_elem = soup.find('div', class_=re.compile(r'description|content', re.I))
        if desc_elem:
            return desc_elem.get_text(separator='\n', strip=True)

        logger.warning(f"[GUMROAD] No description found for {product_url}")
        return ""

    except Exception as e:
        logger.error(f"[GUMROAD] Error fetching product description: {e}")
        return ""


def extract_products_from_scripts(soup: BeautifulSoup, profile_url: str) -> List[Dict]:
    """
    Fallback: Chercher produits dans TOUS les script tags via patterns JSON

    Strategie aggressive: cherche "products", "items", "permalink" dans tous les scripts

    Args:
        soup: BeautifulSoup object
        profile_url: URL du profil

    Returns:
        Liste produits trouves
    """
    products = []

    try:
        all_scripts = soup.find_all('script')
        logger.info(f"[GUMROAD] Scanning {len(all_scripts)} scripts for product data...")

        for idx, script in enumerate(all_scripts):
            if not script.string:
                continue

            script_content = script.string.strip()

            # Skip scripts trop petits ou trop gros
            if len(script_content) < 100 or len(script_content) > 5000000:
                continue

            # Chercher mots-cles produits
            has_products = 'products' in script_content or 'permalink' in script_content
            if not has_products:
                continue

            logger.info(f"[GUMROAD] Script {idx} contains product keywords, attempting extraction...")

            # Patterns JSON a chercher
            patterns = [
                # Pattern 1: Variable assignment avec products
                r'(?:var|let|const)\s+\w+\s*=\s*(\{[^}]*"products"\s*:\s*\[.*?\].*?\})',
                # Pattern 2: Object literal avec products
                r'(\{"props":\{[^}]*"products"\s*:\s*\[.*?\]\})',
                # Pattern 3: Juste un array de produits
                r'"products"\s*:\s*(\[.*?\])',
                # Pattern 4: window.* assignment
                r'window\.\w+\s*=\s*(\{.*?"products".*?\})',
            ]

            for pattern in patterns:
                try:
                    matches = re.finditer(pattern, script_content, re.DOTALL)
                    for match in matches:
                        json_str = match.group(1)

                        # Limiter taille
                        if len(json_str) > 1000000:
                            continue

                        try:
                            data = json.loads(json_str)

                            # Extraire produits selon structure
                            products_raw = None
                            if isinstance(data, list):
                                products_raw = data
                            elif isinstance(data, dict):
                                if 'products' in data:
                                    products_raw = data['products']
                                elif 'props' in data:
                                    products_raw = data.get('props', {}).get('pageProps', {}).get('products', [])

                            if products_raw and isinstance(products_raw, list):
                                logger.info(f"[GUMROAD] Found {len(products_raw)} products in script {idx}")
                                for p in products_raw:
                                    product = parse_nextjs_product(p, profile_url)
                                    if product:
                                        products.append(product)

                                if products:
                                    return products  # Retourne des que produits trouves

                        except json.JSONDecodeError:
                            continue

                except Exception as e:
                    logger.debug(f"[GUMROAD] Pattern matching error: {e}")
                    continue

        logger.warning(f"[GUMROAD] No products found in {len(all_scripts)} scripts")
        return products

    except Exception as e:
        logger.error(f"[GUMROAD] Script extraction error: {e}")
        return []


def extract_opengraph_product(soup: BeautifulSoup, url: str) -> Optional[Dict]:
    """
    Fallback: Extraire produit depuis meta tags OpenGraph (page produit unique)

    Args:
        soup: BeautifulSoup object
        url: URL de la page

    Returns:
        Dict produit ou None
    """
    try:
        og_title = soup.find('meta', property='og:title')
        og_desc = soup.find('meta', property='og:description')
        og_image = soup.find('meta', property='og:image')
        og_price = soup.find('meta', property='og:price:amount')

        if og_title:
            title = og_title.get('content', 'Sans titre')
            description = og_desc.get('content', '') if og_desc else ''
            image_url = og_image.get('content') if og_image else None
            price = parse_price(og_price.get('content', '0')) if og_price else 0.0

            return {
                'title': title,
                'price': price,
                'description': description,
                'image_url': image_url,
                'gumroad_url': url,
                'product_id': None,
                'rating': 0
            }

    except Exception as e:
        logger.debug(f"[GUMROAD] OpenGraph extraction failed: {e}")

    return None


def clean_html_for_telegram(html_text: str) -> str:
    """
    Nettoie HTML pour compatibilite Telegram

    Telegram supporte seulement: <b>, <i>, <u>, <s>, <a>, <code>, <pre>
    Limite: 4096 caracteres

    Args:
        html_text: HTML brut

    Returns:
        Texte nettoye compatible Telegram
    """
    if not html_text:
        return ""

    # Supprimer balises non supportees (garder contenu)
    # Telegram supporte: b, i, u, s, a, code, pre
    # On supprime: div, span, p, h1-h6, etc.
    soup = BeautifulSoup(html_text, 'lxml')

    # Convertir headings en bold
    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        tag.name = 'b'

    # Supprimer balises mais garder texte
    for tag in soup.find_all(['div', 'span', 'p', 'section', 'article']):
        tag.unwrap()

    # Extraire texte avec balises supportees
    cleaned = str(soup)

    # Limiter longueur (Telegram max 4096 chars)
    if len(cleaned) > 4000:
        cleaned = cleaned[:4000] + "..."

    return cleaned


def parse_price(price_str: str) -> float:
    """
    Parser prix Gumroad

    Examples:
        "$19.99" -> 19.99
        "$1,234.56" -> 1234.56
        "Free" -> 0.0
        "19.99" -> 19.99
    """
    if not price_str:
        return 0.0

    price_str = str(price_str).strip()

    if price_str.lower() in ['free', 'gratuit', '0']:
        return 0.0

    # Supprimer symboles et espaces
    cleaned = re.sub(r'[^\d.]', '', price_str)

    try:
        return float(cleaned)
    except (ValueError, TypeError):
        logger.warning(f"[GUMROAD] Failed to parse price: {price_str}")
        return 0.0


async def download_cover_image(image_url: str, product_id: str) -> str:
    """
    Telecharger image cover vers B2/R2

    Args:
        image_url: URL image Gumroad
        product_id: ID produit genere

    Returns:
        URL B2/R2 de l'image uploadee

    Raises:
        Exception: Si download ou upload echoue
    """
    from app.services.b2_storage_service import B2StorageService

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        try:
            logger.info(f"[GUMROAD] Downloading cover image: {image_url}")
            resp = await client.get(image_url)

            if resp.status_code != 200:
                raise Exception(f"Failed to download image: HTTP {resp.status_code}")

            # Detecter extension
            ext = 'jpg'
            content_type = resp.headers.get('content-type', '')
            if 'png' in content_type:
                ext = 'png'
            elif 'webp' in content_type:
                ext = 'webp'
            elif 'gif' in content_type:
                ext = 'gif'
            else:
                # Tenter depuis URL
                url_ext = image_url.split('.')[-1].split('?')[0].lower()
                if url_ext in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
                    ext = url_ext

            # Sauvegarder temporairement avec tempfile
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=f".{ext}",
                prefix=f"gumroad_cover_{product_id}_"
            ) as temp_file:
                temp_file.write(resp.content)
                temp_path = temp_file.name

            try:
                # Upload vers B2/R2
                b2 = B2StorageService()
                object_key = f"products/imported/gumroad/{product_id}/cover.{ext}"

                url = await b2.upload_file(temp_path, object_key)

                logger.info(f"[GUMROAD] Cover image uploaded: {url}")
                return url

            finally:
                # Cleanup
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        except Exception as e:
            logger.error(f"[GUMROAD] Cover image download error: {e}")
            raise
