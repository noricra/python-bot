/**
 * UZEUR Marketplace - i18n System
 * Internationalization and translation management
 * @version 2.0.0
 */

class I18n {
  constructor() {
    this.currentLang = this.detectLanguage();
    this.translations = {};
    this.fallbackLang = 'fr';
  }

  /**
   * Detect user's preferred language
   * Priority: localStorage > browser > fallback
   */
  detectLanguage() {
    // Check localStorage
    const savedLang = localStorage.getItem('uzeur_lang');
    if (savedLang && ['fr', 'en'].includes(savedLang)) {
      return savedLang;
    }

    // Check browser language
    const browserLang = navigator.language.split('-')[0];
    if (['fr', 'en'].includes(browserLang)) {
      return browserLang;
    }

    // Fallback
    return this.fallbackLang;
  }

  /**
   * Load translation data for a language
   */
  async loadTranslations(lang) {
    try {
      const module = await import(`./${lang}.js`);
      this.translations[lang] = module.default || module.translations;

      return true;
    } catch (error) {
      console.error(`Error loading ${lang} translations:`, error);
      return false;
    }
  }

  /**
   * Get translated string by key
   * Supports nested keys using dot notation: "header.nav.home"
   */
  t(key, params = {}) {
    const keys = key.split('.');
    let value = this.translations[this.currentLang];

    // Navigate through nested object
    for (const k of keys) {
      if (value && typeof value === 'object' && k in value) {
        value = value[k];
      } else {
        // Fallback to fallback language
        value = this.translations[this.fallbackLang];
        for (const k of keys) {
          if (value && typeof value === 'object' && k in value) {
            value = value[k];
          } else {
            console.warn(`Translation key not found: ${key}`);
            return key;
          }
        }
        break;
      }
    }

    // Replace parameters in string
    if (typeof value === 'string' && Object.keys(params).length > 0) {
      return value.replace(/\{(\w+)\}/g, (match, paramKey) => {
        return params[paramKey] !== undefined ? params[paramKey] : match;
      });
    }

    return value;
  }

  /**
   * Change current language
   */
  async setLanguage(lang) {
    if (!['fr', 'en'].includes(lang)) {
      console.error(`Unsupported language: ${lang}`);
      return false;
    }

    // Load translations if not already loaded
    if (!this.translations[lang]) {
      const loaded = await this.loadTranslations(lang);
      if (!loaded) return false;
    }

    this.currentLang = lang;
    localStorage.setItem('uzeur_lang', lang);

    // Update HTML lang attribute
    document.documentElement.lang = lang;

    // Update page content
    this.updatePageContent();

    // Dispatch event for other components
    window.dispatchEvent(new CustomEvent('languageChanged', {
      detail: { lang }
    }));

    return true;
  }

  /**
   * Update all translatable elements on the page
   */
  updatePageContent() {
    // Update elements with data-i18n attribute
    document.querySelectorAll('[data-i18n]').forEach(element => {
      const key = element.getAttribute('data-i18n');
      const translation = this.t(key);

      if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
        element.placeholder = translation;
      } else {
        element.textContent = translation;
      }
    });

    // Update elements with data-i18n-html attribute (allows HTML)
    document.querySelectorAll('[data-i18n-html]').forEach(element => {
      const key = element.getAttribute('data-i18n-html');
      element.innerHTML = this.t(key);
    });

    // Update meta tags
    this.updateMetaTags();
  }

  /**
   * Update meta tags for SEO
   */
  updateMetaTags() {
    const metaDescription = document.querySelector('meta[name="description"]');
    if (metaDescription) {
      metaDescription.content = this.t('meta.description');
    }

    const metaOgTitle = document.querySelector('meta[property="og:title"]');
    if (metaOgTitle) {
      metaOgTitle.content = this.t('meta.title');
    }

    const metaOgDescription = document.querySelector('meta[property="og:description"]');
    if (metaOgDescription) {
      metaOgDescription.content = this.t('meta.description');
    }

    const pageTitle = document.querySelector('title');
    if (pageTitle) {
      pageTitle.textContent = this.t('meta.title');
    }
  }

  /**
   * Get current language
   */
  getCurrentLanguage() {
    return this.currentLang;
  }

  /**
   * Check if language is RTL (for future expansion)
   */
  isRTL() {
    return ['ar', 'he', 'fa'].includes(this.currentLang);
  }

  /**
   * Initialize i18n system
   */
  async init() {
    // Load initial language
    await this.loadTranslations(this.currentLang);

    // Load fallback language if different
    if (this.currentLang !== this.fallbackLang) {
      await this.loadTranslations(this.fallbackLang);
    }

    // Update page content
    this.updatePageContent();

    // Setup language switcher buttons
    this.setupLanguageSwitcher();

    console.log(`✅ i18n initialized with language: ${this.currentLang}`);

    return true;
  }

  /**
   * Setup language switcher UI
   */
  setupLanguageSwitcher() {
    document.querySelectorAll('[data-lang-switch]').forEach(button => {
      const lang = button.getAttribute('data-lang-switch');

      // Set active state
      if (lang === this.currentLang) {
        button.classList.add('active');
      }

      // Add click handler
      button.addEventListener('click', async (e) => {
        e.preventDefault();

        // Remove active from all buttons
        document.querySelectorAll('[data-lang-switch]').forEach(btn => {
          btn.classList.remove('active');
        });

        // Set new language
        await this.setLanguage(lang);

        // Add active to clicked button
        button.classList.add('active');
      });
    });
  }

  /**
   * Format date according to current language
   */
  formatDate(date, options = {}) {
    const defaultOptions = {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    };

    return new Intl.DateTimeFormat(this.currentLang, { ...defaultOptions, ...options })
      .format(new Date(date));
  }

  /**
   * Format number according to current language
   */
  formatNumber(number, options = {}) {
    return new Intl.NumberFormat(this.currentLang, options).format(number);
  }

  /**
   * Format currency
   */
  formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat(this.currentLang, {
      style: 'currency',
      currency: currency
    }).format(amount);
  }
}

// Create singleton instance
const i18n = new I18n();

// Export for use in other modules
export default i18n;

// Also attach to window for inline scripts
window.i18n = i18n;
