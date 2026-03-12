# Contributing

感谢你为 Memory MCP Server 做贡献。

## 开始之前

提交 issue 或 pull request 前，请先确认：

1. 你的改动与项目目标一致：为 AI coding 提供轻量、可回捞、低干扰的编码记忆能力。
2. 新增行为不会默认增加额外网络链路、明显放大延迟，或改变已有 tool 的最小输入契约。
3. 配置、README、`.env.example`、测试用例会一起更新，避免文档和实现脱节。

## 本地开发

```powershell
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
.venv\Scripts\python -m pytest -q
```

开发模式启动：

```powershell
.venv\Scripts\python -m uvicorn memory_mcp_server.server:create_app --factory --reload --host 0.0.0.0 --port 8080
```

## 提交规范

- 保持改动聚焦，一个 pull request 只解决一类问题。
- 对外行为变更请在 README 中补充说明。
- 修改配置项时，同时更新 `.env.example`。
- 新增逻辑应尽量补测试，至少覆盖成功路径和关键失败路径。
- 不要提交真实密钥、局域网内网地址或生产数据。

## Pull Request 检查项

- 测试通过：`pytest -q`
- 文档已更新
- 无无关格式化噪音
- 如涉及兼容性或性能取舍，PR 描述中已说明原因

## Issue 反馈

Bug 请尽量附上：

- 复现步骤
- 实际结果与期望结果
- 使用的 Python 版本
- 与 Qdrant / Ollama 相关的关键配置

安全问题请不要通过公开 issue 提交，参见 [SECURITY.md](SECURITY.md)。
