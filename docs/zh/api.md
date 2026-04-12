# API 参考

`Train in Silence` 内置了基于 FastAPI 的 HTTP 服务器，以便在 Web 环境或分布式系统中使用。

## 启动服务

```bash
uvicorn tis.api.server:app --reload
```

默认情况下，服务运行在 `http://127.0.0.1:8000`。

## 核心端点

### 1. 获取硬件推荐 (`POST /recommend`)

接收完整的规划请求结构，并返回经过筛选和排序的硬件配置。

**请求格式：**
参见 [工作负载定义](./index.md) 或 `examples/request.yaml` 的 JSON 版本。

**响应示例：**
```json
{
  "version": "0.1.0",
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
      "notes": ["可用性数据基于历史目录估算。"],
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
