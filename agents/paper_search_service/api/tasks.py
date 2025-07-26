from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

from services.task_service import TaskProcessor
from models.task import ProcessingTask

router = APIRouter(prefix="/tasks", tags=["tasks"])

# Initialize task processor (simplified, no concurrency parameters)
storage_dir = Path(__file__).resolve().parent.parent / "storage" / "tasks"
task_processor = TaskProcessor(storage_dir)

class CreateTaskRequest(BaseModel):
    title: str
    input_text: str
    description: Optional[str] = None

class TaskResponse(BaseModel):
    id: str
    title: str
    status: str
    progress: Dict[str, Any]
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None

class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]

class TaskDetailResponse(BaseModel):
    id: str
    title: str
    status: str
    progress: Dict[str, Any]
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None
    papers: List[Dict[str, Any]]

class TaskLogsResponse(BaseModel):
    task_id: str
    logs: List[Dict[str, Any]]

@router.post("/", response_model=TaskResponse)
async def create_task(request: CreateTaskRequest):
    """Create a new task and add it to the processing queue"""
    try:
        import uuid
        task = ProcessingTask(
            id=str(uuid.uuid4()),
            title=request.title,
            input_text=request.input_text,
            description=request.description
        )
        task_processor.task_storage.add_task(task)
        
        # Task will be automatically picked up by the scheduler
        return TaskResponse(
            id=task.id,
            title=task.title,
            status=task.status,
            progress=task.get_progress_summary(),
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            error=task.error
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

@router.get("/", response_model=TaskListResponse)
async def get_tasks():
    """Get all tasks"""
    try:
        tasks_data = task_processor.get_all_tasks()
        tasks = [TaskResponse(**task_data) for task_data in tasks_data]
        return TaskListResponse(tasks=tasks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tasks: {str(e)}")

@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(task_id: str):
    """Get detailed information about a specific task"""
    try:
        task_data = task_processor.get_task_status(task_id)
        if "error" in task_data and task_data["error"] == "Task not found":
            raise HTTPException(status_code=404, detail="Task not found")
        return TaskDetailResponse(**task_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task: {str(e)}")

@router.get("/{task_id}/logs", response_model=TaskLogsResponse)
async def get_task_logs(task_id: str):
    """Get detailed logs for a task"""
    try:
        task = task_processor.task_storage.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        logs = []
        for log in task.logs:
            log_dict = {
                "timestamp": log.timestamp.isoformat(),
                "stage": log.stage,
                "level": log.level,
                "message": log.message,
                "data": log.data
            }
            logs.append(log_dict)
        
        return TaskLogsResponse(task_id=task_id, logs=logs)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task logs: {str(e)}")

@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """Delete a task"""
    try:
        task = task_processor.task_storage.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Check if task is currently being processed
        if task_processor.is_task_processing(task_id):
            raise HTTPException(status_code=409, detail="Cannot delete task that is currently being processed")
        
        task_processor.task_storage.delete_task(task_id)
        return {"message": f"Task {task_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete task: {str(e)}")

@router.get("/system/stats")
async def get_system_stats():
    """Get system processing statistics"""
    try:
        stats = task_processor.get_processing_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system stats: {str(e)}") 