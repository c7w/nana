# Paper Search Agent Rev1

基于 FastAPI + 原生前端的论文搜索和聊天界面，升级版本无需 Gradio。

## 🚀 功能特性

- **论文浏览**: 加载并显示 Paper Search Agent 收集的论文
- **PDF 查看**: 内嵌 PDF 查看器，支持在线阅读
- **AI 摘要**: 显示 AI 生成的论文摘要，支持 MathJax 数学公式渲染
- **智能聊天**: 与 PDF 对话，基于论文内容进行问答
- **拖拽分割**: 可调整 PDF 和摘要面板大小比例 (60:40 默认)
- **浏览器缓存**: 聊天记录存储在本地，刷新后自动恢复

## 📁 项目结构

```
paper_search_agent_rev1/
├── main.py                 # FastAPI 主应用
├── requirements.txt        # Python 依赖
├── README.md              # 项目说明
├── api/                   # API 路由
│   ├── models.py          # 数据模型
│   ├── papers.py          # 论文 API
│   └── chat.py            # 聊天 API
├── services/              # 业务逻辑层
│   ├── paper_service.py   # 论文服务
│   └── chat_service.py    # 聊天服务
├── templates/             # HTML 模板
│   └── index.html         # 主页面
└── static/                # 静态资源
    ├── css/
    │   └── style.css      # 样式文件
    └── js/
        ├── app.js         # 主应用逻辑
        ├── paper-viewer.js # 论文查看器
        ├── chat.js        # 聊天功能
        └── resizer.js     # 拖拽分割线
```

## 🛠️ 安装和运行

### 1. 安装依赖

```bash
cd pages/paper_search_agent_rev1
pip install -r requirements.txt
```

### 2. 配置 LLM

确保根目录的 `config/config.yaml` 包含聊天模型配置：

```yaml
llms:
  gemini-2.5-flash:
    base_url: https://openrouter.ai/api/v1
    api_key: "sk-or-v1-YOUR_OPENROUTER_API_KEY"
    model: "google/gemini-2.0-flash-exp"
    cost:
      input: 0.35
      output: 0.70
```

### 3. 运行应用

```bash
python main.py
```

或使用 uvicorn：

```bash
uvicorn main:app --host 0.0.0.0 --port 20002 --reload
```

### 4. 访问界面

打开浏览器访问: http://localhost:20002

## 🎯 使用说明

1. **加载论文**: 页面会自动加载 Paper Search Agent 收集的论文
2. **选择论文**: 从下拉列表中选择要查看的论文
3. **查看内容**: PDF 显示在左侧，AI 摘要显示在右侧
4. **调整布局**: 拖拽中间的分割线调整面板大小，双击重置为 60:40
5. **开始聊天**: 点击 "💬 Chat with PDF" 按钮开始与论文对话
6. **智能问答**: 询问论文相关问题，支持建议问题快速开始

## 🔧 技术栈

- **后端**: FastAPI + Python
- **前端**: 原生 HTML/CSS/JavaScript
- **PDF 渲染**: 浏览器原生 iframe
- **Markdown 渲染**: Marked.js
- **数学公式**: MathJax
- **样式**: 现代 CSS Grid/Flexbox
- **缓存**: localStorage (浏览器本地存储)

## 📋 API 端点

### 论文 API
- `GET /api/papers/` - 获取论文列表
- `GET /api/papers/by-title` - 根据标题获取论文详情
- `GET /api/papers/{arxiv_id}` - 根据 arXiv ID 获取论文详情
- `GET /api/papers/refresh` - 刷新论文列表

### 聊天 API
- `POST /api/chat/start` - 开始新对话
- `POST /api/chat/message` - 发送聊天消息
- `GET /api/chat/suggestions/{paper_id}` - 获取建议问题

## 🎨 界面特色

- **响应式设计**: 支持桌面和移动设备
- **现代 UI**: 简洁美观的界面设计
- **拖拽交互**: 直观的面板大小调整
- **实时渲染**: MathJax 数学公式实时渲染
- **动画效果**: 平滑的消息淡入动画
- **状态指示**: 加载状态和错误提示

## 🔗 与原版差异

| 特性 | Gradio 版本 | FastAPI 版本 |
|------|-------------|--------------|
| 框架 | Gradio | FastAPI + 原生前端 |
| 依赖 | 较重 (Gradio 生态) | 轻量 (仅核心依赖) |
| 定制性 | 受限 | 完全可定制 |
| 聊天功能 | ❌ | ✅ |
| 拖拽调整 | 有限 | 完整支持 |
| 缓存机制 | 服务器端 | 浏览器端 |
| 部署复杂度 | 简单 | 中等 |

## 🚀 后续扩展

- [ ] 添加论文搜索和过滤功能
- [ ] 支持多种 PDF 查看模式
- [ ] 导出聊天记录功能
- [ ] 用户认证和多用户支持
- [ ] 论文标注和高亮功能
- [ ] 更多 AI 模型选择 