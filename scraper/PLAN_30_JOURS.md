# 🚀 PLAN DE LANCEMENT 30 JOURS

**Objectif :** Scraper 10,000+ profils et générer tes premiers clients vendeurs

**Budget Total :** 150-300€
**Temps requis :** 2-3h/jour
**ROI attendu :** 5-10 vendeurs acquis

---

# 📅 SEMAINE 1 : SETUP & VALIDATION (Jours 1-7)

## 🎯 Objectif : Système qui fonctionne + 100 premiers emails

### **Jour 1 : Infrastructure de base**

#### Matin (2h)
```bash
✅ Installer dependencies
cd scraper
pip3 install -r requirements.txt
python3 -m playwright install chromium

✅ Installer playwright-stealth
pip3 install playwright-stealth

✅ Tester le système
python3 test_all.py  # Tous les tests doivent passer
```

#### Après-midi (2h)
```bash
✅ Créer compte Smartproxy (ou autre)
- Plan: Résidentiel 2GB trial (gratuit ou 20€)
- Config: USA + rotation 10 min

✅ Configurer les proxies dans config.py
PROXY_ENABLED = True
PROXY_CONFIG = {
    'server': 'gate.smartproxy.com:7000',
    'username': 'user-YOURUSER-sessionduration-10',
    'password': 'YOURPASS',
}

✅ Tester avec 5 profils
python3 main.py --platform tiktok --no-headless
```

**Livrables Jour 1 :**
- [ ] Système fonctionnel
- [ ] Proxies configurés
- [ ] 5 profils scrapés en test

---

### **Jour 2 : Premier scraping réel**

#### Matin (1h)
```bash
✅ Personnaliser les mots-clés dans config.py
SEARCH_KEYWORDS = [
    "digital products creator",
    "ebook author",
    "online course creator",
    "notion templates",
    "figma templates",
]

PROFILES_PER_KEYWORD = 5  # Commence petit
```

#### Après-midi (2h)
```bash
✅ Lancer scraper TikTok
python3 main.py --platform tiktok

Résultat attendu: 25 profils (5 keywords × 5 profils)

✅ Analyser les résultats
cat output/tiktok_leads.csv
- Combien ont des emails ?
- Qualité des profils ?
```

**Livrables Jour 2 :**
- [ ] 25 profils TikTok scrapés
- [ ] 5-10 emails récupérés
- [ ] Analyse de qualité

---

### **Jour 3 : Optimisation + Twitter**

#### Matin (2h)
```bash
✅ Ajuster les mots-clés selon résultats Jour 2
- Garde les mots-clés qui donnent des emails
- Supprime les mauvais

✅ Augmenter le volume
PROFILES_PER_KEYWORD = 10

✅ Scraper Twitter
python3 main.py --platform twitter
```

#### Après-midi (1h)
```bash
✅ Fusionner les résultats
python3 main.py --platform both

✅ Nettoyer les données
- Supprimer doublons
- Vérifier validité emails
```

**Livrables Jour 3 :**
- [ ] 50 profils TikTok
- [ ] 50 profils Twitter
- [ ] 20-30 emails total

---

### **Jour 4 : Scale progressif**

```bash
✅ Augmenter le volume
PROFILES_PER_KEYWORD = 15
MIN_FOLLOWERS = 1000  # Filtrer les petits comptes

✅ Lancer scraping complet
python3 main.py

Objectif: 150 profils (10 keywords × 15 profils)

✅ Sauvegarder les résultats
cp output/all_leads.csv backup/leads_jour4.csv
```

**Livrables Jour 4 :**
- [ ] 150 profils total
- [ ] 40-60 emails
- [ ] Backup sauvegardé

---

### **Jour 5 : Cold Email Setup**

#### Ne PAS scraper aujourd'hui (pause pour éviter ban)

#### Matin (2h)
```bash
✅ Créer domaine dédié cold email
- Acheter: tonfirstname-marketplace.com (10€/an sur Namecheap)
- OU utiliser Gmail perso (gratuit mais moins pro)

✅ Configurer SPF/DKIM/DMARC
(Voir guide COLD_EMAIL.md)

✅ Créer templates emails
```

#### Après-midi (2h)
```bash
✅ Warm-up email (si domaine dédié)
- Envoyer 5 emails à tes potes
- Demander réponses

✅ Tester template sur 5 leads
- Envoyer manuellement
- Analyser les réponses
```

**Livrables Jour 5 :**
- [ ] Domaine email configuré
- [ ] Template email validé
- [ ] 5 premiers emails envoyés

---

### **Jour 6-7 : Scraping intensif**

```bash
✅ Weekend = Temps libre = Scrape max

PROFILES_PER_KEYWORD = 20
SEARCH_KEYWORDS = [15 keywords au total]

✅ Samedi: TikTok (300 profils)
✅ Dimanche: Twitter (300 profils)

Total Semaine 1: 600-800 profils = 180-240 emails
```

**Livrables Semaine 1 :**
- [ ] 600-800 profils scrapés
- [ ] 180-240 emails récupérés
- [ ] Système rodé
- [ ] Premiers emails envoyés

---

# 📅 SEMAINE 2 : SCALING + OUTREACH (Jours 8-14)

## 🎯 Objectif : 2,000 profils + 50 emails/jour

### **Jour 8 : Automatisation cold email**

#### Matin (2h)
```bash
✅ Créer script email sender
(Voir COLD_EMAIL.md pour le code)

✅ Configurer:
- Rate limit: 20 emails/jour (safe)
- Template personnalisé
- Tracking ouvertures (optionnel)
```

#### Après-midi (1h)
```bash
✅ Tester sur 20 leads
python3 email_sender.py --test --limit 20

✅ Analyser:
- Emails bounced?
- Taux d'ouverture
- Réponses
```

---

### **Jour 9-10 : Scraping + Emailing quotidien**

**Routine quotidienne :**
```
Matin (1h):
- Scraper 100-150 profils
- Vérifier pas de ban/CAPTCHA

Après-midi (30min):
- Envoyer 30 cold emails
- Répondre aux leads intéressés

Soir (15min):
- Backup des données
- Check stats
```

---

### **Jour 11 : Optimisation proxies**

```bash
✅ Si ban détecté → Changer de proxy
✅ Si CAPTCHA → Pause 24h
✅ Analyser taux d'emails trouvés:
   - Si < 20% → Changer mots-clés
   - Si > 40% → Continuer
```

---

### **Jour 12-14 : Scale agressif**

```bash
✅ Augmenter volume scraping
PROFILES_PER_KEYWORD = 30

✅ Objectif: 500 profils/jour
✅ Emails: 50/jour

Total Semaine 2: 2,500 profils = 750 emails
```

**Livrables Semaine 2 :**
- [ ] 2,500 profils scrapés
- [ ] 750 emails total
- [ ] 350 cold emails envoyés
- [ ] 5-15 réponses positives

---

# 📅 SEMAINE 3 : CONVERSION (Jours 15-21)

## 🎯 Objectif : Convertir leads en vendeurs

### **Focus : Pas de nouveau scraping, concentre-toi sur conversion**

#### Jour 15-17 : Follow-ups
```
✅ Relancer leads qui n'ont pas répondu (3-5 jours après)
✅ Appels Zoom avec leads intéressés
✅ Onboard premiers vendeurs
```

#### Jour 18-21 : Scraping de maintenance
```
✅ 200 profils/jour (maintien du pipeline)
✅ Focus sur qualité > quantité
✅ Nouveaux mots-clés (niches spécifiques)
```

**Livrables Semaine 3 :**
- [ ] 1-3 vendeurs onboardés
- [ ] 800 profils additionnels
- [ ] Pipeline de 20-30 leads chauds

---

# 📅 SEMAINE 4 : SCALE INFRASTRUCTURE (Jours 22-30)

## 🎯 Objectif : Passer à l'échelle supérieure

### **Jour 22-25 : Upgrade infrastructure**

Si ça marche (3+ vendeurs) :
```bash
✅ Upgrade proxies:
   - Passer à 10GB/mois résidentiel
   - Ajouter proxies mobile pour TikTok

✅ Multi-threading:
   - 3 instances Playwright parallèles
   - 3x plus rapide

✅ Automatisation complète:
   - Scraping quotidien automatique (cron)
   - Email sending automatique
```

### **Jour 26-30 : Scaling**

```bash
✅ Objectif: 1,000 profils/jour
✅ Cold emails: 100/jour
✅ Database PostgreSQL (pour gros volumes)
```

**Livrables Semaine 4 :**
- [ ] Infrastructure scalable
- [ ] 5,000 profils additionnels
- [ ] 5-10 vendeurs total
- [ ] Système automatisé

---

# 📊 RÉCAP 30 JOURS

| Semaine | Profils | Emails | Cold Emails | Vendeurs |
|---------|---------|--------|-------------|----------|
| 1 | 800 | 240 | 50 | 0 |
| 2 | 2,500 | 750 | 350 | 1-2 |
| 3 | 800 | 240 | 200 | 3-5 |
| 4 | 5,000 | 1,500 | 400 | 5-10 |
| **TOTAL** | **9,100** | **2,730** | **1,000** | **5-10** |

---

# 💰 BUDGET DÉTAILLÉ 30 JOURS

## Setup (One-time)
```
Domaine email: 10€
(Optionnel)
```

## Mensuel
```
Proxies Smartproxy 8GB: 70€
Playwright/Python: 0€ (gratuit)
Serveur (optionnel): 0-20€
--------------------------
TOTAL: 70-100€/mois
```

## ROI Attendu

**Acquisition :**
- 10,000 profils scrapés
- 3,000 emails
- 1,000 cold emails envoyés
- 30-50 réponses positives (3-5%)
- **5-10 vendeurs onboardés**

**Si chaque vendeur fait 500€/mois de ventes :**
- Commission 2.78% = 13.9€/vendeur
- 10 vendeurs = **139€/mois récurrent**

**Break-even : Mois 1 si 6+ vendeurs**

---

# ✅ CHECKLIST QUOTIDIENNE (À Partir Semaine 2)

## Matin (1h)
- [ ] Lancer scraper (100-200 profils)
- [ ] Vérifier pas de CAPTCHA/ban
- [ ] Backup auto des résultats

## Midi (30min)
- [ ] Envoyer 30-50 cold emails
- [ ] Répondre aux messages reçus

## Soir (15min)
- [ ] Check stats (profils, emails, réponses)
- [ ] Planifier lendemain

---

# 🎯 INDICATEURS CLÉS (KPIs)

### À Tracker Quotidiennement

```python
# dashboard_stats.py
stats = {
    'profils_scrapés_today': 0,
    'profils_total': 0,
    'emails_trouvés_today': 0,
    'emails_total': 0,
    'cold_emails_sent_today': 0,
    'cold_emails_total': 0,
    'réponses_positives': 0,
    'vendeurs_onboardés': 0,
    'taux_conversion': 0,  # réponses / emails envoyés
}
```

### Seuils d'Alerte
```
🟢 Taux emails trouvés > 25% → Bon
🟡 Taux emails trouvés 15-25% → Moyen (ajuster mots-clés)
🔴 Taux emails trouvés < 15% → Mauvais (changer stratégie)

🟢 Taux réponse > 5% → Excellent
🟡 Taux réponse 2-5% → Normal
🔴 Taux réponse < 2% → Mauvais pitch (revoir template)
```

---

# 🚨 TROUBLESHOOTING

### Problème 1 : Ban/CAPTCHA après 1h
**Solution :**
- Réduire volume (PROFILES_PER_KEYWORD = 10)
- Augmenter délais (DELAY = 10s)
- Vérifier proxies (changer si datacenter)
- Pause 24h

### Problème 2 : 0 emails trouvés
**Solution :**
- Vérifier parsing linktree fonctionne
- Tester manuellement sur 3-4 profils
- Changer de niche (moins de créateurs B2C, plus B2B)

### Problème 3 : Emails bounced
**Solution :**
- Vérifier SPF/DKIM configuré
- Réduire volume emails (10/jour)
- Utiliser email warmup service
- Améliorer contenu (moins "spammy")

### Problème 4 : 0 réponses
**Solution :**
- A/B test templates
- Personnaliser davantage
- Follow-up après 5 jours
- Vérifier landing page marketplace

---

# 📞 PLAN B : Si Ça Ne Marche Pas

### Après 2 semaines, si < 2 vendeurs :

**Option A : Pivot niche**
```
Crypto creators → Trop saturé
   ↓
Pivot vers: Profs qui vendent cours privés
         ou: Consultants avec lead magnets
         ou: Designers freelance
```

**Option B : Approche manuelle**
```
Moins de volume, plus de qualité:
- 10 DMs Twitter/jour ultra-personnalisés
- Offre d'onboarding gratuit
- Call Zoom avec chaque lead
```

**Option C : Partenariats**
```
Contacter micro-influenceurs (5-10K followers):
"Je te donne 20% sur toutes les ventes de vendeurs que tu apportes"
```

---

# 🎯 OBJECTIF FINAL (Fin Mois 1)

```
✅ 10,000 profils scrapés
✅ 3,000 emails récupérés
✅ 1,000 cold emails envoyés
✅ 5-10 vendeurs actifs
✅ Système automatisé qui tourne tout seul
✅ 100-200€/mois de commissions récurrentes
```

**Si atteint → Scale Mois 2:**
- Budget 300-500€
- 50,000 profils
- 30-50 vendeurs
- 500-1000€/mois commissions

---

# 💪 MOTIVATION : C'EST TON PROJET DE VIE

**Jour 1 :** Setup (chiant mais nécessaire)
**Jour 7 :** Premiers emails scrapés (ça marche !)
**Jour 14 :** Premiers cold emails envoyés (excitant)
**Jour 21 :** Premier vendeur onboardé (🎉 VICTOIRE)
**Jour 30 :** 5-10 vendeurs, revenus récurrents

**Dans 6 mois :** 100+ vendeurs, 2,000€/mois passif

**Dans 1 an :** Business à 6 chiffres

---

**TU ES PRÊT. GO! 🚀**

**Commence MAINTENANT:**
```bash
cd scraper
python3 test_all.py
```

**Prochain fichier à lire: COLD_EMAIL.md**
