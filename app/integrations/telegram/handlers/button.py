import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.integrations.telegram.flows import support as support_flows
from telegram.ext import ContextTypes


logger = logging.getLogger(__name__)


async def button_handler(bot_controller, update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_data = bot_controller.get_user(user_id)
    lang = user_data['language_code'] if user_data else 'fr'

    try:
        # Navigation principale
        if query.data == 'buy_menu':
            await bot_controller.buy_menu(query, lang)
        elif query.data == 'sell_menu':
            await bot_controller.sell_menu(query, lang)
        elif query.data == 'seller_dashboard':
            await bot_controller.seller_dashboard(query, lang)
        elif query.data == 'marketplace_stats':
            await bot_controller.marketplace_stats(query, lang)
        elif query.data == 'support_menu':
            await support_flows.show_support_menu(bot_controller, query, lang)
        elif query.data == 'back_main':
            await bot_controller.back_to_main(query)
        elif query.data.startswith('lang_'):
            await bot_controller.change_language(query, query.data[5:])

        # Accès compte (unifié)
        elif query.data == 'seller_login':
            bot_controller.update_user_state(user_id, login_wait_email=True)
            await query.edit_message_text("🔑 Entrez votre email de récupération :")

        # Achat
        elif query.data == 'search_product':
            await bot_controller.search_product_prompt(query, lang)
        elif query.data == 'browse_categories':
            await bot_controller.browse_categories(query, lang)
        elif query.data.startswith('category_'):
            category_key = query.data[9:]
            await bot_controller.show_category_products(query, category_key, lang)
        elif query.data.startswith('product_'):
            product_id = query.data[8:]
            await bot_controller.show_product_details(query, product_id, lang)
        elif query.data.startswith('buy_product_'):
            product_id = query.data[12:]
            await bot_controller.buy_product_prompt(query, product_id, lang)

        # Vente
        elif query.data == 'create_seller':
            await bot_controller.create_seller_prompt(query, lang)
        elif query.data == 'add_product':
            await bot_controller.add_product_prompt(query, lang)
        elif query.data == 'my_products':
            await bot_controller.show_my_products(query, lang)
        elif query.data == 'my_wallet':
            await bot_controller.show_wallet(query, lang)
        elif query.data == 'seller_logout':
            await bot_controller.seller_logout(query)
        elif query.data == 'delete_seller':
            await bot_controller.delete_seller_prompt(query)
        elif query.data == 'delete_seller_confirm':
            await bot_controller.delete_seller_confirm(query)

        # NOUVEAU : Création produit avec catégories
        elif query.data.startswith('set_product_category_'):
            category_key = query.data[21:]
            category_name = category_key.replace('_', ' ').replace('and', '&')

            if user_id in bot_controller.memory_cache and bot_controller.memory_cache[user_id].get('adding_product'):
                user_state = bot_controller.memory_cache[user_id]
                user_state['product_data']['category'] = category_name
                user_state['step'] = 'price'

                await query.edit_message_text(
                    f"✅ **Catégorie :** {category_name}\n\n💰 **Étape 4/5 : Prix**\n\nFixez le prix en euros (ex: 49.99) :",
                    parse_mode='Markdown'
                )

        # Récupération compte
        elif query.data == 'recovery_by_email':
            await bot_controller.recovery_by_email_prompt(query, lang)

        # Parrainage
        elif query.data == 'enter_referral_manual':
            await bot_controller.enter_referral_manual(query, lang)
        elif query.data == 'choose_random_referral':
            await bot_controller.choose_random_referral(query, lang)
        elif query.data.startswith('use_referral_'):
            code = query.data[13:]
            await bot_controller.validate_and_proceed(query, code, lang)
        elif query.data == 'become_partner':
            await bot_controller.become_partner(query, lang)

        # Paiement
        elif query.data == 'proceed_to_payment':
            await bot_controller.show_crypto_options(query, lang)
        elif query.data.startswith('pay_'):
            crypto = query.data[4:]
            await bot_controller.process_payment(query, crypto, lang)
        elif query.data.startswith('check_payment_'):
            order_id = query.data[14:]
            await bot_controller.check_payment_handler(query, order_id, lang)

        # Téléchargement et bibliothèque
        elif query.data.startswith('download_product_'):
            product_id = query.data[17:]
            await bot_controller.download_product(query, context, product_id, lang)
        elif query.data == 'my_library':
            await bot_controller.show_my_library(query, lang)

        # Admin
        elif query.data == 'admin_menu':
            await bot_controller.admin_menu(query)
        elif query.data == 'admin_commissions':
            await bot_controller.admin_commissions_handler(query)
        elif query.data == 'admin_payouts':
            await bot_controller.admin_payouts_handler(query)
        elif query.data == 'admin_mark_all_payouts_paid':
            await bot_controller.admin_mark_all_payouts_paid(query)
        elif query.data == 'admin_export_payouts':
            await bot_controller.admin_export_payouts(query)
        elif query.data == 'admin_users':
            await bot_controller.admin_users_handler(query)
        elif query.data == 'admin_search_user':
            await bot_controller.admin_search_user(query)
        elif query.data == 'admin_export_users':
            await bot_controller.admin_export_users(query)
        elif query.data == 'admin_products':
            await bot_controller.admin_products_handler(query)
        elif query.data == 'admin_search_product':
            await bot_controller.admin_search_product(query)
        elif query.data == 'admin_suspend_product':
            await bot_controller.admin_suspend_product(query)
        elif query.data == 'admin_export_products':
            await bot_controller.admin_export_products(query)
        elif query.data == 'admin_marketplace_stats':
            await bot_controller.admin_marketplace_stats(query)

        # Support
        elif query.data == 'faq':
            await support_flows.show_faq(bot_controller, query, lang)
        elif query.data == 'create_ticket':
            await support_flows.create_ticket(bot_controller, query, lang)
        elif query.data == 'my_tickets':
            await support_flows.show_my_tickets(bot_controller, query, lang)

        # Wallet vendeur actions
        elif query.data == 'payout_history':
            await bot_controller.payout_history(query)
        elif query.data == 'copy_address':
            await bot_controller.copy_address(query)

        # Autres écrans vendeur
        elif query.data == 'seller_analytics':
            await bot_controller.seller_analytics(query, lang)
        elif query.data == 'seller_settings':
            await bot_controller.seller_settings(query, lang)
        elif query.data == 'edit_seller_name':
            bot_controller.update_user_state(user_id, editing_settings=True, step='edit_name')
            await query.edit_message_text("Entrez le nouveau nom vendeur:")
        elif query.data == 'edit_seller_bio':
            bot_controller.update_user_state(user_id, editing_settings=True, step='edit_bio')
            await query.edit_message_text("Entrez la nouvelle biographie:")
        elif query.data.startswith('edit_product_'):
            product_id = query.data.split('edit_product_')[-1]
            bot_controller.update_user_state(user_id, editing_product=True, product_id=product_id, step='choose_field')
            keyboard = [
                [InlineKeyboardButton("✏️ Modifier titre", callback_data=f'edit_field_title_{product_id}')],
                [InlineKeyboardButton("💰 Modifier prix", callback_data=f'edit_field_price_{product_id}')],
                [InlineKeyboardButton("⏸️ Activer/Désactiver", callback_data=f'edit_field_toggle_{product_id}')],
                [InlineKeyboardButton("🔙 Retour", callback_data='my_products')],
                [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')],
            ]
            await query.edit_message_text(f"Édition produit `{product_id}`:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        elif query.data.startswith('edit_field_title_'):
            product_id = query.data.split('edit_field_title_')[-1]
            bot_controller.update_user_state(user_id, editing_product=True, product_id=product_id, step='edit_title_input')
            await query.edit_message_text("Entrez le nouveau titre:")
        elif query.data.startswith('edit_field_price_'):
            product_id = query.data.split('edit_field_price_')[-1]
            bot_controller.update_user_state(user_id, editing_product=True, product_id=product_id, step='edit_price_input')
            await query.edit_message_text("Entrez le nouveau prix (EUR):")
        elif query.data.startswith('edit_field_toggle_'):
            product_id = query.data.split('edit_field_toggle_')[-1]
            try:
                conn = bot_controller.get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT status FROM products WHERE product_id = ? AND seller_user_id = ?', (product_id, user_id))
                row = cursor.fetchone()
                if not row:
                    conn.close()
                    await query.edit_message_text("❌ Produit introuvable.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour", callback_data='my_products')]]))
                else:
                    new_status = 'inactive' if row[0] == 'active' else 'active'
                    cursor.execute('UPDATE products SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE product_id = ? AND seller_user_id = ?', (new_status, product_id, user_id))
                    conn.commit()
                    conn.close()
                    await bot_controller.show_my_products(query, 'fr')
            except Exception as e:
                logger.error(f"Erreur toggle statut produit: {e}")
                await query.edit_message_text("❌ Erreur mise à jour statut.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour", callback_data='my_products')]]))
        elif query.data.startswith('delete_product_'):
            product_id = query.data.split('delete_product_')[-1]
            bot_controller.update_user_state(user_id, confirm_delete_product=product_id)
            keyboard = [
                [InlineKeyboardButton("✅ Confirmer suppression", callback_data=f'confirm_delete_{product_id}')],
                [InlineKeyboardButton("❌ Annuler", callback_data='my_products')],
                [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')],
            ]
            await query.edit_message_text(f"Confirmer la suppression du produit `{product_id}` ?", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        elif query.data.startswith('confirm_delete_'):
            product_id = query.data.split('confirm_delete_')[-1]
            try:
                conn = bot_controller.get_db_connection()
                cursor = conn.cursor()
                cursor.execute('DELETE FROM products WHERE product_id = ? AND seller_user_id = ?', (product_id, user_id))
                conn.commit()
                conn.close()
                await bot_controller.show_my_products(query, lang)
            except Exception as e:
                logger.error(f"Erreur suppression produit: {e}")
                await query.edit_message_text("❌ Erreur lors de la suppression.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour", callback_data='my_products')]]))
        elif query.data == 'seller_info':
            await bot_controller.seller_info(query, lang)

        else:
            await query.edit_message_text(
                "🚧 Fonction en cours de développement...",
                reply_markup=InlineKeyboardMarkup([[ 
                    InlineKeyboardButton("🏠 Accueil", callback_data='back_main')
                ]]))

    except Exception as e:
        logger.error(f"Erreur button_handler: {e}")
        await query.edit_message_text(
            "❌ Erreur temporaire. Retour au menu principal.",
            reply_markup=InlineKeyboardMarkup([[ 
                InlineKeyboardButton("🏠 Accueil", callback_data='back_main')
            ]]))

