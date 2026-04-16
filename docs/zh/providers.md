# 市场供应商

`Train in Silence` 通过多层数据聚合解决了 GPU 市场碎片化的问题。我们提供一套 **5 层级数据层级策略**，以确保数据的准确性、实时性和“即开即用”的体验。

## 数据层级策略

TIS 按以下优先级顺序获取市场数据：

1.  **Level 1: 直连厂商 (官方 API)**: 
    - 适用场景：为您最常用的平台提供最高的准确性和实时库存。
    - 平台：**Vast.ai, RunPod, AWS**。
    - 鉴权：需要 API Key。
2.  **Level 2: 实时聚合器 (GPUHunt)**: 
    - 适用场景：为去中心化或高动态市场提供最新的可用性和价格。
    - 平台：**TensorDock, Lambda Labs, Paperspace, CoreWeave 等**。
    - 鉴权：**无**（无需 Key）。
3.  **Level 3: 通用兜底 (GPUFinder)**: 
    - 适用场景：覆盖 10 多家较冷门的供应商。
    - 平台：**GCP, Azure, CloudRift, Cudo Compute, Verda, Nebius, OCI 等**。
    - 鉴权：**无**（无需 Key）。
4.  **Level 4: 智能补全 (Supplementation)**: 
    - TIS 会自动“修补”缺失的元数据（例如，如果某个厂商 API 返回了价格但缺失 CPU/RAM 详情），通过跨层级比对自动填补。
5.  **Level 5: 样品数据兜底**: 
    - 仅作为最后的安全网，当所有网络连接都失败时使用。

## 支持平台

TIS 目前已覆盖几乎所有主流 GPU 云：

| 类别 | 包含平台 | 鉴权要求 |
|----------|-----------|------|
| **核心直连** | Vast.ai, RunPod, AWS | **可选** (推荐配置以获得更高精度) |
| **算力市场** | TensorDock, Cudo Compute, Verda | **无 (Keyless)** |
| **精品云** | Lambda Labs, CoreWeave, Paperspace, CloudRift | **无 (Keyless)** |
| **头部厂商** | GCP, Azure, OCI | **无 (Keyless)** |
| **专业算力** | Nebius | **无 (Keyless)** |

## 数据透明度

每条推荐都会通过 `source_detail` 标记明确其**真值来源 (Source of Truth)**：
- `live:official`: 直接来自厂商 API 的数据。
- `live:gpuhunt`: 来自高保真聚合器的实时数据。
- `live:gpufinder`: 来自广度聚合器的通用数据。
- `live:official+supplemented`: 结合了官方报价与聚合器元数据的合并数据。
- `sample`: 来自本地离线包的陈旧数据。

## 配置方式

API Key 现在是**可选的**。如果您希望在特定平台上获得更高精度，请设置以下环境变量：

```powershell
$env:VAST_API_KEY="您的 Vast Key"
$env:RUNPOD_API_KEY="您的 RunPod Key"
```

如果未提供，TIS 将自动尝试通过 `gpuhunt` 或 `gpufindr` 层级寻找相同的报价。
