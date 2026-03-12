from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="memory-mcp-server", alias="APP_NAME")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8080, alias="PORT")

    qdrant_url: str = Field(alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")
    qdrant_collection: str = Field(default="coding_memory", alias="QDRANT_COLLECTION")

    ollama_url: str = Field(alias="OLLAMA_URL")
    ollama_embedding_model: str = Field(default="nomic-embed-text", alias="OLLAMA_EMBEDDING_MODEL")
    ollama_timeout_seconds: float = Field(default=30.0, alias="OLLAMA_TIMEOUT_SECONDS")

    memory_dedup_enabled: bool = Field(default=True, alias="MEMORY_DEDUP_ENABLED")
    memory_dedup_similarity_threshold: float = Field(
        default=0.985,
        alias="MEMORY_DEDUP_SIMILARITY_THRESHOLD",
    )
    memory_summary_max_chars: int = Field(default=2000, alias="MEMORY_SUMMARY_MAX_CHARS")
    default_top_k: int = Field(default=5, alias="DEFAULT_TOP_K")

    mcp_dns_rebinding_protection: bool = Field(
        default=False,
        alias="MCP_DNS_REBINDING_PROTECTION",
    )
    mcp_allowed_hosts: list[str] = Field(
        default_factory=lambda: ["127.0.0.1:*", "localhost:*", "[::1]:*"],
        alias="MCP_ALLOWED_HOSTS",
    )
    mcp_allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"],
        alias="MCP_ALLOWED_ORIGINS",
    )

    @field_validator("mcp_allowed_hosts", "mcp_allowed_origins", mode="before")
    @classmethod
    def _split_csv_values(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    perf_metrics_enabled: bool = Field(default=False, alias="PERF_METRICS_ENABLED")
    perf_budget_search_ms: float = Field(default=800.0, alias="PERF_BUDGET_SEARCH_MS")
    perf_budget_ingest_ms: float = Field(default=1200.0, alias="PERF_BUDGET_INGEST_MS")
    perf_budget_recent_ms: float = Field(default=200.0, alias="PERF_BUDGET_RECENT_MS")
