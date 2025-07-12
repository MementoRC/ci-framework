
# 🧹 Cleanup Dev Files Action

[![GitHub release](https://img.shields.io/github/release/MementoRC/ci-framework.svg)](https://github.com/MementoRC/ci-framework/releases)
[![GitHub marketplace](https://img.shields.io/badge/marketplace-cleanup--dev--files-blue?logo=github)](https://github.com/marketplace/actions/cleanup-dev-files)
[![CI](https://github.com/MementoRC/ci-framework/workflows/CI/badge.svg)](https://github.com/MementoRC/ci-framework/actions)

A GitHub Action that automatically removes development files from main branches when pull requests are merged, while preserving them in feature branches for developer productivity.

## 🎯 Problem Solved

Ever accidentally merged development configuration files like `.claude`, `.mcp.json`, `.taskmaster`, or `.cursor` into your main branch? This action prevents that by automatically cleaning up these files after PR merges, keeping your production branches clean while maintaining developer workflow flexibility.

## ✨ Features

- 🔧 **Preserves dev files in feature branches** - Developers can use AI tools and configs freely
- 🧹 **Auto-cleanup on main branch merges** - Removes dev files only when merging to production branches
- 📝 **Comprehensive file handling** - Handles AI tools, editor configs, temp files, and OS artifacts
- 🎯 **Smart operation** - Only commits when files are actually removed
- 💬 **PR feedback** - Optional comment confirming cleanup completion
- 🔧 **Customizable patterns** - Add project-specific files to cleanup
- 📊 **Action outputs** - Reports number of files removed and cleanup status

## 🚀 Quick Start

Add this workflow to your repository at `.github/workflows/cleanup-dev-files.yml`:

```yaml
name: Cleanup Dev Files

on:
  pull_request:
    types: [closed]
    branches:
      - main
      - master
      - development

jobs:
  cleanup:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout target branch
        uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.base.ref }}
          token: ${{ secrets.GITHUB_TOKEN }}
          
      - name: Cleanup dev files
        uses: MementoRC/ci-framework@v1
        with:
          additional_patterns: '.env.local,.cache,node_modules/.tmp'
          skip_comment: false
```

## 📖 Usage

### Basic Usage

```yaml
- name: Cleanup dev files
  uses: MementoRC/ci-framework@v1
```

### Advanced Usage

```yaml
- name: Cleanup dev files
  id: cleanup
  uses: MementoRC/ci-framework@v1
  with:
    additional_patterns: '.env.local,.cache,dist/dev,*.log'
    skip_comment: false
    github_token: ${{ secrets.GITHUB_TOKEN }}

- name: Report cleanup results
  run: |
    echo "Files removed: ${{ steps.cleanup.outputs.files_removed }}"
    echo "Cleanup needed: ${{ steps.cleanup.outputs.cleanup_needed }}"
```

## 🔧 Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `additional_patterns` | Additional file patterns to remove (comma-separated) | No | `''` |
| `skip_comment` | Skip adding cleanup comment to PR | No | `false` |
| `github_token` | GitHub token for authentication | No | `${{ github.token }}` |

## 📤 Outputs

| Output | Description |
|--------|-------------|
| `files_removed` | Number of files/directories removed |
| `cleanup_needed` | Whether cleanup was needed (true/false) |

## 🗂️ Default Files Cleaned

The action automatically removes these common development files:

### AI Development Tools
- `.claude` - Claude AI configuration
- `.mcp.json` - Model Context Protocol config
- `.taskmaster` - TaskMaster AI files
- `.cursor` - Cursor editor settings
- `.aider*` - Aider AI tool files

### Development Files
- `*.dev` - Development-specific files
- `*.tmp` - Temporary files
- `dev-outputs/` - Development output directory
- `tmp/` - Temporary directory

### Editor & IDE
- `.vscode/settings.json` - VS Code settings
- `.idea/` - IntelliJ IDEA directory

### System Files
- `.DS_Store` - macOS Finder files
- `Thumbs.db` - Windows thumbnail cache

## 🛠️ Customization Examples

### Node.js Project
```yaml
with:
  additional_patterns: '.env.local,.cache,node_modules/.tmp,dist/dev'
```

### Python Project
```yaml
with:
  additional_patterns: '.env.local,__pycache__/dev,*.pyc,dist/dev'
```

### Go Project
```yaml
with:
  additional_patterns: '.env.local,vendor/dev,*.test,debug'
```

### Rust Project
```yaml
with:
  additional_patterns: '.env.local,target/dev,Cargo.lock.dev'
```

## 🔄 Complete Workflow Examples

### Multi-Branch Support
```yaml
name: Cleanup Dev Files

on:
  pull_request:
    types: [closed]
    branches:
      - main
      - master
      - development
      - staging
      - production

jobs:
  cleanup:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout target branch
        uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.base.ref }}
          token: ${{ secrets.GITHUB_TOKEN }}
          
      - name: Cleanup dev files
        uses: MementoRC/ci-framework@v1
        with:
          additional_patterns: '.env.local,.cache'
```

### With Conditional Logic
```yaml
jobs:
  cleanup:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout target branch
        uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.base.ref }}
          token: ${{ secrets.GITHUB_TOKEN }}
          
      - name: Cleanup dev files
        id: cleanup
        uses: MementoRC/ci-framework@v1
        with:
          additional_patterns: '.env.local,.cache'
          
      - name: Notify team if cleanup occurred
        if: steps.cleanup.outputs.cleanup_needed == 'true'
        run: |
          echo "::notice::Cleaned up ${{ steps.cleanup.outputs.files_removed }} dev files"
```

## 🛡️ Security

- Uses GitHub's built-in token authentication
- Only operates on merged PRs to prevent abuse
- Commits are signed by GitHub Actions bot
- No external dependencies or network calls (except GitHub API)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with real repositories
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by the need to keep production branches clean while maintaining developer productivity
- Built for teams using AI-assisted development tools
- Designed to work with any programming language or framework

---

**Made with ❤️ by the CI Framework Team**

> Keep your main branches clean, your developers happy, and your deployments safe!
