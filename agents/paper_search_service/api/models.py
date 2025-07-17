"""
API数据模型定义
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class PaperSummary(BaseModel):
    """论文基本信息"""
    arxiv_id: Optional[str] = None
    title: str
    display_title: str
    pdf_url: Optional[str] = None
    summary_path: Optional[str] = None
    collected_at: str

class PaperDetail(BaseModel):
    """论文详细信息"""
    arxiv_id: Optional[str] = None
    title: str
    display_title: str
    pdf_url: Optional[str] = None
    summary: str
    collected_at: str

class PapersListResponse(BaseModel):
    """论文列表响应"""
    papers: List[PaperSummary]
    total: int

class ChatMessage(BaseModel):
    """聊天消息"""
    role: str  # "user" 或 "assistant"
    content: str
    timestamp: datetime

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    paper_id: str
    conversation_history: Optional[List[Dict[str, Any]]] = []

class ChatResponse(BaseModel):
    """聊天响应"""
    message: str
    timestamp: datetime

class ChatStartRequest(BaseModel):
    """开始聊天请求"""
    paper_id: str

class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None 