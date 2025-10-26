# 🔍 AUDIT COMPLET DU BOT FERUS - 26 OCTOBRE 2025

**Statut:** 🚧 CORRECTIFS EN COURS
**Responsable:** Claude
**Objectif:** Identifier et corriger tous les bugs, incohérences et fonctionnalités manquantes

---

## ✅ CORRECTIFS DÉJÀ APPLIQUÉS

### 1. ✅ Mapping multi-compte supprimé
**Problème:** Système de mapping `bot.get_seller_id()` inutilisé causant de la confusion
**Solution:** Remplacé toutes les occurrences par accès direct `user_id`
**Fichiers modifiés:** `sell_handlers.py`
**Impact:** ✅ Code simplifié, mapping supprimé

### 2. ✅ Calcul taux de change masqué
**Problème:** Affichage du calcul `47.0€ × 1.0278 = 48.31€` trop complexe
**Solution:** Affichage simplifié : `Prix total : 48.31€ (Frais inclus)`
**Fichiers modifiés:** `buy_handlers.py` ligne 593
**Impact:** ✅ UX améliorée, moins de friction cognitive

### 3. ✅ Duplication de code éliminée
**Problème:** ~67 lignes de code dupliqué (vérification ownership + états)
**Solution:** Helpers `_verify_product_ownership()` et `_set_editing_state()`
**Fichiers modifiés:** `sell_handlers.py`
**Impact:** ✅ -4% lignes, maintenabilité améliorée

---

## 🔴 BUGS CRITIQUES IDENTIFIÉS

### 🔴 BUG #1: Affichage ventes dans carousel buyer
**Priorité:** CRITIQUE 🔴
**Localisation:** `buy_handlers.py` - carousel produits
**Description:**
- Les ventes ne s'affichent pas correctement dans le carousel acheteur
- Probablement lié au compteur `sales_count`

**À vérifier:**
```python
# buy_handlers.py - ligne ~XXX
# Vérifier que product.get('sales_count', 0) récupère bien les données
```

**Actions requises:**
1. Trouver la fonction `show_product_carousel` dans buy_handlers
2. Vérifier query SQL récupération `sales_count`
3. S'assurer que la table orders met à jour le compteur
4. Ajouter logs pour debug

**Fichiers à analyser:**
- `app/integrations/telegram/handlers/buy_handlers.py`
- `app/domain/repositories/product_repo.py` (get_product_by_id)
- `app/domain/repositories/order_repo.py` (mise à jour compteur)

---

### 🔴 BUG #2: Analytics dans paramètres vendeur
**Priorité:** HAUTE 🟠
**Localisation:** `sell_handlers.py` - seller_analytics()
**Description:**
- Les analytics ne s'affichent pas correctement dans les paramètres vendeur
- Possiblement lié au bouton "Analytics" dans le dashboard

**À vérifier:**
```python
# Vérifier que seller_analytics() récupère les bonnes données
# Vérifier callback_data 'seller_analytics_visual'
```

**Actions requises:**
1. Tester le bouton Analytics depuis le dashboard vendeur
2. Vérifier les queries SQL dans seller_analytics()
3. S'assurer que les graphiques se génèrent correctement

---

### 🟡 BUG #3: Gestion des états conflictuels
**Priorité:** HAUTE 🟠
**Localisation:** `bot_mlt.py` - State manager
**Description:**
- Si un utilisateur commence un ticket support puis se connecte comme vendeur, le bot interprète la réponse comme liée au support
- Problème de gestion d'états non réinitialisés

**Exemple de scénario problématique:**
```
1. User: /support
2. Bot: "Décrivez votre problème"
3. User: /sell (change de contexte)
4. Bot: Affiche menu vendeur
5. User: Tape "test@example.com"
6. Bot: ❌ Interprète comme message support au lieu d'email vendeur
```

**Solution proposée:**
```python
# Dans bot_mlt.py - Avant chaque changement de workflow majeur

def reset_conflicting_states(user_id, keep=None):
    """Réinitialise les états qui pourraient entrer en conflit"""
    all_states = [
        'waiting_support_message',
        'creating_seller',
        'waiting_seller_login_email',
        'editing_product_title',
        'editing_product_price',
        'editing_product_description',
        'editing_seller_name',
        'editing_seller_bio',
        'adding_product',
        'waiting_payment_proof'
    ]

    states_to_reset = {state: False for state in all_states if keep is None or state not in keep}
    bot.state_manager.update_state(user_id, **states_to_reset)
```

**Actions requises:**
1. Auditer TOUS les points d'entrée de workflows (/buy, /sell, /support, /start)
2. Ajouter `reset_conflicting_states()` avant chaque workflow
3. Tester transitions: support→sell, buy→sell, sell→buy

---

## 🟡 FONCTIONNALITÉS NON IMPLÉMENTÉES

### 🟡 MANQUE #1: Fonction suspendre produit
**Priorité:** MOYENNE 🟡
**Statut:** ❓ À vérifier
**Description:**
- La spec mentionne "Activer/Désactiver" produit
- Fonction `toggle_product_status()` existe mais à tester

**Test à faire:**
```python
# Depuis carousel vendeur, cliquer "Désactiver"
# Vérifier que:
# 1. Le produit passe à status='inactive' en DB
# 2. Le produit n'apparaît plus dans /buy
# 3. Le vendeur peut le réactiver
```

**Code existant:**
```python
# sell_handlers.py ligne ~1670
async def toggle_product_status(self, bot, query, product_id, lang):
    # Vérifier que cette fonction marche correctement
```

---

### 🟡 MANQUE #2: Modification mot de passe vendeur
**Priorité:** BASSE 🟢
**Statut:** ❌ Non implémenté
**Description:**
- Bouton "🔐 Mdp" ajouté dans paramètres mais fonction manquante
- Callback `'edit_seller_password'` non géré

**Actions requises:**
1. Créer `edit_seller_password_prompt()` dans sell_handlers.py
2. Créer `process_seller_password_update()` pour validation
3. Hasher le mot de passe avec bcrypt
4. Ajouter callback dans callback_router.py

---

### 🟡 MANQUE #3: Modification email vendeur
**Priorité:** BASSE 🟢
**Statut:** ❌ Non implémenté
**Description:**
- Bouton "📧 Mail" ajouté dans paramètres mais fonction manquante
- Callback `'edit_seller_email'` non géré

**Actions requises:**
1. Créer `edit_seller_email_prompt()` dans sell_handlers.py
2. Vérifier que l'email n'est pas déjà utilisé
3. Valider format email
4. Ajouter callback dans callback_router.py

---

### 🟡 MANQUE #4: Modification adresse Solana
**Priorité:** MOYENNE 🟡
**Statut:** ❌ Non implémenté
**Description:**
- Bouton "💰 Adresse" ajouté dans paramètres mais fonction manquante
- Callback `'edit_solana_address'` non géré
- CRITIQUE car touche aux paiements

**Actions requises:**
1. Créer `edit_solana_address_prompt()` dans sell_handlers.py
2. Valider format Solana (32-44 caractères)
3. Demander confirmation (adresse de paiement critique)
4. Ajouter callback dans callback_router.py

---

### 🟡 MANQUE #5: Désactivation temporaire compte vendeur
**Priorité:** BASSE 🟢
**Statut:** ❌ Non implémenté
**Description:**
- Bouton "🔕 Désactiver" ajouté dans paramètres mais fonction manquante
- Callback `'disable_seller_account'` non géré
- Différent de suppression (doit être réversible)

**Actions requises:**
1. Créer `disable_seller_account_prompt()` dans sell_handlers.py
2. Mettre `is_seller = FALSE` temporairement
3. Cacher produits mais conserver données
4. Permettre réactivation ultérieure
5. Ajouter callback dans callback_router.py

---

## 📝 TEXTES INCOHÉRENTS IDENTIFIÉS

### 📝 INCOHÉRENCE #1: Boutons mélangés FR/EN
**Localisation:** Divers fichiers
**Exemple:**
```python
# sell_handlers.py
InlineKeyboardButton("Dashboard", callback_data='seller_dashboard')  # ❌ EN
InlineKeyboardButton("🔙 Retour", callback_data='back')  # ✅ FR
```

**Solution:** Utiliser `i18n(lang, 'btn_dashboard')` partout

---

### 📝 INCOHÉRENCE #2: Messages d'erreur non traduits
**Localisation:** `sell_handlers.py`, `buy_handlers.py`
**Exemple:**
```python
await update.message.reply_text("Product not found")  # ❌ Hard-coded EN
```

**Solution:** Créer clés i18n pour tous les messages

---

### 📝 INCOHÉRENCE #3: Format des prix
**Localisation:** Divers
**Problème:**
- Parfois `49.99€`, parfois `€49.99`, parfois `49.99 EUR`
- Pas de cohérence

**Solution:** Standardiser sur `49.99€` partout (FR) et `€49.99` (EN)

---

## 🔧 CALLBACKS NON GÉRÉS

### Callbacks manquants dans callback_router.py:

```python
# À ajouter dans callback_router.py

'edit_seller_password': sell_handlers.edit_seller_password_prompt,
'edit_seller_email': sell_handlers.edit_seller_email_prompt,
'edit_solana_address': sell_handlers.edit_solana_address_prompt,
'disable_seller_account': sell_handlers.disable_seller_account_prompt,
'edit_field_description_{product_id}': sell_handlers.edit_product_field,
```

---

## 🚨 AXES D'AMÉLIORATION PRIORITAIRES

### 1. 🔴 CRITIQUE: Tester flux achat complet
**Actions:**
- [ ] Créer produit test comme vendeur
- [ ] Acheter comme buyer
- [ ] Vérifier paiement reçu
- [ ] Vérifier fichier téléchargé
- [ ] Vérifier email confirmation

### 2. 🟠 HAUTE: Validation des états
**Actions:**
- [ ] Mapper tous les états possibles
- [ ] Créer matrice de transitions valides
- [ ] Implémenter reset_conflicting_states() partout
- [ ] Tester toutes les transitions

### 3. 🟡 MOYENNE: Compléter paramètres vendeur
**Actions:**
- [ ] Implémenter modification mot de passe
- [ ] Implémenter modification email
- [ ] Implémenter modification adresse Solana
- [ ] Implémenter désactivation compte
- [ ] Tester chaque fonctionnalité

### 4. 🟢 BASSE: Uniformiser i18n
**Actions:**
- [ ] Créer fichier i18n complet (FR/EN)
- [ ] Remplacer tous les textes hard-coded
- [ ] Tester changement de langue

---

## 📋 POLITIQUE D'UTILISATION VENDEURS

**À rédiger dans:** `docs/SELLER_TERMS_OF_SERVICE.md`

**Sections requises:**
1. **Contenu autorisé**
   - Produits digitaux uniquement
   - Pas de contenu illégal, pirate, ou NSFW
   - Propriété intellectuelle respectée

2. **Qualité du produit**
   - Fichier fonctionnel et complet
   - Description honnête
   - Pas de fausses promesses

3. **Prix et paiements**
   - Prix min 1€, max 5000€
   - Frais 2.78% inclus automatiquement
   - Paiements en crypto uniquement (ETH, BTC, SOL, USDT)
   - Délai réception paiement: 24-48h

4. **Support client**
   - Répondre aux questions acheteurs sous 48h
   - Fournir support technique si nécessaire
   - Remboursement si produit non-conforme

5. **Suspension/Ban**
   - Arnaques → Ban permanent
   - Produits illégaux → Ban + signalement
   - Mauvaise qualité → Avertissement puis suspension
   - Fausses descriptions → Suppression produit

6. **Données personnelles**
   - Email utilisé pour notifications uniquement
   - Adresse Solana stockée de manière sécurisée
   - Pas de revente données à tiers

---

## 🧪 TESTS À EFFECTUER AVANT MISE EN PRODUCTION

### Tests Workflow Vendeur
- [ ] Création compte vendeur (email + Solana)
- [ ] Ajout produit complet (titre, desc, prix, fichier, image)
- [ ] Modification titre produit
- [ ] Modification prix produit
- [ ] Modification description produit
- [ ] Désactivation produit
- [ ] Réactivation produit
- [ ] Suppression produit
- [ ] Modification nom vendeur
- [ ] Modification bio vendeur
- [ ] Visualisation analytics
- [ ] Déconnexion vendeur
- [ ] Reconnexion vendeur

### Tests Workflow Acheteur
- [ ] Parcourir catégories
- [ ] Voir carousel produits
- [ ] Cliquer "Acheter"
- [ ] Choisir crypto (ETH, BTC, SOL, USDT)
- [ ] Voir adresse de paiement
- [ ] Envoyer paiement test
- [ ] Confirmer "J'ai payé"
- [ ] Recevoir email confirmation
- [ ] Télécharger fichier
- [ ] Laisser avis

### Tests Transitions d'États
- [ ] /start → /buy → /sell → /start (sans erreur)
- [ ] /support → /sell (réinitialisation état support)
- [ ] Ajout produit → Annulation → Nouvel ajout
- [ ] Modification titre → Annulation → Dashboard
- [ ] Paiement expiré → Nouvelle tentative

### Tests Sécurité
- [ ] Acheter son propre produit (doit bloquer)
- [ ] Modifier produit d'un autre vendeur (doit bloquer)
- [ ] SQL injection dans titre produit
- [ ] XSS dans description
- [ ] Upload fichier > 10MB (doit rejeter)
- [ ] Upload fichier exécutable malveillant
- [ ] Adresse Solana invalide (doit rejeter)

---

## 📊 MÉTRIQUES DE SUCCÈS

### Avant corrections
- ❌ Mapping inutilisé causant confusion
- ❌ Calcul prix trop complexe
- ❌ 67 lignes de code dupliqué
- ❌ États conflictuels non gérés
- ❌ 5 fonctionnalités manquantes
- ❌ Textes mélangés FR/EN

### Après corrections (objectif)
- ✅ Mapping supprimé, code simplifié
- ✅ Prix affiché clairement
- ✅ Code optimisé, helpers créés
- ✅ États gérés correctement
- ✅ Toutes fonctionnalités implémentées
- ✅ i18n complet FR/EN

---

## 🚀 PROCHAINES ÉTAPES IMMÉDIATES

1. **ANALYSER** carousel buyer (affichage ventes)
2. **ANALYSER** analytics vendeur
3. **TESTER** fonction suspendre produit
4. **IMPLÉMENTER** reset_conflicting_states() global
5. **IMPLÉMENTER** fonctions paramètres manquantes
6. **RÉDIGER** politique d'utilisation vendeurs
7. **TESTER** flux complet end-to-end
8. **CORRIGER** tous les textes incohérents

---

**Date création:** 26 octobre 2025
**Dernière mise à jour:** 26 octobre 2025
**Status:** 🚧 En cours de correction
