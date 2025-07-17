# Tiered Quality Features Guide
> New approach for scalable quality management using pixi feature tiers

## 📋 **OVERVIEW**

This guide explains the **Tiered Quality Features** approach - a new, more scalable way to organize quality tools in Python projects using pixi. This approach is designed to:

- **Reduce dependency bloat** in basic environments
- **Scale quality tools** based on project needs
- **Optimize CI performance** with targeted tool sets
- **Maintain AG command compatibility** with proven workflows
- **🚨 PREVENT CI FAILURES** by ensuring local quality gates match CI exactly

## 🚨 **QUALITY GATES INTEGRATION**

**CRITICAL**: This tiered approach MUST prevent "Found X errors" CI failures:

1. **Local Commands Match CI**: Every tier must provide commands that match CI exactly
2. **Auto-fix Capability**: Include `lint-fix` and `format` commands in all tiers
3. **Pre-commit Integration**: Ensure pre-commit hooks use the same tools as CI
4. **Emergency Recovery**: Provide emergency fix scripts for CI failures

**Essential Commands Required in ALL Tiers**:
```toml
# MANDATORY for quality gates prevention
quality = { depends-on = ["test", "lint", "typecheck"] }   # NEVER commit without this passing
lint-fix = "ruff check --fix framework/"                  # Auto-fix lint violations
format = "ruff format framework/"                         # Format code
pre-commit = "pre-commit run --all-files"                 # Run pre-commit hooks
emergency-fix = "pixi run lint-fix && pixi run format && pixi run test"  # Emergency CI fix
```

**See Current Implementation**: Check this project's `pyproject.toml` for the actual working configuration that prevents CI failures.

## 🎯 **WHEN TO USE THIS APPROACH**

**✅ Use Tiered Quality Features when:**
- Starting new projects
- Projects with CI performance issues
- Teams wanting granular quality control
- Projects with complex dependency trees
- Working with the latest pixi best practices

**❌ Keep existing approach when:**
- Project is already stable with current setup
- Team prefers comprehensive tooling by default
- Migration cost outweighs benefits
- Using legacy systems that depend on specific configurations

## 🏗️ **TIERED ARCHITECTURE**

### **TIER 1: Essential Quality Gates (ZERO-TOLERANCE)**
**Feature**: `quality`  
**Purpose**: Absolute minimum tools that must pass

```toml
[tool.pixi.feature.quality.dependencies]
# Core Testing Framework
pytest = ">=8.0.0"
pytest-cov = ">=4.0.0"
pytest-timeout = ">=2.1.0"
pytest-asyncio = ">=0.21.0"
pytest-xdist = ">=3.3.0"

# Linting & Formatting
ruff = ">=0.7.3"

# Type Checking
pyright = ">=1.1.402"
```

**Commands that use this tier:**
- `pixi run test` - Must pass 100%
- `pixi run lint` - Zero F,E9 violations
- `pixi run typecheck` - Zero type errors
- `pixi run quality` - Combined check

### **TIER 2: Extended Quality & Security**
**Feature**: `quality-extended`  
**Purpose**: Additional quality and security tools

```toml
[tool.pixi.feature.quality-extended.dependencies]
# Security Scanning
bandit = ">=1.7.0"
safety = ">=2.3.0"

# Code Quality Analysis
hypothesis = ">=6.0.0"

# Git Hooks
pre-commit = ">=3.0.0"
```

**Commands that use this tier:**
- `pixi run security-scan` - Vulnerability scanning
- `pixi run safety-check` - Dependency security
- `pixi run pre-commit` - Git hooks

### **TIER 3: CI/CD & Build**
**Feature**: `quality-ci`  
**Purpose**: Build, deployment, and CI-specific tools

```toml
[tool.pixi.feature.quality-ci.dependencies]
# Build Tools
python-build = ">=1.0.0"
pip-audit = ">=2.6.0"
twine = ">=4.0.0"

# CI Reporting
coverage = ">=7.0.0"
```

**Commands that use this tier:**
- `pixi run build` - Package building
- `pixi run ci-test` - CI-optimized testing
- `pixi run ci-lint` - CI-optimized linting

## 🌍 **ENVIRONMENT STRATEGY**

### **Environment Definitions**
```toml
[tool.pixi.environments]
# Basic runtime environment
default = {solve-group = "default"}

# Quality gate environments (tiered approach)
quality = {features = ["quality"], solve-group = "default"}
quality-extended = {features = ["quality", "quality-extended"], solve-group = "default"}
quality-full = {features = ["quality", "quality-extended", "quality-ci"], solve-group = "default"}

# Development environment (full quality + specialized tools)
dev = {features = ["quality", "quality-extended", "quality-ci", "dev-specialized"], solve-group = "default"}

# CI environment (quality + CI reporting)
ci = {features = ["quality", "quality-ci"], solve-group = "default"}
```

### **Environment Usage Patterns**

**Local Development:**
```bash
# Quick development cycle
pixi run test                           # Uses default + quality features
pixi run lint                           # Fast critical checks

# Extended quality assurance
pixi run -e quality-extended security-scan    # Security analysis
pixi run -e quality-extended pre-commit       # Full pre-commit suite
```

**CI/CD Pipelines:**
```bash
# CI-optimized testing (faster, targeted)
pixi run -e ci ci-test                  # CI environment with coverage
pixi run -e ci ci-lint                  # CI-formatted output

# Full validation (comprehensive)
pixi run -e quality-full check-all     # Complete validation pipeline
```

**Development Workflows:**
```bash
# Full development environment
pixi run -e dev benchmark               # Performance testing
pixi run -e dev test-coverage          # Comprehensive coverage
```

## 📊 **PERFORMANCE COMPARISON**

### **Installation Time**
| Environment | Dependencies | Install Time | Use Case |
|-------------|--------------|--------------|----------|
| `default` | 5-10 | ~30s | Runtime only |
| `quality` | 15-20 | ~90s | Essential quality |
| `quality-extended` | 25-30 | ~150s | Full quality |
| `quality-full` | 35-40 | ~200s | Complete pipeline |
| `dev` | 45-50 | ~250s | Full development |

### **CI Pipeline Optimization**
```yaml
# Before: Single large environment
- run: pixi install -e dev              # 250s, 45-50 packages
- run: pixi run -e dev quality          # Uses all packages

# After: Targeted environments
- run: pixi install -e ci               # 120s, 25-30 packages
- run: pixi run -e ci quality           # Uses only needed packages
```

## 🔧 **MIGRATION GUIDE**

### **Step 1: Assess Current Setup**
```bash
# Check current environment complexity
pixi list
pixi info

# Identify which tools are actually used
pixi run quality --dry-run
```

### **Step 2: Create Tiered Features**
```bash
# Copy the tiered template
cp .claude/commands/references/AG_pyproject_tiered_template.toml pyproject.toml

# Update project-specific fields
# - name, version, description
# - dependencies matching your needs
# - authors, repository URLs
```

### **Step 3: Test Migration**
```bash
# Test basic functionality
pixi install -e quality
pixi run test
pixi run lint
pixi run typecheck

# Test extended features
pixi install -e quality-extended
pixi run security-scan
pixi run pre-commit

# Test CI environment
pixi install -e ci
pixi run ci-test
```

### **Step 4: Update CI Configuration**
```yaml
# Update GitHub Actions to use ci environment
- name: Setup pixi
  uses: prefix-dev/setup-pixi@v0.8.11
  with:
    pixi-version: v0.49.0
    cache: true
    manifest-path: pyproject.toml

- name: Install dependencies
  run: pixi install -e ci              # Much faster than full dev

- name: Run quality pipeline
  run: pixi run -e ci quality
```

## 🎛️ **CUSTOMIZATION EXAMPLES**

### **Adding Project-Specific Tools**
```toml
# Add tools to appropriate tiers
[tool.pixi.feature.quality-extended.dependencies]
# Add your project-specific security tools
semgrep = ">=1.45.0"
vulture = ">=2.7.0"  # Dead code detection

[tool.pixi.feature.quality-ci.dependencies]
# Add deployment tools
docker = ">=6.0.0"
kubernetes = ">=28.0.0"
```

### **Custom Environments**
```toml
[tool.pixi.environments]
# Standard tiered environments
quality = {features = ["quality"], solve-group = "default"}
quality-extended = {features = ["quality", "quality-extended"], solve-group = "default"}

# Project-specific environments
performance = {features = ["quality", "dev-specialized"], solve-group = "perf"}
security = {features = ["quality", "quality-extended"], solve-group = "security"}
```

### **Task Customization**
```toml
[tool.pixi.tasks]
# Standard tasks (keep these names for AG compatibility)
test = "pytest tests/ -v"
lint = "ruff check src/ tests/ --select=F,E9"
quality = { depends-on = ["test", "lint", "typecheck"] }

# Project-specific tasks
test-performance = "pytest tests/ -m performance --benchmark-only"
security-full = { depends-on = ["security-scan", "safety-check", "audit"] }
```

## 🚀 **BENEFITS OF TIERED APPROACH**

### **1. Performance Gains**
- **50% faster CI installations** (ci environment vs dev environment)
- **Reduced dependency conflicts** with smaller, focused environments
- **Faster local development** with minimal essential tools

### **2. Scalability**
- **Gradual quality adoption** - start with Tier 1, add tiers as needed
- **Team-specific environments** - different teams can use different tiers
- **Project lifecycle support** - different tiers for different project phases

### **3. Maintainability**
- **Clear separation of concerns** - each tier has specific purpose
- **Easier dependency management** - conflicts isolated to specific tiers
- **Simplified troubleshooting** - issues contained within tiers

### **4. CI/CD Optimization**
- **Targeted testing** - only install tools needed for specific checks
- **Parallel pipeline support** - different jobs can use different tiers
- **Cost reduction** - faster CI runs reduce compute costs

## 📈 **ADOPTION STRATEGY**

### **Phase 1: New Projects (Immediate)**
- Use tiered template for all new projects
- Establish team familiarity with tiered approach
- Collect feedback and optimize configurations

### **Phase 2: Existing Projects (Gradual)**
- Migrate high-impact projects with CI performance issues
- Projects with complex dependency trees
- Projects preparing for major version updates

### **Phase 3: Organization-wide (Long-term)**
- Standardize on tiered approach across all projects
- Develop organization-specific tier definitions
- Create automated migration tools

## ⚠️ **COMPATIBILITY NOTES**

### **AG Command Compatibility**
All AG commands remain fully compatible:
- `test`, `lint`, `typecheck`, `pre-commit`, `quality`, `check-all` task names preserved
- Command behavior identical to previous approach
- Quality standards maintained across all tiers

### **Existing Project Safety**
- Original `AG_pyproject_template_guide.md` remains unchanged
- Existing projects continue to work without modification
- Migration is opt-in, not forced

### **Tool Compatibility**
- All existing quality tools supported
- Tool versions maintained at proven levels
- No breaking changes to tool configurations

## 🔄 **MAINTENANCE**

### **Updating Tier Definitions**
```bash
# Test new tool versions in isolation
pixi install -e quality
pixi run quality

# Update specific tiers as needed
# Always test tier combinations
pixi install -e quality-extended
pixi run check-all
```

### **Version Management**
- Update `AG_pyproject_tiered_template.toml` when new tools are proven
- Maintain backward compatibility with existing projects
- Document changes with clear migration paths

---

## 🎯 **CONCLUSION**

The Tiered Quality Features approach provides a modern, scalable solution for quality management in Python projects. It maintains all the quality standards of the original approach while providing significant performance and maintainability benefits.

**Key Takeaways:**
- Use for new projects immediately
- Migrate existing projects gradually
- Maintain team standards while improving efficiency
- Preserve AG command compatibility

This approach represents the evolution of Python project quality management, balancing comprehensive tooling with practical performance considerations.

---

## 🔧 **CLAUDE CODE INTEGRATION**

### **CLAUDECODE=0 Git Bypass Pattern**

When working in Claude Code environments, git access is redirected through MCP tools. For tasks that need direct git access (tests, pre-commit hooks), use the `CLAUDECODE=0` bypass pattern:

```toml
# ✅ PREFERRED: Modern pixi task-level environment variables (RECOMMENDED)
test = { cmd = "python -m pytest tests/ -v", env = { CLAUDECODE = "0" } }
test-cov = { cmd = "python -m pytest tests/ --cov=src/aider_mcp_server --cov-report=term-missing --cov-report=xml", env = { CLAUDECODE = "0" } }
pre-commit = { cmd = "pre-commit run --all-files", env = { CLAUDECODE = "0" } }
ci-test = { cmd = "python -m pytest tests/ --cov=src/aider_mcp_server --cov-report=xml --timeout=90", env = { CLAUDECODE = "0" } }

# ✅ LEGACY: Bash export pattern (still supported, but verbose)
test = "bash -c 'export CLAUDECODE=${CLAUDECODE:-0}; python -m pytest tests/ -v'"
test-cov = "bash -c 'export CLAUDECODE=${CLAUDECODE:-0}; python -m pytest tests/ --cov=src/aider_mcp_server --cov-report=term-missing --cov-report=xml'"
pre-commit = "bash -c 'export CLAUDECODE=${CLAUDECODE:-0}; pre-commit run --all-files'"

# ❌ AVOID: Direct commands that fail in Claude Code
test = "python -m pytest tests/ -v"                    # Fails: git redirector blocks subprocess git access
pre-commit = "pre-commit run --all-files"              # Fails: pre-commit needs direct git access
```

### **How the Pattern Works**

**Modern Approach (Task-Level Environment Variables):**
1. **In Claude Code**: `CLAUDECODE = "0"` explicitly set, enables git bypass  
2. **In Standard Environments**: `CLAUDECODE = "0"` has no effect (git works normally)
3. **When Explicitly Set**: `CLAUDECODE=1` in shell overrides task setting, forces MCP tool usage

**Legacy Approach (Bash Export Pattern):**
1. **In Claude Code**: `CLAUDECODE` is undefined, defaults to `0`, enables git bypass
2. **In Standard Environments**: `CLAUDECODE` is undefined, defaults to `0`, no effect (git works normally)  
3. **When Explicitly Set**: `CLAUDECODE=1` forces MCP tool usage

```bash
# Legacy environment variable behavior
export CLAUDECODE=${CLAUDECODE:-0}    # If undefined, set to 0
                                       # If defined, keep existing value
```

### **Claude Code Compatibility Checklist**

When setting up pixi tasks for Claude Code compatibility:

- ✅ **Git-dependent tasks**: Use `CLAUDECODE=0` pattern
  - Tests that access git repositories
  - Pre-commit hooks
  - CI tasks that need git access
  - Development tasks using git commands

- ✅ **Non-git tasks**: Use standard commands
  - Linting (ruff, mypy)
  - Formatting (ruff format)
  - Security scans (bandit, safety)
  - Package building

- ✅ **Test environment variables**: Use modern pixi task-level env vars
  ```toml
  # ✅ PREFERRED: Modern pixi task-level environment variables
  test = { cmd = "python -m pytest tests/ -v", env = { CLAUDECODE = "0" } }
  
  # ✅ LEGACY: Bash export pattern (still supported)
  test = "bash -c 'export CLAUDECODE=${CLAUDECODE:-0}; python -m pytest tests/ -v'"
  ```

### **Benefits of This Approach**

**Modern Task-Level Environment Variables:**
1. **Universal Compatibility**: Works in both Claude Code and standard environments
2. **No Manual Setup**: Developers don't need to remember to set environment variables  
3. **CI-Ready**: Defaults work correctly in CI environments
4. **Maintainable**: Clear pattern that's easy to understand and replicate
5. **Clean Syntax**: More readable than bash export patterns
6. **Pixi Native**: Uses built-in pixi features rather than shell workarounds

**Legacy Bash Export Pattern:**
1. **Backward Compatibility**: Works with older pixi versions
2. **Conditional Logic**: Supports `${CLAUDECODE:-0}` default patterns
3. **Shell Integration**: Familiar bash syntax

### **Integration Example**

```toml
[tool.pixi.tasks]
# Standard tasks (no git access needed)
lint = "ruff check src/ tests/ --select=F,E9"
format = "ruff format src/ tests/"
typecheck = "mypy src/"

# Git-dependent tasks (with Claude Code bypass) - MODERN APPROACH
test = { cmd = "python -m pytest tests/ -v", env = { CLAUDECODE = "0" } }
pre-commit = { cmd = "pre-commit run --all-files", env = { CLAUDECODE = "0" } }
install-pre-commit = { cmd = "pre-commit install --install-hooks", env = { CLAUDECODE = "0" } }

# Combined quality check (depends on both types)
quality = { depends-on = ["test", "lint", "typecheck"] }
```

This pattern ensures your pixi tasks work seamlessly across all development environments while maintaining the quality standards and tool compatibility that AG commands expect.