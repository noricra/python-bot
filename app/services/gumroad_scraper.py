import httpx
import json
import re
import asyncio
import tempfile
import os
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


async def scrape_gumroad_profile(profile_url: str) -> List[Dict]:
    """
    Scrape profil Gumroad public en extrayant le JSON embarque
    PUIS visite chaque page produit pour recuperer descriptions completes

    Args:
        profile_url: https://username.gumroad.com

    Returns:
        Liste produits avec metadonnees + descriptions completes

    Raises:
        Exception: Si fetch echoue ou parsing impossible
    """
    products = []

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
        }

        try:
            logger.info(f"Fetching Gumroad profile: {profile_url}")
            resp = await client.get(profile_url, headers=headers)

            if resp.status_code != 200:
                logger.error(f"HTTP {resp.status_code} for {profile_url}")
                raise Exception(f"Failed to fetch profile: HTTP {resp.status_code}")

            html_content = resp.text

            # Methode 1: Extraire JSON embarque dans les scripts
            products_json = extract_json_from_html(html_content)

            if products_json:
                logger.info(f"Found {len(products_json)} products via JSON extraction")
                products.extend(products_json)
            else:
                # Fallback: Parser HTML si JSON non trouve
                logger.warning("JSON extraction failed, falling back to HTML parsing")
                products_html = parse_html_fallback(html_content, profile_url)
                products.extend(products_html)

            # NOUVEAU: Enrichir chaque produit avec description complete depuis page individuelle
            logger.info(f"Enriching {len(products)} products with full descriptions...")
            enriched_products = []

            for idx, product in enumerate(products):
                product_url = product.get('gumroad_url')

                if product_url:
                    try:
                        logger.info(f"[{idx+1}/{len(products)}] Fetching description for: {product['title']}")
                        full_description = await fetch_product_description(client, product_url, headers)

                        if full_description:
                            product['description'] = full_description
                            logger.info(f"Description enriched ({len(full_description)} chars)")
                        else:
                            logger.warning(f"No description found for {product['title']}")

                        # Petit délai pour éviter rate limiting
                        await asyncio.sleep(1)

                    except Exception as e:
                        logger.warning(f"Failed to fetch description for {product['title']}: {e}")
                        # Continue avec description vide

                enriched_products.append(product)

            return enriched_products

        except httpx.TimeoutException:
            logger.error(f"Timeout fetching {profile_url}")
            raise Exception("Request timeout - Gumroad may be slow")
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            raise


async def fetch_product_description(client: httpx.AsyncClient, product_url: str, headers: dict) -> str:
    """
    Visite page produit individuelle pour extraire description complete

    Args:
        client: httpx client
        product_url: URL du produit (ex: https://username.gumroad.com/l/product-slug)
        headers: HTTP headers

    Returns:
        Description complete en texte brut (Markdown preserve)
    """
    try:
        resp = await client.get(product_url, headers=headers)

        if resp.status_code != 200:
            logger.warning(f"HTTP {resp.status_code} for product page: {product_url}")
            return ""

        html = resp.text
        soup = BeautifulSoup(html, 'lxml')

        # Methode 1: Chercher dans JSON embarque (comme page profil)
        scripts = soup.find_all('script')
        for script in scripts:
            if not script.string:
                continue

            script_content = script.string

            # Chercher description dans JSON
            if 'description' in script_content:
                # Pattern: "description":"Le texte ici..."
                desc_match = re.search(r'"description"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', script_content)

                if desc_match:
                    # Decoder escapes JSON (\n, \", etc.)
                    raw_desc = desc_match.group(1)
                    description = raw_desc.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
                    return description.strip()

        # Methode 2: Chercher dans HTML (fallback)
        # Gumroad affiche description dans divers containers
        selectors = [
            'div.product-description',
            'div[class*="description"]',
            'div[id*="description"]',
            'div.content',
            'div.product-content',
            'article',
        ]

        for selector in selectors:
            desc_elem = soup.select_one(selector)

            if desc_elem:
                # Extraire texte en preservant structure
                description = desc_elem.get_text(separator='\n', strip=True)

                if description and len(description) > 50:  # Minimum 50 chars pour etre valide
                    return description

        # Methode 3: Meta description tag (dernier recours)
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            content = meta_desc.get('content', '')
            if content:
                return content

        logger.warning(f"No description found for {product_url}")
        return ""

    except Exception as e:
        logger.error(f"Error fetching product description: {e}")
        return ""


def extract_json_from_html(html_content: str) -> List[Dict]:
    """
    Extraire donnees produit depuis JSON embarque dans la page Gumroad

    Gumroad utilise du JSON dans <script> tags pour hydrate React/Vue

    Args:
        html_content: HTML brut de la page

    Returns:
        Liste produits parsees depuis JSON
    """
    products = []

    try:
        soup = BeautifulSoup(html_content, 'lxml')

        # Chercher tous les script tags
        scripts = soup.find_all('script')

        for script in scripts:
            if not script.string:
                continue

            script_content = script.string

            # Chercher patterns JSON contenant des produits
            # Pattern 1: window.__INITIAL_STATE__ ou similar
            if 'products' in script_content or 'items' in script_content:
                # Tenter d'extraire JSON
                json_match = re.search(r'(\{.*"products".*\}|\{.*"items".*\})', script_content, re.DOTALL)

                if json_match:
                    try:
                        data = json.loads(json_match.group(1))

                        # Extraire produits selon structure
                        if 'products' in data:
                            products_raw = data['products']
                        elif 'items' in data:
                            products_raw = data['items']
                        else:
                            continue

                        # Parser chaque produit
                        if isinstance(products_raw, list):
                            for p in products_raw:
                                product = parse_gumroad_product_json(p)
                                if product:
                                    products.append(product)

                    except json.JSONDecodeError:
                        continue

        return products

    except Exception as e:
        logger.warning(f"JSON extraction error: {e}")
        return []


def parse_gumroad_product_json(product_data: dict) -> Optional[Dict]:
    """
    Parser un objet produit JSON de Gumroad

    Args:
        product_data: Dict JSON du produit

    Returns:
        Dict normalise ou None si invalide
    """
    try:
        # Extraire champs communs
        title = product_data.get('name') or product_data.get('title') or 'Sans titre'

        # Prix (peut etre en cents)
        price_cents = product_data.get('price_cents', 0)
        price_usd = product_data.get('price')

        if price_cents:
            price = float(price_cents) / 100.0
        elif price_usd:
            price = float(price_usd)
        else:
            price = 0.0

        # Description
        description = product_data.get('description') or product_data.get('summary') or ''

        # Image
        image_url = (
            product_data.get('thumbnail_url') or
            product_data.get('cover_image_url') or
            product_data.get('preview_url')
        )

        # URL produit
        product_url = product_data.get('url') or product_data.get('permalink')

        if product_url and not product_url.startswith('http'):
            product_url = f"https://gumroad.com{product_url}"

        return {
            'title': title,
            'price': price,
            'description': description,
            'image_url': image_url,
            'gumroad_url': product_url
        }

    except Exception as e:
        logger.warning(f"Failed to parse product JSON: {e}")
        return None


def parse_html_fallback(html_content: str, profile_url: str) -> List[Dict]:
    """
    Fallback: Parser HTML si JSON extraction echoue

    Args:
        html_content: HTML brut
        profile_url: URL du profil

    Returns:
        Liste produits parsees depuis HTML
    """
    products = []

    try:
        soup = BeautifulSoup(html_content, 'lxml')

        # Tenter plusieurs selecteurs possibles
        selectors = [
            {'card': 'div.product-card'},
            {'card': 'div[class*="product"]'},
            {'card': 'article'},
            {'card': 'a[href*="/l/"]'},  # Gumroad product links format
        ]

        for selector_set in selectors:
            cards = soup.select(selector_set['card'])

            if cards:
                logger.info(f"Found {len(cards)} product cards with selector: {selector_set['card']}")

                for card in cards:
                    product = parse_product_card(card)
                    if product and product.get('title'):
                        products.append(product)

                if products:
                    break

        return products

    except Exception as e:
        logger.error(f"HTML fallback parsing error: {e}")
        return []


def parse_product_card(card) -> Dict:
    """
    Parser une carte produit HTML

    Args:
        card: BeautifulSoup element

    Returns:
        Dict avec metadonnees produit
    """
    # Extraire titre
    title_elem = card.find(['h1', 'h2', 'h3', 'h4']) or card.find(attrs={'class': re.compile(r'title|name', re.I)})
    title = title_elem.get_text(strip=True) if title_elem else 'Sans titre'

    # Extraire prix
    price_elem = card.find(attrs={'class': re.compile(r'price|cost', re.I)}) or card.find(string=re.compile(r'\$\d+'))
    price_text = price_elem if isinstance(price_elem, str) else (price_elem.get_text(strip=True) if price_elem else '$0')
    price = parse_price(price_text)

    # Extraire image
    img_elem = card.find('img')
    image_url = None
    if img_elem:
        image_url = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy-src')

    # Extraire description
    desc_elem = card.find(['p', 'div'], attrs={'class': re.compile(r'desc|summary', re.I)})
    description = desc_elem.get_text(strip=True) if desc_elem else ''

    # Extraire URL produit
    link_elem = card.find('a') if card.name != 'a' else card
    product_url = link_elem.get('href') if link_elem else None

    if product_url and not product_url.startswith('http'):
        product_url = f"https://gumroad.com{product_url}"

    return {
        'title': title,
        'price': price,
        'description': description,
        'image_url': image_url,
        'gumroad_url': product_url
    }


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
        logger.warning(f"Failed to parse price: {price_str}")
        return 0.0


async def download_cover_image(image_url: str, product_id: str) -> str:
    """
    Telecharger image cover vers R2

    Args:
        image_url: URL image Gumroad
        product_id: ID produit genere

    Returns:
        URL R2 de l'image uploadee

    Raises:
        Exception: Si download ou upload echoue
    """
    from app.services.b2_storage_service import B2StorageService

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            logger.info(f"Downloading cover image: {image_url}")
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
                # Upload vers R2
                b2 = B2StorageService()
                object_key = f"products/imported/gumroad/{product_id}/cover.{ext}"

                url = await b2.upload_file(temp_path, object_key)

                logger.info(f"Cover image uploaded: {url}")
                return url

            finally:
                # Cleanup
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        except Exception as e:
            logger.error(f"Cover image download error: {e}")
            raise
