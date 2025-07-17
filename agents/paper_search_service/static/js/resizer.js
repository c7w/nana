/**
 * 面板分割线拖拽功能
 */

class PanelResizer {
    constructor() {
        this.resizer = document.getElementById('resizer');
        this.pdfPanel = document.getElementById('pdfPanel');
        this.summaryPanel = document.getElementById('summaryPanel');
        this.contentPanels = document.getElementById('contentPanels');
        
        this.isDragging = false;
        this.startX = 0;
        this.startPdfWidth = 0;
        this.startSummaryWidth = 0;
        
        this.minPanelWidth = 200; // 最小面板宽度
        this.defaultRatio = 0.6; // 默认比例 60:40
        
        this.init();
    }

    init() {
        // 设置初始比例
        this.setRatio(this.defaultRatio);
        
        // 绑定事件
        this.bindEvents();
    }

    bindEvents() {
        // 鼠标按下开始拖拽
        this.resizer.addEventListener('mousedown', (e) => {
            this.startDrag(e);
        });

        // 双击重置到默认比例
        this.resizer.addEventListener('dblclick', () => {
            this.setRatio(this.defaultRatio);
        });

        // 文档级别的鼠标事件
        document.addEventListener('mousemove', (e) => {
            if (this.isDragging) {
                this.drag(e);
            }
        });

        document.addEventListener('mouseup', () => {
            if (this.isDragging) {
                this.stopDrag();
            }
        });

        // 防止拖拽时选中文本
        document.addEventListener('selectstart', (e) => {
            if (this.isDragging) {
                e.preventDefault();
            }
        });

        // 窗口大小改变时保持比例
        window.addEventListener('resize', () => {
            this.maintainRatio();
        });
    }

    startDrag(e) {
        this.isDragging = true;
        this.startX = e.clientX;
        
        // 获取当前面板宽度
        this.startPdfWidth = this.pdfPanel.offsetWidth;
        this.startSummaryWidth = this.summaryPanel.offsetWidth;
        
        // 添加拖拽状态样式
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
        this.resizer.classList.add('dragging');
        
        e.preventDefault();
    }

    drag(e) {
        if (!this.isDragging) return;

        const deltaX = e.clientX - this.startX;
        const containerWidth = this.contentPanels.offsetWidth;
        const resizerWidth = this.resizer.offsetWidth;
        
        // 计算新的PDF面板宽度
        let newPdfWidth = this.startPdfWidth + deltaX;
        let newSummaryWidth = containerWidth - newPdfWidth - resizerWidth;
        
        // 限制最小宽度
        if (newPdfWidth < this.minPanelWidth) {
            newPdfWidth = this.minPanelWidth;
            newSummaryWidth = containerWidth - newPdfWidth - resizerWidth;
        }
        
        if (newSummaryWidth < this.minPanelWidth) {
            newSummaryWidth = this.minPanelWidth;
            newPdfWidth = containerWidth - newSummaryWidth - resizerWidth;
        }
        
        // 限制在20%-80%范围内
        const minRatio = 0.2;
        const maxRatio = 0.8;
        const ratio = newPdfWidth / containerWidth;
        
        if (ratio < minRatio) {
            newPdfWidth = containerWidth * minRatio;
            newSummaryWidth = containerWidth * (1 - minRatio) - resizerWidth;
        } else if (ratio > maxRatio) {
            newPdfWidth = containerWidth * maxRatio;
            newSummaryWidth = containerWidth * (1 - maxRatio) - resizerWidth;
        }
        
        // 应用新宽度
        this.pdfPanel.style.flex = `0 0 ${newPdfWidth}px`;
        this.summaryPanel.style.flex = `0 0 ${newSummaryWidth}px`;
        
        e.preventDefault();
    }

    stopDrag() {
        this.isDragging = false;
        
        // 移除拖拽状态样式
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        this.resizer.classList.remove('dragging');
    }

    setRatio(ratio) {
        // 确保比例在有效范围内
        ratio = Math.max(0.2, Math.min(0.8, ratio));
        
        const containerWidth = this.contentPanels.offsetWidth;
        const resizerWidth = this.resizer.offsetWidth;
        
        const pdfWidth = containerWidth * ratio;
        const summaryWidth = containerWidth * (1 - ratio) - resizerWidth;
        
        this.pdfPanel.style.flex = `0 0 ${pdfWidth}px`;
        this.summaryPanel.style.flex = `0 0 ${summaryWidth}px`;
    }

    maintainRatio() {
        // 获取当前比例并重新应用
        const containerWidth = this.contentPanels.offsetWidth;
        const pdfWidth = this.pdfPanel.offsetWidth;
        const currentRatio = pdfWidth / containerWidth;
        
        // 重新设置相同的比例
        this.setRatio(currentRatio);
    }

    // 获取当前比例
    getCurrentRatio() {
        const containerWidth = this.contentPanels.offsetWidth;
        const pdfWidth = this.pdfPanel.offsetWidth;
        return pdfWidth / containerWidth;
    }

    // 预设比例快捷方法
    setHalf() {
        this.setRatio(0.5);
    }

    setTwoThirds() {
        this.setRatio(0.67);
    }

    setOneThird() {
        this.setRatio(0.33);
    }

    // 隐藏/显示面板
    hidePdfPanel() {
        this.pdfPanel.style.display = 'none';
        this.resizer.style.display = 'none';
        this.summaryPanel.style.flex = '1';
    }

    hideSummaryPanel() {
        this.summaryPanel.style.display = 'none';
        this.resizer.style.display = 'none';
        this.pdfPanel.style.flex = '1';
    }

    showBothPanels() {
        this.pdfPanel.style.display = 'flex';
        this.summaryPanel.style.display = 'flex';
        this.resizer.style.display = 'block';
        this.setRatio(this.defaultRatio);
    }
} 