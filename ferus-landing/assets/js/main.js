/**
 * UZEUR Marketplace - Main Application
 * Entry point and initialization
 * @version 2.0.0
 */

import i18n from './i18n/i18n.js';
import scrollManager from './components/scroll.js';
import counterManager from './components/counter.js';
import faq from './components/faq.js';
import menu from './components/menu.js';

class UzeurApp {
  constructor() {
    this.initialized = false;
    this.components = {
      i18n: null,
      scroll: null,
      counter: null,
      faq: null,
      menu: null
    };
  }

  /**
   * Initialize application
   */
  async init() {
    if (this.initialized) {
      console.warn('Application already initialized');
      return;
    }

    console.log('🚀 Initializing UZEUR Marketplace...');

    try {
      // Show loading indicator
      this.showLoading();

      // Initialize i18n first
      await this.initI18n();

      // Initialize components
      this.initComponents();

      // Setup analytics (if needed)
      this.initAnalytics();

      // Setup performance monitoring
      this.initPerformance();

      // Hide loading indicator
      this.hideLoading();

      this.initialized = true;
      console.log('✅ UZEUR Marketplace initialized successfully');

      // Dispatch ready event
      window.dispatchEvent(new CustomEvent('uzeurReady'));

    } catch (error) {
      console.error('❌ Error initializing UZEUR Marketplace:', error);
      this.hideLoading();
    }
  }

  /**
   * Initialize i18n system
   */
  async initI18n() {
    try {
      await i18n.init();
      this.components.i18n = i18n;
      console.log('✅ i18n initialized');
    } catch (error) {
      console.error('❌ Error initializing i18n:', error);
    }
  }

  /**
   * Initialize all components
   */
  initComponents() {
    // Scroll manager
    this.components.scroll = scrollManager;
    console.log('✅ Scroll manager initialized');

    // Counter manager
    this.components.counter = counterManager;
    console.log('✅ Counter manager initialized');

    // FAQ
    this.components.faq = faq;
    console.log('✅ FAQ initialized');

    // Menu
    this.components.menu = menu;
    console.log('✅ Menu initialized');
  }

  /**
   * Initialize analytics (Google Analytics, Plausible, etc.)
   */
  initAnalytics() {
    // Check if analytics should be enabled
    const analyticsEnabled = !navigator.doNotTrack && !this.isLocalhost();

    if (!analyticsEnabled) {
      console.log('⚠️ Analytics disabled (localhost or DNT)');
      return;
    }

    // Initialize analytics here if needed
    // Example: gtag, plausible, etc.
    console.log('📊 Analytics initialized');
  }

  /**
   * Initialize performance monitoring
   */
  initPerformance() {
    if (!('PerformanceObserver' in window)) {
      return;
    }

    // Observe long tasks
    try {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.duration > 50) {
            console.warn('⚠️ Long task detected:', entry.duration, 'ms');
          }
        }
      });

      observer.observe({ entryTypes: ['longtask'] });
    } catch (e) {
      // PerformanceObserver not supported
    }

    // Log core web vitals
    this.logWebVitals();
  }

  /**
   * Log Core Web Vitals
   */
  logWebVitals() {
    // FCP (First Contentful Paint)
    const fcpObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        console.log('📊 FCP:', entry.startTime, 'ms');
      }
    });

    try {
      fcpObserver.observe({ entryTypes: ['paint'] });
    } catch (e) {}

    // LCP (Largest Contentful Paint)
    if ('PerformanceLongTaskTiming' in window) {
      const lcpObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const lastEntry = entries[entries.length - 1];
        console.log('📊 LCP:', lastEntry.startTime, 'ms');
      });

      try {
        lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });
      } catch (e) {}
    }

    // CLS (Cumulative Layout Shift)
    let clsScore = 0;
    const clsObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (!entry.hadRecentInput) {
          clsScore += entry.value;
        }
      }
      console.log('📊 CLS:', clsScore);
    });

    try {
      clsObserver.observe({ entryTypes: ['layout-shift'] });
    } catch (e) {}
  }

  /**
   * Show loading indicator
   */
  showLoading() {
    // Add loading class to body
    document.body.classList.add('loading');

    // Create loading overlay if it doesn't exist
    if (!document.querySelector('.loading-overlay')) {
      const overlay = document.createElement('div');
      overlay.className = 'loading-overlay';
      overlay.innerHTML = `
        <div class="loading-spinner">
          <div class="spinner"></div>
        </div>
      `;
      document.body.appendChild(overlay);
    }
  }

  /**
   * Hide loading indicator
   */
  hideLoading() {
    document.body.classList.remove('loading');

    const overlay = document.querySelector('.loading-overlay');
    if (overlay) {
      overlay.style.opacity = '0';
      setTimeout(() => {
        overlay.remove();
      }, 300);
    }
  }

  /**
   * Check if running on localhost
   */
  isLocalhost() {
    return window.location.hostname === 'localhost' ||
           window.location.hostname === '127.0.0.1' ||
           window.location.hostname === '';
  }

  /**
   * Get component instance
   */
  getComponent(name) {
    return this.components[name] || null;
  }

  /**
   * Check if initialized
   */
  isInitialized() {
    return this.initialized;
  }
}

// Create singleton instance
const uzeurApp = new UzeurApp();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    uzeurApp.init();
  });
} else {
  // DOM already loaded
  uzeurApp.init();
}

// Export for use in other modules
export default uzeurApp;

// Also attach to window for inline scripts
window.uzeurApp = uzeurApp;

// Expose components globally for debugging
if (uzeurApp.isLocalhost()) {
  window.i18n = i18n;
  window.scrollManager = scrollManager;
  window.counterManager = counterManager;
  window.faq = faq;
  window.menu = menu;

  console.log('🔧 Debug mode: Components exposed to window object');
}
