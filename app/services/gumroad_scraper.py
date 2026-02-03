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
                logger.info(f"[GUMROAD] ✅ Found {len(products)} products via script JSON extraction")
                logger.info(f"[GUMROAD] 🔍 Products BEFORE enrichment - checking URLs:")
                for idx, p in enumerate(products):
                    logger.info(f"[GUMROAD]   Product {idx+1}: '{p.get('title')}' - URL: {p.get('gumroad_url')} - Desc length: {len(p.get('description', ''))}")

                # Deep scraping parallele pour descriptions completes
                logger.info(f"[GUMROAD] 🚀 STARTING parallel deep scraping for {len(products)} products...")
                products = await enrich_products_parallel(client, products, headers)
                logger.info(f"[GUMROAD] ✅ FINISHED parallel deep scraping")

                logger.info(f"[GUMROAD] 🔍 Products AFTER enrichment - checking descriptions:")
                for idx, p in enumerate(products):
                    logger.info(f"[GUMROAD]   Product {idx+1}: '{p.get('title')}' - Desc length: {len(p.get('description', ''))}")

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

        # Description - Essayer plusieurs champs possibles (priorité aux champs texte pur)
        description_fields = [
            ('description', product_data.get('description')),  # Texte pur prioritaire
            ('short_description', product_data.get('short_description')),
            ('summary', product_data.get('summary')),
            ('preview_text', product_data.get('preview_text')),
            ('description_html', product_data.get('description_html')),  # HTML en dernier recours
            ('content', product_data.get('content')),
        ]

        description = ''
        for field_name, field_value in description_fields:
            if field_value and isinstance(field_value, str) and len(field_value.strip()) > 0:
                # Si c'est un champ HTML, nettoyer immédiatement
                if 'html' in field_name.lower() or '<' in field_value:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(field_value, 'lxml')
                    description = soup.get_text(separator=' ', strip=True)
                    logger.info(f"[GUMROAD] Description HTML nettoyée depuis '{field_name}': {len(description)} caractères")
                else:
                    description = field_value
                    logger.info(f"[GUMROAD] Description trouvée dans champ '{field_name}': {len(description)} caractères")

                logger.debug(f"[GUMROAD] Description preview: {description[:200]}...")
                break

        if not description:
            logger.warning(f"[GUMROAD] AUCUNE DESCRIPTION TROUVÉE - Tous les champs description vides")

        # Image - Ensure absolute URL
        # Essayer plusieurs sources (profil vs page produit ont structures differentes)
        image_url = (
            product_data.get('thumbnail_url') or
            product_data.get('cover_image_url') or
            product_data.get('preview_url') or
            (product_data.get('covers', [{}])[0].get('url') if product_data.get('covers') else None)
        )

        # Ensure image URL is absolute
        if image_url and not image_url.startswith('http'):
            # If relative URL, prefix with Gumroad CDN
            if image_url.startswith('/'):
                image_url = f"https://public-files.gumroad.com{image_url}"
            else:
                image_url = f"https://public-files.gumroad.com/{image_url}"

        logger.info(f"[GUMROAD] Product '{title}' - image_url: {image_url} (from thumbnail_url={product_data.get('thumbnail_url')}, cover_image_url={product_data.get('cover_image_url')}, preview_url={product_data.get('preview_url')})")

        # URL produit avec ?layout=profile pour acceder à la description complete
        permalink = product_data.get('permalink')
        if permalink:
            # Extraire username depuis profile_url
            # Ex: https://tallguytycoon.gumroad.com -> tallguytycoon
            if '.gumroad.com' in profile_url:
                username = profile_url.split('//')[1].split('.gumroad.com')[0]
                product_url = f"https://{username}.gumroad.com/l/{permalink}?layout=profile"
            else:
                # Fallback pour format https://gumroad.com/username
                product_url = f"https://gumroad.com/l/{permalink}?layout=profile"
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
    Retourne None pour forcer user a selectionner categorie dans mini-app

    Args:
        title: Titre du produit
        description: Description du produit

    Returns:
        None (user DOIT choisir dans mini-app)
    """
    return None


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
    logger.info(f"[GUMROAD] 🌟🌟🌟 ENTERING enrich_products_parallel() with {len(products)} products")
    logger.info(f"[GUMROAD] Launching {len(products)} parallel requests for full descriptions...")

    # Creer taches paralleles
    tasks = []
    for product in products:
        product_url = product.get('gumroad_url')
        product_title = product.get('title', 'Unknown')
        if product_url:
            logger.debug(f"[GUMROAD] Queuing deep scrape for '{product_title}': {product_url}")
            tasks.append(fetch_full_description(client, product_url, headers))
        else:
            logger.warning(f"[GUMROAD] No URL for product '{product_title}', skipping deep scrape")
            tasks.append(asyncio.sleep(0))  # Placeholder pour garder meme index

    # Executer TOUTES les requetes en parallele
    logger.info(f"[GUMROAD] Executing {len(tasks)} parallel requests...")
    full_descriptions = await asyncio.gather(*tasks, return_exceptions=True)
    logger.info(f"[GUMROAD] Parallel requests completed")

    # Fusionner descriptions avec produits
    enriched_products = []
    for idx, product in enumerate(products):
        desc = full_descriptions[idx]
        product_title = product.get('title', 'Unknown')

        # Si erreur ou pas de description, garder description courte
        if isinstance(desc, Exception):
            logger.warning(f"[GUMROAD] Failed to fetch description for '{product_title}': {desc}")
            product['full_description'] = product.get('description', '')
            logger.info(f"[GUMROAD] Product '{product_title}' - Using short description ({len(product.get('description', ''))} chars)")
        elif desc:
            product['full_description'] = desc
            # Remplacer description courte par complete
            product['description'] = clean_html_for_telegram(desc)
            logger.info(f"[GUMROAD] Product '{product_title}' - Enriched with full description ({len(desc)} chars)")
        else:
            product['full_description'] = product.get('description', '')
            logger.warning(f"[GUMROAD] Product '{product_title}' - No full description found, using short ({len(product.get('description', ''))} chars)")

        enriched_products.append(product)

    logger.info(f"[GUMROAD] Successfully enriched {len(enriched_products)} products")
    return enriched_products


async def fetch_full_description(client: httpx.AsyncClient, product_url: str, headers: dict) -> str:
    """
    Fetch description complete depuis page produit individuelle avec retry logic

    Args:
        client: httpx client
        product_url: URL du produit
        headers: HTTP headers

    Returns:
        Description HTML complete
    """
    # Retry logic pour gerer rate limiting et timeouts
    max_retries = 3
    soup = None

    for attempt in range(max_retries):
        try:
            # Jitter pour eviter detection pattern (delai aleatoire 0.5-2s)
            await asyncio.sleep(random.uniform(0.5, 2.0))

            logger.info(f"[GUMROAD] Fetching full description from: {product_url} (attempt {attempt + 1}/{max_retries})")
            resp = await client.get(product_url, timeout=20.0)  # Augmente timeout a 20s

            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'lxml')
                break  # Succes, sortir de la boucle retry
            elif resp.status_code == 429:
                # Rate limited - exponential backoff
                wait_time = 2 ** attempt
                logger.warning(f"[GUMROAD] Rate limited (429), waiting {wait_time}s before retry")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"[GUMROAD] HTTP {resp.status_code} for product page: {product_url}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                else:
                    return ""

        except asyncio.TimeoutError:
            logger.warning(f"[GUMROAD] Timeout fetching {product_url}, retry {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                return ""
        except Exception as e:
            logger.error(f"[GUMROAD] Error fetching {product_url}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                return ""

    if not soup:
        logger.error(f"[GUMROAD] Failed to fetch page after {max_retries} attempts: {product_url}")
        return ""

    # Chercher __NEXT_DATA__ dans page produit
    try:
        script_tag = soup.find('script', id='__NEXT_DATA__', type='application/json')

        if script_tag:
            try:
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
                    logger.info(f"[GUMROAD] Found description in __NEXT_DATA__ ({len(description_html)} chars) for {product_url}")
                    return description_html
                else:
                    logger.warning(f"[GUMROAD] __NEXT_DATA__ found but no description_html/description fields for {product_url}")
            except json.JSONDecodeError as e:
                logger.error(f"[GUMROAD] Failed to parse __NEXT_DATA__ for {product_url}: {e}")
        else:
            logger.warning(f"[GUMROAD] No __NEXT_DATA__ found, trying regex extraction from HTML...")

            # NOUVEAU: Chercher description dans React component JSON (pour pages ?layout=profile)
            try:
                # Chercher le script React component ProfileProductPage
                react_script = soup.find('script', {'data-component-name': 'ProfileProductPage', 'type': 'application/json'})

                if react_script:
                    logger.info(f"[GUMROAD] Found React component script tag for {product_url}")
                    if react_script.string:
                        logger.info(f"[GUMROAD] React script has content ({len(react_script.string)} chars)")
                        try:
                            react_data = json.loads(react_script.string)
                            logger.info(f"[GUMROAD] Successfully parsed React JSON")

                            product_data = react_data.get('product', {})
                            logger.info(f"[GUMROAD] product_data keys: {list(product_data.keys())}")

                            desc_html = product_data.get('description_html', '')
                            if desc_html:
                                # json.loads() a deja decode les Unicode escapes (\u003c → <)
                                # desc_html contient deja du HTML valide avec balises
                                logger.info(f"[GUMROAD] SUCCESS - Found description_html in React component ({len(desc_html)} chars) for {product_url}")
                                logger.info(f"[GUMROAD] Description preview: {desc_html[:200]}...")
                                return desc_html
                            else:
                                logger.warning(f"[GUMROAD] React component found but description_html is empty")
                        except json.JSONDecodeError as e:
                            logger.warning(f"[GUMROAD] Failed to parse React component JSON: {e}")
                    else:
                        logger.warning(f"[GUMROAD] React script tag found but has no content")
                else:
                    logger.warning(f"[GUMROAD] No React component script tag found for {product_url}")

                # Fallback: Regex search si React component pas trouvé
                html_content = str(soup)
                desc_match = re.search(r'"description_html"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', html_content)
                if desc_match:
                    desc_json = desc_match.group(1)
                    # Decoder echappements
                    desc_html = desc_json.replace('\\u003c', '<').replace('\\u003e', '>').replace('\\u003cb\u003e', '<b>').replace('\\u003c/b\u003e', '</b>').replace('\\n', '\n').replace('\\"', '"').replace('\\/', '/')
                    logger.info(f"[GUMROAD] Found description_html via regex fallback ({len(desc_html)} chars) for {product_url}")
                    return desc_html

            except Exception as regex_error:
                logger.warning(f"[GUMROAD] React component extraction failed: {regex_error}")

        # Fallback 1: Chercher dans HTML avec regex ameliore
        desc_elem = None

        # Essai 1: Div avec classes description/content
        desc_elem = soup.find('div', class_=re.compile(r'description|content', re.I))

        # Essai 2: Section/Article avec classes variees
        if not desc_elem:
            desc_elem = soup.find(['section', 'article', 'div'],
                class_=re.compile(r'desc|product.*info|details|text|summary|about', re.I))

        # Essai 3: Main content area
        if not desc_elem:
            main = soup.find('main')
            if main:
                # Chercher premier paragraphe substantiel
                paragraphs = main.find_all('p')
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if len(text) > 50:  # Au moins 50 chars
                        desc_elem = p
                        break

        if desc_elem:
            fallback_desc = desc_elem.get_text(separator='\n', strip=True)
            if fallback_desc:
                logger.info(f"[GUMROAD] Using HTML fallback description ({len(fallback_desc)} chars) for {product_url}")
                return fallback_desc

        # Fallback 2: OpenGraph meta tags
        og_desc = soup.find('meta', property='og:description')
        if og_desc:
            og_content = og_desc.get('content', '')
            if og_content:
                logger.info(f"[GUMROAD] Using OpenGraph description ({len(og_content)} chars) for {product_url}")
                return og_content

        # Fallback 3: Twitter Card
        twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
        if twitter_desc:
            twitter_content = twitter_desc.get('content', '')
            if twitter_content:
                logger.info(f"[GUMROAD] Using Twitter Card description ({len(twitter_content)} chars) for {product_url}")
                return twitter_content

        # Fallback 4: Meta description standard
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            meta_content = meta_desc.get('content', '')
            if meta_content:
                logger.info(f"[GUMROAD] Using meta description ({len(meta_content)} chars) for {product_url}")
                return meta_content

        logger.error(f"[GUMROAD] No description found via any method (JSON, HTML, OG, Twitter, Meta) for {product_url}")
        return ""

    except Exception as e:
        logger.error(f"[GUMROAD] Unexpected error fetching product description: {e}")
        import traceback
        logger.error(f"[GUMROAD] Traceback: {traceback.format_exc()}")
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

                                # Ne pas retourner immédiatement - continuer pour potentiellement trouver plus
                                # Le return se fera à la fin de la fonction
                                # if products:
                                #     return products  # SUPPRIMÉ - bloquait l'enrichissement

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
        Texte nettoye compatible Telegram (texte pur sans HTML)
    """
    if not html_text:
        return ""

    # Parser HTML avec BeautifulSoup
    soup = BeautifulSoup(html_text, 'lxml')

    # Extraire UNIQUEMENT le texte (sans balises HTML)
    # get_text() convertit tout en texte pur
    cleaned_text = soup.get_text(separator=' ', strip=True)

    # Nettoyer espaces multiples
    cleaned_text = ' '.join(cleaned_text.split())

    # Limiter longueur (Telegram max 4096 chars)
    if len(cleaned_text) > 4000:
        cleaned_text = cleaned_text[:4000] + "..."

    return cleaned_text


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


async def download_cover_image(image_url: str, product_id: str, seller_id: int = None, referer_url: str = None) -> str:
    """
    Telecharger image cover vers B2/R2 ET creer cache local

    IMPORTANT: Cette fonction doit reproduire EXACTEMENT le flux d'upload classique:
    1. Download image depuis Gumroad
    2. Upload vers R2/B2
    3. Creer cache local (buffer/python-bot/uploads/temp/images/{product_id}/thumb.jpg)

    Args:
        image_url: URL image Gumroad
        product_id: ID produit genere
        seller_id: ID vendeur (optionnel, pour cache local)
        referer_url: URL de la page produit Gumroad (pour contourner protections Referer)

    Returns:
        URL B2/R2 de l'image uploadee

    Raises:
        Exception: Si download ou upload echoue
    """
    from app.services.b2_storage_service import B2StorageService

    # Headers anti-detection avec Referer Gumroad (CRITIQUE pour contourner protections)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Referer': referer_url if referer_url else 'https://gumroad.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'image',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'same-site',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
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

                # Structure R2: products/{seller_id}/{product_id}/cover.jpg (et thumb.jpg)
                # Si seller_id non fourni, utiliser structure temporaire
                if seller_id:
                    cover_key = f"products/{seller_id}/{product_id}/cover.jpg"
                    thumb_key = f"products/{seller_id}/{product_id}/thumb.jpg"
                else:
                    # Fallback: structure import temporaire (sera migre plus tard)
                    cover_key = f"products/imported/gumroad/{product_id}/cover.{ext}"
                    thumb_key = f"products/imported/gumroad/{product_id}/thumb.{ext}"

                # Upload cover
                cover_url = await b2.upload_file(temp_path, cover_key)
                logger.info(f"[GUMROAD] Cover image uploaded to R2: {cover_url}")

                # Upload thumbnail (meme fichier pour import Gumroad)
                thumb_url = await b2.upload_file(temp_path, thumb_key)
                logger.info(f"[GUMROAD] Thumbnail uploaded to R2: {thumb_url}")

                # NOUVEAU: Creer cache local (comme upload classique)
                # Structure: buffer/python-bot/uploads/temp/images/{product_id}/thumb.jpg
                try:
                    cache_dir = os.path.join('buffer', 'python-bot', 'uploads', 'temp', 'images', product_id)
                    os.makedirs(cache_dir, exist_ok=True)

                    # Copier vers cache local (toujours thumb.jpg pour coherence)
                    cache_path = os.path.join(cache_dir, 'thumb.jpg')

                    # Si extension n'est pas jpg, convertir ou copier direct
                    import shutil
                    shutil.copy2(temp_path, cache_path)

                    logger.info(f"[GUMROAD] Cover image cached locally: {cache_path}")

                except Exception as cache_error:
                    # Cache non critique - juste log warning
                    logger.warning(f"[GUMROAD] Failed to create local cache (non-critical): {cache_error}")

                return cover_url

            finally:
                # Cleanup temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        except Exception as e:
            logger.error(f"[GUMROAD] Cover image download error: {e}")
            raise
