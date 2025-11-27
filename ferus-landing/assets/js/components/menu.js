/**
 * UZEUR Marketplace - Menu Component
 * Mobile menu and navigation
 * @version 2.0.0
 */

class Menu {
  constructor() {
    this.menuToggle = null;
    this.mobileMenu = null;
    this.menuLinks = [];
    this.isOpen = false;
    this.init();
  }

  init() {
    this.setupElements();
    this.setupToggle();
    this.setupLinks();
    this.setupEscape();
    this.setupOutsideClick();
  }

  /**
   * Setup menu elements
   */
  setupElements() {
    this.menuToggle = document.querySelector('.menu-toggle');
    this.mobileMenu = document.querySelector('.mobile-menu');
    this.menuLinks = Array.from(document.querySelectorAll('.mobile-menu-link'));
  }

  /**
   * Setup menu toggle button
   */
  setupToggle() {
    if (!this.menuToggle) return;

    this.menuToggle.addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggle();
    });

    // Accessibility
    this.menuToggle.setAttribute('aria-label', 'Toggle menu');
    this.menuToggle.setAttribute('aria-expanded', 'false');
    this.menuToggle.setAttribute('aria-controls', 'mobile-menu');

    if (this.mobileMenu) {
      this.mobileMenu.setAttribute('id', 'mobile-menu');
    }
  }

  /**
   * Setup menu links
   */
  setupLinks() {
    this.menuLinks.forEach(link => {
      link.addEventListener('click', () => {
        // Close menu after clicking a link
        this.close();
      });
    });
  }

  /**
   * Setup escape key to close menu
   */
  setupEscape() {
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isOpen) {
        this.close();
      }
    });
  }

  /**
   * Setup click outside to close menu
   */
  setupOutsideClick() {
    document.addEventListener('click', (e) => {
      if (this.isOpen && this.mobileMenu && !this.mobileMenu.contains(e.target)) {
        this.close();
      }
    });
  }

  /**
   * Toggle menu open/closed
   */
  toggle() {
    if (this.isOpen) {
      this.close();
    } else {
      this.open();
    }
  }

  /**
   * Open menu
   */
  open() {
    if (this.isOpen) return;

    this.isOpen = true;

    if (this.mobileMenu) {
      this.mobileMenu.classList.add('active');
    }

    if (this.menuToggle) {
      this.menuToggle.classList.add('active');
      this.menuToggle.setAttribute('aria-expanded', 'true');
    }

    // Prevent body scroll
    document.body.style.overflow = 'hidden';

    // Focus first menu link for accessibility
    setTimeout(() => {
      if (this.menuLinks[0]) {
        this.menuLinks[0].focus();
      }
    }, 300);

    // Dispatch event
    window.dispatchEvent(new CustomEvent('menuOpened'));
  }

  /**
   * Close menu
   */
  close() {
    if (!this.isOpen) return;

    this.isOpen = false;

    if (this.mobileMenu) {
      this.mobileMenu.classList.remove('active');
    }

    if (this.menuToggle) {
      this.menuToggle.classList.remove('active');
      this.menuToggle.setAttribute('aria-expanded', 'false');
    }

    // Restore body scroll
    document.body.style.overflow = '';

    // Return focus to toggle button
    if (this.menuToggle) {
      this.menuToggle.focus();
    }

    // Dispatch event
    window.dispatchEvent(new CustomEvent('menuClosed'));
  }

  /**
   * Check if menu is open
   */
  isMenuOpen() {
    return this.isOpen;
  }
}

// Create singleton instance
const menu = new Menu();

// Export for use in other modules
export default menu;

// Also attach to window for inline scripts
window.menu = menu;
