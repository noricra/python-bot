# Telegram Cryptocurrency Marketplace Platform

**Live at: [UZEUR.COM](https://uzeur.com)**

## Mission

Enable content creators to sell their digital products at scale, fully automated. By sharing their shop link or product link, customers can pay with multiple cryptocurrencies (BTC, ETH, SOL, USDT, USDC) while sellers receive their revenue in cryptocurrency via manual payouts.

The project was designed, modeled, coded, and optimized to improve user experience and significantly reduce the number of clicks before purchase.

**Production-grade e-commerce platform built entirely on Telegram.** Handles cryptocurrency payments, file storage up to 10GB, manual seller payouts, and complete marketplace operations without external websites.

**Scale:** 65 Python modules • 35 dependencies • 9 database tables

**Stack:** Python 3.11 • FastAPI • PostgreSQL 15 • Cloudflare R2

---

## System Overview

A complete decentralized marketplace where sellers upload digital products (courses, ebooks, software, templates) and buyers pay with cryptocurrency (BTC, ETH, SOL, USDT, USDC on Solana). All interactions happen within Telegram using bot commands and embedded mini-apps (WebView).

**Key Achievements:**
- Direct browser-to-cloud uploads (10GB files) bypassing server RAM constraints
- True streaming downloads with one-time tokens and rate limiting
- Automated cryptocurrency payment processing with IPN callbacks
- Manual seller payout system with 24-hour escrow period
- Web scraping for bulk product imports from Gumroad
- Multi-language support (i18n)
- Real-time analytics with chart generation

---

### Core Components

**Backend (Python 3.11)**
- `app/main.py` - Entry point 
- `bot_mlt.py` - MarketplaceBot class 
- `app/integrations/ipn_server.py` - FastAPI server (16 endpoints)

**Infrastructure (20 modules)**
- Connection pooling (`db_pool.py`)
- Multi-language support (`i18n.py`)
- Email service (`email_service.py` - Mailjet API port 443)
- File operations (`file_utils.py`, `file_validation.py`)
- Rate limiting (`rate_limiter.py`)
- Image processing (`image_utils.py`)
- State management (`state_manager.py`)

**Business Logic (13 services)**
- Payment processing (`payment_service.py` - NowPayments)
- Cloud storage (`b2_storage_service.py` - R2/B2, S3-compatible)
- Web scraping (`gumroad_scraper.py` - BeautifulSoup4)
- Analytics charts (`chart_service.py` - matplotlib)
- Seller payouts (`seller_payout_service.py`)
- Image sync (`image_sync_service.py` - smart caching)

**Data Access (9 repositories)**
- Products, Orders, Users, Payouts, Reviews, Tickets, Downloads, Messaging

**Telegram Integration**
- 10 handlers (buy, sell, library, import, support, admin, analytics, auth, core)
- 7 mini-app files (upload.html/js, download.html/js, import.html/js, styles.css)
- Callback routing, inline keyboards, carousel helpers

---

## Core Features

| Component | Buyer | Seller | Admin |
|-----------|-------|--------|-------|
| **Products** | Browse 11 categories, search, filters | Upload 10GB files via mini-app, Gumroad import | Moderation dashboard |
| **Payments** | 5 cryptos (BTC/ETH/SOL/USDT/USDC), instant delivery | Email alerts, analytics charts | Manual payout processing |
| **Library** | Unlimited re-downloads, download tracking | Product management (edit, soft delete) | Support ticket system |
| **Support** | Built-in tickets | Performance metrics (views, conversion) | Platform-wide analytics |
| **Languages** | i18n support | i18n support | Database backup/restore |

---

## Technology Stack

**Backend:** Python 3.11.9 (async/await) • FastAPI 0.115.0+ • Uvicorn • Pydantic

**Database:** PostgreSQL 15 • psycopg2 (connection pooling) • 9 tables • Triggers • 5 migrations

**Telegram:** python-telegram-bot 21.0 • Webhook mode • Mini-Apps (WebView) • Inline keyboards

**Payments:** NowPayments API • HMAC-SHA512 IPN • 5 cryptocurrencies • Manual payouts

**Storage:** Cloudflare R2 (primary) • Backblaze B2 (fallback) • boto3 • Presigned URLs • Zero egress fees

**Email:** Mailjet API via HTTPS (port 443) • Bypasses Railway SMTP blocks • Async queue

**Web Scraping:** BeautifulSoup4 • httpx (async) • User-agent rotation • Rate limiting

**Data Processing:** Pillow (images) • matplotlib (charts) • qrcode (payments) • pandas (export)


---

## Project Structure

```
Python-bot/
├── app/
│   ├── main.py                           # Entry point 
│   │
│   ├── core/                             # Infrastructure (20 modules)
│   │   ├── __init__.py
│   │   ├── database_init.py              # PostgreSQL schema + migrations
│   │   ├── db_pool.py                    # Connection pooling (max 20)
│   │   ├── db.py                         # Legacy connection (deprecated)
│   │   ├── settings.py                   # Environment configuration
│   │   ├── i18n.py                       # Multi-language support
│   │   ├── email_service.py              # Mailjet API email sender
│   │   ├── file_utils.py                 # File operations
│   │   ├── file_validation.py            # Security validation (file types)
│   │   ├── rate_limiter.py               # API rate limiting
│   │   ├── seller_notifications.py       # Email queue for sellers
│   │   ├── state_manager.py              # Conversation state storage
│   │   ├── image_utils.py                # Image processing (Pillow)
│   │   ├── error_messages.py             # Centralized error messages
│   │   ├── validation.py                 # Input validation
│   │   ├── logging.py                    # Structured logging config
│   │   ├── middleware.py                 # HTTP middleware
│   │   ├── db_helpers.py                 # Database utilities
│   │   ├── user_utils.py                 # User helper functions
│   │   └── utils.py                      # General utilities
│   │
│   ├── domain/repositories/              # Data Access Layer (9 modules)
│   │   ├── __init__.py
│   │   ├── product_repo.py               # Products CRUD + search
│   │   ├── order_repo.py                 # Orders + payment tracking
│   │   ├── user_repo.py                  # Users + seller profiles
│   │   ├── payout_repo.py                # Payouts + escrow logic
│   │   ├── review_repo.py                # Reviews + rating aggregation
│   │   ├── ticket_repo.py                # Support tickets CRUD
│   │   ├── download_repo.py              # Download tokens + rate limits
│   │   └── messaging_repo.py             # Internal messaging
│   │
│   ├── services/                         # Business Logic (13 modules)
│   │   ├── payment_service.py            # NowPayments integration
│   │   ├── b2_storage_service.py         # R2/B2 operations (R2 priority)
│   │   ├── gumroad_scraper.py            # Gumroad product scraper
│   │   ├── seller_service.py             # Seller account management
│   │   ├── payout_service.py             # Payout calculations
│   │   ├── seller_payout_service.py      # Manual payout processing
│   │   ├── support_service.py            # Support ticket logic
│   │   ├── chart_service.py              # Analytics chart generation
│   │   ├── export_service.py             # CSV/JSON data export
│   │   ├── product_service.py            # Product business logic
│   │   ├── messaging_service.py          # Messaging system
│   │   ├── telegram_cache_service.py     # Telegram file caching
│   │   └── image_sync_service.py         # Image synchronization
│   │
│   ├── integrations/
│   │   ├── ipn_server.py                 # FastAPI server 
│   │   ├── nowpayments_client.py         # Payment API client
│   │   │
│   │   └── telegram/
│   │       ├── app_builder.py            # Bot initialization
│   │       ├── callback_router.py        # Callback query routing
│   │       ├── keyboards.py              # Inline keyboard builders
│   │       │
│   │       ├── handlers/                 # Business Handlers (10 modules)
│   │       │   ├── buy_handlers.py       # Purchase flow 
│   │       │   ├── sell_handlers.py      # Product creation
│   │       │   ├── library_handlers.py   # User library
│   │       │   ├── import_handlers.py    # Gumroad import
│   │       │   ├── support_handlers.py   # Support tickets
│   │       │   ├── admin_handlers.py     # Admin panel
│   │       │   ├── analytics_handlers.py # Basic analytics
│   │       │   ├── seller_analytics_enhanced.py  # Advanced charts
│   │       │   ├── auth_handlers.py      # Authentication
│   │       │   └── core_handlers.py      # Core commands (/start, /help)
│   │       │
│   │       ├── utils/                    # Telegram Utilities (3 modules)
│   │       │   ├── __init__.py
│   │       │   ├── carousel_helper.py    # Product carousel pagination
│   │       │   └── message_utils.py      # Message formatting
│   │       │
│   │       └── static/                   # Mini-Apps Frontend (7 files)
│   │           ├── upload.html           # Product upload interface
│   │           ├── upload.js             # Upload logic 
│   │           ├── download.html         # File download interface
│   │           ├── download.js           # Download logic 
│   │           ├── import.html           # Gumroad import wizard
│   │           ├── import.js             # Import logic 
│   │           └── styles.css            # Shared styles
│   │
│   └── tasks/                            # Background Jobs (4 modules)
│       ├── backup_database.py            # Database backup
│       ├── cleanup_deleted_products.py   # Soft delete cleanup
│       ├── restore_database.py           # Database restore
│       └── retry_undelivered_files.py    # Failed delivery retry
│
├── bot_mlt.py                            # MarketplaceBot main class 
│
├── requirements.txt                      # 35 Python dependencies
├── .env                                  # Environment variables 
└──  README.md                             # This file
                            

Total: 65 files, 27,230 lines of code
```


---

## Technical Optimizations

Production-grade optimizations implemented to overcome platform constraints and maximize performance:

### 1. Railway SMTP Bypass - Email via API (Port 443)
**Problem:** Railway blocks SMTP ports (25, 587, 465)
**Solution:** Mailjet API over HTTPS (port 443 - never blocked)
- File: `app/core/email_service.py`
- Uses HTTP POST instead of SMTP protocol
- 100% async to avoid blocking event loop
- Template engine with professional HTML emails

### 2. Image Sync with Smart Caching
**Problem:** Railway ephemeral storage - files lost on restart
**Solution:** Check local first, auto-download from R2 if missing
- File: `app/services/image_sync_service.py`
- Method: `get_image_path_with_fallback()`
- Checks local storage (instant if exists)
- Downloads from R2 on cache miss
- Zero downtime, transparent to user

### 3. Client-Side PDF Preview Generation
**Problem:** Server-side PDF rendering consumes 100MB+ RAM per file
**Solution:** Generate preview in browser using PDF.js
- File: `app/integrations/telegram/static/upload.js`
- Function: `generatePDFPreview()`
- Renders first page of PDF to PNG in browser
- Uploads preview to R2 (no server processing)
- Saves 90% server RAM usage

### 4. Direct Browser-to-Cloud Uploads
**Problem:** 10GB file upload through 0.5GB RAM server = crash
**Solution:** S3 presigned URLs for direct upload
- File: `app/services/b2_storage_service.py`
- Method: `generate_presigned_upload_url()`
- Browser uploads DIRECTLY to R2 (bypasses Railway)
- Server only generates signed URL (50KB request)
- Supports files up to 10GB without consuming server RAM

### 5. PostgreSQL Connection Pooling
**Problem:** Each request creates new DB connection = "too many connections" error
**Solution:** Singleton connection pool (2-10 persistent connections)
- File: `app/core/db_pool.py`
- ThreadedConnectionPool (psycopg2)
- Reuses connections across requests
- Handles 500+ concurrent users with 10 connections
- Automatic cleanup on shutdown

### 6. Telegram file_id Caching
**Problem:** Re-uploading same image to Telegram API repeatedly
**Solution:** Cache Telegram file_id in database
- Migration: `migrations/004_add_telegram_file_ids.sql`
- Stores `telegram_cover_file_id`, `telegram_thumb_file_id`
- First send: Upload to Telegram, cache file_id
- Subsequent sends: Use cached file_id (instant, no upload)
- Saves 95% bandwidth on repeated messages

### 7. Streaming Downloads (Zero RAM)
**Problem:** Loading 10GB file in RAM before sending = crash
**Solution:** Stream chunks directly from R2 to user
- File: `app/integrations/ipn_server.py`
- Function: `stream_from_b2_chunks()`
- Reads 64KB chunks, yields immediately
- 10GB file uses 64KB RAM (constant)
- Direct pipe: R2 → Railway → User

### 8. Mini-App WebView (Bypass 20MB Telegram Limit)
**Problem:** Telegram `bot.send_document()` limited to 20MB
**Solution:** Embedded WebView with direct R2 access
- Files: `upload.html`, `download.html`, `import.html`
- Opens in Telegram app (native WebView)
- Uses presigned URLs for 10GB file operations
- No Telegram API file size limits

### 9. One-Time Download Tokens (Security + Performance)
**Problem:** Shareable download links = abuse + leaked files
**Solution:** UUID tokens with 5-minute expiration
- File: `app/domain/repositories/download_repo.py`
- Generates UUID token per download request
- Stores in PostgreSQL with expiration timestamp
- Single-use only (marked as `used` after first download)
- Rate limiting: 10 downloads/user/hour

### 10. Async-First Architecture
**Problem:** Blocking operations freeze entire server
**Solution:** 100% async/await pattern
- `asyncio.to_thread()` for blocking calls (email, file I/O)
- Async database operations where possible
- Non-blocking HTTP clients (`httpx` instead of `requests`)
- Event loop never blocks, handles 1000+ req/s

### 11. Cloudflare R2 Zero Egress Fees
**Problem:** Backblaze B2 charges $0.01/GB egress (download bandwidth)
**Solution:** Migrated to Cloudflare R2 (zero egress fees)
- File: `app/services/b2_storage_service.py`
- Priority: R2 → B2 fallback
- Same S3-compatible API (boto3)
- 100GB downloads = $0 (vs $1 on B2)
- Custom domain support for CDN

### 12. Gumroad Import Automation
**Problem:** Manually re-creating 100+ products = hours of work
**Solution:** Web scraping with anti-detection measures
- File: `app/services/gumroad_scraper.py`
- BeautifulSoup4 HTML parsing
- Referer header spoofing (bypasses Gumroad protection)
- Rate limiting (1 request/2s)
- Bulk import: product metadata + images → R2

---

## Database Schema (9 Tables)

| Table | Purpose | Key Features |
|-------|---------|--------------|
| **users** | User accounts + seller profiles | `telegram_user_id` indexed, seller stats |
| **products** | Digital catalog | Soft delete, seller FK, 11 categories |
| **orders** | Purchase records | 6 payment statuses, download tracking |
| **payouts** | Seller payments | 24h escrow, manual admin processing |
| **reviews** | Product ratings | Auto-aggregation triggers (1-5 stars) |
| **support_tickets** | Customer support | Status workflow (open/in_progress/resolved/closed) |
| **categories** | Product categories | 11 default categories |
| **download_tokens** | Secure file access | UUID, 5min expiry, one-time use |
| **download_rate_limits** | API protection | 10 downloads/user/hour, sliding window |

**Triggers:** Auto rating aggregation on review insert/update

---

## API Endpoints (16 REST)

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/health` | GET | Health check | Public |
| `/webhook/telegram` | POST | Telegram bot updates | Telegram signature |
| `/ipn/nowpayments` | POST | Payment confirmations | HMAC-SHA512 |
| `/api/generate-upload-url` | POST | R2 presigned upload URL | Telegram WebApp |
| `/api/upload-complete` | POST | Finalize product creation | Telegram WebApp |
| `/api/verify-purchase` | POST | Check order ownership | Telegram WebApp |
| `/api/generate-download-token` | POST | Create download token | Telegram WebApp |
| `/download/{token}` | GET | Stream file from R2 | One-time token |
| `/api/categories` | GET | List categories | Public |
| `/api/import-products` | GET | Scrape Gumroad | Telegram WebApp |
| `/api/import-complete` | POST | Finalize bulk import | Telegram WebApp |
| `/api/log-client-error` | POST | Frontend error logging | Telegram WebApp |

**Deprecated:** `/api/generate-download-url`, `/api/stream-download` (replaced by token system)

---

## Quick Start

### Prerequisites
- Python 3.11+, PostgreSQL 15+
- Telegram Bot Token ([@BotFather](https://t.me/botfather))
- NowPayments API Key
- Cloudflare R2 (or Backblaze B2)

### Installation

```bash
# Clone + setup
git clone <your-repo-url> && cd Python-bot
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Configure (33 env variables)
cp .env.example .env
# Edit .env with your credentials

# Initialize database
python3 -c "from app.core.database_init import DatabaseInitService; DatabaseInitService().init_all_tables()"

# Run
python3 -m app.main
```

**Full setup guide:** See [INSTALLATION.md](INSTALLATION.md) for complete environment variables, troubleshooting, and testing.

---

## Deployment

**Railway (Recommended):**
```bash
npm install -g @railway/cli
railway login && railway init
railway up
railway run python3 -c "from app.core.database_init import DatabaseInitService; DatabaseInitService().init_all_tables()"
```

**Features:** PostgreSQL included • Auto-HTTPS • 512MB RAM minimum

**Full deployment guide:** See [DEPLOYMENT.md](DEPLOYMENT.md) for Railway, Docker, CI/CD, and scaling.

---

## How It Works

### Purchase & Payment Flow (Example)

1. **Browse:** Buyer browses products via bot → clicks "Buy Now"
2. **Select Crypto:** Buyer selects cryptocurrency (BTC/ETH/SOL/USDC/USDT)
3. **Create Payment:** Backend creates order (status: `waiting`) → calls NowPayments API
4. **Display QR:** Bot displays payment QR code + crypto address
5. **Pay:** Buyer sends crypto to address
6. **Blockchain Confirm:** Transaction confirmed (2-10 min) → NowPayments IPN callback
7. **Verify IPN:** Backend verifies HMAC-SHA512 signature
8. **Complete:** Order status → `completed` → Payout created (24h escrow) → Download link sent via Telegram

**Other Flows:**
- **Upload:** Mini-app → Presigned URL → Direct R2 upload → Product created
- **Download:** Token generation → Verification (ownership + rate limit) → Stream R2 → User (64KB chunks)
- **Payout:** 24h escrow → Admin approval → Manual crypto transfer → Email notification
- **Import:** Gumroad URL input → Scrape metadata → Preview table → Bulk create + image upload

---

## Security

11 security measures implemented:

1. **Payment Verification:** HMAC-SHA512 on IPN callbacks
2. **SQL Injection:** 100% parameterized queries
3. **Download Rate Limiting:** 10/user/hour sliding window
4. **One-Time Tokens:** 5min expiry, single-use
5. **File Validation:** Executables (.exe, .sh, .bat) blocked
6. **HTTPS-Only:** Railway enforces SSL
7. **Environment Secrets:** No hardcoded credentials
8. **Telegram WebApp Validation:** HMAC signature verification
9. **Soft Deletes:** Forensic trail (products never truly deleted)
10. **Connection Pooling:** Prevents DB exhaustion attacks
11. **CORS Protection:** Telegram origins only

---

## Monitoring

**Logs:** `/tmp/logs/marketplace_bot.log` • Structured logging • Timestamps + context

**Metrics:** Product views • Download counts • Seller conversion rates • Payment success/failure

**Health Check:** `GET /health` → `{"status": "healthy", "database": "ok", "storage": "ok"}`

**Error Tracking:** Frontend errors via `/api/log-client-error` • Backend exceptions with stack traces


---

## Future Improvements

- [ ] Solana smart-contract (programs) for automated payout
- [ ] Redis caching layer
- [ ] Automated refund processing
- [ ] Affiliate/referral program
- [ ] Subscription products (recurring payments)
- [ ] Product bundles
- [ ] Discount codes/coupons
- [ ] Live chat support (WebSocket)

---

## External Documentation

- **Telegram Bot API:** https://core.telegram.org/bots/api
- **Telegram Mini Apps:** https://core.telegram.org/bots/webapps
- **FastAPI:** https://fastapi.tiangolo.com
- **NowPayments API:** https://documenter.getpostman.com/view/7907941/S1a32n38
- **Cloudflare R2:** https://developers.cloudflare.com/r2/
- **PostgreSQL 15:** https://www.postgresql.org/docs/15/

---

**License:** MIT License - 2025


