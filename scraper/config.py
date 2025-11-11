"""
Configuration pour le scraper TikTok
"""

# Mots-clés pour rechercher des créateurs (international)
SEARCH_KEYWORDS = [
    # 🎓 VENDEURS DE FORMATIONS (priorité absolue)
    "dropshipping course",
    "shopify course", 
    "ecommerce course",
    "masterclass",
    "paid course",
    "course creator",
    
    # 💼 MENTORS/COACHS BUSINESS  
    "business mentor",
    "ecommerce mentor",
    "dropshipping expert",
    "shopify expert",
    
    # 📚 CRÉATEURS PRODUITS DIGITAUX
    "digital products",
    "ebook creator", 
    "template creator",
    "digital creator",
    
    # 💰 CRÉATEURS MONÉTISÉS
    "indie hacker",
    "crypto creator", 
    "nft creator",
    "web3 builder",
    
    # 🇫🇷 FRANÇAIS
    "formation dropshipping",
    "cours shopify",
    "formation en ligne",
    "vendre formation"
]

# Nombre de profils à scraper par mot-clé
PROFILES_PER_KEYWORD = 3

# Délai entre chaque requête (en secondes) pour éviter le ban
DELAY_BETWEEN_REQUESTS = 3

# Minimum de followers pour filtrer les profils
MIN_FOLLOWERS = 50000

# Types de liens bio à parser
BIO_LINK_PLATFORMS = [
    "linktree",
    "linktr.ee",
    "beacons.ai",
    "bio.link",
    "stan.store",
    "hoo.be",
    "solo.to",
    "link.bio",
    "allmylinks",
    "tap.bio",
    "creator.link",
    "lnk.bio"
]

# User agent pour éviter la détection
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Timeout pour les requêtes (en secondes)
TIMEOUT = 30

# Fichier de sortie
OUTPUT_FILE = "output/leads.csv"
