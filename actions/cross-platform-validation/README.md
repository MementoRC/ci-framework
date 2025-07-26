# Cross-Platform Validation Action

Advanced cross-platform testing using native GitHub runners with unlocked pixi dependency resolution for comprehensive platform compatibility validation.

## Philosophy

This action implements the superior "unlocked pixi" approach for cross-platform testing:
- **Real platform testing** on actual GitHub runners (not containers)
- **True dependency resolution** with `locked: false` to catch platform-specific issues
- **Dynamic pyproject.toml modification** for each target platform
- **Lightweight execution** without Docker overhead

## Key Advantages Over Docker-Based Testing

✅ **Authentic Platform Testing**: Uses real Ubuntu, Windows, and macOS runners  
✅ **Dependency Resolution Validation**: Tests actual conda-forge package resolution per platform  
✅ **Performance**: No Docker build/pull overhead  
✅ **Accuracy**: Catches platform-specific dependency conflicts that locked mode misses  
✅ **Integration**: Native GitHub Actions ecosystem support  

## Usage

### Basic Cross-Platform Testing

```yaml
name: Cross-Platform Validation
on: [push, pull_request]

jobs:
  cross-platform:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Cross-Platform Validation
        uses: ./actions/cross-platform-validation
        with:
          platforms: ${{ matrix.os }}
          pixi-environments: "quality"
```

### Advanced Multi-Environment Testing

```yaml
name: Comprehensive Platform Matrix
on: [push, pull_request]

jobs:
  cross-platform:
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: ubuntu-latest
            platform: linux-64
          - os: windows-latest 
            platform: win-64
          - os: macos-latest
            platform: osx-64
          - os: macos-13  # Intel Mac
            platform: osx-64
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Validate Platform Compatibility
        uses: ./actions/cross-platform-validation
        with:
          platforms: ${{ matrix.os }}
          pixi-environments: "quality,dev"
          test-commands: |
            pixi run test
            pixi run lint
            pixi run security-scan
          timeout: 20
          fail-fast: false
```

### Custom Platform Matrix

```yaml
- name: Custom Platform Testing
  uses: ./actions/cross-platform-validation
  with:
    platform-matrix: |
      {
        "include": [
          {"os": "ubuntu-latest", "python": "3.11"},
          {"os": "windows-latest", "python": "3.12"},
          {"os": "macos-latest", "python": "3.12"}
        ]
      }
    pixi-environments: "quality,performance"
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `mode` | Testing mode: `native`, `docker`, or `both` | No | `'native'` |
| `platforms` | Platforms to test (comma-separated) | No | `'ubuntu-latest,windows-latest,macos-latest'` |
| `pixi-environments` | Pixi environments to test | No | `'quality'` |
| `test-commands` | Test commands to run (newline-separated) | No | `pixi run test\npixi run lint` |
| `fail-fast` | Stop on first platform failure | No | `'false'` |
| `timeout` | Timeout in minutes per platform | No | `'15'` |
| `pixi-version` | Pixi version to use | No | `'v0.15.1'` |
| `cache` | Enable pixi caching | No | `'false'` |
| `platform-matrix` | Custom platform matrix JSON | No | `''` |
| `pre-test-setup` | Commands before testing | No | `''` |
| `post-test-cleanup` | Commands after testing | No | `''` |
| `reports-dir` | Directory for reports | No | `'cross-platform-reports'` |
| `backup-original` | Backup original pyproject.toml | No | `'true'` |

## Outputs

| Output | Description |
|--------|-------------|
| `platforms-tested` | Number of platforms successfully tested |
| `test-results` | JSON object with test results per platform |
| `total-duration` | Total duration of all platform tests in seconds |
| `artifacts-path` | Path to generated test artifacts and reports |
| `dependency-resolution-results` | Results of dependency resolution per platform |

## Platform Mapping

The action automatically maps GitHub runner platforms to pixi platforms:

| GitHub Runner | Pixi Platform |
|---------------|---------------|
| `ubuntu-latest` | `linux-64` |
| `windows-latest` | `win-64` |
| `macos-latest` | `osx-64` |
| `macos-13` | `osx-64` (Intel) |
| `macos-14` | `osx-arm64` (Apple Silicon) |

## How It Works

### 1. Platform Detection
- Detects current GitHub runner platform
- Maps to appropriate pixi platform identifier

### 2. Dynamic Configuration
- Backs up original `pyproject.toml`
- Modifies `platforms = ["..."]` for current target platform
- Uses platform-specific commands (PowerShell on Windows, Perl/sed on Unix)

### 3. Dependency Resolution Testing
- Runs `pixi install -e <env> --no-lockfile-update`
- Tests fresh dependency resolution on each platform
- Catches platform-specific conflicts that locked mode misses

### 4. Functional Testing
- Executes user-defined test commands
- Supports multiple pixi environments
- Comprehensive error reporting

### 5. Cleanup and Reporting
- Restores original configuration
- Generates detailed reports per platform
- Uploads artifacts for investigation

## Integration Patterns

### With Change Detection

```yaml
jobs:
  changes:
    runs-on: ubuntu-latest
    outputs:
      python: ${{ steps.changes.outputs.python }}
    steps:
      - uses: ./actions/change-detection
        id: changes

  cross-platform:
    needs: changes
    if: needs.changes.outputs.python == 'true'
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - name: Cross-Platform Validation
        uses: ./actions/cross-platform-validation
```

### With Quality Gates

```yaml
jobs:
  quality-gates:
    runs-on: ubuntu-latest
    steps:
      - uses: ./actions/quality-gates
        
  cross-platform:
    needs: quality-gates
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: ./actions/cross-platform-validation
```

## Best Practices

### 1. **Matrix Strategy**
Use GitHub's matrix strategy for true parallel execution:
```yaml
strategy:
  fail-fast: false  # Test all platforms even if one fails
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
runs-on: ${{ matrix.os }}
```

### 2. **Environment Isolation**
Test multiple pixi environments to ensure broad compatibility:
```yaml
pixi-environments: "default,quality,dev,ci"
```

### 3. **Timeout Management**
Set appropriate timeouts for dependency resolution:
```yaml
timeout: 20  # minutes - dependency resolution can be slow
```

### 4. **Conditional Execution**
Only run when needed:
```yaml
if: needs.changes.outputs.python == 'true' || github.event_name == 'pull_request'
```

### 5. **Artifact Collection**
Always collect reports for debugging:
```yaml
- uses: actions/upload-artifact@v4
  if: always()
  with:
    name: cross-platform-reports-${{ matrix.os }}
    path: cross-platform-reports/
```

## Common Issues and Solutions

### Issue: Platform-Specific Dependencies
```yaml
# Solution: Test with unlocked mode
cache: false
# This forces fresh dependency resolution
```

### Issue: Windows Path Issues
```yaml
# Solution: Use native PowerShell commands
# The action handles Windows-specific path modifications automatically
```

### Issue: Slow Dependency Resolution
```yaml
# Solution: Increase timeout and use selective environments
timeout: 30
pixi-environments: "quality"  # Test only essential environments
```

### Issue: False Positive Lock File Differences
```yaml
# Solution: Use --no-lockfile-update
# The action automatically handles this
```

## Migration from Docker-Based Testing

**Old Docker Approach:**
```yaml
- uses: ./actions/docker-cross-platform
  with:
    environments: "ubuntu,alpine,centos"
```

**New Native Approach:**
```yaml
- uses: ./actions/cross-platform-validation
  with:
    platforms: "ubuntu-latest,windows-latest,macos-latest"
    mode: "native"
```

**Benefits of Migration:**
- ✅ **10x faster** - No Docker build overhead
- ✅ **More accurate** - Real platform testing vs containers
- ✅ **Better error detection** - Unlocked dependency resolution
- ✅ **Simpler maintenance** - No Dockerfile management

## Advanced Configuration

### Testing with Multiple Python Versions
```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
    python-version: ["3.11", "3.12"]
steps:
  - name: Modify Python Version
    run: |
      # Modify pyproject.toml to use matrix python version
      sed -i 's/python = "3\.12\.\*"/python = "${{ matrix.python-version }}.*"/' pyproject.toml
  
  - uses: ./actions/cross-platform-validation
```

### Custom Test Sequences
```yaml
- uses: ./actions/cross-platform-validation
  with:
    test-commands: |
      pixi run install-editable
      pixi run test-unit
      pixi run test-integration
      pixi run benchmark
    pre-test-setup: |
      echo "Setting up test environment..."
      export TEST_ENV=ci
    post-test-cleanup: |
      echo "Cleaning up test artifacts..."
      rm -rf test-outputs/
```

## Performance Characteristics

| Metric | Docker Mode | Native Mode |
|--------|-------------|-------------|
| **Setup Time** | 2-5 minutes | 30-60 seconds |
| **Dependency Resolution** | Locked (cached) | Fresh (real) |
| **Platform Accuracy** | Container simulation | Native platform |
| **Resource Usage** | High (Docker) | Low (native) |
| **Error Detection** | Limited | Comprehensive |
| **Maintenance** | Complex | Simple |

**Recommendation**: Use `mode: native` for all new projects. Docker mode is preserved for legacy container-specific testing scenarios.