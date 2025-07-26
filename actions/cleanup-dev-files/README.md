# Cleanup Dev Files GitHub Action

Automatically remove development files and artifacts from main branches after PR merge, maintaining clean production branches while preserving development context in feature branches.

## Philosophy

Development files (AI tools, temporary files, caches, editor configs) are valuable during feature development but should be automatically cleaned from production branches to maintain repository hygiene.

## Usage

### Basic Usage

```yaml
name: Cleanup After Merge
on:
  pull_request:
    types: [closed]

jobs:
  cleanup:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.base.ref }}
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Cleanup Development Files
        uses: ./actions/cleanup-dev-files
```

### Advanced Usage

```yaml
name: Comprehensive Cleanup
on:
  pull_request:
    types: [closed]

jobs:
  cleanup:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.base.ref }}
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Cleanup with Custom Patterns
        uses: ./actions/cleanup-dev-files
        with:
          additional_patterns: "custom-cache/,*.debug,local-config.json"
          skip_comment: false
          github_token: ${{ secrets.GITHUB_TOKEN }}
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `additional_patterns` | Additional file patterns to remove (comma-separated) | No | `''` |
| `skip_comment` | Skip adding cleanup comment to PR | No | `'false'` |
| `github_token` | GitHub token for authentication | No | `${{ github.token }}` |

## Outputs

| Output | Description |
|--------|-------------|
| `files_removed` | Number of files/directories removed |
| `cleanup_needed` | Whether cleanup was needed (true/false) |

## Default Cleanup Patterns

The action automatically removes:

### 🤖 AI Development Tools
- `.claude/` - Claude AI development context
- `.mcp.json` - MCP server configurations
- `.taskmaster/` - TaskMaster AI project files
- `.cursor/` - Cursor AI editor configs
- `.aider*` - Aider AI coding assistant files
- `ai_docs/` - AI-generated documentation

### 📁 Development Directories
- `dev-outputs/` - Development output files
- `tmp/` - Temporary directories
- `.vscode/settings.json` - VSCode local settings

### 🗃️ Temporary & OS Files
- `*.dev` - Development files
- `*.tmp` - Temporary files
- `.DS_Store` - macOS metadata
- `Thumbs.db` - Windows thumbnails
- `.idea/` - JetBrains IDE files

## Workflow Integration

### With Reusable Workflow

```yaml
# In your repository's .github/workflows/cleanup.yml
name: Development Cleanup
on:
  pull_request:
    types: [closed]

jobs:
  cleanup:
    uses: ./.github/workflows/reusable-cleanup-dev-files.yml
    with:
      target_branches: "main,master,development"
      additional_patterns: "custom-files/,*.local"
```

### Branch Protection

The action is designed to work with branch protection rules:
- Runs after PR merge
- Commits directly to target branch
- Uses `github-actions[bot]` identity
- Includes descriptive commit messages

## Best Practices

### 1. Target Branch Configuration
Only run on merges to production branches:
```yaml
if: github.event.pull_request.merged == true && contains(fromJSON('["main", "master", "development"]'), github.event.pull_request.base.ref)
```

### 2. Permissions
Ensure workflow has necessary permissions:
```yaml
permissions:
  contents: write
  pull-requests: write
```

### 3. Token Configuration
Use PAT for protected branches:
```yaml
- uses: actions/checkout@v4
  with:
    token: ${{ secrets.ADMIN_TOKEN }}
```

## Examples

### Monorepo Cleanup
```yaml
- name: Cleanup Monorepo Development Files
  uses: ./actions/cleanup-dev-files
  with:
    additional_patterns: "packages/*/dev-outputs,apps/*/tmp,*.local.json"
```

### Security-Conscious Cleanup
```yaml
- name: Security-Focused Cleanup
  uses: ./actions/cleanup-dev-files
  with:
    additional_patterns: ".env.local,.secrets.baseline,debug-logs/"
    skip_comment: true
```

## Automation Benefits

- 🧹 **Clean Production**: Maintains pristine production branches
- 🔄 **Zero Maintenance**: Fully automated, no manual intervention
- 📝 **Full Traceability**: Detailed commit messages and PR comments
- 🛡️ **Safe Operation**: Only removes known development patterns
- 🏃 **Fast Execution**: Minimal overhead, efficient pattern matching

## Integration with CI Framework

This action integrates seamlessly with the CI Framework's development philosophy:
- Complements quality gates and security scanning
- Supports the "relaxed development, clean production" methodology
- Works with all package managers (pixi, poetry, pip)
- Compatible with monorepo and single-project structures