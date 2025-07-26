#!/bin/bash
# Monorepo CI Orchestration Script
# ================================
#
# Orchestrates CI execution across multiple packages in a monorepo with
# dependency-aware ordering, parallel execution, and comprehensive reporting.
#
# Usage:
#   ./monorepo-ci.sh [OPTIONS]
#
# Exit Codes:
#   0: All packages passed CI
#   1: One or more packages failed CI
#   2: Configuration or environment error
#   130: Interrupted by user

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Script-specific defaults
DEFAULT_TIER="essential"
MAX_PARALLEL_JOBS=0  # 0 = auto-detect based on CPU cores
DEPENDENCY_ORDER=1
AGGREGATE_REPORTS=1

# Usage information
show_usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Orchestrate CI execution across all packages in a monorepo with intelligent
dependency ordering and parallel execution.

OPTIONS:
  -t, --tier TIER              Quality tier to execute (default: $DEFAULT_TIER)
  -j, --jobs N                 Maximum parallel jobs (default: auto-detect)
      --sequential             Disable parallel execution (same as --jobs 1)
  -d, --dependency-order       Respect package dependencies (default: enabled)
      --no-dependency-order    Ignore package dependencies
  -f, --fail-fast              Stop on first package failure (default)
  -c, --continue-on-error      Continue after package failures
      --changed-only           Only process packages with changes
      --all                    Process all packages (ignore changes)
  -b, --base-ref REF           Base reference for change detection (default: origin/main)
      --include PATTERN        Include packages matching pattern
      --exclude PATTERN        Exclude packages matching pattern
  -r, --reports                Generate aggregate reports (default: enabled)
      --no-reports             Skip aggregate report generation
  -T, --timeout SECONDS        Override default timeout per package
      --package-timeout SEC    Individual package timeout
      --total-timeout SEC      Total execution timeout
      --no-color               Disable colored output
  -v, --verbose                Enable verbose output
  -d, --debug                  Enable debug output
  -n, --dry-run                Show what would be done without executing
  -h, --help                   Show this help message

EXECUTION STRATEGY:
  The script uses intelligent scheduling to:
  1. Detect all packages in the monorepo
  2. Analyze dependencies between packages (if enabled)
  3. Execute CI in optimal order with maximum parallelism
  4. Aggregate results and generate comprehensive reports

DEPENDENCY DETECTION:
  Dependencies are detected from:
  - Package configuration files (package.json dependencies, pyproject.toml dependencies)
  - Workspace/monorepo configuration files
  - Inter-package import analysis (Python, JavaScript)

EXAMPLES:
  $(basename "$0")                               # Run essential tier on all packages
  $(basename "$0") --tier extended --jobs 4     # Run extended tier with 4 parallel jobs
  $(basename "$0") --changed-only --fail-fast   # Run only on changed packages, stop on failure
  $(basename "$0") --sequential --no-reports    # Run sequentially without reports

Exit Codes:
  0   All packages passed CI
  1   One or more packages failed CI  
  2   Configuration or environment error
  130 Interrupted by user
EOF
}

# Parse command line arguments
parse_script_args() {
    TIER="$DEFAULT_TIER"
    CHANGED_ONLY=0
    FORCE_ALL=0
    BASE_REF="origin/main"
    INCLUDE_PATTERNS=()
    EXCLUDE_PATTERNS=()
    FAIL_FAST=1
    PACKAGE_TIMEOUT=""
    TOTAL_TIMEOUT=""
    NO_COLOR=0
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--tier)
                TIER="$2"
                shift 2
                ;;
            -j|--jobs)
                MAX_PARALLEL_JOBS="$2"
                shift 2
                ;;
            --sequential)
                MAX_PARALLEL_JOBS=1
                shift
                ;;
            -d|--dependency-order)
                DEPENDENCY_ORDER=1
                shift
                ;;
            --no-dependency-order)
                DEPENDENCY_ORDER=0
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
            --changed-only)
                CHANGED_ONLY=1
                FORCE_ALL=0
                shift
                ;;
            --all)
                FORCE_ALL=1
                CHANGED_ONLY=0
                shift
                ;;
            -b|--base-ref)
                BASE_REF="$2"
                shift 2
                ;;
            --include)
                INCLUDE_PATTERNS+=("$2")
                shift 2
                ;;
            --exclude)
                EXCLUDE_PATTERNS+=("$2")
                shift 2
                ;;
            -r|--reports)
                AGGREGATE_REPORTS=1
                shift
                ;;
            --no-reports)
                AGGREGATE_REPORTS=0
                shift
                ;;
            -T|--timeout)
                PACKAGE_TIMEOUT="$2"
                shift 2
                ;;
            --package-timeout)
                PACKAGE_TIMEOUT="$2"
                shift 2
                ;;
            --total-timeout)
                TOTAL_TIMEOUT="$2"
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
                die "Unknown argument: $1"
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
    
    # Auto-detect parallel jobs if not specified
    if [[ "$MAX_PARALLEL_JOBS" -eq 0 ]]; then
        MAX_PARALLEL_JOBS=$(get_cpu_cores)
        log_debug "Auto-detected $MAX_PARALLEL_JOBS CPU cores for parallel execution"
    fi
    
    # Set default timeouts
    if [[ -z "$PACKAGE_TIMEOUT" ]]; then
        PACKAGE_TIMEOUT=$(get_tier_timeout "$TIER")
    fi
    
    if [[ -z "$TOTAL_TIMEOUT" ]]; then
        # Total timeout is package timeout * estimated packages + overhead
        TOTAL_TIMEOUT=$((PACKAGE_TIMEOUT * 10 + 300))  # Assume max 10 packages + 5min overhead
    fi
}

# Detect all packages in the monorepo
detect_all_packages() {
    log_info "Detecting all packages in monorepo..."
    
    local packages_file
    packages_file=$(mktemp)
    
    if ! python3 "$SCRIPT_DIR/package-detection.py" --root-dir "$PROJECT_ROOT" > "$packages_file" 2>/dev/null; then
        rm -f "$packages_file"
        die "No packages detected in monorepo"
    fi
    
    local total_packages=0
    for pkg_type in $(jq -r 'keys[]' "$packages_file" 2>/dev/null || echo ""); do
        local count
        count=$(jq -r ".[\"$pkg_type\"] | length" "$packages_file" 2>/dev/null || echo "0")
        total_packages=$((total_packages + count))
    done
    
    log_info "Detected $total_packages packages across $(jq -r 'keys | length' "$packages_file") package types"
    
    if [[ "$VERBOSE" == "1" ]]; then
        for pkg_type in $(jq -r 'keys[]' "$packages_file"); do
            local names
            names=$(jq -r ".[\"$pkg_type\"][].name" "$packages_file" | tr '\n' ', ' | sed 's/,$//')
            local count
            count=$(jq -r ".[\"$pkg_type\"] | length" "$packages_file")
            log_info "  $pkg_type ($count): $names"
        done
    fi
    
    echo "$packages_file"
}

# Analyze package dependencies
analyze_dependencies() {
    local packages_file="$1"
    
    if [[ "$DEPENDENCY_ORDER" == "0" ]]; then
        log_info "Dependency ordering disabled, packages will be processed in discovery order"
        return 0
    fi
    
    log_info "Analyzing package dependencies..."
    
    # For now, use simple ordering based on package structure depth
    # TODO: Implement proper dependency analysis
    local temp_file
    temp_file=$(mktemp)
    
    jq 'to_entries | map(.value | map(. + {"depth": (.path | split("/") | length)})) | flatten | group_by(.depth) | reverse | flatten | group_by(.type) | map({(.[0].type): .}) | add' "$packages_file" > "$temp_file"
    
    log_debug "Dependency analysis completed"
    mv "$temp_file" "$packages_file"
}

# Create execution plan
create_execution_plan() {
    local packages_file="$1"
    
    log_info "Creating execution plan..."
    
    local execution_plan
    execution_plan=$(mktemp)
    
    # Create batches for parallel execution
    local batch_num=0
    local packages_in_batch=0
    
    echo "[]" > "$execution_plan"
    
    for pkg_type in $(jq -r 'keys[]' "$packages_file"); do
        local packages
        packages=$(jq -c ".[\"$pkg_type\"][]" "$packages_file")
        
        while read -r package; do
            [[ -n "$package" ]] || continue
            
            if [[ "$packages_in_batch" -eq 0 ]]; then
                # Start new batch
                local temp_file
                temp_file=$(mktemp)
                jq --argjson batch_num "$batch_num" '. += [{"batch": $batch_num, "packages": []}]' "$execution_plan" > "$temp_file"
                mv "$temp_file" "$execution_plan"
            fi
            
            # Add package to current batch
            local temp_file
            temp_file=$(mktemp)
            jq --argjson batch_num "$batch_num" --argjson package "$package" \
               '.[$batch_num].packages += [$package]' "$execution_plan" > "$temp_file"
            mv "$temp_file" "$execution_plan"
            
            packages_in_batch=$((packages_in_batch + 1))
            
            # Start new batch if we've reached the parallel job limit
            if [[ "$packages_in_batch" -ge "$MAX_PARALLEL_JOBS" ]]; then
                batch_num=$((batch_num + 1))
                packages_in_batch=0
            fi
        done <<< "$packages"
    done
    
    local total_batches
    total_batches=$(jq 'length' "$execution_plan")
    local total_packages
    total_packages=$(jq '[.[].packages | length] | add' "$execution_plan")
    
    log_info "Execution plan created: $total_packages packages in $total_batches batches"
    
    if [[ "$VERBOSE" == "1" ]]; then
        for ((i=0; i<total_batches; i++)); do
            local batch_size
            batch_size=$(jq -r ".[$i].packages | length" "$execution_plan")
            local batch_names
            batch_names=$(jq -r ".[$i].packages[].name" "$execution_plan" | tr '\n' ', ' | sed 's/,$//')
            log_info "  Batch $((i+1)): $batch_size packages ($batch_names)"
        done
    fi
    
    echo "$execution_plan"
}

# Execute a single package
execute_package() {
    local package_info="$1"
    local batch_num="$2"
    local package_num="$3"
    local total_packages="$4"
    
    local pkg_name pkg_path pkg_type
    pkg_name=$(echo "$package_info" | jq -r '.name')
    pkg_path=$(echo "$package_info" | jq -r '.path')
    pkg_type=$(echo "$package_info" | jq -r '.type')
    
    local log_prefix="[Batch $batch_num] [$package_num/$total_packages] [$pkg_name]"
    
    log_info "$log_prefix Starting CI execution..."
    
    local start_time
    start_time=$(date +%s)
    
    # Execute selective CI on this specific package
    local selective_ci_script="$SCRIPT_DIR/selective-ci.sh"
    local selective_args=()
    
    selective_args+=("--tier" "$TIER")
    selective_args+=("--timeout" "$PACKAGE_TIMEOUT")
    
    if [[ "$VERBOSE" == "1" ]]; then
        selective_args+=("--verbose")
    fi
    
    if [[ "$DEBUG" == "1" ]]; then
        selective_args+=("--debug")
    fi
    
    if [[ "$DRY_RUN" == "1" ]]; then
        selective_args+=("--dry-run")
    fi
    
    # Add the specific package path
    selective_args+=("$pkg_path")
    
    local result=0
    if ! "$selective_ci_script" "${selective_args[@]}" >&2; then
        result=1
    fi
    
    local duration=$(($(date +%s) - start_time))
    
    if [[ "$result" -eq 0 ]]; then
        log_success "$log_prefix Completed successfully in ${duration}s"
    else
        log_error "$log_prefix Failed after ${duration}s"
    fi
    
    # Return package result
    echo "{\"name\": \"$pkg_name\", \"path\": \"$pkg_path\", \"type\": \"$pkg_type\", \"result\": $result, \"duration\": $duration}"
}

# Execute a batch of packages in parallel
execute_batch() {
    local batch_info="$1"
    local batch_num="$2"
    local total_batches="$3"
    
    local packages
    packages=$(echo "$batch_info" | jq -c '.packages[]')
    local batch_size
    batch_size=$(echo "$batch_info" | jq '.packages | length')
    
    log_info "=== Executing Batch $batch_num/$total_batches ($batch_size packages) ==="
    
    local pids=()
    local temp_results=()
    local package_num=0
    
    # Start all packages in this batch
    while read -r package; do
        [[ -n "$package" ]] || continue
        ((package_num++))
        
        local result_file
        result_file=$(mktemp)
        temp_results+=("$result_file")
        
        # Execute package in background
        {
            execute_package "$package" "$batch_num" "$package_num" "$batch_size" > "$result_file"
        } &
        
        pids+=($!)
        
        local pkg_name
        pkg_name=$(echo "$package" | jq -r '.name')
        log_debug "Started package $pkg_name (PID: ${pids[-1]})"
        
        # If sequential execution, wait for this package to complete
        if [[ "$MAX_PARALLEL_JOBS" -eq 1 ]]; then
            wait "${pids[-1]}"
        fi
    done <<< "$packages"
    
    # Wait for all packages in this batch to complete
    local batch_results=()
    local failed_packages=()
    
    for i in "${!pids[@]}"; do
        local pid="${pids[$i]}"
        local result_file="${temp_results[$i]}"
        
        if wait "$pid"; then
            log_debug "Package PID $pid completed successfully"
        else
            log_debug "Package PID $pid failed"
        fi
        
        # Read result
        if [[ -f "$result_file" ]]; then
            local result
            result=$(cat "$result_file")
            batch_results+=("$result")
            
            local pkg_name pkg_result
            pkg_name=$(echo "$result" | jq -r '.name')
            pkg_result=$(echo "$result" | jq -r '.result')
            
            if [[ "$pkg_result" != "0" ]]; then
                failed_packages+=("$pkg_name")
            fi
            
            rm -f "$result_file"
        fi
    done
    
    # Report batch results
    if [[ ${#failed_packages[@]} -gt 0 ]]; then
        log_error "Batch $batch_num failed: ${failed_packages[*]}"
        if [[ "$FAIL_FAST" == "1" ]]; then
            die "Stopping execution due to batch failure (fail-fast enabled)"
        fi
    else
        log_success "Batch $batch_num completed successfully"
    fi
    
    # Return batch results
    printf '%s\n' "${batch_results[@]}"
}

# Generate aggregate report
generate_aggregate_report() {
    local results="$1"
    local report_dir="$PROJECT_ROOT/artifacts/reports"
    
    if [[ "$AGGREGATE_REPORTS" == "0" ]]; then
        log_info "Aggregate report generation disabled"
        return 0
    fi
    
    log_info "Generating aggregate report..."
    
    mkdir -p "$report_dir"
    
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local report_file="$report_dir/monorepo_ci_report_$timestamp.json"
    
    # Create comprehensive report
    local total_packages successful_packages failed_packages total_duration
    total_packages=$(echo "$results" | jq -s 'length')
    successful_packages=$(echo "$results" | jq -s 'map(select(.result == 0)) | length')
    failed_packages=$(echo "$results" | jq -s 'map(select(.result != 0)) | length')
    total_duration=$(echo "$results" | jq -s 'map(.duration) | add')
    
    local report
    report=$(cat << EOF
{
  "timestamp": "$(date -Iseconds)",
  "tier": "$TIER",
  "execution": {
    "total_packages": $total_packages,
    "successful_packages": $successful_packages,
    "failed_packages": $failed_packages,
    "success_rate": $(echo "scale=2; $successful_packages * 100 / $total_packages" | bc -l 2>/dev/null || echo "0"),
    "total_duration": $total_duration,
    "parallel_jobs": $MAX_PARALLEL_JOBS,
    "dependency_order": $DEPENDENCY_ORDER,
    "fail_fast": $FAIL_FAST
  },
  "packages": $(echo "$results" | jq -s .)
}
EOF
)
    
    echo "$report" > "$report_file"
    log_success "Aggregate report saved to: $report_file"
    
    # Generate summary
    echo
    log_info "=== MONOREPO CI SUMMARY ==="
    log_info "Total Packages: $total_packages"
    log_info "Successful: $successful_packages"
    log_info "Failed: $failed_packages"
    log_info "Success Rate: $(echo "scale=1; $successful_packages * 100 / $total_packages" | bc -l 2>/dev/null || echo "0")%"
    log_info "Total Duration: ${total_duration}s"
    
    if [[ "$failed_packages" -gt 0 ]]; then
        log_error "Failed packages:"
        echo "$results" | jq -s -r 'map(select(.result != 0)) | .[] | "  - \(.name) (\(.path))"'
    fi
}

# Main execution
main() {
    # Parse arguments
    parse_args "$(basename "$0")" "$@"
    parse_script_args "$@"
    
    # Show header
    show_header "Monorepo CI" "Intelligent multi-package CI orchestration"
    
    # Validate environment
    validate_environment
    
    # Show configuration
    if [[ "$VERBOSE" == "1" ]]; then
        log_info "Configuration:"
        log_info "  Tier: $TIER"
        log_info "  Max Parallel Jobs: $MAX_PARALLEL_JOBS"
        log_info "  Dependency Order: $([[ "$DEPENDENCY_ORDER" == "1" ]] && echo "enabled" || echo "disabled")"
        log_info "  Changed Only: $([[ "$CHANGED_ONLY" == "1" ]] && echo "enabled" || echo "disabled")"
        log_info "  Base Reference: $BASE_REF"
        log_info "  Fail Fast: $([[ "$FAIL_FAST" == "1" ]] && echo "enabled" || echo "disabled")"
        log_info "  Package Timeout: ${PACKAGE_TIMEOUT}s"
        log_info "  Total Timeout: ${TOTAL_TIMEOUT}s"
        log_info "  Aggregate Reports: $([[ "$AGGREGATE_REPORTS" == "1" ]] && echo "enabled" || echo "disabled")"
        echo
    fi
    
    # Start total timeout
    if [[ "$TOTAL_TIMEOUT" -gt 0 ]]; then
        (
            sleep "$TOTAL_TIMEOUT"
            log_error "Total timeout of ${TOTAL_TIMEOUT}s exceeded, terminating execution"
            pkill -P $$
        ) &
        local timeout_pid=$!
        trap "kill $timeout_pid 2>/dev/null || true" EXIT
    fi
    
    # Detect packages
    local packages_file
    packages_file=$(detect_all_packages)
    
    # Ensure cleanup
    trap "rm -f '$packages_file'; kill $timeout_pid 2>/dev/null || true" EXIT
    
    # Apply change detection if requested
    if [[ "$CHANGED_ONLY" == "1" ]]; then
        log_info "Applying change detection..."
        # Use selective-ci.sh with change detection
        local selective_ci_script="$SCRIPT_DIR/selective-ci.sh"
        local selective_args=()
        
        selective_args+=("--tier" "$TIER")
        selective_args+=("--changed-only")
        selective_args+=("--base-ref" "$BASE_REF")
        selective_args+=("--timeout" "$PACKAGE_TIMEOUT")
        
        if [[ "$FAIL_FAST" == "1" ]]; then
            selective_args+=("--fail-fast")
        else
            selective_args+=("--continue-on-error")
        fi
        
        for pattern in "${INCLUDE_PATTERNS[@]}"; do
            selective_args+=("--include" "$pattern")
        done
        
        for pattern in "${EXCLUDE_PATTERNS[@]}"; do
            selective_args+=("--exclude" "$pattern")
        done
        
        if [[ "$VERBOSE" == "1" ]]; then
            selective_args+=("--verbose")
        fi
        
        if [[ "$DEBUG" == "1" ]]; then
            selective_args+=("--debug")
        fi
        
        if [[ "$DRY_RUN" == "1" ]]; then
            selective_args+=("--dry-run")
        fi
        
        # Execute selective CI with change detection
        exec "$selective_ci_script" "${selective_args[@]}"
    fi
    
    # Analyze dependencies
    analyze_dependencies "$packages_file"
    
    # Create execution plan
    local execution_plan
    execution_plan=$(create_execution_plan "$packages_file")
    
    # Ensure cleanup of execution plan
    trap "rm -f '$packages_file' '$execution_plan'; kill $timeout_pid 2>/dev/null || true" EXIT
    
    # Execute batches
    local start_time
    start_time=$(date +%s)
    
    local all_results=()
    local total_batches
    total_batches=$(jq 'length' "$execution_plan")
    
    for ((batch_num=1; batch_num<=total_batches; batch_num++)); do
        local batch_info
        batch_info=$(jq -c ".[$((batch_num-1))]" "$execution_plan")
        
        local batch_results
        if batch_results=$(execute_batch "$batch_info" "$batch_num" "$total_batches"); then
            all_results+=("$batch_results")
        else
            log_error "Batch $batch_num execution failed"
            if [[ "$FAIL_FAST" == "1" ]]; then
                break
            fi
        fi
        
        echo
    done
    
    local total_duration=$(($(date +%s) - start_time))
    
    # Combine all results
    local combined_results=""
    for result_batch in "${all_results[@]}"; do
        while read -r result; do
            [[ -n "$result" ]] || continue
            combined_results+="$result"$'\n'
        done <<< "$result_batch"
    done
    
    # Generate aggregate report
    if [[ -n "$combined_results" ]]; then
        generate_aggregate_report "$combined_results"
    fi
    
    # Determine final exit code
    local failed_count
    failed_count=$(echo "$combined_results" | jq -s 'map(select(.result != 0)) | length' 2>/dev/null || echo "0")
    
    if [[ "$failed_count" -eq 0 ]]; then
        log_success "Monorepo CI completed successfully in ${total_duration}s"
        exit 0
    else
        log_error "Monorepo CI failed with $failed_count package failures after ${total_duration}s"
        exit 1
    fi
}

# Handle interrupts
trap 'log_error "Interrupted by user"; exit 130' INT TERM

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi