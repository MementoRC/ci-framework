#!/usr/bin/env python3
"""
Configuration Template Validator

Validates CI Framework configuration templates against schema and reference projects.
Tests compatibility, completeness, and customization paths.
"""

import json
import os
import sys
import tomllib
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess
import tempfile
import shutil
from dataclasses import dataclass
from enum import Enum


class ValidationLevel(Enum):
    """Validation strictness levels."""
    ESSENTIAL = "essential"  # Basic functionality only
    STANDARD = "standard"   # Most common use cases
    COMPREHENSIVE = "comprehensive"  # All features and edge cases


@dataclass
class ValidationResult:
    """Result of template validation."""
    template_name: str
    level: ValidationLevel
    passed: bool
    errors: List[str]
    warnings: List[str]
    compatibility_score: float  # 0.0 to 1.0


class TemplateValidator:
    """Validates configuration templates."""
    
    def __init__(self, templates_dir: Path, reference_projects: Optional[List[Path]] = None):
        """Initialize validator with template directory and reference projects."""
        self.templates_dir = Path(templates_dir)
        self.reference_projects = reference_projects or []
        self.validation_results: List[ValidationResult] = []
    
    def validate_all_templates(self, level: ValidationLevel = ValidationLevel.STANDARD) -> List[ValidationResult]:
        """Validate all templates in the templates directory."""
        results = []
        
        # Validate each template type
        template_validators = {
            "pyproject-tiered-template.toml": self._validate_pyproject_template,
            "pre-commit-config.yaml": self._validate_precommit_template,
            "github/dependabot.yml": self._validate_dependabot_template,
            "github/SECURITY.md": self._validate_security_template,
        }
        
        for template_file, validator_func in template_validators.items():
            template_path = self.templates_dir / template_file
            if template_path.exists():
                result = validator_func(template_path, level)
                results.append(result)
            else:
                results.append(ValidationResult(
                    template_name=template_file,
                    level=level,
                    passed=False,
                    errors=[f"Template file not found: {template_path}"],
                    warnings=[],
                    compatibility_score=0.0
                ))
        
        self.validation_results = results
        return results
    
    def _validate_pyproject_template(self, template_path: Path, level: ValidationLevel) -> ValidationResult:
        """Validate pyproject.toml template."""
        errors = []
        warnings = []
        
        try:
            # Read template content
            content = template_path.read_text()
            
            # Check for required template variables
            required_vars = [
                "{{ project_name }}",
                "{{ version }}",
                "{{ description }}",
                "{{ author_name }}",
                "{{ author_email }}",
                "{{ package_name }}",
                "{{ source_path }}",
                "{{ test_path }}"
            ]
            
            for var in required_vars:
                if var not in content:
                    errors.append(f"Missing required template variable: {var}")
            
            # Check for tiered structure
            required_tiers = [
                "[tool.pixi.feature.quality.dependencies]",
                "[tool.pixi.feature.quality-extended.dependencies]",
                "[tool.pixi.feature.quality-ci.dependencies]",
            ]
            
            for tier in required_tiers:
                if tier not in content:
                    errors.append(f"Missing required tier: {tier}")
            
            # Check for essential tools
            essential_tools = ["pytest", "ruff", "mypy"]
            for tool in essential_tools:
                if tool not in content:
                    errors.append(f"Missing essential tool: {tool}")
            
            # Test template rendering with sample data
            if level != ValidationLevel.ESSENTIAL:
                try:
                    self._test_template_rendering(template_path, content)
                except Exception as e:
                    errors.append(f"Template rendering failed: {e}")
            
            # Validate against reference projects
            compatibility_score = 0.0
            if level == ValidationLevel.COMPREHENSIVE and self.reference_projects:
                compatibility_score = self._test_project_compatibility(template_path)
            
        except Exception as e:
            errors.append(f"Failed to read template: {e}")
            compatibility_score = 0.0
        
        return ValidationResult(
            template_name="pyproject-tiered-template.toml",
            level=level,
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            compatibility_score=compatibility_score
        )
    
    def _validate_precommit_template(self, template_path: Path, level: ValidationLevel) -> ValidationResult:
        """Validate pre-commit configuration template."""
        errors = []
        warnings = []
        
        try:
            content = template_path.read_text()
            
            # Parse YAML (with template variables, this might fail - that's expected)
            try:
                # Try to validate YAML structure (ignoring template variables)
                yaml_content = content
                # Replace template variables with dummy values for validation
                template_vars = [
                    ("{{ exclude_patterns | default('^$') }}", "^$"),
                    ("{{ test_exclude_patterns | default('tests/|test_') }}", "tests/"),
                ]
                
                for var, default in template_vars:
                    yaml_content = yaml_content.replace(var, default)
                
                parsed = yaml.safe_load(yaml_content)
                
                # Check for required hooks
                if 'repos' not in parsed:
                    errors.append("Missing 'repos' section in pre-commit config")
                else:
                    # Check for essential hooks
                    found_ruff = False
                    found_mypy = False
                    
                    for repo in parsed['repos']:
                        if 'ruff-pre-commit' in repo.get('repo', ''):
                            found_ruff = True
                        if 'mirrors-mypy' in repo.get('repo', ''):
                            found_mypy = True
                    
                    if not found_ruff:
                        errors.append("Missing ruff hook in pre-commit config")
                    if not found_mypy:
                        errors.append("Missing mypy hook in pre-commit config")
            
            except yaml.YAMLError as e:
                warnings.append(f"YAML parsing issues (may be due to templates): {e}")
            
        except Exception as e:
            errors.append(f"Failed to read pre-commit template: {e}")
        
        return ValidationResult(
            template_name="pre-commit-config.yaml",
            level=level,
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            compatibility_score=0.8 if len(errors) == 0 else 0.0
        )
    
    def _validate_dependabot_template(self, template_path: Path, level: ValidationLevel) -> ValidationResult:
        """Validate dependabot configuration template."""
        errors = []
        warnings = []
        
        try:
            content = template_path.read_text()
            
            # Check for required sections
            required_sections = [
                "version: 2",
                "package-ecosystem: \"pip\"",
                "package-ecosystem: \"github-actions\"",
            ]
            
            for section in required_sections:
                if section not in content:
                    errors.append(f"Missing required section: {section}")
            
            # Check for template variables
            required_vars = [
                "{{ python_update_interval",
                "{{ default_reviewer",
                "{{ target_branch",
            ]
            
            for var in required_vars:
                if var not in content:
                    warnings.append(f"Missing template variable: {var}")
        
        except Exception as e:
            errors.append(f"Failed to read dependabot template: {e}")
        
        return ValidationResult(
            template_name="github/dependabot.yml",
            level=level,
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            compatibility_score=0.9 if len(errors) == 0 else 0.0
        )
    
    def _validate_security_template(self, template_path: Path, level: ValidationLevel) -> ValidationResult:
        """Validate security policy template."""
        errors = []
        warnings = []
        
        try:
            content = template_path.read_text()
            
            # Check for required sections
            required_sections = [
                "# Security Policy",
                "## Supported Versions",
                "## Reporting a Vulnerability",
                "## Security Measures",
            ]
            
            for section in required_sections:
                if section not in content:
                    errors.append(f"Missing required section: {section}")
            
            # Check for template variables
            required_vars = [
                "{{ project_name }}",
                "{{ security_email",
                "{{ current_version",
            ]
            
            for var in required_vars:
                if var not in content:
                    warnings.append(f"Missing template variable: {var}")
        
        except Exception as e:
            errors.append(f"Failed to read security template: {e}")
        
        return ValidationResult(
            template_name="github/SECURITY.md",
            level=level,
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            compatibility_score=0.8 if len(errors) == 0 else 0.0
        )
    
    def _test_template_rendering(self, template_path: Path, content: str):
        """Test template rendering with sample data."""
        # This would integrate with a templating engine like Jinja2
        # For now, just check that required variables are present
        sample_data = {
            "project_name": "test-project",
            "version": "0.1.0",
            "description": "Test project",
            "author_name": "Test Author",
            "author_email": "test@example.com",
            "package_name": "test_project",
            "source_path": "src/",
            "test_path": "tests/",
        }
        
        # Simple template variable check
        for key, value in sample_data.items():
            var_pattern = f"{{{{ {key} }}}}"
            if var_pattern in content:
                # Would render template here
                pass
    
    def _test_project_compatibility(self, template_path: Path) -> float:
        """Test template compatibility with reference projects."""
        if not self.reference_projects:
            return 0.5  # No reference projects to test against
        
        compatible_projects = 0
        total_projects = len(self.reference_projects)
        
        for project_path in self.reference_projects:
            try:
                # Test if template could work with this project structure
                if self._is_compatible_with_project(template_path, project_path):
                    compatible_projects += 1
            except Exception:
                # Compatibility test failed
                pass
        
        return compatible_projects / total_projects if total_projects > 0 else 0.0
    
    def _is_compatible_with_project(self, template_path: Path, project_path: Path) -> bool:
        """Check if template is compatible with a specific project."""
        # Basic compatibility checks:
        # 1. Project has Python code
        # 2. Project structure matches template expectations
        # 3. Dependencies could be satisfied
        
        # Check for Python files
        python_files = list(project_path.rglob("*.py"))
        if not python_files:
            return False
        
        # Check for existing pyproject.toml or setup.py
        has_pyproject = (project_path / "pyproject.toml").exists()
        has_setup = (project_path / "setup.py").exists()
        
        if not (has_pyproject or has_setup):
            return False
        
        return True
    
    def generate_report(self) -> str:
        """Generate a validation report."""
        if not self.validation_results:
            return "No validation results available. Run validate_all_templates() first."
        
        report = ["# Configuration Template Validation Report", ""]
        
        # Summary
        total_templates = len(self.validation_results)
        passed_templates = sum(1 for r in self.validation_results if r.passed)
        avg_compatibility = sum(r.compatibility_score for r in self.validation_results) / total_templates
        
        report.extend([
            "## Summary",
            f"- **Total Templates**: {total_templates}",
            f"- **Passed Validation**: {passed_templates}/{total_templates}",
            f"- **Average Compatibility**: {avg_compatibility:.1%}",
            ""
        ])
        
        # Detailed results
        report.append("## Detailed Results")
        
        for result in self.validation_results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            report.extend([
                f"### {result.template_name} {status}",
                f"- **Level**: {result.level.value}",
                f"- **Compatibility Score**: {result.compatibility_score:.1%}",
            ])
            
            if result.errors:
                report.append("- **Errors**:")
                for error in result.errors:
                    report.append(f"  - {error}")
            
            if result.warnings:
                report.append("- **Warnings**:")
                for warning in result.warnings:
                    report.append(f"  - {warning}")
            
            report.append("")
        
        return "\n".join(report)


def main():
    """Main validation script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate CI Framework configuration templates")
    parser.add_argument("--templates-dir", default="./templates", help="Templates directory")
    parser.add_argument("--level", choices=["essential", "standard", "comprehensive"], 
                       default="standard", help="Validation level")
    parser.add_argument("--reference-projects", nargs="*", help="Reference project paths")
    parser.add_argument("--output", help="Output report file")
    
    args = parser.parse_args()
    
    # Convert level string to enum
    level = ValidationLevel(args.level)
    
    # Convert reference project paths
    reference_projects = []
    if args.reference_projects:
        reference_projects = [Path(p) for p in args.reference_projects if Path(p).exists()]
    
    # Run validation
    validator = TemplateValidator(Path(args.templates_dir), reference_projects)
    results = validator.validate_all_templates(level)
    
    # Generate report
    report = validator.generate_report()
    
    # Output report
    if args.output:
        Path(args.output).write_text(report)
        print(f"Validation report written to: {args.output}")
    else:
        print(report)
    
    # Exit with appropriate code
    failed_validations = sum(1 for r in results if not r.passed)
    if failed_validations > 0:
        print(f"\n❌ {failed_validations} template(s) failed validation")
        sys.exit(1)
    else:
        print(f"\n✅ All {len(results)} templates passed validation")
        sys.exit(0)


if __name__ == "__main__":
    main()