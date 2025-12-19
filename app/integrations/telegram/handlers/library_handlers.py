"""Library Handlers - User library with downloads, reviews, ratings and support"""

import os
import time
from datetime import datetime
from typing import Optional
import psycopg2.extras

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.core.utils import logger, escape_markdown
from app.core.i18n import t as i18n
from app.core.db_pool import put_connection
from app.integrations.telegram.keyboards import back_to_main_button
from app.integrations.telegram.utils import safe_transition_to_text


class LibraryHandlers:
    def __init__(self, product_repo, order_repo, user_repo):
        self.product_repo = product_repo
        self.order_repo = order_repo
        self.user_repo = user_repo

    async def show_library(self, bot, query, lang: str, page: int = 0):
        """Affiche la bibliothèque de l'utilisateur avec carousel visuel"""
        await query.answer()

        user_id = query.from_user.id

        # 🔧 FIX: Réinitialiser TOUS les états quand on entre dans la bibliothèque
        bot.reset_user_state(user_id, keep={'lang'})

        try:
            conn = bot.get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Récupérer tous les achats pour carousel
            cursor.execute('''
               SELECT
                    p.product_id,
                    p.title,
                    p.description,
                    p.price_usd,
                    p.thumbnail_url,
                    p.category,
                    p.file_size_mb,
                    COALESCE(u.seller_name, u.first_name) as seller_name,
                    MAX(o.completed_at) as completed_at,
                    o.download_count
                FROM orders o
                JOIN products p ON o.product_id = p.product_id
                JOIN users u ON p.seller_user_id = u.user_id
                WHERE o.buyer_user_id = %s AND o.payment_status = 'completed'
                GROUP BY p.product_id, p.title, p.description, p.price_usd, p.thumbnail_url, p.category, p.file_size_mb, u.seller_name, u.first_name, o.download_count
                ORDER BY MAX(o.completed_at) DESC
            ''', (user_id,))
            purchases_raw = cursor.fetchall()
            put_connection(conn)

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
                    'product_id': row['product_id'],
                    'title': row['title'],
                    'description': row['description'],
                    'price_usd': row['price_usd'],
                    'thumbnail_url': row['thumbnail_url'],
                    'category': row['category'],
                    'file_size_mb': row['file_size_mb'],
                    'seller_name': row['seller_name'],
                    'completed_at': row['completed_at'],
                    'download_count': row['download_count']
                })

            # Launch carousel mode starting at index 0
            # [CORRECTION] Ajout de 'await' car la méthode est async
            await self.show_library_carousel(bot, query, purchases, index=0, lang=lang)

        except Exception as e:
            logger.error(f"Error loading library: {e}")
            await query.edit_message_text(
                "❌ Error loading library." if lang == 'en' else "❌ Erreur de chargement de la bibliothèque.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        " Home" if lang == 'en' else " Accueil",
                        callback_data='back_main'
                    )
                ]])
            )

    async def show_library_carousel(self, bot, query, purchases: list, index: int = 0, lang: str = 'fr') -> None:
        """Carousel visuel pour la bibliothèque (produits achetés)"""
        from app.integrations.telegram.utils.carousel_helper import CarouselHelper
        from telegram import InlineKeyboardButton

        # Caption builder for library carousel
        def build_caption(product, lang):
            title = product['title']
            seller = product.get('seller_name', 'Vendeur')
            price = product['price_usd']
            category = product.get('category', 'Produits')
            file_size = product.get('file_size_mb', 0)
            download_count = product.get('download_count', 0)

            caption = f"<b>{title}</b>\n"
            caption += f"<i>par {seller}</i>\n\n" if lang == 'fr' else f"<i>by {seller}</i>\n\n"

            stats_text = f"💳 Acheté pour ${price:.2f}"
            if download_count > 0:
                stats_text += f" • 📥 {download_count} " + ("téléchargements" if lang == 'fr' else "downloads")
            caption += stats_text + "\n"
            caption += "────────────────\n"
            caption += f"📂 {category} • 📁 {file_size:.1f} MB"

            return caption

        # Keyboard builder for library carousel
        def build_keyboard(product, index, total, lang):
            keyboard = []

            # Row 1: Download
            keyboard.append([
                InlineKeyboardButton(
                    " Télécharger" if lang == 'fr' else " Download",
                    callback_data=f'download_product_{product["product_id"]}'
                )
            ])

            # Row 2: Navigation with carousel helper (asymmetric)
            nav_row = CarouselHelper.build_navigation_row(
                index=index,
                total=total,
                callback_prefix='library_carousel_',
                show_empty_buttons=False  # Asymmetric nav
            )
            keyboard.append(nav_row)

            # Row 3: Review + Contact
            keyboard.append([
                InlineKeyboardButton(
                    " Laisser un avis" if lang == 'fr' else " Leave a review",
                    callback_data=f'review_product_{product["product_id"]}'
                ),
                InlineKeyboardButton(
                    " Contacter vendeur" if lang == 'fr' else " Contact seller",
                    callback_data=f'contact_seller_{product["product_id"]}'
                )
            ])

            # Row 4: Back
            keyboard.append([
                InlineKeyboardButton(
                    "Accueil" if lang == 'fr' else "Home",
                    callback_data='back_main'
                )
            ])

            return keyboard

        # Use carousel helper (eliminates duplication)
        # [CORRECTION] Ajout de 'await' car CarouselHelper.show_carousel est async
        await CarouselHelper.show_carousel(
            query=query,
            bot=bot,
            products=purchases,
            index=index,
            caption_builder=build_caption,
            keyboard_builder=build_keyboard,
            lang=lang,
            parse_mode='HTML'
        )

    async def download_product(self, bot, query, context, product_id: str, lang: str):
        """
        Ouvre la MiniApp de téléchargement (Railway-proof, scalable)
        Download direct B2 → Browser (pas de usage disque Railway)
        """
        await query.answer()

        user_id = query.from_user.id

        try:
            conn = bot.get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Vérifier l'achat et récupérer les infos produit
            cursor.execute('''
                SELECT p.title, p.file_size_mb, o.order_id
                FROM orders o
                JOIN products p ON o.product_id = p.product_id
                WHERE o.buyer_user_id = %s AND o.product_id = %s AND o.payment_status = 'completed'
                LIMIT 1
            ''', (user_id, product_id))

            result = cursor.fetchone()
            put_connection(conn)

            if not result:
                await safe_transition_to_text(
                    query,
                    "Product not purchased or not found." if lang == 'en' else "Produit non acheté ou introuvable.",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "My Library" if lang == 'en' else "Ma Bibliothèque",
                            callback_data='library_menu'
                        )
                    ]])
                )
                return

            title = result['title']
            file_size_mb = result.get('file_size_mb', 0)

            # Formater taille fichier
            if file_size_mb < 1:
                size_text = f"{file_size_mb * 1024:.0f} KB"
            elif file_size_mb < 1024:
                size_text = f"{file_size_mb:.1f} MB"
            else:
                size_text = f"{file_size_mb / 1024:.2f} GB"

            # Obtenir l'URL de la MiniApp
            from app.core.settings import WEBAPP_URL
            webapp_url = WEBAPP_URL or "https://python-bot-production.up.railway.app"
            miniapp_url = f"{webapp_url}/static/download.html?product_id={product_id}&lang={lang}"

            # Afficher le bouton MiniApp pour télécharger
            text = (
                f"**{title}**\n\n"
                f"Taille : {size_text}\n\n"
                f"Cliquez sur le bouton ci-dessous pour télécharger votre fichier.\n"
                f"Le téléchargement se fera directement dans votre navigateur."
            ) if lang == 'fr' else (
                f"**{title}**\n\n"
                f"Size: {size_text}\n\n"
                f"Click the button below to download your file.\n"
                f"The download will happen directly in your browser."
            )

            keyboard = [
                [InlineKeyboardButton(
                    "Télécharger" if lang == 'fr' else "Download",
                    web_app=WebAppInfo(url=miniapp_url)
                )],
                [InlineKeyboardButton(
                    "Retour" if lang == 'fr' else "Back",
                    callback_data='library_menu'
                )]
            ]

            await safe_transition_to_text(
                query,
                text,
                InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error preparing download: {e}")
            await query.message.reply_text(
                "Error preparing download. Please try again." if lang == 'en' else "Erreur de préparation. Réessayez.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "Back" if lang == 'en' else "Retour",
                        callback_data='library_menu'
                    )
                ]])
            )

    async def rate_product_prompt(self, bot, query, product_id: str, lang: str):
        """Affiche le menu de notation"""
        await query.answer()

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
                callback_data='library_menu'
            )
        ])

        await safe_transition_to_text(
            query,
            text,
            InlineKeyboardMarkup(keyboard)
        )

    async def set_rating(self, bot, query, product_id: str, rating: int, lang: str):
        """Enregistre la note et demande un avis optionnel"""
        await query.answer()

        user_id = query.from_user.id

        try:
            conn = bot.get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Créer ou mettre à jour l'avis
            cursor.execute('''
                INSERT INTO reviews (buyer_user_id, product_id, rating, created_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT(buyer_user_id, product_id)
                DO UPDATE SET rating = %s, updated_at = CURRENT_TIMESTAMP
            ''', (user_id, product_id, rating, rating))
            conn.commit()
            put_connection(conn)

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
                        callback_data='library_menu'
                    )
                ]
            ]

            await safe_transition_to_text(
                query,
                text,
                InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Error setting rating: {e}")
            await safe_transition_to_text(
                query,
                "❌ Error saving rating." if lang == 'en' else "❌ Erreur d'enregistrement.",
                InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        " Back" if lang == 'en' else " Retour",
                        callback_data='library_menu'
                    )
                ]])
            )

    async def write_review_prompt(self, bot, query, product_id: str, lang: str):
        """Demande la note sur 5 étoiles d'abord"""
        await query.answer()

        text = (
            "⭐ **RATE THIS PRODUCT**\n\n"
            "How would you rate this product?\n"
            "Choose a rating from 1 to 5 stars:"
            if lang == 'en' else
            "⭐ **NOTEZ CE PRODUIT**\n\n"
            "Quelle note donneriez-vous à ce produit ?\n"
            "Choisissez une note de 1 à 5 étoiles :"
        )

        # Boutons d'étoiles
        keyboard = [
            [
                InlineKeyboardButton("⭐", callback_data=f'rate_{product_id}_1'),
                InlineKeyboardButton("⭐⭐", callback_data=f'rate_{product_id}_2'),
                InlineKeyboardButton("⭐⭐⭐", callback_data=f'rate_{product_id}_3'),
            ],
            [
                InlineKeyboardButton("⭐⭐⭐⭐", callback_data=f'rate_{product_id}_4'),
                InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data=f'rate_{product_id}_5'),
            ],
            [
                InlineKeyboardButton(
                    "❌ Cancel" if lang == 'en' else "❌ Annuler",
                    callback_data='library_menu'
                )
            ]
        ]

        await safe_transition_to_text(
            query,
            text,
            InlineKeyboardMarkup(keyboard)
        )

    async def process_rating(self, bot, query, product_id: str, rating: int, lang: str):
        """Enregistre la note et demande le texte de l'avis"""
        await query.answer()

        user_id = query.from_user.id

        try:
            conn = bot.get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Créer ou mettre à jour la note
            cursor.execute('''
                INSERT INTO reviews (buyer_user_id, product_id, rating, created_at, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(buyer_user_id, product_id)
                DO UPDATE SET rating = %s, updated_at = CURRENT_TIMESTAMP
            ''', (user_id, product_id, rating, rating))

            conn.commit()
            put_connection(conn)

            # Demander maintenant le texte de l'avis
            bot.reset_conflicting_states(user_id, keep={'waiting_for_review'})
            bot.state_manager.update_state(
                user_id,
                waiting_for_review=True,
                review_product_id=product_id,
                lang=lang
            )

            stars = "⭐" * rating
            text = (
                f"✅ **Rating saved: {stars}**\n\n"
                "📝 **Now write your review** (optional)\n\n"
                "Share your experience with this product.\n"
                "Your review will help other buyers.\n\n"
                "Type your review below, or click Cancel:"
                if lang == 'en' else
                f"✅ **Note enregistrée : {stars}**\n\n"
                "📝 **Écrivez maintenant votre avis** (optionnel)\n\n"
                "Partagez votre expérience avec ce produit.\n"
                "Votre avis aidera les autres acheteurs.\n\n"
                "Tapez votre avis ci-dessous, ou cliquez sur Annuler :"
            )

            await safe_transition_to_text(
                query,
                text,
                InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "❌ Skip" if lang == 'en' else "❌ Passer",
                        callback_data='library_menu'
                    )
                ]])
            )

        except Exception as e:
            logger.error(f"Error saving rating: {e}")
            await query.message.reply_text(
                "❌ Error saving rating." if lang == 'en' else "❌ Erreur d'enregistrement de la note."
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
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Mettre à jour l'avis
            cursor.execute('''
                UPDATE reviews
                SET review_text = %s, updated_at = CURRENT_TIMESTAMP
                WHERE buyer_user_id = %s AND product_id = %s
            ''', (review_text, user_id, product_id))

            conn.commit()
            put_connection(conn)

            # Réinitialiser l'état
            bot.reset_user_state_preserve_login(user_id)

            await update.message.reply_text(
                "✅ **Review published!**\n\nThank you for your feedback!" if lang == 'en' else "✅ **Avis publié !**\n\nMerci pour votre retour !",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        " View Product" if lang == 'en' else " Voir Produit",
                        callback_data='library_menu'
                    ),
                    InlineKeyboardButton(
                        " My Library" if lang == 'en' else " Ma Bibliothèque",
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
        """Ouvre directement le chat Telegram privé avec le vendeur"""
        await query.answer()

        user_id = query.from_user.id

        try:
            conn = bot.get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Récupérer les infos du vendeur
            cursor.execute('''
                SELECT COALESCE(u.seller_name, u.first_name) as seller_name, p.seller_user_id, p.title
                FROM orders o
                JOIN products p ON o.product_id = p.product_id
                JOIN users u ON p.seller_user_id = u.user_id
                WHERE o.buyer_user_id = %s AND o.product_id = %s AND o.payment_status = 'completed'
                LIMIT 1
            ''', (user_id, product_id))

            result = cursor.fetchone()
            put_connection(conn)

            if not result:
                await safe_transition_to_text(
                    query,
                    "❌ Product not found." if lang == 'en' else "❌ Produit introuvable.",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            " Back" if lang == 'en' else " Retour",
                            callback_data='library_menu'
                        )
                    ]])
                )
                return

            seller_name, seller_user_id, product_title = result
            safe_seller = escape_markdown(seller_name or "Unknown")
            safe_title = escape_markdown(product_title or "Product")

            text = (
                f" **CONTACT SELLER**\n\n"
                f"**Seller:** {safe_seller}\n"
                f"**Product:** {safe_title}\n\n"
                "Click the button below to open a private chat with the seller."
                if lang == 'en' else
                f" **CONTACTER LE VENDEUR**\n\n"
                f"**Vendeur:** {safe_seller}\n"
                f"**Produit:** {safe_title}\n\n"
                "Cliquez sur le bouton ci-dessous pour ouvrir un chat privé avec le vendeur."
            )

            # Créer un lien direct vers le chat Telegram du vendeur
            keyboard = [
                [
                    InlineKeyboardButton(
                        "💬 Ouvrir le chat" if lang == 'fr' else "💬 Open chat",
                        url=f'tg://user?id={seller_user_id}'
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 Retour" if lang == 'fr' else "🔙 Back",
                        callback_data='library_menu'
                    )
                ]
            ]

            await safe_transition_to_text(
                query,
                text,
                InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Error contacting seller: {e}")
            await safe_transition_to_text(
                query,
                "❌ Error." if lang == 'en' else "❌ Erreur.",
                InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        " Back" if lang == 'en' else " Retour",
                        callback_data='library_menu'
                    )
                ]])
            )
