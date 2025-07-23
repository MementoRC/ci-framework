# Development Artifacts Cleanup for Production Branches

## Overview

This CI Framework provides an automated solution to keep production branches (main, master, development) clean of development artifacts while preserving them in feature branches for historical reference.

## Philosophy

**Development files should flow like this:**
- ✅ **Feature branches**: Free to commit any development files (CLAUDE.md, .taskmaster/, ai_docs/, etc.)
- ✅ **Feature branches**: Serve as complete development context archives for future reference
- ❌ **Production branches**: Should never contain development artifacts
- ✅ **Automated cleanup**: Removes development artifacts from production branches reliably

## Implementation

### 1. Copy the Cleanup Workflow

Copy `.github/workflows/cleanup-dev-files.yml` to your repository. This workflow:

- **Runs daily at 2 AM UTC** to ensure branches stay clean
- **Supports manual triggers** for immediate cleanup via GitHub Actions UI
- **Handles multiple branches** (main, master, development) automatically
- **Gracefully handles missing branches** without failing

### 2. Supported Development Artifacts (80+ patterns)

The cleanup automatically removes:

#### 🤖 AI Development Tools
- `CLAUDE.md` - AI assistant instructions
- `.claude/` - Claude Code workspace files
- `.taskmaster/` - TaskMaster AI project files
- `ai_docs/` - AI-generated documentation
- `.mcp.json` - MCP server configurations
- `.cursor/` - Cursor editor files
- `.aider*` - Aider AI coding tool files

#### 🐍 Python Development Artifacts
- `__pycache__/`, `*.pyc`, `*.pyo`, `*.pyd` - Python cache files
- `.pytest_cache/` - Pytest cache
- `htmlcov/`, `coverage.xml`, `coverage.json`, `.coverage*` - Coverage reports
- `.mypy_cache/`, `.ruff_cache/` - Type checker and linter caches
- `build/`, `dist/`, `*.egg-info/` - Build artifacts
- `.tox/`, `.nox/` - Testing environment artifacts

#### 📁 Development Directories
- `artifacts/` - Generated test/build artifacts
- `logs/` - Development logs
- `performance_data/` - Performance testing data
- `tmp/`, `debug/`, `.cache/` - Temporary directories

#### 🔧 Editor & IDE Files
- `.vscode/settings.json` - VS Code workspace settings
- `.idea/` - IntelliJ/PyCharm files
- `*.code-workspace` - VS Code workspace files
- `.spyderproject`, `.spyproject` - Spyder IDE files
- `.ropeproject` - Rope refactoring tool files

#### 🗃️ Temporary & OS Files
- `*.tmp`, `*.temp`, `*.dev` - Temporary files
- `*.swp`, `*.swo`, `*~` - Editor temporary files
- `.DS_Store`, `Thumbs.db` - OS-specific files
- `*.bak`, `*.backup`, `*.orig` - Backup files

#### 🔒 Security & Environment
- `.env.local`, `.env.*.local` - Local environment files
- `secrets.json`, `.secrets.baseline` - Secret detection files

#### ⚡ Performance & Profiling
- `performance_data/` - Performance test results
- `.prof`, `*.prof` - Profiling data

#### 📦 Package Manager Artifacts
- `node_modules/` - Node.js dependencies
- `package-lock.json`, `yarn.lock` - Lock files
- `.pixi/envs` - Pixi environment caches

## Usage

### Automatic Cleanup (Recommended)

The workflow runs automatically:
- **Daily at 2 AM UTC** - Ensures branches stay clean
- **Zero configuration** - Just copy the workflow file

### Manual Cleanup (Immediate)

For immediate cleanup:

1. Go to **Actions** tab in your GitHub repository
2. Select **"Cleanup Development Artifacts"** workflow
3. Click **"Run workflow"**
4. Select target branch (main, master, or development)
5. Click **"Run workflow"**

The cleanup will:
- Remove all development artifacts from the selected branch
- Commit the changes with detailed message
- Provide summary report

### Integration with CI/CD

Add to your existing workflows if needed:

```yaml
jobs:
  cleanup:
    uses: ./.github/workflows/cleanup-dev-files.yml
    if: github.ref == 'refs/heads/main'
```

## Customization

### Adding Custom Patterns

Edit the `files_to_remove` array in the workflow:

```bash
files_to_remove=(
  # ... existing patterns ...
  
  # Your custom patterns
  "custom-dev-dir"
  "*.custom-ext"
  ".your-tool-config"
)
```

### Excluding Specific Branches

Modify the matrix strategy:

```yaml
strategy:
  matrix:
    branch: [main, master]  # Remove 'development' if not needed
```

### Changing Schedule

Modify the cron expression:

```yaml
on:
  schedule:
    - cron: '0 6 * * *'  # 6 AM UTC instead of 2 AM
```

## Benefits for Development Teams

### ✅ Relaxed Development Practices
- Commit any development files during feature work
- No need to worry about polluting production branches
- Complete freedom in feature branch development

### ✅ Clean Production Branches
- Main/master/development branches stay pristine
- No development artifacts in production deployments
- Clean repository for new developers

### ✅ Historical Preservation
- Feature branches preserved with complete development context
- Can reference old feature branches for similar work
- Complete audit trail of development process

### ✅ Zero Maintenance
- Automated daily cleanup
- Manual trigger for immediate fixes
- Robust error handling

## Troubleshooting

### Workflow Not Running
- Check that the workflow file is in `.github/workflows/`
- Verify repository has Actions enabled
- Check that the cron schedule hasn't been missed due to repository inactivity

### Cleanup Not Working
- Run manual trigger to test immediately
- Check workflow logs in Actions tab
- Verify file patterns match your development artifacts

### Permission Issues
- Ensure `GITHUB_TOKEN` has write permissions
- Check branch protection rules don't block automated commits

## Example Implementation

See this repository's implementation:
- Workflow: `.github/workflows/cleanup-dev-files.yml`
- Documentation: `docs/examples/development-artifacts-cleanup.md`
- Example usage in CI Framework development

This solution has been battle-tested in AI-assisted development workflows where development artifacts are essential during feature development but must be cleaned from production branches.