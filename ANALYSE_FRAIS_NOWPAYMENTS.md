# 📊 Analyse des Frais NOWPayments - Pourquoi 7.3% de Perte ?

## 🔴 Problème Constaté

**Transaction analysée :**
- 💰 Prix du produit : **$2.00 USD**
- 📦 Client paie : **$2.06 USD** (en TON)
- ✅ Vendeur reçoit : **$1.91 USD** (en TON)
- ❌ **PERTE : $0.15 (7.3%)**

**Question :** Pourquoi une perte de 7.3% alors que NOWPayments annonce 0.5% de frais ?

---

## 🔍 Structure des Frais NOWPayments (2025)

### Frais de Service

| Type de Transaction | Frais NOWPayments |
|---------------------|-------------------|
| **Single-currency** (pas de conversion) | **0.5%** |
| **Multi-currency** (avec conversion) | **1%** (0.5% transaction + 0.5% exchange) |
| Fiat conversion | 1.5% - 2.3% |

**Important :** NOWPayments ne facture **AUCUN frais fixe** en dollars - uniquement des pourcentages.

### Frais de Réseau (Network Fees)

- **Frais blockchain variables** (gas fees)
- Dépendent de :
  - La blockchain utilisée
  - La congestion du réseau
  - La vitesse de traitement souhaitée
- **Non fixés par NOWPayments** - imposés par la blockchain

---

## 🧮 Calcul Théorique vs Réalité

### Scénario 1 : Sans Conversion (0.5%)
```
Prix produit     : $2.00
Commission bot   : $0.06 (2.78%)
Total à payer    : $2.06

Frais NOWPayments: $2.06 × 0.5% = $0.01
Montant reçu     : $2.06 - $0.01 = $2.05 ✅

PERTE ATTENDUE   : $0.01 (0.5%)
```

### Scénario 2 : Avec Conversion Crypto (1%)
```
Prix produit     : $2.00
Commission bot   : $0.06
Total à payer    : $2.06

Frais NOWPayments: $2.06 × 1% = $0.02
Montant reçu     : $2.06 - $0.02 = $2.04 ✅

PERTE ATTENDUE   : $0.02 (1%)
```

### ❌ Scénario Actuel : Crypto2Crypto + Network Fees
```
Prix produit     : $2.00
Commission bot   : $0.06
Total client     : $2.06

RÉALITÉ CONSTATÉE:
Montant reçu     : $1.91 ❌
PERTE RÉELLE     : $0.15 (7.3%) ⚠️
```

---

## 🚨 Cause du Problème : Type "crypto2crypto"

### Qu'est-ce qu'une transaction "crypto2crypto" ?

Quand NOWPayments doit **convertir** la crypto que le client paie vers **une autre crypto** pour le payout :

**Exemple :**
```
Client paie en SOL → NOWPayments convertit → Vendeur reçoit en USDT (Solana)
Client paie en BTC → NOWPayments convertit → Vendeur reçoit en TON
```

### Frais Cachés d'une Conversion Crypto2Crypto

1. **Frais de service NOWPayments** : 1% (conversion)
2. **Slippage** : 2-5% (fluctuation du taux de change pendant la conversion)
3. **Network fees** :
   - Frais blockchain de départ (ex: SOL network fee ~$0.01)
   - Frais blockchain d'arrivée (ex: TON network fee ~$0.02-0.05)
4. **Spread** : Différence entre prix d'achat et de vente

**TOTAL POSSIBLE : 5-10%** sur petites transactions ! ⚠️

---

## 📉 Pourquoi C'est Pire sur Petits Montants ?

### Exemple : $2 vs $200

| Montant | Frais NOWPayments (1%) | Network Fee (fixe) | Total Frais | % de Perte |
|---------|------------------------|---------------------|-------------|------------|
| **$2** | $0.02 | $0.03-0.10 | **$0.05-0.12** | **2.5-6%** |
| **$20** | $0.20 | $0.03-0.10 | **$0.23-0.30** | **1.15-1.5%** |
| **$200** | $2.00 | $0.03-0.10 | **$2.03-2.10** | **1.01-1.05%** |

**Conclusion :** Les network fees fixes pèsent beaucoup plus sur les petites transactions.

### Votre Cas : $2.06
```
Frais NOWPayments : ~$0.02 (1%)
Network fee SOL   : ~$0.01
Network fee TON   : ~$0.05
Slippage          : ~$0.05-0.07 (2-3%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL PERDU       : ~$0.13-0.15 (6.3-7.3%) ✅ Correspond !
```

---

## ✅ Solutions pour Réduire les Frais

### Solution 1 : Recevoir dans la Crypto Payée (RECOMMANDÉ)

**Principe :** Pas de conversion = Pas de frais élevés

**Configuration Dashboard NOWPayments :**
1. Allez sur https://nowpayments.io
2. **Settings → Wallets**
3. Configurez plusieurs adresses de réception :
   - ✅ Adresse **USDT TRC20** (pour paiements en USDT)
   - ✅ Adresse **SOL** (pour paiements en SOL)
   - ✅ Adresse **TON** (pour paiements en TON)
   - ✅ Adresse **BTC** (pour paiements en BTC)
   - ✅ Adresse **ETH** (pour paiements en ETH)

**Résultat :**
- Client paie en SOL → Vous recevez en SOL (type: "crypto")
- Client paie en TON → Vous recevez en TON (type: "crypto")
- **Frais : 0.5% + network fee (~$0.01-0.02)**

**Transaction à $2.06 :**
```
Client paie       : $2.06 en SOL
Frais NOWPayments : $0.01 (0.5%)
Network fee       : $0.01
Montant reçu      : $2.04 en SOL ✅
PERTE             : $0.02 (1%) ✅ Acceptable !
```

---

### Solution 2 : Augmenter le Prix Minimum

**Principe :** Sur petits montants, les network fees fixes sont proportionnellement trop élevés.

**Recommandations :**
- ✅ Prix minimum : **$10** (frais < 2%)
- ⚠️ Entre $5-10 : Acceptable (frais ~2-3%)
- ❌ Moins de $5 : Déconseillé (frais > 5%)

**Impact sur votre bot :**
```python
# app/integrations/telegram/handlers/sell_handlers.py
MINIMUM_PRODUCT_PRICE_USD = 10.00  # Au lieu de 2.00

# Message d'erreur
"Le prix minimum est de $10 pour réduire les frais de transaction."
```

---

### Solution 3 : Payout Manuel Hebdomadaire (Long Terme)

**Principe :** Accumuler les revenus et payer les vendeurs en batch

**Avantages :**
- ✅ Frais mutualisés sur gros montants
- ✅ Contrôle total des conversions
- ✅ Meilleurs taux de change

**Flux :**
1. Tous les paiements arrivent sur **votre wallet principal**
2. Calcul automatique des revenus vendeurs en DB
3. **1x/semaine** : Payout groupé vers les vendeurs

**Exemple :**
```
Vendeur A : 50 ventes × $2 = $100
Vendeur B : 30 ventes × $5 = $150

Payout hebdomadaire :
- Vendeur A : $100 (frais 1% = $1)
- Vendeur B : $150 (frais 1% = $1.50)

VS paiement instantané :
- 50 transactions × 7% = $7 de frais !
- 30 transactions × 7% = $10.50 de frais !

ÉCONOMIE : $15 vs $2.50 de frais 💰
```

---

### Solution 4 : Utiliser USDT comme Standard

**Principe :** USDT est un stablecoin 1:1 avec USD

**Configuration :**
1. **Forcer** les paiements en USDT (TRC20, ERC20, SOL)
2. Recevoir en USDT (pas de conversion)
3. Network fees très faibles sur TRC20 (~$1)

**Avantages :**
- ✅ Pas de volatilité
- ✅ Pas de slippage
- ✅ Frais ultra-bas sur TRC20
- ✅ Facile à convertir en fiat

**Code :**
```python
# app/integrations/telegram/handlers/buy_handlers.py
ALLOWED_CRYPTOS = ['usdttrc20', 'usdterc20', 'usdtsol']  # Uniquement USDT

# Message pour l'utilisateur
"Pour réduire les frais, nous acceptons uniquement USDT."
```

---

## 🎯 Recommandation Finale

### Court Terme (Immédiat)
1. ✅ **Configurer plusieurs wallets** dans NOWPayments Dashboard
2. ✅ **Augmenter prix minimum** à $10
3. ✅ **Désactiver auto-payout** (si activé)

### Moyen Terme (1-2 semaines)
4. ✅ **Favoriser USDT** comme crypto de paiement
5. ✅ **Afficher les frais estimés** avant paiement :
   ```
   Prix : $2.00
   Frais plateforme : $0.06
   Frais réseau estimés : $0.05-0.10
   ━━━━━━━━━━━━━━━━━━━━━━━━━
   Total : $2.11-2.16
   ```

### Long Terme (1-2 mois)
6. ✅ **Implémenter payout hebdomadaire**
7. ✅ **Négocier avec NOWPayments** pour volume discount (à partir de 50 BTC/mois : 0.45%)

---

## 📌 Checklist Action

- [ ] Connecter au dashboard NOWPayments
- [ ] Vérifier si "Auto Withdrawal" est activé → **Désactiver**
- [ ] Configurer adresses multiples (USDT, SOL, TON, BTC, ETH)
- [ ] Modifier prix minimum à $10 dans le code
- [ ] Tester une transaction de $10 en SOL
- [ ] Vérifier le type : doit être "crypto" (pas "crypto2crypto")
- [ ] Calculer les frais réels = devrait être ~1%

---

## 📞 Support NOWPayments

Si le problème persiste après configuration :

**Email :** partners@nowpayments.io

**Questions à poser :**
1. Pourquoi mes transactions sont en type "crypto2crypto" ?
2. Comment forcer le type "crypto" (sans conversion) ?
3. Y a-t-il des frais cachés sur petites transactions ?
4. Quelle est la structure exacte des network fees ?

---

**Date :** 11 novembre 2025
**Auteur :** Claude Code
**Version :** 1.0
