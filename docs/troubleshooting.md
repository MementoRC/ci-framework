# 🛠️ Troubleshooting Guide - CI Framework

> Quick solutions to common CI issues and optimization tips

## 🚨 Emergency Fixes

### 🔥 CI is Failing Right Now

#### Quick Diagnosis
```bash
# Check what's failing
gh pr checks  # If you have GitHub CLI
# OR visit: https://github.com/YOUR_USERNAME/YOUR_REPO/actions
```

#### Common Quick Fixes
```bash
# 1. Lint errors - Auto-fix most issues
pixi run lint-fix
pixi run format
git add . && git commit -m "🔧 Fix linting issues"

# 2. Test failures - Run locally first
pixi run test

# 3. Import errors - Install in editable mode
echo 'install-dev = "pip install -e ."' >> pyproject.toml
```

---

## 📋 Common Issues & Solutions

### 1. Package Manager Issues

#### "pixi command not found"

**Symptoms**: CI fails with `pixi: command not found`

**Cause**: Pixi setup action failed or wrong version

**Solution**:
```yaml
# In your workflow file (.github/workflows/ci.yml)
- name: Setup Pixi
  uses: prefix-dev/setup-pixi@v0.8.11  # Use latest version
  with:
    pixi-version: v0.49.0  # Use stable pixi version
```

**Alternative Solution** (Poetry):
```yaml
- name: Setup Poetry
  uses: snok/install-poetry@v1
  with:
    version: latest
    virtualenvs-create: true
```

#### "pixi.lock file not found"

**Symptoms**: Warning about missing lock file

**Solution**:
```bash
# Generate lock file locally
pixi install
git add pixi.lock
git commit -m "Add pixi.lock file"
```

### 2. Import and Module Issues

#### "No module named 'your_module'"

**Symptoms**: Tests fail with import errors

**Cause**: Package not installed in editable mode

**Solution**:
```toml
# Add to pyproject.toml
[tool.pixi.tasks]
install-dev = "pip install -e ."
test = { depends-on = ["install-dev"], cmd = "pytest tests/ -v" }
```

#### "ModuleNotFoundError in tests"

**Symptoms**: Local tests work, CI tests fail

**Solutions**:

1. **Fix PYTHONPATH**:
```toml
[tool.pixi.tasks]
test = "PYTHONPATH=src pytest tests/ -v"
```

2. **Install package in development mode**:
```toml
[tool.pixi.tasks]
install-dev = "pip install -e ."
test = { depends-on = ["install-dev"], cmd = "pytest" }
```

3. **Use src layout**:
```
project/
├── src/
│   └── your_package/
├── tests/
└── pyproject.toml
```

### 3. Test Issues

#### "No tests collected"

**Symptoms**: `collected 0 items`

**Causes & Solutions**:

1. **Wrong test discovery**:
```toml
# Fix pytest configuration
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_functions = ["test_*"]
```

2. **Missing test files**:
```bash
# Create basic test
mkdir -p tests
cat > tests/test_basic.py << EOF
def test_example():
    assert 1 + 1 == 2
EOF
```

#### "Tests pass locally but fail in CI"

**Common Causes**:

1. **Environment differences**:
```yaml
# Add environment debugging to CI
- name: Debug Environment
  run: |
    echo "Python version: $(python --version)"
    echo "Pip version: $(pip --version)"
    pip list
    env | grep -E "(PATH|PYTHON|PIP)"
```

2. **File path issues**:
```python
# Use pathlib for cross-platform paths
from pathlib import Path

# Instead of: "data/file.txt"
data_file = Path(__file__).parent / "data" / "file.txt"
```

3. **Resource limitations**:
```yaml
# Increase timeout
- name: Run Tests
  run: pixi run test
  timeout-minutes: 15  # Default is 6 minutes
```

### 4. Linting and Formatting Issues

#### "Lint errors that auto-fix doesn't solve"

**Solution Strategy**:
```bash
# 1. See what's failing
pixi run lint

# 2. Fix formatting first
pixi run format

# 3. Fix auto-fixable issues
pixi run lint-fix

# 4. Manual fixes for remaining issues
# Common issues:
# - Unused imports: Remove them
# - Line too long: Break into multiple lines
# - Undefined variables: Fix typos or add imports
```

#### "Conflicting lint rules"

**Example Issue**: Black and flake8 disagree on line length

**Solution**:
```toml
# Configure both tools to agree
[tool.ruff]
line-length = 88

[tool.ruff.lint]
ignore = [
    "E501",  # Line too long (handled by formatter)
]
```

### 5. Security Scan Issues

#### "Bandit security warnings"

**Common Issues & Fixes**:

1. **Assert statements in tests**:
```toml
[tool.bandit]
exclude_dirs = ["tests"]
# OR
skips = ["B101"]  # Skip assert_used test
```

2. **Hardcoded passwords (false positives)**:
```python
# Instead of:
password = "test123"  # Bandit flags this

# Use:
password = "test123"  # nosec - test password
# OR
password = get_test_password()
```

#### "Safety/pip-audit vulnerabilities"

**Solution**:
```bash
# 1. See what's vulnerable
pixi run safety-check

# 2. Update vulnerable packages
pixi update

# 3. If update isn't available, add exclusion (carefully!)
# Create .safety-policy.json:
{
  "ignore": {
    "12345": {
      "reason": "False positive - not used in production"
    }
  }
}
```

### 6. Performance Issues

#### "CI is too slow"

**Optimization Strategies**:

1. **Parallel testing**:
```toml
[tool.pixi.dependencies]
pytest-xdist = "*"

[tool.pixi.tasks]
test-fast = "pytest -n auto tests/"
```

2. **Cache dependencies**:
```yaml
- name: Cache Pixi Environment
  uses: actions/cache@v3
  with:
    path: ~/.pixi
    key: pixi-${{ runner.os }}-${{ hashFiles('**/pixi.lock') }}
```

3. **Selective testing**:
```yaml
- name: Run tests conditionally
  run: |
    if [[ "${{ github.event_name }}" == "pull_request" ]]; then
      pixi run test-quick
    else
      pixi run test-full
    fi
```

#### "Matrix jobs taking forever"

**Solutions**:

1. **Reduce matrix size**:
```yaml
# Instead of testing all combinations
strategy:
  matrix:
    python-version: ["3.11"]  # Just one version for PRs
    os: [ubuntu-latest]
```

2. **Fail fast for quick feedback**:
```yaml
strategy:
  fail-fast: true  # Stop other jobs if one fails
  matrix:
    python-version: ["3.10", "3.11", "3.12"]
```

### 7. Platform-Specific Issues

#### "Works on ubuntu, fails on macOS"

**Common Causes**:

1. **Case-sensitive imports**:
```python
# macOS is case-insensitive, Linux isn't
# Fix: Match exact case
from mypackage import MyClass  # Not myclass
```

2. **Path separators**:
```python
# Use pathlib for cross-platform paths
from pathlib import Path
config_path = Path.home() / ".config" / "app"
```

3. **Missing system dependencies**:
```yaml
# Add macOS-specific setup
- name: Install macOS dependencies
  if: runner.os == 'macOS'
  run: |
    brew install your-dependency
```

#### "Windows CI failures"

**Common Issues**:

1. **Long path names**:
```yaml
# Enable long paths on Windows
- name: Enable long paths
  if: runner.os == 'Windows'
  run: |
    git config --system core.longpaths true
```

2. **Line ending issues**:
```bash
# Configure git for consistent line endings
git config --global core.autocrlf false
```

---

## 🔧 Advanced Troubleshooting

### Debugging CI Failures

#### Enable Debug Logging
```yaml
- name: Debug CI Environment
  run: |
    echo "::debug::Python executable: $(which python)"
    echo "::debug::Python version: $(python --version)"
    echo "::debug::Working directory: $(pwd)"
    echo "::debug::Environment variables:"
    env | sort
```

#### SSH into CI Runner (for debugging)
```yaml
# Add this step temporarily for debugging
- name: Setup tmate session
  if: failure()
  uses: mxschmitt/action-tmate@v3
  timeout-minutes: 30
```

### Performance Profiling

#### Profile test execution
```bash
# Add timing to tests
pixi run pytest --durations=10 tests/

# Profile with cProfile
python -m cProfile -s cumulative -m pytest tests/ > profile.txt
```

#### Monitor CI resource usage
```yaml
- name: Monitor resources
  run: |
    echo "Disk usage:"
    df -h
    echo "Memory usage:"
    free -h
    echo "CPU info:"
    nproc
```

---

## 🚀 Optimization Tips

### 1. Dependency Management

```toml
# Optimize dependency resolution
[tool.pixi.project]
channels = ["conda-forge"]  # Fewer channels = faster
platforms = ["linux-64"]   # Only needed platforms

# Pin major versions for stability
[tool.pixi.dependencies]
python = "3.11.*"          # Specific version
pytest = ">=7.0,<8.0"     # Major version range
requests = "*"             # Latest (for non-critical deps)
```

### 2. Test Organization

```python
# tests/conftest.py - Shared fixtures
import pytest

@pytest.fixture(scope="session")
def expensive_setup():
    # Expensive setup once per test session
    return setup_database()

# Use markers for test categories
# pytest.ini
[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests"
]

# Run only fast tests in CI
# pixi run test-fast = "pytest -m 'not slow'"
```

### 3. CI Workflow Optimization

```yaml
# Conditional job execution
jobs:
  quick-feedback:
    runs-on: ubuntu-latest
    steps:
      - name: Quick lint
        run: pixi run lint --select=E9,F63,F7,F82

  comprehensive:
    runs-on: ubuntu-latest
    needs: quick-feedback
    if: github.event_name != 'pull_request' || contains(github.event.pull_request.labels.*.name, 'full-test')
    steps:
      - name: Full test suite
        run: pixi run test-full
```

---

## 📞 Getting Help

### 1. Self-Diagnosis Checklist

- [ ] Does it work locally? (`pixi run test`, `pixi run lint`)
- [ ] Are dependencies up to date? (`pixi update`)
- [ ] Is the workflow file valid YAML?
- [ ] Are secrets/tokens configured correctly?
- [ ] Did you check the full CI logs?

### 2. Gathering Information

When reporting issues, include:

```bash
# System information
echo "OS: $(uname -a)"
echo "Python: $(python --version)"
echo "Pixi: $(pixi --version)"

# Project information
cat pyproject.toml | grep -A 10 "\[tool.pixi"
pixi info

# Error reproduction
pixi run test 2>&1 | tee error.log
```

### 3. Community Resources

- **GitHub Issues**: [CI Framework Issues](https://github.com/MementoRC/ci-framework/issues)
- **Discussions**: [Community Forum](https://github.com/MementoRC/ci-framework/discussions)
- **Pixi Docs**: [Official Documentation](https://pixi.sh/latest/)
- **GitHub Actions**: [Troubleshooting Guide](https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows)

---

**🎯 Quick Reference**: Most CI issues are resolved by ensuring dependencies are correct and tests pass locally first. When in doubt, start with the simplest configuration and build up complexity gradually.