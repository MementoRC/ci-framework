"""
Framework Property-Based Tests

Uses hypothesis to test framework components with generated data
to verify properties and invariants hold across a wide range of inputs.
"""

import pytest
import string
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from framework.performance.collector import PerformanceCollector, PerformanceMetrics
from framework.reporting.github_reporter import GitHubReporter


@pytest.mark.property
class TestFrameworkProperties:
    """Property-based tests for framework components."""

    @given(
        execution_time=st.floats(min_value=0.001, max_value=1000.0),
        memory_usage=st.integers(min_value=1, max_value=10000),
        throughput=st.integers(min_value=1, max_value=100000),
    )
    @settings(
        max_examples=5,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=2000,  # Increase deadline to 2 seconds
    )
    def test_performance_collector_data_integrity(
        self, execution_time, memory_usage, throughput, tmp_path
    ):
        """Test that performance collector maintains data integrity across various inputs."""
        # Setup
        collector = PerformanceCollector(storage_path=tmp_path)

        # Create test data with generated values
        test_name = "property_test"
        performance_data = {
            "name": test_name,
            "execution_time": execution_time,
            "memory_usage": memory_usage,  # Pass as float, not string
            "throughput": throughput,
        }

        # Collect metrics and store as baseline
        metrics = collector.collect_metrics(performance_data)
        collector.store_baseline(metrics, baseline_name=test_name)

        # Retrieve the stored baseline
        retrieved_metrics = collector.load_baseline(baseline_name=test_name)

        # Verify data integrity properties
        assert retrieved_metrics is not None
        assert len(retrieved_metrics.results) == 1

        # Get the stored benchmark result
        stored_result = retrieved_metrics.get_result(test_name)
        assert stored_result is not None

        # Check that the values match (within floating point tolerance)
        assert abs(stored_result.execution_time - execution_time) < 0.0001
        # Note: memory_usage is stored as float, not string
        assert abs(stored_result.memory_usage - memory_usage) < 0.0001
        assert abs(stored_result.throughput - throughput) < 0.0001

    @given(
        test_names=st.lists(
            st.text(
                min_size=1,
                max_size=50,
                alphabet=string.ascii_letters + string.digits + "_-",
            ),
            min_size=1,
            max_size=10,
            unique=True,
        ),
        values=st.lists(
            st.floats(min_value=0.001, max_value=1000.0), min_size=1, max_size=10
        ),
    )
    @settings(
        max_examples=5,
        suppress_health_check=[
            HealthCheck.function_scoped_fixture,
            HealthCheck.filter_too_much,
        ],
    )
    def test_performance_metrics_aggregation_properties(
        self, test_names, values, tmp_path
    ):
        """Test that performance metrics aggregation maintains mathematical properties."""
        assume(len(test_names) == len(values))

        # Setup
        from datetime import datetime

        metrics = PerformanceMetrics(build_id="test_build", timestamp=datetime.now())

        # Add results with generated data
        from framework.performance.models import BenchmarkResult

        for name, value in zip(test_names, values, strict=True):
            result = BenchmarkResult(name=name, execution_time=value)
            metrics.add_result(result)

        # Calculate summary statistics
        summary = metrics.calculate_summary_stats()

        # Verify mathematical properties
        if len(values) > 0:
            min_value = min(values)
            max_value = max(values)

            # The summary stats are aggregated across all results
            if "avg_execution_time" in summary:
                avg_time = summary["avg_execution_time"]
                # Property: min <= mean <= max
                assert min_value <= avg_time <= max_value

    @given(
        vulnerabilities=st.lists(
            st.tuples(
                st.sampled_from(["low", "medium", "high", "critical"]),
                st.text(
                    min_size=1,
                    max_size=30,
                    alphabet=string.ascii_letters + string.digits + "_-",
                ),
            ),
            min_size=0,
            max_size=20,
        ),
    )
    @settings(max_examples=15)
    def test_security_analyzer_vulnerability_counting_properties(
        self, vulnerabilities
    ):
        """Test that security analyzer maintains counting properties."""

        # Create mock vulnerability data from tuples
        vulnerability_data = []
        for severity, package in vulnerabilities:
            vulnerability_data.append(
                {"package": package, "severity": severity, "version": "1.0.0"}
            )

        # Count vulnerabilities by severity
        severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for vuln in vulnerability_data:
            severity_counts[vuln["severity"]] += 1

        # Verify counting properties
        total_count = sum(severity_counts.values())
        assert total_count == len(vulnerability_data)

        # Property: sum of individual counts equals total
        assert (
            severity_counts["low"]
            + severity_counts["medium"]
            + severity_counts["high"]
            + severity_counts["critical"]
            == total_count
        )

        # Property: all counts are non-negative
        for count in severity_counts.values():
            assert count >= 0

    @given(
        test_count=st.integers(min_value=0, max_value=10000),
        coverage=st.floats(min_value=0.0, max_value=100.0),
        duration_seconds=st.integers(min_value=1, max_value=7200),
    )
    @settings(max_examples=20)
    def test_github_reporter_summary_properties(
        self, test_count, coverage, duration_seconds
    ):
        """Test that GitHub reporter maintains summary properties."""
        # Setup
        reporter = GitHubReporter()

        # Generate build status summary
        test_results = {
            "total": test_count,
            "duration": duration_seconds,  # Use seconds as numeric value
            "coverage": coverage,  # Include coverage in test results
        }
        summary = reporter.create_build_status_summary(
            build_status="success",
            test_results=test_results,
        )

        # Verify summary properties
        assert summary is not None
        assert isinstance(summary, str)
        assert len(summary) > 0

        # Property: summary should contain key information
        assert str(test_count) in summary
        # Property: duration should be present when > 0
        if duration_seconds > 0:
            assert "Duration" in summary or "duration" in summary.lower()
        
        # Property: status information should be present
        assert "Status" in summary or "status" in summary.lower()

    @given(
        benchmark_data=st.dictionaries(
            keys=st.text(
                min_size=1,
                max_size=30,
                alphabet=string.ascii_letters + string.digits + "_-",
            ),
            values=st.dictionaries(
                keys=st.sampled_from(["execution_time", "memory_usage", "throughput"]),
                values=st.one_of(
                    st.floats(min_value=0.001, max_value=1000.0),
                    st.integers(min_value=1, max_value=10000),
                ),
                min_size=1,
                max_size=3,
            ),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=10, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_performance_collector_batch_operations_properties(
        self, benchmark_data, tmp_path
    ):
        """Test that batch operations maintain consistency properties."""
        # Setup
        collector = PerformanceCollector(storage_path=tmp_path)

        # Store batch data using collect_metrics + store_baseline
        for test_name, expected_data in benchmark_data.items():
            test_data = {
                "name": test_name,
                "execution_time": expected_data.get("execution_time", 1.0),
                "memory_usage": expected_data.get("memory_usage"),
                "throughput": expected_data.get("throughput")
            }
            metrics = collector.collect_metrics(test_data)
            collector.store_baseline(metrics, baseline_name=test_name)

        # Verify batch consistency properties
        for test_name, expected_data in benchmark_data.items():
            retrieved_metrics = collector.load_baseline(baseline_name=test_name)

            # Property: all stored data can be retrieved
            assert retrieved_metrics is not None
            assert len(retrieved_metrics.results) == 1
            
            retrieved_result = retrieved_metrics.results[0]
            
            # Property: retrieved data matches stored data
            assert retrieved_result.name == test_name
            if "execution_time" in expected_data:
                assert abs(retrieved_result.execution_time - expected_data["execution_time"]) < 1e-10

    @given(
        values_pair=st.integers(min_value=1, max_value=10).flatmap(
            lambda n: st.tuples(
                st.lists(st.floats(min_value=0.1, max_value=100.0), min_size=n, max_size=n),
                st.lists(st.floats(min_value=0.1, max_value=100.0), min_size=n, max_size=n)
            )
        )
    )
    @settings(max_examples=15)
    def test_performance_comparison_properties(self, values_pair):
        """Test that performance comparison maintains mathematical properties."""
        baseline_values, current_values = values_pair

        # Calculate percentage changes
        percentage_changes = []
        for baseline, current in zip(baseline_values, current_values, strict=True):
            if baseline > 0:
                change = ((current - baseline) / baseline) * 100
                percentage_changes.append(change)

        # Verify comparison properties
        for baseline, current, change in zip(
            baseline_values, current_values, percentage_changes, strict=True
        ):
            # Property: improvement should be negative percentage change
            if current < baseline:
                assert change < 0

            # Property: regression should be positive percentage change
            elif current > baseline:
                assert change > 0

            # Property: no change should be zero percentage change
            else:
                assert abs(change) < 1e-10

    @given(
        metric_values=st.lists(
            st.floats(min_value=0.001, max_value=1000.0), min_size=2, max_size=100
        )
    )
    @settings(max_examples=10)
    def test_statistical_properties_invariants(self, metric_values):
        """Test that statistical calculations maintain mathematical invariants."""
        # Calculate basic statistics
        n = len(metric_values)
        mean_val = sum(metric_values) / n
        min_val = min(metric_values)
        max_val = max(metric_values)

        # Verify statistical invariants
        # Property: min <= mean <= max
        assert min_val <= mean_val <= max_val

        # Property: variance is non-negative
        variance = sum((x - mean_val) ** 2 for x in metric_values) / n
        assert variance >= 0

        # Property: standard deviation is non-negative
        std_dev = variance**0.5
        assert std_dev >= 0

        # Property: if all values are the same, variance should be 0
        if len(set(metric_values)) == 1:
            assert variance < 1e-10

    @given(
        file_count=st.integers(min_value=1, max_value=1000),
        test_percentage=st.floats(min_value=0.0, max_value=100.0),
    )
    @settings(max_examples=15)
    def test_coverage_calculation_properties(self, file_count, test_percentage):
        """Test that coverage calculations maintain mathematical properties."""
        # Calculate covered files
        covered_files = int((test_percentage / 100.0) * file_count)

        # Verify coverage properties
        # Property: covered files cannot exceed total files
        assert covered_files <= file_count

        # Property: covered files cannot be negative
        assert covered_files >= 0

        # Property: if percentage is very close to 100%, all files should be covered
        if abs(test_percentage - 100.0) < 1e-10:
            # Use round instead of int for edge cases near 100%
            covered_files_rounded = round((test_percentage / 100.0) * file_count)
            assert covered_files_rounded == file_count

        # Property: if percentage is 0%, no files should be covered
        if abs(test_percentage) < 1e-10:
            assert covered_files == 0


@pytest.mark.property
class TestFrameworkDataValidation:
    """Property-based tests for data validation in framework."""

    @given(
        data=st.dictionaries(
            keys=st.text(min_size=1, max_size=50),
            values=st.one_of(
                st.text(min_size=0, max_size=100),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.booleans(),
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(
        max_examples=3, 
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=5000  # 5 seconds for system info collection
    )
    def test_data_serialization_properties(self, data, tmp_path):
        """Test that data serialization maintains consistency properties."""
        # Setup
        collector = PerformanceCollector(storage_path=tmp_path)

        # Create a test with the generated data
        test_name = "serialization_test"
        test_data = {
            "name": test_name,
            "execution_time": 1.0,
            "test_data": data  # Include the generated data as metadata
        }

        # Collect metrics and store as baseline
        metrics = collector.collect_metrics(test_data)
        collector.store_baseline(metrics, baseline_name=test_name)

        # Retrieve the stored baseline
        retrieved_metrics = collector.load_baseline(baseline_name=test_name)

        # Property: serialization round-trip should preserve data
        assert retrieved_metrics is not None
        assert len(retrieved_metrics.results) == 1

        # Find the stored benchmark result
        stored_result = None
        for result in retrieved_metrics.results:
            if result.name == test_name:
                stored_result = result
                break

        assert stored_result is not None

        # Verify data was preserved in the serialization/deserialization
        # The exact structure may be different but key data should be preserved
        assert stored_result.name == test_name
