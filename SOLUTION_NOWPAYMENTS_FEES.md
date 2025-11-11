# Solution : Problème des Frais NOWPayments Crypto2Crypto

## 🔴 Problème Identifié

**Transaction exemple :**
- Prix produit : $2.00
- Frais plateforme : $0.06 (2.78%)
- **Total attendu : $2.06**

**Résultat réel :**
- Client paie : 0.01307293 SOL ($2.06) ✅
- **Type : crypto2crypto** ❌
- Montant reçu : 0.94104948 TON ($1.91)
- **PERTE : $0.15 (7.3%)**

### Cause

NOWPayments fait une conversion **SOL → TON** parce que :
1. Une adresse TON est configurée comme destination (UQD7Sl9...)
2. La conversion crypto-to-crypto coûte des frais importants
3. Le slippage mange une partie du montant

---

## ✅ Solution 1 : Désactiver les Payouts Automatiques (IMMÉDIAT)

**Principe :** Tout l'argent arrive sur TON wallet principal, pas de conversion.

### Étapes :

#### 1. Vérifier la configuration NOWPayments Dashboard

1. Va sur https://nowpayments.io
2. Settings → Wallets
3. **Vérifie quelle adresse TON est configurée**
4. **Désactive les payouts automatiques** si activé

#### 2. Modifier le code pour NE PAS envoyer payout_address

**Fichier :** `app/integrations/telegram/handlers/buy_handlers.py`

**Ligne 1743-1749 :** Aucun changement nécessaire (déjà correct)
```python
payment_data = self.payment_service.create_payment(
    amount_usd=total_amount,
    pay_currency=crypto_code,
    order_id=order_id,
    description=title,
    ipn_callback_url=core_settings.IPN_CALLBACK_URL
    # PAS de seller_wallet_address = tout va sur ton wallet
)
```

**Vérification :**
Le code n'envoie actuellement AUCUN `seller_wallet_address`, donc c'est bon ! ✅

#### 3. Configurer ton Wallet Principal NOWPayments

**Dashboard NOWPayments → Settings → Wallets :**

Pour éviter les conversions, configure **plusieurs wallets** :
- ✅ Adresse **USDT TRC20** (stablecoin, pas de conversion)
- ✅ Adresse **SOL** (pour recevoir les paiements SOL)
- ✅ Adresse **BTC** (pour recevoir les paiements BTC)
- ✅ Adresse **ETH** (pour recevoir les paiements ETH)

**Résultat :** Chaque paiement arrive dans la crypto que le client utilise, pas de conversion !

---

## ✅ Solution 2 : Utiliser USDT comme Monnaie de Payout (MOYEN TERME)

**Principe :** Convertir vers USDT (stablecoin) au lieu de TON.

### Avantages :
- USDT = stable (pas de fluctuation)
- Frais de conversion plus bas (~1-2% vs 7%)
- Facile à convertir en fiat

### Configuration :

```python
# app/services/payment_service.py ligne 35
seller_payout_currency: Optional[str] = "usdttrc20"  # Déjà configuré ✅
```

**MAIS** : Tu dois toujours envoyer un `seller_wallet_address` pour activer le payout, ce qui coûte des frais.

---

## ✅ Solution 3 : Payouts Manuels Hebdomadaires (LONG TERME)

**Principe :**
1. Tout l'argent arrive sur ton wallet principal
2. Calcul automatique des revenus vendeurs en DB
3. Payout manuel 1x/semaine vers les vendeurs

### Avantages :
- **Zéro frais de conversion** (tu choisis la meilleure méthode)
- Contrôle total sur les paiements
- Possibilité de négocier les frais avec les vendeurs

### Implémentation :

#### A. Désactiver payout automatique
✅ Déjà fait si tu ne passes pas `seller_wallet_address`

#### B. Dashboard Admin pour gérer les payouts

**Fichier :** `app/integrations/telegram/handlers/admin_handlers.py`

Utiliser le système existant :
```python
# Déjà implémenté ! Voir ligne 337-339
from app.services.seller_payout_service import SellerPayoutService
seller_payout_service = SellerPayoutService()
payouts = seller_payout_service.get_all_pending_payouts_admin()
```

#### C. Créer payout hebdomadaire automatique

**Nouveau fichier :** `app/tasks/weekly_seller_payouts.py`

```python
"""
Calcul automatique des payouts vendeurs chaque semaine
À exécuter via cronjob tous les lundis
"""
import psycopg2.extras
from app.core.database_init import get_postgresql_connection
from app.core.db_pool import put_connection
from datetime import datetime, timedelta

def calculate_weekly_payouts():
    """Calcule les revenus de chaque vendeur pour la semaine écoulée"""
    conn = get_postgresql_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Get date range (last 7 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        # Calculate seller revenues from completed orders
        cursor.execute('''
            SELECT
                seller_user_id,
                COUNT(*) as order_count,
                SUM(product_price_usd) as total_revenue_usd
            FROM orders
            WHERE payment_status = 'completed'
            AND completed_at BETWEEN %s AND %s
            GROUP BY seller_user_id
            HAVING SUM(product_price_usd) >= 10  -- Minimum $10 pour payout
        ''', (start_date, end_date))

        sellers = cursor.fetchall()

        for seller in sellers:
            seller_id = seller['seller_user_id']
            revenue = seller['total_revenue_usd']

            # Create payout record
            cursor.execute('''
                INSERT INTO seller_payouts (seller_user_id, total_amount_usdt, payout_status, created_at)
                VALUES (%s, %s, 'pending', CURRENT_TIMESTAMP)
            ''', (seller_id, revenue))

            print(f"✅ Payout créé pour seller {seller_id}: ${revenue:.2f}")

        conn.commit()
        print(f"\n✅ {len(sellers)} payouts créés pour la semaine")

    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur: {e}")
    finally:
        put_connection(conn)

if __name__ == "__main__":
    calculate_weekly_payouts()
```

**Exécution :** Ajouter à crontab sur Railway :
```bash
# Tous les lundis à 9h
0 9 * * 1 python app/tasks/weekly_seller_payouts.py
```

---

## 📊 Comparaison des Solutions

| Solution | Frais | Complexité | Contrôle | Recommandé |
|----------|-------|------------|----------|------------|
| **1. Pas de payout auto** | 0% | Facile | Total | ✅ OUI |
| **2. Payout USDT** | 1-2% | Moyen | Partiel | ⚠️ Si nécessaire |
| **3. Payout manuel hebdo** | 0% | Élevé | Total | ✅ Long terme |

---

## 🚀 Plan d'Action Immédiat

### Étape 1 : Diagnostic (5 min)
```bash
# Vérifier qu'aucun payout_address n'est envoyé
grep -r "seller_wallet_address\|payout_address" app/integrations/telegram/handlers/buy_handlers.py

# Résultat attendu : Rien trouvé (ou seulement dans les commentaires)
```

### Étape 2 : Dashboard NOWPayments (10 min)
1. Connecte-toi sur nowpayments.io
2. Settings → Wallets
3. **Note quelles adresses sont configurées**
4. **Désactive "Auto Payout" si activé**

### Étape 3 : Configuration Multi-Crypto (15 min)
Ajoute dans ton dashboard NOWPayments :
- Adresse USDT (TRC20)
- Adresse SOL
- Adresse BTC
- Adresse ETH

**Résultat :** Chaque paiement arrive dans la crypto du client, pas de conversion !

### Étape 4 : Test (10 min)
1. Crée un produit de test à $5
2. Paie en SOL
3. **Vérifie que tu reçois exactement 5 × taux_SOL en SOL** (pas de conversion)
4. Vérifie dans NOWPayments : Type = **crypto** (pas crypto2crypto)

---

## ❓ Questions à Vérifier

1. **L'adresse `UQD7Sl9UgMKHJEz...` est-elle configurée dans ton dashboard NOWPayments ?**
   - Si OUI → Désactive les payouts automatiques
   - Si NON → C'est bizarre, vérifie le code

2. **As-tu activé "Auto Withdrawal" dans NOWPayments ?**
   - Si OUI → Désactive-le

3. **Le vendeur a-t-il configuré une adresse TON dans le bot ?**
   - Vérifie : `SELECT seller_solana_address FROM users WHERE user_id = <seller_id>`

---

## 🎯 Résultat Attendu

Après la solution :

**Transaction correcte :**
- Prix produit : $2.00
- Frais plateforme : $0.06
- Total client : **$2.06**
- Client paie : **0.01307293 SOL**
- **Type : crypto** (pas crypto2crypto)
- Tu reçois : **0.01307293 SOL** ($2.06) ✅
- **AUCUNE PERTE** ✅

---

**Auteur :** Claude Code
**Date :** 11 novembre 2025
