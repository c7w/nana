from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import json
import fcntl  # For file locking on Unix systems
import time
from pathlib import Path


class LogEntry(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    stage: str
    level: str  # INFO, WARNING, ERROR
    message: str
    data: Optional[Dict[str, Any]] = None


class TaskStatus(str, Enum):
    PENDING = "pending"
    FORMATTING_INPUT = "formatting_input"
    SEARCHING_PAPERS = "searching_papers"
    ANALYZING_PAPERS = "analyzing_papers"
    COMPLETED = "completed"
    FAILED = "failed"


class PaperStatus(str, Enum):
    PENDING = "pending"
    FORMATTING = "formatting"
    SEARCHING = "searching"
    SEARCH_COMPLETED = "search_completed"  # New: search done, ready for analysis
    ANALYZING = "analyzing"
    COMPLETED = "completed"  # Fully completed (both search and analysis)
    FAILED = "failed"


class PaperTask(BaseModel):
    title: str
    url: Optional[str] = None
    status: PaperStatus = PaperStatus.PENDING
    progress: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProcessingTask(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    papers: List[PaperTask] = Field(default_factory=list)
    input_text: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    progress: Dict[str, Any] = Field(default_factory=dict)
    logs: List[LogEntry] = Field(default_factory=list)
    
    def update_status(self, status: TaskStatus):
        self.status = status
        self.updated_at = datetime.now(timezone.utc)
        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            self.completed_at = datetime.now(timezone.utc)
    
    def add_log(self, stage: str, level: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Add a log entry to the task"""
        log_entry = LogEntry(
            stage=stage,
            level=level,
            message=message,
            data=data
        )
        self.logs.append(log_entry)
        self.updated_at = datetime.now(timezone.utc)
    
    def get_progress_summary(self) -> Dict[str, Any]:
        total_papers = len(self.papers)
        if total_papers == 0:
            return {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "pending": 0,
                "percentage": 0
            }
        
        status_counts = {}
        for paper in self.papers:
            status_counts[paper.status] = status_counts.get(paper.status, 0) + 1
        completed = status_counts.get(PaperStatus.COMPLETED, 0)
        failed = status_counts.get(PaperStatus.FAILED, 0)
        pending = total_papers - completed - failed
        
        return {
            "total": total_papers,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "percentage": round((completed + failed) / total_papers * 100)
        }


class TaskStorage:
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_file = storage_dir / "tasks.json"
        self._load_tasks()
    
    def _load_tasks(self):
        if self.tasks_file.exists():
            try:
                with open(self.tasks_file, "r", encoding='utf-8') as f:
                    data = json.load(f)
                    self.tasks = {}
                    for task_id, task_data in data.items():
                        # Convert datetime strings back to datetime objects
                        for key, value in task_data.items():
                            if key in ['created_at', 'updated_at', 'completed_at'] and isinstance(value, str):
                                try:
                                    task_data[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                except ValueError:
                                    pass
                        # Handle papers list
                        if 'papers' in task_data:
                            for paper in task_data['papers']:
                                for paper_key, paper_value in paper.items():
                                    if paper_key in ['created_at', 'updated_at'] and isinstance(paper_value, str):
                                        try:
                                            paper[paper_key] = datetime.fromisoformat(paper_value.replace('Z', '+00:00'))
                                        except ValueError:
                                            pass
                        
                        # Handle logs list
                        if 'logs' in task_data:
                            for log in task_data['logs']:
                                for log_key, log_value in log.items():
                                    if log_key == 'timestamp' and isinstance(log_value, str):
                                        try:
                                            log[log_key] = datetime.fromisoformat(log_value.replace('Z', '+00:00'))
                                        except ValueError:
                                            pass
                        
                        self.tasks[task_id] = ProcessingTask(**task_data)
            except Exception as e:
                print(f"Error loading tasks: {e}")
                self.tasks = {}
        else:
            self.tasks = {}
    
    def _save_tasks(self):
        """Save tasks with file locking to prevent concurrent access issues"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Convert tasks to serializable format
                serializable_tasks = {}
                for task_id, task in self.tasks.items():
                    task_dict = task.dict()
                    # Convert datetime objects to ISO format strings
                    for key, value in task_dict.items():
                        if isinstance(value, datetime):
                            task_dict[key] = value.isoformat()
                    # Handle papers list
                    if 'papers' in task_dict:
                        for paper in task_dict['papers']:
                            for paper_key, paper_value in paper.items():
                                if isinstance(paper_value, datetime):
                                    paper[paper_key] = paper_value.isoformat()
                    
                    # Handle logs list
                    if 'logs' in task_dict:
                        for log in task_dict['logs']:
                            for log_key, log_value in log.items():
                                if isinstance(log_value, datetime):
                                    log[log_key] = log_value.isoformat()
                    
                    serializable_tasks[task_id] = task_dict
                
                # Use file locking for atomic writes (Unix/macOS)
                try:
                    with open(self.tasks_file, "w", encoding='utf-8') as f:
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock
                        json.dump(serializable_tasks, f, indent=2, ensure_ascii=False)
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Release lock
                    break  # Success, exit retry loop
                except (OSError, IOError) as lock_error:
                    # Handle systems without fcntl (like Windows) or lock contention
                    if attempt == max_retries - 1:
                        # Last attempt, try without locking
                        with open(self.tasks_file, "w", encoding='utf-8') as f:
                            json.dump(serializable_tasks, f, indent=2, ensure_ascii=False)
                    else:
                        # Wait and retry
                        time.sleep(0.1 * (attempt + 1))
                        continue
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"Error saving tasks after {max_retries} attempts: {e}")
                else:
                    time.sleep(0.1 * (attempt + 1))
    
    def create_task(self, title: str, input_text: str, description: Optional[str] = None) -> ProcessingTask:
        import uuid
        task_id = str(uuid.uuid4())
        
        task = ProcessingTask(
            id=task_id,
            title=title,
            description=description,
            input_text=input_text
        )
        
        self.tasks[task_id] = task
        self._save_tasks()
        return task
    
    def add_task(self, task: ProcessingTask):
        """Add an existing ProcessingTask instance to storage"""
        self.tasks[task.id] = task
        self._save_tasks()

    def get_task(self, task_id: str) -> Optional[ProcessingTask]:
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[ProcessingTask]:
        return list(self.tasks.values())
    
    def update_task(self, task: ProcessingTask):
        task.updated_at = datetime.now(timezone.utc)
        self.tasks[task.id] = task
        self._save_tasks()
    
    def delete_task(self, task_id: str) -> bool:
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._save_tasks()
            return True
        return False 