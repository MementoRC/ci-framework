"""JSON schema definitions for performance data storage."""

BENCHMARK_RESULT_SCHEMA = {
    "type": "object",
    "required": ["name", "execution_time", "timestamp"],
    "properties": {
        "name": {"type": "string", "description": "Name of the benchmark test"},
        "execution_time": {
            "type": "number",
            "minimum": 0,
            "description": "Execution time in seconds",
        },
        "memory_usage": {
            "type": ["number", "null"],
            "minimum": 0,
            "description": "Memory usage in MB",
        },
        "throughput": {
            "type": ["number", "null"],
            "minimum": 0,
            "description": "Throughput in operations per second",
        },
        "cpu_usage": {
            "type": ["number", "null"],
            "minimum": 0,
            "maximum": 100,
            "description": "CPU usage percentage",
        },
        "timestamp": {"type": "number", "description": "Unix timestamp when the benchmark was run"},
        "metadata": {"type": "object", "description": "Additional metadata for the benchmark"},
    },
    "additionalProperties": False,
}

PERFORMANCE_METRICS_SCHEMA = {
    "type": "object",
    "required": ["build_id", "timestamp", "results"],
    "properties": {
        "build_id": {"type": "string", "description": "Unique identifier for this build/run"},
        "timestamp": {
            "type": "string",
            "format": "date-time",
            "description": "ISO timestamp when metrics were collected",
        },
        "results": {
            "type": "array",
            "items": BENCHMARK_RESULT_SCHEMA,
            "description": "List of benchmark results",
        },
        "environment": {
            "type": "object",
            "description": "Environment variables and CI information",
            "properties": {
                "CI": {"type": "string"},
                "GITHUB_ACTIONS": {"type": "string"},
                "GITHUB_WORKFLOW": {"type": "string"},
                "GITHUB_RUN_ID": {"type": "string"},
                "GITHUB_RUN_NUMBER": {"type": "string"},
                "GITHUB_SHA": {"type": "string"},
                "GITHUB_REF": {"type": "string"},
            },
        },
        "system_info": {
            "type": "object",
            "description": "System information where benchmarks were run",
            "properties": {
                "platform": {"type": "string"},
                "python_version": {"type": "string"},
                "cpu_count": {"type": "integer"},
                "cpu_percent": {"type": "number"},
                "memory_total_gb": {"type": "number"},
                "memory_available_gb": {"type": "number"},
                "memory_percent": {"type": "number"},
                "disk_total_gb": {"type": "number"},
                "disk_free_gb": {"type": "number"},
                "disk_percent": {"type": "number"},
            },
        },
        "summary_stats": {
            "type": "object",
            "description": "Summary statistics across all benchmark results",
            "properties": {
                "avg_execution_time": {"type": "number"},
                "max_execution_time": {"type": "number"},
                "min_execution_time": {"type": "number"},
                "total_execution_time": {"type": "number"},
                "avg_memory_usage": {"type": "number"},
                "max_memory_usage": {"type": "number"},
                "min_memory_usage": {"type": "number"},
                "avg_throughput": {"type": "number"},
                "max_throughput": {"type": "number"},
                "min_throughput": {"type": "number"},
            },
        },
    },
    "additionalProperties": False,
}

COMPARISON_RESULT_SCHEMA = {
    "type": "object",
    "required": ["baseline_build_id", "current_build_id", "comparisons"],
    "properties": {
        "baseline_build_id": {"type": "string", "description": "Build ID of the baseline"},
        "current_build_id": {"type": "string", "description": "Build ID of the current run"},
        "baseline_timestamp": {
            "type": "string",
            "format": "date-time",
            "description": "Timestamp of the baseline",
        },
        "current_timestamp": {
            "type": "string",
            "format": "date-time",
            "description": "Timestamp of the current run",
        },
        "comparisons": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "execution_time"],
                "properties": {
                    "name": {"type": "string", "description": "Name of the benchmark"},
                    "execution_time": {
                        "type": "object",
                        "required": ["current", "baseline", "change_percent", "change_direction"],
                        "properties": {
                            "current": {"type": "number"},
                            "baseline": {"type": "number"},
                            "change_percent": {"type": "number"},
                            "change_direction": {
                                "type": "string",
                                "enum": ["improvement", "regression", "unchanged"],
                            },
                        },
                    },
                    "memory_usage": {
                        "type": "object",
                        "properties": {
                            "current": {"type": "number"},
                            "baseline": {"type": "number"},
                            "change_percent": {"type": "number"},
                            "change_direction": {
                                "type": "string",
                                "enum": ["improvement", "regression", "unchanged"],
                            },
                        },
                    },
                    "throughput": {
                        "type": "object",
                        "properties": {
                            "current": {"type": "number"},
                            "baseline": {"type": "number"},
                            "change_percent": {"type": "number"},
                            "change_direction": {
                                "type": "string",
                                "enum": ["improvement", "regression", "unchanged"],
                            },
                        },
                    },
                },
            },
        },
    },
    "additionalProperties": False,
}
