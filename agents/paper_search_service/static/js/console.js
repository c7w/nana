/**
 * Console Page Management
 * Handles task creation, queue monitoring, and auto-refresh functionality
 */

class ConsoleManager {
    constructor() {
        this.autoRefreshInterval = null;
        this.autoRefreshEnabled = true;
        this.refreshIntervalMs = 10000; // 10 seconds
        this.currentTasks = new Map();
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.startAutoRefresh();
        this.loadTasks();
    }

    setupEventListeners() {
        // Task creation
        document.getElementById('createTask')?.addEventListener('click', () => {
            this.createTask();
        });

        // Manual refresh
        document.getElementById('refreshTasks')?.addEventListener('click', () => {
            this.loadTasks();
        });

        // Enter key in inputs to create task
        document.getElementById('taskTitle')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.createTask();
            }
        });
    }

    async createTask() {
        const title = document.getElementById('taskTitle')?.value.trim();
        const paperList = document.getElementById('paperList')?.value.trim();
        const description = document.getElementById('taskDescription')?.value.trim();

        if (!title || !paperList) {
            this.showMessage('Please provide both task title and paper list.', 'error');
            return;
        }

        try {
            const response = await fetch('/api/tasks/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    title,
                    input_text: paperList,
                    description: description || undefined
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const task = await response.json();
            this.showMessage(`Task "${title}" created successfully!`, 'success');
            
            // Clear form
            document.getElementById('taskTitle').value = '';
            document.getElementById('paperList').value = '';
            document.getElementById('taskDescription').value = '';

            // Start processing the task
            await this.startTaskProcessing(task.id);
            
            // Refresh task list
            this.loadTasks();

        } catch (error) {
            console.error('Error creating task:', error);
            this.showMessage(`Failed to create task: ${error.message}`, 'error');
        }
    }

    async startTaskProcessing(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}/process`, {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            this.showMessage('Task processing started!', 'success');
        } catch (error) {
            console.error('Error starting task processing:', error);
            this.showMessage(`Failed to start processing: ${error.message}`, 'error');
        }
    }

    async loadTasks() {
        try {
            const response = await fetch('/api/tasks/');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.updateTaskDisplay(data.tasks);
            this.updateRefreshStatus();

        } catch (error) {
            console.error('Error loading tasks:', error);
            this.showTaskError('Failed to load tasks');
        }
    }

    updateTaskDisplay(tasks) {
        const activeTasks = tasks.filter(task => 
            ['pending', 'formatting_input', 'searching_papers', 'analyzing_papers'].includes(task.status)
        );
        const completedTasks = tasks.filter(task => 
            ['completed', 'failed'].includes(task.status)
        );

        this.renderTaskQueue(activeTasks);
        this.renderTaskHistory(completedTasks);
    }

    renderTaskQueue(activeTasks) {
        const queueContainer = document.getElementById('taskQueue');
        
        if (activeTasks.length === 0) {
            queueContainer.innerHTML = '<div class="empty-state">No active tasks</div>';
            return;
        }

        const tasksHtml = activeTasks.map(task => this.renderTaskCard(task, true)).join('');
        queueContainer.innerHTML = tasksHtml;
    }

    renderTaskHistory(completedTasks) {
        const historyContainer = document.getElementById('taskHistory');
        
        if (completedTasks.length === 0) {
            historyContainer.innerHTML = '<div class="empty-state">No completed tasks</div>';
            return;
        }

        // Show only latest 10 tasks
        const recentTasks = completedTasks
            .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
            .slice(0, 10);

        const tasksHtml = recentTasks.map(task => this.renderTaskCard(task, false)).join('');
        historyContainer.innerHTML = tasksHtml;
    }

    renderTaskCard(task, isActive) {
        const statusIcon = this.getStatusIcon(task.status);
        const statusText = this.getStatusText(task.status);
        const progressBar = isActive ? this.renderProgressBar(task.progress) : '';
        const timestamp = new Date(task.updated_at).toLocaleString();

        return `
            <div class="task-card ${task.status}" data-task-id="${task.id}">
                <div class="task-header">
                    <div class="task-title">
                        <span class="status-icon">${statusIcon}</span>
                        <h4>${this.escapeHtml(task.title)}</h4>
                    </div>
                    <div class="task-status">
                        <span class="status-text">${statusText}</span>
                        <span class="timestamp">${timestamp}</span>
                    </div>
                </div>
                
                ${progressBar}
                
                ${task.error ? `<div class="task-error">❌ ${this.escapeHtml(task.error)}</div>` : ''}
                
                <div class="task-actions">
                    <button class="btn btn-small" onclick="consoleManager.showTaskDetails('${task.id}')">
                        📋 Details
                    </button>
                    <button class="btn btn-small" onclick="consoleManager.showTaskLogs('${task.id}')">
                        📜 Logs
                    </button>
                    ${task.status === 'completed' || task.status === 'failed' ? 
                        `<button class="btn btn-small btn-danger" onclick="consoleManager.deleteTask('${task.id}')">🗑️ Delete</button>` : 
                        ''
                    }
                </div>
            </div>
        `;
    }

    renderProgressBar(progress) {
        const percentage = progress.percentage || 0;
        const completed = progress.completed || 0;
        const total = progress.total || 0;
        const failed = progress.failed || 0;

        return `
            <div class="progress-section">
                <div class="progress-info">
                    <span>Progress: ${completed}/${total} papers completed</span>
                    ${failed > 0 ? `<span class="failed-count">${failed} failed</span>` : ''}
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${percentage}%"></div>
                </div>
            </div>
        `;
    }

    getStatusIcon(status) {
        const icons = {
            'pending': '⏳',
            'formatting_input': '📝',
            'searching_papers': '🔍',
            'analyzing_papers': '🧠',
            'completed': '✅',
            'failed': '❌'
        };
        return icons[status] || '❓';
    }

    getStatusText(status) {
        const texts = {
            'pending': 'Pending',
            'formatting_input': 'Formatting Input',
            'searching_papers': 'Searching Papers',
            'analyzing_papers': 'Analyzing Papers',
            'completed': 'Completed',
            'failed': 'Failed'
        };
        return texts[status] || 'Unknown';
    }

    async showTaskDetails(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const task = await response.json();
            this.displayTaskDetailsModal(task);

        } catch (error) {
            console.error('Error loading task details:', error);
            this.showMessage('Failed to load task details', 'error');
        }
    }

    async showTaskLogs(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}/logs`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const logsData = await response.json();
            this.displayTaskLogsModal(logsData);

        } catch (error) {
            console.error('Error loading task logs:', error);
            this.showMessage('Failed to load task logs', 'error');
        }
    }

    displayTaskDetailsModal(task) {
        const papersHtml = task.papers.map(paper => `
            <div class="paper-item ${paper.status}">
                <div class="paper-header">
                    <span class="status-icon">${this.getStatusIcon(paper.status)}</span>
                    <span class="paper-title">${this.escapeHtml(paper.title)}</span>
                </div>
                <div class="paper-status">${this.getStatusText(paper.status)}</div>
                ${paper.error ? `<div class="paper-error">Error: ${this.escapeHtml(paper.error)}</div>` : ''}
            </div>
        `).join('');

        const modalHtml = `
            <div class="modal-overlay" onclick="this.remove()">
                <div class="modal-content" onclick="event.stopPropagation()">
                    <div class="modal-header">
                        <h3>Task Details: ${this.escapeHtml(task.title)}</h3>
                        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
                    </div>
                    <div class="modal-body">
                        <div class="task-info">
                            <p><strong>Status:</strong> ${this.getStatusText(task.status)}</p>
                            <p><strong>Created:</strong> ${new Date(task.created_at).toLocaleString()}</p>
                            <p><strong>Updated:</strong> ${new Date(task.updated_at).toLocaleString()}</p>
                            ${task.completed_at ? `<p><strong>Completed:</strong> ${new Date(task.completed_at).toLocaleString()}</p>` : ''}
                        </div>
                        <div class="papers-section">
                            <h4>Papers (${task.papers.length}):</h4>
                            <div class="papers-list">
                                ${papersHtml}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }

    displayTaskLogsModal(logsData) {
        const logsHtml = logsData.logs.map(log => {
            const timestamp = new Date(log.timestamp).toLocaleString();
            const levelClass = log.level.toLowerCase();
            const dataHtml = log.data ? this.formatLogData(log.data) : '';

            return `
                <div class="log-entry ${levelClass}">
                    <div class="log-header">
                        <span class="log-timestamp">${timestamp}</span>
                        <span class="log-stage">${log.stage}</span>
                        <span class="log-level ${levelClass}">${log.level}</span>
                    </div>
                    <div class="log-message">${this.escapeHtml(log.message)}</div>
                    ${dataHtml}
                </div>
            `;
        }).join('');

        const modalHtml = `
            <div class="modal-overlay" onclick="this.remove()">
                <div class="modal-content logs-modal" onclick="event.stopPropagation()">
                    <div class="modal-header">
                        <h3>📜 Task Logs: ${this.escapeHtml(logsData.title)}</h3>
                        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
                    </div>
                    <div class="modal-body">
                        <div class="logs-container">
                            <div class="logs-info">
                                <p><strong>Total Logs:</strong> ${logsData.logs.length}</p>
                                <div class="logs-filters">
                                    <button class="filter-btn active" data-filter="all">All</button>
                                    <button class="filter-btn" data-filter="info">Info</button>
                                    <button class="filter-btn" data-filter="warning">Warning</button>
                                    <button class="filter-btn" data-filter="error">Error</button>
                                </div>
                            </div>
                            <div class="logs-list">
                                ${logsHtml}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Add filter functionality
        this.setupLogFilters();
    }

    formatLogData(data) {
        if (!data || Object.keys(data).length === 0) {
            return '';
        }

        const formatValue = (value) => {
            if (typeof value === 'object' && value !== null) {
                return JSON.stringify(value, null, 2);
            }
            return String(value);
        };

        const dataEntries = Object.entries(data).map(([key, value]) => {
            return `<div class="log-data-item"><strong>${key}:</strong> <span class="log-data-value">${this.escapeHtml(formatValue(value))}</span></div>`;
        }).join('');

        return `
            <div class="log-data">
                <div class="log-data-toggle" onclick="this.nextElementSibling.classList.toggle('expanded')">
                    📊 Additional Data (click to expand)
                </div>
                <div class="log-data-content">
                    ${dataEntries}
                </div>
            </div>
        `;
    }

    setupLogFilters() {
        const filterButtons = document.querySelectorAll('.filter-btn');
        const logEntries = document.querySelectorAll('.log-entry');

        filterButtons.forEach(button => {
            button.addEventListener('click', () => {
                // Update active button
                filterButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');

                const filter = button.getAttribute('data-filter');

                // Filter log entries
                logEntries.forEach(entry => {
                    if (filter === 'all' || entry.classList.contains(filter)) {
                        entry.style.display = '';
                    } else {
                        entry.style.display = 'none';
                    }
                });
            });
        });
    }

    async deleteTask(taskId) {
        if (!confirm('Are you sure you want to delete this task? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch(`/api/tasks/${taskId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            this.showMessage('Task deleted successfully', 'success');
            this.loadTasks();

        } catch (error) {
            console.error('Error deleting task:', error);
            this.showMessage('Failed to delete task', 'error');
        }
    }

    startAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }

        if (this.autoRefreshEnabled) {
            this.autoRefreshInterval = setInterval(() => {
                this.loadTasks();
            }, this.refreshIntervalMs);
        }
    }

    toggleAutoRefresh() {
        this.autoRefreshEnabled = !this.autoRefreshEnabled;
        
        if (this.autoRefreshEnabled) {
            this.startAutoRefresh();
        } else {
            clearInterval(this.autoRefreshInterval);
        }
        
        this.updateRefreshStatus();
    }

    updateRefreshStatus() {
        const statusElement = document.getElementById('autoRefreshStatus');
        if (statusElement) {
            statusElement.textContent = `Auto-refresh: ${this.autoRefreshEnabled ? 'ON' : 'OFF'}`;
            statusElement.className = `status-text ${this.autoRefreshEnabled ? 'active' : 'inactive'}`;
        }
    }

    showTaskError(message) {
        const queueContainer = document.getElementById('taskQueue');
        const historyContainer = document.getElementById('taskHistory');
        
        const errorHtml = `<div class="error-state">❌ ${message}</div>`;
        
        if (queueContainer) queueContainer.innerHTML = errorHtml;
        if (historyContainer) historyContainer.innerHTML = errorHtml;
    }

    showMessage(message, type = 'info') {
        // Create and show a temporary message
        const messageEl = document.createElement('div');
        messageEl.className = `message message-${type}`;
        messageEl.textContent = message;
        
        document.body.appendChild(messageEl);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            messageEl.remove();
        }, 3000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    destroy() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
    }
}

// Initialize console manager when page loads
let consoleManager = null;

document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if we're on the console page
    if (document.getElementById('consolePage')) {
        consoleManager = new ConsoleManager();
    }
});

// Export for external use
if (typeof window !== 'undefined') {
    window.ConsoleManager = ConsoleManager;
} 