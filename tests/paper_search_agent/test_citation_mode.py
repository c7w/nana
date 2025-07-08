import sys
from pathlib import Path
import json
import logging

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from agents.paper_search_agent import extract_papers_from_citation, extract_text_from_pdf, load_config
from tools.log_config import setup_logging

def run_live_citation_test(pdf_path_str: str):
    """
    Runs a live, end-to-end test of the citation extraction feature on a real PDF.
    This test does NOT use mocks and will make a real API call.
    """
    setup_logging()
    
    pdf_path = Path(pdf_path_str)
    if not pdf_path.exists():
        logging.error(f"Test PDF not found at the specified path: {pdf_path}")
        return

    logging.info(f"Starting live test on PDF: {pdf_path.name}")

    # 1. Load the real configuration
    config = load_config()

    # 2. To find all citations, we use the entire PDF content as the "snippet"
    full_text_snippet = extract_text_from_pdf(pdf_path)
    if not full_text_snippet:
        logging.error("Failed to extract any text from the PDF. Aborting test.")
        return

    # 3. Run the extraction function
    extracted_papers = extract_papers_from_citation(config, pdf_path, full_text_snippet)

    # 4. Print the results
    if extracted_papers:
        print("\n\n--- ✅ Live Test Successful: Extracted Papers ---")
        for i, paper in enumerate(extracted_papers):
            print(f"{i+1}. {paper.get('title', 'No Title Found')}")
        print("-------------------------------------------------")
        print(f"Total papers found: {len(extracted_papers)}")
    else:
        print("\n\n--- ❌ Live Test Completed: No papers were extracted. ---")
        print("Please check the logs above for any errors from the API or parsing steps.")

if __name__ == '__main__':
    # The PDF path provided by the user
    pdf_to_test = "/Users/c7w/Downloads/Survey_of_Self_Evolution.pdf"
    run_live_citation_test(pdf_to_test) 