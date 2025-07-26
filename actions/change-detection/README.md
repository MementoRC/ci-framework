# Change Detection and CI Optimization Action

Intelligent CI optimization through file-based change detection and dependency impact analysis to achieve 50%+ CI execution time reduction for typical changes.

## Features

- **Smart File Classification**: Automatically categorizes changes into docs, source, tests, config, dependencies
- **Dependency Impact Analysis**: Analyzes which modules and tests are affected by changes
- **CI Job Optimization**: Provides recommendations to skip unnecessary CI jobs
- **Test Suite Optimization**: Identifies specific tests that need to run based on changes
- **Monorepo Support**: Package-specific change detection for monorepo projects
- **Comprehensive Reporting**: Detailed analysis reports with optimization recommendations
- **Integration Ready**: Easy integration with existing GitHub Actions workflows

## Quick Start

```yaml
name: Optimized CI Pipeline
on: [push, pull_request]

jobs:
  change-detection:
    runs-on: ubuntu-latest
    outputs:
      skip-tests: ${{ steps.detect.outputs.skip-tests }}
      skip-security: ${{ steps.detect.outputs.skip-security }}
      skip-docs: ${{ steps.detect.outputs.skip-docs }}
      optimization-score: ${{ steps.detect.outputs.optimization-score }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Required for change detection
      
      - name: Detect Changes
        id: detect
        uses: ./actions/change-detection
        with:
          detection-level: standard
          enable-test-optimization: true
          enable-job-skipping: true

  tests:
    needs: change-detection
    if: needs.change-detection.outputs.skip-tests != 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Tests
        run: pytest

  security:
    needs: change-detection
    if: needs.change-detection.outputs.skip-security != 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Security Scan
        uses: ./actions/security-scan

  docs:
    needs: change-detection
    if: needs.change-detection.outputs.skip-docs != 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Documentation
        run: make docs
```

## Inputs

| Input | Description | Default | Required |
|-------|-------------|---------|----------|
| `detection-level` | Detection level (quick/standard/comprehensive) | `standard` | No |
| `timeout` | Timeout in seconds for analysis | `300` | No |
| `project-dir` | Project directory to analyze | `.` | No |
| `base-ref` | Base reference for comparison | PR base or `HEAD~1` | No |
| `head-ref` | Head reference for comparison | `github.sha` | No |
| `pattern-config` | Path to custom pattern configuration | | No |
| `enable-test-optimization` | Enable test suite optimization | `true` | No |
| `enable-job-skipping` | Enable CI job skipping | `true` | No |
| `monorepo-mode` | Enable monorepo support | `false` | No |
| `reports-dir` | Directory for reports | `change-reports` | No |
| `package-manager` | Force package manager (pixi/poetry/hatch/pip) | `auto` | No |
| `fail-fast` | Fail immediately on errors | `false` | No |

## Outputs

| Output | Description |
|--------|-------------|
| `success` | Whether analysis completed successfully |
| `changed-files` | List of changed files (comma-separated) |
| `change-categories` | Detected categories (docs,source,test,config) |
| `affected-packages` | Affected packages in monorepo mode |
| `skip-tests` | Whether tests can be safely skipped |
| `skip-security` | Whether security scans can be skipped |
| `skip-docs` | Whether doc builds can be skipped |
| `skip-lint` | Whether linting can be skipped |
| `optimization-score` | Percentage of CI that can be optimized (0-100) |
| `time-savings` | Estimated time savings in seconds |
| `affected-tests` | Specific tests that should run |
| `dependency-impact` | Number of modules affected |
| `reports-path` | Path to generated reports |

## Detection Levels

### Quick (< 30s)
- Basic file pattern matching
- Simple change categorization
- Conservative optimization recommendations

### Standard (< 2min)
- File pattern matching with enhanced rules
- Simple dependency analysis
- Test impact analysis
- Balanced optimization recommendations

### Comprehensive (< 5min)
- Full dependency graph analysis
- Advanced test selection algorithms
- Cross-package impact analysis (monorepo)
- Aggressive optimization with safety checks

## Change Categories

The action classifies files into these categories:

- **docs**: Documentation files (*.md, docs/, README)
- **source**: Source code files (src/, *.py, *.js, *.ts)
- **tests**: Test files (tests/, test_*.py, *_test.py)
- **config**: Configuration files (*.yml, *.toml, *.json)
- **dependencies**: Dependency files (requirements.txt, pyproject.toml)
- **ci**: CI/CD files (.github/, *.yml workflows)
- **build**: Build files (Dockerfile, Makefile, setup.py)

## Optimization Logic

The action uses these rules for optimization recommendations:

### Skip Tests
- ✅ Only documentation changes
- ✅ Only configuration changes (non-dependency)
- ❌ Any source code changes
- ❌ Any dependency changes
- ❌ Any test file changes

### Skip Security Scans
- ✅ Only documentation changes
- ✅ Only non-dependency configuration changes
- ❌ Any source code changes
- ❌ Any dependency changes

### Skip Documentation Builds
- ✅ No documentation file changes
- ❌ Any changes to docs/ or *.md files

### Skip Linting
- ✅ Only documentation changes
- ❌ Any source code changes
- ❌ Any configuration changes that affect code style

## Custom Pattern Configuration

Create a `.change-patterns.toml` file to customize file classifications:

```toml
[patterns]
docs = ["docs/**", "*.md", "*.rst", "README*"]
source = ["src/**", "lib/**", "**/*.py"]
tests = ["tests/**", "**/*test*.py"]
config = ["*.toml", "*.yml", "*.json"]
dependencies = ["requirements*.txt", "pyproject.toml"]

[optimization]
# Custom optimization rules
skip_tests_on_docs_only = true
skip_security_on_config_only = false
minimum_optimization_score = 25
```

## Monorepo Support

Enable monorepo mode to get package-specific analysis:

```yaml
- name: Detect Changes
  uses: ./actions/change-detection
  with:
    monorepo-mode: true
    detection-level: comprehensive
```

The action will:
- Detect which packages are affected by changes
- Provide package-specific optimization recommendations
- Support cross-package dependency analysis
- Enable package-specific CI job execution

## Integration Examples

### Conditional Job Execution

```yaml
jobs:
  change-detection:
    runs-on: ubuntu-latest
    outputs:
      skip-tests: ${{ steps.detect.outputs.skip-tests }}
      affected-tests: ${{ steps.detect.outputs.affected-tests }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - id: detect
        uses: ./actions/change-detection

  unit-tests:
    needs: change-detection
    if: needs.change-detection.outputs.skip-tests != 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Specific Tests
        run: |
          if [ -n "${{ needs.change-detection.outputs.affected-tests }}" ]; then
            pytest ${{ needs.change-detection.outputs.affected-tests }}
          else
            pytest
          fi
```

### Matrix Optimization

```yaml
jobs:
  change-detection:
    runs-on: ubuntu-latest
    outputs:
      optimization-score: ${{ steps.detect.outputs.optimization-score }}
      skip-security: ${{ steps.detect.outputs.skip-security }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - id: detect
        uses: ./actions/change-detection

  test-matrix:
    needs: change-detection
    if: needs.change-detection.outputs.skip-tests != 'true'
    strategy:
      matrix:
        python-version: [3.10, 3.11, 3.12]
        # Optimize matrix based on change impact
        exclude:
          - python-version: ${{ needs.change-detection.outputs.optimization-score > 50 && '3.10' || '' }}
          - python-version: ${{ needs.change-detection.outputs.optimization-score > 75 && '3.11' || '' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - run: pytest
```

### Pipeline Optimization Report

```yaml
jobs:
  optimization-report:
    needs: [change-detection, tests, security, docs]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Generate Optimization Report
        run: |
          echo "## CI Pipeline Optimization Report" >> $GITHUB_STEP_SUMMARY
          echo "**Optimization Score:** ${{ needs.change-detection.outputs.optimization-score }}%" >> $GITHUB_STEP_SUMMARY
          echo "**Time Savings:** ${{ needs.change-detection.outputs.time-savings }}s" >> $GITHUB_STEP_SUMMARY
          echo "**Jobs Skipped:** $([ '${{ needs.change-detection.outputs.skip-tests }}' = 'true' ] && echo 'tests ' || echo '')$([ '${{ needs.change-detection.outputs.skip-security }}' = 'true' ] && echo 'security ' || echo '')$([ '${{ needs.change-detection.outputs.skip-docs }}' = 'true' ] && echo 'docs' || echo '')" >> $GITHUB_STEP_SUMMARY
```

## Performance Targets

- **Quick Detection**: < 30 seconds
- **Standard Detection**: < 2 minutes  
- **Comprehensive Detection**: < 5 minutes
- **Time Savings**: 50%+ for typical documentation/config changes
- **Accuracy**: 95%+ precision in change classification

## Troubleshooting

### Common Issues

1. **No changes detected**: Ensure `fetch-depth: 0` in checkout action
2. **Incorrect base ref**: Set explicit `base-ref` for complex workflows
3. **Test optimization not working**: Check test file naming conventions
4. **Monorepo detection failing**: Verify package structure and enable `monorepo-mode`

### Debug Mode

Enable debug logging:

```yaml
- uses: ./actions/change-detection
  with:
    detection-level: standard
  env:
    RUNNER_DEBUG: 1
```

### Reports

The action generates detailed reports in the `reports-dir`:

- `change-detection-report.json`: Complete analysis results
- `change-detection-summary.md`: Human-readable summary
- Uploaded as GitHub Actions artifacts for 30 days

## Safety Features

- **Conservative by default**: Errs on the side of running more CI rather than less
- **Fail-safe**: On analysis errors, runs full CI pipeline
- **Override protection**: Critical changes (dependencies) always trigger full CI
- **Validation**: Cross-checks optimization recommendations before applying

## Contributing

See the main [CI Framework documentation](../../README.md) for contribution guidelines.

## License

Part of the CI Framework project. See [LICENSE](../../LICENSE) for details.