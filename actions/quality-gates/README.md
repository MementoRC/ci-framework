# Quality Gates GitHub Action

A comprehensive, tiered quality validation system for Python projects with zero-tolerance policy for critical violations.

## Usage

### Basic Usage

```yaml
name: Quality Gates
on: [push, pull_request]

jobs:
  quality-gates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Essential Quality Gates
        uses: ./actions/quality-gates
        with:
          tier: essential
```

### Advanced Usage

```yaml
name: Comprehensive Quality Validation
on: [push, pull_request]

jobs:
  essential:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Essential Quality Gates
        uses: ./actions/quality-gates
        with:
          tier: essential
          timeout: 300
          parallel: true
          fail-fast: true
  
  extended:
    runs-on: ubuntu-latest
    needs: essential
    steps:
      - uses: actions/checkout@v4
      
      - name: Extended Quality Gates
        uses: ./actions/quality-gates
        with:
          tier: extended
          timeout: 600
          reports-dir: extended-reports
  
  full:
    runs-on: ubuntu-latest
    needs: extended
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      
      - name: Full Quality Gates
        uses: ./actions/quality-gates
        with:
          tier: full
          timeout: 900
          config-file: .github/quality-gates.toml
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `tier` | Quality tier (essential, extended, full) | No | `essential` |
| `timeout` | Timeout in seconds | No | `300` |
| `parallel` | Execute checks in parallel | No | `true` |
| `project-dir` | Project directory to validate | No | `.` |
| `config-file` | Custom configuration file | No | `''` |
| `fail-fast` | Fail on first critical violation | No | `true` |
| `reports-dir` | Reports output directory | No | `reports` |
| `package-manager` | Force package manager | No | `auto` |

## Outputs

| Output | Description |
|--------|-------------|
| `success` | Whether all quality gates passed |
| `tier` | Quality tier executed |
| `execution-time` | Total execution time |
| `failed-checks` | List of failed checks |
| `successful-checks` | List of successful checks |
| `failure-reason` | Primary failure reason |
| `reports-path` | Path to quality reports |
| `coverage-percentage` | Test coverage percentage |

## Quality Tiers

### Essential (≤5 minutes)
- Unit tests (100% pass rate)
- Critical lint checks (F,E9 violations)
- Type checking

### Extended (≤10 minutes) 
- All essential checks
- Security scanning (Bandit)
- Dependency audit (Safety)
- Code complexity analysis

### Full (≤15 minutes)
- All extended checks
- Complete CI reporting
- Pre-commit hooks
- Build validation

## Configuration

Create `.github/quality-gates.toml`:

```toml
[quality_gates]
timeouts = { test = 120, lint = 60, typecheck = 90 }
thresholds = { coverage = 90, complexity = 10 }

[quality_gates.tools.ruff]
select = ["F", "E9", "W"]
line-length = 88

[quality_gates.tools.mypy]
strict = true
```

## Package Manager Support

- **Pixi**: Primary support with environment isolation
- **Poetry**: Full support with virtual environments  
- **Hatch**: Basic support
- **Pip**: Fallback support

## Platform Support

- ✅ Linux (Primary)
- ✅ macOS
- 🟡 Windows (Basic)

## Examples

### Matrix Testing

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest]
    python-version: ['3.10', '3.11', '3.12']
    tier: [essential, extended]

steps:
  - uses: actions/checkout@v4
  
  - name: Quality Gates - ${{ matrix.tier }}
    uses: ./actions/quality-gates
    with:
      tier: ${{ matrix.tier }}
```

### Conditional Execution

```yaml
- name: Full Quality Gates (Main Branch Only)
  uses: ./actions/quality-gates
  if: github.ref == 'refs/heads/main'
  with:
    tier: full
    timeout: 1200
```

### Custom Reports

```yaml
- name: Quality Gates with Custom Reports
  uses: ./actions/quality-gates
  with:
    tier: extended
    reports-dir: custom-reports
    
- name: Archive Quality Reports
  uses: actions/upload-artifact@v3
  with:
    name: quality-reports-${{ github.sha }}
    path: custom-reports/
```

## Integration with Other Actions

### Security Scanning

```yaml
- name: Quality Gates Security
  uses: ./actions/quality-gates
  with:
    tier: extended
    
- name: Upload Security Results
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: reports/security.sarif
```

### Coverage Reports

```yaml
- name: Quality Gates with Coverage
  uses: ./actions/quality-gates
  with:
    tier: full
    
- name: Upload Coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    file: reports/coverage.xml
```

## Troubleshooting

### Common Issues

**Package Manager Not Detected**
```yaml
- name: Force Package Manager
  uses: ./actions/quality-gates
  with:
    package-manager: pixi
```

**Timeout Issues**
```yaml
- name: Extended Timeout
  uses: ./actions/quality-gates
  with:
    timeout: 1800  # 30 minutes
```

**Environment Setup**
```yaml
- name: Setup Custom Environment
  run: |
    pixi install
    pixi shell-hook | source
    
- name: Quality Gates
  uses: ./actions/quality-gates
```

## Performance

Benchmarked against real projects:
- **hb-strategy-sandbox**: 18K+ files, <5s dry-run
- **cheap-llm**: Medium project, <1s dry-run
- **Parallel speedup**: 1.5x - 3x vs sequential

## License

Part of CI Framework project.