"""
Change Detection and CI Optimization Action

Provides intelligent CI optimization through file-based change detection and dependency impact analysis.
"""

import ast
import fnmatch
import json
import logging
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ChangeAnalysisResult:
    """Result of change detection analysis."""
    success: bool
    changed_files: list[str]
    classifications: dict[str, list[str]]
    change_categories: str
    affected_packages: list[str]
    affected_tests: list[str]
    dependency_impact: int
    skip_tests: bool
    skip_security: bool
    skip_docs: bool
    skip_lint: bool
    optimization_score: int
    time_savings: int
    execution_time: float
    reports_path: str
    failure_reason: Optional[str] = None


@dataclass
class DependencyNode:
    """Node in the dependency graph."""
    module_path: str
    imports: set[str]
    imported_by: set[str]
    test_files: set[str]
    is_test: bool = False


class FilePatternMatcher:
    """Handles file pattern matching and classification."""

    DEFAULT_PATTERNS = {
        "docs": ["docs/**", "*.md", "*.rst", "*.txt", "README*", "CHANGELOG*", "LICENSE*"],
        "config": ["*.yml", "*.yaml", "*.toml", "*.json", ".github/**", "*.cfg", "*.ini",
                  ".pre-commit-config.yaml", "tox.ini", "setup.cfg"],
        "tests": ["tests/**", "**/test_*.py", "**/*_test.py", "**/*_tests.py", "**/conftest.py",
                 "test_*.py", "*_test.py"],
        "source": ["src/**", "**/*.py", "**/*.js", "**/*.ts", "framework/**", "lib/**"],
        "dependencies": ["requirements*.txt", "pyproject.toml", "package.json", "Pipfile*",
                        "poetry.lock", "package-lock.json", "yarn.lock", "Cargo.toml"],
        "ci": [".github/workflows/**", ".github/actions/**", "*.yml", "*.yaml", ".gitlab-ci.yml"],
        "build": ["Dockerfile*", "docker-compose*.yml", "Makefile", "setup.py", "setup.cfg",
                 "CMakeLists.txt", "build.gradle", "pom.xml"]
    }

    def __init__(self, custom_patterns: Optional[dict[str, list[str]]] = None):
        """Initialize with default or custom patterns."""
        self.patterns = self.DEFAULT_PATTERNS.copy()
        if custom_patterns:
            self.patterns.update(custom_patterns)

    def classify_files(self, files: list[str]) -> dict[str, list[str]]:
        """Classify files into categories based on patterns."""
        classifications: dict[str, list[str]] = {category: [] for category in self.patterns.keys()}
        unclassified = []

        for file in files:
            matched = False
            for category, patterns in self.patterns.items():
                for pattern in patterns:
                    if self._matches_pattern(file, pattern):
                        classifications[category].append(file)
                        matched = True
                        break
                if matched:
                    break

            if not matched:
                unclassified.append(file)
                # Try to infer category from file extension
                ext_category = self._infer_from_extension(file)
                if ext_category:
                    classifications[ext_category].append(file)
                    matched = True

            if not matched:
                logger.warning(f"Unclassified file: {file}")

        return classifications

    def _matches_pattern(self, file: str, pattern: str) -> bool:
        """Check if file matches pattern with glob and path matching."""
        # Direct glob match
        if fnmatch.fnmatch(file, pattern):
            return True

        # Path-based glob match
        if fnmatch.fnmatch(f"/{file}", f"/{pattern}"):
            return True

        # Directory prefix match
        if pattern.endswith("/**") and file.startswith(pattern[:-3]):
            return True

        return False

    def _infer_from_extension(self, file: str) -> Optional[str]:
        """Infer category from file extension."""
        ext = Path(file).suffix.lower()

        extension_map = {
            '.py': 'source',
            '.js': 'source',
            '.ts': 'source',
            '.jsx': 'source',
            '.tsx': 'source',
            '.go': 'source',
            '.rs': 'source',
            '.java': 'source',
            '.cpp': 'source',
            '.c': 'source',
            '.h': 'source',
            '.md': 'docs',
            '.rst': 'docs',
            '.txt': 'docs',
            '.yml': 'config',
            '.yaml': 'config',
            '.toml': 'config',
            '.json': 'config',
            '.ini': 'config',
            '.cfg': 'config'
        }

        return extension_map.get(ext)


class DependencyAnalyzer:
    """Analyzes dependency relationships between modules."""

    def __init__(self, project_dir: Path):
        """Initialize dependency analyzer."""
        self.project_dir = project_dir
        self.dependency_graph: dict[str, DependencyNode] = {}
        self.module_cache: dict[str, set[str]] = {}

    def build_dependency_graph(self, source_files: list[str]) -> dict[str, DependencyNode]:
        """Build dependency graph for source files."""
        logger.info(f"Building dependency graph for {len(source_files)} files")

        # Process files in parallel for better performance
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_file = {
                executor.submit(self._analyze_file_dependencies, file): file
                for file in source_files if file.endswith('.py')
            }

            for future in as_completed(future_to_file):
                file = future_to_file[future]
                try:
                    imports = future.result()
                    if imports is not None:
                        node = DependencyNode(
                            module_path=file,
                            imports=imports,
                            imported_by=set(),
                            test_files=set(),
                            is_test=self._is_test_file(file)
                        )
                        self.dependency_graph[file] = node
                except Exception as e:
                    logger.warning(f"Failed to analyze {file}: {e}")

        # Build reverse dependencies
        self._build_reverse_dependencies()

        # Associate test files
        self._associate_test_files()

        logger.info(f"Built dependency graph with {len(self.dependency_graph)} nodes")
        return self.dependency_graph

    def get_affected_modules(self, changed_files: list[str]) -> set[str]:
        """Get all modules affected by changes (including transitive dependencies)."""
        affected = set()

        # Direct changes
        for file in changed_files:
            if file in self.dependency_graph:
                affected.add(file)

        # Transitive dependencies
        queue = list(affected)
        visited = set()

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            if current in self.dependency_graph:
                # Add modules that import this one
                for dependent in self.dependency_graph[current].imported_by:
                    if dependent not in affected:
                        affected.add(dependent)
                        queue.append(dependent)

        return affected

    def get_affected_tests(self, changed_files: list[str]) -> set[str]:
        """Get test files that should be run based on changed files."""
        affected_tests = set()

        # Direct test file changes
        for file in changed_files:
            if self._is_test_file(file):
                affected_tests.add(file)

        # Get affected modules
        affected_modules = self.get_affected_modules(changed_files)

        # Find tests for affected modules
        for module in affected_modules:
            if module in self.dependency_graph:
                affected_tests.update(self.dependency_graph[module].test_files)

        # Also add tests that import any affected modules
        for test_file, node in self.dependency_graph.items():
            if node.is_test and node.imports.intersection(affected_modules):
                affected_tests.add(test_file)

        return affected_tests

    def _analyze_file_dependencies(self, file_path: str) -> Optional[set[str]]:
        """Analyze imports in a Python file."""
        full_path = self.project_dir / file_path

        if not full_path.exists() or not full_path.is_file():
            return None

        try:
            with open(full_path, encoding='utf-8') as f:
                content = f.read()

            # Parse AST to extract imports
            tree = ast.parse(content)
            imports = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
                        # Also add submodule imports
                        for alias in node.names:
                            if alias.name != '*':
                                imports.add(f"{node.module}.{alias.name}")

            # Filter to only include local imports (relative to project)
            local_imports = set()
            for imp in imports:
                # Check if it's a local import
                if self._is_local_import(imp, file_path):
                    local_imports.add(imp)

            return local_imports

        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
            return set()

    def _is_local_import(self, import_name: str, current_file: str) -> bool:
        """Check if an import is local to the project."""
        # Convert import to potential file paths
        potential_paths = [
            f"{import_name.replace('.', '/')}.py",
            f"{import_name.replace('.', '/')}/__init__.py"
        ]

        for path in potential_paths:
            if (self.project_dir / path).exists():
                return True

        # Check if it's a relative import from current directory
        current_dir = Path(current_file).parent
        for path in potential_paths:
            if (self.project_dir / current_dir / path).exists():
                return True

        return False

    def _is_test_file(self, file_path: str) -> bool:
        """Check if a file is a test file."""
        file_name = Path(file_path).name
        return (
            file_name.startswith('test_') or
            file_name.endswith('_test.py') or
            file_name.endswith('_tests.py') or
            file_name == 'conftest.py' or
            'tests/' in file_path or
            '/test/' in file_path
        )

    def _build_reverse_dependencies(self):
        """Build reverse dependency relationships."""
        for file_path, node in self.dependency_graph.items():
            for imported_module in node.imports:
                # Find the file that corresponds to this import
                for other_file, other_node in self.dependency_graph.items():
                    if self._import_matches_file(imported_module, other_file):
                        other_node.imported_by.add(file_path)

    def _import_matches_file(self, import_name: str, file_path: str) -> bool:
        """Check if an import name matches a file path."""
        # Convert file path to module name
        module_name = file_path.replace('/', '.').replace('.py', '')
        if module_name.endswith('.__init__'):
            module_name = module_name[:-9]  # Remove .__init__

        return import_name == module_name or import_name.startswith(f"{module_name}.")

    def _associate_test_files(self):
        """Associate test files with the modules they test."""
        for test_file, test_node in self.dependency_graph.items():
            if not test_node.is_test:
                continue

            # Find modules this test file might be testing
            for module_file, module_node in self.dependency_graph.items():
                if module_node.is_test:
                    continue

                # Heuristic: test file imports the module, or names match
                if (module_file in test_node.imports or
                    self._test_matches_module(test_file, module_file)):
                    module_node.test_files.add(test_file)

    def _test_matches_module(self, test_file: str, module_file: str) -> bool:
        """Check if a test file matches a module file by naming convention."""
        test_name = Path(test_file).stem
        module_name = Path(module_file).stem

        # Remove test_ prefix or _test suffix
        if test_name.startswith('test_'):
            test_name = test_name[5:]
        elif test_name.endswith('_test'):
            test_name = test_name[:-5]
        elif test_name.endswith('_tests'):
            test_name = test_name[:-6]

        return test_name == module_name


class MonorepoHandler:
    """Handles monorepo-specific change detection."""

    def __init__(self, project_dir: Path):
        """Initialize monorepo handler."""
        self.project_dir = project_dir
        self.packages: dict[str, dict[str, Any]] = {}

    def detect_packages(self) -> dict[str, dict[str, Any]]:
        """Detect packages in monorepo structure."""
        packages = {}

        # Look for Python packages (directories with __init__.py or pyproject.toml)
        for item in self.project_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                package_info = self._analyze_package(item)
                if package_info:
                    packages[item.name] = package_info

        # Look for workspace-style packages (package.json with workspaces)
        package_json = self.project_dir / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                    workspaces = data.get("workspaces", [])
                    for workspace in workspaces:
                        workspace_path = self.project_dir / workspace
                        if workspace_path.exists() and workspace_path.is_dir():
                            packages[workspace] = {
                                "type": "npm_workspace",
                                "path": workspace,
                                "dependencies": self._get_npm_dependencies(workspace_path)
                            }
            except Exception as e:
                logger.warning(f"Failed to parse package.json: {e}")

        self.packages = packages
        return packages

    def get_affected_packages(self, changed_files: list[str]) -> list[str]:
        """Get packages affected by file changes."""
        affected_packages = set()

        for file in changed_files:
            package = self._get_file_package(file)
            if package:
                affected_packages.add(package)

        # Add packages that depend on affected packages
        affected_with_deps = set(affected_packages)
        for package in affected_packages:
            affected_with_deps.update(self._get_dependent_packages(package))

        return list(affected_with_deps)

    def _analyze_package(self, package_dir: Path) -> Optional[dict[str, Any]]:
        """Analyze a potential package directory."""
        package_info = {"path": str(package_dir.relative_to(self.project_dir))}

        # Check for Python package
        if (package_dir / "__init__.py").exists():
            package_info["type"] = "python_package"
            package_info["dependencies"] = ", ".join(self._get_python_dependencies(package_dir))
            return package_info

        # Check for Python project
        pyproject_toml = package_dir / "pyproject.toml"
        if pyproject_toml.exists():
            package_info["type"] = "python_project"
            package_info["dependencies"] = ", ".join(self._get_python_dependencies(package_dir))
            return package_info

        # Check for Node.js package
        package_json = package_dir / "package.json"
        if package_json.exists():
            package_info["type"] = "npm_package"
            package_info["dependencies"] = ", ".join(self._get_npm_dependencies(package_dir))
            return package_info

        return None

    def _get_python_dependencies(self, package_dir: Path) -> list[str]:
        """Get Python package dependencies."""
        deps = []

        # Check pyproject.toml
        pyproject_toml = package_dir / "pyproject.toml"
        if pyproject_toml.exists():
            try:
                import tomllib
                with open(pyproject_toml, "rb") as f:
                    data = tomllib.load(f)

                # Get dependencies from various sections
                project_deps = data.get("project", {}).get("dependencies", [])
                deps.extend(project_deps)

                # Tool-specific dependencies
                tool_deps = data.get("tool", {}).get("pixi", {}).get("dependencies", {})
                deps.extend(tool_deps.keys())

            except Exception as e:
                logger.warning(f"Failed to parse {pyproject_toml}: {e}")

        # Check requirements files
        for req_file in ["requirements.txt", "requirements-dev.txt"]:
            req_path = package_dir / req_file
            if req_path.exists():
                try:
                    with open(req_path) as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                # Extract package name (before ==, >=, etc.)
                                pkg_name = line.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0]
                                deps.append(pkg_name.strip())
                except Exception as e:
                    logger.warning(f"Failed to parse {req_path}: {e}")

        return deps

    def _get_npm_dependencies(self, package_dir: Path) -> list[str]:
        """Get NPM package dependencies."""
        package_json = package_dir / "package.json"
        deps = []

        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)

                # Get dependencies
                deps.extend(data.get("dependencies", {}).keys())
                deps.extend(data.get("devDependencies", {}).keys())
                deps.extend(data.get("peerDependencies", {}).keys())

            except Exception as e:
                logger.warning(f"Failed to parse {package_json}: {e}")

        return deps

    def _get_file_package(self, file_path: str) -> Optional[str]:
        """Determine which package a file belongs to."""
        for package_name, package_info in self.packages.items():
            package_path = package_info["path"]
            if file_path.startswith(f"{package_path}/"):
                return package_name

        return None

    def _get_dependent_packages(self, package_name: str) -> set[str]:
        """Get packages that depend on the given package."""
        dependents: set[str] = set()

        if package_name not in self.packages:
            return dependents

        # Simple approach: check if package is in dependencies of other packages
        for other_package, package_info in self.packages.items():
            if other_package != package_name:
                dependencies = package_info.get("dependencies", [])
                if package_name in dependencies:
                    dependents.add(other_package)

        return dependents


class OptimizationEngine:
    """Handles CI optimization logic and recommendations."""

    def __init__(self, enable_test_optimization: bool = True, enable_job_skipping: bool = True):
        """Initialize optimization engine."""
        self.enable_test_optimization = enable_test_optimization
        self.enable_job_skipping = enable_job_skipping

        # Default time estimates for different CI jobs (in seconds)
        self.job_time_estimates = {
            "tests": 120,      # 2 minutes
            "security": 180,   # 3 minutes
            "docs": 60,        # 1 minute
            "lint": 30,        # 30 seconds
            "build": 90        # 1.5 minutes
        }

    def calculate_optimization(self, classifications: dict[str, list[str]],
                             affected_tests: list[str]) -> dict[str, Any]:
        """Calculate CI optimization opportunities."""
        total_files = sum(len(files) for files in classifications.values())

        if total_files == 0:
            return self._empty_optimization_result()

        # Analyze change patterns
        change_analysis = self._analyze_change_patterns(classifications)

        # Calculate skip recommendations
        skip_recommendations = self._calculate_skip_recommendations(change_analysis)

        # Calculate optimization score and time savings
        optimization_score = self._calculate_optimization_score(skip_recommendations)
        time_savings = self._calculate_time_savings(skip_recommendations)

        return {
            "skip_tests": skip_recommendations["tests"],
            "skip_security": skip_recommendations["security"],
            "skip_docs": skip_recommendations["docs"],
            "skip_lint": skip_recommendations["lint"],
            "optimization_score": optimization_score,
            "time_savings": time_savings,
            "change_analysis": change_analysis,
            "affected_tests": affected_tests,
            "reasoning": skip_recommendations.get("reasoning", {})
        }

    def _analyze_change_patterns(self, classifications: dict[str, list[str]]) -> dict[str, bool]:
        """Analyze patterns in file changes."""
        has_source = len(classifications.get("source", [])) > 0
        has_tests = len(classifications.get("tests", [])) > 0
        has_docs = len(classifications.get("docs", [])) > 0
        has_config = len(classifications.get("config", [])) > 0
        has_dependencies = len(classifications.get("dependencies", [])) > 0
        has_ci = len(classifications.get("ci", [])) > 0
        has_build = len(classifications.get("build", [])) > 0

        # Calculate change patterns
        docs_only = has_docs and not any([has_source, has_tests, has_dependencies, has_build])
        config_only = has_config and not any([has_source, has_tests, has_dependencies, has_docs])
        tests_only = has_tests and not any([has_source, has_dependencies])
        ci_only = has_ci and not any([has_source, has_tests, has_dependencies, has_docs])

        return {
            "has_source": has_source,
            "has_tests": has_tests,
            "has_docs": has_docs,
            "has_config": has_config,
            "has_dependencies": has_dependencies,
            "has_ci": has_ci,
            "has_build": has_build,
            "docs_only": docs_only,
            "config_only": config_only,
            "tests_only": tests_only,
            "ci_only": ci_only
        }

    def _calculate_skip_recommendations(self, analysis: dict[str, bool]) -> dict[str, Any]:
        """Calculate which CI jobs can be safely skipped."""
        reasoning = {}

        # Tests can be skipped if no source, test, or dependency changes
        skip_tests = (
            not analysis["has_source"] and
            not analysis["has_tests"] and
            not analysis["has_dependencies"] and
            self.enable_test_optimization
        )
        reasoning["tests"] = "No source, test, or dependency changes" if skip_tests else "Source/test/dependency changes detected"

        # Security scans can be skipped for docs-only or config-only changes (excluding dependencies)
        skip_security = (
            (analysis["docs_only"] or
             (analysis["has_config"] and not analysis["has_dependencies"] and
              not analysis["has_source"])) and
            self.enable_job_skipping
        )
        reasoning["security"] = "Only docs/config changes (no dependencies)" if skip_security else "Source/dependency changes require security scan"

        # Documentation builds can be skipped if no docs changes
        skip_docs = not analysis["has_docs"] and self.enable_job_skipping
        reasoning["docs"] = "No documentation changes" if skip_docs else "Documentation changes detected"

        # Linting can be skipped for docs-only changes
        skip_lint = analysis["docs_only"] and self.enable_job_skipping
        reasoning["lint"] = "Only documentation changes" if skip_lint else "Source/config changes require linting"

        return {
            "tests": skip_tests,
            "security": skip_security,
            "docs": skip_docs,
            "lint": skip_lint,
            "reasoning": reasoning
        }

    def _calculate_optimization_score(self, skip_recommendations: dict[str, Any]) -> int:
        """Calculate optimization score as percentage of CI that can be skipped."""
        total_jobs = 4  # tests, security, docs, lint
        skipped_jobs = sum([
            skip_recommendations["tests"],
            skip_recommendations["security"],
            skip_recommendations["docs"],
            skip_recommendations["lint"]
        ])

        return int((skipped_jobs / total_jobs) * 100)

    def _calculate_time_savings(self, skip_recommendations: dict[str, Any]) -> int:
        """Calculate estimated time savings in seconds."""
        time_savings = 0

        if skip_recommendations["tests"]:
            time_savings += self.job_time_estimates["tests"]
        if skip_recommendations["security"]:
            time_savings += self.job_time_estimates["security"]
        if skip_recommendations["docs"]:
            time_savings += self.job_time_estimates["docs"]
        if skip_recommendations["lint"]:
            time_savings += self.job_time_estimates["lint"]

        return time_savings

    def _empty_optimization_result(self) -> dict[str, Any]:
        """Return empty optimization result for no changes."""
        return {
            "skip_tests": False,
            "skip_security": False,
            "skip_docs": False,
            "skip_lint": False,
            "optimization_score": 0,
            "time_savings": 0,
            "change_analysis": {},
            "affected_tests": [],
            "reasoning": {"message": "No changes detected"}
        }


class ReportGenerator:
    """Generates comprehensive change detection reports."""

    def __init__(self, reports_dir: Path):
        """Initialize report generator."""
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_reports(self, result: ChangeAnalysisResult,
                        additional_data: Optional[dict[str, Any]] = None) -> str:
        """Generate comprehensive reports."""
        # Generate JSON report
        json_report_path = self._generate_json_report(result, additional_data)

        # Generate Markdown summary
        self._generate_markdown_summary(result, additional_data)

        # Generate detailed analysis report
        self._generate_detailed_report(result, additional_data)

        return str(json_report_path)

    def _generate_json_report(self, result: ChangeAnalysisResult,
                            additional_data: Optional[dict[str, Any]] = None) -> Path:
        """Generate JSON report with all analysis data."""
        report_file = self.reports_dir / "change-detection-report.json"

        report_data = asdict(result)

        # Add additional analysis data
        if additional_data:
            report_data.update(additional_data)

        # Add metadata
        report_data["metadata"] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "version": "0.0.1",
            "generator": "change-detection-action"
        }

        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)

        return report_file

    def _generate_markdown_summary(self, result: ChangeAnalysisResult,
                                 additional_data: Optional[dict[str, Any]] = None) -> Path:
        """Generate human-readable Markdown summary."""
        md_file = self.reports_dir / "change-detection-summary.md"

        with open(md_file, 'w') as f:
            f.write("# Change Detection Analysis Report\n\n")

            # Summary section
            f.write("## 📊 Summary\n\n")
            f.write(f"- **Files Changed:** {len(result.changed_files)}\n")
            f.write(f"- **Optimization Score:** {result.optimization_score}%\n")
            f.write(f"- **Estimated Time Savings:** {result.time_savings}s\n")
            f.write(f"- **Analysis Time:** {result.execution_time:.2f}s\n\n")

            # Change categories
            if result.change_categories:
                f.write("## 📁 Change Categories\n\n")
                for category, files in result.classifications.items():
                    if files:
                        f.write(f"- **{category.title()}:** {len(files)} files\n")
                        if len(files) <= 10:  # Show files if not too many
                            for file in files[:10]:
                                f.write(f"  - `{file}`\n")
                        if len(files) > 10:
                            f.write(f"  - ... and {len(files) - 10} more\n")
                f.write("\n")

            # Optimization recommendations
            f.write("## 🚀 CI Optimization Recommendations\n\n")

            if result.optimization_score > 0:
                f.write(f"**{result.optimization_score}% of CI pipeline can be optimized!**\n\n")

                if result.skip_tests:
                    f.write("- ✅ **Skip Tests:** No source or dependency changes detected\n")
                if result.skip_security:
                    f.write("- ✅ **Skip Security Scans:** Only documentation/config changes\n")
                if result.skip_docs:
                    f.write("- ✅ **Skip Documentation Build:** No documentation changes\n")
                if result.skip_lint:
                    f.write("- ✅ **Skip Linting:** Only documentation changes\n")

                f.write(f"\n**Estimated time savings: {result.time_savings} seconds**\n\n")
            else:
                f.write("- ⚠️ **Full CI Pipeline Required:** Source or dependency changes require all validation steps\n\n")

            # Affected tests
            if result.affected_tests:
                f.write("## 🧪 Affected Tests\n\n")
                f.write("The following tests should be run based on the changes:\n\n")
                for test in result.affected_tests[:20]:  # Limit to first 20
                    f.write(f"- `{test}`\n")
                if len(result.affected_tests) > 20:
                    f.write(f"- ... and {len(result.affected_tests) - 20} more tests\n")
                f.write("\n")

            # Monorepo information
            if result.affected_packages:
                f.write("## 📦 Affected Packages (Monorepo)\n\n")
                for package in result.affected_packages:
                    f.write(f"- `{package}`\n")
                f.write("\n")

            # Integration examples
            f.write("## 🔧 Integration Examples\n\n")
            f.write("Use these outputs in your GitHub Actions workflow:\n\n")
            f.write("```yaml\n")
            f.write("jobs:\n")
            f.write("  tests:\n")
            f.write("    if: steps.change-detection.outputs.skip-tests != 'true'\n")
            f.write("    runs-on: ubuntu-latest\n")
            f.write("    steps:\n")
            f.write("      - name: Run Tests\n")
            if result.affected_tests:
                f.write("        run: pytest ${{ steps.change-detection.outputs.affected-tests }}\n")
            else:
                f.write("        run: pytest\n")
            f.write("\n")
            f.write("  security:\n")
            f.write("    if: steps.change-detection.outputs.skip-security != 'true'\n")
            f.write("    runs-on: ubuntu-latest\n")
            f.write("    steps:\n")
            f.write("      - name: Security Scan\n")
            f.write("        uses: ./actions/security-scan\n")
            f.write("```\n\n")

            f.write("---\n")
            f.write("*Report generated by Change Detection Action v0.0.1*\n")

        return md_file

    def _generate_detailed_report(self, result: ChangeAnalysisResult,
                                additional_data: Optional[dict[str, Any]] = None) -> Path:
        """Generate detailed analysis report."""
        detail_file = self.reports_dir / "change-detection-detailed.md"

        with open(detail_file, 'w') as f:
            f.write("# Detailed Change Detection Analysis\n\n")

            # File-by-file analysis
            f.write("## 📋 File-by-File Analysis\n\n")
            for category, files in result.classifications.items():
                if files:
                    f.write(f"### {category.title()} Files\n\n")
                    for file in files:
                        f.write(f"- `{file}`\n")
                    f.write("\n")

            # Dependency analysis
            if additional_data and "dependency_graph" in additional_data:
                f.write("## 🔗 Dependency Analysis\n\n")
                f.write(f"- **Total modules analyzed:** {len(additional_data['dependency_graph'])}\n")
                f.write(f"- **Modules with dependencies:** {result.dependency_impact}\n\n")

            # Optimization reasoning
            if additional_data and "optimization_reasoning" in additional_data:
                f.write("## 🤔 Optimization Reasoning\n\n")
                reasoning = additional_data["optimization_reasoning"]
                for job, reason in reasoning.items():
                    f.write(f"- **{job.title()}:** {reason}\n")
                f.write("\n")

            # Performance metrics
            f.write("## ⚡ Performance Metrics\n\n")
            f.write(f"- **Analysis execution time:** {result.execution_time:.2f}s\n")
            f.write(f"- **Files processed:** {len(result.changed_files)}\n")
            f.write(f"- **Categories identified:** {len([c for c in result.classifications.values() if c])}\n\n")

        return detail_file


class ChangeDetectionAction:
    """Main change detection action orchestrator."""

    def __init__(self, project_dir: Path | None = None, reports_dir: Path | None = None,
                 detection_level: str = "standard", **kwargs):
        """Initialize change detection action."""
        self.project_dir = project_dir or Path.cwd()
        self.reports_dir = reports_dir or (self.project_dir / "change-reports")
        self.detection_level = detection_level

        # Configuration
        self.base_ref = kwargs.get("base_ref", "HEAD~1")
        self.head_ref = kwargs.get("head_ref", "HEAD")
        self.enable_test_optimization = kwargs.get("enable_test_optimization", True)
        self.enable_job_skipping = kwargs.get("enable_job_skipping", True)
        self.monorepo_mode = kwargs.get("monorepo_mode", False)
        self.pattern_config = kwargs.get("pattern_config")

        # Initialize components
        self.pattern_matcher = FilePatternMatcher(self._load_custom_patterns())
        self.dependency_analyzer = DependencyAnalyzer(self.project_dir)
        self.monorepo_handler = MonorepoHandler(self.project_dir) if self.monorepo_mode else None
        self.optimization_engine = OptimizationEngine(
            self.enable_test_optimization,
            self.enable_job_skipping
        )
        self.report_generator = ReportGenerator(self.reports_dir)

    def execute(self) -> ChangeAnalysisResult:
        """Execute change detection analysis."""
        start_time = time.time()

        try:
            logger.info(f"Starting change detection analysis (level: {self.detection_level})")

            # Get changed files
            changed_files = self._get_changed_files()

            if not changed_files:
                logger.info("No changes detected")
                return self._create_empty_result(time.time() - start_time)

            logger.info(f"Analyzing {len(changed_files)} changed files")

            # Classify files
            classifications = self.pattern_matcher.classify_files(changed_files)

            # Dependency analysis (for standard and comprehensive levels)
            affected_tests = []
            dependency_impact = 0

            if self.detection_level in ["standard", "comprehensive"]:
                source_files = classifications.get("source", [])
                if source_files:
                    logger.info("Building dependency graph...")
                    self.dependency_analyzer.build_dependency_graph(source_files)
                    affected_tests_set = self.dependency_analyzer.get_affected_tests(changed_files)
                    affected_tests = list(affected_tests_set)
                    dependency_impact = len(self.dependency_analyzer.get_affected_modules(changed_files))

            # Monorepo analysis
            affected_packages = []
            if self.monorepo_mode and self.monorepo_handler:
                logger.info("Analyzing monorepo packages...")
                self.monorepo_handler.detect_packages()
                affected_packages = self.monorepo_handler.get_affected_packages(changed_files)

            # Calculate optimization
            optimization_result = self.optimization_engine.calculate_optimization(
                classifications, affected_tests
            )

            # Create result
            result = ChangeAnalysisResult(
                success=True,
                changed_files=changed_files,
                classifications=classifications,
                change_categories=",".join([cat for cat, files in classifications.items() if files]),
                affected_packages=affected_packages,
                affected_tests=affected_tests,
                dependency_impact=dependency_impact,
                skip_tests=optimization_result["skip_tests"],
                skip_security=optimization_result["skip_security"],
                skip_docs=optimization_result["skip_docs"],
                skip_lint=optimization_result["skip_lint"],
                optimization_score=optimization_result["optimization_score"],
                time_savings=optimization_result["time_savings"],
                execution_time=time.time() - start_time,
                reports_path=str(self.reports_dir)
            )

            # Generate reports
            additional_data = {
                "optimization_reasoning": optimization_result.get("reasoning", {}),
                "change_analysis": optimization_result.get("change_analysis", {}),
                "dependency_graph": {k: {"imports": list(v.imports), "imported_by": list(v.imported_by)}
                                   for k, v in self.dependency_analyzer.dependency_graph.items()}
            }

            self.report_generator.generate_reports(result, additional_data)

            logger.info(f"Change detection completed successfully in {result.execution_time:.2f}s")
            logger.info(f"Optimization score: {result.optimization_score}% (saves {result.time_savings}s)")

            return result

        except Exception as e:
            logger.error(f"Change detection failed: {e}")
            return ChangeAnalysisResult(
                success=False,
                changed_files=[],
                classifications={},
                change_categories="",
                affected_packages=[],
                affected_tests=[],
                dependency_impact=0,
                skip_tests=False,
                skip_security=False,
                skip_docs=False,
                skip_lint=False,
                optimization_score=0,
                time_savings=0,
                execution_time=time.time() - start_time,
                reports_path=str(self.reports_dir),
                failure_reason=str(e)
            )

    def _get_changed_files(self) -> list[str]:
        """Get list of changed files between base and head refs."""
        try:
            cmd = ["git", "diff", "--name-only", f"{self.base_ref}...{self.head_ref}"]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_dir)

            if result.returncode != 0:
                logger.warning(f"Git diff failed: {result.stderr}")
                return []

            files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
            return files

        except Exception as e:
            logger.error(f"Error getting changed files: {e}")
            return []

    def _load_custom_patterns(self) -> Optional[dict[str, list[str]]]:
        """Load custom file patterns from configuration."""
        if not self.pattern_config:
            return None

        config_path = self.project_dir / self.pattern_config
        if not config_path.exists():
            logger.warning(f"Pattern config file not found: {config_path}")
            return None

        try:
            if config_path.suffix.lower() == '.json':
                with open(config_path) as f:
                    data = json.load(f)
                    return data.get("patterns", {})
            elif config_path.suffix.lower() == '.toml':
                import tomllib
                with open(config_path, "rb") as f:
                    data = tomllib.load(f)
                    return data.get("patterns", {})
            else:
                logger.warning(f"Unsupported config file format: {config_path.suffix}")
                return None

        except Exception as e:
            logger.error(f"Failed to load pattern config: {e}")
            return None

    def _create_empty_result(self, execution_time: float) -> ChangeAnalysisResult:
        """Create result for no changes scenario."""
        return ChangeAnalysisResult(
            success=True,
            changed_files=[],
            classifications={},
            change_categories="",
            affected_packages=[],
            affected_tests=[],
            dependency_impact=0,
            skip_tests=False,
            skip_security=False,
            skip_docs=False,
            skip_lint=False,
            optimization_score=0,
            time_savings=0,
            execution_time=execution_time,
            reports_path=str(self.reports_dir)
        )


# Standalone execution support
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Change Detection and CI Optimization")
    parser.add_argument("--project-dir", default=".", help="Project directory")
    parser.add_argument("--base-ref", default="HEAD~1", help="Base reference")
    parser.add_argument("--head-ref", default="HEAD", help="Head reference")
    parser.add_argument("--detection-level", default="standard",
                       choices=["quick", "standard", "comprehensive"])
    parser.add_argument("--monorepo-mode", action="store_true", help="Enable monorepo mode")
    parser.add_argument("--reports-dir", default="change-reports", help="Reports directory")

    args = parser.parse_args()

    action = ChangeDetectionAction(
        project_dir=Path(args.project_dir),
        reports_dir=Path(args.reports_dir),
        detection_level=args.detection_level,
        base_ref=args.base_ref,
        head_ref=args.head_ref,
        monorepo_mode=args.monorepo_mode
    )

    result = action.execute()

    if result.success:
        print("✅ Change detection completed successfully!")
        print(f"📊 Optimization Score: {result.optimization_score}%")
        print(f"⏱️ Time Savings: {result.time_savings}s")
        print(f"📁 Reports: {result.reports_path}")
    else:
        print(f"❌ Change detection failed: {result.failure_reason}")
        exit(1)
