from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class RequestMetrics:
    total_requests: int = 0
    total_errors: int = 0
    endpoint_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    status_counts: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    tool_calls: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    start_time: float = field(default_factory=time.monotonic)
    _latencies: list[float] = field(default_factory=list)

    def record(self, endpoint: str, status_code: int, latency: float) -> None:
        self.total_requests += 1
        self.endpoint_counts[endpoint] += 1
        self.status_counts[status_code] += 1
        if status_code >= 400:
            self.total_errors += 1
        self._latencies.append(latency)
        if len(self._latencies) > 1000:
            self._latencies = self._latencies[-500:]

    def record_tool_call(self, tool_name: str) -> None:
        self.tool_calls[tool_name] += 1

    def summary(self) -> dict:
        uptime = time.monotonic() - self.start_time
        latencies = sorted(self._latencies)
        p50 = latencies[len(latencies) // 2] if latencies else 0
        p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0
        p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0
        return {
            "uptime_seconds": round(uptime, 1),
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "error_rate": round(self.total_errors / max(1, self.total_requests), 3),
            "endpoints": dict(self.endpoint_counts),
            "status_codes": dict(self.status_counts),
            "tool_calls": dict(self.tool_calls),
            "latency_ms": {
                "p50": round(p50 * 1000, 1),
                "p95": round(p95 * 1000, 1),
                "p99": round(p99 * 1000, 1),
            },
        }
