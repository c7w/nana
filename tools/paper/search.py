import requests
import arxiv
from pathlib import Path
import re
import json
import sys
from ddgs import DDGS
import logging

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[2] # Adjust path for new location
sys.path.append(str(project_root))

from tools.api.llm import call_llm
from tools.paper.utils import _normalize_title
from ddgs import DDGS
from .utils import _get_config_for_step
from ..trackers import update_usage

def _clean_filename(title: str) -> str:
    """Removes invalid characters from a string to make it a valid filename."""
    s = re.sub(r'[\\/*?:"<>|]', "", title)
    return (s[:100] + '..') if len(s) > 100 else s

def _get_best_match_from_results(query_title: str, results: list, config: dict, usage_tracker: dict) -> arxiv.Result | None:
    """Uses rules and an LLM to find the best match from a list of search results."""
    
    # --- Strategy 1: Rule-based exact match ---
    normalized_query = _normalize_title(query_title)
    for i, result in enumerate(results):
        normalized_result_title = _normalize_title(result.title)
        if normalized_query == normalized_result_title:
            logging.info(f"Found rule-based exact match at index {i+1}: '{result.title}'")
            return result
    
    # --- Strategy 2: LLM-based semantic match (as the final fallback) ---
    logging.info("No exact match found. Asking LLM judge as a fallback...")
    step_config_name = '2_recall_papers'
    agent_config = config['agents'].get('paper_search_agent', {})
    if step_config_name not in agent_config:
        logging.warning("LLM judge for paper recall not configured. Picking first result.")
        return results[0] if results else None

    llm_name = agent_config[step_config_name]
    llm_config = config['llms'][llm_name]
    
    prompt_path = project_root / 'prompts' / 'paper_search_agent' / f'{step_config_name}.md'
    prompt_template = prompt_path.read_text()
    
    formatted_results = "\n".join([f"{i+1}. {result.title}" for i, result in enumerate(results)])
    user_content = f"Original Query: `{query_title}`\n\nSearch Results:\n{formatted_results}"
    
    messages = [
        {"role": "system", "content": prompt_template},
        {"role": "user", "content": user_content}
    ]

    logging.info(f"Asking LLM judge ('{llm_config['model']}') to pick the best match...")
    message, usage = call_llm(llm_config, messages, is_json=True)

    update_usage(usage_tracker, llm_config, usage)

    if message and 'content' in message:
        try:
            data = json.loads(message['content'])
            index = int(data.get("best_match_index", 0))
            logging.info(f"LLM judge picked index: {index}")
            if index > 0 and index <= len(results):
                return results[index - 1]
            return None
        except (json.JSONDecodeError, ValueError, KeyError):
            logging.error(f"Error parsing LLM judge response: {message['content']}")
            return None
    
    return None


def find_paper_details(paper_info: dict, config: dict, usage_tracker: dict) -> dict | None:
    """
    Finds the correct paper metadata (incl. PDF URL) using a multi-step search strategy.
    """
    title = paper_info.get('title', 'untitled')
    url = paper_info.get('url')
    
    # --- Step 1: Handle provided ArXiv URL ---
    if url and 'arxiv.org' in url:
        try:
            arxiv_id = arxiv.Client().get_query(id_list=[url.split('/')[-1]])[0].entry_id
            pdf_url = url.replace('/abs/', '/pdf/') if '/abs/' in url else url
            logging.info(f"Successfully derived details from provided ArXiv URL for '{title}'")
            return {'title': title, 'pdf_url': pdf_url, 'arxiv_id': arxiv_id.split('/')[-1]}
        except Exception as e:
            logging.warning(f"Could not resolve provided ArXiv URL {url}: {e}")

    # --- Step 2: Multi-source search and verification ---
    all_results = []
    processed_ids = set()

    # --- Source A: Direct ArXiv Search ---
    logging.info(f"Searching ArXiv for title: '{title}'")
    try:
        arxiv_search = arxiv.Search(query=title, max_results=5)
        for r in arxiv_search.results():
            if r.entry_id not in processed_ids:
                all_results.append(r)
                processed_ids.add(r.entry_id)
    except Exception as e:
        logging.error(f"An error occurred during ArXiv search: {e}")

    # --- Source B: DuckDuckGo Fallback Search ---
    logging.info("Searching DuckDuckGo as a fallback...")
    try:
        ddgs_results = DDGS().text(f'"{title}" site:arxiv.org', max_results=5)
        arxiv_urls_from_ddgs = [r['href'] for r in ddgs_results if 'arxiv.org/abs' in r.get('href', '')]
        if arxiv_urls_from_ddgs:
            ddgs_ids = [url.split('/')[-1] for url in arxiv_urls_from_ddgs]
            ddgs_ids_to_fetch = [i for i in ddgs_ids if i not in processed_ids]
            if ddgs_ids_to_fetch:
                logging.info(f"Found {len(ddgs_ids_to_fetch)} new ArXiv links from DuckDuckGo. Fetching details...")
                ddgs_arxiv_results = arxiv.Search(id_list=ddgs_ids_to_fetch).results()
                for r in ddgs_arxiv_results:
                     if r.entry_id not in processed_ids:
                        all_results.append(r)
                        processed_ids.add(r.entry_id)
    except Exception as e:
        logging.error(f"An error occurred during DuckDuckGo search: {e}")
    
    if not all_results:
        logging.warning(f"All search attempts failed for '{title}'.")
        return None

    # --- Final Verification ---
    logging.info(f"Found a total of {len(all_results)} unique candidates. Verifying...")
    chosen_paper = _get_best_match_from_results(title, all_results, config, usage_tracker)
    
    if chosen_paper:
        logging.info(f"Confirmed match: '{chosen_paper.title}'")
        return {
            'title': chosen_paper.title,
            'pdf_url': chosen_paper.pdf_url,
            'arxiv_id': chosen_paper.entry_id.split('/')[-1].split('v')[0] # Clean version numbers
        }
    
    logging.warning(f"Could not confirm a final match for '{title}'.")
    return None 