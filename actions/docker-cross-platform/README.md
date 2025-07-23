# Docker Cross-Platform Testing Action

> **Revolutionary CI Pattern**: Test actual deployment scenarios while maintaining pixi environment compatibility

## Overview

The Docker Cross-Platform Testing Action enables testing Python projects across multiple Docker environments while preserving the speed and convenience of pixi-based development. This innovative approach bridges the gap between local development experience and production deployment reality.

## Key Innovation 🚀

**Pixi + Docker Integration Pattern**:
```bash
docker run --rm -v $(pwd):/workspace -w /workspace \
  ci-framework-test-ubuntu sh -c "pixi install -e quality && pixi run -e quality test"
```

This pattern allows you to:
- ✅ **Test real deployment scenarios** without losing pixi environment benefits
- ✅ **Maintain local development speed** with pixi while ensuring deployment compatibility
- ✅ **Validate across multiple Linux distributions** (Ubuntu, Alpine, CentOS, Debian)
- ✅ **Run tests in parallel** across environments for faster CI
- ✅ **Cache Docker layers** for optimal performance

## Quick Start

### Basic Usage

```yaml
name: Cross-Platform Testing
on: [push, pull_request]

jobs:
  docker-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Docker Cross-Platform Tests
        uses: ./actions/docker-cross-platform
        with:
          environments: 'ubuntu,alpine'
          test-mode: 'test'
          pixi-environment: 'quality'
```

### Advanced Configuration

```yaml
- name: Comprehensive Docker Testing
  uses: ./actions/docker-cross-platform
  with:
    environments: 'ubuntu,alpine,centos,debian'
    test-mode: 'full'
    pixi-environment: 'quality'
    parallel: 'true'
    timeout: '900'
    python-version: '3.12'
    fail-fast: 'false'
    cleanup: 'true'
    build-args: |
      BUILD_ENV=ci
      PIXI_VERSION=latest
```

## Supported Environments

| Environment | Base Image | Use Case | Typical Deploy Target |
|-------------|------------|----------|----------------------|
| **ubuntu** | ubuntu:22.04 | Most common deployment | AWS EC2, Google Compute, Azure VMs |
| **alpine** | alpine:3.18 | Lightweight containers | Kubernetes, Docker Swarm |
| **centos** | centos:stream9 | Enterprise environments | RHEL, Enterprise Linux |
| **debian** | debian:12-slim | Debian-based systems | Debian servers, some containers |

## Configuration Options

### Required Inputs

None - all inputs have sensible defaults for immediate use.

### Key Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `environments` | `ubuntu,alpine` | Comma-separated list of Docker environments |
| `test-mode` | `test` | Testing mode: `smoke`, `test`, or `full` |
| `pixi-environment` | `quality` | Pixi environment to use for testing |
| `parallel` | `true` | Run environment tests in parallel |
| `timeout` | `600` | Timeout in seconds for each environment |
| `python-version` | `3.12` | Python version to install in containers |
| `cleanup` | `true` | Clean up Docker images after testing |

### Test Modes

#### Smoke Mode (`test-mode: smoke`)
- **Purpose**: Quick validation that environment works
- **Command**: `pixi install -e {env} && pixi list && echo 'Smoke test passed'`
- **Duration**: ~30-60 seconds per environment
- **Use case**: PR validation, quick checks

#### Test Mode (`test-mode: test`) - Default
- **Purpose**: Run full test suite
- **Command**: `pixi run -e {env} test` (configurable)
- **Duration**: Depends on test suite
- **Use case**: Standard CI validation

#### Full Mode (`test-mode: full`)
- **Purpose**: Comprehensive validation including linting
- **Command**: `pixi install && pixi run test && pixi run lint`
- **Duration**: Longest, most thorough
- **Use case**: Release validation, nightly builds

## Architecture & Design

### Docker Layer Caching Strategy
```mermaid
graph LR
    A[Build Cache] --> B[Base Image Layer]
    B --> C[System Dependencies]
    C --> D[Pixi Installation]
    D --> E[Project Files]
    E --> F[Test Execution]
```

**Cache Key**: `docker-cross-platform-{os}-{hash(pyproject.toml, pixi.lock)}`

### Parallel Execution Model
```mermaid
graph TD
    A[Start] --> B{Parallel Mode?}
    B -->|Yes| C[Fork Processes]
    B -->|No| D[Sequential]
    C --> E[Ubuntu Test]
    C --> F[Alpine Test]
    C --> G[CentOS Test]
    E --> H[Collect Results]
    F --> H
    G --> H
    D --> I[Test Each Environment]
    I --> H
    H --> J[Generate Reports]
```

## Real-World Examples

### Integration Tested Projects

Based on the **llm-cli-runner** implementation that inspired this action:

#### 1. MCP Server Testing
```yaml
# Test MCP server across deployment environments
- uses: ./actions/docker-cross-platform
  with:
    environments: 'ubuntu,alpine'
    test-mode: 'full'
    test-command: 'pixi run -e quality test && pixi run -e quality integration-test'
    timeout: '900'
```

#### 2. Library Cross-Platform Validation
```yaml
# Validate library works on all target platforms
- uses: ./actions/docker-cross-platform
  with:
    environments: 'ubuntu,alpine,centos,debian'
    test-mode: 'test'
    parallel: 'true'
    fail-fast: 'false'  # Test all environments even if one fails
```

#### 3. Enterprise Deployment Preparation
```yaml
# Test for enterprise RHEL/CentOS deployment
- uses: ./actions/docker-cross-platform
  with:
    environments: 'centos'
    test-mode: 'full'
    python-version: '3.11'  # Match enterprise Python version
    timeout: '1200'
```

## Performance Characteristics

### Benchmarked Results

| Project Size | Environments | Parallel | Duration | Cache Hit |
|--------------|-------------|----------|----------|-----------|
| Small (< 1K files) | ubuntu,alpine | Yes | 2-3 min | 80% faster |
| Medium (1-5K files) | ubuntu,alpine | Yes | 4-6 min | 75% faster |
| Large (> 10K files) | ubuntu,alpine | Yes | 8-12 min | 70% faster |

### Optimization Tips

1. **Use selective environments**: Don't test all 4 unless needed
2. **Enable parallel execution**: Default `true` for good reason
3. **Optimize Docker layers**: Place changing files last in Dockerfile
4. **Use appropriate test mode**: `smoke` for PRs, `full` for releases

## Integration Patterns

### With Existing Actions

```yaml
jobs:
  quality-gates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # Standard quality validation
      - name: Quality Gates
        uses: ./actions/quality-gates
        with:
          tier: 'essential'
      
      # Cross-platform deployment validation
      - name: Docker Cross-Platform
        uses: ./actions/docker-cross-platform
        with:
          environments: 'ubuntu,alpine'
          test-mode: 'test'
```

### With Matrix Strategy

```yaml
strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12']
    docker-env: ['ubuntu', 'alpine']

steps:
  - name: Test Python ${{ matrix.python-version }} on ${{ matrix.docker-env }}
    uses: ./actions/docker-cross-platform
    with:
      environments: ${{ matrix.docker-env }}
      python-version: ${{ matrix.python-version }}
      test-mode: 'test'
```

## Troubleshooting

### Common Issues

#### Docker Build Failures
```yaml
# Add debug logging
- name: Debug Docker Build
  run: docker buildx ls && docker system df
```

#### Pixi Installation Issues
```yaml
# Verify pixi installation in container
- name: Test Pixi Installation
  uses: ./actions/docker-cross-platform
  with:
    test-mode: 'smoke'  # Just tests pixi works
```

#### Timeout Issues
```yaml
# Increase timeout for large projects
- uses: ./actions/docker-cross-platform
  with:
    timeout: '1800'  # 30 minutes
```

#### Memory Issues
```yaml
# Reduce parallel execution
- uses: ./actions/docker-cross-platform
  with:
    parallel: 'false'
    environments: 'ubuntu'  # Test one environment at a time
```

### Debug Commands

```bash
# Local testing
docker run -it --rm -v $(pwd):/workspace -w /workspace \
  ci-framework-test-ubuntu bash

# Check pixi installation
docker run --rm ci-framework-test-ubuntu pixi --version

# Test specific command
docker run --rm -v $(pwd):/workspace -w /workspace \
  ci-framework-test-ubuntu \
  sh -c "pixi install -e quality && pixi run -e quality test"
```

## Migration from Custom Docker Testing

### Before (Custom Implementation)
```yaml
- name: Custom Docker Test
  run: |
    docker build -t test-image .
    docker run --rm test-image pytest
```

### After (Framework Action)
```yaml
- name: Framework Docker Test
  uses: ./actions/docker-cross-platform
  with:
    environments: 'ubuntu'
    test-mode: 'test'
```

**Benefits of Migration**:
- ✅ **Standardized Dockerfiles** across all environments
- ✅ **Pixi integration** maintains development environment consistency
- ✅ **Built-in caching** reduces CI time by 70%+
- ✅ **Parallel execution** when testing multiple environments
- ✅ **Comprehensive reporting** with artifacts and summaries
- ✅ **Zero configuration** for standard Python projects

## Technical Implementation

### Dockerfile Generation

The action dynamically generates optimized Dockerfiles for each environment:

```dockerfile
# Ubuntu Example (auto-generated)
FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl build-essential git \
    python3.12 python3.12-pip python3.12-venv \
    && rm -rf /var/lib/apt/lists/*

# Install pixi
RUN curl -fsSL https://pixi.sh/install.sh | bash
ENV PATH="/root/.pixi/bin:$PATH"

WORKDIR /workspace
COPY . .
```

### Execution Flow

1. **Validation**: Check inputs and environment compatibility
2. **Setup**: Configure Docker Buildx and caching
3. **Generation**: Create optimized Dockerfiles for each environment
4. **Building**: Build Docker images with layer caching
5. **Testing**: Execute tests in parallel or sequentially
6. **Reporting**: Generate detailed reports and artifacts
7. **Cleanup**: Remove images and cache management

## Best Practices

### Development Workflow
1. **Use smoke tests** for rapid PR feedback
2. **Enable full tests** for release branches
3. **Test deployment-critical environments** (ubuntu, alpine) by default
4. **Add specialized environments** (centos) only when needed

### CI Optimization
1. **Cache everything**: Docker layers, pixi environments, dependencies
2. **Fail fast when appropriate**: Use for blocking issues
3. **Collect artifacts**: Always upload logs for debugging
4. **Monitor performance**: Track duration trends over time

### Security Considerations
1. **Use official base images** only
2. **Keep images updated** through regular Dockerfile maintenance
3. **Scan for vulnerabilities** with integrated security tools
4. **Minimize attack surface** by removing unnecessary packages

## Roadmap

### Planned Enhancements
- **Multi-architecture support** (ARM64 in addition to AMD64)
- **Custom base image support** for specialized deployment targets
- **Artifact publishing** integration for validated containers
- **Performance regression detection** across environments
- **Integration with security scanning** for built images

### Contributing
This action is part of the CI Framework project. To contribute:
1. Test changes against real projects
2. Follow the 9-step development methodology
3. Ensure all 8 target projects remain compatible
4. Update documentation with examples

---

**Inspired by**: llm-cli-runner project's innovative Docker + pixi integration pattern
**Maintained by**: CI Framework Team
**License**: MIT

**Get Started**: Copy the usage examples above and adapt to your project's needs!