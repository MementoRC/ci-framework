# 🎯 Interactive Quick Start Generator

> **Get your personalized CI setup in 60 seconds with zero configuration knowledge required**

## 🚀 How It Works

This generator asks you simple questions about your project and creates a complete, ready-to-use CI configuration. No CI/CD expertise needed!

---

## 📋 Step 1: Project Information

**What best describes your project?**

<details>
<summary>🌐 <strong>Web Application</strong> (FastAPI, Django, Flask)</summary>

### Web Application Configuration

**Package Manager:**
- 🟢 **Pixi** (Recommended - fastest, most reliable)
- 🟡 **Poetry** (Good - widely used)  
- 🟡 **pip** (Basic - works everywhere)

**Framework:**
- **FastAPI** - Modern async API framework
- **Django** - Full-featured web framework
- **Flask** - Lightweight web framework
- **Other** - Generic web application

**Services you use:**
- [ ] Database (PostgreSQL, MySQL, SQLite)
- [ ] Redis/Caching
- [ ] External APIs
- [ ] Background tasks (Celery, RQ)

**Generated Configuration:**
```yaml
# .github/workflows/ci.yml
name: Web Application CI
on: [push, pull_request]

jobs:
  web-app-pipeline:
    uses: MementoRC/ci-framework/.github/workflows/python-ci.yml@main
    with:
      python-versions: "3.10,3.11,3.12"
      quality-level: "extended"
      enable-api-testing: "true"
      enable-security-scan: "true"
      service-dependencies: "postgres,redis"
```

```toml
# pyproject.toml
[tool.pixi.project]
name = "your-web-app"
channels = ["conda-forge"]
platforms = ["linux-64"]

[tool.pixi.dependencies]
python = "3.11.*"
fastapi = "*"  # or django/flask
uvicorn = "*"
pytest = "*"
httpx = "*"
pytest-asyncio = "*"

[tool.pixi.tasks]
dev = "uvicorn app.main:app --reload"
test = "pytest tests/ -v"
test-api = "pytest tests/api/ -v"
lint = "ruff check app/ tests/ --select=F,E9"
quality = { depends-on = ["test", "lint"] }
```

**🎯 Next Steps:**
1. Copy the configuration files above
2. Adjust the `name` field to match your project
3. Add your specific dependencies
4. Commit and push to trigger CI

</details>

<details>
<summary>📊 <strong>Data Science / ML Project</strong> (Analysis, Models, Research)</summary>

### Data Science Configuration

**Primary Focus:**
- **Machine Learning** - Training and inference pipelines
- **Data Analysis** - Exploratory analysis and reporting
- **Research** - Scientific computing and publication

**Tools you use:**
- [ ] Jupyter Notebooks
- [ ] PyTorch / TensorFlow
- [ ] Pandas / NumPy
- [ ] Matplotlib / Seaborn
- [ ] GPU computing

**Generated Configuration:**
```yaml
# .github/workflows/ci.yml
name: Data Science CI
on: [push, pull_request]

jobs:
  data-science-pipeline:
    uses: MementoRC/ci-framework/.github/workflows/python-ci.yml@main
    with:
      python-versions: "3.10,3.11"
      quality-level: "essential"
      enable-notebook-testing: "true"
      enable-performance-benchmarks: "true"
      data-validation: "true"
```

```toml
# pyproject.toml
[tool.pixi.project]
name = "your-ds-project"
channels = ["conda-forge", "pytorch"]
platforms = ["linux-64"]

[tool.pixi.dependencies]
python = "3.11.*"
numpy = "*"
pandas = "*"
scikit-learn = "*"
matplotlib = "*"
jupyter = "*"
pytest = "*"
pytest-benchmark = "*"

[tool.pixi.tasks]
notebook = "jupyter lab"
preprocess = "python scripts/preprocess.py"
train = "python src/train.py"
test = "pytest tests/ -v"
test-notebooks = "pytest --nbval notebooks/"
lint = "ruff check src/ scripts/ --select=F,E9"
quality = { depends-on = ["test", "test-notebooks", "lint"] }
```

**🎯 Next Steps:**
1. Copy the configuration above
2. Add your specific ML/data dependencies
3. Organize notebooks in `notebooks/` directory
4. Create `scripts/` for data processing

</details>

<details>
<summary>🛠️ <strong>CLI Tool / Utility</strong> (Command-line applications)</summary>

### CLI Tool Configuration

**Distribution:**
- **PyPI Package** - Installable via pip
- **Standalone Tool** - Direct download/usage
- **Internal Tool** - For your organization only

**Platforms:**
- [ ] Linux
- [ ] macOS 
- [ ] Windows
- [ ] Cross-platform (all)

**Generated Configuration:**
```yaml
# .github/workflows/ci.yml
name: CLI Tool CI
on: [push, pull_request]

jobs:
  cli-pipeline:
    uses: MementoRC/ci-framework/.github/workflows/python-ci.yml@main
    with:
      python-versions: "3.10,3.11,3.12"
      quality-level: "extended"
      test-platforms: "ubuntu,macos,windows"
      enable-cli-testing: "true"
      enable-packaging: "true"
```

```toml
# pyproject.toml
[tool.pixi.project]
name = "your-cli-tool"
channels = ["conda-forge"]
platforms = ["linux-64", "osx-arm64", "osx-64", "win-64"]

[tool.pixi.dependencies]
python = ">=3.10"
click = "*"
rich = "*"
pytest = "*"

[project.scripts]
your-tool = "your_tool.cli:main"

[tool.pixi.tasks]
dev = "python -m your_tool"
test = "pytest tests/ -v"
test-cli = "pytest tests/cli/ -v"
test-commands = "your-tool --help && your-tool --version"
lint = "ruff check src/ tests/ --select=F,E9"
build = "python -m build"
quality = { depends-on = ["test", "test-cli", "lint"] }
```

**🎯 Next Steps:**
1. Copy the configuration above
2. Set up your CLI entry point in `src/your_tool/cli.py`
3. Create CLI tests in `tests/cli/`
4. Test cross-platform compatibility

</details>

<details>
<summary>📦 <strong>Python Package / Library</strong> (Reusable code)</summary>

### Python Package Configuration

**Purpose:**
- **Public Library** - Open source, PyPI distribution
- **Private Package** - Internal use, private registry
- **Framework Extension** - Plugin or add-on

**Features:**
- [ ] Documentation (Sphinx)
- [ ] Type hints (mypy)
- [ ] Examples/demos
- [ ] API documentation

**Generated Configuration:**
```yaml
# .github/workflows/ci.yml
name: Python Package CI
on: [push, pull_request]

jobs:
  package-pipeline:
    uses: MementoRC/ci-framework/.github/workflows/python-ci.yml@main
    with:
      python-versions: "3.10,3.11,3.12"
      quality-level: "full"
      enable-documentation: "true"
      enable-type-checking: "true"
      enable-publishing: "true"
```

```toml
# pyproject.toml
[tool.pixi.project]
name = "your-package"
channels = ["conda-forge"]
platforms = ["linux-64", "osx-arm64", "osx-64", "win-64"]

[tool.pixi.dependencies]
python = ">=3.10"
pytest = "*"
pytest-cov = "*"

[tool.pixi.feature.docs.dependencies]
sphinx = "*"
sphinx-rtd-theme = "*"
myst-parser = "*"

[tool.pixi.feature.dev.dependencies]
ruff = "*"
mypy = "*"
pre-commit = "*"

[tool.pixi.environments]
default = {solve-group = "default"}
docs = {features = ["docs"], solve-group = "default"}
dev = {features = ["dev"], solve-group = "default"}

[tool.pixi.tasks]
test = "pytest tests/ -v"
test-cov = "pytest tests/ --cov=src --cov-report=xml"
docs-build = "sphinx-build -b html docs/ docs/_build/"
lint = "ruff check src/ tests/ --select=F,E9"
typecheck = "mypy src/"
build = "python -m build"
quality = { depends-on = ["test-cov", "lint", "typecheck"] }
```

**🎯 Next Steps:**
1. Copy the configuration above
2. Set up proper package structure in `src/`
3. Configure documentation in `docs/`
4. Add type hints for better API docs

</details>

<details>
<summary>🏢 <strong>Enterprise Application</strong> (Large, complex systems)</summary>

### Enterprise Application Configuration

**Architecture:**
- **Monolith** - Single large application
- **Microservices** - Multiple connected services
- **Hybrid** - Mix of approaches

**Requirements:**
- [ ] High security standards
- [ ] Performance monitoring
- [ ] Compliance reporting
- [ ] Multiple environments (dev/staging/prod)

**Generated Configuration:**
```yaml
# .github/workflows/ci.yml
name: Enterprise Application CI
on: [push, pull_request]

jobs:
  enterprise-pipeline:
    uses: MementoRC/ci-framework/.github/workflows/python-ci.yml@main
    with:
      python-versions: "3.11,3.12"
      quality-level: "full"
      security-level: "critical"
      enable-performance-benchmarks: "true"
      enable-compliance-reporting: "true"
      enable-multi-environment: "true"
```

```toml
# pyproject.toml
[tool.pixi.project]
name = "enterprise-app"
channels = ["conda-forge"]
platforms = ["linux-64"]

[tool.pixi.dependencies]
python = "3.11.*"
fastapi = "*"
sqlalchemy = "*"
alembic = "*"
redis = "*"
celery = "*"
pytest = "*"
pytest-xdist = "*"
pytest-benchmark = "*"

[tool.pixi.feature.monitoring.dependencies]
prometheus-client = "*"
sentry-sdk = "*"

[tool.pixi.environments]
default = {solve-group = "default"}
monitoring = {features = ["monitoring"], solve-group = "default"}

[tool.pixi.tasks]
test = "pytest tests/ -v -n auto"
test-security = "bandit -r app/ -f json -o security-report.json"
test-performance = "pytest tests/performance/ --benchmark-only"
lint = "ruff check app/ tests/ --select=F,E9"
typecheck = "mypy app/"
quality = { depends-on = ["test", "lint", "typecheck", "test-security"] }
```

**🎯 Next Steps:**
1. Copy the configuration above
2. Set up proper service architecture
3. Configure monitoring and alerting
4. Implement security best practices

</details>

---

## 📋 Step 2: Quality Level Selection

**How strict should your quality checks be?**

<details>
<summary>⚡ <strong>Essential</strong> - Fast feedback (≤ 5 minutes)</summary>

**Perfect for:**
- Development branches
- Quick iterations
- Personal projects

**Includes:**
- ✅ Critical error detection (F, E9 violations)
- ✅ Fast unit tests
- ✅ Basic security scan
- ✅ Import validation

**Time budget:** 2-5 minutes per run
</details>

<details>
<summary>🔧 <strong>Extended</strong> - Comprehensive validation (≤ 10 minutes)</summary>

**Perfect for:**
- Feature branches
- Team projects
- Pre-merge validation

**Includes:**
- ✅ Everything in Essential
- ✅ Full linting and style checks
- ✅ Integration tests
- ✅ Security vulnerability scan
- ✅ Basic performance checks

**Time budget:** 5-10 minutes per run
</details>

<details>
<summary>🏆 <strong>Full</strong> - Production-ready validation (≤ 15 minutes)</summary>

**Perfect for:**
- Main branch
- Release candidates
- Production deployments

**Includes:**
- ✅ Everything in Extended  
- ✅ Complete test suite
- ✅ Cross-platform testing
- ✅ Security audit with SARIF
- ✅ Performance benchmarking
- ✅ Documentation validation

**Time budget:** 10-15 minutes per run
</details>

---

## 📋 Step 3: Additional Features

**What additional features do you need?**

<details>
<summary>🔒 <strong>Security Scanning</strong></summary>

**Security Level:**
- **Medium** - Standard vulnerability detection
- **High** - Comprehensive security analysis  
- **Critical** - Enterprise-grade security with SBOM

**Tools included:**
- 🛡️ **bandit** - Python code security analysis
- 🔍 **safety** - Dependency vulnerability database
- 📦 **pip-audit** - Package auditing
- ⚔️ **semgrep** - Pattern-based security detection (High+)
- 🐳 **Trivy** - Container and SBOM scanning (Critical)

**Configuration added:**
```yaml
security-scan:
  uses: ./.github/actions/security-scan
  with:
    security-level: 'medium'  # or high/critical
    enable-sarif: 'true'
    enable-sbom: 'false'      # true for critical
```
</details>

<details>
<summary>📊 <strong>Performance Monitoring</strong></summary>

**Benchmark Level:**
- **Quick** - Fast smoke tests (≤ 30s)
- **Full** - Comprehensive benchmarks (≤ 5min)
- **Load** - Stress testing (≤ 10min)

**Features:**
- 📈 **Statistical analysis** with pytest-benchmark
- 🎯 **Regression detection** with configurable thresholds
- 📊 **Baseline comparison** against main branch
- 🏆 **Performance reports** with trends

**Configuration added:**
```yaml
performance-benchmark:
  uses: ./.github/actions/performance-benchmark
  with:
    suite: 'quick'              # or full/load
    regression-threshold: '10'   # % threshold
    store-results: 'true'
```
</details>

<details>
<summary>🐳 <strong>Docker Cross-Platform Testing</strong></summary>

**Environments:**
- **Ubuntu** - Most common production environment
- **Alpine** - Lightweight container base
- **CentOS** - Enterprise RHEL compatibility
- **Debian** - Stable production base

**Test Modes:**
- **Smoke** - Basic installation verification
- **Test** - Standard test suite execution  
- **Full** - Complete validation with linting

**Configuration added:**
```yaml
docker-cross-platform:
  uses: ./.github/actions/docker-cross-platform
  with:
    environments: 'ubuntu,alpine'
    test-mode: 'test'
    parallel: 'true'
```
</details>

<details>
<summary>⚡ <strong>Change Detection Optimization</strong></summary>

**Optimization Level:**
- **Standard** - Basic file pattern analysis
- **Comprehensive** - Full dependency analysis with smart test targeting

**Benefits:**
- 🚀 **40-80% faster** CI runs by skipping unnecessary jobs
- 🎯 **Smart test targeting** - run only affected tests
- 📊 **Optimization reports** showing time saved
- 🔍 **Intelligent analysis** of file changes and dependencies

**Configuration added:**
```yaml
change-detection:
  uses: ./.github/actions/change-detection
  with:
    detection-level: 'standard'
    enable-test-optimization: 'true'
    enable-job-skipping: 'true'
```
</details>

---

## 🎯 Step 4: Generated Configuration

Based on your selections above, here's your complete, ready-to-use CI configuration:

### **Files to Create:**

#### `.github/workflows/ci.yml`
```yaml
# This will be generated based on your selections above
# Copy the specific configuration from your project type section
```

#### `pyproject.toml` 
```toml
# This will be generated based on your selections above
# Copy the specific configuration from your project type section
```

#### `tests/test_example.py` (if you don't have tests yet)
```python
def test_example():
    """Basic test to verify CI setup"""
    assert 1 + 1 == 2

def test_import():
    """Test that your package can be imported"""
    # Adjust import path for your project
    # import your_project
    assert True  # Replace with actual import test
```

---

## 🚀 Implementation Steps

### **1. Copy Configuration (30 seconds)**
1. Copy the generated `.github/workflows/ci.yml` to your repository
2. Copy the `pyproject.toml` configuration
3. Create basic tests if you don't have them

### **2. Customize (1 minute)**
1. Replace `your-project-name` with your actual project name
2. Adjust import paths in tests
3. Add your specific dependencies

### **3. Test & Deploy (1 minute)**
```bash
# Add files to git
git add .github/workflows/ci.yml pyproject.toml tests/

# Commit
git commit -m "🚀 Add CI Framework - Enterprise-grade CI in 5 minutes"

# Push to trigger CI
git push
```

### **4. Verify Success (30 seconds)**
1. Go to GitHub Actions tab in your repository
2. Watch your workflow run
3. Check that all jobs complete successfully

---

## ✅ Success Checklist

After implementation, you should see:

- [ ] 🟢 Green CI status on your latest commit
- [ ] 📊 Detailed job reports in GitHub Actions
- [ ] 🛡️ Security scan results (if enabled)
- [ ] 📈 Performance benchmarks (if enabled)
- [ ] ⚡ Change detection optimization working
- [ ] 🎯 All quality gates passing

---

## 🔧 Need Help?

### **Common Issues:**
- **Tests not found?** → Ensure test files start with `test_` in `tests/` directory
- **Import errors?** → Add `-e .` installation to your test task
- **Linting failures?** → Run `ruff check --fix` locally first

### **Get Support:**
- 📖 [Troubleshooting Guide](../../troubleshooting.md)
- 🎮 [Interactive Troubleshooter](./troubleshooting-guide.md)
- 🐛 [Report Issues](https://github.com/MementoRC/ci-framework/issues)

---

**🎉 Congratulations!** You now have enterprise-grade CI running on your project with zero manual configuration required.

*⏱️ Total time: 1-3 minutes | ⚡ Result: Production-ready CI pipeline*