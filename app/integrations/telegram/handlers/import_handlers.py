"""Import Handlers - Import products from external platforms (Gumroad, etc.)"""

import re
import logging
import asyncio
import tempfile
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes

from app.services.gumroad_scraper import scrape_gumroad_profile, download_cover_image, GumroadScraperException
from app.core.i18n import t as i18n
from app.integrations.telegram.utils import safe_transition_to_text

logger = logging.getLogger(__name__)


class ImportHandlers:
    """Handle import functionality from external platforms"""

    def __init__(self, user_repo, product_repo):
        self.user_repo = user_repo
        self.product_repo = product_repo

    async def import_shop_start(self, bot, query):
        """Entry point unifié pour import boutique"""
        await query.answer()

        user_id = query.from_user.id
        lang = bot.get_user_language(user_id)

        # Reset state
        bot.reset_user_state(user_id, keep={'lang'})
        bot.state_manager.update_state(user_id, importing_shop=True, step='waiting_shop_url')

        text = (
            "📦 **Import de boutique**\n\n"
            "Collez le lien de votre boutique Gumroad:\n\n"
            "**Exemple:**\n"
            "`https://username.gumroad.com`"
        )

        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Annuler" if lang == 'fr' else "Cancel", callback_data='cancel_import')
            ]])
        )

    async def handle_shop_url(self, bot, update, context):
        """Recevoir URL et lancer scraping avec indicateur progression"""
        user_id = update.effective_user.id
        lang = bot.get_user_language(user_id)
        url = update.message.text.strip()

        # Normaliser URL
        if not url.startswith('http'):
            url = f'https://{url}'
        url = url.rstrip('/')

        # Validation URL Gumroad
        if not re.match(r'https?://[\w-]+\.gumroad\.com/?$', url):
            await update.message.reply_text(
                "❌ URL invalide\n\n"
                "**Format attendu:**\n"
                "`https://username.gumroad.com`\n\n"
                "Réessayez ou utilisez /cancel pour annuler.",
                parse_mode='Markdown'
            )
            return

        # Message avec indicateur progression
        status_msg = await update.message.reply_text(
            "🔍 **Scraping en cours...**\n\n"
            "⏳ Temps estimé: 10-30 secondes\n"
            "Veuillez patienter...",
            parse_mode='Markdown'
        )

        # Optionnel: Update message avec progression
        async def update_progress():
            for i in range(3):
                await asyncio.sleep(8)
                try:
                    await status_msg.edit_text(
                        f"🔍 **Scraping en cours...**\n\n"
                        f"⏳ {'.' * (i+1)}\n"
                        f"Analyse de votre boutique...",
                        parse_mode='Markdown'
                    )
                except:
                    pass

        # Lancer update progression en background
        progress_task = asyncio.create_task(update_progress())

        try:
            # Scraping
            products = await scrape_gumroad_profile(url)

            # Annuler progression
            progress_task.cancel()

            if not products:
                await status_msg.edit_text(
                    "⚠️ **Aucun produit trouvé**\n\n"
                    "Vérifiez que:\n"
                    "• Le profil est public\n"
                    "• Le profil contient des produits\n"
                    "• L'URL est correcte\n\n"
                    "Utilisez /import pour réessayer.",
                    parse_mode='Markdown'
                )
                bot.state_manager.update_state(user_id, importing_shop=False, step=None)
                return

            # Stocker produits dans state
            bot.state_manager.update_state(
                user_id,
                step='previewing_products',
                import_products=products,
                import_source_url=url,
                import_current_index=0
            )

            # Afficher carrousel
            await self.show_import_carousel(bot, status_msg, products, 0, lang, is_new_message=True)

        except GumroadScraperException as e:
            # Exception personnalisee avec message specifique utilisateur
            progress_task.cancel()
            logger.warning(f"[IMPORT] Gumroad scraping failed: {e}")

            # Determiner emoji selon type erreur
            error_msg = str(e)
            if "n'existe pas" in error_msg:
                emoji = "❌"
            elif "refuse" in error_msg or "Bot" in error_msg:
                emoji = "🛡️"
            elif "surcharge" in error_msg or "5 minutes" in error_msg:
                emoji = "⚠️"
            elif "serveur" in error_msg:
                emoji = "🔥"
            else:
                emoji = "⚠️"

            await status_msg.edit_text(
                f"{emoji} **Erreur Gumroad**\n\n"
                f"{error_msg}\n\n"
                "Utilisez /import pour réessayer.",
                parse_mode='Markdown'
            )
            bot.state_manager.update_state(user_id, importing_shop=False, step=None)

        except Exception as e:
            # Erreurs inattendues (bugs code, etc.)
            progress_task.cancel()
            logger.error(f"[IMPORT] Unexpected error during scraping: {e}")
            await status_msg.edit_text(
                f"❌ **Erreur inattendue:**\n{str(e)}\n\n"
                "Si le problème persiste, contactez le support.\n"
                "Utilisez /import pour recommencer.",
                parse_mode='Markdown'
            )
            bot.state_manager.update_state(user_id, importing_shop=False, step=None)

    async def show_import_carousel(self, bot, query_or_message, products, index, lang, is_new_message=False):
        """Afficher carrousel import avec format exact des carrousels existants"""

        if index >= len(products):
            index = 0

        product = products[index]

        # Build caption (Image AVANT texte, titre après)
        caption = self._build_import_caption(product, index, len(products), lang)

        # Build keyboard (4 lignes comme spécifié)
        keyboard = self._build_import_keyboard(product, index, len(products), lang)

        # Get image
        image_url = product.get('image_url')

        # Si nouveau message (après scraping)
        if is_new_message:
            # Supprimer message "Scraping en cours..."
            try:
                await query_or_message.delete()
            except:
                pass

            # Envoyer nouveau message avec carrousel
            telegram_bot = bot.application.bot if hasattr(bot, 'application') else bot

            if image_url and image_url.startswith('http'):
                await telegram_bot.send_photo(
                    chat_id=query_or_message.chat.id,
                    photo=image_url,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            else:
                await telegram_bot.send_message(
                    chat_id=query_or_message.chat.id,
                    text=caption,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
        else:
            # Update message existant (navigation)
            if image_url and image_url.startswith('http'):
                try:
                    await query_or_message.edit_message_media(
                        media=InputMediaPhoto(
                            media=image_url,
                            caption=caption,
                            parse_mode='Markdown'
                        ),
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                except:
                    # Fallback to text only
                    await query_or_message.edit_message_text(
                        text=caption,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )
            else:
                await query_or_message.edit_message_text(
                    text=caption,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )

    def _build_import_caption(self, product, index, total, lang):
        """Build caption carrousel import (Image AVANT, titre APRÈS)"""

        # Format: [Image affichée par Telegram]
        #         📦 Titre
        #         Description courte

        title = product['title']
        description = product.get('description', '')

        # Truncate description
        if len(description) > 150:
            description = description[:147] + '...'

        caption = f"📦 **{title}**\n\n"

        if description:
            caption += f"{description}\n\n"

        caption += f"Produit {index + 1}/{total}"

        return caption

    def _build_import_keyboard(self, product, index, total, lang):
        """Build keyboard carrousel import (4 lignes exactes) - MATCHING buy/sell handlers"""

        price = product['price']
        price_display = f"${price:.2f}" if price > 0 else "Gratuit"

        keyboard = []

        # Ligne 1: Bouton Importer avec prix (format similaire à buy_handlers)
        keyboard.append([
            InlineKeyboardButton(
                f"📥 Importer - {price_display}",
                callback_data='import_product'
            )
        ])

        # Ligne 2: Navigation carrousel (EXACTEMENT comme buy/sell handlers)
        # Build navigation manually like buy_handlers (asymmetric - no empty buttons)
        nav_row = []

        # Flèche gauche SI pas au début
        if index > 0:
            nav_row.append(InlineKeyboardButton("⬅️", callback_data=f'import_nav_{index-1}'))

        # Compteur au centre
        nav_row.append(InlineKeyboardButton(
            f"{index+1}/{total}",
            callback_data='noop'
        ))

        # Flèche droite SI pas à la fin
        if index < total - 1:
            nav_row.append(InlineKeyboardButton("➡️", callback_data=f'import_nav_{index+1}'))

        keyboard.append(nav_row)

        # Ligne 3: Détails (sans emoji excessif comme buy_handlers)
        keyboard.append([
            InlineKeyboardButton(
                "Détails" if lang == 'fr' else "Details",
                callback_data=f'import_details_{index}'
            )
        ])

        # Ligne 4: Annuler
        keyboard.append([
            InlineKeyboardButton(
                "Annuler" if lang == 'fr' else "Cancel",
                callback_data='cancel_import'
            )
        ])

        return keyboard

    async def navigate_import_carousel(self, bot, query, new_index):
        """Navigate import carousel - called via callback import_nav_X"""
        await query.answer()

        user_id = query.from_user.id
        lang = bot.get_user_language(user_id)
        user_state = bot.state_manager.get_state(user_id)

        products = user_state.get('import_products', [])

        # Bounds check
        if new_index < 0:
            new_index = 0
        elif new_index >= len(products):
            new_index = len(products) - 1

        # Update state
        bot.state_manager.update_state(user_id, import_current_index=new_index)

        # Show updated carousel
        await self.show_import_carousel(bot, query, products, new_index, lang, is_new_message=False)

    async def show_product_details(self, bot, query, lang, index):
        """Afficher description complète du produit"""
        await query.answer()

        user_id = query.from_user.id
        user_state = bot.state_manager.get_state(user_id)

        products = user_state.get('import_products', [])

        if index >= len(products):
            return

        product = products[index]

        title = product['title']
        price = product['price']
        description = product.get('description', 'Pas de description')
        gumroad_url = product.get('gumroad_url', '')

        text = (
            f"📦 **{title}**\n\n"
            f"**Prix:** ${price:.2f}\n\n"
            f"**Description:**\n{description}\n\n"
        )

        if gumroad_url:
            text += f"**Lien Gumroad:** {gumroad_url}\n\n"

        text += f"Produit {index + 1}/{len(products)}"

        keyboard = [
            [InlineKeyboardButton("⬅️ Retour au carrousel", callback_data=f'import_nav_{index}')]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown',
            disable_web_page_preview=True
        )

    async def start_import_process(self, bot, query, lang):
        """Démarrer processus import - Créer compte si nécessaire"""
        await query.answer()

        user_id = query.from_user.id
        user_data = self.user_repo.get_user(user_id)

        # Si PAS vendeur → Créer compte
        if not user_data or not user_data.get('is_seller'):
            bot.state_manager.update_state(
                user_id,
                creating_seller_for_import=True,
                step='awaiting_seller_email'
            )

            await query.edit_message_text(
                "📧 **Création de votre compte vendeur**\n\n"
                "Pour importer vos produits, créez votre compte vendeur.\n\n"
                "**Étape 1/2:** Envoyez votre email:",
                parse_mode='Markdown'
            )
            return

        # Si DÉJÀ vendeur → Skip création, start upload
        await self.start_file_upload_sequence(bot, query, lang)

    async def process_seller_email_for_import(self, bot, update):
        """Recevoir email vendeur (création compte pour import)"""
        user_id = update.effective_user.id
        lang = bot.get_user_language(user_id)
        email = update.message.text.strip()

        # Validation email basique
        if '@' not in email or '.' not in email:
            await update.message.reply_text(
                "❌ Email invalide. Réessayez:",
                parse_mode='Markdown'
            )
            return

        # Stocker email
        bot.state_manager.update_state(
            user_id,
            seller_email=email,
            step='awaiting_seller_solana'
        )

        await update.message.reply_text(
            f"✅ Email: `{email}`\n\n"
            f"**Étape 2/2:** Envoyez votre adresse Solana\n"
            f"(Pour recevoir vos paiements)",
            parse_mode='Markdown'
        )

    async def process_seller_solana_for_import(self, bot, update):
        """Recevoir adresse Solana vendeur (création compte pour import)"""
        user_id = update.effective_user.id
        lang = bot.get_user_language(user_id)
        user_state = bot.state_manager.get_state(user_id)

        solana_address = update.message.text.strip()

        # Validation Solana address basique (32-44 caractères alphanumériques)
        if len(solana_address) < 32 or len(solana_address) > 44:
            await update.message.reply_text(
                "❌ Adresse Solana invalide. Réessayez:",
                parse_mode='Markdown'
            )
            return

        email = user_state.get('seller_email')

        # Créer compte vendeur
        try:
            self.user_repo.update_user(
                user_id,
                is_seller=True,
                email=email,
                seller_solana_address=solana_address,
                seller_name=update.effective_user.first_name  # Default
            )

            await update.message.reply_text(
                "✅ **Compte vendeur créé!**\n\n"
                "Démarrage de l'import...",
                parse_mode='Markdown'
            )

            # Update state
            bot.state_manager.update_state(
                user_id,
                creating_seller_for_import=False,
                step='uploading_files'
            )

            # Créer mock query pour lancer upload
            class MockQuery:
                def __init__(self, user, msg):
                    self.from_user = user
                    self.message = msg
                    self.effective_chat = msg.chat
                async def edit_message_text(self, text, **kwargs):
                    await self.message.reply_text(text, **kwargs)
                async def answer(self):
                    pass

            mock_query = MockQuery(update.effective_user, update.message)
            await self.start_file_upload_sequence(bot, mock_query, lang)

        except Exception as e:
            logger.error(f"Error creating seller account: {e}")
            await update.message.reply_text(
                f"❌ Erreur création compte:\n{str(e)}\n\n"
                "Contactez le support.",
                parse_mode='Markdown'
            )

    async def start_file_upload_sequence(self, bot, query, lang):
        """Démarrer upload séquentiel guidé"""
        user_id = query.from_user.id
        user_state = bot.state_manager.get_state(user_id)

        products = user_state.get('import_products', [])
        source_url = user_state.get('import_source_url', '')

        if not products:
            await query.edit_message_text(
                "❌ Aucun produit à importer",
                parse_mode='Markdown'
            )
            return

        # Init upload state
        bot.state_manager.update_state(
            user_id,
            step='uploading_files',
            upload_current_index=0,
            upload_results=[]
        )

        # Demander premier fichier
        await self.request_next_file(bot, query.message if hasattr(query, 'message') else query, products, 0, lang)

    async def request_next_file(self, bot, message, products, index, lang):
        """Demander fichier pour produit N"""

        if index >= len(products):
            # Tous fichiers traités → Finaliser
            return

        product = products[index]
        title = product['title']
        price = product['price']

        text = (
            f"📎 **Upload fichier {index + 1}/{len(products)}**\n\n"
            f"**Produit:** {title}\n"
            f"**Prix:** ${price:.2f}\n\n"
            f"Envoyez le fichier (PDF, ZIP, etc.)\n"
            f"Ou cliquez Skip pour ne pas importer ce produit."
        )

        keyboard = [
            [InlineKeyboardButton("⏭️ Ne pas importer ce produit", callback_data='skip_import_file')]
        ]

        await message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def handle_import_file_upload(self, bot, update):
        """Handle fichier uploadé durant import séquentiel"""
        user_id = update.effective_user.id
        lang = bot.get_user_language(user_id)
        user_state = bot.state_manager.get_state(user_id)

        if user_state.get('step') != 'uploading_files':
            return  # Pas en mode upload import

        products = user_state.get('import_products', [])
        current_index = user_state.get('upload_current_index', 0)
        upload_results = user_state.get('upload_results', [])

        if current_index >= len(products):
            return

        product = products[current_index]

        # Upload fichier vers R2
        try:
            from app.core.utils import generate_product_id
            product_id = generate_product_id()

            file = await update.message.document.get_file()
            file_bytes = await file.download_as_bytearray()
            file_name = update.message.document.file_name
            file_size_mb = len(file_bytes) / (1024 * 1024)

            # Upload vers R2
            from app.services.b2_storage_service import B2StorageService
            b2 = B2StorageService()

            object_key = f"products/{product_id}/main/{file_name}"

            # Save bytes to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file_name}") as temp_file:
                temp_file.write(file_bytes)
                temp_path = temp_file.name

            try:
                main_file_url = await b2.upload_file(temp_path, object_key)
            finally:
                os.remove(temp_path)

            # Download cover image si existe
            cover_url = None
            if product.get('image_url'):
                try:
                    cover_url = await download_cover_image(product['image_url'], product_id)
                except Exception as e:
                    logger.warning(f"Failed download cover: {e}")

            # Store result
            upload_results.append({
                'product': product,
                'product_id': product_id,
                'main_file_url': main_file_url,
                'file_size_mb': file_size_mb,
                'cover_image_url': cover_url,
                'status': 'uploaded'
            })

            await update.message.reply_text(
                f"✅ Fichier reçu pour: **{product['title']}**",
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Upload error: {e}")

            upload_results.append({
                'product': product,
                'status': 'error',
                'error': str(e)
            })

            await update.message.reply_text(
                f"❌ Erreur upload: {str(e)}\n\nContinuons avec le suivant.",
                parse_mode='Markdown'
            )

        # Update state
        next_index = current_index + 1
        bot.state_manager.update_state(
            user_id,
            upload_current_index=next_index,
            upload_results=upload_results
        )

        # Passer au suivant ou finaliser
        if next_index < len(products):
            await self.request_next_file(bot, update.message, products, next_index, lang)
        else:
            await self.finalize_import(bot, update, upload_results, lang)

    async def skip_import_file(self, bot, query, lang):
        """Skip upload fichier pour un produit"""
        await query.answer()

        user_id = query.from_user.id
        user_state = bot.state_manager.get_state(user_id)

        products = user_state.get('import_products', [])
        current_index = user_state.get('upload_current_index', 0)
        upload_results = user_state.get('upload_results', [])

        product = products[current_index]

        # Marquer comme skipped
        upload_results.append({
            'product': product,
            'status': 'skipped'
        })

        await query.edit_message_text(
            f"⏭️ Produit skippé: **{product['title']}**",
            parse_mode='Markdown'
        )

        # Passer au suivant
        next_index = current_index + 1
        bot.state_manager.update_state(
            user_id,
            upload_current_index=next_index,
            upload_results=upload_results
        )

        if next_index < len(products):
            await self.request_next_file(bot, query.message, products, next_index, lang)
        else:
            await self.finalize_import(bot, query.message, upload_results, lang)

    async def finalize_import(self, bot, message_or_update, upload_results, lang):
        """Finaliser import - Créer produits en DB"""

        if hasattr(message_or_update, 'message'):
            message = message_or_update.message
            user_id = message_or_update.effective_user.id
        else:
            message = message_or_update
            user_id = message.from_user.id

        user_state = bot.state_manager.get_state(user_id)
        source_url = user_state.get('import_source_url', '')

        imported_count = 0
        skipped_count = 0
        errors = []

        for result in upload_results:
            if result['status'] == 'skipped':
                skipped_count += 1
                continue

            if result['status'] == 'error':
                errors.append(f"• {result['product']['title']}: {result.get('error', 'Unknown')}")
                continue

            # Créer produit en DB (status='active')
            try:
                product_data = result['product']

                self.product_repo.insert_product({
                    'product_id': result['product_id'],
                    'seller_user_id': user_id,
                    'title': product_data['title'],
                    'description': product_data.get('description', ''),
                    'price_usd': product_data['price'],
                    'main_file_url': result['main_file_url'],
                    'file_size_mb': result['file_size_mb'],
                    'cover_image_url': result.get('cover_image_url'),
                    'status': 'active',  # Publié direct
                    'imported_from': 'gumroad',
                    'imported_url': product_data.get('gumroad_url'),
                    'source_profile': source_url
                })

                imported_count += 1

            except Exception as e:
                logger.error(f"Error creating product: {e}")
                errors.append(f"• {product_data['title']}: DB error")

        # Message final
        result_text = "✅ **Import terminé!**\n\n"
        result_text += f"📊 **Résumé:**\n"
        result_text += f"• Importés: {imported_count}\n"

        if skipped_count > 0:
            result_text += f"• Skippés: {skipped_count}\n"

        if errors:
            result_text += f"• Erreurs: {len(errors)}\n\n"
            result_text += "**Erreurs:**\n"
            for err in errors[:5]:
                result_text += f"{err}\n"

        result_text += f"\nVos produits sont maintenant publiés!\n"
        result_text += "Utilisez /stats pour voir votre dashboard."

        # Cleanup state
        bot.state_manager.update_state(
            user_id,
            importing_shop=False,
            creating_seller_for_import=False,
            step=None,
            import_products=None,
            upload_current_index=None,
            upload_results=None
        )

        await message.reply_text(
            result_text,
            parse_mode='Markdown'
        )

    async def cancel_import(self, bot, query, lang):
        """Annuler import en attente"""
        await query.answer()

        user_id = query.from_user.id

        # Cleanup state
        bot.state_manager.update_state(
            user_id,
            importing_shop=False,
            creating_seller_for_import=False,
            step=None,
            import_products=None,
            pending_import=None
        )

        await safe_transition_to_text(
            query,
            "Import annulé" if lang == 'fr' else "Import cancelled",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Retour" if lang == 'fr' else "Back", callback_data='back_main')
            ]])
        )
