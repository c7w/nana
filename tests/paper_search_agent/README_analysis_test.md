# Paper Analysis Testing Guide

这个测试脚本用于测试不同 LLM 模型在论文分析任务上的表现。

## 功能特性

- ✅ 支持测试多个模型的论文分析效果
- ✅ 包含 5 篇经典论文作为测试用例
- ✅ 自动评估分析质量（结构完整性、字数、用时等）
- ✅ 生成详细的对比报告和成本分析
- ✅ 支持单个模型快速测试

## 使用方法

### 1. 测试所有可用模型

```bash
cd tests/paper_search_agent
python test_paper_analysis.py
```

### 2. 测试指定模型

```bash
# 测试特定模型
python test_paper_analysis.py --models gpt-4o-mini claude-3-5-sonnet-20241022

# 测试单个模型
python test_paper_analysis.py --models gemini-pro
```

### 3. 测试指定论文

```bash
# 只测试前两篇论文（索引 0, 1）
python test_paper_analysis.py --papers 0 1

# 只测试 Transformer 论文（索引 0）
python test_paper_analysis.py --papers 0 --models gpt-4o-mini
```

### 4. 快速单次测试

```bash
# 测试 GPT-4o-mini 处理 Transformer 论文
python test_paper_analysis.py --single --model gpt-4o-mini --paper-index 0

# 测试 Claude 处理 BERT 论文
python test_paper_analysis.py --single --model claude-3-5-sonnet-20241022 --paper-index 1
```

## 测试论文列表

| 索引 | 论文标题 | arXiv ID | 年份 |
|------|----------|----------|------|
| 0 | Attention Is All You Need | 1706.03762 | 2017 |
| 1 | BERT: Pre-training of Deep Bidirectional Transformers | 1810.04805 | 2018 |
| 2 | Language Models are Few-Shot Learners (GPT-3) | 2005.14165 | 2020 |
| 3 | ReAct: Synergizing Reasoning and Acting | 2210.03629 | 2022 |
| 4 | Gödel Agent: Self-Referential Agent Framework | 2410.04444 | 2024 |

## 评估指标

测试脚本会自动评估以下指标：

### 质量指标
- **成功率**：模型是否成功生成分析报告
- **结构完整性**：是否包含期望的章节（一句话总结、论文概览、方法详解等）
- **内容长度**：生成的分析报告字数和字符数

### 性能指标
- **响应时间**：从请求到获得结果的时间
- **成本分析**：Token 使用量和预估费用

### 报告内容
- 📊 **模型对比表格**：展示各模型的成功率、平均用时、平均字数等
- 💰 **成本分析**：显示每个模型的 Token 消耗和费用
- 🎯 **推荐建议**：基于测试结果给出最可靠、最快、最详细的模型推荐

## 输出示例

```
🧪 Testing Paper Analysis Module
📄 Papers to test: 2
🤖 Models to test: 3
🔧 Models: gpt-4o-mini, claude-3-5-sonnet-20241022, gemini-pro

================================================================================
Testing model: gpt-4o-mini
Paper: Attention Is All You Need
arXiv ID: 1706.03762
================================================================================
✅ Analysis completed successfully!
   Duration: 15.32 seconds
   Summary length: 1248 words, 8542 characters

📝 Summary preview (first 500 chars):
------------------------------------------------------------
# 作者 机构 与 核心摘要 (One-Sentence Summary)

**一句话总结**：本文提出了完全基于注意力机制的Transformer架构，抛弃了循环和卷积网络，在机器翻译任务上取得了最佳性能同时显著提升了并行化效率。

## 论文概览 (Paper Overview)

**研究背景**：在序列建模和转换任务中，循环神经网络（RNN）特别是长短期记忆网络（LSTM）和门控循环单元...
------------------------------------------------------------

🔍 Sections found: 8/8
   Found: 一句话总结, 论文概览, 方法详解, 实验分析, 优势与不足, 启发与思考, 作者, 核心摘要

====================================================================================================
📊 COMPREHENSIVE ANALYSIS REPORT
====================================================================================================

🏆 MODEL PERFORMANCE COMPARISON
Model Name                Success Rate Avg Duration Avg Words  Avg Sections
---------------------------------------------------------------------------
gpt-4o-mini                   100.0%     15.3s      1248       8.0
claude-3-5-sonnet-20241022    100.0%     12.8s      1456       8.0
gemini-pro                    100.0%     18.1s      1122       7.5

💰 COST ANALYSIS
--------------------------------------------------
gpt-4o-mini              $0.012450
claude-3-5-sonnet-20241022 $0.018750
gemini-pro               $0.008930
TOTAL COST               $0.040130

🎯 RECOMMENDATIONS
------------------------------
🏅 Most reliable: gpt-4o-mini (100.0% success)
⚡ Fastest: claude-3-5-sonnet-20241022 (12.8s average)
📝 Most detailed: claude-3-5-sonnet-20241022 (8.0 sections average)
```

## 配置要求

确保你的 `config/config.yaml` 文件中包含了要测试的模型配置：

```yaml
llms:
  gpt-4o-mini:
    provider: openai
    model: gpt-4o-mini
    # ... 其他配置
  
  claude-3-5-sonnet-20241022:
    provider: anthropic 
    model: claude-3-5-sonnet-20241022
    # ... 其他配置

  gemini-pro:
    provider: google
    model: google/gemini-2.5-pro-preview-06-05
    # ... 其他配置
```

## 结果保存

测试结果会自动保存到 `tests/paper_search_agent/analysis_test_results_YYYYMMDD_HHMMSS.json` 文件中，包含：
- 每个模型对每篇论文的详细分析结果
- Token 使用统计
- 完整的分析文本内容

这样你就可以离线查看和比较不同模型的分析质量了！ 