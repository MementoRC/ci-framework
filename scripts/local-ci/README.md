# Local CI Scripts

Drop-in local CI scripts that mirror GitHub Actions functionality for local development and hybrid workflows.

## 🚀 Quick Start

```bash
# One-command setup
./setup-local-ci.sh

# Run essential quality gates
local-ci

# Run on changed packages only
selective-ci --changed-only

# Run extended tier on all packages
monorepo-ci --tier extended
```

## 📦 Scripts Overview

| Script | Purpose | Usage |
|--------|---------|-------|
| `package-detection.py` | Smart package discovery | `python3 package-detection.py` |
| `local-quality-gates.sh` | Tier-based quality validation | `local-quality-gates.sh [TIER]` |
| `selective-ci.sh` | Package-targeted CI execution | `selective-ci.sh [PACKAGES...]` |
| `monorepo-ci.sh` | Multi-package orchestration | `monorepo-ci.sh [OPTIONS]` |
| `setup-local-ci.sh` | One-command installation | `setup-local-ci.sh [OPTIONS]` |
| `common.sh` | Shared utilities | `source common.sh` |

## 🏗️ Installation

### Automatic Setup

```bash
# Full setup with shell integration
./setup-local-ci.sh

# Custom setup options
./setup-local-ci.sh --no-aliases --symlinks
./setup-local-ci.sh --shell-config ~/.zshrc
```

### Manual Setup

```bash
# Add to PATH
export PATH="$(pwd):$PATH"

# Add aliases
alias local-ci='./local-quality-gates.sh'
alias selective-ci='./selective-ci.sh'
alias monorepo-ci='./monorepo-ci.sh'
```

## 🎯 Usage Examples

### Basic Quality Gates

```bash
# Run essential tier (fast, critical checks)
local-ci essential

# Run extended tier (essential + security)
local-ci extended

# Run full tier (comprehensive analysis)
local-ci full

# Target specific package
local-ci --package src/api extended
```

### Selective CI

```bash
# Run on changed packages since origin/main
selective-ci --changed-only

# Run on specific packages
selective-ci src/api src/web

# Run with patterns
selective-ci --include "src/*" --exclude "*/tests"

# Run extended tier with parallel execution
selective-ci --tier extended --parallel
```

### Monorepo Orchestration

```bash
# Run on all packages with intelligent ordering
monorepo-ci

# Run with maximum 4 parallel jobs
monorepo-ci --jobs 4

# Run only on changed packages
monorepo-ci --changed-only --tier extended

# Sequential execution with full reports
monorepo-ci --sequential --tier full --reports
```

## 🏷️ Quality Tiers

### Essential Tier (< 5 minutes)
- **Tests**: Core test suite
- **Lint**: Critical violations (F, E9)
- **Type Check**: Type safety validation
- **Timeout**: 300 seconds

### Extended Tier (< 10 minutes)
- **Essential** + Security scans
- **Security**: Bandit, safety checks
- **Timeout**: 600 seconds

### Full Tier (< 15 minutes)
- **Extended** + Comprehensive analysis
- **Reports**: Coverage, performance, complexity
- **Quality**: Complete analysis pipeline
- **Timeout**: 900 seconds

## 📋 Package Detection

Automatically detects and configures support for:

- **Pixi**: `pyproject.toml` with `[tool.pixi]`
- **Poetry**: `pyproject.toml` with `[tool.poetry]`
- **npm**: `package.json`
- **Pip**: `requirements.txt`, `setup.py`, `setup.cfg`

### Detection Output

```json
{
  "pixi": [
    {
      "name": "my-project",
      "type": "pixi",
      "path": ".",
      "config_file": "pyproject.toml",
      "absolute_path": "/path/to/project",
      "has_tests": true,
      "commands": {
        "test": "pixi run test",
        "lint": "pixi run lint",
        "quality": "pixi run quality"
      }
    }
  ]
}
```

## 🔧 Configuration

### Environment Variables

```bash
# Enable debug output
export DEBUG=1

# Override timeout for all tiers
export LOCAL_CI_TIMEOUT=600

# Disable colored output
export NO_COLOR=1

# Set parallel job limit
export LOCAL_CI_JOBS=4
```

### Command-Line Options

All scripts support common options:

```bash
-v, --verbose     Enable verbose output
-d, --debug       Enable debug output  
-n, --dry-run     Show what would be done
-h, --help        Show help message
```

## 🧪 Testing

### Test Suite Location

```
framework/tests/local-ci/
├── test_package_detection.py
├── test_local_quality_gates.py
├── test_selective_ci.py
├── test_monorepo_ci.py
└── test_integration.py
```

### Running Tests

```bash
# Run local CI tests
pixi run test framework/tests/local-ci/

# Test specific components
python3 -m pytest framework/tests/local-ci/test_package_detection.py -v

# Integration tests
./scripts/local-ci/local-quality-gates.sh --dry-run
./scripts/local-ci/selective-ci.sh --dry-run --all
```

## 🔄 GitHub Actions Parity

Local CI scripts mirror GitHub Actions behavior:

| GitHub Action | Local Script | Parity Level |
|---------------|--------------|--------------|
| Quality Gates | `local-quality-gates.sh` | 100% |
| Selective CI | `selective-ci.sh` | 95% |
| Package Detection | `package-detection.py` | 100% |
| Timeout Handling | All scripts | 100% |
| Exit Codes | All scripts | 100% |
| Environment Variables | All scripts | 95% |

### Command Mapping

```bash
# GitHub Actions workflow
- uses: ./.github/actions/quality-gates
  with:
    tier: essential
    timeout: 300

# Local equivalent
local-ci essential --timeout 300
```

## 🚨 Error Handling

### Exit Codes

- **0**: Success
- **1**: Quality gate failures
- **2**: Configuration/environment error
- **130**: Interrupted by user

### Common Issues

#### Package Not Detected
```bash
# Debug package detection
python3 package-detection.py --debug --root-dir .

# Check for supported configuration files
ls -la pyproject.toml package.json requirements.txt
```

#### Permission Errors
```bash
# Fix script permissions
chmod +x scripts/local-ci/*.sh

# Check directory permissions
ls -la scripts/local-ci/
```

#### Missing Dependencies
```bash
# Install required tools
# For Ubuntu/Debian
sudo apt install jq python3

# For macOS
brew install jq python3

# For pixi users
pixi install
```

## 🔧 Troubleshooting

### Debug Mode

```bash
# Enable debug output
export DEBUG=1
local-ci --debug essential

# Verbose package detection
python3 package-detection.py --debug --root-dir .
```

### Validation

```bash
# Validate environment
./setup-local-ci.sh --validate --no-install

# Test package detection
python3 package-detection.py --root-dir . | jq .

# Test quality gates (dry run)
local-ci --dry-run essential
```

### Performance Issues

```bash
# Reduce parallel jobs
monorepo-ci --jobs 2

# Increase timeout
selective-ci --timeout 900

# Use sequential execution
local-ci --sequential
```

## 🔗 Integration

### CI/CD Integration

```yaml
# .github/workflows/hybrid-ci.yml
name: Hybrid CI
on: [push, pull_request]

jobs:
  local-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Local CI
        run: ./scripts/local-ci/setup-local-ci.sh --no-aliases
      - name: Run Local Quality Gates
        run: local-ci essential
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: local-ci-essential
        name: Local CI Essential
        entry: ./scripts/local-ci/local-quality-gates.sh essential
        language: system
        pass_filenames: false
        always_run: true
```

### VS Code Integration

```json
// .vscode/tasks.json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Local CI: Essential",
      "type": "shell",
      "command": "./scripts/local-ci/local-quality-gates.sh",
      "args": ["essential"],
      "group": "test",
      "presentation": {
        "echo": true,
        "reveal": "always",
        "focus": false,
        "panel": "shared"
      }
    }
  ]
}
```

## 📊 Reporting

### Aggregate Reports

Reports are generated in `artifacts/reports/`:

```
artifacts/reports/
├── monorepo_ci_report_20240120_143022.json
├── quality_gates_report_essential.json
└── selective_ci_summary.json
```

### Report Structure

```json
{
  "timestamp": "2024-01-20T14:30:22Z",
  "tier": "essential",
  "execution": {
    "total_packages": 5,
    "successful_packages": 4,
    "failed_packages": 1,
    "success_rate": 80.0,
    "total_duration": 245
  },
  "packages": [
    {
      "name": "api-service",
      "path": "src/api",
      "type": "pixi",
      "result": 0,
      "duration": 45
    }
  ]
}
```

## 🎯 Best Practices

### Development Workflow

1. **Start with Essential Tier**
   ```bash
   local-ci essential
   ```

2. **Use Change Detection for Speed**
   ```bash
   selective-ci --changed-only
   ```

3. **Run Full Validation Before Push**
   ```bash
   monorepo-ci --tier extended
   ```

4. **Parallel Execution for Large Monorepos**
   ```bash
   monorepo-ci --jobs 8 --tier essential
   ```

### Performance Optimization

- Use `--changed-only` for incremental builds
- Set appropriate `--jobs` limit based on CPU cores
- Use `--fail-fast` for quick feedback
- Cache package detection results where possible

### Error Prevention

- Run `local-ci essential` before committing
- Use pre-commit hooks for automatic validation
- Set up VS Code tasks for one-click validation
- Monitor aggregate reports for trends

## 🔄 Migration Guide

### From Manual Scripts

1. **Replace direct pytest calls**
   ```bash
   # Old
   pytest tests/
   
   # New
   local-ci essential
   ```

2. **Replace manual package iteration**
   ```bash
   # Old
   for dir in src/*/; do cd "$dir" && pytest && cd ..; done
   
   # New
   monorepo-ci --tier essential
   ```

### From GitHub Actions Only

1. **Install local scripts**
   ```bash
   ./setup-local-ci.sh
   ```

2. **Update development workflow**
   ```bash
   # Before push
   local-ci extended
   
   # Quick check
   selective-ci --changed-only
   ```

## 📖 API Reference

### package-detection.py

```python
# Python API
from package_detection import PackageDetector

detector = PackageDetector(root_dir='.')
packages = detector.detect_packages()
```

### Common Shell Functions

```bash
# Source utilities
source scripts/local-ci/common.sh

# Use functions
detect_package_manager "src/api"
execute_package_command "pixi" "test" "/path/to/package"
check_package_manager "poetry"
```

## 🤝 Contributing

### Adding Package Manager Support

1. **Update `package-detection.py`**:
   - Add detection logic in `PACKAGE_CONFIGS`
   - Implement analyzer method
   - Add command mapping

2. **Update `common.sh`**:
   - Add commands in `get_package_manager_commands`
   - Add execution logic in `execute_package_command`

3. **Add tests**:
   - Unit tests for detection
   - Integration tests for execution

### Extending Quality Tiers

1. **Define tier commands** in each script
2. **Update timeout mappings** in `get_tier_timeout`
3. **Add documentation** for new tier
4. **Test with various package types**

## 📄 License

This project is part of the CI Framework and follows the same license terms.

## 🔗 Related Documentation

- [Quality Gates Action](../actions/quality-gates/README.md)
- [CI Framework Guide](../../docs/ci-framework-guide.md)
- [GitHub Actions Templates](../../examples/)
- [Troubleshooting Guide](../../docs/troubleshooting.md)