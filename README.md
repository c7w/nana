# Nana 项目：论文研究助手

![paper](assets/rev1.png)

本工具是 Nana 项目的其中一个核心功能，一个旨在简化和自动化科研流程的智能助手。

它能够接收一个论文标题列表，自动在线查找论文的详细信息（如 arXiv ID 和 PDF 链接），然后利用大语言模型（LLM）来生成结构清晰、内容详尽的专业摘要。所有结果都将通过一个现代化的 FastAPI + 原生前端 Web 界面进行展示，支持PDF查看、AI摘要显示和智能聊天功能。

## 功能特性

- **自动论文信息获取**：仅需提供标题，即可自动查找论文的详细信息。
- **AI 驱动的论文摘要**：利用大语言模型深入阅读 PDF，并根据可配置的模板生成结构化的专业解读。
- **现代化Web界面**：基于 FastAPI + 原生HTML/CSS/JS 构建的响应式界面，无需额外依赖。
- **PDF在线查看**：直接在浏览器中查看论文PDF，支持缩放和导航。
- **智能聊天功能**：与PDF进行智能对话，支持上下文记忆和建议问题。
- **三栏布局设计**：论文选择、PDF/摘要查看(90vh×90vw)、聊天区域完美分割。
- **动态界面调整**：聊天框根据对话内容自动调整高度，提供最佳用户体验。
- **Markdown渲染**：支持丰富的Markdown格式，包括标题、列表、代码块等。
- **持久化缓存**：自动将成功处理的论文及其摘要保存在本地，避免重复工作和开销。
- **灵活配置**：通过 `config.yaml` 文件，可以轻松配置 API 密钥和为不同任务选择不同的大语言模型。
- **结构化日志**：在终端输出带有颜色和级别的日志，清晰地展示代理的运行状态和每一步操作。

## 快速开始

请遵循以下步骤在您的本地环境中运行本项目。

### 环境要求

- Python 3.9 或更高版本
- 一个大语言模型（LLM）提供商的 API 密钥（例如 [OpenRouter](https://openrouter.ai/)）
- 现代浏览器（支持ES6+和PDF.js）
- uvicorn（FastAPI应用服务器，已包含在requirements.txt中）

### 1. 安装

首先，将项目代码克隆到您的本地机器。强烈建议您使用 Python 虚拟环境。

```bash
# 进入项目目录
cd nana

# 创建并激活虚拟环境 (推荐)
python -m venv venv
source venv/bin/activate  # Windows 用户请使用 `venv\Scripts\activate`

# 安装所需依赖
pip install -r requirements.txt
```

### 2. 配置

本项目使用 `config.yaml` 文件来管理 API 密钥和模型偏好。为了简化配置，我们提供了一个模板文件。

1.  **重命名模板文件**：
    在 `config/` 目录下, 将 `config.template.yaml` 重命名为 `config.yaml`。

2.  **添加您的 API 密钥**：
    打开新的 `config/config.yaml` 文件，将文件中的 API 密钥占位符 (`"sk-or-v1-YOUR_OPENROUTER_API_KEY"`) 替换为您自己的密钥。您也可以在该文件中自定义不同代理任务所使用的模型。

## 使用说明

整个工作流程分为两个主要步骤：首先运行代理来收集和分析论文，然后启动现代化的 FastAPI Web 界面来查阅结果。

### 第一步：运行研究代理

代理会读取一个输入文件中的论文标题列表，处理它们，并保存结果。

1.  **创建输入列表**：
    在 `agents/` 目录下创建一个名为 `paper_search_agent.in` 的文件。如果该文件不存在，代理在首次运行时会自动为您创建一个包含示例内容的文件。

2.  **添加论文标题**：
    打开 `agents/paper_search_agent.in` 文件，在其中添加您想要研究的论文标题，每行一个。例如：
    ```
    Toolformer: Language Models Can Teach Themselves to Use Tools
    ReAct Meets ActRe: When Language Agents Enjoy Training Data Autonomy
    ```

3.  **执行代理**：
    在项目根目录下运行以下命令：
    ```bash
    python agents/paper_search_agent.py
    ```
    代理会在终端中打印出详细的日志，并将所有结果保存在 `storage/paper_search_agent/cache.json` 文件中。

### 第二步：通过现代化 Web 界面查看结果

当代理完成数据收集后，您可以启动现代化的 FastAPI Web 界面来查看和交互。

1.  **启动 FastAPI 服务**：
    进入 rev1 目录并启动服务：
    ```bash
    cd pages/paper_search_agent_rev1
    uvicorn main:app --host 0.0.0.0 --port 20002 --reload
    ```

2.  **打开交互界面**：
    在浏览器中访问 `http://localhost:20002`，您将看到一个现代化的三栏布局界面：

    - **Block 1 - 论文选择区域**：
      - 搜索和过滤论文
      - 下拉列表选择论文
      - 显示论文数量统计
      - 刷新按钮

    - **Block 2 - 主内容区域 (90vh × 90vw)**：
      - **PDF查看器** (60%)：直接在线查看论文PDF
      - **AI摘要显示** (40%)：结构化的论文解读
      - 可拖拽调整两个面板的大小比例

    - **Block 3 - 智能聊天区域**：
      - 与选中的论文进行智能对话
      - 支持上下文记忆的多轮对话
      - 自动生成的建议问题
      - 聊天框根据对话内容自动调整高度
      - 丰富的Markdown格式支持

### 界面特性

- **响应式设计**：适配不同屏幕尺寸
- **无刷新体验**：选择论文时页面内容无缝更新
- **智能交互**：点击建议问题快速开始对话
- **专业外观**：现代化的UI设计和流畅的动画效果
- **键盘支持**：回车键发送消息，Shift+回车换行

## 技术架构 (Rev1)

### 后端架构
- **FastAPI**：现代化的Python Web框架，提供高性能的API服务
- **Pydantic**：数据验证和序列化，确保API数据的类型安全
- **服务层设计**：
  - `PaperService`：论文数据管理和缓存
  - `ChatService`：聊天功能和LLM集成
  - 清晰的关注点分离和可维护性

### 前端架构
- **原生技术栈**：HTML5 + CSS3 + 原生JavaScript，无重型框架依赖
- **模块化设计**：
  - `app.js`：主应用逻辑和状态管理
  - `paper-viewer.js`：PDF查看器组件
  - `chat.js`：聊天界面组件
  - `resizer.js`：可拖拽面板调整组件
- **响应式CSS**：自适应布局，支持桌面和移动设备

### 第三方集成
- **PDF.js**：Mozilla的PDF渲染引擎，支持在线PDF查看
- **Marked.js**：高性能Markdown解析和渲染
- **MathJax**：数学公式渲染支持

### 数据流
1. 用户选择论文 → API获取论文详情 → 更新PDF和摘要显示
2. 用户发送聊天消息 → ChatService处理 → LLM生成回复 → Markdown渲染显示
3. 所有交互均为异步处理，保证界面流畅性

## 版本说明

**当前版本**: Rev1 (FastAPI + 原生前端)

Rev1 是对原版本的重大升级，从 Gradio 迁移到了更加灵活和高性能的 FastAPI + 原生前端架构。主要改进包括：

- 🚀 **更高性能**：FastAPI 提供更快的API响应速度
- 🎨 **更美观的界面**：原生CSS设计，完全可定制的用户体验
- 💬 **智能聊天功能**：与PDF进行自然语言对话，支持上下文记忆
- 📱 **更好的响应式设计**：适配各种设备屏幕尺寸
- ⚡ **无刷新体验**：所有操作都是异步的，页面切换更流畅
- 🔧 **更好的可维护性**：模块化的代码结构，便于功能扩展

如果您需要使用旧版本的Gradio界面，请运行：
```bash
python pages/paper_search_agent/app.py
```

我们强烈推荐使用Rev1版本以获得最佳的用户体验。
