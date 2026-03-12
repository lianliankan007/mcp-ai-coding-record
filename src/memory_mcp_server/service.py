from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from memory_mcp_server.config import Settings
from memory_mcp_server.models import MemoryRecord
from memory_mcp_server.store import MemoryStore


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...


class MemoryService:
    def __init__(self, store: MemoryStore, embedder: Embedder, settings: Settings) -> None:
        self._store = store
        self._embedder = embedder
        self._settings = settings
        self._collection_ready = False

    def ingest(
        self,
        *,
        project: str,
        repo: str,
        task: str,
        summary: str,
        memory_type: str,
        importance: int,
        tags: list[str] | None = None,
        artifacts: list[str] | None = None,
    ) -> dict[str, object]:
        started_at = time.perf_counter()
        cleaned_summary = self._clean_summary(summary)
        vector = self._embed_and_prepare(cleaned_summary)
        dedup_hit = None
        if self._settings.memory_dedup_enabled:
            hits = self._store.search(
                project=project,
                repo=repo,
                query_vector=vector,
                top_k=1,
                tags=None,
                memory_type=memory_type,
            )
            if hits and hits[0].score >= self._settings.memory_dedup_similarity_threshold:
                dedup_hit = hits[0]
        if dedup_hit is not None:
            result = {
                "id": dedup_hit.id,
                "status": "duplicate_skipped",
                "title": dedup_hit.record.title,
            }
            return self._attach_perf(result, started_at=started_at, budget_ms=self._settings.perf_budget_ingest_ms)

        record = MemoryRecord(
            id=str(uuid4()),
            project=project.strip(),
            repo=repo.strip(),
            memory_type=memory_type.strip(),
            title=self._build_title(task=task, summary=cleaned_summary),
            summary=cleaned_summary,
            tags=self._normalize_list(tags),
            importance=max(1, min(5, int(importance))),
            created_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            files=self._normalize_list(artifacts),
            task=task.strip(),
        )
        self._store.upsert(record, vector)
        result = {"id": record.id, "status": "created"}
        return self._attach_perf(result, started_at=started_at, budget_ms=self._settings.perf_budget_ingest_ms)

    def search(
        self,
        *,
        project: str,
        repo: str,
        query: str,
        top_k: int,
        tags: list[str] | None = None,
        memory_type: str | None = None,
    ) -> dict[str, object]:
        started_at = time.perf_counter()
        query_vector = self._embed_and_prepare(self._clean_summary(query))
        hits = self._store.search(
            project=project.strip(),
            repo=repo.strip(),
            query_vector=query_vector,
            top_k=max(1, top_k),
            tags=self._normalize_list(tags),
            memory_type=memory_type.strip() if memory_type else None,
        )
        result = {
            "items": [hit.as_tool_result() for hit in hits],
            "count": len(hits),
        }
        return self._attach_perf(result, started_at=started_at, budget_ms=self._settings.perf_budget_search_ms)

    def recent(self, *, project: str, repo: str, limit: int) -> dict[str, object]:
        started_at = time.perf_counter()
        records = self._store.recent(project=project.strip(), repo=repo.strip(), limit=max(1, limit))
        result = {
            "items": [
                {
                    "id": record.id,
                    "title": record.title,
                    "summary": record.summary,
                    "metadata": {
                        "project": record.project,
                        "repo": record.repo,
                        "memory_type": record.memory_type,
                        "tags": record.tags,
                        "importance": record.importance,
                        "created_at": record.created_at,
                        "files": record.files,
                        "task": record.task,
                    },
                }
                for record in records
            ],
            "count": len(records),
        }
        return self._attach_perf(result, started_at=started_at, budget_ms=self._settings.perf_budget_recent_ms)

    def _embed_and_prepare(self, text: str) -> list[float]:
        vector = self._embedder.embed(text)
        if not self._collection_ready:
            self._store.ensure_collection(len(vector))
            self._collection_ready = True
        return vector

    def _clean_summary(self, summary: str) -> str:
        collapsed = re.sub(r"\s+", " ", summary.replace("\x00", " ")).strip()
        if not collapsed:
            raise ValueError("summary must not be empty")
        return collapsed[: self._settings.memory_summary_max_chars]

    def _attach_perf(
        self,
        result: dict[str, object],
        *,
        started_at: float,
        budget_ms: float,
    ) -> dict[str, object]:
        if not self._settings.perf_metrics_enabled:
            return result
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        enriched = dict(result)
        enriched["perf"] = {
            "duration_ms": duration_ms,
            "budget_ms": budget_ms,
            "within_budget": duration_ms <= budget_ms,
        }
        return enriched

    @staticmethod
    def _build_title(*, task: str, summary: str) -> str:
        candidate = task.strip() or summary.strip()
        if not candidate:
            return "Untitled memory"
        first_sentence = re.split(r"[.!?。！？]\s*", candidate, maxsplit=1)[0].strip()
        return (first_sentence or candidate)[:80]

    @staticmethod
    def _normalize_list(items: list[str] | None) -> list[str]:
        if not items:
            return []
        normalized: list[str] = []
        seen: set[str] = set()
        for item in items:
            cleaned = str(item).strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                normalized.append(cleaned)
        return normalized
