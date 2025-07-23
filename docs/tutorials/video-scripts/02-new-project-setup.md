# Video Tutorial Script: New Project Setup

**Video Title**: "New Python Project Setup - Production-Ready CI/CD in 2 Minutes"  
**Duration**: 3 minutes  
**Target Audience**: Developers starting new Python projects  
**Objective**: Demonstrate fastest path from zero to production-ready project

---

## Pre-Production Checklist

### Setup Requirements
- [ ] Clean desktop with no distracting windows
- [ ] Terminal configured with clear, large font
- [ ] GitHub CLI authenticated and ready
- [ ] Code editor (VS Code) ready for demonstration
- [ ] Timer/stopwatch for real-time demonstration
- [ ] Screen recording at 1920x1080, 30fps

### Demo Preparation
```bash
# Clean workspace
cd ~/Desktop
rm -rf demo-new-project 2>/dev/null || true
# Ensure GitHub CLI is authenticated
gh auth status
# Prepare environment
export DEMO_PROJECT_NAME="my-awesome-project"
```

---

## Video Script

### Introduction (0:00-0:20)

**[Visual: Split screen - blank desktop vs completed project with CI badges]**

**Narrator**: "Starting a new Python project? In the next 3 minutes, I'll show you how to go from empty folder to production-ready project with complete CI/CD pipeline. We're timing this - let's see if we can beat the 2-minute target."

**[Visual: Timer starts counting: 00:00]**

### Option A: Template Method (0:20-1:00)

**[Visual: Full-screen terminal with clear, large font]**

**Narrator**: "First, the fastest method - using our project template. This takes about 30 seconds."

**[Visual: Terminal commands with real-time execution]**

```bash
# Step 1: Clone the template
git clone https://github.com/MementoRC/ci-framework-template my-awesome-project
cd my-awesome-project
```

**[Visual: Files appearing as they're cloned, showing timer: 00:15]**

**Narrator**: "Now customize it for our project:"

```bash
# Step 2: Run the setup script
./setup-new-project.sh "My Awesome Project" "my-awesome-package"
```

**[Visual: Setup script running with progress indicators, timer: 00:25]**

**Narrator**: "And create the GitHub repository:"

```bash
# Step 3: Push to GitHub
gh repo create my-awesome-project --public --push
```

**[Visual: GitHub creation success message, timer: 00:30]**

**Narrator**: "Done! 30 seconds from zero to GitHub repository with complete CI. Let's verify everything works."

### Validation and First Run (1:00-1:45)

**[Visual: Split screen - terminal on left, browser on right]**

**Narrator**: "Let's test our setup locally first:"

```bash
# Test the local quality pipeline
pixi run quality
```

**[Visual: Quality checks running - tests, lint, type checking all passing in green]**

**Narrator**: "Perfect! All quality gates pass. Now let's see the CI pipeline in action:"

**[Visual: Browser showing GitHub repository]**

**Narrator**: "Our first commit already triggered the CI pipeline. Look at these workflow jobs running:"

**[Visual: GitHub Actions tab showing running workflows]**
- Quality Gates (Essential Tier)
- Security Scanning  
- Performance Benchmarking
- Change Detection Baseline

**[Visual: Timer showing 01:15 as workflows complete successfully]**

**Narrator**: "All green! We have a fully functional CI/CD pipeline in under 90 seconds."

### Project Structure Walkthrough (1:45-2:30)

**[Visual: Code editor showing project structure]**

**Narrator**: "Let's explore what we got. The template includes everything you need:"

**[Visual: File explorer showing generated structure]**

```
my-awesome-project/
├── src/my_awesome_package/          # Your main package
│   ├── __init__.py
│   └── main.py                      # Sample implementation
├── tests/                           # Test structure ready
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── .github/workflows/               # Complete CI/CD pipeline
│   ├── ci.yml                       # Main quality pipeline
│   ├── security.yml                 # Security scanning
│   └── performance.yml              # Performance monitoring
├── pyproject.toml                   # Optimized pixi configuration
├── .pre-commit-config.yaml          # Quality hooks
└── README.md                        # Professional documentation
```

**[Visual: Opening pyproject.toml to show configuration]**

**Narrator**: "The pixi configuration includes our proven 3-tier quality system:"

```toml
[tool.pixi.tasks]
test = "pytest tests/ -v"
lint = "ruff check src/ tests/ --select=F,E9"  # Zero-tolerance
typecheck = "mypy src/"
quality = { depends-on = ["test", "lint", "typecheck"] }
```

**[Visual: Opening GitHub workflow file]**

**Narrator**: "And the GitHub workflow uses our reusable actions for consistency:"

```yaml
jobs:
  quality-gates:
    uses: MementoRC/ci-framework/.github/workflows/python-ci.yml@main
    with:
      quality-level: "essential"
      python-versions: "3.10,3.11,3.12"
```

### Making Your First Change (2:30-2:50)

**[Visual: Code editor with simple code change]**

**Narrator**: "Let's make a simple change to see the pipeline in action:"

```python
# Edit src/my_awesome_package/main.py
def hello_world():
    return "Hello from My Awesome Project!"
```

**[Visual: Terminal showing commit and push]**

```bash
git add .
git commit -m "Add hello world function"
git push
```

**[Visual: GitHub showing new workflow triggered, with change detection optimization]**

**Narrator**: "Notice how change detection optimizes this run - it detected this is a simple code change and ran the essential tier only, completing in under 2 minutes instead of the full 10-minute suite."

### Wrap-up and Next Steps (2:50-3:00)

**[Visual: Timer showing final time: 02:45, GitHub repository with green badges]**

**Narrator**: "In under 3 minutes, we've created a production-ready Python project with comprehensive CI/CD. Your next steps: add your actual code, customize the quality rules for your team, and start building amazing things!"

**[Visual: Links appearing on screen]**
- "Documentation: framework.dev/docs"
- "Advanced setup: framework.dev/tutorials"
- "Community: github.com/MementoRC/ci-framework/discussions"

---

## Alternative Script: Manual Method (Optional B-roll)

### When to Use
For viewers who prefer understanding each step individually or have specific customization needs.

### Script Addition (1:00-2:00, replacing template method)

**Narrator**: "Prefer to understand each step? Here's the manual approach:"

```bash
# Step 1: Create project structure (15 seconds)
mkdir my-awesome-project && cd my-awesome-project
git init
mkdir -p src/my_awesome_package tests docs
touch src/my_awesome_package/__init__.py tests/__init__.py README.md

# Step 2: Add CI Framework (30 seconds)
curl -sSL https://raw.githubusercontent.com/MementoRC/ci-framework/main/scripts/quick-setup.sh | bash

# Step 3: Initialize pixi (15 seconds)
pixi init
pixi add pytest ruff mypy

# Step 4: Apply framework configuration (30 seconds)
cp .ci-framework/templates/pyproject-template.toml pyproject.toml
cp .ci-framework/templates/pre-commit-config.yaml .pre-commit-config.yaml
mkdir -p .github/workflows
cp .ci-framework/workflows/python-ci-template.yml .github/workflows/ci.yml
```

**[Visual: Each command executing with file creation visible]**

---

## Post-Production Notes

### Visual Enhancements
- [ ] **Timer Overlay**: Constant timer in corner showing real execution time
- [ ] **Progress Indicators**: Visual progress bars during long operations
- [ ] **Highlight Effects**: Subtle highlighting of key files as they're created
- [ ] **Split Screens**: Show multiple perspectives (terminal + browser + editor)
- [ ] **Color Coding**: Green for success, blue for information, red for attention

### Audio Considerations
- [ ] **Pacing**: Allow brief pauses for viewers to process information
- [ ] **Emphasis**: Stress key timing achievements ("under 30 seconds", "2-minute pipeline")
- [ ] **Energy**: Maintain excitement about speed and efficiency gains
- [ ] **Clarity**: Ensure technical terms are pronounced clearly

### Accessibility Features
- [ ] **Captions**: Accurate technical terminology in captions
- [ ] **Audio Description**: Describe visual file structure and UI elements
- [ ] **Contrast**: Ensure terminal and code have high contrast for visibility
- [ ] **Font Size**: Use large, readable fonts throughout

---

## Success Metrics & Goals

### Primary KPIs
- **Completion Rate**: Target >85% watch to end
- **Setup Success Rate**: >95% successful project creation after viewing
- **Time to First Success**: <5 minutes average from video end to working project
- **Follow-up Engagement**: >60% proceed to advanced tutorials

### Optimization Opportunities
- **A/B Test Template vs Manual**: Measure preference and success rates
- **Timer Pressure**: Test with/without real-time timer to see impact on engagement
- **Project Complexity**: Test with different example project types
- **Call-to-Action Timing**: Test CTA placement for maximum conversion

---

## Distribution & Integration

### Embedding Locations
- **Quick Start Documentation**: Featured prominently in new project guide
- **GitHub Template Repository**: Auto-play on template landing page
- **Framework Landing Page**: Hero section demonstration
- **Community Onboarding**: First video in new user journey

### Supporting Content
- **Written Transcript**: SEO-optimized blog post version
- **Interactive Demo**: Embedded terminal for hands-on practice
- **Template Gallery**: Showcasing different project type variations
- **Community Showcase**: User projects created with this method

---

*Script Version: 1.0 | Production Complexity: Medium | Estimated Editing Time: 6-8 hours*