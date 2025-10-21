# 📚 Système de Bibliothèque - Documentation

## Vue d'ensemble

Système complet de gestion des achats utilisateurs avec fonctionnalités avancées :
- Bibliothèque personnelle
- Téléchargements illimités
- Système de notation et d'avis
- Support client intégré
- Contact vendeur

## 🗂️ Structure des fichiers

### Nouveaux fichiers créés

1. **`app/integrations/telegram/handlers/library_handlers.py`** (nouveau)
   - Handler complet pour toutes les fonctionnalités de bibliothèque
   - ~700 lignes de code
   - Gestion des avis, notes, téléchargements, support

2. **`sync_sales_counters.py`** (utilitaire)
   - Script de synchronisation des compteurs de ventes
   - À utiliser après modifications manuelles de la DB

### Fichiers modifiés

1. **`app/integrations/telegram/handlers/buy_handlers.py`**
   - Vérification d'achat existant (ligne 582)
   - Amélioration du preview PDF (ligne 704-793)
   - Fichier PDF affiché en premier, boutons en bas

2. **`app/integrations/telegram/keyboards.py`**
   - Ajout bouton "📚 Ma Bibliothèque" au menu principal (ligne 7-8)

3. **`app/integrations/telegram/callback_router.py`**
   - Routes bibliothèque (lignes 77-82)
   - Routes actions (lignes 254-306)
   - Download redirigé vers library_handlers

4. **`bot_mlt.py`**
   - Import et initialisation library_handlers (lignes 139-140)
   - Gestion état `waiting_for_review` (lignes 376-377)

5. **`app/core/database_init.py`**
   - Schema complet avec toutes les colonnes nécessaires
   - Migrations automatiques pour bases existantes
   - Création d'index unique pour les avis

## 🗄️ Schéma de base de données

### Table `orders` - Nouvelles colonnes
```sql
last_download_at TIMESTAMP  -- Date du dernier téléchargement
```

### Table `reviews` - Structure complète
```sql
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT,
    buyer_user_id INTEGER,
    order_id TEXT,
    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
    comment TEXT,
    review_text TEXT,              -- Nouveau
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Nouveau
    FOREIGN KEY (product_id) REFERENCES products (product_id),
    FOREIGN KEY (buyer_user_id) REFERENCES users (user_id),
    FOREIGN KEY (order_id) REFERENCES orders (order_id),
    UNIQUE(buyer_user_id, product_id)  -- Un seul avis par acheteur/produit
);
CREATE UNIQUE INDEX idx_reviews_buyer_product ON reviews(buyer_user_id, product_id);
```

### Table `support_tickets` - Nouvelles colonnes
```sql
product_id TEXT,      -- Produit concerné
issue_type TEXT,      -- Type de problème (file, content, access, other)
order_id TEXT,        -- Commande associée
seller_user_id INTEGER,
assigned_to_user_id INTEGER
```

## 🎯 Fonctionnalités

### 1. Bibliothèque personnelle
- **Route**: `library_menu`
- **Affichage**: Liste paginée des produits achetés (10 par page)
- **Informations**: Titre, vendeur, date d'achat, nombre de téléchargements
- **Vide**: Message encourageant à explorer les produits

### 2. Fiche produit acheté
- **Route**: `library_item_{product_id}`
- **Actions disponibles**:
  - 📥 Télécharger
  - ⭐ Noter/Avis
  - 📞 Contacter vendeur
  - 🚨 Signaler problème
- **Informations**: Prix payé, date d'achat, nombre de téléchargements, taille fichier

### 3. Téléchargement
- **Route**: `download_product_{product_id}`
- **Fonctionnalités**:
  - Vérification de l'achat
  - Compteur de téléchargements incrémenté
  - Date du dernier téléchargement enregistrée
  - Envoi du fichier complet
  - Gestion d'erreurs (fichier introuvable)

### 4. Système de notation
- **Route**: `rate_product_{product_id}` → `set_rating_{product_id}_{rating}`
- **Notes**: 1 à 5 étoiles
- **Interface**: Sélection visuelle avec étoiles
- **Après notation**: Proposition d'ajouter un avis textuel

### 5. Avis textuels
- **Route**: `write_review_{product_id}`
- **État**: `waiting_for_review`
- **Validation**: Minimum 10 caractères
- **Modification**: Possibilité de mettre à jour son avis
- **Affichage**: Visible sur la fiche produit

### 6. Contact vendeur
- **Route**: `contact_seller_{product_id}`
- **Conditions**: Uniquement pour produits achetés
- **Options**:
  - 💬 Envoyer message
  - 🚨 Signaler problème

### 7. Signalement de problèmes
- **Route**: `report_issue_{product_id}`
- **Types de problèmes**:
  - 📁 Fichier ne fonctionne pas
  - ❌ Contenu incorrect
  - 🔒 Problème d'accès
  - 💬 Autre problème
- **Création**: Ticket support automatique
- **Suivi**: Notification des mises à jour

### 8. Protection contre double achat
- **Vérification**: Avant affichage du paiement
- **Message**: "Vous possédez déjà ce produit"
- **Actions**: Redirection vers bibliothèque ou téléchargement direct

### 9. Amélioration preview
- **PDF en premier**: Image de la première page affichée en haut
- **Boutons en bas**: Actions faciles d'accès
- **Emoji**: 👇 au lieu de 👆 pour indiquer les boutons

## 📋 Routes callback complètes

```python
# Bibliothèque principale
'library_menu' → show_library(page=0)
'library_page_{page}' → show_library(page=page)

# Fiche produit
'library_item_{product_id}' → show_library_item()

# Téléchargement
'download_product_{product_id}' → download_product()

# Notation
'rate_product_{product_id}' → rate_product_prompt()
'set_rating_{product_id}_{rating}' → set_rating()
'write_review_{product_id}' → write_review_prompt()

# Support
'contact_seller_{product_id}' → contact_seller()
'report_issue_{product_id}' → report_issue()
'issue_type_{type}_{product_id}' → handle_issue_type()
```

## 🔧 Script utilitaire

### sync_sales_counters.py

Synchronise les compteurs de ventes avec la base de données.

**Utilisation**:
```bash
python3 sync_sales_counters.py
```

**Fonctionnalités**:
1. Réinitialise tous les compteurs
2. Recalcule les ventes par produit
3. Recalcule les ventes par vendeur
4. Recalcule le revenu total par vendeur
5. Affiche un rapport complet

**Quand l'utiliser**:
- Après modification manuelle de `payment_status` dans la DB
- Après import/migration de données
- Pour corriger des incohérences dans les compteurs

## 🚀 Déploiement

### Nouvelle installation

Les tables seront créées automatiquement avec le schéma complet lors du premier lancement :

```python
from app.core.database_init import DatabaseInitService
from app.core.settings import settings

db = DatabaseInitService(settings.DATABASE_PATH)
db.init_all_tables()
```

### Installation existante

Les migrations s'appliquent automatiquement :
1. Colonnes manquantes ajoutées
2. Index créés
3. Contraintes appliquées

Aucune action manuelle nécessaire.

## 🧪 Tests

### Tester la bibliothèque vide
1. Se connecter avec un compte sans achats
2. Cliquer sur "📚 Ma Bibliothèque"
3. Vérifier le message d'encouragement

### Tester un achat complet
1. Marquer un paiement comme 'completed' :
```sql
UPDATE orders SET payment_status = 'completed', completed_at = CURRENT_TIMESTAMP
WHERE order_id = 'XXX';
```
2. Synchroniser les compteurs : `python3 sync_sales_counters.py`
3. Accéder à la bibliothèque
4. Tester toutes les fonctionnalités

### Tester la protection double achat
1. Avoir un produit dans sa bibliothèque
2. Cliquer "Acheter" sur le même produit
3. Vérifier la redirection vers la bibliothèque

## 📊 Statistiques disponibles

### Par utilisateur
- Nombre de produits achetés
- Nombre de téléchargements par produit
- Date du dernier téléchargement
- Avis laissés

### Par produit
- Nombre de ventes (compteur synchronisé)
- Nombre d'avis
- Note moyenne (à implémenter dans les prochaines versions)

### Par vendeur
- Nombre total de ventes
- Revenu total
- Produits les plus vendus

## 🔐 Sécurité

### Vérifications
- ✅ L'utilisateur possède le produit avant téléchargement
- ✅ Un seul avis par utilisateur par produit (index unique)
- ✅ Validation de la longueur minimale des avis
- ✅ Vérification de l'existence du fichier

### Logs
Tous les téléchargements et actions sont loggés avec :
- User ID
- Product ID
- Timestamp
- Action effectuée

## 🐛 Résolution de problèmes

### Les compteurs ne correspondent pas
```bash
python3 sync_sales_counters.py
```

### Erreur "table has no column named X"
Les migrations ne se sont pas appliquées. Relancer :
```python
from app.core.database_init import DatabaseInitService
DatabaseInitService().init_all_tables()
```

### Fichier introuvable au téléchargement
Vérifier que `main_file_path` contient un chemin relatif, pas absolu.
Le système reconstruit le chemin complet : `settings.UPLOADS_DIR + main_file_path`

## 📝 TODO / Améliorations futures

- [ ] Calcul automatique de la note moyenne des produits
- [ ] Notification vendeur lors d'un nouvel avis
- [ ] Export de la bibliothèque en PDF/CSV
- [ ] Historique des téléchargements
- [ ] Partage de produits (cadeaux)
- [ ] Wishlist / Liste de souhaits
- [ ] Système de recommandations basé sur les achats

## 🎉 Résumé

Le système de bibliothèque est maintenant **100% opérationnel** avec :
- ✅ Toutes les fonctionnalités demandées
- ✅ Base de données complète et migrée
- ✅ Interface utilisateur intuitive
- ✅ Protection contre les doubles achats
- ✅ Preview amélioré
- ✅ Support client intégré
- ✅ Script de maintenance

**Lignes de code ajoutées** : ~1500
**Nouveaux handlers** : 1
**Tables modifiées** : 3
**Routes ajoutées** : 15+