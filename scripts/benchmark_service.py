from __future__ import annotations

import argparse
import statistics
import sys
import time
from typing import Callable

from memory_mcp_server.config import Settings
from memory_mcp_server.server import build_service


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * ratio))))
    return ordered[index]


def run_case(name: str, iterations: int, budget_ms: float, fn: Callable[[], None]) -> tuple[str, list[float], float]:
    samples: list[float] = []
    for _ in range(iterations):
        started_at = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - started_at) * 1000)
    return name, samples, budget_ms


def print_case(name: str, samples: list[float], budget_ms: float) -> bool:
    avg_ms = statistics.fmean(samples)
    p50_ms = percentile(samples, 0.50)
    p95_ms = percentile(samples, 0.95)
    ok = p95_ms <= budget_ms
    status = "PASS" if ok else "FAIL"
    print(
        f"{name:14} {status}  avg={avg_ms:.2f}ms  p50={p50_ms:.2f}ms  p95={p95_ms:.2f}ms  budget={budget_ms:.2f}ms"
    )
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run lightweight latency benchmarks for Memory MCP service without changing the normal MCP flow."
    )
    parser.add_argument("--project", default="benchmark-project")
    parser.add_argument("--repo", default="benchmark-repo")
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--search-budget-ms", type=float, default=None)
    parser.add_argument("--ingest-budget-ms", type=float, default=None)
    parser.add_argument("--recent-budget-ms", type=float, default=None)
    args = parser.parse_args()

    settings = Settings()
    service = build_service(settings)
    seed_task = "benchmark seed memory"
    seed_summary = "Memory MCP benchmark seed entry for latency testing and retrieval validation."
    seed_tags = ["benchmark", "latency"]

    seed_result = service.ingest(
        project=args.project,
        repo=args.repo,
        task=seed_task,
        summary=seed_summary,
        memory_type="task_summary",
        importance=3,
        tags=seed_tags,
        artifacts=["scripts/benchmark_service.py"],
    )
    print(f"seed_status={seed_result['status']} seed_id={seed_result['id']}")

    cases = [
        run_case(
            "memory_search",
            args.iterations,
            args.search_budget_ms or settings.perf_budget_search_ms,
            lambda: service.search(
                project=args.project,
                repo=args.repo,
                query="Find the benchmark seed memory for latency testing.",
                top_k=3,
                tags=["benchmark"],
                memory_type="task_summary",
            ),
        ),
        run_case(
            "memory_ingest",
            args.iterations,
            args.ingest_budget_ms or settings.perf_budget_ingest_ms,
            lambda: service.ingest(
                project=args.project,
                repo=args.repo,
                task="benchmark ingest sample",
                summary=f"Benchmark ingest sample at {time.time()} for latency measurement.",
                memory_type="task_summary",
                importance=2,
                tags=["benchmark"],
                artifacts=[],
            ),
        ),
        run_case(
            "memory_recent",
            args.iterations,
            args.recent_budget_ms or settings.perf_budget_recent_ms,
            lambda: service.recent(
                project=args.project,
                repo=args.repo,
                limit=5,
            ),
        ),
    ]

    all_ok = True
    for name, samples, budget_ms in cases:
        all_ok = print_case(name, samples, budget_ms) and all_ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
