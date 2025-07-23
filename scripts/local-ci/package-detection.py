#!/usr/bin/env python3
"""
Package Detection Script for Local CI
=====================================

Smart monorepo package discovery that detects pixi, poetry, npm, and pip configurations.
Provides JSON output for integration with shell scripts.

Usage:
    python package-detection.py [--format json|list] [--type all|pixi|poetry|npm|pip] [--root-dir DIR]

Exit Codes:
    0: Success
    1: No packages found
    2: Invalid arguments
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set


class PackageDetector:
    """Detects package configurations in a project tree."""
    
    PACKAGE_CONFIGS = {
        'pixi': ['pyproject.toml'],  # Check for [tool.pixi] section
        'poetry': ['pyproject.toml'],  # Check for [tool.poetry] section
        'npm': ['package.json'],
        'pip': ['requirements.txt', 'requirements.in', 'setup.py', 'setup.cfg']
    }
    
    def __init__(self, root_dir: str = '.'):
        self.root_dir = Path(root_dir).resolve()
        self.packages = {}
        
    def detect_packages(self, package_types: Set[str] = None) -> Dict[str, List[Dict]]:
        """
        Detect packages in the project tree.
        
        Args:
            package_types: Set of package types to detect ('pixi', 'poetry', 'npm', 'pip')
                          If None, detects all types.
        
        Returns:
            Dictionary mapping package type to list of package info dictionaries
        """
        if package_types is None:
            package_types = set(self.PACKAGE_CONFIGS.keys())
            
        results = {pkg_type: [] for pkg_type in package_types}
        
        # Walk the directory tree
        for root, dirs, files in os.walk(self.root_dir):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
                '__pycache__', 'node_modules', 'venv', 'env', '.venv', '.env',
                'build', 'dist', 'htmlcov', 'coverage', '.pytest_cache'
            }]
            
            root_path = Path(root)
            
            # Check each package type
            for pkg_type in package_types:
                config_files = self.PACKAGE_CONFIGS[pkg_type]
                
                for config_file in config_files:
                    config_path = root_path / config_file
                    
                    if config_path.exists():
                        package_info = self._analyze_package(pkg_type, config_path)
                        if package_info:
                            results[pkg_type].append(package_info)
                            
        return results
    
    def _analyze_package(self, pkg_type: str, config_path: Path) -> Optional[Dict]:
        """
        Analyze a specific package configuration file.
        
        Args:
            pkg_type: Type of package ('pixi', 'poetry', 'npm', 'pip')
            config_path: Path to the configuration file
            
        Returns:
            Package information dictionary or None if not a valid package
        """
        try:
            if pkg_type in {'pixi', 'poetry'} and config_path.name == 'pyproject.toml':
                return self._analyze_pyproject_toml(pkg_type, config_path)
            elif pkg_type == 'npm' and config_path.name == 'package.json':
                return self._analyze_package_json(config_path)
            elif pkg_type == 'pip':
                return self._analyze_pip_package(config_path)
        except Exception as e:
            # Log error but continue detection
            print(f"Warning: Error analyzing {config_path}: {e}", file=sys.stderr)
            
        return None
    
    def _analyze_pyproject_toml(self, pkg_type: str, config_path: Path) -> Optional[Dict]:
        """Analyze pyproject.toml for pixi or poetry configuration."""
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                # Fallback: simple text parsing for detection
                with open(config_path, 'r') as f:
                    content = f.read()
                    if f'[tool.{pkg_type}' in content:
                        return self._create_package_info(pkg_type, config_path, 'unknown')
                return None
        
        try:
            with open(config_path, 'rb') as f:
                data = tomllib.load(f)
                
            tool_section = data.get('tool', {})
            
            if pkg_type == 'pixi' and 'pixi' in tool_section:
                project_info = tool_section['pixi'].get('project', {})
                name = project_info.get('name', config_path.parent.name)
                return self._create_package_info(pkg_type, config_path, name, data=tool_section['pixi'])
                
            elif pkg_type == 'poetry' and 'poetry' in tool_section:
                name = tool_section['poetry'].get('name', config_path.parent.name)
                return self._create_package_info(pkg_type, config_path, name, data=tool_section['poetry'])
                
        except Exception:
            # Fallback to simple detection
            with open(config_path, 'r') as f:
                content = f.read()
                if f'[tool.{pkg_type}' in content:
                    return self._create_package_info(pkg_type, config_path, config_path.parent.name)
                    
        return None
    
    def _analyze_package_json(self, config_path: Path) -> Dict:
        """Analyze package.json for npm configuration."""
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
                
            name = data.get('name', config_path.parent.name)
            return self._create_package_info('npm', config_path, name, data=data)
            
        except json.JSONDecodeError:
            return self._create_package_info('npm', config_path, config_path.parent.name)
    
    def _analyze_pip_package(self, config_path: Path) -> Dict:
        """Analyze pip package configuration."""
        name = config_path.parent.name
        
        # Try to extract name from setup.py or setup.cfg
        if config_path.name in {'setup.py', 'setup.cfg'}:
            try:
                with open(config_path, 'r') as f:
                    content = f.read()
                    
                # Simple regex to find name in setup files
                import re
                name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                if name_match:
                    name = name_match.group(1)
            except Exception:
                pass
                
        return self._create_package_info('pip', config_path, name)
    
    def _create_package_info(self, pkg_type: str, config_path: Path, name: str, data: Dict = None) -> Dict:
        """Create standardized package information dictionary."""
        rel_path = config_path.relative_to(self.root_dir)
        package_dir = config_path.parent.relative_to(self.root_dir)
        
        info = {
            'name': name,
            'type': pkg_type,
            'path': str(package_dir),
            'config_file': str(rel_path),
            'absolute_path': str(config_path.parent),
            'has_tests': self._has_tests(config_path.parent),
            'commands': self._detect_commands(pkg_type, config_path.parent, data)
        }
        
        return info
    
    def _has_tests(self, package_dir: Path) -> bool:
        """Check if package has test directories."""
        test_patterns = {'test', 'tests', 'test_*', '*_test'}
        
        for item in package_dir.iterdir():
            if item.is_dir():
                if item.name.lower() in {'test', 'tests'}:
                    return True
                if item.name.startswith('test_') or item.name.endswith('_test'):
                    return True
                    
        # Check for test files
        for item in package_dir.rglob('test_*.py'):
            return True
            
        return False
    
    def _detect_commands(self, pkg_type: str, package_dir: Path, data: Dict = None) -> Dict[str, str]:
        """Detect available commands for the package type."""
        commands = {}
        
        if pkg_type == 'pixi':
            commands.update({
                'install': 'pixi install',
                'test': 'pixi run test',
                'lint': 'pixi run lint',
                'quality': 'pixi run quality',
                'shell': 'pixi shell'
            })
            
            # Check for custom tasks in data
            if data and 'tasks' in data:
                for task_name in data['tasks']:
                    commands[task_name] = f'pixi run {task_name}'
                    
        elif pkg_type == 'poetry':
            commands.update({
                'install': 'poetry install',
                'test': 'poetry run pytest',
                'lint': 'poetry run ruff check',
                'shell': 'poetry shell'
            })
            
        elif pkg_type == 'npm':
            commands.update({
                'install': 'npm install',
                'test': 'npm test',
                'lint': 'npm run lint',
                'build': 'npm run build'
            })
            
            # Check for custom scripts in package.json
            if data and 'scripts' in data:
                for script_name in data['scripts']:
                    commands[script_name] = f'npm run {script_name}'
                    
        elif pkg_type == 'pip':
            commands.update({
                'install': 'pip install -r requirements.txt',
                'test': 'python -m pytest',
                'lint': 'python -m ruff check'
            })
            
        return commands


def main():
    """Main entry point for the package detection script."""
    parser = argparse.ArgumentParser(
        description='Detect package configurations in a project tree',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--format',
        choices=['json', 'list'],
        default='json',
        help='Output format (default: json)'
    )
    
    parser.add_argument(
        '--type',
        choices=['all', 'pixi', 'poetry', 'npm', 'pip'],
        default='all',
        help='Package types to detect (default: all)'
    )
    
    parser.add_argument(
        '--root-dir',
        default='.',
        help='Root directory to search (default: current directory)'
    )
    
    args = parser.parse_args()
    
    # Determine package types to detect
    if args.type == 'all':
        package_types = None
    else:
        package_types = {args.type}
    
    try:
        detector = PackageDetector(args.root_dir)
        packages = detector.detect_packages(package_types)
        
        # Filter out empty results
        packages = {k: v for k, v in packages.items() if v}
        
        if not packages:
            print("No packages found", file=sys.stderr)
            sys.exit(1)
            
        if args.format == 'json':
            print(json.dumps(packages, indent=2))
        else:
            # List format
            for pkg_type, pkg_list in packages.items():
                for pkg in pkg_list:
                    print(f"{pkg_type}:{pkg['path']}:{pkg['name']}")
                    
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()