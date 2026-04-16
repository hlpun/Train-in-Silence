# 架构与核心逻辑

`Train in Silence` 的核心目标是将抽象的训练工作负载转化为具体的硬件推荐。其工作流为：**分析 (Analyze) -> 估算 (Estimate) -> 抓取 (Fetch) -> 优化 (Optimize)**。

## 系统架构

```text
输入 (工作负载 + 约束)
        - [资源估算器] ----> 计算所需的显存、CPU、内存和总 FLOPs
        - [市场聚合器] ----> 通过 5 层级策略聚合各渠道报价
        - [优化器引擎] ----> 过滤无效选项，计算时间/成本，生成帕累托前沿
        - [推荐模块]   ----> 输出带有“真值来源”标记的排序结果
```

## 核心算法

### 1. 资源估算

估算逻辑主要遵循以下模型（详见 `tis/planner/estimator.py`）：
- **显存估算**：精确计算，综合考虑模型参数、精度、批次大小以及 KV Cache（基于 `hidden_dim`, `num_heads`, `num_layers` 等架构参数）。
- **FLOPs 与吞吐量**：
    - **训练**：遵循标准 $6 \times \text{Params} \times \text{Tokens}$ 缩放定律。
    - **推理（两阶段）**：区分 **Prefill (全量参数)** 与 **Decoding (MoE 激活参数)**。公式如下：$2 \times (\text{Params} \times \text{Prefill\_Tokens} + \text{Active\_Params} \times \text{New\_Tokens})$。
- **分布式损耗 (Distributed Taxes)**：估算多 GPU 配置下的 CPU 和 RAM 额外开销（如通信缓冲区和并行编排开销）。

### 2. 帕累托优化 (Pareto Optimization)

一个“好”的硬件配置通常涉及两个冲突的指标：**更低的成本**和**更快的用时**。

系统不会仅仅返回一个“最佳”值，而是计算**帕累托前沿 (Pareto Frontier)**：即在这个选项集合中，没有任何一个选项可以在不损害一个指标的情况下改进另一个指标。

### 3. 多层级数据策略

系统采用 5 层级方法，确保官方数据的准确性与全球覆盖范围之间的平衡：
1. **直连 API**：Vast.ai, Runpod, 以及 AWS (公开价格) 的实时行情。
2. **GPUHunt**：针对 Lambda, Fluidstack 等动态市场的实时聚合。
3. **GPUFinder**：长尾服务商的全网可见性覆盖。
4. **智能融合 (Consolidation)**：3 层元数据合并策略（官方数据辅以 GPUHunt 和 GPUFinder，用于补全显存带宽、CPU 核心等缺失字段）。
5. **样品数据兜底**：高质量的离线数据安全网。

每条结果都标有 `source_detail`（如 `live:official`, `live:gpuhunt`），以确保数据实时性的全方位透明。

## 模块概览

- `tis/planner/models.py`: 核心数据结构定义（Pydantic 模型）。
- `tis/planner/workload.py`: 请求加载、验证和解析逻辑。
- `tis/planner/market/`: 市场供应商的具体实现和抽象层。
- `tis/planner/pareto.py`: 前沿计算算法。
- `tis/planner/recommender.py`: 推荐排序和响应构建。
