"""Data models for performance metrics and benchmark results."""

import time
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BenchmarkResult:
    """Single benchmark measurement result."""

    name: str
    execution_time: float  # seconds
    memory_usage: float | None = None  # MB
    throughput: float | None = None  # operations per second
    cpu_usage: float | None = None  # percentage
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, str | int | float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "execution_time": self.execution_time,
            "memory_usage": self.memory_usage,
            "throughput": self.throughput,
            "cpu_usage": self.cpu_usage,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BenchmarkResult":
        """Create from dictionary representation."""
        return cls(
            name=data["name"],
            execution_time=data["execution_time"],
            memory_usage=data.get("memory_usage"),
            throughput=data.get("throughput"),
            cpu_usage=data.get("cpu_usage"),
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {}),
        )


@dataclass
class PerformanceMetrics:
    """Collection of performance metrics for a build/run."""

    build_id: str
    timestamp: datetime
    results: list[BenchmarkResult] = field(default_factory=list)
    environment: dict[str, str] = field(default_factory=dict)
    system_info: dict[str, str | int | float] = field(default_factory=dict)

    def add_result(self, result: BenchmarkResult) -> None:
        """Add a benchmark result to the collection."""
        self.results.append(result)

    def get_result(self, name: str) -> BenchmarkResult | None:
        """Get a specific benchmark result by name."""
        for result in self.results:
            if result.name == name:
                return result
        return None

    def get_results_by_pattern(self, pattern: str) -> list[BenchmarkResult]:
        """Get benchmark results matching a name pattern."""
        return [result for result in self.results if pattern in result.name]

    def calculate_summary_stats(self) -> dict[str, float]:
        """Calculate summary statistics across all results."""
        if not self.results:
            return {}

        execution_times = [r.execution_time for r in self.results if r.execution_time is not None]
        memory_usages = [r.memory_usage for r in self.results if r.memory_usage is not None]
        throughputs = [r.throughput for r in self.results if r.throughput is not None]

        stats = {}

        if execution_times:
            stats.update(
                {
                    "avg_execution_time": sum(execution_times) / len(execution_times),
                    "max_execution_time": max(execution_times),
                    "min_execution_time": min(execution_times),
                    "total_execution_time": sum(execution_times),
                }
            )

        if memory_usages:
            stats.update(
                {
                    "avg_memory_usage": sum(memory_usages) / len(memory_usages),
                    "max_memory_usage": max(memory_usages),
                    "min_memory_usage": min(memory_usages),
                }
            )

        if throughputs:
            stats.update(
                {
                    "avg_throughput": sum(throughputs) / len(throughputs),
                    "max_throughput": max(throughputs),
                    "min_throughput": min(throughputs),
                }
            )

        return stats

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "build_id": self.build_id,
            "timestamp": self.timestamp.isoformat(),
            "results": [result.to_dict() for result in self.results],
            "environment": self.environment,
            "system_info": self.system_info,
            "summary_stats": self.calculate_summary_stats(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PerformanceMetrics":
        """Create from dictionary representation."""
        return cls(
            build_id=data["build_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            results=[BenchmarkResult.from_dict(r) for r in data.get("results", [])],
            environment=data.get("environment", {}),
            system_info=data.get("system_info", {}),
        )
