# CI Framework Configuration Templates

This directory contains centralized configuration templates for consistent project setup across the organization.

## Template Categories

### Core Configuration Templates
- **pyproject.toml**: Tiered Python project configuration
- **pre-commit-config.yaml**: Standardized pre-commit hooks
- **ruff.toml**: Unified linting and formatting rules
- **pytest.ini**: Testing configuration with coverage and timeouts

### GitHub Templates
- **dependabot.yml**: Automated dependency updates
- **security.yml**: Security policy template
- **workflow-templates/**: GitHub Actions workflow templates

## Usage

### Quick Start
1. Copy the appropriate template to your project root
2. Customize the placeholders (marked with `{{ }}`)
3. Run validation: `python templates/validate_config.py`
4. Test migration: `python templates/test_migration.py`

### Template Tiers

#### Essential Tier
- Basic testing and linting
- Minimal dependencies
- Fast CI execution

#### Extended Tier  
- Security scanning
- Code quality analysis
- Performance monitoring

#### Full Tier
- Comprehensive reporting
- Advanced security features
- Complete CI/CD pipeline

## Validation

Each template includes:
- Schema validation
- Compatibility testing with 7 reference projects
- Migration path verification
- Customization point documentation

## Reference Projects

Templates are tested against:
1. hb-strategy-sandbox
2. cheap-llm
3. claude-code-knowledge-framework
4. git (llm-compliance)
5. aider
6. pytest-analyzer
7. ci-framework (this project)

## Contributing

When updating templates:
1. Test against all reference projects
2. Update validation scripts
3. Document breaking changes
4. Provide migration guides