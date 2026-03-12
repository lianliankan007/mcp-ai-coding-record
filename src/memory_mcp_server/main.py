from __future__ import annotations

import uvicorn

from memory_mcp_server.config import Settings


def main() -> None:
    settings = Settings()
    uvicorn.run(
        "memory_mcp_server.server:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
