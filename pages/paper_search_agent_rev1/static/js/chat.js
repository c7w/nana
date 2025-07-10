/**
 * 聊天功能JavaScript - 处理PDF聊天交互
 */

class ChatInterface {
    constructor() {
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.sendChatBtn = document.getElementById('sendChatBtn');
        this.suggestedQuestions = document.getElementById('suggestedQuestions');
        
        this.currentPaper = null;
        this.conversationHistory = [];
        
        this.initializeEvents();
    }

    initializeEvents() {
        // 发送按钮点击事件
        this.sendChatBtn.addEventListener('click', () => {
            this.sendMessage();
        });

        // 输入框回车事件
        this.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // 窗口大小改变时重新调整聊天高度
        window.addEventListener('resize', () => {
            this.adjustChatHeight();
        });
    }

    async preparePaper(paper) {
        this.currentPaper = paper;
        this.conversationHistory = [];
        
        // 启用聊天输入
        this.chatInput.disabled = false;
        this.sendChatBtn.disabled = false;
        this.chatInput.placeholder = "Ask a question about this paper...";
        
        // 清除聊天历史
        this.clearMessages();
        
        // 加载建议问题
        await this.loadSuggestedQuestions(paper.arxiv_id || paper.title);
        
        // 显示欢迎消息
        this.showWelcomeMessage();
        
        // 初始调整高度
        setTimeout(() => {
            this.adjustChatHeight();
        }, 100);
    }

    async loadSuggestedQuestions(paperId) {
        try {
            const response = await fetch(`/api/chat/suggestions/${encodeURIComponent(paperId)}`);
            if (response.ok) {
                const data = await response.json();
                this.displaySuggestedQuestions(data.suggestions);
            }
        } catch (error) {
            console.error('Failed to load suggested questions:', error);
        }
    }

    displaySuggestedQuestions(suggestions) {
        if (!suggestions || suggestions.length === 0) {
            this.suggestedQuestions.innerHTML = '';
            return;
        }

        const suggestionsHtml = suggestions.map(suggestion => 
            `<button class="suggestion-btn" onclick="chatInterface.askSuggestion('${suggestion.replace(/'/g, "\\'")}')">
                ${suggestion}
            </button>`
        ).join('');

        this.suggestedQuestions.innerHTML = suggestionsHtml;
    }

    askSuggestion(question) {
        this.chatInput.value = question;
        this.sendMessage();
    }

    showWelcomeMessage() {
        const welcomeHtml = `
            <div class="welcome-message">
                <p>🤖 Ready to chat about: <strong>${this.currentPaper.display_title}</strong></p>
                <p>Ask me anything about this paper!</p>
            </div>
        `;
        
        this.chatMessages.innerHTML = welcomeHtml + this.suggestedQuestions.outerHTML;
    }

    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message || !this.currentPaper) return;

        // 添加用户消息
        this.addMessage('user', message);
        this.chatInput.value = '';
        
        // 禁用输入
        this.setInputEnabled(false);
        
        // 显示正在输入指示器
        this.showTypingIndicator();

        try {
            // 发送到后端
            const response = await fetch('/api/chat/message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    paper_id: this.currentPaper.arxiv_id || this.currentPaper.title,
                    message: message,
                    conversation_history: this.conversationHistory
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // 移除输入指示器
            this.hideTypingIndicator();
            
            // 添加AI响应
            this.addMessage('assistant', data.message);
            
        } catch (error) {
            console.error('Failed to send message:', error);
            this.hideTypingIndicator();
            this.addMessage('assistant', '抱歉，发生了错误。请稍后重试。');
        } finally {
            // 重新启用输入
            this.setInputEnabled(true);
            this.chatInput.focus();
        }
    }

    addMessage(role, content) {
        // 确保content不为空
        if (content === undefined || content === null || content === '') {
            content = role === 'assistant' ? '🤖 抱歉，我没有收到有效的响应。' : '(空消息)';
        }
        
        // 添加到对话历史
        this.conversationHistory.push({ role, content });
        
        // 创建消息元素
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${role} fade-in`;
        
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'chat-message-avatar';
        avatarDiv.textContent = role === 'user' ? '👤' : '🤖';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'chat-message-content';
        
        try {
            if (role === 'assistant') {
                // 对AI响应进行Markdown渲染
                contentDiv.innerHTML = marked.parse(String(content));
            } else {
                contentDiv.textContent = String(content);
            }
        } catch (error) {
            console.error('Error rendering message content:', error);
            contentDiv.textContent = role === 'assistant' ? 
                '🤖 抱歉，消息渲染失败。' : 
                String(content);
        }
        
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        
        // 添加到聊天区域
        this.chatMessages.appendChild(messageDiv);
        
        // 滚动到底部
        this.scrollToBottom();
        
        // 如果是AI消息，重新渲染MathJax
        if (role === 'assistant' && window.MathJax && window.MathJax.typesetPromise) {
            window.MathJax.typesetPromise([contentDiv]).catch((err) => {
                console.log('MathJax typeset failed: ' + err.message);
            });
        }
        
        // 延迟调整高度，确保内容已渲染
        setTimeout(() => {
            this.adjustChatHeight();
        }, 100);
    }

    showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.id = 'typing-indicator';
        typingDiv.className = 'chat-message assistant fade-in';
        typingDiv.innerHTML = `
            <div class="chat-message-avatar">🤖</div>
            <div class="chat-message-content">
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        
        this.chatMessages.appendChild(typingDiv);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    setInputEnabled(enabled) {
        this.chatInput.disabled = !enabled;
        this.sendChatBtn.disabled = !enabled;
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        
        // 动态调整聊天区域高度
        this.adjustChatHeight();
    }

    adjustChatHeight() {
        const chatSection = document.querySelector('.chat-section');
        if (!chatSection || !this.chatMessages) return;
        
        const chatMessages = this.chatMessages;
        const messagesHeight = chatMessages.scrollHeight;
        const headerHeight = 70; // chat header 高度 (包含边框)
        const inputHeight = 90;  // chat input 高度 (包含padding)
        const padding = 10;      // 额外padding
        
        // 计算需要的总高度
        const requiredHeight = messagesHeight + headerHeight + inputHeight + padding;
        
        // 设置最小和最大高度限制
        const minHeight = 300;
        const maxHeight = Math.floor(window.innerHeight * 0.8); // 80vh
        
        // 计算实际高度
        const newHeight = Math.min(Math.max(requiredHeight, minHeight), maxHeight);
        
        // 只有当高度确实需要改变时才应用（避免不必要的重排）
        const currentHeight = chatSection.offsetHeight;
        if (Math.abs(currentHeight - newHeight) > 5) { // 5px的阈值避免小幅抖动
            chatSection.style.height = `${newHeight}px`;
        }
    }

    clearMessages() {
        this.chatMessages.innerHTML = '';
        this.conversationHistory = [];
    }

    disableChat() {
        this.currentPaper = null;
        this.chatInput.disabled = true;
        this.sendChatBtn.disabled = true;
        this.chatInput.placeholder = "Select a paper to start chatting...";
        this.clearMessages();
        
        this.chatMessages.innerHTML = `
            <div class="welcome-message">
                <p>🤖 Select a paper to start chatting!</p>
            </div>
        `;
    }
} 