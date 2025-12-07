# Plan de Migration : Presigned URLs + Telegram Mini App

**Date:** 5 décembre 2025
**Objectif:** Gérer les fichiers volumineux (10 GB+) sans crash Railway (512 Mo RAM)
**Contraintes:** Backblaze B2 (S3-compatible), Telegram Bot, Railway hosting
**Design Inspiration:** ferus-landing/index.html

---

## 📋 Table des Matières

1. [Contexte & Problématique](#1-contexte--problématique)
2. [Architecture Cible](#2-architecture-cible)
3. [Phase 1: Fixes Critiques (Presigned URLs)](#3-phase-1-fixes-critiques-presigned-urls)
4. [Phase 2: Preview Feature Fix](#4-phase-2-preview-feature-fix)
5. [Phase 3: Telegram Mini App](#5-phase-3-telegram-mini-app)
6. [Phase 4: Testing & Deployment](#6-phase-4-testing--deployment)
7. [Annexes](#7-annexes)

---

## 1. Contexte & Problématique

### 1.1 Problème Actuel

**Railway crash avec fichiers >500 MB** à cause du workflow actuel :

```
┌─────────────────────────────────────────────────────────┐
│ WORKFLOW ACTUEL (❌ CRASH RAILWAY)                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Backblaze B2 ──┐                                       │
│                 │                                       │
│                 ▼                                       │
│           ┌──────────┐                                  │
│           │ Railway  │  ← Download ENTIER fichier 5 GB │
│           │ 512 Mo   │  ← OOM CRASH 💥                 │
│           └────┬─────┘                                  │
│                │                                        │
│                ▼                                        │
│         Telegram User  ← send_document()               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Points de crash identifiés:**

1. **Library download** (`library_handlers.py:266-327`)
2. **Post-payment delivery** (`buy_handlers.py:1663-1700`)
3. **Preview generation** (`buy_handlers.py:1972-2138`) - Download ENTIER fichier pour créer aperçu
4. **Retry cronjob** (`retry_undelivered_files.py`) - Appelle fonction manquante

---

### 1.2 Solution : Presigned URLs

**Presigned URL** = Lien temporaire signé qui permet téléchargement DIRECT depuis B2.

```
┌─────────────────────────────────────────────────────────┐
│ WORKFLOW CIBLE (✅ PAS DE CRASH)                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Backblaze B2 ────────────────────┐                    │
│                                   │                    │
│                                   │                    │
│           ┌──────────┐            │                    │
│           │ Railway  │  ← Generate Presigned URL (1 KB)│
│           │ 512 Mo   │  ← NO OOM ✅                    │
│           └────┬─────┘                                  │
│                │                                        │
│                ▼                                        │
│         Telegram User                                  │
│                │                                        │
│                │  Click link                            │
│                ▼                                        │
│         Download DIRECT from B2 ───────────────────────┘│
│         (bypass Railway completely)                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Avantages:**
- ✅ Railway ne touche JAMAIS le fichier (utilisation RAM < 1 MB)
- ✅ Vitesse max (download direct depuis B2 → User)
- ✅ Aucune limite de taille fichier (10 GB, 1 TB...)
- ✅ Code déjà implémenté (mais inutilisé) : `get_b2_presigned_url()` existe

---

## 2. Architecture Cible

### 2.1 Flows Modifiés

```
┌───────────────────────────────────────────────────────────────────┐
│ UPLOAD VENDOR (déjà OK - fichier temporaire <10s)                │
├───────────────────────────────────────────────────────────────────┤
│ Telegram → Railway temp file → B2 upload → Delete temp           │
│ ✅ Pas de changement nécessaire                                   │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│ LIBRARY DOWNLOAD (FIX CRITIQUE)                                  │
├───────────────────────────────────────────────────────────────────┤
│ AVANT: B2 → Railway download → send_document()                   │
│ APRÈS: B2 → Generate Presigned URL → send_message(URL)           │
│                                                                   │
│ 📁 library_handlers.py:266-327                                    │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│ POST-PAYMENT DELIVERY (FIX CRITIQUE)                             │
├───────────────────────────────────────────────────────────────────┤
│ AVANT: B2 → Railway download → reply_document()                  │
│ APRÈS: B2 → Generate Presigned URL → send_message(URL)           │
│                                                                   │
│ 📁 buy_handlers.py:1663-1700                                      │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│ PREVIEW FEATURE (FIX CRITIQUE)                                   │
├───────────────────────────────────────────────────────────────────┤
│ AVANT: Download ENTIER fichier → PyMuPDF/ffmpeg → Aperçu         │
│ APRÈS: Désactiver si >100 MB (quick fix)                         │
│        OU Pre-generate preview au moment upload vendeur           │
│                                                                   │
│ 📁 buy_handlers.py:1972-2138                                      │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│ RETRY CRONJOB (FIX MANQUANT)                                     │
├───────────────────────────────────────────────────────────────────┤
│ AVANT: Appelle send_formation_to_buyer() (MISSING FUNCTION)      │
│ APRÈS: Implémenter fonction avec Presigned URLs                  │
│                                                                   │
│ 📁 app/integrations/ipn_server.py (nouvelle fonction)            │
└───────────────────────────────────────────────────────────────────┘
```

---

### 2.2 Fonctions Existantes (Déjà Codées)

**app/core/file_utils.py:183-209**
```python
def get_b2_presigned_url(b2_url: str, expires_in: int = 3600) -> Optional[str]:
    """
    Get a presigned URL for direct download from B2
    ✅ DÉJÀ IMPLÉMENTÉ - JAMAIS UTILISÉ
    """
```

**app/services/b2_storage_service.py:142-165**
```python
def get_download_url(self, object_key: str, expires_in: int = 3600) -> Optional[str]:
    """Generate a presigned URL for downloading a file"""
    ✅ DÉJÀ IMPLÉMENTÉ - UTILISE BOTO3 generate_presigned_url
```

**Conclusion:** La solution technique existe, il suffit de **l'utiliser**.

---

## 3. Phase 1: Fixes Critiques (Presigned URLs)

### 3.1 Library Download Fix

**Fichier:** `app/integrations/telegram/handlers/library_handlers.py`
**Lignes:** 266-327
**Durée estimée:** 10 minutes

#### Code Actuel (❌ CRASH):
```python
# LINES 266-327
from app.core.file_utils import download_product_file_from_b2

local_path = await download_product_file_from_b2(b2_file_url, product_id)

if not local_path or not os.path.exists(local_path):
    # Error handling...

with open(full_file_path, 'rb') as file:
    await bot_instance.send_document(
        chat_id=query.message.chat_id,
        document=file,
    )

os.remove(local_path)  # Cleanup
```

#### Code Cible (✅ NO CRASH):
```python
# NOUVELLE IMPLÉMENTATION
from app.core.file_utils import get_b2_presigned_url
from app.core.utils import logger

# Générer Presigned URL (1 KB RAM, pas de download)
presigned_url = get_b2_presigned_url(b2_file_url, expires_in=86400)  # 24h

if not presigned_url:
    logger.error(f"Failed to generate presigned URL: {b2_file_url}")
    await safe_transition_to_text(
        query,
        "❌ Download link generation failed. Contact support." if lang == 'en'
        else "❌ Échec de génération du lien. Contactez le support.",
        InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "🆘 Support" if lang == 'en' else "🆘 Support",
                callback_data='support_menu'
            ),
            InlineKeyboardButton(
                "🔙 Back" if lang == 'en' else "🔙 Retour",
                callback_data='library_menu'
            )
        ]])
    )
    return

# Envoyer message avec lien de téléchargement
download_message = (
    f"📥 **{product_title}**\n\n"
    f"🔗 **Download link** (valid 24h):\n{presigned_url}\n\n"
    f"💡 Click the link to download your file directly."
) if lang == 'en' else (
    f"📥 **{product_title}**\n\n"
    f"🔗 **Lien de téléchargement** (valide 24h):\n{presigned_url}\n\n"
    f"💡 Cliquez sur le lien pour télécharger votre fichier directement."
)

await query.message.reply_text(
    download_message,
    parse_mode='Markdown',
    reply_markup=InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🔙 Retour à ma bibliothèque" if lang == 'fr' else "🔙 Back to my library",
            callback_data='library_menu'
        )
    ]])
)

logger.info(f"✅ Presigned URL sent to user {query.from_user.id} for product {product_id}")
```

**Changements:**
1. Remplacer `download_product_file_from_b2()` par `get_b2_presigned_url()`
2. Supprimer tout le bloc `with open() / send_document() / os.remove()`
3. Envoyer message texte avec URL au lieu de fichier attaché
4. Expiration 24h (86400 secondes) - customizable

---

### 3.2 Post-Payment Delivery Fix

**Fichier:** `app/integrations/telegram/handlers/buy_handlers.py`
**Lignes:** 1663-1700
**Durée estimée:** 10 minutes

#### Code Actuel (❌ CRASH):
```python
# LINES 1663-1700
from app.core.file_utils import download_product_file_from_b2

local_path = await download_product_file_from_b2(file_url, order['product_id'])

if local_path and os.path.exists(local_path):
    with open(local_path, 'rb') as file:
        await query.message.reply_document(
            document=file,
            caption=f"📚 **{product_title}**\n\n✅ Téléchargement réussi !...",
            parse_mode='Markdown'
        )
        file_sent = True

        # Mark as delivered
        cursor.execute('''UPDATE orders SET file_delivered = TRUE,
                         download_count = download_count + 1
                         WHERE order_id = %s''', (order_id,))
        conn.commit()

    os.remove(local_path)
```

#### Code Cible (✅ NO CRASH):
```python
# NOUVELLE IMPLÉMENTATION
from app.core.file_utils import get_b2_presigned_url

# Générer Presigned URL
presigned_url = get_b2_presigned_url(file_url, expires_in=86400)  # 24h

if presigned_url:
    delivery_message = (
        f"📚 **{product_title}**\n\n"
        f"✅ Payment confirmed!\n\n"
        f"🔗 **Download link** (valid 24h):\n{presigned_url}\n\n"
        f"💡 Save this file safely - you can re-download from your Library."
    ) if buyer_lang == 'en' else (
        f"📚 **{product_title}**\n\n"
        f"✅ Paiement confirmé !\n\n"
        f"🔗 **Lien de téléchargement** (valide 24h):\n{presigned_url}\n\n"
        f"💡 Conservez ce fichier précieusement - vous pouvez re-télécharger depuis votre Bibliothèque."
    )

    await query.message.reply_text(
        delivery_message,
        parse_mode='Markdown'
    )
    file_sent = True

    # Mark as delivered
    cursor.execute('''UPDATE orders SET file_delivered = TRUE,
                     download_count = download_count + 1
                     WHERE order_id = %s''', (order_id,))
    conn.commit()

    logger.info(f"✅ Presigned URL sent to buyer {query.from_user.id} for order {order_id}")
else:
    logger.error(f"❌ Failed to generate presigned URL for order {order_id}")
    file_sent = False
```

**Changements:**
1. Remplacer `download_product_file_from_b2()` par `get_b2_presigned_url()`
2. Supprimer `with open() / reply_document() / os.remove()`
3. Envoyer `reply_text()` au lieu de `reply_document()`
4. Conserver la logique DB (mark as delivered)

---

### 3.3 Implémenter send_formation_to_buyer()

**Fichier:** `app/integrations/ipn_server.py`
**Fonction:** NOUVELLE (actuellement manquante)
**Durée estimée:** 15 minutes

**Contexte:** Fonction référencée dans `retry_undelivered_files.py:79-84` mais n'existe PAS.

#### Code à Ajouter:
```python
async def send_formation_to_buyer(buyer_user_id: int, order_id: str, product_id: str, payment_id: str):
    """
    Envoie le fichier formation à l'acheteur via Presigned URL

    Utilisé par:
    - Cronjob retry_undelivered_files.py
    - Webhook IPN fallback
    """
    from app.core.file_utils import get_b2_presigned_url
    from app.domain.repositories.product_repo import ProductRepository
    from app.domain.repositories.order_repo import OrderRepository
    from app.domain.repositories.user_repo import UserRepository
    from app.core.utils import logger

    product_repo = ProductRepository()
    order_repo = OrderRepository()
    user_repo = UserRepository()

    try:
        # Récupérer product info
        product = product_repo.get_product_by_id(product_id)
        if not product:
            logger.error(f"Product not found: {product_id}")
            return False

        # Récupérer main file URL from B2
        main_file_url = product.get('main_file_url')
        if not main_file_url:
            logger.error(f"No main_file_url for product {product_id}")
            return False

        # Générer Presigned URL
        presigned_url = get_b2_presigned_url(main_file_url, expires_in=86400)  # 24h
        if not presigned_url:
            logger.error(f"Failed to generate presigned URL for {product_id}")
            return False

        # Récupérer buyer language
        buyer_data = user_repo.get_user(buyer_user_id)
        buyer_lang = buyer_data['language_code'] if buyer_data else 'fr'

        # Message de livraison
        product_title = product.get('title', 'Formation')
        delivery_message = (
            f"📚 **{product_title}**\n\n"
            f"✅ Payment confirmed (Order #{order_id})\n\n"
            f"🔗 **Download link** (valid 24h):\n{presigned_url}\n\n"
            f"💡 You can re-download from your Library anytime."
        ) if buyer_lang == 'en' else (
            f"📚 **{product_title}**\n\n"
            f"✅ Paiement confirmé (Commande #{order_id})\n\n"
            f"🔗 **Lien de téléchargement** (valide 24h):\n{presigned_url}\n\n"
            f"💡 Vous pouvez re-télécharger depuis votre Bibliothèque à tout moment."
        )

        # Envoyer via Telegram bot
        from app.main import application  # Import bot instance
        await application.bot.send_message(
            chat_id=buyer_user_id,
            text=delivery_message,
            parse_mode='Markdown'
        )

        # Mark as delivered
        order_repo.mark_order_delivered(order_id)

        logger.info(f"✅ Formation delivered to buyer {buyer_user_id} for order {order_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Error sending formation to buyer {buyer_user_id}: {e}")
        return False
```

**Ajouts nécessaires:**

1. **Dans OrderRepository** (`app/domain/repositories/order_repo.py`) :
```python
def mark_order_delivered(self, order_id: str) -> bool:
    """Mark order as delivered and increment download count"""
    conn = db_pool.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE orders
            SET file_delivered = TRUE,
                download_count = download_count + 1,
                delivered_at = NOW()
            WHERE order_id = %s
        ''', (order_id,))
        conn.commit()
        return True
    finally:
        db_pool.put_connection(conn)
```

---

## 4. Phase 2: Preview Feature Fix

**Fichier:** `app/integrations/telegram/handlers/buy_handlers.py`
**Lignes:** 1972-2138
**Durée estimée:** 20 minutes

### Problème Actuel

Preview download ENTIER fichier pour générer aperçu:

```python
# ACTUEL (❌ CRASH si fichier >500 MB)
full_path = await download_product_file_from_b2(main_file_url, product_id)

# PyMuPDF charge TOUT le PDF en RAM
doc = fitz.open(full_path)

# ffmpeg traite TOUTE la vidéo
subprocess.run(['ffmpeg', '-i', full_path, ...])

# zipfile lit TOUT l'archive
with zipfile.ZipFile(full_path, 'r') as zip_ref:
```

### Solutions

#### Option A: Quick Fix (Désactiver >100 MB)

```python
# Vérifier taille fichier AVANT download
from app.services.b2_storage_service import B2StorageService
b2_service = B2StorageService()

# Extract object_key from B2 URL
object_key = main_file_url.split(f"/{settings.B2_BUCKET_NAME}/")[1]

# Check file size via HEAD request (pas de download)
file_size = b2_service.get_file_size(object_key)  # Nouvelle méthode

if file_size > 100 * 1024 * 1024:  # 100 MB
    await query.answer("⚠️ Preview unavailable (file too large)" if lang == 'en'
                      else "⚠️ Aperçu indisponible (fichier trop volumineux)")
    return

# Sinon, preview normal
full_path = await download_product_file_from_b2(main_file_url, product_id)
# ... existing preview logic
```

**Nouvelle méthode B2StorageService:**
```python
# app/services/b2_storage_service.py

def get_file_size(self, object_key: str) -> Optional[int]:
    """Get file size WITHOUT downloading (HEAD request)"""
    if not self.client:
        return None

    try:
        response = self.client.head_object(
            Bucket=self.bucket_name,
            Key=object_key
        )
        return response['ContentLength']
    except Exception as e:
        logger.error(f"Failed to get file size: {e}")
        return None
```

#### Option B: Pre-generate Previews (Solution Complète)

**Workflow:**
1. Lors upload vendeur → Générer preview IMMÉDIATEMENT
2. Stocker preview sur B2 : `previews/{product_id}/thumb.jpg`
3. Lors click "Aperçu" → Envoyer preview depuis B2 (fichier <1 MB)

**Implémentation:**

```python
# app/services/preview_service.py (NOUVEAU FICHIER)

async def generate_and_upload_preview(product_id: str, file_path: str, file_type: str):
    """
    Generate preview and upload to B2 during vendor upload

    Args:
        product_id: Product ID
        file_path: Local temp file path
        file_type: 'pdf', 'video', 'zip', etc.
    """
    from app.services.b2_storage_service import B2StorageService
    b2_service = B2StorageService()

    preview_path = None

    try:
        if file_type == 'pdf':
            # Generate PDF preview (first page)
            import fitz
            doc = fitz.open(file_path)
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            preview_path = f"/tmp/{product_id}_preview.jpg"
            pix.save(preview_path)
            doc.close()

        elif file_type == 'video':
            # Generate video thumbnail (first frame)
            preview_path = f"/tmp/{product_id}_preview.jpg"
            subprocess.run([
                'ffmpeg', '-i', file_path,
                '-ss', '00:00:01',
                '-vframes', '1',
                preview_path
            ], check=True)

        elif file_type == 'zip':
            # Generate ZIP file list
            import zipfile
            preview_path = f"/tmp/{product_id}_preview.txt"
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                file_list = '\n'.join(zip_ref.namelist()[:50])  # First 50 files
                with open(preview_path, 'w') as f:
                    f.write(file_list)

        # Upload preview to B2
        if preview_path and os.path.exists(preview_path):
            preview_b2_key = f"previews/{product_id}/preview.{preview_path.split('.')[-1]}"
            preview_url = await b2_service.upload_file(preview_path, preview_b2_key)

            # Cleanup temp preview
            os.remove(preview_path)

            return preview_url

        return None

    except Exception as e:
        logger.error(f"Preview generation failed: {e}")
        if preview_path and os.path.exists(preview_path):
            os.remove(preview_path)
        return None
```

**Modifications sell_handlers.py:**
```python
# Après upload du main_file vers B2
from app.services.preview_service import generate_and_upload_preview

preview_url = await generate_and_upload_preview(product_id, local_file_path, file_type)

# Sauvegarder preview_url en DB
product_repo.update_product_preview(product_id, preview_url)
```

**Modifications buy_handlers.py (preview display):**
```python
# AVANT: Download entire file
# APRÈS: Get preview from B2 (small file)

preview_url = product.get('preview_url')
if preview_url:
    # Download preview (small <1 MB)
    preview_path = await download_product_file_from_b2(preview_url, product_id)

    with open(preview_path, 'rb') as preview_file:
        await query.message.reply_photo(photo=preview_file)

    os.remove(preview_path)
```

**Recommandation:** Utiliser **Option A** (quick fix) pour déploiement immédiat, puis implémenter **Option B** progressivement.

---

## 5. Phase 3: Telegram Mini App

**Durée estimée:** 2-3 heures
**Design:** Inspiré de `ferus-landing/index.html`

### 5.1 Architecture Mini App

```
┌─────────────────────────────────────────────────────────┐
│ TELEGRAM MINI APP - Upload Flow                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 1. Vendeur clique "Vendre formation"                   │
│    → Bot envoie WebApp button                          │
│                                                         │
│ 2. Mini App s'ouvre (HTML/JS in Telegram)              │
│    → Interface moderne avec barre de progression       │
│                                                         │
│ 3. Vendeur sélectionne fichier (10 GB+)                │
│    → Presigned Upload URL générée par Railway          │
│                                                         │
│ 4. Upload DIRECT Browser → B2 (bypass Railway)         │
│    → Barre de progression en temps réel                │
│                                                         │
│ 5. Upload terminé → Callback Bot                       │
│    → Finaliser création produit                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Design System (Ferus-Inspired)

**Design tokens extraits de `ferus-landing/index.html`:**

```css
/* Variables CSS from ferus-landing */
:root {
    /* Colors */
    --purple-vibrant: #8b5cf6;
    --purple-accent: #8b5cf6;
    --purple-glow: #a78bfa;
    --purple-deep: #7c3aed;
    --purple-soft: #e9d5ff;

    --orange-vivid: #f59e0b;
    --cyan-vivid: #06b6d4;
    --pink-vivid: #ec4899;

    /* Backgrounds */
    --bg-white: #fafbfc;
    --bg-light: #f3f4f6;
    --bg-gray-subtle: #e5e7eb;

    /* Text */
    --text-black: #1e293b;
    --text-dark: #334155;
    --text-gray: #64748b;
    --text-light: #94a3b8;

    /* Shadows */
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.03);
    --shadow-md: 0 4px 6px rgba(0,0,0,0.04), 0 2px 4px rgba(0,0,0,0.03);
    --shadow-lg: 0 10px 15px rgba(0,0,0,0.05), 0 4px 6px rgba(0,0,0,0.03);
    --shadow-purple: 0 10px 40px rgba(139, 92, 246, 0.12);
}

/* Typography */
h1, h2, h3, h4 {
    line-height: 1.25;
    font-weight: 900;
    letter-spacing: -0.02em;
    color: var(--text-black);
}
```

### 5.3 Fichiers à Créer

#### 5.3.1 static/upload.html

**Emplacement:** `app/integrations/telegram/static/upload.html`

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Upload Formation</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="header">
            <h1 class="title">📤 Upload Formation</h1>
            <p class="subtitle">Fichiers jusqu'à 10 GB acceptés</p>
        </header>

        <!-- Upload Area -->
        <div id="uploadArea" class="upload-area">
            <div class="upload-icon">📁</div>
            <h2 class="upload-title">Glissez votre fichier ici</h2>
            <p class="upload-description">ou cliquez pour sélectionner</p>
            <input type="file" id="fileInput" class="file-input" />
            <button class="btn-primary" onclick="document.getElementById('fileInput').click()">
                Sélectionner un fichier
            </button>
        </div>

        <!-- Progress Section (hidden initially) -->
        <div id="progressSection" class="progress-section hidden">
            <h3 class="progress-title">Upload en cours...</h3>

            <div class="progress-bar-container">
                <div id="progressBar" class="progress-bar"></div>
            </div>

            <div class="progress-stats">
                <span id="progressPercent">0%</span>
                <span id="uploadSpeed">0 MB/s</span>
            </div>

            <p id="fileName" class="file-name"></p>
            <p id="fileSize" class="file-size"></p>
        </div>

        <!-- Success Section (hidden initially) -->
        <div id="successSection" class="success-section hidden">
            <div class="success-icon">✅</div>
            <h2 class="success-title">Upload terminé !</h2>
            <p class="success-description">Votre formation a été uploadée avec succès.</p>
            <button class="btn-primary" onclick="window.Telegram.WebApp.close()">
                Fermer
            </button>
        </div>

        <!-- Error Section (hidden initially) -->
        <div id="errorSection" class="error-section hidden">
            <div class="error-icon">❌</div>
            <h2 class="error-title">Erreur d'upload</h2>
            <p id="errorMessage" class="error-description"></p>
            <button class="btn-primary" onclick="location.reload()">
                Réessayer
            </button>
        </div>
    </div>

    <!-- Telegram WebApp SDK -->
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="/static/upload.js"></script>
</body>
</html>
```

---

#### 5.3.2 static/upload.js

**Emplacement:** `app/integrations/telegram/static/upload.js`

```javascript
// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();

// Get user data from Telegram
const userId = tg.initDataUnsafe?.user?.id;
const username = tg.initDataUnsafe?.user?.username;

// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const progressSection = document.getElementById('progressSection');
const successSection = document.getElementById('successSection');
const errorSection = document.getElementById('errorSection');
const progressBar = document.getElementById('progressBar');
const progressPercent = document.getElementById('progressPercent');
const uploadSpeed = document.getElementById('uploadSpeed');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const errorMessage = document.getElementById('errorMessage');

// Drag & Drop
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelection(files[0]);
    }
});

// File Input
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileSelection(e.target.files[0]);
    }
});

// Handle File Selection
async function handleFileSelection(file) {
    console.log('File selected:', file.name, formatBytes(file.size));

    // Validation
    const maxSize = 10 * 1024 * 1024 * 1024; // 10 GB
    if (file.size > maxSize) {
        showError('Fichier trop volumineux (max 10 GB)');
        return;
    }

    // Update UI
    fileName.textContent = file.name;
    fileSize.textContent = formatBytes(file.size);

    uploadArea.classList.add('hidden');
    progressSection.classList.remove('hidden');

    // Request Presigned Upload URL
    try {
        const presignedData = await requestPresignedUploadURL(file.name, file.type, userId);

        if (!presignedData || !presignedData.upload_url) {
            throw new Error('Failed to get upload URL');
        }

        // Upload to B2
        await uploadFileToB2(file, presignedData.upload_url, presignedData.object_key);

        // Notify backend upload complete
        await notifyUploadComplete(presignedData.object_key, file.name, file.size);

        // Show success
        showSuccess();

    } catch (error) {
        console.error('Upload error:', error);
        showError(error.message || 'Erreur lors de l\'upload');
    }
}

// Request Presigned Upload URL from Backend
async function requestPresignedUploadURL(fileName, fileType, userId) {
    const response = await fetch('/api/generate-upload-url', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            file_name: fileName,
            file_type: fileType,
            user_id: userId,
            telegram_init_data: tg.initData  // For auth verification
        })
    });

    if (!response.ok) {
        throw new Error('Failed to get upload URL');
    }

    return await response.json();
}

// Upload File to B2 via Presigned URL
async function uploadFileToB2(file, uploadUrl, objectKey) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        // Track upload progress
        let startTime = Date.now();
        let lastLoaded = 0;

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percent = (e.loaded / e.total) * 100;
                progressBar.style.width = percent + '%';
                progressPercent.textContent = Math.round(percent) + '%';

                // Calculate upload speed
                const elapsed = (Date.now() - startTime) / 1000; // seconds
                const speed = (e.loaded - lastLoaded) / elapsed / (1024 * 1024); // MB/s
                uploadSpeed.textContent = speed.toFixed(2) + ' MB/s';

                lastLoaded = e.loaded;
                startTime = Date.now();
            }
        });

        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve();
            } else {
                reject(new Error('Upload failed: ' + xhr.status));
            }
        });

        xhr.addEventListener('error', () => {
            reject(new Error('Network error during upload'));
        });

        xhr.open('PUT', uploadUrl);
        xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream');
        xhr.send(file);
    });
}

// Notify Backend Upload Complete
async function notifyUploadComplete(objectKey, fileName, fileSize) {
    const response = await fetch('/api/upload-complete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            object_key: objectKey,
            file_name: fileName,
            file_size: fileSize,
            user_id: userId,
            telegram_init_data: tg.initData
        })
    });

    if (!response.ok) {
        throw new Error('Failed to notify upload completion');
    }
}

// UI State Management
function showSuccess() {
    progressSection.classList.add('hidden');
    successSection.classList.remove('hidden');
}

function showError(message) {
    uploadArea.classList.add('hidden');
    progressSection.classList.add('hidden');
    errorSection.classList.remove('hidden');
    errorMessage.textContent = message;
}

// Helper: Format bytes to human readable
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];

    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}
```

---

#### 5.3.3 static/styles.css

**Emplacement:** `app/integrations/telegram/static/styles.css`

```css
/* Design System - Ferus Inspired */
:root {
    /* Colors */
    --purple-vibrant: #8b5cf6;
    --purple-accent: #8b5cf6;
    --purple-glow: #a78bfa;
    --purple-deep: #7c3aed;
    --purple-soft: #e9d5ff;

    --orange-vivid: #f59e0b;
    --cyan-vivid: #06b6d4;
    --pink-vivid: #ec4899;

    /* Backgrounds */
    --bg-white: #fafbfc;
    --bg-light: #f3f4f6;
    --bg-gray-subtle: #e5e7eb;

    /* Text */
    --text-black: #1e293b;
    --text-dark: #334155;
    --text-gray: #64748b;
    --text-light: #94a3b8;

    /* Shadows */
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.03);
    --shadow-md: 0 4px 6px rgba(0,0,0,0.04), 0 2px 4px rgba(0,0,0,0.03);
    --shadow-lg: 0 10px 15px rgba(0,0,0,0.05), 0 4px 6px rgba(0,0,0,0.03);
    --shadow-purple: 0 10px 40px rgba(139, 92, 246, 0.12);
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif;
    background: var(--bg-white);
    color: var(--text-dark);
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    padding: 20px;
}

.container {
    max-width: 600px;
    margin: 0 auto;
}

/* Header */
.header {
    text-align: center;
    margin-bottom: 2rem;
}

.title {
    font-size: 2rem;
    font-weight: 900;
    color: var(--text-black);
    margin-bottom: 0.5rem;
}

.subtitle {
    font-size: 1rem;
    color: var(--text-gray);
}

/* Upload Area */
.upload-area {
    background: white;
    border: 3px dashed var(--purple-soft);
    border-radius: 1rem;
    padding: 3rem 2rem;
    text-align: center;
    transition: all 0.3s ease;
    cursor: pointer;
}

.upload-area:hover,
.upload-area.dragover {
    border-color: var(--purple-vibrant);
    background: var(--purple-soft);
    box-shadow: var(--shadow-purple);
}

.upload-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
}

.upload-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-black);
    margin-bottom: 0.5rem;
}

.upload-description {
    color: var(--text-gray);
    margin-bottom: 1.5rem;
}

.file-input {
    display: none;
}

/* Buttons */
.btn-primary {
    background: linear-gradient(135deg, var(--purple-vibrant) 0%, var(--purple-deep) 100%);
    color: white;
    border: none;
    padding: 1rem 2rem;
    border-radius: 0.75rem;
    font-size: 1rem;
    font-weight: 700;
    cursor: pointer;
    box-shadow: var(--shadow-purple);
    transition: all 0.3s ease;
}

.btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 20px 40px rgba(139, 92, 246, 0.2);
}

.btn-primary:active {
    transform: translateY(0);
}

/* Progress Section */
.progress-section {
    background: white;
    border-radius: 1rem;
    padding: 2rem;
    box-shadow: var(--shadow-lg);
}

.progress-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text-black);
    margin-bottom: 1.5rem;
    text-align: center;
}

.progress-bar-container {
    width: 100%;
    height: 1rem;
    background: var(--bg-gray-subtle);
    border-radius: 1rem;
    overflow: hidden;
    margin-bottom: 1rem;
}

.progress-bar {
    height: 100%;
    background: linear-gradient(90deg, var(--purple-vibrant) 0%, var(--pink-vivid) 100%);
    border-radius: 1rem;
    transition: width 0.3s ease;
    width: 0;
}

.progress-stats {
    display: flex;
    justify-content: space-between;
    font-size: 0.875rem;
    color: var(--text-gray);
    margin-bottom: 1rem;
}

.file-name {
    font-weight: 600;
    color: var(--text-black);
    word-break: break-all;
}

.file-size {
    color: var(--text-gray);
    font-size: 0.875rem;
}

/* Success Section */
.success-section,
.error-section {
    background: white;
    border-radius: 1rem;
    padding: 3rem 2rem;
    box-shadow: var(--shadow-lg);
    text-align: center;
}

.success-icon,
.error-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
}

.success-title,
.error-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-black);
    margin-bottom: 0.5rem;
}

.success-description,
.error-description {
    color: var(--text-gray);
    margin-bottom: 2rem;
}

/* Utility */
.hidden {
    display: none !important;
}
```

---

### 5.4 Backend API Routes (FastAPI)

**Fichier:** `app/integrations/ipn_server.py` (étendre existant)

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import hashlib
import hmac
from app.services.b2_storage_service import B2StorageService
from app.core.utils import logger
from app.core.settings import settings

app = FastAPI()

# Monter static files
app.mount("/static", StaticFiles(directory="app/integrations/telegram/static"), name="static")

b2_service = B2StorageService()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Telegram WebApp Authentication
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def verify_telegram_webapp_data(init_data: str) -> bool:
    """
    Vérifier authentification Telegram WebApp
    Docs: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        # Parse init_data
        params = dict(item.split('=') for item in init_data.split('&'))

        received_hash = params.pop('hash', None)
        if not received_hash:
            return False

        # Sort params
        data_check_string = '\n'.join(f"{k}={v}" for k, v in sorted(params.items()))

        # Generate secret key
        secret_key = hmac.new(
            "WebAppData".encode(),
            settings.TELEGRAM_BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()

        # Calculate hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        return calculated_hash == received_hash

    except Exception as e:
        logger.error(f"Telegram WebApp auth error: {e}")
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API Models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class GenerateUploadURLRequest(BaseModel):
    file_name: str
    file_type: str
    user_id: int
    telegram_init_data: str


class UploadCompleteRequest(BaseModel):
    object_key: str
    file_name: str
    file_size: int
    user_id: int
    telegram_init_data: str


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API Routes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.post("/api/generate-upload-url")
async def generate_upload_url(request: GenerateUploadURLRequest):
    """
    Génère Presigned Upload URL pour upload direct Browser → B2
    """
    # Vérifier authentification Telegram
    if not verify_telegram_webapp_data(request.telegram_init_data):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # Generate unique object key
        import uuid
        from datetime import datetime

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        file_extension = request.file_name.split('.')[-1]

        object_key = f"uploads/{request.user_id}/{timestamp}_{unique_id}.{file_extension}"

        # Generate Presigned Upload URL (PUT)
        upload_url = b2_service.generate_presigned_upload_url(object_key, expires_in=3600)

        if not upload_url:
            raise HTTPException(status_code=500, detail="Failed to generate upload URL")

        logger.info(f"✅ Presigned upload URL generated for user {request.user_id}")

        return {
            "upload_url": upload_url,
            "object_key": object_key,
            "expires_in": 3600
        }

    except Exception as e:
        logger.error(f"❌ Error generating upload URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload-complete")
async def upload_complete(request: UploadCompleteRequest):
    """
    Callback après upload réussi - Finalise création produit
    """
    # Vérifier authentification
    if not verify_telegram_webapp_data(request.telegram_init_data):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # Vérifier que fichier existe sur B2
        file_exists = b2_service.file_exists(request.object_key)

        if not file_exists:
            raise HTTPException(status_code=404, detail="File not found on B2")

        # Construire B2 URL
        b2_url = f"https://s3.{settings.B2_REGION}.backblazeb2.com/{settings.B2_BUCKET_NAME}/{request.object_key}"

        # Sauvegarder en session utilisateur pour finaliser création produit
        # (Alternative: notifier le bot via webhook interne)
        from app.main import application

        # Notifier bot que upload terminé
        await application.bot.send_message(
            chat_id=request.user_id,
            text=(
                f"✅ Upload terminé !\n\n"
                f"📁 Fichier: {request.file_name}\n"
                f"📊 Taille: {request.file_size / (1024*1024):.2f} MB\n\n"
                f"Continuons la création de votre formation..."
            )
        )

        # Sauvegarder info upload dans state
        # marketplace_bot.update_user_state(request.user_id, uploaded_file_url=b2_url)

        logger.info(f"✅ Upload complete for user {request.user_id}: {request.object_key}")

        return {
            "status": "success",
            "b2_url": b2_url
        }

    except Exception as e:
        logger.error(f"❌ Error processing upload completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Nouvelle méthode B2StorageService:**

```python
# app/services/b2_storage_service.py

def generate_presigned_upload_url(self, object_key: str, expires_in: int = 3600) -> Optional[str]:
    """Generate a presigned URL for uploading (PUT) a file"""
    if not self.client:
        logger.error("❌ B2 client not initialized")
        return None

    try:
        url = self.client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': self.bucket_name,
                'Key': object_key
            },
            ExpiresIn=expires_in
        )
        logger.info(f"✅ Presigned upload URL generated for: {object_key}")
        return url

    except Exception as e:
        logger.error(f"❌ Failed to generate presigned upload URL: {e}")
        return None


def file_exists(self, object_key: str) -> bool:
    """Check if file exists on B2"""
    if not self.client:
        return False

    try:
        self.client.head_object(Bucket=self.bucket_name, Key=object_key)
        return True
    except:
        return False
```

---

### 5.5 Keyboard Modification

**Fichier:** `app/integrations/telegram/keyboards.py`

```python
# Ajouter WebApp button dans sell_menu

from telegram import WebAppInfo

def sell_menu_keyboard_with_webapp(lang: str):
    """Menu vente avec Mini App button"""
    return [
        # WebApp Upload
        [InlineKeyboardButton(
            "📤 Upload Formation (Mini App)" if lang == 'en' else "📤 Uploader Formation (Mini App)",
            web_app=WebAppInfo(url="https://YOUR-RAILWAY-DOMAIN.up.railway.app/static/upload.html")
        )],

        # Classic flow
        [InlineKeyboardButton(i18n(lang, 'btn_seller_login'), callback_data='seller_login_menu')],
        [InlineKeyboardButton(i18n(lang, 'btn_create_seller'), callback_data='create_seller')],
        [InlineKeyboardButton(i18n(lang, 'btn_seller_info'), callback_data='seller_info')],
        [back_to_main_button(lang)],
    ]
```

---

## 6. Phase 4: Testing & Deployment

### 6.1 Tests Unitaires

```python
# tests/test_presigned_urls.py

import pytest
from app.core.file_utils import get_b2_presigned_url
from app.services.b2_storage_service import B2StorageService


def test_generate_presigned_download_url():
    """Test génération Presigned Download URL"""
    b2_url = "https://s3.us-west-000.backblazeb2.com/my-bucket/products/TBF-123/file.pdf"

    presigned_url = get_b2_presigned_url(b2_url, expires_in=3600)

    assert presigned_url is not None
    assert "Signature=" in presigned_url
    assert "Expires=" in presigned_url


def test_generate_presigned_upload_url():
    """Test génération Presigned Upload URL"""
    b2_service = B2StorageService()

    upload_url = b2_service.generate_presigned_upload_url(
        "uploads/123/test.pdf",
        expires_in=3600
    )

    assert upload_url is not None
    assert "Signature=" in upload_url


def test_file_size_check():
    """Test vérification taille fichier sans download"""
    b2_service = B2StorageService()

    file_size = b2_service.get_file_size("products/TBF-123/file.pdf")

    assert file_size is not None
    assert file_size > 0
```

---

### 6.2 Tests d'Intégration

```bash
# Test 1: Download depuis Library
# 1. Acheter une formation
# 2. Aller dans "Ma Bibliothèque"
# 3. Cliquer "Télécharger"
# 4. Vérifier réception message avec Presigned URL
# 5. Cliquer lien → Vérifier download fichier

# Test 2: Post-payment delivery
# 1. Créer commande test
# 2. Simuler IPN payment_finished
# 3. Vérifier réception message avec Presigned URL
# 4. Vérifier order.file_delivered = TRUE en DB

# Test 3: Preview feature
# 1. Upload formation PDF >100 MB
# 2. Cliquer "Aperçu"
# 3. Vérifier message "Aperçu indisponible (fichier trop volumineux)"

# Test 4: Retry cronjob
# 1. Créer order avec file_delivered=FALSE
# 2. Lancer cronjob: python -m app.tasks.retry_undelivered_files
# 3. Vérifier send_formation_to_buyer() appelé
# 4. Vérifier réception Presigned URL
```

---

### 6.3 Tests de Charge

```python
# tests/load_test_presigned_urls.py

import asyncio
from app.core.file_utils import get_b2_presigned_url


async def generate_100_presigned_urls():
    """Test génération 100 URLs simultanées"""
    b2_url = "https://s3.us-west-000.backblazeb2.com/my-bucket/products/TBF-123/file.pdf"

    tasks = [
        asyncio.create_task(asyncio.to_thread(get_b2_presigned_url, b2_url))
        for _ in range(100)
    ]

    results = await asyncio.gather(*tasks)

    assert all(url is not None for url in results)
    print(f"✅ Generated {len(results)} Presigned URLs successfully")


if __name__ == "__main__":
    asyncio.run(generate_100_presigned_urls())
```

---

### 6.4 Déploiement

#### Étape 1: Déployer Phase 1 (Critical Fixes)

```bash
# 1. Commit changements
git add app/integrations/telegram/handlers/library_handlers.py
git add app/integrations/telegram/handlers/buy_handlers.py
git add app/integrations/ipn_server.py
git add app/domain/repositories/order_repo.py

git commit -m "Fix: Replace local download with Presigned URLs (library + post-payment delivery)"

# 2. Push to Railway
git push origin main

# 3. Vérifier logs Railway
railway logs --tail 100

# 4. Test production
# - Télécharger depuis Library
# - Effectuer achat test
# - Vérifier réception Presigned URLs
```

---

#### Étape 2: Déployer Phase 2 (Preview Fix)

```bash
# Option A: Quick fix
git add app/integrations/telegram/handlers/buy_handlers.py
git add app/services/b2_storage_service.py
git commit -m "Fix: Disable preview for files >100 MB (prevent OOM)"
git push origin main

# Option B: Pre-generate previews (later)
# Implémenter progressivement
```

---

#### Étape 3: Déployer Phase 3 (Mini App)

```bash
# 1. Créer static folder
mkdir -p app/integrations/telegram/static

# 2. Ajouter fichiers
# - upload.html
# - upload.js
# - styles.css

# 3. Modifier ipn_server.py (API routes)

# 4. Modifier keyboards.py (WebApp button)

# 5. Commit & Deploy
git add app/integrations/telegram/static/
git add app/integrations/ipn_server.py
git add app/integrations/telegram/keyboards.py

git commit -m "Feature: Add Telegram Mini App for large file uploads"
git push origin main

# 6. Configurer domaine Railway (si pas déjà fait)
# Settings → Networking → Generate Domain
# Exemple: https://python-bot-production.up.railway.app

# 7. Mettre à jour WebAppInfo URL dans keyboards.py
# WebAppInfo(url="https://YOUR-DOMAIN.up.railway.app/static/upload.html")
```

---

## 7. Annexes

### 7.1 Résumé Technique

| Workflow | Avant (❌ CRASH) | Après (✅ NO CRASH) | Gain RAM |
|----------|------------------|---------------------|----------|
| Library download | Download 5 GB → send_document | Generate URL (1 KB) | **5000x** |
| Post-payment delivery | Download 5 GB → reply_document | Generate URL (1 KB) | **5000x** |
| Preview generation | Download 5 GB → PyMuPDF | Disable >100 MB | **100%** |
| Vendor upload | Temp file 5 GB (<10s) | Presigned Upload (Browser→B2) | **100%** |

**Résultat:**
- ✅ Railway RAM usage: **<10 MB** (au lieu de 512+ MB crash)
- ✅ Support fichiers jusqu'à **10 TB** (pas de limite Presigned URLs)
- ✅ Vitesse download max (B2 → User direct)

---

### 7.2 Checklist Finale

**Phase 1: Presigned URLs (Critical)**
- [ ] Modifier `library_handlers.py:266-327` (Presigned URL)
- [ ] Modifier `buy_handlers.py:1663-1700` (Presigned URL)
- [ ] Implémenter `send_formation_to_buyer()` dans `ipn_server.py`
- [ ] Ajouter `mark_order_delivered()` dans `order_repo.py`
- [ ] Tester Library download
- [ ] Tester Post-payment delivery
- [ ] Tester Retry cronjob

**Phase 2: Preview Fix**
- [ ] Implémenter `get_file_size()` dans `b2_storage_service.py`
- [ ] Ajouter vérification taille avant preview
- [ ] Désactiver preview >100 MB
- [ ] Tester avec fichier >100 MB
- [ ] (Optionnel) Implémenter pre-generation previews

**Phase 3: Mini App**
- [ ] Créer `static/upload.html`
- [ ] Créer `static/upload.js`
- [ ] Créer `static/styles.css`
- [ ] Ajouter routes API (`/api/generate-upload-url`, `/api/upload-complete`)
- [ ] Implémenter `generate_presigned_upload_url()` dans B2
- [ ] Implémenter `verify_telegram_webapp_data()` auth
- [ ] Modifier `keyboards.py` (WebApp button)
- [ ] Configurer domaine Railway
- [ ] Tester upload 1 GB
- [ ] Tester upload 10 GB

**Phase 4: Testing & Deployment**
- [ ] Tests unitaires (Presigned URLs)
- [ ] Tests d'intégration (Library, Post-payment, Preview)
- [ ] Tests de charge (100 URLs simultanées)
- [ ] Déploiement Phase 1 → Production
- [ ] Monitoring Railway RAM usage (<10 MB ✅)
- [ ] Déploiement Phase 2 (si Quick Fix)
- [ ] Déploiement Phase 3 (Mini App)

---

### 7.3 Dépendances

**Aucune nouvelle dépendance** nécessaire - tout utilise les libraries existantes:

```python
# Déjà installé
boto3  # S3/B2 client (generate_presigned_url)
fastapi  # API routes (déjà configuré dans ipn_server.py)
httpx  # Async HTTP (déjà utilisé)
```

---

### 7.4 Rollback Plan

Si problème après déploiement:

```bash
# 1. Revenir au commit précédent
git log --oneline -5
git revert <commit_hash>
git push origin main

# 2. OU déployer hotfix
# Si Presigned URLs échouent → Fallback vers download local temporaire

# app/core/file_utils.py
def get_b2_presigned_url_with_fallback(b2_url: str, expires_in: int = 3600):
    """Presigned URL avec fallback download local"""
    try:
        presigned_url = get_b2_presigned_url(b2_url, expires_in)
        if presigned_url:
            return presigned_url
    except Exception as e:
        logger.error(f"Presigned URL failed, fallback to local download: {e}")

    # Fallback: download local (ancien flow)
    return None  # Handler détecte None → utilise ancien flow
```

---

### 7.5 Questions Ouvertes

1. **Expiration Presigned URLs:**
   - Actuellement: 24h (86400 secondes)
   - Alternative: 7 jours pour Library downloads ?

2. **Preview Pre-generation:**
   - Quick fix: Désactiver >100 MB (immédiat)
   - Long-term: Pre-generate au moment upload (Phase future)

3. **Mini App UX:**
   - Afficher preview fichier avant upload ?
   - Multi-file upload support ?

4. **Monitoring:**
   - Logger chaque génération Presigned URL
   - Dashboard analytics (combien URLs générées/jour) ?

---

**FIN DU PLAN**

👨‍💼 **Architecte:** Claude Code
📅 **Date:** 5 décembre 2025
🎯 **Objectif:** Gérer fichiers 10 GB+ sans crash Railway
✅ **Status:** Plan complet - Ready for execution
