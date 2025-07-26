# Performance Benchmark Action

Standardized performance monitoring action with pytest-benchmark integration and statistical regression detection for Python projects.

## Features

- **Multiple Benchmark Suites**: Support for quick, full, and load testing suites
- **Statistical Regression Detection**: Configurable thresholds with significance testing
- **Historical Trend Analysis**: Track performance changes over time
- **Package Manager Support**: Auto-detection for pixi, poetry, hatch, and pip
- **Baseline Comparison**: Compare against main branch or custom baseline
- **PR Performance Reports**: Automated comments with performance impact analysis
- **Parallel Execution**: Optional parallel benchmark execution for faster results

## Quick Start

```yaml
name: Performance Tests
on: [push, pull_request]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Needed for baseline comparison
      
      - name: Run Performance Benchmarks
        uses: ./actions/performance-benchmark
        with:
          suite: 'quick'
          regression-threshold: '10.0'
          compare-baseline: 'true'
          fail-on-regression: 'true'
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `suite` | Benchmark suite to execute (`quick`, `full`, `load`) | No | `quick` |
| `baseline-branch` | Branch to compare performance against | No | `main` |
| `regression-threshold` | Performance regression threshold percentage | No | `10.0` |
| `timeout` | Timeout in seconds for benchmark execution | No | `1800` |
| `project-dir` | Project directory to benchmark | No | `.` |
| `config-file` | Path to custom benchmark configuration file | No | `` |
| `store-results` | Store benchmark results for historical analysis | No | `true` |
| `results-dir` | Directory to store benchmark results | No | `benchmark-results` |
| `package-manager` | Force specific package manager | No | `auto` |
| `compare-baseline` | Compare against baseline and detect regressions | No | `true` |
| `fail-on-regression` | Fail the action if performance regression is detected | No | `true` |
| `parallel` | Run benchmarks in parallel when possible | No | `false` |

## Outputs

| Output | Description |
|--------|-------------|
| `success` | Whether all benchmarks passed without regression |
| `suite` | Benchmark suite that was executed |
| `execution-time` | Total benchmark execution time in seconds |
| `benchmark-count` | Number of benchmarks executed |
| `regression-detected` | Whether performance regression was detected |
| `regression-percentage` | Percentage of performance regression detected |
| `baseline-comparison` | Performance comparison with baseline |
| `results-path` | Path to generated benchmark results |
| `performance-report` | Detailed performance report summary |
| `trend-analysis` | Performance trend analysis over time |

## Benchmark Suites

### Quick Suite
- **Duration**: ~30 seconds max per benchmark
- **Rounds**: 3 minimum
- **Use Case**: Fast feedback during development
- **When to Use**: Pull requests, frequent commits

### Full Suite
- **Duration**: ~5 minutes max per benchmark  
- **Rounds**: 5 minimum
- **Use Case**: Comprehensive performance validation
- **When to Use**: Release preparation, nightly builds

### Load Suite
- **Duration**: ~10 minutes max per benchmark
- **Rounds**: 10 minimum
- **Use Case**: Stress testing and scalability analysis
- **When to Use**: Performance validation, capacity planning

## Configuration

Create a `benchmark-config.toml` file in your project root:

```toml
[performance_benchmark]
regression_threshold = 15.0
significance_level = 0.05
min_rounds = 5
max_rounds = 50
warmup_rounds = 3
statistical_analysis = true
trend_analysis = true
store_historical = true

[performance_benchmark.quick]
max_time = 30
min_rounds = 3
warmup_rounds = 1

[performance_benchmark.full]
max_time = 300
min_rounds = 5
warmup_rounds = 3

[performance_benchmark.load]
max_time = 600
min_rounds = 10
warmup_rounds = 5
```

## Writing Benchmarks

Use pytest-benchmark to write performance tests:

```python
def test_function_performance(benchmark):
    """Test function performance with pytest-benchmark."""
    result = benchmark(my_function, arg1, arg2)
    assert result is not None

def test_api_endpoint_performance(benchmark):
    """Benchmark API endpoint response time."""
    def call_api():
        return requests.get("http://localhost:8000/api/data")
    
    response = benchmark(call_api)
    assert response.status_code == 200

@pytest.mark.parametrize("data_size", [100, 1000, 10000])
def test_algorithm_scaling(benchmark, data_size):
    """Test algorithm performance scaling."""
    data = generate_test_data(data_size)
    result = benchmark(process_data, data)
    assert len(result) == data_size
```

## Statistical Analysis

The action performs comprehensive statistical analysis:

### Regression Detection
- **Threshold-based**: Configurable percentage increase threshold
- **Statistical Significance**: Tests for meaningful performance changes
- **Effect Size Classification**: Small (<5%), Medium (5-15%), Large (>15%)
- **Confidence Intervals**: 95% confidence intervals for performance estimates

### Trend Analysis
- **Historical Tracking**: Maintains performance history across runs
- **Trend Direction**: Identifies improving, degrading, or stable trends
- **Linear Regression**: Calculates overall performance trajectory
- **Recent vs Overall**: Compares recent changes to long-term trends

## Integration Examples

### Basic Performance Gate
```yaml
- name: Performance Gate
  uses: ./actions/performance-benchmark
  with:
    suite: 'quick'
    fail-on-regression: 'true'
    regression-threshold: '10.0'
```

### Comprehensive Performance Testing
```yaml
- name: Full Performance Suite
  uses: ./actions/performance-benchmark
  with:
    suite: 'full'
    baseline-branch: 'main'
    store-results: 'true'
    parallel: 'true'
    timeout: '3600'
```

### Load Testing with Custom Config
```yaml
- name: Load Testing
  uses: ./actions/performance-benchmark
  with:
    suite: 'load'
    config-file: 'performance/load-test-config.toml'
    fail-on-regression: 'false'
    results-dir: 'load-test-results'
```

## Package Manager Support

The action automatically detects and supports:

- **pixi**: `pixi run python -m pytest --benchmark-only`
- **poetry**: `poetry run python -m pytest --benchmark-only`
- **hatch**: `hatch run python -m pytest --benchmark-only`
- **pip**: `python -m pytest --benchmark-only`

## Results and Artifacts

### Stored Artifacts
- **benchmark-results-{suite}-{sha}**: Current run results (90 days retention)
- **benchmark-baseline-{branch}**: Baseline results for comparison (365 days retention)

### Result Files
- `benchmark-results.json`: pytest-benchmark output
- `performance-analysis.json`: Statistical analysis results
- `trend-report.html`: Historical trend visualization

## Performance Report Example

The action automatically comments on PRs with performance analysis:

```
## ✅ Performance Benchmarks COMPLETED - QUICK Suite

**Execution Time:** 45.2s
**Benchmarks Executed:** 12

### 📊 Performance Analysis
**Baseline Comparison:** Compared against 12 baseline benchmarks, no significant regression
**Report:** Successfully executed 12 benchmarks without regression
**Trend Analysis:** 8 improving, 3 stable, 1 degrading trends

### 📈 Results Summary
- ✅ 12 benchmarks completed successfully
- 📈 No performance regression detected  
- 🚀 Performance within acceptable thresholds

---
*Generated by Performance Benchmark Action v0.0.1*
```

## Troubleshooting

### Common Issues

**Missing pytest-benchmark dependency:**
```bash
# Add to your project dependencies
pip install pytest-benchmark
# or
poetry add pytest-benchmark --group dev
```

**No benchmarks found:**
- Ensure benchmark tests are named with `test_` prefix
- Use `@pytest.mark.benchmark` marker if needed
- Check that `--benchmark-only` finds your tests

**Timeout errors:**
- Increase `timeout` input for longer benchmark suites
- Use `quick` suite for faster feedback
- Enable `parallel` execution to speed up runs

**Baseline comparison failures:**
- Ensure `fetch-depth: 0` in checkout action
- Verify baseline branch exists and has benchmark data
- Check artifact retention hasn't expired

### Debug Mode

Enable debug output by setting environment variables:

```yaml
env:
  BENCHMARK_DEBUG: 'true'
  BENCHMARK_VERBOSE: 'true'
```

## Integration with CI Framework

This action integrates seamlessly with other CI Framework actions:

```yaml
- name: Quality Gates
  uses: ./actions/quality-gates
  with:
    tier: 'essential'

- name: Performance Benchmarks  
  uses: ./actions/performance-benchmark
  with:
    suite: 'quick'
    
- name: Security Scan
  uses: ./actions/security-scan
  with:
    level: 'standard'
```

## Contributing

See the main [CI Framework documentation](../../README.md) for contribution guidelines.

## License

Part of the CI Framework project. See [LICENSE](../../LICENSE) for details.