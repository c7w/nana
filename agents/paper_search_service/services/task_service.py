import asyncio
import logging
from pathlib import Path
import sys
import yaml
import json
from datetime import datetime, timezone
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

from tools.api.llm import call_llm
from tools.paper.search import find_paper_details
from tools.paper.utils import _normalize_title, _get_config_for_step
from tools.paper.analyze import analyze_paper
from tools.trackers import update_usage
from models.task import ProcessingTask, PaperTask, TaskStatus, PaperStatus, TaskStorage

class TaskProcessor:
    """Service for processing paper collection and analysis tasks."""
    def __init__(self, storage_dir: Path, max_search_concurrent: int = 3, max_analysis_concurrent: int = 1):
        self.storage_dir = storage_dir
        self.task_storage = TaskStorage(storage_dir)
        self.config = self._load_config()
        self.usage_tracker = {}
        self.max_search_concurrent = max_search_concurrent
        self.max_analysis_concurrent = max_analysis_concurrent
        self._search_semaphore = asyncio.Semaphore(max_search_concurrent)
        self._analysis_semaphore = asyncio.Semaphore(max_analysis_concurrent)

    def _load_config(self) -> Dict[str, Any]:
        config_path = project_root / 'config' / 'config.yaml'
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    async def process_task(self, task_id: str) -> bool:
        task = self.task_storage.get_task(task_id)
        if not task:
            logging.error(f"Task {task_id} not found")
            return False
        
        task.add_log("INIT", "INFO", f"Starting task processing: {task.title}")
        self.task_storage.update_task(task)
        
        try:
            await self._format_input(task)
            await self._search_papers(task)
            await self._analyze_papers(task)
            
            task.add_log("COMPLETE", "INFO", "Task processing completed successfully")
            task.update_status(TaskStatus.COMPLETED)
            self.task_storage.update_task(task)
            return True
        except Exception as e:
            error_msg = f"Error processing task {task_id}: {e}"
            logging.error(error_msg)
            task.add_log("ERROR", "ERROR", error_msg, {"exception": str(e)})
            task.error = str(e)
            task.update_status(TaskStatus.FAILED)
            self.task_storage.update_task(task)
            return False

    def process_task_sync(self, task_id: str) -> bool:
        """Synchronous wrapper for async process_task method for BackgroundTasks"""
        try:
            # Create new event loop for this background task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.process_task(task_id))
            finally:
                loop.close()
        except Exception as e:
            logging.error(f"Error in background task processing: {e}")
            return False

    async def _format_input(self, task: ProcessingTask):
        task.update_status(TaskStatus.FORMATTING_INPUT)
        task.add_log("FORMAT_INPUT", "INFO", "Starting input formatting stage")
        self.task_storage.update_task(task)
        
        logging.info(f"Formatting input for task {task.id}")
        step_config_name = '1_input_formatting'
        llm_name = self.config['agents']['paper_search_agent'][step_config_name]
        llm_config = self.config['llms'][llm_name]
        prompt_path = project_root / 'prompts' / 'paper_search_agent' / f'{step_config_name}.md'
        prompt_template = prompt_path.read_text()
        
        # Log the input being processed
        task.add_log("FORMAT_INPUT", "INFO", f"Processing input text with {len(task.input_text)} characters", {
            "input_preview": task.input_text[:200] + "..." if len(task.input_text) > 200 else task.input_text,
            "llm_model": llm_name
        })
        
        messages = [
            {"role": "system", "content": prompt_template},
            {"role": "user", "content": task.input_text}
        ]
        
        try:
            message, usage = call_llm(llm_config, messages, is_json=True)
            update_usage(self.usage_tracker, llm_config, usage)
            
            # Log LLM usage
            task.add_log("FORMAT_INPUT", "INFO", "LLM call completed", {
                "usage": usage,
                "model": llm_name
            })
            
            if message and 'content' in message:
                try:
                    content = message['content']
                    formatted_data = json.loads(content)
                    papers = formatted_data.get('papers', [])
                    task.papers = [PaperTask(title=paper['title'], url=paper.get('url')) for paper in papers]
                    
                    # Log the formatted results
                    task.add_log("FORMAT_INPUT", "INFO", f"Successfully formatted {len(task.papers)} papers", {
                        "papers_count": len(task.papers),
                        "formatted_data": formatted_data,
                        "paper_titles": [paper['title'] for paper in papers[:5]]  # First 5 titles
                    })
                    
                    logging.info(f"Formatted {len(task.papers)} papers")
                except (json.JSONDecodeError, KeyError) as e:
                    error_msg = f"Error parsing LLM response: {e}"
                    task.add_log("FORMAT_INPUT", "ERROR", error_msg, {
                        "raw_response": content[:500] if content else None,
                        "exception": str(e)
                    })
                    logging.error(error_msg)
                    raise Exception(f"Failed to format input: {e}")
            else:
                error_msg = "Failed to get valid response from LLM"
                task.add_log("FORMAT_INPUT", "ERROR", error_msg, {
                    "message": message
                })
                raise Exception(error_msg)
        except Exception as e:
            if not any(log.level == "ERROR" for log in task.logs if log.stage == "FORMAT_INPUT"):
                task.add_log("FORMAT_INPUT", "ERROR", f"Unexpected error during formatting: {str(e)}", {
                    "exception": str(e)
                })
            raise
        
        self.task_storage.update_task(task)

    async def _search_papers(self, task: ProcessingTask):
        task.update_status(TaskStatus.SEARCHING_PAPERS)
        task.add_log("SEARCH_PAPERS", "INFO", f"Starting paper search stage for {len(task.papers)} papers")
        self.task_storage.update_task(task)
        logging.info(f"Searching papers for task {task.id}")
        
        # Create tasks for concurrent processing
        search_tasks = []
        for i, paper in enumerate(task.papers):
            search_task = self._search_single_paper(task, paper, i)
            search_tasks.append(search_task)
        
        task.add_log("SEARCH_PAPERS", "INFO", f"Initiating concurrent search with max {self.max_search_concurrent} parallel searches")
        
        # Process all papers concurrently with semaphore control
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Log overall results
        successful_searches = sum(1 for paper in task.papers if paper.status == PaperStatus.COMPLETED)
        failed_searches = sum(1 for paper in task.papers if paper.status == PaperStatus.FAILED)
        
        task.add_log("SEARCH_PAPERS", "INFO", f"Search stage completed: {successful_searches} successful, {failed_searches} failed", {
            "successful_count": successful_searches,
            "failed_count": failed_searches,
            "total_papers": len(task.papers)
        })

    async def _search_single_paper(self, task: ProcessingTask, paper: PaperTask, index: int):
        async with self._search_semaphore:
            try:
                paper.status = PaperStatus.SEARCHING
                paper.updated_at = datetime.now(timezone.utc)
                
                task.add_log("SEARCH_PAPERS", "INFO", f"Starting search for paper: {paper.title[:100]}...", {
                    "paper_index": index,
                    "paper_title": paper.title,
                    "initial_url": paper.url
                })
                self.task_storage.update_task(task)
                
                paper_dict = {"title": paper.title, "url": paper.url}
                details = find_paper_details(paper_dict, self.config, self.usage_tracker)
                
                if details:
                    paper.url = details.get('pdf_url', paper.url)
                    # Ensure details are JSON serializable
                    serializable_details = {}
                    for k, v in details.items():
                        if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                            serializable_details[k] = v
                        else:
                            serializable_details[k] = str(v)
                    paper.progress['search'] = serializable_details
                    paper.status = PaperStatus.COMPLETED
                    
                    task.add_log("SEARCH_PAPERS", "INFO", f"Successfully found details for: {paper.title[:100]}...", {
                        "paper_index": index,
                        "paper_title": paper.title,
                        "found_url": paper.url,
                        "arxiv_id": details.get('arxiv_id'),
                        "authors": details.get('authors', [])[:3] if details.get('authors') else [],
                        "search_method": details.get('search_method', 'unknown')
                    })
                    logging.info(f"Found details for: {paper.title}")
                else:
                    paper.status = PaperStatus.FAILED
                    paper.error = "Failed to find paper details"
                    task.add_log("SEARCH_PAPERS", "WARNING", f"Failed to find details for: {paper.title[:100]}...", {
                        "paper_index": index,
                        "paper_title": paper.title,
                        "error": "No matching paper found in search databases"
                    })
                    logging.warning(f"Failed to find details for: {paper.title}")
                
                paper.updated_at = datetime.now(timezone.utc)
                self.task_storage.update_task(task)
                
                # Add delay to avoid overwhelming APIs
                await asyncio.sleep(1)
                
            except Exception as e:
                error_msg = f"Error searching paper {paper.title}: {e}"
                logging.error(error_msg)
                task.add_log("SEARCH_PAPERS", "ERROR", f"Search error for paper: {paper.title[:100]}...", {
                    "paper_index": index,
                    "paper_title": paper.title,
                    "exception": str(e),
                    "error_type": type(e).__name__
                })
                paper.status = PaperStatus.FAILED
                paper.error = str(e)
                paper.updated_at = datetime.now(timezone.utc)
                self.task_storage.update_task(task)

    async def _analyze_papers(self, task: ProcessingTask):
        task.update_status(TaskStatus.ANALYZING_PAPERS)
        task.add_log("ANALYZE_PAPERS", "INFO", f"Starting paper analysis stage")
        self.task_storage.update_task(task)
        logging.info(f"Analyzing papers for task {task.id}")
        
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        analysis_dir = self.storage_dir / today_str
        analysis_dir.mkdir(parents=True, exist_ok=True)
        
        # Filter papers that are ready for analysis
        papers_to_analyze = [
            (i, paper) for i, paper in enumerate(task.papers) 
            if paper.status == PaperStatus.COMPLETED and 'search' in paper.progress
        ]
        
        task.add_log("ANALYZE_PAPERS", "INFO", f"Found {len(papers_to_analyze)} papers ready for analysis out of {len(task.papers)} total", {
            "papers_to_analyze": len(papers_to_analyze),
            "total_papers": len(task.papers),
            "analysis_directory": str(analysis_dir),
            "max_concurrent": self.max_analysis_concurrent
        })
        
        if len(papers_to_analyze) == 0:
            task.add_log("ANALYZE_PAPERS", "WARNING", "No papers available for analysis - all papers failed search stage")
            return
        
        # Create tasks for concurrent processing
        analysis_tasks = []
        for i, paper in papers_to_analyze:
            analysis_task = self._analyze_single_paper(task, paper, i, analysis_dir)
            analysis_tasks.append(analysis_task)
        
        # Process all papers concurrently with semaphore control
        results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        # Log overall analysis results
        completed_analysis = sum(1 for i, paper in papers_to_analyze if paper.status == PaperStatus.COMPLETED and 'analysis' in paper.progress)
        failed_analysis = len(papers_to_analyze) - completed_analysis
        
        task.add_log("ANALYZE_PAPERS", "INFO", f"Analysis stage completed: {completed_analysis} successful, {failed_analysis} failed", {
            "successful_analysis": completed_analysis,
            "failed_analysis": failed_analysis,
            "total_attempted": len(papers_to_analyze)
        })

    async def _analyze_single_paper(self, task: ProcessingTask, paper: PaperTask, index: int, analysis_dir: Path):
        async with self._analysis_semaphore:
            try:
                paper.status = PaperStatus.ANALYZING
                paper.updated_at = datetime.now(timezone.utc)
                
                task.add_log("ANALYZE_PAPERS", "INFO", f"Starting analysis for paper: {paper.title[:100]}...", {
                    "paper_index": index,
                    "paper_title": paper.title,
                    "paper_url": paper.url,
                    "has_search_data": 'search' in paper.progress
                })
                self.task_storage.update_task(task)
                
                paper_dict = {"title": paper.title, "url": paper.url, **paper.progress.get('search', {})}
                
                try:
                    analysis_results = analyze_paper(paper_dict, self.config, self.usage_tracker)
                    
                    if analysis_results:
                        paper_id = paper_dict.get('arxiv_id', f'paper_{index}')
                        paper_dir = analysis_dir / paper_id
                        paper_dir.mkdir(parents=True, exist_ok=True)
                        summary_path = paper_dir / 'summary.md'
                        
                        with open(summary_path, 'w', encoding='utf-8') as f:
                            f.write(analysis_results['summary'])
                        
                        paper.progress['analysis'] = {"summary_path": str(summary_path.relative_to(project_root))}
                        paper.status = PaperStatus.COMPLETED
                        
                        task.add_log("ANALYZE_PAPERS", "INFO", f"Successfully analyzed paper: {paper.title[:100]}...", {
                            "paper_index": index,
                            "paper_title": paper.title,
                            "paper_id": paper_id,
                            "summary_path": str(summary_path.relative_to(project_root)),
                            "summary_length": len(analysis_results['summary']),
                            "analysis_keys": list(analysis_results.keys()) if isinstance(analysis_results, dict) else []
                        })
                        logging.info(f"Analyzed: {paper.title}")
                    else:
                        paper.status = PaperStatus.FAILED
                        paper.error = "Failed to analyze paper"
                        task.add_log("ANALYZE_PAPERS", "WARNING", f"Analysis returned no results for: {paper.title[:100]}...", {
                            "paper_index": index,
                            "paper_title": paper.title,
                            "error": "Analysis function returned empty/null result"
                        })
                        logging.warning(f"Failed to analyze: {paper.title}")
                except Exception as analysis_error:
                    error_msg = f"Analysis function error for {paper.title}: {analysis_error}"
                    task.add_log("ANALYZE_PAPERS", "ERROR", f"Analysis function failed for: {paper.title[:100]}...", {
                        "paper_index": index,
                        "paper_title": paper.title,
                        "exception": str(analysis_error),
                        "error_type": type(analysis_error).__name__
                    })
                    paper.status = PaperStatus.FAILED
                    paper.error = str(analysis_error)
                    logging.error(error_msg)
                
                paper.updated_at = datetime.now(timezone.utc)
                self.task_storage.update_task(task)
                
                # Add delay for LLM rate limiting
                await asyncio.sleep(2)
                
            except Exception as e:
                error_msg = f"Error analyzing paper {paper.title}: {e}"
                logging.error(error_msg)
                task.add_log("ANALYZE_PAPERS", "ERROR", f"Unexpected error during analysis: {paper.title[:100]}...", {
                    "paper_index": index,
                    "paper_title": paper.title,
                    "exception": str(e),
                    "error_type": type(e).__name__
                })
                paper.status = PaperStatus.FAILED
                paper.error = str(e)
                paper.updated_at = datetime.now(timezone.utc)
                self.task_storage.update_task(task)

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        task = self.task_storage.get_task(task_id)
        if not task:
            return {"error": "Task not found"}
        progress = task.get_progress_summary()
        return {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "progress": progress,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error": task.error,
            "papers": [
                {
                    "title": paper.title,
                    "status": paper.status,
                    "error": paper.error,
                    "updated_at": paper.updated_at.isoformat()
                }
                for paper in task.papers
            ]
        }

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        tasks = self.task_storage.get_all_tasks()
        return [
            {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "progress": task.get_progress_summary(),
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "error": task.error
            }
            for task in tasks
        ] 