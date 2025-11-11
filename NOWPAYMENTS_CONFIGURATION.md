# Configuration NowPayments API - Guide Complet

## 🔑 Variables d'environnement requises

Ajoutez ces variables dans votre `.env`:

```bash
# NowPayments API
NOWPAYMENTS_API_KEY=your_nowpayments_api_key_here
NOWPAYMENTS_IPN_SECRET=your_nowpayments_ipn_secret_here

# IPN Callback URL (Railway URL correcte)
IPN_CALLBACK_URL=https://python-bot-production-312a.up.railway.app/ipn/nowpayments
```

---

## 🏗️ Architecture Actuelle vs Requise

### ❌ Architecture Actuelle (À MODIFIER)
**Flux:** Client → Paiement Crypto → Votre Wallet Principal
- Tous les fonds vont vers VOTRE wallet
- Vous devez manuellement redistribuer aux vendeurs
- Beaucoup de travail manuel

### ✅ Architecture Requise (SPLIT PAYMENTS)
**Flux:** Client → Paiement Crypto → Commission (vous) + Vendeur
- **Commission automatique** vers votre wallet
- **Paiement vendeur automatique** vers son wallet
- Zéro intervention manuelle

---

## 🔧 Modifications à faire dans le code

### 1. Modifier la création de paiement

**Fichier:** `app/services/payment_service.py` ou le fichier qui appelle NowPayments

**ACTUELLEMENT:**
```python
payload = {
    "price_amount": product_price,
    "price_currency": "usd",
    "pay_currency": crypto_currency,
    "ipn_callback_url": IPN_CALLBACK_URL,
    "order_id": order_id
}
```

**À MODIFIER EN:**
```python
# Calculer la commission (ex: 10%)
PLATFORM_COMMISSION_PERCENT = 10  # 10% de commission
commission_amount = product_price * (PLATFORM_COMMISSION_PERCENT / 100)
seller_amount = product_price - commission_amount

payload = {
    "price_amount": product_price,
    "price_currency": "usd",
    "pay_currency": crypto_currency,
    "ipn_callback_url": IPN_CALLBACK_URL,
    "order_id": order_id,

    # ⚠️ IMPORTANT: Payout vers le wallet du vendeur
    "payout_address": seller_wallet_address,  # Wallet du VENDEUR
    "payout_currency": "usdttrc20"  # ou autre crypto que le vendeur préfère
}
```

### 2. Gérer la commission dans IPN

**Fichier:** `app/integrations/ipn_server.py`

**Ajouter après la confirmation du paiement:**
```python
if payment_status in ['finished', 'confirmed']:
    # Récupérer les infos
    order = get_order(order_id)
    product_price = order['product_price_usd']

    # Calculer commission et revenus vendeur
    commission = product_price * 0.10  # 10%
    seller_revenue = product_price - commission

    # Mettre à jour la DB
    cursor.execute('''
        UPDATE orders
        SET payment_status = %s,
            platform_commission_usdt = %s,
            seller_revenue_usdt = %s,
            completed_at = CURRENT_TIMESTAMP
        WHERE order_id = %s
    ''', ('completed', commission, seller_revenue, order_id))

    # Le vendeur recevra automatiquement son paiement via NowPayments
    # Vous recevrez la commission sur votre wallet principal
```

---

## 💰 Exemple de Flow Complet

### Scénario: Produit à 100 USDT

1. **Client achète produit:** 100 USDT
2. **NowPayments reçoit:** 100 USDT en crypto (ex: TRX)
3. **NowPayments distribue automatiquement:**
   - ✅ **90 USDT → Wallet vendeur** (via `payout_address`)
   - ✅ **10 USDT → Votre wallet** (commission automatique)

### Dans votre code:
```python
# Lors de la création du paiement
product_price = 100  # USDT
commission_rate = 0.10  # 10%

seller_payout = product_price * (1 - commission_rate)  # 90 USDT
your_commission = product_price * commission_rate  # 10 USDT

# Créer le paiement avec payout vers vendeur
response = nowpayments_api.create_payment(
    price_amount=product_price,
    price_currency="usd",
    pay_currency="trx",  # ou autre
    payout_address=seller.wallet_address,  # ⚠️ WALLET DU VENDEUR
    payout_currency="usdttrc20",
    order_id=order_id
)
```

---

## 🔐 Configuration Dashboard NowPayments

### Étapes à suivre:

1. **Connectez-vous sur nowpayments.io**

2. **Settings → Payment Settings:**
   - ✅ Activez **"IPN (Instant Payment Notifications)"**
   - ✅ Entrez votre **IPN Secret Key** (déjà dans .env)
   - ✅ URL IPN: `https://python-bot-production-312a.up.railway.app/ipn/nowpayments`

3. **Settings → Wallets:**
   - ✅ Configurez votre **wallet principal** pour recevoir les commissions
   - ⚠️ Ce wallet recevra UNIQUEMENT vos commissions
   - Les vendeurs reçoivent sur leurs propres wallets via `payout_address`

4. **Settings → API:**
   - ✅ Vérifiez votre **API Key** (déjà dans .env)
   - ✅ Activez les **Split Payments** si disponible

---

## ⚠️ Points Critiques

### 1. Wallet Vendeur OBLIGATOIRE
```python
# Dans votre table users, vérifiez que vous avez:
seller_solana_address  # ou seller_wallet_address
```

**Avant de créer un paiement:**
```python
if not seller.wallet_address:
    raise Exception("Le vendeur doit configurer son wallet avant de recevoir des paiements")
```

### 2. Commission configurable
```python
# app/core/settings.py
PLATFORM_COMMISSION_PERCENT = 10  # Modifiable facilement
```

### 3. Validation IPN
```python
# Votre ipn_server.py le fait déjà ✅
def verify_signature(secret: str, payload: bytes, signature: str) -> bool:
    mac = hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha512).hexdigest()
    return hmac.compare_digest(mac, signature)
```

---

## 📊 Schéma Base de Données

Vérifiez que votre table `orders` a ces colonnes:

```sql
-- Colonnes requises:
product_price_usdt REAL NOT NULL,
seller_revenue_usdt REAL DEFAULT 0.0,
platform_commission_usdt REAL DEFAULT 0.0,
payment_currency TEXT,
payment_status TEXT DEFAULT 'pending',
nowpayments_id TEXT,
```

✅ **Déjà en place dans votre DB PostgreSQL!**

---

## 🚀 Étapes de Mise en Production

### 1. Testez d'abord en sandbox
```bash
# Mode test (si NowPayments le propose)
NOWPAYMENTS_SANDBOX=true
```

### 2. Déployez sur Railway

### 3. Configurez l'URL IPN
```
https://python-bot-production-312a.up.railway.app/ipn/nowpayments
```

### 4. Testez avec une vraie transaction de 1$

### 5. Vérifiez que:
- ✅ Commission arrive sur VOTRE wallet
- ✅ Paiement vendeur arrive sur SON wallet
- ✅ Base de données mise à jour correctement

---

## 📞 Support

En cas de problème:
- **Email NowPayments:** support@nowpayments.io
- **Documentation:** https://documenter.getpostman.com/view/7907941/

---

## ✅ Checklist Finale

- [ ] API Key configurée dans .env
- [ ] IPN Secret configurée dans .env
- [ ] IPN URL configurée sur dashboard NowPayments
- [ ] Code modifié pour inclure `payout_address`
- [ ] Wallet vendeur obligatoire avant vente
- [ ] Commission calculée et enregistrée en DB
- [ ] Tests effectués avec petite somme
- [ ] Monitoring des paiements en place
