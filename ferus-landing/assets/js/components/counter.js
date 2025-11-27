/**
 * UZEUR Marketplace - Counter Component
 * Animated number counters
 * @version 2.0.0
 */

class Counter {
  constructor(element, options = {}) {
    this.element = element;
    this.options = {
      duration: options.duration || 2000,
      start: options.start || 0,
      end: options.end || parseInt(element.getAttribute('data-target')) || 100,
      decimals: options.decimals || 0,
      separator: options.separator || ',',
      suffix: options.suffix || element.getAttribute('data-suffix') || '',
      prefix: options.prefix || element.getAttribute('data-prefix') || '',
      easing: options.easing || 'easeOutQuad',
      onComplete: options.onComplete || null
    };

    this.current = this.options.start;
    this.isAnimating = false;
    this.hasAnimated = false;
  }

  /**
   * Easing functions
   */
  easings = {
    linear: t => t,
    easeInQuad: t => t * t,
    easeOutQuad: t => t * (2 - t),
    easeInOutQuad: t => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t,
    easeOutCubic: t => (--t) * t * t + 1
  };

  /**
   * Start counter animation
   */
  start() {
    if (this.isAnimating || this.hasAnimated) return;

    this.isAnimating = true;
    const startTime = performance.now();
    const easingFunc = this.easings[this.options.easing] || this.easings.easeOutQuad;

    const animate = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / this.options.duration, 1);
      const easedProgress = easingFunc(progress);

      // Calculate current value
      this.current = this.options.start + (this.options.end - this.options.start) * easedProgress;

      // Update display
      this.updateDisplay();

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        this.isAnimating = false;
        this.hasAnimated = true;
        this.current = this.options.end;
        this.updateDisplay();

        if (this.options.onComplete) {
          this.options.onComplete();
        }
      }
    };

    requestAnimationFrame(animate);
  }

  /**
   * Update display
   */
  updateDisplay() {
    const value = this.formatNumber(this.current);
    this.element.textContent = `${this.options.prefix}${value}${this.options.suffix}`;
  }

  /**
   * Format number with decimals and separator
   */
  formatNumber(num) {
    const fixed = num.toFixed(this.options.decimals);
    const parts = fixed.split('.');
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, this.options.separator);
    return parts.join('.');
  }

  /**
   * Reset counter
   */
  reset() {
    this.current = this.options.start;
    this.isAnimating = false;
    this.hasAnimated = false;
    this.updateDisplay();
  }
}

/**
 * Counter Manager - manages all counters on page
 */
class CounterManager {
  constructor() {
    this.counters = [];
    this.observer = null;
    this.init();
  }

  init() {
    this.setupCounters();
    this.setupIntersectionObserver();
  }

  /**
   * Find and setup all counter elements
   */
  setupCounters() {
    const counterElements = document.querySelectorAll('[data-counter]');

    counterElements.forEach(element => {
      const counter = new Counter(element, {
        duration: parseInt(element.getAttribute('data-duration')) || 2000,
        decimals: parseInt(element.getAttribute('data-decimals')) || 0,
        separator: element.getAttribute('data-separator') || ',',
        suffix: element.getAttribute('data-suffix') || '',
        prefix: element.getAttribute('data-prefix') || ''
      });

      this.counters.push({
        element,
        counter,
        triggered: false
      });
    });
  }

  /**
   * Setup intersection observer to trigger counters when visible
   */
  setupIntersectionObserver() {
    const options = {
      root: null,
      rootMargin: '0px',
      threshold: 0.5
    };

    this.observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const counterData = this.counters.find(c => c.element === entry.target);
          if (counterData && !counterData.triggered) {
            counterData.counter.start();
            counterData.triggered = true;
            // Unobserve after triggering
            this.observer.unobserve(entry.target);
          }
        }
      });
    }, options);

    // Observe all counter elements
    this.counters.forEach(({ element }) => {
      this.observer.observe(element);
    });
  }

  /**
   * Start all counters manually
   */
  startAll() {
    this.counters.forEach(({ counter }) => {
      counter.start();
    });
  }

  /**
   * Reset all counters
   */
  resetAll() {
    this.counters.forEach(({ counter, triggered }) => {
      counter.reset();
      triggered = false;
    });
  }

  /**
   * Add new counter
   */
  addCounter(element, options = {}) {
    const counter = new Counter(element, options);
    this.counters.push({
      element,
      counter,
      triggered: false
    });

    if (this.observer) {
      this.observer.observe(element);
    }

    return counter;
  }
}

// Create singleton instance
const counterManager = new CounterManager();

// Export for use in other modules
export { Counter, CounterManager };
export default counterManager;

// Also attach to window for inline scripts
window.Counter = Counter;
window.counterManager = counterManager;
