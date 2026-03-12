from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from memory_mcp_server.clients.ollama import OllamaEmbedder
from memory_mcp_server.config import Settings
from memory_mcp_server.service import MemoryService
from memory_mcp_server.store import QdrantMemoryStore


def build_service(settings: Settings | None = None) -> MemoryService:
    app_settings = settings or Settings()
    store = QdrantMemoryStore(
        url=app_settings.qdrant_url,
        api_key=app_settings.qdrant_api_key,
        collection_name=app_settings.qdrant_collection,
    )
    embedder = OllamaEmbedder(
        base_url=app_settings.ollama_url,
        model=app_settings.ollama_embedding_model,
        timeout_seconds=app_settings.ollama_timeout_seconds,
    )
    return MemoryService(store=store, embedder=embedder, settings=app_settings)


def build_mcp(service: MemoryService, settings: Settings | None = None) -> FastMCP:
    app_settings = settings or Settings()
    mcp = FastMCP(
        app_settings.app_name,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=app_settings.mcp_dns_rebinding_protection,
            allowed_hosts=app_settings.mcp_allowed_hosts,
            allowed_origins=app_settings.mcp_allowed_origins,
        ),
    )

    @mcp.tool(
        name="memory_search",
        description="Search relevant coding memories by semantic similarity with project and repo filtering.",
    )
    def memory_search(
        project: str,
        repo: str,
        query: str,
        top_k: int = 5,
        tags: list[str] | None = None,
        memory_type: str | None = None,
    ) -> dict[str, object]:
        return service.search(
            project=project,
            repo=repo,
            query=query,
            top_k=top_k,
            tags=tags,
            memory_type=memory_type,
        )

    @mcp.tool(
        name="memory_ingest",
        description="Store a high-value coding memory summary into Qdrant.",
    )
    def memory_ingest(
        project: str,
        repo: str,
        task: str,
        summary: str,
        memory_type: str,
        importance: int,
        tags: list[str] | None = None,
        artifacts: list[str] | None = None,
    ) -> dict[str, object]:
        return service.ingest(
            project=project,
            repo=repo,
            task=task,
            summary=summary,
            memory_type=memory_type,
            importance=importance,
            tags=tags,
            artifacts=artifacts,
        )

    @mcp.tool(
        name="memory_recent",
        description="Return the most recently written coding memories for a project and repo.",
    )
    def memory_recent(project: str, repo: str, limit: int = 10) -> dict[str, object]:
        return service.recent(project=project, repo=repo, limit=limit)

    return mcp


def create_app():
    settings = Settings()
    service = build_service(settings)
    mcp = build_mcp(service, settings)
    return mcp.streamable_http_app()
