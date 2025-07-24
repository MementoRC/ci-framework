#!/bin/bash

# Manual script to clean development artifacts from development branch
# This fixes the immediate issue while we perfect the automated workflow

set -e

echo "🧹 Manual cleanup of development artifacts from development branch..."

# Check if we're on development branch
current_branch=$(git branch --show-current)
if [ "$current_branch" != "development" ]; then
    echo "❌ Error: This script must be run from the development branch"
    echo "Current branch: $current_branch"
    exit 1
fi

echo "✅ Running on development branch"

# Files and directories to remove
files_to_remove=(
    ".claude"
    "CLAUDE.md"
    "ai_docs"
    "__pycache__"
    ".pytest_cache"
    "htmlcov"
    "coverage.xml"
    "coverage.json"
    ".coverage"
    ".mypy_cache"
    ".ruff_cache"
    "artifacts"
    "logs"
    "performance_data"
    "tmp"
    "debug"
    ".cache"
    "build"
    "dist"
    "*.egg-info"
    ".tox"
    ".nox"
    "*.pyc"
    "*.pyo"
    "*.pyd"
    "*.tmp"
    "*.temp"
    "*.swp"
    "*.swo"
    "*~"
    ".DS_Store"
    "Thumbs.db"
    "*.bak"
    "*.backup"
    "*.orig"
    ".env.local"
    ".env.*.local"
    "secrets.json"
    ".secrets.baseline"
    ".prof"
    "*.prof"
    "node_modules"
    "package-lock.json"
    "yarn.lock"
)

removed_files=()

for pattern in "${files_to_remove[@]}"; do
    if [[ "$pattern" == *"*"* ]]; then
        # Handle patterns with wildcards
        for file in $pattern; do
            if [[ -e "$file" ]]; then
                echo "Removing: $file"
                rm -rf "$file"
                removed_files+=("$file")
            fi
        done
    else
        # Handle exact file/directory names
        if [[ -e "$pattern" ]]; then
            echo "Removing: $pattern"
            rm -rf "$pattern"
            removed_files+=("$pattern")
        fi
    fi
done

# Log what was removed
if [ ${#removed_files[@]} -gt 0 ]; then
    echo ""
    echo "🗑️  Removed files/directories:"
    printf '  - %s\n' "${removed_files[@]}"
    echo ""
    
    # Commit the changes
    git add -A
    git commit -m "chore: manual cleanup of development artifacts from development branch

Removed development files that shouldn't be in production branches:

$(printf '- %s\n' "${removed_files[@]}")

This manual cleanup fixes the issue where the automated cleanup workflow
failed to remove these files. Future automated cleanups should work correctly.

Manual cleanup script: scripts/manual-cleanup-development.sh"

    echo "✅ Changes committed. Ready to push."
    echo ""
    echo "To push the changes, run:"
    echo "  git push origin development"
    
else
    echo "✅ No dev files found to remove - development branch is already clean!"
fi

echo ""
echo "🎯 Development branch cleanup complete!"