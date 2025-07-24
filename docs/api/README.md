# CI Framework API Reference

> **Complete API reference for the CI Framework - GitHub Actions, Reusable Workflows, and Configuration Options**

## Overview

The CI Framework provides a comprehensive API consisting of GitHub Actions, reusable workflows, and configuration interfaces designed for systematic CI/CD implementation across Python projects.

## API Categories

### 🔧 [GitHub Actions](actions/)
Self-contained, reusable GitHub Actions for specific CI/CD functionality:
- **[Quality Gates Action](actions/quality-gates.md)** - Tiered quality validation system
- **[Security Scan Action](actions/security-scan.md)** - Multi-tool security analysis
- **[Performance Benchmark Action](actions/performance-benchmark.md)** - Statistical performance monitoring
- **[Docker Cross-Platform Action](actions/docker-cross-platform.md)** - Hybrid container testing
- **[Change Detection Action](actions/change-detection.md)** - Intelligent CI optimization

### 🔄 [Reusable Workflows](workflows/)
Complete CI/CD workflow templates for common scenarios:
- **[Python CI Workflow](workflows/python-ci.md)** - Standard Python project pipeline
- **[Multi-Stage Pipeline](workflows/multi-stage.md)** - Enterprise-grade deployment pipeline
- **[Release Workflow](workflows/release.md)** - Automated release management

### ⚙️ [Configuration Reference](configuration/)
Framework configuration options and customization:
- **[Project Configuration](configuration/project.md)** - pyproject.toml settings
- **[Action Configuration](configuration/actions.md)** - Action-specific options
- **[Environment Variables](configuration/environment.md)** - Runtime configuration

---

## Quick API Reference

### Core Action Usage

```yaml
# Essential quality validation
- uses: ./actions/quality-gates
  with:
    tier: 'essential'
    timeout: '300'

# Security scanning
- uses: ./actions/security-scan
  with:
    security-level: 'medium'
    enable-sarif: 'true'

# Performance monitoring
- uses: ./actions/performance-benchmark
  with:
    suite: 'quick'
    regression-threshold: '10'
```

### Reusable Workflow Integration

```yaml
jobs:
  ci:
    uses: MementoRC/ci-framework/.github/workflows/python-ci.yml@main
    with:
      python-versions: "3.10,3.11,3.12"
      quality-level: "essential"
```

### Configuration Integration

```toml
# pyproject.toml
[tool.ci-framework.quality-gates]
essential_max_time = 300
extended_max_time = 600
full_max_time = 900

[tool.ci-framework.security-scan]
default_level = "medium"
enable_sarif = true
```

---

## API Design Principles

### 1. **Progressive Complexity**
Actions support multiple tiers/levels allowing users to adopt incrementally:
- **Essential**: Basic functionality with minimal setup
- **Extended**: Enhanced features for production use
- **Full/Critical**: Comprehensive validation for enterprise

### 2. **Intelligent Defaults**
All actions work with zero configuration while supporting extensive customization:
- Smart package manager detection (pixi → poetry → pip)
- Automatic environment setup and dependency management
- Sensible timeout and resource limits

### 3. **Composability**
Actions are designed to work together seamlessly:
- Consistent input/output patterns
- Shared configuration standards
- Compatible data formats (SARIF, JSON, artifacts)

### 4. **Observability**
Comprehensive feedback and reporting:
- Detailed GitHub outputs for workflow integration
- Structured logging with performance metrics
- Automatic PR comments with actionable insights
- SARIF integration for security findings

---

## Common Integration Patterns

### Basic Project Setup
```yaml
name: CI
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

### Production Pipeline
```yaml
name: Production CI
on: [push, pull_request]

jobs:
  changes:
    runs-on: ubuntu-latest
    outputs:
      code-changed: ${{ steps.changes.outputs.code-changed }}
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/change-detection
        id: changes

  quality:
    needs: changes
    if: needs.changes.outputs.code-changed == 'true'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        tier: [essential, extended]
    steps:
      - uses: actions/checkout@v4  
      - uses: ./actions/quality-gates
        with:
          tier: ${{ matrix.tier }}

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/security-scan
        with:
          security-level: 'high'
          enable-sarif: 'true'

  performance:
    needs: [quality]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/performance-benchmark
        with:
          suite: 'full'
          store-results: 'true'
```

### Enterprise Deployment
```yaml
name: Enterprise CI/CD
on:
  push:
    branches: [main, develop]
  pull_request:

jobs:
  pipeline:
    uses: ./.github/workflows/multi-stage-pipeline.yml
    with:
      environments: "dev,staging,prod"
      quality-gates: "essential,extended,full"
      security-levels: "medium,high,critical"
      enable-compliance: "true"
    secrets:
      ENTERPRISE_TOKEN: ${{ secrets.ENTERPRISE_TOKEN }}
```

---

## Action Input/Output Standards

### Standard Input Parameters

All actions support these common inputs:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `timeout` | string | varies | Maximum execution time in seconds |
| `project-dir` | string | `'.'` | Project directory to analyze |
| `config-file` | string | `''` | Path to custom configuration file |
| `reports-dir` | string | varies | Directory for generated reports |
| `package-manager` | string | `'auto'` | Force specific package manager |
| `parallel` | boolean | varies | Enable parallel execution when supported |
| `fail-fast` | boolean | `true` | Stop on first critical issue |

### Standard Output Parameters

All actions provide these common outputs:

| Output | Type | Description |
|--------|------|-------------|
| `success` | boolean | Whether the action completed successfully |
| `execution-time` | number | Total execution time in seconds |
| `reports-path` | string | Path to generated reports directory |
| `failure-reason` | string | Primary reason for failure (if any) |

### Action-Specific Parameters

Each action provides specialized inputs and outputs documented in their individual API references:

- **[Quality Gates API](actions/quality-gates.md#api-reference)**
- **[Security Scan API](actions/security-scan.md#api-reference)**
- **[Performance Benchmark API](actions/performance-benchmark.md#api-reference)**
- **[Docker Cross-Platform API](actions/docker-cross-platform.md#api-reference)**
- **[Change Detection API](actions/change-detection.md#api-reference)**

---

## Error Handling & Debugging

### Standard Error Patterns

All actions follow consistent error handling:

```yaml
- uses: ./actions/quality-gates
  id: quality
  continue-on-error: true

- name: Handle Quality Gate Failure
  if: steps.quality.outputs.success != 'true'
  run: |
    echo "Quality gates failed: ${{ steps.quality.outputs.failure-reason }}"
    echo "Failed checks: ${{ steps.quality.outputs.failed-checks }}"
```

### Debug Mode

Enable detailed logging for any action:

```yaml
- uses: ./actions/quality-gates
  with:
    tier: 'essential'
  env:
    ACTIONS_STEP_DEBUG: true
    ACTIONS_RUNNER_DEBUG: true
```

### Timeout Configuration

Adjust timeouts based on project size:

```yaml
# Small project (< 1000 files)
- uses: ./actions/quality-gates
  with:
    timeout: '300'  # 5 minutes

# Large project (> 10000 files)  
- uses: ./actions/quality-gates
  with:
    timeout: '1800'  # 30 minutes
```

---

## Version Compatibility

### Action Versioning

Actions follow semantic versioning with tagged releases:

```yaml
# Latest stable release (recommended)
- uses: MementoRC/ci-framework/actions/quality-gates@v1

# Specific version
- uses: MementoRC/ci-framework/actions/quality-gates@v1.2.3

# Development version (not recommended for production)
- uses: MementoRC/ci-framework/actions/quality-gates@main
```

### Compatibility Matrix

| Framework Version | GitHub Actions | Python Versions | Package Managers |
|------------------|----------------|------------------|------------------|
| v1.0.x | v4+ | 3.10, 3.11, 3.12 | pixi, poetry, hatch, pip |
| v0.9.x | v3+ | 3.9, 3.10, 3.11 | poetry, pip |

---

## Performance Characteristics

### Execution Time Benchmarks

Typical execution times by project size:

| Action | Small Project | Medium Project | Large Project |
|--------|---------------|----------------|---------------|
| Quality Gates (essential) | 30-60s | 2-3min | 5-8min |
| Security Scan (medium) | 1-2min | 3-5min | 8-12min |
| Performance Benchmark | 1-3min | 5-10min | 15-25min |
| Docker Cross-Platform | 2-5min | 8-15min | 20-35min |
| Change Detection | 5-15s | 15-30s | 30-60s |

### Resource Usage

- **CPU**: Actions designed for 2-core runners (scale to 4+ cores)
- **Memory**: 2-4GB typical usage (up to 8GB for large projects)
- **Storage**: 1-5GB for artifacts and caches
- **Network**: Minimal external dependencies (package downloads only)

---

## Migration Guide

### From Generic Actions

Replace common actions with framework equivalents:

```yaml
# Before: Generic testing
- name: Run tests
  run: pytest

# After: Framework quality gates
- uses: ./actions/quality-gates
  with:
    tier: 'essential'
```

### From Custom Scripts

Convert custom CI scripts to framework actions:

```yaml
# Before: Custom security script
- name: Security scan
  run: ./scripts/security-check.sh

# After: Framework security action
- uses: ./actions/security-scan
  with:
    security-level: 'medium'
    enable-sarif: 'true'
```

---

## Contributing to the API

### Action Development

Follow established patterns when creating new actions:

1. **Use composite actions** for maximum compatibility
2. **Follow input/output standards** for consistency
3. **Include comprehensive error handling** with clear messages
4. **Provide detailed documentation** with examples
5. **Test across multiple project types** for robustness

### API Enhancement Requests

Submit enhancement requests with:

- **Use case description** and business value
- **Proposed API changes** with backward compatibility plan
- **Implementation approach** with resource estimates
- **Testing strategy** for validation

---

## Support and Resources

### API Documentation
- **[GitHub Actions Documentation](actions/)** - Complete action reference
- **[Workflow Templates](workflows/)** - Reusable workflow patterns
- **[Configuration Guide](configuration/)** - Framework configuration options

### Community Resources
- **[GitHub Discussions](https://github.com/MementoRC/ci-framework/discussions)** - API questions and feedback
- **[Issue Tracker](https://github.com/MementoRC/ci-framework/issues)** - Bug reports and feature requests
- **[Examples Repository](https://github.com/MementoRC/ci-framework-examples)** - Real-world usage examples

---

**API Version**: 1.0.0  
**Last Updated**: January 2025  
**Compatibility**: GitHub Actions v4+, Python 3.10+