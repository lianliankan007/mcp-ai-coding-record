# Memory MCP Server

一个最小可运行的 HTTP MCP server，用来把高价值编码记忆沉淀到 Qdrant，并在新任务开始前通过语义检索回捞相关上下文。MVP 只实现 3 个 MCP tools：

- GitHub: https://github.com/lianliankan007/mcp-ai-coding-record
- Issues: https://github.com/lianliankan007/mcp-ai-coding-record/issues

- `memory_search`
- `memory_ingest`
- `memory_recent`

## 项目用途

目标是给 Codex 提供一个局域网可直连的记忆服务：

1. 开始编码前，先按 `project` / `repo` 搜索相关历史经验。
2. 结束任务后，把高价值摘要写入 Qdrant。
3. 不保存完整原始对话，只保存结构化摘要记忆。

## 架构图

文字版架构如下：

1. Codex 通过 HTTP 访问 `http://LAN_HOST:PORT/mcp`
2. HTTP MCP Server 暴露 `memory_search`、`memory_ingest`、`memory_recent`
3. `memory_ingest` / `memory_search` 调用 Ollama 的 `nomic-embed-text` 生成向量
4. 向量和结构化 payload 写入 / 检索自 Qdrant
5. `memory_recent` 直接按 `created_at` 返回最近写入记录

数据流：

- Search: Codex -> MCP -> Ollama embedding -> Qdrant vector search -> Codex
- Ingest: Codex -> MCP -> summary 清洗 -> 可选轻量去重 -> Ollama embedding -> Qdrant upsert
- Recent: Codex -> MCP -> Qdrant order by `created_at` desc -> Codex

## Qdrant Collection 设计

MVP 使用单个 collection，默认名为 `coding_memory`。

- Vector: `summary` 的 embedding，距离度量使用 `Cosine`
- Payload 字段：
  - `project`
  - `repo`
  - `memory_type`
  - `title`
  - `summary`
  - `tags`
  - `importance`
  - `created_at`
  - `files`
  - `task`

建议建立 payload index 的字段：

- `project`
- `repo`
- `memory_type`
- `tags`
- `created_at`

服务启动后会自动确保这些 payload index 存在。

## 目录结构

```text
.
|-- .env.example
|-- AGENTS.md
|-- README.md
|-- pyproject.toml
|-- scripts
|   |-- start.ps1
|   `-- start.sh
|-- src
|   `-- memory_mcp_server
|       |-- __init__.py
|       |-- config.py
|       |-- main.py
|       |-- models.py
|       |-- server.py
|       |-- service.py
|       |-- store.py
|       `-- clients
|           |-- __init__.py
|           `-- ollama.py
`-- tests
    `-- test_service.py
```

## 环境变量说明

统一通过 `.env` 配置，先复制 `.env.example`：

```bash
cp .env.example .env
```

关键变量：

- `HOST`: 服务监听地址，默认 `0.0.0.0`
- `PORT`: 服务端口，默认 `8080`
- `QDRANT_URL`: Qdrant HTTP 地址，例如 `http://192.168.1.10:6333`
- `QDRANT_API_KEY`: 当前 MVP 默认可留空
- `QDRANT_COLLECTION`: collection 名称，默认 `coding_memory`
- `OLLAMA_URL`: Ollama 地址，例如 `http://192.168.1.20:11434`
- `OLLAMA_EMBEDDING_MODEL`: 默认 `nomic-embed-text`
- `OLLAMA_TIMEOUT_SECONDS`: Ollama 请求超时
- `MEMORY_DEDUP_ENABLED`: 是否启用轻量去重
- `MEMORY_DEDUP_SIMILARITY_THRESHOLD`: 去重相似度阈值
- `MEMORY_SUMMARY_MAX_CHARS`: summary 清洗后的最大长度
- `DEFAULT_TOP_K`: 默认检索条数
- `MCP_DNS_REBINDING_PROTECTION`: 是否开启 Host/Origin 校验，局域网直连 MVP 默认 `false`
- `MCP_ALLOWED_HOSTS`: 开启校验时允许的 Host 列表，逗号分隔
- `MCP_ALLOWED_ORIGINS`: 开启校验时允许的 Origin 列表，逗号分隔
- `PERF_METRICS_ENABLED`: 是否在 tool 返回中附带性能数据，默认 `false`
- `PERF_BUDGET_SEARCH_MS`: `memory_search` 延迟预算
- `PERF_BUDGET_INGEST_MS`: `memory_ingest` 延迟预算
- `PERF_BUDGET_RECENT_MS`: `memory_recent` 延迟预算

## 本地启动方法

### 1. 安装依赖

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
```

### 2. 配置环境变量

```bash
copy .env.example .env
```

把 `.env` 里的 `QDRANT_URL` 和 `OLLAMA_URL` 改成你的局域网服务地址。

### 3. 一键启动

Windows PowerShell:

```powershell
.\scripts\start.ps1
```

POSIX shell:

```bash
./scripts/start.sh
```

默认会启动一个 HTTP MCP server，并暴露：

- MCP endpoint: `http://127.0.0.1:8080/mcp`

如果你用局域网 IP 访问 Codex，MVP 默认关闭 DNS rebinding 校验，避免出现 `Invalid Host header` 和 `421 Misdirected Request`。如果后续要收紧，可把 `MCP_DNS_REBINDING_PROTECTION=true`，再显式配置 `MCP_ALLOWED_HOSTS` / `MCP_ALLOWED_ORIGINS`。

## 本地开发模式

开发模式建议直接用热重载：

```bash
.venv/Scripts/python -m uvicorn memory_mcp_server.server:create_app --factory --reload --host 0.0.0.0 --port 8080
```

如果 Qdrant / Ollama 不在本机，只需要把 `.env` 里的地址指向局域网服务即可。

## 效率检测

为了不影响 AI coding 默认效率，效率检测分成两种模式：

1. 默认模式：`PERF_METRICS_ENABLED=false`
2. 检测模式：手动开启返回埋点，或手动运行基准脚本

默认模式下不会额外发检测请求，也不会改变你的正常使用方式。

### 轻量埋点模式

把 `.env` 里的下面开关改成 `true`：

```env
PERF_METRICS_ENABLED=true
```

开启后，3 个 tools 的返回里会额外带一个 `perf` 字段：

```json
{
  "perf": {
    "duration_ms": 132.4,
    "budget_ms": 800.0,
    "within_budget": true
  }
}
```

这个模式只做本次调用的本地计时，不增加额外网络链路，默认关闭。

### 手动基准模式

需要验证“记忆功能是否拖慢 AI coding”时，再手动运行：

```powershell
.venv\Scripts\python.exe scripts\benchmark_service.py --project ai-coding --repo memory-mcp-server --iterations 5
```

脚本会输出 `memory_search`、`memory_ingest`、`memory_recent` 的 `avg / p50 / p95`，并按预算给出 `PASS / FAIL`。这是离线手动检测，不会插入到 Codex 的日常调用流程里。

## Codex MCP 配置方法

把服务跑起来后，执行：

```bash
codex mcp add memory --url http://LAN_HOST:PORT/mcp
```

例如：

```bash
codex mcp add memory --url http://192.168.1.50:8080/mcp
```

## 示例调用

下面是三个工具的典型输入。

### `memory_search`

```json
{
  "project": "ai-coding",
  "repo": "memory-mcp-server",
  "query": "之前是怎么处理 Qdrant 超时和重试的？",
  "top_k": 5,
  "tags": ["qdrant"],
  "memory_type": "error_fix"
}
```

返回字段包含：

- `title`
- `summary`
- `score`
- `metadata`

### `memory_ingest`

```json
{
  "project": "ai-coding",
  "repo": "memory-mcp-server",
  "task": "修复 Qdrant 超时问题",
  "summary": "将 Qdrant 客户端超时调高，并在查询入口增加有限重试，避免局域网偶发抖动导致检索失败。",
  "memory_type": "error_fix",
  "importance": 4,
  "tags": ["qdrant", "timeout"],
  "artifacts": ["src/memory_mcp_server/store.py"]
}
```

返回字段包含：

- `id`
- `status`

### `memory_recent`

```json
{
  "project": "ai-coding",
  "repo": "memory-mcp-server",
  "limit": 10
}
```

## 测试

运行最小测试：

```bash
.venv/Scripts/python -m pytest -q
```

当前包含 3 个测试：

1. ingest 成功写入
2. search 能检索到相关数据
3. recent 能返回最近记录

## 关键文件说明

- `src/memory_mcp_server/server.py`: MCP tool 注册和 HTTP app 工厂
- `src/memory_mcp_server/service.py`: 核心业务逻辑，负责清洗、去重、检索、入库
- `src/memory_mcp_server/store.py`: Qdrant 存储实现和 payload filter / index 创建
- `src/memory_mcp_server/clients/ollama.py`: Ollama embedding 客户端
- `AGENTS.md`: Codex 使用记忆工具的最小约束

## 启动命令

```powershell
.\scripts\start.ps1
```

或：

```bash
.venv/Scripts/python -m memory_mcp_server.main
```

## Codex 接入命令

```bash
codex mcp add memory --url http://LAN_HOST:PORT/mcp
```

## Phase 2 扩展建议

- 增加基于内容哈希和相似度的双重去重策略
- 增加 `memory_type` 白名单和更严格的输入校验
- 增加可观测性，如结构化日志和基础健康检查
- 增加可选 rerank，但保持默认链路不变
- 增加按项目导出 / 备份记忆的运维脚本

## 开源协作

仓库已经补齐最小开源协作文件，首次对外发布时建议至少同步以下内容：

- [LICENSE](LICENSE)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [SECURITY.md](SECURITY.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- [`.github/ISSUE_TEMPLATE`](.github/ISSUE_TEMPLATE)
- [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md)
- [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

建议发布前再确认两项：

1. 确认安全联系方式，避免漏洞报告只能走公开 issue。
2. 首次推送前检查默认分支名和 CI 触发分支是否一致。

## 贡献方式

欢迎提交 issue 和 pull request。提交前请先：

1. 阅读 [CONTRIBUTING.md](CONTRIBUTING.md)
2. 本地运行 `pytest -q`
3. 确认 `.env.example` 与 README 中的配置说明保持一致

## 安全报告

如果你发现安全问题，请不要直接公开披露。请优先参考 [SECURITY.md](SECURITY.md) 中的流程，通过私有渠道联系维护者。

## 许可证

本项目采用 [MIT License](LICENSE)。
