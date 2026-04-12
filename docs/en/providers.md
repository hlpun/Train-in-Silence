# Market Providers

`Train in Silence` is dedicated to providing trustworthy market data. Data acquisition methods and accuracy vary by platform, which we address through "Data Transparency" flags in the system design.

## Supported Platforms

### 1. Vast.ai
- **Data Source**: Real-time API.
- **Parsing**: Each result represents a specific machine instance.
- **Certainty**: High. Inventory data is real-time.

### 2. RunPod
- **Data Source**: Real-time GraphQL.
- **Parsing**: Aggregated based on total available GPUs (maxUnreservedGpuCount) and node configurations.
- **Certainty**: Medium-High. Region data is often inferred based on stock status (stockStatus), flagged as `is_region_estimated=true`.

- **Certainty**: Medium. Current availability for AWS is catalog-based (optimistic default score), while regions and pricing are accurate from the public API. Flagged as `is_availability_estimated=true`.
- **Note**: You can use shorthand region aliases such as `us` (expands to us-east-1, us-west-2), `eu` (eu-west-1, eu-central-1), or `ap` (ap-northeast-1, ap-southeast-1) in your request configuration.

### 4. Sample (Built-in)
- **Data Source**: Local `tis/data/gpu_offers.json`.
- **Note**: Currently, `tis` aggregates both On-Demand and Spot/Community prices where available. While the `spot` flag is preserved in the data, there is no constraint to filter strictly for one or the other in the current MVP.
- **Parsing**: Enabled only when `TIS_ALLOW_SAMPLE_FALLBACK=true` and online markets are unreachable.

## Data Transparency

In recommendation responses, you may see a `notes` field. This ensures you understand the nature of the data sources:

- **Availability is estimated...**: Indicates the platform doesn't support real-time inventory queries. We provide an optimistic default score based on historical instance attributes.
- **Region is inferred...**: Indicates the platform didn't specify a clear physical location. We inferred the likely region based on stock status.

## How to Configure API Keys

Set the following environment variables before running. Unconfigured providers will be marked `ok=False` and skipped:

```powershell
$env:VAST_API_KEY="your_vast_key"
$env:RUNPOD_API_KEY="your_runpod_key"
```
