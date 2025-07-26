import logging
from pathlib import Path
import sys
import yaml
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
import threading
import time

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

from tools.api.llm import call_llm
from tools.paper.search import find_paper_details
from tools.paper.utils import _normalize_title
from tools.paper.analyze import analyze_paper
from tools.trackers import update_usage
from models.task import ProcessingTask, PaperTask, TaskStatus, PaperStatus, TaskStorage

class TaskProcessor:
    """Service for processing paper collection and analysis tasks."""
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.task_storage = TaskStorage(storage_dir)
        self.config = self._load_config()
        self.usage_tracker = {}
        self._current_processing_task = None  # Track the currently processing task
        self._processing_lock = threading.Lock()  # Thread safety for processing state
        self._scheduler_running = False
        self._scheduler_thread = None
        
        # Start the scheduler
        self.start_scheduler()

    def _load_config(self) -> Dict[str, Any]:
        config_path = project_root / 'config' / 'config.yaml'
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def start_scheduler(self):
        """Start the background task scheduler"""
        if self._scheduler_running:
            return
        
        self._scheduler_running = True
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        logging.info("Task scheduler started")

    def stop_scheduler(self):
        """Stop the background task scheduler"""
        self._scheduler_running = False
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5.0)
        logging.info("Task scheduler stopped")

    def _scheduler_loop(self):
        """Background scheduler loop that processes pending tasks"""
        while self._scheduler_running:
            try:
                # Check if we can process a new task
                with self._processing_lock:
                    if self._current_processing_task is None:
                        # Find the oldest pending task
                        pending_task = self._get_next_pending_task()
                        if pending_task:
                            logging.info(f"Scheduler starting task: {pending_task.id} - {pending_task.title}")
                            # Process task in a separate thread to avoid blocking the scheduler
                            process_thread = threading.Thread(
                                target=self._process_task_wrapper, 
                                args=(pending_task.id,),
                                daemon=True
                            )
                            process_thread.start()
                
                # Sleep for a short interval before checking again
                time.sleep(2.0)  # Check every 2 seconds
                
            except Exception as e:
                logging.error(f"Error in scheduler loop: {e}")
                time.sleep(5.0)  # Wait longer on error

    def _get_next_pending_task(self) -> ProcessingTask:
        """Get the next pending task to process (oldest first)"""
        all_tasks = self.task_storage.get_all_tasks()
        pending_tasks = [task for task in all_tasks if task.status == TaskStatus.PENDING]
        
        if pending_tasks:
            # Sort by creation time (oldest first)
            pending_tasks.sort(key=lambda t: t.created_at)
            return pending_tasks[0]
        
        return None

    def _process_task_wrapper(self, task_id: str):
        """Wrapper for task processing with proper error handling"""
        try:
            self.process_task(task_id)
        except Exception as e:
            logging.error(f"Error in task processing wrapper for {task_id}: {e}")
            # Make sure we release the lock even if processing fails
            with self._processing_lock:
                if self._current_processing_task == task_id:
                    self._current_processing_task = None

    def process_task(self, task_id: str) -> bool:
        """Process a single task through all stages synchronously"""
        task = self.task_storage.get_task(task_id)
        if not task:
            logging.error(f"Task {task_id} not found")
            return False
        
        # Check if task is already being processed or completed
        if task.status != TaskStatus.PENDING:
            logging.warning(f"Task {task_id} is not in pending status (current: {task.status}), skipping processing")
            return False
        
        # Atomically update status to prevent concurrent processing
        with self._processing_lock:
            if self._current_processing_task is not None:
                logging.warning(f"Task {task_id} cannot be processed: another task {self._current_processing_task} is already being processed")
                return False
            
            self._current_processing_task = task_id
        
        task.update_status(TaskStatus.FORMATTING_INPUT)
        task.add_log("INIT", "INFO", f"Starting task processing: {task.title}")
        self.task_storage.update_task(task)
        
        try:
            self._format_input(task)
            self._search_papers(task)
            self._analyze_papers(task)
            
            # Update reading page cache with completed papers
            self._update_reading_cache(task)
            
            # Check if task should be marked as completed or failed
            completed_papers = sum(1 for paper in task.papers if paper.status == PaperStatus.COMPLETED)
            failed_papers = sum(1 for paper in task.papers if paper.status == PaperStatus.FAILED)
            pending_papers = sum(1 for paper in task.papers if paper.status == PaperStatus.PENDING)
            
            if pending_papers > 0:
                # Still have pending papers - this shouldn't happen in normal flow
                task.add_log("COMPLETE", "WARNING", f"Task has {pending_papers} pending papers - marking as failed")
                task.error = f"Task incomplete: {pending_papers} papers failed to process"
                task.update_status(TaskStatus.FAILED)
            elif completed_papers == 0:
                # No papers completed - mark as failed
                task.add_log("COMPLETE", "ERROR", "Task failed: no papers were successfully processed")
                task.error = "All papers failed to process"
                task.update_status(TaskStatus.FAILED)
            else:
                # At least some papers completed successfully
                task.add_log("COMPLETE", "INFO", f"Task processing completed: {completed_papers} successful, {failed_papers} failed")
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
        finally:
            # Always clear the current processing task
            with self._processing_lock:
                self._current_processing_task = None

    def _format_input(self, task: ProcessingTask):
        # Status already set in process_task to prevent race condition
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
                        "paper_titles": [paper['title'] for paper in papers]  # First 5 titles
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

    def _search_papers(self, task: ProcessingTask):
        task.update_status(TaskStatus.SEARCHING_PAPERS)
        task.add_log("SEARCH_PAPERS", "INFO", f"Starting paper search stage for {len(task.papers)} papers")
        self.task_storage.update_task(task)
        logging.info(f"Searching papers for task {task.id}")
        
        # Process papers sequentially (no concurrency)
        successful_searches = 0
        failed_searches = 0
        
        for i, paper in enumerate(task.papers):
            try:
                paper.status = PaperStatus.SEARCHING
                paper.updated_at = datetime.now(timezone.utc)
                
                task.add_log("SEARCH_PAPERS", "INFO", f"Starting search for paper {i+1}/{len(task.papers)}: {paper.title[:100]}...", {
                    "paper_index": i,
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
                    paper.status = PaperStatus.SEARCH_COMPLETED  # Search done, ready for analysis
                    successful_searches += 1
                    
                    task.add_log("SEARCH_PAPERS", "INFO", f"Successfully found details for paper {i+1}: {paper.title[:100]}...", {
                        "paper_index": i,
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
                    failed_searches += 1
                    task.add_log("SEARCH_PAPERS", "WARNING", f"Failed to find details for paper {i+1}: {paper.title[:100]}...", {
                        "paper_index": i,
                        "paper_title": paper.title,
                        "error": "No matching paper found in search databases"
                    })
                    logging.warning(f"Failed to find details for: {paper.title}")
                
                paper.updated_at = datetime.now(timezone.utc)
                self.task_storage.update_task(task)
                
            except Exception as e:
                error_msg = f"Error searching paper {paper.title}: {e}"
                logging.error(error_msg)
                task.add_log("SEARCH_PAPERS", "ERROR", f"Search error for paper {i+1}: {paper.title[:100]}...", {
                    "paper_index": i,
                    "paper_title": paper.title,
                    "exception": str(e),
                    "error_type": type(e).__name__
                })
                paper.status = PaperStatus.FAILED
                paper.error = str(e)
                paper.updated_at = datetime.now(timezone.utc)
                failed_searches += 1
                self.task_storage.update_task(task)
        
        # Log overall results
        task.add_log("SEARCH_PAPERS", "INFO", f"Search stage completed: {successful_searches} successful, {failed_searches} failed", {
            "successful_count": successful_searches,
            "failed_count": failed_searches,
            "total_papers": len(task.papers)
        })

    def _analyze_papers(self, task: ProcessingTask):
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
            if paper.status == PaperStatus.SEARCH_COMPLETED and 'search' in paper.progress
        ]
        
        task.add_log("ANALYZE_PAPERS", "INFO", f"Found {len(papers_to_analyze)} papers ready for analysis out of {len(task.papers)} total", {
            "papers_to_analyze": len(papers_to_analyze),
            "total_papers": len(task.papers),
            "analysis_directory": str(analysis_dir)
        })
        
        if len(papers_to_analyze) == 0:
            task.add_log("ANALYZE_PAPERS", "WARNING", "No papers available for analysis - all papers failed search stage")
            return
        
        # Process papers sequentially (no concurrency)
        completed_analysis = 0
        failed_analysis = 0
        
        # Load existing cache for checking
        cache_path = project_root / 'storage' / 'paper_search_agent' / 'cache.json'
        cache = {}
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                task.add_log("ANALYZE_PAPERS", "INFO", f"Loaded existing cache with {len(cache)} entries", {
                    "cache_path": str(cache_path),
                    "cache_entries": len(cache)
                })
            except Exception as e:
                logging.warning(f"Failed to load existing cache: {e}")
                task.add_log("ANALYZE_PAPERS", "WARNING", f"Failed to load cache: {e}")
                cache = {}
        
        for i, paper in papers_to_analyze:
            try:
                # Check if analysis already exists in cache
                cache_key = _normalize_title(paper.title)
                if cache_key in cache and 'summary_path' in cache[cache_key]:
                    # Found existing analysis in cache
                    cached_summary_path = cache[cache_key]['summary_path']
                    full_summary_path = project_root / cached_summary_path
                    
                    if full_summary_path.exists():
                        # Use cached analysis
                        paper.progress['analysis'] = {"summary_path": str(cached_summary_path)}
                        paper.status = PaperStatus.COMPLETED
                        completed_analysis += 1
                        
                        task.add_log("ANALYZE_PAPERS", "INFO", f"Found cached analysis for paper {i+1}: {paper.title[:100]}...", {
                            "paper_index": i,
                            "paper_title": paper.title,
                            "cache_key": cache_key,
                            "cached_summary_path": cached_summary_path,
                            "cache_hit": True
                        })
                        logging.info(f"Cache hit for analysis: {paper.title}")
                        paper.updated_at = datetime.now(timezone.utc)
                        self.task_storage.update_task(task)
                        continue
                    else:
                        # Cache entry exists but file is missing, proceed with analysis
                        task.add_log("ANALYZE_PAPERS", "WARNING", f"Cache entry exists but file missing for paper {i+1}: {paper.title[:100]}...", {
                            "paper_index": i,
                            "paper_title": paper.title,
                            "cache_key": cache_key,
                            "missing_file": str(full_summary_path),
                            "cache_miss": True
                        })

                # Use the new analysis method with immediate cache update
                if self._analyze_single_paper_with_retry(task, paper, i, analysis_dir, cache):
                    completed_analysis += 1
                else:
                    failed_analysis += 1
                
            except Exception as e:
                error_msg = f"Error analyzing paper {paper.title}: {e}"
                logging.error(error_msg)
                task.add_log("ANALYZE_PAPERS", "ERROR", f"Unexpected error during analysis of paper {i+1}: {paper.title[:100]}...", {
                    "paper_index": i,
                    "paper_title": paper.title,
                    "exception": str(e),
                    "error_type": type(e).__name__
                })
                paper.status = PaperStatus.FAILED
                paper.error = str(e)
                paper.updated_at = datetime.now(timezone.utc)
                failed_analysis += 1
                self.task_storage.update_task(task)
        
        # Retry failed papers
        retry_completed = 0
        for i, paper in papers_to_analyze:
            if self._should_retry_paper(paper):
                task.add_log("ANALYZE_PAPERS", "INFO", f"Starting retry for failed paper {i+1}: {paper.title[:100]}...", {
                    "paper_index": i,
                    "paper_title": paper.title,
                    "retry_attempt": paper.progress.get('retry_count', 0) + 1
                })
                
                if self._analyze_single_paper_with_retry(task, paper, i, analysis_dir, cache):
                    retry_completed += 1
                    if paper.status == PaperStatus.COMPLETED:
                        completed_analysis += 1
                        failed_analysis -= 1
        
        # Log retry results
        if retry_completed > 0:
            task.add_log("ANALYZE_PAPERS", "INFO", f"Retry completed: {retry_completed} papers were retried", {
                "retry_completed": retry_completed,
                "final_completed": completed_analysis,
                "final_failed": failed_analysis
            })
        
        # Log overall analysis results
        task.add_log("ANALYZE_PAPERS", "INFO", f"Analysis stage completed: {completed_analysis} successful, {failed_analysis} failed", {
            "successful_analysis": completed_analysis,
            "failed_analysis": failed_analysis,
            "total_attempted": len(papers_to_analyze),
            "immediate_cache_updates": "enabled"
        })

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

    def _update_reading_cache(self, task: ProcessingTask):
        """Update the reading page cache with successfully analyzed papers"""
        import json
        
        # Path to the reading page cache
        cache_path = project_root / 'storage' / 'paper_search_agent' / 'cache.json'
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing cache
        cache = {}
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load existing cache: {e}")
                cache = {}
        
        # Add successfully analyzed papers to cache
        updated_count = 0
        skipped_count = 0
        for paper in task.papers:
            if paper.status == PaperStatus.COMPLETED and 'search' in paper.progress and 'analysis' in paper.progress:
                # Normalize title for cache key (use same logic as original paper_search_agent)
                cache_key = _normalize_title(paper.title)
                
                # Check if paper already exists in cache with summary
                if cache_key in cache and 'summary_path' in cache[cache_key]:
                    task.add_log("CACHE_UPDATE", "INFO", f"Paper already exists in cache with summary: {paper.title[:100]}...", {
                        "paper_title": paper.title,
                        "cache_key": cache_key,
                        "existing_summary_path": cache[cache_key]['summary_path']
                    })
                    skipped_count += 1
                    continue
                
                # Create cache entry
                cache_entry = {
                    "title": paper.title,
                    "url": paper.url,
                    "collected_at": task.created_at.isoformat(),
                    **paper.progress['search'],  # Include search metadata
                    "summary_path": paper.progress['analysis']['summary_path']
                }
                
                cache[cache_key] = cache_entry
                updated_count += 1
                
                task.add_log("CACHE_UPDATE", "INFO", f"Added paper to reading cache: {paper.title[:100]}...", {
                    "paper_title": paper.title,
                    "cache_key": cache_key,
                    "summary_path": paper.progress['analysis']['summary_path']
                })
        
        if updated_count > 0:
            # Save updated cache
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(cache, f, indent=2, ensure_ascii=False)
                
                task.add_log("CACHE_UPDATE", "INFO", f"Successfully updated reading cache with {updated_count} papers ({skipped_count} skipped as duplicates)", {
                    "cache_path": str(cache_path),
                    "papers_added": updated_count,
                    "papers_skipped": skipped_count,
                    "total_cache_entries": len(cache)
                })
                logging.info(f"Updated reading cache with {updated_count} papers from task {task.id} ({skipped_count} skipped)")
            except Exception as e:
                error_msg = f"Failed to save reading cache: {e}"
                task.add_log("CACHE_UPDATE", "ERROR", error_msg, {
                    "exception": str(e),
                    "cache_path": str(cache_path)
                })
                logging.error(error_msg)
        else:
            if skipped_count > 0:
                task.add_log("CACHE_UPDATE", "INFO", f"No new papers to add to reading cache ({skipped_count} papers already exist)")
            else:
                task.add_log("CACHE_UPDATE", "INFO", "No completed papers to add to reading cache")

    def _update_single_paper_to_cache(self, task: ProcessingTask, paper: PaperTask) -> bool:
        """Immediately update a single completed paper to the reading cache"""
        import json
        
        if paper.status != PaperStatus.COMPLETED or 'search' not in paper.progress or 'analysis' not in paper.progress:
            return False
        
        # Path to the reading page cache
        cache_path = project_root / 'storage' / 'paper_search_agent' / 'cache.json'
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing cache
        cache = {}
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load existing cache for single paper update: {e}")
                cache = {}
        
        # Normalize title for cache key
        cache_key = _normalize_title(paper.title)
        
        # Check if paper already exists in cache
        if cache_key in cache and 'summary_path' in cache[cache_key]:
            task.add_log("CACHE_UPDATE", "INFO", f"Paper already exists in cache, skipping: {paper.title[:100]}...", {
                "paper_title": paper.title,
                "cache_key": cache_key,
                "existing_summary_path": cache[cache_key]['summary_path']
            })
            return True
        
        # Create cache entry
        cache_entry = {
            "title": paper.title,
            "url": paper.url,
            "collected_at": task.created_at.isoformat(),
            **paper.progress['search'],  # Include search metadata
            "summary_path": paper.progress['analysis']['summary_path']
        }
        
        cache[cache_key] = cache_entry
        
        # Save updated cache immediately
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
            
            task.add_log("CACHE_UPDATE", "INFO", f"Immediately added paper to reading cache: {paper.title[:100]}...", {
                "paper_title": paper.title,
                "cache_key": cache_key,
                "summary_path": paper.progress['analysis']['summary_path'],
                "cache_path": str(cache_path)
            })
            return True
            
        except Exception as e:
            task.add_log("CACHE_UPDATE", "ERROR", f"Failed to save cache for paper: {paper.title[:100]}...", {
                "paper_title": paper.title,
                "cache_key": cache_key,
                "error": str(e),
                "cache_path": str(cache_path)
            })
            return False

    def _should_retry_paper(self, paper: PaperTask, max_retries: int = 2) -> bool:
        """Check if a paper should be retried based on failure reason and retry count"""
        if paper.status != PaperStatus.FAILED:
            return False
        
        # Get retry count from progress
        retry_count = paper.progress.get('retry_count', 0)
        
        # Check if we haven't exceeded max retries
        if retry_count >= max_retries:
            return False
        
        # Check if error is retryable (avoid retrying permanent failures)
        if paper.error:
            error_msg = paper.error.lower()
            # Don't retry if it's a permanent error
            if any(permanent_error in error_msg for permanent_error in [
                'not found', 'does not exist', '404', 'invalid url', 'malformed'
            ]):
                return False
        
        return True
    
    def _retry_paper_analysis(self, task: ProcessingTask, paper: PaperTask, paper_index: int, analysis_dir: Path, cache: dict):
        """Retry analysis for a failed paper"""
        # Increment retry count
        retry_count = paper.progress.get('retry_count', 0) + 1
        paper.progress['retry_count'] = retry_count
        
        task.add_log("ANALYZE_PAPERS", "INFO", f"Retrying analysis for paper {paper_index+1} (attempt {retry_count}): {paper.title[:100]}...", {
            "paper_index": paper_index,
            "paper_title": paper.title,
            "retry_attempt": retry_count,
            "previous_error": paper.error
        })
        
        # Reset status and error for retry
        paper.status = PaperStatus.ANALYZING
        paper.error = None
        paper.updated_at = datetime.now(timezone.utc)
        
        return self._analyze_single_paper_with_retry(task, paper, paper_index, analysis_dir, cache)
    
    def _analyze_single_paper_with_retry(self, task: ProcessingTask, paper: PaperTask, paper_index: int, analysis_dir: Path, cache: dict) -> bool:
        """Analyze a single paper with immediate cache update and return success status"""
        try:
            paper.status = PaperStatus.ANALYZING
            paper.updated_at = datetime.now(timezone.utc)
            
            task.add_log("ANALYZE_PAPERS", "INFO", f"Analyzing paper {paper_index+1}: {paper.title[:100]}...", {
                "paper_index": paper_index,
                "paper_title": paper.title,
                "paper_url": paper.url,
                "has_search_data": 'search' in paper.progress,
                "retry_count": paper.progress.get('retry_count', 0)
            })
            self.task_storage.update_task(task)
            
            paper_dict = {"title": paper.title, "url": paper.url, **paper.progress.get('search', {})}
            
            try:
                analysis_results = analyze_paper(paper_dict, self.config, self.usage_tracker)
                
                if analysis_results:
                    paper_id = paper_dict.get('arxiv_id', f'paper_{paper_index}')
                    paper_dir = analysis_dir / paper_id
                    paper_dir.mkdir(parents=True, exist_ok=True)
                    summary_path = paper_dir / 'summary.md'
                    
                    with open(summary_path, 'w', encoding='utf-8') as f:
                        f.write(analysis_results['summary'])
                    
                    paper.progress['analysis'] = {"summary_path": str(summary_path.relative_to(project_root))}
                    paper.status = PaperStatus.COMPLETED
                    paper.updated_at = datetime.now(timezone.utc)
                    
                    task.add_log("ANALYZE_PAPERS", "INFO", f"Successfully analyzed paper {paper_index+1}: {paper.title[:100]}...", {
                        "paper_index": paper_index,
                        "paper_title": paper.title,
                        "paper_id": paper_id,
                        "summary_path": str(summary_path.relative_to(project_root)),
                        "summary_length": len(analysis_results['summary']),
                        "retry_count": paper.progress.get('retry_count', 0)
                    })
                    
                    # Immediately update cache after successful analysis
                    cache_updated = self._update_single_paper_to_cache(task, paper)
                    if cache_updated:
                        task.add_log("ANALYZE_PAPERS", "INFO", f"Paper {paper_index+1} immediately added to cache", {
                            "paper_index": paper_index,
                            "paper_title": paper.title,
                            "cache_updated": True
                        })
                    
                    # Update task storage after completing the paper
                    self.task_storage.update_task(task)
                    
                    logging.info(f"Analyzed and cached: {paper.title}")
                    return True
                    
                else:
                    paper.status = PaperStatus.FAILED
                    paper.error = "Analysis function returned empty/null result"
                    paper.updated_at = datetime.now(timezone.utc)
                    
                    task.add_log("ANALYZE_PAPERS", "WARNING", f"Analysis returned no results for paper {paper_index+1}: {paper.title[:100]}...", {
                        "paper_index": paper_index,
                        "paper_title": paper.title,
                        "error": "Analysis function returned empty/null result",
                        "retry_count": paper.progress.get('retry_count', 0)
                    })
                    
                    self.task_storage.update_task(task)
                    logging.warning(f"Failed to analyze: {paper.title}")
                    return False
                    
            except Exception as analysis_error:
                error_msg = f"Analysis function error for {paper.title}: {analysis_error}"
                paper.status = PaperStatus.FAILED
                paper.error = str(analysis_error)
                paper.updated_at = datetime.now(timezone.utc)
                
                task.add_log("ANALYZE_PAPERS", "ERROR", f"Analysis function failed for paper {paper_index+1}: {paper.title[:100]}...", {
                    "paper_index": paper_index,
                    "paper_title": paper.title,
                    "exception": str(analysis_error),
                    "error_type": type(analysis_error).__name__,
                    "retry_count": paper.progress.get('retry_count', 0)
                })
                
                self.task_storage.update_task(task)
                logging.error(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Unexpected error analyzing paper {paper.title}: {e}"
            paper.status = PaperStatus.FAILED
            paper.error = str(e)
            paper.updated_at = datetime.now(timezone.utc)
            
            task.add_log("ANALYZE_PAPERS", "ERROR", f"Unexpected error during analysis of paper {paper_index+1}: {paper.title[:100]}...", {
                "paper_index": paper_index,
                "paper_title": paper.title,
                "exception": str(e),
                "error_type": type(e).__name__,
                "retry_count": paper.progress.get('retry_count', 0)
            })
            
            self.task_storage.update_task(task)
            logging.error(error_msg)
            return False
    
    def is_task_processing(self, task_id: str) -> bool:
        """Check if a task is currently being processed"""
        with self._processing_lock:
            return self._current_processing_task == task_id
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics"""
        with self._processing_lock:
            # Get queue status
            pending_task = self._get_next_pending_task()
            all_tasks = self.task_storage.get_all_tasks()
            pending_count = len([t for t in all_tasks if t.status == TaskStatus.PENDING])
            
            return {
                "current_processing_task": self._current_processing_task,
                "processing_mode": "sequential_with_scheduler",
                "scheduler_running": self._scheduler_running,
                "pending_tasks_count": pending_count,
                "next_pending_task": pending_task.id if pending_task else None
            }

