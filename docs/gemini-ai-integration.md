# Gemini AI Integration Guide

## 🤖 Overview

The CI Framework now includes comprehensive Gemini AI integration powered by Google's Gemini CLI GitHub Actions. This provides intelligent code analysis, automated PR reviews, issue triage, and CI failure insights.

## 🚀 Quick Setup

### Prerequisites

1. **Google AI Studio API Key**
   - Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Create a new API key
   - Store it as `GEMINI_API_KEY` in your repository secrets

2. **Enable AI Analysis**
   - Add repository variable: `ENABLE_AI_ANALYSIS` = `true`
   - Optionally set `AI_ANALYSIS_LEVEL` = `basic|standard|comprehensive`

3. **Update Your Workflow**
   - Use CI Framework v1.1.0+ which includes Gemini integration
   - Ensure proper permissions are granted (see below)

### Basic Integration

```yaml
# .github/workflows/ci.yml
name: CI with AI Analysis

uses: Claire-s-Monster/ci-framework/.github/workflows/reusable-ci.yml@v1.1.0
with:
  tier: 'comprehensive'
  enable-ai-analysis: true  # Enable AI-powered insights

secrets:
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}  # Required for AI analysis
```

## 🎯 Features

### 1. Automated PR Reviews

**Triggers**: Pull request opened, updated, or reopened

**Analysis Includes**:
- Code quality and best practices assessment
- Security vulnerability identification
- Performance impact analysis
- Test coverage and quality evaluation
- Architecture and design review
- Integration with CI results

**Output**: Detailed comment on PR with ratings and specific recommendations

### 2. Intelligent Issue Triage

**Triggers**: New issues opened

**Capabilities**:
- Automatic classification (bug/feature/documentation/question)
- Priority assignment (critical/high/medium/low)
- Area labeling (ci-framework/actions/security/performance)
- Complexity estimation (simple/moderate/complex)
- Team assignment suggestions

**Output**: Labels applied and initial response comment

### 3. Comprehensive Analysis

**Triggers**: Manual workflow dispatch

**Analysis Types**:
- `pr-review`: Focused PR analysis
- `security-analysis`: Deep security assessment
- `performance-analysis`: Performance optimization insights
- `comprehensive`: Full project analysis

**Usage**:
```bash
# Trigger comprehensive analysis
gh workflow run gemini-ai-analysis.yml -f analysis_type=comprehensive

# Security-focused analysis on specific area
gh workflow run gemini-ai-analysis.yml \
  -f analysis_type=security-analysis \
  -f focus_area=src/security

# Custom analysis with specific prompt
gh workflow run gemini-ai-analysis.yml \
  -f analysis_type=comprehensive \
  -f prompt="Analyze this codebase for scalability issues"
```

### 4. CI Failure Analysis

**Triggers**: When main CI workflow fails (future feature)

**Capabilities**:
- Root cause analysis of CI failures
- Fix suggestions and recommendations
- Prevention strategies
- GitHub issue creation with action items

## 🔧 Configuration

### Repository Settings

#### Required Secrets
```
GEMINI_API_KEY     # Google AI Studio API key
```

#### Required Variables
```
ENABLE_AI_ANALYSIS=true    # Enable AI analysis features
```

#### Optional Variables
```
AI_ANALYSIS_LEVEL=standard      # basic|standard|comprehensive
GEMINI_MODEL=gemini-2.0-flash-exp  # AI model to use
```

#### Required Permissions

Add to your workflow file:
```yaml
permissions:
  contents: read          # Read repository content
  pull-requests: write    # Comment on PRs
  issues: write          # Create and label issues
  actions: read          # Access workflow information
```

### Advanced Configuration

#### Custom Analysis Prompts

Create `.github/gemini-prompts.yml`:
```yaml
pr_review: |
  Focus on security, performance, and maintainability.
  Consider the impact on CI/CD pipeline efficiency.
  Provide specific, actionable recommendations.

issue_triage: |
  Classify based on our project priorities:
  - P0: Security vulnerabilities, CI breakage
  - P1: Major features, significant bugs
  - P2: Minor enhancements, documentation
  - P3: Nice-to-have improvements

security_analysis: |
  Perform comprehensive security assessment:
  - Vulnerability scanning
  - Dependency analysis
  - Code security patterns
  - Supply chain security
```

#### Workflow Integration

```yaml
# Full CI workflow with AI integration
name: Enhanced CI Pipeline

on:
  pull_request:
  push:
    branches: [main]

jobs:
  # Main CI workflow
  ci:
    uses: Claire-s-Monster/ci-framework/.github/workflows/reusable-ci.yml@v1.1.0
    with:
      tier: 'comprehensive'
      enable-ai-analysis: true
    secrets:
      GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}

  # Additional AI analysis (optional)
  ai-deep-dive:
    if: github.event_name == 'pull_request' && contains(github.event.pull_request.labels.*.name, 'ai-review')
    uses: Claire-s-Monster/ci-framework/.github/workflows/gemini-ai-analysis.yml@v1.1.0
    with:
      analysis_type: 'comprehensive'
      focus_area: ${{ github.event.pull_request.changed_files }}
    secrets:
      GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

## 📊 Usage Examples

### Example 1: Basic Project Setup

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  pull_request:
  push:
    branches: [main, develop]

uses: Claire-s-Monster/ci-framework/.github/workflows/reusable-ci.yml@v1.1.0
with:
  tier: 'essential'
  enable-ai-analysis: true

secrets:
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

**Repository Settings**:
- `ENABLE_AI_ANALYSIS` = `true`
- `GEMINI_API_KEY` = `your-api-key`

**Result**:
- Automatic PR reviews on all pull requests
- Issue triage for new issues
- AI insights integrated with CI results

### Example 2: Enterprise Project

```yaml
# .github/workflows/ci.yml
name: Enterprise CI Pipeline

on:
  pull_request:
  push:
    branches: [main, release/*]
  schedule:
    - cron: '0 2 * * *'  # Daily analysis

uses: Claire-s-Monster/ci-framework/.github/workflows/reusable-ci.yml@v1.1.0
with:
  tier: 'extended'
  enable-ai-analysis: true
  security-level: 'critical'
  performance-threshold: '5.0'  # Strict performance requirements

secrets:
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

**Repository Settings**:
- `ENABLE_AI_ANALYSIS` = `true`
- `AI_ANALYSIS_LEVEL` = `comprehensive`
- `GEMINI_MODEL` = `gemini-2.0-flash-exp`

**Result**:
- Comprehensive AI analysis on all changes
- Daily automated code quality reviews
- Security-focused AI insights
- Performance regression analysis

### Example 3: Open Source Project

```yaml
# .github/workflows/ci.yml
name: Community CI

on:
  pull_request:
  push:
    branches: [main]

uses: Claire-s-Monster/ci-framework/.github/workflows/reusable-ci.yml@v1.1.0
with:
  tier: 'comprehensive'
  enable-ai-analysis: ${{ github.event_name == 'pull_request' && github.actor != 'dependabot[bot]' }}

secrets:
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

**Result**:
- AI reviews only for human contributors (not bots)
- Helps maintainers with code review workload
- Consistent quality feedback for contributors

## 🎯 Best Practices

### 1. API Key Management
- Use GitHub repository secrets for `GEMINI_API_KEY`
- Consider organization-level secrets for multiple repositories
- Rotate API keys regularly
- Monitor API usage and quotas

### 2. Analysis Configuration
- Start with `basic` analysis level and increase as needed
- Use `focus_area` parameter for large repositories
- Customize prompts for domain-specific requirements
- Monitor AI analysis quality and adjust prompts

### 3. Workflow Integration
- Enable AI analysis conditionally based on PR size/type
- Use labels to trigger deeper analysis when needed
- Integrate with existing code review processes
- Consider cost implications for high-traffic repositories

### 4. Team Workflow
- Train team on interpreting AI feedback
- Use AI insights to supplement, not replace, human review
- Create feedback loops to improve AI prompts
- Document team-specific analysis requirements

## 🔍 Troubleshooting

### Common Issues

#### API Key Issues
```
Error: Gemini API key not found or invalid
```

**Solution**:
1. Verify `GEMINI_API_KEY` secret is set
2. Check API key permissions in Google AI Studio
3. Ensure API key has not expired

#### Workflow Permission Issues
```
Error: Insufficient permissions to comment on PR
```

**Solution**:
```yaml
permissions:
  contents: read
  pull-requests: write
  issues: write
  actions: read
```

#### Analysis Not Triggering
```
AI analysis steps are skipped
```

**Solution**:
1. Check `ENABLE_AI_ANALYSIS` variable is set to `true`
2. Verify workflow conditions are met
3. Check if PR is from a fork (may need different configuration)

### Debug Mode

Enable detailed logging:
```yaml
env:
  GEMINI_DEBUG: true
  ACTIONS_STEP_DEBUG: true
```

### Support

- **Documentation**: [CI Framework Docs](https://github.com/Claire-s-Monster/ci-framework/docs)
- **Issues**: [Report Issues](https://github.com/Claire-s-Monster/ci-framework/issues)
- **Discussions**: [Community Forum](https://github.com/Claire-s-Monster/ci-framework/discussions)

## 📈 Monitoring & Analytics

### Metrics to Track

- **AI Analysis Success Rate**: Percentage of successful AI analyses
- **Review Quality Score**: Team feedback on AI review usefulness
- **Issue Triage Accuracy**: Correct classification rate
- **Response Time**: Time from trigger to analysis completion

### Cost Management

- **API Usage**: Monitor Google AI Studio usage and billing
- **Analysis Frequency**: Balance insight quality with costs
- **Targeted Analysis**: Use focus areas to reduce token usage

---

## 🎉 Getting Started Checklist

- [ ] Get Google AI Studio API key
- [ ] Add `GEMINI_API_KEY` to repository secrets
- [ ] Set `ENABLE_AI_ANALYSIS=true` in repository variables
- [ ] Update CI workflow to use v1.1.0+ of CI Framework
- [ ] Add required permissions to workflow
- [ ] Test with a sample PR
- [ ] Customize analysis prompts if needed
- [ ] Train team on interpreting AI feedback
- [ ] Monitor usage and adjust configuration

**🎯 Ready to transform your code review process with AI-powered insights!**
