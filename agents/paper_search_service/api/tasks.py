from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

from services.task_service import TaskProcessor
from models.task import ProcessingTask

router = APIRouter(prefix="/tasks", tags=["tasks"])

# Initialize task processor
storage_dir = Path(__file__).resolve().parent.parent / "storage" / "tasks"
task_processor = TaskProcessor(storage_dir, max_search_concurrent=3, max_analysis_concurrent=1)

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
    completed_at: Optional[str]
    error: Optional[str]

class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]

class TaskDetailResponse(BaseModel):
    id: str
    title: str
    status: str
    progress: Dict[str, Any]
    created_at: str
    updated_at: str
    completed_at: Optional[str]
    error: Optional[str]
    papers: List[Dict[str, Any]]

class TaskLogsResponse(BaseModel):
    id: str
    title: str
    logs: List[Dict[str, Any]]

@router.post("/", response_model=TaskResponse)
async def create_task(request: CreateTaskRequest):
    """Create a new paper processing task"""
    try:
        task = task_processor.task_storage.create_task(
            title=request.title,
            input_text=request.input_text,
            description=request.description
        )
        
        task_data = task_processor.get_task_status(task.id)
        return TaskResponse(**task_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

@router.get("/", response_model=TaskListResponse)
async def list_tasks():
    """Get list of all tasks"""
    try:
        tasks_data = task_processor.get_all_tasks()
        return TaskListResponse(tasks=[TaskResponse(**task) for task in tasks_data])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")

@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(task_id: str):
    """Get detailed task information"""
    try:
        task_data = task_processor.get_task_status(task_id)
        if "error" in task_data and task_data["error"] == "Task not found":
            raise HTTPException(status_code=404, detail="Task not found")
        return TaskDetailResponse(**task_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task: {str(e)}")

@router.post("/{task_id}/process")
async def start_processing(task_id: str, background_tasks: BackgroundTasks):
    """Start processing a task in the background"""
    try:
        task = task_processor.task_storage.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task.status != "pending":
            raise HTTPException(status_code=400, detail="Task is not in pending status")
        
        # Start processing in background
        background_tasks.add_task(task_processor.process_task_sync, task_id)
        
        return {"message": "Task processing started", "task_id": task_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start processing: {str(e)}")

@router.get("/{task_id}/logs", response_model=TaskLogsResponse)
async def get_task_logs(task_id: str):
    """Get detailed logs for a task"""
    try:
        task = task_processor.task_storage.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Convert logs to serializable format
        logs_data = []
        for log in task.logs:
            log_dict = {
                "timestamp": log.timestamp.isoformat(),
                "stage": log.stage,
                "level": log.level,
                "message": log.message,
                "data": log.data
            }
            logs_data.append(log_dict)
        
        return TaskLogsResponse(
            id=task.id,
            title=task.title,
            logs=logs_data
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task logs: {str(e)}")

@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """Delete a task"""
    try:
        success = task_processor.task_storage.delete_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"message": "Task deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete task: {str(e)}") 