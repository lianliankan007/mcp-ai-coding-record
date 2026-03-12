from __future__ import annotations

from typing import Any

import httpx


class OllamaEmbedder:
    def __init__(self, base_url: str, model: str, timeout_seconds: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._client = httpx.Client(timeout=timeout_seconds)

    @property
    def model(self) -> str:
        return self._model

    def embed(self, text: str) -> list[float]:
        payload = {"model": self._model, "input": text}
        for endpoint in ("/api/embed", "/api/embeddings"):
            response = self._client.post(f"{self._base_url}{endpoint}", json=payload)
            if response.status_code == 404:
                continue
            response.raise_for_status()
            body: dict[str, Any] = response.json()
            if "embeddings" in body and body["embeddings"]:
                return [float(value) for value in body["embeddings"][0]]
            if "embedding" in body:
                return [float(value) for value in body["embedding"]]
            raise ValueError(f"Ollama response missing embedding field: {body}")
        raise ValueError("Ollama embed endpoint not found at /api/embed or /api/embeddings")

    def close(self) -> None:
        self._client.close()
