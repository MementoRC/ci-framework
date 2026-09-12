"""Tests guarding the scope and CI wiring of the `workflow-lint` pixi task.

Issue #279: ci.yml ran `python -m framework.workflow_lint` against a
hand-maintained six-file list, so 12 of the 18 files in `.github/workflows/`
were never linted - including `branch-policy.yml`, the exact file #255 found
a script injection in. `actionlint` (#255), `action-shellcheck` (#261) and
`yaml-lint` (#274) had each already been moved off hand-maintained lists;
this linter was the last one still reading from one.

These are the #255-shaped guards: derive both the linted set and the shipped
set from the filesystem and the manifest rather than hand-listing them, so a
future narrowing of scope (or a dropped CI invocation) fails a test instead
of silently shipping unlinted workflows.

The pixi-manifest and ci.yml parsing primitives these tests need live in
`framework/tests/utils/pixi_meta.py`, shared with `test_yaml_lint_scope.py`.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from framework.tests.utils.pixi_meta import (
    CI_WORKFLOW,
    WORKFLOWS_DIR,
    ci_invokes_task,
    iter_workflow_run_bodies,
    load_tasks,
    logical_run_lines,
    resolve_task_commands,
)
from framework.workflow_lint import discover_workflow_files

# A direct `python -m framework.workflow_lint` invocation, capturing whatever
# arguments follow it on the same logical line.
WORKFLOW_LINT_MODULE_RE = re.compile(
    r"python\s+-m\s+framework\.workflow_lint(?P<args>[^\n]*)"
)


def shipped_workflow_files() -> list[Path]:
    """Every workflow file GitHub would actually run from this repo.

    `.github/workflows/*.yml` and `*.yaml`, read off the filesystem rather
    than hand-listed. `python-ci-template.yml.template` is deliberately out of
    scope: it is scaffolding copied into consumer projects, not a workflow
    this repo runs, and it is not a standalone parseable workflow.

    The scan is deliberately flat rather than recursive. GitHub's workflow
    loader reads only files sitting directly in `.github/workflows/` and
    ignores subdirectories, so an `rglob` here would assert coverage of files
    that never run - and would then disagree with `discover_workflow_files`,
    which is flat for the same reason.
    """
    return sorted(
        path
        for path in WORKFLOWS_DIR.iterdir()
        if path.is_file() and path.suffix in (".yml", ".yaml")
    )


def test_discovery_is_not_empty():
    """Vacuity guard: empty discovery would pass the coverage test for free."""
    assert shipped_workflow_files(), "no workflow files found - the walk is broken"
    assert discover_workflow_files(WORKFLOWS_DIR), (
        "framework.workflow_lint discovered no workflow files - discovery is broken"
    )


def test_workflow_lint_discovers_every_shipped_workflow():
    """`workflow_lint`'s discovery must cover every shipped workflow file."""
    discovered = {path.resolve() for path in discover_workflow_files(WORKFLOWS_DIR)}
    uncovered = [
        str(path)
        for path in shipped_workflow_files()
        if path.resolve() not in discovered
    ]
    assert not uncovered, (
        "these workflow files are outside framework.workflow_lint's discovery: "
        + "; ".join(sorted(uncovered))
    )


def test_workflow_lint_task_takes_no_file_list():
    """The `workflow-lint` task must lint by discovery, not by a file list."""
    tasks = load_tasks()
    assert "workflow-lint" in tasks, "'workflow-lint' task missing from pyproject.toml"
    commands = resolve_task_commands(tasks, "workflow-lint")
    assert commands, "'workflow-lint' resolved to no command - the parse is broken"
    for cmd in commands:
        match = WORKFLOW_LINT_MODULE_RE.search(cmd)
        assert match is not None, (
            f"'workflow-lint' does not invoke framework.workflow_lint: {cmd!r}"
        )
        args = match.group("args").strip()
        assert not args, (
            "'workflow-lint' passes an explicit file list to "
            f"framework.workflow_lint ({args!r}); pass nothing so discovery "
            f"walks {WORKFLOWS_DIR} (#279)"
        )


def test_workflow_lint_is_invoked_by_ci():
    """`workflow-lint` must actually be invoked by some job in ci.yml."""
    tasks = load_tasks()
    assert "workflow-lint" in tasks, "'workflow-lint' task missing from pyproject.toml"
    assert ci_invokes_task("workflow-lint"), (
        "'workflow-lint' exists in pyproject.toml but no `run:` step in "
        f"{CI_WORKFLOW} invokes it via `pixi run [-e <env>] workflow-lint`"
    )


def test_ci_does_not_pass_a_hand_maintained_file_list():
    """No ci.yml step may pass explicit paths to framework.workflow_lint.

    The regression #279 records: the invocation named six files, all of which
    existed, so nothing looked stale - it was simply missing twelve others.
    """
    doc = yaml.safe_load(CI_WORKFLOW.read_text())
    body_text = "\n".join(
        line
        for body in iter_workflow_run_bodies(doc)
        for line in logical_run_lines(body)
    )
    offenders = [
        match.group("args").strip()
        for match in WORKFLOW_LINT_MODULE_RE.finditer(body_text)
        if match.group("args").strip()
    ]
    assert not offenders, (
        f"{CI_WORKFLOW} passes an explicit file list to framework.workflow_lint "
        f"({offenders!r}); lint by discovery instead (#279)"
    )
