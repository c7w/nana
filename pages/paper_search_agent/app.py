import gradio as gr
import json
from pathlib import Path
import pandas as pd
from datetime import datetime

# Define project paths, adjusting for the new file location
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_FILE = PROJECT_ROOT / "storage/paper_search_agent/cache.json"

CUSTOM_CSS = """
/* Create a scrollable container for the summary with a fixed height matching the PDF viewer */
#summary-viewer {
    height: 800px;
    overflow-y: auto !important;
    padding: 1rem;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
}
/* Standardize header font sizes within the summary to prevent them from becoming too small */
#summary-viewer h1, #summary-viewer h2, #summary-viewer h3, #summary-viewer h4, #summary-viewer h5, #summary-viewer h6 {
    font-size: 1em; /* Set to the base body font size */
    font-weight: 600; /* Keep headers bold for structure */
}
/* Style for the refresh button */
.refresh-button {
    margin-bottom: 1rem;
}

/* Simple resizer styles */
#main-row {
    position: relative;
}

#main-row::after {
    content: '';
    position: absolute;
    top: 0;
    bottom: 0;
    left: 60%;
    width: 4px;
    background: #e0e0e0;
    cursor: col-resize;
    z-index: 1000;
    transform: translateX(-2px);
    transition: background 0.2s;
}

#main-row:hover::after {
    background: #007bff;
}
"""

def format_collection_time(collected_at_str):
    """Format collection time for display."""
    if not collected_at_str:
        return "Unknown"
    
    try:
        # Parse ISO format datetime
        dt = datetime.fromisoformat(collected_at_str.replace('Z', '+00:00'))
        # Format as readable date
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return "Unknown"

def load_data():
    """Loads, sorts, and prepares the paper data for display. Only includes papers with summaries."""
    if not CACHE_FILE.exists():
        return pd.DataFrame(columns=["display_title", "title", "collected_at"]), {}
    
    with open(CACHE_FILE, 'r') as f:
        # The cache is pre-sorted by the agent, so we load it as is.
        cache_data = json.load(f)

    papers = []
    filtered_cache = {}
    
    for key, paper in cache_data.items():
        # Only include papers that have a summary_path
        summary_path_str = paper.get('summary_path')
        if summary_path_str:
            summary_path = PROJECT_ROOT / summary_path_str
            # Also check that the summary file actually exists
            if summary_path.exists():
                collected_at = paper.get('collected_at', '')
                formatted_time = format_collection_time(collected_at)
                
                display_title = f"[{paper.get('arxiv_id', 'N/A')}] {paper.get('title', 'No Title')} | 📅 {formatted_time}"
                papers.append({
                    "display_title": display_title,
                    "title": paper.get('title', 'No Title'),
                    "collected_at": collected_at or "1970-01-01T00:00:00+00:00"  # Default old date for sorting
                })
                filtered_cache[key] = paper

    # Sort by collection time in descending order (newest first)
    papers.sort(key=lambda x: x["collected_at"], reverse=True)
    
    df = pd.DataFrame(papers)
    return df, filtered_cache # Return df for display, and filtered cache for lookups

def search_papers(df, keyword):
    """Filters the dataframe based on a keyword."""
    if not keyword:
        return df
    # Case-insensitive search in the display title
    return df[df['display_title'].str.contains(keyword, case=False, na=False)]

def get_paper_content(selected_display_title: str, cache_data: dict):
    """
    Given a selected paper's display title, returns its PDF URL and summary markdown.
    """
    if not selected_display_title:
        return "### Select a paper to view its PDF.", "### Select a paper to view its summary."

    # Find the full paper details from the cache using the display title
    # Need to reconstruct the display title to match
    paper_details = None
    for paper in cache_data.values():
        collected_at = paper.get('collected_at', '')
        formatted_time = format_collection_time(collected_at)
        display_title = f"[{paper.get('arxiv_id', 'N/A')}] {paper.get('title', 'No Title')} | 📅 {formatted_time}"
        
        if display_title == selected_display_title:
            paper_details = paper
            break
            
    if not paper_details:
        return "### Paper details not found.", "### Paper details not found."

    # Get PDF URL for the iframe
    pdf_url = paper_details.get('pdf_url')
    pdf_viewer_html = f'<iframe src="{pdf_url}" width="100%" height="800px" style="border:none;"></iframe>' if pdf_url else "### No PDF URL available."

    # Get summary content from the relative path
    summary_content = "### No summary available for this paper."
    summary_path_str = paper_details.get('summary_path')
    if summary_path_str:
        summary_path = PROJECT_ROOT / summary_path_str
        if summary_path.exists():
            summary_content = summary_path.read_text()
        else:
            summary_content = f"### Summary file not found at:\n`{summary_path_str}`"

    return pdf_viewer_html, summary_content

def refresh_data():
    """Reloads the paper data and returns updated components."""
    df, cache_data = load_data()
    choices = df["display_title"].tolist()
    paper_count = len(choices)
    
    # Return the new choices and updated info message
    return (
        gr.Dropdown(choices=choices, value=None),  # Updated dropdown
        cache_data,  # Updated cache state
        f"🔄 Refreshed! Found {paper_count} papers with summaries (sorted by collection time).",  # Status message
        "### Select a paper from the search bar above.",  # Reset PDF viewer
        "### Select a paper from the search bar above."   # Reset summary viewer
    )

# --- Gradio App ---
with gr.Blocks(theme=gr.themes.Soft(), title="Paper Research Interface", css=CUSTOM_CSS) as demo:
    # Inject MathJax for LaTeX rendering and simple resizer
    gr.HTML("""
    <script>
    window.MathJax = {
      tex: {inlineMath: [['$', '$'], ['\\\(', '\\\)']]},
      svg: {fontCache: 'global'}
    };
    </script>
    <script src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js'></script>
    
    <script>
    function initSimpleResizer() {
        const mainRow = document.getElementById('main-row');
        const leftColumn = document.getElementById('left-column');
        const rightColumn = document.getElementById('right-column');
        
        if (!mainRow || !leftColumn || !rightColumn) {
            setTimeout(initSimpleResizer, 500);
            return;
        }
        
        let isResizing = false;
        let startX, startLeftWidth;
        
        // Add event listener to the pseudo-element area
        mainRow.addEventListener('mousedown', (e) => {
            const rect = mainRow.getBoundingClientRect();
            const resizerX = rect.left + (rect.width * 0.6);
            
            // Check if click is near the resizer (within 10px)
            if (Math.abs(e.clientX - resizerX) <= 10) {
                isResizing = true;
                startX = e.clientX;
                startLeftWidth = 60; // Current left width percentage
                
                document.addEventListener('mousemove', handleMouseMove);
                document.addEventListener('mouseup', handleMouseUp);
                e.preventDefault();
            }
        });
        
        function handleMouseMove(e) {
            if (!isResizing) return;
            
            const mainRect = mainRow.getBoundingClientRect();
            const deltaX = e.clientX - startX;
            const deltaPercent = (deltaX / mainRect.width) * 100;
            let newLeftWidth = startLeftWidth + deltaPercent;
            
            // Constrain between 20% and 80%
            newLeftWidth = Math.max(20, Math.min(80, newLeftWidth));
            const newRightWidth = 100 - newLeftWidth;
            
            // Update the CSS custom property for the resizer position
            mainRow.style.setProperty('--resizer-pos', newLeftWidth + '%');
            
            // Update column flexbox properties
            leftColumn.style.flex = newLeftWidth;
            rightColumn.style.flex = newRightWidth;
            
            // Update the CSS ::after position
            const style = document.createElement('style');
            style.textContent = `#main-row::after { left: ${newLeftWidth}% !important; }`;
            document.head.appendChild(style);
        }
        
        function handleMouseUp() {
            isResizing = false;
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        }
    }
    
    // Initialize after DOM loads
    document.addEventListener('DOMContentLoaded', initSimpleResizer);
    setTimeout(initSimpleResizer, 1000);
    </script>
    """)

    # Store data in the app state for performance
    initial_df, full_cache = load_data()
    state_cache = gr.State(full_cache)

    gr.Markdown("# Paper Research Interface")
    gr.Markdown("Search for papers collected by the agent. Only papers with AI-generated summaries are shown. Papers are sorted by collection time (newest first).")
    
    # Add refresh functionality
    with gr.Row():
        with gr.Column(scale=0.8):
            refresh_status = gr.Markdown(f"📊 Currently showing {len(initial_df)} papers with summaries (sorted by collection time).")
        with gr.Column(scale=0.2):
            refresh_button = gr.Button("🔄 Refresh Papers", elem_classes=["refresh-button"])
    
    # A single dropdown for both searching and selecting papers
    search_dropdown = gr.Dropdown(
        label="Search and Select Paper",
        choices=initial_df["display_title"].tolist(),
        value=None,
        interactive=True,
        max_choices=10,
        info="Type to search for a paper by its ID, title, or collection date. Papers are sorted by collection time (newest first)."
    )

    # Two-column layout with resizer
    with gr.Row(elem_id="main-row"):
        with gr.Column(scale=60, elem_id="left-column"):
            gr.Markdown("### 📄 PDF Viewer")
            pdf_viewer = gr.HTML(value="### Select a paper from the search bar above.", elem_id="pdf-viewer")
        
        with gr.Column(scale=40, elem_id="right-column"):
            gr.Markdown("### 🤖 AI Summary")
            summary_viewer = gr.Markdown(value="### Select a paper first to see its summary.", elem_id="summary-viewer")

    # Event handler for when a paper is selected from the dropdown
    search_dropdown.change(
        fn=get_paper_content,
        inputs=[search_dropdown, state_cache],
        outputs=[pdf_viewer, summary_viewer],
        queue=True
    )
    
    # Event handler for refresh button
    refresh_button.click(
        fn=refresh_data,
        inputs=[],
        outputs=[search_dropdown, state_cache, refresh_status, pdf_viewer, summary_viewer],
        queue=True
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=20001, share=True) 