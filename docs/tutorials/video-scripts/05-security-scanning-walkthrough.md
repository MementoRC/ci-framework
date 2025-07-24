# Video Tutorial Script: Security Scanning Walkthrough

**Video Title**: "Security Scanning Walkthrough - Multi-Layered Defense with Automated Remediation"  
**Duration**: 6 minutes  
**Target Audience**: Security-conscious developers, DevSecOps teams, compliance teams  
**Objective**: Demonstrate comprehensive security scanning with progressive levels and automated remediation

---

## Pre-Production Checklist

### Setup Requirements
- [ ] Demo project with various security vulnerability types prepared
- [ ] Terminal configured for security scan outputs (may contain sensitive-looking data)
- [ ] GitHub repository with security scanning workflows configured
- [ ] SARIF report viewer ready for GitHub Security tab demonstration
- [ ] Code examples with common vulnerability patterns prepared
- [ ] Screen recording configured to handle security scan timing (variable duration)

### Demo Project Setup with Realistic Vulnerabilities
```bash
cd ~/demo-security-scanning
# Prepare project with common security issues for demonstration:
# - SQL injection patterns
# - Hardcoded secrets (demo only)
# - Dependency vulnerabilities
# - Insecure random number generation
# - Path traversal vulnerabilities
```

---

## Video Script

### Introduction & Security Landscape (0:00-0:45)

**[Visual: News headlines about security breaches and vulnerability statistics]**

**Narrator**: "Security vulnerabilities in Python applications are discovered daily. The average Python project has 15+ security issues that traditional development workflows miss completely. What if your CI pipeline could catch these automatically, before they reach production?"

**[Visual: Framework security scanning dashboard showing comprehensive coverage]**

**Narrator**: "The CI Framework provides a multi-layered security defense system with 4 progressive security levels - from basic vulnerability detection to enterprise-grade compliance scanning. In the next 6 minutes, I'll show you how this system automatically protects your applications while providing clear remediation guidance."

**[Visual: Security scanning architecture showing multiple tools integrated]**

### The 4-Level Security Architecture (0:45-1:30)

**[Visual: Progressive security levels diagram with tool integration]**

**Narrator**: "The security scanning system uses multiple specialized tools in four progressive levels:"

**[Visual: Level 1 - Basic Security with bandit logo]**
**Level 1 - BASIC**: Bandit static analysis for common Python security issues
- Hardcoded passwords and secrets
- SQL injection patterns  
- Shell injection vulnerabilities
- Insecure random number generation

**[Visual: Level 2 - Standard Security with safety + pip-audit logos]**
**Level 2 - STANDARD**: Dependency vulnerability scanning
- Safety database checking against PyUp.io
- pip-audit for Python package vulnerabilities
- Known CVE detection in dependencies
- License compliance checking

**[Visual: Level 3 - Advanced Security with semgrep logo]**
**Level 3 - ADVANCED**: Semgrep for complex security patterns
- Custom security rules for your domain
- Framework-specific vulnerability detection
- Advanced taint analysis
- Business logic security patterns

**[Visual: Level 4 - Critical Security with trivy logo]** 
**Level 4 - CRITICAL**: Trivy for comprehensive security analysis
- Container image vulnerability scanning
- Infrastructure as Code security analysis
- Compliance framework validation (SOC 2, PCI DSS)
- Supply chain security analysis

### Live Demonstration: Basic Level Scanning (1:30-2:45)

**[Visual: Code editor showing a Python file with security vulnerabilities]**

**Narrator**: "Let me demonstrate with a realistic example. Here's code that might pass code review but contains serious security issues:"

```python
import subprocess
import os
from random import random

# Security Issue 1: Hardcoded secret
API_KEY = "sk-1234567890abcdef"  # B105: Hardcoded password

# Security Issue 2: SQL injection vulnerability  
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"  # B608: SQL injection
    return execute_query(query)

# Security Issue 3: Shell injection
def backup_file(filename):
    subprocess.call(f"cp {filename} /backup/", shell=True)  # B602: Shell injection

# Security Issue 4: Insecure random
def generate_token():
    return int(random() * 1000000)  # B311: Insecure random
```

**[Visual: Running basic security scan]**

```bash
# Run basic security level
pixi run security-basic
```

**[Visual: Bandit scan results with clear vulnerability identification]**

```
🔍 Bandit Security Scan Results:

❌ HIGH SEVERITY (4 issues found):
Issue 1: B105:hardcoded_password_string
  - File: src/app.py:4
  - Severity: HIGH  
  - Confidence: MEDIUM
  - Description: Possible hardcoded password 'sk-1234567890abcdef'

❌ MEDIUM SEVERITY (2 issues found):
Issue 2: B608:hardcoded_sql_expressions  
  - File: src/app.py:8
  - Severity: MEDIUM
  - Confidence: MEDIUM
  - Description: Possible SQL injection vector through string formatting

🛠️ Automatic Remediation Available:
Run: pixi run security-fix-basic
```

**[Visual: Automated remediation in action]**

**Narrator**: "The framework doesn't just identify issues - it provides automated remediation where possible:"

```bash
pixi run security-fix-basic
```

**[Visual: Code being automatically fixed]**

```python
import subprocess
import os
from secrets import token_urlsafe

# Fixed: Use environment variable
API_KEY = os.getenv("API_KEY")  # Secure: Environment variable

# Fixed: Parameterized query  
def get_user(user_id):
    query = "SELECT * FROM users WHERE id = %s"  # Secure: Parameterized
    return execute_query(query, (user_id,))

# Fixed: Secure token generation
def generate_token():
    return token_urlsafe(16)  # Secure: Cryptographically secure random
```

### Dependency Vulnerability Scanning (2:45-3:45)

**[Visual: Requirements file with vulnerable dependencies]**

**Narrator**: "Basic code scanning catches obvious issues, but what about vulnerable dependencies? Let's escalate to Standard level scanning:"

```bash
# Run standard security level (includes dependency scanning)
pixi run security-standard
```

**[Visual: Safety and pip-audit running with dependency analysis]**

```
🔍 Dependency Vulnerability Scan Results:

❌ CRITICAL: 3 vulnerabilities found in dependencies

Vulnerability 1: requests 2.25.1
  - CVE: CVE-2023-32681
  - Severity: CRITICAL
  - CVSS Score: 9.1
  - Description: Requests 2.25.1 vulnerable to proxy-authorization header leak
  - Fix: Upgrade to requests >= 2.31.0

Vulnerability 2: pyyaml 5.4.1  
  - CVE: CVE-2023-44487
  - Severity: HIGH
  - CVSS Score: 7.5
  - Description: PyYAML vulnerable to arbitrary code execution
  - Fix: Upgrade to pyyaml >= 6.0.1

🔧 Automated Dependency Updates Available:
Run: pixi run security-update-deps
```

**[Visual: Automated dependency updates]**

```bash
pixi run security-update-deps
```

**[Visual: Package manager updating dependencies safely]**

**Narrator**: "The framework automatically updates vulnerable dependencies while respecting version constraints and testing compatibility. This prevents the common problem of security patches breaking existing functionality."

### GitHub Security Integration (3:45-4:30)

**[Visual: GitHub repository Security tab]**

**Narrator**: "All security scan results are automatically integrated with GitHub's Security tab using SARIF format:"

**[Visual: GitHub Security dashboard showing vulnerability overview]**

- **Code Scanning Alerts**: 4 security issues detected by Bandit
- **Dependabot Alerts**: 3 vulnerable dependencies identified  
- **Secret Scanning**: 1 potential secret detected
- **Security Policy**: Framework security policy automatically applied

**[Visual: Clicking into specific vulnerability for detailed view]**

**Narrator**: "Each vulnerability provides detailed information including:"
- **Severity and confidence levels**
- **Exact file location with code snippet**
- **Remediation guidance with code examples**
- **Links to CVE databases and security advisories**

**[Visual: Remediation workflow integration]**

**Narrator**: "GitHub's interface allows you to create issues, assign remediation tasks, and track security improvements over time - all automatically populated with framework scan data."

### Advanced Security Patterns (4:30-5:15)

**[Visual: More complex code showing business logic vulnerabilities]**

**Narrator**: "For advanced security needs, the framework includes Semgrep for detecting complex security patterns specific to your application domain:"

```python
# Business logic vulnerability - privilege escalation
def update_user_role(user_id, new_role, requesting_user):
    # Missing authorization check - Advanced security rule would catch this
    if new_role == "admin":
        # Should verify requesting_user has admin privileges
        user_service.update_role(user_id, new_role)
```

**[Visual: Advanced security scan results]**

```bash
pixi run security-advanced
```

```
🔍 Semgrep Advanced Security Analysis:

❌ BUSINESS LOGIC VULNERABILITY:
Rule: privilege-escalation-pattern
  - File: src/user_service.py:15
  - Severity: HIGH
  - Pattern: Admin role assignment without authorization check
  - Recommendation: Add privilege verification before role updates

❌ FRAMEWORK-SPECIFIC ISSUE:
Rule: django-sql-injection  
  - File: src/views.py:42
  - Severity: MEDIUM
  - Pattern: Django ORM raw query with user input
  - Recommendation: Use parameterized queries or ORM methods
```

**[Visual: Custom security rules configuration]**

**Narrator**: "You can configure custom Semgrep rules specific to your application's security requirements, frameworks, and business logic patterns."

### Enterprise Compliance Scanning (5:15-6:00)

**[Visual: Enterprise compliance dashboard]**

**Narrator**: "For enterprise environments, the Critical level provides comprehensive compliance scanning:"

```bash
# Run critical security level (full enterprise scanning)
pixi run security-critical
```

**[Visual: Trivy comprehensive security analysis]**

```
🔍 Enterprise Security & Compliance Analysis:

✅ SOC 2 Compliance: 94% compliant (3 issues to address)
✅ PCI DSS Requirements: 89% compliant (5 issues to address)  
✅ Container Security: Base image vulnerabilities detected
✅ Supply Chain Analysis: Dependency integrity verified

📋 Compliance Report Generated:
- Full security assessment: security-report.pdf
- SARIF data: security-results.sarif
- Compliance matrix: compliance-matrix.xlsx

🚨 Critical Issues Requiring Immediate Attention:
1. Cryptographic keys using deprecated algorithms
2. Insufficient logging for audit trail requirements
3. Missing input validation on financial calculation endpoints
```

**[Visual: Comprehensive compliance reporting interface]**

**Narrator**: "The framework generates detailed compliance reports suitable for audit requirements, regulatory submissions, and executive security briefings."

### Conclusion and Implementation (6:00-6:00)

**[Visual: Security scanning summary dashboard showing comprehensive protection]**

**Narrator**: "The multi-layered security scanning system provides comprehensive protection from basic code vulnerabilities to enterprise compliance requirements. Automated remediation reduces security technical debt while clear reporting enables informed risk management decisions."

**[Visual: Quick setup guide]**

**Implementation Steps:**
1. **Add Security Scanning**: `pixi add bandit safety pip-audit`
2. **Configure Security Levels**: Customize scan depth for your needs
3. **Enable GitHub Integration**: Automatic SARIF report generation
4. **Set Up Automated Remediation**: Let the framework fix common issues

**Resources:**
- **Setup Guide**: framework.dev/security-scanning
- **Custom Rules**: framework.dev/security/custom-rules
- **Compliance Matrix**: framework.dev/compliance

---

## Post-Production Considerations

### Sensitive Content Handling
- [ ] **Sanitize Demo Vulnerabilities**: Ensure demo code can't be misused maliciously
- [ ] **Blur Sensitive Information**: Protect any real API keys or credentials that appear
- [ ] **Educational Context**: Clearly label vulnerabilities as educational examples
- [ ] **Responsible Disclosure**: Follow security best practices in examples

### Technical Accuracy
- [ ] **Current CVE Data**: Use up-to-date vulnerability information
- [ ] **Tool Version Accuracy**: Ensure security tools shown match current versions
- [ ] **Compliance Requirements**: Verify compliance standards are accurately represented
- [ ] **Remediation Validity**: Test all automated fixes actually work as shown

### Visual Clarity
- [ ] **Vulnerability Highlighting**: Clear visual indication of security issues
- [ ] **Severity Color Coding**: Consistent color scheme for different severity levels
- [ ] **Report Formatting**: Ensure security reports are readable in video format
- [ ] **GitHub UI Navigation**: Clear demonstration of security tab features

---

## Success Metrics

### Security Awareness
- **Vulnerability Recognition**: Viewers can identify common security patterns
- **Tool Understanding**: Can explain when to use different security scanning levels
- **Remediation Confidence**: Comfortable implementing automated security fixes
- **Compliance Awareness**: Understanding of enterprise security requirements

### Implementation Success
- **Adoption Rate**: >70% implement basic security scanning after viewing
- **Advanced Feature Usage**: >40% use dependency vulnerability scanning
- **Integration Success**: >80% successfully integrate with GitHub Security tab
- **Compliance Interest**: >20% inquire about enterprise compliance features

---

*Script Version: 1.0 | Security Review Required: Yes | Production Complexity: High | Estimated Time: 12-15 hours*