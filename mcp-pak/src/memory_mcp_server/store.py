from __future__ import annotations

from typing import Protocol

from qdrant_client import QdrantClient
from qdrant_client.http import models

from memory_mcp_server.models import MemoryRecord, SearchHit


class MemoryStore(Protocol):
    def ensure_collection(self, vector_size: int) -> None: ...

    def upsert(self, record: MemoryRecord, vector: list[float]) -> None: ...

    def search(
        self,
        *,
        project: str,
        repo: str,
        query_vector: list[float],
        top_k: int,
        tags: list[str] | None = None,
        memory_type: str | None = None,
    ) -> list[SearchHit]: ...

    def recent(self, *, project: str, repo: str, limit: int) -> list[MemoryRecord]: ...


class QdrantMemoryStore:
    def __init__(self, url: str, collection_name: str, api_key: str | None = None) -> None:
        self._collection_name = collection_name
        self._client = QdrantClient(url=url, api_key=api_key)

    def ensure_collection(self, vector_size: int) -> None:
        if not self._client.collection_exists(self._collection_name):
            self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
                on_disk_payload=True,
            )
        self._ensure_payload_indexes()

    def upsert(self, record: MemoryRecord, vector: list[float]) -> None:
        point = models.PointStruct(id=record.id, vector=vector, payload=record.to_payload())
        self._client.upsert(collection_name=self._collection_name, points=[point], wait=True)

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
        query_filter = self._build_filter(project=project, repo=repo, tags=tags, memory_type=memory_type)
        response = self._client.query_points(
            collection_name=self._collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
        return [
            SearchHit(
                id=str(point.id),
                score=float(point.score),
                record=MemoryRecord.from_payload(str(point.id), point.payload or {}),
            )
            for point in response.points
        ]

    def recent(self, *, project: str, repo: str, limit: int) -> list[MemoryRecord]:
        query_filter = self._build_filter(project=project, repo=repo, tags=None, memory_type=None)
        records, _ = self._client.scroll(
            collection_name=self._collection_name,
            scroll_filter=query_filter,
            limit=limit,
            order_by=models.OrderBy(key="created_at", direction=models.Direction.DESC),
            with_payload=True,
            with_vectors=False,
        )
        return [MemoryRecord.from_payload(str(record.id), record.payload or {}) for record in records]

    def _ensure_payload_indexes(self) -> None:
        index_fields: list[tuple[str, models.PayloadSchemaType]] = [
            ("project", models.PayloadSchemaType.KEYWORD),
            ("repo", models.PayloadSchemaType.KEYWORD),
            ("memory_type", models.PayloadSchemaType.KEYWORD),
            ("tags", models.PayloadSchemaType.KEYWORD),
            ("created_at", models.PayloadSchemaType.DATETIME),
        ]
        for field_name, field_type in index_fields:
            self._client.create_payload_index(
                collection_name=self._collection_name,
                field_name=field_name,
                field_schema=field_type,
                wait=True,
            )

    @staticmethod
    def _build_filter(
        *,
        project: str,
        repo: str,
        tags: list[str] | None,
        memory_type: str | None,
    ) -> models.Filter:
        conditions: list[models.Condition] = [
            models.FieldCondition(key="project", match=models.MatchValue(value=project)),
            models.FieldCondition(key="repo", match=models.MatchValue(value=repo)),
        ]
        if memory_type:
            conditions.append(models.FieldCondition(key="memory_type", match=models.MatchValue(value=memory_type)))
        if tags:
            conditions.append(models.FieldCondition(key="tags", match=models.MatchAny(any=tags)))
        return models.Filter(must=conditions)
