import gradio as gr
import json
from pathlib import Path
import pandas as pd

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
"""

def load_data():
    """Loads, sorts, and prepares the paper data for display."""
    if not CACHE_FILE.exists():
        return pd.DataFrame(columns=["display_title", "title"]), {}
    
    with open(CACHE_FILE, 'r') as f:
        # The cache is pre-sorted by the agent, so we load it as is.
        cache_data = json.load(f)

    papers = []
    for _, paper in cache_data.items():
        display_title = f"[{paper.get('arxiv_id', 'N/A')}] {paper.get('title', 'No Title')}"
        papers.append({
            "display_title": display_title,
            "title": paper.get('title', 'No Title'), # Keep original title for lookup
        })

    df = pd.DataFrame(papers)
    return df, cache_data # Return df for display, and full cache for lookups

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
    paper_details = None
    for paper in cache_data.values():
        display_title = f"[{paper.get('arxiv_id', 'N/A')}] {paper.get('title', 'No Title')}"
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

# --- Gradio App ---
with gr.Blocks(theme=gr.themes.Soft(), title="Paper Research Interface", css=CUSTOM_CSS) as demo:
    # Store data in the app state for performance
    initial_df, full_cache = load_data()
    state_cache = gr.State(full_cache)

    gr.Markdown("# Paper Research Interface")
    gr.Markdown("Search for papers collected by the agent. Select a paper to view its PDF and AI-generated summary.")
    
    # A single dropdown for both searching and selecting papers
    search_dropdown = gr.Dropdown(
        label="Search and Select Paper",
        choices=initial_df["display_title"].tolist(),
        value=None,
        interactive=True,
        max_choices=10,
        info="Type to search for a paper by its ID or title. The list will filter as you type."
    )

    # Side-by-side layout for the PDF and summary
    with gr.Row():
        with gr.Column(scale=0.4):
            gr.Markdown("### PDF Viewer")
            pdf_viewer = gr.HTML("### Select a paper from the search bar above.")
        with gr.Column(scale=0.6):
            gr.Markdown("### AI Summary")
            summary_viewer = gr.Markdown("### Select a paper from the search bar above.", elem_id="summary-viewer")

    # Event handler for when a paper is selected from the dropdown
    search_dropdown.change(
        fn=get_paper_content,
        inputs=[search_dropdown, state_cache],
        outputs=[pdf_viewer, summary_viewer],
        queue=True
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=20001, share=True) 