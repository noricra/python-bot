# BUYER WORKFLOW V2 - Spécifications Détaillées

**Date de création:** 2025-10-18
**Statut:** 📋 EN ATTENTE DE VALIDATION
**Objectif:** Réduire le workflow acheteur de 6+ clics à 2-3 clics maximum

---

## 1. WORKFLOW PRINCIPAL

### ÉTAPE 0 : Menu principal
**Commande:** `/start`

**Boutons affichés:**
```
[Acheter] [Vendre] 
    [Support]
```

**État actuel dans le code:** ✅ Existe (fichier: `app/integrations/telegram/handlers/core_handlers.py`)

---

### ÉTAPE 1 : Card Produit (version courte)

**Déclencheur:** Clic sur "Acheter"

**Contenu affiché:**
- **Photo produit** (en haut de message)
- **Titre** (gras, 1-2 lignes max)
- **Nom vendeur** (🏪 Nom)
- **Prix** (💰 XX.XX€)
- **Description raccourcie** (2-3 lignes max, tronquée intelligemment avec "...")
- **Catégorie** (📂 Nom catégorie - en bas du texte)

**Boutons (5 lignes):**
```
Ligne 1: [ACHETER] (pleine largeur, CTA principal)

Ligne 2: [←] [1|2|3|4|5] [→] (pagination produits dans catégorie actuelle)

Ligne 3: [Détails] (pleine largeur)

Ligne 4: [←] [Nom catégorie] [→] (pagination entre catégories)

Ligne 5: [HOME]
```

**État actuel dans le code:**
- ✅ **Fonction existante:** `show_product_carousel()` (ligne 293, buy_handlers.py)
- ❌ **PROBLÈME:** Pagination catégories (ligne 4) n'existe pas actuellement
- ❌ **PROBLÈME:** Description pas raccourcie de manière optimale (actuellement 180 chars, devrait être 2-3 lignes visuelles)

---

### ÉTAPE 2 : Sélection Crypto

**Déclencheur:** Clic sur "ACHETER" (depuis n'importe quelle card: courte, détails, avis, preview)

**Contenu:**
```
💳 PAIEMENT

📦 [Titre produit]
💰 [XX.XX€]

Choisissez votre cryptomonnaie:
```

**Boutons (4 lignes):**
```
Ligne 1: [BTC] [ETH]

Ligne 2: [SOLANA] (pleine largeur)

Ligne 3: [USDC] [USDT]

Ligne 4: [Précédent]
```

**État actuel dans le code:**
- ✅ **Fonction existante:** `buy_product()` (ligne 1084, buy_handlers.py)
- ✅ **Bon état:** La sélection crypto existe déjà et fonctionne bien
- ⚠️ **À améliorer:** Layout boutons (actuellement liste verticale, devrait être grille 2x2 + 1)

---

### ÉTAPE 3 : Paiement QR Code

**Déclencheur:** Clic sur une crypto (ex: SOLANA)

**Contenu:**
- **QR code** (à l'emplacement habituel de l'image)
- **Texte:**
  ```
  💳 PAIEMENT SOLANA

  Envoyez exactement:
  X.XXXXXXX SOL

  À cette adresse:
  [adresse_longue]

  ⏰ Expire dans 1 heure
  ```

**Boutons (1 ligne):**
```
[Précédent]
```

**État actuel dans le code:**
- ✅ **Fonction existante:** `process_crypto_payment()` puis `_display_payment_details()` (lignes 1160 et 1544)
- ✅ **Bon état:** QR code généré et affiché
- ✅ **Bon état:** Informations paiement complètes

---

## 2. VARIANTES DU WORKFLOW

### VARIANTE 1A : Card Détails (version longue)

**Déclencheur:** Clic sur "Détails" depuis card produit

**Contenu affiché:**
- **Photo produit**
- **Titre**
- **Nom vendeur**
- **Prix**
- **Description COMPLÈTE** (tout le texte sans troncature, listes à puces, programme, audience cible)
- **Métadonnées** (catégorie, taille fichier, nombre vues, nombre ventes)

**Boutons (4 lignes):**
```
Ligne 1: [ACHETER] (pleine largeur)

Ligne 2: [Avis] [Préview]

Ligne 3: [Réduire] (pleine largeur - retour à card courte)

Ligne 4: [Précédent]
```

**État actuel dans le code:**
- ✅ **Fonction existante:** `show_product_details()` puis `_show_product_visual()` (lignes 524 et 549)
- ⚠️ **PROBLÈME:** Description complète affichée dès le carousel (ligne 357-363)
- ❌ **MANQUE:** Bouton "Réduire" n'existe pas
- ❌ **MANQUE:** Bouton "Avis" n'existe pas dans ce contexte

---

### VARIANTE 1B : Page Avis

**Déclencheur:** Clic sur "Avis" depuis card détails

**Contenu:**
```
⭐ AVIS CLIENTS

📦 [Titre produit]
💰 [Prix]

Note moyenne: ⭐⭐⭐⭐⭐ 4.8/5 (127 avis)

───────────────────
👤 Marie L.
⭐⭐⭐⭐⭐ 5/5
"Excellent contenu, très complet!"
Il y a 3 jours

👤 Thomas K.
⭐⭐⭐⭐ 4/5
"Bon produit mais un peu long"
Il y a 1 semaine

[... 3 autres avis ...]
```

**Boutons (3 lignes):**
```
Ligne 1: [ACHETER] (pleine largeur)

Ligne 2: [←] [1|2|3|4|5] [→] (pagination avis, 5 par page)

Ligne 3: [Précédent]
```

**État actuel dans le code:**
- ❌ **MANQUE COMPLÈTEMENT:** Aucune page d'avis dédiée
- ✅ **Données existent:** Table `reviews` existe (database_init.py ligne 179)
- ❌ **Fonction à créer:** `show_product_reviews()`

---

### VARIANTE 1C : Preview PDF

**Déclencheur:** Clic sur "Préview" depuis card détails

**Contenu:**
- **Image:** Première page du PDF convertie en image
- **Texte:**
  ```
  👁️ APERÇU

  📄 Page 1/125

  📦 [Titre produit]
  ```

**Boutons (2 lignes):**
```
Ligne 1: [ACHETER] (pleine largeur)

Ligne 2: [Précédent]
```

**État actuel dans le code:**
- ✅ **Fonction existante:** `preview_product()` (ligne 1260)
- ✅ **Bon état:** PDF preview fonctionne déjà (PyMuPDF, ligne 1315-1347)
- ✅ **Bon état:** Aussi video preview (ffmpeg, ligne 1352-1415) et zip preview (ligne 1420-1467)

---

## 3. RÈGLES DE NAVIGATION

### Bouton ACHETER

**Présent dans:**
- ✅ Card produit (carousel)
- ✅ Card détails
- ❌ Page avis (à ajouter)
- ✅ Preview PDF

**Comportement:** TOUJOURS mène à ÉTAPE 2 (Sélection Crypto)

**Remarque:** C'est LE MÊME bouton partout, même destination (`callback_data='buy_product_{product_id}'`)

**Callback actuel:** `buy_product_{product_id}` → fonction `buy_product()` ✅

---

### Bouton Précédent

**Comportement contextuel selon l'origine:**

| Depuis... | Retour vers... | État actuel |
|-----------|----------------|-------------|
| Sélection crypto | Card produit | ✅ Fonctionne |
| Paiement QR | Sélection crypto | ✅ Fonctionne |
| Page avis | Card détails | ❌ À créer |
| Preview PDF | Card détails | ✅ Fonctionne |
| Card détails | Navigation contextuelle | ⚠️ Retourne browse_categories |

---

### Bouton Réduire

**Présent uniquement dans:** Card détails

**Comportement:** Retour à Card produit (version courte) avec même index carousel

**État actuel:** ❌ N'existe pas, à créer

---

### Accès direct par ID produit

**Fonctionnalité:** À N'IMPORTE QUELLE étape, l'utilisateur peut entrer un ID produit (ex: TBF-12345678)

**Comportement:** Charge immédiatement la card de ce produit (ÉTAPE 1)

**État actuel:**
- ✅ **Fonction existante:** `process_product_search()` (ligne 644)
- ✅ **Bon état:** Fonctionne bien, affiche card visuelle complète

---

## 4. DONNÉES DATABASE NÉCESSAIRES

### Table `products` (existante)

**Champs actuels à CONSERVER:**
```sql
✅ product_id TEXT UNIQUE
✅ seller_user_id INTEGER
✅ title TEXT NOT NULL
✅ description TEXT
✅ category TEXT
✅ price_eur REAL NOT NULL
✅ main_file_path TEXT
✅ file_size_mb REAL
✅ cover_image_path TEXT
✅ thumbnail_path TEXT
✅ views_count INTEGER DEFAULT 0
✅ sales_count INTEGER DEFAULT 0
✅ rating REAL DEFAULT 0.0
✅ reviews_count INTEGER DEFAULT 0
✅ created_at TIMESTAMP
```

**Nouveaux champs NÉCESSAIRES:**
```sql
❌ short_description TEXT  -- Description 2-3 lignes pour card courte
                           -- (Actuellement: description tronquée dynamiquement à 180 chars)

❌ full_description TEXT   -- Description complète pour card détails
                           -- (Actuellement: même champ "description" pour tout)
```

**Recommandation:**
- **NE PAS** ajouter de nouvelles colonnes maintenant
- **Utiliser** logique de troncature intelligente (couper au dernier espace avant 180 chars) pour card courte
- **Afficher** description complète pour card détails
- **Migration future:** Si besoin, vendeur pourra définir short_description séparément

---

### Table `reviews` (existante)

**Champs actuels:**
```sql
✅ id INTEGER PRIMARY KEY AUTOINCREMENT
✅ product_id TEXT
✅ buyer_user_id INTEGER
✅ order_id TEXT
✅ rating INTEGER CHECK(rating >= 1 AND rating <= 5)
✅ comment TEXT
✅ review_text TEXT
✅ created_at TIMESTAMP
✅ updated_at TIMESTAMP
```

**État:** ✅ **Prête à l'emploi** - Tous les champs nécessaires existent

**Nouveaux champs OPTIONNELS (Phase 2):**
```sql
⏳ photo_path TEXT  -- Photo uploadée par acheteur avec son avis
⏳ helpful_count INTEGER DEFAULT 0  -- Nombre de "👍 Utile"
```

---

### Table `categories` (existante)

**Champs actuels:**
```sql
✅ id INTEGER PRIMARY KEY AUTOINCREMENT
✅ name TEXT UNIQUE
✅ description TEXT
✅ icon TEXT
✅ products_count INTEGER DEFAULT 0
```

**État:** ✅ **Prête à l'emploi**

**Données par défaut (7 catégories):**
1. 💰 Finance & Crypto
2. 📈 Marketing Digital
3. 💻 Développement
4. 🎨 Design & Créatif
5. 📊 Business
6. 🎓 Formation Pro
7. 🔧 Outils & Tech

---

## 5. ANALYSE DE L'EXISTANT À NETTOYER

### Fichiers suspects/inutiles

#### ❌ Fichiers à SUPPRIMER (après validation workflow V2)
```
app/integrations/telegram/handlers/stoooock.py  -- Fichier de test/backup vide ou obsolète
```

#### ⚠️ Fichiers à ANALYSER (potentiellement redondants)
```
app/integrations/telegram/keyboards.py  -- Vérifier si tout est utilisé
                                        -- Actuellement: 150+ lignes de définitions keyboard
                                        -- Beaucoup pourraient être inline dans handlers
```

---

### Fonctions obsolètes dans `buy_handlers.py`

**Ligne de code actuel:** 1645 lignes (buy_handlers.py)

#### ✅ Fonctions À CONSERVER (workflow V2)

| Fonction | Ligne | Usage V2 |
|----------|-------|----------|
| `show_product_carousel()` | 293 | ✅ Card produit courte (Étape 1) |
| `buy_product()` | 1084 | ✅ Sélection crypto (Étape 2) |
| `process_crypto_payment()` | 1160 | ✅ Paiement QR (Étape 3) |
| `preview_product()` | 1260 | ✅ Preview PDF/Video/Zip (Variante 1C) |
| `show_product_details()` | 524 | ✅ Card détails (Variante 1A) |
| `process_product_search()` | 644 | ✅ Recherche par ID |
| `browse_categories()` | 107 | ✅ Liste catégories |
| `check_payment_handler()` | 797 | ✅ Vérification paiement |

#### ❌ Fonctions POTENTIELLEMENT REDONDANTES

| Fonction | Ligne | Problème | Action |
|----------|-------|----------|--------|
| `send_product_card()` | 169 | Doublon avec `show_product_carousel()` ? | À ANALYSER - Peut-être utilisé pour envoi initial vs navigation |
| `_show_product_visual()` | 549 | Doublon avec `show_product_carousel()` ? | À ANALYSER - Semble être wrapper interne |
| `show_product_details_from_search()` | 677 | Doublon avec `show_product_details()` ? | À FUSIONNER - Logique quasi-identique |
| `show_category_products()` | 490 | Semble wrapper de `show_product_carousel()` | À ANALYSER - Peut être simplifié |

---

### Code dupliqué identifié

#### 🔁 DUPLICATION #1: Construction caption produit

**Emplacements:**
- `show_product_carousel()` ligne 312-371 (60 lignes)
- `_show_product_visual()` ligne 559-581 (23 lignes)
- `show_product_details_from_search()` ligne 686-740 (55 lignes)

**Solution:** Créer fonction `_build_product_caption(product, mode='short'|'full')`

**Réduction estimée:** ~90 lignes → ~30 lignes (gain de 60 lignes)

---

#### 🔁 DUPLICATION #2: Gestion image/placeholder

**Emplacements:**
- `show_product_carousel()` ligne 373-388 (16 lignes)
- `_show_product_visual()` ligne 584-596 (13 lignes)
- `show_product_details_from_search()` ligne 742-757 (16 lignes)
- `send_product_card()` ligne 183-193 (11 lignes)

**Solution:** Créer fonction `_get_product_image_or_placeholder(product)`

**Réduction estimée:** ~56 lignes → ~15 lignes (gain de 41 lignes)

---

#### 🔁 DUPLICATION #3: Keyboard construction "Acheter + Actions"

**Emplacements:**
- `show_product_carousel()` ligne 389-431 (43 lignes)
- `_show_product_visual()` ligne 597-614 (18 lignes)
- `show_product_details_from_search()` ligne 758-778 (21 lignes)

**Solution:** Créer fonction `_build_product_keyboard(product, context='carousel'|'details'|'search')`

**Réduction estimée:** ~82 lignes → ~30 lignes (gain de 52 lignes)

---

### Estimation réduction

| Métrique | Avant | Après nettoyage | Réduction |
|----------|-------|-----------------|-----------|
| **Lignes buy_handlers.py** | 1645 | ~1200 | **-27%** |
| **Fichiers handlers/** | 7 fichiers | 6-7 fichiers | 0-1 supprimé |
| **Fonctions dans buy_handlers** | ~25 | ~18 | **-7 fonctions** |
| **Duplication code** | ~228 lignes | ~75 lignes | **-153 lignes** |

**Objectif final:** Code plus maintenable, moins de bugs, workflow 2x plus rapide pour utilisateur

---

## 6. CHECKLIST VALIDATION

Avant implémentation, valider:

- [ ] **Workflows clairs et cohérents**
  - [ ] Étape 0 → 1 → 2 → 3 bien défini
  - [ ] Variantes 1A, 1B, 1C bien documentées
  - [ ] Aucune ambiguïté dans les transitions

- [ ] **Règles de navigation sans ambiguïté**
  - [ ] Bouton ACHETER toujours même destination
  - [ ] Bouton Précédent contextuel bien défini
  - [ ] Bouton Réduire comportement clair
  - [ ] Recherche par ID fonctionne partout

- [ ] **Données DB identifiées**
  - [ ] Table products prête
  - [ ] Table reviews prête
  - [ ] Table categories prête
  - [ ] Pas de migration DB urgente nécessaire

- [ ] **Ancien code à supprimer listé**
  - [ ] Fonctions redondantes identifiées
  - [ ] Code dupliqué repéré
  - [ ] Plan de nettoyage clair

- [ ] **Nouveau workflow plus court**
  - [ ] 2-3 clics vs 6+ actuellement
  - [ ] Bouton ACHETER accessible partout
  - [ ] Moins de navigation inutile

---

## 7. PLAN DE NETTOYAGE POST-VALIDATION

⚠️ **À exécuter UNIQUEMENT après validation des spécifications et implémentation réussie**

### Phase 1 : Identification code obsolète

#### Handlers de l'ancien workflow à analyser

**Callbacks potentiellement obsolètes après V2:**

| Callback actuel | Fonction | Remplacé par | Action |
|-----------------|----------|--------------|--------|
| `product_details_{id}` | `show_product_details()` | Card détails intégrée | ⚠️ À CONSERVER (variante 1A) |
| `product_preview_{id}` | `preview_product()` | Preview intégré | ✅ GARDER (variante 1C) |
| `category_{name}` | `show_category_products()` | Carousel catégorie | ✅ GARDER |
| `browse_categories` | `browse_categories()` | Liste catégories | ✅ GARDER |

**Conclusion:** Très peu d'obsolescence - le workflow actuel est déjà assez propre !

---

#### Fonctions qui ne seront plus appelées

**Après refactoring duplication:**

```python
# Ces fonctions seront FUSIONNÉES dans helpers internes
❌ _show_product_visual()          → Fusionné dans show_product_carousel()
❌ show_product_details_from_search() → Fusionné dans show_product_details()
```

---

#### Imports inutilisés à vérifier

```python
# buy_handlers.py lignes 1-22
⚠️ import uuid  -- Utilisé ? (Vérifier usage dans code)
⚠️ from io import BytesIO  -- Utilisé pour QR code (GARDER)
⚠️ import re  -- Utilisé ? (Vérifier usage)
```

**Action:** Analyse statique pour détecter imports non utilisés

---

#### Constantes/configs obsolètes

**Aucune constante obsolète identifiée pour l'instant** ✅

---

### Phase 2 : Suppressions à effectuer

#### Fichiers complets à supprimer

```
❌ app/integrations/telegram/handlers/stoooock.py
   Justification: Fichier de test/backup, nom suspect, probablement vide
```

---

#### Fonctions à supprimer par fichier

**buy_handlers.py:**

```python
# Après refactoring, ces fonctions deviennent internes (préfixe _)
# et sont fusionnées:

Ligne 549: async def _show_product_visual()
  → FUSIONNER dans show_product_carousel() avec param mode='full'

Ligne 677: async def show_product_details_from_search()
  → FUSIONNER dans show_product_details() (caller directement)

# Nouvelles fonctions helpers internes à créer:
+ async def _build_product_caption(product, mode='short'|'full')
+ async def _get_product_image_or_placeholder(product)
+ async def _build_product_keyboard(product, context)
```

---

#### Sections de code à retirer

**buy_handlers.py - Duplication caption:**

```python
# AVANT (3 endroits dupliqués):
Lignes 312-371: Construction caption dans show_product_carousel()
Lignes 686-740: Construction caption dans show_product_details_from_search()

# APRÈS (appel fonction unique):
caption = await self._build_product_caption(product, mode='short')
```

---

### Phase 3 : Objectif final

#### Métriques code

| Métrique | Actuel | Cible | Réduction |
|----------|--------|-------|-----------|
| **Lignes buy_handlers.py** | 1645 lignes | **~1200 lignes** | **-27%** |
| **Fonctions publiques** | 15 fonctions | **12 fonctions** | **-20%** |
| **Fonctions helpers internes** | 5 fonctions | **8 fonctions** | +60% (meilleure organisation) |
| **Code dupliqué** | ~228 lignes | **~75 lignes** | **-67%** |
| **Complexité cyclomatique** | Moyenne | **Faible** | ⬇️ Meilleure maintenabilité |

---

#### Métriques UX utilisateur

| Métrique | Avant V2 | Après V2 | Amélioration |
|----------|----------|----------|--------------|
| **Clics Browse → Achat** | 6+ clics | **2-3 clics** | **-50% à -66%** |
| **Temps moyen achat** | ~90 secondes | **~30 secondes** | **-66%** |
| **Taux abandon panier** | 60-70% | **30-40%** (objectif) | **-43% à -50%** |
| **Bouton ACHETER visible** | 1 endroit | **Partout** | ⬆️ Toujours accessible |

---

### ⚠️ IMPORTANT - Ordre d'exécution

**NE PAS commencer le nettoyage avant:**

1. ✅ Validation de ces spécifications par le développeur
2. ✅ Implémentation complète du nouveau workflow V2
3. ✅ Tests utilisateurs confirmant que V2 fonctionne
4. ✅ Backup de la branche actuelle (`git branch backup/pre-v2-cleanup`)

**Une fois ces 4 étapes validées:**
- On supprime l'ancien code
- On consolide les fonctions
- On nettoie les duplications
- **Objectif:** Code 30% plus court, UX 2x plus rapide

---

## 8. AJOUTS NÉCESSAIRES (Nouvelles fonctionnalités)

### ❌ MANQUE : Page Avis produit (Variante 1B)

**Fonction à créer:** `show_product_reviews(bot, query, product_id, page=0)`

**Emplacement:** buy_handlers.py (~60 lignes)

**Logique:**
```python
async def show_product_reviews(self, bot, query, product_id: str, lang: str, page: int = 0):
    """Affiche les avis clients avec pagination (5 avis par page)"""

    # 1. Récupérer produit pour contexte
    product = bot.get_product_by_id(product_id)

    # 2. Récupérer avis depuis DB avec pagination
    reviews = self.review_repo.get_product_reviews(product_id, limit=5, offset=page*5)
    total_reviews = product.get('reviews_count', 0)

    # 3. Construire message avec note moyenne + liste avis
    text = f"⭐ AVIS CLIENTS\n\n📦 {product['title']}\n..."

    # 4. Keyboard avec pagination + bouton ACHETER
    keyboard = [
        [InlineKeyboardButton("🛒 ACHETER", callback_data=f'buy_product_{product_id}')],
        [InlineKeyboardButton("←", ...), ..., InlineKeyboardButton("→", ...)],
        [InlineKeyboardButton("Précédent", callback_data=f'product_details_{product_id}')]
    ]

    # 5. Afficher (gérer transition depuis card avec photo)
    await self._safe_transition_to_text(query, text, InlineKeyboardMarkup(keyboard))
```

**Callback à ajouter dans router:** `reviews_{product_id}_p{page}`

---

### ❌ MANQUE : Bouton "Réduire" (Card détails → Card courte)

**Fonction à créer:** `collapse_product_details(bot, query, product_id, category_key, index)`

**Emplacement:** buy_handlers.py (~15 lignes)

**Logique:**
```python
async def collapse_product_details(self, bot, query, product_id: str, category_key: str, index: int, lang: str):
    """Retour de card détails vers card courte (carousel)"""

    # Récupérer tous les produits de la catégorie
    products = self.product_repo.get_products_by_category(category_key)

    # Relancer carousel à l'index sauvegardé
    await self.show_product_carousel(bot, query, category_key, products, index, lang)
```

**Problème:** Comment sauvegarder `category_key` et `index` dans callback ?

**Solution:** Callback data: `collapse_{product_id}_{category_key}_{index}`

---

### ⚠️ AMÉLIORATION : Pagination catégories (Card produit ligne 4)

**Fonction à créer:** `navigate_categories(bot, query, current_category, direction='next'|'prev')`

**Emplacement:** buy_handlers.py (~40 lignes)

**Logique:**
```python
async def navigate_categories(self, bot, query, current_category: str, direction: str, lang: str):
    """Navigation entre catégories avec ← →"""

    # 1. Récupérer toutes les catégories (ordre fixe)
    all_categories = ['Finance & Crypto', 'Marketing Digital', 'Développement', ...]

    # 2. Trouver index catégorie actuelle
    current_index = all_categories.index(current_category)

    # 3. Calculer nouvelle catégorie
    if direction == 'next':
        new_index = (current_index + 1) % len(all_categories)
    else:
        new_index = (current_index - 1) % len(all_categories)

    new_category = all_categories[new_index]

    # 4. Afficher premier produit de nouvelle catégorie
    await self.show_category_products(bot, query, new_category, lang, page=0)
```

**Callback à ajouter:** `navcat_{category}_{direction}`

---

## 9. RÉCAPITULATIF ACTIONS REQUISES

### ✅ Code déjà fonctionnel (garder tel quel)

1. ✅ Carousel produits (Étape 1)
2. ✅ Sélection crypto (Étape 2)
3. ✅ Paiement QR code (Étape 3)
4. ✅ Preview PDF/Video/Zip (Variante 1C)
5. ✅ Recherche par ID produit
6. ✅ Liste catégories

---

### ⚠️ Code à AMÉLIORER

1. ⚠️ Layout boutons sélection crypto (grille 2x2 au lieu de liste)
2. ⚠️ Description tronquée intelligemment (card courte vs détails)
3. ⚠️ Refactoring duplication (caption, images, keyboards)

---

### ❌ Code à CRÉER

1. ❌ Page avis produit (Variante 1B)
2. ❌ Bouton "Réduire" (Card détails → Card courte)
3. ❌ Navigation entre catégories (flèches ← →)
4. ❌ Fonctions helpers internes:
   - `_build_product_caption(product, mode)`
   - `_get_product_image_or_placeholder(product)`
   - `_build_product_keyboard(product, context)`

---

### 🗑️ Code à SUPPRIMER (après validation V2)

1. 🗑️ Fichier `stoooock.py`
2. 🗑️ Fonctions redondantes (après fusion):
   - `_show_product_visual()`
   - `show_product_details_from_search()`

---

## 10. QUESTIONS POUR VALIDATION

### Question 1: Description courte vs complète

**Actuellement:** Même champ `description` tronqué dynamiquement

**Options:**

A) ✅ **Garder approche actuelle** (troncature dynamique 180 chars)
   - Avantage: Pas de migration DB, simple
   - Inconvénient: Vendeur ne contrôle pas le texte court

B) ❌ Ajouter colonnes `short_description` et `full_description`
   - Avantage: Vendeur contrôle les 2 versions
   - Inconvénient: Migration DB, plus complexe

**Recommandation:** **Option A** pour V2, Option B en V3 si demandé

---

### Question 2: Pagination catégories

**Actuellement:** Pas de navigation catégories depuis card produit

**Options:**

A) ✅ **Ajouter boutons ← [Catégorie] →** (ligne 4 card produit)
   - Avantage: Navigation rapide entre catégories
   - Inconvénient: +2 boutons, un peu plus chargé

B) ❌ Garder seulement bouton "Retour catégories"
   - Avantage: Interface plus simple
   - Inconvénient: Moins fluide pour découvrir produits

**Recommandation:** **Option A** - Navigation fluide type e-commerce moderne

---

### Question 3: Ordre priorité implémentation

**Quel ordre préférez-vous ?**

1. **Approche "Améliorer puis nettoyer"**
   - Étape 1: Créer nouvelles fonctionnalités (avis, réduire, nav catégories)
   - Étape 2: Refactoring duplication
   - Étape 3: Suppression code obsolète

2. **Approche "Nettoyer puis améliorer"**
   - Étape 1: Refactoring duplication
   - Étape 2: Suppression code obsolète
   - Étape 3: Créer nouvelles fonctionnalités

**Recommandation:** **Approche 1** - Ajout fonctionnalités d'abord, puis cleanup

---

## ✅ VALIDATION FINALE

**Ce document est prêt pour validation.**

Une fois validé, nous pourrons:
1. Implémenter les améliorations proposées
2. Créer les nouvelles fonctionnalités manquantes
3. Refactoriser le code dupliqué
4. Nettoyer le code obsolète

**Objectif:** Workflow acheteur 2x plus rapide, code 30% plus court, UX moderne type e-commerce.

---

**Statut:** 📋 **EN ATTENTE DE VALIDATION DÉVELOPPEUR**

**Prochaine étape:** Relire ce document, poser questions, valider ou demander modifications.
