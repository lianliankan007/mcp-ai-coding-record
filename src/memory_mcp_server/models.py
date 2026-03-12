from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MemoryRecord:
    id: str
    project: str
    repo: str
    memory_type: str
    title: str
    summary: str
    tags: list[str] = field(default_factory=list)
    importance: int = 3
    created_at: str = ""
    files: list[str] = field(default_factory=list)
    task: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "repo": self.repo,
            "memory_type": self.memory_type,
            "title": self.title,
            "summary": self.summary,
            "tags": self.tags,
            "importance": self.importance,
            "created_at": self.created_at,
            "files": self.files,
            "task": self.task,
        }

    @classmethod
    def from_payload(cls, record_id: str, payload: dict[str, Any]) -> "MemoryRecord":
        return cls(
            id=str(record_id),
            project=str(payload.get("project", "")),
            repo=str(payload.get("repo", "")),
            memory_type=str(payload.get("memory_type", "")),
            title=str(payload.get("title", "")),
            summary=str(payload.get("summary", "")),
            tags=[str(tag) for tag in payload.get("tags", []) or []],
            importance=int(payload.get("importance", 0) or 0),
            created_at=str(payload.get("created_at", "")),
            files=[str(item) for item in payload.get("files", []) or []],
            task=str(payload.get("task", "")),
        )


@dataclass(slots=True)
class SearchHit:
    id: str
    score: float
    record: MemoryRecord

    def as_tool_result(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.record.title,
            "summary": self.record.summary,
            "score": self.score,
            "metadata": {
                "project": self.record.project,
                "repo": self.record.repo,
                "memory_type": self.record.memory_type,
                "tags": self.record.tags,
                "importance": self.record.importance,
                "created_at": self.record.created_at,
                "files": self.record.files,
                "task": self.record.task,
            },
        }
