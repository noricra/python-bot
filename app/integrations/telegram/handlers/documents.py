import logging
import os
from io import BytesIO
from typing import Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


logger = logging.getLogger(__name__)


async def document_upload_handler(bot_controller, update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in bot_controller.memory_cache:
        await update.message.reply_text(
            "❌ **Session expirée**\n\nRecommencez l'ajout de produit.",
            reply_markup=InlineKeyboardMarkup([[ 
                InlineKeyboardButton("➕ Ajouter produit", callback_data='add_product')
            ]])
        )
        return

    user_state = bot_controller.memory_cache[user_id]

    if not user_state.get('adding_product') or user_state.get('step') != 'file':
        await update.message.reply_text(
            "❌ **Étape incorrecte**\n\nVous devez d'abord remplir les informations du produit.",
            reply_markup=InlineKeyboardMarkup([[ 
                InlineKeyboardButton("➕ Ajouter produit", callback_data='add_product')
            ]])
        )
        return

    document = update.message.document
    if not document:
        await update.message.reply_text(
            "❌ **Aucun fichier détecté**\n\nEnvoyez un fichier en pièce jointe."
        )
        return

    # Vérifier taille
    try:
        file_size_mb = document.file_size / (1024 * 1024)
        if document.file_size > bot_controller.MAX_FILE_SIZE_MB * 1024 * 1024:  # type: ignore[attr-defined]
            await update.message.reply_text(
                f"❌ **Fichier trop volumineux**\n\nTaille max : {bot_controller.MAX_FILE_SIZE_MB}MB\nVotre fichier : {file_size_mb:.1f}MB",
                parse_mode='Markdown'
            )
            return
    except Exception as e:
        logger.error(f"Erreur vérification taille fichier: {e}")
        await update.message.reply_text("❌ **Erreur lors de la vérification de la taille du fichier**")
        return

    # Vérifier extension
    try:
        if not document.file_name:
            await update.message.reply_text("❌ **Nom de fichier invalide**")
            return

        file_ext = os.path.splitext(document.file_name)[1].lower()
        if file_ext not in bot_controller.SUPPORTED_FILE_TYPES:  # type: ignore[attr-defined]
            await update.message.reply_text(
                f"❌ **Format non supporté :** {file_ext}\n\n✅ **Formats acceptés :** {', '.join(bot_controller.SUPPORTED_FILE_TYPES)}",
                parse_mode='Markdown'
            )
            return
    except Exception as e:
        logger.error(f"Erreur vérification extension fichier: {e}")
        await update.message.reply_text("❌ **Erreur lors de la vérification du format de fichier**")
        return

    try:
        await update.message.reply_text("📤 **Upload en cours...**", parse_mode='Markdown')

        uploads_dir = os.path.join('uploads')
        os.makedirs(uploads_dir, exist_ok=True)

        file = await document.get_file()

        product_id = bot_controller.generate_product_id()
        filename = f"{product_id}_{bot_controller.sanitize_filename(document.file_name)}"
        filepath = os.path.join(uploads_dir, filename)

        try:
            await file.download_to_drive(filepath)
            logger.info(f"Fichier téléchargé avec succès: {filepath}")
        except Exception as download_error:
            logger.error(f"Erreur téléchargement fichier: {download_error}")
            await update.message.reply_text(
                f"❌ **Erreur de téléchargement**\n\nDétail: {str(download_error)[:100]}...",
                parse_mode='Markdown'
            )
            return

        if not os.path.exists(filepath):
            await update.message.reply_text("❌ **Fichier non sauvegardé**")
            return

        product_data: Dict = user_state['product_data']
        product_data['main_file_path'] = filepath
        product_data['file_size_mb'] = file_size_mb

        try:
            success = await bot_controller.create_product_in_database(user_id, product_id, product_data)
        except Exception as db_error:
            logger.error(f"Erreur base de données: {db_error}")
            if os.path.exists(filepath):
                os.remove(filepath)
            await update.message.reply_text(
                f"❌ **Erreur base de données**\n\nDétail: {str(db_error)[:100]}...",
                parse_mode='Markdown'
            )
            return

        if success:
            del bot_controller.memory_cache[user_id]

            safe_filename = bot_controller.escape_markdown(filename)
            safe_title = bot_controller.escape_markdown(product_data['title'])
            safe_category = bot_controller.escape_markdown(product_data['category'])

            success_text = f"""🎉 **FORMATION CRÉÉE AVEC SUCCÈS \!**

✅ **ID Produit :** `{product_id}`
📦 **Titre :** {safe_title}
💰 **Prix :** {product_data['price_eur']}€
📂 **Catégorie :** {safe_category}
📁 **Fichier :** {safe_filename}

🚀 **Votre formation est maintenant en vente \!**

🔗 **Lien direct :** Les clients peuvent la trouver avec l'ID `{product_id}`"""

            keyboard = [[
                InlineKeyboardButton("📊 Voir mon produit",
                                     callback_data=f'product_{product_id}')
            ],
                        [
                            InlineKeyboardButton(
                                "🏪 Mon dashboard",
                                callback_data='seller_dashboard')
                        ],
                        [
                            InlineKeyboardButton(
                                "➕ Créer un autre",
                                callback_data='add_product')
                        ]]

            await update.message.reply_text(
                success_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown')
        else:
            if os.path.exists(filepath):
                os.remove(filepath)

            await update.message.reply_text(
                "❌ **Erreur lors de la création du produit**\n\nVérifiez que tous les champs sont remplis.",
                reply_markup=InlineKeyboardMarkup([[ 
                    InlineKeyboardButton("🔄 Réessayer",
                                         callback_data='add_product')
                ]]),
                parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Erreur upload fichier (général): {e}")
        await update.message.reply_text(
            f"❌ **Erreur lors de l'upload**\n\nDétail: {str(e)[:100]}...\n\nVérifiez:\n• Format de fichier supporté\n• Taille < {bot_controller.MAX_FILE_SIZE_MB}MB\n• Connexion stable",
            reply_markup=InlineKeyboardMarkup([[ 
                InlineKeyboardButton("🔄 Réessayer",
                                     callback_data='add_product')
            ]]),
            parse_mode='Markdown')

