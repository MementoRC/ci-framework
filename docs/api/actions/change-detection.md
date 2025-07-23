# Change Detection Action API Reference

> **Intelligent CI optimization through file-based change detection and dependency impact analysis**

## Overview

The Change Detection Action provides intelligent CI optimization by analyzing file changes between commits and recommending which CI pipeline components can be safely skipped. It uses sophisticated pattern matching, dependency analysis, and monorepo support to minimize CI execution time while maintaining quality assurance.

## Action Metadata

| Property | Value |
|----------|-------|
| **Name** | `Change Detection and CI Optimization` |
| **Description** | Intelligent CI optimization through file-based change detection and dependency impact analysis |
| **Author** | CI Framework |
| **Version** | v0.0.1 |
| **Icon** | zap |
| **Color** | yellow |

## Usage

```yaml
- uses: ./actions/change-detection
  with:
    detection-level: 'standard'
    enable-test-optimization: 'true'
    enable-job-skipping: 'true'
    monorepo-mode: 'false'
```

## API Reference

### Inputs

#### `detection-level`
- **Description**: Detection level to execute (quick, standard, comprehensive)
- **Required**: No
- **Default**: `'standard'`
- **Type**: String
- **Valid Values**: `quick`, `standard`, `comprehensive`

**Detection Level Characteristics:**
- **Quick**: Basic file pattern matching and simple categorization
- **Standard**: Enhanced analysis with dependency impact assessment
- **Comprehensive**: Full dependency tree analysis and intelligent test targeting

#### `timeout`
- **Description**: Timeout in seconds for change detection analysis
- **Required**: No
- **Default**: `'300'` (5 minutes)
- **Type**: String (numeric)
- **Example**: `'600'` for 10 minutes

#### `project-dir`
- **Description**: Project directory to analyze (default: current directory)
- **Required**: No
- **Default**: `'.'`
- **Type**: String
- **Example**: `'./my-project'`

#### `base-ref`
- **Description**: Base reference for comparison (default: PR base or main)
- **Required**: No
- **Default**: `''` (auto-detect)
- **Type**: String
- **Example**: `'main'`, `'develop'`, `'HEAD~1'`

#### `head-ref`
- **Description**: Head reference for comparison (default: current SHA)
- **Required**: No
- **Default**: `''` (auto-detect)
- **Type**: String
- **Example**: `'feature-branch'`, `'HEAD'`

#### `pattern-config`
- **Description**: Path to custom pattern configuration file
- **Required**: No
- **Default**: `''` (use built-in patterns)
- **Type**: String
- **Example**: `'./change-patterns.toml'`

#### Change Detection Controls

#### `enable-test-optimization`
- **Description**: Enable intelligent test suite optimization
- **Required**: No
- **Default**: `'true'`
- **Type**: String (boolean)
- **Valid Values**: `'true'`, `'false'`

#### `enable-job-skipping`
- **Description**: Enable CI job skipping recommendations
- **Required**: No
- **Default**: `'true'`
- **Type**: String (boolean)
- **Valid Values**: `'true'`, `'false'`

#### `monorepo-mode`
- **Description**: Enable monorepo support with package-specific detection
- **Required**: No
- **Default**: `'false'`
- **Type**: String (boolean)
- **Valid Values**: `'true'`, `'false'`

#### Advanced Options

#### `reports-dir`
- **Description**: Directory to store change detection reports
- **Required**: No
- **Default**: `'change-reports'`
- **Type**: String
- **Example**: `'analysis-output'`

#### `package-manager`
- **Description**: Force specific package manager (pixi, poetry, hatch, pip)
- **Required**: No
- **Default**: `'auto'`
- **Type**: String
- **Valid Values**: `'auto'`, `'pixi'`, `'poetry'`, `'hatch'`, `'pip'`

#### `fail-fast`
- **Description**: Fail immediately on analysis errors
- **Required**: No
- **Default**: `'false'`
- **Type**: String (boolean)
- **Valid Values**: `'true'`, `'false'`

### Outputs

#### Core Outputs

#### `success`
- **Description**: Whether change detection completed successfully
- **Type**: Boolean
- **Example**: `true`

#### `detection-level`
- **Description**: Detection level that was executed
- **Type**: String
- **Example**: `'standard'`

#### `execution-time`
- **Description**: Total analysis execution time in seconds
- **Type**: Number
- **Example**: `87.45`

#### Change Analysis

#### `changed-files`
- **Description**: List of changed files (comma-separated)
- **Type**: String
- **Example**: `'src/core.py,tests/test_core.py,docs/readme.md'`

#### `change-categories`
- **Description**: Detected change categories (docs,source,test,config)
- **Type**: String
- **Example**: `'source,test'`

#### `affected-packages`
- **Description**: Affected packages in monorepo mode (comma-separated)
- **Type**: String
- **Example**: `'core,utils,cli'`

#### CI Optimization Recommendations

#### `skip-tests`
- **Description**: Whether tests can be safely skipped (true/false)
- **Type**: Boolean
- **Example**: `false`

#### `skip-security`
- **Description**: Whether security scans can be safely skipped (true/false)
- **Type**: Boolean
- **Example**: `true`

#### `skip-docs`
- **Description**: Whether documentation builds can be safely skipped (true/false)
- **Type**: Boolean
- **Example**: `false`

#### `skip-lint`
- **Description**: Whether linting can be safely skipped (true/false)
- **Type**: Boolean
- **Example**: `true`

#### Performance Metrics

#### `optimization-score`
- **Description**: Percentage of CI pipeline that can be optimized (0-100)
- **Type**: Number
- **Example**: `65`

#### `time-savings`
- **Description**: Estimated time savings in seconds
- **Type**: Number
- **Example**: `240`

#### `affected-tests`
- **Description**: List of specific tests that should be run (comma-separated)
- **Type**: String
- **Example**: `'tests/test_core.py,tests/test_utils.py'`

#### `dependency-impact`
- **Description**: Number of modules affected by dependency analysis
- **Type**: Number
- **Example**: `7`

#### File Outputs

#### `reports-path`
- **Description**: Path to generated change detection reports
- **Type**: String
- **Example**: `'change-reports'`

#### `failure-reason`
- **Description**: Reason for failure if analysis failed
- **Type**: String
- **Example**: `'Git diff command failed'`

---

## Configuration

### Project Configuration

Configure change detection in `pyproject.toml`:

```toml
[tool.ci-framework.change-detection]
# Default detection level
default_level = "standard"

# File pattern customization
[tool.ci-framework.change-detection.patterns]
docs = ["docs/**", "*.md", "*.rst", "README*"]
source = ["src/**", "**/*.py", "framework/**"]
tests = ["tests/**", "**/test_*.py", "**/*_test.py"]
config = ["*.yml", "*.yaml", "*.toml", "*.json", ".github/**"]
dependencies = ["requirements*.txt", "pyproject.toml", "poetry.lock"]

# Optimization thresholds
[tool.ci-framework.change-detection.optimization]
test_skip_threshold = 0.8    # Skip tests if 80%+ unrelated changes
security_skip_threshold = 0.9  # Skip security if 90%+ docs-only
docs_skip_threshold = 0.7    # Skip docs build if 70%+ non-doc changes

# Monorepo configuration
[tool.ci-framework.change-detection.monorepo]
enabled = false
package_directories = ["packages/*", "apps/*"]
dependency_mapping = {
    "core" = ["utils", "shared"],
    "api" = ["core", "auth"],
    "frontend" = ["shared"]
}
```

### Pattern Configuration File

Create custom change patterns:

```toml
# change-patterns.toml
[patterns]
# Core source files
critical_source = [
    "src/core/**",
    "src/api/**", 
    "src/auth/**"
]

# Non-critical source files
non_critical_source = [
    "src/utils/**",
    "src/helpers/**"
]

# Test files by category
unit_tests = ["tests/unit/**"]
integration_tests = ["tests/integration/**"]
e2e_tests = ["tests/e2e/**"]

# Documentation
user_docs = ["docs/user/**", "README.md"]
dev_docs = ["docs/dev/**", "CONTRIBUTING.md"]

# Infrastructure
ci_config = [".github/workflows/**", ".github/actions/**"]
docker_files = ["Dockerfile*", "docker-compose*.yml"]
```

---

## Usage Examples

### Basic Change Detection

```yaml
name: Optimized CI
on: [push, pull_request]

jobs:
  changes:
    runs-on: ubuntu-latest
    outputs:
      skip-tests: ${{ steps.detection.outputs.skip-tests }}
      skip-security: ${{ steps.detection.outputs.skip-security }}
      skip-docs: ${{ steps.detection.outputs.skip-docs }}
      optimization-score: ${{ steps.detection.outputs.optimization-score }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Required for change detection
      
      - uses: ./actions/change-detection
        id: detection
        with:
          detection-level: 'standard'
          enable-test-optimization: 'true'
          enable-job-skipping: 'true'

  tests:
    needs: changes
    runs-on: ubuntu-latest
    if: needs.changes.outputs.skip-tests != 'true'
    steps:
      - uses: actions/checkout@v4
      - name: Run Tests
        run: pytest

  security:
    needs: changes
    runs-on: ubuntu-latest
    if: needs.changes.outputs.skip-security != 'true'
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/security-scan
        with:
          security-level: 'medium'

  docs:
    needs: changes
    runs-on: ubuntu-latest
    if: needs.changes.outputs.skip-docs != 'true'
    steps:
      - uses: actions/checkout@v4
      - name: Build Documentation
        run: mkdocs build
```

### Advanced Monorepo Detection

```yaml
name: Monorepo CI Optimization
on: [push, pull_request]

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      affected-packages: ${{ steps.detection.outputs.affected-packages }}
      optimization-score: ${{ steps.detection.outputs.optimization-score }}
      affected-tests: ${{ steps.detection.outputs.affected-tests }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - uses: ./actions/change-detection
        id: detection
        with:
          detection-level: 'comprehensive'
          monorepo-mode: 'true'
          pattern-config: './monorepo-patterns.toml'
          enable-test-optimization: 'true'

  package-tests:
    needs: detect-changes
    if: needs.detect-changes.outputs.affected-packages != ''
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: ${{ fromJson(needs.detect-changes.outputs.affected-packages) }}
    steps:
      - uses: actions/checkout@v4
      - name: Test Package - ${{ matrix.package }}
        run: |
          cd packages/${{ matrix.package }}
          pytest
```

### Custom Pattern Configuration

```yaml
name: Custom Change Detection
on: [push, pull_request]

jobs:
  intelligent-ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Detect Changes with Custom Patterns
        uses: ./actions/change-detection
        id: changes
        with:
          detection-level: 'comprehensive'
          pattern-config: './custom-patterns.toml'
          base-ref: ${{ github.event.pull_request.base.sha }}
          head-ref: ${{ github.sha }}
      
      - name: Display Change Analysis
        run: |
          echo "🔍 Change Detection Results:"
          echo "Changed files: ${{ steps.changes.outputs.changed-files }}"
          echo "Categories: ${{ steps.changes.outputs.change-categories }}"
          echo "Optimization score: ${{ steps.changes.outputs.optimization-score }}%"
          echo "Time savings: ${{ steps.changes.outputs.time-savings }}s"
          
          echo ""
          echo "🚀 CI Optimizations:"
          [[ "${{ steps.changes.outputs.skip-tests }}" == "true" ]] && echo "✅ Skip tests"
          [[ "${{ steps.changes.outputs.skip-security }}" == "true" ]] && echo "✅ Skip security"
          [[ "${{ steps.changes.outputs.skip-docs }}" == "true" ]] && echo "✅ Skip docs"
          [[ "${{ steps.changes.outputs.skip-lint }}" == "true" ]] && echo "✅ Skip linting"
```

### Performance-Aware CI Pipeline

```yaml
name: Performance-Optimized CI
on: [push, pull_request]

jobs:
  analyze-changes:
    runs-on: ubuntu-latest
    outputs:
      optimization-score: ${{ steps.changes.outputs.optimization-score }}
      time-savings: ${{ steps.changes.outputs.time-savings }}
      execution-strategy: ${{ steps.strategy.outputs.strategy }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - uses: ./actions/change-detection
        id: changes
        with:
          detection-level: 'comprehensive'
          timeout: '600'
      
      - name: Determine Execution Strategy
        id: strategy
        run: |
          optimization_score=${{ steps.changes.outputs.optimization-score }}
          
          if [[ $optimization_score -gt 70 ]]; then
            echo "strategy=minimal" >> $GITHUB_OUTPUT
          elif [[ $optimization_score -gt 40 ]]; then
            echo "strategy=selective" >> $GITHUB_OUTPUT
          else
            echo "strategy=full" >> $GITHUB_OUTPUT
          fi

  minimal-ci:
    needs: analyze-changes
    if: needs.analyze-changes.outputs.execution-strategy == 'minimal'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Minimal Validation
        run: echo "Running minimal CI (docs-only changes)"

  selective-ci:
    needs: analyze-changes
    if: needs.analyze-changes.outputs.execution-strategy == 'selective'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/quality-gates
        with:
          tier: 'essential'

  full-ci:
    needs: analyze-changes
    if: needs.analyze-changes.outputs.execution-strategy == 'full'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/quality-gates
        with:
          tier: 'full'
      - uses: ./actions/security-scan
        with:
          security-level: 'high'
```

---

## Integration Patterns

### With Quality Gates

```yaml
jobs:
  changes:
    runs-on: ubuntu-latest
    outputs:
      code-changed: ${{ steps.changes.outputs.change-categories contains 'source' }}
      test-changed: ${{ steps.changes.outputs.change-categories contains 'test' }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: ./actions/change-detection
        id: changes

  quality:
    needs: changes
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/quality-gates
        with:
          # Use higher tier if source code changed
          tier: ${{ needs.changes.outputs.code-changed == 'true' && 'extended' || 'essential' }}
```

### With Security Scanning

```yaml
jobs:
  security-analysis:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Analyze Changes
        uses: ./actions/change-detection
        id: changes
        with:
          detection-level: 'standard'
      
      - name: Security Scan
        if: steps.changes.outputs.skip-security != 'true'
        uses: ./actions/security-scan
        with:
          # Higher security level if dependencies changed
          security-level: ${{ contains(steps.changes.outputs.change-categories, 'dependencies') && 'high' || 'medium' }}
```

### With Performance Benchmarks

```yaml
jobs:
  performance-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - uses: ./actions/change-detection
        id: changes
        with:
          pattern-config: './performance-patterns.toml'
      
      - name: Performance Benchmarks
        if: contains(steps.changes.outputs.change-categories, 'performance-critical')
        uses: ./actions/performance-benchmark
        with:
          suite: ${{ contains(steps.changes.outputs.affected-tests, 'benchmark') && 'full' || 'quick' }}
```

---

## Troubleshooting

### Common Issues

#### Git History Requirements
```yaml
# Ensure sufficient git history for change detection
- uses: actions/checkout@v4
  with:
    fetch-depth: 0  # Full history required
    # OR for performance: fetch-depth: 50  # Last 50 commits
```

#### Pattern Matching Issues
```yaml
# Debug pattern matching
- uses: ./actions/change-detection
  with:
    detection-level: 'standard'
  env:
    ACTIONS_STEP_DEBUG: true
```

#### Monorepo Configuration
```toml
# Ensure monorepo patterns are correctly configured
[tool.ci-framework.change-detection.monorepo]
package_directories = [
    "packages/*",      # npm/yarn workspaces
    "apps/*",         # nx monorepo apps
    "services/*"      # microservices
]
```

### Performance Optimization

```yaml
# Optimize for different project sizes
- uses: ./actions/change-detection
  with:
    # Small project
    detection-level: 'quick'
    timeout: '120'
    
    # Large monorepo
    # detection-level: 'comprehensive'
    # timeout: '600'
    # monorepo-mode: 'true'
```

### Debug Information

```yaml
- uses: ./actions/change-detection
  with:
    detection-level: 'standard'
  env:
    ACTIONS_STEP_DEBUG: true
    ACTIONS_RUNNER_DEBUG: true

- name: Debug Change Detection Results
  if: always()
  run: |
    echo "Success: ${{ steps.changes.outputs.success }}"
    echo "Changed files: ${{ steps.changes.outputs.changed-files }}"
    echo "Categories: ${{ steps.changes.outputs.change-categories }}"
    echo "Optimization score: ${{ steps.changes.outputs.optimization-score }}"
    
    if [[ -f "${{ steps.changes.outputs.reports-path }}/change-detection-report.json" ]]; then
      echo "Full report:"
      cat "${{ steps.changes.outputs.reports-path }}/change-detection-report.json"
    fi
```

---

## Change Pattern Categories

### Built-in Pattern Definitions

The action includes intelligent pattern matching for common file types:

```python
DEFAULT_PATTERNS = {
    "docs": [
        "docs/**", "*.md", "*.rst", "*.txt", "README*",
        "CHANGELOG*", "LICENSE*", "CONTRIBUTING*"
    ],
    "source": [
        "src/**", "**/*.py", "**/*.js", "**/*.ts", 
        "framework/**", "lib/**", "**/*.go", "**/*.rs"
    ],
    "tests": [
        "tests/**", "**/test_*.py", "**/*_test.py", 
        "**/*_tests.py", "**/conftest.py", "**/*.test.js"
    ],
    "config": [
        "*.yml", "*.yaml", "*.toml", "*.json", "*.cfg",
        "*.ini", ".github/**", "*.xml"
    ],
    "dependencies": [
        "requirements*.txt", "pyproject.toml", "package.json",
        "Pipfile*", "poetry.lock", "yarn.lock", "go.mod"
    ],
    "ci": [
        ".github/workflows/**", ".github/actions/**",
        "*.yml", "*.yaml", "Jenkinsfile", ".gitlab-ci.yml"
    ],
    "build": [
        "Dockerfile*", "docker-compose*.yml", "Makefile",
        "setup.py", "setup.cfg", "CMakeLists.txt"
    ]
}
```

### Smart Optimization Logic

The action applies intelligent rules to determine safe CI skip conditions:

- **Skip Tests**: When only docs/config changed and no source/dependency changes
- **Skip Security**: When only documentation changes with no dependency updates
- **Skip Docs**: When no documentation files changed
- **Skip Lint**: When only documentation changes detected

---

## Performance Characteristics

### Execution Times by Detection Level

| Project Size | Quick | Standard | Comprehensive |
|--------------|-------|----------|---------------|
| Small (< 1K files) | 5-15s | 10-30s | 20-60s |
| Medium (1K-10K files) | 10-30s | 30s-2min | 1-5min |
| Large (> 10K files) | 30s-1min | 1-3min | 3-10min |

### Resource Usage

- **CPU**: Low to moderate (analysis is primarily I/O bound)
- **Memory**: 100-500MB depending on project size
- **Storage**: 10-100MB for reports and temporary files
- **Network**: Minimal (git operations only)

### Optimization Effectiveness

Typical CI time savings by change type:

| Change Type | Optimization Score | Time Savings |
|-------------|-------------------|--------------|
| Docs-only | 75-90% | 5-15 minutes |
| Config-only | 50-70% | 3-8 minutes |
| Test-only | 25-40% | 2-5 minutes |
| Source changes | 0-20% | 0-2 minutes |

---

## Migration Guide

### From Manual Change Detection

```yaml
# Before: Manual file checking
- name: Check for changes
  run: |
    if git diff --name-only HEAD~1 | grep -q "^docs/"; then
      echo "docs_changed=true" >> $GITHUB_OUTPUT
    fi

# After: Framework change detection
- uses: ./actions/change-detection
  id: changes
  with:
    detection-level: 'standard'
```

### From Custom Scripts

```yaml
# Before: Custom change analysis
- name: Analyze changes
  run: ./scripts/check-changes.sh

# After: Framework action with custom patterns
- uses: ./actions/change-detection
  with:
    pattern-config: './custom-patterns.toml'
```

---

**Action Version**: 0.0.1  
**Last Updated**: January 2025  
**Compatibility**: GitHub Actions v4+, Git 2.0+