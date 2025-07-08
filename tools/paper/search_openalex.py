"""
OpenAlex and arXiv API-based paper search functionality.
Combined search strategy for maximum precision and recall.
"""

import requests
import logging
from urllib.parse import quote_plus
import time
import json
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET
from pathlib import Path

def search_arxiv(title: str, max_results: int = 10) -> List[Dict]:
    """
    Search for papers using the arXiv API.
    Uses multiple search strategies for better recall.
    
    Args:
        title: The title of the paper to search for
        max_results: Maximum number of results to return
        
    Returns:
        List of paper dictionaries with metadata
    """
    base_url = "http://export.arxiv.org/api/query"
    
    try:
        logging.info(f"Searching arXiv for: {title}")
        
        # Strategy 1: Exact title search
        query1 = f'ti:"{title}"'
        params1 = {
            'search_query': query1,
            'start': 0,
            'max_results': max_results,
            'sortBy': 'relevance',
            'sortOrder': 'descending'
        }
        
        response1 = requests.get(base_url, params=params1, timeout=30)
        response1.raise_for_status()
        
        results = _parse_arxiv_response(response1.content)
        
        # If exact title search found results, return them
        if results:
            logging.info(f"Found {len(results)} results from arXiv (exact title)")
            return results
        
        # Strategy 2: Keywords search as fallback
        logging.info("Exact title search failed, trying keywords search...")
        
        # Extract meaningful keywords (remove common words)
        import re
        # Remove common academic words and punctuation
        keywords = re.sub(r'\b(a|an|the|and|or|of|for|in|on|at|to|with|by|from)\b', '', title.lower())
        keywords = re.sub(r'[^\w\s]', ' ', keywords)  # Remove punctuation
        keywords = ' '.join(keywords.split())  # Normalize whitespace
        
        query2 = f'all:{keywords}'
        params2 = {
            'search_query': query2,
            'start': 0,
            'max_results': max_results,
            'sortBy': 'relevance',
            'sortOrder': 'descending'
        }
        
        response2 = requests.get(base_url, params=params2, timeout=30)
        response2.raise_for_status()
        
        results = _parse_arxiv_response(response2.content)
        logging.info(f"Found {len(results)} results from arXiv (keywords)")
        return results
        
    except Exception as e:
        logging.error(f"Error searching arXiv: {e}")
        return []

def _parse_arxiv_response(xml_content: bytes) -> List[Dict]:
    """
    Parse arXiv API XML response into our standard format.
    
    Args:
        xml_content: Raw XML response from arXiv API
        
    Returns:
        List of paper dictionaries
    """
    try:
        # Parse XML response
        root = ET.fromstring(xml_content)
        namespace = {'atom': 'http://www.w3.org/2005/Atom', 
                    'arxiv': 'http://arxiv.org/schemas/atom'}
        
        entries = root.findall('atom:entry', namespace)
        results = []
        
        for entry in entries:
            try:
                # Extract arXiv ID from ID URL
                id_url = entry.find('atom:id', namespace).text
                arxiv_id = id_url.split('/')[-1]
                if 'v' in arxiv_id:  # Remove version number
                    arxiv_id = arxiv_id.split('v')[0]
                
                # Extract title
                title_elem = entry.find('atom:title', namespace)
                paper_title = title_elem.text.strip() if title_elem is not None else ''
                # Normalize title whitespace
                paper_title = ' '.join(paper_title.split())
                
                # Extract authors
                authors = []
                for author in entry.findall('atom:author', namespace):
                    name_elem = author.find('atom:name', namespace)
                    if name_elem is not None:
                        authors.append(name_elem.text.strip())
                
                # Extract publication date
                published_elem = entry.find('atom:published', namespace)
                publication_year = None
                if published_elem is not None:
                    try:
                        publication_year = int(published_elem.text[:4])
                    except (ValueError, TypeError):
                        pass
                
                # Extract DOI if available
                doi = None
                doi_elem = entry.find('arxiv:doi', namespace)
                if doi_elem is not None:
                    doi = doi_elem.text.strip()
                
                result = {
                    'title': paper_title,
                    'authors': authors,
                    'publication_year': publication_year,
                    'doi': doi,
                    'pdf_url': f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                    'arxiv_id': arxiv_id,
                    'source': 'arxiv'
                }
                
                results.append(result)
                
            except Exception as e:
                logging.warning(f"Error processing arXiv entry: {e}")
                continue
        logging.info(f"Found {len(results)} results from arXiv")
        logging.info(f"Results: {results}")
        return results
        
    except Exception as e:
        logging.error(f"Error parsing arXiv response: {e}")
        return []

def search_openalex(title: str, max_results: int = 10) -> List[Dict]:
    """
    Search for papers using the OpenAlex API.
    
    Args:
        title: The title of the paper to search for (will use complete title)
        max_results: Maximum number of results to return from API (default 10 for better recall)
        
    Returns:
        List of paper dictionaries with metadata, sorted by relevance score
    """
    # OpenAlex API endpoint for works
    base_url = "https://api.openalex.org/works"
    
    try:
        logging.info(f"Searching OpenAlex for: {title}")
        # Use the complete title, not just keywords
        encoded_query = title.replace(' ', '%20')
        url = f"{base_url}?search={encoded_query}&per-page={min(max_results, 25)}"
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        works = data.get('results', [])
        
        if not works:
            logging.warning(f"No results found for '{title}' in OpenAlex")
            return []
        
        # Process results
        processed_results = []
        
        for work in works:
            try:
                result = {
                    'title': work.get('display_name', ''),
                    'authors': [],
                    'publication_year': work.get('publication_year'),
                    'doi': work.get('doi'),
                    'pdf_url': None,
                    'arxiv_id': None,
                    'source': 'openalex'
                }
                
                # Extract authors safely
                authorships = work.get('authorships', [])
                for authorship in authorships:
                    if authorship and authorship.get('author') and authorship['author'].get('display_name'):
                        result['authors'].append(authorship['author']['display_name'])
                
                # Extract arXiv ID from various sources
                arxiv_id = None
                
                # Check primary location
                primary_location = work.get('primary_location')
                if primary_location and primary_location.get('source'):
                    source = primary_location['source']
                    if source and source.get('display_name') == 'arXiv':
                        # Extract arXiv ID from URL pattern
                        pdf_url = primary_location.get('pdf_url', '')
                        if pdf_url and 'arxiv.org' in pdf_url:
                            import re
                            match = re.search(r'arxiv\.org/(?:pdf/|abs/)?(\d+\.\d+)', pdf_url)
                            if match:
                                arxiv_id = match.group(1)
                
                # Check all locations for arXiv
                if not arxiv_id:
                    for location in work.get('locations', []):
                        if not location:
                            continue
                        source = location.get('source')
                        if source and source.get('display_name'):
                            if 'arxiv' in source.get('display_name', '').lower():
                                pdf_url = location.get('pdf_url', '')
                                if pdf_url and 'arxiv.org' in pdf_url:
                                    import re
                                    match = re.search(r'arxiv\.org/(?:pdf/|abs/)?(\d+\.\d+)', pdf_url)
                                    if match:
                                        arxiv_id = match.group(1)
                                        break
                
                # Check external IDs
                if not arxiv_id:
                    external_ids = work.get('ids', {})
                    if external_ids and 'arxiv' in external_ids:
                        arxiv_url = external_ids['arxiv']
                        if arxiv_url:
                            import re
                            match = re.search(r'arxiv\.org/(?:abs/|pdf/)?(\d+\.\d+)', arxiv_url)
                            if match:
                                arxiv_id = match.group(1)
                
                result['arxiv_id'] = arxiv_id
                
                # Determine PDF URL
                pdf_url = None
                if arxiv_id:
                    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                elif primary_location and primary_location.get('pdf_url'):
                    pdf_url = primary_location['pdf_url']
                else:
                    # Look for any available PDF
                    for location in work.get('locations', []):
                        if location.get('pdf_url'):
                            pdf_url = location['pdf_url']
                            break
                
                result['pdf_url'] = pdf_url
                processed_results.append(result)
                
            except Exception as e:
                logging.warning(f"Error processing OpenAlex result: {e}. Skipping this result.")
                continue
        
        logging.info(f"Found {len(processed_results)} results from OpenAlex")
        logging.info(f"Results: {processed_results}")
        return processed_results
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Error searching OpenAlex: {e}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error in OpenAlex search: {e}")
        return []

def combined_search_with_llm_fallback(title: str, max_results_per_source: int = 10) -> Optional[Dict]:
    """
    Combined search strategy: arXiv + OpenAlex with exact matching and LLM fallback.
    
    Args:
        title: The title of the paper to search for
        max_results_per_source: Maximum results from each search engine
        
    Returns:
        Best matching paper or None if no good match found
    """
    logging.info(f"Starting combined search for: {title}")
    
    # Step 1: Search both arXiv and OpenAlex
    arxiv_results = search_arxiv(title, max_results_per_source)
    openalex_results = search_openalex(title, max_results_per_source)
    
    # Step 2: Merge results and deduplicate
    all_results = []
    seen_titles = set()
    
    # Add arXiv results first (they have priority)
    for result in arxiv_results:
        result_title = result.get('title', '').strip().lower()
        if result_title and result_title not in seen_titles:
            all_results.append(result)
            seen_titles.add(result_title)
    
    # Add OpenAlex results, avoiding duplicates
    for result in openalex_results:
        if result is None:
            continue
        title_text = result.get('title')
        if not title_text:
            continue
        result_title = title_text.strip().lower()
        if result_title and result_title not in seen_titles:
            all_results.append(result)
            seen_titles.add(result_title)
    
    if not all_results:
        logging.warning(f"No results found from any source for: {title}")
        return None
    
    logging.info(f"Combined search found {len(all_results)} unique results")
    
    # Step 3: Look for exact title match with arXiv ID and PDF URL
    title_lower = title.strip().lower()
    for result in all_results:
        result_title = result.get('title', '').strip().lower()
        arxiv_id = result.get('arxiv_id')
        pdf_url = result.get('pdf_url')
        
        if title_lower == result_title and arxiv_id and pdf_url:
            logging.info(f"✓ Found exact title match with arXiv content: {result.get('title')}")
            logging.info(f"  arXiv ID: {arxiv_id}")
            logging.info(f"  PDF URL: {pdf_url}")
            logging.info(f"  Source: {result.get('source', 'unknown')}")
            return result
    
    # Step 4: If no exact match with arXiv, use LLM to judge the best match
    logging.info("No exact match with arXiv found. Using LLM to judge best match...")
    
    # Prepare results for LLM (limit to top 20 for cost efficiency)
    llm_candidates = all_results[:20]
    
    return _select_best_match_with_llm(title, llm_candidates)

def _select_best_match_with_llm(original_title: str, candidates: List[Dict]) -> Optional[Dict]:
    """
    Use LLM to select the best matching paper from candidates.
    
    Args:
        original_title: The original paper title query
        candidates: List of candidate papers
        
    Returns:
        Best matching paper or None if no good match
    """
    from tools.api.llm import call_llm
    from tools.paper.utils import _get_config_for_step
    
    # Get project root for prompt loading
    project_root = Path(__file__).resolve().parents[2]
    
    try:
        # Load configuration (we need a minimal config for LLM)
        import yaml
        config_path = project_root / "config/config.yaml"
        if not config_path.exists():
            logging.error("config.yaml not found. Cannot use LLM for result selection.")
            return None
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Get LLM configuration for recall step
        llm_config = _get_config_for_step(config, 'paper_search_agent', '2_recall_papers')
        
        # Load prompt template
        prompt_path = project_root / 'prompts' / 'paper_search_agent' / '2_recall_papers.md'
        prompt_template = prompt_path.read_text()
        
        # Format candidates for LLM
        candidate_list = []
        for i, candidate in enumerate(candidates, 1):
            title = candidate.get('title', 'No title')
            authors = candidate.get('authors', [])
            year = candidate.get('publication_year')
            arxiv_id = candidate.get('arxiv_id')
            source = candidate.get('source', 'unknown')
            
            author_str = ', '.join(authors[:3])
            if len(authors) > 3:
                author_str += '...'
            
            line = f"{i}. {title}"
            if author_str:
                line += f" (Authors: {author_str})"
            if year:
                line += f" (Year: {year})"
            if arxiv_id:
                line += f" (arXiv: {arxiv_id})"
            line += f" (Source: {source})"
            
            candidate_list.append(line)
        
        # Construct user message
        user_content = f"Original Query: `{original_title}`\n\nSearch Results:\n" + '\n'.join(candidate_list)
        
        messages = [
            {"role": "system", "content": prompt_template},
            {"role": "user", "content": user_content}
        ]
        
        logging.info(f"Calling LLM ({llm_config['model']}) to select best match...")
        message, usage = call_llm(llm_config, messages, is_json=True)
        
        if message and 'content' in message:
            try:
                response_data = json.loads(message['content'])
                best_match_index = response_data.get('best_match_index', 0)
                
                if best_match_index == 0:
                    logging.info("LLM determined no good match found")
                    return None
                elif 1 <= best_match_index <= len(candidates):
                    selected_paper = candidates[best_match_index - 1]
                    logging.info(f"✓ LLM selected result #{best_match_index}: {selected_paper.get('title')}")
                    logging.info(f"  arXiv ID: {selected_paper.get('arxiv_id', 'None')}")
                    logging.info(f"  PDF URL: {selected_paper.get('pdf_url', 'None')}")
                    logging.info(f"  Source: {selected_paper.get('source', 'unknown')}")
                    return selected_paper
                else:
                    logging.error(f"LLM returned invalid index: {best_match_index}")
                    return None
                    
            except (json.JSONDecodeError, KeyError) as e:
                logging.error(f"Error parsing LLM response: {e}")
                logging.error(f"Raw response: {message['content']}")
                return None
        else:
            logging.error("Failed to get valid response from LLM")
            return None
            
    except Exception as e:
        logging.error(f"Error in LLM-based selection: {e}")
        return None

# Keep the old functions for backward compatibility
def get_paper_by_doi(doi: str) -> Optional[Dict]:
    """
    Get specific paper information by DOI from OpenAlex.
    
    Args:
        doi: DOI of the paper
        
    Returns:
        Paper dictionary or None if not found
    """
    if not doi:
        return None
        
    base_url = "https://api.openalex.org/works"
    
    params = {
        'filter': f'doi:{doi}',
        'mailto': 'researcher@example.com'
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        results = data.get('results', [])
        
        if results:
            work = results[0]  # Should only be one result for a specific DOI
            return {
                'title': work.get('title', ''),
                'doi': work.get('doi'),
                'pdf_url': work.get('primary_location', {}).get('pdf_url'),
                'open_access': work.get('open_access', {}),
                'authors': [auth.get('author', {}).get('display_name', '') 
                           for auth in work.get('authorships', [])]
            }
        
        return None
        
    except Exception as e:
        logging.error(f"Error fetching paper by DOI {doi}: {e}")
        return None

def search_openalex_by_arxiv_id(arxiv_id: str) -> Optional[Dict]:
    """
    Search for a paper by arXiv ID using OpenAlex.
    
    Args:
        arxiv_id: arXiv identifier (e.g., "2301.00001")
        
    Returns:
        Paper dictionary or None if not found
    """
    if not arxiv_id:
        return None
        
    base_url = "https://api.openalex.org/works"
    
    # Try different arXiv URL formats
    arxiv_urls = [
        f"https://arxiv.org/abs/{arxiv_id}",
        f"http://arxiv.org/abs/{arxiv_id}"
    ]
    
    for arxiv_url in arxiv_urls:
        params = {
            'filter': f'arxiv:{arxiv_url}',
            'mailto': 'researcher@example.com'
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            results = data.get('results', [])
            
            if results:
                work = results[0]
                return {
                    'title': work.get('title', ''),
                    'arxiv_id': arxiv_id,
                    'pdf_url': f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                    'doi': work.get('doi'),
                    'authors': [auth.get('author', {}).get('display_name', '') 
                               for auth in work.get('authorships', [])],
                    'publication_year': work.get('publication_year')
                }
        except Exception as e:
            logging.warning(f"Error searching arXiv ID {arxiv_id} with URL {arxiv_url}: {e}")
            continue
    
    return None 