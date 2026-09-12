# CI Framework - Workflow Template Guide

> **Quick Start**: Get your Python project running with enterprise-grade CI in 5 minutes

## Table of Contents

- [🚀 Quick Start (5 minutes)](#-quick-start-5-minutes)
- [📋 Requirements](#-requirements)
- [🔧 Customization Guide](#-customization-guide)
- [🛠️ Troubleshooting](#️-troubleshooting)
- [📚 Examples](#-examples)
- [🔄 Migration Guide](#-migration-guide)
- [⚡ Performance Tuning](#-performance-tuning)

## 🚀 Quick Start (5 minutes)

### Step 1: Copy the Template (1 minute)

Copy the CI workflow template to your repository:

```bash
# From your repository root
curl -O https://raw.githubusercontent.com/MementoRC/ci-framework/main/.github/workflows/python-ci-template.yml.template
mv python-ci-template.yml.template .github/workflows/ci.yml
```

### Step 2: Configure Your Project (2 minutes)

Ensure your `pyproject.toml` has the minimum required configuration:

```toml
[tool.pixi.project]
name = "your-project"
channels = ["conda-forge"]
platforms = ["linux-64"]

[tool.pixi.dependencies]
python = ">=3.10,<3.13"
pytest = "*"

[tool.pixi.tasks]
test = "pytest"
lint = "ruff check --select=F,E9"
```

### Step 3: Push and Verify (2 minutes)

```bash
git add .github/workflows/ci.yml pyproject.toml
git commit -m "Add CI framework workflow"
git push
```

**✅ Done!** Check your GitHub Actions tab to see the CI pipeline running.

---

## 📋 Requirements

### Minimum Requirements

- **Python**: 3.10 or higher
- **Package Manager**: pixi (recommended) or poetry/hatch
- **Repository**: GitHub repository with Actions enabled

### Recommended Project Structure

```
your-project/
├── .github/workflows/ci.yml
├── pyproject.toml
├── src/your_project/
├── tests/
└── README.md
```

---

## 🔧 Customization Guide

### Matrix Strategy Customization

The default matrix tests Python 3.10-3.12 on ubuntu-latest and macos-latest:

```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12"]
    os: [ubuntu-latest, macos-latest]
```

**Custom Examples:**

```yaml
# Windows support
strategy:
  matrix:
    python-version: ["3.11", "3.12"]
    os: [ubuntu-latest, windows-latest, macos-latest]

# Single platform for faster CI
strategy:
  matrix:
    python-version: ["3.11"]
    os: [ubuntu-latest]

# Extended Python versions
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12", "3.13"]
    os: [ubuntu-latest]
```

### Making the Python Version Matrix Real

**The problem**: `reusable-ci.yml`'s `python-versions` matrix used to be a false
assurance. The `test` and `test-postgres` jobs used to run `actions/setup-python`,
which installs an interpreter on the runner, but `pixi run -e <env> test`
actually executes under the environment's own interpreter as pinned in
`pixi.lock` — not whatever `setup-python` put on `PATH`. If your
`pyproject.toml` only defines one pixi environment, every matrix leg ran the
exact same Python, while the job names (`🧪 Test Python 3.10 on ubuntu-latest`,
`🧪 Test Python 3.11 on ubuntu-latest`, `🧪 Test Python 3.12 on ubuntu-latest`)
implied otherwise. A repo declaring `requires-python = ">=3.11"` could show
three green ticks without its 3.11 floor ever having been exercised. The
`actions/setup-python` step has since been removed from those two jobs, since
the pixi path never used the interpreter it installed (see #251).

The workflow now closes this gap:

- it derives a candidate pixi environment name per matrix leg from the
  `python-version-env-pattern` input (default `py{nodot}`, where `{version}`
  expands to e.g. `3.11` and `{nodot}` expands to `311`),
- it uses that environment if your pixi manifest actually declares it,
  otherwise it falls back to `pixi-environment` (so nothing breaks for repos
  that haven't opted in),
- it verifies the interpreter that actually ran the tests and reports a
  mismatch against the requested matrix version.

#### Declaring real per-version environments

To make the matrix test what it claims, declare one pixi environment per
Python version, each pinning that version via a feature:

```toml
[tool.pixi.feature.py310.dependencies]
python = "3.10.*"

[tool.pixi.feature.py311.dependencies]
python = "3.11.*"

[tool.pixi.feature.py312.dependencies]
python = "3.12.*"

[tool.pixi.feature.test.dependencies]
pytest = "*"

[tool.pixi.environments]
py310 = ["py310", "test"]
py311 = ["py311", "test"]
py312 = ["py312", "test"]
```

With this in place, `pixi run -e py311 test` genuinely runs under a 3.11
interpreter — matching the `py{nodot}` default of `python-version-env-pattern`.

#### Caller-side configuration

```yaml
with:
  python-versions: '["3.10", "3.11", "3.12"]'
  strict-python-matrix: true  # only once py310/py311/py312 exist
```

Leave `strict-python-matrix` unset (or `false`) until the environments above
exist — see the warn-vs-fail note below.

#### Custom environment naming

If your repo already names its environments differently (e.g. `test-py311`
instead of `py311`), don't rename them — point the pattern at your existing
convention instead:

```yaml
with:
  python-version-env-pattern: 'test-py{nodot}'
```

#### What you'll see in the logs

- When a per-version environment is found and used (from the "Resolve pixi
  environment for this matrix leg" step):
  ```
  Using per-version pixi environment 'py311' for Python 3.11
  ```
- When it isn't declared, that same resolve step logs a plain fallback notice
  (not a warning annotation) and continues with the default environment:
  ```
  No pixi environment named 'py311'; falling back to 'default'
  ```
- Separately, the "Verify interpreter matches this matrix leg" step is what
  actually detects the resulting version mismatch and emits the annotation,
  titled `Python matrix mismatch`:
  ```
  ::warning title=Python matrix mismatch::this job is named for Python 3.11 but pixi environment 'default' runs Python 3.9, so this leg does not test its declared version. ...
  ```
- When the interpreter can't be determined at all, the verify step emits an
  annotation titled `Python matrix unverified` and does not fail the leg,
  regardless of `strict-python-matrix`.

#### Warn by default, fail on opt-in

The mismatch check **warns by default** rather than failing, so adopting a
newer version of the framework won't suddenly turn existing green pipelines
red for repos that haven't declared per-version environments yet. Once you've
added the environments as shown above, set `strict-python-matrix: true` to
turn the mismatch into a hard failure and keep the matrix honest going
forward.

### Adding Custom Jobs

#### Database Testing Job

```yaml
database-tests:
  runs-on: ubuntu-latest
  needs: quick-checks
  services:
    postgres:
      image: postgres:15
      env:
        POSTGRES_PASSWORD: postgres
      options: >-
        --health-cmd pg_isready
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
  steps:
    - uses: actions/checkout@v4
    - name: Setup Pixi
      uses: prefix-dev/setup-pixi@v0.8.11
      with:
        pixi-version: ${{ env.PIXI_VERSION }}
    - name: Run Database Tests
      run: pixi run test-db
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test
```

#### Docker Build Job

```yaml
docker-build:
  runs-on: ubuntu-latest
  needs: comprehensive-tests
  steps:
    - uses: actions/checkout@v4
    - name: Build Docker Image
      run: |
        docker build -t ${{ github.repository }}:${{ github.sha }} .
        docker tag ${{ github.repository }}:${{ github.sha }} ${{ github.repository }}:latest
    - name: Test Docker Image
      run: |
        docker run --rm ${{ github.repository }}:${{ github.sha }} pixi run test
```

### Change Detection Customization

Customize which changes trigger specific jobs:

```yaml
- name: Detect Changes
  id: changes
  uses: dorny/paths-filter@v2
  with:
    filters: |
      python:
        - 'src/**/*.py'
        - 'tests/**/*.py'
        - 'pyproject.toml'
      docs:
        - 'docs/**/*'
        - '*.md'
      docker:
        - 'Dockerfile'
        - 'docker-compose.yml'
      ci:
        - '.github/workflows/**'
```

### Environment Variables

Add project-specific environment variables:

```yaml
env:
  PIXI_VERSION: v0.74.0
  # Add your custom variables
  API_BASE_URL: https://api.example.com
  ENVIRONMENT: ci
  PYTHON_VERSION: "3.11"
```

---

## 🛠️ Troubleshooting

### Common Issues

#### 1. "pixi command not found"

**Problem**: Pixi setup action failed or wrong version
**Solution**:
```yaml
- name: Setup Pixi
  uses: prefix-dev/setup-pixi@v0.8.11  # Use latest version
  with:
    pixi-version: v0.74.0  # Use specific pixi version
```

#### 2. "No module named 'your_module'"

**Problem**: Module not in Python path
**Solution**: Install in editable mode
```toml
[tool.pixi.tasks]
install-dev = "pip install -e ."
test = { depends-on = ["install-dev"], cmd = "pytest" }
```

#### 3. Matrix Job Failures

**Problem**: One matrix combination fails, others pass
**Solution**: Check platform-specific dependencies
```toml
[tool.pixi.target.linux-64.dependencies]
linux-specific-package = "*"

[tool.pixi.target.osx-64.dependencies]
macos-specific-package = "*"
```

#### 4. Timeout Issues

**Problem**: Jobs exceed timeout limits
**Solutions**:
```yaml
# Increase timeout
timeout-minutes: 30

# Optimize tests
- name: Run Tests
  run: pixi run test --maxfail=1 -x
```

#### 5. Artifact Upload Failures

**Problem**: Artifact paths don't exist
**Solution**: Create directories before upload
```yaml
- name: Prepare Artifacts
  run: |
    mkdir -p artifacts/reports
    mkdir -p artifacts/coverage
- name: Upload Results
  uses: actions/upload-artifact@v4
  if: always()  # Upload even if tests fail
```

### Performance Issues

#### Slow pixi Installation

```yaml
# Cache pixi environment
- name: Cache Pixi Environment
  uses: actions/cache@v3
  with:
    path: ~/.pixi
    key: pixi-${{ runner.os }}-${{ hashFiles('**/pixi.lock') }}
```

#### Large Test Suite

```yaml
# Parallel testing
- name: Run Tests in Parallel
  run: pixi run pytest -n auto --dist worksteal
```

#### Large Dependencies

```yaml
# Minimal install for quick checks
- name: Install Minimal Dependencies
  run: pixi install --locked -e minimal
```

### Security Issues

#### Failed Security Scans

**Problem**: Bandit/safety checks fail
**Solution**: Configure exclusions
```toml
[tool.bandit]
exclude_dirs = ["tests", "build", "dist"]
skips = ["B101", "B601"]  # Skip specific checks

[tool.pixi.tasks]
security-scan = "bandit -r src/ --severity-level medium"
```

---

## 📚 Examples

### Example Configurations by Project Type

#### Web Application (FastAPI/Flask)

```toml
[tool.pixi.dependencies]
python = "3.11.*"
fastapi = "*"
uvicorn = "*"
pytest = "*"
httpx = "*"  # For testing

[tool.pixi.tasks]
dev = "uvicorn app.main:app --reload"
test = "pytest tests/ -v"
test-integration = "pytest tests/integration/ -v"
lint = "ruff check src/ tests/"
```

#### Data Science Project

```toml
[tool.pixi.dependencies]
python = "3.11.*"
pandas = "*"
numpy = "*"
scikit-learn = "*"
jupyter = "*"
pytest = "*"

[tool.pixi.tasks]
notebook = "jupyter lab"
test = "pytest tests/ -v"
test-data = "pytest tests/data/ -v --tb=short"
```

#### CLI Tool

```toml
[tool.pixi.dependencies]
python = "3.11.*"
click = "*"
rich = "*"
pytest = "*"

[tool.pixi.tasks]
dev = "python -m myapp"
test = "pytest tests/ -v"
test-cli = "pytest tests/cli/ -v"
build = "python -m build"
```

### Custom Workflow Examples

#### Monorepo with Multiple Services

```yaml
strategy:
  matrix:
    service: [api, worker, frontend]
    python-version: ["3.11"]
    os: [ubuntu-latest]

steps:
  - name: Test Service
    run: |
      cd services/${{ matrix.service }}
      pixi run test
```

#### Multi-Stage Deployment

```yaml
deploy-staging:
  runs-on: ubuntu-latest
  needs: [comprehensive-tests, security-audit]
  if: github.ref == 'refs/heads/develop'
  environment: staging
  steps:
    - name: Deploy to Staging
      run: |
        pixi run deploy-staging

deploy-production:
  runs-on: ubuntu-latest
  needs: deploy-staging
  if: github.ref == 'refs/heads/main'
  environment: production
  steps:
    - name: Deploy to Production
      run: |
        pixi run deploy-production
```

---

## 🔄 Migration Guide

### From GitHub Actions Starter Workflows

1. **Replace workflow file**:
   ```bash
   rm .github/workflows/python-app.yml
   cp python-ci-template.yml.template .github/workflows/ci.yml
   ```

2. **Update pyproject.toml**:
   ```toml
   # Add pixi configuration
   [tool.pixi.project]
   name = "your-project"

   [tool.pixi.dependencies]
   python = ">=3.10"
   # Move dependencies from requirements.txt
   ```

### From CircleCI

1. **Remove CircleCI config**:
   ```bash
   rm -rf .circleci/
   ```

2. **Convert CircleCI jobs to GitHub Actions**:
   ```yaml
   # CircleCI orb equivalent
   - name: Setup Python Environment
     uses: prefix-dev/setup-pixi@v0.8.11
   ```

### From Jenkins

1. **Convert Jenkinsfile steps**:
   ```yaml
   # Jenkins pipeline step equivalent
   - name: Build and Test
     run: |
       pixi run build
       pixi run test
   ```

---

## ⚡ Performance Tuning

### CI Optimization Strategies

#### 1. Cache Optimization

```yaml
- name: Cache Dependencies
  uses: actions/cache@v3
  with:
    path: |
      ~/.pixi
      ~/.cache/pip
    key: deps-${{ runner.os }}-${{ hashFiles('**/pixi.lock', '**/pyproject.toml') }}
```

#### 2. Conditional Job Execution

```yaml
comprehensive-tests:
  if: |
    contains(github.event.head_commit.message, '[full-test]') ||
    github.event_name == 'pull_request' ||
    github.ref == 'refs/heads/main'
```

#### 3. Parallel Matrix Strategy

```yaml
strategy:
  fail-fast: false  # Don't cancel other jobs
  max-parallel: 6   # Limit concurrent jobs
  matrix:
    include:
      - python-version: "3.11"
        os: ubuntu-latest
        test-type: "unit"
      - python-version: "3.11"
        os: ubuntu-latest
        test-type: "integration"
```

#### 4. Optimized Test Commands

```toml
[tool.pixi.tasks]
# Fast feedback
test-quick = "pytest tests/unit/ -x --tb=line"
# Comprehensive but efficient
test-full = "pytest tests/ --maxfail=3 --tb=short -q"
# Parallel execution
test-parallel = "pytest tests/ -n auto --dist worksteal"
```

### Performance Monitoring

Add performance tracking to your workflow:

```yaml
- name: Performance Benchmark
  run: |
    start_time=$(date +%s)
    pixi run test
    end_time=$(date +%s)
    echo "Test duration: $((end_time - start_time)) seconds"
```

---

## 📊 Metrics and Monitoring

### GitHub Status Integration

Monitor CI performance:

```yaml
- name: Report Status
  if: always()
  uses: actions/github-script@v6
  with:
    script: |
      const status = '${{ job.status }}';
      const message = `CI ${status}: Tests completed in ${process.env.GITHUB_RUN_NUMBER}`;
      github.rest.repos.createCommitStatus({
        owner: context.repo.owner,
        repo: context.repo.repo,
        sha: context.sha,
        state: status === 'success' ? 'success' : 'failure',
        description: message,
        context: 'ci/comprehensive-tests'
      });
```

### Coverage Tracking

```yaml
- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: coverage.xml
    fail_ci_if_error: true
```

---

## 🔗 Additional Resources

- [Pixi Documentation](https://pixi.sh/latest/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Python CI Best Practices](https://docs.python.org/3/howto/pyporting.html)
- [Matrix Strategy Guide](https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs)

---

## 🤝 Contributing

Found an issue or want to improve this guide?

1. Check existing issues in the [ci-framework repository](https://github.com/MementoRC/ci-framework/issues)
2. Submit a pull request with your improvements
3. Join our [discussions](https://github.com/MementoRC/ci-framework/discussions) for questions

---

*This guide is part of the [CI Framework project](https://github.com/MementoRC/ci-framework) - bringing enterprise-grade CI to Python projects with minimal setup.*
