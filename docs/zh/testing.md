# 开发者指南：自动化测试与 VCR

为了在与外部云服务商 API（如 Vast.ai, Runpod 等）交互时确保稳定性，`Train in Silence` 通过 `pytest-recording` 插件使用了 **VCR.py**。这允许测试录制真实的辅助网络交互，并在不需要 API Key 的情况下进行重放。

## 工作原理

1. **重放模式 (默认)**：当您运行 `pytest` 时，系统会在 `tests/cassettes/` 中查找“磁带”（录制文件）。它使用这些保存的响应，而不是发起真实的联网调用。
2. **录制模式**：如果您正在添加新的服务商或更新逻辑，可以通过提供真实的 API Key 并运行 `pytest --record-mode=once` 来录制新的磁带。

## 运行测试

### 标准运行（无需 API Key）
```bash
pytest tests
```

### 录制新磁带（需要 API Key）
```bash
# 设置环境变量
$env:VAST_API_KEY="your_key"
$env:RUNPOD_API_KEY="your_key"

# 对特定测试执行重写录制
pytest tests/test_networking.py --record-mode=rewrite
```

## 安全与隐私 (Masking)

我们在 `tests/conftest.py` 中使用了自定义配置，以确保敏感数据**永远不会**保存到磁带中：
- `Authorization` 请求头会被替换为 `MASKED`。
- `api_key` 查询参数会被替换为 `MASKED`。
- 任何在 `vcr_config` 中注册的其他敏感字段都会被自动脱敏。

> [!IMPORTANT]
> 在提交代码前，请务必检查 `tests/cassettes/` 中生成的 `.yaml` 文件，确保没有私密信息泄露。

## 最佳实践

- **原子化磁带**：理想情况下，每个测试应拥有自己的磁带，以保持文件易于管理。
- **CI/CD 集成**：我们的 CI 流水线以重放模式运行测试，确保在不依赖外部服务在线的情况下实现 100% 通过率。
- **缓存重定向**：产生本地文件缓存的测试应使用临时的 `tests/.cache/` 目录，该目录已被 Git 忽略。
