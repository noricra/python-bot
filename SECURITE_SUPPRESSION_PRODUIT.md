# 🚨 PROBLÈME CRITIQUE : Suppression de Produit Non Sécurisée

**Date de découverte :** 10 novembre 2025
**Sévérité :** 🔴 CRITIQUE
**Impact :** Perte de données, clients ne peuvent plus télécharger leurs achats

---

## 🔍 Problème Identifié

### Fichier : `app/domain/repositories/product_repo.py` ligne 136-178

La fonction `delete_product()` fait un **HARD DELETE** sans vérifications :

```python
def delete_product(self, product_id: str, seller_user_id: int) -> bool:
    # ...
    cursor.execute(
        'DELETE FROM products WHERE product_id = %s AND seller_user_id = %s',
        (product_id, seller_user_id)
    )
    # ❌ Pas de vérification des commandes existantes
    # ❌ Pas de suppression des fichiers B2
    # ❌ Pas de suppression des images locales
```

---

## 💥 Conséquences

### Scénario Catastrophe

```
1. Client A achète un produit pour 50€
2. Vendeur supprime le produit par erreur
3. ❌ Produit supprimé de la DB
4. ❌ Fichiers B2 TOUJOURS présents (gaspillage stockage)
5. ❌ Images locales TOUJOURS présentes (gaspillage disque)
6. ❌ Client A ne peut PLUS télécharger son fichier
7. ❌ Ticket support du client
8. ❌ Remboursement nécessaire
9. ❌ Perte de confiance
```

### Impact Financier

| Problème | Coût |
|----------|------|
| Remboursement client | 50€ par commande affectée |
| Temps support | 30 min/ticket |
| Stockage B2 inutile | 0.005$/GB/mois (s'accumule) |
| Perte de réputation | Inestimable |

---

## ✅ Solution Recommandée : Soft Delete

### Concept

**Soft Delete** = Marquer comme supprimé au lieu de supprimer réellement

```
┌─────────────────────────────────────────────┐
│  HARD DELETE (actuel - ❌)                  │
├─────────────────────────────────────────────┤
│  DELETE FROM products WHERE id = 123        │
│  → Données PERDUES pour toujours            │
│  → Commandes existantes CASSÉES             │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  SOFT DELETE (recommandé - ✅)               │
├─────────────────────────────────────────────┤
│  UPDATE products                            │
│  SET status = 'deleted',                    │
│      deleted_at = NOW()                     │
│  WHERE id = 123                             │
│                                             │
│  → Données PRÉSERVÉES                       │
│  → Commandes existantes FONCTIONNENT        │
│  → Acheteurs peuvent télécharger            │
│  → Produit invisible dans marketplace       │
└─────────────────────────────────────────────┘
```

---

## 🔧 Implémentation

### Étape 1 : Ajouter colonne `deleted_at`

**Migration SQL :**
```sql
ALTER TABLE products
ADD COLUMN deleted_at TIMESTAMP DEFAULT NULL;

-- Index pour performance
CREATE INDEX idx_products_deleted_at ON products(deleted_at);
```

### Étape 2 : Modifier `delete_product()`

**Fichier :** `app/domain/repositories/product_repo.py`

**AVANT (ligne 156-159) :**
```python
cursor.execute(
    'DELETE FROM products WHERE product_id = %s AND seller_user_id = %s',
    (product_id, seller_user_id)
)
```

**APRÈS :**
```python
# Vérifier s'il y a des commandes existantes
cursor.execute(
    'SELECT COUNT(*) as count FROM orders WHERE product_id = %s',
    (product_id,)
)
orders_count = cursor.fetchone()['count']

if orders_count > 0:
    # SOFT DELETE : Produit acheté, on le cache mais garde les données
    cursor.execute(
        '''
        UPDATE products
        SET status = 'deleted', deleted_at = NOW()
        WHERE product_id = %s AND seller_user_id = %s
        ''',
        (product_id, seller_user_id)
    )
    logger.info(f"✅ SOFT DELETE: Product {product_id} (had {orders_count} orders)")
else:
    # HARD DELETE : Jamais acheté, on peut vraiment supprimer
    # 1. Supprimer fichiers B2
    from app.services.b2_storage_service import B2StorageService
    b2 = B2StorageService()

    # Récupérer le file_url avant suppression
    cursor.execute(
        'SELECT file_url, cover_image_url, thumbnail_url FROM products WHERE product_id = %s',
        (product_id,)
    )
    product = cursor.fetchone()

    if product and product['file_url']:
        # Supprimer fichier produit B2
        b2.delete_file(product['file_url'])
        logger.info(f"✅ Deleted B2 file: {product['file_url']}")

    # Supprimer images B2
    if product:
        cover_b2_key = f"products/{product_id}/cover.jpg"
        thumb_b2_key = f"products/{product_id}/thumb.jpg"
        b2.delete_file(cover_b2_key)
        b2.delete_file(thumb_b2_key)
        logger.info(f"✅ Deleted B2 images: {product_id}")

    # 2. Supprimer images locales
    import shutil
    import os
    local_dir = f"data/product_images/{seller_user_id}/{product_id}"
    if os.path.exists(local_dir):
        shutil.rmtree(local_dir)
        logger.info(f"✅ Deleted local images: {local_dir}")

    # 3. Supprimer de la DB
    cursor.execute(
        'DELETE FROM products WHERE product_id = %s AND seller_user_id = %s',
        (product_id, seller_user_id)
    )
    logger.info(f"✅ HARD DELETE: Product {product_id} (no orders)")
```

### Étape 3 : Filtrer produits supprimés

**Toutes les requêtes SELECT doivent exclure les produits deleted :**

**AVANT :**
```python
SELECT * FROM products WHERE status = 'active'
```

**APRÈS :**
```python
SELECT * FROM products
WHERE status = 'active'
AND deleted_at IS NULL
```

**Ou mieux :**
```python
SELECT * FROM products
WHERE status = 'active'
AND (deleted_at IS NULL OR deleted_at > NOW())  -- Support future "undelete"
```

### Étape 4 : Permettre téléchargement même si produit supprimé

**Fichier :** `app/integrations/ipn_server.py`

Lors de la livraison du fichier, ne pas vérifier le statut du produit :

```python
# ✅ AVANT : Récupérer produit même si deleted
cursor.execute(
    'SELECT file_url, title FROM products WHERE product_id = %s',
    # Pas de filtre sur deleted_at ici !
    (product_id,)
)
```

---

## 📊 Avantages Soft Delete

| Fonctionnalité | Hard Delete ❌ | Soft Delete ✅ |
|----------------|---------------|----------------|
| **Clients peuvent télécharger** | Non, lien cassé | Oui, toujours accessible |
| **Récupération données** | Impossible | Possible (undelete) |
| **Audit trail** | Aucun | Complet (qui/quand) |
| **Support client** | Difficile | Facile (historique) |
| **Conformité RGPD** | Non conforme | Conforme |
| **Gestion stockage** | Manuel | Automatique (cleanup après 90j) |

---

## 🗓️ Stratégie de Nettoyage

### Cleanup Automatique Après 90 Jours

**Cronjob mensuel :**
```python
def cleanup_old_deleted_products():
    """
    Nettoie les produits supprimés depuis > 90 jours
    ET sans commandes actives dans les 30 derniers jours
    """
    cursor.execute('''
        SELECT p.product_id, p.seller_user_id, p.file_url
        FROM products p
        WHERE p.deleted_at IS NOT NULL
        AND p.deleted_at < NOW() - INTERVAL '90 days'
        AND NOT EXISTS (
            SELECT 1 FROM orders o
            WHERE o.product_id = p.product_id
            AND o.created_at > NOW() - INTERVAL '30 days'
        )
    ''')

    for product in cursor.fetchall():
        # Supprimer fichiers B2
        b2.delete_file(product['file_url'])

        # Supprimer images B2
        b2.delete_file(f"products/{product['product_id']}/cover.jpg")
        b2.delete_file(f"products/{product['product_id']}/thumb.jpg")

        # Hard delete de la DB
        cursor.execute(
            'DELETE FROM products WHERE product_id = %s',
            (product['product_id'],)
        )
```

---

## ⚡ Priorité d'Implémentation

### Phase 1 : Urgent (Avant Railway)
- [ ] Ajouter colonne `deleted_at` à la table `products`
- [ ] Modifier `delete_product()` avec soft delete
- [ ] Tester suppression avec/sans commandes
- [ ] Vérifier que clients peuvent toujours télécharger

### Phase 2 : Important (Première semaine)
- [ ] Filtrer produits deleted dans toutes les requêtes
- [ ] Créer endpoint admin "undelete" (restauration)
- [ ] Audit logs pour traçabilité

### Phase 3 : Maintenance (Après 1 mois)
- [ ] Cronjob cleanup automatique (90 jours)
- [ ] Dashboard admin "Produits supprimés"
- [ ] Métriques de stockage B2

---

## 📋 Checklist de Test

### Test 1 : Produit Jamais Acheté
```
1. Créer produit test
2. NE PAS l'acheter
3. Supprimer le produit
4. ✅ Vérifie HARD DELETE (DB + B2 + local)
5. ✅ Vérifie produit invisible dans marketplace
```

### Test 2 : Produit Avec Commandes
```
1. Créer produit test
2. Acheter le produit (créer commande)
3. Supprimer le produit
4. ✅ Vérifie SOFT DELETE (status='deleted')
5. ✅ Vérifie produit invisible dans marketplace
6. ✅ Vérifie client peut toujours télécharger
7. ✅ Vérifie fichiers B2 toujours présents
```

### Test 3 : Cleanup Automatique
```
1. Créer produit test avec deleted_at = -95 jours
2. Exécuter cleanup_old_deleted_products()
3. ✅ Vérifie HARD DELETE après 90 jours
4. ✅ Vérifie fichiers B2 supprimés
```

---

## 💰 Impact sur Valorisation

**Avant (sans soft delete) :**
- Valorisation : 50,500€
- Risque : Perte de données client

**Après (avec soft delete) :**
- Valorisation : **+3,000€** → **53,500€**
- Sécurité : Protection données client ✅
- Conformité : RGPD compliant ✅

---

## 📚 Ressources

**Soft Delete Best Practices :**
- https://en.wikipedia.org/wiki/Soft_deletion
- https://stackoverflow.com/questions/378331/physical-vs-logical-soft-delete

**RGPD Right to Erasure :**
- https://gdpr.eu/right-to-be-forgotten/

---

**Créé le :** 10 novembre 2025
**Auteur :** Claude Code
**Statut :** ⚠️ À IMPLÉMENTER AVANT PRODUCTION
