// ========================================
// FERUS LANDING - JAVASCRIPT
// Carousel horizontal, traductions complètes
// ========================================

// Translations complètes
const translations = {
    fr: {
        // Navigation
        "nav-features": "Fonctionnalités",
        "nav-platform": "Plateforme",
        "nav-pricing": "Tarifs",
        "nav-cta-text": "Accéder au bot",

        // Hero
        "hero-badge": "Version Beta — Accès gratuit",
        "hero-title": "Marketplace de produits numériques<br><span class='gradient-text'>sur Telegram</span>",
        "hero-subtitle": "Vendez vos produits numériques directement sur Telegram. Paiements crypto automatisés via BTC, ETH, USDT ou USDC. Livraison automatique après confirmation. <strong>Aucun frais vendeur. Plateforme axée sur la confidentialité.</strong>",
        "stat-inline-1": "0% commission",
        "stat-inline-2": "Livraison automatique",
        "stat-inline-3": "8 cryptomonnaies",
        "hero-cta-primary": "Créer un compte",
        "hero-cta-secondary": "Documentation (2 min)",
        "hero-trust": "BTC · ETH · USDT · USDC · LTC · XRP · SOL · BNB",

        // Social Proof
        "proof-1": "Utilisateurs Telegram",
        "proof-2": "Frais vendeur",
        "proof-3": "Pour être en ligne",
        "proof-4": "Automatisé",

        // Features
        "features-badge": "Fonctionnalités",
        "features-title": "Interface complète de gestion<br><span class='gradient-text'>intégrée à Telegram</span>",
        "features-subtitle": "Dashboard analytics, paiements automatisés, livraison instantanée. Architecture technique conçue pour les vendeurs de produits numériques.",

        "feature-badge-1": "Paiements",
        "feature-1-title": "Intégration NowPayments",
        "feature-1-text": "Système de paiement crypto via NowPayments. Supporte 8 cryptomonnaies majeures. Confirmation blockchain automatique, livraison instantanée après validation.",
        "feature-1-li-1": "BTC, ETH, USDT, USDC",
        "feature-1-li-2": "LTC, XRP, SOL, BNB",
        "feature-1-li-3": "Confirmation blockchain",
        "feature-1-li-4": "Paiements irréversibles",

        "feature-badge-2": "Analytics",
        "feature-2-title": "Dashboard vendeur",
        "feature-2-text": "Interface de suivi des ventes et revenus. Analytics par produit et période. Visualisation graphique des performances. Export de données disponible.",
        "feature-2-li-1": "Suivi temps réel",
        "feature-2-li-2": "Export CSV",
        "feature-2-li-3": "Graphiques de ventes",

        "feature-badge-3": "Automatisation",
        "feature-3-title": "Livraison automatique",
        "feature-3-text": "Système de livraison automatisé. Le fichier est envoyé à l'acheteur dès la confirmation du paiement crypto. Aucune intervention manuelle requise.",
        "feature-3-li-1": "Automatisation complète",
        "feature-3-li-2": "Confirmation blockchain",
        "feature-3-li-3": "Disponible 24/7",

        "feature-badge-4": "Confidentialité",
        "feature-4-title": "Plateforme axée sur la confidentialité",
        "feature-4-text": "Aucun processus KYC requis. Seule une adresse email de récupération et une adresse crypto Solana sont nécessaires pour commencer à vendre.",
        "feature-4-li-1": "Aucun KYC",
        "feature-4-li-2": "Données minimales",
        "feature-4-li-3": "Paiements crypto directs",

        // Platform
        "platform-badge": "Plateforme",
        "platform-title": "Bot Telegram<br><span class='gradient-text'>avec interface complète</span>",
        "platform-text": "Système de vente intégré directement dans Telegram. Plus de 800 millions d'utilisateurs actifs utilisent cette plateforme quotidiennement.",
        "platform-feat-1-title": "Intégration native",
        "platform-feat-1-text": "Interface utilisateur entièrement dans Telegram. Aucun site externe requis pour vos clients.",
        "platform-feat-2-title": "Processus d'achat simplifié",
        "platform-feat-2-text": "Navigation par catégories ou recherche par ID. Paiement crypto et livraison automatique.",
        "platform-feat-3-title": "Notifications en temps réel",
        "platform-feat-3-text": "Alertes instantanées pour chaque vente et confirmation de paiement via messages Telegram.",

        // Pricing
        "pricing-badge": "Version Beta",
        "pricing-title": "Commencez à vendre<br><span class='gradient-text'>gratuitement</span>",
        "pricing-subtitle": "Plateforme en version beta. Accès gratuit pour tous les vendeurs.",
        "pricing-plan-badge": "Version Beta",
        "pricing-plan-name": "Compte Vendeur",
        "pricing-value": "0",
        "pricing-period": "€ / mois",
        "pricing-desc": "Création de compte, ajout de produits et ventes.",
        "pricing-group-1": "Fonctionnalités incluses",
        "pricing-feat-1": "Produits numériques illimités",
        "pricing-feat-2": "8 cryptomonnaies acceptées",
        "pricing-feat-3": "Dashboard analytics",
        "pricing-feat-4": "Livraison automatique",
        "pricing-feat-5": "Système de notation",
        "pricing-feat-6": "Système de tickets support",
        "pricing-feat-7": "Multi-comptes vendeur",
        "pricing-feat-8": "Récupération par email",
        "pricing-cta": "Créer un compte",
        "pricing-note": "Accès beta gratuit",
        "faq-1-q": "Comment démarrer ?",
        "faq-1-a": "Créez un compte vendeur, configurez votre adresse Solana, ajoutez vos produits. Les ventes sont automatisées.",
        "faq-2-q": "Délai de réception des paiements ?",
        "faq-2-a": "Paiements reçus après confirmation blockchain (5-30 minutes selon la crypto). Transfert direct sur wallet Solana.",

        // CTA Final
        "cta-title": "Commencer à vendre<br><span class='gradient-text'>sur Telegram</span>",
        "cta-text": "Création de compte en quelques minutes. Configuration de l'adresse Solana et ajout de produits. Ventes possibles immédiatement après.",
        "cta-button": "Accéder au bot Telegram",
        "cta-check-1": "Aucune carte bancaire",
        "cta-check-2": "Version beta gratuite",
        "cta-check-3": "Vendez gratuitement",

        // Footer
        "footer-tagline": "Marketplace de produits numériques sur Telegram avec paiements crypto.",
        "footer-product": "Produit",
        "footer-features": "Fonctionnalités",
        "footer-platform": "Plateforme",
        "footer-pricing": "Tarifs",
        "footer-support": "Support",
        "footer-contact": "Telegram",
        "footer-help": "Documentation",
        "footer-copyright": "© 2025 Ferus. Version beta.",
        "footer-disclaimer": "Ferus est une plateforme technique en version beta. Les vendeurs sont responsables de leurs produits et de leur conformité légale. La plateforme fournit uniquement l'infrastructure de paiement et de livraison automatique."
    },
    en: {
        // Navigation
        "nav-features": "Features",
        "nav-platform": "Platform",
        "nav-pricing": "Pricing",
        "nav-cta-text": "Access bot",

        // Hero
        "hero-badge": "Beta Version — Free Access",
        "hero-title": "Digital products marketplace<br><span class='gradient-text'>on Telegram</span>",
        "hero-subtitle": "Sell your digital products directly on Telegram. Automated crypto payments via BTC, ETH, USDT or USDC. Automatic delivery after confirmation. <strong>No seller fees. Privacy-focused platform.</strong>",
        "stat-inline-1": "0% commission",
        "stat-inline-2": "Automatic delivery",
        "stat-inline-3": "8 cryptocurrencies",
        "hero-cta-primary": "Create account",
        "hero-cta-secondary": "Documentation (2 min)",
        "hero-trust": "BTC · ETH · USDT · USDC · LTC · XRP · SOL · BNB",

        // Social Proof
        "proof-1": "Telegram Users",
        "proof-2": "Seller Fees",
        "proof-3": "To go live",
        "proof-4": "Automated",

        // Features
        "features-badge": "Features",
        "features-title": "Complete management interface<br><span class='gradient-text'>integrated into Telegram</span>",
        "features-subtitle": "Analytics dashboard, automated payments, instant delivery. Technical architecture designed for digital product sellers.",

        "feature-badge-1": "Payments",
        "feature-1-title": "NowPayments integration",
        "feature-1-text": "Crypto payment system via NowPayments. Supports 8 major cryptocurrencies. Automatic blockchain confirmation, instant delivery after validation.",
        "feature-1-li-1": "BTC, ETH, USDT, USDC",
        "feature-1-li-2": "LTC, XRP, SOL, BNB",
        "feature-1-li-3": "Blockchain confirmation",
        "feature-1-li-4": "Irreversible payments",

        "feature-badge-2": "Analytics",
        "feature-2-title": "Seller dashboard",
        "feature-2-text": "Sales and revenue tracking interface. Analytics by product and period. Graphical performance visualization. Data export available.",
        "feature-2-li-1": "Real-time tracking",
        "feature-2-li-2": "CSV export",
        "feature-2-li-3": "Sales charts",

        "feature-badge-3": "Automation",
        "feature-3-title": "Automatic delivery",
        "feature-3-text": "Automated delivery system. File is sent to buyer upon crypto payment confirmation. No manual intervention required.",
        "feature-3-li-1": "Full automation",
        "feature-3-li-2": "Blockchain confirmation",
        "feature-3-li-3": "Available 24/7",

        "feature-badge-4": "Privacy",
        "feature-4-title": "Privacy-focused platform",
        "feature-4-text": "No KYC process required. Only a recovery email address and Solana crypto address are needed to start selling.",
        "feature-4-li-1": "No KYC",
        "feature-4-li-2": "Minimal data",
        "feature-4-li-3": "Direct crypto payments",

        // Platform
        "platform-badge": "Platform",
        "platform-title": "Telegram bot<br><span class='gradient-text'>with complete interface</span>",
        "platform-text": "Sales system integrated directly into Telegram. Over 800 million active users use this platform daily.",
        "platform-feat-1-title": "Native integration",
        "platform-feat-1-text": "User interface entirely within Telegram. No external website required for your customers.",
        "platform-feat-2-title": "Simplified purchase process",
        "platform-feat-2-text": "Category navigation or ID search. Crypto payment and automatic delivery.",
        "platform-feat-3-title": "Real-time notifications",
        "platform-feat-3-text": "Instant alerts for each sale and payment confirmation via Telegram messages.",

        // Pricing
        "pricing-badge": "Beta Version",
        "pricing-title": "Start selling<br><span class='gradient-text'>for free</span>",
        "pricing-subtitle": "Platform in beta version. Free access for all sellers.",
        "pricing-plan-badge": "Beta Version",
        "pricing-plan-name": "Seller Account",
        "pricing-value": "0",
        "pricing-period": "€ / month",
        "pricing-desc": "Account creation, product addition and sales.",
        "pricing-group-1": "Included features",
        "pricing-feat-1": "Unlimited digital products",
        "pricing-feat-2": "8 cryptocurrencies accepted",
        "pricing-feat-3": "Analytics dashboard",
        "pricing-feat-4": "Automatic delivery",
        "pricing-feat-5": "Rating system",
        "pricing-feat-6": "Support ticket system",
        "pricing-feat-7": "Multi-seller accounts",
        "pricing-feat-8": "Email recovery",
        "pricing-cta": "Create account",
        "pricing-note": "Free beta access",
        "faq-1-q": "How to get started?",
        "faq-1-a": "Create a seller account, configure your Solana address, add your products. Sales are automated.",
        "faq-2-q": "Payment reception delay?",
        "faq-2-a": "Payments received after blockchain confirmation (5-30 minutes depending on crypto). Direct transfer to Solana wallet.",

        // CTA Final
        "cta-title": "Start selling<br><span class='gradient-text'>on Telegram</span>",
        "cta-text": "Account creation in minutes. Solana address configuration and product addition. Sales possible immediately after.",
        "cta-button": "Access Telegram bot",
        "cta-check-1": "No credit card",
        "cta-check-2": "Free beta version",
        "cta-check-3": "Sell for free",

        // Footer
        "footer-tagline": "Digital products marketplace on Telegram with crypto payments.",
        "footer-product": "Product",
        "footer-features": "Features",
        "footer-platform": "Platform",
        "footer-pricing": "Pricing",
        "footer-support": "Support",
        "footer-contact": "Telegram",
        "footer-help": "Documentation",
        "footer-copyright": "© 2025 Ferus. Beta version.",
        "footer-disclaimer": "Ferus is a technical platform in beta version. Sellers are responsible for their products and legal compliance. The platform provides only the payment and automatic delivery infrastructure."
    }
};

// Current language
let currentLang = localStorage.getItem('preferredLanguage') || 'fr';

// Translate page
function translatePage(lang) {
    currentLang = lang;
    const elements = document.querySelectorAll('[data-translate]');

    elements.forEach(element => {
        const key = element.getAttribute('data-translate');
        if (translations[lang] && translations[lang][key]) {
            element.innerHTML = translations[lang][key];
        }
    });

    // Update active language button
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-lang') === lang);
    });

    // Save preference
    localStorage.setItem('preferredLanguage', lang);
}

// ========================================
// DOM Ready
// ========================================
document.addEventListener('DOMContentLoaded', function() {

    // Apply saved language
    translatePage(currentLang);

    // Language switcher
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const lang = this.getAttribute('data-lang');
            translatePage(lang);
        });
    });

    // ========================================
    // Mobile Menu
    // ========================================
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const mobileMenu = document.querySelector('.mobile-menu');

    if (mobileMenuBtn && mobileMenu) {
        mobileMenuBtn.addEventListener('click', function() {
            mobileMenu.classList.toggle('active');
            this.classList.toggle('active');
        });

        // Close mobile menu when clicking on a link
        mobileMenu.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', function() {
                mobileMenu.classList.remove('active');
                mobileMenuBtn.classList.remove('active');
            });
        });
    }

    // Close mobile menu when clicking outside
    document.addEventListener('click', function(e) {
        if (mobileMenu && mobileMenuBtn) {
            if (!mobileMenu.contains(e.target) && !mobileMenuBtn.contains(e.target)) {
                mobileMenu.classList.remove('active');
                mobileMenuBtn.classList.remove('active');
            }
        }
    });

    // ========================================
    // Smooth Scroll
    // ========================================
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href !== '#' && href.length > 1) {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    const headerOffset = 80;
                    const elementPosition = target.getBoundingClientRect().top;
                    const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

                    window.scrollTo({
                        top: offsetPosition,
                        behavior: 'smooth'
                    });
                }
            }
        });
    });

    // ========================================
    // Header Scroll Effect
    // ========================================
    const header = document.getElementById('header');
    let lastScroll = 0;

    window.addEventListener('scroll', function() {
        const currentScroll = window.pageYOffset;

        if (currentScroll > 50) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }

        lastScroll = currentScroll;
    });

    // ========================================
    // Features Carousel (Horizontal Scroll)
    // ========================================
    const featuresScroll = document.querySelector('.features-scroll');
    const scrollDots = document.querySelectorAll('.scroll-dots .dot');
    const prevBtn = document.querySelector('.scroll-btn.prev');
    const nextBtn = document.querySelector('.scroll-btn.next');

    if (featuresScroll) {
        let currentIndex = 0;
        const cards = document.querySelectorAll('.feature-card-large');
        const totalCards = cards.length;

        // Update dots
        function updateDots(index) {
            scrollDots.forEach((dot, i) => {
                dot.classList.toggle('active', i === index);
            });
        }

        // Scroll to card
        function scrollToCard(index) {
            if (index < 0) index = 0;
            if (index >= totalCards) index = totalCards - 1;

            currentIndex = index;
            const card = cards[index];

            if (card) {
                const scrollLeft = card.offsetLeft - (featuresScroll.offsetWidth - card.offsetWidth) / 2;
                featuresScroll.scrollTo({
                    left: scrollLeft,
                    behavior: 'smooth'
                });
                updateDots(index);
            }
        }

        // Previous button
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                scrollToCard(currentIndex - 1);
            });
        }

        // Next button
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                scrollToCard(currentIndex + 1);
            });
        }

        // Dot clicks
        scrollDots.forEach((dot, index) => {
            dot.addEventListener('click', () => {
                scrollToCard(index);
            });
        });

        // Update on scroll
        featuresScroll.addEventListener('scroll', () => {
            const scrollPosition = featuresScroll.scrollLeft;
            const cardWidth = cards[0].offsetWidth + parseInt(getComputedStyle(featuresScroll).gap);
            const newIndex = Math.round(scrollPosition / cardWidth);

            if (newIndex !== currentIndex) {
                currentIndex = newIndex;
                updateDots(newIndex);
            }
        });

        // Initialize
        updateDots(0);

        // Touch swipe support
        let touchStartX = 0;
        let touchEndX = 0;

        featuresScroll.addEventListener('touchstart', e => {
            touchStartX = e.changedTouches[0].screenX;
        });

        featuresScroll.addEventListener('touchend', e => {
            touchEndX = e.changedTouches[0].screenX;
            handleSwipe();
        });

        function handleSwipe() {
            if (touchEndX < touchStartX - 50) {
                // Swipe left
                scrollToCard(currentIndex + 1);
            }
            if (touchEndX > touchStartX + 50) {
                // Swipe right
                scrollToCard(currentIndex - 1);
            }
        }

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') {
                scrollToCard(currentIndex - 1);
            }
            if (e.key === 'ArrowRight') {
                scrollToCard(currentIndex + 1);
            }
        });
    }

    // ========================================
    // Intersection Observer for Animations
    // ========================================
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe sections
    document.querySelectorAll('.social-proof, .features-carousel, .platform-section, .pricing-section, .cta-final').forEach(section => {
        observer.observe(section);
    });

    // ========================================
    // Button Animations
    // ========================================
    document.querySelectorAll('.btn').forEach(btn => {
        btn.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });

        btn.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });

        btn.addEventListener('click', function(e) {
            if (this.href && this.href.includes('t.me')) {
                this.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    this.style.transform = '';
                }, 200);
            }
        });
    });

    // ========================================
    // Card Hover Effects
    // ========================================
    const cards = document.querySelectorAll('.feature-card-large, .stat-card, .platform-feature');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.zIndex = '10';
        });

        card.addEventListener('mouseleave', function() {
            this.style.zIndex = '1';
        });
    });

    // ========================================
    // Smooth Number Animation
    // ========================================
    const animateNumber = (element, target, duration = 1000) => {
        const start = 0;
        const increment = target / (duration / 16);
        let current = start;

        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                element.textContent = target;
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(current);
            }
        }, 16);
    };

    // ========================================
    // Parallax Effect on Hero Visual
    // ========================================
    const heroVisual = document.querySelector('.hero-visual');
    if (heroVisual) {
        window.addEventListener('scroll', function() {
            const scrolled = window.pageYOffset;
            const speed = 0.3;
            heroVisual.style.transform = `translateY(${scrolled * speed}px)`;
        });
    }

    // ========================================
    // Stats Animation on Scroll
    // ========================================
    const statValues = document.querySelectorAll('.proof-number');
    const hasAnimated = new Set();

    const statsObserver = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting && !hasAnimated.has(entry.target)) {
                hasAnimated.add(entry.target);
                entry.target.style.opacity = '0';

                setTimeout(() => {
                    entry.target.style.transition = 'opacity 0.8s ease';
                    entry.target.style.opacity = '1';
                }, 100);
            }
        });
    }, { threshold: 0.5 });

    statValues.forEach(stat => statsObserver.observe(stat));

    // ========================================
    // Auto-scroll Carousel (optional)
    // ========================================
    let autoScrollInterval = null;
    const startAutoScroll = () => {
        if (featuresScroll && window.innerWidth > 768) {
            autoScrollInterval = setInterval(() => {
                const currentIndex = Math.round(featuresScroll.scrollLeft / (cards[0].offsetWidth + 48));
                const nextIndex = (currentIndex + 1) % totalCards;
                scrollToCard(nextIndex);
            }, 5000);
        }
    };

    const stopAutoScroll = () => {
        if (autoScrollInterval) {
            clearInterval(autoScrollInterval);
            autoScrollInterval = null;
        }
    };

    // Pause auto-scroll on hover
    if (featuresScroll) {
        featuresScroll.addEventListener('mouseenter', stopAutoScroll);
        featuresScroll.addEventListener('mouseleave', startAutoScroll);

        // Start auto-scroll after page load
        setTimeout(startAutoScroll, 2000);
    }

    // ========================================
    // Crypto Icons Animation
    // ========================================
    const cryptoBadges = document.querySelectorAll('.crypto-badge');
    cryptoBadges.forEach((badge, index) => {
        badge.style.animationDelay = `${index * 0.1}s`;
    });

    // ========================================
    // Gradient Text Animation
    // ========================================
    const gradientTexts = document.querySelectorAll('.gradient-text');
    gradientTexts.forEach(text => {
        text.style.backgroundSize = '200% auto';
    });

    // ========================================
    // Loading Complete
    // ========================================
    window.addEventListener('load', function() {
        document.body.classList.add('loaded');
    });

    // ========================================
    // Performance: Reduce animations on low-end devices
    // ========================================
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        document.querySelectorAll('*').forEach(el => {
            el.style.animation = 'none';
            el.style.transition = 'none';
        });
    }

    // ========================================
    // Console Easter Egg
    // ========================================
    console.log('%c⚡ FERUS', 'color: #5eead4; font-size: 32px; font-weight: bold;');
    console.log('%cLa marketplace crypto qu\'attendaient les créateurs', 'color: #cbd5e1; font-size: 14px;');
    console.log('%c0% frais vendeur · Paiements crypto natifs · Livraison automatique', 'color: #94a3b8; font-size: 12px;');
    console.log('%chttps://t.me/FerusBot', 'color: #5eead4; font-size: 12px;');
});
