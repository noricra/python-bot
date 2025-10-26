# 🎯 ROADMAP VERS 100% FONCTIONNEL - BOT MARKETPLACE FERUS

**Date:** 26 octobre 2025
**Status actuel:** 75% fonctionnel
**Objectif:** Atteindre 100% production-ready

---

## 📊 ÉTAT ACTUEL

### ✅ CE QUI EST FAIT (75%)

| Composant | Complétude | Status |
|-----------|-----------|--------|
| Paiements crypto NowPayments | 100% | ✅ Production-ready |
| Carousel produits visuel | 100% | ✅ Production-ready |
| **Badges automatiques** | 100% | ✅ **ACTIVÉ AUJOURD'HUI** |
| **Chemins images absolus** | 100% | ✅ **FIXÉ AUJOURD'HUI** |
| Reviews/Ratings système | 100% | ✅ Production-ready |
| Bibliothèque utilisateur | 100% | ✅ Production-ready |
| Gestion produits vendeur | 90% | ⚠️ Édition limitée |
| Images produits | 95% | ✅ Upload + thumbnails OK |
| Architecture code | 100% | ✅ Propre et modulaire |

### ❌ CE QUI MANQUE (25%)

| Composant | Complétude | Impact |
|-----------|-----------|--------|
| **Notifications critiques** | 30% | 🔴 Critique |
| Recherche textuelle | 0% | 🔴 Critique |
| Filtres produits | 0% | 🟠 Important |
| Preview fichiers complet | 50% | 🟡 Moyen |
| Social proof temps réel | 0% | 🟡 Moyen |
| Reviews avec photos | 0% | 🟢 Nice to have |
| Analytics complet | 40% | 🟡 Moyen |

---

## 🔴 SPRINT 1 - NOTIFICATIONS CRITIQUES (2-3 heures)

**Objectif:** Tous les workflows ont des notifications

### Tâche 1.1: Notification Admin - Nouveau Ticket (15 min)

**Problème:** Admin ne voit pas les tickets support
**Fichier:** `app/integrations/telegram/handlers/support_handlers.py`
**Ligne:** Ajouter après 323

**Code à ajouter:**
```python
# Après: ticket_id = self.support_service.create_ticket(...)
if ticket_id:
    # Notification admin
    try:
        from app.core import settings as core_settings
        if core_settings.ADMIN_USER_ID:
            admin_text = f"""
🎫 **NOUVEAU TICKET SUPPORT**

🆔 Ticket: `{ticket_id}`
👤 Client: {user_name} (ID: {user_id})
📋 Sujet: {subject}

💬 {message_text[:200]}...
"""
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("👁️ Voir", callback_data=f'view_ticket_{ticket_id}'),
                InlineKeyboardButton("↩️ Répondre", callback_data=f'admin_reply_ticket_{ticket_id}')
            ]])

            await bot.application.bot.send_message(
                chat_id=core_settings.ADMIN_USER_ID,
                text=admin_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(f"Failed to notify admin: {e}")
```

---

### Tâche 1.2: Notification Client - Réponse Admin (10 min)

**Problème:** Client ne sait pas que l'admin a répondu
**Fichier:** `app/integrations/telegram/handlers/support_handlers.py`
**Ligne:** Ajouter après 156

**Code à ajouter:**
```python
# Après: ok = MessagingService(...).post_admin_message(...)
if ok:
    try:
        ticket = support_service.get_ticket(ticket_id)
        client_user_id = ticket['user_id']

        client_text = f"""
💬 **RÉPONSE À VOTRE TICKET**

🎫 Ticket: `{ticket_id}`

**Support:**
{msg[:200]}...
"""
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("👁️ Voir", callback_data=f'view_ticket_{ticket_id}'),
            InlineKeyboardButton("↩️ Répondre", callback_data=f'reply_ticket_{ticket_id}')
        ]])

        await bot.application.bot.send_message(
            chat_id=client_user_id,
            text=client_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Failed to notify client: {e}")
```

---

### Tâche 1.3: Notification Vendeur - Payout Effectué (20 min)

**Problème:** Vendeur ne sait pas qu'il a été payé
**Fichier:** `app/integrations/telegram/handlers/admin_handlers.py`
**Ligne:** Modifier 383-392

**Code à modifier:**
```python
async def admin_mark_all_payouts_paid(self, query, lang):
    try:
        # Récupérer détails AVANT de marquer comme payé
        pending = self.payout_service.repo.get_pending_payouts()

        count = self.payout_service.mark_all_payouts_paid()

        # Notifier chaque vendeur
        for payout in pending:
            try:
                seller_user_id = payout['user_id']
                amount = payout['amount']

                # Récupérer telegram_id
                conn = bot.get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT telegram_id FROM telegram_mappings
                    WHERE seller_user_id = ? AND is_active = 1
                    LIMIT 1
                ''', (seller_user_id,))
                result = cursor.fetchone()
                conn.close()

                if result:
                    telegram_id = result[0]
                    seller_text = f"""
💰 **PAIEMENT EFFECTUÉ !**

💵 Montant: {amount:.4f} SOL
📅 Date: {datetime.now().strftime('%d/%m/%Y à %H:%M')}

💡 Fonds envoyés à votre wallet Solana.
"""
                    await bot.application.bot.send_message(
                        chat_id=telegram_id,
                        text=seller_text,
                        parse_mode='Markdown'
                    )
            except Exception as e:
                logger.error(f"Failed to notify seller: {e}")

        await query.edit_message_text(
            f"✅ {count} payouts payés\n📨 Vendeurs notifiés"
        )
    except Exception as e:
        await query.edit_message_text(f"❌ Erreur: {e}")
```

---

### Tâche 1.4: Emails SMTP Vendeur (1 heure)

**Fichier:** `app/services/smtp_service.py`

**A. Email nouvelle commande:**
```python
def send_order_notification_email(self, email: str, seller_name: str,
                                  product_title: str, amount_eur: float,
                                  buyer_name: str) -> bool:
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🎉 Nouvelle vente - {product_title}"
        msg['From'] = self.from_email
        msg['To'] = email

        html_content = f"""
        <html><body>
            <h1>🎉 NOUVELLE VENTE !</h1>
            <p>Bonjour {seller_name},</p>
            <ul>
                <li><strong>Produit :</strong> {product_title}</li>
                <li><strong>Montant :</strong> {amount_eur}€</li>
                <li><strong>Acheteur :</strong> {buyer_name}</li>
            </ul>
        </body></html>
        """

        msg.attach(MIMEText(html_content, 'html'))

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)

        return True
    except Exception as e:
        logger.error(f"Failed to send order email: {e}")
        return False
```

**B. Appeler dans:** `buy_handlers.py:1575`
```python
# Après notification Telegram
try:
    seller_data = self.user_repo.get_user(product['seller_user_id'])
    if seller_data and seller_data.get('email'):
        from app.services.smtp_service import SMTPService
        smtp = SMTPService()
        smtp.send_order_notification_email(
            email=seller_data['email'],
            seller_name=seller_data.get('seller_name', 'Vendeur'),
            product_title=product['title'],
            amount_eur=product['price_eur'],
            buyer_name=query.from_user.first_name
        )
except Exception as e:
    logger.error(f"Failed to send email: {e}")
```

**C. Email paiement confirmé:** (même pattern, appeler dans `buy_handlers.py:1298`)

---

## 🔴 SPRINT 2 - RECHERCHE & FILTRES (4-5 heures)

**Objectif:** Navigation marketplace moderne

### Tâche 2.1: Recherche Textuelle (2 heures)

**Fichier:** `app/domain/repositories/product_repo.py`

**A. Ajouter méthode:**
```python
def search_products(self, query: str, limit: int = 10) -> List[Dict]:
    """Recherche full-text dans titre + description"""
    conn = get_sqlite_connection(self.database_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        search_pattern = f'%{query}%'
        cursor.execute('''
            SELECT p.*,
                   COUNT(DISTINCT o.order_id) as sales_count,
                   COALESCE(AVG(r.rating), 0.0) as rating
            FROM products p
            LEFT JOIN orders o ON o.product_id = p.product_id AND o.payment_status = 'completed'
            LEFT JOIN reviews r ON r.product_id = p.product_id
            WHERE (p.title LIKE ? OR p.description LIKE ?)
              AND p.status = 'active'
            GROUP BY p.product_id
            ORDER BY sales_count DESC
            LIMIT ?
        ''', (search_pattern, search_pattern, limit))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Search error: {e}")
        return []
    finally:
        conn.close()
```

**B. Handler dans:** `app/integrations/telegram/handlers/buy_handlers.py`

```python
async def handle_search_query(self, bot, update, query_text: str):
    """Gère la recherche textuelle"""
    user_id = update.effective_user.id
    lang = bot.get_user_state(user_id).get('lang', 'fr')

    results = self.product_repo.search_products(query_text, limit=10)

    if not results:
        await update.message.reply_text(
            f"🔍 Aucun résultat pour: **{query_text}**\n\n"
            "Essayez des mots-clés plus courts ou parcourez les catégories.",
            parse_mode='Markdown'
        )
        return

    # Afficher en carousel
    await self.show_search_carousel(bot, update, results, index=0, lang=lang)

async def show_search_carousel(self, bot, update, results, index, lang):
    """Carousel pour résultats recherche"""
    # Même logique que show_carousel_navigation
    # Remplacer context 'carousel' par 'search'
    # ... (code carousel standard)
```

**C. Ajouter dans callback_router:**
```python
# Dans process_text_message()
if not user_state.get('waiting_for_...'):
    # Traiter comme recherche
    await buy_handlers.handle_search_query(bot, update, message_text)
```

---

### Tâche 2.2: Filtres Prix + Rating (2 heures)

**A. Interface boutons dans:** `buy_handlers.py`

```python
async def show_filter_menu(self, bot, query, category_key, lang):
    """Menu de filtres"""
    filter_text = "🎛️ **Filtres**" if lang == 'fr' else "🎛️ **Filters**"

    keyboard = [
        # Filtres prix
        [InlineKeyboardButton("💰 Prix", callback_data=f'filter_menu_price_{category_key}')],
        # Sous-menu prix
        [
            InlineKeyboardButton("0-50€", callback_data=f'filter_price_0_50_{category_key}'),
            InlineKeyboardButton("50-100€", callback_data=f'filter_price_50_100_{category_key}')
        ],
        [
            InlineKeyboardButton("100-200€", callback_data=f'filter_price_100_200_{category_key}'),
            InlineKeyboardButton("200+€", callback_data=f'filter_price_200_plus_{category_key}')
        ],

        # Filtres rating
        [InlineKeyboardButton("⭐ Note", callback_data=f'filter_menu_rating_{category_key}')],
        [
            InlineKeyboardButton("4+ ⭐", callback_data=f'filter_rating_4_{category_key}'),
            InlineKeyboardButton("3+ ⭐", callback_data=f'filter_rating_3_{category_key}')
        ],

        # Tri
        [InlineKeyboardButton("🔥 Populaires", callback_data=f'sort_sales_{category_key}')],
        [InlineKeyboardButton("🆕 Nouveautés", callback_data=f'sort_date_{category_key}')],

        # Reset + Retour
        [
            InlineKeyboardButton("🔄 Reset", callback_data=f'filter_reset_{category_key}'),
            InlineKeyboardButton("🔙 Retour", callback_data=f'browse_category_{category_key}')
        ]
    ]

    await query.edit_message_text(
        filter_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
```

**B. Méthode repository avec filtres:**

```python
def get_products_filtered(self, category: str, filters: Dict = None) -> List[Dict]:
    """Récupère produits avec filtres"""
    conn = get_sqlite_connection(self.database_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        query = "SELECT * FROM products WHERE category = ? AND status = 'active'"
        params = [category]

        # Filtre prix
        if filters and 'price_min' in filters:
            query += " AND price_eur >= ?"
            params.append(filters['price_min'])
        if filters and 'price_max' in filters:
            query += " AND price_eur <= ?"
            params.append(filters['price_max'])

        # Filtre rating
        if filters and 'min_rating' in filters:
            query += " AND rating >= ?"
            params.append(filters['min_rating'])

        # Tri
        sort = filters.get('sort', 'created_at') if filters else 'created_at'
        if sort == 'sales':
            query += " ORDER BY sales_count DESC"
        elif sort == 'date':
            query += " ORDER BY created_at DESC"
        else:
            query += " ORDER BY created_at DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
```

---

## 🟡 SPRINT 3 - PREVIEW & SOCIAL PROOF (3-4 heures)

### Tâche 3.1: Preview PDF 3 Pages (1 heure)

**Fichier:** `buy_handlers.py:1618-1643`

**Modifier:**
```python
# Au lieu de page 0 seulement
preview_images = []
for page_num in range(min(3, doc.page_count)):
    page = doc.load_page(page_num)
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    preview_images.append(pix.tobytes('png'))

# Envoyer media group
media_group = [
    InputMediaPhoto(BytesIO(img), caption=f"📄 Page {i+1}/3")
    for i, img in enumerate(preview_images)
]

await bot.send_media_group(
    chat_id=query.message.chat_id,
    media=media_group
)
```

---

### Tâche 3.2: Preview Vidéo 30 Secondes (1 heure)

**Modifier preview vidéo:**
```python
import ffmpeg

# Au lieu de thumbnail seulement
preview_path = f"/tmp/preview_{product['product_id']}.mp4"

# Extraire 30 premières secondes
ffmpeg.input(video_path, ss=0, t=30).output(
    preview_path,
    vcodec='libx264',
    preset='fast'
).run()

await bot.send_video(
    chat_id=query.message.chat_id,
    video=open(preview_path, 'rb'),
    caption="🎬 Aperçu 30 secondes"
)
```

---

### Tâche 3.3: Social Proof Temps Réel (2 heures)

**A. Créer table:**
```sql
CREATE TABLE product_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    action TEXT NOT NULL,  -- 'view', 'purchase'
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE INDEX idx_activity_product_time ON product_activity(product_id, timestamp);
```

**B. Logger activité:**
```python
# Dans increment_views()
def log_product_activity(product_id: str, user_id: int, action: str):
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO product_activity (product_id, user_id, action)
        VALUES (?, ?, ?)
    ''', (product_id, user_id, action))
    conn.commit()
    conn.close()
```

**C. Afficher dans caption:**
```python
# Dans _build_product_caption mode='full'
recent_purchases = get_recent_activity(product_id, 'purchase', hours=24)
if recent_purchases:
    caption += f"\n💬 {len(recent_purchases)} achats récents (24h)"
```

---

## 🟢 SPRINT 4 - NICE TO HAVE (optionnel)

### Tâche 4.1: Reviews avec Photos (3 heures)

**A. ALTER TABLE:**
```sql
ALTER TABLE reviews ADD COLUMN photo_path TEXT;
```

**B. Flow upload photo review:**
1. Rating → Texte → "📸 Ajouter photo (optionnel)"
2. Upload → Stockage `/data/reviews/{product_id}/{user_id}.jpg`
3. Affichage liste reviews avec `send_photo()`

---

### Tâche 4.2: Analytics Complet Vendeur (4 heures)

- Dashboard graphiques (revenus, top produits, conversion)
- Export CSV/PDF
- Insights IA (suggestions, tendances)

---

## 📊 PLANNING RECOMMANDÉ

### **Semaine 1: Notifications + Recherche**
- ✅ Sprint 1: Notifications (2-3h)
- ✅ Sprint 2: Recherche + Filtres (4-5h)
- **Résultat:** Bot 90% fonctionnel

### **Semaine 2: Preview + Social Proof**
- ✅ Sprint 3: Preview améliorer + Social proof (3-4h)
- **Résultat:** Bot 95% fonctionnel

### **Semaine 3: Polish (optionnel)**
- ✅ Sprint 4: Reviews photos + Analytics (7-8h)
- **Résultat:** Bot 100% complet selon CLAUDE.md

---

## ✅ CHECKLIST PRODUCTION

### Critique (bloquant)
- [ ] Notifications admin ticket support
- [ ] Notifications client réponse admin
- [ ] Notifications vendeur payout
- [ ] Recherche textuelle produits
- [ ] Emails SMTP vendeur (backup)

### Important (améliore UX)
- [ ] Filtres prix + rating
- [ ] Preview PDF 3 pages
- [ ] Preview vidéo 30s
- [ ] Social proof temps réel

### Nice to have
- [ ] Reviews avec photos
- [ ] Analytics vendeur complet
- [ ] Export CSV/PDF

---

## 🎯 RÉSUMÉ

**Temps total pour 100%:** 15-20 heures
**Temps pour 90% (production):** 6-8 heures
**Temps pour 95% (excellent):** 10-12 heures

**Recommandation:** Commencer par Sprint 1 + 2 (6-8h) pour avoir un bot production-ready à 90%.

---

## 📁 FICHIERS CRÉÉS AUJOURD'HUI

1. ✅ `EXEMPLE_RENDU_BADGES.md` - Documentation badges
2. ✅ `test_badges.py` - Script test badges
3. ✅ `test_image_paths.py` - Script test chemins
4. ✅ `RAPPORT_NOTIFICATIONS.md` - Analyse notifications
5. ✅ `TODO_100_PERCENT.md` - Ce fichier

## 🚀 NEXT STEPS

**Choix 1:** Implémenter Sprint 1 (notifications) → 2-3h
**Choix 2:** Implémenter Sprint 2 (recherche/filtres) → 4-5h
**Choix 3:** Tester le bot actuel avec badges + images fixés

**Quelle est votre priorité ?**
