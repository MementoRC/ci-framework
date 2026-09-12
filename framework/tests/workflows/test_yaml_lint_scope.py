"""Tests guarding the scope and CI wiring of the `yaml-lint` pixi task.

Issue #274: `yaml-lint` (`yamllint .github/workflows/`) only covers the
top-level workflow YAML files, leaving every composite `action.yml`/
`action.yaml` in the repo unlinted by yamllint. Worse, no CI job invokes
`yaml-lint` at all, so it cannot fail even for the files it does cover.

This is the #255-shaped guard: derive the actually-linted paths and the
actually-shipped YAML universe from the manifest/filesystem themselves,
rather than hand-listing "the files this covers", so a future narrowing of
scope (or a dropped CI invocation) fails a test instead of silently
shipping unlinted YAML.

The pixi-manifest and ci.yml parsing primitives these tests need live in
`framework/tests/utils/pixi_meta.py`, shared with
`test_workflow_lint_scope.py`.
"""

from __future__ import annotations

import re
from pathlib import Path

from framework.tests.utils.pixi_meta import (
    CI_WORKFLOW,
    WORKFLOWS_DIR,
    ci_invokes_task,
    load_tasks,
    resolve_task_commands,
)

REPO_ROOT = Path(".")

# Directories that never contain shipped YAML worth linting: VCS internals,
# the pixi environment cache, JS deps, the scaffolding template (which is
# copied into *other* projects, not linted by *this* repo's gate), and
# `.claude/` — gitignored agent-worktree scratch space that can contain
# stray duplicate `action.yml` copies that were never actually shipped.
EXCLUDED_DIR_NAMES = {".git", ".pixi", "node_modules", "templates", ".claude"}

# A single `-f`/`-d`/`--strict`-style flag, optionally with an attached
# `=value`, or a flag followed by a separate value token. Anything left over
# after stripping the leading `yamllint` and these flags is a path argument.
YAMLLINT_FLAG_WITH_VALUE_RE = re.compile(r"^-[a-zA-Z]$|^--[\w-]+$")
YAMLLINT_FLAGS_TAKING_VALUE = {"-f", "-d", "-c"}


def yamllint_linted_paths(cmd: str) -> list[str]:
    """Extract the path arguments from a `yamllint ...` command.

    Skips the leading `yamllint` token, drops flags like `-f`, `-d`,
    `--strict`, and the value that follows a flag known to take one, and
    treats everything else as a path argument.
    """
    tokens = cmd.strip().split()
    if not tokens or tokens[0] != "yamllint":
        return []
    paths = []
    skip_next = False
    for token in tokens[1:]:
        if skip_next:
            skip_next = False
            continue
        if YAMLLINT_FLAG_WITH_VALUE_RE.match(token):
            if token in YAMLLINT_FLAGS_TAKING_VALUE:
                skip_next = True
            continue
        paths.append(token)
    return paths


def discover_shipped_yaml_files() -> list[Path]:
    """Find every YAML file yaml-lint ought to be able to cover.

    Covers `.github/workflows/*.yml`/`*.yaml`, and every `action.yml`/
    `action.yaml` anywhere in the repo (composite actions are not confined
    to any one directory). Walks the tree rather than hand-listing action
    directories, so a newly added action is discovered automatically —
    the exact staleness failure mode named in #255/#261.
    """
    found: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in (".yml", ".yaml"):
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        is_workflow_file = path.parent == WORKFLOWS_DIR
        is_action_file = path.name in ("action.yml", "action.yaml")
        if is_workflow_file or is_action_file:
            found.append(path)
    return found


def path_is_covered(path: Path, linted_paths: list[str]) -> bool:
    """True when `path` sits inside (or equals) at least one linted path."""
    resolved = path.resolve()
    for linted in linted_paths:
        linted_path = Path(linted).resolve()
        if resolved == linted_path or linted_path in resolved.parents:
            return True
    return False


def test_yaml_lint_scope_is_not_empty():
    """Vacuity guard: a silently-empty discovery would pass the coverage test for free."""
    tasks = load_tasks()
    commands = resolve_task_commands(tasks, "yaml-lint")
    linted_paths = [p for cmd in commands for p in yamllint_linted_paths(cmd)]
    shipped = discover_shipped_yaml_files()
    assert shipped, "no shipped YAML files discovered — walk is broken"
    assert linted_paths, (
        "'yaml-lint' resolved to no yamllint path arguments — parse is broken"
    )


def test_yaml_lint_covers_every_shipped_yaml_tree():
    """Every shipped workflow/action YAML file must fall under a linted path.

    Currently fails: `yaml-lint-impl` only lints `.github/workflows/`, so
    every `action.yml`/`action.yaml` in the repo is outside its scope.
    """
    tasks = load_tasks()
    assert "yaml-lint" in tasks, "'yaml-lint' task not found in pyproject.toml"
    commands = resolve_task_commands(tasks, "yaml-lint")
    linted_paths = [p for cmd in commands for p in yamllint_linted_paths(cmd)]

    shipped = discover_shipped_yaml_files()
    uncovered = [
        str(path) for path in shipped if not path_is_covered(path, linted_paths)
    ]
    assert not uncovered, (
        "these shipped YAML files are outside 'yaml-lint's scope "
        f"(linted paths: {linted_paths!r}): " + "; ".join(sorted(uncovered))
    )


def test_yaml_lint_is_invoked_by_ci():
    """`yaml-lint` must actually be invoked by some job in ci.yml.

    Currently fails: the task exists in pyproject.toml but nothing in
    ci.yml runs it, so a regression in yamllint findings can never fail CI.
    """
    tasks = load_tasks()
    assert "yaml-lint" in tasks, "'yaml-lint' task not found in pyproject.toml"
    assert ci_invokes_task("yaml-lint"), (
        "'yaml-lint' task exists in pyproject.toml but no `run:` step in "
        f"{CI_WORKFLOW} invokes it via `pixi run [-e <env>] yaml-lint`"
    )
