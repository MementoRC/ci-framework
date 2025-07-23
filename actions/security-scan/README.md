# Security Scan Action

Comprehensive multi-tool security scanning action with SARIF integration and configurable security levels.

## Overview

This action provides unified security scanning by integrating multiple security tools:

- **bandit** - AST-based security analysis for Python code
- **safety** - Dependency vulnerability scanning
- **pip-audit** - Package auditing for known vulnerabilities  
- **semgrep** - Pattern-based security detection
- **Trivy** - Container scanning and SBOM generation

## Features

- 🔒 **Multi-level Security**: Configurable security levels (low/medium/high/critical)
- 🚀 **Parallel Execution**: Run scans in parallel for faster results
- 📊 **SARIF Integration**: Upload results to GitHub Security tab
- 📦 **SBOM Generation**: Software Bill of Materials for supply chain security
- ⚡ **Fail-fast Mode**: Stop on first critical vulnerability
- 📈 **Comprehensive Reporting**: Detailed vulnerability counts and analysis

## Usage

### Basic Usage

```yaml
- name: Security Scan
  uses: ./actions/security-scan
  with:
    security-level: 'medium'
```

### Advanced Usage

```yaml
- name: Comprehensive Security Scan
  uses: ./actions/security-scan
  with:
    security-level: 'high'
    timeout: 900
    parallel: true
    enable-semgrep: true
    enable-trivy: true
    sarif-upload: true
    sbom-generation: true
    fail-fast: false
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `security-level` | Security level (low/medium/high/critical) | No | `medium` |
| `timeout` | Timeout in seconds | No | `600` |
| `parallel` | Execute scans in parallel | No | `true` |
| `project-dir` | Project directory to scan | No | `.` |
| `config-file` | Custom configuration file | No | `` |
| `fail-fast` | Fail on first critical vulnerability | No | `true` |
| `reports-dir` | Reports output directory | No | `security-reports` |
| `package-manager` | Package manager (auto/pixi/poetry/hatch/pip) | No | `auto` |
| `enable-bandit` | Enable bandit scanning | No | `true` |
| `enable-safety` | Enable safety scanning | No | `true` |
| `enable-pip-audit` | Enable pip-audit scanning | No | `true` |
| `enable-semgrep` | Enable semgrep scanning | No | `false` |
| `enable-trivy` | Enable Trivy scanning | No | `false` |
| `sarif-upload` | Upload SARIF to GitHub Security | No | `true` |
| `sbom-generation` | Generate SBOM | No | `false` |

## Outputs

| Output | Description |
|--------|-------------|
| `success` | Whether all scans passed |
| `security-level` | Security level executed |
| `execution-time` | Total execution time |
| `vulnerabilities-found` | Total vulnerabilities found |
| `critical-vulnerabilities` | Critical vulnerabilities count |
| `high-vulnerabilities` | High vulnerabilities count |
| `medium-vulnerabilities` | Medium vulnerabilities count |
| `low-vulnerabilities` | Low vulnerabilities count |
| `tools-executed` | List of executed tools |
| `failed-tools` | List of failed tools |
| `failure-reason` | Primary failure reason |
| `reports-path` | Path to reports |
| `sarif-file` | Path to SARIF file |
| `sbom-file` | Path to SBOM file |

## Security Levels

### Low
- **Tools**: bandit (low severity)
- **Timeout**: 60s per tool
- **Fail on vulnerabilities**: No
- **Use case**: Development builds, rapid feedback

### Medium (Default)
- **Tools**: bandit, safety, pip-audit
- **Timeout**: 120s per tool  
- **Fail on vulnerabilities**: Yes (critical/high only)
- **Use case**: PR validation, CI pipelines

### High
- **Tools**: bandit, safety, pip-audit, semgrep
- **Timeout**: 300s per tool
- **Fail on vulnerabilities**: Yes
- **Use case**: Release builds, security audits

### Critical
- **Tools**: bandit, safety, pip-audit, semgrep, Trivy
- **Timeout**: 600s per tool
- **Fail on vulnerabilities**: Yes (strict thresholds)
- **Use case**: Production deployments, compliance

## Integration Examples

### Standard CI Pipeline

```yaml
name: CI Pipeline
on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Security Scan
        uses: ./actions/security-scan
        with:
          security-level: 'medium'
          sarif-upload: true
        
      - name: Upload Security Reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: security-reports
          path: security-reports/
```

### Release Pipeline with Full Security

```yaml
name: Release Pipeline
on:
  push:
    tags: ['v*']

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Comprehensive Security Scan
        uses: ./actions/security-scan
        with:
          security-level: 'critical'
          enable-semgrep: true
          enable-trivy: true
          sbom-generation: true
          timeout: 1200
```

### Matrix Testing with Different Security Levels

```yaml
name: Security Matrix
on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        security-level: [low, medium, high]
    steps:
      - uses: actions/checkout@v4
      
      - name: Security Scan - ${{ matrix.security-level }}
        uses: ./actions/security-scan
        with:
          security-level: ${{ matrix.security-level }}
```

## Output Artifacts

The action generates several artifacts:

### Security Reports
- `bandit-results.json` - Bandit scan results
- `safety-results.json` - Safety vulnerability results  
- `pip-audit-results.json` - Pip-audit findings
- `semgrep-results.json` - Semgrep pattern matches
- `trivy-results.json` - Trivy scan results

### SARIF Files
- `bandit.sarif` - Bandit SARIF format
- `semgrep.sarif` - Semgrep SARIF format
- `trivy.sarif` - Trivy SARIF format
- `security-unified.sarif` - Combined SARIF report

### SBOM Files  
- `trivy-sbom.json` - Software Bill of Materials

## Troubleshooting

### Common Issues

#### Tool Installation Failures
```yaml
- name: Pre-install Security Tools
  run: |
    pip install bandit safety pip-audit
    # For semgrep: pip install semgrep
    # For trivy: see installation steps in action
```

#### Timeout Issues
```yaml
- name: Security Scan with Extended Timeout
  uses: ./actions/security-scan
  with:
    timeout: 1200  # 20 minutes
    parallel: false  # Sequential for debugging
```

#### SARIF Upload Failures
```yaml
- name: Security Scan without SARIF
  uses: ./actions/security-scan
  with:
    sarif-upload: false  # Disable if issues
```

### Configuration Files

#### Custom Bandit Configuration
Create `.bandit` in project root:
```yaml
exclude_dirs:
  - tests/
  - test_*
skips:
  - B101  # Skip assert statements
```

#### Custom Safety Policy
Create `.safety-policy.json`:
```json
{
  "ignore": {
    "12345": {
      "reason": "False positive in test environment"
    }
  }
}
```

## Security Best Practices

1. **Progressive Security**: Start with `low` level, gradually increase
2. **Tool Selection**: Enable additional tools based on project needs
3. **SARIF Integration**: Always upload SARIF for GitHub Security tab
4. **SBOM Generation**: Enable for supply chain visibility
5. **Regular Updates**: Keep security tools updated
6. **Baseline Management**: Track and approve acceptable vulnerabilities

## Contributing

When contributing to this action:

1. Test all security levels
2. Validate SARIF output format
3. Ensure backward compatibility
4. Update documentation for new features
5. Add integration tests for new tools

## Changelog

### v0.0.1
- Initial implementation
- Multi-tool integration (bandit, safety, pip-audit, semgrep, Trivy)
- Configurable security levels
- SARIF output support
- SBOM generation
- Parallel execution support