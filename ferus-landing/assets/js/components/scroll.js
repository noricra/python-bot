/**
 * UZEUR Marketplace - Scroll Component
 * Scroll animations, reveal effects, and scroll-to-top
 * @version 2.0.0
 */

class ScrollManager {
  constructor() {
    this.scrollToTopBtn = null;
    this.scrollProgress = null;
    this.header = null;
    this.revealElements = [];
    this.init();
  }

  init() {
    this.setupScrollToTop();
    this.setupScrollProgress();
    this.setupHeaderScroll();
    this.setupSmoothScroll();
    this.setupScrollReveal();
    this.attachScrollListener();
  }

  /**
   * Setup scroll-to-top button
   */
  setupScrollToTop() {
    // Create button if it doesn't exist
    if (!document.querySelector('.scroll-to-top')) {
      const btn = document.createElement('button');
      btn.className = 'scroll-to-top';
      btn.setAttribute('aria-label', 'Scroll to top');
      btn.innerHTML = '↑';
      document.body.appendChild(btn);
      this.scrollToTopBtn = btn;
    } else {
      this.scrollToTopBtn = document.querySelector('.scroll-to-top');
    }

    // Click handler
    this.scrollToTopBtn.addEventListener('click', () => {
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    });
  }

  /**
   * Setup scroll progress indicator
   */
  setupScrollProgress() {
    this.scrollProgress = document.querySelector('.scroll-progress');
    if (!this.scrollProgress) {
      const progress = document.createElement('div');
      progress.className = 'scroll-progress';
      const header = document.querySelector('.header');
      if (header) {
        header.appendChild(progress);
        this.scrollProgress = progress;
      }
    }
  }

  /**
   * Setup header scroll behavior
   */
  setupHeaderScroll() {
    this.header = document.querySelector('.header');
  }

  /**
   * Setup smooth scroll for anchor links
   */
  setupSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', (e) => {
        const href = anchor.getAttribute('href');

        // Ignore # only links
        if (href === '#') return;

        const target = document.querySelector(href);
        if (target) {
          e.preventDefault();

          // Close mobile menu if open
          const mobileMenu = document.querySelector('.mobile-menu');
          if (mobileMenu && mobileMenu.classList.contains('active')) {
            mobileMenu.classList.remove('active');
            document.querySelector('.menu-toggle')?.classList.remove('active');
          }

          // Scroll to target
          const headerHeight = this.header?.offsetHeight || 0;
          const targetPosition = target.offsetTop - headerHeight;

          window.scrollTo({
            top: targetPosition,
            behavior: 'smooth'
          });
        }
      });
    });
  }

  /**
   * Setup scroll reveal animations
   */
  setupScrollReveal() {
    this.revealElements = Array.from(document.querySelectorAll('.scroll-reveal'));

    // Create intersection observer
    const observerOptions = {
      root: null,
      rootMargin: '0px 0px -100px 0px',
      threshold: 0.1
    };

    this.revealObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          // Optionally unobserve after reveal
          // this.revealObserver.unobserve(entry.target);
        }
      });
    }, observerOptions);

    // Observe all reveal elements
    this.revealElements.forEach(el => {
      this.revealObserver.observe(el);
    });
  }

  /**
   * Main scroll event handler
   */
  handleScroll() {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const scrollHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
    const scrollPercent = (scrollTop / scrollHeight) * 100;

    // Update scroll progress
    if (this.scrollProgress) {
      this.scrollProgress.style.width = `${scrollPercent}%`;
    }

    // Update header scroll state
    if (this.header) {
      if (scrollTop > 50) {
        this.header.classList.add('scrolled');
      } else {
        this.header.classList.remove('scrolled');
      }
    }

    // Show/hide scroll to top button
    if (this.scrollToTopBtn) {
      if (scrollTop > 300) {
        this.scrollToTopBtn.classList.add('visible');
      } else {
        this.scrollToTopBtn.classList.remove('visible');
      }
    }
  }

  /**
   * Attach scroll listener with throttle
   */
  attachScrollListener() {
    let ticking = false;

    window.addEventListener('scroll', () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          this.handleScroll();
          ticking = false;
        });
        ticking = true;
      }
    });

    // Initial call
    this.handleScroll();
  }

  /**
   * Scroll to element
   */
  scrollToElement(element, offset = 0) {
    if (typeof element === 'string') {
      element = document.querySelector(element);
    }

    if (element) {
      const headerHeight = this.header?.offsetHeight || 0;
      const targetPosition = element.offsetTop - headerHeight - offset;

      window.scrollTo({
        top: targetPosition,
        behavior: 'smooth'
      });
    }
  }

  /**
   * Get current scroll position
   */
  getScrollPosition() {
    return {
      x: window.pageXOffset || document.documentElement.scrollLeft,
      y: window.pageYOffset || document.documentElement.scrollTop
    };
  }

  /**
   * Disable scroll (for modals, etc.)
   */
  disableScroll() {
    document.body.style.overflow = 'hidden';
    document.body.style.paddingRight = `${this.getScrollbarWidth()}px`;
  }

  /**
   * Enable scroll
   */
  enableScroll() {
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
  }

  /**
   * Get scrollbar width
   */
  getScrollbarWidth() {
    const outer = document.createElement('div');
    outer.style.visibility = 'hidden';
    outer.style.overflow = 'scroll';
    document.body.appendChild(outer);

    const inner = document.createElement('div');
    outer.appendChild(inner);

    const scrollbarWidth = outer.offsetWidth - inner.offsetWidth;
    outer.parentNode.removeChild(outer);

    return scrollbarWidth;
  }

  /**
   * Check if element is in viewport
   */
  isInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
      rect.top >= 0 &&
      rect.left >= 0 &&
      rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
      rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
  }
}

// Create singleton instance
const scrollManager = new ScrollManager();

// Export for use in other modules
export default scrollManager;

// Also attach to window for inline scripts
window.scrollManager = scrollManager;
