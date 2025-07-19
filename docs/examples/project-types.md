# 📚 CI Framework Examples by Project Type

This guide provides ready-to-use CI configurations for different types of Python projects.

## 🌐 Web Applications

### FastAPI Project

```toml
# pyproject.toml
[tool.pixi.project]
name = "fastapi-app"
channels = ["conda-forge"]
platforms = ["linux-64"]

[tool.pixi.dependencies]
python = "3.11.*"
fastapi = "*"
uvicorn = "*"
pytest = "*"
httpx = "*"  # For async testing
pytest-asyncio = "*"

[tool.pixi.tasks]
# Development
dev = "uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
dev-debug = "uvicorn app.main:app --reload --log-level debug"

# Testing
test = "pytest tests/ -v"
test-unit = "pytest tests/unit/ -v"
test-integration = "pytest tests/integration/ -v --asyncio-mode=auto"
test-api = "pytest tests/api/ -v -s"
test-cov = "pytest tests/ --cov=app --cov-report=term-missing --cov-report=xml"

# Quality
lint = "ruff check app/ tests/ --select=F,E9"
lint-full = "ruff check app/ tests/"
format = "ruff format app/ tests/"
typecheck = "mypy app/"

# Combined
quality = { depends-on = ["test", "lint", "typecheck"] }
quality-full = { depends-on = ["test-cov", "lint-full", "typecheck"] }
```

**Custom CI Job for API Testing:**
```yaml
api-tests:
  runs-on: ubuntu-latest
  needs: quick-checks
  services:
    redis:
      image: redis:7
      options: >-
        --health-cmd "redis-cli ping"
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
  steps:
    - uses: actions/checkout@v4
    - name: Setup Pixi
      uses: prefix-dev/setup-pixi@v0.8.11
      with:
        pixi-version: ${{ env.PIXI_VERSION }}
    - name: Start FastAPI
      run: |
        pixi run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
        sleep 5
    - name: Run API Tests
      run: pixi run test-api
      env:
        API_URL: http://localhost:8000
        REDIS_URL: redis://localhost:6379
```

### Django Project

```toml
# pyproject.toml
[tool.pixi.project]
name = "django-app"
channels = ["conda-forge"]
platforms = ["linux-64"]

[tool.pixi.dependencies]
python = "3.11.*"
django = ">=4.2"
pytest = "*"
pytest-django = "*"
django-extensions = "*"

[tool.pixi.tasks]
# Django management
migrate = "python manage.py migrate"
collectstatic = "python manage.py collectstatic --noinput"
createsuperuser = "python manage.py createsuperuser"

# Development
dev = "python manage.py runserver"
dev-plus = "python manage.py runserver_plus"  # django-extensions

# Testing
test = "pytest"
test-unit = "pytest tests/unit/"
test-integration = "pytest tests/integration/"
test-models = "pytest tests/models/"
test-views = "pytest tests/views/"
test-cov = "pytest --cov=. --cov-report=xml"

# Quality
lint = "ruff check . --exclude=migrations --select=F,E9"
lint-full = "ruff check . --exclude=migrations"
format = "ruff format . --exclude=migrations"

quality = { depends-on = ["test", "lint"] }
```

## 📊 Data Science Projects

### Machine Learning Project

```toml
# pyproject.toml
[tool.pixi.project]
name = "ml-project"
channels = ["conda-forge", "pytorch", "nvidia"]
platforms = ["linux-64"]

[tool.pixi.dependencies]
python = "3.11.*"
numpy = "*"
pandas = "*"
scikit-learn = "*"
matplotlib = "*"
seaborn = "*"
jupyter = "*"
pytest = "*"
pytest-benchmark = "*"

[tool.pixi.feature.gpu.dependencies]
pytorch = "*"
torchvision = "*"
torchaudio = "*"
pytorch-cuda = "11.8.*"

[tool.pixi.environments]
default = {solve-group = "default"}
gpu = {features = ["gpu"], solve-group = "default"}

[tool.pixi.tasks]
# Development
notebook = "jupyter lab --ip=0.0.0.0 --allow-root"
clean-notebooks = "jupyter nbconvert --clear-output --inplace notebooks/*.ipynb"

# Data processing
download-data = "python scripts/download_data.py"
preprocess = "python scripts/preprocess.py"
train = "python src/train.py"
evaluate = "python src/evaluate.py"

# Testing
test = "pytest tests/ -v"
test-data = "pytest tests/data/ -v"
test-models = "pytest tests/models/ -v --tb=short"
test-performance = "pytest tests/performance/ --benchmark-only"
test-notebooks = "pytest --nbval notebooks/"

# Quality
lint = "ruff check src/ tests/ scripts/ --select=F,E9"
format = "ruff format src/ tests/ scripts/"

quality = { depends-on = ["test", "lint"] }
benchmark = { depends-on = ["test-performance"] }
```

**Custom CI Job for ML Testing:**
```yaml
ml-validation:
  runs-on: ubuntu-latest
  needs: comprehensive-tests
  steps:
    - uses: actions/checkout@v4
    - name: Setup Pixi
      uses: prefix-dev/setup-pixi@v0.8.11
      with:
        pixi-version: ${{ env.PIXI_VERSION }}
    - name: Download test data
      run: pixi run download-data
    - name: Run model validation
      run: |
        pixi run test-models
        pixi run test-performance
    - name: Upload model artifacts
      uses: actions/upload-artifact@v4
      with:
        name: model-validation-results
        path: |
          outputs/model_metrics.json
          outputs/performance_benchmarks.json
```

### Data Analysis Project

```toml
# pyproject.toml
[tool.pixi.project]
name = "data-analysis"
channels = ["conda-forge"]
platforms = ["linux-64"]

[tool.pixi.dependencies]
python = "3.11.*"
pandas = ">=2.0"
numpy = "*"
matplotlib = "*"
seaborn = "*"
plotly = "*"
jupyter = "*"
ipykernel = "*"
pytest = "*"

[tool.pixi.tasks]
# Analysis
notebook = "jupyter lab"
clean-notebooks = "jupyter nbconvert --clear-output --inplace analysis/*.ipynb"
export-html = "jupyter nbconvert --to html analysis/*.ipynb --output-dir exports/"

# Data processing
load-data = "python scripts/load_data.py"
clean-data = "python scripts/clean_data.py"
analyze = "python scripts/analyze.py"
visualize = "python scripts/visualize.py"

# Testing
test = "pytest tests/ -v"
test-data-quality = "pytest tests/data_quality/ -v"
test-analysis = "pytest tests/analysis/ -v"
validate-notebooks = "pytest --nbval analysis/ --nbval-lax"

# Quality
lint = "ruff check scripts/ tests/ --select=F,E9"
format = "ruff format scripts/ tests/"

quality = { depends-on = ["test", "lint", "validate-notebooks"] }
```

## 🛠️ CLI Tools & Utilities

### Command Line Tool

```toml
# pyproject.toml
[tool.pixi.project]
name = "cli-tool"
channels = ["conda-forge"]
platforms = ["linux-64", "osx-arm64", "osx-64", "win-64"]

[tool.pixi.dependencies]
python = ">=3.10"
click = ">=8.0"
rich = "*"
typer = "*"  # Alternative to click
pytest = "*"

[project.scripts]
mytool = "mytool.cli:main"

[tool.pixi.tasks]
# Development
dev = "python -m mytool"
install-dev = "pip install -e ."

# Testing
test = "pytest tests/ -v"
test-cli = "pytest tests/cli/ -v"
test-integration = "pytest tests/integration/ -v -s"

# CLI testing with actual commands
test-commands = """
    python -m mytool --help &&
    python -m mytool command1 --dry-run &&
    python -m mytool command2 --version
"""

# Quality
lint = "ruff check src/ tests/ --select=F,E9"
format = "ruff format src/ tests/"
typecheck = "mypy src/"

# Building
build = "python -m build"
build-wheel = "python setup.py bdist_wheel"

quality = { depends-on = ["test", "test-cli", "lint"] }
```

**Custom CI for Cross-Platform CLI Testing:**
```yaml
cli-cross-platform:
  runs-on: ${{ matrix.os }}
  strategy:
    matrix:
      os: [ubuntu-latest, macos-latest, windows-latest]
      python-version: ["3.10", "3.11", "3.12"]
  steps:
    - uses: actions/checkout@v4
    - name: Setup Pixi
      uses: prefix-dev/setup-pixi@v0.8.11
      with:
        pixi-version: ${{ env.PIXI_VERSION }}
    - name: Install CLI tool
      run: pixi run install-dev
    - name: Test CLI commands
      run: |
        pixi run test-commands
        mytool --version
        mytool --help
    - name: Test CLI integration
      run: pixi run test-integration
```

## 📦 Libraries & Packages

### Python Package

```toml
# pyproject.toml
[tool.pixi.project]
name = "my-python-package"
channels = ["conda-forge"]
platforms = ["linux-64", "osx-arm64", "osx-64", "win-64"]

[tool.pixi.dependencies]
python = ">=3.10"
pytest = "*"
pytest-cov = "*"

[tool.pixi.feature.docs.dependencies]
sphinx = "*"
sphinx-rtd-theme = "*"
myst-parser = "*"

[tool.pixi.feature.dev.dependencies]
black = "*"
ruff = "*"
mypy = "*"
pre-commit = "*"

[tool.pixi.environments]
default = {solve-group = "default"}
dev = {features = ["dev"], solve-group = "default"}
docs = {features = ["docs"], solve-group = "default"}

[tool.pixi.tasks]
# Testing
test = "pytest tests/ -v"
test-cov = "pytest tests/ --cov=src --cov-report=term-missing --cov-report=xml"
test-docs = "pytest docs/ --doctest-modules"

# Documentation
docs-build = "sphinx-build -b html docs/ docs/_build/"
docs-serve = "python -m http.server 8000 --directory docs/_build"
docs-clean = "rm -rf docs/_build"

# Quality
lint = "ruff check src/ tests/ --select=F,E9"
lint-full = "ruff check src/ tests/"
format = "ruff format src/ tests/"
typecheck = "mypy src/"

# Building
build = "python -m build"
clean = "rm -rf dist/ build/ *.egg-info/"

# Publishing (use carefully!)
publish-test = "twine upload --repository testpypi dist/*"
publish = "twine upload dist/*"

quality = { depends-on = ["test-cov", "lint", "typecheck"] }
```

**Custom CI for Package Publishing:**
```yaml
publish:
  runs-on: ubuntu-latest
  needs: [comprehensive-tests, security-audit]
  if: github.event_name == 'release'
  steps:
    - uses: actions/checkout@v4
    - name: Setup Pixi
      uses: prefix-dev/setup-pixi@v0.8.11
      with:
        pixi-version: ${{ env.PIXI_VERSION }}
    - name: Build package
      run: |
        pixi run clean
        pixi run build
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: pixi run publish
```

## 🔬 Scientific Computing

### Research Project

```toml
# pyproject.toml
[tool.pixi.project]
name = "research-project"
channels = ["conda-forge", "bioconda"]
platforms = ["linux-64"]

[tool.pixi.dependencies]
python = "3.11.*"
numpy = "*"
scipy = "*"
pandas = "*"
matplotlib = "*"
jupyter = "*"
pytest = "*"
hypothesis = "*"  # Property-based testing

[tool.pixi.feature.bio.dependencies]
biopython = "*"
pysam = "*"
scikit-bio = "*"

[tool.pixi.environments]
default = {solve-group = "default"}
bio = {features = ["bio"], solve-group = "default"}

[tool.pixi.tasks]
# Research workflow
preprocess = "python scripts/preprocess.py"
analyze = "python scripts/analyze.py"
plot = "python scripts/plot.py"
report = "jupyter nbconvert report.ipynb --to html"

# Testing
test = "pytest tests/ -v"
test-hypothesis = "pytest tests/property/ -v --hypothesis-show-statistics"
test-numerical = "pytest tests/numerical/ -v --tb=short"

# Quality
lint = "ruff check src/ scripts/ tests/ --select=F,E9"
format = "ruff format src/ scripts/ tests/"

quality = { depends-on = ["test", "test-hypothesis", "lint"] }
```

## 🏢 Enterprise Applications

### Large Application with Multiple Services

```toml
# pyproject.toml
[tool.pixi.project]
name = "enterprise-app"
channels = ["conda-forge"]
platforms = ["linux-64"]

[tool.pixi.dependencies]
python = "3.11.*"
fastapi = "*"
sqlalchemy = "*"
alembic = "*"
redis = "*"
celery = "*"
pytest = "*"
pytest-asyncio = "*"
pytest-xdist = "*"  # Parallel testing

[tool.pixi.feature.monitoring.dependencies]
prometheus-client = "*"
sentry-sdk = "*"

[tool.pixi.environments]
default = {solve-group = "default"}
monitoring = {features = ["monitoring"], solve-group = "default"}

[tool.pixi.tasks]
# Services
api = "uvicorn app.main:app --host 0.0.0.0 --port 8000"
worker = "celery -A app.celery worker --loglevel=info"
scheduler = "celery -A app.celery beat --loglevel=info"

# Database
db-upgrade = "alembic upgrade head"
db-downgrade = "alembic downgrade -1"
db-migration = "alembic revision --autogenerate"

# Testing
test = "pytest tests/ -v -n auto"  # Parallel testing
test-unit = "pytest tests/unit/ -v"
test-integration = "pytest tests/integration/ -v"
test-api = "pytest tests/api/ -v"
test-e2e = "pytest tests/e2e/ -v -s"

# Quality
lint = "ruff check app/ tests/ --select=F,E9"
format = "ruff format app/ tests/"
typecheck = "mypy app/"
security = "bandit -r app/ -x tests/"

quality = { depends-on = ["test", "lint", "typecheck", "security"] }
```

**Custom CI for Microservices:**
```yaml
microservices-test:
  runs-on: ubuntu-latest
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
    redis:
      image: redis:7
      options: >-
        --health-cmd "redis-cli ping"
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
  steps:
    - uses: actions/checkout@v4
    - name: Setup Pixi
      uses: prefix-dev/setup-pixi@v0.8.11
      with:
        pixi-version: ${{ env.PIXI_VERSION }}
    - name: Run database migrations
      run: pixi run db-upgrade
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost/test
    - name: Test all services
      run: |
        pixi run test-unit
        pixi run test-integration
        pixi run test-api
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost/test
        REDIS_URL: redis://localhost:6379
        ENVIRONMENT: test
```

## 🎯 Choosing the Right Configuration

### Decision Matrix

| Project Type | Key Features | CI Complexity | Recommended Config |
|--------------|--------------|---------------|-------------------|
| **Web App** | API testing, DB integration | Medium | FastAPI/Django examples |
| **Data Science** | Notebooks, large data, GPUs | High | ML/Analysis examples |
| **CLI Tool** | Cross-platform, binary testing | Medium | CLI example |
| **Library** | Documentation, publishing | Low-Medium | Package example |
| **Research** | Reproducibility, hypothesis testing | Medium | Scientific example |
| **Enterprise** | Multiple services, complex deps | High | Enterprise example |

### Getting Started Tips

1. **Start Simple**: Begin with the basic configuration for your project type
2. **Add Gradually**: Add features like security scanning, performance testing as needed
3. **Customize**: Adapt the examples to your specific requirements
4. **Test Locally**: Always test your pixi configuration locally before pushing

---

*Need help choosing or customizing? Check our [troubleshooting guide](../ci-workflow-guide.md#️-troubleshooting) or [open an issue](https://github.com/MementoRC/ci-framework/issues).*