/**
 * 论文查看器JavaScript - 处理PDF显示和摘要渲染
 */

class PaperViewer {
    constructor() {
        this.pdfViewer = document.getElementById('pdfViewer');
        this.summaryViewer = document.getElementById('summaryViewer');
        this.currentPaper = null;
    }

    async loadPaper(paper) {
        this.currentPaper = paper;
        
        // 并行加载PDF和摘要
        await Promise.all([
            this.loadPDF(paper),
            this.loadSummary(paper)
        ]);
    }

    async loadPDF(paper) {
        try {
            if (paper.pdf_url) {
                // 使用iframe显示PDF
                this.pdfViewer.innerHTML = `
                    <iframe src="${paper.pdf_url}" 
                            width="100%" 
                            height="100%" 
                            style="border: none;">
                        <p>Your browser does not support PDFs. 
                           <a href="${paper.pdf_url}" target="_blank">Download the PDF</a>
                        </p>
                    </iframe>
                `;
            } else {
                this.pdfViewer.innerHTML = `
                    <div class="empty-state">
                        <h3>📄 PDF Not Available</h3>
                        <p>PDF file is not available for this paper.</p>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading PDF:', error);
            this.pdfViewer.innerHTML = `
                <div class="empty-state">
                    <h3>❌ Error Loading PDF</h3>
                    <p>Failed to load PDF. Please try again.</p>
                </div>
            `;
        }
    }

    async loadSummary(paper) {
        try {
            if (paper.summary) {
                // 使用marked.js渲染Markdown
                const html = marked.parse(paper.summary);
                this.summaryViewer.innerHTML = html;
                
                // 重新渲染MathJax
                if (window.MathJax && window.MathJax.typesetPromise) {
                    await window.MathJax.typesetPromise([this.summaryViewer]);
                }
            } else {
                this.summaryViewer.innerHTML = `
                    <div class="empty-state">
                        <h3>🤖 No AI Summary</h3>
                        <p>AI summary is not available for this paper.</p>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading summary:', error);
            this.summaryViewer.innerHTML = `
                <div class="empty-state">
                    <h3>❌ Error Loading Summary</h3>
                    <p>Failed to load AI summary. Please try again.</p>
                </div>
            `;
        }
    }

    clearViewer() {
        this.pdfViewer.innerHTML = `
            <div class="empty-state">
                Select a paper to view its PDF
            </div>
        `;
        
        this.summaryViewer.innerHTML = `
            <div class="empty-state">
                Select a paper to view its AI summary
            </div>
        `;
        
        this.currentPaper = null;
    }

    getCurrentPaper() {
        return this.currentPaper;
    }
} 