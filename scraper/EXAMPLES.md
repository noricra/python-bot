# 📚 Exemples d'utilisation du scraper

## 🎯 Cas d'usage par niche

### 1. Créateurs crypto/web3

**Modifier `config.py` :**
```python
SEARCH_KEYWORDS = [
    "crypto trader",
    "nft creator",
    "web3 builder",
    "defi educator",
    "crypto signals",
    "trading course",
    "blockchain developer"
]
```

### 2. Créateurs de cours/ebooks

**Modifier `config.py` :**
```python
SEARCH_KEYWORDS = [
    "online course creator",
    "ebook author",
    "digital course",
    "udemy instructor",
    "skillshare teacher",
    "educational content"
]
```

### 3. Développeurs/Tech

**Modifier `config.py` :**
```python
SEARCH_KEYWORDS = [
    "indie developer",
    "open source",
    "python developer",
    "javascript tutorial",
    "coding bootcamp",
    "tech educator"
]
```

### 4. Designers

**Modifier `config.py` :**
```python
SEARCH_KEYWORDS = [
    "ui designer",
    "figma templates",
    "canva creator",
    "notion templates",
    "design resources",
    "graphic designer"
]
```

### 5. Freelancers/Solopreneurs

**Modifier `config.py` :**
```python
SEARCH_KEYWORDS = [
    "freelancer",
    "solopreneur",
    "digital nomad",
    "remote worker",
    "side hustle",
    "passive income"
]
```

## 🔧 Personnalisation avancée

### Scraper uniquement des gros comptes

```python
MIN_FOLLOWERS = 10000  # Seulement 10K+ followers
```

### Scraper plus de profils

```python
PROFILES_PER_KEYWORD = 50  # 50 profils par mot-clé
```

### Mode ultra-safe (éviter les bans)

```python
DELAY_BETWEEN_REQUESTS = 10  # 10 secondes entre chaque requête
PROFILES_PER_KEYWORD = 10   # Seulement 10 profils par mot-clé
```

### Mode rapide (risqué)

```python
DELAY_BETWEEN_REQUESTS = 1   # 1 seconde seulement
PROFILES_PER_KEYWORD = 100   # 100 profils (risque de ban!)
```

## 📊 Exemples de résultats attendus

### Scraping 5 mots-clés × 20 profils = 100 profils

**Résultats typiques :**
- Total scraped: 100 profils
- Avec email: 30-40 profils (30-40%)
- Avec linktree: 60-70 profils
- Sans rien: 10-20 profils

**Fichier CSV exemple :**
```csv
source,username,profile_url,bio,email,bio_links,followers
TikTok,johndoe,https://tiktok.com/@johndoe,Digital creator | Courses,john@example.com,https://linktr.ee/johndoe,15000
Twitter,janecreator,https://twitter.com/janecreator,Building in public,,https://beacons.ai/janecreator,8500
```

## 🚀 Workflows recommandés

### Workflow 1 : Premier test (30 min)

```bash
# 1. Modifie config.py avec 3-5 mots-clés
# 2. Limite à 10 profils par mot-clé
PROFILES_PER_KEYWORD = 10

# 3. Lance le scraper (TikTok seulement)
python main.py --platform tiktok

# 4. Analyse les résultats
# 5. Ajuste les mots-clés si nécessaire
```

### Workflow 2 : Production (quotidien)

```bash
# Matin : TikTok
python main.py --platform tiktok

# Après-midi : Twitter
python main.py --platform twitter

# Fusion manuelle des CSV si besoin
```

### Workflow 3 : Full automation

```bash
# Lance les deux en une fois
python main.py

# Résultat : output/all_leads.csv avec tout combiné
```

## 💡 Astuces

### Trouver des mots-clés pertinents

1. Va sur TikTok/Twitter
2. Cherche manuellement "digital products"
3. Regarde les hashtags utilisés
4. Ajoute ces hashtags dans `SEARCH_KEYWORDS`

### Filtrer les faux emails

Certains profils ont des emails génériques (ex: `contact@platform.com`). Le parser les filtre automatiquement.

### Combiner avec d'autres sources

Tu peux aussi scraper :
- Instagram (ajouter un scraper similaire)
- LinkedIn (plus complexe, requiert login)
- Reddit (chercher dans r/entrepreneur, r/SideProject)

### Export vers Google Sheets

```python
# Après le scraping
import pandas as pd
import gspread

df = pd.read_csv('output/all_leads.csv')
# Upload vers Google Sheets (configure gspread d'abord)
```

## ⚠️ Erreurs communes

### Erreur : "No profiles found"

**Causes :**
- Mauvais mots-clés (trop spécifiques)
- TikTok/Twitter a changé sa structure HTML
- Rate limit atteint (ban temporaire)

**Solutions :**
- Teste avec des mots-clés plus génériques
- Attends 1-2h avant de recommencer
- Utilise `--no-headless` pour voir ce qui se passe

### Erreur : "Timeout"

**Cause :** Connexion lente ou page trop longue à charger

**Solution :**
```python
# Augmente le timeout dans config.py
TIMEOUT = 60  # 60 secondes au lieu de 30
```

### Email non trouvés sur linktree

**Cause :** Linktree ne contient pas toujours d'email (souvent juste des liens vers produits)

**Solution :** C'est normal, beaucoup de créateurs n'exposent pas leur email publiquement.

---

**Bon scraping ! 🚀**
