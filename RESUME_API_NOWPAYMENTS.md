# 📚 Guide Complet de l'API NOWPayments

## 📋 Table des Matières

1. [Configuration Initiale](#-0-configuration-initiale)
2. [Auth and API Status](#%EF%B8%8F⃣-1-auth-and-api-status)
3. [Currencies](#-2-currencies)
4. [Payments](#-3-payments)
5. [Mass Payouts](#-4-mass-payouts)
6. [Conversions](#-5-conversions)
7. [Customer Management](#-6-customer-management)
8. [Fiat Payouts](#-7-fiat-payouts)
9. [Recurring Payments API](#-8-recurring-payments-api)
10. [Use Cases Pratiques](#-9-use-cases-pratiques)

---

## 🚀 0. Configuration Initiale

### **À quoi sert NOWPayments ?**

NOWPayments est un **processeur de paiements crypto** qui permet de :
- ✅ Accepter **150+ cryptomonnaies** (BTC, ETH, USDT, SOL, TON, etc.)
- ✅ **Convertir automatiquement** vers la crypto de votre choix
- ✅ **Split payments** : envoyer directement une partie aux vendeurs
- ✅ **Non-custodial** : vous gardez le contrôle de vos fonds
- ✅ **IPN webhooks** : notifications automatiques des paiements

**Idéal pour :** E-commerce, marketplaces, donations, SaaS, abonnements

---

### **Étape 1 : Inscription et Configuration Dashboard**

#### 1.1 Créer un compte
1. Allez sur https://nowpayments.io
2. Cliquez sur **"Sign Up"**
3. Vérifiez votre email

#### 1.2 Configurer vos Wallets de Réception
**Dashboard → Settings → Wallets**

**Option A : Un seul wallet (simple)**
```
Configurez 1 adresse principale (ex: USDT TRC20)
└─> Tous les paiements seront convertis vers USDT
└─> Frais : 1% (conversion) + network fees
```

**Option B : Plusieurs wallets (recommandé)**
```
Configurez plusieurs adresses :
├─ USDT TRC20 : TXyz123...
├─ SOL : 8bK9x...
├─ TON : UQD7Sl...
├─ BTC : bc1q...
└─ ETH : 0xABC...

Avantages :
└─> Pas de conversion si client paie dans la même crypto
└─> Frais réduits à 0.5%
└─> Type "crypto" au lieu de "crypto2crypto"
```

**Pour votre bot (marketplace) :**
```
Recommandation : Option B avec focus sur USDT
├─ USDT TRC20 (principal) : frais réseau très bas (~$1)
├─ SOL : populaire, rapide, frais bas
└─ BTC : pour les puristes
```

#### 1.3 Générer leas Clés API
**Dashboard → Settings → API**

1. Cliquez sur **"Generate API Key"**
2. Sauvegardez immédiatement votre **API Key**
   ```
   Exemple : NPM_API_KEY_abc123def456...
   ```

3. Générez votre **IPN Secret Key**
   ```
   ⚠️ CRITIQUE : N'est affiché qu'une seule fois !
   Exemple : ipn_secret_xyz789...
   ```

4. Sauvegardez dans votre `.env` :
   ```bash
   NOWPAYMENTS_API_KEY=NPM_API_KEY_abc123def456...
   NOWPAYMENTS_IPN_SECRET=ipn_secret_xyz789...
   ```

#### 1.4 Configurer l'IPN Callback URL
**Dashboard → Settings → Payment Settings**

```
IPN Callback URL : https://votre-bot.railway.app/ipn/nowpayments
```

⚠️ **Important :**
- Doit être en **HTTPS** (pas HTTP)
- Doit être **accessible publiquement** (pas localhost)
- Vérifier que Cloudflare/firewall autorise les IPs NOWPayments

#### 1.5 Activer les Features (optionnel)
**Dashboard → Settings → Payment Settings**

- ✅ **Auto Withdrawal** : ❌ Désactiver (pour éviter conversions forcées)
- ✅ **Wrong-Asset Auto-Processing** : ⚠️ Activer si vous voulez accepter n'importe quelle crypto
- ✅ **Fee Paid by User** : ✅ Activer (client paie les frais réseau)

---

### **Étape 2 : Configuration du Code**

#### 2.1 Variables d'environnement (`.env`)
```bash
# NOWPayments API
NOWPAYMENTS_API_KEY=votre_api_key_ici
NOWPAYMENTS_IPN_SECRET=votre_ipn_secret_ici

# IPN Callback URL (votre serveur)
IPN_CALLBACK_URL=https://votre-bot.railway.app/ipn/nowpayments

# Configuration plateforme
PLATFORM_COMMISSION_PERCENT=2.78
```

#### 2.2 Client NOWPayments (`app/integrations/nowpayments_client.py`)
```python
import logging
import requests
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class NowPaymentsClient:
    BASE_URL = "https://api.nowpayments.io/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    def get_status(self) -> bool:
        """Vérifier si l'API est disponible"""
        try:
            response = requests.get(f"{self.BASE_URL}/status", timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"API status check failed: {e}")
            return False

    def list_currencies(self) -> list:
        """Récupérer les cryptos disponibles"""
        try:
            response = requests.get(
                f"{self.BASE_URL}/currencies",
                headers=self._headers(),
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get("currencies", [])
            return []
        except Exception as e:
            logger.error(f"Get currencies failed: {e}")
            return []

    def get_estimate(self, amount: float, currency_from: str, currency_to: str) -> Optional[Dict]:
        """Obtenir le montant exact en crypto"""
        try:
            response = requests.get(
                f"{self.BASE_URL}/estimate",
                headers=self._headers(),
                params={
                    "amount": amount,
                    "currency_from": currency_from.lower(),
                    "currency_to": currency_to.lower()
                },
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            logger.error(f"Estimate failed: {response.status_code} - {response.text}")
            return None
        except Exception as e:
            logger.error(f"Get estimate exception: {e}")
            return None

    def create_payment(
        self,
        amount_usd: float,
        pay_currency: str,
        order_id: str,
        description: str,
        ipn_callback_url: str,
        payout_address: Optional[str] = None,
        payout_currency: Optional[str] = None
    ) -> Optional[Dict]:
        """Créer un paiement"""
        try:
            payload = {
                "price_amount": amount_usd,
                "price_currency": "usd",
                "pay_currency": pay_currency.lower(),
                "order_id": order_id,
                "order_description": description,
                "ipn_callback_url": ipn_callback_url
            }

            # Split payment (optionnel)
            if payout_address:
                payload["payout_address"] = payout_address
                payload["payout_currency"] = payout_currency.lower() if payout_currency else "usdttrc20"

            response = requests.post(
                f"{self.BASE_URL}/payment",
                headers=self._headers(),
                json=payload,
                timeout=30
            )

            if response.status_code == 201:
                return response.json()

            logger.error(f"Create payment failed: {response.status_code} - {response.text}")
            return {"error": "PAYMENT_CREATION_FAILED", "details": response.text}

        except Exception as e:
            logger.error(f"Create payment exception: {e}")
            return {"error": "EXCEPTION", "message": str(e)}

    def get_payment(self, payment_id: str) -> Optional[Dict]:
        """Récupérer le statut d'un paiement"""
        try:
            response = requests.get(
                f"{self.BASE_URL}/payment/{payment_id}",
                headers=self._headers(),
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            logger.error(f"Get payment failed: {response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Get payment exception: {e}")
            return None
```

#### 2.3 IPN Server (`app/integrations/ipn_server.py`)
```python
import hmac
import hashlib
import json
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

IPN_SECRET = "votre_ipn_secret"

def verify_ipn_signature(ipn_secret: str, payload: bytes, signature: str) -> bool:
    """Vérifier que l'IPN vient de NOWPayments"""
    data = json.loads(payload)
    sorted_json = json.dumps(data, separators=(',', ':'), sort_keys=True)

    mac = hmac.new(
        ipn_secret.encode(),
        sorted_json.encode(),
        hashlib.sha512
    ).hexdigest()

    return hmac.compare_digest(mac, signature)

@app.post("/ipn/nowpayments")
async def handle_ipn(request: Request):
    """Recevoir les notifications de paiement"""
    # Récupérer la signature
    signature = request.headers.get("x-nowpayments-sig")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature")

    # Lire le body
    body = await request.body()

    # Vérifier la signature
    if not verify_ipn_signature(IPN_SECRET, body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parser les données
    data = await request.json()

    payment_status = data.get("payment_status")
    order_id = data.get("order_id")
    payment_id = data.get("payment_id")

    print(f"IPN received: order_id={order_id}, status={payment_status}")

    # Gérer selon le statut
    if payment_status == "finished":
        # ✅ Paiement confirmé
        mark_order_completed(order_id)
        send_product_to_buyer(order_id)

    elif payment_status == "failed":
        # ❌ Paiement échoué
        mark_order_failed(order_id)

    elif payment_status == "partially_paid":
        # ⚠️ Sous-payé
        notify_admin_underpayment(order_id, data)

    return {"status": "ok"}
```

---

### **Étape 3 : Test de l'Intégration**

#### 3.1 Vérifier l'API Status
```bash
curl https://api.nowpayments.io/v1/status
# Réponse attendue : {"message": "OK"}
```

#### 3.2 Test avec votre API Key
```bash
curl -H "x-api-key: VOTRE_API_KEY" \
  https://api.nowpayments.io/v1/currencies
# Réponse : {"currencies": ["btc", "eth", ...]}
```

#### 3.3 Créer un Paiement de Test ($1)
```python
from nowpayments_client import NowPaymentsClient

client = NowPaymentsClient("VOTRE_API_KEY")

payment = client.create_payment(
    amount_usd=1.00,
    pay_currency="usdttrc20",
    order_id="TEST-001",
    description="Test paiement",
    ipn_callback_url="https://votre-bot.railway.app/ipn/nowpayments"
)

print(f"Adresse de paiement : {payment['pay_address']}")
print(f"Montant à payer : {payment['pay_amount']} USDT")
```

#### 3.4 Tester l'IPN
1. Créez un paiement
2. Envoyez le montant vers l'adresse générée
3. Vérifiez les logs de votre serveur pour voir l'IPN
4. Confirmez que la commande est marquée comme "completed"

---

## 1️⃣ Auth and API Status

### **À quoi ça sert ?**

**Objectif principal :** Authentifier toutes vos requêtes et vérifier que le service NOWPayments est opérationnel.

**Cas d'usage pratiques :**
- ✅ Vérifier l'API avant de créer un paiement (évite erreurs)
- ✅ Monitoring : alerter si l'API est down
- ✅ Healthcheck de votre intégration

---

### **Authentification**

**Header requis pour TOUTES les requêtes :**
```http
x-api-key: VOTRE_API_KEY
```

**Exemple avec curl :**
```bash
curl -H "x-api-key: NPM_API_KEY_abc123..." \
  https://api.nowpayments.io/v1/currencies
```

**Exemple avec Python :**
```python
import requests

headers = {
    "x-api-key": "NPM_API_KEY_abc123...",
    "Content-Type": "application/json"
}

response = requests.get(
    "https://api.nowpayments.io/v1/currencies",
    headers=headers
)
```

---

### **Endpoint : GET /status**

```http
GET https://api.nowpayments.io/v1/status
```

**Usage :** Vérifier si l'API est disponible

**Réponse (200 OK) :**
```json
{
  "message": "OK"
}
```

**Implémentation dans votre bot :**
```python
async def check_nowpayments_health():
    """Vérifier si NOWPayments est disponible"""
    try:
        response = requests.get("https://api.nowpayments.io/v1/status", timeout=5)
        if response.status_code == 200:
            logger.info("✅ NOWPayments API is operational")
            return True
        else:
            logger.error(f"⚠️ NOWPayments API returned {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ NOWPayments API is down: {e}")
        return False

# Utilisation avant de créer un paiement
if not await check_nowpayments_health():
    await bot.send_message(user_id, "❌ Service de paiement temporairement indisponible")
    return
```

---

## 2️⃣ Currencies

### **À quoi ça sert ?**

**Objectif :** Récupérer la liste des cryptomonnaies acceptées et calculer les taux de change en temps réel.

**Pourquoi c'est important ?**
- ✅ Afficher uniquement les cryptos disponibles à vos utilisateurs
- ✅ Calculer le montant EXACT en crypto (évite sous-paiement/sur-paiement)
- ✅ Vérifier si le montant est supérieur au minimum requis
- ✅ Gérer les cryptos temporairement indisponibles

---

### **Endpoint : GET /currencies**

```http
GET https://api.nowpayments.io/v1/currencies
Headers:
  x-api-key: VOTRE_API_KEY
```

**Usage :** Récupérer toutes les cryptos disponibles

**Réponse (200 OK) :**
```json
{
  "currencies": [
    "btc", "eth", "usdt", "usdttrc20", "usdterc20",
    "sol", "ton", "bnb", "ltc", "xrp", "ada", ...
  ]
}
```

**Implémentation dans votre bot :**
```python
async def get_available_cryptos():
    """Récupérer les cryptos disponibles avec cache"""
    # Cache 1 heure
    cache_key = "nowpayments_currencies"
    cached = redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # Récupérer depuis l'API
    response = requests.get(
        "https://api.nowpayments.io/v1/currencies",
        headers={"x-api-key": API_KEY},
        timeout=10
    )

    if response.status_code == 200:
        currencies = response.json()["currencies"]

        # Filtrer uniquement les principales
        main_currencies = ["btc", "eth", "usdttrc20", "sol", "ton", "bnb"]
        available = [c for c in currencies if c in main_currencies]

        # Cache 1h
        redis.setex(cache_key, 3600, json.dumps(available))
        return available

    # Fallback
    return ["btc", "eth", "usdttrc20"]

# Afficher dans le bot Telegram
@router.callback_query(F.data == "select_crypto")
async def select_crypto_handler(query: CallbackQuery):
    cryptos = await get_available_cryptos()

    keyboard = []
    for crypto in cryptos:
        keyboard.append([InlineKeyboardButton(
            text=f"💰 {crypto.upper()}",
            callback_data=f"pay_{crypto}"
        )])

    await query.message.edit_text(
        "Sélectionnez votre crypto de paiement :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
```

---

### **Endpoint : GET /estimate**

```http
GET https://api.nowpayments.io/v1/estimate
  ?amount=100
  &currency_from=usd
  &currency_to=btc
Headers:
  x-api-key: VOTRE_API_KEY
```

**Paramètres :**
- `amount` : Montant à convertir
- `currency_from` : Devise source (usd, eur, btc, eth, etc.)
- `currency_to` : Devise cible

**Usage :** Calculer le montant EXACT en crypto à payer

**Réponse (200 OK) :**
```json
{
  "currency_from": "usd",
  "amount_from": 100,
  "currency_to": "btc",
  "estimated_amount": 0.00234567
}
```

**Pourquoi utiliser `/estimate` ?**
```
❌ MAUVAIS : Utiliser un taux fixe ou une API externe
└─> Risque de sous-paiement (paiement refusé)
└─> Risque de sur-paiement (client perd de l'argent)

✅ BON : Utiliser /estimate de NOWPayments
└─> Montant exact attendu par NOWPayments
└─> Prend en compte le slippage et les frais
└─> Synchronisé avec le système de paiement
```

**Implémentation dans votre bot :**
```python
async def get_crypto_amount(amount_usd: float, crypto: str):
    """Calculer le montant exact en crypto"""

    # Pour les stablecoins, utiliser 1:1
    stablecoins = ["usdt", "usdttrc20", "usdterc20", "usdtsol", "usdc"]
    if crypto.lower() in stablecoins:
        return amount_usd

    # Récupérer l'estimation depuis NOWPayments
    response = requests.get(
        "https://api.nowpayments.io/v1/estimate",
        headers={"x-api-key": API_KEY},
        params={
            "amount": amount_usd,
            "currency_from": "usd",
            "currency_to": crypto.lower()
        },
        timeout=10
    )

    if response.status_code == 200:
        data = response.json()
        return data["estimated_amount"]

    # Si l'API échoue, ne pas continuer
    raise Exception(f"Failed to get estimate for {crypto}")

# Utilisation avant de créer le paiement
product_price = 10.00
commission = 0.28
total_usd = product_price + commission

crypto_amount = await get_crypto_amount(total_usd, "btc")

# Afficher à l'utilisateur
await bot.send_message(
    user_id,
    f"💰 Montant à payer : {crypto_amount:.8f} BTC\n"
    f"≈ ${total_usd} USD"
)
```

---

### **Endpoint : GET /min-amount**

```http
GET https://api.nowpayments.io/v1/min-amount
  ?currency_from=usd
  &currency_to=btc
Headers:
  x-api-key: VOTRE_API_KEY
```

**Usage :** Vérifier le montant minimum requis pour un paiement

**Réponse (200 OK) :**
```json
{
  "currency_from": "usd",
  "currency_to": "btc",
  "min_amount": 1.0
}
```

**Implémentation :**
```python
async def validate_amount(amount_usd: float, crypto: str):
    """Vérifier que le montant est >= minimum"""
    response = requests.get(
        "https://api.nowpayments.io/v1/min-amount",
        headers={"x-api-key": API_KEY},
        params={
            "currency_from": "usd",
            "currency_to": crypto.lower()
        },
        timeout=10
    )

    if response.status_code == 200:
        min_amount = response.json()["min_amount"]
        if amount_usd < min_amount:
            raise Exception(f"Montant minimum : ${min_amount}")

    return True
```

---

## 3️⃣ Payments

### **À quoi ça sert ?**

**Objectif principal :** Créer et gérer les paiements crypto de bout en bout.

**Cycle de vie d'un paiement :**
```
1. Créer le paiement (POST /payment)
   └─> Générer une adresse de dépôt unique

2. Afficher l'adresse au client
   └─> QR code + adresse + montant exact

3. Client envoie les fonds
   └─> Transaction blockchain en cours

4. NOWPayments détecte le paiement
   └─> IPN envoyé à votre serveur (status: confirming)

5. Confirmations blockchain
   └─> IPN envoyé (status: confirmed)

6. NOWPayments envoie vers votre wallet
   └─> IPN envoyé (status: sending)

7. Fonds reçus
   └─> IPN envoyé (status: finished) ✅
   └─> Livrer le produit au client
```

---

### **Endpoint : POST /payment**

```http
POST https://api.nowpayments.io/v1/payment
Headers:
  x-api-key: VOTRE_API_KEY
  Content-Type: application/json

Body:
{
  "price_amount": 10.00,
  "price_currency": "usd",
  "pay_currency": "btc",
  "order_id": "ORDER-12345",
  "order_description": "Formation Python avancée",
  "ipn_callback_url": "https://votre-bot.railway.app/ipn/nowpayments",
  "payout_address": "bc1q...",        // Optionnel (split payment)
  "payout_currency": "btc",           // Optionnel
  "payout_extra_id": ""               // Optionnel (XRP, XLM)
}
```

**Paramètres Obligatoires :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `price_amount` | float | Prix du produit en devise `price_currency` |
| `price_currency` | string | Devise du prix (usd, eur, btc, etc.) |
| `pay_currency` | string | Crypto que le client va utiliser |
| `order_id` | string | ID unique de votre commande (max 255 chars) |
| `order_description` | string | Description lisible (apparaît dans l'historique) |

**Paramètres Optionnels (Split Payment) :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `ipn_callback_url` | string | URL pour recevoir les webhooks |
| `payout_address` | string | Adresse du vendeur (pour paiement direct) |
| `payout_currency` | string | Crypto pour le payout (ex: usdttrc20) |
| `payout_extra_id` | string | Memo/Tag pour XRP, XLM, etc. |

**Réponse (201 Created) :**
```json
{
  "payment_id": 6249365965,
  "payment_status": "waiting",
  "pay_address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
  "pay_amount": 0.00023456,
  "actually_paid": 0,
  "pay_currency": "btc",
  "price_amount": 10,
  "price_currency": "usd",
  "order_id": "ORDER-12345",
  "order_description": "Formation Python avancée",
  "purchase_id": 5312822613,
  "created_at": "2025-01-11T10:30:00.000Z",
  "updated_at": "2025-01-11T10:30:00.000Z",
  "expiration_estimate_date": "2025-01-18T10:30:00.000Z"
}
```

**Champs Importants :**
- `payment_id` : ID NOWPayments (pour vérifier le statut)
- `pay_address` : Adresse où le client doit envoyer les fonds
- `pay_amount` : Montant EXACT en crypto à payer
- `payment_status` : Statut actuel (waiting, confirming, finished, etc.)
- `expiration_estimate_date` : Date d'expiration (7 jours par défaut)

---

### **Implémentation Complète dans Votre Bot**

```python
from nowpayments_client import NowPaymentsClient
import qrcode
import io

async def create_crypto_payment(
    product_id: str,
    product_price: float,
    buyer_user_id: int,
    crypto: str
):
    """Créer un paiement crypto pour un produit"""

    # 1. Calculer le montant total avec commission
    commission_percent = 2.78
    commission = product_price * (commission_percent / 100)
    total_usd = product_price + commission

    # 2. Générer un order_id unique
    order_id = f"ORD-{product_id}-{buyer_user_id}-{int(time.time())}"

    # 3. Récupérer les infos produit
    product = get_product(product_id)
    description = f"{product['title']} - {product['seller_name']}"

    # 4. Créer le paiement
    client = NowPaymentsClient(settings.NOWPAYMENTS_API_KEY)

    payment_data = client.create_payment(
        amount_usd=total_usd,
        pay_currency=crypto,
        order_id=order_id,
        description=description,
        ipn_callback_url=settings.IPN_CALLBACK_URL
        # PAS de payout_address = tout va sur votre wallet principal
    )

    if "error" in payment_data:
        raise Exception(f"Payment creation failed: {payment_data['error']}")

    # 5. Sauvegarder dans la DB
    save_order({
        "order_id": order_id,
        "payment_id": payment_data["payment_id"],
        "product_id": product_id,
        "buyer_user_id": buyer_user_id,
        "seller_user_id": product["seller_user_id"],
        "product_price_usd": product_price,
        "platform_commission_usd": commission,
        "total_amount_usd": total_usd,
        "payment_currency": crypto,
        "payment_address": payment_data["pay_address"],
        "payment_amount": payment_data["pay_amount"],
        "payment_status": "pending",
        "created_at": datetime.now()
    })

    # 6. Générer un QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=4)

    # URI pour les wallets (meilleure UX)
    if crypto == "btc":
        qr_data = f"bitcoin:{payment_data['pay_address']}?amount={payment_data['pay_amount']}"
    elif crypto == "eth":
        qr_data = f"ethereum:{payment_data['pay_address']}?value={payment_data['pay_amount']}"
    else:
        qr_data = payment_data['pay_address']

    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_bytes = buf.getvalue()

    # 7. Afficher au client
    message = f"""
✅ **Paiement Créé**

💳 **Produit :** {product['title']}
💰 **Prix :** ${product_price:.2f}
📊 **Frais plateforme :** ${commission:.2f}
━━━━━━━━━━━━━━━━━━━━
💵 **TOTAL :** ${total_usd:.2f}

🔐 **Crypto :** {crypto.upper()}
📤 **Montant à envoyer :**
`{payment_data['pay_amount']}` {crypto.upper()}

📍 **Adresse de paiement :**
`{payment_data['pay_address']}`

⏰ **Expiration :** 7 jours
🆔 **Commande :** {order_id}

⚠️ Envoyez **exactement** le montant indiqué
"""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ J'ai payé", callback_data=f"check_payment_{order_id}")],
        [InlineKeyboardButton("❌ Annuler", callback_data=f"cancel_payment_{order_id}")]
    ])

    await bot.send_photo(
        chat_id=buyer_user_id,
        photo=qr_bytes,
        caption=message,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

    return order_id
```

---

### **Endpoint : GET /payment/:payment_id**

```http
GET https://api.nowpayments.io/v1/payment/6249365965
Headers:
  x-api-key: VOTRE_API_KEY
```

**Usage :** Vérifier le statut actuel d'un paiement

**Statuts Possibles :**

| Statut | Description | Action |
|--------|-------------|--------|
| `waiting` | En attente du paiement | Afficher "En attente..." |
| `confirming` | Transaction détectée sur blockchain | Afficher "Confirmation en cours..." |
| `confirmed` | Transaction confirmée | Afficher "Confirmé !" |
| `sending` | Envoi vers votre wallet | Afficher "Traitement..." |
| `finished` | ✅ **Terminé** | **Livrer le produit** |
| `partially_paid` | Sous-payé | Demander complément ou rembourser |
| `failed` | ❌ Échoué | Afficher erreur + support |
| `refunded` | Remboursé | Notifier le client |
| `expired` | Expiré (7j) | Proposer de recréer |

**Réponse (200 OK) :**
```json
{
  "payment_id": 6249365965,
  "payment_status": "finished",
  "pay_address": "bc1q...",
  "payin_extra_id": null,
  "price_amount": 10,
  "price_currency": "usd",
  "pay_amount": 0.00023456,
  "actually_paid": 0.00023456,
  "pay_currency": "btc",
  "order_id": "ORDER-12345",
  "order_description": "Formation Python",
  "purchase_id": 5312822613,
  "outcome_amount": 0.00023000,
  "outcome_currency": "btc",
  "payout_hash": "abc123...",
  "payin_hash": "def456...",
  "created_at": "2025-01-11T10:30:00.000Z",
  "updated_at": "2025-01-11T10:35:00.000Z",
  "burning_percent": null,
  "type": "crypto",  // ⚠️ Vérifier si "crypto" ou "crypto2crypto"
  "parent_payment_id": null,
  "payment_extra_ids": []
}
```

**Champs Critiques :**
- `actually_paid` : Montant réellement payé (peut différer de `pay_amount`)
- `outcome_amount` : Montant que **vous** allez recevoir
- `outcome_currency` : Crypto que **vous** allez recevoir
- `type` :
  - `"crypto"` : Pas de conversion ✅ (frais 0.5%)
  - `"crypto2crypto"` : Avec conversion ⚠️ (frais ~7%)

**Implémentation :**
```python
@router.callback_query(F.data.startswith("check_payment_"))
async def check_payment_status(query: CallbackQuery):
    """Vérifier manuellement le statut du paiement"""
    order_id = query.data.split("_")[2]

    # Récupérer le payment_id depuis la DB
    order = get_order(order_id)
    payment_id = order["payment_id"]

    # Interroger NOWPayments
    client = NowPaymentsClient(settings.NOWPAYMENTS_API_KEY)
    payment = client.get_payment(payment_id)

    if not payment:
        await query.answer("❌ Erreur de vérification", show_alert=True)
        return

    status = payment["payment_status"]

    if status == "finished":
        # ✅ Paiement confirmé
        update_order_status(order_id, "completed")
        send_product_to_buyer(order_id)

        await query.message.edit_text(
            "✅ **PAIEMENT CONFIRMÉ !**\n\n"
            "📦 Votre produit est en cours d'envoi...",
            parse_mode="Markdown"
        )

    elif status in ["waiting", "confirming", "confirmed", "sending"]:
        # ⏳ En cours
        await query.answer(
            f"⏳ Statut : {status}\nVeuillez patienter...",
            show_alert=True
        )

    elif status == "partially_paid":
        # ⚠️ Sous-payé
        paid = payment["actually_paid"]
        expected = payment["pay_amount"]
        missing = expected - paid

        await query.message.edit_text(
            f"⚠️ **PAIEMENT INCOMPLET**\n\n"
            f"💰 Payé : {paid:.8f} {payment['pay_currency'].upper()}\n"
            f"💰 Attendu : {expected:.8f}\n"
            f"❌ Manquant : {missing:.8f}\n\n"
            "Envoyez le montant manquant vers la même adresse.",
            parse_mode="Markdown"
        )

    elif status == "failed":
        # ❌ Échoué
        update_order_status(order_id, "failed")
        await query.message.edit_text(
            "❌ **PAIEMENT ÉCHOUÉ**\n\n"
            "Contactez le support avec votre numéro de commande.",
            parse_mode="Markdown"
        )
```

---

### **IPN (Instant Payment Notifications) - Webhooks**

**À quoi ça sert ?**

Les IPN sont des **webhooks automatiques** envoyés par NOWPayments à votre serveur à chaque changement de statut d'un paiement.

**Avantages vs Polling manuel :**
```
❌ Polling (GET /payment/:id en boucle)
├─ Requêtes inutiles toutes les X secondes
├─ Latence (détection retardée)
└─ Rate limiting possible

✅ IPN (Webhooks)
├─ Notification instantanée (<1 seconde)
├─ Pas de polling nécessaire
├─ Sécurisé (signature HMAC)
└─ Idéal pour l'UX temps réel
```

---

**Configuration IPN :**

**1. Dashboard NOWPayments**
```
Settings → Payment Settings → IPN Secret Key
└─> Générer et sauvegarder le secret
```

**2. Configurer l'URL de callback**
```python
# Lors de la création du paiement
payment = client.create_payment(
    amount_usd=10,
    pay_currency="btc",
    order_id="ORDER-123",
    description="Formation",
    ipn_callback_url="https://votre-bot.railway.app/ipn/nowpayments"  # ✅
)
```

**3. Vérifier la signature HMAC**
```python
import hmac
import hashlib
import json

def verify_ipn_signature(ipn_secret: str, payload: bytes, signature: str) -> bool:
    """Vérifier que l'IPN vient bien de NOWPayments"""
    # Étape 1 : Parser le JSON
    data = json.loads(payload)

    # Étape 2 : Trier par clés (CRITIQUE)
    sorted_json = json.dumps(data, separators=(',', ':'), sort_keys=True)

    # Étape 3 : Calculer le HMAC SHA-512
    mac = hmac.new(
        ipn_secret.encode('utf-8'),
        sorted_json.encode('utf-8'),
        hashlib.sha512
    ).hexdigest()

    # Étape 4 : Comparer avec la signature reçue
    return hmac.compare_digest(mac, signature)

# Exemple d'utilisation
signature = request.headers.get("x-nowpayments-sig")
body = await request.body()

if not verify_ipn_signature(IPN_SECRET, body, signature):
    raise HTTPException(401, "Invalid signature")
```

---

**Implémentation Complète IPN Server :**

```python
from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib
import json

app = FastAPI()

@app.post("/ipn/nowpayments")
async def handle_nowpayments_ipn(request: Request):
    """Recevoir les notifications de NOWPayments"""

    # 1. Récupérer la signature
    signature = request.headers.get("x-nowpayments-sig")
    if not signature:
        logger.error("IPN without signature")
        raise HTTPException(401, "Missing signature")

    # 2. Lire le body
    body = await request.body()

    # 3. Vérifier la signature
    if not verify_ipn_signature(settings.NOWPAYMENTS_IPN_SECRET, body, signature):
        logger.error(f"Invalid IPN signature: {signature}")
        raise HTTPException(401, "Invalid signature")

    # 4. Parser les données
    data = await request.json()

    payment_id = data.get("payment_id")
    payment_status = data.get("payment_status")
    order_id = data.get("order_id")
    actually_paid = data.get("actually_paid")
    pay_amount = data.get("pay_amount")
    pay_currency = data.get("pay_currency")

    logger.info(f"IPN received: payment_id={payment_id}, order_id={order_id}, status={payment_status}")

    # 5. Récupérer la commande
    order = get_order_by_id(order_id)
    if not order:
        logger.error(f"Order not found: {order_id}")
        return {"status": "error", "message": "Order not found"}

    # 6. Gérer selon le statut
    if payment_status == "finished":
        # ✅ PAIEMENT CONFIRMÉ
        logger.info(f"✅ Payment finished: {order_id}")

        # Mettre à jour la commande
        update_order({
            "order_id": order_id,
            "payment_status": "completed",
            "completed_at": datetime.now(),
            "actually_paid": actually_paid,
            "payment_hash": data.get("payin_hash")
        })

        # Envoyer le produit au client
        await send_product_to_buyer(
            buyer_user_id=order["buyer_user_id"],
            order_id=order_id,
            product_id=order["product_id"]
        )

        # Notifier le vendeur
        await notify_seller_of_sale(
            seller_user_id=order["seller_user_id"],
            order_id=order_id,
            amount_usd=order["seller_revenue_usd"]
        )

    elif payment_status in ["confirming", "confirmed"]:
        # ⏳ CONFIRMATION EN COURS
        logger.info(f"⏳ Payment confirming: {order_id}")

        update_order({
            "order_id": order_id,
            "payment_status": "confirming"
        })

        # Notifier le client
        await bot.send_message(
            order["buyer_user_id"],
            "⏳ Paiement détecté ! Confirmation en cours..."
        )

    elif payment_status == "sending":
        # 📤 ENVOI VERS WALLET
        logger.info(f"📤 Payment sending: {order_id}")

        update_order({
            "order_id": order_id,
            "payment_status": "sending"
        })

    elif payment_status == "partially_paid":
        # ⚠️ SOUS-PAYÉ
        logger.warning(f"⚠️ Partial payment: {order_id}, paid={actually_paid}, expected={pay_amount}")

        update_order({
            "order_id": order_id,
            "payment_status": "partially_paid",
            "actually_paid": actually_paid
        })

        # Notifier le client
        missing = float(pay_amount) - float(actually_paid)
        await bot.send_message(
            order["buyer_user_id"],
            f"⚠️ **PAIEMENT INCOMPLET**\n\n"
            f"Montant reçu : {actually_paid} {pay_currency}\n"
            f"Montant attendu : {pay_amount} {pay_currency}\n"
            f"Manquant : {missing:.8f} {pay_currency}\n\n"
            f"Envoyez le complément vers la même adresse.",
            parse_mode="Markdown"
        )

    elif payment_status == "failed":
        # ❌ PAIEMENT ÉCHOUÉ
        logger.error(f"❌ Payment failed: {order_id}")

        update_order({
            "order_id": order_id,
            "payment_status": "failed"
        })

        # Notifier le client
        await bot.send_message(
            order["buyer_user_id"],
            "❌ Le paiement a échoué.\n\n"
            "Contactez le support avec votre numéro de commande."
        )

    elif payment_status == "refunded":
        # 💸 REMBOURSÉ
        logger.info(f"💸 Payment refunded: {order_id}")

        update_order({
            "order_id": order_id,
            "payment_status": "refunded"
        })

        # Notifier le client
        await bot.send_message(
            order["buyer_user_id"],
            "💸 Votre paiement a été remboursé."
        )

    elif payment_status == "expired":
        # ⏰ EXPIRÉ
        logger.info(f"⏰ Payment expired: {order_id}")

        update_order({
            "order_id": order_id,
            "payment_status": "expired"
        })

    # 7. Retourner OK (IMPORTANT)
    return {"status": "ok"}
```

**⚠️ Important :**
- Toujours retourner `{"status": "ok"}` en HTTP 200
- Si vous retournez une erreur, NOWPayments va retry (jusqu'à 10x)
- Logger tous les IPN pour debug

---

### **Endpoint : GET /payment/ (List)**

```http
GET https://api.nowpayments.io/v1/payment/
  ?limit=50
  &page=0
  &sortBy=created_at
  &orderBy=desc
  &dateFrom=2025-01-01
  &dateTo=2025-01-31
Headers:
  Authorization: Bearer YOUR_TOKEN
  x-api-key: YOUR_API_KEY
```

**Usage :** Récupérer l'historique des paiements (pour analytics, dashboard admin)

**Paramètres :**
- `limit` : Résultats par page (1-500)
- `page` : Numéro de page (0, 1, 2, ...)
- `sortBy` : Trier par (payment_id, created_at, payment_status, etc.)
- `orderBy` : Ordre (asc, desc)
- `dateFrom` : Date début (YYYY-MM-DD)
- `dateTo` : Date fin (YYYY-MM-DD)
- `invoiceId` : Filtrer par invoice

**Réponse (200 OK) :**
```json
{
  "data": [
    {
      "payment_id": 6249365965,
      "payment_status": "finished",
      "pay_address": "bc1q...",
      "price_amount": 10,
      "pay_amount": 0.00023456,
      "actually_paid": 0.00023456,
      "pay_currency": "btc",
      "order_id": "ORDER-12345",
      "created_at": "2025-01-11T10:30:00.000Z",
      "updated_at": "2025-01-11T10:35:00.000Z",
      "type": "crypto"
    },
    ...
  ],
  "limit": 50,
  "page": 0,
  "pagesCount": 5,
  "total": 234
}
```

**Implémentation (Dashboard Admin) :**
```python
@router.get("/admin/payments")
async def admin_payments_history(page: int = 0):
    """Dashboard admin : historique des paiements"""

    client = NowPaymentsClient(settings.NOWPAYMENTS_API_KEY)

    # Récupérer depuis NOWPayments
    payments = client.list_payments(
        limit=50,
        page=page,
        sort_by="created_at",
        order_by="desc"
    )

    if not payments:
        return {"error": "Failed to fetch payments"}

    # Enrichir avec données de la DB
    enriched = []
    for payment in payments["data"]:
        order = get_order_by_payment_id(payment["payment_id"])
        if order:
            payment["product_title"] = order["product_title"]
            payment["buyer_name"] = order["buyer_name"]
            payment["seller_name"] = order["seller_name"]
        enriched.append(payment)

    return {
        "payments": enriched,
        "pagination": {
            "page": page,
            "total_pages": payments["pagesCount"],
            "total": payments["total"]
        }
    }
```

---

## 4️⃣ Mass Payouts

### **À quoi ça sert ?**

**Objectif :** Envoyer des paiements crypto en masse vers plusieurs wallets (ideal pour payouts vendeurs).

**Cas d'usage :**
- ✅ Payer les vendeurs (hebdomadaire/mensuel)
- ✅ Remboursements groupés
- ✅ Airdrops / Distributions
- ✅ Salaires en crypto

**Avantages :**
- 🚀 Rapide : jusqu'à 1000 payouts en 1 requête
- 💰 Économique : frais mutualisés
- 🔒 Sécurisé : 2FA obligatoire

---

### **Endpoint : GET /balance**

```http
GET https://api.nowpayments.io/v1/balance
Headers:
  x-api-key: YOUR_API_KEY
```

**Usage :** Vérifier votre solde en custody avant de créer des payouts

**Réponse (200 OK) :**
```json
{
  "eth": {
    "amount": 1.5,
    "pendingAmount": 0.2
  },
  "btc": {
    "amount": 0.05,
    "pendingAmount": 0
  },
  "usdttrc20": {
    "amount": 5000,
    "pendingAmount": 100
  }
}
```

**Implémentation :**
```python
async def check_balance_before_payout(currency: str, required_amount: float):
    """Vérifier qu'on a assez de fonds"""
    client = NowPaymentsClient(settings.NOWPAYMENTS_API_KEY)
    balance = client.get_balance()

    if not balance:
        raise Exception("Failed to get balance")

    currency_lower = currency.lower()
    if currency_lower not in balance:
        raise Exception(f"No balance for {currency}")

    available = balance[currency_lower]["amount"]

    if available < required_amount:
        raise Exception(
            f"Insufficient balance: {available} {currency} "
            f"(required: {required_amount})"
        )

    return True
```

---

### **Endpoint : POST /payout (Create)**

```http
POST https://api.nowpayments.io/v1/payout
Headers:
  Authorization: Bearer YOUR_TOKEN
  x-api-key: YOUR_API_KEY
  Content-Type: application/json

Body:
{
  "withdrawals": [
    {
      "address": "TXyz123...",
      "currency": "usdttrc20",
      "amount": "100",
      "ipn_callback_url": "https://votre-bot.railway.app/ipn/payout",
      "unique_external_id": "PAYOUT-SELLER-123"
    },
    {
      "address": "0xABC...",
      "currency": "eth",
      "amount": "0.5",
      "unique_external_id": "PAYOUT-SELLER-456"
    }
  ]
}
```

**Paramètres :**
- `address` : Adresse wallet du destinataire
- `currency` : Crypto à envoyer
- `amount` : Montant (string)
- `ipn_callback_url` : URL pour webhook (optionnel)
- `unique_external_id` : Votre ID interne (optionnel mais recommandé)

**Réponse (200 OK) :**
```json
{
  "id": "5000000191",  // batch_withdrawal_id
  "withdrawals": [
    {
      "id": "123456789",
      "address": "TXyz123...",
      "currency": "usdttrc20",
      "amount": "100",
      "batch_withdrawal_id": "5000000191",
      "status": "CREATING",
      "created_at": "2025-01-11T10:00:00.000Z"
    },
    ...
  ]
}
```

**Implémentation (Payout Hebdomadaire) :**
```python
async def process_weekly_seller_payouts():
    """Payer tous les vendeurs avec solde >= $50"""

    # 1. Récupérer les vendeurs à payer
    sellers = get_sellers_pending_payout(min_amount=50.00)

    if not sellers:
        logger.info("No sellers to pay this week")
        return

    # 2. Vérifier le solde total nécessaire
    total_usdt = sum(s["pending_amount"] for s in sellers)
    await check_balance_before_payout("usdttrc20", total_usdt)

    # 3. Préparer les withdrawals
    withdrawals = []
    for seller in sellers:
        # Valider l'adresse
        is_valid = await validate_seller_address(
            seller["wallet_address"],
            "usdttrc20"
        )

        if not is_valid:
            logger.error(f"Invalid address for seller {seller['user_id']}")
            continue

        withdrawals.append({
            "address": seller["wallet_address"],
            "currency": "usdttrc20",
            "amount": str(seller["pending_amount"]),
            "ipn_callback_url": settings.IPN_PAYOUT_URL,
            "unique_external_id": f"PAYOUT-SELLER-{seller['user_id']}-{int(time.time())}"
        })

    # 4. Créer le batch
    client = NowPaymentsClient(settings.NOWPAYMENTS_API_KEY)
    result = client.create_payout(withdrawals)

    if "error" in result:
        logger.error(f"Payout creation failed: {result['error']}")
        return

    batch_id = result["id"]

    # 5. Vérifier avec 2FA (automatique)
    code_2fa = generate_2fa_code(settings.NOWPAYMENTS_2FA_SECRET)
    verify_result = client.verify_payout(batch_id, code_2fa)

    if not verify_result:
        logger.error(f"Payout verification failed for batch {batch_id}")
        return

    # 6. Sauvegarder dans la DB
    for i, seller in enumerate(sellers):
        payout_id = result["withdrawals"][i]["id"]

        save_seller_payout({
            "seller_user_id": seller["user_id"],
            "payout_id": payout_id,
            "batch_id": batch_id,
            "amount_usdt": seller["pending_amount"],
            "currency": "usdttrc20",
            "address": seller["wallet_address"],
            "status": "processing",
            "created_at": datetime.now()
        })

        # Notifier le vendeur
        await bot.send_message(
            seller["user_id"],
            f"💸 **Payout Initié**\n\n"
            f"Montant : ${seller['pending_amount']:.2f} USDT\n"
            f"Adresse : {seller['wallet_address'][:10]}...\n"
            f"Statut : En cours de traitement"
        )

    logger.info(f"✅ Batch payout created: {batch_id}, {len(sellers)} sellers")
```

---

### **Endpoint : POST /payout/:batch_id/verify (2FA)**

```http
POST https://api.nowpayments.io/v1/payout/5000000191/verify
Headers:
  Authorization: Bearer YOUR_TOKEN
  x-api-key: YOUR_API_KEY
  Content-Type: application/json

Body:
{
  "verification_code": "123456"
}
```

**Usage :** Vérifier le payout avec code 2FA (obligatoire)

**⚠️ Important :**
- Code 2FA envoyé par email OU depuis Google Authenticator
- 10 tentatives maximum
- Payout rejeté après 1h si non vérifié

**Automation avec OTP Library :**
```python
import pyotp

def generate_2fa_code(secret_key: str) -> str:
    """Générer un code 2FA automatiquement"""
    totp = pyotp.TOTP(secret_key)
    return totp.now()

# Configuration
# 1. Dashboard → Account Settings → Two-Step Auth → Use an app
# 2. Sauvegarder le secret key
# 3. Utiliser dans le code

# Utilisation
code = generate_2fa_code(settings.NOWPAYMENTS_2FA_SECRET)
client.verify_payout(batch_id, code)
```

---

### **Endpoint : GET /payout/:payout_id (Status)**

```http
GET https://api.nowpayments.io/v1/payout/123456789
Headers:
  x-api-key: YOUR_API_KEY
```

**Usage :** Vérifier le statut d'un payout individuel

**Statuts :**
- `creating` : Création en cours
- `processing` : En traitement
- `sending` : Envoi blockchain
- `finished` : ✅ Terminé
- `failed` : ❌ Échoué
- `rejected` : Rejeté (non vérifié)

**Réponse (200 OK) :**
```json
{
  "id": "123456789",
  "address": "TXyz123...",
  "currency": "usdttrc20",
  "amount": "100",
  "batch_withdrawal_id": "5000000191",
  "status": "FINISHED",
  "hash": "abc123def456...",
  "fee": "1",
  "created_at": "2025-01-11T10:00:00.000Z",
  "updated_at": "2025-01-11T10:05:00.000Z"
}
```

---

### **IPN Webhook pour Payouts**

```python
@app.post("/ipn/payout")
async def handle_payout_ipn(request: Request):
    """Recevoir les notifications de payout"""

    # Vérifier la signature (même méthode que paiements)
    signature = request.headers.get("x-nowpayments-sig")
    body = await request.body()

    if not verify_ipn_signature(settings.NOWPAYMENTS_IPN_SECRET, body, signature):
        raise HTTPException(401, "Invalid signature")

    data = await request.json()

    payout_id = data.get("id")
    status = data.get("status")
    address = data.get("address")
    amount = data.get("amount")
    currency = data.get("currency")
    tx_hash = data.get("hash")

    logger.info(f"Payout IPN: id={payout_id}, status={status}")

    # Récupérer le payout en DB
    payout = get_payout_by_id(payout_id)
    if not payout:
        return {"status": "error", "message": "Payout not found"}

    # Mettre à jour le statut
    if status == "FINISHED":
        update_payout({
            "payout_id": payout_id,
            "status": "completed",
            "tx_hash": tx_hash,
            "completed_at": datetime.now()
        })

        # Notifier le vendeur
        await bot.send_message(
            payout["seller_user_id"],
            f"✅ **Payout Confirmé !**\n\n"
            f"💰 Montant : ${amount} {currency.upper()}\n"
            f"📍 Adresse : {address}\n"
            f"🔗 TX : {tx_hash[:20]}...\n\n"
            f"Vérifiez votre wallet !",
            parse_mode="Markdown"
        )

    elif status == "FAILED":
        update_payout({
            "payout_id": payout_id,
            "status": "failed",
            "error": data.get("error")
        })

        # Notifier l'admin
        await bot.send_message(
            ADMIN_ID,
            f"❌ Payout failed: {payout_id}\n"
            f"Seller: {payout['seller_user_id']}\n"
            f"Amount: ${amount}\n"
            f"Error: {data.get('error')}"
        )

    return {"status": "ok"}
```

---

## 5️⃣ Conversions

### **À quoi ça sert ?**

**Objectif :** Convertir vos cryptos en custody (ex: BTC → USDT).

**Cas d'usage :**
- ✅ Convertir tous les revenus en stablecoin
- ✅ Préparer les payouts dans la bonne crypto
- ✅ Hedge contre la volatilité

**⚠️ Nécessite NOWPayments Custody activé**

---

### **Endpoint : POST /conversion**

```http
POST https://api.nowpayments.io/v1/conversion
Headers:
  x-api-key: YOUR_API_KEY
  Content-Type: application/json

Body:
{
  "from_currency": "btc",
  "to_currency": "usdttrc20",
  "amount": 0.1
}
```

**Usage :** Convertir 0.1 BTC → USDT

**Réponse (200 OK) :**
```json
{
  "id": "123456789",
  "from_currency": "btc",
  "to_currency": "usdttrc20",
  "from_amount": 0.1,
  "to_amount": 4500,
  "status": "finished",
  "created_at": "2025-01-11T10:00:00.000Z"
}
```

**Implémentation (Conversion Automatique) :**
```python
async def auto_convert_to_usdt():
    """Convertir tous les revenus crypto en USDT chaque jour"""

    client = NowPaymentsClient(settings.NOWPAYMENTS_API_KEY)

    # Récupérer le solde
    balance = client.get_balance()

    for currency, amounts in balance.items():
        # Ignorer USDT
        if currency == "usdttrc20":
            continue

        available = amounts["amount"]

        # Convertir si >= 0.001 (évite les dust)
        if available >= 0.001:
            logger.info(f"Converting {available} {currency} to USDT")

            result = client.convert_currency(
                from_currency=currency,
                to_currency="usdttrc20",
                amount=available
            )

            if result and "error" not in result:
                logger.info(f"✅ Converted {available} {currency} → {result['to_amount']} USDT")
            else:
                logger.error(f"❌ Conversion failed for {currency}")
```

---

## 6️⃣ Customer Management

### **À quoi ça sert ?**

**Objectif :** Gérer les clients et leurs paiements récurrents via la fonctionnalité **NOWPayments Custody**.

**Fonctionnalités :**
- ✅ Créer des comptes clients
- ✅ Gérer les abonnements
- ✅ Suivre l'historique de paiements
- ✅ Wallets hébergés

**⚠️ Feature Premium - Nécessite activation**

**Cas d'usage :**
- SaaS avec abonnements crypto
- Plateformes de streaming
- Services premium

---

## 7️⃣ Fiat Payouts

### **À quoi ça sert ?**

**Objectif :** Convertir des cryptos en monnaie fiat (EUR, USD, GBP) et recevoir sur compte bancaire.

**Frais :** 1.5% - 2.3% selon le montant

**Cas d'usage :**
- ✅ Payer les vendeurs en EUR/USD (plus accessible)
- ✅ Recevoir vos revenus en fiat
- ✅ Factures en monnaie légale

**⚠️ Fonctionnalité en beta (coming soon)**

---

## 8️⃣ Recurring Payments API

### **À quoi ça sert ?**

**Objectif :** Gérer les abonnements et paiements récurrents par email.

**Fonctionnalités :**
- ✅ Créer des plans d'abonnement (mensuel, annuel)
- ✅ Envoyer des factures par email
- ✅ Gérer les renouvellements automatiques
- ✅ Gérer les annulations

**Cas d'usage :**
- ✅ Abonnements mensuels à des formations
- ✅ Accès premium récurrent
- ✅ SaaS crypto payments
- ✅ Newsletters premium

---

## 9️⃣ Use Cases Pratiques

### **Use Case 1 : Marketplace de Produits Numériques (Votre Bot)**

**Flux Complet :**

```
1. VENDEUR publie un produit
   ├─ Titre, description, prix en USD
   ├─ Upload du fichier → Backblaze B2
   └─ Configure son wallet USDT pour recevoir les revenus

2. ACHETEUR achète le produit
   ├─ Sélectionne la crypto de paiement (BTC, USDT, SOL, etc.)
   ├─ Voir le montant exact en crypto (via /estimate)
   └─ Total = Prix produit + Commission plateforme (2.78%)

3. CRÉATION DU PAIEMENT
   ├─ POST /payment (SANS payout_address)
   ├─ Tous les fonds vont sur votre wallet principal
   └─ Afficher QR code + adresse au client

4. CLIENT PAIE
   ├─ Envoie les fonds vers l'adresse générée
   └─ Transaction blockchain en cours

5. IPN WEBHOOK (status: confirming)
   ├─ NOWPayments détecte le paiement
   └─ Notifier le client : "Paiement détecté !"

6. IPN WEBHOOK (status: finished)
   ├─ Paiement confirmé
   ├─ Marquer la commande comme "completed"
   ├─ Envoyer le fichier au client (depuis B2)
   └─ Notifier le vendeur de la vente

7. PAYOUT VENDEUR (hebdomadaire)
   ├─ Calculer les revenus de tous les vendeurs
   ├─ Créer un batch payout (POST /payout)
   ├─ Vérifier avec 2FA
   └─ Vendeurs reçoivent directement sur leur wallet
```

**Avantages :**
- ✅ Pas de conversion crypto2crypto (frais réduits)
- ✅ Flexibilité sur les cryptos acceptées
- ✅ Contrôle total sur les payouts
- ✅ Meilleurs taux de change (payouts groupés)

---

### **Use Case 2 : E-commerce avec Split Payment Automatique**

**Flux :**

```
1. CLIENT achète un produit du vendeur
   └─> Total = $100

2. CRÉATION PAIEMENT AVEC SPLIT
   POST /payment {
     price_amount: 100,
     pay_currency: "btc",
     payout_address: "WALLET_VENDEUR",
     payout_currency: "usdttrc20"
   }

3. CLIENT PAIE
   └─> NOWPayments reçoit $100 en BTC

4. NOWPAYMENTS DISTRIBUE AUTOMATIQUEMENT
   ├─ 90% → Wallet vendeur (en USDT)
   └─ 10% → Votre wallet (commission)

5. IPN WEBHOOK (status: finished)
   └─> Livrer le produit
```

**Avantages :**
- ✅ Distribution automatique
- ✅ Aucune intervention manuelle
- ✅ Vendeur reçoit instantanément

**Inconvénients :**
- ⚠️ Frais élevés si conversion crypto2crypto
- ⚠️ Moins de contrôle

---

### **Use Case 3 : SaaS avec Abonnements Crypto**

**Flux :**

```
1. CLIENT s'inscrit
   └─> Choisit plan mensuel ($29/mois)

2. CRÉER ABONNEMENT (Recurring Payments API)
   ├─ Plan : "Premium Monthly"
   ├─ Prix : $29
   └─ Email : client@example.com

3. CHAQUE MOIS
   ├─ NOWPayments envoie facture par email
   ├─ Client paie en crypto
   └─ Accès renouvelé automatiquement

4. ANNULATION
   └─> API pour annuler l'abonnement
```

---

### **Use Case 4 : Donations / Crowdfunding**

**Flux :**

```
1. CRÉER CAMPAGNE
   └─> Objectif : $10,000

2. DONATEUR choisit montant
   ├─ $50, $100, $500, custom
   └─> Sélectionne crypto

3. PAIEMENT
   └─> Sans ordre_id (optionnel)

4. TRACKING
   └─> Dashboard temps réel des donations
```

---

## 🔧 Configuration Complète pour Votre Bot

### **1. Variables d'environnement**
```bash
# NOWPayments
NOWPAYMENTS_API_KEY=NPM_API_KEY_abc123...
NOWPAYMENTS_IPN_SECRET=ipn_secret_xyz789...
NOWPAYMENTS_2FA_SECRET=base32_secret_key...

# URLs
IPN_CALLBACK_URL=https://votre-bot.railway.app/ipn/nowpayments
IPN_PAYOUT_URL=https://votre-bot.railway.app/ipn/payout

# Plateforme
PLATFORM_COMMISSION_PERCENT=2.78
MINIMUM_PRODUCT_PRICE_USD=10.00
```

### **2. Structure DB (PostgreSQL)**
```sql
-- Table orders
CREATE TABLE orders (
  order_id TEXT PRIMARY KEY,
  payment_id TEXT UNIQUE,
  product_id TEXT NOT NULL,
  buyer_user_id BIGINT NOT NULL,
  seller_user_id BIGINT NOT NULL,
  product_price_usd REAL NOT NULL,
  platform_commission_usd REAL NOT NULL,
  seller_revenue_usd REAL NOT NULL,
  total_amount_usd REAL NOT NULL,
  payment_currency TEXT,
  payment_address TEXT,
  payment_amount REAL,
  actually_paid REAL,
  payment_status TEXT DEFAULT 'pending',
  payment_type TEXT,  -- 'crypto' ou 'crypto2crypto'
  payment_hash TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP,
  download_count INT DEFAULT 0,
  last_download_at TIMESTAMP
);

-- Table seller_payouts
CREATE TABLE seller_payouts (
  payout_id TEXT PRIMARY KEY,
  batch_id TEXT,
  seller_user_id BIGINT NOT NULL,
  amount_usdt REAL NOT NULL,
  currency TEXT DEFAULT 'usdttrc20',
  wallet_address TEXT NOT NULL,
  status TEXT DEFAULT 'pending',
  tx_hash TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP
);
```

### **3. Cron Jobs (Automatisation)**
```python
# app/tasks/scheduled_tasks.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Payouts vendeurs hebdomadaires (chaque lundi 9h)
@scheduler.scheduled_job('cron', day_of_week='mon', hour=9)
async def weekly_seller_payouts():
    await process_weekly_seller_payouts()

# Conversion auto en USDT (chaque jour 2h)
@scheduler.scheduled_job('cron', hour=2)
async def daily_convert_to_usdt():
    await auto_convert_to_usdt()

# Vérifier les paiements expirés (chaque heure)
@scheduler.scheduled_job('interval', hours=1)
async def check_expired_payments():
    await mark_expired_payments()

scheduler.start()
```

---

## 📊 Monitoring et Analytics

### **Dashboard Admin**
```python
@router.get("/admin/analytics")
async def admin_analytics():
    """Dashboard analytics temps réel"""

    # Revenus du mois
    monthly_revenue = calculate_monthly_revenue()

    # Nombre de ventes
    sales_count = count_completed_orders(period="month")

    # Top vendeurs
    top_sellers = get_top_sellers(limit=10)

    # Cryptos les plus utilisées
    crypto_stats = get_crypto_usage_stats()

    # Frais moyens par transaction
    avg_fees = calculate_average_fees()

    return {
        "revenue": {
            "total": monthly_revenue,
            "sales_count": sales_count,
            "avg_per_sale": monthly_revenue / sales_count if sales_count > 0 else 0
        },
        "top_sellers": top_sellers,
        "crypto_stats": crypto_stats,
        "avg_fees": avg_fees
    }
```

---

## 🔐 Sécurité

### **Checklist Complète**

- ✅ **API Key** : Ne JAMAIS exposer en frontend
- ✅ **IPN Secret** : Toujours vérifier la signature HMAC
- ✅ **HTTPS** : Obligatoire pour IPN callback
- ✅ **Whitelist IPs** : Pour les payouts (contacter support)
- ✅ **2FA** : Obligatoire pour les payouts
- ✅ **Rate Limiting** : Sur vos endpoints publics
- ✅ **Logs** : Tout logger (IPN, payments, errors)
- ✅ **Monitoring** : Alertes si API down
- ✅ **Backups** : DB réguliers

---

## 📞 Support NOWPayments

**Email :** partners@nowpayments.io
**Documentation :** https://documenter.getpostman.com/view/7907941/
**Dashboard :** https://nowpayments.io/
**Status Page :** https://status.nowpayments.io/

---

**Date :** 11 novembre 2025
**Auteur :** Claude Code
**Version :** 2.0 (Complète)
