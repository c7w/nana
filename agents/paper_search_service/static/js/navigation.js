/**
 * Navigation and Theme Management
 * Handles page navigation and dark/light theme switching
 */

class NavigationManager {
    constructor() {
        this.currentPage = 'reading';
        this.currentTheme = 'light';
        this.init();
    }

    init() {
        this.setupNavigation();
        this.setupThemeToggle();
        this.loadThemePreference();
        this.handleHashChange();
    }

    setupNavigation() {
        // Handle navigation clicks
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = e.target.getAttribute('data-page');
                this.navigateToPage(page);
            });
        });

        // Handle browser back/forward
        window.addEventListener('popstate', () => {
            this.handleHashChange();
        });
    }

    setupThemeToggle() {
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                this.toggleTheme();
            });
        }
    }

    navigateToPage(page) {
        // Update active nav link
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        
        const activeLink = document.querySelector(`[data-page="${page}"]`);
        if (activeLink) {
            activeLink.classList.add('active');
        }

        // Hide all pages
        document.querySelectorAll('.page-content').forEach(pageEl => {
            pageEl.classList.remove('active');
        });

        // Show target page
        const targetPage = document.getElementById(`${page}Page`);
        if (targetPage) {
            targetPage.classList.add('active');
            this.currentPage = page;
        }

        // Update URL hash
        window.location.hash = page;

        // Trigger page-specific initialization
        this.initializePage(page);
    }

    handleHashChange() {
        const hash = window.location.hash.slice(1) || 'reading';
        const page = ['reading', 'console'].includes(hash) ? hash : 'reading';
        this.navigateToPage(page);
    }

    initializePage(page) {
        switch (page) {
            case 'reading':
                // Initialize reading page if not already done
                if (!window.paperSearchApp || !window.paperSearchApp.initialized) {
                    window.paperSearchApp = new PaperSearchApp();
                }
                break;
            case 'console':
                this.initializeConsolePage();
                break;
        }
    }

    initializeConsolePage() {
        // Future console page initialization
        console.log('Console page initialized');
    }

    toggleTheme() {
        this.currentTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme();
        this.saveThemePreference();
        this.updateThemeToggle();
    }

    applyTheme() {
        document.documentElement.setAttribute('data-theme', this.currentTheme);
        
        // Update MathJax if it's loaded
        if (window.MathJax) {
            window.MathJax.typesetPromise && window.MathJax.typesetPromise();
        }
    }

    updateThemeToggle() {
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            const icon = themeToggle.querySelector('.icon');
            const text = themeToggle.querySelector('.text');
            
            if (this.currentTheme === 'dark') {
                icon.textContent = '☀️';
                text.textContent = 'Light';
            } else {
                icon.textContent = '🌙';
                text.textContent = 'Dark';
            }
        }
    }

    loadThemePreference() {
        const savedTheme = localStorage.getItem('paper-search-theme');
        if (savedTheme && ['light', 'dark'].includes(savedTheme)) {
            this.currentTheme = savedTheme;
        } else {
            // Auto-detect system preference
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            this.currentTheme = prefersDark ? 'dark' : 'light';
        }
        
        this.applyTheme();
        this.updateThemeToggle();
    }

    saveThemePreference() {
        localStorage.setItem('paper-search-theme', this.currentTheme);
    }

    // Public methods for external use
    getCurrentPage() {
        return this.currentPage;
    }

    getCurrentTheme() {
        return this.currentTheme;
    }
}

// Initialize navigation when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.navigationManager = new NavigationManager();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NavigationManager;
} 