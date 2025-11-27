/**
 * UZEUR - Carousel Performance Optimization
 * Fix lag pendant le swipe
 */

(function() {
    'use strict';

    // Debounce function pour optimiser les événements
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Throttle pour scroll events (plus performant que debounce)
    function throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    // Optimiser le carousel scroll
    function optimizeCarouselScroll() {
        const carousels = document.querySelectorAll('.carousel-container');

        carousels.forEach(carousel => {
            let isScrolling = false;
            let scrollTimeout;

            // Marquer comme en cours de scroll
            carousel.addEventListener('scroll', throttle(() => {
                if (!isScrolling) {
                    carousel.classList.add('scrolling');
                    isScrolling = true;
                }

                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(() => {
                    carousel.classList.remove('scrolling');
                    isScrolling = false;
                }, 150);
            }, 50), { passive: true });

            // Touch optimizations
            carousel.addEventListener('touchstart', () => {
                carousel.style.scrollBehavior = 'auto';
            }, { passive: true });

            carousel.addEventListener('touchend', () => {
                setTimeout(() => {
                    carousel.style.scrollBehavior = 'smooth';
                }, 300);
            }, { passive: true });
        });
    }

    // Optimiser les 3D transforms
    function optimize3DEffects() {
        const cards = document.querySelectorAll('.carousel-container .feature-card, .carousel-container .core-card');

        cards.forEach(card => {
            // Force GPU acceleration
            card.style.transform = 'translateZ(0)';
            card.style.backfaceVisibility = 'hidden';
        });
    }

    // Optimiser les dots updates (éviter trop de DOM updates)
    let dotsUpdatePending = false;
    function optimizeDotsUpdate(updateFunction) {
        if (!dotsUpdatePending) {
            dotsUpdatePending = true;
            requestAnimationFrame(() => {
                updateFunction();
                dotsUpdatePending = false;
            });
        }
    }

    // Lazy load images dans le carousel
    function lazyLoadCarouselImages() {
        const images = document.querySelectorAll('.carousel-container img[data-src]');

        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    imageObserver.unobserve(img);
                }
            });
        }, {
            rootMargin: '50px'
        });

        images.forEach(img => imageObserver.observe(img));
    }

    // Désactiver animations pendant resize
    let resizeTimeout;
    function handleResize() {
        document.body.classList.add('resizing');

        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            document.body.classList.remove('resizing');
        }, 300);
    }

    // CSS pour désactiver transitions pendant resize
    const style = document.createElement('style');
    style.textContent = `
        body.resizing * {
            transition: none !important;
        }

        .carousel-container.scrolling .feature-card,
        .carousel-container.scrolling .core-card {
            transition: none !important;
        }
    `;
    document.head.appendChild(style);

    // Initialize optimizations
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            optimizeCarouselScroll();
            optimize3DEffects();
            lazyLoadCarouselImages();
        });
    } else {
        optimizeCarouselScroll();
        optimize3DEffects();
        lazyLoadCarouselImages();
    }

    // Handle resize
    window.addEventListener('resize', debounce(handleResize, 250), { passive: true });

    console.log('✅ Carousel optimizations loaded');
})();
