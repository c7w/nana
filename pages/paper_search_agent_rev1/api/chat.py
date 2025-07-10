"""
聊天相关API路由
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

from api.models import ChatRequest, ChatResponse, ChatStartRequest, ErrorResponse
from services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])

# 创建服务实例
chat_service = ChatService()

@router.post("/start")
async def start_chat(request: ChatStartRequest):
    """
    开始新的聊天对话
    """
    try:
        result = await chat_service.start_conversation(request.paper_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start chat: {str(e)}")

@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    发送聊天消息
    """
    try:
        response = await chat_service.send_message(
            message=request.message,
            paper_id=request.paper_id,
            conversation_history=request.conversation_history or []
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

@router.get("/suggestions/{paper_id}")
async def get_suggested_questions(paper_id: str):
    """
    获取建议的问题列表
    """
    try:
        # 先验证论文是否存在
        paper_detail = chat_service.paper_service.get_paper_by_id(paper_id)
        if not paper_detail:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        suggestions = chat_service.get_suggested_questions(paper_detail)
        return {"suggestions": suggestions}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}") 