# Performance Benchmark Action API Reference

> **Standardized performance monitoring with pytest-benchmark integration and statistical regression detection**

## Overview

The Performance Benchmark Action provides comprehensive performance monitoring through systematic benchmarking with statistical regression detection. It integrates pytest-benchmark for standardized Python performance testing and includes baseline comparison, trend analysis, and automated alerting for performance regressions.

## Action Metadata

| Property | Value |
|----------|-------|
| **Name** | `Performance Benchmark Action` |
| **Description** | Standardized performance monitoring with pytest-benchmark integration and statistical regression detection |
| **Author** | CI Framework |
| **Version** | v0.0.1 |
| **Icon** | trending-up |
| **Color** | orange |

## Usage

```yaml
- uses: ./actions/performance-benchmark
  with:
    suite: 'quick'
    regression-threshold: '10.0'
    compare-baseline: 'true'
    store-results: 'true'
```

## API Reference

### Inputs

#### `suite`
- **Description**: Benchmark suite to execute (quick, full, load)
- **Required**: No
- **Default**: `'quick'`
- **Type**: String
- **Valid Values**: `quick`, `full`, `load`

**Suite Characteristics:**
- **Quick (≤30s)**: Fast benchmarks for development feedback
- **Full (≤5min)**: Comprehensive benchmark suite for integration
- **Load (≤10min)**: Stress testing and load performance validation

#### `baseline-branch`
- **Description**: Branch to compare performance against
- **Required**: No
- **Default**: `'main'`
- **Type**: String
- **Example**: `'develop'`, `'release/v1.0'`

#### `regression-threshold`
- **Description**: Performance regression threshold percentage (e.g. 10.0)
- **Required**: No
- **Default**: `'10.0'`
- **Type**: String (numeric)
- **Example**: `'5.0'` for 5% threshold, `'25.0'` for 25% threshold

#### `timeout`
- **Description**: Timeout in seconds for benchmark execution
- **Required**: No
- **Default**: `'1800'` (30 minutes)
- **Type**: String (numeric)
- **Example**: `'3600'` for 1 hour

#### `project-dir`
- **Description**: Project directory to benchmark (default: current directory)
- **Required**: No
- **Default**: `'.'`
- **Type**: String
- **Example**: `'./performance-tests'`

#### `config-file`
- **Description**: Path to custom benchmark configuration file
- **Required**: No
- **Default**: `''` (auto-detect)
- **Type**: String
- **Example**: `'./benchmark-config.toml'`

#### `store-results`
- **Description**: Store benchmark results for historical analysis
- **Required**: No
- **Default**: `'true'`
- **Type**: String (boolean)
- **Valid Values**: `'true'`, `'false'`

#### `results-dir`
- **Description**: Directory to store benchmark results
- **Required**: No
- **Default**: `'benchmark-results'`
- **Type**: String
- **Example**: `'performance-data'`

#### `package-manager`
- **Description**: Force specific package manager (pixi, poetry, hatch, pip)
- **Required**: No
- **Default**: `'auto'`
- **Type**: String
- **Valid Values**: `'auto'`, `'pixi'`, `'poetry'`, `'hatch'`, `'pip'`

#### `compare-baseline`
- **Description**: Compare against baseline and detect regressions
- **Required**: No
- **Default**: `'true'`
- **Type**: String (boolean)
- **Valid Values**: `'true'`, `'false'`

#### `fail-on-regression`
- **Description**: Fail the action if performance regression is detected
- **Required**: No
- **Default**: `'true'`
- **Type**: String (boolean)
- **Valid Values**: `'true'`, `'false'`

#### `parallel`
- **Description**: Run benchmarks in parallel when possible
- **Required**: No
- **Default**: `'false'`
- **Type**: String (boolean)
- **Valid Values**: `'true'`, `'false'`

### Outputs

#### `success`
- **Description**: Whether all benchmarks passed without regression
- **Type**: Boolean
- **Example**: `true`

#### `suite`
- **Description**: Benchmark suite that was executed
- **Type**: String
- **Example**: `'quick'`

#### `execution-time`
- **Description**: Total benchmark execution time in seconds
- **Type**: Number
- **Example**: `145.67`

#### `benchmark-count`
- **Description**: Number of benchmarks executed
- **Type**: Number
- **Example**: `23`

#### `regression-detected`
- **Description**: Whether performance regression was detected
- **Type**: Boolean
- **Example**: `false`

#### `regression-percentage`
- **Description**: Percentage of performance regression detected
- **Type**: Number
- **Example**: `15.3`

#### `baseline-comparison`  
- **Description**: Performance comparison with baseline
- **Type**: String
- **Example**: `'5.2% faster than baseline'`

#### `results-path`
- **Description**: Path to generated benchmark results
- **Type**: String
- **Example**: `'benchmark-results'`

#### `performance-report`
- **Description**: Detailed performance report summary
- **Type**: String
- **Example**: `'Executed 23 benchmarks successfully, 2 showed improvement'`

#### `trend-analysis`
- **Description**: Performance trend analysis over time
- **Type**: String
- **Example**: `'Performance stable over last 10 runs'`

---

## Configuration

### Project Configuration

Configure performance benchmarking in `pyproject.toml`:

```toml
[tool.ci-framework.performance-benchmark]
# Default suite configuration
default_suite = "quick"
regression_threshold = 10.0
baseline_branch = "main"

# Suite definitions
[tool.ci-framework.performance-benchmark.suites]
quick = { max_time = 30, min_rounds = 3 }
full = { max_time = 300, min_rounds = 5 }
load = { max_time = 600, min_rounds = 10 }

# Benchmark configuration
[tool.pytest.benchmark]
disable = false
min_rounds = 5
max_time = 60
min_time = 0.01
sort = "mean"
group_by = "group"
columns = ["mean", "stddev", "rounds", "min", "max"]
histogram = true
save_data = true
```

### Benchmark Test Structure

Organize benchmarks in a dedicated directory:

```
tests/
├── benchmarks/
│   ├── test_performance_core.py      # Core functionality benchmarks
│   ├── test_performance_io.py        # I/O operation benchmarks
│   ├── test_performance_algorithms.py # Algorithm benchmarks
│   └── conftest.py                   # Benchmark fixtures
```

Example benchmark test:

```python
import pytest
from myproject import algorithms

class TestAlgorithmPerformance:
    
    @pytest.mark.benchmark(group="sorting")
    def test_quicksort_performance(self, benchmark):
        data = list(range(1000, 0, -1))  # Worst case
        result = benchmark(algorithms.quicksort, data)
        assert result == list(range(1, 1001))
    
    @pytest.mark.benchmark(group="sorting") 
    def test_mergesort_performance(self, benchmark):
        data = list(range(1000, 0, -1))
        result = benchmark(algorithms.mergesort, data)
        assert result == list(range(1, 1001))
    
    @pytest.mark.benchmark(group="search")
    def test_binary_search_performance(self, benchmark):
        data = list(range(10000))
        target = 7500
        result = benchmark(algorithms.binary_search, data, target)
        assert result == 7500
```

---

## Usage Examples

### Basic Performance Testing

```yaml
name: Performance Check
on: [push, pull_request]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/performance-benchmark
        with:
          suite: 'quick'
```

### Comprehensive Performance Pipeline

```yaml
name: Performance Monitoring
on:
  push:
    branches: [main, develop]
  pull_request:

jobs:
  quick-benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/performance-benchmark
        with:
          suite: 'quick'
          regression-threshold: '15.0'
  
  full-benchmark:
    needs: quick-benchmark
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/performance-benchmark
        with:
          suite: 'full'
          regression-threshold: '10.0'
          store-results: 'true'
  
  load-testing:
    needs: full-benchmark
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/performance-benchmark
        with:
          suite: 'load'
          regression-threshold: '5.0'
          timeout: '3600'
```

### Baseline Comparison

```yaml
name: Performance Regression Detection
on: [pull_request]

jobs:
  performance-comparison:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Need full history for baseline comparison
      
      - name: Benchmark Current Changes
        uses: ./actions/performance-benchmark
        id: current
        with:
          suite: 'full'
          compare-baseline: 'true'
          baseline-branch: 'main'
          fail-on-regression: 'true'
          regression-threshold: '10.0'
      
      - name: Comment Performance Results
        uses: actions/github-script@v6
        if: always()
        with:
          script: |
            const regressionDetected = '${{ steps.current.outputs.regression-detected }}' === 'true';
            const regressionPercent = '${{ steps.current.outputs.regression-percentage }}';
            const baselineComparison = '${{ steps.current.outputs.baseline-comparison }}';
            
            let comment = '## 📊 Performance Benchmark Results\n\n';
            
            if (regressionDetected) {
              comment += `⚠️ **Performance Regression Detected**: ${regressionPercent}% slower\n\n`;
            } else {
              comment += `✅ **No Performance Regression**: ${baselineComparison}\n\n`;
            }
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
```

### Advanced Configuration with Custom Thresholds

```yaml
name: Tiered Performance Testing
on: [push, pull_request]

jobs:
  performance-matrix:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        include:
          - suite: quick
            threshold: "20.0"
            timeout: "300"
          - suite: full
            threshold: "10.0" 
            timeout: "1800"
          - suite: load
            threshold: "5.0"
            timeout: "3600"
    steps:
      - uses: actions/checkout@v4
      
      - name: Performance Benchmark - ${{ matrix.suite }}
        uses: ./actions/performance-benchmark
        with:
          suite: ${{ matrix.suite }}
          regression-threshold: ${{ matrix.threshold }}
          timeout: ${{ matrix.timeout }}
          parallel: ${{ matrix.suite == 'load' && 'false' || 'true' }}
          results-dir: 'benchmarks-${{ matrix.suite }}'
```

### Historical Performance Tracking

```yaml
name: Performance Trend Analysis
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  push:
    branches: [main]

jobs:
  trend-analysis:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Download Historical Data
        uses: actions/download-artifact@v3
        continue-on-error: true
        with:
          name: performance-history
          path: performance-history
      
      - name: Run Performance Benchmarks
        uses: ./actions/performance-benchmark
        id: benchmarks
        with:
          suite: 'full'
          store-results: 'true'
          compare-baseline: 'true'
      
      - name: Store Performance History
        uses: actions/upload-artifact@v3
        with:
          name: performance-history
          path: ${{ steps.benchmarks.outputs.results-path }}
          retention-days: 365
```

---

## Integration Patterns

### With Quality Gates

```yaml
jobs:
  quality-performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Quality Gates
        uses: ./actions/quality-gates
        id: quality
        with:
          tier: 'extended'
      
      - name: Performance Benchmarks
        if: steps.quality.outputs.success == 'true'
        uses: ./actions/performance-benchmark
        with:
          suite: 'quick'
          fail-on-regression: 'false'  # Don't fail on performance issues during development
```

### With Change Detection

```yaml
jobs:
  changes:
    runs-on: ubuntu-latest
    outputs:
      performance-critical: ${{ steps.changes.outputs.performance-critical }}
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/change-detection
        id: changes
        with:
          patterns: |
            performance-critical:
              - 'src/algorithms/**'
              - 'src/core/**'
              - 'tests/benchmarks/**'

  performance:
    needs: changes
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/performance-benchmark
        with:
          # Use more comprehensive suite if performance-critical files changed
          suite: ${{ needs.changes.outputs.performance-critical == 'true' && 'full' || 'quick' }}
          regression-threshold: ${{ needs.changes.outputs.performance-critical == 'true' && '5.0' || '15.0' }}
```

### With Security Scanning

```yaml
jobs:
  security-performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Security Scan
        uses: ./actions/security-scan
        with:
          security-level: 'medium'
      
      - name: Performance Impact Analysis
        uses: ./actions/performance-benchmark
        with:
          suite: 'quick'
          compare-baseline: 'true'
        # Ensure security fixes don't introduce performance regressions
```

---

## Troubleshooting

### Common Issues

#### Benchmark Timeouts
```yaml
# Increase timeout for compute-intensive benchmarks
- uses: ./actions/performance-benchmark
  with:
    suite: 'load'
    timeout: '7200'  # 2 hours
```

#### Flaky Benchmark Results
```yaml
# Increase minimum rounds for stability
- uses: ./actions/performance-benchmark
  with:
    config-file: './benchmark-stable-config.toml'
```

```toml
# benchmark-stable-config.toml
[tool.pytest.benchmark]
min_rounds = 10
max_time = 120
warmup = true
warmup_iterations = 3
```

#### Baseline Comparison Issues
```yaml
# Ensure baseline data is available
- name: Download Baseline
  uses: actions/download-artifact@v3
  continue-on-error: true
  with:
    name: benchmark-baseline-main
    path: baseline-results

- uses: ./actions/performance-benchmark
  with:
    compare-baseline: 'true'
    fail-on-regression: 'false'  # Don't fail if no baseline available
```

### Performance Optimization

```yaml
# Optimize for different runner types
- uses: ./actions/performance-benchmark
  with:
    # For standard runners (2 cores)
    parallel: 'false'
    suite: 'quick'
    
    # For larger runners (4+ cores) 
    # parallel: 'true'
    # suite: 'full'
```

### Debug Information

```yaml
- uses: ./actions/performance-benchmark
  with:
    suite: 'quick'
  env:
    ACTIONS_STEP_DEBUG: true
    PYTEST_BENCHMARK_DISABLE: false
```

---

## Benchmark Design Best Practices

### Writing Effective Benchmarks

```python
import pytest
import time

class TestPerformanceBestPractices:
    
    def test_good_benchmark(self, benchmark):
        """Well-designed benchmark with proper setup."""
        
        # Good: Setup data outside of benchmark
        data = list(range(1000))
        
        # Good: Benchmark only the specific operation
        result = benchmark(my_algorithm, data)
        
        # Good: Verify correctness
        assert len(result) == 1000
    
    def test_avoid_this_benchmark(self, benchmark):
        """Example of what NOT to do."""
        
        def bad_benchmark_function():
            # Bad: Setup inside benchmark
            data = list(range(1000))
            # Bad: Multiple operations
            result1 = operation1(data)
            result2 = operation2(result1)
            # Bad: No verification
            return result2
        
        # This benchmarks setup + multiple operations
        benchmark(bad_benchmark_function)
```

### Benchmark Organization

```python
# Group related benchmarks
@pytest.mark.benchmark(group="data-structures")
def test_list_performance(self, benchmark):
    pass

@pytest.mark.benchmark(group="data-structures")  
def test_dict_performance(self, benchmark):
    pass

@pytest.mark.benchmark(group="algorithms")
def test_sort_performance(self, benchmark):
    pass
```

### Parameterized Benchmarks

```python
@pytest.mark.parametrize("size", [100, 1000, 10000])
@pytest.mark.benchmark(group="scaling")
def test_algorithm_scaling(self, benchmark, size):
    """Test how algorithm performs with different input sizes."""
    data = list(range(size))
    result = benchmark(my_algorithm, data)
    assert len(result) == size
```

---

## Performance Metrics

### Execution Times by Suite

| Project Size | Quick Suite | Full Suite | Load Suite |
|--------------|-------------|------------|------------|
| Small (< 10 benchmarks) | 10-30s | 1-3min | 3-8min |
| Medium (10-50 benchmarks) | 30s-2min | 3-10min | 10-25min |
| Large (> 50 benchmarks) | 1-5min | 10-30min | 30-60min |

### Resource Requirements

- **CPU**: Benchmarks are CPU-intensive, benefit from dedicated runners
- **Memory**: Varies by benchmark, typically 1-4GB
- **Storage**: Results data typically 10-100MB per run
- **Network**: Minimal (only for downloading baseline data)

### Statistical Significance

The action uses pytest-benchmark's statistical analysis:

- **Minimum Rounds**: Ensures statistically valid results
- **Confidence Intervals**: Provides result reliability metrics
- **Outlier Detection**: Automatically handles anomalous results
- **Trend Analysis**: Compares against historical baselines

---

## Migration Guide

### From Manual pytest-benchmark

```yaml
# Before: Manual benchmark execution
- name: Run Benchmarks
  run: pytest tests/benchmarks/ --benchmark-only --benchmark-json=results.json

# After: Framework performance action
- uses: ./actions/performance-benchmark
  with:
    suite: 'quick'
    store-results: 'true'
```

### From Custom Performance Tests

```yaml
# Before: Custom performance scripts
- name: Performance Test
  run: python scripts/performance_test.py

# After: Standardized benchmarking
- uses: ./actions/performance-benchmark
  with:
    suite: 'full'
    regression-threshold: '10.0'
```

### From pytest-benchmark directly

Replace direct pytest-benchmark usage with action for:
- **Automated baseline comparison**
- **Regression detection with configurable thresholds**
- **GitHub integration with PR comments**
- **Artifact management for historical analysis**
- **Consistent CI/CD integration patterns**

---

**Action Version**: 0.0.1  
**Last Updated**: January 2025  
**Compatibility**: GitHub Actions v4+, Python 3.10+, pytest-benchmark 4.0+