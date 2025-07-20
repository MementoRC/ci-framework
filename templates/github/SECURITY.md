# Security Policy

## Supported Versions

We actively support the following versions of {{ project_name }}:

| Version | Supported          |
| ------- | ------------------ |
| {{ current_version | default('1.x.x') }}   | :white_check_mark: |
| {{ previous_version | default('0.x.x') }}   | {{ previous_support | default(':x:') }} |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security vulnerability, please follow these steps:

### 1. **Do Not** Create a Public Issue

Please **do not** create a public GitHub issue for security vulnerabilities. Public disclosure could put users at risk.

### 2. Contact Us Privately

Send an email to {{ security_email | default('security@organization.com') }} with:

- A clear description of the vulnerability
- Steps to reproduce the issue
- Potential impact assessment
- Any suggested fixes (if available)

### 3. Response Timeline

- **Initial Response**: Within {{ initial_response_time | default('24 hours') }}
- **Assessment**: Within {{ assessment_time | default('72 hours') }}
- **Resolution**: {{ resolution_time | default('30 days maximum') }}

### 4. Disclosure Process

1. We will acknowledge receipt of your report
2. We will investigate and validate the vulnerability
3. We will develop and test a fix
4. We will coordinate the release of the fix
5. We will publicly disclose the vulnerability after the fix is released

## Security Measures

### Automated Security Scanning

This project uses multiple layers of automated security scanning:

- **Dependency Scanning**: {{ dependency_scanner | default('Dependabot') }} for known vulnerabilities
- **Code Analysis**: {{ code_scanner | default('Bandit') }} for Python security issues
- **Secret Detection**: {{ secret_scanner | default('detect-secrets') }} for exposed credentials
- **Supply Chain**: {{ supply_chain_scanner | default('pip-audit') }} for package vulnerabilities

### CI Framework Integration

Security is integrated into our CI/CD pipeline through the CI Framework:

- **Tier 2 Quality Gates**: Security scanning on every pull request
- **Tier 3 Compliance**: Comprehensive security reporting
- **SARIF Integration**: Security findings integrated with GitHub Security tab

### Security Best Practices

We follow these security best practices:

- Minimal dependencies with regular updates
- No credentials in source code
- Input validation and sanitization
- Secure coding guidelines
- Regular security audits

## Vulnerability Management

### Classification

We classify vulnerabilities using the following severity levels:

| Severity | Description | Response Time |
|----------|-------------|---------------|
| **Critical** | Immediate threat to user security | {{ critical_response | default('24 hours') }} |
| **High** | Significant security risk | {{ high_response | default('72 hours') }} |
| **Medium** | Moderate security concern | {{ medium_response | default('1 week') }} |
| **Low** | Minor security issue | {{ low_response | default('2 weeks') }} |

### Remediation Process

1. **Immediate**: Disable affected functionality if necessary
2. **Short-term**: Implement temporary mitigations
3. **Long-term**: Develop and deploy permanent fixes
4. **Follow-up**: Monitor and verify resolution

## Security Updates

### Notification Channels

Security updates are communicated through:

- **GitHub Security Advisories**: For detailed technical information
- **Release Notes**: For user-friendly summaries
- **Security Mailing List**: {{ security_mailing_list | default('security-announce@organization.com') }}

### Update Recommendations

- Monitor our GitHub releases for security updates
- Subscribe to security notifications
- Enable automated dependency updates where possible
- Test security updates in development before production deployment

## Bug Bounty Program

{% if has_bug_bounty %}
We operate a bug bounty program for security researchers:

- **Scope**: {{ bounty_scope | default('Production systems and critical repositories') }}
- **Rewards**: {{ bounty_range | default('$50 - $1000 depending on severity') }}
- **Platform**: {{ bounty_platform | default('Contact security email for details') }}

For more information, contact {{ security_email | default('security@organization.com') }}.
{% else %}
We do not currently operate a formal bug bounty program, but we welcome and appreciate security research. Contact {{ security_email | default('security@organization.com') }} for coordinated disclosure.
{% endif %}

## Compliance

{{ project_name }} is designed to meet or exceed the following security standards:

- **OWASP Top 10**: Mitigations for common web application vulnerabilities
- **CWE/SANS Top 25**: Protection against dangerous software errors
- **{{ compliance_standard | default('Industry Best Practices') }}**: {{ compliance_description | default('Following established security guidelines') }}

## Contact Information

- **Security Team**: {{ security_email | default('security@organization.com') }}
- **General Contact**: {{ general_email | default('contact@organization.com') }}
- **Maintainers**: {{ maintainer_contact | default('See CODEOWNERS file') }}

---

**Last Updated**: {{ last_updated | default('YYYY-MM-DD') }}
**Version**: {{ security_policy_version | default('1.0') }}