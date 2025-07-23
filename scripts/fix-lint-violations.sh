#!/bin/bash

# CI Framework - Emergency Lint Fix Script
# Run this when you get "Found 13 errors" in CI

set -e

echo "🚨 Emergency Lint Fix Script"
echo "================================"
echo ""

echo "📋 Step 1: Running quality checks to identify issues..."
if pixi run quality; then
    echo "✅ All quality checks pass locally"
else
    echo "❌ Quality checks failed - proceeding with fixes"
fi

echo ""
echo "🔧 Step 2: Running emergency fix (lint-fix + format + test)..."
pixi run emergency-fix

echo ""
echo "📋 Step 3: Running final quality check..."
if pixi run quality; then
    echo "✅ All issues fixed!"
else
    echo "❌ Some issues remain - manual intervention needed"
    echo ""
    echo "Please check the output above and fix manually:"
    echo "- Type errors: Check framework/ files"
    echo "- Test failures: Run pixi run test -v"
    echo "- Complex lint issues: Check ruff output"
    exit 1
fi

echo ""
echo "🎯 Step 5: Checking for uncommitted changes..."
if git diff --quiet; then
    echo "ℹ️  No changes to commit"
else
    echo "📝 Changes detected - ready to commit"
    echo ""
    echo "To commit the fixes:"
    echo "  git add ."
    echo "  git commit -m 'fix: auto-fix lint violations'"
    echo "  git push"
fi

echo ""
echo "🎉 Lint fix process complete!"
echo ""
echo "💡 To prevent this in future:"
echo "1. Always run 'pixi run quality' before committing"
echo "2. Install pre-commit hooks: pixi run install-pre-commit"
echo "3. Use 'pixi run emergency-fix' for quick fixes"
echo "4. Use 'pixi run lint-fix' to auto-fix lint issues only"