import sys
from pathlib import Path
from ddgs import DDGS

# Add project root to path to allow importing 'tools'
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from tools.log_config import setup_logging
from tools.patches.ddgs_patch import apply_ddgs_patch

def run_test_search():
    """
    Applies the patch and runs a test search to verify functionality.
    """
    # 1. Setup logging to see output
    setup_logging()

    # 2. Apply the patch for DDGS
    apply_ddgs_patch()

    # 3. The title that was failing previously
    test_query = 'AndroidWorld: A Dynamic Benchmarking Environment for Autonomous Agents'
    
    print("\n--- Running DuckDuckGo Search Test ---")
    print(f"Query: {test_query}")

    try:
        # 4. Initialize the search client and perform the search
        with DDGS() as ddgs:
            results = ddgs.text(test_query, max_results=5)
            
            print("\n--- Search Results ---")
            if results:
                for i, r in enumerate(results):
                    print(f"{i+1}. {r['title']}")
                    print(f"   Link: {r['href']}")
            else:
                print("No results returned.")
            print("----------------------\n")

    except Exception as e:
        print(f"\n--- An error occurred during the test search ---")
        print(e)
        print("------------------------------------------------\n")

if __name__ == "__main__":
    run_test_search() 