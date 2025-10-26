# SPÉCIFICATIONS BASE DE DONNÉES - MARKETPLACE TELEGRAM

**Version:** 1.0
**Date:** 2025-10-18
**Statut:** 📋 EN ATTENTE DE VALIDATION

---

## 📋 TABLE DES MATIÈRES

1. [Schéma Cible (Nouveau)](#1-schéma-cible-nouveau)
2. [Diagramme Relations](#2-diagramme-relations)
3. [Analyse de l'Existant](#3-analyse-de-lexistant)
4. [Propositions d'Amélioration](#4-propositions-damélioration)
5. [Plan de Migration](#5-plan-de-migration)
6. [Risques et Précautions](#6-risques-et-précautions)
7. [Checklist Validation](#7-checklist-validation)

---

## 1. SCHÉMA CIBLE (NOUVEAU)

### 1.1 Table `users`

**Fonction:** Stocke TOUS les utilisateurs (acheteurs et/ou vendeurs).

**⚠️ ANALYSE ANTI-DOUBLON:**
- ✅ **Table existe déjà** : `users` dans database_init.py:57
- 🔄 **RENOMMER CLEF PRIMAIRE** : `user_id` → `telegram_id` (pour clarté)
- ✅ **Champs réutilisables tels quels** : `username`, `is_seller`, `seller_name`, `seller_bio`, `email`, `seller_solana_address`, `password_hash`, `password_salt`, `recovery_code_hash`
- ➕ **Champs à AJOUTER** : `is_buyer`, `products_purchased_count`, `is_active`
- ❌ **Champs OBSOLÈTES à supprimer** : `first_name`, `language_code`, `registration_date`, `last_activity`, `seller_rating`, `total_sales`, `total_revenue`, `recovery_code_expiry`

**Schéma cible:**
```sql
CREATE TABLE users (
    -- Identité Telegram (RENAMED from user_id)
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,

    -- Rôles (un user peut être les deux)
    is_seller BOOLEAN DEFAULT 0,        -- ✅ EXISTS
    is_buyer BOOLEAN DEFAULT 1,         -- ➕ TO ADD

    -- Stats acheteur
    products_purchased_count INTEGER DEFAULT 0,  -- ➕ TO ADD

    -- Infos vendeur (NULL si pas vendeur)
    seller_name TEXT,                   -- ✅ EXISTS
    seller_bio TEXT,                    -- ✅ EXISTS
    seller_email TEXT UNIQUE,           -- ✅ EXISTS (currently 'email')
    password_hash TEXT,                 -- ✅ EXISTS
    password_salt TEXT,                 -- ✅ EXISTS
    solana_address TEXT,                -- ✅ EXISTS (currently 'seller_solana_address')
    recovery_code_hash TEXT,            -- ✅ EXISTS

    -- État compte
    is_active BOOLEAN DEFAULT 1,        -- ➕ TO ADD

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- ✅ EXISTS (currently 'registration_date')
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP   -- ➕ TO ADD
);
```

**Migration nécessaire:**
- ALTER TABLE (renommer colonnes)
- ALTER TABLE (ajouter nouvelles colonnes)
- UPDATE (supprimer colonnes obsolètes via recréation table)

---

### 1.2 Table `products`

**Fonction:** Stocke tous les produits numériques vendus sur la marketplace.

**⚠️ ANALYSE ANTI-DOUBLON:**
- ✅ **Table existe déjà** : `products` dans database_init.py:112
- ✅ **Champs réutilisables tels quels** : `product_id`, `seller_user_id`, `title`, `price_eur`, `cover_image_path`, `thumbnail_path`, `views_count`, `status`, `created_at`, `updated_at`
- 🔄 **Champs à RENOMMER** : `description` → `full_description`, `main_file_path` → `file_url`, `category` (TEXT) → `category_id` (INTEGER)
- ➕ **Champs à AJOUTER** : `short_description`, `preview_image_url`, `is_suspended`
- ❌ **Champs OBSOLÈTES** : `price_usd` (redondant), `file_size_mb` (inutile), `sales_count` (dénormalisé), `rating` (dénormalisé), `reviews_count` (dénormalisé)

**Schéma cible:**
```sql
CREATE TABLE products (
    -- Identifiant
    product_id TEXT PRIMARY KEY,                    -- ✅ EXISTS (currently indexed on 'id')

    -- Vendeur
    seller_user_id INTEGER NOT NULL,                -- ✅ EXISTS (FK to users.telegram_id)

    -- Informations produit
    title TEXT NOT NULL,                            -- ✅ EXISTS
    short_description TEXT,                         -- ➕ TO ADD (max 200 chars)
    full_description TEXT,                          -- 🔄 RENAME from 'description'
    price DECIMAL(10,2) NOT NULL,                   -- ✅ EXISTS ('price_eur')

    -- Fichiers
    file_url TEXT,                                  -- 🔄 RENAME from 'main_file_path'
    cover_image_url TEXT,                           -- ✅ EXISTS ('cover_image_path')
    preview_image_url TEXT,                         -- ➕ TO ADD (preview PDF 1ère page)

    -- Catégorie
    category_id INTEGER,                            -- 🔄 CHANGE from TEXT to INTEGER FK

    -- État produit
    status TEXT DEFAULT 'active',                   -- ✅ EXISTS
    is_suspended BOOLEAN DEFAULT 0,                 -- ➕ TO ADD

    -- Stats
    views_count INTEGER DEFAULT 0,                  -- ✅ EXISTS

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- ✅ EXISTS
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- ✅ EXISTS

    FOREIGN KEY (seller_user_id) REFERENCES users(telegram_id),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);
```

**❌ Données DÉNORMALISÉES à supprimer:**
- `sales_count` → calculable via `COUNT(orders WHERE product_id=X)`
- `rating` → calculable via `AVG(reviews.rating WHERE product_id=X)`
- `reviews_count` → calculable via `COUNT(reviews WHERE product_id=X)`

**💡 Justification:** Les triggers actuels (database_init.py:533-589) maintiennent automatiquement ces champs, mais créent une complexité inutile. Préférer requêtes JOINs pour analytics.

---

### 1.3 Table `orders`

**Fonction:** Représente les commandes/achats. Une commande = un acheteur achète un produit.

**⚠️ ANALYSE ANTI-DOUBLON:**
- ✅ **Table existe déjà** : `orders` dans database_init.py:146
- ✅ **Champs réutilisables tels quels** : `order_id`, `product_id`, `buyer_user_id`, `seller_user_id`, `crypto_currency`, `payment_status`, `created_at`, `payment_id`,
- 🔄 **Champs à RENOMMER** : `product_price_eur` → `amount`, `crypto_currency` → `crypto_used`, `completed_at` → `updated_at`
- ➕ **Champs à AJOUTER** : `transaction_hash`, `category_id` (dénormalisé pour analytics)
- ❌ **Champs OBSOLÈTES** : `product_title` (JOIN avec products), `nowpayments_id`, `payment_currency`, `crypto_amount`, `payment_address`, `seller_revenue`, `file_delivered`, `download_count`, `last_download_at`

**Schéma cible:**
```sql
CREATE TABLE orders (
    -- Identifiant
    order_id TEXT PRIMARY KEY,                      -- ✅ EXISTS (currently indexed on 'id')

    -- Relations
    product_id TEXT NOT NULL,                       -- ✅ EXISTS
    buyer_user_id INTEGER NOT NULL,                 -- ✅ EXISTS
    seller_user_id INTEGER NOT NULL,                -- ✅ EXISTS

    -- Paiement
    amount DECIMAL(10,2) NOT NULL,                  -- 🔄 RENAME from 'product_price_eur'
    crypto_used TEXT,                               -- 🔄 RENAME from 'crypto_currency'
    transaction_hash TEXT,                          -- ➕ TO ADD (blockchain TX hash)
    payment_id INTEGER NOT NULL,

    -- État
    payment_status TEXT DEFAULT 'pending',          -- ✅ EXISTS

    -- Catégorie (dénormalisée pour analytics rapides)
    category_id INTEGER,                            -- ➕ TO ADD

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- ✅ EXISTS
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 🔄 RENAME from 'completed_at'

    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (buyer_user_id) REFERENCES users(telegram_id),
    FOREIGN KEY (seller_user_id) REFERENCES users(telegram_id),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);
```

**❌ Champs NowPayments à supprimer:**
- `nowpayments_id`, `payment_address`, `crypto_amount` → déplacés vers table `payment_transactions` (si nécessaire)
- `file_delivered`, `download_count`, `last_download_at` → déplacés vers table `library_downloads` (si nécessaire)

---

### 1.4 Table `reviews`

**Fonction:** Stocke les avis/notes des acheteurs sur les produits.

**⚠️ ANALYSE ANTI-DOUBLON:**
- ✅ **Table existe déjà** : `reviews` dans database_init.py:183
- ✅ **Champs réutilisables tels quels** : `id`, `product_id`, `buyer_user_id`, `order_id`, `rating`, `created_at`
- 🔄 **Champs à FUSIONNER** : `comment` + `review_text` → `comment` (un seul champ suffit)
- ❌ **Champs OBSOLÈTES** : `updated_at` (les avis ne sont pas modifiables)

**Schéma cible:**
```sql
CREATE TABLE reviews (
    -- Identifiant
    id INTEGER PRIMARY KEY AUTOINCREMENT,           -- ✅ EXISTS

    -- Relations
    product_id TEXT NOT NULL,                       -- ✅ EXISTS
    buyer_user_id INTEGER NOT NULL,                 -- ✅ EXISTS
    order_id TEXT NOT NULL,                         -- ✅ EXISTS

    -- Avis
    rating INTEGER CHECK(rating >= 1 AND rating <= 5), -- ✅ EXISTS
    comment TEXT,                                   -- ✅ EXISTS (fusionner avec review_text)

    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- ✅ EXISTS

    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (buyer_user_id) REFERENCES users(telegram_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id),

    UNIQUE(order_id)  -- ✅ CHANGER de UNIQUE(buyer_user_id, product_id) à UNIQUE(order_id)
);
```

**🔄 Contrainte UNIQUE à modifier:**
- **Actuellement** : `UNIQUE(buyer_user_id, product_id)` → empêche un user d'acheter 2x le même produit et le noter 2x
- **Cible** : `UNIQUE(order_id)` → permet plusieurs achats du même produit, mais 1 seul avis par commande

---

### 1.5 Table `categories`

**Fonction:** Catégories de produits.

**⚠️ ANALYSE ANTI-DOUBLON:**
- ✅ **Table existe déjà** : `categories` dans database_init.py:280
- ✅ **Champs réutilisables tels quels** : `id`, `name`, `icon`, `products_count`
- ➕ **Champs à AJOUTER** : `slug`, `created_at`
- 🔄 **Champ à GARDER** : `description` (utile)

**Schéma cible:**
```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,           -- ✅ EXISTS
    name TEXT NOT NULL UNIQUE,                      -- ✅ EXISTS
    slug TEXT NOT NULL UNIQUE,                      -- ➕ TO ADD (URL-friendly)
    icon TEXT,                                      -- ✅ EXISTS (emoji)
    description TEXT,                               -- ✅ EXISTS
    products_count INTEGER DEFAULT 0,               -- ✅ EXISTS (compteur optimisé)

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- ➕ TO ADD
);
```

**✅ Catégories par défaut** (database_init.py:591-616):
```
'Finance & Crypto', 'Marketing Digital', 'Développement',
'Design & Créatif', 'Business', 'Formation Pro', 'Outils & Tech'
```

---

### 1.6 Table `payouts`

**Fonction:** Gestion des paiements aux vendeurs.

**⚠️ ANALYSE ANTI-DOUBLON:**
- ✅ **Table existe déjà** : `seller_payouts` dans database_init.py:89
- 🔄 **Nom de table à CHANGER** : `seller_payouts` → `payouts` (plus court)
- ✅ **Champs réutilisables tels quels** : `id`, `seller_user_id`, `created_at`
- 🔄 **Champs à RENOMMER** : `total_amount_sol` → `amount`, `payout_status` → `status`, `payout_tx_hash` → supprimé, `processed_at` → `completed_at`
- ➕ **Champs à AJOUTER** : `crypto`, `solana_address`
- ❌ **Champs OBSOLÈTES** : `order_ids` (JSON array, mauvaise pratique)

**Schéma cible:**
```sql
CREATE TABLE payouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,           -- ✅ EXISTS

    -- Vendeur
    seller_user_id INTEGER NOT NULL,                -- ✅ EXISTS

    -- Montant
    amount DECIMAL(10,2) NOT NULL,                  -- 🔄 RENAME from 'total_amount_sol'
    crypto TEXT,                                    -- ➕ TO ADD
    solana_address TEXT,                            -- ➕ TO ADD

    -- État
    status TEXT DEFAULT 'pending',                  -- 🔄 RENAME from 'payout_status'

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- ✅ EXISTS
    completed_at TIMESTAMP,                         -- 🔄 RENAME from 'processed_at'

    FOREIGN KEY (seller_user_id) REFERENCES users(telegram_id)
);
```

**❌ Supprimer champ `order_ids`:**
- Mauvaise pratique de stocker JSON array dans SQLite
- Si besoin de lier payouts aux orders, créer table `payout_orders` (N:N)

---

### 1.7 Table `support_tickets`

**Fonction:** Tickets de support utilisateurs.

**⚠️ ANALYSE ANTI-DOUBLON:**
- ✅ **Table existe déjà** : `support_tickets` dans database_init.py:238
- ✅ **Champs réutilisables tels quels** : `id`, `user_id`, `subject`, `status`, `created_at`, `updated_at`
- ❌ **Champs OBSOLÈTES** : `ticket_id` (redondant avec `id`), `message` (devrait être dans `messages`), `admin_response` (devrait être dans `messages`), `order_id`, `product_id`, `seller_user_id`, `assigned_to_user_id`, `issue_type`

**Schéma cible:**
```sql
CREATE TABLE support_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,           -- ✅ EXISTS

    -- Utilisateur
    user_id INTEGER NOT NULL,                       -- ✅ EXISTS

    -- Ticket
    subject TEXT,                                   -- ✅ EXISTS
    status TEXT DEFAULT 'open',                     -- ✅ EXISTS

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- ✅ EXISTS
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- ✅ EXISTS

    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
);
```

**💡 Simplification:** Supprimer tous les champs métier supplémentaires. Si besoin de contexte (order_id, product_id), le mettre dans le premier message du ticket.

---

### 1.8 Table `messages`

**Fonction:** Messages dans les tickets de support.

**⚠️ ANALYSE ANTI-DOUBLON:**
- ✅ **Table existe déjà** : `support_messages` dans database_init.py:259
- 🔄 **Nom de table à CHANGER** : `support_messages` → `messages` (plus court)
- ✅ **Champs réutilisables tels quels** : `id`, `ticket_id`, `sender_user_id`, `created_at`
- 🔄 **Champs à RENOMMER** : `message` → `message_text`, suppression de `sender_role`
- 🔄 **FK à CORRIGER** : `ticket_id` (TEXT) → INTEGER

**Schéma cible:**
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,           -- ✅ EXISTS

    -- Ticket
    ticket_id INTEGER NOT NULL,                     -- 🔄 CHANGE from TEXT to INTEGER

    -- Message
    sender_id INTEGER NOT NULL,                     -- 🔄 RENAME from 'sender_user_id'
    message_text TEXT NOT NULL,                     -- 🔄 RENAME from 'message'

    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- ✅ EXISTS

    FOREIGN KEY (ticket_id) REFERENCES support_tickets(id),
    FOREIGN KEY (sender_id) REFERENCES users(telegram_id)
);
```

**❌ Supprimer `sender_role`:** Déterminable via JOIN avec users.is_seller

---

### 1.9 Table `telegram_mappings` (CONSERVER)

**Fonction:** Multi-account support - permet à un Telegram user de gérer plusieurs comptes vendeurs.

**⚠️ ANALYSE:**
- ✅ **Table spécifique existante** : `telegram_mappings` dans database_init.py:469
- ✅ **À CONSERVER TEL QUEL** : Cette table est unique au système actuel et fonctionne bien
- ✅ **Structure optimale** : Déjà migrée vers multi-account (id AUTOINCREMENT + UNIQUE(telegram_id, seller_user_id))

**Schéma actuel (à garder):**
```sql
CREATE TABLE telegram_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    seller_user_id INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    account_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (seller_user_id) REFERENCES users (user_id),
    UNIQUE(telegram_id, seller_user_id)
);
```

**💡 Pas de modification nécessaire.**

---

### 1.10 Table `wallet_transactions` (OBSOLÈTE?)

**Fonction:** Transactions crypto wallet.

**⚠️ ANALYSE:**
- ✅ **Table existe** : `wallet_transactions` dans database_init.py:210
- ❓ **Utilité discutable** : Peut être remplacée par `orders` + `payouts`
- 🔄 **Décision à prendre** : Garder ou supprimer?

**Recommandation:** ❌ **SUPPRIMER** si non utilisée. Les transactions sont déjà trackées dans `orders`.

---

## 2. DIAGRAMME RELATIONS

### Relations entre tables (schéma cible)

```
users (telegram_id)
  ├─── 1:N ──> products (seller_user_id)
  ├─── 1:N ──> orders AS buyer (buyer_user_id)
  ├─── 1:N ──> orders AS seller (seller_user_id)
  ├─── 1:N ──> reviews (buyer_user_id)
  ├─── 1:N ──> payouts (seller_user_id)
  ├─── 1:N ──> support_tickets (user_id)
  └─── 1:N ──> messages (sender_id)

products (product_id)
  ├─── 1:N ──> orders (product_id)
  ├─── 1:N ──> reviews (product_id)
  └─── N:1 ──> categories (category_id)

orders (order_id)
  └─── 1:1 ──> reviews (order_id)

categories (id)
  └─── 1:N ──> products (category_id)

support_tickets (id)
  └─── 1:N ──> messages (ticket_id)

telegram_mappings (multi-account)
  └─── N:1 ──> users (seller_user_id)
```

---

## 3. ANALYSE DE L'EXISTANT

### 3.1 Tables actuelles

**Fichier:** `app/core/database_init.py`

#### Table: `users`
**Localisation:** database_init.py:57
**Champs actuels:**
```
user_id (PK), username, first_name, language_code, registration_date,
last_activity, is_seller, seller_name, seller_bio, seller_rating,
total_sales, total_revenue, email, seller_solana_address,
recovery_code_hash, recovery_code_expiry, password_salt, password_hash
```

#### Table: `seller_payouts`
**Localisation:** database_init.py:89
**Champs actuels:**
```
id (PK), seller_user_id, order_ids (JSON), total_amount_sol,
payout_status, payout_tx_hash, created_at, processed_at
```

#### Table: `products`
**Localisation:** database_init.py:112
**Champs actuels:**
```
id (PK), product_id (UNIQUE), seller_user_id, title, description,
category (TEXT), price_eur, price_usd, main_file_path, file_size_mb,
cover_image_path, thumbnail_path, views_count, sales_count, rating,
reviews_count, status, created_at, updated_at
```

#### Table: `orders`
**Localisation:** database_init.py:146
**Champs actuels:**
```
id (PK), order_id (UNIQUE), buyer_user_id, seller_user_id, product_id,
product_title, product_price_eur, payment_id, payment_currency,
crypto_currency, crypto_amount, payment_status, payment_address,
nowpayments_id, seller_revenue, file_delivered, download_count,
last_download_at, created_at, completed_at
```

#### Table: `reviews`
**Localisation:** database_init.py:183
**Champs actuels:**
```
id (PK), product_id, buyer_user_id, order_id, rating, comment,
review_text, created_at, updated_at, UNIQUE(buyer_user_id, product_id)
```

#### Table: `wallet_transactions`
**Localisation:** database_init.py:210
**Champs actuels:**
```
id (PK), user_id, transaction_type, crypto_currency, amount,
from_address, to_address, tx_hash, status, related_order_id,
created_at, confirmed_at
```

#### Table: `support_tickets`
**Localisation:** database_init.py:238
**Champs actuels:**
```
id (PK), user_id, ticket_id (UNIQUE), subject, message, status,
admin_response, order_id, product_id, seller_user_id,
assigned_to_user_id, issue_type, created_at, updated_at
```

#### Table: `support_messages`
**Localisation:** database_init.py:259
**Champs actuels:**
```
id (PK), ticket_id (TEXT), sender_user_id, sender_role, message,
created_at
```

#### Table: `categories`
**Localisation:** database_init.py:280
**Champs actuels:**
```
id (PK), name (UNIQUE), description, icon, products_count
```

#### Table: `telegram_mappings`
**Localisation:** database_init.py:513
**Champs actuels:**
```
id (PK), telegram_id, seller_user_id, is_active, account_name,
created_at, last_login, UNIQUE(telegram_id, seller_user_id)
```

#### Table: `id_counters` (utilitaire)
**Localisation:** app/core/utils.py:45
**Champs actuels:**
```
counter_type (PK), last_value
```

---

### 3.2 Différences avec le schéma cible

#### Table `users`

| Différence | Type | Détail |
|------------|------|--------|
| ✅ **Champs OK** | Réutilisable | `username`, `is_seller`, `seller_name`, `seller_bio`, `email`, `seller_solana_address`, `password_hash`, `password_salt`, `recovery_code_hash` |
| 🔄 **À RENOMMER** | Renommer | `user_id` → `telegram_id`, `email` → `seller_email`, `seller_solana_address` → `solana_address`, `registration_date` → `created_at` |
| ➕ **Manquants** | Ajouter | `is_buyer`, `products_purchased_count`, `is_active`, `updated_at` |
| ❌ **Obsolètes** | Supprimer | `first_name`, `language_code`, `last_activity`, `seller_rating`, `total_sales`, `total_revenue`, `recovery_code_expiry` |

**Justification suppressions:**
- `first_name`, `language_code` → Non utilisés dans workflows
- `seller_rating`, `total_sales`, `total_revenue` → Dénormalisés, calculables via JOINs
- `recovery_code_expiry` → Logique de recovery simplifiée

#### Table `products`

| Différence | Type | Détail |
|------------|------|--------|
| ✅ **Champs OK** | Réutilisable | `product_id`, `seller_user_id`, `title`, `cover_image_path`, `thumbnail_path`, `views_count`, `status`, `created_at`, `updated_at` |
| 🔄 **À RENOMMER** | Renommer | `description` → `full_description`, `main_file_path` → `file_url`, `cover_image_path` → `cover_image_url`, `price_eur` → `price`, `category` (TEXT) → `category_id` (INTEGER) |
| ➕ **Manquants** | Ajouter | `short_description`, `preview_image_url`, `is_suspended` |
| ❌ **Obsolètes** | Supprimer | `id` (auto-increment inutile si product_id est PK), `price_usd`, `file_size_mb`, `sales_count`, `rating`, `reviews_count` |

**Justification suppressions:**
- `price_usd` → Conversion en temps réel, pas besoin de stocker
- `sales_count`, `rating`, `reviews_count` → Dénormalisés avec triggers (complexité inutile)

#### Table `orders`

| Différence | Type | Détail |
|------------|------|--------|
| ✅ **Champs OK** | Réutilisable | `order_id`, `product_id`, `buyer_user_id`, `seller_user_id`, `crypto_currency`, `payment_status`, `created_at` |
| 🔄 **À RENOMMER** | Renommer | `product_price_eur` → `amount`, `crypto_currency` → `crypto_used`, `completed_at` → `updated_at` |
| ➕ **Manquants** | Ajouter | `transaction_hash`, `category_id` |
| ❌ **Obsolètes** | Supprimer | `id` (auto-increment inutile), `product_title`, `payment_id`, `payment_currency`, `crypto_amount`, `payment_address`, `nowpayments_id`, `seller_revenue`, `file_delivered`, `download_count`, `last_download_at` |

**Justification suppressions:**
- `product_title` → JOIN avec products.title
- Champs NowPayments → Si nécessaire, créer table séparée `payment_transactions`
- `file_delivered`, `download_count` → Si nécessaire, créer table séparée `library_downloads`

#### Table `reviews`

| Différence | Type | Détail |
|------------|------|--------|
| ✅ **Champs OK** | Réutilisable | `id`, `product_id`, `buyer_user_id`, `order_id`, `rating`, `created_at` |
| 🔄 **À FUSIONNER** | Fusionner | `comment` + `review_text` → `comment` (un seul champ) |
| ❌ **Obsolètes** | Supprimer | `updated_at` (avis non modifiables) |
| 🔄 **Contrainte UNIQUE** | Modifier | `UNIQUE(buyer_user_id, product_id)` → `UNIQUE(order_id)` |

#### Table `categories`

| Différence | Type | Détail |
|------------|------|--------|
| ✅ **Champs OK** | Réutilisable | `id`, `name`, `icon`, `description`, `products_count` |
| ➕ **Manquants** | Ajouter | `slug`, `created_at` |

#### Table `payouts`

| Différence | Type | Détail |
|------------|------|--------|
| 🔄 **Nom table** | Renommer | `seller_payouts` → `payouts` |
| ✅ **Champs OK** | Réutilisable | `id`, `seller_user_id`, `created_at` |
| 🔄 **À RENOMMER** | Renommer | `total_amount_sol` → `amount`, `payout_status` → `status`, `processed_at` → `completed_at` |
| ➕ **Manquants** | Ajouter | `crypto`, `solana_address` |
| ❌ **Obsolètes** | Supprimer | `order_ids` (JSON array), `payout_tx_hash` |

#### Table `support_tickets`

| Différence | Type | Détail |
|------------|------|--------|
| ✅ **Champs OK** | Réutilisable | `id`, `user_id`, `subject`, `status`, `created_at`, `updated_at` |
| ❌ **Obsolètes** | Supprimer | `ticket_id`, `message`, `admin_response`, `order_id`, `product_id`, `seller_user_id`, `assigned_to_user_id`, `issue_type` |

#### Table `messages`

| Différence | Type | Détail |
|------------|------|--------|
| 🔄 **Nom table** | Renommer | `support_messages` → `messages` |
| ✅ **Champs OK** | Réutilisable | `id`, `created_at` |
| 🔄 **À RENOMMER** | Renommer | `sender_user_id` → `sender_id`, `message` → `message_text` |
| 🔄 **Type champ** | Modifier | `ticket_id` (TEXT) → INTEGER |
| ❌ **Obsolètes** | Supprimer | `sender_role` |

#### Tables à SUPPRIMER

| Table | Raison |
|-------|--------|
| `wallet_transactions` | Redondante avec `orders` + `payouts` |
| `id_counters` | Utilité limitée, peut être remplacée par MAX(id) |

---

### 3.3 Requêtes SQL actuelles

**Analyse des fichiers avec requêtes SQL:**

#### Fichier: `app/domain/repositories/user_repo.py`

| Ligne | Type | Table | Complexité | Requête |
|-------|------|-------|------------|---------|
| 17 | INSERT | users | Simple | `INSERT OR IGNORE INTO users (user_id, username, first_name, language_code)` |
| 35 | SELECT | users | Simple | `SELECT * FROM users WHERE user_id = ?` |
| 47 | UPDATE | users | Simple | `UPDATE users SET seller_name = ? WHERE user_id = ?` |
| 59 | UPDATE | users | Simple | `UPDATE users SET seller_bio = ? WHERE user_id = ?` |
| 71 | UPDATE | users | Simple | `UPDATE users SET language_code = ? WHERE user_id = ?` |
| 83 | UPDATE | users | Simple | `UPDATE users SET is_seller = 0, seller_name = NULL WHERE user_id = ?` |
| 96 | SELECT | users | Simple | `SELECT * FROM users ORDER BY registration_date DESC LIMIT ?` |
| 108 | SELECT | users | Simple | `SELECT COUNT(*) FROM users` |
| 119 | SELECT | users | Simple | `SELECT COUNT(*) FROM users WHERE is_seller = 1` |
| 134 | SELECT | users | Simple | `SELECT * FROM users WHERE email = ?` |
| 148 | UPDATE | users | Simple | `UPDATE users SET recovery_code_hash = ?, recovery_code_expiry = ? WHERE email = ?` |
| 164 | SELECT | users | Moyenne | `SELECT user_id FROM users WHERE email = ? AND recovery_code_hash = ? AND recovery_code_expiry > ?` |
| 180 | UPDATE | users | Simple | `UPDATE users SET password_salt = ?, password_hash = ?, recovery_code_hash = NULL WHERE email = ?` |

**Méthodes existantes:** `add_user`, `get_user`, `update_seller_name`, `update_seller_bio`, `update_user_language`, `delete_seller_account`, `get_all_users`, `count_users`, `count_sellers`, `get_user_by_email`, `set_recovery_code`, `validate_recovery_code`, `update_password_by_email`

#### Fichier: `app/domain/repositories/product_repo.py`

| Ligne | Type | Table | Complexité | Requête |
|-------|------|-------|------------|---------|
| 18 | INSERT | products | Simple | `INSERT INTO products (product_id, seller_user_id, title, description, ...)` |
| 44 | UPDATE | categories | Simple | `UPDATE categories SET products_count = products_count + 1 WHERE name = ?` |
| 68 | SELECT | products JOIN users | Moyenne | `SELECT p.*, u.seller_name, u.seller_bio FROM products p LEFT JOIN users u WHERE p.product_id = ?` |
| 88 | SELECT | products JOIN users | Moyenne | `SELECT p.*, u.seller_name, u.seller_rating, u.seller_bio FROM products p JOIN users u WHERE p.product_id = ? AND p.status = 'active'` |
| 109 | UPDATE | products | Simple | `UPDATE products SET views_count = views_count + 1 WHERE product_id = ?` |
| 125 | UPDATE | products | Simple | `UPDATE products SET status = ? WHERE product_id = ?` |
| 142 | SELECT | products | Simple | `SELECT seller_user_id, title FROM products WHERE product_id = ?` |
| 149 | SELECT | products | Simple | `SELECT category FROM products WHERE product_id = ? AND seller_user_id = ?` |
| 157 | DELETE | products | Simple | `DELETE FROM products WHERE product_id = ? AND seller_user_id = ?` |
| 167 | UPDATE | categories | Simple | `UPDATE categories SET products_count = CASE WHEN products_count > 0 ...` |
| 187 | SELECT | products | Simple | `SELECT * FROM products WHERE seller_user_id = ? ORDER BY created_at DESC` |
| 208 | SELECT | products | Simple | `SELECT COUNT(*) FROM products WHERE seller_user_id = ?` |
| 223 | SELECT | products | Moyenne | `SELECT * FROM products WHERE category = ? AND status = 'active' ORDER BY sales_count DESC` |
| 244 | SELECT | products | Simple | `SELECT COUNT(*) FROM products WHERE category = ? AND status = 'active'` |
| 258 | UPDATE | products | Simple | `UPDATE products SET price_eur = ?, price_usd = ?, updated_at = CURRENT_TIMESTAMP` |
| 277 | UPDATE | products | Simple | `UPDATE products SET title = ?, updated_at = CURRENT_TIMESTAMP` |
| 296 | UPDATE | products | Simple | `UPDATE products SET description = ?, updated_at = CURRENT_TIMESTAMP` |
| 315 | SELECT | products | Simple | `SELECT * FROM products ORDER BY created_at DESC LIMIT ?` |
| 327 | SELECT | products | Simple | `SELECT COUNT(*) FROM products` |
| 372 | UPDATE | categories | Complexe | `UPDATE categories SET products_count = (SELECT COUNT(*) FROM products ...)` |

**Méthodes existantes:** `insert_product`, `get_product_by_id`, `get_product_with_seller_info`, `increment_views`, `update_status`, `delete_product`, `get_products_by_seller`, `count_products_by_seller`, `get_products_by_category`, `count_products_by_category`, `update_price`, `update_title`, `update_description`, `get_all_products`, `count_products`, `create_product`, `recalculate_category_counts`

#### Fichier: `app/domain/repositories/order_repo.py`

| Ligne | Type | Table | Complexité | Requête |
|-------|------|-------|------------|---------|
| 16 | INSERT | orders | Simple | `INSERT INTO orders (order_id, buyer_user_id, product_id, ...)` |
| 49 | SELECT | orders | Simple | `SELECT * FROM orders WHERE order_id = ?` |
| 63 | UPDATE | orders | Simple | `UPDATE orders SET payment_status = ? WHERE order_id = ?` |
| 79 | SELECT | orders | Simple | `SELECT * FROM orders WHERE buyer_user_id = ? ORDER BY created_at DESC` |
| 95 | SELECT | orders | Simple | `SELECT * FROM orders WHERE seller_user_id = ? ORDER BY created_at DESC` |
| 110 | SELECT | orders | Simple | `SELECT COUNT(*) FROM orders WHERE buyer_user_id = ? AND product_id = ? AND payment_status = "completed"` |
| 125 | UPDATE | orders | Simple | `UPDATE orders SET download_count = download_count + 1 WHERE product_id = ? AND buyer_user_id = ?` |
| 144 | SELECT | orders | Simple | `SELECT COUNT(*) FROM orders` |
| 155 | SELECT | orders | Simple | `SELECT SUM(seller_revenue) FROM orders WHERE payment_status = "completed"` |

**Méthodes existantes:** `insert_order`, `get_order_by_id`, `update_payment_status`, `get_orders_by_buyer`, `get_orders_by_seller`, `check_user_purchased_product`, `increment_download_count`, `create_order`, `count_orders`, `get_total_revenue`

---

### 3.4 Repositories existants

#### `UserRepository` (app/domain/repositories/user_repo.py)
**Méthodes existantes:**
- ✅ `add_user(user_id, username, first_name, language_code)`
- ✅ `get_user(user_id)`
- ✅ `update_seller_name(user_id, seller_name)`
- ✅ `update_seller_bio(user_id, seller_bio)`
- ✅ `update_user_language(user_id, language_code)`
- ✅ `delete_seller_account(user_id)`
- ✅ `get_all_users(limit)`
- ✅ `count_users()`
- ✅ `count_sellers()`
- ✅ `get_user_by_email(email)`
- ✅ `set_recovery_code(email, code_hash, expiry_timestamp)`
- ✅ `validate_recovery_code(email, code_hash, current_timestamp)`
- ✅ `update_password_by_email(email, password_salt, password_hash)`

**Méthodes manquantes pour nouveaux workflows:**
- ❌ `update_seller_email(user_id, new_email)` - Changer email vendeur
- ❌ `update_solana_address(user_id, address)` - Changer adresse Solana
- ❌ `deactivate_account(user_id)` - Désactiver compte
- ❌ `reactivate_account(user_id)` - Réactiver compte
- ❌ `get_seller_stats(seller_id)` - Stats vendeur (calculées dynamiquement)
- ❌ `increment_products_purchased(user_id)` - Incrémenter compteur achats

#### `ProductRepository` (app/domain/repositories/product_repo.py)
**Méthodes existantes:**
- ✅ `insert_product(product)`
- ✅ `get_product_by_id(product_id)`
- ✅ `get_product_with_seller_info(product_id)`
- ✅ `increment_views(product_id)`
- ✅ `update_status(product_id, status)`
- ✅ `delete_product(product_id, seller_user_id)`
- ✅ `get_products_by_seller(seller_user_id, limit, offset)`
- ✅ `count_products_by_seller(seller_user_id)`
- ✅ `get_products_by_category(category, limit, offset)`
- ✅ `count_products_by_category(category)`
- ✅ `update_price(product_id, seller_user_id, price_eur, price_usd)`
- ✅ `update_title(product_id, seller_user_id, title)`
- ✅ `update_description(product_id, seller_user_id, description)`
- ✅ `get_all_products(limit)`
- ✅ `count_products()`
- ✅ `create_product(product_data)`
- ✅ `recalculate_category_counts()`

**Méthodes manquantes pour nouveaux workflows:**
- ❌ `update_short_description(product_id, seller_id, short_desc)` - Modifier description courte
- ❌ `suspend_product(product_id, seller_id)` - Suspendre produit
- ❌ `unsuspend_product(product_id, seller_id)` - Réactiver produit
- ❌ `get_product_rating(product_id)` - Calculer rating dynamiquement
- ❌ `get_product_sales_count(product_id)` - Calculer ventes dynamiquement
- ❌ `search_products(query, limit)` - Recherche full-text

#### `OrderRepository` (app/domain/repositories/order_repo.py)
**Méthodes existantes:**
- ✅ `insert_order(order)`
- ✅ `get_order_by_id(order_id)`
- ✅ `update_payment_status(order_id, status)`
- ✅ `get_orders_by_buyer(buyer_user_id)`
- ✅ `get_orders_by_seller(seller_user_id)`
- ✅ `check_user_purchased_product(buyer_user_id, product_id)`
- ✅ `increment_download_count(product_id, buyer_user_id)`
- ✅ `create_order(order)`
- ✅ `count_orders()`
- ✅ `get_total_revenue()`

**Méthodes manquantes pour nouveaux workflows:**
- ❌ `get_orders_by_category(category_id)` - Filtrer par catégorie
- ❌ `get_recent_orders(limit)` - Dernières commandes
- ❌ `update_transaction_hash(order_id, tx_hash)` - Ajouter hash blockchain

#### `ReviewRepository` (À CRÉER)
**Méthodes nécessaires:**
- ❌ `add_review(product_id, buyer_id, order_id, rating, comment)`
- ❌ `get_reviews_by_product(product_id, page, per_page)`
- ❌ `get_review_by_order(order_id)`
- ❌ `can_user_review(buyer_id, product_id)` - Vérifier si achat validé
- ❌ `delete_review(review_id, buyer_id)` - Supprimer avis (si propriétaire)
- ❌ `get_average_rating(product_id)`
- ❌ `count_reviews(product_id)`

#### Autres repositories existants:
- ✅ `PayoutRepository` (app/domain/repositories/payout_repo.py)
- ✅ `TicketRepository` (app/domain/repositories/ticket_repo.py)
- ✅ `MessagingRepository` (app/domain/repositories/messaging_repo.py)

**Note:** Ces repositories existent mais nécessitent adaptation au nouveau schéma.

---

## 4. PROPOSITIONS D'AMÉLIORATION

### 4.1 Optimisations de schéma

#### Proposition 1: Index pour performances

**Description:** Ajouter index sur colonnes fréquemment utilisées dans WHERE/JOIN

```sql
-- Users
CREATE INDEX idx_users_is_seller ON users(is_seller);
CREATE INDEX idx_users_seller_email ON users(seller_email);

-- Products
CREATE INDEX idx_products_seller_id ON products(seller_user_id);
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_status ON products(status);

-- Orders
CREATE INDEX idx_orders_buyer ON orders(buyer_user_id);
CREATE INDEX idx_orders_seller ON orders(seller_user_id);
CREATE INDEX idx_orders_product ON orders(product_id);
CREATE INDEX idx_orders_status ON orders(payment_status);
CREATE INDEX idx_orders_created ON orders(created_at DESC);

-- Reviews
CREATE INDEX idx_reviews_product ON reviews(product_id);
CREATE INDEX idx_reviews_buyer ON reviews(buyer_user_id);
```

**Justification:** Accélérer requêtes JOINs et filtres sur ces colonnes
**Impact:** Moyen - Amélioration 2-5x sur requêtes complexes
**Implémentation:** Exécuter après migrations principales

#### Proposition 2: Dénormalisation catégorie dans orders

**Description:** Ajouter `category_id` dans `orders` pour analytics rapides

```sql
ALTER TABLE orders ADD COLUMN category_id INTEGER REFERENCES categories(id);
```

**Justification:** Éviter JOIN products→categories pour requêtes analytics
**Impact:** Faible - Optimisation analytics
**Implémentation:** Via trigger sur INSERT orders

```sql
CREATE TRIGGER copy_category_to_order
AFTER INSERT ON orders
BEGIN
    UPDATE orders
    SET category_id = (SELECT category_id FROM products WHERE product_id = NEW.product_id)
    WHERE order_id = NEW.order_id;
END;
```

#### Proposition 3: Contraintes CHECK supplémentaires

**Description:** Ajouter validations métier au niveau DB

```sql
-- Users
ALTER TABLE users ADD CONSTRAINT check_email_format
    CHECK (seller_email LIKE '%@%' OR seller_email IS NULL);

-- Products
ALTER TABLE products ADD CONSTRAINT check_price_positive
    CHECK (price > 0);

-- Orders
ALTER TABLE orders ADD CONSTRAINT check_amount_positive
    CHECK (amount > 0);

-- Reviews
ALTER TABLE reviews ADD CONSTRAINT check_rating_range
    CHECK (rating >= 1 AND rating <= 5);  -- ✅ Déjà existant
```

**Justification:** Intégrité données au niveau DB (défense en profondeur)
**Impact:** Faible - Sécurité additionnelle
**Implémentation:** Après migrations principales

#### Proposition 4: Supprimer triggers auto-rating

**Description:** Supprimer triggers complexes de database_init.py:533-589

**Justification:**
- Complexité inutile (3 triggers à maintenir)
- Dénormalisation évitable
- Préférer calculs dynamiques:
  ```sql
  SELECT
      p.*,
      COALESCE(AVG(r.rating), 0.0) as rating,
      COUNT(r.id) as reviews_count,
      COUNT(DISTINCT o.order_id) as sales_count
  FROM products p
  LEFT JOIN reviews r ON r.product_id = p.product_id
  LEFT JOIN orders o ON o.product_id = p.product_id AND o.payment_status = 'completed'
  GROUP BY p.product_id
  ```

**Impact:** Élevé - Simplification architecture
**Implémentation:** Supprimer triggers + mettre à jour requêtes produits

---

### 4.2 Migrations nécessaires

#### Migration 1: Restructurer table users

```sql
-- Étape 1: Backup
CREATE TABLE users_backup AS SELECT * FROM users;

-- Étape 2: Recréer table propre
DROP TABLE users;

CREATE TABLE users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    is_seller BOOLEAN DEFAULT 0,
    is_buyer BOOLEAN DEFAULT 1,
    products_purchased_count INTEGER DEFAULT 0,
    seller_name TEXT,
    seller_bio TEXT,
    seller_email TEXT UNIQUE,
    password_hash TEXT,
    password_salt TEXT,
    solana_address TEXT,
    recovery_code_hash TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Étape 3: Migrer données
INSERT INTO users (
    telegram_id, username, is_seller, seller_name, seller_bio,
    seller_email, password_hash, password_salt, solana_address,
    recovery_code_hash, created_at
)
SELECT
    user_id, username, is_seller, seller_name, seller_bio,
    email, password_hash, password_salt, seller_solana_address,
    recovery_code_hash, registration_date
FROM users_backup;

-- Étape 4: Vérifier
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM users_backup;

-- Étape 5: Cleanup
DROP TABLE users_backup;
```

#### Migration 2: Restructurer table products

```sql
-- Étape 1: Backup
CREATE TABLE products_backup AS SELECT * FROM products;

-- Étape 2: Recréer table
DROP TABLE products;

CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    seller_user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    short_description TEXT,
    full_description TEXT,
    price DECIMAL(10,2) NOT NULL,
    file_url TEXT,
    cover_image_url TEXT,
    preview_image_url TEXT,
    category_id INTEGER,
    status TEXT DEFAULT 'active',
    is_suspended BOOLEAN DEFAULT 0,
    views_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (seller_user_id) REFERENCES users(telegram_id),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- Étape 3: Migrer données
INSERT INTO products (
    product_id, seller_user_id, title, full_description, price,
    file_url, cover_image_url, category_id, status, views_count,
    created_at, updated_at
)
SELECT
    product_id, seller_user_id, title, description, price_eur,
    main_file_path, cover_image_path,
    (SELECT id FROM categories WHERE categories.name = products_backup.category),
    status, views_count, created_at, updated_at
FROM products_backup;

-- Étape 4: Vérifier
SELECT COUNT(*) FROM products;
SELECT COUNT(*) FROM products_backup;

-- Étape 5: Cleanup
DROP TABLE products_backup;
```

#### Migration 3: Restructurer table orders

```sql
-- Étape 1: Backup
CREATE TABLE orders_backup AS SELECT * FROM orders;

-- Étape 2: Recréer table
DROP TABLE orders;

CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    buyer_user_id INTEGER NOT NULL,
    seller_user_id INTEGER NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    crypto_used TEXT,
    transaction_hash TEXT,
    payment_status TEXT DEFAULT 'pending',
    category_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (buyer_user_id) REFERENCES users(telegram_id),
    FOREIGN KEY (seller_user_id) REFERENCES users(telegram_id),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- Étape 3: Migrer données
INSERT INTO orders (
    order_id, product_id, buyer_user_id, seller_user_id,
    amount, crypto_used, payment_status, created_at, updated_at
)
SELECT
    order_id, product_id, buyer_user_id, seller_user_id,
    product_price_eur, crypto_currency, payment_status,
    created_at, COALESCE(completed_at, created_at)
FROM orders_backup;

-- Étape 4: Update category_id via JOIN
UPDATE orders SET category_id = (
    SELECT category_id FROM products WHERE products.product_id = orders.product_id
);

-- Étape 5: Vérifier
SELECT COUNT(*) FROM orders;
SELECT COUNT(*) FROM orders_backup;

-- Étape 6: Cleanup
DROP TABLE orders_backup;
```

#### Migration 4: Restructurer table reviews

```sql
-- Étape 1: Supprimer ancien UNIQUE constraint
DROP INDEX IF EXISTS idx_reviews_buyer_product;

-- Étape 2: Fusionner comment + review_text
UPDATE reviews SET comment = COALESCE(comment, '') || ' ' || COALESCE(review_text, '');

-- Étape 3: Supprimer colonne review_text
-- SQLite ne supporte pas DROP COLUMN, donc recréer table:

CREATE TABLE reviews_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    buyer_user_id INTEGER NOT NULL,
    order_id TEXT NOT NULL,
    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (buyer_user_id) REFERENCES users(telegram_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    UNIQUE(order_id)
);

INSERT INTO reviews_new SELECT id, product_id, buyer_user_id, order_id, rating, comment, created_at FROM reviews;

DROP TABLE reviews;
ALTER TABLE reviews_new RENAME TO reviews;
```

#### Migration 5: Restructurer table categories

```sql
-- Ajouter colonnes manquantes
ALTER TABLE categories ADD COLUMN slug TEXT UNIQUE;
ALTER TABLE categories ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Générer slugs automatiquement
UPDATE categories SET slug = LOWER(REPLACE(name, ' ', '-'));
UPDATE categories SET slug = REPLACE(slug, '&', 'and');
UPDATE categories SET slug = REPLACE(slug, 'é', 'e');

-- Exemples résultats:
-- 'Finance & Crypto' → 'finance-and-crypto'
-- 'Marketing Digital' → 'marketing-digital'
```

#### Migration 6: Restructurer table payouts

```sql
-- Étape 1: Backup
CREATE TABLE payouts_backup AS SELECT * FROM seller_payouts;

-- Étape 2: Recréer table
DROP TABLE seller_payouts;

CREATE TABLE payouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_user_id INTEGER NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    crypto TEXT,
    solana_address TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (seller_user_id) REFERENCES users(telegram_id)
);

-- Étape 3: Migrer données
INSERT INTO payouts (
    seller_user_id, amount, status, created_at, completed_at
)
SELECT
    seller_user_id, total_amount_sol, payout_status, created_at, processed_at
FROM payouts_backup;

-- Étape 4: Ajouter crypto et solana_address depuis users
UPDATE payouts SET
    crypto = 'SOL',
    solana_address = (SELECT solana_address FROM users WHERE users.telegram_id = payouts.seller_user_id);

-- Étape 5: Cleanup
DROP TABLE payouts_backup;
```

#### Migration 7: Simplifier support_tickets

```sql
-- Étape 1: Backup
CREATE TABLE support_tickets_backup AS SELECT * FROM support_tickets;

-- Étape 2: Recréer table simplifiée
DROP TABLE support_tickets;

CREATE TABLE support_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    subject TEXT,
    status TEXT DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
);

-- Étape 3: Migrer données essentielles
INSERT INTO support_tickets (id, user_id, subject, status, created_at, updated_at)
SELECT id, user_id, subject, status, created_at, updated_at
FROM support_tickets_backup;

-- Étape 4: Migrer messages initiaux
INSERT INTO messages (ticket_id, sender_id, message_text, created_at)
SELECT id, user_id, message, created_at
FROM support_tickets_backup
WHERE message IS NOT NULL;

-- Étape 5: Cleanup
DROP TABLE support_tickets_backup;
```

#### Migration 8: Renommer support_messages → messages

```sql
-- Étape 1: Backup
CREATE TABLE messages_backup AS SELECT * FROM support_messages;

-- Étape 2: Recréer table
DROP TABLE support_messages;

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    sender_id INTEGER NOT NULL,
    message_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES support_tickets(id),
    FOREIGN KEY (sender_id) REFERENCES users(telegram_id)
);

-- Étape 3: Migrer données
INSERT INTO messages (id, ticket_id, sender_id, message_text, created_at)
SELECT
    id,
    CAST(ticket_id AS INTEGER),  -- Convertir TEXT → INTEGER
    sender_user_id,
    message,
    created_at
FROM messages_backup;

-- Étape 4: Cleanup
DROP TABLE messages_backup;
```

#### Migration 9: Supprimer tables obsolètes

```sql
DROP TABLE IF EXISTS wallet_transactions;
DROP TABLE IF EXISTS id_counters;
```

#### Migration 10: Supprimer triggers rating

```sql
DROP TRIGGER IF EXISTS update_rating_after_insert;
DROP TRIGGER IF EXISTS update_rating_after_update;
DROP TRIGGER IF EXISTS update_rating_after_delete;
```

---

### 4.3 Requêtes à optimiser

#### Requête 1: Product listing avec stats (remplacer dénormalisation)

**Avant (avec sales_count, rating dénormalisés):**
```sql
SELECT * FROM products WHERE category = ? AND status = 'active'
ORDER BY sales_count DESC, created_at DESC LIMIT 10;
```

**Après (calcul dynamique):**
```sql
SELECT
    p.*,
    COALESCE(AVG(r.rating), 0.0) as rating,
    COUNT(DISTINCT r.id) as reviews_count,
    COUNT(DISTINCT o.order_id) as sales_count
FROM products p
LEFT JOIN reviews r ON r.product_id = p.product_id
LEFT JOIN orders o ON o.product_id = p.product_id AND o.payment_status = 'completed'
WHERE p.category_id = ? AND p.status = 'active'
GROUP BY p.product_id
ORDER BY sales_count DESC, p.created_at DESC
LIMIT 10;
```

**Impact:** Suppression triggers + simplification code
**Performance:** Similaire avec index appropriés

#### Requête 2: Seller stats (remplacer total_sales, total_revenue)

**Avant (dénormalisé dans users):**
```sql
SELECT seller_name, total_sales, total_revenue FROM users WHERE user_id = ?;
```

**Après (calcul dynamique):**
```sql
SELECT
    u.seller_name,
    COUNT(o.order_id) as total_sales,
    SUM(o.amount * 0.95) as total_revenue  -- 5% frais plateforme
FROM users u
LEFT JOIN orders o ON o.seller_user_id = u.telegram_id AND o.payment_status = 'completed'
WHERE u.telegram_id = ?
GROUP BY u.telegram_id;
```

**Impact:** Données toujours à jour, pas de maintenance triggers

#### Requête 3: Éviter N+1 queries (seller product carousel)

**Problème actuel (N+1):**
```python
products = product_repo.get_products_by_seller(seller_id)
for product in products:
    reviews_count = review_repo.count_reviews(product['product_id'])  # N queries!
    sales_count = order_repo.count_sales(product['product_id'])
```

**Solution optimisée:**
```sql
SELECT
    p.*,
    COUNT(DISTINCT r.id) as reviews_count,
    COUNT(DISTINCT o.order_id) as sales_count
FROM products p
LEFT JOIN reviews r ON r.product_id = p.product_id
LEFT JOIN orders o ON o.product_id = p.product_id AND o.payment_status = 'completed'
WHERE p.seller_user_id = ?
GROUP BY p.product_id
ORDER BY p.created_at DESC;
```

**Impact:** 1 requête au lieu de 1+N+N (énorme gain)

---

### 4.4 Méthodes repository manquantes

#### UserRepository

```python
# À AJOUTER dans app/domain/repositories/user_repo.py

def update_seller_email(self, user_id: int, new_email: str) -> bool:
    """Changer email vendeur"""
    conn = get_sqlite_connection(self.database_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            'UPDATE users SET seller_email = ?, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?',
            (new_email, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        return False
    finally:
        conn.close()

def update_solana_address(self, user_id: int, address: str) -> bool:
    """Changer adresse Solana"""
    conn = get_sqlite_connection(self.database_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            'UPDATE users SET solana_address = ?, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?',
            (address, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        return False
    finally:
        conn.close()

def deactivate_account(self, user_id: int) -> bool:
    """Désactiver compte utilisateur"""
    conn = get_sqlite_connection(self.database_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            'UPDATE users SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?',
            (user_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        return False
    finally:
        conn.close()

def get_seller_stats(self, seller_id: int) -> Optional[Dict]:
    """Obtenir stats vendeur (calculées dynamiquement)"""
    conn = get_sqlite_connection(self.database_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT
                u.seller_name,
                COUNT(DISTINCT p.product_id) as products_count,
                COUNT(DISTINCT o.order_id) as total_sales,
                SUM(o.amount * 0.95) as total_revenue,
                AVG(r.rating) as average_rating
            FROM users u
            LEFT JOIN products p ON p.seller_user_id = u.telegram_id
            LEFT JOIN orders o ON o.seller_user_id = u.telegram_id AND o.payment_status = 'completed'
            LEFT JOIN reviews r ON r.product_id = p.product_id
            WHERE u.telegram_id = ?
            GROUP BY u.telegram_id
        ''', (seller_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error:
        return None
    finally:
        conn.close()

def increment_products_purchased(self, user_id: int) -> bool:
    """Incrémenter compteur achats"""
    conn = get_sqlite_connection(self.database_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            'UPDATE users SET products_purchased_count = products_purchased_count + 1 WHERE telegram_id = ?',
            (user_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        return False
    finally:
        conn.close()
```

#### ProductRepository

```python
# À AJOUTER dans app/domain/repositories/product_repo.py

def update_short_description(self, product_id: str, seller_id: int, short_desc: str) -> bool:
    """Modifier description courte"""
    conn = get_sqlite_connection(self.database_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            'UPDATE products SET short_description = ?, updated_at = CURRENT_TIMESTAMP WHERE product_id = ? AND seller_user_id = ?',
            (short_desc, product_id, seller_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        return False
    finally:
        conn.close()

def suspend_product(self, product_id: str, seller_id: int) -> bool:
    """Suspendre produit"""
    conn = get_sqlite_connection(self.database_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            'UPDATE products SET is_suspended = 1, status = "suspended", updated_at = CURRENT_TIMESTAMP WHERE product_id = ? AND seller_user_id = ?',
            (product_id, seller_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        return False
    finally:
        conn.close()

def get_product_with_stats(self, product_id: str) -> Optional[Dict]:
    """Récupère produit avec stats calculées dynamiquement"""
    conn = get_sqlite_connection(self.database_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT
                p.*,
                u.seller_name,
                u.seller_bio,
                COALESCE(AVG(r.rating), 0.0) as rating,
                COUNT(DISTINCT r.id) as reviews_count,
                COUNT(DISTINCT o.order_id) as sales_count
            FROM products p
            LEFT JOIN users u ON p.seller_user_id = u.telegram_id
            LEFT JOIN reviews r ON r.product_id = p.product_id
            LEFT JOIN orders o ON o.product_id = p.product_id AND o.payment_status = 'completed'
            WHERE p.product_id = ?
            GROUP BY p.product_id
        ''', (product_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error:
        return None
    finally:
        conn.close()

def search_products(self, query: str, limit: int = 10) -> List[Dict]:
    """Recherche full-text dans titre + description"""
    conn = get_sqlite_connection(self.database_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        search_pattern = f'%{query}%'
        cursor.execute('''
            SELECT p.*,
                   COUNT(DISTINCT o.order_id) as sales_count
            FROM products p
            LEFT JOIN orders o ON o.product_id = p.product_id AND o.payment_status = 'completed'
            WHERE (p.title LIKE ? OR p.full_description LIKE ?)
              AND p.status = 'active'
            GROUP BY p.product_id
            ORDER BY sales_count DESC
            LIMIT ?
        ''', (search_pattern, search_pattern, limit))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error:
        return []
    finally:
        conn.close()
```

#### OrderRepository

```python
# À AJOUTER dans app/domain/repositories/order_repo.py

def get_orders_by_category(self, category_id: int) -> List[Dict]:
    """Filtrer commandes par catégorie"""
    conn = get_sqlite_connection(self.database_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(
            'SELECT * FROM orders WHERE category_id = ? ORDER BY created_at DESC',
            (category_id,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error:
        return []
    finally:
        conn.close()

def get_recent_orders(self, limit: int = 10) -> List[Dict]:
    """Dernières commandes toutes catégories"""
    conn = get_sqlite_connection(self.database_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(
            'SELECT * FROM orders ORDER BY created_at DESC LIMIT ?',
            (limit,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error:
        return []
    finally:
        conn.close()

def update_transaction_hash(self, order_id: str, tx_hash: str) -> bool:
    """Ajouter hash blockchain"""
    conn = get_sqlite_connection(self.database_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            'UPDATE orders SET transaction_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE order_id = ?',
            (tx_hash, order_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        return False
    finally:
        conn.close()
```

#### ReviewRepository (À CRÉER ENTIÈREMENT)

```python
# NOUVEAU FICHIER: app/domain/repositories/review_repo.py

import sqlite3
from typing import Optional, Dict, List
from app.core import get_sqlite_connection, settings as core_settings

class ReviewRepository:
    def __init__(self, database_path: Optional[str] = None) -> None:
        self.database_path = database_path or core_settings.DATABASE_PATH

    def add_review(self, product_id: str, buyer_id: int, order_id: str, rating: int, comment: str) -> bool:
        """Ajouter un avis"""
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO reviews (product_id, buyer_user_id, order_id, rating, comment) VALUES (?, ?, ?, ?, ?)',
                (product_id, buyer_id, order_id, rating, comment)
            )
            conn.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            conn.close()

    def get_reviews_by_product(self, product_id: str, page: int = 1, per_page: int = 5) -> List[Dict]:
        """Récupérer avis d'un produit avec pagination"""
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            offset = (page - 1) * per_page
            cursor.execute('''
                SELECT r.*, u.username
                FROM reviews r
                LEFT JOIN users u ON r.buyer_user_id = u.telegram_id
                WHERE r.product_id = ?
                ORDER BY r.created_at DESC
                LIMIT ? OFFSET ?
            ''', (product_id, per_page, offset))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    def can_user_review(self, buyer_id: int, product_id: str) -> bool:
        """Vérifier si user a acheté le produit et peut laisser avis"""
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            # Vérifier achat validé
            cursor.execute(
                'SELECT COUNT(*) FROM orders WHERE buyer_user_id = ? AND product_id = ? AND payment_status = "completed"',
                (buyer_id, product_id)
            )
            purchased = cursor.fetchone()[0] > 0

            # Vérifier pas déjà reviewé
            cursor.execute(
                'SELECT COUNT(*) FROM reviews WHERE buyer_user_id = ? AND product_id = ?',
                (buyer_id, product_id)
            )
            already_reviewed = cursor.fetchone()[0] > 0

            return purchased and not already_reviewed
        except sqlite3.Error:
            return False
        finally:
            conn.close()

    def get_average_rating(self, product_id: str) -> float:
        """Calculer rating moyen d'un produit"""
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT AVG(rating) FROM reviews WHERE product_id = ?',
                (product_id,)
            )
            result = cursor.fetchone()[0]
            return float(result) if result else 0.0
        except sqlite3.Error:
            return 0.0
        finally:
            conn.close()

    def count_reviews(self, product_id: str) -> int:
        """Compter nombre d'avis d'un produit"""
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT COUNT(*) FROM reviews WHERE product_id = ?',
                (product_id,)
            )
            return cursor.fetchone()[0]
        except sqlite3.Error:
            return 0
        finally:
            conn.close()
```

---

## 5. PLAN DE MIGRATION

### Phase 1: Audit complet

- [ ] **Backup database actuelle**
  ```bash
  cp marketplace_database.db marketplace_database.backup_$(date +%Y%m%d_%H%M%S).db
  ```

- [ ] **Documenter toutes les tables existantes**
  ```sql
  SELECT name FROM sqlite_master WHERE type='table';
  ```

- [ ] **Vérifier intégrité données**
  ```sql
  PRAGMA integrity_check;
  ```

- [ ] **Compter rows par table**
  ```sql
  SELECT 'users' as table_name, COUNT(*) as row_count FROM users
  UNION ALL
  SELECT 'products', COUNT(*) FROM products
  UNION ALL
  SELECT 'orders', COUNT(*) FROM orders
  UNION ALL
  SELECT 'reviews', COUNT(*) FROM reviews;
  ```

- [ ] **Identifier données critiques à préserver**
  - Users avec is_seller=1
  - Products avec status='active'
  - Orders avec payment_status='completed'
  - Reviews existants

---

### Phase 2: Migrations schéma (SANS PERTE DE DONNÉES)

**Ordre d'exécution recommandé:**

1. [ ] **Migration 9: Supprimer tables obsolètes** (pas de dépendances)
   - `wallet_transactions`
   - `id_counters`

2. [ ] **Migration 10: Supprimer triggers rating** (simplification)
   - `update_rating_after_insert`
   - `update_rating_after_update`
   - `update_rating_after_delete`

3. [ ] **Migration 5: Categories (simple)** - Ajouter slug + created_at

4. [ ] **Migration 1: Users (critique!)** - Renommer user_id → telegram_id

5. [ ] **Migration 2: Products (après users)** - Dépend de users

6. [ ] **Migration 3: Orders (après products)** - Dépend de products + users

7. [ ] **Migration 4: Reviews (après orders)** - Dépend de orders

8. [ ] **Migration 6: Payouts (après users)** - Dépend de users

9. [ ] **Migration 7: Support tickets (simple)** - Simplification

10. [ ] **Migration 8: Messages (après tickets)** - Dépend de support_tickets

---

### Phase 3: Adaptation repositories

- [ ] **Mettre à jour UserRepository**
  - Renommer toutes références `user_id` → `telegram_id`
  - Ajouter méthodes manquantes (update_seller_email, etc.)

- [ ] **Mettre à jour ProductRepository**
  - Renommer `description` → `full_description`
  - Renommer `main_file_path` → `file_url`
  - Remplacer requêtes avec sales_count/rating dénormalisés par JOINs
  - Ajouter méthodes manquantes (suspend_product, etc.)

- [ ] **Mettre à jour OrderRepository**
  - Renommer `product_price_eur` → `amount`
  - Supprimer références à champs obsolètes (nowpayments_id, etc.)
  - Ajouter méthodes manquantes

- [ ] **Créer ReviewRepository**
  - Implémenter toutes les méthodes nécessaires
  - Tester cas edge (user pas acheté, déjà reviewé, etc.)

- [ ] **Mettre à jour PayoutRepository**
  - Adapter au nouveau schéma `payouts`

- [ ] **Mettre à jour TicketRepository + MessagingRepository**
  - Adapter au schéma simplifié

---

### Phase 4: Validation

- [ ] **Tests unitaires repositories**
  ```python
  pytest tests/test_repos.py -v
  ```

- [ ] **Tests d'intégration workflows**
  ```python
  pytest tests/test_buyer_workflow.py -v
  pytest tests/test_seller_workflow.py -v
  ```

- [ ] **Vérification contraintes respectées**
  ```sql
  -- Vérifier FK intégrité
  PRAGMA foreign_key_check;

  -- Vérifier UNIQUE constraints
  SELECT product_id, COUNT(*) FROM products GROUP BY product_id HAVING COUNT(*) > 1;
  ```

- [ ] **Performance benchmarks**
  ```python
  # Tester requêtes avec EXPLAIN QUERY PLAN
  cursor.execute('EXPLAIN QUERY PLAN SELECT * FROM products WHERE category_id = 1')
  ```

- [ ] **Validation données migrées**
  ```sql
  -- Comparer counts avant/après
  SELECT COUNT(*) FROM users;  -- Doit être identique
  SELECT COUNT(*) FROM products;
  SELECT COUNT(*) FROM orders;
  ```

---

## 6. RISQUES ET PRÉCAUTIONS

### Risques identifiés

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| **Perte de données pendant migration** | Moyenne | Critique | Backup complet avant toute opération |
| **Downtime pendant migration** | Élevée | Moyen | Migration en heures creuses, notifications users |
| **Foreign Keys cassées** | Faible | Élevé | Vérifier PRAGMA foreign_key_check après chaque migration |
| **Requêtes cassées dans code** | Élevée | Élevé | Tests exhaustifs après chaque changement repository |
| **Contraintes UNIQUE bloquant insertions** | Moyenne | Moyen | Vérifier doublons avant migration |
| **Performances dégradées** | Faible | Moyen | Ajouter index appropriés, benchmarks avant/après |
| **Triggers manquants** | Faible | Faible | Vérifier que logique métier est dans code, pas DB |

---

### Précautions recommandées

#### 1. Backup Strategy (CRITIQUE)

```bash
# Script backup automatique
#!/bin/bash
BACKUP_DIR="/backups/marketplace_db"
DATE=$(date +%Y%m%d_%H%M%S)
DB_PATH="marketplace_database.db"

# Backup complet
cp $DB_PATH "$BACKUP_DIR/marketplace_$DATE.db"

# Backup SQL dump (plus sûr)
sqlite3 $DB_PATH .dump > "$BACKUP_DIR/marketplace_$DATE.sql"

# Vérifier intégrité backup
sqlite3 "$BACKUP_DIR/marketplace_$DATE.db" "PRAGMA integrity_check;"

echo "✅ Backup créé: marketplace_$DATE.db"
```

#### 2. Rollback Plan

**En cas d'échec de migration:**

```bash
# Restaurer backup
cp /backups/marketplace_db/marketplace_YYYYMMDD_HHMMSS.db marketplace_database.db

# Ou restaurer depuis SQL dump
sqlite3 marketplace_database.db < /backups/marketplace_db/marketplace_YYYYMMDD_HHMMSS.sql
```

**Critères de rollback:**
- Perte de données détectée (count mismatch)
- Erreurs FK integrity
- Tests critiques échouent
- Performances dégradées > 50%

#### 3. Migration Progressive

**Ne PAS tout migrer d'un coup!**

Plan recommandé:
1. **Semaine 1:** Migrations tables simples (categories, payouts, support)
2. **Semaine 2:** Migration users (critique!)
3. **Semaine 3:** Migration products (critique!)
4. **Semaine 4:** Migration orders + reviews
5. **Semaine 5:** Tests exhaustifs + optimisations

#### 4. Tests en Environnement Dev

**JAMAIS migrer directement en production!**

```bash
# Créer copie DB pour tests
cp marketplace_database.db marketplace_database.TEST.db

# Exécuter migrations sur copie
python migrate_database.py --db-path marketplace_database.TEST.db

# Tester workflows
pytest tests/ --db-path marketplace_database.TEST.db

# Si OK → migrer production
```

#### 5. Monitoring Post-Migration

**Surveiller pendant 48h après migration:**
- Logs erreurs DB
- Performance requêtes (ajouter logging temps exécution)
- Nombre erreurs users (tickets support)
- Métriques conversions (pas de chute brutale)

```python
# Exemple logging performance
import time
import logging

def log_query_performance(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        if duration > 1.0:  # Alerte si > 1s
            logging.warning(f"Slow query: {func.__name__} took {duration:.2f}s")
        return result
    return wrapper
```

---

## 7. CHECKLIST VALIDATION

### Avant implémentation des changements DB:

- [ ] **Schéma cible validé et cohérent**
  - Toutes les tables ont PRIMARY KEY
  - Tous les FOREIGN KEY sont valides
  - Contraintes CHECK appropriées
  - Pas de redondance inutile

- [ ] **Toutes les tables existantes analysées**
  - 10 tables actuelles documentées
  - Différences identifiées (OK/Rename/Add/Obsolete)
  - Impacts sur code évalués

- [ ] **Migrations SQL écrites et testées**
  - 10 migrations écrites
  - Testées sur copie DB
  - Ordre d'exécution validé
  - Rollback plan documenté

- [ ] **Repositories mis à jour**
  - UserRepository adapté (user_id → telegram_id)
  - ProductRepository adapté (suppression dénormalisation)
  - OrderRepository adapté
  - ReviewRepository créé
  - PayoutRepository adapté
  - TicketRepository + MessagingRepository adaptés

- [ ] **Tests unitaires écrits**
  - Tests pour chaque méthode repository
  - Tests contraintes DB (UNIQUE, FK, CHECK)
  - Tests edge cases (valeurs NULL, doublons, etc.)

- [ ] **Backup DB créé**
  - Backup fichier .db
  - Backup SQL dump
  - Intégrité vérifiée
  - Stocké en lieu sûr

- [ ] **Plan de rollback documenté**
  - Script restore backup
  - Critères de rollback définis
  - Procédure testée

- [ ] **Performance validée (pas de régression)**
  - Benchmarks avant/après migration
  - Index appropriés ajoutés
  - Requêtes lentes identifiées et optimisées

---

## 📊 RÉCAPITULATIF FINAL

### Tables à MODIFIER (8)

1. ✅ `users` - Renommer clé, ajouter champs, supprimer obsolètes
2. ✅ `products` - Renommer champs, supprimer dénormalisation
3. ✅ `orders` - Renommer champs, supprimer NowPayments details
4. ✅ `reviews` - Fusionner champs, changer contrainte UNIQUE
5. ✅ `categories` - Ajouter slug + created_at
6. ✅ `seller_payouts` → `payouts` - Renommer table + champs
7. ✅ `support_tickets` - Simplifier (supprimer champs métier)
8. ✅ `support_messages` → `messages` - Renommer table

### Tables à SUPPRIMER (2)

1. ❌ `wallet_transactions` - Redondante
2. ❌ `id_counters` - Utilité limitée

### Tables à CONSERVER TELLES QUELLES (1)

1. ✅ `telegram_mappings` - Structure optimale, pas de modification

### Triggers à SUPPRIMER (3)

1. ❌ `update_rating_after_insert`
2. ❌ `update_rating_after_update`
3. ❌ `update_rating_after_delete`

### Repositories à CRÉER (1)

1. ➕ `ReviewRepository` - Nouvelle classe complète

### Repositories à METTRE À JOUR (6)

1. 🔄 `UserRepository` - +6 méthodes
2. 🔄 `ProductRepository` - +5 méthodes
3. 🔄 `OrderRepository` - +3 méthodes
4. 🔄 `PayoutRepository` - Adapter au nouveau schéma
5. 🔄 `TicketRepository` - Simplification
6. 🔄 `MessagingRepository` - Adaptation

---

## ✅ PROCHAINE ÉTAPE

**📋 VALIDATION DÉVELOPPEUR REQUISE**

Ce document contient:
- ✅ Schéma cible complet
- ✅ Analyse exhaustive existant
- ✅ Comparaison détaillée (anti-doublon)
- ✅ 10 migrations SQL prêtes
- ✅ Méthodes repository manquantes identifiées
- ✅ Plan de migration en 4 phases
- ✅ Gestion des risques
- ✅ Checklist validation

**❌ AUCUNE MODIFICATION N'A ÉTÉ FAITE** sur la base de données actuelle.

**Avant de procéder:**
1. Relire ce document en entier
2. Valider ou modifier le schéma cible
3. Confirmer l'ordre des migrations
4. Donner GO pour implémentation

---

**Statut:** 📋 **EN ATTENTE DE VALIDATION DÉVELOPPEUR**
