# ✅ CHECKLIST TESTS MANUELS - BUYER WORKFLOW V2

**Date:** 2025-10-18
**Testeur:** _____________
**Version bot:** V2

---

## 🚀 PRÉPARATION

- [ ] Bot lancé: `python3 bot_mlt.py`
- [ ] Bot répond au `/start`
- [ ] Au moins 2-3 produits existent dans DB
- [ ] Au moins 2 catégories ont des produits

---

## 📦 TEST 1: Navigation Carousel

### Accès
- [ ] `/start` → Bouton "Acheter"
- [ ] Bouton "Parcourir catégories"
- [ ] Liste des catégories s'affiche

### Sélection Catégorie
- [ ] Clic sur une catégorie (ex: Finance & Crypto)
- [ ] Card produit s'affiche avec:
  - [ ] Image (ou placeholder)
  - [ ] Titre en gras
  - [ ] Prix visible (💰 XX.XX €)
  - [ ] Description tronquée (~2-3 lignes, termine par "...")
  - [ ] Vendeur + nombre ventes
  - [ ] Catégorie en bas

### Navigation Produits
- [ ] Boutons ⬅️ 1/5 ➡️ présents
- [ ] Clic ➡️ → affiche produit suivant
- [ ] Clic ⬅️ → affiche produit précédent
- [ ] Premier produit: bouton ⬅️ désactivé (espace vide)
- [ ] Dernier produit: bouton ➡️ désactivé (espace vide)
- [ ] Compteur 1/5 s'update correctement

---

## 🔀 TEST 2: Navigation Catégories (NOUVEAU V2)

### Flèches Catégories
- [ ] Ligne 4 du keyboard affiche: [←] [Finance & Crypto] [→]
- [ ] Clic → passe à catégorie suivante
- [ ] Clic ← retourne à catégorie précédente
- [ ] Nom catégorie tronqué si > 20 chars
- [ ] Navigation circulaire (après dernière → première)

---

## 📄 TEST 3: Page Détails

### Accès
- [ ] Depuis carousel: clic "ℹ️ Détails"
- [ ] Card détails s'affiche avec:
  - [ ] Image
  - [ ] Titre
  - [ ] Prix
  - [ ] **Description COMPLÈTE** (pas tronquée)
  - [ ] Métadonnées (catégorie, taille fichier)
  - [ ] Vendeur + stats

### Boutons
- [ ] Bouton "🛒 ACHETER" présent (pleine largeur)
- [ ] Bouton "⭐ Avis" présent (NOUVEAU V2)
- [ ] Bouton "👁️ Preview" présent
- [ ] Bouton "📋 Réduire" présent (NOUVEAU V2)
- [ ] Bouton "🔙 Précédent" présent

---

## ⭐ TEST 4: Page Avis (NOUVEAU V2)

### Accès
- [ ] Depuis page détails: clic "⭐ Avis"

### Si Aucun Avis
- [ ] Message "Aucun avis pour le moment"
- [ ] Message encourageant "Soyez le premier..."
- [ ] Bouton "🛒 ACHETER" présent
- [ ] Bouton "🔙 Précédent" → retour détails

### Si Avis Existent
- [ ] Note moyenne affichée (⭐⭐⭐⭐⭐ 4.8/5)
- [ ] Total avis affiché
- [ ] Liste de max 5 avis:
  - [ ] Nom acheteur (👤)
  - [ ] Rating étoiles
  - [ ] Texte avis (tronqué à 150 chars si long)
  - [ ] Temps relatif (🕒 "Il y a 3 jours")

### Pagination Avis
- [ ] Si > 5 avis: boutons ⬅️ 1/3 ➡️
- [ ] Navigation entre pages fonctionne
- [ ] Compteur s'update

---

## 📋 TEST 5: Bouton Réduire (NOUVEAU V2)

### Fonctionnalité
- [ ] Depuis page détails: clic "📋 Réduire"
- [ ] Retourne au carousel (card courte)
- [ ] **Préserve l'index:** même produit affiché
- [ ] **Préserve la catégorie:** même catégorie
- [ ] Description tronquée à nouveau visible
- [ ] Navigation ⬅️ ➡️ fonctionne

---

## 🛒 TEST 6: Bouton ACHETER (Partout)

### Accessibilité
- [ ] Présent dans carousel
- [ ] Présent dans page détails
- [ ] Présent dans page avis
- [ ] Présent dans preview (si implémenté)

### Fonctionnalité
- [ ] Clic "ACHETER" → page sélection crypto
- [ ] Texte: "💳 PAIEMENT"
- [ ] Titre + prix produit affichés

---

## 💰 TEST 7: Layout Crypto (AMÉLIORÉ V2)

### Layout Grille 2x2
- [ ] **Ligne 1:** [₿ BTC] [⟠ ETH] (côte à côte)
- [ ] **Ligne 2:** [◎ SOLANA ⚡ 1-3 min] (pleine largeur)
- [ ] **Ligne 3:** [🟢 USDC] [₮ USDT] (côte à côte)
- [ ] **Ligne 4:** [🔙 Précédent]

### Fonctionnalité
- [ ] Clic BTC → page paiement BTC
- [ ] Clic ETH → page paiement ETH
- [ ] Clic SOLANA → page paiement SOL
- [ ] Clic USDC → page paiement USDC
- [ ] Clic USDT → page paiement USDT
- [ ] Bouton Précédent → retour page produit

---

## 🔄 TEST 8: Workflow Complet End-to-End

### Scénario Complet
1. [ ] `/start` → Acheter → Parcourir catégories
2. [ ] Choisir catégorie → Carousel s'affiche
3. [ ] Naviguer avec ➡️ (2-3 produits)
4. [ ] Tester navigation catégories (→)
5. [ ] Clic "Détails" sur un produit
6. [ ] Page détails affiche description complète
7. [ ] Clic "Avis" → Page avis s'affiche
8. [ ] Clic "🔙 Précédent" → Retour détails
9. [ ] Clic "Réduire" → Retour carousel (même index)
10. [ ] Clic "ACHETER" → Sélection crypto
11. [ ] Layout grille 2x2 s'affiche
12. [ ] Clic SOLANA → Page paiement

**Temps total:** _________ secondes
**Nombre de clics:** _________ (objectif: 2-3 clics pour achat simple)

---

## 🐛 BUGS IDENTIFIÉS

### Bug #1
- **Description:** __________________________________________________
- **Étapes reproduction:** __________________________________________
- **Sévérité:** [ ] Critique [ ] Majeur [ ] Mineur [ ] Cosmétique

### Bug #2
- **Description:** __________________________________________________
- **Étapes reproduction:** __________________________________________
- **Sévérité:** [ ] Critique [ ] Majeur [ ] Mineur [ ] Cosmétique

### Bug #3
- **Description:** __________________________________________________
- **Étapes reproduction:** __________________________________________
- **Sévérité:** [ ] Critique [ ] Majeur [ ] Mineur [ ] Cosmétique

---

## ✅ VALIDATION FINALE

- [ ] Tous les tests passent
- [ ] Aucun bug critique/majeur
- [ ] Workflow 2-3 clics confirmé
- [ ] UX moderne et fluide
- [ ] Aucune régression ancien workflow

---

**Signature testeur:** _____________
**Date:** _____________
**Statut:** [ ] ✅ APPROUVÉ  [ ] ⚠️ AMÉLIORATIONS REQUISES  [ ] ❌ REJETÉ

**Commentaires:**
___________________________________________________________________
___________________________________________________________________
___________________________________________________________________
