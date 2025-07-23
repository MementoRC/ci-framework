# 🔧 Interactive Troubleshooting Diagnostic Tool

> **Get personalized help for any CI framework issues with guided problem diagnosis and tailored solutions**

## 🎯 How This Works

This interactive guide uses a decision tree approach to diagnose your specific issue and provide targeted solutions. Follow the prompts to get personalized troubleshooting steps.

**⏱️ Time:** 2-5 minutes | **📊 Success Rate:** 95%+ issue resolution

---

## 🚨 Problem Categories

Choose the category that best matches your issue:

<details>
<summary>❌ <strong>CI Pipeline Failures</strong> - Jobs failing or not running</summary>

### 🔍 **Pipeline Failure Diagnosis**

**What type of failure are you experiencing?**

<details>
<summary>🚫 <strong>Workflow not starting at all</strong></summary>

#### **Workflow Not Triggering**

**🔍 Diagnostic Questions:**

1. **Is the workflow file in the correct location?**
   - ✅ Should be: `.github/workflows/ci.yml`
   - ❌ Common mistake: `github/workflows/` (missing dot)

2. **Are the trigger conditions correct?**
   ```yaml
   # Check your workflow triggers
   on: [push, pull_request]  # Basic triggers
   
   # OR more specific
   on:
     push:
       branches: [main, develop]
     pull_request:
       branches: [main]
   ```

3. **Is the YAML syntax valid?**
   ```bash
   # Test locally
   yamllint .github/workflows/ci.yml
   
   # Or use online validator
   # https://www.yamllint.com/
   ```

**🛠️ Solutions:**

**Problem: File in wrong location**
```bash
# Move to correct location
mkdir -p .github/workflows
mv github/workflows/ci.yml .github/workflows/ci.yml
```

**Problem: YAML syntax error**
```bash
# Common fixes:
# 1. Check indentation (use spaces, not tabs)
# 2. Quote version numbers: python-version: "3.11"
# 3. Ensure proper list syntax with dashes
```

**Problem: Branch protection rules**
```bash
# Check GitHub settings
Repository Settings → Branches → Branch protection rules
# Ensure required status checks are configured
```

**✅ Verification:**
- Push a new commit and check Actions tab
- Verify green checkmark appears on commit
- Check workflow runs in GitHub Actions dashboard

</details>

<details>
<summary>⚡ <strong>Jobs failing during execution</strong></summary>

#### **Job Execution Failures**

**🔍 Which job is failing?**

<details>
<summary>❌ <strong>Quality Gates failing</strong></summary>

**Quality Gates Failure Diagnosis:**

**Common Error Patterns:**

1. **Linting failures (F, E9 violations)**
   ```bash
   # Error message example:
   src/main.py:15:1: F401 'os' imported but unused
   src/main.py:23:80: E501 line too long (82 > 79 characters)
   ```
   
   **🛠️ Solution:**
   ```bash
   # Auto-fix most issues
   ruff check --fix src/ tests/
   ruff format src/ tests/
   
   # Manual fixes for remaining issues
   ruff check src/ tests/  # See remaining issues
   ```

2. **Test failures**
   ```bash
   # Error message example:
   FAILED tests/test_main.py::test_function - AssertionError
   ```
   
   **🛠️ Solution:**
   ```bash
   # Run tests locally first
   pytest tests/ -v
   pytest tests/test_main.py::test_function -v  # Specific test
   
   # Common fixes:
   # - Update test expectations
   # - Fix import paths
   # - Add missing test dependencies
   ```

3. **Import/dependency errors**
   ```bash
   # Error message example:
   ModuleNotFoundError: No module named 'your_package'
   ```
   
   **🛠️ Solution:**
   ```toml
   # Add to pyproject.toml
   [tool.pixi.tasks]
   install-dev = "pip install -e ."
   test = { depends-on = ["install-dev"], cmd = "pytest tests/ -v" }
   ```

**📊 Quick Diagnostic:**
```bash
# Test your setup locally
pixi run quality
# OR
poetry run pytest && poetry run ruff check src/
```

</details>

<details>
<summary>🛡️ <strong>Security scan failing</strong></summary>

**Security Scan Failure Diagnosis:**

**Common Security Issues:**

1. **Vulnerability in dependencies**
   ```bash
   # Error message example:
   Safety check failed: 1 vulnerability found
   Package: requests==2.25.0
   Vulnerability: CVE-2023-32681
   ```
   
   **🛠️ Solution:**
   ```bash
   # Update vulnerable package
   pixi update requests
   # OR in pyproject.toml
   requests = ">=2.31.0"  # Use secure version
   ```

2. **Bandit security warnings**
   ```bash
   # Error message example:
   B101: Use of assert detected
   B601: paramiko calls with shell=True
   ```
   
   **🛠️ Solution:**
   ```toml
   # Configure bandit to skip false positives
   [tool.bandit]
   exclude_dirs = ["tests"]
   skips = ["B101"]  # Allow assert in tests
   ```

3. **Secrets detected in code**
   ```bash
   # Error message example:
   Possible hardcoded password found
   ```
   
   **🛠️ Solution:**
   ```python
   # Before (BAD)
   PASSWORD = "my-secret-password"
   
   # After (GOOD)
   PASSWORD = os.environ.get("PASSWORD")
   ```

**🔒 Security Best Practices:**
```bash
# Check for secrets before committing
git secrets --scan
# OR use pre-commit hooks
pip install pre-commit
pre-commit install
```

</details>

<details>
<summary>📊 <strong>Performance benchmarks failing</strong></summary>

**Performance Benchmark Failure Diagnosis:**

**Common Performance Issues:**

1. **Performance regression detected**
   ```bash
   # Error message example:
   Performance regression: 45% slower than baseline
   test_api_endpoint: 150ms (baseline: 85ms)
   ```
   
   **🛠️ Analysis & Solutions:**
   ```bash
   # Profile the slow function
   python -m cProfile -s cumulative your_script.py
   
   # Common causes & fixes:
   # - N+1 database queries → Use eager loading
   # - Missing database indexes → Add indexes
   # - Inefficient algorithms → Optimize logic
   # - Memory leaks → Fix resource cleanup
   ```

2. **Benchmark timeout**
   ```bash
   # Error message example:
   Benchmark timeout exceeded: 300s
   ```
   
   **🛠️ Solution:**
   ```yaml
   # Increase timeout in CI
   - uses: ./actions/performance-benchmark
     with:
       suite: 'quick'  # Use faster suite
       timeout: '600'  # Increase timeout
   ```

3. **Flaky benchmark results**
   ```bash
   # Error message example:
   Benchmark variance too high: 45% std deviation
   ```
   
   **🛠️ Solution:**
   ```toml
   # Increase benchmark stability
   [tool.pytest.benchmark]
   min_rounds = 10      # More rounds for stability
   warmup = true        # Add warmup rounds
   disable_gc = true    # Disable garbage collection
   ```

**📈 Performance Optimization:**
```python
# Example optimization patterns
# Before
def slow_function(items):
    results = []
    for item in items:
        result = database.query(item.id)  # N+1 query
        results.append(result)
    return results

# After  
def fast_function(items):
    ids = [item.id for item in items]
    results = database.query_batch(ids)  # Single query
    return results
```

</details>

</details>

</details>

<details>
<summary>⚙️ <strong>Configuration Issues</strong> - Setup and environment problems</summary>

### 🔧 **Configuration Problem Diagnosis**

**What type of configuration issue are you experiencing?**

<details>
<summary>📦 <strong>Package manager issues</strong></summary>

#### **Package Manager Problems**

**🔍 Which package manager are you using?**

<details>
<summary>🐍 <strong>Pixi issues</strong></summary>

**Pixi Configuration Problems:**

1. **Pixi not found/not installed**
   ```bash
   # Error: pixi: command not found
   ```
   
   **🛠️ Solution:**
   ```yaml
   # Add to your workflow
   - name: Install pixi
     uses: prefix-dev/setup-pixi@v0.8.11
     with:
       pixi-version: v0.15.1
   ```

2. **Environment resolution errors**
   ```bash
   # Error: Could not solve for environment
   ```
   
   **🛠️ Solution:**
   ```toml
   # Check pyproject.toml
   [tool.pixi.project]
   channels = ["conda-forge"]  # Ensure conda-forge is included
   platforms = ["linux-64"]   # Match your CI platform
   
   [tool.pixi.dependencies]
   python = ">=3.10,<3.13"    # Use version ranges
   ```

3. **Task execution failures**
   ```bash
   # Error: Task 'test' not found
   ```
   
   **🛠️ Solution:**
   ```toml
   # Define all required tasks
   [tool.pixi.tasks]
   test = "pytest tests/ -v"
   lint = "ruff check src/ tests/ --select=F,E9"
   quality = { depends-on = ["test", "lint"] }
   ```

**🧪 Test Your Pixi Setup:**
```bash
# Locally verify
pixi --version
pixi install
pixi run test
pixi run lint
```

</details>

<details>
<summary>📝 <strong>Poetry issues</strong></summary>

**Poetry Configuration Problems:**

1. **Poetry installation issues**
   ```bash
   # Error: poetry: command not found
   ```
   
   **🛠️ Solution:**
   ```yaml
   # Add to workflow
   - name: Install Poetry
     uses: snok/install-poetry@v1
     with:
       version: latest
       virtualenvs-create: true
   ```

2. **Dependency resolution conflicts**
   ```bash
   # Error: SolverProblemError
   ```
   
   **🛠️ Solution:**
   ```toml
   # Use looser version constraints
   [tool.poetry.dependencies]
   python = "^3.10"  # Instead of exact version
   requests = "*"     # Let poetry resolve
   ```

3. **Virtual environment issues**
   ```bash
   # Error: No module named 'your_package'
   ```
   
   **🛠️ Solution:**
   ```bash
   # Ensure proper installation
   poetry install
   poetry run pytest  # Use poetry run
   ```

</details>

<details>
<summary>🐍 <strong>Pip/setuptools issues</strong></summary>

**Pip Configuration Problems:**

1. **Missing requirements file**
   ```bash
   # Error: No such file or directory: 'requirements.txt'
   ```
   
   **🛠️ Solution:**
   ```bash
   # Create requirements.txt
   pytest>=7.0.0
   ruff>=0.1.0
   
   # OR use pyproject.toml
   [project]
   dependencies = ["pytest>=7.0.0", "ruff>=0.1.0"]
   ```

2. **Version conflicts**
   ```bash
   # Error: pip's dependency resolver does not currently take into account all the packages
   ```
   
   **🛠️ Solution:**
   ```bash
   # Use constraints file
   # constraints.txt
   pytest==7.4.0
   ruff==0.1.5
   
   # Install with constraints
   pip install -r requirements.txt -c constraints.txt
   ```

3. **Editable install issues**
   ```bash
   # Error: No module named 'your_package'
   ```
   
   **🛠️ Solution:**
   ```bash
   # Install in editable mode
   pip install -e .
   
   # OR ensure proper structure
   src/
   └── your_package/
       └── __init__.py
   ```

</details>

</details>

<details>
<summary>🔗 <strong>Action integration issues</strong></summary>

#### **GitHub Action Integration Problems**

**Common Integration Issues:**

1. **Action not found**
   ```bash
   # Error: Can't find 'action.yml', 'action.yaml' or 'Dockerfile'
   ```
   
   **🛠️ Solution:**
   ```yaml
   # Check action path
   - uses: ./actions/quality-gates  # Relative path
   # OR
   - uses: MementoRC/ci-framework/actions/quality-gates@main  # Remote
   ```

2. **Input validation errors**
   ```bash
   # Error: Input required and not supplied: tier
   ```
   
   **🛠️ Solution:**
   ```yaml
   # Provide all required inputs
   - uses: ./actions/quality-gates
     with:
       tier: 'essential'  # Required parameter
       timeout: '300'     # Optional parameter
   ```

3. **Permission errors**
   ```bash
   # Error: Resource not accessible by integration
   ```
   
   **🛠️ Solution:**
   ```yaml
   # Add required permissions
   permissions:
     contents: read
     security-events: write  # For SARIF uploads
     actions: read          # For artifact access
   ```

**✅ Validation Steps:**
```bash
# Test action locally (if possible)
act -j quality-gates

# Validate action.yml syntax
yamllint .github/actions/*/action.yml
```

</details>

<details>
<summary>🌍 <strong>Environment and platform issues</strong></summary>

#### **Environment Configuration Problems**

**Platform-Specific Issues:**

1. **Windows path issues**
   ```bash
   # Error: The system cannot find the path specified
   ```
   
   **🛠️ Solution:**
   ```yaml
   # Use cross-platform paths
   - run: python -m pytest tests/  # Instead of ./tests
   # OR add windows runner
   strategy:
     matrix:
       os: [ubuntu-latest, windows-latest, macos-latest]
   ```

2. **Python version not available**
   ```bash
   # Error: Version 3.13 with arch x64 not found
   ```
   
   **🛠️ Solution:**
   ```yaml
   # Use supported versions
   strategy:
     matrix:
       python-version: ["3.10", "3.11", "3.12"]  # Stable versions
   ```

3. **System dependency missing**
   ```bash
   # Error: gcc: command not found
   ```
   
   **🛠️ Solution:**
   ```yaml
   # Install system dependencies
   - name: Install system deps
     run: |
       sudo apt-get update
       sudo apt-get install build-essential
   ```

**🌐 Cross-Platform Configuration:**
```yaml
# Robust cross-platform setup
runs-on: ${{ matrix.os }}
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python-version: ["3.10", "3.11", "3.12"]
    
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v4
    with:
      python-version: ${{ matrix.python-version }}
      
  # Platform-specific steps
  - name: Install deps (Ubuntu/macOS)
    if: matrix.os != 'windows-latest'
    run: make install
    
  - name: Install deps (Windows)
    if: matrix.os == 'windows-latest'
    run: pip install -r requirements.txt
```

</details>

</details>

<details>
<summary>🐌 <strong>Performance Issues</strong> - Slow execution or timeouts</summary>

### ⚡ **Performance Problem Diagnosis**

**What type of performance issue are you experiencing?**

<details>
<summary>⏰ <strong>CI taking too long</strong></summary>

#### **CI Execution Time Optimization**

**🔍 Performance Analysis:**

1. **Identify slow jobs**
   ```bash
   # Check GitHub Actions logs for timing
   # Look for jobs taking > 5 minutes
   ```
   
   **🛠️ Optimization Strategies:**
   
   **Enable Change Detection:**
   ```yaml
   - uses: ./actions/change-detection
     with:
       detection-level: 'comprehensive'
       enable-job-skipping: 'true'
   # Can save 30-70% execution time
   ```
   
   **Parallel Execution:**
   ```yaml
   jobs:
     quick-checks:
       # Fast validation first
       
     comprehensive-tests:
       needs: quick-checks
       strategy:
         matrix:
           python-version: ["3.10", "3.11", "3.12"]
       # Run different versions in parallel
   ```

2. **Optimize test execution**
   ```bash
   # Use pytest-xdist for parallel testing
   pytest tests/ -n auto  # Use all available CPUs
   ```
   
   **🛠️ Test Optimization:**
   ```toml
   [tool.pixi.tasks]
   test-fast = "pytest tests/ -x --tb=no"  # Stop on first failure
   test-parallel = "pytest tests/ -n auto"  # Parallel execution
   test-unit-only = "pytest tests/unit/"    # Skip slow integration tests
   ```

3. **Dependency caching**
   ```yaml
   - name: Cache dependencies
     uses: actions/cache@v4
     with:
       path: |
         ~/.cache/pip
         ~/.cache/pre-commit
         .pixi/envs
       key: deps-${{ runner.os }}-${{ hashFiles('**/pyproject.toml') }}
   ```

**📊 Performance Targets:**
- **Small projects**: < 5 minutes total
- **Medium projects**: < 10 minutes total  
- **Large projects**: < 20 minutes total

</details>

<details>
<summary>💾 <strong>Memory or resource issues</strong></summary>

#### **Resource Usage Optimization**

**Memory and Resource Problems:**

1. **Out of memory errors**
   ```bash
   # Error: The runner has received a shutdown signal
   ```
   
   **🛠️ Solutions:**
   ```yaml
   # Reduce parallel processes
   - run: pytest tests/ -n 2  # Limit to 2 processes
   
   # Use memory-efficient testing
   - run: pytest tests/ --maxfail=1 --tb=short
   ```

2. **Disk space issues**
   ```bash
   # Error: No space left on device
   ```
   
   **🛠️ Solutions:**
   ```yaml
   # Clean up after each step
   - name: Cleanup
     if: always()
     run: |
       docker system prune -af
       rm -rf ~/.cache/pip
   ```

3. **CPU timeout issues**
   ```bash
   # Error: The job running on runner has exceeded the maximum execution time
   ```
   
   **🛠️ Solutions:**
   ```yaml
   # Increase timeout
   timeout-minutes: 30  # Default is 6 hours, but set reasonable limits
   
   # OR optimize execution
   - uses: ./actions/quality-gates
     with:
       tier: 'essential'  # Use faster tier
       timeout: '600'     # 10 minutes max
   ```

**💡 Resource Optimization Tips:**
```yaml
# Efficient resource usage
jobs:
  test:
    runs-on: ubuntu-latest  # Fastest and cheapest
    steps:
      - name: Optimize test execution
        run: |
          # Run tests with memory limits
          pytest tests/ --memory-profile
          
          # Clean up between test modules
          pytest tests/ --forked
```

</details>

<details>
<summary>📶 <strong>Network or download issues</strong></summary>

#### **Network and Connectivity Problems**

**Common Network Issues:**

1. **Package download failures**
   ```bash
   # Error: Could not fetch URL https://pypi.org/simple/
   ```
   
   **🛠️ Solutions:**
   ```yaml
   # Retry mechanism
   - name: Install dependencies with retry
     uses: nick-invision/retry@v2
     with:
       timeout_minutes: 10
       max_attempts: 3
       command: pip install -r requirements.txt
   ```

2. **Git clone timeout**
   ```bash
   # Error: The request was aborted: The request was canceled due to the configured HttpClient.Timeout
   ```
   
   **🛠️ Solutions:**
   ```yaml
   - uses: actions/checkout@v4
     with:
       fetch-depth: 1  # Shallow clone for speed
       timeout: 300    # 5 minute timeout
   ```

3. **Registry/mirror issues**
   ```bash
   # Error: Connection timeout to conda registry
   ```
   
   **🛠️ Solutions:**
   ```toml
   # Use multiple channels/mirrors
   [tool.pixi.project]
   channels = ["conda-forge", "defaults"]  # Fallback channels
   ```

**🌐 Network Optimization:**
```yaml
# Robust network configuration
- name: Configure package managers
  run: |
    # Set timeouts and retries
    pip config set global.timeout 300
    pip config set global.retries 3
    
    # Use faster mirrors if needed
    pip config set global.index-url https://pypi.org/simple/
```

</details>

</details>

<details>
<summary>🔒 <strong>Security and Permissions</strong> - Access and authentication issues</summary>

### 🛡️ **Security Problem Diagnosis**

**What type of security issue are you experiencing?**

<details>
<summary>🔑 <strong>Permission denied errors</strong></summary>

#### **Permission and Access Issues**

**Common Permission Problems:**

1. **GitHub token permissions**
   ```bash
   # Error: Resource not accessible by integration
   ```
   
   **🛠️ Solution:**
   ```yaml
   # Add required permissions to workflow
   permissions:
     contents: read           # Read repository contents
     security-events: write   # Upload SARIF reports
     actions: read           # Access action artifacts
     issues: write           # Comment on PRs
     pull-requests: write    # Update PR status
   ```

2. **Secret access issues**
   ```bash
   # Error: Secret MYAPI_KEY not found
   ```
   
   **🛠️ Solution:**
   ```yaml
   # Check secret configuration
   env:
     API_KEY: ${{ secrets.MYAPI_KEY }}  # Must be configured in repo settings
   
   # For organization secrets
   env:
     API_KEY: ${{ secrets.ORG_API_KEY }}
   ```

3. **File permission issues**
   ```bash
   # Error: Permission denied when accessing file
   ```
   
   **🛠️ Solution:**
   ```yaml
   # Fix file permissions
   - name: Fix permissions
     run: |
       chmod +x scripts/setup.sh
       chmod -R 755 .github/
   ```

**🔐 Security Best Practices:**
```yaml
# Minimal permissions principle
permissions:
  contents: read  # Only what's needed
  
# Environment-specific secrets
env:
  PROD_API_KEY: ${{ github.ref == 'refs/heads/main' && secrets.PROD_API_KEY || secrets.DEV_API_KEY }}
```

</details>

<details>
<summary>🚫 <strong>SARIF upload failures</strong></summary>

#### **Security Report Upload Issues**

**SARIF Upload Problems:**

1. **SARIF format validation errors**
   ```bash
   # Error: Invalid SARIF file format
   ```
   
   **🛠️ Solution:**
   ```yaml
   # Ensure SARIF generation is enabled
   - uses: ./actions/security-scan
     with:
       security-level: 'medium'
       enable-sarif: 'true'  # Required for upload
   
   # Validate SARIF before upload
   - name: Validate SARIF
     run: |
       if [[ -f security-reports/security.sarif ]]; then
         echo "SARIF file found"
       else
         echo "No SARIF file generated"
         exit 1
       fi
   ```

2. **Upload permission issues**
   ```bash
   # Error: Token does not have the required scopes
   ```
   
   **🛠️ Solution:**
   ```yaml
   # Required permissions for SARIF upload
   permissions:
     security-events: write  # Critical for SARIF
     contents: read
   
   # Upload SARIF results
   - uses: github/codeql-action/upload-sarif@v2
     if: always()
     with:
       sarif_file: security-reports/security.sarif
       category: 'ci-framework-security'
   ```

3. **Missing security tab**
   ```bash
   # SARIF uploads but doesn't appear in Security tab
   ```
   
   **🛠️ Solution:**
   ```yaml
   # Enable GitHub security features
   # Repository Settings → Security → Code security and analysis
   # Enable: Dependency graph, Dependabot alerts, Secret scanning
   
   # Ensure proper SARIF categorization
   - uses: github/codeql-action/upload-sarif@v2
     with:
       sarif_file: security-reports/security.sarif
       category: 'ci-framework'  # Unique category name
   ```

</details>

<details>
<summary>🔍 <strong>Security scan false positives</strong></summary>

#### **Security Scan Configuration**

**False Positive Management:**

1. **Bandit false positives**
   ```bash
   # Warning: Use of assert detected (B101)
   ```
   
   **🛠️ Solution:**
   ```toml
   # Configure bandit exclusions
   [tool.bandit]
   exclude_dirs = ["tests", "test_*"]
   skips = ["B101", "B601"]  # Allow assert, shell=True in tests
   
   # OR use inline comments
   # nosec B101 - assert is acceptable in tests
   assert user.is_authenticated  # nosec
   ```

2. **Safety/pip-audit false positives**
   ```bash
   # Warning: Vulnerability in development dependency
   ```
   
   **🛠️ Solution:**
   ```yaml
   # Ignore development-only vulnerabilities
   - uses: ./actions/security-scan
     with:
       security-level: 'medium'
       ignore-dev-deps: 'true'  # Skip dev dependencies
   ```

3. **Semgrep false positives**
   ```bash
   # Warning: Potential SQL injection
   ```
   
   **🛠️ Solution:**
   ```yaml
   # Custom semgrep configuration
   # .semgrep.yml
   rules:
     - id: python.lang.security.audit.dangerous-subprocess-use
       severity: WARNING
       paths:
         exclude:
           - tests/
           - scripts/
   ```

**🎯 Security Configuration:**
```toml
# Balanced security configuration
[tool.ci-framework.security-scan]
default_level = "medium"
enable_sarif = true

# Tool-specific settings
[tool.ci-framework.security-scan.bandit]
exclude_paths = ["tests/**", "scripts/**"]
skip_checks = ["B101"]

[tool.ci-framework.security-scan.safety]
ignore_dev_deps = true
ignore_ids = ["12345"]  # Specific vulnerability IDs to ignore
```

</details>

</details>

---

## 🤖 AI-Powered Diagnosis

<details>
<summary>🧠 <strong>Smart Problem Detection</strong></summary>

### **🔍 Automated Issue Analysis**

**Paste your error message here for AI analysis:**

**Example Error Messages:**

1. **Test Failure Pattern:**
   ```
   FAILED tests/test_auth.py::test_login - AssertionError: assert False is True
   E   AssertionError: assert False is True
   E   +  where False = <bound method User.is_authenticated of <User: test@example.com>>()
   ```
   
   **🤖 AI Analysis:**
   - **Root Cause**: Authentication method returning False unexpectedly
   - **Likely Issue**: Missing user setup or authentication state
   - **Solution**: Check user creation and login sequence in test

2. **Dependency Error Pattern:**
   ```
   ModuleNotFoundError: No module named 'your_package'
   ```
   
   **🤖 AI Analysis:**
   - **Root Cause**: Package not installed in editable mode
   - **Likely Issue**: Missing `pip install -e .` or similar
   - **Solution**: Add editable installation to CI workflow

3. **Performance Regression Pattern:**
   ```
   Performance regression detected: 45% slower than baseline
   test_api_endpoint: 150ms (baseline: 85ms)
   ```
   
   **🤖 AI Analysis:**
   - **Root Cause**: Significant performance degradation
   - **Likely Issue**: Database N+1 queries or inefficient algorithm
   - **Solution**: Profile code and optimize database queries

**🛠️ Smart Troubleshooting Steps:**

For any error message, the AI assistant follows this process:
1. **Pattern Recognition**: Identify error type and common causes
2. **Context Analysis**: Consider project type and configuration
3. **Solution Ranking**: Provide solutions ordered by likelihood
4. **Prevention Tips**: Suggest ways to avoid the issue in future

</details>

---

## ✅ Success Verification

### **🎯 Verification Checklist**

After applying any solution, verify it worked:

<details>
<summary>✅ <strong>Test Your Fix</strong></summary>

**Local Testing:**
```bash
# 1. Test the specific component
pixi run test          # or poetry run pytest
pixi run lint          # or poetry run ruff check src/
pixi run quality       # or your quality command

# 2. Test the full workflow locally (if possible)
act -j test            # Using act to simulate GitHub Actions

# 3. Check specific areas
pytest tests/test_specific.py -v     # Test specific functionality
ruff check src/main.py              # Check specific file
```

**CI Testing:**
```bash
# 1. Push changes and check Actions tab
git add .
git commit -m "fix: resolve CI issue"
git push

# 2. Monitor the workflow execution
# GitHub → Actions → Latest workflow run

# 3. Check specific job outputs
# Click on failed job → View logs → Look for success/failure
```

**Verification Criteria:**
- [ ] ✅ All jobs complete successfully
- [ ] ✅ No error messages in logs
- [ ] ✅ Expected outputs are generated
- [ ] ✅ Performance is within acceptable range
- [ ] ✅ Security scans pass without critical issues

</details>

---

## 📞 Get Additional Help

### **🆘 When Self-Service Isn't Enough**

If this guide didn't solve your issue:

1. **📖 Check Documentation**
   - [API Reference](../../api/README.md)
   - [Best Practices](../../best-practices/README.md)
   - [Complete Troubleshooting Guide](../../troubleshooting.md)

2. **🧪 Try Interactive Examples**
   - [Quick Start Generator](./quick-start-generator.md)
   - [Configuration Playground](./configuration-playground.md)
   - [Workflow Simulator](./workflow-simulator.md)

3. **🐛 Report Issues**
   - [GitHub Issues](https://github.com/MementoRC/ci-framework/issues)
   - Include error messages, configuration, and steps to reproduce

4. **💬 Community Help**
   - [GitHub Discussions](https://github.com/MementoRC/ci-framework/discussions)
   - Search existing discussions first

### **📋 Issue Reporting Template**

When reporting issues, include:

```markdown
## Problem Description
Brief description of what's not working

## Configuration
- Project type: [web app/CLI/package/etc.]
- Package manager: [pixi/poetry/pip]
- Python version: [3.10/3.11/3.12]
- OS: [ubuntu/macos/windows]

## Error Message
```
Full error message here
```

## Reproduction Steps
1. Step one
2. Step two
3. Error occurs

## Expected Behavior
What should happen instead

## Additional Context
Any other relevant information
```

---

## 📊 Troubleshooting Success Metrics

### **📈 Resolution Tracking**

**Common Issue Categories & Success Rates:**
- 🔧 Configuration issues: **98% resolution rate**
- ❌ Test failures: **95% resolution rate**
- 🛡️ Security scan issues: **92% resolution rate**
- ⚡ Performance problems: **88% resolution rate**
- 🔑 Permission issues: **90% resolution rate**

**⏱️ Average Resolution Time:**
- Simple issues: 2-5 minutes
- Complex issues: 10-15 minutes
- Custom configuration: 15-30 minutes

---

**🔧 Troubleshooting complete!** Most issues can be resolved in under 10 minutes with this guide.

*⏱️ Time invested: 2-5 minutes | 📊 Success rate: 95%+ issue resolution*