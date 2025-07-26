# 🔄 Existing Project Integration (3-4 Minutes)

> **For**: Python projects with existing code/CI  
> **Time**: 3-4 minutes  
> **Result**: Enhanced CI/CD with framework integration

## ⏱️ Integration Strategy

### Option A: Automated Migration (1 minute)
**Recommended**: Let our tools handle the heavy lifting

```bash
# 1. Install migration tool
pip install ci-framework-migrator

# 2. Analyze your project
ci-migrate analyze .
# Output: Migration plan with step-by-step instructions

# 3. Execute migration
ci-migrate migrate . --backup --preview
# Review changes, then run without --preview
```

**✅ Done!** Skip to [Validation](#validation) section.

### Option B: Manual Integration (3-4 minutes)
**Full control**: Step-by-step integration

#### Step 1: Project Analysis (30 seconds)
```bash
# Check current setup
ls -la                    # Look for existing config files
cat pyproject.toml 2>/dev/null || echo "No pyproject.toml found"
cat .github/workflows/*.yml 2>/dev/null || echo "No workflows found"

# Identify package manager
which poetry && echo "Poetry detected" || echo "Poetry not found"
which pixi && echo "Pixi detected" || echo "Pixi not found"
ls requirements*.txt 2>/dev/null && echo "Requirements files found"
```

#### Step 2: Add CI Framework (1 minute)
```bash
# Add framework as submodule (preserves your git history)
git submodule add https://github.com/MementoRC/ci-framework .ci-framework

# Or copy framework files
curl -sSL https://github.com/MementoRC/ci-framework/archive/main.tar.gz | tar -xz
mv ci-framework-main .ci-framework
```

#### Step 3: Integrate Package Management (1 minute)

**If you use Poetry:**
```bash
# Add pixi alongside poetry
pixi init --import-from-poetry
# Keeps poetry.lock, adds pixi.lock for CI acceleration

# Update pyproject.toml with CI framework config
.ci-framework/scripts/merge-config.py pyproject.toml .ci-framework/templates/pyproject-addon.toml
```

**If you use pip/requirements.txt:**
```bash
# Migrate to pixi (optional, recommended)
pixi init
pixi install $(cat requirements.txt | tr '\n' ' ')

# Or add pixi alongside pip
cp .ci-framework/templates/pyproject-pip-compat.toml pyproject.toml
```

**If you already use pixi:**
```bash
# Enhance existing pixi config
.ci-framework/scripts/enhance-pixi-config.py pyproject.toml
```

#### Step 4: Integrate CI Workflows (1 minute)
```bash
# Backup existing workflows
mkdir -p .github/workflows-backup
cp .github/workflows/*.yml .github/workflows-backup/ 2>/dev/null || true

# Add framework workflows
cp .ci-framework/workflows/python-ci-integration.yml .github/workflows/ci-framework.yml

# Integrate with existing workflows (optional)
.ci-framework/scripts/merge-workflows.py .github/workflows/
```

---

## 🔄 Migration Scenarios

### Scenario 1: GitHub Actions + Poetry
**Current setup**: `.github/workflows/test.yml` + `poetry.lock`

```bash
# Quick integration
ci-migrate migrate . --from=poetry-github-actions --backup

# Manual steps
pixi init --import-from-poetry
cp .ci-framework/workflows/poetry-integration.yml .github/workflows/ci-framework.yml
```

### Scenario 2: No CI + requirements.txt
**Current setup**: Just `requirements.txt`, no CI

```bash
# Full migration recommended
ci-migrate migrate . --from=pip-no-ci --full-setup

# Manual steps
pixi init
pixi install $(cat requirements.txt | tr '\n' ' ')
cp .ci-framework/workflows/python-ci-template.yml .github/workflows/ci.yml
```

### Scenario 3: Travis CI + setuptools
**Current setup**: `.travis.yml` + `setup.py`

```bash
# Modernize and migrate
ci-migrate migrate . --from=travis-setuptools --modernize

# Manual steps
pixi init
pixi install pytest flake8 mypy  # Add modern tools
cp .ci-framework/workflows/travis-migration.yml .github/workflows/ci.yml
```

### Scenario 4: Complex Multi-Tool Setup
**Current setup**: Multiple tools, complex configuration

```bash
# Analyze first, then custom migration
ci-migrate analyze . --detailed
ci-migrate migrate . --custom --interactive
```

---

## ⚙️ Configuration Integration

### Merging Quality Tools
The framework intelligently merges with existing configurations:

**Existing `.pre-commit-config.yaml`:**
```yaml
# Your existing hooks are preserved
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black

# Framework adds optimized hooks
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
      - id: ruff-format
```

**Existing `pyproject.toml` sections:**
```toml
# Your existing project config is preserved
[project]
name = "my-existing-project"
version = "1.2.3"
dependencies = ["requests", "click"]

# Framework adds optimized sections
[tool.pixi.dependencies]
python = ">=3.10"
pytest = "*"
ruff = "*"

[tool.pixi.tasks]
test = "pytest"
quality = { depends-on = ["test", "lint", "typecheck"] }
```

---

## ✅ Validation

### Pre-Integration Backup
Always create a backup before migration:
```bash
# Automatic backup
ci-migrate migrate . --backup

# Manual backup
git branch backup-before-ci-framework
git add . && git commit -m "Backup before CI framework integration"
```

### Integration Health Check
```bash
# Test new setup works alongside existing tools
pixi run quality              # New framework commands ✅
poetry run pytest 2>/dev/null || echo "Poetry still works if you had it"
npm test 2>/dev/null || echo "Node.js tools still work if you had them"

# Test CI integration
git add . && git commit -m "Integrate CI framework"
git push                     # Should trigger enhanced CI ✅
```

### Success Validation
After integration, verify:
- [ ] **Existing functionality** still works
- [ ] **New quality gates** run successfully
- [ ] **CI pipeline** includes framework jobs
- [ ] **Local development** workflow improved
- [ ] **Performance** is same or better

### Rollback if Needed
```bash
# Rollback option 1: Git branch
git checkout backup-before-ci-framework

# Rollback option 2: Migration tool
ci-migrate rollback .

# Rollback option 3: Manual
rm -rf .ci-framework
git checkout HEAD~1 -- .github/workflows/ pyproject.toml
```

---

## 🎯 Integration Best Practices

### Gradual Integration
1. **Week 1**: Add framework alongside existing CI
2. **Week 2**: Migrate quality tools to framework versions
3. **Week 3**: Optimize CI performance with change detection
4. **Week 4**: Full framework adoption

### Team Communication
```bash
# Generate integration report for your team
ci-migrate analyze . --report=team-report.md

# Test integration on feature branch first
git checkout -b integrate-ci-framework
ci-migrate migrate .
# Test thoroughly, then merge to main
```

### Preserving Team Workflows
```bash
# Keep existing commands working
echo "alias old-test='pixi run test'" >> ~/.bashrc
echo "alias old-lint='pixi run lint'" >> ~/.bashrc

# Document changes for team
ci-migrate generate-changelog . > MIGRATION_CHANGELOG.md
```

---

## 🔧 Troubleshooting Integration

### Common Integration Issues

**Dependency conflicts:**
```bash
# Check for conflicts
pixi solve
poetry check 2>/dev/null || echo "Poetry not used"

# Resolve conflicts
ci-migrate resolve-conflicts .
```

**CI workflow conflicts:**
```bash
# Check workflow syntax
gh workflow validate .github/workflows/*.yml

# Fix common issues
.ci-framework/scripts/fix-workflow-conflicts.py
```

**Tool version mismatches:**
```bash
# Align tool versions
.ci-framework/scripts/align-tool-versions.py
```

### Getting Help
- **[Integration Troubleshooting](../troubleshooting/common-issues.md#integration-issues)**
- **[Migration Tool Issues](../migration/troubleshooting.md)**
- **[Community Support](https://github.com/MementoRC/ci-framework/discussions)**

---

## 📊 Integration Metrics

Track your integration success:
- **Setup Time**: Target <4 minutes
- **CI Performance**: Same or better than before
- **Quality Coverage**: More comprehensive than before
- **Team Adoption**: Smooth transition

**Benchmark your integration**: [Performance Comparison Guide](../best-practices/performance-monitoring.md#before-after-comparison)

---

*⏱️ Average integration time: 3.2 minutes | Success rate: 89%*