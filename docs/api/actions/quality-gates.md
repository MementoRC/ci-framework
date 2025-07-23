# Quality Gates Action API Reference

> **Comprehensive tiered quality validation for Python projects with zero-tolerance policy**

## Overview

The Quality Gates Action implements a revolutionary 3-tier quality validation system that adapts validation depth to development context. It provides essential quality checks for development velocity, extended validation for integration confidence, and full validation for release readiness.

## Action Metadata

| Property | Value |
|----------|-------|
| **Name** | `Quality Gates Action` |
| **Description** | Comprehensive tiered quality validation for Python projects with zero-tolerance policy |
| **Author** | CI Framework |
| **Version** | v0.0.1 |
| **Icon** | shield |
| **Color** | green |

## Usage

```yaml
- uses: ./actions/quality-gates
  with:
    tier: 'essential'
    timeout: '300'
    parallel: 'true'
    fail-fast: 'true'
```

## API Reference

### Inputs

#### `tier`
- **Description**: Quality tier to execute (essential, extended, full)
- **Required**: No
- **Default**: `'essential'`
- **Type**: String
- **Valid Values**: `essential`, `extended`, `full`

**Tier Characteristics:**
- **Essential (≤5min)**: Critical error detection, fast unit tests, public interface type checking
- **Extended (≤10min)**: Comprehensive linting, integration tests, complete type checking, basic security
- **Full (≤15min)**: Complete test suite, all security levels, performance checks, complexity analysis

#### `timeout`
- **Description**: Timeout in seconds for quality gate execution
- **Required**: No
- **Default**: `'300'` (5 minutes)
- **Type**: String (numeric)
- **Example**: `'600'` for 10 minutes

#### `parallel`
- **Description**: Execute quality checks in parallel
- **Required**: No
- **Default**: `'true'`
- **Type**: String (boolean)
- **Valid Values**: `'true'`, `'false'`

#### `project-dir`
- **Description**: Project directory to validate (default: current directory)
- **Required**: No
- **Default**: `'.'`
- **Type**: String
- **Example**: `'./src/my-project'`

#### `config-file`
- **Description**: Path to custom configuration file
- **Required**: No
- **Default**: `''` (auto-detect)
- **Type**: String
- **Example**: `'./quality-config.toml'`

#### `fail-fast`
- **Description**: Fail immediately on first critical violation
- **Required**: No
- **Default**: `'true'`
- **Type**: String (boolean)
- **Valid Values**: `'true'`, `'false'`

#### `reports-dir`
- **Description**: Directory to store quality reports
- **Required**: No
- **Default**: `'reports'`
- **Type**: String
- **Example**: `'quality-reports'`

#### `package-manager`
- **Description**: Force specific package manager (pixi, poetry, hatch, pip)
- **Required**: No
- **Default**: `'auto'`
- **Type**: String
- **Valid Values**: `'auto'`, `'pixi'`, `'poetry'`, `'hatch'`, `'pip'`

### Outputs

#### `success`
- **Description**: Whether all quality gates passed
- **Type**: Boolean
- **Example**: `true`

#### `tier`
- **Description**: Quality tier that was executed
- **Type**: String
- **Example**: `'essential'`

#### `execution-time`
- **Description**: Total execution time in seconds
- **Type**: Number
- **Example**: `247.35`

#### `failed-checks`
- **Description**: List of failed quality checks (comma-separated)
- **Type**: String
- **Example**: `'lint-critical,type-check'`

#### `successful-checks`
- **Description**: List of successful quality checks (comma-separated)
- **Type**: String
- **Example**: `'unit-tests,lint-style,coverage'`

#### `failure-reason`
- **Description**: Primary reason for failure
- **Type**: String
- **Example**: `'Critical lint violations detected'`

#### `reports-path`
- **Description**: Path to generated quality reports
- **Type**: String
- **Example**: `'reports'`

#### `coverage-percentage`
- **Description**: Test coverage percentage
- **Type**: Number
- **Example**: `94.2`

---

## Configuration

### Project Configuration

Configure quality gates in `pyproject.toml`:

```toml
[tool.ci-framework.quality-gates]
# Tier time budgets
essential_max_time = 300    # 5 minutes
extended_max_time = 600     # 10 minutes
full_max_time = 900         # 15 minutes

# Zero-tolerance violations
zero_tolerance = ["F", "E9", "W292"]

# Custom tier triggers
[tool.ci-framework.quality-gates.triggers]
essential = [
    "docs/**",
    "*.md",
    "minor code changes"
]

extended = [
    "src/**",
    "tests/**",
    "feature branches"
]

full = [
    "main branch",
    "release/*",
    "security fixes"
]
```

### Environment Variables

```bash
# Debug mode
export ACTIONS_STEP_DEBUG=true
export ACTIONS_RUNNER_DEBUG=true

# Quality configuration
export QUALITY_GATES_TIMEOUT=600
export QUALITY_GATES_PARALLEL=true
```

---

## Usage Examples

### Basic Usage

```yaml
name: Quality Check
on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/quality-gates
        with:
          tier: 'essential'
```

### Advanced Configuration

```yaml
name: Comprehensive Quality
on: 
  push:
    branches: [main]
  pull_request:

jobs:
  quality-matrix:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        tier: [essential, extended, full]
        python-version: [3.10, 3.11, 3.12]
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Quality Gates - ${{ matrix.tier }}
        uses: ./actions/quality-gates
        with:
          tier: ${{ matrix.tier }}
          timeout: '900'
          parallel: 'true'
          reports-dir: 'quality-reports-${{ matrix.tier }}'
```

### Production Pipeline

```yaml
name: Production Quality Gates
on:
  push:
    branches: [main]

jobs:
  essential:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/quality-gates
        id: essential
        with:
          tier: 'essential'
          fail-fast: 'true'

  extended:
    needs: essential
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/quality-gates
        id: extended
        with:
          tier: 'extended'
          timeout: '600'

  full:
    needs: [essential, extended]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/quality-gates
        with:
          tier: 'full'
          timeout: '900'
          store-reports: 'true'
```

### Error Handling

```yaml
- uses: ./actions/quality-gates
  id: quality
  continue-on-error: true
  with:
    tier: 'essential'

- name: Handle Quality Failure
  if: steps.quality.outputs.success != 'true'
  run: |
    echo "Quality gates failed: ${{ steps.quality.outputs.failure-reason }}"
    echo "Failed checks: ${{ steps.quality.outputs.failed-checks }}"
    
    # Parse failed checks
    IFS=',' read -ra CHECKS <<< "${{ steps.quality.outputs.failed-checks }}"
    for check in "${CHECKS[@]}"; do
      echo "Failed check: $check"
    done
    
    # Exit with appropriate code
    exit 1
```

---

## Integration Patterns

### With Change Detection

```yaml
jobs:
  changes:
    runs-on: ubuntu-latest
    outputs:
      code-changed: ${{ steps.changes.outputs.code-changed }}
      test-changed: ${{ steps.changes.outputs.test-changed }}
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/change-detection
        id: changes

  quality:
    needs: changes
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/quality-gates
        with:
          tier: ${{ needs.changes.outputs.code-changed == 'true' && 'extended' || 'essential' }}
```

### With Security Scanning

```yaml
jobs:
  quality-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Quality Gates
        uses: ./actions/quality-gates
        id: quality
        with:
          tier: 'extended'
      
      - name: Security Scan
        if: steps.quality.outputs.success == 'true'
        uses: ./actions/security-scan
        with:
          security-level: 'medium'
```

### With Performance Benchmarks

```yaml
jobs:
  quality-performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Quality Gates
        uses: ./actions/quality-gates
        with:
          tier: 'full'
      
      - name: Performance Benchmarks
        uses: ./actions/performance-benchmark
        with:
          suite: 'full'
          baseline-comparison: 'true'
```

---

## Troubleshooting

### Common Issues

#### Quality Gates Timeout
```yaml
# Increase timeout for large projects
- uses: ./actions/quality-gates
  with:
    timeout: '1800'  # 30 minutes
```

#### Package Manager Detection Issues
```yaml
# Force specific package manager
- uses: ./actions/quality-gates
  with:
    package-manager: 'pixi'
```

#### Parallel Execution Problems
```yaml
# Disable parallel execution
- uses: ./actions/quality-gates
  with:
    parallel: 'false'
```

### Debug Information

Enable debug logging:
```yaml
- uses: ./actions/quality-gates
  with:
    tier: 'essential'
  env:
    ACTIONS_STEP_DEBUG: true
    ACTIONS_RUNNER_DEBUG: true
```

View quality reports:
```yaml
- name: Upload Quality Reports
  uses: actions/upload-artifact@v3
  if: always()
  with:
    name: quality-reports
    path: ${{ steps.quality.outputs.reports-path }}
```

### Performance Tuning

Optimize for different project sizes:

```yaml
# Small project (< 1000 files)
- uses: ./actions/quality-gates
  with:
    tier: 'essential'
    timeout: '180'

# Medium project (1000-10000 files)
- uses: ./actions/quality-gates
  with:
    tier: 'extended'
    timeout: '600'
    parallel: 'true'

# Large project (> 10000 files)
- uses: ./actions/quality-gates
  with:
    tier: 'full'
    timeout: '1800'
    parallel: 'true'
```

---

## Quality Checks Included

### Essential Tier
- **Critical Lint**: F, E9 violations (zero-tolerance)
- **Fast Unit Tests**: Core functionality validation (< 30s timeout)
- **Public Type Checking**: Interface contracts validation
- **High-Severity Security**: Critical vulnerability detection

### Extended Tier
- **Comprehensive Lint**: All style and code quality checks
- **Integration Tests**: Cross-module functionality validation
- **Complete Type Checking**: Internal and external type validation
- **Medium-Severity Security**: Broader vulnerability detection
- **Basic Performance**: Regression detection for critical paths

### Full Tier
- **Complete Test Suite**: Unit, integration, property-based tests
- **All Security Levels**: Comprehensive vulnerability analysis
- **Performance Benchmarks**: Statistical analysis with baselines
- **Code Complexity**: Technical debt and maintainability analysis
- **Cross-Platform**: Compatibility testing across environments

---

## Performance Characteristics

### Execution Times

| Project Size | Essential | Extended | Full |
|--------------|-----------|----------|------|
| Small (< 1K files) | 30-90s | 2-4min | 5-8min |
| Medium (1K-10K files) | 1-3min | 4-8min | 10-15min |
| Large (> 10K files) | 3-5min | 8-12min | 15-25min |

### Resource Usage
- **CPU**: 2-4 cores utilized (scales with available resources)
- **Memory**: 1-4GB depending on project size and test suite
- **Storage**: 100MB-1GB for reports and temporary files
- **Cache**: Significant speed improvements with pixi/poetry caching

---

## Migration Guide

### From pytest + flake8
```yaml
# Before
- name: Test
  run: pytest
- name: Lint
  run: flake8

# After
- uses: ./actions/quality-gates
  with:
    tier: 'essential'
```

### From tox
```yaml
# Before
- name: Quality Check
  run: tox -e py,lint,type

# After
- uses: ./actions/quality-gates
  with:
    tier: 'extended'
```

### From pre-commit
Quality gates include and extend pre-commit functionality:
```yaml
# Before
- name: Pre-commit
  run: pre-commit run --all-files

# After (includes pre-commit + more)
- uses: ./actions/quality-gates
  with:
    tier: 'extended'
```

---

**Action Version**: 0.0.1  
**Last Updated**: January 2025  
**Compatibility**: GitHub Actions v4+, Python 3.10+