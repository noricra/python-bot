# Configuration URL IPN NOWPayments - Guide Complet

## Problème Identifié

**URL IPN incorrecte détectée :**
- ❌ **Placeholder** : `https://votre-app.railway.app/ipn/nowpayments`
- ✅ **URL correcte** : `https://python-bot-production-312a.up.railway.app/ipn/nowpayments`

**Impact :** Sans l'URL correcte, NOWPayments ne peut pas envoyer les notifications de paiement à votre bot, ce qui signifie :
- Les commandes ne seront jamais marquées comme "payées"
- Les fichiers ne seront jamais livrés aux acheteurs
- Les vendeurs ne recevront jamais de notification de paiement confirmé

---

## 1. Mise à Jour Dashboard NOWPayments

### Étape 1 : Connexion
1. Allez sur [nowpayments.io](https://nowpayments.io)
2. Connectez-vous à votre compte

### Étape 2 : Configuration IPN
1. **Navigation** : Settings → Payment Settings
2. **Activez IPN** : Cochez "Enable IPN (Instant Payment Notifications)"
3. **IPN Secret Key** : Vérifiez que votre IPN Secret est configuré (doit correspondre à votre `.env`)
4. **IPN Callback URL** :
   ```
   https://python-bot-production-312a.up.railway.app/ipn/nowpayments
   ```
5. **Sauvegardez** les modifications

### Schéma visuel
```
NOWPayments Dashboard
├── Settings
│   └── Payment Settings
│       ├── [✓] Enable IPN
│       ├── IPN Secret: ●●●●●●●●●●●●●●●●
│       └── IPN Callback URL: https://python-bot-production-312a.up.railway.app/ipn/nowpayments
│       └── [SAVE SETTINGS]
```

---

## 2. Vérification Variables d'Environnement Railway

### Étape 1 : Ouvrir Railway Dashboard
1. Allez sur [railway.app](https://railway.app)
2. Ouvrez votre projet : **python-bot-production-312a**

### Étape 2 : Vérifier Variables
1. Cliquez sur votre service (le bot)
2. Allez dans l'onglet **Variables**
3. Vérifiez que ces variables existent et sont correctes :

```bash
# Variables critiques à vérifier
NOWPAYMENTS_API_KEY=<votre-clé-api>
NOWPAYMENTS_IPN_SECRET=<votre-secret-ipn>
IPN_CALLBACK_URL=https://python-bot-production-312a.up.railway.app/ipn/nowpayments
```

### Étape 3 : Ajouter/Modifier si Nécessaire
Si `IPN_CALLBACK_URL` n'existe pas ou est incorrecte :
1. Cliquez sur **+ New Variable**
2. **Name** : `IPN_CALLBACK_URL`
3. **Value** : `https://python-bot-production-312a.up.railway.app/ipn/nowpayments`
4. Cliquez **Add**

**IMPORTANT** : Railway redémarrera automatiquement le bot après modification des variables.

---

## 3. Vérification Endpoint IPN

### Test 1 : Vérifier que l'endpoint répond

**Commande** :
```bash
curl https://python-bot-production-312a.up.railway.app/health
```

**Réponse attendue** :
```json
{
  "status": "ok",
  "service": "ipn_server",
  "timestamp": "2025-11-11T..."
}
```

Si l'endpoint `/health` répond, alors `/ipn/nowpayments` est aussi disponible.

### Test 2 : Vérifier dans Railway Logs

1. Railway Dashboard → Votre service → **Deployments**
2. Cliquez sur le déploiement actif
3. Onglet **Logs**
4. Cherchez ces lignes au démarrage :

```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

Si vous voyez ces logs, le serveur IPN est opérationnel.

---

## 4. Test Complet du Flow IPN

### Test avec Transaction Réelle (Recommandé)

1. **Créer un produit de test** :
   - Prix : $5 (minimum)
   - Titre : "Test IPN"

2. **Faire un achat de test** :
   - Utilisez un petit montant (ex: $5)
   - Payez avec une crypto que vous possédez déjà

3. **Surveiller les logs Railway** en temps réel :
   ```bash
   # Dans Railway Dashboard → Logs, vous devriez voir :

   ✅ IPN received: payment_id=...
   ✅ Signature verified
   ✅ Payment status: finished
   ✅ Order updated: order_id=...
   ✅ File delivered to buyer
   ✅ Seller notification sent
   ```

4. **Vérifications** :
   - ✅ L'acheteur reçoit le fichier via Telegram
   - ✅ Le vendeur reçoit la notification "PAIEMENT CONFIRMÉ"
   - ✅ La commande est marquée comme "completed" dans la DB
   - ✅ Le statut dans library est "completed"

---

## 5. Résolution de Problèmes

### Problème : IPN ne reçoit rien

**Causes possibles :**
1. ❌ URL IPN mal configurée dans NOWPayments
2. ❌ Serveur IPN non démarré sur Railway
3. ❌ Firewall Railway bloque les requêtes

**Solutions :**
```bash
# 1. Vérifier que le serveur IPN tourne
curl https://python-bot-production-312a.up.railway.app/health

# 2. Vérifier les logs Railway
# Cherchez "Uvicorn running" dans les logs

# 3. Vérifier la configuration NOWPayments
# Dashboard → Settings → Payment Settings → IPN Callback URL
```

### Problème : Signature IPN invalide

**Cause :** `NOWPAYMENTS_IPN_SECRET` ne correspond pas entre `.env` et NOWPayments dashboard

**Solution :**
1. Dashboard NOWPayments → Settings → IPN Secret Key
2. Copiez le secret
3. Railway → Variables → `NOWPAYMENTS_IPN_SECRET`
4. Remplacez par le secret copié
5. Attendez le redémarrage automatique

### Problème : IPN reçu mais commande non mise à jour

**Vérifier dans les logs Railway :**
```bash
# Cherchez ces erreurs :
❌ Database connection failed
❌ Order not found
❌ Seller notification failed
```

**Solutions :**
- Vérifiez la connexion PostgreSQL (variables `PGHOST`, `PGUSER`, `PGPASSWORD`)
- Vérifiez que la commande existe dans la DB avec `order_id` correspondant

---

## 6. Checklist Finale

Avant de considérer la configuration comme terminée :

### NOWPayments Dashboard
- [ ] IPN activé
- [ ] IPN Secret configuré
- [ ] IPN Callback URL = `https://python-bot-production-312a.up.railway.app/ipn/nowpayments`
- [ ] Configuration sauvegardée

### Railway
- [ ] Variable `IPN_CALLBACK_URL` existe et est correcte
- [ ] Variable `NOWPAYMENTS_IPN_SECRET` correspond au dashboard
- [ ] Variable `NOWPAYMENTS_API_KEY` configurée
- [ ] Bot déployé et en cours d'exécution
- [ ] Logs montrent "Uvicorn running"

### Tests
- [ ] Endpoint `/health` répond avec status "ok"
- [ ] Transaction de test effectuée ($5 minimum)
- [ ] IPN reçu dans les logs Railway
- [ ] Signature IPN vérifiée avec succès
- [ ] Fichier livré à l'acheteur
- [ ] Notification vendeur envoyée
- [ ] Commande marquée "completed" en DB

---

## 7. URLs de Référence

**Dashboard NOWPayments :**
- Production : https://nowpayments.io/
- Documentation : https://documenter.getpostman.com/view/7907941/

**Railway Dashboard :**
- Projet : https://railway.app/project/python-bot-production-312a

**Endpoints Bot :**
- Health : `https://python-bot-production-312a.up.railway.app/health`
- IPN : `https://python-bot-production-312a.up.railway.app/ipn/nowpayments`

---

## 8. Support

**En cas de problème persistant :**

1. **Vérifier logs Railway** :
   - Railway Dashboard → Deployments → Logs
   - Cherchez les erreurs liées à "ipn", "payment", "nowpayments"

2. **Support NOWPayments** :
   - Email : support@nowpayments.io
   - Chat : Disponible sur le dashboard

3. **Tester manuellement l'IPN** :
   ```bash
   # Simuler un IPN (ATTENTION : utiliser le bon secret)
   curl -X POST https://python-bot-production-312a.up.railway.app/ipn/nowpayments \
     -H "Content-Type: application/json" \
     -H "x-nowpayments-sig: <signature-hmac>" \
     -d '{"payment_id":"test","payment_status":"finished",...}'
   ```

---

**Dernière mise à jour** : 11 novembre 2025
**Version** : 1.0
