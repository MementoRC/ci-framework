# 🛠️ Comprehensive Troubleshooting Guide - CI Framework

> **Complete Solutions Repository**: 90%+ coverage of common CI Framework issues with step-by-step solutions, diagnostic tools, and prevention strategies

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

---

## 🎯 Action-Specific Troubleshooting

### Quality Gates Action Issues

#### "Quality gates timeout"
**Symptoms**: Action exceeds timeout limits  
**Cause**: Large codebase or slow environment  

**Solutions**:
```yaml
- name: Quality Gates with Extended Timeout
  uses: ./actions/quality-gates
  with:
    tier: essential
    timeout: 1800  # 30 minutes
    parallel: true
```

#### "Essential tier failures"
**Common Issues**:

1. **F,E9 lint violations**:
```bash
# Emergency fix
pixi run emergency-fix
git add . && git commit -m "🚨 Emergency quality fix"
```

2. **Type checking failures**:
```toml
# Temporary fix - add to pyproject.toml
[tool.mypy]
ignore_missing_imports = true
```

3. **Test failures with quality gates**:
```bash
# Debug specific test failures
pixi run test --lf --tb=short
```

#### "Package manager not detected"
**Solution**:
```yaml
- name: Force Package Manager
  uses: ./actions/quality-gates
  with:
    package-manager: pixi  # or poetry, hatch, pip
```

### Security Scan Action Issues

#### "Bandit false positives"
**Common Solutions**:

1. **Test-related flags**:
```toml
# .bandit configuration
[tool.bandit]
exclude_dirs = ["tests", "test_*"]
skips = ["B101", "B601"]
```

2. **Hardcoded secrets in tests**:
```python
# Use nosec comment for test data
test_password = "password123"  # nosec
```

#### "Safety/pip-audit failures"
**Emergency Response**:
```bash
# 1. Identify vulnerable packages
pixi run safety check --json > vulnerabilities.json

# 2. Create temporary policy file
cat > .safety-policy.json << EOF
{
  "ignore": {
    "VULNERABILITY_ID": {
      "reason": "Temporary ignore - tracking in issue #XXX",
      "expires": "2024-12-31"
    }
  }
}
EOF

# 3. Update dependencies
pixi update
```

#### "Semgrep/Trivy tool failures"
**Solutions**:
```yaml
# Disable problematic tools temporarily
- name: Security Scan (Reduced)
  uses: ./actions/security-scan
  with:
    security-level: medium
    enable-semgrep: false  # If semgrep fails
    enable-trivy: false    # If trivy fails
```

### Performance Benchmark Action Issues

#### "Benchmark failures in CI"
**Common Causes & Solutions**:

1. **Environment variability**:
```yaml
- name: Stable Performance Environment
  uses: ./actions/performance-benchmark
  with:
    suite: quick
    regression-threshold: 25.0  # More lenient in CI
```

2. **Baseline missing**:
```bash
# Generate initial baseline
pixi run pytest --benchmark-only --benchmark-save=baseline
git add .benchmarks/
git commit -m "Add performance baselines"
```

3. **Memory/CPU limitations**:
```yaml
# Reduce benchmark intensity
- name: Lightweight Benchmarks
  uses: ./actions/performance-benchmark
  with:
    suite: quick
    parallel: false
    timeout: 300
```

#### "Statistical regression false positives"
**Solution**:
```toml
# benchmark-config.toml
[performance_benchmark]
regression_threshold = 20.0  # More lenient
significance_level = 0.01    # Higher confidence required
min_rounds = 10              # More stable results
```

### Docker Cross-Platform Action Issues

#### "Docker build failures"
**Common Solutions**:

1. **Missing system dependencies**:
```yaml
# Check Dockerfile generation
- name: Debug Docker Build
  run: |
    cat docker/cross-platform-tests/Dockerfile.ubuntu
    docker build --no-cache -t debug-ubuntu .
```

2. **Pixi installation failures in container**:
```yaml
# Use different pixi installation method
- name: Docker Cross-Platform (Alternative)
  uses: ./actions/docker-cross-platform
  with:
    environments: ubuntu
    test-mode: smoke  # Test pixi installation only
```

3. **Container resource limits**:
```yaml
# Sequential execution
- name: Docker Cross-Platform (Sequential)
  uses: ./actions/docker-cross-platform
  with:
    environments: ubuntu,alpine
    parallel: false
    timeout: 1800
```

#### "Test failures in containers"
**Diagnostic Steps**:
```bash
# Debug container environment
docker run -it --rm ubuntu:22.04 bash
# Then manually run installation steps
```

### Change Detection Action Issues

#### "Incorrect optimization decisions"
**Solutions**:

1. **Conservative mode**:
```yaml
- name: Safe Change Detection
  uses: ./actions/change-detection
  with:
    detection-level: quick
    optimization-strategy: conservative
```

2. **Manual override**:
```yaml
- name: Force Full CI
  if: contains(github.event.pull_request.labels.*.name, 'full-ci')
  run: echo "skip-tests=false" >> $GITHUB_OUTPUT
```

3. **Custom patterns**:
```toml
# .change-patterns.toml
[patterns]
critical = ["src/security/**", "src/auth/**"]

[optimization]
skip_tests_on_docs_only = false  # Always run tests
```

#### "Dependency analysis failures"
**Solutions**:
```yaml
# Fallback to simple detection
- name: Change Detection (Fallback)
  uses: ./actions/change-detection
  with:
    detection-level: quick
    enable-dependency-analysis: false
```

---

## 🔧 Framework Integration Issues

### Multi-Action Workflow Problems

#### "Actions interfering with each other"
**Solution Pattern**:
```yaml
# Proper action sequencing
jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Quality Gates
        uses: ./actions/quality-gates
        with:
          tier: essential
      
      - name: Security Scan (after quality)
        if: success()
        uses: ./actions/security-scan
        with:
          security-level: medium
```

#### "Resource conflicts between actions"
**Solutions**:
```yaml
# Use separate jobs for resource-intensive actions
jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - name: Quality Gates
        uses: ./actions/quality-gates
  
  performance:
    runs-on: ubuntu-latest
    steps:
      - name: Performance Benchmarks
        uses: ./actions/performance-benchmark
  
  security:
    needs: [quality]  # Run after quality
    runs-on: ubuntu-latest
    steps:
      - name: Security Scan
        uses: ./actions/security-scan
```

### Environment and Platform Issues

#### "Cross-platform CI failures"
**Strategy**:
```yaml
# Platform-specific configurations
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    include:
      - os: ubuntu-latest
        timeout: 20
      - os: macos-latest
        timeout: 30
      - os: windows-latest
        timeout: 45
```

#### "Pixi vs other package managers"
**Migration Issues**:
```yaml
# Gradual migration approach
- name: Try Pixi First
  id: pixi
  continue-on-error: true
  run: |
    if [ -f "pixi.toml" ]; then
      pixi run test
    else
      exit 1
    fi

- name: Fallback to Poetry
  if: failure() && steps.pixi.outcome == 'failure'
  run: |
    poetry install
    poetry run pytest
```

---

## 🚨 Emergency Response Procedures

### Critical Production Issues

#### "All CI is broken organization-wide"
**Emergency Protocol**:

1. **Immediate Assessment**:
```bash
# Check framework health
curl -s https://api.github.com/repos/MementoRC/ci-framework/commits/main
gh api repos/MementoRC/ci-framework/actions/runs --paginate
```

2. **Rollback Strategy**:
```yaml
# Pin to last known good version
- name: Emergency Quality Gates
  uses: MementoRC/ci-framework/.github/actions/quality-gates@v1.0.0
```

3. **Bypass Framework**:
```yaml
# Minimal CI bypass
- name: Emergency Basic Checks
  run: |
    python -m pytest tests/ --tb=short
    python -m ruff check . --select=F,E9
```

#### "Security vulnerability in framework"
**Response Steps**:

1. **Immediate mitigation**:
```yaml
# Disable security scanning temporarily
- name: Basic Quality Only
  uses: ./actions/quality-gates
  with:
    tier: essential
# Remove security-scan action temporarily
```

2. **Monitor and update**:
```bash
# Check for framework updates
gh release list --repo MementoRC/ci-framework
```

### Performance Degradation Response

#### "CI taking 10x longer than normal"
**Diagnostic Protocol**:

1. **Resource monitoring**:
```yaml
- name: Monitor CI Performance
  run: |
    echo "Start time: $(date)"
    free -h
    df -h
    nproc
```

2. **Progressive optimization**:
```yaml
# Start with minimal CI
- name: Minimal Quality Check
  uses: ./actions/quality-gates
  with:
    tier: essential
    timeout: 300
    parallel: true

# Skip other actions until performance improves
```

---

## 📊 Diagnostic Tools and Monitoring

### Built-in Diagnostics

#### "Framework Health Check"
```bash
# Run comprehensive diagnostics
pixi run framework-health-check

# Check action versions
grep -r "uses.*ci-framework" .github/workflows/

# Validate configuration
pixi run validate-config
```

#### "Performance Monitoring"
```yaml
# Add performance tracking
- name: Track CI Performance
  run: |
    start_time=$(date +%s)
    # ... CI actions ...
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    echo "CI Duration: ${duration}s" >> $GITHUB_STEP_SUMMARY
```

### External Monitoring

#### "GitHub Actions Insights"
```bash
# Monitor action usage
gh api repos/OWNER/REPO/actions/workflows --paginate | jq '.workflows[].name'

# Check runner performance
gh api repos/OWNER/REPO/actions/runs --paginate | jq '.workflow_runs[] | {name: .name, duration: .run_started_at}'
```

#### "Resource Usage Analysis"
```yaml
- name: Resource Analysis
  run: |
    echo "## Resource Usage Report" >> $GITHUB_STEP_SUMMARY
    echo "**CPU Cores**: $(nproc)" >> $GITHUB_STEP_SUMMARY
    echo "**Memory**: $(free -h | awk '/^Mem:/ {print $2}')" >> $GITHUB_STEP_SUMMARY
    echo "**Disk**: $(df -h / | awk 'NR==2 {print $4}')" >> $GITHUB_STEP_SUMMARY
```

---

## 🛡️ Prevention and Best Practices

### Proactive Issue Prevention

#### "Pre-commit Quality Gates"
```bash
# Install local pre-commit hooks
pixi run install-pre-commit

# Or manual validation script
cat > scripts/pre-commit-check.sh << 'EOF'
#!/bin/bash
set -e
echo "Running pre-commit quality checks..."
pixi run emergency-fix
pixi run test --tb=short
echo "✅ All checks passed!"
EOF
chmod +x scripts/pre-commit-check.sh
```

#### "CI Workflow Validation"
```yaml
# Validate workflow syntax
name: Workflow Validation
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate Actions
        run: |
          # Check action.yml files
          for action in actions/*/action.yml; do
            echo "Validating $action"
            yamllint "$action"
          done
```

### Monitoring and Alerts

#### "Performance Regression Alerts"
```yaml
# Add to CI workflow
- name: Performance Regression Check
  uses: ./actions/performance-benchmark
  with:
    suite: quick
    fail-on-regression: true
    regression-threshold: 15.0

- name: Alert on Regression
  if: failure()
  run: |
    echo "🚨 Performance regression detected!" >> $GITHUB_STEP_SUMMARY
    # Add alert mechanism here
```

#### "Framework Update Notifications"
```yaml
# Weekly framework update check
name: Framework Update Check
on:
  schedule:
    - cron: '0 9 * * 1'  # Monday 9 AM

jobs:
  check-updates:
    runs-on: ubuntu-latest
    steps:
      - name: Check Framework Updates
        run: |
          latest=$(gh api repos/MementoRC/ci-framework/releases/latest --jq .tag_name)
          current=$(grep "uses.*ci-framework" .github/workflows/ci.yml | head -1 | cut -d@ -f2)
          if [ "$latest" != "$current" ]; then
            echo "Framework update available: $current -> $latest"
          fi
```

---

## 📞 Advanced Support and Escalation

### Self-Service Diagnostics

#### "Comprehensive System Check"
```bash
#!/bin/bash
# scripts/diagnose-ci.sh
echo "🔍 CI Framework Diagnostic Report"
echo "=================================="

echo "## Environment"
echo "- OS: $(uname -a)"
echo "- Python: $(python --version 2>&1)"
echo "- Pixi: $(pixi --version 2>&1 || echo 'Not installed')"
echo "- Git: $(git --version)"

echo "## Project Configuration"
echo "- Framework version: $(grep -r "uses.*ci-framework" .github/workflows/ | head -1 || echo 'Not found')"
echo "- Package manager: $([ -f pixi.toml ] && echo 'pixi' || [ -f pyproject.toml ] && echo 'python' || echo 'unknown')"

echo "## Quick Tests"
echo "- Lint check: $(pixi run lint 2>&1 | tail -1 || echo 'Failed')"
echo "- Test discovery: $(pixi run pytest --collect-only -q 2>&1 | tail -1 || echo 'Failed')"

echo "## Common Issues Check"
if [ ! -f pixi.lock ]; then echo "⚠️ Missing pixi.lock file"; fi
if [ ! -d tests ]; then echo "⚠️ No tests directory found"; fi
if grep -q "B101" bandit.log 2>/dev/null; then echo "⚠️ Bandit test issues detected"; fi

echo "Run complete. Check warnings above."
```

#### "Performance Baseline"
```bash
# Establish performance baseline
pixi run pytest --benchmark-only --benchmark-save=baseline-$(date +%Y%m%d)
echo "Baseline saved for performance comparison"
```

### Community Support Channels

#### "Issue Reporting Template"
```markdown
## Bug Report Template

**Framework Version**: [e.g., v1.0.0]
**Action**: [quality-gates/security-scan/performance-benchmark/etc.]
**Environment**: [ubuntu-latest/macos-latest/windows-latest]

### Expected Behavior
[What should happen]

### Actual Behavior
[What actually happens]

### Reproduction Steps
1. [First step]
2. [Second step]
3. [See error]

### Error Logs
```
[Paste relevant error logs here]
```

### System Information
- OS: [e.g., Ubuntu 22.04]
- Python Version: [e.g., 3.11.5]
- Package Manager: [pixi/poetry/pip]

### Additional Context
[Any other relevant information]
```

#### "Support Escalation Path"
1. **Level 1**: Self-diagnosis with this guide
2. **Level 2**: Community discussions and GitHub issues
3. **Level 3**: Framework maintainer support
4. **Level 4**: Enterprise support (if available)

### Enterprise Support Features

#### "Custom Troubleshooting"
```yaml
# Enterprise diagnostic action
- name: Enterprise Diagnostics
  uses: ./actions/enterprise-diagnostics
  with:
    collect-logs: true
    performance-analysis: true
    security-audit: true
    support-ticket: ${{ secrets.SUPPORT_TICKET }}
```

---

## 🎯 Quick Reference Card

### Most Common Issues (90% of cases)

| Issue | Quick Fix | Prevention |
|-------|-----------|------------|
| Import errors | `pixi run install-dev` | Use editable installs |
| Lint failures | `pixi run emergency-fix` | Pre-commit hooks |
| Test failures | Check locally first | Regular local testing |
| Timeout errors | Increase timeout limits | Optimize test performance |
| Platform issues | Use pathlib, avoid hardcoded paths | Cross-platform testing |
| Security false positives | Configure tool exclusions | Proper test organization |
| Performance regressions | Adjust thresholds | Baseline monitoring |
| Docker build failures | Check system dependencies | Use tested base images |

### Emergency Commands
```bash
# One-liner fixes for common issues
pixi run emergency-fix && git add . && git commit -m "🚨 Emergency fix"

# Reset to working state
git checkout HEAD~1 && pixi install && pixi run test

# Bypass framework temporarily
python -m pytest tests/ && python -m ruff check . --select=F,E9
```

### Support Resources
- **Documentation**: [CI Framework Docs](./README.md)
- **Best Practices**: [Best Practices Collection](./best-practices/README.md)
- **Community**: [GitHub Discussions](https://github.com/MementoRC/ci-framework/discussions)
- **Issues**: [GitHub Issues](https://github.com/MementoRC/ci-framework/issues)

---

**🎯 Remember**: Start simple, test locally, and escalate systematically. Most issues have simple solutions when approached methodically.

**Framework Version**: 1.0.0 | **Last Updated**: January 2025 | **Coverage**: 90%+ of common issues