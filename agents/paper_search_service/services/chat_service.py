"""
聊天服务层 - 处理与PDF的对话功能
"""

import yaml
import base64
import requests
from pathlib import Path
from typing import Dict, List, Optional, AsyncGenerator
import sys
import logging

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

from tools.api.llm import call_llm
from api.models import ChatMessage, ChatResponse
from services.paper_service import PaperService
from datetime import datetime

class ChatService:
    def __init__(self):
        self.project_root = project_root
        self.paper_service = PaperService()
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """加载配置文件"""
        config_path = self.project_root / "config" / "config.yaml"
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _get_chat_llm_config(self) -> Dict:
        """获取聊天用的LLM配置 - 使用gemini 2.5 flash"""
        # 优先使用专门的聊天配置，如果不存在则回退到gemini-flash
        llm_name = "gemini-2.5-flash" if "gemini-2.5-flash" in self.config['llms'] else "gemini-flash"
        llm_config = self.config['llms'][llm_name]
        
        # 检查配置是否有效 - 只检查是否为模板默认值
        api_key = str(llm_config.get('api_key', ''))
        if not api_key or 'YOUR_OPENROUTER_API_KEY' in api_key:
            logging.warning(f"LLM配置无效: {llm_name}。请检查 config.yaml 中的 API key 设置。")
        else:
            logging.info(f"Using LLM: {llm_name} with model: {llm_config.get('model')}")
        
        return llm_config

    def _get_pdf_content_base64(self, pdf_url: str) -> Optional[str]:
        """获取PDF文件的base64内容"""
        try:
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()
            return base64.b64encode(response.content).decode('utf-8')
        except Exception as e:
            logging.error(f"Failed to fetch PDF from {pdf_url}: {e}")
            return None

    def _create_system_prompt(self, paper_detail, pdf_base64: Optional[str] = None) -> str:
        """创建系统提示词"""
        system_prompt = f"""你是一个专业的学术论文助手。你正在帮助用户理解和分析以下论文：

## 论文信息
- **标题**: {paper_detail.title}
- **arXiv ID**: {paper_detail.arxiv_id or 'N/A'}

## 论文AI摘要
{paper_detail.summary}

## 你的能力
你可以：
1. 解释论文中的概念、方法和实验结果
2. 回答关于论文内容的具体问题  
3. 分析论文的创新点、优缺点和局限性
4. 与其他相关工作进行比较分析
5. 帮助理解复杂的技术细节和数学公式

## 回答要求
- 请用中文回答
- 基于论文摘要和你的知识来回答问题
- 如果问题超出了论文范围，请明确说明
- 保持专业、准确和有帮助的语气
- 可以适当引用论文中的具体内容

请准备好回答用户关于这篇论文的问题。"""

        # 如果有PDF内容，可以在这里添加
        if pdf_base64:
            system_prompt += f"\n\n## PDF内容\n[PDF文件已加载，包含{len(pdf_base64)}字符的base64数据]"
            
        return system_prompt

    async def start_conversation(self, paper_id: str) -> Dict:
        """开始新的对话"""
        # 获取论文详情
        paper_detail = self.paper_service.get_paper_by_id(paper_id)
        if not paper_detail:
            raise ValueError(f"Paper with ID {paper_id} not found")
        
        # 获取PDF内容（可选）
        pdf_base64 = None
        if paper_detail.pdf_url:
            pdf_base64 = self._get_pdf_content_base64(paper_detail.pdf_url)
        
        # 创建系统提示词
        system_prompt = self._create_system_prompt(paper_detail, pdf_base64)
        
        return {
            "paper_detail": paper_detail,
            "system_prompt": system_prompt,
            "pdf_available": pdf_base64 is not None,
            "conversation_started": True
        }

    async def send_message(self, message: str, paper_id: str, conversation_history: List[Dict]) -> ChatResponse:
        """发送消息并获取回复"""
        # 获取论文详情
        paper_detail = self.paper_service.get_paper_by_id(paper_id)
        if not paper_detail:
            raise ValueError(f"Paper with ID {paper_id} not found")
        
        # 获取LLM配置
        llm_config = self._get_chat_llm_config()
        
        # 检查配置是否有效 - 只检查是否为模板默认值
        api_key = str(llm_config.get('api_key', ''))
        if not api_key or 'YOUR_OPENROUTER_API_KEY' in api_key:
            return ChatResponse(
                message="⚠️ 聊天功能需要配置有效的 API key。请在 `config/config.yaml` 中设置正确的 OpenRouter API key。",
                timestamp=datetime.now()
            )
        
        # 构建消息历史
        messages = []
        
        # 添加系统提示词
        pdf_base64 = None
        if paper_detail.pdf_url:
            pdf_base64 = self._get_pdf_content_base64(paper_detail.pdf_url)
        
        system_prompt = self._create_system_prompt(paper_detail, pdf_base64)
        messages.append({"role": "system", "content": system_prompt})
        
        # 添加对话历史
        for msg in conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # 添加当前用户消息
        messages.append({"role": "user", "content": message})
        
        # 调用LLM
        try:
            response_message, usage = call_llm(llm_config, messages, is_json=False)
            
            if response_message and 'content' in response_message:
                return ChatResponse(
                    message=response_message['content'],
                    timestamp=datetime.now()
                )
            else:
                logging.error(f"LLM returned invalid response: {response_message}")
                return ChatResponse(
                    message="🤖 很抱歉，我暂时无法处理您的请求。这可能是由于 API 配置问题或网络连接问题。请稍后重试。",
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            logging.error(f"Error in chat service: {e}")
            error_msg = "🤖 处理您的消息时出现了错误"
            if "401" in str(e) or "unauthorized" in str(e).lower():
                error_msg += "：API key 无效或已过期"
            elif "429" in str(e) or "rate limit" in str(e).lower():
                error_msg += "：API 调用频率超限，请稍后重试"
            elif "timeout" in str(e).lower():
                error_msg += "：网络超时，请检查网络连接"
            else:
                error_msg += f"：{str(e)}"
            
            return ChatResponse(
                message=error_msg,
                timestamp=datetime.now()
            )

    def get_suggested_questions(self, paper_detail) -> List[str]:
        """获取建议的问题列表"""
        return [
            "这篇论文的主要贡献是什么？",
            "论文使用了什么方法或技术？",
            "实验结果如何？有什么重要发现？",
            "这篇论文有什么局限性？",
            "论文与相关工作的区别在哪里？",
            "如何评价这篇论文的创新性？"
        ] 