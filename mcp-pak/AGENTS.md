# Memory MCP Server Agent Guide

## Memory Usage Rules
- Before starting a new coding task, call `memory_search` first with the current `project`, `repo`, and task-oriented query.
- After finishing a task, call `memory_ingest` to store a high-value summary.
- Do not store full raw conversations, full prompts, or complete original context directly in memory.
- Only ingest high-value summaries in these categories: `task_summary`, `decision`, `error_fix`, `constraint`.

## Recommended Inputs
- Keep `summary` concise, factual, and reusable.
- Put file paths or artifact names in `artifacts`.
- Use stable `project` and `repo` names so retrieval stays accurate.
