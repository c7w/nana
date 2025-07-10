"""
论文服务层 - 复用现有的论文处理逻辑
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

from api.models import PaperSummary, PaperDetail, PapersListResponse

class PaperService:
    def __init__(self):
        self.project_root = project_root
        self.agent_storage_path = self.project_root / 'storage' / 'paper_search_agent'
        self.cache_path = self.agent_storage_path / 'cache.json'

    def format_collection_time(self, collected_at_str: str) -> str:
        """格式化收集时间"""
        try:
            dt = datetime.fromisoformat(collected_at_str.replace('Z', '+00:00'))
            dt_local = dt.astimezone()
            return dt_local.strftime("%m/%d %H:%M")
        except Exception:
            return "Unknown"

    def load_cache(self) -> Dict:
        """加载缓存文件"""
        if self.cache_path.exists():
            with open(self.cache_path, 'r') as f:
                return json.load(f)
        return {}

    def load_papers_data(self) -> PapersListResponse:
        """加载论文数据，返回格式化的列表"""
        cache = self.load_cache()
        papers = []
        
        for key, paper in cache.items():
            # 只显示有摘要的论文
            if not paper.get('summary_path'):
                continue
                
            collected_at = paper.get('collected_at', '')
            formatted_time = self.format_collection_time(collected_at)
            
            display_title = f"[{paper.get('arxiv_id', 'N/A')}] {paper.get('title', 'No Title')} | 📅 {formatted_time}"
            
            paper_summary = PaperSummary(
                arxiv_id=paper.get('arxiv_id'),
                title=paper.get('title', 'No Title'),
                display_title=display_title,
                pdf_url=paper.get('pdf_url'),
                summary_path=paper.get('summary_path'),
                collected_at=collected_at
            )
            papers.append(paper_summary)

        # 按收集时间排序（最新的在前）
        papers.sort(key=lambda x: x.collected_at, reverse=True)
        
        return PapersListResponse(papers=papers, total=len(papers))

    def get_paper_by_display_title(self, display_title: str) -> Optional[PaperDetail]:
        """根据显示标题获取论文详情"""
        cache = self.load_cache()
        
        # 找到匹配的论文
        for paper in cache.values():
            collected_at = paper.get('collected_at', '')
            formatted_time = self.format_collection_time(collected_at)
            paper_display_title = f"[{paper.get('arxiv_id', 'N/A')}] {paper.get('title', 'No Title')} | 📅 {formatted_time}"
            
            if paper_display_title == display_title:
                # 读取摘要内容
                summary_content = "### No summary available for this paper."
                summary_path_str = paper.get('summary_path')
                if summary_path_str:
                    summary_path = self.project_root / summary_path_str
                    if summary_path.exists():
                        summary_content = summary_path.read_text()
                    else:
                        summary_content = f"### Summary file not found at:\n`{summary_path_str}`"
                
                return PaperDetail(
                    arxiv_id=paper.get('arxiv_id'),
                    title=paper.get('title', 'No Title'),
                    display_title=paper_display_title,
                    pdf_url=paper.get('pdf_url'),
                    summary=summary_content,
                    collected_at=collected_at
                )
        
        return None

    def get_paper_by_arxiv_id(self, arxiv_id: str) -> Optional[PaperDetail]:
        """根据arXiv ID获取论文详情"""
        cache = self.load_cache()
        
        for paper in cache.values():
            if paper.get('arxiv_id') == arxiv_id:
                # 读取摘要内容
                summary_content = "### No summary available for this paper."
                summary_path_str = paper.get('summary_path')
                if summary_path_str:
                    summary_path = self.project_root / summary_path_str
                    if summary_path.exists():
                        summary_content = summary_path.read_text()
                    else:
                        summary_content = f"### Summary file not found at:\n`{summary_path_str}`"
                
                # 生成display_title
                collected_at = paper.get('collected_at', '')
                formatted_time = self.format_collection_time(collected_at)
                display_title = f"[{paper.get('arxiv_id', 'N/A')}] {paper.get('title', 'No Title')} | 📅 {formatted_time}"
                
                return PaperDetail(
                    arxiv_id=paper.get('arxiv_id'),
                    title=paper.get('title', 'No Title'),
                    display_title=display_title,
                    pdf_url=paper.get('pdf_url'),
                    summary=summary_content,
                    collected_at=paper.get('collected_at', '')
                )
        
        return None

    def get_paper_by_id(self, paper_id: str) -> Optional[PaperDetail]:
        """
        根据paper_id获取论文详情（先尝试arxiv_id，再尝试title）
        """
        # 首先尝试使用arxiv_id查找
        paper = self.get_paper_by_arxiv_id(paper_id)
        if paper:
            return paper
        
        # 如果没找到，尝试使用title查找
        cache = self.load_cache()
        for cached_paper in cache.values():
            if cached_paper.get('title') == paper_id:
                # 读取摘要内容
                summary_content = "### No summary available for this paper."
                summary_path_str = cached_paper.get('summary_path')
                if summary_path_str:
                    summary_path = self.project_root / summary_path_str
                    if summary_path.exists():
                        summary_content = summary_path.read_text()
                    else:
                        summary_content = f"### Summary file not found at:\n`{summary_path_str}`"
                
                # 生成display_title
                collected_at = cached_paper.get('collected_at', '')
                formatted_time = self.format_collection_time(collected_at)
                display_title = f"[{cached_paper.get('arxiv_id', 'N/A')}] {cached_paper.get('title', 'No Title')} | 📅 {formatted_time}"
                
                return PaperDetail(
                    arxiv_id=cached_paper.get('arxiv_id'),
                    title=cached_paper.get('title', 'No Title'),
                    display_title=display_title,
                    pdf_url=cached_paper.get('pdf_url'),
                    summary=summary_content,
                    collected_at=cached_paper.get('collected_at', '')
                )
        
        return None

    def search_papers(self, keyword: str) -> PapersListResponse:
        """搜索论文"""
        all_papers = self.load_papers_data()
        
        if not keyword:
            return all_papers
        
        # 过滤匹配关键词的论文
        filtered_papers = [
            paper for paper in all_papers.papers 
            if keyword.lower() in paper.display_title.lower()
        ]
        
        return PapersListResponse(papers=filtered_papers, total=len(filtered_papers)) 