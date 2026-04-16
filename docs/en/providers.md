# Market Providers

`Train in Silence` solves the fragmented GPU market problem by aggregating data across multiple layers. We provide a **5-layer hierarchical data strategy** to ensure accuracy, real-time performance, and a "ready-to-use" experience.

## Hierarchical Data Strategy

TIS fetches market data in the following order of priority:

1.  **Level 1: Dedicated Providers (Official APIs)**: 
    - Best for: Highest accuracy and real-time inventory for platforms you use most.
    - Platforms: **Vast.ai, RunPod, AWS**.
    - Auth: Requires API Keys.
2.  **Level 2: Real-time Aggregator (GPUHunt)**: 
    - Best for: Fresh availability and pricing for decentralized or high-dynamism markets.
    - Platforms: **TensorDock, Lambda Labs, Paperspace, CoreWeave, etc.**
    - Auth: **None**.
3.  **Level 3: Universal Fallback (GPUFinder)**: 
    - Best for: Broad coverage across 10+ less common providers.
    - Platforms: **GCP, Azure, CloudRift, Cudo Compute, Verda, Nebius, OCI, etc.**
    - Auth: **None**.
4.  **Level 4: Smart Supplementation**: 
    - TIS automatically "patches" missing metadata (e.g., if a provider API returns price but misses CPU/RAM details) by cross-referencing between layers.
5.  **Level 5: Sample Fallback**: 
    - Used only as a final safety net when all network connections fail.

## Supported Platforms

TIS now covers nearly every major GPU cloud:

| Category | Platforms | Auth |
|----------|-----------|------|
| **Core** | Vast.ai, RunPod, AWS | **Optional** (Rec: Required for precision) |
| **Marketplaces** | TensorDock, Cudo Compute, Verda | **Keyless** |
| **Boutique Clouds** | Lambda Labs, CoreWeave, Paperspace, CloudRift | **Keyless** |
| **Hyperscalers** | GCP, Azure, OCI | **Keyless** |
| **Specialized** | Nebius | **Keyless** |

## Data Transparency

Every recommendation clearly identifies its **Source of Truth** via the `source_detail` tag:
- `live:official`: Direct data from the vendor API.
- `live:gpuhunt`: Real-time data from the high-fidelity aggregator.
- `live:gpufinder`: Universal data from the broad aggregator.
- `live:official+supplemented`: Merged data combining official pricing with aggregator metadata.
- `sample`: Stale data from the local bundle.

## Configuration

API Keys are **optional**. If you want higher precision for specific platforms, set the following environment variables:

```powershell
$env:VAST_API_KEY="your_vast_key"
$env:RUNPOD_API_KEY="your_runpod_key"
```

If not provided, TIS will automatically attempt to find the same offers through the `gpuhunt` or `gpufindr` layers.
