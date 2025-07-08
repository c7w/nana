"""
Paper search functionality using combined arXiv + OpenAlex strategy.
"""

import logging
import traceback
import json
from tools.paper.utils import _normalize_title
from tools.trackers import update_usage
from tools.paper.search_openalex import combined_search_with_llm_fallback
from pathlib import Path

# Get project root for prompt loading
import sys
project_root = Path(__file__).resolve().parents[2]

def find_paper_details(paper: dict, config: dict, usage_tracker: dict) -> dict:
    """
    Finds detailed information about a paper including PDF URL and arXiv ID.
    If a URL is provided in the input, use it directly; otherwise use combined search.
    """
    title = paper.get('title', '').strip()
    provided_url = paper.get('url', '').strip() if paper.get('url') else None
    
    if not title:
        logging.error("Cannot search for paper without title")
        return {}

    logging.info(f"Searching for: {title}")
    
    # If URL is provided, use it directly
    if provided_url:
        logging.info(f"Using provided URL: {provided_url}")
        return _use_provided_url(title, provided_url)

    try:
        # Use the new combined search strategy
        result = combined_search_with_llm_fallback(title, max_results_per_source=10)
        
        if result:
            # Format the result in the expected structure
            formatted_result = _format_result(result)
            logging.info(f"✓ Successfully found paper via combined search")
            return formatted_result
        else:
            logging.error(f"No suitable match found for: {title}")
            return {}
        
    except Exception as e:
        logging.error(f"Error during paper search: {e}")
        logging.error(traceback.format_exc())
        return {}

def _use_provided_url(title: str, url: str) -> dict:
    """
    Use the URL provided by the user to generate paper details.
    Attempts to extract arXiv ID and generate PDF URL from the provided URL.
    """
    import re
    
    arxiv_id = None
    pdf_url = None
    doi = None
    
    # Extract arXiv ID from various URL patterns
    arxiv_patterns = [
        r'arxiv\.org/abs/(\d+\.\d+)',
        r'arxiv\.org/pdf/(\d+\.\d+)',
        r'arxiv\.org/(?:abs|pdf)/(\d+\.\d+)(?:v\d+)?(?:\.pdf)?'
    ]
    
    for pattern in arxiv_patterns:
        match = re.search(pattern, url)
        if match:
            arxiv_id = match.group(1)
            break
    
    # If we found arXiv ID, generate PDF URL
    if arxiv_id:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        logging.info(f"  ✓ Extracted arXiv ID from URL: {arxiv_id}")
        logging.info(f"  ✓ Generated PDF URL: {pdf_url}")
    else:
        # If not arXiv, check if it's already a PDF URL
        if url.endswith('.pdf') or 'pdf' in url.lower():
            pdf_url = url
            logging.info(f"  ✓ Using provided PDF URL: {pdf_url}")
        else:
            # Try to convert to PDF URL for common patterns
            if 'arxiv.org/abs/' in url:
                pdf_url = url.replace('/abs/', '/pdf/') + '.pdf'
                logging.info(f"  ✓ Converted abs URL to PDF: {pdf_url}")
            else:
                # Use as-is, might be a direct PDF link
                pdf_url = url
                logging.info(f"  ✓ Using URL as PDF: {pdf_url}")
    
    return {
        'title': title,
        'authors': [],  # Unknown from URL alone
        'publication_year': None,  # Unknown from URL alone
        'doi': doi,
        'pdf_url': pdf_url,
        'arxiv_id': arxiv_id,
        'search_engine': 'provided_url'
    }

def _format_result(result: dict) -> dict:
    """Format the result in the expected structure."""
    arxiv_id = result.get('arxiv_id')
    pdf_url = result.get('pdf_url')
    doi = result.get('doi')
    
    # Try to extract arXiv ID from DOI if not already present
    if not arxiv_id and doi:
        import re
        arxiv_match = re.search(r'arxiv\.(\d+\.\d+)', doi)
        if arxiv_match:
            arxiv_id = arxiv_match.group(1)
            logging.info(f"  ✓ Extracted arXiv ID from DOI: {arxiv_id}")
    
    # Generate PDF URL from arXiv ID if not already present
    if arxiv_id and not pdf_url:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        logging.info(f"  ✓ Generated PDF URL from arXiv ID: {pdf_url}")
    
    return {
        'title': result.get('title', ''),
        'authors': result.get('authors', []),
        'publication_year': result.get('publication_year'),
        'doi': doi,
        'pdf_url': pdf_url,
        'arxiv_id': arxiv_id,
        'search_engine': f"combined_{result.get('source', 'unknown')}"
    } 