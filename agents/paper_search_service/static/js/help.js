/**
 * Help Page Manager
 * Handles loading and displaying help content from markdown
 */

class HelpManager {
    constructor() {
        this.initialized = false;
        this.content = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadHelpContent();
        this.initialized = true;
    }

    setupEventListeners() {
        // Refresh button
        const refreshBtn = document.getElementById('refreshHelp');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadHelpContent();
            });
        }
    }

    async loadHelpContent() {
        const loadingEl = document.getElementById('helpLoading');
        const contentEl = document.getElementById('helpContentArea');
        const errorEl = document.getElementById('helpError');

        // Show loading state
        this.showLoading();

        try {
            const response = await fetch('/api/helper/content');
            const data = await response.json();

            if (data.success && data.html_content) {
                this.content = data.html_content;
                this.displayContent();
            } else {
                throw new Error(data.message || 'Failed to load content');
            }

        } catch (error) {
            console.error('Error loading help content:', error);
            this.showError(error.message);
        }
    }

    showLoading() {
        const loadingEl = document.getElementById('helpLoading');
        const contentEl = document.getElementById('helpContentArea');
        const errorEl = document.getElementById('helpError');

        if (loadingEl) loadingEl.style.display = 'flex';
        if (contentEl) contentEl.style.display = 'none';
        if (errorEl) errorEl.style.display = 'none';
    }

    displayContent() {
        const loadingEl = document.getElementById('helpLoading');
        const contentEl = document.getElementById('helpContentArea');
        const errorEl = document.getElementById('helpError');

        if (loadingEl) loadingEl.style.display = 'none';
        if (errorEl) errorEl.style.display = 'none';
        
        if (contentEl) {
            contentEl.innerHTML = this.content;
            contentEl.style.display = 'block';
            
            // Apply syntax highlighting if needed
            this.applySyntaxHighlighting();
            
            // Smooth scroll to top
            contentEl.scrollTop = 0;
        }
    }

    showError(message = 'Failed to load help content') {
        const loadingEl = document.getElementById('helpLoading');
        const contentEl = document.getElementById('helpContentArea');
        const errorEl = document.getElementById('helpError');

        if (loadingEl) loadingEl.style.display = 'none';
        if (contentEl) contentEl.style.display = 'none';
        
        if (errorEl) {
            const errorMsg = errorEl.querySelector('.error-message');
            if (errorMsg) {
                errorMsg.textContent = `❌ ${message}. Please try refreshing the page.`;
            }
            errorEl.style.display = 'flex';
        }
    }

    applySyntaxHighlighting() {
        // Apply basic syntax highlighting to code blocks
        const codeBlocks = document.querySelectorAll('#helpContentArea pre code');
        codeBlocks.forEach(block => {
            // Add language detection and highlighting if needed
            block.classList.add('hljs');
        });
    }

    // Public methods
    refresh() {
        this.loadHelpContent();
    }

    getContent() {
        return this.content;
    }

    isInitialized() {
        return this.initialized;
    }
}

// Auto-initialize when DOM is loaded and help page is active
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if help page exists
    if (document.getElementById('helpPage')) {
        // Will be initialized by navigation manager when needed
        console.log('Help manager ready for initialization');
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HelpManager;
}
