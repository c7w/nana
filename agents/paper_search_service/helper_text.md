## 【开发 TODO】

- [ ] 一个浏览器插件，可以直接收录 arXiv paper 到本系统。
- [ ] 对大文件的支持
- [ ] 对论文打 tagging


## 【系统帮助】

帮助你快速做 **文献调研** 的一个系统 :)

使用流程：

1. 新建任务。填写任务名和任务接收的字段（比如下面是我在 google scholar 某个 paper 的“引用”里找出来的）
2. openai/gpt-4.1 会从中抽取论文标题
3. 会调用 arXiv 和 openalex 的搜索引擎去试着在 arXiv 上找到这个工作
4. google/gemini-2.5-pro 会去为每个paper生成summary，生成完就可以在左边的 paper list 里面看到了！:)

注意 Paper 的大小不要超过 5M，不然处理的时候会有问题。


下面是一个示例输入：

```text
Echo chamber: Rl post-training amplifies behaviors learned in pretrainingPreprint
R Zhao, A Meterez, S Kakade, C Pehlevan… - arXiv preprint arXiv …, 2025 - arxiv.org
Reinforcement learning (RL)-based fine-tuning has become a crucial step in post-training
language models for advanced mathematical reasoning and coding. Following the success …
保存 引用 被引用次数：22 相关文章 所有 2 个版本 
[PDF] arxiv.org
A sober look at progress in language model reasoning: Pitfalls and paths to reproducibilityPreprint
A Hochlehnert, H Bhatnagar, V Udandarao… - arXiv preprint arXiv …, 2025 - arxiv.org
Reasoning has emerged as the next major frontier for language models (LMs), with rapid
advances from both academic and industrial labs. However, this progress often outpaces …
保存 引用 被引用次数：24 相关文章 所有 2 个版本 
[PDF] arxiv.org
Atom of thoughts for markov llm test-time scalingPreprint
F Teng, Z Yu, Q Shi, J Zhang, C Wu, Y Luo - arXiv preprint arXiv …, 2025 - arxiv.org
Large Language Models (LLMs) achieve superior performance through training-time
scaling, and test-time scaling further enhances their capabilities by conducting effective …
保存 引用 被引用次数：21 相关文章 所有 3 个版本 
[PDF] arxiv.org
Sota with less: Mcts-guided sample selection for data-efficient visual reasoning self-improvementPreprint
X Wang, Z Yang, C Feng, H Lu, L Li, CC Lin… - arXiv preprint arXiv …, 2025 - arxiv.org
In this paper, we present an effective method to enhance visual reasoning with significantly
fewer training samples, relying purely on self-improvement with no knowledge distillation …
保存 引用 被引用次数：20 相关文章 所有 3 个版本 
[PDF] arxiv.org
Right question is already half the answer: Fully unsupervised llm reasoning incentivizationPreprint
Q Zhang, H Wu, C Zhang, P Zhao, Y Bian - arXiv preprint arXiv …, 2025 - arxiv.org
Existing methods to enhance the reasoning capability of large language models
predominantly rely on supervised fine-tuning (SFT) followed by reinforcement learning (RL) …
保存 引用 被引用次数：18 相关文章 所有 2 个版本 
[PDF] arxiv.org
Crossing the Reward Bridge: Expanding RL with Verifiable Rewards Across Diverse DomainsPreprint
Y Su, D Yu, L Song, J Li, H Mi, Z Tu, M Zhang… - arXiv preprint arXiv …, 2025 - arxiv.org
Reinforcement learning with verifiable rewards (RLVR) has demonstrated significant
success in enhancing mathematical reasoning and coding performance of large language …
保存 引用 被引用次数：18 相关文章 所有 3 个版本 
[PDF] arxiv.org
Reinforcement learning from human feedbackPreprint
N Lambert - arXiv preprint arXiv:2504.12501, 2025 - arxiv.org
Reinforcement learning from human feedback (RLHF) has become an important technical
and storytelling tool to deploy the latest machine learning systems. In this book, we hope to …
保存 引用 被引用次数：11 相关文章 所有 3 个版本 
[PDF] arxiv.org
100 days after deepseek-r1: A survey on replication studies and more directions for reasoning language modelsPreprint
C Zhang, Y Deng, X Lin, B Wang, D Ng, H Ye… - arXiv preprint arXiv …, 2025 - arxiv.org
The recent development of reasoning language models (RLMs) represents a novel
evolution in large language models. In particular, the recent release of DeepSeek-R1 has …
保存 引用 被引用次数：11 相关文章 所有 2 个版本 
[PDF] arxiv.org
Not all rollouts are useful: Down-sampling rollouts in llm reinforcement learningPreprint
YE Xu, Y Savani, F Fang, Z Kolter - arXiv preprint arXiv:2504.13818, 2025 - arxiv.org
Reinforcement learning (RL) has emerged as a powerful paradigm for enhancing reasoning
capabilities in large language models, but faces a fundamental asymmetry in computation …
保存 引用 被引用次数：13 相关文章 所有 3 个版本 
[PDF] arxiv.org
Noisyrollout: Reinforcing visual reasoning with data augmentation
X Liu, J Ni, Z Wu, C Du, L Dou, H Wang, T Pang… - arXiv preprint arXiv …, 2025 - arxiv.org
Recent advances in reinforcement learning (RL) have strengthened the reasoning
capabilities of vision-language models (VLMs). However, enhancing policy exploration to …
保存 引用 被引用次数：13 相关文章 所有 2 个版本 
```


