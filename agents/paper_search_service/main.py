"""
FastAPI版本的Paper Search Agent主应用
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from api.papers import router as papers_router
from api.chat import router as chat_router

app = FastAPI(title="Paper Search Agent Rev1", version="1.0.0")

# 设置静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 设置模板目录
templates = Jinja2Templates(directory="templates")

# 包含API路由
app.include_router(papers_router, prefix="/api")
app.include_router(chat_router, prefix="/api")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """主页面"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=20002,
        reload=True,
        reload_dirs=[".", str(project_root)]
    ) 