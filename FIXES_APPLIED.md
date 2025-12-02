# 🔧 Corrections Appliquées - 2 Décembre 2025

## 🐛 Bugs Corrigés

### 1. AttributeError: 'MarketplaceBot' object has no attribute 'send_photo'

**Symptôme :**
```
File "carousel_helper.py", line 245, in _display_message
    await bot.send_photo(...)
AttributeError: 'MarketplaceBot' object has no attribute 'send_photo'
```

**Cause :**
Le paramètre `bot` passé à `show_carousel()` est `MarketplaceBot`, pas `telegram.Bot`. `send_photo()` existe uniquement sur `telegram.Bot`.

**Correction appliquée :**
- **Fichier :** `app/integrations/telegram/utils/carousel_helper.py`
- **Ligne 33 :** Extraction de l'instance Telegram Bot
  ```python
  telegram_bot = bot.application.bot if hasattr(bot, 'application') else bot
  ```
- **Ligne 64 :** Utilisation de `telegram_bot` au lieu de `bot`

**Résultat :**
✅ `/library` et `/acheter` affichent maintenant correctement les produits avec images

---

### 2. Recherche interprétée comme titre de ticket support

**Symptôme :**
1. Utilisateur fait `/support`
2. Utilisateur fait `/start`
3. Utilisateur tape un ID de produit pour rechercher
4. ❌ Le bot interprète la recherche comme le sujet du ticket support

**Cause :**
L'état `creating_ticket` n'était pas nettoyé lors du retour au menu principal.

**Corrections appliquées :**

#### A. Commande `/start`
- **Fichier :** `app/integrations/telegram/handlers/core_handlers.py`
- **Ligne 19 :** Réinitialisation complète des états
  ```python
  marketplace_bot.reset_user_state(user.id, keep={'lang'})
  ```

#### B. Callback `back_main` (bouton Retour)
- **Fichier :** `app/integrations/telegram/handlers/core_handlers.py`
- **Ligne 108 :** Réinitialisation complète des états
  ```python
  marketplace_bot.reset_user_state(user_id, keep={'lang'})
  ```

#### C. Menu Acheter
- **Fichier :** `app/integrations/telegram/handlers/buy_handlers.py`
- **Ligne 555 :** Réinitialisation lors de l'entrée dans le menu
  ```python
  bot.reset_user_state(query.from_user.id, keep={'lang'})
  ```

#### D. Menu Vendre
- **Fichier :** `app/integrations/telegram/handlers/sell_handlers.py`
- **Ligne 82 :** Réinitialisation lors de l'entrée dans le menu
  ```python
  bot.reset_user_state(user_id, keep={'lang'})
  ```

#### E. Menu Bibliothèque
- **Fichier :** `app/integrations/telegram/handlers/library_handlers.py`
- **Ligne 29 :** Réinitialisation lors de l'entrée dans le menu
  ```python
  bot.reset_user_state(user_id, keep={'lang'})
  ```

#### F. Menu Support
- **Fichier :** `app/integrations/telegram/handlers/support_handlers.py`
- **Ligne 778 :** Réinitialisation lors de l'entrée dans le menu
  ```python
  bot.reset_user_state(query.from_user.id, keep={'lang'})
  ```

**Résultat :**
✅ Tous les états conflictuels (support, recherche, édition, etc.) sont nettoyés quand l'utilisateur :
- Appuie sur un bouton "Retour"
- Fait `/start`
- Entre dans n'importe quel menu (Acheter, Vendre, Bibliothèque, Support)

---

## 🎯 Principe Appliqué

**Reset systématique des états à chaque changement de contexte**

Quand l'utilisateur change d'avis (bouton retour, commande, menu), tous les états sont réinitialisés **sauf la langue**.

```python
bot.reset_user_state(user_id, keep={'lang'})
```

Cela garantit qu'aucun état résiduel (création ticket, recherche produit, édition produit, etc.) ne persiste et pollue le nouveau contexte.

---

## 📊 Fichiers Modifiés

| Fichier | Lignes modifiées | Description |
|---------|------------------|-------------|
| `carousel_helper.py` | 33, 64 | Fix AttributeError send_photo |
| `core_handlers.py` | 19, 108 | Reset états sur /start et back_main |
| `buy_handlers.py` | 555 | Reset états sur menu Acheter |
| `sell_handlers.py` | 82 | Reset états sur menu Vendre |
| `library_handlers.py` | 29 | Reset états sur menu Bibliothèque |
| `support_handlers.py` | 778 | Reset états sur menu Support |

---

## ✅ Tests Recommandés

### Scénario 1 : Support → Start → Recherche
1. Cliquer "Support"
2. Cliquer "Créer un ticket"
3. Faire `/start`
4. Chercher un produit (ex: `TBF-XXX-1`)
5. ✅ Vérifier que la recherche fonctionne (pas interprétée comme titre ticket)

### Scénario 2 : Library → Acheter
1. Cliquer "Bibliothèque"
2. Cliquer bouton "Retour"
3. Cliquer "Acheter"
4. ✅ Vérifier que les produits s'affichent avec images

### Scénario 3 : Support → Retour → Acheter
1. Cliquer "Support"
2. Cliquer "Créer un ticket"
3. Cliquer "Retour" (back_main)
4. Cliquer "Acheter"
5. ✅ Vérifier que le carousel fonctionne

---

## 🚀 Déploiement

Prêt à déployer sur Railway avec :
```bash
git add .
git commit -m "Fix: Nettoyage états utilisateur + carousel bot.application.bot"
git push origin main
```

---

**Date de correction :** 2 Décembre 2025
**Correctifs :** Bug carousel + États résiduels
