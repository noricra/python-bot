"""Support Handlers - Support and ticket management functions with dependency injection"""

from typing import Optional, List, Dict
import psycopg2.extras
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.services.messaging_service import MessagingService
from app.core import settings as core_settings
from app.core.db_pool import put_connection
from app.integrations.telegram.keyboards import back_to_main_button


# FAQ Data Structure (French) - REORGANIZED BY RELEVANCE
FAQ_DATA_FR: List[Dict[str, str]] = [
    # BLOC 1: ACHETER (Le plus important)
    {
        "category": "ACHETER UN PRODUIT",
        "question": "Comment acheter un produit ? (Guide complet)",
        "answer": (
            "**Étape 1:** Menu \"Acheter\" > Parcourir catégories ou rechercher par ID\n"
            "**Étape 2:** Cliquer sur le produit souhaité pour voir les détails\n"
            "**Étape 3:** Cliquer \"Acheter\" puis choisir votre crypto (BTC, ETH, SOL, USDT, USDC)\n"
            "**Étape 4:** Le bot affiche une adresse crypto + QR code\n"
            "**Étape 5:** Ouvrir votre wallet crypto (Binance, Trust Wallet, Coinbase, etc.)\n"
            "**Étape 6:** Envoyer le montant EXACT indiqué à l'adresse fournie\n"
            "**Étape 7:** Attendre la confirmation blockchain (5-30 min selon la crypto)\n"
            "**Étape 8:** Livraison automatique du fichier dans \"Ma bibliothèque\"\n\n"
            "IMPORTANT: N'envoyez JAMAIS un montant différent, cela pourrait bloquer le paiement."
        )
    },
    {
        "category": "ACHETER UN PRODUIT",
        "question": "Quelles cryptomonnaies sont acceptées ?",
        "answer": (
            "Le bot accepte **5 cryptomonnaies majeures** :\n\n"
            "**Bitcoin (BTC)** - La plus sécurisée et décentralisée\n"
            "**Ethereum (ETH)** - Rapide et fiable\n"
            "**Solana (SOL)** - Ultra rapide (1-5 min) et frais très bas\n"
            "**USDT (Tether)** - Stablecoin indexé sur le dollar US\n"
            "**USDC (USD Coin)** - Stablecoin réglementé et audité\n\n"
            "CONSEIL: Utilisez **USDT** ou **USDC** si vous voulez éviter la volatilité des prix.\n"
            "Utilisez **Solana** pour des paiements quasi-instantanés."
        )
    },
    {
        "category": "ACHETER UN PRODUIT",
        "question": "Dois-je fournir mes données personnelles (KYC) ?",
        "answer": (
            "**NON, aucune vérification KYC requise.**\n\n"
            "Pas de nom, pas d'adresse, pas de carte d'identité, pas de selfie.\n\n"
            "Cette plateforme est axée sur la **confidentialité** et l'**anonymat**. "
            "Vous n'avez besoin que d'un compte Telegram et d'un wallet crypto pour acheter ou vendre."
        )
    },
    # BLOC 2: VENDRE (Important pour vendeurs)
    {
        "category": "VENDRE VOS PRODUITS",
        "question": "Comment devenir vendeur ?",
        "answer": (
            "**En 3 étapes simples** :\n\n"
            "**1.** Menu \"Vendre\" > \"Créer un compte vendeur\"\n"
            "**2.** Configurez votre **adresse wallet Solana** (pour recevoir les paiements)\n"
            "**3.** Uploadez votre premier produit (titre, description, fichier, prix)\n\n"
            "**Types de produits acceptés** :\n"
            "- eBooks (PDF, EPUB)\n"
            "- Formations vidéo (MP4, AVI, MKV)\n"
            "- Fichiers audio (MP3, WAV, FLAC)\n"
            "- Archives (ZIP, RAR, 7Z)\n"
            "- Templates, Presets (PSD, AI, Sketch, etc.)\n"
            "- Code source (PY, JS, HTML, CSS, etc.) - Fichiers texte uniquement\n\n"
            "**Limite par fichier** : Jusqu'à 100 MB par fichier\n"
            "**Stockage total** : 100 MB gratuits (contactez le support pour extension)\n\n"
            "**IMPORTANT** : Les fichiers exécutables (EXE, BAT, SH, APP, etc.) sont bloqués pour raisons de sécurité."
        )
    },
    {
        "category": "VENDRE VOS PRODUITS",
        "question": "Quels sont les avantages vendeur ?",
        "answer": (
            "**Frais les plus bas du marché** - Seulement les frais techniques obligatoires (NowPayments, slippage, spread, frais blockchain)\n"
            "**Aucun KYC requis** - Vendez en toute confidentialité\n"
            "**Paiements crypto directs** - Recevez vos gains sur votre wallet Solana\n"
            "**Portée internationale** - Vendez partout dans le monde sans restrictions\n"
            "**Livraison automatique** - Vos clients reçoivent le produit instantanément après paiement\n"
            "**Stockage sécurisé** - 100MB gratuits avec extension possible\n"
            "**Support 24/7** - Système de tickets pour toute question\n\n"
            "Contrairement aux plateformes traditionnelles (Gumroad 9%, Shopify 2.9%+30¢), "
            "vous gardez le **contrôle total** de vos revenus avec les frais les plus compétitifs."
        )
    },
    {
        "category": "VENDRE VOS PRODUITS",
        "question": "Quand et comment suis-je payé en tant que vendeur ?",
        "answer": (
            "**Processus de paiement vendeur** :\n\n"
            "**1.** Un client achète votre produit\n"
            "**2.** Paiement confirmé sur la blockchain\n"
            "**3.** Vérification anti-fraude manuelle (sécurité)\n"
            "**4.** Payout envoyé directement sur votre **wallet Solana**\n\n"
            "**Délai** : Généralement 24-48h après la vérification anti-fraude\n"
            "**Frais** : Frais techniques minimaux (NowPayments, slippage, spread, frais blockchain) - Les plus bas du marché\n"
            "**Monnaie** : Payout en USDT (stablecoin) sur le réseau Solana\n\n"
            "Vous pouvez suivre vos payouts dans \"Payouts / Adresse\" du dashboard vendeur."
        )
    },
    # BLOC 3: SUPPORT (Important pour résolution)
    {
        "category": "SUPPORT",
        "question": "Comment contacter le support ?",
        "answer": (
            "Support disponible **24/7** via le système de tickets :\n\n"
            "**1.** Menu \"Support\" > \"Créer un ticket\"\n"
            "**2.** Saisissez le sujet de votre demande\n"
            "**3.** Décrivez votre problème en détail\n"
            "**4.** Fournissez votre email pour recevoir une réponse\n"
            "**5.** Notre équipe répond sous 2-24h\n\n"
            "**Types de problèmes traités** :\n"
            "- Paiement non reçu\n"
            "- Fichier non livré\n"
            "- Problème technique\n"
            "- Question sur un payout vendeur\n"
            "- Signalement de contenu frauduleux\n"
            "- Autre demande"
        )
    },
    {
        "category": "SUPPORT",
        "question": "Puis-je signaler un problème avec un achat ?",
        "answer": (
            "Oui ! Vous disposez de **24 heures** après l'achat pour signaler un problème :\n\n"
            "**1.** Allez dans \"Ma bibliothèque\"\n"
            "**2.** Cliquez sur le produit concerné\n"
            "**3.** Utilisez le bouton \"Signaler un problème\"\n"
            "**4.** Décrivez le problème (fichier corrompu, contenu manquant, etc.)\n\n"
            "**Problèmes couramment signalés** :\n"
            "- Fichier corrompu ou illisible\n"
            "- Contenu différent de la description\n"
            "- Fichier vide ou incomplet\n"
            "- Mauvaise qualité (vidéo, audio)\n\n"
            "Un ticket est automatiquement créé et notre équipe examine le cas rapidement."
        )
    },
    {
        "category": "SUPPORT",
        "question": "Que faire si je ne reçois pas mon fichier ?",
        "answer": (
            "Si vous ne recevez pas votre fichier après paiement confirmé :\n\n"
            "**1.** Vérifiez \"Ma bibliothèque\" - Le fichier y est peut-être déjà\n"
            "**2.** Attendez 30 minutes - Certaines cryptos prennent du temps (BTC, ETH)\n"
            "**3.** Vérifiez votre paiement sur blockchain - Utilisez un explorateur (blockchain.com pour BTC)\n"
            "**4.** Contactez le support - Menu \"Support\" > \"Créer un ticket\"\n\n"
            "**Informations à fournir au support** :\n"
            "- ID de la commande\n"
            "- ID de transaction crypto (TxHash)\n"
            "- Montant envoyé\n\n"
            "Le support répond généralement sous 2-24h."
        )
    },
    # BLOC 4: BIBLIOTHÈQUE
    {
        "category": "BIBLIOTHÈQUE",
        "question": "Comment accéder à mes achats ?",
        "answer": (
            "Tous vos produits achetés sont stockés dans **\"Ma bibliothèque\"** :\n\n"
            "**1.** Menu principal > \"Ma bibliothèque\"\n"
            "**2.** Parcourez la liste de vos produits achetés\n"
            "**3.** Cliquez sur un produit pour le télécharger à nouveau\n\n"
            "**Téléchargements illimités** - Vous pouvez re-télécharger autant de fois que vous voulez\n"
            "**Accès permanent** - Vos produits restent disponibles indéfiniment\n"
            "**Aucune expiration** - Pas de limite de temps\n\n"
            "CONSEIL: Sauvegardez vos fichiers importants dans votre cloud personnel (Google Drive, Dropbox...)"
        )
    },
    {
        "category": "BIBLIOTHÈQUE",
        "question": "Puis-je contacter le vendeur après un achat ?",
        "answer": (
            "Oui ! Vous pouvez contacter le vendeur directement depuis votre bibliothèque :\n\n"
            "**1.** Allez dans \"Ma bibliothèque\"\n"
            "**2.** Cliquez sur le produit acheté\n"
            "**3.** Utilisez le bouton \"Contacter le vendeur\"\n\n"
            "Un système de **messagerie interne** s'ouvre pour discuter avec le vendeur.\n"
            "Utile pour poser des questions, signaler un problème, ou demander une mise à jour."
        )
    },
    # BLOC 5: SÉCURITÉ
    {
        "category": "SÉCURITÉ",
        "question": "La plateforme est-elle sécurisée ?",
        "answer": (
            "**Oui, voici nos garanties de sécurité** :\n\n"
            "**Paiements crypto** via NOWPayments (certifié PCI DSS, leader mondial)\n"
            "**Stockage cloud sécurisé** - Fichiers accessibles 24/7\n"
            "**Telegram chiffré** - Toutes les communications passent par Telegram (end-to-end encryption)\n"
            "**Anti-fraude** - Vérification manuelle des transactions avant payout vendeur\n"
            "**Pas de collecte de données** - Aucune information personnelle stockée (pas de KYC)\n"
            "**Livraison automatique** - Fichiers livrés instantanément après confirmation blockchain\n\n"
            "Les paiements crypto sont irréversibles, ce qui protège les vendeurs contre les chargebacks frauduleux."
        )
    },
    # BLOC 6: DÉTAILS TECHNIQUES (Moins prioritaire)
    {
        "category": "DÉTAILS TECHNIQUES",
        "question": "Combien de temps prend un paiement crypto ?",
        "answer": (
            "**Temps de confirmation par crypto** :\n\n"
            "**Bitcoin (BTC)** : 10-60 minutes (nécessite 6 confirmations blockchain)\n"
            "**Ethereum (ETH)** : 5-15 minutes (nécessite 12 confirmations)\n"
            "**Solana (SOL)** : 1-5 minutes (le plus rapide)\n"
            "**USDT/USDC** : 5-15 minutes (selon le réseau utilisé)\n\n"
            "Si votre paiement prend plus de 2 heures, contactez le support avec votre **ID de transaction**."
        )
    },
    {
        "category": "DÉTAILS TECHNIQUES",
        "question": "Comment obtenir un wallet Solana pour recevoir mes payouts ?",
        "answer": (
            "Pour recevoir vos payouts vendeur, vous avez besoin d'un **wallet Solana** :\n\n"
            "**Option 1: Phantom Wallet** (recommandé)\n"
            "- Télécharger l'extension Chrome ou l'app mobile\n"
            "- Créer un nouveau wallet\n"
            "- Copier votre adresse Solana (~44 caractères)\n\n"
            "**Option 2: Binance**\n"
            "- Créer un compte Binance\n"
            "- Aller dans \"Wallet\" > \"Dépôt\"\n"
            "- Chercher \"SOL\" (Solana)\n"
            "- Copier l'adresse de dépôt\n\n"
            "**Option 3: Coinbase**\n"
            "- Créer un compte Coinbase\n"
            "- Aller dans \"Receive\"\n"
            "- Sélectionner \"Solana (SOL)\"\n"
            "- Copier l'adresse\n\n"
            "Configurez cette adresse dans votre dashboard vendeur (\"Payouts / Adresse\")."
        )
    },
    {
        "category": "DÉTAILS TECHNIQUES",
        "question": "Puis-je payer par carte bancaire ?",
        "answer": (
            "**Non, uniquement paiements crypto**.\n\n"
            "**Pourquoi crypto uniquement ?**\n"
            "- **Anonymat** - Pas de KYC, pas de collecte de données\n"
            "- **International** - Fonctionne dans tous les pays\n"
            "- **Rapide** - Confirmation en quelques minutes\n"
            "- **Frais les plus bas** - Frais techniques minimaux vs Stripe/PayPal (3-5%)\n"
            "- **Pas de chargeback** - Protection contre la fraude vendeur\n\n"
            "**Vous n'avez jamais utilisé la crypto ?**\n"
            "**1.** Créez un compte sur **Binance** ou **Coinbase**\n"
            "**2.** Achetez de la crypto avec votre carte (USDT recommandé)\n"
            "**3.** Envoyez-la à l'adresse fournie par le bot\n\n"
            "C'est aussi simple qu'un virement bancaire !"
        )
    },
    {
        "category": "DÉTAILS TECHNIQUES",
        "question": "Quelles sont les commandes slash disponibles ?",
        "answer": (
            "Le bot supporte plusieurs **commandes rapides** :\n\n"
            "**/start** - Ouvrir le menu principal\n"
            "**/achat** - Accès direct au menu d'achat\n"
            "**/vendre** - Accès direct au menu vendeur\n"
            "**/library** - Accès direct à votre bibliothèque\n"
            "**/stats** - Dashboard vendeur (si vous êtes vendeur)\n"
            "**/support** - Créer un ticket de support rapidement\n\n"
            "Ces commandes vous permettent d'accéder rapidement aux fonctionnalités "
            "sans passer par le menu principal."
        )
    }
]

# FAQ Data Structure (English) - REORGANIZED BY RELEVANCE
FAQ_DATA_EN: List[Dict[str, str]] = [
    # BLOCK 1: BUYING (Most important)
    {
        "category": "BUYING A PRODUCT",
        "question": "How to buy a product? (Complete guide)",
        "answer": (
            "**Step 1:** Menu \"Buy\" > Browse categories or search by ID\n"
            "**Step 2:** Click on desired product to see details\n"
            "**Step 3:** Click \"Buy\" then choose your crypto (BTC, ETH, SOL, USDT, USDC)\n"
            "**Step 4:** Bot displays crypto address + QR code\n"
            "**Step 5:** Open your crypto wallet (Binance, Trust Wallet, Coinbase, etc.)\n"
            "**Step 6:** Send the EXACT amount shown to the provided address\n"
            "**Step 7:** Wait for blockchain confirmation (5-30 min depending on crypto)\n"
            "**Step 8:** Automatic file delivery to \"My Library\"\n\n"
            "IMPORTANT: NEVER send a different amount, this could block the payment."
        )
    },
    {
        "category": "BUYING A PRODUCT",
        "question": "Which cryptocurrencies are accepted?",
        "answer": (
            "The bot accepts **5 major cryptocurrencies**:\n\n"
            "**Bitcoin (BTC)** - Most secure and decentralized\n"
            "**Ethereum (ETH)** - Fast and reliable\n"
            "**Solana (SOL)** - Ultra fast (1-5 min) and very low fees\n"
            "**USDT (Tether)** - Stablecoin pegged to US dollar\n"
            "**USDC (USD Coin)** - Regulated and audited stablecoin\n\n"
            "TIP: Use **USDT** or **USDC** if you want to avoid price volatility.\n"
            "Use **Solana** for near-instant payments."
        )
    },
    {
        "category": "BUYING A PRODUCT",
        "question": "Do I need to provide personal data (KYC)?",
        "answer": (
            "**NO, no KYC verification required.**\n\n"
            "No name, no address, no ID card, no selfie.\n\n"
            "This platform focuses on **privacy** and **anonymity**. "
            "You only need a Telegram account and a crypto wallet to buy or sell."
        )
    },
    # BLOCK 2: SELLING (Important for sellers)
    {
        "category": "SELLING YOUR PRODUCTS",
        "question": "How to become a seller?",
        "answer": (
            "**In 3 simple steps**:\n\n"
            "**1.** Menu \"Sell\" > \"Create seller account\"\n"
            "**2.** Configure your **Solana wallet address** (to receive payments)\n"
            "**3.** Upload your first product (title, description, file, price)\n\n"
            "**Accepted product types**:\n"
            "- eBooks (PDF, EPUB)\n"
            "- Video courses (MP4, AVI, MKV)\n"
            "- Audio files (MP3, WAV, FLAC)\n"
            "- Archives (ZIP, RAR, 7Z)\n"
            "- Templates, Presets (PSD, AI, Sketch, etc.)\n"
            "- Source code (PY, JS, HTML, CSS, etc.) - Text files only\n\n"
            "**Per file limit**: Up to 100 MB per file\n"
            "**Total storage**: 100 MB free (contact support for extension)\n\n"
            "**IMPORTANT**: Executable files (EXE, BAT, SH, APP, etc.) are blocked for security reasons."
        )
    },
    {
        "category": "SELLING YOUR PRODUCTS",
        "question": "What are the seller advantages?",
        "answer": (
            "**Lowest fees on the market** - Only mandatory technical fees (NowPayments, slippage, spread, blockchain fees)\n"
            "**No KYC required** - Sell with complete privacy\n"
            "**Direct crypto payments** - Receive earnings to your Solana wallet\n"
            "**Global reach** - Sell worldwide without restrictions\n"
            "**Automatic delivery** - Customers receive product instantly after payment\n"
            "**Secure storage** - 100MB free with possible extension\n"
            "**24/7 Support** - Ticket system for any question\n\n"
            "Unlike traditional platforms (Gumroad 9%, Shopify 2.9%+30¢), "
            "you keep **full control** of your revenue with the most competitive fees."
        )
    },
    {
        "category": "SELLING YOUR PRODUCTS",
        "question": "When and how do I get paid as a seller?",
        "answer": (
            "**Seller payment process**:\n\n"
            "**1.** A customer buys your product\n"
            "**2.** Payment confirmed on blockchain\n"
            "**3.** Manual anti-fraud verification (security)\n"
            "**4.** Payout sent directly to your **Solana wallet**\n\n"
            "**Delay**: Usually 24-48h after anti-fraud verification\n"
            "**Fees**: Minimal technical fees (NowPayments, slippage, spread, blockchain fees) - Lowest on the market\n"
            "**Currency**: Payout in USDT (stablecoin) on Solana network\n\n"
            "You can track your payouts in \"Payouts / Address\" from seller dashboard."
        )
    },
    # BLOCK 3: SUPPORT (Important for problem resolution)
    {
        "category": "SUPPORT",
        "question": "How to contact support?",
        "answer": (
            "Support available **24/7** via ticket system:\n\n"
            "**1.** Menu \"Support\" > \"Create ticket\"\n"
            "**2.** Enter your request subject\n"
            "**3.** Describe your problem in detail\n"
            "**4.** Provide your email to receive a response\n"
            "**5.** Our team responds within 2-24h\n\n"
            "**Types of issues handled**:\n"
            "- Payment not received\n"
            "- File not delivered\n"
            "- Technical problem\n"
            "- Question about seller payout\n"
            "- Fraudulent content report\n"
            "- Other request"
        )
    },
    {
        "category": "SUPPORT",
        "question": "Can I report a problem with a purchase?",
        "answer": (
            "Yes! You have **24 hours** after purchase to report a problem:\n\n"
            "**1.** Go to \"My Library\"\n"
            "**2.** Click on the concerned product\n"
            "**3.** Use the \"Report problem\" button\n"
            "**4.** Describe the issue (corrupted file, missing content, etc.)\n\n"
            "**Commonly reported problems**:\n"
            "- Corrupted or unreadable file\n"
            "- Content different from description\n"
            "- Empty or incomplete file\n"
            "- Poor quality (video, audio)\n\n"
            "A ticket is automatically created and our team examines the case quickly."
        )
    },
    {
        "category": "SUPPORT",
        "question": "What if I don't receive my file?",
        "answer": (
            "If you don't receive your file after confirmed payment:\n\n"
            "**1.** Check \"My Library\" - The file might already be there\n"
            "**2.** Wait 30 minutes - Some cryptos take time (BTC, ETH)\n"
            "**3.** Check your payment on blockchain - Use an explorer (blockchain.com for BTC)\n"
            "**4.** Contact support - Menu \"Support\" > \"Create ticket\"\n\n"
            "**Information to provide to support**:\n"
            "- Order ID\n"
            "- Crypto transaction ID (TxHash)\n"
            "- Amount sent\n\n"
            "Support usually responds within 2-24h."
        )
    },
    # BLOCK 4: LIBRARY
    {
        "category": "LIBRARY",
        "question": "How to access my purchases?",
        "answer": (
            "All your purchased products are stored in **\"My Library\"**:\n\n"
            "**1.** Main menu > \"My Library\"\n"
            "**2.** Browse your list of purchased products\n"
            "**3.** Click on a product to download it again\n\n"
            "**Unlimited downloads** - You can re-download as many times as you want\n"
            "**Permanent access** - Your products remain available indefinitely\n"
            "**No expiration** - No time limit\n\n"
            "TIP: Save your important files to your personal cloud (Google Drive, Dropbox...)"
        )
    },
    {
        "category": "LIBRARY",
        "question": "Can I contact the seller after a purchase?",
        "answer": (
            "Yes! You can contact the seller directly from your library:\n\n"
            "**1.** Go to \"My Library\"\n"
            "**2.** Click on the purchased product\n"
            "**3.** Use the \"Contact seller\" button\n\n"
            "An **internal messaging system** opens to chat with the seller.\n"
            "Useful for asking questions, reporting issues, or requesting updates."
        )
    },
    # BLOCK 5: SECURITY
    {
        "category": "SECURITY",
        "question": "Is the platform secure?",
        "answer": (
            "**Yes, here are our security guarantees**:\n\n"
            "**Crypto payments** via NOWPayments (PCI DSS certified, global leader)\n"
            "**Secure cloud storage** - Files accessible 24/7\n"
            "**Encrypted Telegram** - All communications through Telegram (end-to-end encryption)\n"
            "**Anti-fraud** - Manual transaction verification before seller payout\n"
            "**No data collection** - No personal information stored (no KYC)\n"
            "**Automatic delivery** - Files delivered instantly after blockchain confirmation\n\n"
            "Crypto payments are irreversible, which protects sellers against fraudulent chargebacks."
        )
    },
    # BLOCK 6: TECHNICAL DETAILS (Less priority)
    {
        "category": "TECHNICAL DETAILS",
        "question": "How long does a crypto payment take?",
        "answer": (
            "**Confirmation time by crypto**:\n\n"
            "**Bitcoin (BTC)**: 10-60 minutes (requires 6 blockchain confirmations)\n"
            "**Ethereum (ETH)**: 5-15 minutes (requires 12 confirmations)\n"
            "**Solana (SOL)**: 1-5 minutes (fastest)\n"
            "**USDT/USDC**: 5-15 minutes (depending on network)\n\n"
            "If your payment takes more than 2 hours, contact support with your **transaction ID**."
        )
    },
    {
        "category": "TECHNICAL DETAILS",
        "question": "How to get a Solana wallet to receive payouts?",
        "answer": (
            "To receive seller payouts, you need a **Solana wallet**:\n\n"
            "**Option 1: Phantom Wallet** (recommended)\n"
            "- Download Chrome extension or mobile app\n"
            "- Create new wallet\n"
            "- Copy your Solana address (~44 characters)\n\n"
            "**Option 2: Binance**\n"
            "- Create Binance account\n"
            "- Go to \"Wallet\" > \"Deposit\"\n"
            "- Search \"SOL\" (Solana)\n"
            "- Copy Solana deposit address\n\n"
            "**Option 3: Coinbase**\n"
            "- Create Coinbase account\n"
            "- Go to \"Receive\"\n"
            "- Select \"Solana (SOL)\"\n"
            "- Copy address\n\n"
            "Configure this address in your seller dashboard (\"Payouts / Address\")."
        )
    },
    {
        "category": "TECHNICAL DETAILS",
        "question": "Can I pay with credit card?",
        "answer": (
            "**No, only crypto payments**.\n\n"
            "**Why crypto only?**\n"
            "- **Anonymity** - No KYC, no data collection\n"
            "- **International** - Works in all countries\n"
            "- **Fast** - Confirmation in minutes\n"
            "- **Lowest fees** - Minimal technical fees vs Stripe/PayPal (3-5%)\n"
            "- **No chargeback** - Protection against seller fraud\n\n"
            "**Never used crypto?**\n"
            "**1.** Create account on **Binance** or **Coinbase**\n"
            "**2.** Buy crypto with your card (USDT recommended)\n"
            "**3.** Send it to address provided by bot\n\n"
            "It's as simple as a bank transfer!"
        )
    },
    {
        "category": "TECHNICAL DETAILS",
        "question": "What slash commands are available?",
        "answer": (
            "The bot supports several **quick commands**:\n\n"
            "**/start** - Open main menu\n"
            "**/achat** - Direct access to buy menu\n"
            "**/vendre** - Direct access to seller menu\n"
            "**/library** - Direct access to your library\n"
            "**/stats** - Seller dashboard (if you're a seller)\n"
            "**/support** - Create support ticket quickly\n\n"
            "These commands let you quickly access features "
            "without going through the main menu."
        )
    }
]


class SupportHandlers:
    def __init__(self, user_repo, product_repo, support_service):
        self.user_repo = user_repo
        self.product_repo = product_repo
        self.support_service = support_service

    async def support_command(self, bot, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Redirige vers la création de ticket de support directement."""
        user = update.effective_user
        user_data = self.user_repo.get_user(user.id)
        lang = user_data['language_code'] if user_data else (user.language_code or 'fr')
        # Ouvre directement la création de ticket
        class DummyQuery:
            def __init__(self, uid):
                self.from_user = type('u', (), {'id': uid})
            async def edit_message_text(self, *args, **kwargs):
                await update.message.reply_text(*args, **kwargs)
        await self.create_ticket_prompt(bot, DummyQuery(user.id), lang)

    async def report_order_problem(self, bot, query, order_id: str, lang: str) -> None:
        """
        Report a problem with a specific order (under 24h)

        Args:
            bot: Bot instance
            query: Callback query
            order_id: The order ID to report a problem for
            lang: User language
        """
        user_id = query.from_user.id

        try:
            # Get order details
            conn = bot.get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute('''
                SELECT o.order_id, o.product_id, p.title, o.completed_at
                FROM orders o
                JOIN products p ON p.product_id = o.product_id
                WHERE o.order_id = %s AND o.buyer_user_id = %s
            ''', (order_id, user_id))

            order = cursor.fetchone()
            put_connection(conn)

            if not order:
                await query.edit_message_text(
                    "❌ Commande introuvable." if lang == 'fr' else "❌ Order not found.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🏠 Menu principal", callback_data='back_main')
                    ]])
                )
                return

            # Set state to wait for problem description
            bot.state_manager.update_state(
                user_id,
                reporting_problem=True,
                problem_order_id=order_id,
                problem_product_title=order['title']
            )

            message_text = f"""⚠️ **SIGNALER UN PROBLÈME**

📦 **Commande:** `{order_id}`
📚 **Produit:** {order['title']}

Décrivez le problème rencontré (sous 24H):
• Fichier corrompu
• Contenu manquant
• Erreur de téléchargement
• Autre problème...

Envoyez votre message maintenant.""" if lang == 'fr' else f"""⚠️ **REPORT A PROBLEM**

📦 **Order:** `{order_id}`
📚 **Product:** {order['title']}

Describe the problem (within 24h):
• Corrupted file
• Missing content
• Download error
• Other issue...

Send your message now."""

            await query.edit_message_text(
                message_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='back_main')
                ]])
            )

        except Exception as e:
            from app.core.db_pool import put_connection
            put_connection(conn)
            import logging
            logging.error(f"Error in report_order_problem: {e}")
            await query.edit_message_text(
                "❌ Erreur lors du signalement." if lang == 'fr' else "❌ Error reporting problem.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Menu principal", callback_data='back_main')
                ]])
            )

    async def contact_seller_start(self, bot, query, product_id: str, lang: str) -> None:
        buyer_id = query.from_user.id
        try:
            conn = bot.get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                '''
                SELECT o.order_id, p.seller_user_id, p.title
                FROM orders o
                JOIN products p ON p.product_id = o.product_id
                WHERE o.buyer_user_id = %s AND o.product_id = %s AND o.payment_status = 'completed'
                ORDER BY o.completed_at DESC LIMIT 1
                ''', (buyer_id, product_id)
            )
            row = cursor.fetchone()
            put_connection(conn)
            if not row:
                await query.edit_message_text("❌ Vous devez avoir acheté ce produit pour contacter le vendeur.")
                return
            order_id, seller_user_id, title = row['order_id'], row['seller_user_id'], row['title']
        except Exception:
            await query.edit_message_text("❌ Erreur lors de l'initiation du contact.")
            return

        ticket_id = MessagingService(bot.db_path).start_or_get_ticket(buyer_id, order_id, seller_user_id, f"Contact vendeur: {title}")
        if not ticket_id:
            await query.edit_message_text("❌ Impossible de créer le ticket.")
            return
        bot.reset_conflicting_states(buyer_id, keep={'waiting_reply_ticket_id'})
        bot.state_manager.update_state(buyer_id, waiting_reply_ticket_id=ticket_id)
        safe_title = bot.escape_markdown(title)
        await query.edit_message_text(
            f"📨 Contact vendeur pour `{safe_title}`\n\n✍️ Écrivez votre message:",
            parse_mode='Markdown'
        )

    async def process_messaging_reply(self, bot, update, message_text: str) -> None:
        user_id = update.effective_user.id
        state = bot.get_user_state(user_id)
        ticket_id = state.get('waiting_reply_ticket_id')
        if not ticket_id:
            await update.message.reply_text("❌ Session expirée. Relancez le contact vendeur depuis votre bibliothèque.")
            return
        msg = message_text.strip()
        if not msg:
            await update.message.reply_text("❌ Message vide.")
            return
        ok = MessagingService(bot.db_path).post_user_message(ticket_id, user_id, msg)
        if not ok:
            await update.message.reply_text("❌ Erreur lors de l'envoi du message.")
            return
        state.pop('waiting_reply_ticket_id', None)
        bot.state_manager.update_state(user_id, **state)
        messages = MessagingService(bot.db_path).list_recent_messages(ticket_id, 5)
        thread = "\n".join([f"[{m['created_at']}] {m['sender_role']}: {m['message']}" for m in reversed(messages)])
        keyboard = [[
            InlineKeyboardButton("↩️ Répondre", callback_data=f'reply_ticket_{ticket_id}'),
            InlineKeyboardButton("🚀 Escalader", callback_data=f'escalate_ticket_{ticket_id}')
        ]]
        await update.message.reply_text(f"✅ Message envoyé.\n\n🧵 Derniers messages:\n{thread}", reply_markup=InlineKeyboardMarkup(keyboard))

    async def view_ticket(self, bot, query, ticket_id: str) -> None:
        messages = MessagingService(bot.db_path).list_recent_messages(ticket_id, 10)
        if not messages:
            await query.edit_message_text("🎫 Aucun message dans ce ticket.")
            return
        thread = "\n".join([f"[{m['created_at']}] {m['sender_role']}: {m['message']}" for m in reversed(messages)])
        keyboard = [[
            InlineKeyboardButton("↩️ Répondre", callback_data=f'reply_ticket_{ticket_id}'),
            InlineKeyboardButton(" Escalader", callback_data=f'escalate_ticket_{ticket_id}')
        ]]
        await query.edit_message_text(f" Thread ticket `{ticket_id}`:\n\n{thread}", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    async def reply_ticket_prepare(self, bot, query, ticket_id: str) -> None:
        bot.reset_conflicting_states(query.from_user.id, keep={'waiting_reply_ticket_id'})
        bot.state_manager.update_state(query.from_user.id, waiting_reply_ticket_id=ticket_id)
        await query.edit_message_text("✍️ Écrivez votre réponse:")

    async def escalate_ticket(self, bot, query, ticket_id: str) -> None:
        admin_id = core_settings.ADMIN_USER_ID or query.from_user.id
        ok = MessagingService(bot.db_path).escalate(ticket_id, admin_id)
        if not ok:
            await query.edit_message_text("❌ Impossible d'escalader ce ticket.")
            return
        await query.edit_message_text(" Ticket escaladé au support.")

    async def admin_tickets(self, bot, query) -> None:
        if core_settings.ADMIN_USER_ID is None or query.from_user.id != core_settings.ADMIN_USER_ID:
            await query.edit_message_text("❌ Accès non autorisé.")
            return
        rows = MessagingService(bot.db_path).list_recent_tickets(10)
        if not rows:
            await query.edit_message_text(" Aucun ticket.")
            return
        text = " Tickets récents:\n\n"
        keyboard = []
        for t in rows:
            text += f"• {t['ticket_id']} — {t['subject']} — {t['status']}\n"
            keyboard.append([
                InlineKeyboardButton("👁️ Voir", callback_data=f"view_ticket_{t['ticket_id']}"),
                InlineKeyboardButton("↩️ Répondre", callback_data=f"admin_reply_ticket_{t['ticket_id']}")
            ])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def admin_reply_prepare(self, bot, query, ticket_id: str) -> None:
        if core_settings.ADMIN_USER_ID is None or query.from_user.id != core_settings.ADMIN_USER_ID:
            await query.edit_message_text("❌ Accès non autorisé.")
            return
        bot.reset_conflicting_states(query.from_user.id, keep={'waiting_admin_reply_ticket_id'})
        bot.state_manager.update_state(query.from_user.id, waiting_admin_reply_ticket_id=ticket_id)
        await query.edit_message_text("✍️ Écrivez votre réponse admin:")

    async def process_admin_reply(self, bot, update, message_text: str) -> None:
        admin_id = update.effective_user.id
        if admin_id != core_settings.ADMIN_USER_ID:
            return
        state = bot.get_user_state(admin_id)
        ticket_id = state.get('waiting_admin_reply_ticket_id')
        if not ticket_id:
            await update.message.reply_text("❌ Session expirée.")
            return
        msg = message_text.strip()
        if not msg:
            await update.message.reply_text("❌ Message vide.")
            return
        ok = MessagingService(bot.db_path).post_admin_message(ticket_id, admin_id, msg)
        if not ok:
            await update.message.reply_text("❌ Erreur lors de l'envoi.")
            return
        state.pop('waiting_admin_reply_ticket_id', None)
        bot.state_manager.update_state(admin_id, **state)
        messages = MessagingService(bot.db_path).list_recent_messages(ticket_id, 10)
        thread = "\n".join([f"[{m['created_at']}] {m['sender_role']}: {m['message']}" for m in reversed(messages)])
        await update.message.reply_text(f"✅ Réponse envoyée.\n\n🧵 Derniers messages:\n{thread}")

    # Support UI Methods - Extracted from bot_mlt.py
    async def support_menu(self, bot, query, lang):
        """Main support menu"""
        # Reset conflicting states when entering support workflow
        if hasattr(query, 'from_user'):
            bot.reset_conflicting_states(query.from_user.id, keep={'lang'})

        await self.show_faq(query, lang)

    async def show_faq(self, query, lang, index: int = 0):
        """FAQ display with pagination"""
        # Get FAQ data based on language
        faq_data = FAQ_DATA_FR if lang == 'fr' else FAQ_DATA_EN

        # Validate index
        if index < 0:
            index = 0
        elif index >= len(faq_data):
            index = len(faq_data) - 1

        # Get current FAQ item
        current_faq = faq_data[index]

        # Build FAQ text
        header = "FAQ - Questions Fréquentes" if lang == 'fr' else "FAQ - Frequently Asked Questions"
        faq_text = f"{header}\n\n"
        faq_text += f"**{current_faq['category']}**\n\n"
        faq_text += f"**Q:** {current_faq['question']}\n\n"
        faq_text += f"{current_faq['answer']}"

        # Build navigation buttons
        nav_buttons = []
        if len(faq_data) > 1:
            nav_row = []

            # Previous button
            if index > 0:
                nav_row.append(InlineKeyboardButton("◀️ Précédent" if lang == 'fr' else "◀️ Previous", callback_data=f'faq_{index-1}'))

            # Page indicator
            nav_row.append(InlineKeyboardButton(f"[{index+1}/{len(faq_data)}]", callback_data='noop'))

            # Next button
            if index < len(faq_data) - 1:
                nav_row.append(InlineKeyboardButton("Suivant ▶️" if lang == 'fr' else "Next ▶️", callback_data=f'faq_{index+1}'))

            nav_buttons.append(nav_row)

        # Build keyboard with navigation + action buttons
        keyboard = nav_buttons + [
            [
                InlineKeyboardButton("Mes tickets" if lang == 'fr' else "My Tickets", callback_data='my_tickets')
            ],
            [
                InlineKeyboardButton("Créer un ticket" if lang == 'fr' else "Create ticket", callback_data='create_ticket')
            ],
            [
                back_to_main_button(lang)
            ]
        ]

        await query.edit_message_text(faq_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def create_ticket_prompt(self, bot, query, lang):
        """Create ticket prompt"""
        user_id = query.from_user.id
        bot.reset_conflicting_states(user_id, keep={'creating_ticket'})
        bot.state_manager.update_state(user_id, creating_ticket=True, step='subject')

        await query.edit_message_text(
            "📝 Entrez le sujet de votre ticket:" if lang == 'fr' else "📝 Enter your ticket subject:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='back_main')
            ]]))

    async def my_tickets(self, query, lang):
        """Show user's tickets"""
        user_id = query.from_user.id
        tickets = self.support_service.list_user_tickets(user_id)

        if not tickets:
            await query.edit_message_text(
                " Aucun ticket trouvé." if lang == 'fr' else " No tickets found.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(" Créer un ticket" if lang == 'fr' else " Create ticket", callback_data='create_ticket'),
                    back_to_main_button(lang)
                ]])
            )
            return

        text = " Vos tickets:" if lang == 'fr' else " Your tickets:"
        keyboard = []
        for ticket in tickets[:5]:
            text += f"\n• {ticket['ticket_id']} - {ticket['status']}"
            keyboard.append([InlineKeyboardButton(f"👁️ {ticket['ticket_id']}", callback_data=f"view_ticket_{ticket['ticket_id']}")])

        keyboard.append([back_to_main_button(lang)])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def process_ticket_creation(self, bot, update, message_text: str):
        """Process ticket creation based on current step"""
        user_id = update.effective_user.id
        user_state = bot.state_manager.get_state(user_id)
        step = user_state.get('step', 'subject')
        lang = user_state.get('lang', 'fr')

        if step == 'subject':
            if len(message_text.strip()) < 3:
                # Preserve state on error
                bot.state_manager.update_state(user_id, creating_ticket=True, step='subject', lang=lang)
                await update.message.reply_text("❌ Le sujet doit contenir au moins 3 caractères.")
                return

            # Store subject and move to content step
            user_state['ticket_subject'] = message_text.strip()[:100]
            user_state['step'] = 'content'
            bot.state_manager.update_state(user_id, **user_state)

            await update.message.reply_text(
                f"✅ **Sujet :** {bot.escape_markdown(message_text.strip())}\n\n📝 Maintenant, décrivez votre problème en détail :",
                parse_mode='Markdown'
            )

        elif step == 'content':
            if len(message_text.strip()) < 10:
                # Preserve state on error - keep ticket_subject too
                subject = user_state.get('ticket_subject', '')
                bot.state_manager.update_state(user_id, creating_ticket=True, step='content', lang=lang, ticket_subject=subject)
                await update.message.reply_text("Le message doit contenir au moins 10 caractères." if lang == 'fr' else "Message must contain at least 10 characters.")
                return

            # Store content and move to email step
            user_state['ticket_content'] = message_text.strip()[:2000]
            user_state['step'] = 'email'
            bot.state_manager.update_state(user_id, **user_state)

            await update.message.reply_text(
                "Veuillez entrer votre adresse email pour recevoir une réponse :" if lang == 'fr' else "Please enter your email address to receive a response:",
                parse_mode='Markdown'
            )

        elif step == 'email':
            # Validate email format
            email = message_text.strip()
            if '@' not in email or '.' not in email.split('@')[-1]:
                # Preserve state on error - keep subject and content
                subject = user_state.get('ticket_subject', '')
                content = user_state.get('ticket_content', '')
                bot.state_manager.update_state(user_id, creating_ticket=True, step='email', lang=lang, ticket_subject=subject, ticket_content=content)
                await update.message.reply_text("Adresse email invalide. Veuillez réessayer." if lang == 'fr' else "Invalid email address. Please try again.")
                return

            subject = user_state.get('ticket_subject', 'Support Request')
            content = user_state.get('ticket_content', '')

            # Create ticket using support service with email
            ticket_id = self.support_service.create_ticket(user_id, subject, content, client_email=email)

            if ticket_id:
                keyboard = [[InlineKeyboardButton("🏠 Menu principal" if lang == 'fr' else "🏠 Main menu", callback_data='back_main')]]
                await update.message.reply_text(
                    f"Ticket créé avec succès !\n\nID : {ticket_id}\n\nNotre équipe vous répondra à l'adresse : {email}" if lang == 'fr'
                    else f"Ticket created successfully!\n\nID: {ticket_id}\n\nOur team will respond to: {email}",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("Erreur lors de la création du ticket. Veuillez réessayer." if lang == 'fr' else "Error creating ticket. Please try again.")

            # Reset state
            bot.reset_user_state(user_id)

    async def process_problem_report(self, bot, update, message_text: str):
        """
        Process problem report for an order
        Creates a support ticket with order details automatically
        """
        user_id = update.effective_user.id
        user_state = bot.state_manager.get_state(user_id)
        order_id = user_state.get('problem_order_id')
        product_title = user_state.get('problem_product_title', 'Produit')
        lang = user_state.get('lang', 'fr')

        # Validate description length
        if len(message_text.strip()) < 10:
            await update.message.reply_text(
                "❌ La description doit contenir au moins 10 caractères." if lang == 'fr'
                else "❌ Description must contain at least 10 characters."
            )
            return

        # Get user email from database
        user_data = self.user_repo.get_user(user_id)
        user_email = user_data.get('email') if user_data else None

        if not user_email:
            # Fallback email if user doesn't have one
            user_email = f"user{user_id}@telegram.temp"

        # Create support ticket
        try:
            from app.core.utils import generate_ticket_id
            ticket_id = generate_ticket_id()

            # Format ticket content with order details
            ticket_subject = f"Problème avec commande {order_id}"
            ticket_content = f"""**Commande:** {order_id}
**Produit:** {product_title}

**Description du problème:**
{message_text.strip()}

---
Signalé sous 24H après achat.
"""

            # Create ticket via support_service
            success = self.support_service.create_ticket(
                ticket_id=ticket_id,
                user_id=user_id,
                subject=ticket_subject,
                message=ticket_content,
                user_email=user_email
            )

            if success:
                keyboard = [[InlineKeyboardButton(
                    "🏠 Menu principal" if lang == 'fr' else "🏠 Main menu",
                    callback_data='back_main'
                )]]

                await update.message.reply_text(
                    f"""✅ **PROBLÈME SIGNALÉ**

🎫 **Ticket créé:** `{ticket_id}`
📦 **Commande:** `{order_id}`

Notre équipe va examiner votre signalement et vous contactera rapidement.

Vous recevrez une réponse à : {user_email}""" if lang == 'fr' else
                    f"""✅ **PROBLEM REPORTED**

🎫 **Ticket created:** `{ticket_id}`
📦 **Order:** `{order_id}`

Our team will review your report and contact you shortly.

You will receive a response at: {user_email}""",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ Erreur lors de la création du ticket. Veuillez réessayer." if lang == 'fr'
                    else "❌ Error creating ticket. Please try again."
                )

        except Exception as e:
            import logging
            logging.error(f"Error creating problem report ticket: {e}")
            await update.message.reply_text(
                "❌ Erreur lors de la création du ticket." if lang == 'fr'
                else "❌ Error creating ticket."
            )

        # Reset state
        bot.reset_user_state(user_id)

    async def admin_reply_ticket_prompt(self, query, ticket_id: str):
        """Admin reply to ticket prompt"""
        if core_settings.ADMIN_USER_ID is None or query.from_user.id != core_settings.ADMIN_USER_ID:
            await query.edit_message_text("❌ Accès non autorisé.")
            return

        user_id = query.from_user.id
        # Using the admin_reply_prepare method that already exists
        await self.admin_reply_prepare(None, query, ticket_id)