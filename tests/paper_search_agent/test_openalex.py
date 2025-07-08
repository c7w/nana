"""
Test script for combined arXiv + OpenAlex search functionality.
Tests papers from test_openalex.input file to verify search quality with new strategy.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from tools.log_config import setup_logging
from tools.paper.search_openalex import search_arxiv, search_openalex, combined_search_with_llm_fallback
import yaml

def test_combined_search():
    """Test the new combined search strategy with papers from input file."""
    setup_logging()
    
    # Read test input file
    input_file = Path(__file__).parent / "test_openalex.input"
    if not input_file.exists():
        print(f"Error: Test input file not found at {input_file}")
        return
    
    paper_titles = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            title = line.strip()
            if title:
                paper_titles.append(title)
    
    print(f"\n--- Testing Combined arXiv + OpenAlex Search with {len(paper_titles)} Papers ---")
    print("=" * 100)
    
    results_summary = {
        'total': len(paper_titles),
        'found': 0,
        'exact_match': 0,
        'llm_selected': 0,
        'with_arxiv': 0,
        'with_pdf': 0,
        'failed': 0,
        'arxiv_source': 0,
        'openalex_source': 0
    }
    
    failed_papers = []
    detailed_results = []
    
    for i, title in enumerate(paper_titles, 1):
        print(f"\n[{i}/{len(paper_titles)}] Testing: {title}")
        print("=" * 100)
        
        try:
            # Test the combined search strategy
            result = combined_search_with_llm_fallback(title, max_results_per_source=10)
            
            if result:
                results_summary['found'] += 1
                
                result_title = result.get('title', 'No title')
                arxiv_id = result.get('arxiv_id')
                pdf_url = result.get('pdf_url')
                source = result.get('source', 'unknown')
                year = result.get('publication_year')
                authors = result.get('authors', [])
                
                print(f"✓ FOUND: {result_title}")
                print(f"  Source: {source}")
                print(f"  arXiv ID: {arxiv_id or 'None'}")
                print(f"  PDF URL: {pdf_url or 'None'}")
                print(f"  Year: {year or 'Unknown'}")
                if authors:
                    print(f"  Authors: {', '.join(authors[:3])}{'...' if len(authors) > 3 else ''}")
                
                # Check if it's exact match
                if title.lower().strip() == result_title.lower().strip():
                    results_summary['exact_match'] += 1
                    print("  ✓ EXACT TITLE MATCH")
                else:
                    results_summary['llm_selected'] += 1
                    print("  ℹ️  LLM SELECTED MATCH")
                
                # Track metrics
                if arxiv_id:
                    results_summary['with_arxiv'] += 1
                if pdf_url:
                    results_summary['with_pdf'] += 1
                if source == 'arxiv':
                    results_summary['arxiv_source'] += 1
                elif source == 'openalex':
                    results_summary['openalex_source'] += 1
                
                # Verify downloadable content
                if not (arxiv_id or pdf_url):
                    print("  ⚠️  WARNING: No downloadable content!")
                    failed_papers.append(title)
                    results_summary['failed'] += 1
                else:
                    detailed_results.append({
                        'query': title,
                        'result': result,
                        'match_type': 'exact' if results_summary['exact_match'] > len(detailed_results) else 'llm'
                    })
                
            else:
                print("✗ NO SUITABLE MATCH FOUND")
                failed_papers.append(title)
                results_summary['failed'] += 1
                
        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed_papers.append(title)
            results_summary['failed'] += 1
    
    # Print comprehensive summary
    print("\n" + "=" * 100)
    print("--- COMPREHENSIVE SUMMARY ---")
    print("=" * 100)
    print(f"Total papers tested: {results_summary['total']}")
    print(f"Papers found: {results_summary['found']} ({results_summary['found']/results_summary['total']*100:.1f}%)")
    print(f"Exact title matches: {results_summary['exact_match']} ({results_summary['exact_match']/results_summary['total']*100:.1f}%)")
    print(f"LLM selected matches: {results_summary['llm_selected']} ({results_summary['llm_selected']/results_summary['total']*100:.1f}%)")
    print(f"Papers with arXiv ID: {results_summary['with_arxiv']} ({results_summary['with_arxiv']/results_summary['total']*100:.1f}%)")
    print(f"Papers with PDF URL: {results_summary['with_pdf']} ({results_summary['with_pdf']/results_summary['total']*100:.1f}%)")
    print(f"Papers failed/unusable: {results_summary['failed']} ({results_summary['failed']/results_summary['total']*100:.1f}%)")
    
    print(f"\n--- SOURCE BREAKDOWN ---")
    print(f"Found via arXiv: {results_summary['arxiv_source']} ({results_summary['arxiv_source']/max(1,results_summary['found'])*100:.1f}%)")
    print(f"Found via OpenAlex: {results_summary['openalex_source']} ({results_summary['openalex_source']/max(1,results_summary['found'])*100:.1f}%)")
    
    # Calculate success rate (papers that can be processed downstream)
    processable = results_summary['found'] - results_summary['failed']
    success_rate = processable / results_summary['total'] * 100
    print(f"\nDownstream processable: {processable} ({success_rate:.1f}%)")
    
    if failed_papers:
        print(f"\n--- FAILED PAPERS ({len(failed_papers)}) ---")
        for title in failed_papers:
            print(f"  ✗ {title}")
    
    # Success criteria
    if success_rate >= 90:
        print(f"\n🎉 EXCELLENT: Combined search strategy is OUTSTANDING (success rate: {success_rate:.1f}%)")
    elif success_rate >= 80:
        print(f"\n✅ GOOD: Combined search strategy is PRODUCTION READY (success rate: {success_rate:.1f}%)")
    elif success_rate >= 70:
        print(f"\n⚠️  ACCEPTABLE: Combined search strategy works but could improve (success rate: {success_rate:.1f}%)")
    else:
        print(f"\n❌ NEEDS WORK: Combined search strategy requires improvement (success rate: {success_rate:.1f}%)")
    
    print("=" * 100)
    
    return detailed_results

def test_individual_engines():
    """Test arXiv and OpenAlex individually with a few papers."""
    setup_logging()
    
    test_papers = [
        "Attention Is All You Need",
        "Voyager: An open-ended embodied agent with large language models",
        "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding"
    ]
    
    print("\n--- Testing Individual Search Engines ---")
    print("=" * 80)
    
    for i, title in enumerate(test_papers, 1):
        print(f"\n[{i}/{len(test_papers)}] Testing: {title}")
        print("-" * 60)
        
        # Test arXiv
        print("🔍 arXiv Results:")
        try:
            arxiv_results = search_arxiv(title, max_results=3)
            if arxiv_results:
                for j, result in enumerate(arxiv_results, 1):
                    print(f"  {j}. {result.get('title', 'No title')}")
                    print(f"     arXiv ID: {result.get('arxiv_id', 'None')}")
            else:
                print("  No results found")
        except Exception as e:
            print(f"  Error: {e}")
        
        # Test OpenAlex
        print("\n🔍 OpenAlex Results:")
        try:
            openalex_results = search_openalex(title, max_results=3)
            if openalex_results:
                for j, result in enumerate(openalex_results, 1):
                    print(f"  {j}. {result.get('title', 'No title')}")
                    print(f"     arXiv ID: {result.get('arxiv_id', 'None')}")
                    print(f"     PDF URL: {result.get('pdf_url', 'None')}")
            else:
                print("  No results found")
        except Exception as e:
            print(f"  Error: {e}")
    
    print("\n" + "=" * 80)

def test_nonexistent_papers():
    """Test with obviously fake papers to verify LLM correctly returns 0."""
    setup_logging()
    
    fake_papers = [
        "The Ultimate Guide to Training Dragons with Machine Learning",
        "Blockchain-Based Time Travel: A Practical Approach",
        "Neural Networks for Predicting Lottery Numbers with 100% Accuracy"
    ]
    
    print("\n--- Testing Non-existent Papers (Should Return None) ---")
    print("=" * 80)
    
    for i, title in enumerate(fake_papers, 1):
        print(f"\n[{i}/{len(fake_papers)}] Testing: {title}")
        print("-" * 60)
        
        try:
            result = combined_search_with_llm_fallback(title, max_results_per_source=5)
            
            if result is None:
                print("✓ CORRECT: No match found (as expected)")
            else:
                print(f"✗ ERROR: Found unexpected match: {result.get('title', 'Unknown')}")
                
        except Exception as e:
            print(f"✗ ERROR: {e}")
    
    print("\n" + "=" * 80)

def test_integrated_search():
    """Test the integrated search functionality through the main search function."""
    setup_logging()
    
    # Import the main search function
    from tools.paper.search import find_paper_details
    
    # Load config
    config_path = project_root / "config/config.yaml"
    if not config_path.exists():
        print("Error: config.yaml not found. Cannot test integrated search.")
        return
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Test papers
    test_papers = [
        {"title": "Attention Is All You Need"},
        {"title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding"},
        {"title": "The Ultimate Guide to Training Dragons"},  # Should fail
    ]
    
    usage_tracker = {}
    
    print("\n--- Testing Integrated Search Pipeline ---")
    print("=" * 80)
    
    for i, paper in enumerate(test_papers, 1):
        title = paper['title']
        print(f"\n[{i}/{len(test_papers)}] Testing: {title}")
        print("-" * 60)
        
        result = find_paper_details(paper, config, usage_tracker)
        
        if result:
            print(f"✓ SUCCESS: {result.get('title', 'No title')}")
            print(f"  arXiv ID: {result.get('arxiv_id', 'None')}")
            print(f"  PDF URL: {result.get('pdf_url', 'None')}")
            print(f"  Search Engine: {result.get('search_engine', 'Unknown')}")
        else:
            print("✗ No results found")
    
    # Print usage summary
    if usage_tracker:
        print(f"\n--- API Usage Summary ---")
        total_cost = 0
        for model, usage in usage_tracker.items():
            cost = usage.get('cost_usd', 0)
            total_cost += cost
            print(f"{model}: ${cost:.6f} (Input: {usage['input']}, Output: {usage['output']})")
        print(f"Total cost: ${total_cost:.6f}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "--batch":
            test_combined_search()
        elif sys.argv[1] == "--individual":
            test_individual_engines()
        elif sys.argv[1] == "--fake":
            test_nonexistent_papers()
        elif sys.argv[1] == "--integrated":
            test_integrated_search()
        else:
            print("Usage: python test_openalex.py [--batch|--individual|--fake|--integrated]")
    else:
        print("Running combined search test...")
        test_combined_search() 