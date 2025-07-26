# GitHub Actions API Reference

> **Complete reference for all CI Framework GitHub Actions**

## Available Actions

The CI Framework provides a comprehensive suite of GitHub Actions designed to work together for complete CI/CD coverage.

### Core Quality Actions

#### 1. [Quality Gates Action](quality-gates.md)
**Purpose**: Tiered quality validation with zero-tolerance policy  
**Use case**: Essential for every project - validates tests, linting, and type checking  
**Tiers**: Essential (2-5min), Extended (5-10min), Full (10-15min)

```yaml
- uses: ./actions/quality-gates
  with:
    tier: 'essential'
    fail-fast: 'true'
```

#### 2. [Security Scan Action](security-scan.md)
**Purpose**: Comprehensive security vulnerability detection  
**Use case**: Identify security issues before they reach production  
**Tools**: Bandit, safety, pip-audit, semgrep, Trivy

```yaml
- uses: ./actions/security-scan
  with:
    security-level: 'standard'
    enable-sarif: 'true'
```

### Platform Testing Actions

#### 3. [Docker Cross-Platform Testing Action](docker-cross-platform.md) 🆕
**Purpose**: Test across multiple Docker environments while maintaining pixi compatibility  
**Use case**: Validate deployment scenarios without losing development speed  
**Innovation**: Combines pixi environments with Docker containers

```yaml
- uses: ./actions/docker-cross-platform
  with:
    environments: 'ubuntu,alpine'
    test-mode: 'test'
```

**Key Innovation**: This action bridges the gap between local development (pixi) and production deployment (Docker), enabling:
- ✅ **Real deployment scenario testing** 
- ✅ **Pixi environment consistency**
- ✅ **Multi-platform validation** (Ubuntu, Alpine, CentOS, Debian)
- ✅ **Parallel execution** for faster CI

### Performance & Optimization Actions

#### 4. [Performance Benchmark Action](performance-benchmark.md)
**Purpose**: Automated performance monitoring with regression detection  
**Use case**: Catch performance regressions before they impact users  
**Features**: Statistical analysis, baseline comparison, trend reporting

```yaml
- uses: ./actions/performance-benchmark
  with:
    benchmark-suite: 'quick'
    regression-threshold: '10'
```

#### 5. [Change Detection Action](change-detection.md)
**Purpose**: Intelligent CI optimization through change analysis  
**Use case**: Skip unnecessary CI jobs based on file changes  
**Features**: Smart path detection, dependency mapping, job optimization

```yaml
- uses: ./actions/change-detection
  with:
    patterns: 'src/**/*.py,tests/**/*.py'
    outputs: 'code-changed'
```

## Action Categories

### By Purpose

| Purpose | Actions | Use Case |
|---------|---------|----------|
| **Quality Assurance** | Quality Gates, Security Scan | Every commit, PR validation |
| **Platform Testing** | Docker Cross-Platform | Deployment validation |
| **Performance** | Performance Benchmark | Release validation, regression detection |
| **Optimization** | Change Detection | CI efficiency, resource optimization |

### By Project Phase

| Phase | Essential Actions | Optional Actions |
|-------|------------------|------------------|
| **Development** | Quality Gates (essential) | Change Detection |
| **Pull Request** | Quality Gates (extended), Security Scan | Docker Cross-Platform (smoke) |
| **Release** | All actions | Performance Benchmark (full) |
| **Production** | Security Scan (critical) | Performance monitoring |

## Integration Patterns

### Standard CI Pipeline
```yaml
name: CI
on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # Quick quality validation
      - name: Essential Quality Gates
        uses: ./actions/quality-gates
        with:
          tier: 'essential'
      
      # Security validation
      - name: Security Scan
        uses: ./actions/security-scan
        with:
          security-level: 'standard'

  platform-test:
    runs-on: ubuntu-latest
    needs: quality
    steps:
      - uses: actions/checkout@v4
      
      # Cross-platform deployment validation
      - name: Docker Cross-Platform Test
        uses: ./actions/docker-cross-platform
        with:
          environments: 'ubuntu,alpine'
          test-mode: 'test'
```

### Advanced Enterprise Pipeline
```yaml
name: Enterprise CI
on: 
  push:
    branches: [main, develop]
  pull_request:

jobs:
  change-detection:
    runs-on: ubuntu-latest
    outputs:
      code-changed: ${{ steps.changes.outputs.code-changed }}
      deps-changed: ${{ steps.changes.outputs.deps-changed }}
    steps:
      - uses: actions/checkout@v4
      - name: Detect Changes
        id: changes
        uses: ./actions/change-detection
        with:
          patterns: |
            src/**/*.py
            tests/**/*.py
            pyproject.toml

  quality-gates:
    runs-on: ubuntu-latest
    needs: change-detection
    if: needs.change-detection.outputs.code-changed == 'true'
    strategy:
      matrix:
        tier: [essential, extended, full]
    steps:
      - uses: actions/checkout@v4
      - name: Quality Gates - ${{ matrix.tier }}
        uses: ./actions/quality-gates
        with:
          tier: ${{ matrix.tier }}

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Security Analysis
        uses: ./actions/security-scan
        with:
          security-level: 'critical'
          enable-sarif: 'true'

  cross-platform:
    runs-on: ubuntu-latest
    needs: [quality-gates]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    strategy:
      matrix:
        environment: [ubuntu, alpine, centos]
    steps:
      - uses: actions/checkout@v4
      - name: Test on ${{ matrix.environment }}
        uses: ./actions/docker-cross-platform
        with:
          environments: ${{ matrix.environment }}
          test-mode: 'full'

  performance:
    runs-on: ubuntu-latest
    needs: [quality-gates, cross-platform]
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Performance Benchmarks
        uses: ./actions/performance-benchmark
        with:
          benchmark-suite: 'full'
          store-baseline: 'true'
```

## Configuration Best Practices

### Action Input Patterns

#### Environment-Specific Configuration
```yaml
# Development environment
- uses: ./actions/quality-gates
  with:
    tier: 'essential'
    timeout: '300'

# Staging environment  
- uses: ./actions/quality-gates
  with:
    tier: 'extended'
    timeout: '600'

# Production environment
- uses: ./actions/quality-gates
  with:
    tier: 'full'
    timeout: '900'
```

#### Matrix Testing Patterns
```yaml
# Cross-platform matrix
strategy:
  matrix:
    include:
      - environment: ubuntu
        test-mode: full
      - environment: alpine  
        test-mode: test
      - environment: centos
        test-mode: smoke

steps:
  - uses: ./actions/docker-cross-platform
    with:
      environments: ${{ matrix.environment }}
      test-mode: ${{ matrix.test-mode }}
```

## Troubleshooting Actions

### Common Issues

#### Action Not Found
```yaml
# ❌ Incorrect path
- uses: actions/quality-gates

# ✅ Correct path
- uses: ./actions/quality-gates
```

#### Missing Dependencies
```yaml
# ✅ Ensure checkout first
steps:
  - uses: actions/checkout@v4  # Required for local actions
  - uses: ./actions/quality-gates
```

#### Timeout Issues
```yaml
# ✅ Increase timeout for large projects
- uses: ./actions/quality-gates
  with:
    timeout: '900'  # 15 minutes
```

### Debug Mode
```yaml
# Enable debug logging for any action
- uses: ./actions/quality-gates
  with:
    tier: 'essential'
  env:
    ACTIONS_STEP_DEBUG: true
    ACTIONS_RUNNER_DEBUG: true
```

## Performance Characteristics

### Execution Times (Typical)

| Action | Small Project | Medium Project | Large Project |
|--------|---------------|----------------|---------------|
| Quality Gates (essential) | 1-2 min | 3-5 min | 5-10 min |
| Security Scan (standard) | 2-3 min | 4-6 min | 8-12 min |
| Docker Cross-Platform | 3-5 min | 6-10 min | 12-20 min |
| Performance Benchmark | 2-4 min | 5-8 min | 10-15 min |
| Change Detection | 10-30 sec | 30-60 sec | 1-2 min |

### Optimization Tips

1. **Use change detection** to skip unnecessary jobs
2. **Choose appropriate tiers** for different environments
3. **Enable parallel execution** where supported
4. **Cache dependencies** with built-in caching
5. **Use selective environments** for Docker testing

## Action Development

### Creating New Actions

Follow the established patterns in `/actions/` directory:

```
actions/
├── my-new-action/
│   ├── action.yml          # Action definition
│   ├── README.md          # Comprehensive documentation
│   └── scripts/           # Action implementation scripts
```

### Testing Actions

```bash
# Test action locally using act
act -j test-action

# Test against real projects
pixi run test-integration
```

### Documentation Standards

Each action must include:
- **Complete README.md** with examples
- **Input/output documentation** with types and defaults
- **Usage examples** for common scenarios
- **Troubleshooting section** with common issues
- **Performance characteristics** and benchmarks

---

## 🚀 New Action Spotlight: Docker Cross-Platform Testing

The latest addition to our action suite represents a major innovation in CI/CD testing. Inspired by the llm-cli-runner project's breakthrough Docker + pixi integration pattern, this action enables:

### Revolutionary Testing Pattern
```bash
# The core innovation
docker run --rm -v $(pwd):/workspace -w /workspace \
  ci-framework-test-ubuntu sh -c "pixi install -e quality && pixi run -e quality test"
```

This pattern allows projects to:
- **Maintain local development speed** with pixi
- **Test actual deployment scenarios** with Docker
- **Validate cross-platform compatibility** without complexity
- **Preserve environment consistency** across dev and production

### Real-World Impact
- **Deployment confidence**: Test exactly how your code will run in production
- **Platform compatibility**: Validate Ubuntu, Alpine, CentOS, and Debian targets
- **Developer experience**: No changes to local development workflow
- **CI efficiency**: Parallel testing with intelligent caching

**Learn more**: [Docker Cross-Platform Testing Action Documentation](docker-cross-platform.md)

---

**Framework Version**: 1.0.0  
**Last Updated**: January 2025  
**Next Release**: Enhanced multi-architecture support, custom base images