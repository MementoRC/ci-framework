#!/bin/bash
# Local Quality Gates Script
# ==========================
#
# Mirrors GitHub Actions quality gates functionality for local development.
# Supports tier-based execution (essential, extended, full) with identical
# behavior to the GitHub Actions quality-gates action.
#
# Usage:
#   ./local-quality-gates.sh [OPTIONS] [TIER]
#
# Tiers:
#   essential  - Fast critical checks (tests, lint, typecheck) - 5min timeout
#   extended   - Essential + security scans - 10min timeout  
#   full       - Extended + reports and analysis - 15min timeout
#
# Exit Codes:
#   0: All quality gates passed
#   1: Quality gate failures detected
#   2: Configuration or environment error
#   130: Interrupted by user

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Script-specific defaults
DEFAULT_TIER="essential"
PARALLEL=1
FAIL_FAST=1

# Usage information
show_usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS] [TIER]

Execute local quality gates with tier-based validation.

TIERS:
  essential     Fast critical checks (tests, lint, typecheck)
  extended      Essential + security scans  
  full          Extended + comprehensive reports and analysis

OPTIONS:
  -t, --tier TIER           Quality tier to execute (default: $DEFAULT_TIER)
  -p, --package PATH        Target specific package directory
  -j, --parallel            Enable parallel execution (default: enabled)
  -s, --sequential          Disable parallel execution
  -f, --fail-fast           Stop on first failure (default: enabled)
  -c, --continue-on-error   Continue on failures
  -T, --timeout SECONDS     Override default timeout
      --no-color            Disable colored output
  -v, --verbose             Enable verbose output
  -d, --debug               Enable debug output
  -n, --dry-run             Show what would be done without executing
  -h, --help                Show this help message

EXAMPLES:
  $(basename "$0")                           # Run essential tier
  $(basename "$0") extended                  # Run extended tier
  $(basename "$0") --package src/api full    # Run full tier on specific package
  $(basename "$0") --sequential --timeout 300  # Run with custom settings

Exit Codes:
  0   All quality gates passed
  1   Quality gate failures detected  
  2   Configuration or environment error
  130 Interrupted by user

This script mirrors the GitHub Actions quality-gates behavior for local development.
EOF
}

# Parse command line arguments
parse_script_args() {
    TIER="$DEFAULT_TIER"
    PACKAGE_PATH=""
    TIMEOUT=""
    NO_COLOR=0
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--tier)
                TIER="$2"
                shift 2
                ;;
            -p|--package)
                PACKAGE_PATH="$2"
                shift 2
                ;;
            -j|--parallel)
                PARALLEL=1
                shift
                ;;
            -s|--sequential)
                PARALLEL=0
                shift
                ;;
            -f|--fail-fast)
                FAIL_FAST=1
                shift
                ;;
            -c|--continue-on-error)
                FAIL_FAST=0
                shift
                ;;
            -T|--timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --no-color)
                NO_COLOR=1
                shift
                ;;
            essential|extended|full)
                TIER="$1"
                shift
                ;;
            --)
                shift
                break
                ;;
            -*)
                # Common options handled by parse_args
                break
                ;;
            *)
                # Assume it's a tier if it matches
                if [[ "$1" =~ ^(essential|extended|full)$ ]]; then
                    TIER="$1"
                    shift
                else
                    die "Unknown argument: $1"
                fi
                ;;
        esac
    done
    
    # Disable colors if requested
    if [[ "$NO_COLOR" == "1" ]]; then
        RED="" GREEN="" YELLOW="" BLUE="" PURPLE="" CYAN="" NC=""
    fi
    
    # Validate tier
    if [[ ! "$TIER" =~ ^(essential|extended|full)$ ]]; then
        die "Invalid tier: $TIER. Must be one of: essential, extended, full"
    fi
    
    # Set default timeout if not specified
    if [[ -z "$TIMEOUT" ]]; then
        TIMEOUT=$(get_tier_timeout "$TIER")
    fi
    
    # Set package path to current directory if not specified
    if [[ -z "$PACKAGE_PATH" ]]; then
        PACKAGE_PATH="$PWD"
    fi
    
    # Convert to absolute path
    PACKAGE_PATH="$(cd "$PACKAGE_PATH" && pwd)"
}

# Detect packages to process
detect_packages() {
    log_info "Detecting packages in $PACKAGE_PATH..."
    
    local temp_file
    temp_file=$(mktemp)
    
    if ! python3 "$SCRIPT_DIR/package-detection.py" --root-dir "$PACKAGE_PATH" > "$temp_file" 2>/dev/null; then
        rm -f "$temp_file"
        die "No packages detected in $PACKAGE_PATH"
    fi
    
    log_debug "Package detection output saved to $temp_file"
    echo "$temp_file"
}

# Get quality commands for a package type and tier
get_quality_commands() {
    local pkg_type="$1"
    local tier="$2"
    
    case "$pkg_type" in
        pixi)
            case "$tier" in
                essential)
                    echo "test lint typecheck"
                    ;;
                extended)
                    echo "test lint typecheck security-scan"
                    ;;
                full)
                    echo "test lint typecheck security-scan quality check-all"
                    ;;
            esac
            ;;
        poetry)
            case "$tier" in
                essential)
                    echo "pytest ruff mypy"
                    ;;
                extended)
                    echo "pytest ruff mypy bandit"
                    ;;
                full)
                    echo "pytest ruff mypy bandit safety pip-audit"
                    ;;
            esac
            ;;
        npm)
            case "$tier" in
                essential)
                    echo "test lint type-check"
                    ;;
                extended)
                    echo "test lint type-check audit"
                    ;;
                full)
                    echo "test lint type-check audit build"
                    ;;
            esac
            ;;
        pip)
            case "$tier" in
                essential)
                    echo "pytest ruff mypy"
                    ;;
                extended)
                    echo "pytest ruff mypy bandit"
                    ;;
                full)
                    echo "pytest ruff mypy bandit safety pip-audit"
                    ;;
            esac
            ;;
        *)
            die "Unsupported package type: $pkg_type"
            ;;
    esac
}

# Execute quality command for a specific package
execute_quality_command() {
    local pkg_type="$1"
    local command="$2"
    local package_dir="$3"
    local package_name="$4"
    
    log_step_start="$(date +%s)"
    
    case "$pkg_type" in
        pixi)
            log_info "[$package_name] Running: pixi run $command"
            if [[ "$DRY_RUN" == "1" ]]; then
                log_info "[DRY RUN] Would execute: pixi run $command in $package_dir"
                return 0
            fi
            (cd "$package_dir" && run_with_timeout "$TIMEOUT" pixi run "$command")
            ;;
        poetry)
            log_info "[$package_name] Running: poetry run $command"
            if [[ "$DRY_RUN" == "1" ]]; then
                log_info "[DRY RUN] Would execute: poetry run $command in $package_dir"
                return 0
            fi
            (cd "$package_dir" && run_with_timeout "$TIMEOUT" poetry run "$command")
            ;;
        npm)
            log_info "[$package_name] Running: npm run $command"
            if [[ "$DRY_RUN" == "1" ]]; then
                log_info "[DRY RUN] Would execute: npm run $command in $package_dir"
                return 0
            fi
            (cd "$package_dir" && run_with_timeout "$TIMEOUT" npm run "$command")
            ;;
        pip)
            log_info "[$package_name] Running: python -m $command"
            if [[ "$DRY_RUN" == "1" ]]; then
                log_info "[DRY RUN] Would execute: python -m $command in $package_dir"
                return 0
            fi
            (cd "$package_dir" && run_with_timeout "$TIMEOUT" python -m "$command")
            ;;
    esac
    
    local duration=$(($(date +%s) - log_step_start))
    log_success "[$package_name] Completed $command in ${duration}s"
}

# Process a single package
process_package() {
    local package_info="$1"
    local tier="$2"
    
    local pkg_name pkg_type pkg_path pkg_dir
    pkg_name=$(echo "$package_info" | jq -r '.name')
    pkg_type=$(echo "$package_info" | jq -r '.type')
    pkg_path=$(echo "$package_info" | jq -r '.path')
    pkg_dir=$(echo "$package_info" | jq -r '.absolute_path')
    
    log_info "Processing package: $pkg_name ($pkg_type) at $pkg_path"
    
    # Check if package manager is available
    check_package_manager "$pkg_type"
    
    # Get commands for this tier
    local commands
    commands=$(get_quality_commands "$pkg_type" "$tier")
    
    if [[ -z "$commands" ]]; then
        log_warning "No commands defined for $pkg_type with tier $tier"
        return 0
    fi
    
    # Execute commands
    local failed_commands=()
    local total_commands
    total_commands=$(echo "$commands" | wc -w)
    local current_command=1
    
    for command in $commands; do
        log_step "$current_command" "$total_commands" "Executing $command for $pkg_name"
        
        if ! execute_quality_command "$pkg_type" "$command" "$pkg_dir" "$pkg_name"; then
            failed_commands+=("$command")
            log_error "[$pkg_name] Command failed: $command"
            
            if [[ "$FAIL_FAST" == "1" ]]; then
                die "Failing fast due to error in $pkg_name:$command"
            fi
        fi
        
        ((current_command++))
    done
    
    if [[ ${#failed_commands[@]} -gt 0 ]]; then
        log_error "[$pkg_name] Failed commands: ${failed_commands[*]}"
        return 1
    else
        log_success "[$pkg_name] All quality gates passed"
        return 0
    fi
}

# Process all packages
process_packages() {
    local packages_file="$1"
    local tier="$2"
    
    local failed_packages=()
    local processed_packages=0
    local total_packages=0
    
    # Count total packages
    for pkg_type in $(jq -r 'keys[]' "$packages_file"); do
        local count
        count=$(jq -r ".[\"$pkg_type\"] | length" "$packages_file")
        total_packages=$((total_packages + count))
    done
    
    if [[ "$total_packages" -eq 0 ]]; then
        die "No packages found to process"
    fi
    
    log_info "Processing $total_packages package(s) with tier: $tier"
    log_info "Timeout: ${TIMEOUT}s, Parallel: $([[ "$PARALLEL" == "1" ]] && echo "enabled" || echo "disabled"), Fail-fast: $([[ "$FAIL_FAST" == "1" ]] && echo "enabled" || echo "disabled")"
    echo
    
    # Process each package type
    for pkg_type in $(jq -r 'keys[]' "$packages_file"); do
        local packages
        packages=$(jq -c ".[\"$pkg_type\"][]" "$packages_file")
        
        for package in $packages; do
            ((processed_packages++))
            
            local pkg_name
            pkg_name=$(echo "$package" | jq -r '.name')
            
            log_info "=== Package $processed_packages/$total_packages: $pkg_name ==="
            
            if ! process_package "$package" "$tier"; then
                failed_packages+=("$pkg_name")
                
                if [[ "$FAIL_FAST" == "1" ]]; then
                    die "Stopping due to failure in package: $pkg_name"
                fi
            fi
            
            echo
        done
    done
    
    # Report results
    if [[ ${#failed_packages[@]} -gt 0 ]]; then
        log_error "Quality gates failed for ${#failed_packages[@]} package(s): ${failed_packages[*]}"
        return 1
    else
        log_success "All quality gates passed for $processed_packages package(s)"
        return 0
    fi
}

# Main execution
main() {
    # Parse arguments
    parse_args "$(basename "$0")" "$@"
    parse_script_args "$@"
    
    # Show header
    show_header "Quality Gates" "Local tier-based quality validation"
    
    # Validate environment
    validate_environment
    
    # Show configuration
    if [[ "$VERBOSE" == "1" ]]; then
        log_info "Configuration:"
        log_info "  Tier: $TIER"
        log_info "  Package Path: $PACKAGE_PATH"
        log_info "  Timeout: ${TIMEOUT}s"
        log_info "  Parallel: $([[ "$PARALLEL" == "1" ]] && echo "enabled" || echo "disabled")"
        log_info "  Fail Fast: $([[ "$FAIL_FAST" == "1" ]] && echo "enabled" || echo "disabled")"
        log_info "  Dry Run: $([[ "$DRY_RUN" == "1" ]] && echo "enabled" || echo "disabled")"
        echo
    fi
    
    # Detect packages
    local packages_file
    packages_file=$(detect_packages)
    
    # Ensure cleanup
    trap "cleanup_temp_dir $(dirname "$packages_file")" EXIT
    
    # Process packages
    local start_time
    start_time=$(date +%s)
    
    if process_packages "$packages_file" "$TIER"; then
        local duration=$(($(date +%s) - start_time))
        log_success "Local quality gates completed successfully in ${duration}s"
        exit 0
    else
        local duration=$(($(date +%s) - start_time))
        log_error "Local quality gates failed after ${duration}s"
        exit 1
    fi
}

# Handle interrupts
trap 'log_error "Interrupted by user"; exit 130' INT TERM

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi