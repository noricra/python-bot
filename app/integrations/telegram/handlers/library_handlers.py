"""Library Handlers - User library with downloads, reviews, ratings and support"""

import os
import time
from datetime import datetime
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.utils import logger, escape_markdown
from app.core.i18n import t as i18n


class LibraryHandlers:
    def __init__(self, product_repo, order_repo, user_repo):
        self.product_repo = product_repo
        self.order_repo = order_repo
        self.user_repo = user_repo

    async def _safe_transition_to_text(self, query, text: str, keyboard=None, parse_mode='Markdown'):
        """
        Gère intelligemment la transition d'un message (photo ou texte) vers un message texte

        Problème résolu:
        - Les carousels ont des photos → edit_message_text() échoue
        - Solution: Détecter photo et supprimer/renvoyer au lieu d'éditer
        """
        try:
            # Si le message original a une photo, on ne peut pas edit_message_text
            if query.message.photo:
                # Supprimer l'ancien message avec photo
                try:
                    await query.message.delete()
                except:
                    pass

                # Envoyer nouveau message texte
                await query.message.get_bot().send_message(
                    chat_id=query.message.chat_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode=parse_mode
                )
            else:
                # Message texte normal, on peut éditer
                await query.edit_message_text(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode=parse_mode
                )
        except Exception as e:
            logger.error(f"Error in _safe_transition_to_text: {e}")
            # Fallback ultime : nouveau message
            try:
                await query.message.delete()
            except:
                pass
            await query.message.get_bot().send_message(
                chat_id=query.message.chat_id,
                text=text,
                reply_markup=keyboard,
                parse_mode=parse_mode
            )

    async def show_library(self, bot, query, lang: str, page: int = 0):
        """Affiche la bibliothèque de l'utilisateur avec carousel visuel"""
        user_id = query.from_user.id

        try:
            conn = bot.get_db_connection()
            cursor = conn.cursor()

            # Récupérer tous les achats pour carousel
            cursor.execute('''
               SELECT
                    p.product_id,
                    p.title,
                    p.description,
                    p.price_eur,
                    p.thumbnail_path,
                    p.category,
                    p.file_size_mb,
                    COALESCE(u.seller_name, u.first_name) as seller_name,
                    MAX(o.completed_at) as completed_at,
                    o.download_count
                FROM orders o
                JOIN products p ON o.product_id = p.product_id
                JOIN users u ON p.seller_user_id = u.user_id
                WHERE o.buyer_user_id = ? AND o.payment_status = 'completed'
                GROUP BY p.product_id, p.title, p.description, p.price_eur, p.thumbnail_path, p.category, p.file_size_mb, u.seller_name
                ORDER BY MAX(o.completed_at) DESC
            ''', (user_id,))
            purchases_raw = cursor.fetchall()
            conn.close()

            if not purchases_raw:
                empty_text = (
                    "📚 **MY LIBRARY**\n\n"
                    "Your library is empty. Start exploring products!\n\n"
                    "💡 All your purchased products will appear here."
                    if lang == 'en' else
                    "📚 **MA BIBLIOTHÈQUE**\n\n"
                    "Votre bibliothèque est vide. Commencez à explorer les produits !\n\n"
                    "💡 Tous vos produits achetés apparaîtront ici."
                )

                await query.edit_message_text(
                    empty_text,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "🛒 Browse Products" if lang == 'en' else "🛒 Parcourir",
                            callback_data='buy_menu'
                        ),
                        InlineKeyboardButton(
                            "🏠 Home" if lang == 'en' else "🏠 Accueil",
                            callback_data='back_main'
                        )
                    ]]),
                    parse_mode='Markdown'
                )
                return

            # Convert to dict format for carousel
            purchases = []
            for row in purchases_raw:
                purchases.append({
                    'product_id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'price_eur': row[3],
                    'thumbnail_path': row[4],
                    'category': row[5],
                    'file_size_mb': row[6],
                    'seller_name': row[7],
                    'completed_at': row[8],
                    'download_count': row[9]
                })

            # Launch carousel mode starting at index 0
            await self.show_library_carousel(bot, query, purchases, index=0, lang=lang)

        except Exception as e:
            logger.error(f"Error loading library: {e}")
            await query.edit_message_text(
                "❌ Error loading library." if lang == 'en' else "❌ Erreur de chargement de la bibliothèque.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Home" if lang == 'en' else "🏠 Accueil",
                        callback_data='back_main'
                    )
                ]])
            )

    async def show_library_carousel(self, bot, query, purchases: list, index: int = 0, lang: str = 'fr') -> None:
        """Carousel visuel pour la bibliothèque (produits achetés)"""
        try:
            from telegram import InputMediaPhoto
            from app.core.image_utils import ImageUtils
            import os
            from datetime import datetime

            if not purchases or index >= len(purchases):
                await query.edit_message_text("❌ No products found" if lang == 'en' else "❌ Aucun produit trouvé")
                return

            product = purchases[index]

            # Build caption - UX OPTIMIZED Bibliothèque
            caption = ""

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 0. BREADCRUMB (Bibliothèque + Catégorie)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            category = product.get('category', '')
            if lang == 'fr':
                breadcrumb = "📚 _Ma Bibliothèque" + (f" › {category}_" if category else "_")
            else:
                breadcrumb = "📚 _My Library" + (f" › {category}_" if category else "_")
            caption += f"{breadcrumb}\n\n"

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 1. TITRE PRODUIT (GRAS pour maximum visibilité)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            caption += f"**{product['title']}**\n\n"

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 3. INFOS ACHAT
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            caption += f"💳 Acheté pour **{product['price_eur']:.2f} €**\n"

            # Date d'achat
            if product.get('completed_at'):
                try:
                    purchase_date = datetime.fromisoformat(product['completed_at'])
                    caption += f"📅 _{purchase_date.strftime('%d %B %Y')}_\n"
                except:
                    pass

            caption += f"🏪 Par **{product['seller_name']}**\n\n"

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 4. UTILISATION
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            download_count = product.get('download_count', 0)
            if download_count > 0:
                caption += f"📥 Téléchargé **{download_count}** fois\n\n"

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 5. DESCRIPTION (Texte utilisateur - GARDER LE MARKDOWN)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            if product.get('description'):
                desc = product['description']
                if len(desc) > 160:
                    desc = desc[:160].rsplit(' ', 1)[0] + "..."
                caption += f"{desc}\n\n"

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 6. MÉTADONNÉES
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            caption += f"📂 _{product.get('category', 'N/A')}_  •  📁 {product.get('file_size_mb', 0):.1f} MB"

            # Get image or placeholder
            thumbnail_path = product.get('thumbnail_path')

            if not thumbnail_path or not os.path.exists(thumbnail_path):
                thumbnail_path = ImageUtils.create_or_get_placeholder(
                    product_title=product['title'],
                    category=product.get('category', 'General'),
                    product_id=product['product_id']
                )

            # Build keyboard - Actions bibliothèque
            keyboard = []

            # Row 1: Télécharger (bouton principal)
            keyboard.append([
                InlineKeyboardButton(
                    "📥 TÉLÉCHARGER" if lang == 'fr' else "📥 DOWNLOAD",
                    callback_data=f'library_item_{product["product_id"]}'
                )
            ])

            # Row 2: Navigation arrows
            nav_row = []
            if index > 0:
                nav_row.append(InlineKeyboardButton("⬅️", callback_data=f'library_carousel_{index-1}'))
            else:
                nav_row.append(InlineKeyboardButton(" ", callback_data='noop'))

            nav_row.append(InlineKeyboardButton(
                f"{index+1}/{len(purchases)}",
                callback_data='noop'
            ))

            if index < len(purchases) - 1:
                nav_row.append(InlineKeyboardButton("➡️", callback_data=f'library_carousel_{index+1}'))
            else:
                nav_row.append(InlineKeyboardButton(" ", callback_data='noop'))

            keyboard.append(nav_row)

            # Row 3: Laisser un avis
            keyboard.append([
                InlineKeyboardButton(
                    "⭐ Laisser un avis" if lang == 'fr' else "⭐ Leave a review",
                    callback_data=f'review_product_{product["product_id"]}'
                )
            ])

            # Row 4: Back
            keyboard.append([
                InlineKeyboardButton(
                    "🏠 Accueil" if lang == 'fr' else "🏠 Home",
                    callback_data='back_main'
                )
            ])

            # Send or edit message
            try:
                if thumbnail_path and os.path.exists(thumbnail_path):
                    with open(thumbnail_path, 'rb') as photo_file:
                        await query.edit_message_media(
                            media=InputMediaPhoto(
                                media=photo_file,
                                caption=caption,
                                parse_mode='Markdown'
                            ),
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                else:
                    await query.edit_message_text(
                        text=caption,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )
            except Exception as e:
                logger.warning(f"Failed to edit message, sending new: {e}")
                await query.message.delete()

                if thumbnail_path and os.path.exists(thumbnail_path):
                    with open(thumbnail_path, 'rb') as photo_file:
                        await bot.application.bot.send_photo(
                            chat_id=query.message.chat_id,
                            photo=photo_file,
                            caption=caption,
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode='Markdown'
                        )
                else:
                    await bot.application.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=caption,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )

        except Exception as e:
            logger.error(f"Error in show_library_carousel: {e}")
            import traceback
            logger.error(traceback.format_exc())
            await query.edit_message_text(
                "❌ Error displaying product" if lang == 'en' else "❌ Erreur affichage produit"
            )

    async def show_library_item(self, bot, query, product_id: str, lang: str):
        """Affiche les détails d'un produit acheté avec toutes les options"""
        user_id = query.from_user.id

        try:
            conn = bot.get_db_connection()
            cursor = conn.cursor()

            # Vérifier que l'utilisateur possède ce produit
            cursor.execute('''
                SELECT
                    p.product_id,
                    p.title,
                    p.description,
                    COALESCE(u.seller_name, u.first_name) as seller_name,
                    p.seller_user_id,
                    p.category,
                    p.file_size_mb,
                    o.product_price_eur,
                    o.completed_at,
                    o.download_count,
                    o.order_id
                FROM orders o
                JOIN products p ON o.product_id = p.product_id
                JOIN users u ON p.seller_user_id = u.user_id
                WHERE o.buyer_user_id = ? AND o.product_id = ? AND o.payment_status = 'completed'
                ORDER BY o.completed_at DESC
                LIMIT 1
            ''', (user_id, product_id))

            result = cursor.fetchone()

            if not result:
                conn.close()
                await query.edit_message_text(
                    "❌ Product not found in your library." if lang == 'en' else "❌ Produit introuvable dans votre bibliothèque.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "📚 My Library" if lang == 'en' else "📚 Ma Bibliothèque",
                            callback_data='library_menu'
                        )
                    ]])
                )
                return

            (product_id, title, description, seller_name, seller_user_id,
             category, file_size_mb, price, completed_at, download_count, order_id) = result

            # Vérifier s'il y a déjà un avis
            cursor.execute('''
                SELECT rating, review_text
                FROM reviews
                WHERE buyer_user_id = ? AND product_id = ?
            ''', (user_id, product_id))
            review_data = cursor.fetchone()
            conn.close()

            # Construire le texte
            safe_title = escape_markdown(title or "Sans titre")
            safe_seller = escape_markdown(seller_name or "Unknown")
            safe_category = escape_markdown(category or "N/A")

            # Date d'achat
            try:
                purchase_date = datetime.fromisoformat(completed_at).strftime("%d/%m/%Y")
            except:
                purchase_date = "N/A"

            text = (
                f"📦 **{safe_title}**\n\n"
                f"👤 **Seller:** {safe_seller}\n"
                f"📂 **Category:** {safe_category}\n"
                f"💰 **Paid:** {price}€\n"
                f"📅 **Purchased:** {purchase_date}\n"
                f"📥 **Downloads:** {download_count or 0}\n"
                f"📁 **Size:** {file_size_mb:.1f} MB\n"
                if lang == 'en' else
                f"📦 **{safe_title}**\n\n"
                f"👤 **Vendeur:** {safe_seller}\n"
                f"📂 **Catégorie:** {safe_category}\n"
                f"💰 **Payé:** {price}€\n"
                f"📅 **Acheté le:** {purchase_date}\n"
                f"📥 **Téléchargements:** {download_count or 0}\n"
                f"📁 **Taille:** {file_size_mb:.1f} MB\n"
            )

            if review_data:
                rating, review_text = review_data
                stars = "⭐" * rating
                review_label = "Your Review" if lang == 'en' else "Votre Avis"
                text += f"\n**{review_label}:** {stars}\n"
                if review_text:
                    text += f"_{escape_markdown(review_text[:100])}_\n"

            # Boutons d'action - Layout 2-2-2
            keyboard = [
                [
                    InlineKeyboardButton(
                        "📥 Download" if lang == 'en' else "📥 Télécharger",
                        callback_data=f'download_product_{product_id}'
                    ),
                    InlineKeyboardButton(
                        "⭐ Rate/Review" if lang == 'en' else "⭐ Noter/Avis",
                        callback_data=f'rate_product_{product_id}'
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📞 Contact Seller" if lang == 'en' else "📞 Contacter Vendeur",
                        callback_data=f'contact_seller_{product_id}'
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 Library" if lang == 'en' else "🔙 Bibliothèque",
                        callback_data='library_menu'
                    ),
                    InlineKeyboardButton(
                        "🏠 Home" if lang == 'en' else "🏠 Accueil",
                        callback_data='back_main'
                    )
                ]
            ]

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error showing library item: {e}")
            await query.edit_message_text(
                "❌ Error loading product details." if lang == 'en' else "❌ Erreur de chargement.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "📚 My Library" if lang == 'en' else "📚 Ma Bibliothèque",
                        callback_data='library_menu'
                    )
                ]])
            )

    async def download_product(self, bot, query, context, product_id: str, lang: str):
        """Télécharge un produit acheté"""
        user_id = query.from_user.id

        try:
            conn = bot.get_db_connection()
            cursor = conn.cursor()

            # Vérifier l'achat et récupérer le fichier
            cursor.execute('''
                SELECT p.main_file_path, p.title, o.order_id
                FROM orders o
                JOIN products p ON o.product_id = p.product_id
                WHERE o.buyer_user_id = ? AND o.product_id = ? AND o.payment_status = 'completed'
                LIMIT 1
            ''', (user_id, product_id))

            result = cursor.fetchone()

            if not result:
                conn.close()
                await self._safe_transition_to_text(
                    query,
                    "❌ Product not purchased or not found." if lang == 'en' else "❌ Produit non acheté ou introuvable.",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "📚 My Library" if lang == 'en' else "📚 Ma Bibliothèque",
                            callback_data='library_menu'
                        )
                    ]])
                )
                return

            file_path, title, order_id = result

            # Incrémenter le compteur de téléchargements
            cursor.execute('''
                UPDATE orders
                SET download_count = COALESCE(download_count, 0) + 1,
                    last_download_at = CURRENT_TIMESTAMP
                WHERE order_id = ?
            ''', (order_id,))
            conn.commit()
            conn.close()

            # Construire le chemin complet
            from app.core.settings import settings
            full_file_path = os.path.join(settings.UPLOADS_DIR, file_path) if file_path else None

            if not file_path or not os.path.exists(full_file_path):
                logger.error(f"File not found: {full_file_path}")
                await self._safe_transition_to_text(
                    query,
                    "❌ File not found on server. Contact support." if lang == 'en' else "❌ Fichier introuvable sur le serveur. Contactez le support.",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "💬 Support" if lang == 'en' else "💬 Support",
                            callback_data='support_menu'
                        ),
                        InlineKeyboardButton(
                            "🔙 Back" if lang == 'en' else "🔙 Retour",
                            callback_data=f'library_item_{product_id}'
                        )
                    ]])
                )
                return

            # Message de téléchargement en cours
            try:
                await self._safe_transition_to_text(
                    query,
                    "📥 Preparing download..." if lang == 'en' else "📥 Préparation du téléchargement..."
                )
            except:
                pass

            # Envoyer le fichier
            bot_instance = context.bot if context else query.get_bot()

            with open(full_file_path, 'rb') as file:
                await bot_instance.send_document(
                    chat_id=query.message.chat_id,
                    document=file,
                    caption=f"📦 {title}\n\n✅ " + ("Download complete!" if lang == 'en' else "Téléchargement terminé !"),
                    reply_to_message_id=query.message.message_id
                )

            # Retourner à la fiche produit
            await self.show_library_item(bot, query, product_id, lang)

        except Exception as e:
            logger.error(f"Error downloading product: {e}")
            await query.message.reply_text(
                "❌ Download error. Please try again." if lang == 'en' else "❌ Erreur de téléchargement. Réessayez.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🔙 Back" if lang == 'en' else "🔙 Retour",
                        callback_data=f'library_item_{product_id}'
                    )
                ]])
            )

    async def rate_product_prompt(self, bot, query, product_id: str, lang: str):
        """Affiche le menu de notation"""
        text = (
            "⭐ **RATE THIS PRODUCT**\n\n"
            "How would you rate this product?\n"
            "Select the number of stars:"
            if lang == 'en' else
            "⭐ **NOTER CE PRODUIT**\n\n"
            "Comment notez-vous ce produit ?\n"
            "Sélectionnez le nombre d'étoiles :"
        )

        keyboard = []
        for rating in range(5, 0, -1):
            stars = "⭐" * rating
            keyboard.append([
                InlineKeyboardButton(
                    f"{stars} ({rating}/5)",
                    callback_data=f'set_rating_{product_id}_{rating}'
                )
            ])

        keyboard.append([
            InlineKeyboardButton(
                "🔙 Back" if lang == 'en' else "🔙 Retour",
                callback_data=f'library_item_{product_id}'
            )
        ])

        await self._safe_transition_to_text(
            query,
            text,
            InlineKeyboardMarkup(keyboard)
        )

    async def set_rating(self, bot, query, product_id: str, rating: int, lang: str):
        """Enregistre la note et demande un avis optionnel"""
        user_id = query.from_user.id

        try:
            conn = bot.get_db_connection()
            cursor = conn.cursor()

            # Créer ou mettre à jour l'avis
            cursor.execute('''
                INSERT INTO reviews (buyer_user_id, product_id, rating, created_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(buyer_user_id, product_id)
                DO UPDATE SET rating = ?, updated_at = CURRENT_TIMESTAMP
            ''', (user_id, product_id, rating, rating))
            conn.commit()
            conn.close()

            # Demander un commentaire optionnel
            stars = "⭐" * rating
            text = (
                f"✅ **Rating saved: {stars}**\n\n"
                "Would you like to add a written review?\n"
                "(Optional, but helpful for other buyers)"
                if lang == 'en' else
                f"✅ **Note enregistrée : {stars}**\n\n"
                "Souhaitez-vous ajouter un commentaire ?\n"
                "(Optionnel, mais utile pour les autres acheteurs)"
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "📝 Write Review" if lang == 'en' else "📝 Écrire un Avis",
                        callback_data=f'write_review_{product_id}'
                    )
                ],
                [
                    InlineKeyboardButton(
                        "✅ Done" if lang == 'en' else "✅ Terminé",
                        callback_data=f'library_item_{product_id}'
                    )
                ]
            ]

            await self._safe_transition_to_text(
                query,
                text,
                InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Error setting rating: {e}")
            await self._safe_transition_to_text(
                query,
                "❌ Error saving rating." if lang == 'en' else "❌ Erreur d'enregistrement.",
                InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🔙 Back" if lang == 'en' else "🔙 Retour",
                        callback_data=f'library_item_{product_id}'
                    )
                ]])
            )

    async def write_review_prompt(self, bot, query, product_id: str, lang: str):
        """Demande à l'utilisateur d'écrire un avis"""
        # Use the MarketplaceBot instance passed as parameter
        bot.reset_conflicting_states(query.from_user.id, keep={'waiting_for_review'})
        bot.state_manager.update_state(
            query.from_user.id,
            waiting_for_review=True,
            review_product_id=product_id,
            lang=lang
        )

        text = (
            "📝 **WRITE YOUR REVIEW**\n\n"
            "Share your experience with this product.\n"
            "Your review will help other buyers.\n\n"
            "Type your review below:"
            if lang == 'en' else
            "📝 **ÉCRIRE VOTRE AVIS**\n\n"
            "Partagez votre expérience avec ce produit.\n"
            "Votre avis aidera les autres acheteurs.\n\n"
            "Tapez votre avis ci-dessous :"
        )

        await self._safe_transition_to_text(
            query,
            text,
            InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "❌ Cancel" if lang == 'en' else "❌ Annuler",
                    callback_data=f'library_item_{product_id}'
                )
            ]])
        )

    async def process_review_text(self, bot, update, message_text: str):
        """Traite l'avis écrit par l'utilisateur"""
        user_id = update.effective_user.id
        user_state = bot.get_user_state(user_id)
        product_id = user_state.get('review_product_id')
        lang = user_state.get('lang', 'fr')

        if not product_id:
            await update.message.reply_text(
                "❌ Session expired. Please try again." if lang == 'en' else "❌ Session expirée. Réessayez."
            )
            bot.reset_user_state_preserve_login(user_id)
            return

        review_text = message_text.strip()

        if len(review_text) < 10:
            await update.message.reply_text(
                "❌ Review too short. Please write at least 10 characters." if lang == 'en' else "❌ Avis trop court. Minimum 10 caractères."
            )
            return

        try:
            conn = bot.get_db_connection()
            cursor = conn.cursor()

            # Mettre à jour l'avis
            cursor.execute('''
                UPDATE reviews
                SET review_text = ?, updated_at = CURRENT_TIMESTAMP
                WHERE buyer_user_id = ? AND product_id = ?
            ''', (review_text, user_id, product_id))

            conn.commit()
            conn.close()

            # Réinitialiser l'état
            bot.reset_user_state_preserve_login(user_id)

            await update.message.reply_text(
                "✅ **Review published!**\n\nThank you for your feedback!" if lang == 'en' else "✅ **Avis publié !**\n\nMerci pour votre retour !",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "📦 View Product" if lang == 'en' else "📦 Voir Produit",
                        callback_data=f'library_item_{product_id}'
                    ),
                    InlineKeyboardButton(
                        "📚 My Library" if lang == 'en' else "📚 Ma Bibliothèque",
                        callback_data='library_menu'
                    )
                ]]),
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error saving review: {e}")
            await update.message.reply_text(
                "❌ Error saving review." if lang == 'en' else "❌ Erreur d'enregistrement."
            )
            bot.reset_user_state_preserve_login(user_id)

    async def contact_seller(self, bot, query, product_id: str, lang: str):
        """Permet de contacter le vendeur d'un produit acheté"""
        user_id = query.from_user.id

        try:
            conn = bot.get_db_connection()
            cursor = conn.cursor()

            # Récupérer les infos du vendeur
            cursor.execute('''
                SELECT COALESCE(u.seller_name, u.first_name) as seller_name, p.seller_user_id, p.title
                FROM orders o
                JOIN products p ON o.product_id = p.product_id
                JOIN users u ON p.seller_user_id = u.user_id
                WHERE o.buyer_user_id = ? AND o.product_id = ? AND o.payment_status = 'completed'
                LIMIT 1
            ''', (user_id, product_id))

            result = cursor.fetchone()
            conn.close()

            if not result:
                await self._safe_transition_to_text(
                    query,
                    "❌ Product not found." if lang == 'en' else "❌ Produit introuvable.",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "🔙 Back" if lang == 'en' else "🔙 Retour",
                            callback_data='library_menu'
                        )
                    ]])
                )
                return

            seller_name, seller_user_id, product_title = result
            safe_seller = escape_markdown(seller_name or "Unknown")
            safe_title = escape_markdown(product_title or "Product")

            text = (
                f"📞 **CONTACT SELLER**\n\n"
                f"**Seller:** {safe_seller}\n"
                f"**Product:** {safe_title}\n\n"
                "What would you like to do?"
                if lang == 'en' else
                f"📞 **CONTACTER LE VENDEUR**\n\n"
                f"**Vendeur:** {safe_seller}\n"
                f"**Produit:** {safe_title}\n\n"
                "Que souhaitez-vous faire ?"
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "💬 Send Message" if lang == 'en' else "💬 Envoyer Message",
                        callback_data=f'message_seller_{seller_user_id}_{product_id}'
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 Back" if lang == 'en' else "🔙 Retour",
                        callback_data=f'library_item_{product_id}'
                    )
                ]
            ]

            await self._safe_transition_to_text(
                query,
                text,
                InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Error contacting seller: {e}")
            await self._safe_transition_to_text(
                query,
                "❌ Error." if lang == 'en' else "❌ Erreur.",
                InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🔙 Back" if lang == 'en' else "🔙 Retour",
                        callback_data=f'library_item_{product_id}'
                    )
                ]])
            )

    async def message_seller(self, bot, query, seller_user_id: int, product_id: str, lang: str):
        """Create a support ticket to contact seller about a product"""
        try:
            conn = bot.get_db_connection()
            cursor = conn.cursor()

            # Get product and seller info
            cursor.execute('''
                SELECT p.title, COALESCE(u.seller_name, u.first_name) as seller_name
                FROM products p
                JOIN users u ON p.seller_user_id = u.user_id
                WHERE p.product_id = ?
            ''', (product_id,))
            result = cursor.fetchone()

            if not result:
                conn.close()
                await query.edit_message_text("❌ Error" if lang == 'en' else "❌ Erreur")
                return

            product_title, seller_name = result
            user_id = query.from_user.id

            # Create ticket ID
            import time
            ticket_id = f"SELLER-{user_id}-{int(time.time())}"

            # Create support ticket with seller context
            subject = f"Message to seller: {seller_name}" if lang == 'en' else f"Message au vendeur : {seller_name}"
            message = f"Product: {product_title}\n\n[User will reply to this ticket to send message]" if lang == 'en' else f"Produit : {product_title}\n\n[L'utilisateur répondra à ce ticket pour envoyer son message]"

            cursor.execute('''
                INSERT INTO support_tickets
                (ticket_id, user_id, subject, message, status, seller_user_id, product_id, created_at)
                VALUES (?, ?, ?, ?, 'open', ?, ?, CURRENT_TIMESTAMP)
            ''', (ticket_id, user_id, subject, message, seller_user_id, product_id))
            conn.commit()
            conn.close()

            # Set state for waiting message
            bot.reset_conflicting_states(user_id, keep={'waiting_ticket_message'})
            bot.state_manager.update_state(user_id, waiting_ticket_message=ticket_id, lang=lang)

            text = (
                f"💬 **MESSAGE TO SELLER**\n\n"
                f"**Seller:** {seller_name}\n"
                f"**Product:** {product_title}\n"
                f"**Ticket:** `{ticket_id}`\n\n"
                f"Type your message below:"
                if lang == 'en' else
                f"💬 **MESSAGE AU VENDEUR**\n\n"
                f"**Vendeur :** {seller_name}\n"
                f"**Produit :** {product_title}\n"
                f"**Ticket :** `{ticket_id}`\n\n"
                f"Écrivez votre message ci-dessous :"
            )

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "❌ Cancel" if lang == 'en' else "❌ Annuler",
                        callback_data=f'library_item_{product_id}'
                    )
                ]]),
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error in message_seller: {e}")
            await query.edit_message_text("❌ Error" if lang == 'en' else "❌ Erreur")

