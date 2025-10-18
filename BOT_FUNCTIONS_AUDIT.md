# 🔍 AUDIT COMPLET FONCTIONS BOT TECHBOT MARKETPLACE

## 📊 **Résumé**
- **Total fonctions**: 82
- **Total routes CallbackRouter**: 40
- **Handlers**: 7 classes

---

## 🎯 **1. CORE HANDLERS** (5 fonctions)

### CoreHandlers
```python
CoreHandlers.back_to_main(self, query, lang)
CoreHandlers.back_to_main_with_bot(self, marketplace_bot, query, lang)
CoreHandlers.change_language(self, bot, query, new_lang)
CoreHandlers.help_command(self, marketplace_bot, update, context)
CoreHandlers.start_command(self, marketplace_bot, update, context)
```

---

## 🛒 **2. BUY HANDLERS** (10 fonctions)

### BuyHandlers
```python
BuyHandlers.browse_categories(self, bot, query, lang: str) -> None
BuyHandlers.buy_menu(self, bot, query, lang: str) -> None
BuyHandlers.check_payment_handler(self, bot, query, order_id, lang)
BuyHandlers.download_product(self, bot, query, context, product_id, lang)
BuyHandlers.process_product_search(self, bot, update, message_text)
BuyHandlers.search_product_prompt(self, bot, query, lang: str) -> None
BuyHandlers.show_category_products(self, bot, query, category_key: str, lang: str) -> None
BuyHandlers.show_my_library(self, bot, query, lang)
BuyHandlers.show_product_details(self, bot, query, product_id: str, lang: str) -> None
BuyHandlers.show_product_details_from_search(self, bot, update, product)
```

---

## 📚 **3. SELL HANDLERS** (18 fonctions)

### SellHandlers
```python
SellHandlers.add_product_prompt(self, bot, query, lang: str)
SellHandlers.copy_address(self, bot, query, lang)
SellHandlers.create_seller_prompt(self, bot, query, lang: str)
SellHandlers.delete_seller_confirm(self, bot, query)
SellHandlers.delete_seller_prompt(self, bot, query)
SellHandlers.payout_history(self, bot, query, lang)
SellHandlers.process_product_addition(self, bot, update, message_text: str)
SellHandlers.process_seller_creation(self, bot, update, message_text: str)
SellHandlers.process_seller_login(self, bot, update, message_text: str)
SellHandlers.process_seller_settings(self, bot, update, message_text: str)
SellHandlers.sell_menu(self, bot, query, lang: str)
SellHandlers.seller_analytics(self, bot, query, lang: str)
SellHandlers.seller_dashboard(self, bot, query, lang: str)
SellHandlers.seller_login_menu(self, bot, query, lang: str)
SellHandlers.seller_logout(self, bot, query)
SellHandlers.seller_settings(self, bot, query, lang: str)
SellHandlers.show_my_products(self, bot, query, lang: str)
SellHandlers.show_wallet(self, bot, query, lang: str)
```

---

## 🔧 **4. ADMIN HANDLERS** (16 fonctions)

### AdminHandlers
```python
AdminHandlers.admin_export_payouts(self, query, lang)
AdminHandlers.admin_export_users(self, query, lang)
AdminHandlers.admin_mark_all_payouts_paid(self, query, lang)
AdminHandlers.admin_marketplace_stats(self, query, lang)
AdminHandlers.admin_menu(self, query, lang)
AdminHandlers.admin_payouts(self, query, lang)
AdminHandlers.admin_products(self, query, lang)
AdminHandlers.admin_search_product_prompt(self, query, lang)
AdminHandlers.admin_search_user_prompt(self, query, lang)
AdminHandlers.admin_suspend_product_prompt(self, query, lang)
AdminHandlers.admin_users(self, query, lang)
AdminHandlers.commissions_handler(self, query, lang)
AdminHandlers.export_products(self, query, lang)
AdminHandlers.handle_product_search_message(self, bot, update, user_state)
AdminHandlers.handle_product_suspend_message(self, bot, update, user_state)
AdminHandlers.handle_user_search_message(self, bot, update, user_state)
```

---

## 🆘 **5. SUPPORT HANDLERS** (16 fonctions)

### SupportHandlers
```python
SupportHandlers.admin_reply_prepare(self, bot, query, ticket_id: str) -> None
SupportHandlers.admin_tickets(self, bot, query) -> None
SupportHandlers.contact_seller_start(self, bot, query, product_id: str, lang: str) -> None
SupportHandlers.create_ticket_prompt(self, bot, query, lang)
SupportHandlers.escalate_ticket(self, bot, query, ticket_id: str) -> None
SupportHandlers.my_tickets(self, query, lang)
SupportHandlers.process_admin_reply(self, bot, update, message_text: str) -> None
SupportHandlers.process_messaging_reply(self, bot, update, message_text: str) -> None
SupportHandlers.reply_ticket_prepare(self, bot, query, ticket_id: str) -> None
SupportHandlers.show_faq(self, query, lang)
SupportHandlers.support_command(self, bot, update, context)
SupportHandlers.support_menu(self, query, lang)
SupportHandlers.view_ticket(self, bot, query, ticket_id: str) -> None
```

---

## 🔐 **6. AUTH HANDLERS** (6 fonctions)

### AuthHandlers
```python
AuthHandlers.account_recovery_menu(self, query, lang)
AuthHandlers.process_login_code(self, bot, update, message_text: str)
AuthHandlers.process_login_email(self, bot, update, message_text: str)
AuthHandlers.process_recovery_code(self, bot, update, message_text: str)
AuthHandlers.process_recovery_email(self, bot, update, message_text: str)
AuthHandlers.recovery_by_email_prompt(self, query, lang)
```

---

## 🤖 **7. MARKETPLACE BOT** (13 fonctions)

### MarketplaceBot
```python
MarketplaceBot.auto_create_seller_payout(self, order_id: str) -> bool
MarketplaceBot.button_handler(self, update, context)
MarketplaceBot.get_user_language(self, user_id: int) -> str
MarketplaceBot.get_user_state(self, user_id: int) -> dict
MarketplaceBot.handle_text_message(self, update, context)
MarketplaceBot.is_seller_logged_in(self, user_id: int) -> bool
MarketplaceBot.login_seller(self, user_id: int)
MarketplaceBot.logout_seller(self, user_id: int)
MarketplaceBot.process_support_ticket(self, update, message_text: str)
MarketplaceBot.reset_conflicting_states(self, user_id: int, keep: set = None) -> None
MarketplaceBot.reset_user_state(self, user_id: int, keep: set = None) -> None
MarketplaceBot.reset_user_state_preserve_login(self, user_id: int) -> None
MarketplaceBot.update_user_mapping(self, from_user_id: int, to_user_id: int)
MarketplaceBot.update_user_state(self, user_id: int, **kwargs) -> None
```

---

## 🔀 **ROUTES CALLBACK ROUTER** (40 routes)

### Routes Principales
```
account_recovery -> AuthHandlers.account_recovery_menu
add_product -> SellHandlers.add_product_prompt
admin_commission_handler -> AdminHandlers.commissions_handler
admin_export_payouts -> AdminHandlers.admin_export_payouts
admin_export_products -> AdminHandlers.export_products
admin_export_users -> AdminHandlers.admin_export_users
admin_mark_all_payouts_paid -> AdminHandlers.admin_mark_all_payouts_paid
admin_marketplace_stats -> AdminHandlers.admin_marketplace_stats
admin_menu -> AdminHandlers.admin_menu
admin_payouts -> AdminHandlers.admin_payouts
admin_products -> AdminHandlers.admin_products
admin_search_product -> AdminHandlers.admin_search_product_prompt
admin_search_user -> AdminHandlers.admin_search_user_prompt
admin_suspend_product -> AdminHandlers.admin_suspend_product_prompt
admin_users -> AdminHandlers.admin_users
back_main -> Lambda wrapper
browse_categories -> BuyHandlers.browse_categories
buy_menu -> Lambda wrapper
create_seller -> SellHandlers.create_seller_prompt
create_ticket -> SupportHandlers.create_ticket_prompt
delete_seller -> SellHandlers.delete_seller_prompt
delete_seller_confirm -> SellHandlers.delete_seller_confirm
lang_en -> Lambda wrapper
lang_fr -> Lambda wrapper
library -> Lambda wrapper
my_products -> SellHandlers.show_my_products
my_tickets -> SupportHandlers.my_tickets
my_wallet -> SellHandlers.show_wallet
search_product -> BuyHandlers.search_product_prompt
sell_copy_address -> Lambda wrapper
sell_menu -> Lambda wrapper
sell_payout_history -> Lambda wrapper
seller_analytics -> SellHandlers.seller_analytics
seller_dashboard -> Lambda wrapper
seller_info -> CallbackRouter._handle_seller_info
seller_login -> SellHandlers.seller_login_menu
seller_login_menu -> Lambda wrapper
seller_logout -> SellHandlers.seller_logout
seller_settings -> SellHandlers.seller_settings
support_menu -> SupportHandlers.support_menu
```

### Routes avec Lambda Wrappers (corrections de signatures)
- `back_main` - Passe MarketplaceBot à CoreHandlers.back_to_main_with_bot
- `buy_menu` - Passe MarketplaceBot à BuyHandlers.buy_menu
- `sell_menu` - Passe MarketplaceBot à SellHandlers.sell_menu
- `seller_dashboard` - Passe MarketplaceBot à SellHandlers.seller_dashboard
- `seller_login_menu` - Passe MarketplaceBot à SellHandlers.seller_login_menu
- `lang_fr` / `lang_en` - Passe MarketplaceBot à CoreHandlers.change_language
- `library` - Passe MarketplaceBot à BuyHandlers.show_my_library
- `sell_copy_address` - Passe MarketplaceBot à SellHandlers.copy_address
- `sell_payout_history` - Passe MarketplaceBot à SellHandlers.payout_history

---

## ⚠️ **PATTERNS DE SIGNATURE**

### Signatures avec `bot` parameter (nécessitent lambda wrapper)
- **BuyHandlers**: Toutes les méthodes `(self, bot, query, lang)`
- **SellHandlers**: Toutes les méthodes `(self, bot, query, lang)`
- **CoreHandlers**: Méthodes command `(self, marketplace_bot, update, context)`

### Signatures compatibles CallbackRouter directement
- **AdminHandlers**: Toutes les méthodes `(self, query, lang)`
- **SupportHandlers**: Méthodes callback `(self, query, lang)`
- **AuthHandlers**: Méthodes callback `(self, query, lang)`

---

## 🛠️ **USAGE POUR DEBUG**

Quand tu as une erreur comme `"fonction X n'existe pas"`:

1. **Cherche dans ce fichier** avec Ctrl+F
2. **Vérifie la signature** - est-ce qu'elle correspond à l'appel ?
3. **Regarde la route** - est-ce qu'elle pointe vers la bonne méthode ?
4. **Vérifie les wrappers** - certaines méthodes nécessitent des lambda wrappers

**Exemple d'erreur typique**: `function missing argument 'lang'`
→ Vérifier si la méthode a signature `(self, bot, query, lang)` et nécessite un lambda wrapper dans CallbackRouter.

---

📅 **Dernière mise à jour**: 2025-09-28
🎯 **Status**: Toutes les fonctions auditées et routes vérifiées