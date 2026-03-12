from __future__ import annotations

from dataclasses import dataclass

from memory_mcp_server.config import Settings
from memory_mcp_server.models import MemoryRecord, SearchHit
from memory_mcp_server.service import MemoryService


class FakeEmbedder:
    def embed(self, text: str) -> list[float]:
        lowered = text.lower()
        return [
            1.0 if "qdrant" in lowered else 0.0,
            1.0 if "timeout" in lowered else 0.0,
            float(len(lowered.split())),
        ]


@dataclass
class FakeStore:
    records: list[tuple[MemoryRecord, list[float]]]
    ensured_size: int | None = None

    def ensure_collection(self, vector_size: int) -> None:
        self.ensured_size = vector_size

    def upsert(self, record: MemoryRecord, vector: list[float]) -> None:
        self.records.append((record, vector))

    def search(
        self,
        *,
        project: str,
        repo: str,
        query_vector: list[float],
        top_k: int,
        tags: list[str] | None = None,
        memory_type: str | None = None,
    ) -> list[SearchHit]:
        hits: list[SearchHit] = []
        for record, vector in self.records:
            if record.project != project or record.repo != repo:
                continue
            if memory_type and record.memory_type != memory_type:
                continue
            if tags and not any(tag in record.tags for tag in tags):
                continue
            score = sum(left * right for left, right in zip(query_vector, vector))
            hits.append(SearchHit(id=record.id, score=score, record=record))
        hits.sort(key=lambda item: item.score, reverse=True)
        return hits[:top_k]

    def recent(self, *, project: str, repo: str, limit: int) -> list[MemoryRecord]:
        items = [record for record, _ in self.records if record.project == project and record.repo == repo]
        return list(reversed(items))[:limit]


def build_service() -> tuple[MemoryService, FakeStore]:
    settings = Settings.model_validate(
        {
            "QDRANT_URL": "http://unused:6333",
            "OLLAMA_URL": "http://unused:11434",
            "MEMORY_DEDUP_ENABLED": False,
        }
    )
    store = FakeStore(records=[])
    return MemoryService(store=store, embedder=FakeEmbedder(), settings=settings), store


def test_ingest_success_writes_record() -> None:
    service, store = build_service()

    result = service.ingest(
        project="demo",
        repo="memory-mcp",
        task="Persist Qdrant timeout fix",
        summary="Qdrant timeout was fixed by extending the client timeout and retrying the request.",
        memory_type="error_fix",
        importance=4,
        tags=["qdrant", "timeout"],
        artifacts=["src/store.py"],
    )

    assert result["status"] == "created"
    assert len(store.records) == 1
    record, vector = store.records[0]
    assert record.memory_type == "error_fix"
    assert record.files == ["src/store.py"]
    assert store.ensured_size == len(vector)


def test_search_returns_relevant_memory() -> None:
    service, _ = build_service()
    service.ingest(
        project="demo",
        repo="memory-mcp",
        task="Persist Qdrant timeout fix",
        summary="Qdrant timeout was fixed by extending the client timeout and retrying the request.",
        memory_type="error_fix",
        importance=4,
        tags=["qdrant", "timeout"],
        artifacts=["src/store.py"],
    )
    service.ingest(
        project="demo",
        repo="memory-mcp",
        task="Document coding constraint",
        summary="Do not store raw conversation logs in the memory database.",
        memory_type="constraint",
        importance=5,
        tags=["privacy"],
        artifacts=[],
    )

    result = service.search(
        project="demo",
        repo="memory-mcp",
        query="How did we fix the Qdrant timeout issue?",
        top_k=2,
        tags=["qdrant"],
        memory_type="error_fix",
    )

    assert result["count"] == 1
    first = result["items"][0]
    assert first["title"] == "Persist Qdrant timeout fix"
    assert first["metadata"]["memory_type"] == "error_fix"


def test_recent_returns_latest_records() -> None:
    service, _ = build_service()
    first = service.ingest(
        project="demo",
        repo="memory-mcp",
        task="Initial constraint",
        summary="Keep the service LAN-only for the MVP.",
        memory_type="constraint",
        importance=3,
        tags=["mvp"],
        artifacts=[],
    )
    second = service.ingest(
        project="demo",
        repo="memory-mcp",
        task="Decision on transport",
        summary="Use HTTP MCP so multiple Codex clients can connect over the LAN.",
        memory_type="decision",
        importance=5,
        tags=["mcp", "http"],
        artifacts=["README.md"],
    )

    result = service.recent(project="demo", repo="memory-mcp", limit=2)

    assert result["count"] == 2
    assert result["items"][0]["id"] == second["id"]
    assert result["items"][1]["id"] == first["id"]


def test_perf_metrics_are_opt_in() -> None:
    settings = Settings.model_validate(
        {
            "QDRANT_URL": "http://unused:6333",
            "OLLAMA_URL": "http://unused:11434",
            "MEMORY_DEDUP_ENABLED": False,
            "PERF_METRICS_ENABLED": True,
            "PERF_BUDGET_SEARCH_MS": 500,
        }
    )
    store = FakeStore(records=[])
    service = MemoryService(store=store, embedder=FakeEmbedder(), settings=settings)
    service.ingest(
        project="demo",
        repo="memory-mcp",
        task="Seed memory",
        summary="Qdrant timeout fix summary.",
        memory_type="error_fix",
        importance=4,
        tags=["qdrant"],
        artifacts=[],
    )

    result = service.search(
        project="demo",
        repo="memory-mcp",
        query="Find the Qdrant timeout fix.",
        top_k=1,
    )

    assert "perf" in result
    assert result["perf"]["budget_ms"] == 500
    assert isinstance(result["perf"]["within_budget"], bool)
