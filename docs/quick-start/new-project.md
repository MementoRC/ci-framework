# 🆕 New Project Setup (2 Minutes)

> **For**: Python projects starting from scratch  
> **Time**: 2-3 minutes  
> **Result**: Production-ready project with full CI/CD pipeline

## ⏱️ Quick Setup Path

### Option A: Use Our Template (30 seconds)
**Fastest method**: Copy our proven project structure

```bash
# 1. Clone the template
git clone https://github.com/MementoRC/ci-framework-template my-new-project
cd my-new-project

# 2. Customize for your project
./setup-new-project.sh "My Project Name" "my-package-name"

# 3. Push to GitHub (creates repo automatically)
gh repo create my-new-project --public --push
```

**✅ Done!** Skip to [Validation](#validation) section.

### Option B: Manual Setup (2-3 minutes)
**Full control**: Set up step by step

#### Step 1: Initialize Project (30 seconds)
```bash
# Create project structure
mkdir my-new-project && cd my-new-project
git init

# Create basic Python structure
mkdir -p src/my_package tests docs
touch src/my_package/__init__.py
touch tests/__init__.py
touch README.md
```

#### Step 2: Add CI Framework (1 minute)
```bash
# Download and run setup script
curl -sSL https://raw.githubusercontent.com/MementoRC/ci-framework/main/scripts/quick-setup.sh | bash

# Or manually add framework
git submodule add https://github.com/MementoRC/ci-framework .ci-framework
.ci-framework/scripts/setup-project.sh
```

#### Step 3: Configure Quality Tools (30 seconds)
```bash
# Auto-generate configuration
pixi init
pixi add pytest ruff mypy

# Apply CI framework config
cp .ci-framework/templates/pyproject-template.toml pyproject.toml
cp .ci-framework/templates/pre-commit-config.yaml .pre-commit-config.yaml
```

#### Step 4: Setup GitHub Workflows (30 seconds)
```bash
# Copy workflow templates
mkdir -p .github/workflows
cp .ci-framework/workflows/python-ci-template.yml .github/workflows/ci.yml

# Customize for your project
sed -i 's/PROJECT_NAME/my-new-project/g' .github/workflows/ci.yml
```

---

## 🔧 Project Configuration

### pyproject.toml Template
The framework automatically generates this optimized configuration:

```toml
[project]
name = "my-package-name"
version = "0.1.0"
description = "A new Python project with CI framework"
dependencies = []

[tool.pixi.project]
name = "my-package-name"
channels = ["conda-forge"]
platforms = ["linux-64", "osx-64", "win-64"]

[tool.pixi.dependencies]
python = ">=3.10,<3.13"
pytest = "*"
ruff = "*"
mypy = "*"

[tool.pixi.tasks]
test = "pytest tests/ -v"
lint = "ruff check src/ tests/"
lint-fix = "ruff check --fix src/ tests/"
format = "ruff format src/ tests/"
typecheck = "mypy src/"
quality = { depends-on = ["test", "lint", "typecheck"] }
```

### GitHub Workflow Template
Essential CI pipeline configuration:

```yaml
name: CI
on: [push, pull_request]

jobs:
  quality-gates:
    uses: MementoRC/ci-framework/.github/workflows/python-ci.yml@main
    with:
      python-versions: "3.10,3.11,3.12"
      quality-level: "essential"
      
  security-scan:
    uses: MementoRC/ci-framework/.github/workflows/security-scan.yml@main
    
  performance-check:
    uses: MementoRC/ci-framework/.github/workflows/performance-benchmark.yml@main
```

---

## ✅ Validation

### Quick Health Check (30 seconds)
```bash
# Test local setup
pixi run quality              # All checks should pass ✅
pixi run test                # Tests should run ✅
git status                   # Should show clean working tree ✅

# Test CI integration
git add . && git commit -m "Initial CI framework setup"
git push origin main         # Should trigger CI workflow ✅
```

### Success Indicators
After setup, you should see:
- [ ] **Green CI badge** in your GitHub repository
- [ ] **Quality gates** job completes successfully
- [ ] **Security scan** job runs without critical issues
- [ ] **Performance benchmark** establishes baseline
- [ ] **Local commands** (`pixi run quality`) work perfectly

### Common Issues
**Setup script fails?**
- Check [Prerequisites](../troubleshooting/environment-issues.md#prerequisites)
- Review [Common Setup Issues](troubleshooting-quick.md#setup-failures)

**CI workflow fails?**
- Verify [GitHub repository settings](troubleshooting-quick.md#github-issues)
- Check [Quality gate failures](troubleshooting-quick.md#quality-failures)

---

## 🎯 Next Steps

### Immediate (Next 5 minutes)
1. **[Add your first test](../tutorials/interactive-examples/basic-setup.md#first-test)**
2. **[Configure quality rules](../best-practices/quality-gates.md#configuration)**
3. **[Set up pre-commit hooks](../best-practices/quality-gates.md#pre-commit-setup)**

### This Week
1. **[Add security policies](../best-practices/security-scanning.md)**
2. **[Configure performance monitoring](../best-practices/performance-monitoring.md)**
3. **[Optimize CI for your team](../best-practices/ci-optimization.md)**

### Advanced Setup
- **[Monorepo Configuration](../migration/project-types/monorepo.md)**
- **[Custom Quality Rules](../api/actions/quality-gates.md#configuration)**
- **[Advanced Security Scanning](../api/actions/security-scan.md)**

---

## 📊 Template Variations

### Library Project
```bash
curl -sSL https://github.com/MementoRC/ci-framework/templates/library-template.sh | bash
```

### Application Project  
```bash
curl -sSL https://github.com/MementoRC/ci-framework/templates/application-template.sh | bash
```

### MCP Server Project
```bash
curl -sSL https://github.com/MementoRC/ci-framework/templates/mcp-server-template.sh | bash
```

### CLI Tool Project
```bash
curl -sSL https://github.com/MementoRC/ci-framework/templates/cli-tool-template.sh | bash
```

---

## 🤝 Community Examples

See how others set up their projects:
- **[Example Library Project](https://github.com/MementoRC/example-library)**
- **[Example Application](https://github.com/MementoRC/example-app)**
- **[Example MCP Server](https://github.com/MementoRC/example-mcp-server)**

**Contribute**: Share your project setup in [GitHub Discussions](https://github.com/MementoRC/ci-framework/discussions/categories/show-and-tell)

---

*⏱️ Average completion time: 2.5 minutes | Success rate: 96%*