"""
Test script for paper analysis functionality with different LLM models.
This script allows testing various models on paper summarization tasks.
"""

import sys
from pathlib import Path
import yaml
import json
import argparse
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from tools.log_config import setup_logging
from tools.paper.analyze import analyze_paper
from tools.api.llm import call_llm
from tools.paper.utils import _get_config_for_step

def load_test_config():
    """Load test configuration."""
    config_path = project_root / "config/config.yaml"
    if not config_path.exists():
        print("Error: config.yaml not found. Please create it from config.template.yaml")
        return None
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def get_test_papers():
    """Get a list of test papers for analysis."""
    return [
        {
            'title': 'Attention Is All You Need',
            'arxiv_id': '1706.03762',
            'pdf_url': 'https://arxiv.org/pdf/1706.03762.pdf',
            'authors': ['Ashish Vaswani', 'Noam Shazeer', 'Niki Parmar'],
            'publication_year': 2017
        },
        {
            'title': 'BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding',
            'arxiv_id': '1810.04805',
            'pdf_url': 'https://arxiv.org/pdf/1810.04805.pdf',
            'authors': ['Jacob Devlin', 'Ming-Wei Chang', 'Kenton Lee'],
            'publication_year': 2018
        },
        {
            'title': 'Language Models are Few-Shot Learners',
            'arxiv_id': '2005.14165',
            'pdf_url': 'https://arxiv.org/pdf/2005.14165.pdf',
            'authors': ['Tom B. Brown', 'Benjamin Mann', 'Nick Ryder'],
            'publication_year': 2020
        },
        {
            'title': 'ReAct: Synergizing Reasoning and Acting in Language Models',
            'arxiv_id': '2210.03629',
            'pdf_url': 'https://arxiv.org/pdf/2210.03629.pdf',
            'authors': ['Shunyu Yao', 'Jeffrey Zhao', 'Dian Yu'],
            'publication_year': 2022
        },
        {
            'title': 'Gödel Agent: A Self-Referential Agent Framework for Recursive Self-Improvement',
            'arxiv_id': '2410.04444',
            'pdf_url': 'https://arxiv.org/pdf/2410.04444.pdf',
            'authors': ['Xunjian Yin', 'Xinyi Wang', 'Liangming Pan'],
            'publication_year': 2024
        }
    ]

def test_analysis_with_model(paper, model_name, config, usage_tracker):
    """Test paper analysis with a specific model."""
    print(f"\n{'='*80}")
    print(f"Testing model: {model_name}")
    print(f"Paper: {paper['title']}")
    print(f"arXiv ID: {paper['arxiv_id']}")
    print(f"{'='*80}")
    
    # Create a temporary config with the specified model
    temp_config = config.copy()
    temp_config['agents']['paper_search_agent']['3_2_paper_summary'] = model_name
    
    start_time = datetime.now()
    
    try:
        # Run the analysis
        result = analyze_paper(paper, temp_config, usage_tracker)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if result and result.get('summary'):
            summary = result['summary']
            word_count = len(summary.split())
            char_count = len(summary)
            
            print(f"✅ Analysis completed successfully!")
            print(f"   Duration: {duration:.2f} seconds")
            print(f"   Summary length: {word_count} words, {char_count} characters")
            
            # Show a preview of the summary
            print(f"\n📝 Summary preview (first 500 chars):")
            print("-" * 60)
            print(summary[:500] + "..." if len(summary) > 500 else summary)
            print("-" * 60)
            
            # Check for key sections
            sections_found = []
            expected_sections = [
                "一句话总结", "论文概览", "方法详解", "实验分析", 
                "优势与不足", "启发与思考", "作者", "核心摘要"
            ]
            
            for section in expected_sections:
                if section in summary:
                    sections_found.append(section)
            
            print(f"\n🔍 Sections found: {len(sections_found)}/{len(expected_sections)}")
            print(f"   Found: {', '.join(sections_found)}")
            
            missing_sections = set(expected_sections) - set(sections_found)
            if missing_sections:
                print(f"   Missing: {', '.join(missing_sections)}")
            
            return {
                'success': True,
                'duration': duration,
                'word_count': word_count,
                'char_count': char_count,
                'sections_found': len(sections_found),
                'sections_total': len(expected_sections),
                'summary': summary
            }
        else:
            print(f"❌ Analysis failed - no summary generated")
            return {
                'success': False,
                'duration': duration,
                'error': 'No summary generated'
            }
            
    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"❌ Analysis failed with error: {str(e)}")
        return {
            'success': False,
            'duration': duration,
            'error': str(e)
        }

def test_multiple_models(paper_indices=None, models=None):
    """Test multiple models on selected papers."""
    setup_logging()
    
    config = load_test_config()
    if not config:
        return
    
    test_papers = get_test_papers()
    
    # Filter papers if indices specified
    if paper_indices:
        test_papers = [test_papers[i] for i in paper_indices if 0 <= i < len(test_papers)]
    
    # Use specified models or get available models from config
    if models:
        available_models = models
    else:
        available_models = list(config.get('llms', {}).keys())
    
    print(f"\n🧪 Testing Paper Analysis Module")
    print(f"📄 Papers to test: {len(test_papers)}")
    print(f"🤖 Models to test: {len(available_models)}")
    print(f"🔧 Models: {', '.join(available_models)}")
    
    results = {}
    usage_tracker = {}
    
    for paper_idx, paper in enumerate(test_papers):
        print(f"\n\n📚 PAPER {paper_idx + 1}/{len(test_papers)}: {paper['title']}")
        
        paper_results = {}
        
        for model_idx, model_name in enumerate(available_models):
            if model_name not in config.get('llms', {}):
                print(f"⚠️  Model '{model_name}' not found in config, skipping...")
                continue
                
            print(f"\n🤖 MODEL {model_idx + 1}/{len(available_models)}: {model_name}")
            
            result = test_analysis_with_model(paper, model_name, config, usage_tracker)
            paper_results[model_name] = result
        
        results[paper['title']] = paper_results
    
    # Print summary report
    print_summary_report(results, usage_tracker)
    
    # Save detailed results
    save_results(results, usage_tracker)

def print_summary_report(results, usage_tracker):
    """Print a comprehensive summary report."""
    print(f"\n\n{'='*100}")
    print(f"📊 COMPREHENSIVE ANALYSIS REPORT")
    print(f"{'='*100}")
    
    # Model performance summary
    model_stats = {}
    
    for paper_title, paper_results in results.items():
        for model_name, result in paper_results.items():
            if model_name not in model_stats:
                model_stats[model_name] = {
                    'total_tests': 0,
                    'successful_tests': 0,
                    'total_duration': 0,
                    'total_words': 0,
                    'total_sections': 0,
                    'errors': []
                }
            
            stats = model_stats[model_name]
            stats['total_tests'] += 1
            stats['total_duration'] += result.get('duration', 0)
            
            if result.get('success'):
                stats['successful_tests'] += 1
                stats['total_words'] += result.get('word_count', 0)
                stats['total_sections'] += result.get('sections_found', 0)
            else:
                stats['errors'].append(result.get('error', 'Unknown error'))
    
    # Print model comparison table
    print(f"\n🏆 MODEL PERFORMANCE COMPARISON")
    print(f"{'Model Name':<25} {'Success Rate':<12} {'Avg Duration':<12} {'Avg Words':<10} {'Avg Sections':<12}")
    print("-" * 75)
    
    for model_name, stats in model_stats.items():
        success_rate = (stats['successful_tests'] / stats['total_tests']) * 100 if stats['total_tests'] > 0 else 0
        avg_duration = stats['total_duration'] / stats['total_tests'] if stats['total_tests'] > 0 else 0
        avg_words = stats['total_words'] / stats['successful_tests'] if stats['successful_tests'] > 0 else 0
        avg_sections = stats['total_sections'] / stats['successful_tests'] if stats['successful_tests'] > 0 else 0
        
        print(f"{model_name:<25} {success_rate:>8.1f}%   {avg_duration:>8.1f}s    {avg_words:>6.0f}    {avg_sections:>8.1f}")
    
    # Print cost analysis if available
    if usage_tracker:
        print(f"\n💰 COST ANALYSIS")
        print("-" * 50)
        total_cost = 0
        for model_name, usage in usage_tracker.items():
            cost = usage.get('cost_usd', 0)
            total_cost += cost
            print(f"{model_name:<25} ${cost:>8.6f}")
            print(f"  Input tokens: {usage.get('input', 0):,}")
            print(f"  Output tokens: {usage.get('output', 0):,}")
        
        print(f"{'TOTAL COST':<25} ${total_cost:>8.6f}")
    
    # Print recommendations
    print(f"\n🎯 RECOMMENDATIONS")
    print("-" * 30)
    
    if model_stats:
        # Best success rate
        best_success = max(model_stats.items(), key=lambda x: x[1]['successful_tests']/x[1]['total_tests'] if x[1]['total_tests'] > 0 else 0)
        print(f"🏅 Most reliable: {best_success[0]} ({(best_success[1]['successful_tests']/best_success[1]['total_tests']*100):.1f}% success)")
        
        # Fastest model
        fastest = min(model_stats.items(), key=lambda x: x[1]['total_duration']/x[1]['total_tests'] if x[1]['total_tests'] > 0 else float('inf'))
        avg_time = fastest[1]['total_duration']/fastest[1]['total_tests'] if fastest[1]['total_tests'] > 0 else 0
        print(f"⚡ Fastest: {fastest[0]} ({avg_time:.1f}s average)")
        
        # Most detailed
        most_detailed = max(model_stats.items(), key=lambda x: x[1]['total_sections']/x[1]['successful_tests'] if x[1]['successful_tests'] > 0 else 0)
        avg_sections = most_detailed[1]['total_sections']/most_detailed[1]['successful_tests'] if most_detailed[1]['successful_tests'] > 0 else 0
        print(f"📝 Most detailed: {most_detailed[0]} ({avg_sections:.1f} sections average)")

def save_results(results, usage_tracker):
    """Save detailed results to JSON file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = project_root / f"tests/paper_search_agent/analysis_test_results_{timestamp}.json"
    
    output_data = {
        'timestamp': timestamp,
        'results': results,
        'usage_tracker': usage_tracker
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Detailed results saved to: {output_file}")

def test_single_model_paper(model_name, paper_index=0):
    """Test a single model on a single paper for quick testing."""
    setup_logging()
    
    config = load_test_config()
    if not config:
        return
    
    test_papers = get_test_papers()
    if paper_index >= len(test_papers):
        print(f"Error: Paper index {paper_index} out of range (0-{len(test_papers)-1})")
        return
    
    paper = test_papers[paper_index]
    usage_tracker = {}
    
    print(f"\n🔬 SINGLE MODEL TEST")
    print(f"Model: {model_name}")
    print(f"Paper: {paper['title']}")
    
    result = test_analysis_with_model(paper, model_name, config, usage_tracker)
    
    if result.get('success'):
        print(f"\n✅ Test completed successfully!")
        if usage_tracker:
            print(f"\n💰 Usage:")
            for model, usage in usage_tracker.items():
                print(f"  {model}: ${usage.get('cost_usd', 0):.6f}")
    else:
        print(f"\n❌ Test failed: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test paper analysis with different LLM models")
    parser.add_argument('--models', nargs='+', help='Specific models to test (e.g., gpt-4o-mini gemini-pro)')
    parser.add_argument('--papers', nargs='+', type=int, help='Paper indices to test (0-4, default: all)')
    parser.add_argument('--single', action='store_true', help='Test single model on single paper')
    parser.add_argument('--model', type=str, help='Model name for single test')
    parser.add_argument('--paper-index', type=int, default=0, help='Paper index for single test (0-4)')
    
    args = parser.parse_args()
    
    if args.single:
        if not args.model:
            print("Error: --model required for single test mode")
            print("Available models: gpt-4o-mini, gpt-4o, claude-3-5-sonnet-20241022, gemini-pro, etc.")
            sys.exit(1)
        test_single_model_paper(args.model, args.paper_index)
    else:
        test_multiple_models(
            paper_indices=args.papers,
            models=args.models
        ) 