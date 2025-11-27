# 📧 GUIDE COLD EMAIL POST-SCRAPING

**Objectif :** Convertir tes 3,000 emails en 10+ vendeurs actifs

---

# ⚠️ LA VÉRITÉ SUR LE COLD EMAIL

## Taux de Conversion Réalistes

```
1,000 emails envoyés
    ↓
50-100 emails ouverts (5-10%)
    ↓
15-30 réponses (1.5-3%)
    ↓
5-10 leads intéressés (0.5-1%)
    ↓
1-3 vendeurs onboardés (0.1-0.3%)
```

**Pour 10 vendeurs → Envoyer 3,000-10,000 emails**

---

# 🚨 RÈGLES D'OR (Sinon SPAM)

### 1. **Domaine Dédié** (Obligatoire si > 50 emails/jour)

#### NE JAMAIS utiliser ton email perso
```
❌ tonnom@gmail.com → BAN permanent si spam
✅ contact@tonsite.com → Séparé, protégé
```

#### Setup domaine (10€/an)
```
1. Acheter: firstname-marketplace.com (Namecheap/OVH)
2. Créer email: hello@firstname-marketplace.com
3. Configurer DNS (SPF/DKIM/DMARC)
```

---

### 2. **Email Warming** (Critical!)

#### Problème :
```
Nouveau domaine + 100 emails/jour = Spam instantané
```

#### Solution : Warm-up progressif
```
Jour 1-3:   5 emails/jour   (à des potes, demande réponse)
Jour 4-7:   10 emails/jour
Jour 8-14:  20 emails/jour
Jour 15-21: 30 emails/jour
Jour 22-30: 50 emails/jour
Mois 2:     100 emails/jour
```

**Services automatiques :**
- Warmup Inbox (gratuit 14 jours) : https://warmupinbox.com
- Mailwarm : https://mailwarm.com
- Lemwarm : https://lemlist.com/lemwarm

**Comment ça marche :**
1. Tu connectes ton email
2. Le service envoie des emails à d'autres users du service
3. Ils répondent, marquent "pas spam"
4. Ta réputation monte
5. Après 2 semaines → Prêt pour cold email

---

### 3. **SPF/DKIM/DMARC** (Anti-Spam DNS)

#### Configuration DNS (Obligatoire)

**SPF Record :**
```
Type: TXT
Name: @
Value: v=spf1 include:_spf.gmail.com ~all
```

**DKIM Record :**
```
(Dépend du provider, généré automatiquement par Gmail/Outlook)
```

**DMARC Record :**
```
Type: TXT
Name: _dmarc
Value: v=DMARC1; p=none; rua=mailto:hello@tondomaine.com
```

**Vérification :**
- https://mxtoolbox.com/spf.aspx
- https://mxtoolbox.com/dkim.aspx
- https://mxtoolbox.com/dmarc.aspx

Tous doivent être ✅ VERT

---

### 4. **Content Quality** (Éviter triggers spam)

#### Mots à ÉVITER
```
❌ "Free", "Act now", "Limited time"
❌ "Buy", "Purchase", "Order now"
❌ "Click here", "100% guaranteed"
❌ Trop de MAJUSCULES
❌ Trop d'emojis (max 2)
❌ Trop de liens (max 1-2)
```

#### Bonnes pratiques
```
✅ Personnalisation (nom, projet spécifique)
✅ Ton conversationnel
✅ Court (< 150 mots)
✅ 1 CTA clair
✅ Signature professionnelle
✅ Lien opt-out facile
```

---

# 📝 TEMPLATES EMAILS (Copy-Paste Ready)

## Template 1 : Cold Email Créateurs

```
Objet: {{Prénom}}, 2.78% vs 10% de commission ?

Salut {{Prénom}},

J'ai vu que tu vends {{produit}} sur {{plateforme}}.

Quick question : ça te dit de garder 97.22% de tes revenus au lieu de 90% ?

Je lance une marketplace Telegram pour créateurs. Mêmes features que Gumroad, mais :
• Commission 2.78% (vs 10%)
• Paiements crypto directs (BTC/ETH/USDT)
• Pas de KYC

Tu serais intéressé pour migrer {{produit}} en beta ?
Je t'aide gratuitement à setup.

Réponds "oui" si curieux 👀

{{Ton prénom}}
Fondateur - {{Nom marketplace}}
{{Lien}}

---
PS : Si pas intéressé, réponds juste "non merci" et je ne te recontacte plus.
```

**Taux d'ouverture attendu :** 15-25%
**Taux de réponse attendu :** 2-4%

---

## Template 2 : Side Projects qui dorment

```
Objet: Monétiser tes side projects ?

Hey {{Prénom}},

J'ai vu ton {{profil/projet spécifique}} - excellent travail !

Question : t'as des side projects qui dorment sur GitHub/Behance/Dribbble ?

Je lance une marketplace pour monétiser les produits digitaux.
Commission ultra-faible (2.78% vs 10% Gumroad).

Exemples qui marchent :
• Templates, scripts, bots
• Guides, cours, ebooks
• Assets design, mockups

Ça te dit de publier un de tes projets en beta ?
Je t'aide à tout setup (gratuit).

Intéressé ?

{{Prénom}}
{{Lien marketplace}}
```

**Taux de réponse attendu :** 3-5%

---

## Template 3 : Indie Hackers

```
Objet: Alternative à Gumroad (2.78% fee)

Salut {{Prénom}},

Indie hacker à indie hacker : tu paies 10% à Gumroad/Patreon ?

J'ai créé une alternative Telegram avec 2.78% commission.

Features clés :
✅ Paiements crypto (BTC, ETH, USDT)
✅ Livraison automatique
✅ Analytics vendeur
✅ 0 KYC

Cherche 10 beta testers. Je t'onboard perso si intéressé.

Dispo pour un quick call cette semaine ?

{{Prénom}}
Building in public | {{Twitter/LinkedIn}}
```

**Taux de conversion call → vendeur :** 30-50%

---

# 🤖 AUTOMATISATION COLD EMAIL

## Option 1 : Gmail SMTP (Gratuit, 100/jour max)

```python
# email_sender.py
import smtplib
import csv
import time
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class GmailSender:
    """Envoi d'emails via Gmail SMTP"""

    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password  # App password, pas ton vrai mdp
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587

    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Envoie un email"""
        try:
            # Créer message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email
            msg['To'] = to_email
            msg['Subject'] = subject

            # Body HTML
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    {body.replace('\n', '<br>')}
                </body>
            </html>
            """

            msg.attach(MIMEText(body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))

            # Connexion SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.send_message(msg)

            print(f"✅ Email envoyé: {to_email}")
            return True

        except Exception as e:
            print(f"❌ Erreur envoi {to_email}: {e}")
            return False

    def send_campaign(self, csv_file: str, template: str, limit: int = 20):
        """Envoie une campagne depuis CSV"""

        # Lire leads
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            leads = [row for row in reader if row.get('email')]

        print(f"📧 {len(leads)} leads trouvés")

        sent = 0
        for lead in leads[:limit]:
            if sent >= limit:
                break

            # Personnaliser template
            email = lead['email']
            username = lead.get('username', 'there')
            bio = lead.get('bio', '')

            # Variables à remplacer
            subject = f"{username}, 2.78% vs 10% commission ?"
            body = template.replace('{{Prénom}}', username)
            body = body.replace('{{produit}}', 'tes produits')  # Améliorer parsing bio

            # Envoyer
            if self.send_email(email, subject, body):
                sent += 1

                # Délai anti-spam
                delay = random.uniform(30, 90)  # 30-90s entre emails
                print(f"⏳ Attente {delay:.0f}s...")
                time.sleep(delay)

        print(f"\n✅ Campagne terminée: {sent}/{limit} emails envoyés")


# Configuration
GMAIL_EMAIL = "tonemail@gmail.com"
GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"  # À générer dans Gmail

# Template
TEMPLATE = """
Salut {{Prénom}},

J'ai vu ton profil - excellent travail !

Question : ça te dit de passer de 10% à 2.78% de commission sur tes ventes ?

Je lance une marketplace Telegram crypto-native. Mêmes features que Gumroad mais :
• Commission 2.78% (vs 10%)
• Paiements crypto directs
• Pas de KYC

Tu serais intéressé pour tester en beta ? Je t'aide gratuitement.

Réponds "oui" si curieux 👀

Prénom
Marketplace - lien.com

---
PS : Pas intéressé ? Réponds "non merci".
"""

# Usage
if __name__ == "__main__":
    sender = GmailSender(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
    sender.send_campaign(
        csv_file='output/all_leads.csv',
        template=TEMPLATE,
        limit=20  # 20 emails/jour pour commencer
    )
```

**Setup Gmail App Password :**
1. Google Account → Security
2. 2-Step Verification (activer)
3. App passwords → Generate
4. Copie le mot de passe généré

---

## Option 2 : Services Professionnels (Payant)

### **Lemlist** (Recommandé)
**Prix :** 59€/mois
**Features :**
- Warm-up automatique
- Personnalisation avancée ({{variables}})
- Follow-ups automatiques
- Tracking ouvertures/clicks
- A/B testing

**Lien :** https://lemlist.com

---

### **Instantly.ai**
**Prix :** 37€/mois
**Features :**
- Unlimited emails
- Multi-inbox (plusieurs emails)
- AI email writing
- Analytics détaillées

**Lien :** https://instantly.ai

---

### **Smartlead**
**Prix :** 39€/mois
**Features :**
- Unlimited emails
- Unlimited warmup
- Meilleur rapport qualité/prix

**Lien :** https://smartlead.ai

---

# 📊 STRATÉGIES D'ENVOI

## Stratégie 1 : Conservative (Gratuit)

```
Outil: Gmail SMTP
Volume: 20 emails/jour
Warm-up: 2 semaines
Coût: 0€

Timeline:
Jour 1-14: Warm-up (5-10 emails/jour à des potes)
Jour 15+: 20 emails/jour cold

Résultats/mois: 600 emails → 12-18 réponses → 2-4 vendeurs
```

---

## Stratégie 2 : Agressive (Payant)

```
Outil: Lemlist
Volume: 100 emails/jour
Warm-up: Automatique
Coût: 59€/mois

Timeline:
Jour 1: Setup + warm-up auto
Jour 2+: 100 emails/jour

Résultats/mois: 3,000 emails → 60-90 réponses → 10-20 vendeurs
```

---

## Stratégie 3 : Multi-Account (Scale)

```
Outils: 5 comptes Gmail + Instantly.ai
Volume: 500 emails/jour (100/compte)
Coût: 37€/mois

Setup:
- Créer 5 adresses Gmail
- Warm-up toutes simultanément
- Rotationentre comptes

Résultats/mois: 15,000 emails → 300-450 réponses → 50-100 vendeurs
```

---

# 🎯 PERSONNALISATION AVANCÉE

## Variables à Extraire du Scraping

```python
# Améliorer tiktok_scraper.py
def extract_personalization_data(bio: str, username: str) -> dict:
    """Extrait données pour personnalisation"""

    data = {
        'first_name': username.split('_')[0].capitalize(),
        'platform': 'TikTok',  # ou Twitter
        'product_type': None,
        'current_platform': None,
    }

    # Détecter type de produit dans bio
    if any(word in bio.lower() for word in ['ebook', 'book', 'guide']):
        data['product_type'] = 'ebook'
    elif any(word in bio.lower() for word in ['course', 'class', 'training']):
        data['product_type'] = 'online course'
    elif any(word in bio.lower() for word in ['template', 'notion', 'figma']):
        data['product_type'] = 'templates'

    # Détecter plateforme actuelle
    if 'gumroad' in bio.lower():
        data['current_platform'] = 'Gumroad'
    elif 'patreon' in bio.lower():
        data['current_platform'] = 'Patreon'

    return data
```

**Usage dans template :**
```python
body = template.replace('{{Prénom}}', data['first_name'])
body = body.replace('{{produit}}', data['product_type'] or 'tes produits')
body = body.replace('{{plateforme}}', data['current_platform'] or 'ta plateforme actuelle')
```

---

# ✅ CHECKLIST AVANT ENVOI

### Technique
- [ ] Domaine configuré (SPF/DKIM/DMARC)
- [ ] Email warm-up (min 2 semaines)
- [ ] Test envoi à toi-même (vérifier spam folder)
- [ ] Variables {{Prénom}} remplacées
- [ ] Lien opt-out fonctionnel

### Contenu
- [ ] Objet personnalisé (pas generic)
- [ ] Email < 150 mots
- [ ] Pas de mots spam
- [ ] 1 seul CTA clair
- [ ] Signature pro

### Compliance
- [ ] Lien opt-out présent
- [ ] Adresse physique (optionnel EU)
- [ ] Pas de fausses promesses

---

# 📈 TRACKING & OPTIMISATION

## Métriques Clés

```python
metrics = {
    'emails_sent': 0,
    'emails_delivered': 0,  # Pas bounced
    'emails_opened': 0,
    'emails_clicked': 0,
    'replies_total': 0,
    'replies_interested': 0,
    'replies_not_interested': 0,
    'calls_booked': 0,
    'vendors_onboarded': 0,
}

# KPIs
'deliverability': emails_delivered / emails_sent * 100,  # >95%
'open_rate': emails_opened / emails_delivered * 100,     # >15%
'reply_rate': replies_total / emails_delivered * 100,    # >2%
'conversion': vendors_onboarded / emails_sent * 100,     # >0.3%
```

---

## A/B Testing

### Test Objet
```
Variante A: "{{Prénom}}, 2.78% vs 10% commission ?"
Variante B: "Question pour toi {{Prénom}}"
Variante C: "{{Prénom}} - Alternative à Gumroad"

Envoyer 100 emails de chaque
Garder le meilleur
```

### Test Body
```
Variante A: Long (200 mots) avec détails features
Variante B: Court (100 mots) direct au but
Variante C: Storytelling (150 mots)
```

---

# 🚨 GESTION DES RÉPONSES

## Réponses Positives ("Intéressé")

**Action immédiate :**
```
1. Répondre dans les 2h max
2. Proposer call Zoom (Calendly link)
3. Envoyer ressources (landing page, démo)
```

**Template réponse :**
```
Excellent ! Ravi que ça t'intéresse.

Dispo pour un quick call de 15 min cette semaine ?
→ Lien Calendly

En attendant, voici notre page démo :
→ Lien

À très vite !
```

---

## Réponses Négatives ("Pas intéressé")

**Action :**
```
1. Remercier
2. Demander feedback (pourquoi pas ?)
3. Proposer de rester en contact
```

**Template :**
```
Pas de souci, merci d'avoir pris le temps de répondre !

Par curiosité : qu'est-ce qui ne colle pas ?
(Aide-moi à améliorer l'offre)

Bonne continuation !
```

---

## Pas de Réponse

**Follow-up Sequence :**

**Jour 0 :** Email initial
**Jour 3 :** Follow-up 1
```
Objet: Re: [Objet initial]

Hey {{Prénom}},

Tu as sûrement raté mon dernier email.

TL;DR: Marketplace avec 2.78% commission vs 10% Gumroad.

Intéressé pour tester en beta ?
```

**Jour 7 :** Follow-up 2 (Breakup email)
```
Objet: Dernier message

{{Prénom}},

Je suppose que le timing n'est pas bon.

Si jamais tu changes d'avis, ma porte est ouverte.

Bon courage avec {{projet}} !

PS: Si pas intéressé du tout, réponds "non" et je ne te recontacte plus.
```

**Après Jour 7 :** Arrêter

---

# 💰 BUDGET COLD EMAIL

## Option 1 : Gratuit
```
Gmail SMTP: 0€
Warm-up manuel: 0€ (mais chronophage)
Volume: 20 emails/jour
```

## Option 2 : Pro (Recommandé)
```
Lemlist: 59€/mois
ou Instantly.ai: 37€/mois

Warm-up auto
Volume: 100-500 emails/jour
```

## Option 3 : Scale
```
Lemlist: 59€
+ 3 domaines additionnels: 30€
= 89€/mois

Volume: 500+ emails/jour
```

---

# ✅ RECOMMANDATION FINALE

### Semaine 1-2 : Gratuit
```
- Gmail SMTP
- 20 emails/jour manuellement
- Apprendre ce qui marche
```

### Semaine 3-4 : Upgrade si ça marche
```
- Lemlist ou Instantly.ai
- 50-100 emails/jour
- Automatisation + follow-ups
```

### Mois 2+ : Scale
```
- Multi-domaines
- 500+ emails/jour
- VA pour gérer réponses
```

---

**Prochaine étape : Créer ton premier template et envoyer 5 emails test !**
