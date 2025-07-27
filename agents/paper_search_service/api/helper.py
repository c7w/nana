"""
Helper页面API端点
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
import markdown
import logging

router = APIRouter()

@router.get("/helper/content")
async def get_helper_content():
    """获取helper页面的HTML内容"""
    try:
        # 读取markdown文件
        helper_file = Path(__file__).parent.parent / "helper_text.md"
        
        if not helper_file.exists():
            raise HTTPException(status_code=404, detail="Helper file not found")
        
        # 读取markdown内容
        with open(helper_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # 转换为HTML
        html_content = markdown.markdown(
            markdown_content,
            extensions=['codehilite', 'fenced_code', 'tables', 'nl2br']
        )
        
        return {
            "success": True,
            "html_content": html_content,
            "raw_markdown": markdown_content
        }
        
    except Exception as e:
        logging.error(f"Error reading helper content: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load helper content: {str(e)}")

@router.get("/helper/raw")
async def get_helper_raw():
    """获取helper页面的原始markdown内容"""
    try:
        helper_file = Path(__file__).parent.parent / "helper_text.md"
        
        if not helper_file.exists():
            raise HTTPException(status_code=404, detail="Helper file not found")
        
        with open(helper_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "success": True,
            "content": content
        }
        
    except Exception as e:
        logging.error(f"Error reading raw helper content: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load raw helper content: {str(e)}")
