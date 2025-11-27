#!/usr/bin/env python3
"""
Script pour corriger la FAQ dans support_handlers.py
- Réorganise par pertinence
- Corrige l'incohérence stockage
- Nuance les frais/commissions
- Retire mentions techniques inutiles
"""

import re

# Lire le fichier
with open('/Users/noricra/Python-bot/app/integrations/telegram/handlers/support_handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Nouvelle FAQ FR réorganisée par pertinence
new_faq_fr = '''# FAQ Data Structure (French) - REORGANIZED BY RELEVANCE
FAQ_DATA_FR: List[Dict[str, str]] = [
    # BLOC 1: ACHETER (Le plus important)
    {
        "category": "ACHETER UN PRODUIT",
        "question": "Comment acheter un produit ? (Guide complet)",
        "answer": (
            "**Étape 1:** Menu \\"Acheter\\" > Parcourir catégories ou rechercher par ID\\n"
            "**Étape 2:** Cliquer sur le produit souhaité pour voir les détails\\n"
            "**Étape 3:** Cliquer \\"Acheter\\" puis choisir votre crypto (BTC, ETH, SOL, USDT, USDC)\\n"
            "**Étape 4:** Le bot affiche une adresse crypto + QR code\\n"
            "**Étape 5:** Ouvrir votre wallet crypto (Binance, Trust Wallet, Coinbase, etc.)\\n"
            "**Étape 6:** Envoyer le montant EXACT indiqué à l'adresse fournie\\n"
            "**Étape 7:** Attendre la confirmation blockchain (5-30 min selon la crypto)\\n"
            "**Étape 8:** Livraison automatique du fichier dans \\"Ma bibliothèque\\"\\n\\n"
            "IMPORTANT: N'envoyez JAMAIS un montant différent, cela pourrait bloquer le paiement."
        )
    },
    {
        "category": "ACHETER UN PRODUIT",
        "question": "Quelles cryptomonnaies sont acceptées ?",
        "answer": (
            "Le bot accepte **5 cryptomonnaies majeures** :\\n\\n"
            "**Bitcoin (BTC)** - La plus sécurisée et décentralisée\\n"
            "**Ethereum (ETH)** - Rapide et fiable\\n"
            "**Solana (SOL)** - Ultra rapide (1-5 min) et frais très bas\\n"
            "**USDT (Tether)** - Stablecoin indexé sur le dollar US\\n"
            "**USDC (USD Coin)** - Stablecoin réglementé et audité\\n\\n"
            "CONSEIL: Utilisez **USDT** ou **USDC** si vous voulez éviter la volatilité des prix.\\n"
            "Utilisez **Solana** pour des paiements quasi-instantanés."
        )
    },
    {
        "category": "ACHETER UN PRODUIT",
        "question": "Dois-je fournir mes données personnelles (KYC) ?",
        "answer": (
            "**NON, aucune vérification KYC requise.**\\n\\n"
            "Pas de nom, pas d'adresse, pas de carte d'identité, pas de selfie.\\n\\n"
            "Cette plateforme est axée sur la **confidentialité** et l'**anonymat**. "
            "Vous n'avez besoin que d'un compte Telegram et d'un wallet crypto pour acheter ou vendre."
        )
    },
    # BLOC 2: VENDRE (Important pour vendeurs)
    {
        "category": "VENDRE VOS PRODUITS",
        "question": "Comment devenir vendeur ?",
        "answer": (
            "**En 3 étapes simples** :\\n\\n"
            "**1.** Menu \\"Vendre\\" > \\"Créer un compte vendeur\\"\\n"
            "**2.** Configurez votre **adresse wallet Solana** (pour recevoir les paiements)\\n"
            "**3.** Uploadez votre premier produit (titre, description, fichier, prix)\\n\\n"
            "**Types de produits acceptés** :\\n"
            "- eBooks (PDF, EPUB)\\n"
            "- Formations vidéo (MP4, AVI)\\n"
            "- Fichiers audio (MP3, WAV)\\n"
            "- Archives (ZIP, RAR)\\n"
            "- Templates, Presets (PSD, AI, etc.)\\n"
            "- Scripts et plugins\\n\\n"
            "**Limite par fichier** : Jusqu'à 100 MB par fichier\\n"
            "**Stockage total** : 100 MB gratuits (contactez le support pour extension)"
        )
    },
    {
        "category": "VENDRE VOS PRODUITS",
        "question": "Quels sont les avantages vendeur ?",
        "answer": (
            "**Frais les plus bas du marché** - Seulement les frais techniques obligatoires (NowPayments, slippage, spread, frais blockchain)\\n"
            "**Aucun KYC requis** - Vendez en toute confidentialité\\n"
            "**Paiements crypto directs** - Recevez vos gains sur votre wallet Solana\\n"
            "**Portée internationale** - Vendez partout dans le monde sans restrictions\\n"
            "**Livraison automatique** - Vos clients reçoivent le produit instantanément après paiement\\n"
            "**Stockage sécurisé** - 100MB gratuits avec extension possible\\n"
            "**Support 24/7** - Système de tickets pour toute question\\n\\n"
            "Contrairement aux plateformes traditionnelles (Gumroad 9%, Shopify 2.9%+30¢), "
            "vous gardez le **contrôle total** de vos revenus avec les frais les plus compétitifs."
        )
    },
    {
        "category": "VENDRE VOS PRODUITS",
        "question": "Quand et comment suis-je payé en tant que vendeur ?",
        "answer": (
            "**Processus de paiement vendeur** :\\n\\n"
            "**1.** Un client achète votre produit\\n"
            "**2.** Paiement confirmé sur la blockchain\\n"
            "**3.** Vérification anti-fraude manuelle (sécurité)\\n"
            "**4.** Payout envoyé directement sur votre **wallet Solana**\\n\\n"
            "**Délai** : Généralement 24-48h après la vérification anti-fraude\\n"
            "**Frais** : Frais techniques minimaux (NowPayments, slippage, spread, frais blockchain) - Les plus bas du marché\\n"
            "**Monnaie** : Payout en USDT (stablecoin) sur le réseau Solana\\n\\n"
            "Vous pouvez suivre vos payouts dans \\"Payouts / Adresse\\" du dashboard vendeur."
        )
    },
    # BLOC 3: SUPPORT (Important pour résolution)
    {
        "category": "SUPPORT",
        "question": "Comment contacter le support ?",
        "answer": (
            "Support disponible **24/7** via le système de tickets :\\n\\n"
            "**1.** Menu \\"Support\\" > \\"Créer un ticket\\"\\n"
            "**2.** Saisissez le sujet de votre demande\\n"
            "**3.** Décrivez votre problème en détail\\n"
            "**4.** Fournissez votre email pour recevoir une réponse\\n"
            "**5.** Notre équipe répond sous 2-24h\\n\\n"
            "**Types de problèmes traités** :\\n"
            "- Paiement non reçu\\n"
            "- Fichier non livré\\n"
            "- Problème technique\\n"
            "- Question sur un payout vendeur\\n"
            "- Signalement de contenu frauduleux\\n"
            "- Autre demande"
        )
    },
    {
        "category": "SUPPORT",
        "question": "Puis-je signaler un problème avec un achat ?",
        "answer": (
            "Oui ! Vous disposez de **24 heures** après l'achat pour signaler un problème :\\n\\n"
            "**1.** Allez dans \\"Ma bibliothèque\\"\\n"
            "**2.** Cliquez sur le produit concerné\\n"
            "**3.** Utilisez le bouton \\"Signaler un problème\\"\\n"
            "**4.** Décrivez le problème (fichier corrompu, contenu manquant, etc.)\\n\\n"
            "**Problèmes couramment signalés** :\\n"
            "- Fichier corrompu ou illisible\\n"
            "- Contenu différent de la description\\n"
            "- Fichier vide ou incomplet\\n"
            "- Mauvaise qualité (vidéo, audio)\\n\\n"
            "Un ticket est automatiquement créé et notre équipe examine le cas rapidement."
        )
    },
    {
        "category": "SUPPORT",
        "question": "Que faire si je ne reçois pas mon fichier ?",
        "answer": (
            "Si vous ne recevez pas votre fichier après paiement confirmé :\\n\\n"
            "**1.** Vérifiez \\"Ma bibliothèque\\" - Le fichier y est peut-être déjà\\n"
            "**2.** Attendez 30 minutes - Certaines cryptos prennent du temps (BTC, ETH)\\n"
            "**3.** Vérifiez votre paiement sur blockchain - Utilisez un explorateur (blockchain.com pour BTC)\\n"
            "**4.** Contactez le support - Menu \\"Support\\" > \\"Créer un ticket\\"\\n\\n"
            "**Informations à fournir au support** :\\n"
            "- ID de la commande\\n"
            "- ID de transaction crypto (TxHash)\\n"
            "- Montant envoyé\\n\\n"
            "Le support répond généralement sous 2-24h."
        )
    },
    # BLOC 4: BIBLIOTHÈQUE
    {
        "category": "BIBLIOTHÈQUE",
        "question": "Comment accéder à mes achats ?",
        "answer": (
            "Tous vos produits achetés sont stockés dans **\\"Ma bibliothèque\\"** :\\n\\n"
            "**1.** Menu principal > \\"Ma bibliothèque\\"\\n"
            "**2.** Parcourez la liste de vos produits achetés\\n"
            "**3.** Cliquez sur un produit pour le télécharger à nouveau\\n\\n"
            "**Téléchargements illimités** - Vous pouvez re-télécharger autant de fois que vous voulez\\n"
            "**Accès permanent** - Vos produits restent disponibles indéfiniment\\n"
            "**Aucune expiration** - Pas de limite de temps\\n\\n"
            "CONSEIL: Sauvegardez vos fichiers importants dans votre cloud personnel (Google Drive, Dropbox...)"
        )
    },
    {
        "category": "BIBLIOTHÈQUE",
        "question": "Puis-je contacter le vendeur après un achat ?",
        "answer": (
            "Oui ! Vous pouvez contacter le vendeur directement depuis votre bibliothèque :\\n\\n"
            "**1.** Allez dans \\"Ma bibliothèque\\"\\n"
            "**2.** Cliquez sur le produit acheté\\n"
            "**3.** Utilisez le bouton \\"Contacter le vendeur\\"\\n\\n"
            "Un système de **messagerie interne** s'ouvre pour discuter avec le vendeur.\\n"
            "Utile pour poser des questions, signaler un problème, ou demander une mise à jour."
        )
    },
    # BLOC 5: SÉCURITÉ
    {
        "category": "SÉCURITÉ",
        "question": "La plateforme est-elle sécurisée ?",
        "answer": (
            "**Oui, voici nos garanties de sécurité** :\\n\\n"
            "**Paiements crypto** via NOWPayments (certifié PCI DSS, leader mondial)\\n"
            "**Stockage cloud sécurisé** - Fichiers accessibles 24/7\\n"
            "**Telegram chiffré** - Toutes les communications passent par Telegram (end-to-end encryption)\\n"
            "**Anti-fraude** - Vérification manuelle des transactions avant payout vendeur\\n"
            "**Pas de collecte de données** - Aucune information personnelle stockée (pas de KYC)\\n"
            "**Livraison automatique** - Fichiers livrés instantanément après confirmation blockchain\\n\\n"
            "Les paiements crypto sont irréversibles, ce qui protège les vendeurs contre les chargebacks frauduleux."
        )
    },
    # BLOC 6: DÉTAILS TECHNIQUES (Moins prioritaire)
    {
        "category": "DÉTAILS TECHNIQUES",
        "question": "Combien de temps prend un paiement crypto ?",
        "answer": (
            "**Temps de confirmation par crypto** :\\n\\n"
            "**Bitcoin (BTC)** : 10-60 minutes (nécessite 6 confirmations blockchain)\\n"
            "**Ethereum (ETH)** : 5-15 minutes (nécessite 12 confirmations)\\n"
            "**Solana (SOL)** : 1-5 minutes (le plus rapide)\\n"
            "**USDT/USDC** : 5-15 minutes (selon le réseau utilisé)\\n\\n"
            "Si votre paiement prend plus de 2 heures, contactez le support avec votre **ID de transaction**."
        )
    },
    {
        "category": "DÉTAILS TECHNIQUES",
        "question": "Comment obtenir un wallet Solana pour recevoir mes payouts ?",
        "answer": (
            "Pour recevoir vos payouts vendeur, vous avez besoin d'un **wallet Solana** :\\n\\n"
            "**Option 1: Phantom Wallet** (recommandé)\\n"
            "- Télécharger l'extension Chrome ou l'app mobile\\n"
            "- Créer un nouveau wallet\\n"
            "- Copier votre adresse Solana (~44 caractères)\\n\\n"
            "**Option 2: Binance**\\n"
            "- Créer un compte Binance\\n"
            "- Aller dans \\"Wallet\\" > \\"Dépôt\\"\\n"
            "- Chercher \\"SOL\\" (Solana)\\n"
            "- Copier l'adresse de dépôt\\n\\n"
            "**Option 3: Coinbase**\\n"
            "- Créer un compte Coinbase\\n"
            "- Aller dans \\"Receive\\"\\n"
            "- Sélectionner \\"Solana (SOL)\\"\\n"
            "- Copier l'adresse\\n\\n"
            "Configurez cette adresse dans votre dashboard vendeur (\\"Payouts / Adresse\\")."
        )
    },
    {
        "category": "DÉTAILS TECHNIQUES",
        "question": "Puis-je payer par carte bancaire ?",
        "answer": (
            "**Non, uniquement paiements crypto**.\\n\\n"
            "**Pourquoi crypto uniquement ?**\\n"
            "- **Anonymat** - Pas de KYC, pas de collecte de données\\n"
            "- **International** - Fonctionne dans tous les pays\\n"
            "- **Rapide** - Confirmation en quelques minutes\\n"
            "- **Frais les plus bas** - Frais techniques minimaux vs Stripe/PayPal (3-5%)\\n"
            "- **Pas de chargeback** - Protection contre la fraude vendeur\\n\\n"
            "**Vous n'avez jamais utilisé la crypto ?**\\n"
            "**1.** Créez un compte sur **Binance** ou **Coinbase**\\n"
            "**2.** Achetez de la crypto avec votre carte (USDT recommandé)\\n"
            "**3.** Envoyez-la à l'adresse fournie par le bot\\n\\n"
            "C'est aussi simple qu'un virement bancaire !"
        )
    },
    {
        "category": "DÉTAILS TECHNIQUES",
        "question": "Quelles sont les commandes slash disponibles ?",
        "answer": (
            "Le bot supporte plusieurs **commandes rapides** :\\n\\n"
            "**/start** - Ouvrir le menu principal\\n"
            "**/achat** - Accès direct au menu d'achat\\n"
            "**/vendre** - Accès direct au menu vendeur\\n"
            "**/library** - Accès direct à votre bibliothèque\\n"
            "**/stats** - Dashboard vendeur (si vous êtes vendeur)\\n"
            "**/support** - Créer un ticket de support rapidement\\n\\n"
            "Ces commandes vous permettent d'accéder rapidement aux fonctionnalités "
            "sans passer par le menu principal."
        )
    }
]'''

# Trouver et remplacer la FAQ FR
pattern_fr = r'# FAQ Data Structure \(French\).*?(?=# FAQ Data Structure \(English\)|^class SupportHandlers:)'
content = re.sub(pattern_fr, new_faq_fr + '\n\n', content, flags=re.DOTALL | re.MULTILINE)

# Écrire le fichier
with open('/Users/noricra/Python-bot/app/integrations/telegram/handlers/support_handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ FAQ FR corrigée avec succès!")
print("- Réorganisée par pertinence (Acheter, Vendre, Support, Bibliothèque, Sécurité, Technique)")
print("- Stockage corrigé: 100MB par fichier ET 100MB total")
print("- Frais nuancés: mentions des frais techniques minimaux")
print("- Mentions techniques inutiles retirées")
