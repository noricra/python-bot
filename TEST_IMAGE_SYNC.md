# 🧪 Guide de Test : Système de Synchronisation d'Images

## Objectif
Vérifier que les images sont bien stockées localement + sur B2, et qu'elles se re-téléchargent automatiquement après un redémarrage.

---

## ✅ Test 1 : Upload d'un Nouveau Produit

### Étapes
1. Démarrer le bot : `python bot_mlt.py`
2. Dans Telegram : `/vendre`
3. Créer un nouveau produit avec une image
4. Observer les logs

### Résultat Attendu
```
✅ Images created locally (upload B2 after ID final)
✅ Uploaded to B2: products/PROD_xxx/cover.jpg
✅ Uploaded to B2: products/PROD_xxx/thumb.jpg
✅ Local images kept as backup: data/product_images/...
```

### Vérification Manuelle
```bash
# Vérifier fichiers locaux
ls -lh data/product_images/{seller_id}/{product_id}/

# Doit contenir :
# - cover.jpg
# - thumb.jpg
```

---

## ✅ Test 2 : Affichage avec Fichiers Locaux

### Étapes
1. Dans Telegram : `/acheter`
2. Parcourir les produits
3. Vérifier que les images s'affichent

### Résultat Attendu (Logs)
```
📁 Resolved absolute path: /path/to/data/product_images/.../thumb.jpg
✅ Using local image: ...
```

---

## ✅ Test 3 : Simulation Redémarrage Railway

### Étapes
1. **Sauvegarder** un produit ID pour référence
2. **Supprimer** les fichiers locaux d'un produit :
   ```bash
   rm -rf data/product_images/{seller_id}/{product_id}/
   ```
3. **Redémarrer** le bot : `python bot_mlt.py`
4. Observer les logs de démarrage

### Résultat Attendu (Logs)
```
🔄 Starting product images sync from B2...
⚠️ Product images missing locally for PROD_xxx, downloading from B2...
✅ Downloaded cover from B2: PROD_xxx
✅ Downloaded thumbnail from B2: PROD_xxx
✅ Image sync complete: {'total': X, 'synced': Y, 'already_local': Z, 'failed': 0}
🔄 Image sync started in background
```

5. **Afficher** le produit dans Telegram
6. Vérifier que l'image s'affiche correctement

### Résultat Attendu (Logs)
```
⚠️ Local image not found: ...
🔄 Attempting to sync image from B2...
✅ Image synced from B2: ...
```

---

## ✅ Test 4 : Vérification B2 (Optionnel)

### Étapes
1. Se connecter à Backblaze B2 Console
2. Naviguer vers le bucket `uzeur-marketplace`
3. Vérifier la structure :
   ```
   products/
   ├── PROD_ABC123/
   │   ├── cover.jpg
   │   └── thumb.jpg
   ├── PROD_DEF456/
   │   ├── cover.jpg
   │   └── thumb.jpg
   ...
   ```

---

## ❌ Résolution de Problèmes

### Problème 1 : "B2 upload failed"

**Cause** : Credentials B2 manquantes ou invalides

**Solution** :
```bash
# Vérifier .env
cat .env | grep B2

# Doit contenir :
B2_KEY_ID=...
B2_APPLICATION_KEY=...
B2_BUCKET_NAME=uzeur-marketplace
B2_ENDPOINT=https://s3.us-west-004.backblazeb2.com
```

### Problème 2 : "Image sync failed (non-critical)"

**Cause** : Service B2 temporairement indisponible

**Impact** : Non bloquant - les images uploadées après le démarrage fonctionneront

**Solution** :
- Redémarrer le bot pour réessayer
- Ou attendre que B2 revienne en ligne

### Problème 3 : Images ne s'affichent pas

**Étapes de Debug** :
1. Vérifier les logs pour voir quel chemin est utilisé
2. Vérifier si le fichier existe localement :
   ```bash
   ls -lh data/product_images/{seller_id}/{product_id}/
   ```
3. Vérifier si le fichier existe sur B2 (console web)
4. Forcer un re-téléchargement :
   ```bash
   # Supprimer fichier local
   rm data/product_images/{seller_id}/{product_id}/thumb.jpg

   # Réafficher le produit dans Telegram
   # → Doit télécharger automatiquement depuis B2
   ```

---

## 📊 Statistiques de Sync

Après chaque démarrage, vérifier les stats dans les logs :

```python
{
    'total': 10,        # Total de produits avec images
    'synced': 3,        # Images téléchargées depuis B2
    'already_local': 7, # Images déjà présentes localement
    'failed': 0         # Échecs (doit être 0)
}
```

**Cible** : `failed: 0` et `synced + already_local = total`

---

## 🚀 Test sur Railway

### Avant le Déploiement
1. S'assurer que les variables B2 sont configurées dans Railway
2. Vérifier que le bucket existe et est accessible

### Après le Déploiement
1. Consulter les logs Railway au démarrage
2. Vérifier le message de sync
3. Tester l'affichage des produits existants

### En Cas de Redémarrage Railway
1. Les images se re-téléchargent automatiquement
2. Pas d'intervention manuelle nécessaire
3. Les utilisateurs ne voient aucune interruption

---

## ✅ Checklist Finale

- [ ] Upload nouveau produit → fichiers locaux + B2 ✅
- [ ] Affichage produit → utilise fichiers locaux ✅
- [ ] Suppression fichiers locaux → redémarrage → re-téléchargement B2 ✅
- [ ] Logs sans erreurs critiques ✅
- [ ] Stats de sync correctes (failed: 0) ✅
- [ ] Images s'affichent dans Telegram ✅

---

**Date de création** : 10 novembre 2025
**Auteur** : Claude Code
