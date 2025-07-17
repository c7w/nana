/**
 * 主应用JavaScript - 处理页面初始化、论文加载、搜索功能
 */

class PaperSearchApp {
    constructor() {
        console.log('PaperSearchApp constructor started');
        
        this.papers = [];
        this.currentPaper = null;
        this.isLoading = false;
        this.initialized = false;
        
        // Only initialize if were on the reading page
        if (document.getElementById('readingPage')) {
            this.init();
        }
    }

    init() {
        try {
            this.initializeElements();
            this.bindEvents();
            this.loadPapers();
            this.initialized = true;
            console.log('PaperSearchApp initialized successfully');
        } catch (error) {
            console.error('Error initializing PaperSearchApp:', error);
        }
    }

    initializeElements() {
        console.log('Initializing elements...');
        
        // 获取DOM元素
        this.searchInput = document.getElementById('searchInput');
        this.paperSelect = document.getElementById('paperSelect');
        this.paperCount = document.getElementById('paperCount');
        this.refreshBtn = document.getElementById('refreshBtn');
        this.loadingOverlay = document.getElementById('loadingOverlay');
        
        console.log('DOM elements found:', {
            searchInput: !!this.searchInput,
            paperSelect: !!this.paperSelect,
            paperCount: !!this.paperCount,
            refreshBtn: !!this.refreshBtn,
            loadingOverlay: !!this.loadingOverlay
        });
        
        // 检查依赖类是否存在
        if (typeof PaperViewer === 'undefined') {
            console.error('PaperViewer class not found');
            return;
        }
        if (typeof ChatInterface === 'undefined') {
            console.error('ChatInterface class not found');
            return;
        }
        if (typeof PanelResizer === 'undefined') {
            console.error('PanelResizer class not found');
            return;
        }
        
        // 初始化其他组件
        try {
            this.paperViewer = new PaperViewer();
            console.log('PaperViewer initialized');
        } catch (error) {
            console.error('Error initializing PaperViewer:', error);
        }
        
        try {
            this.chatInterface = new ChatInterface();
            console.log('ChatInterface initialized');
        } catch (error) {
            console.error('Error initializing ChatInterface:', error);
        }
        
        try {
            this.resizer = new PanelResizer();
            console.log('PanelResizer initialized');
        } catch (error) {
            console.error('Error initializing PanelResizer:', error);
        }
        
        // 将chatInterface暴露为全局变量，供HTML中的onclick使用
        if (this.chatInterface) {
            window.chatInterface = this.chatInterface;
        }
    }

    bindEvents() {
        // 搜索输入事件
        this.searchInput.addEventListener('input', (e) => {
            this.filterPapers(e.target.value);
        });

        // 论文选择事件
        this.paperSelect.addEventListener('change', (e) => {
            if (e.target.value) {
                this.selectPaper(e.target.value);
            }
        });

        // 刷新按钮事件
        this.refreshBtn.addEventListener('click', () => {
            this.refreshPapers();
        });
    }

    async loadPapers() {
        try {
            this.showLoading();
            const response = await fetch('/api/papers/');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.papers = data.papers;
            this.updatePaperList(this.papers);
            this.updatePaperCount(data.total);
            
        } catch (error) {
            console.error('Failed to load papers:', error);
            this.showError('Failed to load papers. Please try again.');
        } finally {
            this.hideLoading();
        }
    }

    async refreshPapers() {
        try {
            this.showLoading();
            const response = await fetch('/api/papers/refresh');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.papers = data.papers;
            this.updatePaperList(this.papers);
            this.updatePaperCount(data.total);
            
            // 显示刷新成功消息
            this.showMessage(`🔄 Refreshed! Found ${data.total} papers with summaries.`);
            
        } catch (error) {
            console.error('Failed to refresh papers:', error);
            this.showError('Failed to refresh papers. Please try again.');
        } finally {
            this.hideLoading();
        }
    }

    filterPapers(keyword) {
        if (!keyword.trim()) {
            this.updatePaperList(this.papers);
            this.updatePaperCount(this.papers.length);
            return;
        }

        const filtered = this.papers.filter(paper => 
            paper.display_title.toLowerCase().includes(keyword.toLowerCase())
        );
        
        this.updatePaperList(filtered);
        this.updatePaperCount(filtered.length);
    }

    updatePaperList(papers) {
        // 清空现有选项
        this.paperSelect.innerHTML = '';
        
        if (papers.length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No papers found';
            option.disabled = true;
            this.paperSelect.appendChild(option);
            return;
        }

        // 添加空选项
        const emptyOption = document.createElement('option');
        emptyOption.value = '';
        emptyOption.textContent = 'Select a paper...';
        this.paperSelect.appendChild(emptyOption);

        // 添加论文选项
        papers.forEach(paper => {
            const option = document.createElement('option');
            option.value = paper.display_title;
            option.textContent = paper.display_title;
            this.paperSelect.appendChild(option);
        });
    }

    updatePaperCount(count) {
        this.paperCount.textContent = `📊 Found ${count} papers with summaries`;
    }

    async selectPaper(displayTitle) {
        try {
            // 只显示内容区域的加载状态
            this.showContentLoading();
            
            // 从API获取论文详情
            const response = await fetch(
                `/api/papers/by-title?display_title=${encodeURIComponent(displayTitle)}`
            );
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const paper = await response.json();
            this.currentPaper = paper;
            
            // 更新PDF和摘要显示（无刷新）
            this.paperViewer.loadPaper(paper);
            
            // 准备聊天功能
            this.prepareChatForPaper(paper);
            
        } catch (error) {
            console.error('Failed to load paper details:', error);
            this.showError('Failed to load paper details. Please try again.');
        } finally {
            this.hideContentLoading();
        }
    }

    showContentLoading() {
        // 在PDF和摘要区域显示加载状态
        const pdfViewer = document.getElementById('pdfViewer');
        const summaryViewer = document.getElementById('summaryViewer');
        
        pdfViewer.innerHTML = '<div class="empty-state"><div class="loading-spinner"></div><div>Loading PDF...</div></div>';
        summaryViewer.innerHTML = '<div class="empty-state"><div class="loading-spinner"></div><div>Loading summary...</div></div>';
    }

    hideContentLoading() {
        // 加载完成后，内容会被 paperViewer.loadPaper() 替换
    }

    prepareChatForPaper(paper) {
        // 启用聊天功能（使用arxiv_id作为paper_id，如果没有则使用title）
        if (paper.arxiv_id || paper.title) {
            this.chatInterface.preparePaper(paper);
        } else {
            this.chatInterface.disableChat();
        }
    }

    showLoading() {
        this.isLoading = true;
        this.loadingOverlay.style.display = 'flex';
    }

    hideLoading() {
        this.isLoading = false;
        this.loadingOverlay.style.display = 'none';
    }

    showMessage(message) {
        // 简单的消息显示（可以后续改进为更好的通知系统）
        const messageDiv = document.createElement('div');
        messageDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #28a745;
            color: white;
            padding: 15px 20px;
            border-radius: 4px;
            z-index: 10000;
            font-size: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        `;
        messageDiv.textContent = message;
        document.body.appendChild(messageDiv);

        // 3秒后自动移除
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.parentNode.removeChild(messageDiv);
            }
        }, 3000);
    }

    showError(message) {
        // 错误消息显示
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #dc3545;
            color: white;
            padding: 15px 20px;
            border-radius: 4px;
            z-index: 10000;
            font-size: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        `;
        errorDiv.textContent = message;
        document.body.appendChild(errorDiv);

        // 5秒后自动移除
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.parentNode.removeChild(errorDiv);
            }
        }, 5000);
    }
}

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.app = new PaperSearchApp();
}); 