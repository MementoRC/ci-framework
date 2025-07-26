#!/bin/bash
# Common utilities for Local CI Scripts
# ====================================
# 
# Shared functions and utilities used across all local CI scripts.
# Source this file in other scripts: source "$(dirname "$0")/common.sh"

set -euo pipefail

# Script metadata
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOCAL_CI_VERSION="1.0.0"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_debug() {
    if [[ "${DEBUG:-0}" == "1" ]]; then
        echo -e "${PURPLE}[DEBUG]${NC} $*" >&2
    fi
}

# Progress reporting
log_step() {
    local step_num="$1"
    local total_steps="$2"
    local description="$3"
    echo -e "${CYAN}[Step $step_num/$total_steps]${NC} $description" >&2
}

# Error handling
die() {
    log_error "$*"
    exit 1
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if we're in a Git repository
is_git_repo() {
    git rev-parse --git-dir >/dev/null 2>&1
}

# Get the project root directory (Git root or current directory)
get_project_root() {
    if is_git_repo; then
        git rev-parse --show-toplevel
    else
        pwd
    fi
}

# Detect package manager in current directory
detect_package_manager() {
    local dir="${1:-$PWD}"
    
    if [[ -f "$dir/pyproject.toml" ]]; then
        # Check for pixi first, then poetry
        if grep -q "\[tool\.pixi\]" "$dir/pyproject.toml" 2>/dev/null; then
            echo "pixi"
        elif grep -q "\[tool\.poetry\]" "$dir/pyproject.toml" 2>/dev/null; then
            echo "poetry"
        else
            echo "pip"
        fi
    elif [[ -f "$dir/package.json" ]]; then
        echo "npm"
    elif [[ -f "$dir/requirements.txt" ]] || [[ -f "$dir/setup.py" ]] || [[ -f "$dir/setup.cfg" ]]; then
        echo "pip"
    else
        echo "unknown"
    fi
}

# Get package manager commands
get_package_manager_commands() {
    local pkg_manager="$1"
    local tier="${2:-essential}"
    
    case "$pkg_manager" in
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
                *)
                    echo "quality"
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
                *)
                    echo "pytest"
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
                *)
                    echo "test"
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
                *)
                    echo "pytest"
                    ;;
            esac
            ;;
        *)
            die "Unsupported package manager: $pkg_manager"
            ;;
    esac
}

# Execute command with package manager
execute_package_command() {
    local pkg_manager="$1"
    local command="$2"
    local directory="${3:-$PWD}"
    
    log_debug "Executing '$command' with $pkg_manager in $directory"
    
    case "$pkg_manager" in
        pixi)
            (cd "$directory" && pixi run "$command")
            ;;
        poetry)
            (cd "$directory" && poetry run "$command")
            ;;
        npm)
            (cd "$directory" && npm run "$command")
            ;;
        pip)
            (cd "$directory" && python -m "$command")
            ;;
        *)
            die "Unsupported package manager: $pkg_manager"
            ;;
    esac
}

# Check if package manager is available
check_package_manager() {
    local pkg_manager="$1"
    
    case "$pkg_manager" in
        pixi)
            if ! command_exists pixi; then
                die "pixi is not installed. Please install pixi first."
            fi
            ;;
        poetry)
            if ! command_exists poetry; then
                die "poetry is not installed. Please install poetry first."
            fi
            ;;
        npm)
            if ! command_exists npm; then
                die "npm is not installed. Please install Node.js and npm first."
            fi
            ;;
        pip)
            if ! command_exists python; then
                die "python is not installed. Please install Python first."
            fi
            ;;
        *)
            die "Unsupported package manager: $pkg_manager"
            ;;
    esac
}

# Get timeout for tier
get_tier_timeout() {
    local tier="$1"
    
    case "$tier" in
        essential)
            echo "300"  # 5 minutes
            ;;
        extended)
            echo "600"  # 10 minutes
            ;;
        full)
            echo "900"  # 15 minutes
            ;;
        *)
            echo "300"  # Default 5 minutes
            ;;
    esac
}

# Run command with timeout
run_with_timeout() {
    local timeout_seconds="$1"
    shift
    
    if command_exists timeout; then
        timeout "$timeout_seconds" "$@"
    else
        # Fallback for systems without timeout command
        log_warning "timeout command not available, running without timeout"
        "$@"
    fi
}

# Check if running in CI environment
is_ci_environment() {
    [[ "${CI:-false}" == "true" ]] || [[ -n "${GITHUB_ACTIONS:-}" ]] || [[ -n "${JENKINS_URL:-}" ]]
}

# Get number of CPU cores for parallel execution
get_cpu_cores() {
    if command_exists nproc; then
        nproc
    elif [[ -f /proc/cpuinfo ]]; then
        grep -c ^processor /proc/cpuinfo
    elif command_exists sysctl; then
        sysctl -n hw.ncpu 2>/dev/null || echo "1"
    else
        echo "1"
    fi
}

# Create temporary directory
create_temp_dir() {
    local prefix="${1:-local-ci}"
    mktemp -d -t "${prefix}.XXXXXX"
}

# Cleanup function
cleanup_temp_dir() {
    local temp_dir="$1"
    if [[ -n "$temp_dir" ]] && [[ -d "$temp_dir" ]]; then
        rm -rf "$temp_dir"
        log_debug "Cleaned up temporary directory: $temp_dir"
    fi
}

# Parse command line arguments with support for common patterns
parse_args() {
    local script_name="$1"
    shift
    
    # Initialize default values
    VERBOSE=0
    DEBUG=0
    DRY_RUN=0
    HELP=0
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--verbose)
                VERBOSE=1
                shift
                ;;
            -d|--debug)
                DEBUG=1
                VERBOSE=1
                shift
                ;;
            -n|--dry-run)
                DRY_RUN=1
                shift
                ;;
            -h|--help)
                HELP=1
                shift
                ;;
            --)
                shift
                break
                ;;
            -*)
                die "Unknown option: $1"
                ;;
            *)
                break
                ;;
        esac
    done
    
    # Export for use in other functions
    export VERBOSE DEBUG DRY_RUN
    
    if [[ "$HELP" == "1" ]]; then
        show_usage "$script_name"
        exit 0
    fi
}

# Show usage information (to be overridden by calling script)
show_usage() {
    local script_name="$1"
    cat << EOF
Usage: $script_name [OPTIONS]

Common Options:
  -v, --verbose     Enable verbose output
  -d, --debug       Enable debug output
  -n, --dry-run     Show what would be done without executing
  -h, --help        Show this help message

Local CI Scripts v${LOCAL_CI_VERSION}
EOF
}

# Validate environment
validate_environment() {
    log_debug "Validating environment..."
    
    # Check basic requirements
    if ! command_exists python3 && ! command_exists python; then
        die "Python is required but not found"
    fi
    
    # Check if we can run package detection
    local package_detection_script="$SCRIPT_DIR/package-detection.py"
    if [[ ! -f "$package_detection_script" ]]; then
        die "Package detection script not found: $package_detection_script"
    fi
    
    if [[ ! -x "$package_detection_script" ]]; then
        die "Package detection script is not executable: $package_detection_script"
    fi
    
    log_debug "Environment validation passed"
}

# Show script header
show_header() {
    local script_name="$1"
    local description="$2"
    
    echo -e "${CYAN}================================${NC}"
    echo -e "${CYAN}Local CI: $script_name${NC}"
    echo -e "${CYAN}$description${NC}"
    echo -e "${CYAN}Version: $LOCAL_CI_VERSION${NC}"
    echo -e "${CYAN}================================${NC}"
    echo
}

# Export all functions for use in other scripts
export -f log_info log_success log_warning log_error log_debug log_step
export -f die command_exists is_git_repo get_project_root
export -f detect_package_manager get_package_manager_commands execute_package_command
export -f check_package_manager get_tier_timeout run_with_timeout
export -f is_ci_environment get_cpu_cores create_temp_dir cleanup_temp_dir
export -f parse_args show_usage validate_environment show_header

# Export variables
export SCRIPT_DIR PROJECT_ROOT LOCAL_CI_VERSION
export RED GREEN YELLOW BLUE PURPLE CYAN NC