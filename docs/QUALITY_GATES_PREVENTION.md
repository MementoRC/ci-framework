# Quality Gates Prevention Guide

## 🚨 Problem: Lint Violations Reaching CI

The user correctly identified that we're getting lint errors in CI like:
```
Found 13 errors.
[*] 11 fixable with the `--fix` option (1 hidden fix can be enabled with the `--unsafe-fixes` option).
Error: Process completed with exit code 1.
```

This is **unacceptable** and wastes CI time. Code should be clean before commit.

## 🔧 Root Cause Analysis

1. **Pre-commit hooks not installed or not working**
2. **Local quality commands don't match CI exactly**
3. **Developers bypassing quality gates**
4. **Git worktree issues with pre-commit**

## 🛡️ Comprehensive Solution

### 1. Pre-commit Hook Installation (Fixed)

```bash
# Install pre-commit hooks (run this once per developer)
pixi run -e dev bash -c "pre-commit install --install-hooks"

# Or if git worktree issues, install manually:
cd /path/to/main/repo
pre-commit install --install-hooks
```

### 2. Updated Pre-commit Configuration

Our `.pre-commit-config.yaml` includes:
- **Ruff linting** with `--fix` and `--exit-non-zero-on-fix`
- **Ruff formatting** 
- **Standard file checks** (trailing whitespace, yaml, json, etc.)

### 3. Local Quality Commands Match CI

**CI Command**: `pixi run lint-full` → `pixi run -e quality ruff check framework/`

**Local Commands**:
```bash
# Before commit, always run:
pixi run quality           # Comprehensive check (tests + lint + typecheck)
pixi run lint-full         # Full lint check (matches CI)
pixi run lint-fix          # Auto-fix lint issues
pixi run format            # Format code
pixi run pre-commit        # Run all pre-commit hooks
```

### 4. Mandatory Pre-commit Workflow

**NEVER commit without running quality checks**:

```bash
# Recommended pre-commit workflow:
pixi run quality           # Full quality check
pixi run lint-fix          # Auto-fix any lint issues
pixi run format            # Format code
git add .
git commit -m "your message"  # Pre-commit hooks will run automatically
```

### 5. Emergency Fix for Current Issues

If you encounter lint errors in CI:

```bash
# 1. Auto-fix lint issues
pixi run lint-fix

# 2. Check what was fixed
pixi run lint-full

# 3. Commit the fixes
git add .
git commit -m "fix: auto-fix lint violations"
git push
```

## 🔒 Protective Measures

### 1. Pre-commit Hook Enforcement

The pre-commit hooks will:
- **Block commits** with lint violations
- **Auto-fix** fixable issues
- **Require manual fixes** for complex issues

### 2. Local Quality Gate Matching

All local commands now match CI exactly:
- `pixi run lint-full` = CI lint command
- `pixi run typecheck` = CI typecheck command  
- `pixi run test` = CI test command

### 3. Developer Education

**Add to README**:
```markdown
## Development Workflow

Before committing, ALWAYS run:
\`\`\`bash
pixi run quality    # Tests + lint + typecheck
\`\`\`

This ensures your code passes CI checks locally.
```

## 🎯 Implementation Checklist

- [x] Pre-commit hooks configured (`.pre-commit-config.yaml`)
- [x] Local quality commands match CI exactly
- [x] Auto-fix commands available (`lint-fix`, `format`)
- [ ] Pre-commit hooks installed (developer-specific)
- [ ] Developer documentation updated
- [ ] Team training on quality workflow

## 🚀 Benefits

1. **Zero CI failures** from lint violations
2. **Faster development** (catch issues early)
3. **Consistent code quality** across team
4. **Reduced CI time** and costs
5. **Better developer experience** (immediate feedback)

## 📋 Developer Quick Reference

```bash
# Daily workflow
pixi run quality           # Before committing
pixi run lint-fix          # Auto-fix lint issues
pixi run format            # Format code
git add . && git commit    # Pre-commit hooks run automatically

# If pre-commit fails
pixi run lint-full         # See what's failing
pixi run lint-fix          # Fix automatically
pixi run format            # Format code
git add . && git commit    # Try again
```

This prevents the "Found 13 errors" CI failures completely.