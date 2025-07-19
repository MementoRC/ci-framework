# 🚀 Quick Start - Python CI Framework

> Get enterprise-grade CI running in your Python project in **under 5 minutes**

## What You'll Get

After following this guide, your project will have:

- ✅ **Cross-platform testing** (Python 3.10-3.12 × ubuntu/macos)
- ✅ **Quality gates** (tests, linting, security, type checking)
- ✅ **Security scanning** (bandit, safety, CodeQL)
- ✅ **Performance monitoring** (benchmark tracking)
- ✅ **Smart CI optimization** (change-based execution)

## Step 1: Copy the Workflow Template (30 seconds)

```bash
# Navigate to your repository root
cd your-python-project

# Copy the CI workflow template
curl -O https://raw.githubusercontent.com/MementoRC/ci-framework/main/.github/workflows/python-ci-template.yml.template

# Place it in the correct location
mkdir -p .github/workflows
mv python-ci-template.yml.template .github/workflows/ci.yml
```

## Step 2: Configure Your Project (2 minutes)

### Option A: Using Pixi (Recommended)

Create or update your `pyproject.toml`:

```toml
[tool.pixi.project]
name = "your-project-name"
channels = ["conda-forge"]
platforms = ["linux-64"]  # Add "osx-arm64", "osx-64" for local macOS support

[tool.pixi.dependencies]
python = ">=3.10,<3.13"
pytest = "*"
ruff = "*"

[tool.pixi.tasks]
# Essential tasks for CI
test = "pytest tests/ -v"
lint = "ruff check --select=F,E9 src/ tests/"
lint-full = "ruff check src/ tests/"
format = "ruff format src/ tests/"
typecheck = "echo 'Add mypy if using type hints'"

# Combined quality check
quality = { depends-on = ["test", "lint"] }
```

### Option B: Using Poetry

```toml
[tool.poetry]
name = "your-project-name"
version = "0.1.0"
description = ""

[tool.poetry.dependencies]
python = "^3.10"

[tool.poetry.group.dev.dependencies]
pytest = "*"
ruff = "*"

[tool.poetry.scripts]
test = "pytest tests/ -v"
lint = "ruff check --select=F,E9 src/ tests/"
```

### Option C: Using pip

Create `requirements.txt`:
```
pytest>=7.0.0
ruff>=0.1.0
```

And ensure you have these scripts available:
```bash
# Add to your Makefile or package.json scripts
test: pytest tests/ -v
lint: ruff check --select=F,E9 src/ tests/
```

## Step 3: Project Structure Setup (1 minute)

Ensure your project has this basic structure:

```
your-project/
├── .github/workflows/ci.yml  ✅ Added in Step 1
├── pyproject.toml             ✅ Configured in Step 2
├── src/your_project/          📁 Your source code
│   └── __init__.py
├── tests/                     📁 Your tests
│   └── test_example.py
└── README.md                  📝 Project documentation
```

### Quick Test Setup

If you don't have tests yet, create a simple one:

```python
# tests/test_example.py
def test_example():
    """Basic test to verify CI setup"""
    assert 1 + 1 == 2

def test_import():
    """Test that your package can be imported"""
    # Adjust import path for your project
    # import your_project
    assert True  # Replace with actual import test
```

## Step 4: Commit and Push (1 minute)

```bash
# Add the new files
git add .github/workflows/ci.yml pyproject.toml

# Include tests if you created them
git add tests/

# Commit with a descriptive message
git commit -m "🚀 Add CI Framework

- Add comprehensive CI workflow with quality gates
- Configure cross-platform testing (Python 3.10-3.12)
- Enable security scanning and performance monitoring
- Set up pixi/poetry package management"

# Push to trigger CI
git push
```

## Step 5: Verify CI is Running (30 seconds)

1. Go to your GitHub repository
2. Click on the **"Actions"** tab
3. You should see your workflow running
4. Click on the latest run to see detailed progress

### Expected CI Jobs

You should see these jobs running:
- 🔍 **Change Detection** - Determines what to test
- ⚡ **Quick Checks** - Fast linting and basic validation
- 🧪 **Comprehensive Tests** - Full test matrix (6 combinations)
- 🛡️ **Security Audit** - Security vulnerability scanning
- ⚡ **Performance Check** - Benchmark validation
- 📊 **Summary** - Aggregated results and reporting

## ✅ Success Indicators

### Green CI Badge
If everything is working, you should see:
- ✅ All jobs completing successfully
- 🟢 Green status checks on your commit
- 📊 Detailed test reports in job outputs

### What Each Job Does

| Job | Purpose | Duration |
|-----|---------|----------|
| Change Detection | Analyzes what files changed to optimize testing | ~10s |
| Quick Checks | Runs fast linting for immediate feedback | ~30s |
| Comprehensive Tests | Runs full test suite across Python 3.10-3.12 on ubuntu/macos | ~2-5min |
| Security Audit | Scans for vulnerabilities with bandit, safety, CodeQL | ~1-3min |
| Performance Check | Runs benchmarks and checks for regressions | ~1-2min |
| Summary | Aggregates results and generates reports | ~15s |

## 🔧 Common First-Run Issues & Fixes

### Issue: "pixi command not found"
**Fix**: The workflow auto-installs pixi. If it fails, check the pixi version in your workflow.

### Issue: "No tests collected"
**Fix**: Ensure your test files start with `test_` and are in a `tests/` directory.

### Issue: "Import errors in tests"
**Fix**: Add this to your `pyproject.toml`:
```toml
[tool.pixi.tasks]
install-dev = "pip install -e ."
test = { depends-on = ["install-dev"], cmd = "pytest tests/ -v" }
```

### Issue: "Linting errors"
**Fix**: Run locally to fix:
```bash
# Auto-fix most issues
pixi run ruff check --fix src/ tests/
pixi run ruff format src/ tests/

# Then commit the fixes
git add . && git commit -m "🔧 Fix linting issues"
```

## 🎯 Next Steps

### Customize Your CI

1. **Add More Tests**: Expand your test suite for better coverage
2. **Configure Security**: Customize security scanning rules
3. **Performance Benchmarks**: Add performance tests
4. **Custom Quality Gates**: Define project-specific quality criteria

### Learn More

- 📖 [Complete CI Workflow Guide](../ci-workflow-guide.md)
- 🔧 [Customization Examples](../ci-workflow-guide.md#-examples)
- 🛠️ [Troubleshooting Guide](../ci-workflow-guide.md#️-troubleshooting)
- 🚀 [Advanced Configurations](../examples/)

## 🏆 You're Done!

Congratulations! You now have enterprise-grade CI running on your Python project. Your repository is now equipped with:

- **Quality Assurance**: Automated testing and code quality checks
- **Security Protection**: Vulnerability scanning and secret detection
- **Cross-Platform Validation**: Testing across multiple Python versions and OS
- **Performance Monitoring**: Benchmark tracking for performance regressions
- **Professional Standards**: Industry best practices built-in

### Share Your Success! 

Add a CI badge to your README:

```markdown
[![CI](https://github.com/YOUR_USERNAME/YOUR_REPO/workflows/CI/badge.svg)](https://github.com/YOUR_USERNAME/YOUR_REPO/actions)
```

---

**⏱️ Total Time**: ~5 minutes  
**⚡ Result**: Enterprise-grade CI with zero configuration needed  
**🔄 Maintenance**: Minimal - updates automatically  

*Need help? Check our [troubleshooting guide](../ci-workflow-guide.md#️-troubleshooting) or [open an issue](https://github.com/MementoRC/ci-framework/issues).*