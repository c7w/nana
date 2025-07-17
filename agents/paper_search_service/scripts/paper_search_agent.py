"""
This agent is responsible for going through the paper list and extracting the information.
"""

import yaml
import json
from pathlib import Path
import sys
import hashlib
import re
import argparse

# Add the project root to the Python path BEFORE local imports
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

# Setup logging as the very first thing to ensure it's configured
from tools.log_config import setup_logging
setup_logging()

import logging
from datetime import datetime, timezone
from tools.api.llm import call_llm

from tools.paper.search import find_paper_details
from tools.paper.utils import _normalize_title, _get_config_for_step
from tools.paper.analyze import analyze_paper
from tools.trackers import update_usage
import PyPDF2



# --- Main Agent Logic ---

def load_config():
    """Loads the YAML configuration file."""
    with open(project_root / "config/config.yaml", 'r') as f:
        return yaml.safe_load(f)

def load_cache(cache_path: Path) -> dict:
    """Loads the cache file if it exists."""
    if cache_path.exists():
        with open(cache_path, 'r') as f:
            return json.load(f)
    return {}

def save_cache(cache_path: Path, cache: dict):
    """Saves the cache to a file, sorted by collection date."""
    # Sort the cache items by 'collected_at' descending.
    # Use a default old date for items missing the key to handle old data.
    sorted_items = sorted(
        cache.items(),
        key=lambda item: item[1].get('collected_at', '1970-01-01T00:00:00+00:00'),
        reverse=True
    )
    sorted_cache = dict(sorted_items)
    with open(cache_path, 'w') as f:
        json.dump(sorted_cache, f, indent=2)

def read_input_file(file_path: Path) -> str:
    """Reads the content of the input file."""
    if not file_path.exists():
        logging.error(f"Input file not found at {file_path}")
        dummy_content = "Revisiting the Effectiveness of NeRFs for Dense Mapping https://arxiv.org/abs/2405.09332\nGenerative Pre-training of Diffusion Models"
        file_path.write_text(dummy_content)
        logging.info(f"Created a dummy input file for you at '{file_path.name}'. Please edit it and run again.")
        return dummy_content
    return file_path.read_text()

# --- Citation Extraction Mode Logic (NEW) ---

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extracts all text from a given PDF file."""
    if not pdf_path.exists():
        logging.error(f"PDF file not found at: {pdf_path}")
        return ""
    text = ""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
    except Exception as e:
        logging.error(f"Failed to read or parse PDF file: {e}")
    return text

def find_references_section(full_text: str) -> str:
    """Isolates the 'References' section from the full text of a paper."""
    match = re.search(r'(?is)(references|bibliography|参考文献)\n', full_text)
    if match:
        return full_text[match.start():]
    logging.warning("Could not find a clear 'References' section. Using the last 20% of the document.")
    return full_text[-int(len(full_text) * 0.20):]

def extract_papers_from_citation(config: dict, pdf_path: Path, snippet: str) -> list:
    """Extracts cited paper titles from a snippet using a source PDF."""
    logging.info(f"Starting citation extraction from PDF: {pdf_path.name}")
    full_text = extract_text_from_pdf(pdf_path)
    if not full_text: return []
    references_text = find_references_section(full_text)
    if not references_text:
        logging.error("Could not extract a references section from the PDF.")
        return []

    llm_config = _get_config_for_step(config, 'paper_search_agent', '0_extract_from_citation')
    prompt_path = project_root / 'prompts' / 'paper_search_agent' / '0_extract_from_citation.md'
    prompt_template = prompt_path.read_text()
    
    user_content = f"## Text Snippet:\n\n{snippet}\n\n---\n\n## Reference List:\n\n{references_text}"
    messages = [{"role": "system", "content": prompt_template}, {"role": "user", "content": user_content}]
    
    logging.info(f"Calling model '{llm_config['model']}' to extract citations...")
    message, _ = call_llm(llm_config, messages, is_json=True)
    
    if message and 'content' in message:
        try:
            data = json.loads(message['content'])
            papers = data.get('papers', [])
            if papers:
                logging.info(f"Successfully extracted {len(papers)} cited papers.")
                return [{'title': p} for p in papers] # Return in the format the main loop expects
            else:
                logging.warning("LLM returned a valid response, but no papers were extracted.")
        except (json.JSONDecodeError, KeyError) as e:
            logging.error(f"Error parsing LLM response for citation extraction: {e}")
            logging.error(f"Raw response content: {message['content']}")
    else:
        logging.error("Failed to get a valid response from the LLM for citation extraction.")
    return []

# --- Main Execution Logic ---

def format_input(config: dict, raw_text: str, usage_tracker: dict) -> list:
    """
    Uses an LLM to format the raw text input into a structured list of papers.
    """
    logging.info("---")
    logging.info("Step 1: Formatting input...")
    
    # 1. Get LLM configuration for this step
    step_config_name = '1_input_formatting'
    llm_name = config['agents']['paper_search_agent'][step_config_name]
    llm_config = config['llms'][llm_name]
    
    # 2. Load the prompt
    prompt_path = project_root / 'prompts' / 'paper_search_agent' / f'{step_config_name}.md'
    prompt_template = prompt_path.read_text()
    
    # 3. Construct messages
    messages = [
        {"role": "system", "content": prompt_template},
        {"role": "user", "content": raw_text}
    ]
    
    # 4. Call the LLM
    logging.info(f"Calling model '{llm_config['model']}' for formatting...")
    message, usage = call_llm(llm_config, messages, is_json=True)
    
    # 5. Update usage tracker
    update_usage(usage_tracker, llm_config, usage)

    if message and 'content' in message:
        try:
            content = message['content']
            formatted_data = json.loads(content)
            logging.info("Input formatted successfully.")
            return formatted_data.get('papers', [])
        except (json.JSONDecodeError, KeyError) as e:
            logging.error(f"Error parsing LLM response: {e}")
            logging.error(f"Raw response content: {message['content']}")
            return []
    else:
        logging.error("Failed to get a valid response from the LLM.")
        return []

def main():
    """Main execution flow of the paper search agent."""
    parser = argparse.ArgumentParser(description="Nana Paper Search Agent")
    parser.add_argument(
        '--mode', 
        type=str, 
        default='from_file', 
        choices=['from_file', 'from_citation'],
        help="The input mode for the agent."
    )
    parser.add_argument('--pdf', type=str, help="Path to the source PDF file (for 'from_citation' mode).")
    parser.add_argument('--snippet', type=str, help="Text snippet with citations (for 'from_citation' mode).")
    args = parser.parse_args()

    config = load_config()
    usage_tracker = {}
    
    # Counters for the final report
    cached_details_count = 0
    cached_analysis_count = 0
    
    agent_name = Path(__file__).stem
    agent_storage_path = project_root / 'storage' / agent_name
    agent_storage_path.mkdir(parents=True, exist_ok=True)
    cache_path = agent_storage_path / 'cache.json'
    cache = load_cache(cache_path)

    # --- One-time cache migration ---
    migrated = False
    for key, value in cache.items():
        if 'summary_path' in value and value['summary_path'] and Path(value['summary_path']).is_absolute():
            value['summary_path'] = str(Path(value['summary_path']).relative_to(project_root))
            migrated = True
        if 'collected_at' not in value:
            summary_mtime = datetime.fromtimestamp(0, timezone.utc)
            if 'summary_path' in value and value['summary_path']:
                try:
                    summary_mtime = datetime.fromtimestamp((project_root / value['summary_path']).stat().st_mtime, timezone.utc)
                except (FileNotFoundError, TypeError):
                    pass
            value['collected_at'] = summary_mtime.isoformat()
            migrated = True
    if migrated:
        logging.info("Performed one-time migration on cache.json.")
    # --- End migration ---
    
    paper_list = []
    if args.mode == 'from_file':
        logging.info("Running in 'from_file' mode.")
        input_file_path = project_root / 'agents' / f'{agent_name}.in'
        raw_input_text = read_input_file(input_file_path)
        if raw_input_text.strip():
            paper_list = format_input(config, raw_input_text, usage_tracker)
    elif args.mode == 'from_citation':
        logging.info("Running in 'from_citation' mode.")
        if not args.pdf or not args.snippet:
            logging.error("--pdf and --snippet arguments are required for 'from_citation' mode.")
            return
        pdf_path = Path(args.pdf)
        paper_list = extract_papers_from_citation(config, pdf_path, args.snippet)

    if not paper_list:
        logging.error("Could not generate a paper list to process. Aborting.")
        return
        
    logging.info("\n--- Papers to Process ---")
    logging.info(json.dumps(paper_list, indent=2))
    logging.info("--------------------------\n")

    # Step 2: Find Paper Details (Recall)
    logging.info("---")
    logging.info("Step 2: Finding paper details (PDF links)...")
    recalled_papers = []
    failed_recall = []

    for paper in paper_list:
        logging.info(f"\nProcessing: {paper['title']}")
        cache_key = _normalize_title(paper['title'])
        provided_url = paper.get('url', '').strip() if paper.get('url') else None
        
        # Check if we should use cache or update with new URL
        use_cache = (
            cache_key in cache and 
            'pdf_url' in cache[cache_key] and 
            cache[cache_key]['pdf_url'] and  # Cache has valid PDF URL
            not provided_url  # No new URL provided
        )
        
        if use_cache:
            logging.info("Found paper details in cache.")
            paper.update(cache[cache_key])
            recalled_papers.append(paper)
            cached_details_count += 1
            continue
        
        # If URL is provided or cache is missing/incomplete, get/update details
        if provided_url and cache_key in cache:
            logging.info("Updating cached paper with provided URL.")
        elif provided_url:
            logging.info("Using provided URL for new paper.")
        else:
            logging.info("No URL provided, searching for paper details.")

        details = find_paper_details(paper, config, usage_tracker)
        if details:
            paper.update(details)
            # Add/update collected_at timestamp
            details['collected_at'] = datetime.now(timezone.utc).isoformat()
            cache[cache_key] = details
            recalled_papers.append(paper)
        else:
            failed_recall.append(paper)

    logging.info("\n--- Recall Results ---")
    logging.info(f"Successfully found details for: {len(recalled_papers)} paper(s)")
    if failed_recall:
        logging.warning(f"Failed to find details for: {len(failed_recall)} paper(s)")
    logging.info("----------------------\n")

    # Step 3: Analyze Papers
    logging.info("---")
    logging.info("Step 3: Analyzing papers...")
    analyzed_papers = []
    failed_analysis = []

    for paper in recalled_papers:
        cache_key = _normalize_title(paper['title'])
        if cache_key in cache and 'summary_path' in cache[cache_key]:
            logging.info(f"Found analysis in cache for '{paper['title']}'. Skipping.")
            paper.update(cache[cache_key])
            analyzed_papers.append(paper)
            cached_analysis_count += 1
            continue
        
        analysis_results = analyze_paper(paper, config, usage_tracker)
        if analysis_results:
            # Save results to a date-based, human-readable directory
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            paper_id = paper.get('arxiv_id', 'unknown_id')
            paper_dir = agent_storage_path / today_str / paper_id
            paper_dir.mkdir(parents=True, exist_ok=True)
            
            summary_path = paper_dir / 'summary.md'
            
            with open(summary_path, 'w') as f:
                f.write(analysis_results['summary'])
            
            # Use relative path for storage
            relative_summary_path = summary_path.relative_to(project_root)
            
            paper['summary_path'] = str(relative_summary_path)

            # The cache key may have changed if the title was canonicalized during recall.
            # We must ensure the entry exists for the potentially new key before updating.
            if cache_key not in cache:
                # This is a new entry, probably due to a title change.
                # We'll create it and copy over the existing paper details.
                cache[cache_key] = paper.copy()

            # Now, update the entry with the summary path.
            cache[cache_key]['summary_path'] = str(relative_summary_path)
            cache[cache_key]['collected_at'] = datetime.now(timezone.utc).isoformat()
            
            # Save cache immediately after each analysis
            save_cache(cache_path, cache)
            
            analyzed_papers.append(paper)
        else:
            failed_analysis.append(paper)

    # Finalization
    save_cache(cache_path, cache)

    # Step 4: Final Report
    logging.info("\n\n---")
    logging.info("--- Final Report ---")
    logging.info("---")
    logging.info(f"Total papers in input: {len(paper_list)}")
    logging.info(f"\n[Recall Stage]")
    logging.info(f"Successfully found details for {len(recalled_papers)} papers ({cached_details_count} from cache).")
    logging.warning(f"Failed to find details for {len(failed_recall)} papers.")
    if failed_recall:
        logging.warning("Failed papers:")
        for paper in failed_recall:
            logging.warning(f"  - {paper['title']}")
    
    logging.info(f"\n[Analysis Stage]")
    logging.info(f"Successfully analyzed {len(analyzed_papers)} papers ({cached_analysis_count} from cache).")
    logging.warning(f"Failed to analyze {len(failed_analysis)} papers.")
    if failed_analysis:
        logging.warning("Failed papers:")
        for paper in failed_analysis:
            logging.warning(f"  - {paper['title']}")

    logging.info("\n--- Token Usage & Cost ---")
    USD_TO_CNY_RATE = 7.17
    total_cost_usd = 0.0

    if not usage_tracker:
        logging.info("No new API calls were made.")
    else:
        for model, data in usage_tracker.items():
            cost_usd = data.get('cost_usd', 0.0)
            total_cost_usd += cost_usd
            logging.info(f"Model: {model}")
            logging.info(f"  Input Tokens: {data['input']}")
            logging.info(f"  Output Tokens: {data['output']}")
            logging.info(f"  Estimated Cost (USD): ${cost_usd:.6f}")
        
        total_cost_cny = total_cost_usd * USD_TO_CNY_RATE
        logging.info("\n--- Total Estimated Cost ---")
        logging.info(f"USD: ${total_cost_usd:.4f}")
        logging.info(f"CNY: ¥{total_cost_cny:.4f}")
    logging.info("--------------------------")


if __name__ == "__main__":
    main()

