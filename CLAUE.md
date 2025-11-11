# Instructions de nettoyage et de migration du projet

## Contexte
Ce projet nécessite un nettoyage complet et une migration de SQLite vers PostgreSQL. L'objectif est d'éliminer tout le code inutile, les doublons, et de restructurer la base de données avant le prochain déploiement.

## Règles critiques
- **MIGRATION POSTGRESQL** : Modifier uniquement l'initialisation pour que le prochain déploiement utilise exclusivement PostgreSQL (pas de migration de données existantes)
- Utiliser une database sur Railway (externe, pas locale)
- Tous les fichiers référençant SQLite doivent être modifiés pour PostgreSQL

---

## 1) APP/

### \_\_init\_\_.py
- Ce fichier est vide

### CORE/

#### analytics_engine.py
- Fichier non utilisé (553 lignes) - À SUPPRIMER

#### chart_generator.py
- Est du même registre que analytics_engine.py - À SUPPRIMER

#### email_service.py
- Supprimer recovery code (il n'y a plus de code)
- Dans "durée de suspension" : on ne sait pas car cela n'existe pas dans la DB et l'admin n'a pas de bouton
- Il manque le mail de confirmation de vente et le mail de confirmation de paiement reçu sur l'adresse du vendeur
- Ajouter mail produit ajouté / mail produit supprimé

#### errors_message.py
- Il y a des doublons car tous les messages d'erreurs ne sont pas dans ce fichier, il y en a partout
- Il ne devrait pas exister de référence au wallet car il n'y a pas de wallet intégré
- Il y a d'autres erreurs qui ne sont plus à jour

#### fils_utils.py
- Voir plus tard (nous allons utiliser un object Storage donc il faudra m'expliquer comment configurer puis modifier ce fichier)

#### image_utils.py
- Voir si pas de doublons ou code mort

#### pdf_utils
- Supprimer si non utilisé

#### sellers_notification
- Il y a un problème, ce n'est pas fonctionnel
- Il y a du keyboard faisant référence à son wallet
- L'idée est bonne mais pas implémentée (quelques autres incohérences, il est écrit "stock faible" or ce sont des produits numériques)

#### settings.py
- Doit être complètement revu surtout pour les doublons (le texte n'est jamais utilisé)

#### utils.py
- Tous les fichiers en SQLite devront pointer vers du PostgreSQL

### DOMAIN/REPOSITORIES/

#### \_\_init\_\_.py
- Je ne comprends pas pourquoi il y a plusieurs fichiers init, est-ce des doublons ?

#### TOUS LES FICHIERS DE CE DOSSIER
- À modifier en fonction de la nouvelle DB

### INTEGRATION/

#### Telegrams/Handler/

##### admin_handlers.py
- "Recherche user" et "Voir users" doivent être mergés
- De même pour les payout, il manque des détails (adresse, montants)

##### analytics_handlers.py
- Quel est ce fichier d'analytics ? On en avait déjà 2

##### buy_handlers.py
- Je vois V2, il faut supprimer toutes les V1 (s'il y en a) afin d'éviter les doublons

##### library_handlers
- "Contacter vendeur" redirige vers le chat privé du vendeur, donc il faut supprimer le message_seller

##### support_handlers
- Il faut complètement revoir, il n'est pas à jour par rapport à tout le bot

##### sell_handlers
- Il faudrait que seller-setting soit plus large
- Dans "succès message" il y a le "name" mais est-ce que ça prend le name par défaut du Telegram comme on le demande plus ? Vérifier ce point
- Supprimer la section seller_message

#### Telegrams/

##### app_builders.py
- Il faut ajouter des / et qu'ils soient tous implémentés
- Quelques idées : /achat /vendre /stats (si on est pas connecté ça dit "il faut devenir vendeur") /library, etc.
- Un / pour beaucoup de choses

##### callback_routers
- Vérifier que ce ne soit pas du code dupliqué

##### keyboards.py
- De même

#### IPN/

##### ipn_server.py
- OK on a confirmation, mais on doit pouvoir appuyer sur "télécharger" directement ou être redirigé vers la bibliothèque une fois le paiement confirmé
- De plus la détection n'est pas automatique, nous sommes obligés de refresh la page
- De plus quand on refresh la page les infos de paiement disparaissent, ce n'est pas pratique, elles doivent rester

##### nowpayments_client.py
- Voir comment configurer la nouvelle API

### SERVICES/

#### password_recovery_service.py
- Supprimer car plus de recovery

#### payment_service.py
- Il y a du code mort (fonction des _get_network_info)
- Aussi du doublon de texte avec nowpayment_client.py

#### product_service.py
- On va mettre tous les prix en USDT
- Mettre le prix en euros entre parenthèse au moment de payment info (beaucoup plus simple)

#### smtp_service.py
- Il y a beaucoup de code mort et de duplication avec email_service

---

## 2) DATABASE

Il faut faire les modifications dans database_init :

### 1) À quoi sert id_counters ?

### 2) Table ORDERS :
- La clé primaire est order_id pas id qui ne devrait pas être là
- 2.1) Il y a un doublon entre payment_currency et crypto_currency (à supprimer)
- 2.2) crypto_amount n'est jamais utilisé
- 2.3) payment_address n'est jamais utilisé (nous allons utiliser une nouvelle API pour NowPayments, l'actuelle prend les monnaies et envoie vers mon wallet, on va utiliser une qui prend les monnaies, envoie la commission vers mon wallet et le reste vers le wallet du vendeur)
- 2.4) La colonne created_at est en timestamp (ex: 1761602307) et completed_at est en heure classique, c'est incohérent

### 3) Table PRODUCTS :
- La clé primaire est product_id donc supprimer id
- 3.1) Le taux en USDT ne doit pas être conservé dans la Database car il varie donc l'information est fausse
- 3.2) Nous allons utiliser un object-storage donc il faut modifier le main_file_path car ce n'est plus un projet local, de même pour cover_image_path et thumbnail_path

### 4) Table REVIEWS :
- La clé primaire est le product_id donc supprimer id
- 4.1) "comment" est un doublon de review_text, corriger
- 4.2) order_id n'est jamais utilisé

### 5) Table SELLER_PAYOUT :
- À adapter en fonction de la nouvelle API

### 6) Table SQLITE_SEQUENCE :
- Il est écrit colonne seq 1547 pour catégorie, c'est complètement faux

### 7) Table SUPPORT_MESSAGE :
- Non utilisée et non utile. Si le client veut contacter le vendeur il est dirigé vers le chat privé du vendeur et s'il laisse un message au support il doit laisser son mail pour être recontacté - À SUPPRIMER

### 8) Table SUPPORT_TICKET :
- Supprimer

### 9) Table TELEGRAM_MAPPING :
- À supprimer

### 10) Table USER :
- Supprimer les colonnes recovery_code_cash et recovery_code_expiry (il n'y a plus de mot de passe)

### 11) Table WALLET_TRANSACTION :
- À supprimer

### 12) INFO GÉNÉRALE :
- IL FAUT MIGRER VERS POSTGRESQL

---

## 3) INFORMATIONS GÉNÉRALES

Voici quelques points à améliorer :

- Il faut migrer vers PostgreSQL
- Problème de compteur vente qui reste bloqué à 0
- Je ne reçois pas le mail lorsque le paiement est confirmé (vendeur)
- Il faut un bouton qui permette de voir la boutique complète d'un vendeur (à implémenter dans un carousel full et avec le app builder /shop + nom du vendeur)
- Chaque vendeur a droit à 100MB au total, donc il faut que ce soit affiché dans le dashboard avec les revenus totaux, nombre de produits (donc implémenter un compteur dégressif ainsi qu'une limite de stockage)
- La partie analytics n'est pas optimale, trouver une nouvelle bibliothèque ou m'inquiéter une API à implémenter
- L'ID produit doit être visible dans le mode full du carousel
- Dans le bouton qui permet de voir la boutique totale d'un vendeur, il faut qu'on puisse lire sa bio
- Il ne faut pas qu'un vendeur puisse réactiver un produit désactivé par l'admin
- Vérifier que le système de suspension fonctionne correctement