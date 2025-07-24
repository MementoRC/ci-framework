#!/bin/bash
# Selective CI Script
# ===================
#
# Runs CI selectively on changed packages in a monorepo or specific packages.
# Uses package detection to identify targets and change detection to optimize execution.
#
# Usage:
#   ./selective-ci.sh [OPTIONS] [PACKAGES...]
#
# Exit Codes:
#   0: All targeted packages passed CI
#   1: CI failures detected
#   2: Configuration or environment error
#   130: Interrupted by user

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Script-specific defaults
DEFAULT_TIER="essential"
CHANGE_DETECTION=1
FORCE_ALL=0
BASE_REF="origin/main"

# Usage information
show_usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS] [PACKAGES...]

Run CI selectively on specific packages or changed packages in a monorepo.

ARGUMENTS:
  PACKAGES...           Specific package directories to process
                       If not specified, uses change detection

OPTIONS:
  -t, --tier TIER           Quality tier to execute (default: $DEFAULT_TIER)
  -b, --base-ref REF        Base reference for change detection (default: $BASE_REF)
  -a, --all                 Force run on all packages (disable change detection)
  -c, --changed-only        Only run on changed packages (enable change detection)
      --include PATTERN     Include packages matching pattern
      --exclude PATTERN     Exclude packages matching pattern  
  -j, --parallel            Enable parallel package processing
  -s, --sequential          Disable parallel package processing
  -f, --fail-fast           Stop on first package failure
      --continue-on-error   Continue processing after package failures
  -T, --timeout SECONDS     Override default timeout per package
      --no-color            Disable colored output
  -v, --verbose             Enable verbose output
  -d, --debug               Enable debug output
  -n, --dry-run             Show what would be done without executing
  -h, --help                Show this help message

EXAMPLES:
  $(basename "$0")                           # Run on changed packages
  $(basename "$0") src/api src/web           # Run on specific packages
  $(basename "$0") --all extended            # Run extended tier on all packages
  $(basename "$0") --changed-only --tier full  # Run full tier on changed packages only
  $(basename "$0") --include "src/*" --exclude "*/tests"  # Pattern-based selection

CHANGE DETECTION:
  By default, the script detects changed packages by comparing against the base
  reference ($BASE_REF). This can be overridden with --base-ref or disabled
  with --all to force processing of all packages.

Exit Codes:
  0   All targeted packages passed CI
  1   CI failures detected
  2   Configuration or environment error
  130 Interrupted by user
EOF
}

# Parse command line arguments
parse_script_args() {
    TIER="$DEFAULT_TIER"
    TARGET_PACKAGES=()
    INCLUDE_PATTERNS=()
    EXCLUDE_PATTERNS=()
    PARALLEL=1
    FAIL_FAST=1
    TIMEOUT=""
    NO_COLOR=0
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--tier)
                TIER="$2"
                shift 2
                ;;
            -b|--base-ref)
                BASE_REF="$2"
                shift 2
                ;;
            -a|--all)
                FORCE_ALL=1
                CHANGE_DETECTION=0
                shift
                ;;
            -c|--changed-only)
                FORCE_ALL=0
                CHANGE_DETECTION=1
                shift
                ;;
            --include)
                INCLUDE_PATTERNS+=("$2")
                shift 2
                ;;
            --exclude)
                EXCLUDE_PATTERNS+=("$2")
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
            --continue-on-error)
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
                # Assume it's a package directory
                TARGET_PACKAGES+=("$1")
                shift
                ;;
        esac
    done
    
    # Add remaining arguments as target packages
    TARGET_PACKAGES+=("$@")
    
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
    
    # If target packages specified, disable change detection by default
    if [[ ${#TARGET_PACKAGES[@]} -gt 0 ]] && [[ "$FORCE_ALL" == "0" ]]; then
        CHANGE_DETECTION=0
    fi
}

# Detect changed files since base reference
detect_changed_files() {
    if ! is_git_repo; then
        log_warning "Not in a Git repository, cannot detect changes"
        return 1
    fi
    
    log_info "Detecting changes since $BASE_REF..."
    
    # Ensure we have the latest refs
    if command_exists git && git remote >/dev/null 2>&1; then
        log_debug "Fetching latest changes from remote..."
        git fetch origin >/dev/null 2>&1 || log_warning "Failed to fetch from remote"
    fi
    
    # Check if base ref exists
    if ! git rev-parse --verify "$BASE_REF" >/dev/null 2>&1; then
        log_warning "Base reference $BASE_REF not found, using HEAD~1"
        BASE_REF="HEAD~1"
        
        if ! git rev-parse --verify "$BASE_REF" >/dev/null 2>&1; then
            log_warning "Cannot determine base reference, running on all packages"
            return 1
        fi
    fi
    
    # Get changed files
    local changed_files
    changed_files=$(git diff --name-only "$BASE_REF" HEAD 2>/dev/null) || {
        log_warning "Failed to get changed files, running on all packages"
        return 1
    }
    
    if [[ -z "$changed_files" ]]; then
        log_info "No changes detected since $BASE_REF"
        return 1
    fi
    
    log_debug "Changed files:"
    echo "$changed_files" | while read -r file; do
        log_debug "  $file"
    done
    
    echo "$changed_files"
}

# Get packages affected by changed files
get_affected_packages() {
    local changed_files="$1"
    local packages_file="$2"
    
    log_info "Determining affected packages..."
    
    # Get all package directories
    local all_package_dirs=()
    for pkg_type in $(jq -r 'keys[]' "$packages_file"); do
        while read -r pkg_path; do
            all_package_dirs+=("$pkg_path")
        done < <(jq -r ".[\"$pkg_type\"][].path" "$packages_file")
    done
    
    # Find packages affected by changes
    local affected_packages=()
    
    while read -r changed_file; do
        [[ -n "$changed_file" ]] || continue
        
        # Find which package directory contains this file
        for pkg_dir in "${all_package_dirs[@]}"; do
            if [[ "$changed_file" == "$pkg_dir"* ]] || [[ "$changed_file" == "./$pkg_dir"* ]]; then
                # Add to affected packages if not already present
                if [[ ! " ${affected_packages[*]} " =~ " ${pkg_dir} " ]]; then
                    affected_packages+=("$pkg_dir")
                    log_debug "Package $pkg_dir affected by $changed_file"
                fi
            fi
        done
        
        # Special case: root-level changes might affect all packages
        if [[ "$changed_file" =~ ^(pyproject\.toml|package\.json|requirements\.txt|\.github/|scripts/|Dockerfile)$ ]]; then
            log_debug "Root-level change detected: $changed_file (may affect all packages)"
        fi
    done <<< "$changed_files"
    
    # Filter packages based on include/exclude patterns
    local filtered_packages=()
    for pkg_dir in "${affected_packages[@]}"; do
        local include=1
        
        # Check exclude patterns
        for pattern in "${EXCLUDE_PATTERNS[@]}"; do
            if [[ "$pkg_dir" == $pattern ]]; then
                include=0
                log_debug "Excluding package $pkg_dir (matches exclude pattern: $pattern)"
                break
            fi
        done
        
        # Check include patterns (if any specified)
        if [[ ${#INCLUDE_PATTERNS[@]} -gt 0 ]] && [[ "$include" == "1" ]]; then
            include=0
            for pattern in "${INCLUDE_PATTERNS[@]}"; do
                if [[ "$pkg_dir" == $pattern ]]; then
                    include=1
                    log_debug "Including package $pkg_dir (matches include pattern: $pattern)"
                    break
                fi
            done
        fi
        
        if [[ "$include" == "1" ]]; then
            filtered_packages+=("$pkg_dir")
        fi
    done
    
    if [[ ${#filtered_packages[@]} -eq 0 ]]; then
        log_info "No packages affected by changes"
        return 1
    fi
    
    log_info "Affected packages: ${filtered_packages[*]}"
    printf '%s\n' "${filtered_packages[@]}"
}

# Filter packages by target list and patterns
filter_packages() {
    local packages_file="$1"
    
    local selected_packages=()
    
    # If specific packages were requested
    if [[ ${#TARGET_PACKAGES[@]} -gt 0 ]]; then
        log_info "Processing specified packages: ${TARGET_PACKAGES[*]}"
        
        for target in "${TARGET_PACKAGES[@]}"; do
            # Convert to absolute path and normalize
            local abs_target
            abs_target="$(cd "$target" 2>/dev/null && pwd)" || {
                log_warning "Package directory not found: $target"
                continue
            }
            
            # Find matching package in detection results
            local found=0
            for pkg_type in $(jq -r 'keys[]' "$packages_file"); do
                while read -r pkg_path pkg_abs_path; do
                    if [[ "$abs_target" == "$pkg_abs_path" ]] || [[ "$target" == "$pkg_path" ]]; then
                        selected_packages+=("$pkg_path")
                        found=1
                        break
                    fi
                done < <(jq -r ".[\"$pkg_type\"][] | .path + \" \" + .absolute_path" "$packages_file")
                
                [[ "$found" == "1" ]] && break
            done
            
            if [[ "$found" == "0" ]]; then
                log_warning "No package configuration found in: $target"
            fi
        done
    else
        # Use all detected packages
        for pkg_type in $(jq -r 'keys[]' "$packages_file"); do
            while read -r pkg_path; do
                selected_packages+=("$pkg_path")
            done < <(jq -r ".[\"$pkg_type\"][].path" "$packages_file")
        done
    fi
    
    # Apply include/exclude patterns
    local filtered_packages=()
    for pkg_path in "${selected_packages[@]}"; do
        local include=1
        
        # Check exclude patterns
        for pattern in "${EXCLUDE_PATTERNS[@]}"; do
            if [[ "$pkg_path" == $pattern ]]; then
                include=0
                log_debug "Excluding package $pkg_path (matches exclude pattern: $pattern)"
                break
            fi
        done
        
        # Check include patterns (if any specified)
        if [[ ${#INCLUDE_PATTERNS[@]} -gt 0 ]] && [[ "$include" == "1" ]]; then
            include=0
            for pattern in "${INCLUDE_PATTERNS[@]}"; do
                if [[ "$pkg_path" == $pattern ]]; then
                    include=1
                    log_debug "Including package $pkg_path (matches include pattern: $pattern)"
                    break
                fi
            done
        fi
        
        if [[ "$include" == "1" ]]; then
            filtered_packages+=("$pkg_path")
        fi
    done
    
    if [[ ${#filtered_packages[@]} -eq 0 ]]; then
        log_info "No packages selected after filtering"
        return 1
    fi
    
    printf '%s\n' "${filtered_packages[@]}"
}

# Create filtered packages file
create_filtered_packages_file() {
    local original_file="$1"
    local target_paths="$2"
    
    local filtered_file
    filtered_file=$(mktemp)
    
    # Start with empty structure
    echo '{}' > "$filtered_file"
    
    # Add packages that match target paths
    while read -r target_path; do
        [[ -n "$target_path" ]] || continue
        
        for pkg_type in $(jq -r 'keys[]' "$original_file"); do
            # Find packages in this type that match the target path
            local matching_packages
            matching_packages=$(jq -c ".[\"$pkg_type\"][] | select(.path == \"$target_path\")" "$original_file")
            
            if [[ -n "$matching_packages" ]]; then
                # Add to filtered file
                local temp_file
                temp_file=$(mktemp)
                
                jq --argjson pkg "$matching_packages" \
                   --arg type "$pkg_type" \
                   'if has($type) then .[$type] += [$pkg] else .[$type] = [$pkg] end' \
                   "$filtered_file" > "$temp_file"
                   
                mv "$temp_file" "$filtered_file"
                log_debug "Added $pkg_type package at $target_path to filtered list"
            fi
        done
    done <<< "$target_paths"
    
    echo "$filtered_file"
}

# Main execution
main() {
    # Parse arguments
    parse_args "$(basename "$0")" "$@"
    parse_script_args "$@"
    
    # Show header
    show_header "Selective CI" "Smart package-targeted CI execution"
    
    # Validate environment
    validate_environment
    
    # Show configuration
    if [[ "$VERBOSE" == "1" ]]; then
        log_info "Configuration:"
        log_info "  Tier: $TIER"
        log_info "  Change Detection: $([[ "$CHANGE_DETECTION" == "1" ]] && echo "enabled" || echo "disabled")"
        log_info "  Base Reference: $BASE_REF"
        log_info "  Force All: $([[ "$FORCE_ALL" == "1" ]] && echo "enabled" || echo "disabled")"
        log_info "  Target Packages: ${TARGET_PACKAGES[*]:-"(auto-detect)"}"
        log_info "  Include Patterns: ${INCLUDE_PATTERNS[*]:-"(none)"}"
        log_info "  Exclude Patterns: ${EXCLUDE_PATTERNS[*]:-"(none)"}"
        log_info "  Timeout: ${TIMEOUT}s"
        log_info "  Parallel: $([[ "$PARALLEL" == "1" ]] && echo "enabled" || echo "disabled")"
        log_info "  Fail Fast: $([[ "$FAIL_FAST" == "1" ]] && echo "enabled" || echo "disabled")"
        echo
    fi
    
    # Detect all packages first
    log_info "Detecting packages in project..."
    local all_packages_file
    all_packages_file=$(mktemp)
    
    if ! python3 "$SCRIPT_DIR/package-detection.py" --root-dir "$PROJECT_ROOT" > "$all_packages_file" 2>/dev/null; then
        rm -f "$all_packages_file"
        die "No packages detected in project"
    fi
    
    # Ensure cleanup
    trap "rm -f '$all_packages_file'" EXIT
    
    # Determine target packages
    local target_packages_list
    
    if [[ "$CHANGE_DETECTION" == "1" ]] && [[ ${#TARGET_PACKAGES[@]} -eq 0 ]]; then
        # Use change detection
        local changed_files
        if changed_files=$(detect_changed_files); then
            if target_packages_list=$(get_affected_packages "$changed_files" "$all_packages_file"); then
                log_info "Running CI on changed packages only"
            else
                log_info "No affected packages found, running on all packages"
                target_packages_list=$(filter_packages "$all_packages_file")
            fi
        else
            log_info "Change detection failed, running on all packages"
            target_packages_list=$(filter_packages "$all_packages_file")
        fi
    else
        # Use specified packages or all packages
        target_packages_list=$(filter_packages "$all_packages_file")
    fi
    
    if [[ -z "$target_packages_list" ]]; then
        log_info "No packages to process"
        exit 0
    fi
    
    # Create filtered packages file for processing
    local filtered_packages_file
    filtered_packages_file=$(create_filtered_packages_file "$all_packages_file" "$target_packages_list")
    
    # Ensure cleanup of filtered file
    trap "rm -f '$all_packages_file' '$filtered_packages_file'" EXIT
    
    # Execute quality gates on selected packages
    log_info "Executing $TIER tier quality gates on selected packages..."
    
    if [[ "$DRY_RUN" == "1" ]]; then
        log_info "[DRY RUN] Would execute local-quality-gates.sh with:"
        log_info "  Tier: $TIER"
        log_info "  Timeout: ${TIMEOUT}s"
        log_info "  Packages: $(echo "$target_packages_list" | tr '\n' ' ')"
        exit 0
    fi
    
    # Execute local quality gates script
    local quality_gates_script="$SCRIPT_DIR/local-quality-gates.sh"
    local quality_args=()
    
    quality_args+=("--tier" "$TIER")
    quality_args+=("--timeout" "$TIMEOUT")
    
    if [[ "$PARALLEL" == "1" ]]; then
        quality_args+=("--parallel")
    else
        quality_args+=("--sequential")
    fi
    
    if [[ "$FAIL_FAST" == "1" ]]; then
        quality_args+=("--fail-fast")
    else
        quality_args+=("--continue-on-error")
    fi
    
    if [[ "$VERBOSE" == "1" ]]; then
        quality_args+=("--verbose")
    fi
    
    if [[ "$DEBUG" == "1" ]]; then
        quality_args+=("--debug")
    fi
    
    # Process each target package
    local failed_packages=()
    local processed_packages=0
    local total_packages
    total_packages=$(echo "$target_packages_list" | wc -l)
    
    while read -r package_path; do
        [[ -n "$package_path" ]] || continue
        
        ((processed_packages++))
        
        log_info "=== Processing package $processed_packages/$total_packages: $package_path ==="
        
        if ! "$quality_gates_script" "${quality_args[@]}" --package "$package_path"; then
            failed_packages+=("$package_path")
            
            if [[ "$FAIL_FAST" == "1" ]]; then
                die "Stopping due to failure in package: $package_path"
            fi
        fi
        
        echo
    done <<< "$target_packages_list"
    
    # Report final results
    if [[ ${#failed_packages[@]} -gt 0 ]]; then
        log_error "Selective CI failed for ${#failed_packages[@]} package(s): ${failed_packages[*]}"
        exit 1
    else
        log_success "Selective CI passed for all $processed_packages package(s)"
        exit 0
    fi
}

# Handle interrupts
trap 'log_error "Interrupted by user"; exit 130' INT TERM

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi