"""Admin Handlers - Administration functions with dependency injection"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.core.i18n import t as i18n
from app.core.db import get_sqlite_connection
from app.core.settings import settings
import logging

logger = logging.getLogger(__name__)

class AdminHandlers:
    def __init__(self, user_repo, product_repo, order_repo, payout_service):
        self.user_repo = user_repo
        self.product_repo = product_repo
        self.order_repo = order_repo
        self.payout_service = payout_service

    async def admin_menu(self, bot, query, lang):
        """Menu principal admin"""
        # Clean any conflicting states when entering admin
        user_id = query.from_user.id
        bot.reset_conflicting_states(user_id)

        admin_keyboard = [
            [InlineKeyboardButton("👥 Users", callback_data='admin_users_menu'),
             InlineKeyboardButton("📦 Products", callback_data='admin_products_menu')],
            [InlineKeyboardButton(i18n(lang, 'admin_payouts'), callback_data='admin_payouts'),
             InlineKeyboardButton(i18n(lang, 'admin_stats'), callback_data='admin_marketplace_stats')],
            [InlineKeyboardButton(i18n(lang, 'admin_back'), callback_data='back_main')]
        ]

        await query.edit_message_text(
            "🔧 **ADMINISTRATION**\n\nChoisissez une section :",
            reply_markup=InlineKeyboardMarkup(admin_keyboard),
            parse_mode='Markdown')

    async def admin_users_menu(self, query, lang):
        """Menu gestion utilisateurs"""
        users_keyboard = [
            [InlineKeyboardButton("👥 Voir utilisateurs", callback_data='admin_users'),
             InlineKeyboardButton("🔍 Rechercher user", callback_data='admin_search_user')],
            [InlineKeyboardButton("❌ Suspendre user", callback_data='admin_suspend_user'),
             InlineKeyboardButton("✅ Rétablir user", callback_data='admin_restore_user')],
            [InlineKeyboardButton("📊 Export users", callback_data='admin_export_users')],
            [InlineKeyboardButton("🔙 Retour admin", callback_data='admin_menu')]
        ]

        await query.edit_message_text(
            "👥 **GESTION UTILISATEURS**\n\nChoisissez une action :",
            reply_markup=InlineKeyboardMarkup(users_keyboard),
            parse_mode='Markdown')

    async def admin_products_menu(self, query, lang):
        """Menu gestion produits"""
        products_keyboard = [
            [InlineKeyboardButton("📦 Voir produits", callback_data='admin_products'),
             InlineKeyboardButton("🔍 Rechercher produit", callback_data='admin_search_product')],
            [InlineKeyboardButton("❌ Suspendre produit", callback_data='admin_suspend_product'),
             InlineKeyboardButton("📊 Export produits", callback_data='admin_export_products_csv')],
            [InlineKeyboardButton("🔙 Retour admin", callback_data='admin_menu')]
        ]

        await query.edit_message_text(
            "📦 **GESTION PRODUITS**\n\nChoisissez une action :",
            reply_markup=InlineKeyboardMarkup(products_keyboard),
            parse_mode='Markdown')

    async def admin_users(self, query, lang):
        """Gestion utilisateurs"""
        try:
            users = self.user_repo.get_all_users(limit=50)  # Increased limit
            text = "👥 **UTILISATEURS ENREGISTRÉS**\n\n" if lang == 'fr' else "👥 **REGISTERED USERS**\n\n"

            if not users:
                text += "Aucun utilisateur trouvé." if lang == 'fr' else "No users found."
            else:
                text += f"Total: {len(users)} utilisateurs\n\n" if lang == 'fr' else f"Total: {len(users)} users\n\n"

                for i, user in enumerate(users[:30], 1):  # Show first 30 for readability
                    status = "🟢 Vendeur" if user.get('is_seller') else "🔵 Acheteur"
                    status_en = "🟢 Seller" if user.get('is_seller') else "🔵 Buyer"
                    display_status = status if lang == 'fr' else status_en

                    username = user.get('username', 'N/A')
                    first_name = user.get('first_name', 'N/A')
                    registration_date = user.get('registration_date', 'N/A')[:10] if user.get('registration_date') else 'N/A'

                    text += f"**{i}.** {display_status}\n"
                    text += f"   • ID: `{user['user_id']}`\n"
                    text += f"   • Nom: {first_name}\n" if lang == 'fr' else f"   • Name: {first_name}\n"
                    text += f"   • Username: @{username}\n" if username != 'N/A' else ""
                    text += f"   • Inscrit: {registration_date}\n\n" if lang == 'fr' else f"   • Registered: {registration_date}\n\n"

                if len(users) > 30:
                    text += f"... et {len(users) - 30} autres utilisateurs" if lang == 'fr' else f"... and {len(users) - 30} more users"

            keyboard = [
                [InlineKeyboardButton("📊 Export CSV", callback_data='admin_export_users')],
                [InlineKeyboardButton("🔙 Menu Users" if lang == 'fr' else "🔙 Users Menu", callback_data='admin_users_menu')]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error in admin_users: {e}")
            await query.edit_message_text(
                f"❌ Erreur lors du chargement des utilisateurs: {str(e)}" if lang == 'fr' else f"❌ Error loading users: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Menu", callback_data='admin_menu')]])
            )

    async def admin_products(self, query, lang):
        """Gestion produits"""
        try:
            products = self.product_repo.get_all_products(limit=20)
            text = i18n(lang, 'admin_products_title') + "\n\n"

            for product in products:
                status = "✅" if product['status'] == 'active' else "❌"
                text += f"{status} {product['product_id']} - {product['title'][:20]}...\n"

            keyboard = [[InlineKeyboardButton("🔙 Products Menu", callback_data='admin_products_menu')]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except Exception as e:
            await query.edit_message_text(f"❌ Erreur: {str(e)}")

    async def admin_payouts(self, query, lang):
        """Gestion payouts"""
        try:
            payouts = self.payout_service.get_pending_payouts(limit=20)
            text = i18n(lang, 'admin_payouts_title') + "\n\n"

            for payout in payouts:
                text += f"User {payout['user_id']}: {payout['amount']}€\n"

            keyboard = [
                [InlineKeyboardButton("✅ Mark All Paid", callback_data='admin_mark_all_payouts_paid')],
                [InlineKeyboardButton("🔙 Admin Menu", callback_data='admin_menu')]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except Exception as e:
            await query.edit_message_text(f"❌ Erreur: {str(e)}")

    async def admin_marketplace_stats(self, query, lang):
        """Stats marketplace"""
        try:
            total_users = self.user_repo.count_users()
            total_sellers = self.user_repo.count_sellers()
            total_products = self.product_repo.count_products()
            total_orders = self.order_repo.count_orders()

            stats_text = f"""📊 **MARKETPLACE STATS**

👥 Total Users: {total_users}
🏪 Sellers: {total_sellers}
📦 Products: {total_products}
🛒 Orders: {total_orders}

💰 Total Revenue: {self.order_repo.get_total_revenue():.2f}€"""

            await query.edit_message_text(
                stats_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Menu", callback_data='admin_menu')]]),
                parse_mode='Markdown')
        except Exception as e:
            await query.edit_message_text(f"❌ Erreur: {str(e)}")

    async def admin_search_user_prompt(self, query, lang):
        """Prompt recherche utilisateur"""
        # Set searching state for this user
        user_id = query.from_user.id

        await query.edit_message_text(
            "🔍 **Recherche Utilisateur**\n\nEntrez l'ID utilisateur à rechercher :" if lang == 'fr' else "🔍 **User Search**\n\nEnter user ID to search:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='admin_menu')]]),
            parse_mode='Markdown')

    async def admin_search_product_prompt(self, query, lang):
        """Prompt recherche produit"""
        # Set searching state for this user
        user_id = query.from_user.id

        await query.edit_message_text(
            "🔍 **Recherche Produit**\n\nEntrez l'ID produit à rechercher :" if lang == 'fr' else "🔍 **Product Search**\n\nEnter product ID to search:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='admin_menu')]]),
            parse_mode='Markdown')

    async def admin_suspend_product_prompt(self, query, lang):
        """Prompt suspension produit"""
        user_id = query.from_user.id

        await query.edit_message_text(
            "❌ **Suspendre Produit**\n\nEntrez l'ID produit à suspendre :" if lang == 'fr' else "❌ **Suspend Product**\n\nEnter product ID to suspend:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='admin_menu')]]),
            parse_mode='Markdown')

    async def admin_suspend_user_prompt(self, bot, query, lang):
        """Prompt suspension utilisateur"""
        user_id = query.from_user.id
        bot.state_manager.update_state(user_id, suspending_user=True, lang=lang)

        await query.edit_message_text(
            "❌ **Suspendre Utilisateur**\n\nEntrez l'ID utilisateur à suspendre :" if lang == 'fr' else "❌ **Suspend User**\n\nEnter user ID to suspend:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='admin_menu')]]),
            parse_mode='Markdown')

    async def process_admin_suspend_user(self, update, message_text: str):
        """Process suspension d'utilisateur"""
        try:
            user_id = int(message_text.strip())

            # Check if user exists
            user_data = self.user_repo.get_user(user_id)
            if not user_data:
                await update.message.reply_text(f"❌ Utilisateur {user_id} introuvable")
                return

            # Comprehensive user suspension
            conn = get_sqlite_connection(settings.DATABASE_PATH)
            cursor = conn.cursor()

            # Store original seller status and suspend
            was_seller = user_data.get('is_seller', False)

            # Mark as suspended by setting seller_name to special suspend marker
            # and removing seller status
            suspend_marker = f"[SUSPENDED]{user_data.get('seller_name', '')}"
            cursor.execute('''
                UPDATE users SET
                    is_seller = FALSE,
                    seller_name = ?
                WHERE user_id = ?
            ''', (suspend_marker, user_id))

            # Suspend all their products
            cursor.execute('UPDATE products SET status = "suspended" WHERE seller_user_id = ?', (user_id,))

            conn.commit()
            conn.close()

            # Send suspension notification email if email exists
            user_email = user_data.get('email')
            if user_email:
                try:
                    from app.services.smtp_service import SMTPService
                    smtp_service = SMTPService()

                    success = smtp_service.send_suspension_notification(user_email, first_name or 'Utilisateur')
                    email_status = "✅ Email de suspension envoyé" if success else "❌ Échec envoi email"
                except Exception as e:
                    email_status = f"❌ Erreur email: {str(e)}"
            else:
                email_status = "⚠️ Pas d'email - notification non envoyée"

            username = user_data.get('username', 'N/A')
            first_name = user_data.get('first_name', 'N/A')

            await update.message.reply_text(
                f"✅ **Utilisateur suspendu**\n\n👤 **ID:** `{user_id}`\n📝 **Nom:** {first_name}\n📝 **Username:** @{username}\n\n🚫 **Actions prises:**\n• Statut vendeur retiré\n• Produits suspendus\n• Accès marketplace restreint\n\n📧 **Notification:** {email_status}\n\nℹ️ Utilisez /admin pour le rétablir",
                parse_mode='Markdown'
            )

        except ValueError:
            await update.message.reply_text("❌ ID utilisateur invalide. Entrez un nombre.")
        except Exception as e:
            await update.message.reply_text(f"❌ Erreur: {str(e)}")

    async def admin_restore_user_prompt(self, bot, query, lang):
        """Prompt rétablissement utilisateur"""
        user_id = query.from_user.id
        bot.state_manager.update_state(user_id, restoring_user=True, lang=lang)

        # Get list of suspended users
        try:
            conn = get_sqlite_connection(settings.DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, seller_name, email, first_name
                FROM users
                WHERE seller_name LIKE '[SUSPENDED]%'
                LIMIT 20
            ''')
            suspended_users = cursor.fetchall()
            conn.close()

            text = "✅ **Rétablir Utilisateur**\n\n" if lang == 'fr' else "✅ **Restore User**\n\n"

            if suspended_users:
                text += "👥 **Utilisateurs suspendus:**\n\n" if lang == 'fr' else "👥 **Suspended users:**\n\n"
                for user in suspended_users[:10]:  # Show first 10
                    u_id, seller_name, email, first_name = user
                    clean_name = seller_name.replace('[SUSPENDED]', '').strip() or first_name or 'N/A'
                    text += f"• ID: `{u_id}` - {clean_name[:20]}\n"
                text += f"\n📝 **Entrez l'ID ou email à rétablir:**" if lang == 'fr' else f"\n📝 **Enter ID or email to restore:**"
            else:
                text += "✅ Aucun utilisateur suspendu" if lang == 'fr' else "✅ No suspended users"

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='admin_users_menu')]]),
                parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error showing suspended users: {e}")
            await query.edit_message_text(
                "✅ **Rétablir Utilisateur**\n\nEntrez l'ID utilisateur OU email à rétablir :" if lang == 'fr' else "✅ **Restore User**\n\nEnter user ID OR email to restore:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='admin_users_menu')]]),
                parse_mode='Markdown')

    async def process_admin_restore_user(self, update, message_text: str):
        """Process rétablissement d'utilisateur"""
        try:
            input_text = message_text.strip()

            # Determine if input is email or user ID
            if '@' in input_text:
                # Search by email
                user_data = self.user_repo.get_user_by_email(input_text.lower())
                search_type = "email"
                search_value = input_text.lower()
            else:
                # Search by user ID
                try:
                    user_id = int(input_text)
                    user_data = self.user_repo.get_user(user_id)
                    search_type = "user_id"
                    search_value = user_id
                except ValueError:
                    await update.message.reply_text("❌ Entrée invalide. Utilisez un ID numérique ou un email valide.")
                    return

            if not user_data:
                await update.message.reply_text(f"❌ Utilisateur introuvable avec {search_type}: {search_value}")
                return

            user_id = user_data['user_id']

            # Check suspension more comprehensively:
            # 1. Check seller_name for [SUSPENDED] marker
            # 2. Check if there are suspended products for this user
            conn = get_sqlite_connection(settings.DATABASE_PATH)
            cursor = conn.cursor()

            # Check for suspended products
            cursor.execute('SELECT COUNT(*) FROM products WHERE seller_user_id = ? AND status = "suspended"', (user_id,))
            suspended_products_count = cursor.fetchone()[0]

            seller_name = user_data.get('seller_name', '')
            is_marked_suspended = seller_name.startswith('[SUSPENDED]')

            if not is_marked_suspended and suspended_products_count == 0:
                conn.close()
                await update.message.reply_text(f"❌ L'utilisateur {user_id} n'est pas suspendu")
                return

            # Restore original seller name and status
            original_name = seller_name.replace('[SUSPENDED]', '') if seller_name.startswith('[SUSPENDED]') else seller_name
            if not original_name:
                # If no seller name, create a default one
                original_name = f"Vendeur{user_id}"

            cursor.execute('''
                UPDATE users SET
                    is_seller = TRUE,
                    seller_name = ?
                WHERE user_id = ?
            ''', (original_name, user_id))

            # Restore all their products (set back to active)
            cursor.execute('UPDATE products SET status = "active" WHERE seller_user_id = ? AND status = "suspended"', (user_id,))

            conn.commit()
            conn.close()

            username = user_data.get('username', 'N/A')
            first_name = user_data.get('first_name', 'N/A')

            await update.message.reply_text(
                f"✅ **Utilisateur rétabli**\n\n👤 **ID:** `{user_id}`\n📝 **Nom:** {first_name}\n📝 **Username:** @{username}\n\n🔄 **Actions prises:**\n• Statut vendeur rétabli ({suspended_products_count} produits réactivés)\n• Accès marketplace restauré",
                parse_mode='Markdown'
            )

        except Exception as e:
            await update.message.reply_text(f"❌ Erreur: {str(e)}")

    async def admin_mark_all_payouts_paid(self, query, lang):
        """Marquer tous payouts comme payés"""
        try:
            count = self.payout_service.mark_all_payouts_paid()
            await query.edit_message_text(
                f"✅ {count} payouts marqués comme payés",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Menu", callback_data='admin_menu')]])
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Erreur: {str(e)}")

    async def admin_export_users(self, query, lang):
        """Export utilisateurs en CSV"""
        try:
            import io
            import csv
            from datetime import datetime

            users = self.user_repo.get_all_users()

            if not users:
                await query.edit_message_text(
                    "👥 Aucun utilisateur à exporter." if lang == 'fr' else "👥 No users to export.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Admin" if lang == 'fr' else "🔙 Admin Menu", callback_data='admin_menu')]])
                )
                return

            # Create CSV content
            csv_content = io.StringIO()
            writer = csv.writer(csv_content)

            # Write header
            writer.writerow([
                'user_id', 'username', 'first_name', 'language_code',
                'registration_date', 'last_activity', 'is_seller',
                'seller_name', 'email', 'total_sales', 'total_revenue'
            ])

            # Write user data
            for user in users:
                writer.writerow([
                    user.get('user_id', ''),
                    user.get('username', ''),
                    user.get('first_name', ''),
                    user.get('language_code', ''),
                    user.get('registration_date', ''),
                    user.get('last_activity', ''),
                    user.get('is_seller', False),
                    user.get('seller_name', ''),
                    user.get('email', ''),
                    user.get('total_sales', 0),
                    user.get('total_revenue', 0.0)
                ])

            # Create file
            csv_bytes = csv_content.getvalue().encode('utf-8')
            file_name = f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            # Send CSV file
            await query.message.reply_document(
                document=io.BytesIO(csv_bytes),
                filename=file_name,
                caption=f"📊 Export CSV: {len(users)} utilisateurs" if lang == 'fr' else f"📊 CSV Export: {len(users)} users"
            )

            await query.edit_message_text(
                "✅ Fichier CSV généré avec succès!" if lang == 'fr' else "✅ CSV file generated successfully!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Admin" if lang == 'fr' else "🔙 Admin Menu", callback_data='admin_menu')]])
            )

        except Exception as e:
            logger.error(f"Error in admin_export_users: {e}")
            await query.edit_message_text(
                "❌ Erreur lors de la génération du CSV." if lang == 'fr' else "❌ Error generating CSV.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Menu", callback_data='admin_menu')]])
            )

    async def admin_export_payouts(self, query, lang):
        """Export payouts"""
        try:
            payouts = self.payout_service.get_all_payouts()
            export_text = "📄 **EXPORT PAYOUTS**\n\n"
            for payout in payouts[:50]:  # Limit for Telegram
                export_text += f"{payout['user_id']},{payout['amount']},{payout['status']}\n"

            await query.edit_message_text(
                export_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Menu", callback_data='admin_menu')]]))
        except Exception as e:
            await query.edit_message_text(f"❌ Erreur: {str(e)}")

    # Alias methods for simplified calls
    # Wrapper methods removed - duplicates of existing admin_* methods (32 lines removed)

    # Commission system removed - partner system deleted

    async def export_products(self, query, lang):
        """Export products to text format"""
        try:
            products = self.product_repo.get_all_products(limit=100)

            if not products:
                await query.edit_message_text(
                    "📦 Aucun produit à exporter." if lang == 'fr' else "📦 No products to export.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Admin" if lang == 'fr' else "🔙 Admin Menu", callback_data='admin_menu')]])
                )
                return

            # Create export text
            export_text = "📊 **Export Produits**\n\n" if lang == 'fr' else "📊 **Products Export**\n\n"
            export_text += f"Total: {len(products)} produits\n\n" if lang == 'fr' else f"Total: {len(products)} products\n\n"

            for i, product in enumerate(products[:20], 1):  # Limit to first 20 for readability
                export_text += f"**{i}. {product.get('title', 'N/A')}**\n"
                export_text += f"• ID: `{product.get('product_id', 'N/A')}`\n"
                export_text += f"• Prix: {product.get('price_eur', 0):.2f}€\n" if lang == 'fr' else f"• Price: €{product.get('price_eur', 0):.2f}\n"
                export_text += f"• Catégorie: {product.get('category', 'N/A')}\n" if lang == 'fr' else f"• Category: {product.get('category', 'N/A')}\n"
                export_text += f"• Statut: {product.get('status', 'N/A')}\n" if lang == 'fr' else f"• Status: {product.get('status', 'N/A')}\n"
                export_text += f"• Vendeur ID: {product.get('seller_user_id', 'N/A')}\n\n"

            if len(products) > 20:
                export_text += f"... et {len(products) - 20} autres produits\n" if lang == 'fr' else f"... and {len(products) - 20} more products\n"

            # Split message if too long
            if len(export_text) > 4000:
                export_text = export_text[:4000] + "..."

            keyboard = [
                [InlineKeyboardButton("📊 Stats détaillées" if lang == 'fr' else "📊 Detailed stats", callback_data='admin_marketplace_stats')],
                [InlineKeyboardButton("🔙 Menu Admin" if lang == 'fr' else "🔙 Admin Menu", callback_data='admin_menu')]
            ]

            await query.edit_message_text(
                export_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error in export_products: {e}")
            await query.edit_message_text(
                "❌ Erreur lors de l'export des produits." if lang == 'fr' else "❌ Error exporting products.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Menu", callback_data='admin_menu')]])
            )

    # Text processing methods compatible with compact architecture
    async def handle_user_search_message(self, bot, update, user_state):
        """Process recherche utilisateur"""
        message_text = update.message.text.strip()
        try:
            if message_text.isdigit():
                user = self.user_repo.get_user(int(message_text))
            else:
                user = None  # Partner code search removed

            if user:
                text = f"👤 **User Found**\n\nID: {user['user_id']}\nName: {user.get('first_name', 'N/A')}\nSeller: {user.get('is_seller', False)}"
            else:
                text = "❌ Utilisateur non trouvé"

            await update.message.reply_text(text)
            bot.reset_user_state(update.effective_user.id)
        except Exception as e:
            await update.message.reply_text(f"❌ Erreur: {str(e)}")

    async def handle_product_search_message(self, bot, update, user_state):
        """Process recherche produit"""
        message_text = update.message.text.strip()
        try:
            product = self.product_repo.get_product_by_id(message_text.strip())
            if product:
                text = f"📦 **Product Found**\n\nID: {product['product_id']}\nTitle: {product['title']}\nStatus: {product['status']}"
            else:
                text = "❌ Produit non trouvé"

            await update.message.reply_text(text)
            bot.reset_user_state(update.effective_user.id)
        except Exception as e:
            await update.message.reply_text(f"❌ Erreur: {str(e)}")

    async def handle_product_suspend_message(self, bot, update, user_state):
        """Process suspension produit"""
        message_text = update.message.text.strip()
        try:
            success = self.product_repo.update_status(message_text.strip(), 'banned')
            text = "✅ Produit suspendu" if success else "❌ Erreur suspension"
            await update.message.reply_text(text)
            bot.reset_user_state(update.effective_user.id)
        except Exception as e:
            await update.message.reply_text(f"❌ Erreur: {str(e)}")

    async def admin_export_products_csv(self, query, lang):
        """Export products to CSV file"""
        try:
            import csv
            import io
            from datetime import datetime

            products = self.product_repo.get_all_products()

            if not products:
                await query.edit_message_text(
                    "📦 Aucun produit à exporter." if lang == 'fr' else "📦 No products to export.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Admin" if lang == 'fr' else "🔙 Admin Menu", callback_data='admin_menu')]])
                )
                return

            # Create CSV content
            csv_content = io.StringIO()
            writer = csv.writer(csv_content)

            # Headers
            headers = ['ID Produit', 'Titre', 'Prix EUR', 'Catégorie', 'Statut', 'Vendeur ID', 'Date Création'] if lang == 'fr' else \
                     ['Product ID', 'Title', 'Price EUR', 'Category', 'Status', 'Seller ID', 'Created Date']
            writer.writerow(headers)

            # Data rows
            for product in products:
                writer.writerow([
                    product.get('product_id', ''),
                    product.get('title', ''),
                    product.get('price_eur', 0),
                    product.get('category', ''),
                    product.get('status', ''),
                    product.get('seller_user_id', ''),
                    product.get('created_at', '')
                ])

            csv_data = csv_content.getvalue()
            csv_content.close()

            # Send as document
            filename = f"products_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

            await query.message.reply_document(
                document=io.BytesIO(csv_data.encode('utf-8')),
                filename=filename,
                caption=f"📊 Export CSV: {len(products)} produits" if lang == 'fr' else f"📊 CSV Export: {len(products)} products"
            )

            await query.edit_message_text(
                "✅ Fichier CSV généré avec succès!" if lang == 'fr' else "✅ CSV file generated successfully!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Admin" if lang == 'fr' else "🔙 Admin Menu", callback_data='admin_menu')]])
            )

        except Exception as e:
            logger.error(f"Error in admin_export_products_csv: {e}")
            await query.edit_message_text(
                "❌ Erreur lors de la génération du CSV." if lang == 'fr' else "❌ Error generating CSV.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Menu", callback_data='admin_menu')]])
            )