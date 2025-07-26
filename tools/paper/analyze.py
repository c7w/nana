import base64
import requests
from pathlib import Path
import sys
import PyPDF2
from io import BytesIO
import logging

# Add the project root to the Python path to allow importing from 'tools'
project_root = Path(__file__).resolve().parents[2] # Adjust path for new location
sys.path.append(str(project_root))

from tools.api.llm import call_llm
from tools.paper.utils import _normalize_title
from tools.trackers import update_usage
import json


def _get_pdf_content_as_base64(pdf_url: str) -> str | None:
    """Downloads a PDF and returns its content as a base64 encoded string."""
    try:
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()
        
        # Check file size (limit to 10MB)
        file_size = len(response.content)
        max_size = 10 * 1024 * 1024  # 10MB in bytes
        
        if file_size > max_size:
            logging.warning(f"PDF at {pdf_url} is too large ({file_size / 1024 / 1024:.1f}MB). Max size is {max_size / 1024 / 1024}MB.")
            return None
        
        # Check if the content is actually a PDF
        if 'application/pdf' not in response.headers.get('Content-Type', ''):
            logging.warning(f"URL did not return a PDF. Content-Type: {response.headers.get('Content-Type')}")
            return None

        # Read with PyPDF2 to check for validity and extract text
        with BytesIO(response.content) as pdf_file:
            try:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                if len(pdf_reader.pages) > 0:
                     # Re-read the bytes for base64 encoding
                    logging.info(f"PDF size: {file_size / 1024 / 1024:.1f}MB, Pages: {len(pdf_reader.pages)}")
                    return base64.b64encode(response.content).decode('utf-8')
                else:
                    logging.warning(f"PDF at {pdf_url} is empty or corrupted.")
                    return None
            except PyPDF2.errors.PdfReadError:
                logging.warning(f"Could not read PDF from {pdf_url}. It may be corrupted.")
                return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download PDF from {pdf_url}: {e}")
        return None

def analyze_paper(paper_info: dict, config: dict, usage_tracker: dict) -> dict | None:
    """
    Analyzes a paper from its PDF URL, performing a summary.

    Returns:
        A dictionary {'summary': str} or None on failure.
    """
    pdf_url = paper_info.get('pdf_url')
    if not pdf_url:
        logging.warning(f"No PDF URL for '{paper_info['title']}', skipping analysis.")
        return None

    logging.info(f"Analyzing paper: {paper_info.get('title')}")
    base64_pdf = _get_pdf_content_as_base64(pdf_url)
    if not base64_pdf:
        logging.error(f"Could not retrieve or process PDF for '{paper_info['title']}'.")
        return None
    
    data_url = f"data:application/pdf;base64,{base64_pdf}"
    pdf_filename = f"{_normalize_title(paper_info.get('title', 'untitled'))}.pdf"
    
    plugins = [{"id": "file-parser", "pdf": {"engine": "pdf-text"}}]

    # --- Task: Summarization ---
    summary_step_name = '3_2_paper_summary'
    summary_llm_name = config['agents']['paper_search_agent'][summary_step_name]
    summary_llm_config = config['llms'][summary_llm_name]
    summary_prompt = (project_root / 'prompts' / 'paper_search_agent' / f'{summary_step_name}.md').read_text()

    summary_messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": summary_prompt},
                {
                    "type": "file", 
                    "file": {"filename": pdf_filename, "file_data": data_url}
                },
            ]
        }
    ]
    logging.info(f"Requesting summary from '{summary_llm_config['model']}'...")
    
    plugins = [{"id": "file-parser", "pdf": {"engine": "pdf-text"}}]
    message, usage = call_llm(summary_llm_config, summary_messages, is_json=False, plugins=plugins)
    
    update_usage(usage_tracker, summary_llm_config, usage)

    if message and 'content' in message:
        analysis_content = message['content']
        # The prompt asks for a structured markdown, so we just check for content.
        if analysis_content and analysis_content.strip():
            logging.info(f"Successfully analyzed '{paper_info['title']}'. Summary length: {len(analysis_content)} characters.")
            return {
                'summary': analysis_content,
            }
        else:
            logging.error(f"LLM returned an empty analysis for '{paper_info['title']}'. Response was: '{analysis_content}'")
            return None
    else:
        logging.error(f"LLM analysis failed for '{paper_info['title']}'. Message structure: {message}")
        return None