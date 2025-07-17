# Scripts 目录 - 离线处理工具

本目录包含用于离线处理论文数据的脚本工具。这些脚本可以独立运行，用于批量处理、数据维护和系统管理任务。

## 📁 脚本列表

### `paper_search_agent.py` - 主要论文处理脚本

这是核心的论文搜索和分析脚本，支持两种工作模式。

#### 🔧 功能特性

- **批量论文处理**：从文件读取论文列表并批量处理
- **引用提取模式**：从 PDF 文件中提取引用的论文
- **智能搜索**：自动查找论文的 PDF 链接和元数据
- **AI 摘要生成**：为每篇论文生成详细的 AI 摘要
- **缓存机制**：避免重复处理已分析的论文
- **成本追踪**：显示 API 调用的详细成本信息

#### 📖 使用方法

**模式 1: 从文件读取论文列表**

```bash
cd agents/paper_search_service/scripts

# 基本用法 - 从 paper_search_agent.in 文件读取
python paper_search_agent.py

# 指定从文件模式（默认）
python paper_search_agent.py --mode from_file
```

输入文件格式 (`paper_search_agent.in`)：
```
Revisiting the Effectiveness of NeRFs for Dense Mapping https://arxiv.org/abs/2405.09332
Generative Pre-training of Diffusion Models
Neural Radiance Fields for 3D Scene Understanding
```

**模式 2: 从 PDF 引用中提取论文**

```bash
# 从 PDF 文件的引用部分提取论文
python paper_search_agent.py --mode from_citation \
    --pdf "/path/to/paper.pdf" \
    --snippet "Here are some key papers: [1] Smith et al. 2023 [2] Johnson et al. 2022"
```

#### 📝 输入文件格式

创建 `paper_search_agent.in` 文件，支持以下格式：

```
# 基本格式：标题
Paper Title Here

# 带 URL 格式：标题 + URL
Another Paper Title https://arxiv.org/abs/1234.5678

# 带元数据格式：
{
  "title": "Detailed Paper Title",
  "url": "https://arxiv.org/abs/1234.5678",
  "authors": ["Author 1", "Author 2"]
}

# 混合格式
Simple Title 1
Complex Title with URL https://example.com/paper.pdf
```

#### 🗂️ 输出结果

脚本会在以下位置生成结果：

```
storage/paper_search_agent/
├── cache.json                    # 论文缓存数据库
├── 2024-01-15/                  # 按日期组织的结果
│   ├── 2401.12345/              # 按 arXiv ID 组织
│   │   └── summary.md           # 论文 AI 摘要
│   └── unknown_id/              # 无 arXiv ID 的论文
│       └── summary.md
└── 2024-01-16/
    └── ...
```

#### 💰 成本控制

脚本会显示详细的 API 使用情况：

```
--- Token Usage & Cost ---
Model: gemini-2.5-flash
  Input Tokens: 15420
  Output Tokens: 3240
  Estimated Cost (USD): $0.008640

--- Total Estimated Cost ---
USD: $0.0086
CNY: ¥0.0617
```

#### ⚙️ 高级配置

编辑 `config/config.yaml` 来自定义行为：

```yaml
agents:
  paper_search_agent:
    1_input_formatting: "gemini-flash"     # 输入格式化模型
    2_recall_papers: "gemini-flash"        # 论文搜索模型
    3_2_paper_summary: "gemini-flash"      # 摘要生成模型

llms:
  gemini-flash:
    base_url: "https://openrouter.ai/api/v1"
    api_key: "your-api-key"
    model: "google/gemini-1.5-flash"
    cost:
      input: 0.15   # 每百万 token 的输入成本
      output: 0.60  # 每百万 token 的输出成本
```

## 🛠️ 脚本开发指南

### 添加新脚本

如果需要添加新的处理脚本，请遵循以下模式：

```python
#!/usr/bin/env python3
"""
新脚本的描述
"""

import sys
from pathlib import Path

# 设置项目根路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

# 导入共享工具
from tools.log_config import setup_logging
from tools.api.llm import call_llm

def main():
    """主要功能"""
    setup_logging()
    # 脚本逻辑
    pass

if __name__ == "__main__":
    main()
```

### 脚本命名规范

- 使用描述性的文件名：`paper_analysis.py`、`data_cleanup.py`
- 添加详细的文档字符串
- 包含使用示例和参数说明

## 🔍 故障排除

### 常见问题

**1. 配置文件未找到**
```bash
# 检查配置文件是否存在
ls -la ../../../config/config.yaml

# 如果不存在，从模板复制
cp ../../../config/config.template.yaml ../../../config/config.yaml
```

**2. API Key 无效**
```
⚠️ Warning: LLM配置无效: gemini-flash。请检查 config.yaml 中的 API key 设置。
```

解决方法：编辑 `config/config.yaml`，设置有效的 API Key。

**3. 输入文件不存在**
```
Input file not found at paper_search_agent.in
Created a dummy input file for you at 'paper_search_agent.in'. Please edit it and run again.
```

解决方法：编辑生成的 `paper_search_agent.in` 文件，添加你要处理的论文。

**4. 权限错误**
```bash
# 确保存储目录有写权限
chmod -R 755 ../../../storage/
```

### 调试技巧

**启用详细日志**：
```bash
# 设置环境变量启用调试日志
export LOG_LEVEL=DEBUG
python paper_search_agent.py
```

**检查缓存状态**：
```bash
# 查看缓存文件
cat ../../../storage/paper_search_agent/cache.json | jq .

# 清空缓存（谨慎操作）
rm ../../../storage/paper_search_agent/cache.json
```

## 📊 性能优化

### 批量处理优化

对于大量论文的处理：

1. **分批处理**：将大的输入文件分成小批次
2. **并行处理**：考虑使用多进程（注意 API 限制）
3. **错误恢复**：利用缓存机制，失败后可以断点续传

### 成本优化

1. **选择合适的模型**：
   - 格式化：使用较小的模型（如 `gemini-flash`）
   - 摘要生成：可以使用更大的模型获得更好质量

2. **缓存利用**：
   - 避免重复处理相同论文
   - 检查缓存中是否已有结果

## 🔄 集成与自动化

### 定时任务

设置 cron 任务定期处理论文：

```bash
# 编辑 crontab
crontab -e

# 添加每天凌晨 2 点执行的任务
0 2 * * * cd /path/to/nana/agents/paper_search_service/scripts && python paper_search_agent.py
```

### CI/CD 集成

在 GitHub Actions 中使用：

```yaml
name: Process Papers
on:
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨 2 点

jobs:
  process:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Process papers
        run: |
          cd agents/paper_search_service/scripts
          python paper_search_agent.py
```

## 📈 监控和指标

### 处理统计

脚本会输出详细的处理统计：

```
--- Final Report ---
Total papers in input: 10

[Recall Stage]
Successfully found details for 8 papers (3 from cache).
Failed to find details for 2 papers.

[Analysis Stage]
Successfully analyzed 7 papers (2 from cache).
Failed to analyze 1 papers.
```

### 日志监控

关键日志位置：
- `../../../logs/` - 系统日志
- `server.log` - 服务日志（如果存在）

---

## 📞 获取帮助

如果在使用脚本时遇到问题：

1. 检查 `DEPLOYMENT.md` 中的故障排除部分
2. 查看日志文件获取详细错误信息  
3. 确认配置文件和 API Key 设置正确
4. 验证输入文件格式是否正确

更多详细的部署和配置信息，请参考项目根目录的 `DEPLOYMENT.md` 文件。 