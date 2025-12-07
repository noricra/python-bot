# Telegram Mini App - Guide complet upload fichiers

## 📋 Table des matières

1. [Contexte du problème](#contexte)
2. [Solution 1: Script local CORS](#solution-1-script-local)
3. [Solution 2: Endpoint admin CORS](#solution-2-endpoint-admin)
4. [Solution 3: Upload via serveur](#solution-3-upload-serveur)
5. [Comparaison des solutions](#comparaison)
6. [Troubleshooting](#troubleshooting)

---

## 🔍 Contexte du problème {#contexte}

### Architecture actuelle

```
Mini App (Browser) ──[PUT presigned URL]──> Backblaze B2
```

### Erreur rencontrée

```javascript
status: 0
statusText: ""
readyState: 4
responseText: "No response"
```

**Signification:** Le navigateur **bloque la requête AVANT qu'elle n'atteigne B2** à cause de CORS.

### Pourquoi CORS est requis ?

1. La Mini App Telegram s'exécute dans un contexte `https://web.telegram.org`
2. Elle tente d'uploader vers `https://s3.us-west-004.backblazeb2.com`
3. C'est une **requête cross-origin** → Le navigateur demande la permission à B2
4. B2 doit répondre avec les headers CORS appropriés
5. **Sans CORS configuré sur B2, le navigateur bloque** (status 0)

### Flux CORS complet

```
1. Browser → Preflight OPTIONS request → B2
2. B2 → Response with CORS headers → Browser
3. Browser vérifie les headers:
   - Access-Control-Allow-Origin: *
   - Access-Control-Allow-Methods: PUT
   - Access-Control-Allow-Headers: Content-Type
4. Si OK → Browser envoie le PUT
5. Si KO → Browser bloque (status 0) ❌
```

**Problème:** L'interface web B2 permet de configurer "Share with HTTPS origins" mais ça ne configure **PAS les headers CORS S3** nécessaires.

---

## ✅ Solution 1: Script local pour configurer CORS {#solution-1-script-local}

**⭐ RECOMMANDÉE** - La plus simple et sécurisée

### Principe

Exécuter un script Python **une fois en local** qui configure CORS sur le bucket B2 via l'API.

### Fichier: `configure_b2_cors.py`

```python
"""
Script de configuration CORS pour Backblaze B2
À exécuter UNE SEULE FOIS en local
"""
from b2sdk.v2 import InMemoryAccountInfo, B2Api
import os
from dotenv import load_dotenv

# Charger les credentials depuis .env
load_dotenv()

def configure_b2_cors():
    """Configure CORS sur le bucket B2 pour permettre uploads depuis Telegram"""

    # 1. Connexion à B2
    print("🔌 Connexion à Backblaze B2...")
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)

    b2_api.authorize_account(
        "production",
        os.getenv("B2_KEY_ID"),
        os.getenv("B2_APPLICATION_KEY")
    )
    print("✅ Connecté à B2")

    # 2. Récupérer le bucket
    bucket_name = os.getenv("B2_BUCKET_NAME", "Uzeur-StockFiles")
    print(f"📦 Récupération du bucket: {bucket_name}")
    bucket = b2_api.get_bucket_by_name(bucket_name)

    # 3. Configuration CORS
    cors_rules = [{
        "corsRuleName": "telegram-miniapp-upload",
        "allowedOrigins": [
            "https://web.telegram.org",
            "https://oauth.telegram.org"
        ],
        "allowedOperations": [
            "s3_put",      # Pour upload
            "s3_get",      # Pour download
            "s3_head"      # Pour vérifier existence
        ],
        "allowedHeaders": [
            "content-type",
            "x-bz-file-name",
            "x-bz-content-sha1",
            "x-bz-info-*"
        ],
        "exposeHeaders": [
            "x-bz-file-id",
            "x-bz-file-name"
        ],
        "maxAgeSeconds": 3600
    }]

    print("🔧 Application des règles CORS...")

    # 4. Appliquer CORS
    b2_api.update_bucket(
        bucket.id_,
        bucket_type="allPublic",  # ou "allPrivate" selon votre config
        cors_rules=cors_rules
    )

    print("✅ CORS configuré avec succès!")
    print("\n📋 Règles appliquées:")
    print(f"   - Origins: {cors_rules[0]['allowedOrigins']}")
    print(f"   - Opérations: {cors_rules[0]['allowedOperations']}")
    print(f"   - Headers: {cors_rules[0]['allowedHeaders']}")

if __name__ == "__main__":
    try:
        configure_b2_cors()
        print("\n🎉 Configuration terminée!")
        print("   Vous pouvez maintenant tester l'upload dans la Mini App.")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        print("   Vérifiez vos credentials B2 dans le fichier .env")
```

### Instructions d'utilisation

**1. Créer le fichier**
```bash
# Dans votre projet
nano configure_b2_cors.py
# Coller le code ci-dessus
```

**2. Vérifier le .env**
```bash
# Votre fichier .env doit contenir:
B2_KEY_ID=votre_key_id
B2_APPLICATION_KEY=votre_application_key
B2_BUCKET_NAME=Uzeur-StockFiles
```

**3. Installer b2sdk si nécessaire**
```bash
pip3 install b2sdk python-dotenv
```

**4. Exécuter le script**
```bash
python3 configure_b2_cors.py
```

**5. Sortie attendue**
```
🔌 Connexion à Backblaze B2...
✅ Connecté à B2
📦 Récupération du bucket: Uzeur-StockFiles
🔧 Application des règles CORS...
✅ CORS configuré avec succès!

📋 Règles appliquées:
   - Origins: ['https://web.telegram.org', 'https://oauth.telegram.org']
   - Opérations: ['s3_put', 's3_get', 's3_head']
   - Headers: ['content-type', 'x-bz-file-name', ...]

🎉 Configuration terminée!
   Vous pouvez maintenant tester l'upload dans la Mini App.
```

### Avantages ✅

- Simple et rapide (1 minute)
- Sécurisé (credentials en local uniquement)
- Une seule exécution nécessaire
- Pas de code additionnel dans l'app

### Inconvénients ❌

- Nécessite Python et b2sdk en local
- Doit être relancé si règles CORS changent

---

## 🌐 Solution 2: Endpoint admin pour configurer CORS {#solution-2-endpoint-admin}

**Alternative si vous ne pouvez pas exécuter de script local**

### Principe

Créer un endpoint admin `/admin/configure-cors` dans votre API Railway qui configure CORS quand on l'appelle.

### Code à ajouter dans `ipn_server.py`

```python
from b2sdk.v2 import InMemoryAccountInfo, B2Api

@app.post("/admin/configure-cors")
async def configure_b2_cors_endpoint(admin_secret: str):
    """
    Endpoint admin pour configurer CORS sur B2
    À appeler UNE SEULE FOIS après déploiement

    Usage:
    curl -X POST "https://votre-app.railway.app/admin/configure-cors?admin_secret=VOTRE_SECRET"
    """
    # Vérification secret admin
    if admin_secret != os.getenv("ADMIN_SECRET_KEY"):
        logger.warning("⚠️ Tentative accès admin avec mauvais secret")
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        # Connexion B2
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account(
            "production",
            core_settings.B2_KEY_ID,
            core_settings.B2_APPLICATION_KEY
        )

        # Récupérer bucket
        bucket = b2_api.get_bucket_by_name(core_settings.B2_BUCKET_NAME)

        # Configuration CORS
        cors_rules = [{
            "corsRuleName": "telegram-miniapp-upload",
            "allowedOrigins": [
                "https://web.telegram.org",
                "https://oauth.telegram.org"
            ],
            "allowedOperations": ["s3_put", "s3_get", "s3_head"],
            "allowedHeaders": [
                "content-type",
                "x-bz-file-name",
                "x-bz-content-sha1",
                "x-bz-info-*"
            ],
            "exposeHeaders": ["x-bz-file-id", "x-bz-file-name"],
            "maxAgeSeconds": 3600
        }]

        # Appliquer CORS
        b2_api.update_bucket(
            bucket.id_,
            bucket_type="allPublic",
            cors_rules=cors_rules
        )

        logger.info("✅ CORS configuré sur B2 via endpoint admin")

        return {
            "status": "success",
            "message": "CORS configured successfully",
            "rules": cors_rules
        }

    except Exception as e:
        logger.error(f"❌ Erreur configuration CORS: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### Instructions d'utilisation

**1. Ajouter le code ci-dessus dans `ipn_server.py`**

**2. Ajouter secret admin dans Railway**
```bash
# Dans Railway Dashboard > Variables
ADMIN_SECRET_KEY=un_secret_très_long_et_complexe_xyz123
```

**3. Déployer sur Railway**
```bash
git add app/integrations/ipn_server.py
git commit -m "Add: Endpoint admin pour config CORS"
git push origin miniapp-railway-test
```

**4. Appeler l'endpoint**
```bash
curl -X POST "https://votre-app.railway.app/admin/configure-cors?admin_secret=un_secret_très_long_et_complexe_xyz123"
```

**5. Réponse attendue**
```json
{
  "status": "success",
  "message": "CORS configured successfully",
  "rules": [...]
}
```

**6. (Optionnel) Supprimer l'endpoint après usage**

Pour sécurité, supprimez l'endpoint après la configuration:
```python
# Commenter ou supprimer le code de l'endpoint
```

### Avantages ✅

- Pas besoin d'exécution locale
- Peut être appelé depuis n'importe où (curl, browser)
- Idéal si pas d'accès local au code

### Inconvénients ❌

- Endpoint admin exposé (besoin secret)
- Nécessite redéploiement Railway
- Secret dans les logs si mal configuré

---

## 🔄 Solution 3: Upload via serveur (sans CORS) {#solution-3-upload-serveur}

**Alternative complète si CORS impossible à configurer**

### Principe

Au lieu d'uploader directement depuis le navigateur vers B2, le fichier transite par Railway:

```
Browser ──[POST multipart]──> Railway ──[PUT boto3]──> B2
```

Pas de CORS requis car communication server-to-server.

### Modifications requises

#### 1. Nouveau endpoint dans `ipn_server.py`

```python
from fastapi import File, UploadFile, Form

@app.post("/api/upload-file")
async def upload_file_via_server(
    file: UploadFile = File(...),
    user_id: int = Form(...),
    telegram_init_data: str = Form(...)
):
    """
    Upload fichier via serveur Railway (bypass CORS B2)
    Le fichier transite: Browser → Railway → B2
    """
    # Vérifier auth Telegram
    if not verify_telegram_webapp_data(telegram_init_data):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # Générer object key unique
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        ext = file.filename.split('.')[-1] if '.' in file.filename else 'bin'
        object_key = f"uploads/{user_id}/{timestamp}_{unique_id}.{ext}"

        # Upload vers B2 (server-to-server, pas de CORS)
        logger.info(f"📤 Uploading {file.filename} to B2 via server...")
        b2 = B2StorageService()
        b2_url = await b2.upload_fileobj(file.file, object_key)

        if not b2_url:
            raise HTTPException(status_code=500, detail="B2 upload failed")

        logger.info(f"✅ File uploaded to B2: {object_key}")

        # Notifier utilisateur Telegram
        global telegram_application
        if telegram_application:
            await telegram_application.bot.send_message(
                chat_id=user_id,
                text=(
                    f"✅ **Fichier reçu avec succès !**\n\n"
                    f"📁 Nom: `{file.filename}`\n"
                    f"📊 Taille: `{file.size / (1024*1024):.2f} MB`\n\n"
                    f"Je prépare la suite..."
                ),
                parse_mode='Markdown'
            )

        return {
            "status": "success",
            "b2_url": b2_url,
            "object_key": object_key,
            "file_size": file.size
        }

    except Exception as e:
        logger.error(f"❌ Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

#### 2. Modifications dans `upload.js`

```javascript
// Remplacer la fonction handleFileSelection complète

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

    try {
        // Upload via serveur (pas de presigned URL)
        await uploadFileViaServer(file);
        showSuccess();
    } catch (error) {
        console.error('Upload error:', error);
        showError(error.message || 'Erreur lors de l\'upload');
    }
}

// Nouvelle fonction d'upload
async function uploadFileViaServer(file) {
    return new Promise((resolve, reject) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('user_id', userId);
        formData.append('telegram_init_data', tg.initData);

        const xhr = new XMLHttpRequest();

        // Progress tracking
        let startTime = Date.now();
        let lastLoaded = 0;

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percent = (e.loaded / e.total) * 100;
                progressBar.style.width = percent + '%';
                progressPercent.textContent = Math.round(percent) + '%';

                // Calculate upload speed
                const elapsed = (Date.now() - startTime) / 1000;
                const speed = (e.loaded - lastLoaded) / elapsed / (1024 * 1024);
                uploadSpeed.textContent = speed.toFixed(2) + ' MB/s';

                lastLoaded = e.loaded;
                startTime = Date.now();
            }
        });

        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve(JSON.parse(xhr.responseText));
            } else {
                reject(new Error(`Upload failed: ${xhr.status}`));
            }
        });

        xhr.addEventListener('error', () => {
            reject(new Error('Network error during upload'));
        });

        xhr.open('POST', '/api/upload-file');
        xhr.send(formData);  // Pas de Content-Type header (FormData auto)
    });
}
```

#### 3. Supprimer les anciens endpoints

Vous pouvez supprimer (ou garder pour compatibilité):
- `/api/generate-upload-url`
- `/api/upload-complete`

### Avantages ✅

- **Pas de CORS requis** (server-to-server)
- Fonctionne immédiatement
- Pas de configuration B2 complexe
- Contrôle total côté serveur

### Inconvénients ❌

- **Fichier transite par Railway** (double bandwidth)
- Plus lent pour gros fichiers
- Coûts Railway plus élevés
- Limite taille selon Railway

---

## 📊 Comparaison des solutions {#comparaison}

| Critère | Solution 1: Script local | Solution 2: Endpoint admin | Solution 3: Via serveur |
|---------|-------------------------|---------------------------|------------------------|
| **Complexité** | ⭐⭐ Moyenne | ⭐⭐⭐ Élevée | ⭐ Simple |
| **CORS requis** | ✅ Oui (configuré) | ✅ Oui (configuré) | ❌ Non |
| **Fichier transite Railway** | ❌ Non | ❌ Non | ✅ Oui |
| **Performance** | ⭐⭐⭐ Excellente | ⭐⭐⭐ Excellente | ⭐⭐ Moyenne |
| **Bandwidth Railway** | Minimal | Minimal | Double |
| **Sécurité** | ⭐⭐⭐ Excellente | ⭐⭐ Bonne | ⭐⭐⭐ Excellente |
| **Maintenance** | Aucune | Endpoint à sécuriser | Code serveur |
| **Taille fichiers** | 10 GB | 10 GB | Selon Railway |

### Recommandations

**Pour production:**
- **Solution 1** si vous avez accès local → Meilleure performance, sécurisé
- **Solution 2** si impossible d'exécuter en local → Pratique mais endpoint à sécuriser

**Pour développement/test rapide:**
- **Solution 3** → Fonctionne immédiatement, pas de configuration B2

**Pour très gros fichiers (>500 MB):**
- **Solution 1 ou 2** obligatoires (upload direct évite saturer Railway)

---

## 🔧 Troubleshooting {#troubleshooting}

### Vérifier si CORS est configuré sur B2

**Méthode 1: Via script Python**
```python
from b2sdk.v2 import InMemoryAccountInfo, B2Api
import os
from dotenv import load_dotenv

load_dotenv()

info = InMemoryAccountInfo()
b2_api = B2Api(info)
b2_api.authorize_account("production", os.getenv("B2_KEY_ID"), os.getenv("B2_APPLICATION_KEY"))

bucket = b2_api.get_bucket_by_name("Uzeur-StockFiles")
print("CORS Rules:", bucket.cors_rules)
```

**Méthode 2: Tester avec curl**
```bash
# Preflight OPTIONS request
curl -X OPTIONS \
  -H "Origin: https://web.telegram.org" \
  -H "Access-Control-Request-Method: PUT" \
  -H "Access-Control-Request-Headers: content-type" \
  https://s3.us-west-004.backblazeb2.com/Uzeur-StockFiles/test.txt \
  -v
```

**Réponse attendue:**
```
< HTTP/1.1 200 OK
< Access-Control-Allow-Origin: https://web.telegram.org
< Access-Control-Allow-Methods: PUT
< Access-Control-Allow-Headers: content-type
< Access-Control-Max-Age: 3600
```

### Logs à surveiller après configuration CORS

**Railway logs attendus (succès):**
```
🔧 Generating presigned URL with params: {...}
✅ Presigned URL generated:
   Host: https://s3.us-west-004.backblazeb2.com
   Path: /Uzeur-StockFiles/uploads/...
   Content-Type in URL: True
✅ Generated presigned URL for user 5229892870
INFO: "POST /api/generate-upload-url HTTP/1.1" 200 OK
```

**Pas d'erreur CLIENT ERROR si CORS OK**

### Erreurs communes

**1. Status 0 persiste après config CORS**
- Attendre 1-2 minutes (propagation CORS)
- Vider cache navigateur
- Vérifier que les origins correspondent exactement

**2. Status 403 Forbidden**
- Content-Type dans signature ne correspond pas
- URL expirée (> 1h)
- Credentials B2 invalides

**3. Status 404 Not Found**
- Bucket name incorrect
- Endpoint B2 incorrect

### Test manuel

**1. Générer URL presigned manuellement:**
```python
from app.services.b2_storage_service import B2StorageService

b2 = B2StorageService()
url = b2.generate_presigned_upload_url("test.txt", "text/plain")
print(url)
```

**2. Tester l'upload avec curl:**
```bash
curl -X PUT \
  -H "Content-Type: text/plain" \
  -d "test content" \
  "PRESIGNED_URL_HERE"
```

**3. Vérifier le fichier sur B2:**
```bash
# Via B2 dashboard ou API
```

---

## 📝 Checklist finale

Avant de tester l'upload dans la Mini App:

- [ ] CORS configuré sur bucket B2 (Solution 1 ou 2)
- [ ] Variables d'environnement Railway:
  - [ ] `B2_KEY_ID`
  - [ ] `B2_APPLICATION_KEY`
  - [ ] `B2_BUCKET_NAME`
  - [ ] `B2_ENDPOINT`
  - [ ] `WEBAPP_URL`
- [ ] Code déployé sur Railway
- [ ] Logs Railway actifs pour monitoring
- [ ] Fichiers statiques (upload.html, upload.js, styles.css) présents
- [ ] CORSMiddleware configuré dans FastAPI

---

## 🎯 Résumé

**Problème:** Upload direct Browser → B2 bloqué par CORS (status 0)

**Cause:** B2 ne retourne pas les headers CORS nécessaires pour S3 API

**Solution recommandée:** Script local `configure_b2_cors.py` (Solution 1)
- Simple, rapide, sécurisé
- Une seule exécution
- Meilleure performance

**Alternative:** Endpoint admin (Solution 2) si pas d'accès local

**Dernier recours:** Upload via serveur (Solution 3) si CORS impossible

---

**Document créé le:** 2025-12-07
**Version:** 1.0
**Auteur:** Claude Code
