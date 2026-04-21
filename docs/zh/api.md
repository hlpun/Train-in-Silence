# API 参考

`Train in Silence` 内置了基于 FastAPI 的 HTTP 服务器，以便在 Web 环境或分布式系统中使用。

## 启动服务

```bash
uvicorn tis.api.server:app --reload
```

默认情况下，服务运行在 `http://127.0.0.1:8000`。

## 核心端点

### 1. 获取硬件推荐 (`POST /recommend`)

接收硬件需求并返回排序后的推荐配置。支持单任务 (Workload) 或多阶段流水线 (Pipeline) 请求。

**请求 Schema (高保真要求):**
为确保估算结果的精确性，`ModelSpec` 要求必须提供以下架构参数：
- `hidden_dim`: 隐藏层维度大小。
- `num_layers`: Transformer 层数。
- `num_heads`: Query 注意力头数。
- `num_kv_heads`: KV 注意力头数 (对于 GQA/MQA 模型至关重要)。

**高级任务约束 (`Constraints`):**
我们使用物理开销模型来确保时间与成本估算的真实性。您可以根据环境调整以下参数：
- `network_speed_gbps`: 预估下载速度 (默认: 1.0 Gbps)。
- `storage_speed_gbps`: 预估磁盘到显存的带宽 (默认: 3.0 GB/s)。
- `skip_download`: 是否跳过模型下载时间计算 (默认: true)。

**请求示例:**

```json
{
  "workload": {
    "model": {
      "name": "llama-3-8b", "params": 8030000000, 
      "hidden_dim": 4096, "num_layers": 32, 
      "num_heads": 32, "num_kv_heads": 8
    },
    ...
  }
}
```

**流水线 (Pipeline) 请求:**
除了单一的 `workload`，您还可以提供 `pipeline`（任务列表），用于对涉及多阶段微调或复杂推理工作流的任务进行整体优化。

**响应示例：**
```json
{
  "version": "0.1.3",
  "summary": "Found 5 viable configurations...",
  "provider_statuses": [...],
  "recommendations": [
    {
      "label": "cheapest",
      "config": { ... },
      "metrics": {
        "time_hours": 10.5,
        "cost_usd": 12.0,
        "gpu_utilization": 0.85
      },
      "availability": {
        "score": 0.8,
        "risk": "low"
      },
      "source_detail": "live:official+supplemented",
      "notes": ["可用性数据基于历史目录估算。"]
    }
  ]
}
```

### 2. 版本信息 (`GET /version`)

**返回：** `{"version": "0.1.0"}`

### 3. 健康检查 (`GET /health`)

列出所有当前配置的算力服务商及其在线状态。

## 错误处理

API 使用标准的 HTTP 状态码，并返回结构化的错误消息：

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": [...]
  },
  "version": "0.1.0"
}
```

常见错误码：
- `validation_error`: 请求参数无效。
- `internal_error`: 市场数据抓取或算法处理失败。
