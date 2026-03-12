---
name: memory-mcp-workflow
description: Use this skill when working in repositories where the Memory MCP server is configured and you want Codex to reuse prior coding decisions, fixes, and constraints without storing raw conversation logs. Trigger it at the start of a new coding task to search relevant memory with `memory_search`, and at the end of a task to persist a high-value summary with `memory_ingest`.
---

# Memory MCP Workflow

## Overview

Use the `memory` MCP server as a lightweight task memory loop. Search before coding to recover reusable context, and ingest after coding to preserve only high-value structured summaries.

The MCP service URL for this workflow is `http://localhost:8080/mcp`.

## Workflow

1. Before starting implementation, call `memory_search`.
2. During the task, use retrieved memory as supporting context, not as unquestioned truth.
3. After completing the task, call `memory_ingest` with a concise reusable summary.
4. If the MCP server is unavailable or returns no useful results, continue the task normally.

## Before Coding

Call `memory_search` once near the beginning of a task when any of these are true:

- The task continues prior work in the same project or repo.
- The task asks about earlier design decisions, bug fixes, or constraints.
- The task touches infrastructure already debugged before.
- The task is likely to benefit from known implementation patterns.

Use stable `project` and `repo` values. Keep the query task-oriented, for example:

- "What did we decide earlier about graceful shutdown in this repo?"
- "Have we already fixed a similar Qdrant timeout problem?"
- "What constraints should I keep when editing this service?"

Prefer `top_k` in the `3` to `5` range unless the task explicitly needs a wider scan.

## After Coding

Call `memory_ingest` once after finishing a task when the result contains reusable value. Only ingest high-value summaries in these categories:

- `task_summary`
- `decision`
- `error_fix`
- `constraint`

Keep `summary` short, factual, and reusable across future tasks. Put file paths or outputs in `artifacts`.

## What Not To Store

Do not store:

- Full raw conversation logs
- Full prompts or chain-of-thought
- Large copied code blocks
- Low-signal status chatter
- Secrets, tokens, or credentials

## Ingest Heuristics

Good memories usually capture one of these:

- A decision and why it was chosen
- A concrete bug and its fix
- A project constraint that will matter again
- A task summary that future work can build on

Bad memories are vague, redundant, or too detailed to retrieve cleanly later.

## Minimal Examples

Search example:

```json
{
  "project": "ai-coding",
  "repo": "mcp-ai-coding-record",
  "query": "How was Memory MCP deployed and connected to Codex?",
  "top_k": 3
}
```

Ingest example:

```json
{
  "project": "ai-coding",
  "repo": "mcp-ai-coding-record",
  "task": "Deploy Memory MCP on LAN host",
  "summary": "Memory MCP server was deployed on a LAN Linux host and connected to Codex over HTTP MCP.",
  "memory_type": "task_summary",
  "importance": 3,
  "tags": ["deploy", "mcp"],
  "artifacts": ["README.md"]
}
```

## Agent Setup Prompts

Use these prompts when you want an AI coding agent to configure or use the Memory MCP service.

Expected server name:

```text
memory
```

Expected tools:

- `memory_search`
- `memory_ingest`
- `memory_recent`

### Codex

Direct config snippet:

```toml
[mcp_servers.memory]
enabled = true
url = "http://localhost:8080/mcp"
startup_timeout_sec = 10.0
tool_timeout_sec = 60.0
```

Prompt to paste into Codex:

```text
Please configure an MCP server named memory using this streamable HTTP URL: http://localhost:8080/mcp

If memory is already configured, verify it is enabled and reachable.
After configuration, confirm that these tools are available:
- memory_search
- memory_ingest
- memory_recent

If configuration cannot be applied automatically, show me the exact config snippet or command I should run.
```

### Claude Code

Prompt to paste into Claude Code:

```text
Please help me configure an MCP server named memory for this coding environment.

Target MCP server:
- name: memory
- transport: streamable HTTP
- url: http://localhost:8080/mcp

After configuring it, verify that these tools are available:
- memory_search
- memory_ingest
- memory_recent

If your current version uses a config file or CLI command for MCP setup, give me the exact command or config block for this environment.
```

### OpenCode

Prompt to paste into OpenCode:

```text
Configure a streamable HTTP MCP server named memory with this URL:
http://localhost:8080/mcp

Then verify that the following tools are exposed:
- memory_search
- memory_ingest
- memory_recent

If automatic setup is not supported in this environment, tell me the exact config file location and the exact config content or command I need.
```

### Generic Prompt

Use this when the agent supports MCP but you do not know its exact config mechanism.

```text
Help me configure an MCP server for my AI coding environment.

Server details:
- name: memory
- transport: streamable HTTP
- url: http://localhost:8080/mcp

Please do one of these:
1. Apply the configuration automatically if your environment supports it.
2. Otherwise, give me the exact command or config snippet I should use.

After setup, verify that these tools are available:
- memory_search
- memory_ingest
- memory_recent
```
