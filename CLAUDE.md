# Architecture Lead Python - Refactorisation Bot Telegram

## 🎯 Mission

Tu agis en tant qu'**Architecte Lead Python**. Je te confie la refactorisation d'un bot Telegram complexe (~15k lignes, architecture DDD).

---

## 🏛️ Architecture Cible (Strict)

### Core (Infrastructure)
**Emplacement :** `app/core/`

**Responsabilité :** Gestion pure des connexions DB (Pool), Logs, Configuration.

**Règles :**
- Pas de logique métier
- Uniquement l'infrastructure technique

---

### Domain (Repositories)
**Emplacement :** `app/domain/repositories/`

**Responsabilité :** Contient **TOUT le SQL**. Interdiction de voir du SQL ailleurs.

**Règles :**
- Utilisation exclusive de `db_pool.get_connection()`
- Toujours utiliser `try...finally...put_connection()`
- Un repository par entité (Product, User, Order, etc.)

---

### Services (Business Logic)
**Emplacement :** `app/services/`

**Responsabilité :** Logique métier (calculs, appels API externes).

**Règles :**
- 100% Async
- Pas de SQL direct (appeler les repositories)
- Pas de librairies bloquantes (`requests`, `time.sleep`)

---

### Integration (Handlers)
**Emplacement :** `app/integrations/telegram/handlers/`

**Responsabilité :** Gestion uniquement de l'interaction Telegram (Boutons, Messages).

**Règles :**
- Appellent les Services, jamais la DB directement
- Navigation Telegram pure
- Pas de logique métier complexe

---

## ⚙️ Règles Techniques Globales

### 1. 100% Async
- ❌ Pas de `requests` → ✅ Utiliser `httpx`
- ❌ Pas de `time.sleep` → ✅ Utiliser `asyncio.sleep`
- ❌ Pas d'appels DB bloquants dans la main loop

### 2. DB Safety
**Pattern obligatoire :**
```python
conn = db_pool.get_connection()
try:
    cursor = conn.cursor()
    # ... SQL operations
    conn.commit()
finally:
    db_pool.put_connection(conn)
```

### 3. Pas de SQL hors Repositories
- Tout `cursor.execute()` doit être dans `app/domain/repositories/`
- Les handlers et services utilisent uniquement les méthodes des repositories

---

## 🚀 Plan de Refactorisation par Phase

### 📋 Phase 0 : Initialisation

**Prompt :**
```
Analyse l'arborescence du projet et prépare-toi à recevoir les tâches par module.
Crée ou mets à jour le fichier CLAUDE.md avec ce plan d'architecture.
```

---

### 🖼️ TÂCHE #1 : Migration Images vers B2 + Telegram file_id (PRIORITÉ CRITIQUE)

**Contexte :** Railway redémarre régulièrement et supprime les fichiers locaux (système éphémère). Les images produits sont actuellement stockées uniquement en local, causant des 404 après restart.

**Problème actuel :**
- ❌ `thumbnail_url` et `cover_image_url` contiennent des **chemins locaux** : `/Users/.../thumb.jpg`
- ❌ Images perdues à chaque restart Railway
- ❌ Fallback vers B2 échoue (404) car images jamais uploadées

**Architecture cible :**

```
┌─────────────────────────────────────────────────────────────┐
│ STOCKAGE MULTI-LAYER (Railway-proof)                        │
├─────────────────────────────────────────────────────────────┤
│ 1. SOURCE DE VÉRITÉ (B2)                                    │
│    - thumbnail_url: https://s3.../products/TBF-XXX/thumb.jpg│
│    - cover_url: https://s3.../products/TBF-XXX/cover.jpg    │
│    → Survit aux restarts                                    │
│                                                              │
│ 2. CACHE TELEGRAM (Gratuit, Instantané)                     │
│    - telegram_thumb_file_id: "AgACAgIAAxkBAAIB..."         │
│    - telegram_cover_file_id: "AgACAgIAAxkBAAIB..."         │
│    → 99% des affichages (instantané, $0)                    │
│                                                              │
│ 3. CACHE LOCAL (Optionnel, Éphémère)                       │
│    - data/product_images/{seller_id}/{product_id}/thumb.jpg│
│    → Rebuild on-demand après restart                        │
└─────────────────────────────────────────────────────────────┘
```

**Flux d'affichage optimisé :**

```python
def get_product_thumbnail(product_id):
    # 1. Priorité: file_id Telegram (⚡ instantané, gratuit)
    if product.telegram_thumb_file_id:
        return product.telegram_thumb_file_id

    # 2. Fallback: Cache local (rapide)
    local_path = f"data/product_images/{product_id}/thumb.jpg"
    if os.path.exists(local_path):
        file_id = upload_to_telegram(local_path)
        save_telegram_file_id(product_id, file_id)
        return file_id

    # 3. Dernier recours: Download depuis B2 (première fois seulement)
    download_from_b2(product.thumbnail_url, local_path)
    file_id = upload_to_telegram(local_path)
    save_telegram_file_id(product_id, file_id)
    return file_id
```

---

#### Étape 1.1 : Migration Base de Données

**Fichier à créer :** `migrations/add_telegram_file_ids.sql`

```sql
-- Ajouter colonnes pour Telegram file_id
ALTER TABLE products
ADD COLUMN telegram_thumb_file_id TEXT,
ADD COLUMN telegram_cover_file_id TEXT;

-- Index pour optimiser les lookups
CREATE INDEX idx_products_telegram_thumb ON products(telegram_thumb_file_id) WHERE telegram_thumb_file_id IS NOT NULL;
CREATE INDEX idx_products_telegram_cover ON products(telegram_cover_file_id) WHERE telegram_cover_file_id IS NOT NULL;
```

**Commande d'exécution :**
```bash
PGPASSWORD="" psql -h localhost -U noricra -d marketplace_bot -f migrations/add_telegram_file_ids.sql
```

---

#### Étape 1.2 : Upload Images Locales vers B2

**Fichier :** `migrate_images_to_b2.py` (déjà créé)

**Fonction :** Upload toutes les images locales existantes vers B2 et met à jour la DB avec les URLs B2.

**Exécution :**
```bash
python3 migrate_images_to_b2.py
```

**Résultat attendu :**
- ✅ Images uploadées sur B2: `products/{product_id}/thumb.jpg`, `products/{product_id}/cover.jpg`
- ✅ DB mise à jour: `thumbnail_url` et `cover_image_url` contiennent maintenant des URLs B2

---

#### Étape 1.3 : Modifier Code de Création de Produit

**Fichier à modifier :** `app/integrations/telegram/handlers/sell_handlers.py`

**Changements requis :**

1. Lors de la réception de la cover image du vendeur :
   ```python
   # AVANT
   local_path = save_image_locally(photo_file)
   product.cover_image_url = local_path  # ❌ Chemin local

   # APRÈS
   local_path = save_image_locally(photo_file)
   b2_url = b2_service.upload_file(local_path, f"products/{product_id}/cover.jpg")
   product.cover_image_url = b2_url  # ✅ URL B2
   ```

2. Lors de la génération du thumbnail :
   ```python
   # AVANT
   thumb_path = generate_thumbnail(cover_path)
   product.thumbnail_url = thumb_path  # ❌ Chemin local

   # APRÈS
   thumb_path = generate_thumbnail(cover_path)
   thumb_b2_url = b2_service.upload_file(thumb_path, f"products/{product_id}/thumb.jpg")
   product.thumbnail_url = thumb_b2_url  # ✅ URL B2
   ```

**Fichiers concernés :**
- `app/integrations/telegram/handlers/sell_handlers.py` (création produit)
- `app/core/image_utils.py` (génération thumbnail)

---

#### Étape 1.4 : Implémenter Logique file_id Telegram

**Fichier à créer :** `app/services/telegram_cache_service.py`

```python
"""
Service de cache Telegram pour réutilisation des file_id
Évite les re-uploads et accélère l'affichage
"""
import logging
from typing import Optional
from telegram import InputMediaPhoto
from app.core.database_init import get_postgresql_connection
from app.core.db_pool import put_connection
import psycopg2.extras

logger = logging.getLogger(__name__)

class TelegramCacheService:
    """Gestion du cache Telegram (file_id) pour images produits"""

    def get_product_image_file_id(self, product_id: str, image_type: str = 'thumb') -> Optional[str]:
        """
        Récupère le file_id Telegram pour une image produit

        Args:
            product_id: ID du produit
            image_type: 'thumb' ou 'cover'

        Returns:
            file_id Telegram ou None si pas en cache
        """
        conn = get_postgresql_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            field = 'telegram_thumb_file_id' if image_type == 'thumb' else 'telegram_cover_file_id'
            cursor.execute(f"SELECT {field} FROM products WHERE product_id = %s", (product_id,))

            result = cursor.fetchone()
            return result[field] if result else None
        finally:
            put_connection(conn)

    def save_telegram_file_id(self, product_id: str, file_id: str, image_type: str = 'thumb'):
        """
        Sauvegarde le file_id Telegram pour réutilisation future

        Args:
            product_id: ID du produit
            file_id: file_id retourné par Telegram
            image_type: 'thumb' ou 'cover'
        """
        conn = get_postgresql_connection()
        try:
            cursor = conn.cursor()

            field = 'telegram_thumb_file_id' if image_type == 'thumb' else 'telegram_cover_file_id'
            cursor.execute(
                f"UPDATE products SET {field} = %s WHERE product_id = %s",
                (file_id, product_id)
            )
            conn.commit()
            logger.info(f"✅ Telegram file_id cached: {product_id}/{image_type}")
        finally:
            put_connection(conn)
```

---

#### Étape 1.5 : Modifier Logique d'Affichage

**Fichier à modifier :** `app/core/utils.py` (ou créer `app/services/image_display_service.py`)

**Fonction à remplacer :** `get_product_image_or_placeholder()`

```python
async def get_product_thumbnail_for_telegram(product_id: str) -> str:
    """
    Récupère le thumbnail optimisé pour affichage Telegram

    Ordre de priorité:
    1. Telegram file_id (instantané, gratuit)
    2. Cache local → Upload Telegram → Save file_id
    3. Download B2 → Cache local → Upload Telegram → Save file_id

    Returns:
        file_id Telegram ou chemin local vers placeholder
    """
    from app.services.telegram_cache_service import TelegramCacheService
    from app.services.image_sync_service import ImageSyncService
    from app.domain.repositories.product_repo import ProductRepository

    telegram_cache = TelegramCacheService()
    image_sync = ImageSyncService()
    product_repo = ProductRepository()

    # 1. Essayer file_id Telegram (99% des cas)
    file_id = telegram_cache.get_product_image_file_id(product_id, 'thumb')
    if file_id:
        logger.info(f"⚡ Using cached Telegram file_id: {product_id}")
        return file_id

    # 2. Récupérer le produit pour obtenir l'URL B2
    product = product_repo.get_product_by_id(product_id)
    if not product:
        return get_placeholder_image()

    seller_id = product['seller_user_id']

    # 3. Chercher en cache local
    local_path = f"data/product_images/{seller_id}/{product_id}/thumb.jpg"

    if not os.path.exists(local_path):
        # 4. Télécharger depuis B2 si manquant
        thumbnail_url = product.get('thumbnail_url')
        if thumbnail_url and thumbnail_url.startswith('https://'):
            logger.info(f"📥 Downloading thumbnail from B2: {product_id}")
            from app.core.file_utils import download_product_file_from_b2
            local_path = await download_product_file_from_b2(thumbnail_url, product_id)

        if not local_path or not os.path.exists(local_path):
            logger.warning(f"⚠️ Thumbnail unavailable: {product_id}")
            return get_placeholder_image()

    # 5. Uploader vers Telegram et sauvegarder le file_id
    # Note: Cette partie sera gérée par le handler qui envoie le message
    # car on a besoin du bot instance pour uploader
    logger.info(f"📤 Returning local path for Telegram upload: {product_id}")
    return local_path
```

---

#### Étape 1.6 : Tests de Validation

**Commandes de vérification :**

```bash
# 1. Vérifier que les colonnes ont été ajoutées
PGPASSWORD="" psql -h localhost -U noricra -d marketplace_bot -c "\d products" | grep telegram

# 2. Vérifier qu'il n'y a plus de chemins locaux en DB (après migration)
PGPASSWORD="" psql -h localhost -U noricra -d marketplace_bot -c "SELECT COUNT(*) FROM products WHERE thumbnail_url LIKE '/Users/%';"
# Résultat attendu: 0

# 3. Vérifier que les URLs B2 sont présentes
PGPASSWORD="" psql -h localhost -U noricra -d marketplace_bot -c "SELECT COUNT(*) FROM products WHERE thumbnail_url LIKE 'https://s3%';"
# Résultat attendu: > 0
```

**Tests fonctionnels :**
1. Créer un nouveau produit → Vérifier que les images sont uploadées sur B2
2. Afficher un produit → Vérifier que le file_id Telegram est sauvegardé après premier affichage
3. Redémarrer Railway → Vérifier que les images s'affichent toujours (via file_id ou re-download B2)

---

**Critères de succès Tâche #1 :**
- ✅ DB migrée: colonnes `telegram_thumb_file_id`, `telegram_cover_file_id` ajoutées
- ✅ Images existantes uploadées sur B2
- ✅ DB mise à jour: `thumbnail_url` et `cover_image_url` contiennent des URLs B2
- ✅ Code de création produit upload directement sur B2
- ✅ Cache Telegram implémenté et fonctionnel
- ✅ Affichage instantané via file_id (99% des cas)
- ✅ Résilient aux restarts Railway (source de vérité sur B2)
- ✅ Coûts B2 minimisés (download une seule fois par produit)

---

### 🏗️ PHASE 1 : Assainir les Fondations (Core & DB)

**Focus :** `app/core/` et `app/domain/repositories/`

**Problème Critique :** Les repositories créent actuellement de nouvelles connexions (`get_postgresql_connection`) au lieu d'utiliser le pool (`db_pool`).

**Tâches :**

1. Vérifie `app/core/db_pool.py`
   - Assure-toi que `get_connection()` et `put_connection()` sont robustes

2. Passe en revue **TOUS** les fichiers dans `app/domain/repositories/` :
   - `product_repo.py`
   - `user_repo.py`
   - `order_repo.py`
   - `seller_repo.py`
   - etc.

3. Remplace systématiquement la création de connexion par l'appel au Pool avec un bloc `try/finally` pour garantir le retour de la connexion

4. Supprime l'import de `get_postgresql_connection` dans ces fichiers pour éviter toute régression

**Critères de succès :**
- ✅ Aucun `get_postgresql_connection()` dans les repositories
- ✅ Tous les repositories utilisent `db_pool.get_connection()`
- ✅ Tous les appels DB ont un `finally: put_connection(conn)`

---

### ⚡ PHASE 2 : Débloquer l'Event Loop (Services Async)

**Focus :** `app/services/` et `app/integrations/nowpayments_client.py`

**Problème Critique :** Utilisation de librairies synchrones (`requests`) qui bloquent le bot Telegram.

**Tâches :**

1. **nowpayments_client.py :**
   - Réécris pour utiliser `httpx` et être totalement async
   - Remplace tous les `requests.get/post` par `httpx.AsyncClient`

2. **payment_service.py :**
   - Mets à jour pour `await` les appels au client NowPayments
   - Vérifie que toutes les méthodes sont `async def`

3. **email_service.py :**
   - Si utilise `smtplib` (bloquant), encapsule l'envoi dans `asyncio.to_thread` ou utilise `aiosmtplib`

4. **b2_storage_service.py :**
   - Assure-toi que les uploads de fichiers (lourds) ne bloquent pas la boucle principale
   - Utilise `asyncio.to_thread` si nécessaire

**Critères de succès :**
- ✅ Aucun `import requests` dans le projet
- ✅ Tous les services ont des méthodes `async def`
- ✅ Aucun appel bloquant dans la main loop

---

### 🧹 PHASE 3 : Nettoyage des "God Handlers" (Le plus critique)

C'est la plus grosse partie. On divise pour régner.

Le fichier `buy_handlers.py` est énorme (2187 lignes) et contient tout : du SQL, du HTML, de la logique métier... C'est une bombe à retardement.

#### PHASE 3-A : Buy Flow - Refactoring Massif

**Focus :** `app/integrations/telegram/handlers/buy_handlers.py`

**Problème :** Ce fichier viole le principe de responsabilité unique. Il fait office de Vue (Telegram), de Contrôleur (Logique) et de Modèle (SQL).

**Objectif :** Le fichier final `buy_handlers.py` doit faire **moins de 500 lignes** et ne contenir QUE la logique d'interface Telegram.

**Instructions précises :**

1. **Extraction SQL (Modèle) :**
   - Analyse `buy_handlers.py` et repère toutes les lignes avec `cursor.execute`
   - Déplace ces requêtes dans `app/domain/repositories/product_repo.py` ou `order_repo.py`
   - *Exemple :* La requête `SELECT * FROM products WHERE category = %s` doit devenir une méthode `product_repo.get_products_by_category(...)`

2. **Extraction Logique Métier (Service) :**
   - Déplace la logique de calcul de prix (`total = price + fees`) dans `app/services/payment_service.py`
   - Déplace la logique de formatage de texte (les méthodes `_build_product_caption`, `_build_crypto_selection_text`) dans un nouveau fichier `app/services/product_display_service.py` ou `app/core/formatters.py`

3. **Nettoyage du Handler (Contrôleur) :**
   - Réécris `buy_handlers.py` pour qu'il instancie les services et appelle leurs méthodes
   - Remplace les blocs `try/except psycopg2.Error` par des appels propres aux repositories qui gèrent déjà le pool DB

4. **Vérification :**
   - Lance une analyse statique pour vérifier qu'il ne reste aucun `import psycopg2` dans `buy_handlers.py`

**Commande de vérification à exécuter :**
```bash
grep "psycopg2" app/integrations/telegram/handlers/buy_handlers.py
```
*(Le résultat doit être vide)*

**Critères de succès :**
- ✅ Aucun SQL dans `buy_handlers.py`
- ✅ Fichier réduit à < 500 lignes
- ✅ Navigation Telegram pure
- ✅ Aucun `import psycopg2`

---

#### PHASE 3-B : Sell Flow & Admin

**Focus :** `sell_handlers.py` et `admin_handlers.py`

**Tâches :**

1. Applique la même logique de nettoyage que Phase 3-A

2. Extrais tout SQL vers les repositories correspondants :
   - `user_repository`
   - `product_repository`
   - `seller_repository`

3. Pour `admin_handlers.py` :
   - Assure-toi que les actions lourdes (ex: statistiques sur toute la DB) sont déléguées à un Service (`AdminService` ou `AnalyticsService`)
   - Ces actions ne doivent pas bloquer

**Commandes de vérification :**
```bash
grep "cursor.execute" app/integrations/telegram/handlers/sell_handlers.py
grep "cursor.execute" app/integrations/telegram/handlers/admin_handlers.py
```
*(Les résultats doivent être vides)*

**Critères de succès :**
- ✅ Aucun SQL dans les handlers
- ✅ Actions lourdes déléguées aux services
- ✅ Pas de blocage de l'event loop

---

### 🚀 PHASE 4 : Consolidation & Scalabilité (Infrastructure)

Une fois que le code métier est propre, il faut s'assurer que l'infrastructure tient la route (Rate Limiting, Config).

**Focus :** Global & `app/main.py`

#### Tâche 1 : Rate Limiter (Redis Ready)

**Problème :** Actuellement, `app/core/rate_limiter.py` stocke tout en mémoire RAM (`self._requests`). Ce n'est pas scalable.

**Instructions :**
1. Analyse `app/core/rate_limiter.py`
2. Refactorise-le pour utiliser une **interface abstraite** `RateLimitStore`
3. Implémente deux versions :
   - `MemoryRateLimitStore` (actuel, pour dev/test)
   - Prépare le squelette pour `RedisRateLimitStore` (pour le futur scaling)
4. Modifie `middleware.py` pour utiliser cette abstraction

**Pattern recommandé :**
```python
class RateLimitStore(ABC):
    @abstractmethod
    def increment(self, user_id: int) -> int:
        pass

    @abstractmethod
    def get_count(self, user_id: int) -> int:
        pass
```

---

#### Tâche 2 : Configuration Centralisée

**Instructions :**
1. Vérifie `app/core/settings.py`
2. Assure-toi que TOUTES les variables critiques (Clés API, DB URL) sont chargées via `os.getenv`
3. Aucune valeur par défaut "dangereuse" (ex: clés de prod en dur) ne doit être présente

**Commande de vérification :**
```bash
grep -E "(api_key|password|secret)" app/core/settings.py | grep -v "os.getenv"
```
*(Le résultat doit être vide ou montrer uniquement des fallbacks sécurisés)*

---

#### Tâche 3 : Point d'entrée (Main)

**Instructions :**
1. Vérifie `app/main.py`
2. Assure-toi que `init_connection_pool()` est appelé **AVANT** toute autre opération
3. Supprime le code de threading bizarre (`threading.Thread(target=run_ipn_server)`) et remplace-le par une approche purement `asyncio` si possible, ou documente pourquoi c'est nécessaire (ex: uvicorn blocking)

---

#### Tâche 4 : Analyse Statique

**Commandes de vérification finale :**
```bash
# Vérifier qu'il ne reste aucun import bloquant
grep -r "import requests" app/

# Vérifier qu'il ne reste aucune connexion DB directe hors de core
grep -r "psycopg2.connect" app/ | grep -v "app/core"
```

**Critères de succès :**
- ✅ Pool DB initialisé avant le bot
- ✅ Aucun import bloquant résiduel
- ✅ Rate limiting avec interface abstraite
- ✅ Configuration sécurisée
- ✅ Architecture prête pour la scalabilité

---

### 🛠️ PHASE 5 (Bonus) : Le Grand Ménage

**Objectif :** Supprimer tout le code mort et finaliser la migration PostgreSQL.

#### Tâche 1 : Suppression des fichiers morts

Supprime les fichiers identifiés comme inutiles :
- `app/core/analytics_engine.py` (553 lignes inutilisées)
- `app/core/chart_generator.py` (même registre)
- Tout fichier `.sqlite` ou `.db` qui traîne

**Commande :**
```bash
rm -f app/core/analytics_engine.py
rm -f app/core/chart_generator.py
find . -name "*.sqlite" -delete
find . -name "*.db" -delete
```

---

#### Tâche 2 : Vérification migration PostgreSQL

Vérifie qu'il n'y a plus aucune référence à SQLite dans le projet :

**Commande :**
```bash
grep -r "sqlite" . --exclude-dir=.git --exclude-dir=__pycache__
```
*(Le résultat doit être vide)*

---

#### Tâche 3 : Documentation Architecture

Crée un fichier `README_TECH.md` expliquant la nouvelle architecture pour les futurs développeurs :

**Contenu minimal :**
```markdown
# Architecture Technique

## Couches
- **Core** : Infrastructure (DB Pool, Logs)
- **Domain** : Repositories (SQL uniquement)
- **Services** : Logique métier (100% Async)
- **Integration** : Handlers Telegram (Navigation)

## Patterns
- 100% Async (httpx, pas requests)
- DB Pool systématique (try/finally)
- Pas de SQL hors repositories

## Démarrage
1. `pip install -r requirements.txt`
2. Configurer `.env` (voir `.env.example`)
3. `python app/main.py`
```

---

**Critères de succès Phase 5 :**
- ✅ Code mort supprimé
- ✅ Aucune trace de SQLite
- ✅ Documentation architecture créée

---

## 💡 Conseil d'exécution

**Donnez ces prompts un par un à Claude Code et attendez qu'il confirme (ou qu'il exécute les commandes de vérification) avant de passer au suivant.**

C'est la seule façon de réussir un refactoring de cette ampleur sans tout casser.

---

## 📝 Checklist Finale

Avant de considérer la refactorisation terminée :

### Architecture
- [ ] Tout le SQL est dans `app/domain/repositories/`
- [ ] Toute la logique métier est dans `app/services/`
- [ ] Les handlers ne font que de la navigation Telegram

### Performance
- [ ] 100% Async (aucun import bloquant)
- [ ] Pool de connexions DB utilisé partout
- [ ] Aucun blocage de l'event loop

### Sécurité
- [ ] Toutes les connexions DB ont un `finally: put_connection()`
- [ ] Aucune fuite de connexion possible
- [ ] Rate limiting actif

### Scalabilité
- [ ] Architecture prête pour Redis (rate limiting)
- [ ] Architecture prête pour worker pool (tâches lourdes)
- [ ] Logs structurés pour monitoring

---

## 🎓 Principes de Développement

1. **Separation of Concerns** : Chaque couche a une responsabilité unique
2. **DRY (Don't Repeat Yourself)** : Pas de duplication de code
3. **KISS (Keep It Simple, Stupid)** : Solutions simples avant tout
4. **Async First** : Tout doit être non-bloquant
5. **Fail Safe** : Toujours prévoir le `finally` pour les ressources

---

## 📞 Support

Si un pattern n'est pas clair ou si tu identifies un problème d'architecture non couvert par ce document, demande des clarifications avant de procéder.

**Prêt pour la Phase 1 ! 🚀**
