# 市场供应商

`Train in Silence` 致力于提供可信的市场数据。数据获取方式和准确度因平台而异，我们在系统设计中通过“数据透明度（Data Transparency）”标志来解决这一问题。

## 支持平台

### 1. Vast.ai
- **数据源**: 实时 API。
- **解析方式**: 每个结果代表一个具体的机器实例。
- **确信度**: 高。库存数据为实时更新。

### 2. RunPod
- **数据源**: 实时 GraphQL。
- **解析方式**: 基于总可用 GPU 数量（maxUnreservedGpuCount）和节点配置进行聚合。
- **确信度**: 中高。地区数据通常根据库存状态（stockStatus）推断，并标记为 `is_region_estimated=true`。

- **确信度**: 中。AWS 目前的可用性数据基于目录（默认赋予乐观分值），而其地理位置和价格数据直接来自公开 API，较为准确。标记为 `is_availability_estimated=true`。
- **注意**：您可以在请求配置中使用简写的区域别名，例如 `us`（扩展为 us-east-1, us-west-2）、`eu`（eu-west-1, eu-central-1）或 `ap`（ap-northeast-1, ap-southeast-1）。

### 4. 样例数据 (内置)
- **数据源**: 本地 `tis/data/gpu_offers.json`。
- **说明**: 目前 `tis` 会聚合所捕获到的所有价格（包括竞价/社区实例和按需实例）。虽然数据中保留了 `spot` 标记，但目前的 MVP 版本中尚未提供锁定筛选特定实例类型的开关。
- **解析方式**: 仅在 `TIS_ALLOW_SAMPLE_FALLBACK=true` 且在线市场连接失败时启用。

## 数据透明度

在推荐结果中，您可能会看到 `notes` 字段。这确保了您了解数据源的性质：

- **可用性为估算值...**: 表示平台不支持实时库存查询。我们根据历史实例属性提供了一个乐观的默认分值。
- **地区为推断值...**: 表示平台未指明明确的物理位置。我们根据库存状态推断了可能的地区。

## 如何配置 API Key

在运行前设置以下环境变量。未配置的服务商将被标记为 `ok=False` 并被跳过：

```powershell
$env:VAST_API_KEY="您的 Vast Key"
$env:RUNPOD_API_KEY="您的 RunPod Key"
```
