/**
 * UZEUR Marketplace - FAQ Component
 * Accordion functionality for FAQ section
 * @version 2.0.0
 */

class FAQ {
  constructor() {
    this.items = [];
    this.currentOpen = null;
    this.init();
  }

  init() {
    this.setupFAQItems();
    this.setupSearch();
    this.setupCategories();
  }

  /**
   * Setup FAQ accordion items
   */
  setupFAQItems() {
    const faqItems = document.querySelectorAll('.faq-item');

    faqItems.forEach((item, index) => {
      const question = item.querySelector('.faq-question');
      const answer = item.querySelector('.faq-answer');

      if (question && answer) {
        this.items.push({ item, question, answer, index });

        // Add click handler
        question.addEventListener('click', () => {
          this.toggleItem(index);
        });

        // Add keyboard accessibility
        question.setAttribute('role', 'button');
        question.setAttribute('aria-expanded', 'false');
        question.setAttribute('aria-controls', `faq-answer-${index}`);
        question.setAttribute('tabindex', '0');

        answer.setAttribute('id', `faq-answer-${index}`);
        answer.setAttribute('role', 'region');

        // Keyboard navigation
        question.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            this.toggleItem(index);
          }
        });
      }
    });
  }

  /**
   * Toggle FAQ item open/closed
   */
  toggleItem(index) {
    const itemData = this.items[index];
    if (!itemData) return;

    const { item, question, answer } = itemData;
    const isOpen = item.classList.contains('active');

    // Close all other items (accordion behavior)
    this.closeAll();

    if (!isOpen) {
      // Open this item
      item.classList.add('active');
      question.setAttribute('aria-expanded', 'true');

      // Set max-height for smooth animation
      const contentHeight = answer.scrollHeight;
      answer.style.maxHeight = `${contentHeight}px`;

      this.currentOpen = index;
    } else {
      // Close this item
      item.classList.remove('active');
      question.setAttribute('aria-expanded', 'false');
      answer.style.maxHeight = '0';
      this.currentOpen = null;
    }
  }

  /**
   * Close all FAQ items
   */
  closeAll() {
    this.items.forEach(({ item, question, answer }) => {
      item.classList.remove('active');
      question.setAttribute('aria-expanded', 'false');
      answer.style.maxHeight = '0';
    });
    this.currentOpen = null;
  }

  /**
   * Open all FAQ items
   */
  openAll() {
    this.items.forEach(({ item, question, answer }) => {
      item.classList.add('active');
      question.setAttribute('aria-expanded', 'true');
      answer.style.maxHeight = `${answer.scrollHeight}px`;
    });
  }

  /**
   * Setup FAQ search
   */
  setupSearch() {
    const searchInput = document.querySelector('.faq-search-input');
    if (!searchInput) return;

    let searchTimeout;

    searchInput.addEventListener('input', (e) => {
      clearTimeout(searchTimeout);

      searchTimeout = setTimeout(() => {
        const query = e.target.value.toLowerCase().trim();
        this.filterItems(query);
      }, 300);
    });
  }

  /**
   * Filter FAQ items by search query
   */
  filterItems(query) {
    if (!query) {
      // Show all items
      this.items.forEach(({ item }) => {
        item.style.display = '';
      });
      return;
    }

    this.items.forEach(({ item, question, answer }) => {
      const questionText = question.textContent.toLowerCase();
      const answerText = answer.textContent.toLowerCase();

      if (questionText.includes(query) || answerText.includes(query)) {
        item.style.display = '';
        // Highlight matching items
        item.style.borderColor = 'var(--color-primary)';
      } else {
        item.style.display = 'none';
      }
    });
  }

  /**
   * Setup category filtering
   */
  setupCategories() {
    const categoryButtons = document.querySelectorAll('.faq-category');
    if (categoryButtons.length === 0) return;

    categoryButtons.forEach(button => {
      button.addEventListener('click', () => {
        const category = button.getAttribute('data-category');

        // Update active state
        categoryButtons.forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');

        // Filter items
        this.filterByCategory(category);
      });
    });
  }

  /**
   * Filter FAQ items by category
   */
  filterByCategory(category) {
    if (category === 'all') {
      // Show all items
      this.items.forEach(({ item }) => {
        item.style.display = '';
      });
      return;
    }

    this.items.forEach(({ item }) => {
      const itemCategory = item.getAttribute('data-category');

      if (itemCategory === category) {
        item.style.display = '';
      } else {
        item.style.display = 'none';
      }
    });
  }

  /**
   * Get FAQ item by index
   */
  getItem(index) {
    return this.items[index];
  }

  /**
   * Get all FAQ items
   */
  getAllItems() {
    return this.items;
  }

  /**
   * Open specific item by index
   */
  openItem(index) {
    const itemData = this.items[index];
    if (!itemData) return;

    this.closeAll();

    const { item, question, answer } = itemData;
    item.classList.add('active');
    question.setAttribute('aria-expanded', 'true');
    answer.style.maxHeight = `${answer.scrollHeight}px`;

    this.currentOpen = index;
  }

  /**
   * Close specific item by index
   */
  closeItem(index) {
    const itemData = this.items[index];
    if (!itemData) return;

    const { item, question, answer } = itemData;
    item.classList.remove('active');
    question.setAttribute('aria-expanded', 'false');
    answer.style.maxHeight = '0';

    if (this.currentOpen === index) {
      this.currentOpen = null;
    }
  }
}

// Create singleton instance
const faq = new FAQ();

// Export for use in other modules
export default faq;

// Also attach to window for inline scripts
window.faq = faq;
