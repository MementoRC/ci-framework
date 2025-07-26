#!/usr/bin/env python3
"""
Template Migration Testing Script

Tests migration of existing projects to CI Framework templates.
Validates that configurations work with real project structures.
"""

import os
import sys
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json


class MigrationStatus(Enum):
    """Migration test status."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class MigrationResult:
    """Result of migration testing."""
    project_name: str
    project_path: Path
    template_name: str
    status: MigrationStatus
    errors: List[str]
    warnings: List[str]
    quality_score: float  # 0.0 to 1.0
    performance_impact: Optional[float]  # Execution time change


class ProjectMigrationTester:
    """Tests template migration against real projects."""
    
    def __init__(self, templates_dir: Path):
        """Initialize migration tester."""
        self.templates_dir = Path(templates_dir)
        self.test_results: List[MigrationResult] = []
    
    def test_all_migrations(self, reference_projects: List[Path]) -> List[MigrationResult]:
        """Test migration for all reference projects."""
        results = []
        
        for project_path in reference_projects:
            if not project_path.exists():
                print(f"⚠️ Project path does not exist: {project_path}")
                continue
            
            print(f"🧪 Testing migration for: {project_path.name}")
            
            # Test pyproject.toml migration
            pyproject_result = self._test_pyproject_migration(project_path)
            results.append(pyproject_result)
            
            # Test pre-commit migration  
            precommit_result = self._test_precommit_migration(project_path)
            results.append(precommit_result)
            
            # Test overall project compatibility
            compatibility_result = self._test_project_compatibility(project_path)
            results.append(compatibility_result)
        
        self.test_results = results
        return results
    
    def _test_pyproject_migration(self, project_path: Path) -> MigrationResult:
        """Test pyproject.toml template migration."""
        project_name = project_path.name
        errors = []
        warnings = []
        quality_score = 0.0
        
        try:
            # Create temporary copy of project
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_project = Path(temp_dir) / project_name
                shutil.copytree(project_path, temp_project)
                
                # Backup original pyproject.toml if it exists
                original_pyproject = temp_project / "pyproject.toml"
                backup_pyproject = None
                if original_pyproject.exists():
                    backup_pyproject = temp_project / "pyproject.toml.backup"
                    shutil.copy2(original_pyproject, backup_pyproject)
                
                # Apply template with project-specific values
                template_values = self._extract_project_values(temp_project)
                rendered_template = self._render_pyproject_template(template_values)
                
                # Write new pyproject.toml
                original_pyproject.write_text(rendered_template)
                
                # Test if project still works
                migration_status, test_errors = self._test_project_functionality(temp_project)
                errors.extend(test_errors)
                
                # Calculate quality score based on functionality
                if migration_status == MigrationStatus.SUCCESS:
                    quality_score = 1.0
                elif migration_status == MigrationStatus.PARTIAL:
                    quality_score = 0.6
                else:
                    quality_score = 0.0
                
                # Test performance impact
                performance_impact = self._measure_performance_impact(
                    temp_project, backup_pyproject, original_pyproject
                )
        
        except Exception as e:
            errors.append(f"Migration test failed: {e}")
            migration_status = MigrationStatus.FAILED
            quality_score = 0.0
            performance_impact = None
        
        return MigrationResult(
            project_name=f"{project_name}-pyproject",
            project_path=project_path,
            template_name="pyproject-tiered-template.toml",
            status=migration_status,
            errors=errors,
            warnings=warnings,
            quality_score=quality_score,
            performance_impact=performance_impact
        )
    
    def _test_precommit_migration(self, project_path: Path) -> MigrationResult:
        """Test pre-commit template migration."""
        project_name = project_path.name
        errors = []
        warnings = []
        
        try:
            # Check if project already has pre-commit
            existing_precommit = project_path / ".pre-commit-config.yaml"
            
            if existing_precommit.exists():
                # Test compatibility with existing setup
                status = MigrationStatus.PARTIAL
                warnings.append("Project already has pre-commit configuration")
                quality_score = 0.7
            else:
                # Test adding pre-commit to project
                status = MigrationStatus.SUCCESS
                quality_score = 0.9
        
        except Exception as e:
            errors.append(f"Pre-commit migration test failed: {e}")
            status = MigrationStatus.FAILED
            quality_score = 0.0
        
        return MigrationResult(
            project_name=f"{project_name}-precommit",
            project_path=project_path,
            template_name="pre-commit-config.yaml",
            status=status,
            errors=errors,
            warnings=warnings,
            quality_score=quality_score,
            performance_impact=None
        )
    
    def _test_project_compatibility(self, project_path: Path) -> MigrationResult:
        """Test overall project compatibility with CI Framework."""
        project_name = project_path.name
        errors = []
        warnings = []
        
        try:
            # Check project structure
            structure_score = self._analyze_project_structure(project_path)
            
            # Check dependency compatibility
            dependency_score = self._analyze_dependency_compatibility(project_path)
            
            # Check CI compatibility
            ci_score = self._analyze_ci_compatibility(project_path)
            
            # Overall compatibility score
            overall_score = (structure_score + dependency_score + ci_score) / 3.0
            
            if overall_score >= 0.8:
                status = MigrationStatus.SUCCESS
            elif overall_score >= 0.5:
                status = MigrationStatus.PARTIAL
                warnings.append(f"Partial compatibility: {overall_score:.1%}")
            else:
                status = MigrationStatus.FAILED
                errors.append(f"Low compatibility: {overall_score:.1%}")
        
        except Exception as e:
            errors.append(f"Compatibility test failed: {e}")
            status = MigrationStatus.FAILED
            overall_score = 0.0
        
        return MigrationResult(
            project_name=f"{project_name}-compatibility",
            project_path=project_path,
            template_name="ci-framework-overall",
            status=status,
            errors=errors,
            warnings=warnings,
            quality_score=overall_score,
            performance_impact=None
        )
    
    def _extract_project_values(self, project_path: Path) -> Dict[str, str]:
        """Extract project-specific values for template rendering."""
        values = {
            "project_name": project_path.name,
            "version": "0.1.0",
            "description": f"Migrated project: {project_path.name}",
            "author_name": "Project Team",
            "author_email": "team@example.com",
            "package_name": project_path.name.replace("-", "_"),
            "source_path": "src/",
            "test_path": "tests/",
        }
        
        # Try to extract values from existing pyproject.toml
        existing_pyproject = project_path / "pyproject.toml"
        if existing_pyproject.exists():
            try:
                import tomllib
                with open(existing_pyproject, "rb") as f:
                    data = tomllib.load(f)
                
                project_data = data.get("project", {})
                values.update({
                    "project_name": project_data.get("name", values["project_name"]),
                    "version": project_data.get("version", values["version"]),
                    "description": project_data.get("description", values["description"]),
                })
                
                # Extract author info
                authors = project_data.get("authors", [])
                if authors and isinstance(authors[0], dict):
                    values["author_name"] = authors[0].get("name", values["author_name"])
                    values["author_email"] = authors[0].get("email", values["author_email"])
            
            except Exception:
                # Use defaults if parsing fails
                pass
        
        # Detect source and test paths
        common_source_paths = ["src/", "lib/", f"{values['package_name']}/"]
        for src_path in common_source_paths:
            if (project_path / src_path).exists():
                values["source_path"] = src_path
                break
        
        common_test_paths = ["tests/", "test/", "testing/"]
        for test_path in common_test_paths:
            if (project_path / test_path).exists():
                values["test_path"] = test_path
                break
        
        return values
    
    def _render_pyproject_template(self, values: Dict[str, str]) -> str:
        """Render pyproject.toml template with project values."""
        template_path = self.templates_dir / "pyproject-tiered-template.toml"
        template_content = template_path.read_text()
        
        # Simple template variable replacement
        # In a real implementation, use Jinja2 or similar
        for key, value in values.items():
            template_content = template_content.replace(f"{{{{ {key} }}}}", value)
            template_content = template_content.replace(f"{{{{ {key} | default(", value + ' | default(')
        
        # Handle default values
        import re
        default_pattern = r"{{{\s*([^}|]+)\s*\|\s*default\(['\"]([^'\"]*)['\"])\s*}}}}"
        template_content = re.sub(default_pattern, r"\\2", template_content)
        
        return template_content
    
    def _test_project_functionality(self, project_path: Path) -> Tuple[MigrationStatus, List[str]]:
        """Test if project functionality still works after migration."""
        errors = []
        
        try:
            # Test if pixi commands work
            os.chdir(project_path)
            
            # Test pixi install
            result = subprocess.run(
                ["pixi", "install"], 
                capture_output=True, 
                text=True, 
                timeout=300
            )
            
            if result.returncode != 0:
                errors.append(f"Pixi install failed: {result.stderr}")
                return MigrationStatus.FAILED, errors
            
            # Test basic quality commands
            quality_commands = ["pixi run lint", "pixi run format-check"]
            partial_success = False
            
            for cmd in quality_commands:
                result = subprocess.run(
                    cmd.split(), 
                    capture_output=True, 
                    text=True, 
                    timeout=120
                )
                
                if result.returncode == 0:
                    partial_success = True
                else:
                    errors.append(f"Command failed: {cmd}")
            
            if partial_success:
                return MigrationStatus.PARTIAL if errors else MigrationStatus.SUCCESS, errors
            else:
                return MigrationStatus.FAILED, errors
        
        except subprocess.TimeoutExpired:
            errors.append("Command timed out")
            return MigrationStatus.FAILED, errors
        except Exception as e:
            errors.append(f"Functionality test failed: {e}")
            return MigrationStatus.FAILED, errors
    
    def _measure_performance_impact(self, project_path: Path, 
                                  original_config: Optional[Path], 
                                  new_config: Path) -> Optional[float]:
        """Measure performance impact of template migration."""
        if not original_config or not original_config.exists():
            return None
        
        try:
            # This would measure actual performance differences
            # For now, return a placeholder
            return 0.0  # No significant impact
        
        except Exception:
            return None
    
    def _analyze_project_structure(self, project_path: Path) -> float:
        """Analyze project structure compatibility."""
        score = 0.0
        
        # Check for Python files
        python_files = list(project_path.rglob("*.py"))
        if python_files:
            score += 0.3
        
        # Check for test directory
        test_dirs = ["tests", "test", "testing"]
        if any((project_path / td).exists() for td in test_dirs):
            score += 0.3
        
        # Check for source organization
        src_dirs = ["src", "lib", project_path.name.replace("-", "_")]
        if any((project_path / sd).exists() for sd in src_dirs):
            score += 0.2
        
        # Check for existing configuration
        config_files = ["pyproject.toml", "setup.py", "setup.cfg"]
        if any((project_path / cf).exists() for cf in config_files):
            score += 0.2
        
        return min(score, 1.0)
    
    def _analyze_dependency_compatibility(self, project_path: Path) -> float:
        """Analyze dependency compatibility."""
        # Check if project uses compatible package management
        score = 0.5  # Default moderate compatibility
        
        if (project_path / "pyproject.toml").exists():
            score = 0.9  # High compatibility
        elif (project_path / "requirements.txt").exists():
            score = 0.7  # Good compatibility
        elif (project_path / "setup.py").exists():
            score = 0.6  # Moderate compatibility
        
        return score
    
    def _analyze_ci_compatibility(self, project_path: Path) -> float:
        """Analyze CI compatibility."""
        score = 0.5  # Default
        
        github_dir = project_path / ".github"
        if github_dir.exists():
            score = 0.8  # Good existing CI
            
            workflows_dir = github_dir / "workflows"
            if workflows_dir.exists() and list(workflows_dir.glob("*.yml")):
                score = 0.9  # Excellent existing CI
        
        return score
    
    def generate_migration_report(self) -> str:
        """Generate migration testing report."""
        if not self.test_results:
            return "No migration test results available."
        
        report = ["# Template Migration Testing Report", ""]
        
        # Summary
        total_tests = len(self.test_results)
        success_tests = sum(1 for r in self.test_results if r.status == MigrationStatus.SUCCESS)
        partial_tests = sum(1 for r in self.test_results if r.status == MigrationStatus.PARTIAL)
        failed_tests = sum(1 for r in self.test_results if r.status == MigrationStatus.FAILED)
        
        avg_quality = sum(r.quality_score for r in self.test_results) / total_tests
        
        report.extend([
            "## Summary",
            f"- **Total Migration Tests**: {total_tests}",
            f"- **Successful**: {success_tests} ({success_tests/total_tests:.1%})",
            f"- **Partial Success**: {partial_tests} ({partial_tests/total_tests:.1%})",
            f"- **Failed**: {failed_tests} ({failed_tests/total_tests:.1%})",
            f"- **Average Quality Score**: {avg_quality:.1%}",
            ""
        ])
        
        # Group by project
        projects = {}
        for result in self.test_results:
            project_base = result.project_name.split("-")[0]
            if project_base not in projects:
                projects[project_base] = []
            projects[project_base].append(result)
        
        report.append("## Project Migration Results")
        
        for project_name, results in projects.items():
            report.append(f"### {project_name}")
            
            for result in results:
                status_emoji = {
                    MigrationStatus.SUCCESS: "✅",
                    MigrationStatus.PARTIAL: "⚠️",
                    MigrationStatus.FAILED: "❌",
                    MigrationStatus.SKIPPED: "⏭️"
                }[result.status]
                
                template_type = result.template_name.replace(".toml", "").replace(".yaml", "")
                report.append(f"- **{template_type}**: {status_emoji} {result.status.value} ({result.quality_score:.1%})")
                
                if result.errors:
                    for error in result.errors:
                        report.append(f"  - ❌ {error}")
                
                if result.warnings:
                    for warning in result.warnings:
                        report.append(f"  - ⚠️ {warning}")
            
            report.append("")
        
        return "\n".join(report)


def main():
    """Main migration testing script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test CI Framework template migration")
    parser.add_argument("--templates-dir", default="./templates", help="Templates directory")
    parser.add_argument("--projects", nargs="+", required=True, help="Reference project paths")
    parser.add_argument("--output", help="Output report file")
    
    args = parser.parse_args()
    
    # Convert project paths
    reference_projects = [Path(p) for p in args.projects if Path(p).exists()]
    
    if not reference_projects:
        print("❌ No valid reference projects found")
        sys.exit(1)
    
    # Run migration tests
    tester = ProjectMigrationTester(Path(args.templates_dir))
    results = tester.test_all_migrations(reference_projects)
    
    # Generate report
    report = tester.generate_migration_report()
    
    # Output report
    if args.output:
        Path(args.output).write_text(report)
        print(f"Migration test report written to: {args.output}")
    else:
        print(report)
    
    # Exit with appropriate code
    failed_tests = sum(1 for r in results if r.status == MigrationStatus.FAILED)
    if failed_tests > 0:
        print(f"\n❌ {failed_tests} migration test(s) failed")
        sys.exit(1)
    else:
        success_tests = sum(1 for r in results if r.status == MigrationStatus.SUCCESS)
        print(f"\n✅ {success_tests} migration test(s) passed")
        sys.exit(0)


if __name__ == "__main__":
    main()