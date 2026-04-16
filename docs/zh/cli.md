# CLI 指南

`Train in Silence` 提供了一个名为 `tis` 的命令行界面，涵盖了从请求验证到推荐生成的所有功能。

## 基础命令

所有命令都需要一个 YAML 或 JSON 格式的请求配置文件。您可以参考 `examples/request.yaml`。

### 1. 生成硬件推荐 (`recommend`)

这是最常用的命令。它会估算资源需求，抓取市场数据并输出最佳方案。

```bash
tis recommend examples/request.yaml
```

**常用选项：**
- `--output json`: 以结构化的 JSON 格式输出结果。
- `--platforms vast.ai`: 仅针对特定平台进行筛选。

### 2. 详细过程分析 (`explain`)

如果您想知道为什么推荐了这些配置，请使用 `explain` 命令。它将显示：
- 具体的资源估算值（显存、FLOPs、CPU/RAM 需求）。
- 标准化后的市场数据。
- 每个方案的时间和价格计算细节。

```bash
tis recommend examples/request.yaml --explain
# 或者直接使用 explain 命令
tis explain examples/request.yaml
```

### 3. 验证配置 (`validate`)

在提交复杂的微调任务之前，验证工作负载和约束定义是否有效。

```bash
tis validate examples/request.yaml
```

### 4. 市场探测 (`market`)

这些子命令用于调试算力供应商的状态。

- **探测状态**: `tis market probe examples/request.yaml`（显示每个供应商是否成功、原因以及 Offer 数量）。
- **导出原始数据**: `tis market dump-offers examples/request.yaml`（从第三方市场导出标准化的原始数据）。

## 环境变量

CLI 的行为受以下环境变量的影响：

| 变量 | 描述 | 默认值 |
| :--- | :--- | :--- |
| `TIS_ALLOW_SAMPLE_FALLBACK` | 是否允许在在线市场不可用时回退到样例数据。 | `true` |
| `VAST_API_KEY` | 您的 Vast.ai API Key (可选)。 | - |
| `RUNPOD_API_KEY` | 您的 RunPod API Key (可选)。 | - |

## 缓存机制

为了减少 API 调用并提高速度，`tis` 将市场数据缓存在名为 `.tis_cache` 的本地目录中。
- **默认 TTL**: 300 秒。
- 您可以随时手动删除 `.tis_cache` 以强制刷新数据。
