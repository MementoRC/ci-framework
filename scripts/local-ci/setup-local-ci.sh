#!/bin/bash
# Local CI Setup Script
# =====================
#
# One-command installation and configuration of local CI scripts.
# Sets up shell aliases, PATH additions, and validates environment.
#
# Usage:
#   ./setup-local-ci.sh [OPTIONS]
#
# Exit Codes:
#   0: Setup completed successfully
#   1: Setup failed
#   2: Environment validation failed

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Setup defaults
INSTALL_ALIASES=1
ADD_TO_PATH=1
VALIDATE_ENVIRONMENT=1
SHELL_CONFIG=""
CREATE_SYMLINKS=0

# Usage information
show_usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

One-command setup for local CI scripts with shell integration.

OPTIONS:
  -a, --aliases                 Install shell aliases (default: enabled)
      --no-aliases              Skip shell alias installation
  -p, --path                    Add to PATH (default: enabled)
      --no-path                 Skip PATH addition
  -s, --shell-config FILE       Specify shell config file (auto-detect if not provided)
  -l, --symlinks                Create symlinks in /usr/local/bin (requires sudo)
      --validate                Validate environment after setup (default: enabled)
      --no-validate             Skip environment validation
  -f, --force                   Overwrite existing configuration
      --uninstall               Remove local CI setup
  -v, --verbose                 Enable verbose output
  -d, --debug                   Enable debug output
  -n, --dry-run                 Show what would be done without executing
  -h, --help                    Show this help message

SHELL INTEGRATION:
  The script will add aliases and PATH entries to your shell configuration:
  
  Aliases added:
    local-ci           = local-quality-gates.sh
    lci                = local-quality-gates.sh  
    selective-ci       = selective-ci.sh
    sci                = selective-ci.sh
    monorepo-ci        = monorepo-ci.sh
    mci                = monorepo-ci.sh
    
  PATH addition:
    $SCRIPT_DIR added to PATH for direct script execution

EXAMPLES:
  $(basename "$0")                           # Full setup with auto-detection
  $(basename "$0") --no-aliases --symlinks  # PATH and symlinks only
  $(basename "$0") --shell-config ~/.zshrc  # Specific shell config
  $(basename "$0") --uninstall              # Remove local CI setup

Exit Codes:
  0   Setup completed successfully
  1   Setup failed
  2   Environment validation failed
EOF
}

# Parse command line arguments
parse_script_args() {
    FORCE=0
    UNINSTALL=0
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -a|--aliases)
                INSTALL_ALIASES=1
                shift
                ;;
            --no-aliases)
                INSTALL_ALIASES=0
                shift
                ;;
            -p|--path)
                ADD_TO_PATH=1
                shift
                ;;
            --no-path)
                ADD_TO_PATH=0
                shift
                ;;
            -s|--shell-config)
                SHELL_CONFIG="$2"
                shift 2
                ;;
            -l|--symlinks)
                CREATE_SYMLINKS=1
                shift
                ;;
            --validate)
                VALIDATE_ENVIRONMENT=1
                shift
                ;;
            --no-validate)
                VALIDATE_ENVIRONMENT=0
                shift
                ;;
            -f|--force)
                FORCE=1
                shift
                ;;
            --uninstall)
                UNINSTALL=1
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
}

# Detect shell configuration file
detect_shell_config() {
    if [[ -n "$SHELL_CONFIG" ]] && [[ -f "$SHELL_CONFIG" ]]; then
        echo "$SHELL_CONFIG"
        return 0
    fi
    
    local shell_name
    shell_name=$(basename "${SHELL:-bash}")
    
    case "$shell_name" in
        bash)
            for config in ~/.bashrc ~/.bash_profile ~/.profile; do
                if [[ -f "$config" ]]; then
                    echo "$config"
                    return 0
                fi
            done
            # Create .bashrc if none exist
            echo "$HOME/.bashrc"
            ;;
        zsh)
            for config in ~/.zshrc ~/.zprofile; do
                if [[ -f "$config" ]]; then
                    echo "$config"
                    return 0
                fi
            done
            # Create .zshrc if none exist
            echo "$HOME/.zshrc"
            ;;
        fish)
            local fish_config="$HOME/.config/fish/config.fish"
            mkdir -p "$(dirname "$fish_config")"
            echo "$fish_config"
            ;;
        *)
            # Default to .profile for unknown shells
            echo "$HOME/.profile"
            ;;
    esac
}

# Check if local CI is already configured
is_already_configured() {
    local config_file="$1"
    
    if [[ ! -f "$config_file" ]]; then
        return 1
    fi
    
    grep -q "# Local CI Setup" "$config_file" 2>/dev/null
}

# Remove existing configuration
remove_configuration() {
    local config_file="$1"
    
    if [[ ! -f "$config_file" ]]; then
        log_info "No configuration found in $config_file"
        return 0
    fi
    
    log_info "Removing Local CI configuration from $config_file..."
    
    # Create backup
    local backup_file="${config_file}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$config_file" "$backup_file"
    log_info "Created backup: $backup_file"
    
    # Remove Local CI configuration block
    sed -i '/# Local CI Setup - Start/,/# Local CI Setup - End/d' "$config_file"
    
    log_success "Configuration removed from $config_file"
}

# Add configuration to shell
add_shell_configuration() {
    local config_file="$1"
    
    if is_already_configured "$config_file" && [[ "$FORCE" == "0" ]]; then
        log_warning "Local CI already configured in $config_file (use --force to overwrite)"
        return 0
    fi
    
    log_info "Adding Local CI configuration to $config_file..."
    
    # Create backup if file exists
    if [[ -f "$config_file" ]]; then
        local backup_file="${config_file}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$config_file" "$backup_file"
        log_debug "Created backup: $backup_file"
    fi
    
    # Remove existing configuration if present
    if is_already_configured "$config_file"; then
        sed -i '/# Local CI Setup - Start/,/# Local CI Setup - End/d' "$config_file"
        log_debug "Removed existing Local CI configuration"
    fi
    
    # Detect shell type for appropriate syntax
    local shell_name
    shell_name=$(basename "${SHELL:-bash}")
    
    # Generate configuration block
    local config_block=""
    
    if [[ "$shell_name" == "fish" ]]; then
        # Fish shell configuration
        config_block="# Local CI Setup - Start
# Added by local CI setup script on $(date)

# Local CI Scripts PATH
set -gx PATH \"$SCRIPT_DIR\" \$PATH
"
        
        if [[ "$INSTALL_ALIASES" == "1" ]]; then
            config_block+="
# Local CI Aliases
alias local-ci='$SCRIPT_DIR/local-quality-gates.sh'
alias lci='$SCRIPT_DIR/local-quality-gates.sh'
alias selective-ci='$SCRIPT_DIR/selective-ci.sh'
alias sci='$SCRIPT_DIR/selective-ci.sh'
alias monorepo-ci='$SCRIPT_DIR/monorepo-ci.sh'
alias mci='$SCRIPT_DIR/monorepo-ci.sh'
"
        fi
        
        config_block+="
# Local CI Setup - End
"
    else
        # Bash/Zsh configuration
        config_block="# Local CI Setup - Start
# Added by local CI setup script on $(date)
"
        
        if [[ "$ADD_TO_PATH" == "1" ]]; then
            config_block+="
# Local CI Scripts PATH
export PATH=\"$SCRIPT_DIR:\$PATH\"
"
        fi
        
        if [[ "$INSTALL_ALIASES" == "1" ]]; then
            config_block+="
# Local CI Aliases
alias local-ci='$SCRIPT_DIR/local-quality-gates.sh'
alias lci='$SCRIPT_DIR/local-quality-gates.sh'
alias selective-ci='$SCRIPT_DIR/selective-ci.sh'
alias sci='$SCRIPT_DIR/selective-ci.sh'
alias monorepo-ci='$SCRIPT_DIR/monorepo-ci.sh'
alias mci='$SCRIPT_DIR/monorepo-ci.sh'
"
        fi
        
        config_block+="
# Local CI Setup - End
"
    fi
    
    # Add configuration to file
    if [[ "$DRY_RUN" == "1" ]]; then
        log_info "[DRY RUN] Would add to $config_file:"
        echo "$config_block"
    else
        echo "$config_block" >> "$config_file"
        log_success "Configuration added to $config_file"
    fi
}

# Create symlinks in system PATH
create_symlinks() {
    if [[ "$CREATE_SYMLINKS" == "0" ]]; then
        return 0
    fi
    
    log_info "Creating symlinks in /usr/local/bin..."
    
    local symlink_dir="/usr/local/bin"
    local scripts=(
        "local-quality-gates.sh:local-ci"
        "selective-ci.sh:selective-ci"
        "monorepo-ci.sh:monorepo-ci"
        "package-detection.py:package-detection"
    )
    
    for script_mapping in "${scripts[@]}"; do
        local script_name="${script_mapping%:*}"
        local symlink_name="${script_mapping#*:}"
        local script_path="$SCRIPT_DIR/$script_name"
        local symlink_path="$symlink_dir/$symlink_name"
        
        if [[ ! -f "$script_path" ]]; then
            log_warning "Script not found: $script_path"
            continue
        fi
        
        if [[ -L "$symlink_path" ]] || [[ -f "$symlink_path" ]]; then
            if [[ "$FORCE" == "1" ]]; then
                log_info "Removing existing symlink: $symlink_path"
                if [[ "$DRY_RUN" == "0" ]]; then
                    sudo rm -f "$symlink_path"
                fi
            else
                log_warning "Symlink already exists: $symlink_path (use --force to overwrite)"
                continue
            fi
        fi
        
        log_info "Creating symlink: $symlink_path -> $script_path"
        if [[ "$DRY_RUN" == "0" ]]; then
            sudo ln -s "$script_path" "$symlink_path"
        fi
    done
    
    log_success "Symlinks created in $symlink_dir"
}

# Remove symlinks
remove_symlinks() {
    log_info "Removing symlinks from /usr/local/bin..."
    
    local symlink_dir="/usr/local/bin"
    local symlinks=(
        "local-ci"
        "selective-ci" 
        "monorepo-ci"
        "package-detection"
    )
    
    for symlink_name in "${symlinks[@]}"; do
        local symlink_path="$symlink_dir/$symlink_name"
        
        if [[ -L "$symlink_path" ]]; then
            local target
            target=$(readlink "$symlink_path")
            
            if [[ "$target" == "$SCRIPT_DIR"* ]]; then
                log_info "Removing symlink: $symlink_path"
                if [[ "$DRY_RUN" == "0" ]]; then
                    sudo rm -f "$symlink_path"
                fi
            else
                log_debug "Skipping symlink (not ours): $symlink_path -> $target"
            fi
        fi
    done
}

# Validate installation
validate_installation() {
    if [[ "$VALIDATE_ENVIRONMENT" == "0" ]]; then
        return 0
    fi
    
    log_info "Validating Local CI installation..."
    
    local validation_errors=()
    
    # Check script permissions
    for script in package-detection.py common.sh local-quality-gates.sh selective-ci.sh monorepo-ci.sh; do
        local script_path="$SCRIPT_DIR/$script"
        if [[ ! -f "$script_path" ]]; then
            validation_errors+=("Script not found: $script_path")
        elif [[ ! -x "$script_path" ]]; then
            validation_errors+=("Script not executable: $script_path")
        fi
    done
    
    # Check Python availability
    if ! command_exists python3; then
        validation_errors+=("python3 not found in PATH")
    fi
    
    # Check jq availability (needed for JSON processing)
    if ! command_exists jq; then
        validation_errors+=("jq not found in PATH (required for package detection)")
    fi
    
    # Test package detection
    local temp_file
    temp_file=$(mktemp)
    
    if python3 "$SCRIPT_DIR/package-detection.py" --root-dir "$PROJECT_ROOT" > "$temp_file" 2>/dev/null; then
        log_debug "Package detection test: PASSED"
    else
        validation_errors+=("Package detection test failed")
    fi
    
    rm -f "$temp_file"
    
    # Report validation results
    if [[ ${#validation_errors[@]} -eq 0 ]]; then
        log_success "Installation validation passed"
        
        # Show usage examples
        echo
        log_info "Local CI is ready! Try these commands:"
        log_info "  local-ci essential           # Run essential quality gates"
        log_info "  selective-ci --changed-only  # Run CI on changed packages only"
        log_info "  monorepo-ci --tier extended  # Run extended tier on all packages"
        log_info "  package-detection --help     # Show package detection options"
        
        return 0
    else
        log_error "Installation validation failed:"
        for error in "${validation_errors[@]}"; do
            log_error "  - $error"
        done
        
        return 2
    fi
}

# Show post-installation instructions
show_post_install() {
    echo
    log_info "=== POST-INSTALLATION INSTRUCTIONS ==="
    
    local config_file
    config_file=$(detect_shell_config)
    
    if [[ "$ADD_TO_PATH" == "1" ]] || [[ "$INSTALL_ALIASES" == "1" ]]; then
        log_info "Shell configuration updated: $config_file"
        log_info "To use Local CI in this session, run:"
        log_info "  source $config_file"
        echo
        log_info "Or restart your terminal to automatically load the configuration."
    fi
    
    if [[ "$CREATE_SYMLINKS" == "1" ]]; then
        log_info "System-wide symlinks created in /usr/local/bin"
        log_info "Local CI commands are now available globally."
    fi
    
    echo
    log_info "Quick Start:"
    log_info "  cd your-project-directory"
    log_info "  local-ci                    # Run essential quality gates"
    log_info "  selective-ci --help         # See selective CI options"
    log_info "  monorepo-ci --help          # See monorepo CI options"
}

# Uninstall local CI
uninstall_local_ci() {
    log_info "Uninstalling Local CI setup..."
    
    # Remove shell configuration
    local config_file
    config_file=$(detect_shell_config)
    remove_configuration "$config_file"
    
    # Remove symlinks
    remove_symlinks
    
    log_success "Local CI setup removed"
    log_info "Shell configuration backed up with .backup suffix"
    log_info "You may need to restart your terminal for changes to take effect"
}

# Main execution
main() {
    # Parse arguments
    parse_args "$(basename "$0")" "$@"
    parse_script_args "$@"
    
    # Show header
    show_header "Local CI Setup" "One-command installation and configuration"
    
    # Handle uninstall
    if [[ "$UNINSTALL" == "1" ]]; then
        uninstall_local_ci
        exit 0
    fi
    
    # Show configuration
    if [[ "$VERBOSE" == "1" ]]; then
        log_info "Setup Configuration:"
        log_info "  Install Aliases: $([[ "$INSTALL_ALIASES" == "1" ]] && echo "enabled" || echo "disabled")"
        log_info "  Add to PATH: $([[ "$ADD_TO_PATH" == "1" ]] && echo "enabled" || echo "disabled")"
        log_info "  Create Symlinks: $([[ "$CREATE_SYMLINKS" == "1" ]] && echo "enabled" || echo "disabled")"
        log_info "  Validate Environment: $([[ "$VALIDATE_ENVIRONMENT" == "1" ]] && echo "enabled" || echo "disabled")"
        log_info "  Force Overwrite: $([[ "$FORCE" == "1" ]] && echo "enabled" || echo "disabled")"
        echo
    fi
    
    # Detect shell configuration
    local config_file
    config_file=$(detect_shell_config)
    log_info "Using shell configuration: $config_file"
    
    # Install shell configuration
    if [[ "$INSTALL_ALIASES" == "1" ]] || [[ "$ADD_TO_PATH" == "1" ]]; then
        add_shell_configuration "$config_file"
    fi
    
    # Create symlinks if requested
    create_symlinks
    
    # Validate installation
    if ! validate_installation; then
        log_error "Installation validation failed"
        exit 2
    fi
    
    # Show post-installation instructions
    if [[ "$DRY_RUN" == "0" ]]; then
        show_post_install
    fi
    
    log_success "Local CI setup completed successfully!"
}

# Handle interrupts
trap 'log_error "Setup interrupted by user"; exit 130' INT TERM

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi