# Security Scan Action API Reference

> **Comprehensive multi-tool security scanning with SARIF integration and configurable security levels**

## Overview

The Security Scan Action provides comprehensive security vulnerability detection through a progressive 4-level security system. It integrates multiple specialized security tools (bandit, safety, pip-audit, semgrep, Trivy) with unified SARIF reporting and automated remediation guidance.

## Action Metadata

| Property | Value |
|----------|-------|
| **Name** | `Security Scan Action` |
| **Description** | Comprehensive multi-tool security scanning with SARIF integration and configurable security levels |
| **Author** | CI Framework |
| **Version** | v0.0.1 |
| **Icon** | shield |
| **Color** | red |

## Usage

```yaml
- uses: ./actions/security-scan
  with:
    security-level: 'medium'
    enable-sarif: 'true'
    enable-bandit: 'true'
    enable-safety: 'true'
```

## API Reference

### Inputs

#### `security-level`
- **Description**: Security level to execute (low, medium, high, critical)
- **Required**: No
- **Default**: `'medium'`
- **Type**: String
- **Valid Values**: `low`, `medium`, `high`, `critical`

**Security Level Characteristics:**
- **Low**: Basic bandit analysis, non-blocking vulnerabilities
- **Medium**: Bandit + safety + pip-audit, fail on vulnerabilities
- **High**: Add semgrep pattern analysis, comprehensive detection
- **Critical**: Add Trivy + SBOM generation, enterprise-grade scanning

#### `timeout`
- **Description**: Timeout in seconds for security scan execution
- **Required**: No
- **Default**: `'600'` (10 minutes)
- **Type**: String (numeric)
- **Example**: `'1200'` for 20 minutes

#### `parallel`
- **Description**: Execute security scans in parallel
- **Required**: No
- **Default**: `'true'`
- **Type**: String (boolean)
- **Valid Values**: `'true'`, `'false'`

#### `project-dir`
- **Description**: Project directory to scan (default: current directory)
- **Required**: No
- **Default**: `'.'`
- **Type**: String
- **Example**: `'./src/my-project'`

#### `config-file`
- **Description**: Path to custom security configuration file
- **Required**: No
- **Default**: `''` (auto-detect)
- **Type**: String
- **Example**: `'./security-config.toml'`

#### `fail-fast`
- **Description**: Fail immediately on first critical vulnerability
- **Required**: No
- **Default**: `'true'`
- **Type**: String (boolean)
- **Valid Values**: `'true'`, `'false'`

#### `reports-dir`
- **Description**: Directory to store security reports
- **Required**: No
- **Default**: `'security-reports'`
- **Type**: String
- **Example**: `'security-analysis'`

#### `package-manager`
- **Description**: Force specific package manager (pixi, poetry, hatch, pip)
- **Required**: No
- **Default**: `'auto'`
- **Type**: String
- **Valid Values**: `'auto'`, `'pixi'`, `'poetry'`, `'hatch'`, `'pip'`

#### Tool Enable/Disable Controls

#### `enable-bandit`
- **Description**: Enable bandit AST-based security analysis
- **Required**: No
- **Default**: `'true'`
- **Type**: String (boolean)

#### `enable-safety`
- **Description**: Enable safety dependency vulnerability scanning
- **Required**: No
- **Default**: `'true'`
- **Type**: String (boolean)

#### `enable-pip-audit`
- **Description**: Enable pip-audit package auditing
- **Required**: No
- **Default**: `'true'`
- **Type**: String (boolean)

#### `enable-semgrep`
- **Description**: Enable semgrep pattern-based security detection
- **Required**: No
- **Default**: `'false'`
- **Type**: String (boolean)

#### `enable-trivy`
- **Description**: Enable Trivy container scanning and SBOM generation
- **Required**: No
- **Default**: `'false'`
- **Type**: String (boolean)

#### Advanced Options

#### `sarif-upload`
- **Description**: Upload SARIF results to GitHub Security tab
- **Required**: No
- **Default**: `'true'`
- **Type**: String (boolean)

#### `sbom-generation`
- **Description**: Generate Software Bill of Materials (SBOM)
- **Required**: No
- **Default**: `'false'`
- **Type**: String (boolean)

### Outputs

#### `success`
- **Description**: Whether all security scans passed
- **Type**: Boolean
- **Example**: `true`

#### `security-level`
- **Description**: Security level that was executed
- **Type**: String
- **Example**: `'medium'`

#### `execution-time`
- **Description**: Total execution time in seconds
- **Type**: Number
- **Example**: `342.78`

#### Vulnerability Counts

#### `vulnerabilities-found`
- **Description**: Total number of vulnerabilities found
- **Type**: Number
- **Example**: `7`

#### `critical-vulnerabilities`
- **Description**: Number of critical vulnerabilities found
- **Type**: Number
- **Example**: `2`

#### `high-vulnerabilities`
- **Description**: Number of high-severity vulnerabilities found
- **Type**: Number
- **Example**: `3`

#### `medium-vulnerabilities`
- **Description**: Number of medium-severity vulnerabilities found
- **Type**: Number
- **Example**: `2`

#### `low-vulnerabilities`
- **Description**: Number of low-severity vulnerabilities found
- **Type**: Number
- **Example**: `0`

#### Tool Execution Results

#### `tools-executed`
- **Description**: List of security tools that were executed (comma-separated)
- **Type**: String
- **Example**: `'bandit,safety,pip-audit'`

#### `failed-tools`
- **Description**: List of security tools that failed (comma-separated)
- **Type**: String
- **Example**: `'semgrep'`

#### `failure-reason`
- **Description**: Primary reason for failure
- **Type**: String
- **Example**: `'Found 2 critical vulnerabilities'`

#### File Outputs

#### `reports-path`
- **Description**: Path to generated security reports
- **Type**: String
- **Example**: `'security-reports'`

#### `sarif-file`
- **Description**: Path to generated SARIF file
- **Type**: String
- **Example**: `'security-reports/security-unified.sarif'`

#### `sbom-file`
- **Description**: Path to generated SBOM file
- **Type**: String
- **Example**: `'security-reports/trivy-sbom.json'`

---

## Configuration

### Project Configuration

Configure security scanning in `pyproject.toml`:

```toml
[tool.ci-framework.security-scan]
# Default security level
default_level = "medium"

# Tool configuration
enable_sarif = true
enable_sbom = false
fail_on_vulnerabilities = true

# Bandit configuration
[tool.ci-framework.security-scan.bandit]
severity_level = "medium"
exclude_paths = ["**/tests/**", "**/test_**"]
skip_checks = ["B101"]  # Allow assert statements

# Safety configuration
[tool.ci-framework.security-scan.safety]
ignore_ids = ["12345"]  # Ignore specific vulnerability IDs

# Semgrep configuration
[tool.ci-framework.security-scan.semgrep]
config = "auto"  # or path to custom rules
exclude_paths = ["tests/"]

# Trivy configuration
[tool.ci-framework.security-scan.trivy]
scan_type = "fs"  # filesystem scan
severity = ["HIGH", "CRITICAL"]
```

### Security Level Definitions

```python
SECURITY_CONFIGS = {
    "low": {
        "required_tools": ["bandit"],
        "fail_on_vulnerabilities": False,
        "timeout_per_tool": 60
    },
    "medium": {
        "required_tools": ["bandit", "safety", "pip-audit"],
        "fail_on_vulnerabilities": True,
        "timeout_per_tool": 120
    },
    "high": {
        "required_tools": ["bandit", "safety", "pip-audit", "semgrep"],
        "fail_on_vulnerabilities": True,
        "timeout_per_tool": 300
    },
    "critical": {
        "required_tools": ["bandit", "safety", "pip-audit", "semgrep", "trivy"],
        "fail_on_vulnerabilities": True,
        "timeout_per_tool": 600
    }
}
```

---

## Usage Examples

### Basic Security Scanning

```yaml
name: Security Check
on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/security-scan
        with:
          security-level: 'medium'
```

### Advanced Security Pipeline

```yaml
name: Comprehensive Security
on:
  push:
    branches: [main, develop]
  pull_request:

jobs:
  security-matrix:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        level: [medium, high, critical]
    steps:
      - uses: actions/checkout@v4
      
      - name: Security Scan - ${{ matrix.level }}
        uses: ./actions/security-scan
        with:
          security-level: ${{ matrix.level }}
          sarif-upload: 'true'
          sbom-generation: ${{ matrix.level == 'critical' && 'true' || 'false' }}
          reports-dir: 'security-${{ matrix.level }}'
```

### Tool-Specific Configuration

```yaml
name: Custom Security Tools
on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Basic Security (Bandit + Safety)
        uses: ./actions/security-scan
        with:
          security-level: 'medium'
          enable-bandit: 'true'
          enable-safety: 'true'
          enable-pip-audit: 'false'
          enable-semgrep: 'false'
          enable-trivy: 'false'
      
      - name: Advanced Security (Add Semgrep)
        if: github.ref == 'refs/heads/main'
        uses: ./actions/security-scan
        with:
          security-level: 'high'
          enable-semgrep: 'true'
          enable-trivy: 'false'
      
      - name: Enterprise Security (Full Suite)
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        uses: ./actions/security-scan
        with:
          security-level: 'critical'
          enable-trivy: 'true'
          sbom-generation: 'true'
```

### Integration with SARIF

```yaml
name: Security with SARIF
on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Security Scan
        uses: ./actions/security-scan
        id: security
        with:
          security-level: 'high'
          sarif-upload: 'true'
      
      - name: Upload SARIF to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        if: always() && steps.security.outputs.sarif-file != ''
        with:
          sarif_file: ${{ steps.security.outputs.sarif-file }}
          category: 'ci-framework-security'
```

### Error Handling and Reporting

```yaml
- uses: ./actions/security-scan
  id: security
  continue-on-error: true
  with:
    security-level: 'medium'

- name: Process Security Results
  if: always()
  run: |
    echo "Security scan completed: ${{ steps.security.outputs.success }}"
    echo "Vulnerabilities found: ${{ steps.security.outputs.vulnerabilities-found }}"
    echo "Critical: ${{ steps.security.outputs.critical-vulnerabilities }}"
    echo "High: ${{ steps.security.outputs.high-vulnerabilities }}"
    echo "Medium: ${{ steps.security.outputs.medium-vulnerabilities }}"
    echo "Tools executed: ${{ steps.security.outputs.tools-executed }}"
    
    if [[ "${{ steps.security.outputs.failed-tools }}" != "" ]]; then
      echo "Failed tools: ${{ steps.security.outputs.failed-tools }}"
    fi
    
    # Fail job if critical vulnerabilities found
    if [[ "${{ steps.security.outputs.critical-vulnerabilities }}" -gt "0" ]]; then
      echo "❌ Critical vulnerabilities found - failing job"
      exit 1
    fi
```

---

## Tool Integration Details

### Bandit (AST Security Analysis)
- **Purpose**: Static analysis of Python code for security issues
- **Detects**: Hardcoded passwords, SQL injection, shell injection, crypto issues
- **Output**: JSON reports with severity levels and confidence scores
- **SARIF**: Native support for GitHub Security integration

### Safety (Dependency Vulnerability Database)
- **Purpose**: Check Python packages against known vulnerabilities
- **Database**: PyUp.io vulnerability database
- **Detects**: Known CVEs in installed packages
- **Output**: JSON reports with CVE details and remediation advice

### pip-audit (Package Auditing)
- **Purpose**: Audit Python packages for known vulnerabilities
- **Database**: PyPI Advisory Database + OSV.dev
- **Detects**: Vulnerabilities in direct and transitive dependencies
- **Output**: JSON reports with vulnerability details and fix versions

### Semgrep (Pattern-Based Analysis)
- **Purpose**: Custom security rules and pattern detection
- **Rules**: Community rules + custom organizational rules
- **Detects**: Complex security patterns, framework-specific issues
- **Output**: JSON + SARIF reports with rule-specific findings

### Trivy (Container & SBOM Scanning)
- **Purpose**: Comprehensive security scanning and SBOM generation
- **Scans**: Filesystem, containers, configuration files
- **Detects**: CVEs, misconfigurations, secrets, licenses
- **Output**: JSON, SARIF, CycloneDX SBOM formats

---

## Integration Patterns

### With Quality Gates

```yaml
jobs:
  quality-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Quality Gates
        uses: ./actions/quality-gates
        id: quality
        with:
          tier: 'extended'
      
      - name: Security Scan
        if: steps.quality.outputs.success == 'true'
        uses: ./actions/security-scan
        with:
          security-level: 'medium'
```

### With Change Detection

```yaml
jobs:
  changes:
    runs-on: ubuntu-latest
    outputs:
      code-changed: ${{ steps.changes.outputs.code-changed }}
      deps-changed: ${{ steps.changes.outputs.deps-changed }}
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/change-detection
        id: changes

  security:
    needs: changes
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/security-scan
        with:
          # Higher security level if dependencies changed
          security-level: ${{ needs.changes.outputs.deps-changed == 'true' && 'high' || 'medium' }}
          enable-safety: ${{ needs.changes.outputs.deps-changed == 'true' && 'true' || 'false' }}
          enable-pip-audit: ${{ needs.changes.outputs.deps-changed == 'true' && 'true' || 'false' }}
```

### Enterprise Compliance

```yaml
name: Enterprise Security Compliance
on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly security scan
  push:
    branches: [main]

jobs:
  compliance-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Critical Security Scan
        uses: ./actions/security-scan
        with:
          security-level: 'critical'
          enable-trivy: 'true'
          sbom-generation: 'true'
          sarif-upload: 'true'
          timeout: '1800'  # 30 minutes for comprehensive scan
      
      - name: Upload SBOM for Compliance
        uses: actions/upload-artifact@v3
        with:
          name: security-sbom-${{ github.sha }}
          path: ${{ steps.security.outputs.sbom-file }}
          retention-days: 365
```

---

## Troubleshooting

### Common Issues

#### Tool Installation Failures
```bash
# Manual tool installation
- name: Install Security Tools
  run: |
    pip install bandit safety pip-audit
    # For Semgrep
    pip install semgrep
    # For Trivy (Ubuntu)
    wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
    echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
    sudo apt-get update && sudo apt-get install trivy
```

#### SARIF Upload Issues
```yaml
- name: Upload SARIF with Error Handling
  uses: github/codeql-action/upload-sarif@v2
  if: always() && steps.security.outputs.sarif-file != ''
  continue-on-error: true
  with:
    sarif_file: ${{ steps.security.outputs.sarif-file }}
```

#### False Positive Management
```yaml
# Configure tool-specific exclusions
- uses: ./actions/security-scan
  with:
    security-level: 'medium'
    config-file: './security-config.toml'
```

```toml
# security-config.toml
[tool.ci-framework.security-scan.bandit]
skip_checks = ["B101", "B601"]  # Skip assert and shell checks

[tool.ci-framework.security-scan.safety]
ignore_ids = ["12345", "67890"]  # Ignore specific CVEs
```

### Performance Optimization

```yaml
# Optimize for different project sizes
- uses: ./actions/security-scan
  with:
    # Small project
    security-level: 'medium'
    timeout: '300'
    parallel: 'true'
    
    # Large project
    # security-level: 'high'
    # timeout: '1800'
    # parallel: 'true'
```

### Debug Information

```yaml
- uses: ./actions/security-scan
  with:
    security-level: 'medium'
  env:
    ACTIONS_STEP_DEBUG: true
    ACTIONS_RUNNER_DEBUG: true
```

---

## Performance Characteristics

### Execution Times by Security Level

| Project Size | Low | Medium | High | Critical |
|--------------|-----|--------|------|----------|
| Small (< 1K files) | 30-60s | 1-2min | 2-4min | 4-8min |
| Medium (1K-10K files) | 1-2min | 3-5min | 6-10min | 12-20min |
| Large (> 10K files) | 2-4min | 8-12min | 15-25min | 25-40min |

### Tool-Specific Performance

| Tool | Typical Runtime | Resource Usage |
|------|----------------|----------------|
| Bandit | 10-60s | Low CPU, <500MB RAM |
| Safety | 5-30s | Network dependent |
| pip-audit | 10-45s | Network dependent |
| Semgrep | 30s-5min | Medium CPU, <1GB RAM |
| Trivy | 1-10min | High CPU, <2GB RAM |

---

## Security Best Practices

### Level Selection Guidelines

- **Development**: Use `medium` level for regular development
- **Pull Requests**: Use `high` level for comprehensive review
- **Production**: Use `critical` level for release validation
- **Scheduled Scans**: Use `critical` level for compliance

### SARIF Integration Best Practices

1. **Always enable SARIF upload** for GitHub Security integration
2. **Use meaningful categories** to organize findings
3. **Configure automatic issue creation** for critical vulnerabilities
4. **Set up security policies** to enforce scan requirements

### SBOM Management

1. **Generate SBOMs** for production releases
2. **Store SBOMs** with long retention periods (365+ days)
2. **Use SBOMs** for vulnerability tracking and compliance
4. **Integrate SBOMs** with dependency management workflows

---

**Action Version**: 0.0.1  
**Last Updated**: January 2025  
**Compatibility**: GitHub Actions v4+, Python 3.10+