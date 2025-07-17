"""
论文相关API路由
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from api.models import PapersListResponse, PaperDetail, ErrorResponse
from services.paper_service import PaperService

router = APIRouter(prefix="/papers", tags=["papers"])

# 创建服务实例
paper_service = PaperService()

@router.get("/", response_model=PapersListResponse)
async def get_papers(keyword: Optional[str] = Query(None, description="搜索关键词")):
    """
    获取论文列表，支持关键词搜索
    """
    try:
        if keyword:
            return paper_service.search_papers(keyword)
        else:
            return paper_service.load_papers_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load papers: {str(e)}")

@router.get("/by-title", response_model=PaperDetail)
async def get_paper_by_title(display_title: str = Query(..., description="论文显示标题")):
    """
    根据显示标题获取论文详情
    """
    try:
        paper = paper_service.get_paper_by_display_title(display_title)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        return paper
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get paper: {str(e)}")

@router.get("/refresh", response_model=PapersListResponse)
async def refresh_papers():
    """
    刷新论文列表（重新加载缓存）
    """
    try:
        # 这里可以添加缓存刷新逻辑
        return paper_service.load_papers_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh papers: {str(e)}")

@router.get("/{arxiv_id}", response_model=PaperDetail)
async def get_paper_by_id(arxiv_id: str):
    """
    根据arXiv ID获取论文详情
    """
    try:
        paper = paper_service.get_paper_by_arxiv_id(arxiv_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        return paper
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get paper: {str(e)}") 